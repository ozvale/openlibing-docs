# vul-view-org-adapt — 技术设计

## 1. 概述

本设计将漏洞视图从单社区（OpenEuler）扩展为多社区支持，涉及数据同步、持久化、查询三个层面的改造。

## 2. 数据模型变更

### 2.1 VulnerabilityLifecycle 实体

新增两个字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `product_type` | TEXT | 社区标识，如 openEuler、openGauss |
| `issue_url` | TEXT | Issue 详情页 URL |

```java
@Column(name = "product_type", columnDefinition = "TEXT")
private String productType;

@Column(name = "issue_url", columnDefinition = "TEXT")
private String issueUrl;
```

### 2.2 IssueDetail 响应模型

新增 `issueUrl` 字段，与远程 API 返回结构对齐：

```java
private String issueUrl;
```

### 2.3 VulnerabilityVo 视图对象

新增 `issueUrl` 和 `productType` 字段：

```java
private String issueUrl;
private String productType;
```

### 2.4 ShowVulnerabilityVo 封装类

新增外层封装，表达一对多关系：

```java
public class ShowVulnerabilityVo {
    private String vulId;
    private List<VulnerabilityVo> data;
}
```

- `ShowVulnerabilityVo` 作为外层封装，语义清晰：一个 CVE 编号对应多条 Issue 数据
- `VulnerabilityVo` 保持原有字段不变，新增 `issueUrl` 和 `productType`

## 3. Repository 层变更

### VulnerabilityLifecycleRepository

新增方法：

```java
void deleteByProductType(String productType);
List<VulnerabilityLifecycle> findByCveNumAndProductType(String cveNum, String productType);
```

- `deleteByProductType`：按社区删除，支持逐社区全量刷新
- `findByCveNumAndProductType`：按 CVE 编号 + 社区查询，替代原来的 `findByCveNum`

## 4. Feign Client 变更

### VulViewClient

接口方法新增 `org` 参数：

```java
@GetMapping("/admin/ci-portal/ci-admin/cve/details")
MajunVulDetailsResponse getMajunVulDetails(@RequestParam("org") String org);
```

远程 API 通过 `?org=xxx` 查询参数区分社区。

## 5. 同步服务改造

### MajunVulServiceImpl.syncMajunVulData

改造前：单次调用，仅同步 OpenEuler 社区数据。

改造后：遍历所有 active 社区逐个同步。

```java
@Override
public void syncMajunVulData() {
    List<ProductType> productTypes = productTypeRepository.findAll().stream()
            .filter(pt -> Boolean.TRUE.equals(pt.getActive()))
            .toList();
    for (ProductType pt : productTypes) {
        String org = pt.getType();
        try {
            MajunVulDetailsResponse majunVulDetails = vulViewClient.getMajunVulDetails(org);
            List<IssueDetail> details = majunVulDetails.getResult();
            List<VulnerabilityLifecycle> lifecycles = details.stream()
                .map(detail -> {
                    VulnerabilityLifecycle vl = new VulnerabilityLifecycle();
                    vl.setIssueId(detail.getIssueId());
                    vl.setIssueCustomizeState(detail.getIssueCustomizeState());
                    vl.setAffectedSoftware(detail.getAffectedSoftware());
                    vl.setUnAffectedBranches(detail.getUnAffectedBranches());
                    vl.setAffectedBranches(detail.getAffectedBranches());
                    vl.setNotAnalyzedBranches(detail.getNotAnalyzedBranches());
                    vl.setCveNum(detail.getCveNum());
                    String versions = (detail.getVersions() != null) ? detail.getVersions().toString() : null;
                    vl.setVersions(versions);
                    vl.setReasonMap(detail.getReasonMap());
                    vl.setStateMap(detail.getStateMap());
                    vl.setProductType(org);
                    vl.setIssueUrl(detail.getIssueUrl());
                    return vl;
                })
                .toList();

            vulnerabilityLifecycleRepository.deleteByProductType(org);
            vulnerabilityLifecycleRepository.saveAll(lifecycles);
            logger.info("finish sync org={}, size={}", org, lifecycles.size());
        } catch (Exception e) {
            logger.error("sync vul data failed for org={}", org, e);
        }
    }
}
```

关键变化：
- 遍历 `product_type` 表获取 active 社区列表
- 逐社区调用 API（传 org 参数）
- 每个 `VulnerabilityLifecycle` 记录设置 `productType` 和 `issueUrl`
- 按社区维度刷新：`deleteByProductType(org)` + `saveAll`
- 单社区失败不影响其他社区

## 6. 查询服务改造

### SbomServiceImpl.queryVulnerability

`PageVo<VulnerabilityVo>` 改为 `PageVo<ShowVulnerabilityVo>`，`productType` 提前解析一次传入 `getVulnerabilityStatus`：

```java
@Override
public PageVo<ShowVulnerabilityVo> queryVulnerability(String productName, String packageId,
                                                      String severity, String vulId, Pageable pageable) {
    Page<Vulnerability> result = vulnerabilityRepository.findByProductNameAndPackageIdAndSeverityAndVulId(
            productName, Objects.isNull(packageId) ? null : UUID.fromString(packageId), severity, vulId, pageable);
    Package pkg = packageRepository.findById(UUID.fromString(packageId)).orElse(new Package());
    String productType = resolveProductType(pkg, productName);
    List<ShowVulnerabilityVo> showVoList = result.stream()
            .map(v -> getVulnerabilityStatus(productName, v, productType))
            .toList();
    return new PageVo<>(new PageImpl<>(showVoList, result.getPageable(), result.getTotalElements()));
}

private String resolveProductType(Package pkg, String productName) {
    if (pkg != null && pkg.getSbom() != null && pkg.getSbom().getProduct() != null) {
        String pkgProductType = pkg.getSbom().getProduct().getProductType();
        if (pkgProductType != null) {
            return pkgProductType;
        }
    }
    return productName;
}
```

### SbomServiceImpl.getVulnerabilityStatus

返回类型改为 `ShowVulnerabilityVo`，接收 `productType` 参数而非 `Package`：

```java
public ShowVulnerabilityVo getVulnerabilityStatus(String productName, Vulnerability vulnerability, String productType) {
    List<VulnerabilityLifecycle> vulnerabilityList = vulnerabilityLifecycleRepository
            .findByCveNumAndProductType(vulnerability.getVulId(), productType);
    ShowVulnerabilityVo showVo = new ShowVulnerabilityVo();
    showVo.setVulId(vulnerability.getVulId());
    if (vulnerabilityList.isEmpty()) {
        return showVo;
    }

    Gson gson = new Gson();
    Type type = new TypeToken<Map<String, String>>() {}.getType();

    List<VulnerabilityVo> voList = vulnerabilityList.stream()
        .map(vl -> {
            VulnerabilityVo vo = new VulnerabilityVo();
            vo.setVulId(vulnerability.getVulId());
            VulnerabilityVo.inferAndSetScore(vo, vulnerability);
            vo.setIssueId(vl.getIssueId());
            vo.setIssueCustomizeState(vl.getIssueCustomizeState());
            vo.setIssueUrl(vl.getIssueUrl());
            vo.setProductType(vl.getProductType());
            vo.setAffectedSoftware(vl.getAffectedSoftware());
            vo.setAffectedBranches(vl.getAffectedBranches());
            vo.setUnAffectedBranches(vl.getUnAffectedBranches());
            vo.setNotAnalyzedBranches(vl.getNotAnalyzedBranches());

            String stateMapString = vl.getStateMap();
            if (StringUtils.isNotBlank(stateMapString) && !"{}".equals(stateMapString)) {
                Map<String, String> stateMap = gson.fromJson(stateMapString, type);
                for (Map.Entry<String, String> entry : stateMap.entrySet()) {
                    if (productName.contains(entry.getKey())) {
                        vo.setState(entry.getValue());
                        break;
                    }
                }
            }

            String reasonMapString = vl.getReasonMap();
            if (StringUtils.isNotBlank(reasonMapString) && !"{}".equals(reasonMapString)) {
                Map<String, String> reasonMap = gson.fromJson(reasonMapString, type);
                for (Map.Entry<String, String> entry : reasonMap.entrySet()) {
                    if (productName.contains(entry.getKey())) {
                        vo.setReason(entry.getValue());
                        break;
                    }
                }
            }
            return vo;
        })
        .toList();

    showVo.setData(voList);
    return showVo;
}
```

关键变化：
- `queryVulnerability` 中提前调用 `resolveProductType` 解析一次 productType
- `getVulnerabilityStatus` 签名从 `(productName, vulnerability, pkg)` 改为 `(productName, vulnerability, productType)`
- 使用 `findByCveNumAndProductType` 替代 `findByCveNum`，数据库层面按社区过滤
- 返回 `ShowVulnerabilityVo` 封装一对多关系

## 7. 接口层变更

### SbomService 接口

```java
PageVo<ShowVulnerabilityVo> queryVulnerability(String productName, String packageId,
                                                String severity, String vulId, Pageable pageable);
```

### SbomController

```java
PageVo<ShowVulnerabilityVo> vulnerabilities = sbomService.queryVulnerability(productName, packageId, severity, vulId, pageable);
```

## 8. 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 远程 API 某社区返回异常导致该社区数据丢失 | 单社区 try-catch 隔离，失败跳过不影响其他社区 |
| `deleteByProductType` + `saveAll` 非原子操作，中途失败数据丢失 | 同步任务由 Quartz 调度，下次执行会重新同步；可考虑事务包覆 |
| 存量 `vulnerability_lifecycle` 数据无 `product_type` | 新增列允许 NULL；首次同步后所有数据均有 productType |
| Feign GET 传参方式与远程不匹配 | 需确认远程 API 接受 `?org=xxx` 查询参数格式 |
| 一对多返回结构变更影响前端 | 新增 `ShowVulnerabilityVo` 封装层，`VulnerabilityVo` 新增字段但不删原有字段；前端需适配新结构 |

## 9. 跨仓影响

无跨仓影响。变更仅涉及 `openlibing-sbom` 仓内部。
