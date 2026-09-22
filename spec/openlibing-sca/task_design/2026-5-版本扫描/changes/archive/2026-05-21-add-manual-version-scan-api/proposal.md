# Proposal: Add Manual Version Scan API

## Summary

为 `tbl_manual_version_scan` 表新增 4 个 REST 接口：新增记录、条件查询、删除记录、启动版本扫描。扫描完成后通过修改 `saveVersionScanResult` 回调更新 `scanResult` 状态。

## Motivation

当前 `tbl_manual_version_scan` 表的 Liquibase 建表脚本和 MyBatis Mapper XML 已就绪，但 Java 层（Entity、Mapper 接口、Service、Controller）均未实现。需要补全完整的 CRUD + 扫描触发能力，使前端可以管理社区版本扫描记录并触发扫描。

## Scope

### 新增文件（5个）

| 文件 | 说明 |
|------|------|
| `analysis/entity/TblManualVersionScan.java` | 实体类，对应 `tbl_manual_version_scan` 表 |
| `analysis/dao/TblManualVersionScanMapper.java` | Mapper 接口，方法与已有 XML 对应 |
| `analysis/service/ManualVersionScanService.java` | Service 接口 |
| `analysis/service/impl/ManualVersionScanServiceImpl.java` | Service 实现 |
| `analysis/controller/ManualVersionScanController.java` | REST Controller，4 个接口 |

### 修改文件（2个）

| 文件 | 说明 |
|------|------|
| `dm/service/impl/IntegrationApiServiceImpl.java` | `saveVersionScanResult` 中新增：通过 scanId 查找并更新 `tbl_manual_version_scan` 的 `scanResult=1` + `modified` |
| `common/config/rabbitmq/IntegrationApiListener.java` | 异常路径中新增：scanResult=-1 时同步更新 `tbl_manual_version_scan` |

### 不在范围内

- 不修改 `tbl_manual_version_scan` 表结构
- 不修改已有的 Mapper XML
- 不修改 `startVersionScan` 方法本身
- 不新增操作日志注解（`@LogApi`）

## API Design

### 1. 新增记录

- **POST** `/manual/version/scan/add`
- 入参：`communityId`, `repoUrl`, `repoName`, `repoId`, `branch`, `platform`, `isScan`
- 初始状态：`scanResult=null`, `scanId=null`, `created=now`, `modified=now`
- 返回：`ResponseEntity.success()`

### 2. 条件查询

- **POST** `/manual/version/scan/list`
- 入参：`communityId`（精确）, `repoName`（模糊）, `repoUrl`（模糊）, `platform`（精确）
- 返回：`ResponseEntity(200, "查询成功", list, list.size())`

### 3. 删除记录

- **POST** `/manual/version/scan/delete`
- 入参：`id`
- 返回：`ResponseEntity.success()`

### 4. 启动版本扫描

- **POST** `/manual/version/scan/start`
- 入参：`id`, `repoUrl`, `branch`, `projectName`
- 流程：
  1. 构建 `VersionScanPo(repoUrl, branch, projectName)`
  2. 调用 `integrationApiService.startVersionScan(po)` 获取 `scanId`
  3. 更新记录：`scanId=scanId`, `scanResult=0`, `modified=now`, `scanTime=now`
- 返回：`ResponseEntity.success(scanId)`

## Scan Result State Machine

```
null ──startScan──▶ 0 (扫描中) ──saveVersionScanResult──▶ 1 (扫描完成)
                                 ──异常路径──────────────▶ -1 (扫描失败)
```

## Risks

- `saveVersionScanResult` 是共享方法，修改时需确保不影响现有版本扫描流程
- 需在 Mapper 中新增 `updateByScanId` 方法（通过 scanId 而非主键更新），XML 也需同步
