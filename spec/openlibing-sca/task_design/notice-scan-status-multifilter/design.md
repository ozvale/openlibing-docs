# notice-scan-status-multifilter — 技术设计

## 1. 方案设计

一句话：SCA 新增状态聚合查询接口——入参透传 SBOM internal-api 换取制品名清单，再按制品名批量查本仓 `tbl_project_notice_scan` 每制品最新扫描状态，组装 VO 全量返回。

```text
前端 → POST /project/notice/scan/scanStatusByMultiFilter（body 同 SBOM queryProductListMultiFilter）
     → ProjectNoticeScanService.queryScanStatusByMultiFilter
     → OpenlibingSbomClient.queryProductNamesByMultiFilter（POST /internal-api/queryProductNamesByMultiFilter）
     ← DataResult{code,msg,data: List<String>} 制品名
     → TblProjectNoticeScanMapper.selectLatestByProjectNames(names)
     ← 每制品最新一条扫描记录
     → List<ProjectNoticeScanStatusVO> 全量返回
```

架构决策：

- 复用既有 `OpenlibingSbomClient` Feign 客户端（`url = ${sca.to.sbom.url:}`），不新建客户端。
- 请求 PO 在 SCA 侧镜像 SBOM `QueryProductListMultiFilterRequest` 字段（同名同义，JSON 序列化后同构），不引入对 SBOM 仓的编译依赖。
- 批量取最新记录用 `ROW_NUMBER() OVER (PARTITION BY project_name ORDER BY create_time DESC, id DESC)`（仓内 `TblScanMapper.xml` 已有窗口函数先例），一次查询消除 `GROUP BY + JOIN` 在 `create_time` 并列时的双行问题，`id DESC` 兜底并列确定性。
- `sortField` / `sortDir` / `pageNum` / `pageSize` 仅透传：SBOM internal-api 契约声明忽略排序分页，返回形态已确认为全量列表，SCA 侧不做二次分页。

## 2. 实现逻辑设计

`ProjectNoticeScanServiceImpl#queryScanStatusByMultiFilter`：

1. `productType` 空白 → 抛 `ScaException(60000, "查询失败", "productType不能为空")`（与 SBOM 侧校验语义一致，避免无效跨服务调用）。
2. Feign 调 internal-api，`try/catch` → 失败抛 `ScaException(60000, "查询失败", "调用SBOM服务获取制品名称失败")`（非 2xx 时 Feign 抛 `FeignException`，统一兜底，不向调用方泄露内部细节）。
3. 响应校验：`resp == null || resp.getCode() != 200 || resp.getData() == null` → 同上异常（SBOM `DataResult{code,msg,data}` 的 `code` 字段经 Feign 反序列化到 SCA `ResponseEntity.code`，与 `queryProductConfig` 既有消费模式一致）。
4. 制品名列表为空 → 直接返回空列表，不发 DB 查询。
5. `selectLatestByProjectNames(names)` → 按 `projectName` 建 Map（窗口函数保证一制品一行，Map 兜底容忍脏数据并列）。
6. 按 SBOM 返回顺序组装 VO：有记录 → `status=记录状态`、`statusName=ProjectNoticeScanStatus.nameOf(status)`；无记录 → `status=null`、`statusName="未扫描"`。
7. VO 仅含 3 个字段，天然不透出 `mergedOssUrl` / `errorMsg`。

Controller 沿用既有模板：入参 info 日志 + `try/catch(ScaException → failure(code, msg, advice))` + `catch(Exception → failure("查询失败"))`。

## 3. 类设计

| 类                                                                     | 位置                  | 操作 | 说明                                                                                                                        |
| ---------------------------------------------------------------------- | --------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------- |
| `ProjectNoticeScanMultiFilterQueryPo`                                  | `analysis/entity/dto` | 新增 | 请求体 PO：`productType` / `filters(Map<String,String>)` / `sortField` / `sortDir` / `pageNum` / `pageSize`，镜像 SBOM 请求 |
| `ProjectNoticeScanStatusVO`                                            | `analysis/entity/vo`  | 新增 | 返回 VO：`productName` / `status` / `statusName`                                                                            |
| `OpenlibingSbomClient`                                                 | `common/feign`        | 修改 | 新增 `POST /internal-api/queryProductNamesByMultiFilter`                                                                    |
| `ProjectNoticeScanService`                                             | `dm/service`          | 修改 | 新增 `queryScanStatusByMultiFilter` 声明                                                                                    |
| `ProjectNoticeScanServiceImpl`                                         | `dm/service/impl`     | 修改 | 新增实现（见 §2）                                                                                                           |
| `ProjectNoticeScanController`                                          | `dm/controller`       | 修改 | 新增 `POST /scanStatusByMultiFilter`                                                                                        |
| `TblProjectNoticeScanMapper`                                           | `dm/dao`              | 修改 | 新增 `selectLatestByProjectNames(List<String>)`                                                                             |
| `TblProjectNoticeScanMapper.xml`                                       | `resources/mapper/dm` | 修改 | 新增窗口函数 SQL                                                                                                            |
| `ProjectNoticeScanServiceImplTest` / `ProjectNoticeScanControllerTest` | `test`                | 修改 | 补用例                                                                                                                      |

## 4. 数据模型设计

无表结构变更。只读查询既有 `tbl_project_notice_scan`（`project_name` 即 SBOM 制品名）：

```sql
SELECT id, scan_id, project_name, release_name, total_count, success_count, fail_count,
       merged_oss_url, status, error_msg, create_time, update_time, finish_time
FROM (
  SELECT t.*, ROW_NUMBER() OVER (PARTITION BY project_name ORDER BY create_time DESC, id DESC) AS rn
  FROM tbl_project_notice_scan t
  WHERE project_name IN (#{...foreach...})
) ranked
WHERE ranked.rn = 1
```

`project_name` 检索模式与既有 `selectLatestByProjectName` 一致，不在本需求内新增索引。

## 5. 性能设计

- 制品名数量 = SBOM 过滤后全量，预估千级以内，单条 `IN` 查询可接受；未来若到万级，再引入分批查询（如每 500 一批合并结果），本期不实现，记录为已知边界。
- 窗口函数排序范围为命中制品的历史扫描记录，量级可控。
- 跨服务调用仅 1 次（SBOM），无循环调用。

## 6. API 接口设计

`POST /project/notice/scan/scanStatusByMultiFilter`

请求体（与 SBOM `/sbom-api/queryProductListMultiFilter` 请求体一致，无 `userId`）：

```json
{
  "productType": "binary",
  "filters": { "NAME": "openEuler" },
  "sortField": null,
  "sortDir": null,
  "pageNum": 0,
  "pageSize": 10
}
```

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "data": [
    { "productName": "openEuler-24.03", "status": 2, "statusName": "成功" },
    { "productName": "not-scanned", "status": null, "statusName": "未扫描" }
  ],
  "total": 0
}
```

失败响应：`code=60000`、`message="查询失败"`、`data`=具体原因（productType 不能为空 / 调用SBOM服务获取制品名称失败）。

## 7. 安全设计

详见 `spec/openlibing-sca/system_design/threat-model.md` 与 `security-design.md`。要点：

- 输入：`filters` / `sortField` 仅透传 SBOM（其服务层有 key 白名单校验）；SCA 侧 SQL 全参数化（`#{}` + `<foreach>`），无拼接注入面。
- 最小化：VO 仅 3 字段，不透出 OBS 内部地址与错误详情。
- 鉴权：与同 Controller 既有接口一致，由网关统一认证，SCA 侧不新增鉴权。
- 失败安全：SBOM 不可用时返回业务失败，不降级为无过滤查询。

## 风险 & 缓解

- SBOM internal-api 为 sbom-dev 分支新增接口，若线上版本未包含 → 部署对齐问题，联调阶段验证。
- `create_time` 并列 → 窗口函数 `id DESC` tie-break 消除。

## 跨仓影响

- 只读依赖 `openlibing-sbom` `/internal-api/queryProductNamesByMultiFilter`，不修改 SBOM 仓。
