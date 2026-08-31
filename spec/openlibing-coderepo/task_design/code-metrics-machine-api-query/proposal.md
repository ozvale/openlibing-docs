# coderepo 暴露代码度量时序关联查询接口 - Proposal

> 关联业务仓 spec：`openlibing-codecheck/task_design/full-codecheck-record-codeql-fallback`（同一次跨仓改动）
> 关联业务仓分支：`openlibing-coderepo: feat-code-metrics-machine-api-query`
> 状态：最终方案。等待开发完成。

## 1. 背景

`openlibing-codecheck` 仓的 `POST /machine-api/v1/full-codecheck-record/list` 接口当前数据源为 MongoDB `task_result_summary` 集合（华为云 CodeCheck 入库）。当某项目/仓库的分支未接入华为云 CodeCheck 时，该接口需要降级到 CodeQL 扫描结果组装数据。

CodeQL 扫描结果（`static_alarm_scan_run` + `static_alarm_issue`）位于 codecheck 仓，但代码度量扫描结果（`code_metrics_record`）位于 coderepo 仓。两条扫描链路独立运行，无共享 run id，需要按 `git_url + branch_name` 关联并按 `detection_completed_at` 时序取最近一次度量记录。

为支撑 codecheck 降级路径，coderepo 需要新增**机机接口专用 HTTP 查询接口**，供 codecheck 通过 Feign 调用。

## 2. 需求

### 2.1 新增 HTTP 接口

机机接口专用 Controller `MachineApiCodeMetricsController`，类级路径 `/machine-api/v1/metrics/code`：

| 路径                                                         | 方法 | 入参                                    | 出参                                       | 用途                               |
| ------------------------------------------------------------ | ---- | --------------------------------------- | ------------------------------------------ | ---------------------------------- |
| `POST /machine-api/v1/metrics/code/latest-before-time`       | POST | `LatestMetricsBeforeTimeQueryDTO`       | `DataResult<CodeMetricsSnapshotDTO>`       | 单条查询                           |
| `POST /machine-api/v1/metrics/code/latest-before-time/batch` | POST | `List<LatestMetricsBeforeTimeQueryDTO>` | `DataResult<List<CodeMetricsSnapshotDTO>>` | 批量查询（codecheck 主要调用入口） |

### 2.2 关联规则

- 关联键：`git_url + branch_name`
- 时序过滤：`detection_completed_at < beforeTime`，取 `detection_completed_at DESC` 第一条
- 失败记录过滤：`status = 0`（仅取成功度量记录）

### 2.3 metrics_data_json 新增字段

插件上报时 `metrics_data_json` 新增 6 个字段：

| #   | 字段                          | 类型    | 用途         |
| --- | ----------------------------- | ------- | ------------ |
| 1   | `codeLineTotal`               | Integer | 总代码行数   |
| 2   | `commentLines`                | Integer | 注释行数     |
| 3   | `complexityCount`             | Integer | 复杂度计数   |
| 4   | `cyclomaticComplexityPerFile` | Double  | 文件圈复杂度 |
| 5   | `duplicatedBlocks`            | Integer | 重复块数     |
| 6   | `duplicatedLines`             | Integer | 重复行数     |

## 3. In Scope

### 3.1 coderepo 仓改动

- **新增** `MachineApiCodeMetricsController`：机机接口专用 Controller，与现有 `CodeMetricsController`（前端接口）隔离
- **修改** `CodeMetricsService` / `CodeMetricsServiceImpl`：新增 `getLatestMetricsBeforeTime` 单条 + `getLatestMetricsBeforeTimeBatch` 批量两个 Service 方法
- **修改** `CodeMetricsRecordMapper` + xml：新增 `selectLatestBeforeTime` 单条 + `selectLatestBeforeTimeBatch` 批量两个 Mapper 方法
- **新增** `LatestMetricsBeforeTimeQueryDTO`：HTTP 接口入参 DTO
- **新增** `CodeMetricsSnapshotDTO`：HTTP 接口出参 DTO（含 `metricsDataJson` 原文，由 codecheck 自行解析各字段）
- **修改** 插件上报逻辑：`metrics_data_json` 新增 6 个字段上报
- **新增** 测试用例：HTTP 接口 + Service + Mapper 单元测试

### 3.2 不在范围

- 不动现有 `CodeMetricsController` 的 4 个接口（前端 + 上报接口）
- 不动 `getLatestMetricsByGitUrl` Service 方法（保留原「合并 5 指标」语义，供前端使用）
- 不动 `code_metrics_file_detail` 表（本次 codecheck 降级路径不对接 file_detail 字段）

## 4. 验收标准

### 4.1 接口契约

- `POST /latest-before-time` 入参 `LatestMetricsBeforeTimeQueryDTO`，3 个字段（`gitUrl` / `branchName` / `beforeTime`）均有 `@NotBlank` / `@NotNull` 校验
- `POST /latest-before-time/batch` 入参为 `List<LatestMetricsBeforeTimeQueryDTO>`，单次最大 100 条（超过拒绝）
- 出参 `CodeMetricsSnapshotDTO` 含 `metricsDataJson` 原文（不分解字段，由消费方自行解析）
- 找不到记录时返回空 list / null，不抛异常

### 4.2 数据正确性

- 单条查询：返回 `detection_completed_at < beforeTime AND status = 0` 的最近一条
- 批量查询：每个 `(gitUrl, branchName)` 取 `detection_completed_at` 最大的一条
- 失败度量记录（`status != 0`）不返回

### 4.3 metrics_data_json 字段

- 6 个新字段在插件上报时正确写入 `metrics_data_json`
- 字段缺失时（旧度量记录没有新字段）消费方自行兜底，coderepo 不强制补默认值

## 5. 遗留项

| 编号 | 遗留项                                                                                                                                                             | 时机               |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ |
| L-1  | `metrics_data_json` 6 个新字段最终字段名确认（暂命名见 §2.3）                                                                                                      | 插件改造时确认     |
| L-2  | 批量接口 SQL 在 MySQL 8 上的 IN 元组语法性能验证（建议加 `(git_url, branch_name, status, detection_completed_at)` 联合索引）                                       | 联调时验证         |
| L-3  | docs 仓 spec 分支名 `spec-code-metrics-action-metrics-new-fields` 不符合 AGENTS.md 命名规则（应为 `spec-openlibing-coderepo-<change-name>`），后续 PR 时考虑重命名 | docs PR 创建时处理 |

## 6. 跨仓联动

- 本 spec 与 `openlibing-codecheck/task_design/full-codecheck-record-codeql-fallback` 是同一次跨仓改动的两部分
- codecheck 侧依赖 coderepo 的 HTTP 接口暴露，Feign client 调通后才能完成降级路径
- 跨仓 PR 矩阵：coderepo 业务 PR 先行（暴露接口 + 字段）→ codecheck 业务 PR 跟进（Feign 调用 + 降级路径）→ docs PR 统一归档
