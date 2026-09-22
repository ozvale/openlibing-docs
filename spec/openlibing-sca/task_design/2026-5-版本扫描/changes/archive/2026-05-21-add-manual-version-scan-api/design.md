# Design: Add Manual Version Scan API

## Architecture

遵循项目现有的分层架构：

```
Controller (REST) → Service (业务逻辑) → Mapper (DAO) → MySQL
                                         ↓
                              IntegrationApiService.startVersionScan()
                                         ↓
                                    RabbitMQ → doScanV3()
                                         ↓
                              saveVersionScanResult() → 回调更新
```

## Data Model

### TblManualVersionScan Entity

| 字段 | Java类型 | DB类型 | 说明 |
|------|---------|--------|------|
| id | Integer | INT (AI, PK) | 主键 |
| communityId | String | VARCHAR(64) | 社区ID |
| repoUrl | String | VARCHAR(128) | 仓库地址 |
| repoName | String | VARCHAR(64) | 仓库名称 |
| repoId | String | VARCHAR(64) | 仓库ID |
| branch | String | VARCHAR(64) | 分支 |
| scanResult | Integer | INT(2) | 扫描结果 (null/0/1/-1) |
| platform | String | VARCHAR(32) | 平台 |
| scanId | String | VARCHAR(64) | 扫描ID |
| isScan | Integer | INT(2) | 是否接入版本扫描 |
| created | Date | DATETIME | 创建时间 |
| modified | Date | DATETIME | 更新时间 |
| scanTime | Date | DATETIME | 开始扫描时间 |

### scanResult 状态定义

| 值 | 含义 | 设置时机 |
|----|------|----------|
| null | 未扫描 | 新增记录时 |
| 0 | 扫描中 | startScan 接口调用后 |
| 1 | 扫描完成 | saveVersionScanResult 回调 |
| -1 | 扫描失败 | IntegrationApiListener 异常回调 |

## Component Design

### TblManualVersionScanMapper

方法与已有 XML 对应，新增一个方法：

| 方法 | 对应XML | 说明 |
|------|---------|------|
| `insert(TblManualVersionScan)` | insert | 插入 |
| `deleteByPrimaryKey(Integer)` | deleteByPrimaryKey | 按主键删除 |
| `selectByPrimaryKey(Integer)` | selectByPrimaryKey | 按主键查询 |
| `selectByCondition(TblManualVersionScan)` | selectByCondition | 条件查询 |
| `updateByPrimaryKey(TblManualVersionScan)` | updateByPrimaryKey | 按主键更新 |
| `updateScanResult(@Param("id") Integer, @Param("scanResult") Integer)` | updateScanResult | 更新扫描结果 |
| **`updateByScanId(@Param("scanId") String, @Param("scanResult") Integer)`** | **新增XML** | 通过scanId更新扫描结果 |

### ManualVersionScanService

| 方法 | 说明 |
|------|------|
| `add(TblManualVersionScan)` | 新增记录 |
| `list(TblManualVersionScan)` | 条件查询 |
| `deleteById(Integer)` | 按ID删除 |
| `startScan(Integer id, String repoUrl, String branch, String projectName)` | 启动版本扫描 |

### ManualVersionScanController

| 端点 | 方法 | HTTP方法 |
|------|------|----------|
| `/manual/version/scan/add` | add | POST |
| `/manual/version/scan/list` | list | POST |
| `/manual/version/scan/delete` | delete | POST |
| `/manual/version/scan/start` | startScan | POST |

## Key Design Decisions

### 1. 回调更新方式

在 `saveVersionScanResult` 中，扫描成功后通过 `scanRequestVO.getScanId()` 查找 `tbl_manual_version_scan` 中匹配的记录并更新 `scanResult=1` + `modified`。

需在 Mapper XML 中新增 `updateByScanId` SQL：

```xml
<update id="updateByScanId">
    UPDATE tbl_manual_version_scan
    SET scan_result = #{scanResult}, modified = NOW()
    WHERE scan_id = #{scanId}
</update>
```

### 2. 异常路径同步

在 `IntegrationApiListener` 中，当扫描异常时设置 `scanResult=-1`，同样需要通过 `scanId` 同步更新 `tbl_manual_version_scan`。

### 3. startScan 入参

前端传入 `id`（记录ID）+ `repoUrl` + `branch` + `projectName`。其中 `repoUrl`、`branch`、`projectName` 用于构建 `VersionScanPo` 传给 `integrationApiService.startVersionScan`。

### 4. Entity 风格

采用 `@Data` + `@NoArgsConstructor` 风格（参照 TblShieldRole），Date 字段加 `@JsonFormat` 注解，不做防御性复制（保持简洁，与多数现有 Entity 一致）。

## Dependency Injection

`ManualVersionScanServiceImpl` 需注入：
- `TblManualVersionScanMapper` — CRUD 操作
- `IntegrationApiService` — 调用 `startVersionScan`

`IntegrationApiServiceImpl` 中需注入：
- `TblManualVersionScanMapper` — 回调更新 scanResult
