# 技术方案：接口传参大小限制

## 方案选型

- ops 仓 Controller 普遍已带 `@Valid`/`@Validated`，`GlobalExceptionHandler` 已处理 `MethodArgumentNotValidException`，采用**声明式注解**（`@Max`/`@Size`）即可覆盖，无需拦截器或逐服务钳制。
- metric 仓 `GlobalExceptionHandler` 缺 `MethodArgumentNotValidException` 处理（此前校验失败会被通用 Exception 处理器吞成 500），本次补充该处理器，返回 400 + 字段校验消息（放在 `Result.data`）。

## 改动明细

### openlibing-metric（分支 fix-metric-dict-codes-limit）

| 文件 | 改动 |
|------|------|
| `api/controller/req/MetricDictQueryReq.java` | `codes` 加 `@Size(max = 200, message = "指标code数量不能超过200")` |
| `api/controller/DigitalMetricInfoController.java` | `getEnabledDict` 的 `@RequestBody` 加 `@Valid` |
| `infrastructure/exception/GlobalExceptionHandler.java` | 新增 `MethodArgumentNotValidException` 处理器，返回 `BAD_REQUEST` + 校验消息 |

### openlibing-ops（分支 fix-pagesize-upper-limit）

| 文件 | 改动 | 说明 |
|------|------|------|
| `api/request/common/detail/DetailReq.java` | `pageSize` 加 `@Max(100)` | 父类，覆盖约 35 个 detail 子类 |
| `api/request/ops/OpsOverviewMainReq.java` | 同上 | 工程能力看板主表 |
| `api/request/ops/OpsRepoDetailReq.java` | 同上 | |
| `api/request/ops/OpsResourceRunReq.java` | 同上 | |
| `api/request/external/ExternalRepoIssueDetailReq.java` | 同上 | 对外接口 |
| `api/request/external/IssueLegacyStatisticsDto.java` | 同上 + Schema 描述更新 | 遗留问题统计 |
| `api/request/report/ReportDataQueryReq.java` | `@Max(500)` | 与既有 Schema 描述和 service 层 `MAX_PAGE_SIZE=500` 钳制对齐 |

## 不受影响的路径（已核实）

- 导出接口：`OpsGithubController` 导出接口、`IssueLegacyDetailService`（`EXPORT_PAGE_SIZE=2000`）、`OpsGithubService`/`OpsOverviewMainExportService`（`EXPORT_MAX_ROWS`）均为 **service 内部 setPageSize**，入口校验只在 Controller 边界执行一次，前端导出也不传分页参数。
- 内部回填 `req.setPageSize(total)` 的服务（`DwiProjectStatisticsServiceImpl`、`DmRdEfcRepoSumPipelineStatisticsDayServiceImpl`、`DwiRepoPullRequestPipelineStatisticsServiceImpl`、`NightlyPipelineDashboardServiceImpl`）同理不受影响。
- GET 接口 `RepoController.queryAllRepoBranch` 的 `@RequestParam pageSize` 此前已有 `@Max(100)`。
