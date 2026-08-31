# coderepo 暴露代码度量 commit 关联查询接口 - Proposal

> 关联业务仓 spec：`openlibing-codecheck/task_design/full-codecheck-record-codeql-fallback`（同一次跨仓改动）
> 关联业务仓分支：`openlibing-coderepo: feat-code-metrics-machine-api-query`
> 状态：最终方案。实现已随业务 PR openlibing/openlibing-coderepo#159 交付。

## 1. 背景

`openlibing-codecheck` 仓的 `POST /machine-api/v1/full-codecheck-record/list` 接口当前数据源为 MongoDB `task_result_summary` 集合（华为云 CodeCheck 入库）。当某项目/仓库的分支未接入华为云 CodeCheck 时，该接口需要降级到 CodeQL 扫描结果组装数据。

CodeQL 扫描结果（`static_alarm_scan_run` + `static_alarm_issue`）位于 codecheck 仓，但代码度量扫描结果（`code_metrics_record`）位于 coderepo 仓。两条扫描链路独立运行，无共享 run id。同一 commit 触发的 CodeQL 扫描与度量扫描天然对应同一份代码快照，因此**按 `git_url + branch_name + commit_id` 三元组精确关联**（取代早期 `git_url + branch_name + beforeTime` 时序窗口方案，避免度量扫描时刻偏离导致指标失真）。

为支撑 codecheck 降级路径，coderepo 需要新增**机机接口专用 HTTP 查询接口**，供 codecheck 通过 Feign 调用。

## 2. 需求

### 2.1 新增 HTTP 接口

挂载在现有机机接口专用 Controller `InternalProjectRepoController`（类级路径 `/project-repo/internal`），不新建 Controller：

| 路径                                                                   | 方法 | 入参                                    | 出参                                       | 用途                               |
| ---------------------------------------------------------------------- | ---- | --------------------------------------- | ------------------------------------------ | ---------------------------------- |
| `POST /project-repo/internal/metrics/code/latest-by-commit/batch`      | POST | `List<LatestMetricsByCommitQueryDTO>`   | `DataResult<List<CodeMetricsSnapshotDTO>>` | 批量查询（codecheck 唯一调用入口） |

> 不提供单条接口：单条场景由调用方以 1 元素列表复用 batch 接口，避免维护两套契约。

### 2.2 关联规则

- 关联键：`git_url + branch_name + commit_id` 三元组精确匹配
- 失败记录过滤：`status = 0`（仅取成功度量记录）
- 排序取数：`detection_completed_at DESC`，同一 commit 重跑取最新一条
- 未命中的三元组不出现在返回结果中，由调用方（codecheck）自行兜底默认值

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

插件端同时上报 `commitId`（取 `process.env['ATOMGIT_SHA']`），入库到 `code_metrics_record.commit_id` 列，作为本接口的关联键。

## 3. In Scope

### 3.1 coderepo 仓改动

- **修改** `InternalProjectRepoController`：新增机机接口 `POST /metrics/code/latest-by-commit/batch`（与现有 `CodeMetricsController` 前端接口隔离）
- **修改** `CodeMetricsService` / `CodeMetricsServiceImpl`：新增 `getLatestMetricsByCommitBatch` 批量 Service 方法 + `toSnapshotDto` 私有转换方法
- **修改** `CodeMetricsRecordMapper` + xml：新增 `selectLatestByCommitBatch` 批量 Mapper 方法（三元组 IN SQL）
- **新增** `LatestMetricsByCommitQueryDTO`：HTTP 接口入参 DTO（`gitUrl` / `branchName` / `commitId`）
- **新增** `CodeMetricsSnapshotDTO`：HTTP 接口出参 DTO（含 `metricsDataJson` 原文与 `commitId`，由 codecheck 自行解析各字段）
- **修改** `CodeMetricsRecordEntity`：新增 `commitId` 字段
- **修改** `db.changelog.xml`：Liquibase 新增 `commit_id` 列（幂等：columnExists 前置检查）
- **修改** 插件上报逻辑：`metrics_data_json` 新增 6 个字段 + `commitId` 上报
- **修改** 测试用例：`CodeMetricsServiceImplTest` 补充批量查询用例

### 3.2 不在范围

- 不动现有 `CodeMetricsController` 的 4 个接口（前端 + 上报接口）
- 不动 `getLatestMetricsByGitUrl` Service 方法（保留原「合并 5 指标」语义，供前端使用）
- 不动 `code_metrics_file_detail` 表（本次 codecheck 降级路径不对接 file_detail 字段）
- 不新建 `(git_url, branch_name, commit_id)` 全量联合索引（现有 `idx_git_url_branch` 前缀可支撑，留待性能验证后评估）

## 4. 验收标准

### 4.1 接口契约

- `POST /latest-by-commit/batch` 入参为 `List<LatestMetricsByCommitQueryDTO>`，3 个字段（`gitUrl` / `branchName` / `commitId`）均有 `@NotBlank` 校验
- 入参列表 `@Size(min = 1, max = 100)`，单次最大 100 条（超过拒绝）
- 出参 `CodeMetricsSnapshotDTO` 含 `metricsDataJson` 原文（不分解字段，由消费方自行解析）与 `commitId`
- 未命中的三元组不出现在返回结果中，不抛异常

### 4.2 数据正确性

- 批量查询：每个 `(gitUrl, branchName, commitId)` 三元组取 `detection_completed_at` 最大的一条（完成时间为空的记录不参与「最新」竞争）
- 失败度量记录（`status != 0`）不返回
- 结果数 ≤ 入参数，按 `gitUrl, branchName` 排序返回

### 4.3 metrics_data_json 字段

- 6 个新字段 + `commitId` 在插件上报时正确写入 `metrics_data_json` / `commit_id` 列
- 字段缺失时（旧度量记录没有新字段）消费方自行兜底，coderepo 不强制补默认值

## 5. 验收结果

| 编号 | 验收项                                             | 结果                                          |
| ---- | -------------------------------------------------- | --------------------------------------------- |
| V-1  | 批量接口契约（入参校验 / 出参结构 / 空结果语义）   | 通过，随 PR openlibing-coderepo#159 交付      |
| V-2  | 三元组 IN 批量 SQL 正确性（分组取最新 / status 过滤） | 通过，`CodeMetricsServiceImplTest` 覆盖       |
| V-3  | 同一 commit 重跑取 `detection_completed_at` 最新   | 通过，单测覆盖                                |
| V-4  | `commit_id` 列 Liquibase 幂等变更                  | 通过                                          |
| V-5  | MySQL 8 IN 元组语法性能验证                        | 联调时验证（见遗留项）                        |

## 6. 遗留项

| 编号 | 遗留项                                                                                              | 时机               |
| ---- | --------------------------------------------------------------------------------------------------- | ------------------ |
| L-1  | 批量接口 SQL 在 MySQL 8 上的 IN 元组语法性能验证（现有 `idx_git_url_branch` 前缀索引命中率监控）    | 联调时验证         |
| L-2  | `(git_url, branch_name, commit_id)` 全量联合索引评估                                                | 上线后 RT 不达标时 |
| L-3  | docs 仓 spec 分支名 `spec-code-metrics-action-metrics-new-fields` 不符合 AGENTS.md 命名规则（应为 `spec-openlibing-coderepo-<change-name>`），后续 PR 时考虑重命名 | docs PR 创建时处理 |

## 7. 跨仓联动

- 本 spec 与 `openlibing-codecheck/task_design/full-codecheck-record-codeql-fallback` 是同一次跨仓改动的两部分
- codecheck 侧依赖 coderepo 的 HTTP 接口暴露，Feign client 调通后才能完成降级路径；codecheck 侧消费方为 `StaticAlarmSummaryOperation`
- 跨仓 PR 矩阵：coderepo 业务 PR 先行（暴露接口 + 字段）→ codecheck 业务 PR 跟进（Feign 调用 + 降级路径）→ docs PR 统一归档
