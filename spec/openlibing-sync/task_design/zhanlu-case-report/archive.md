# 湛卢仿真用例执行数上报（zhanlu-case-report）— 归档

## 需求信息

| 项       | 内容                                                                                                                                                                         |
| -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 需求     | [openlibing-sync#33 新增湛卢仿真用例执行数上报](https://gitcode.com/openlibing/openlibing-sync/issues/33)                                                                    |
| 业务仓   | `openlibing-sync`                                                                                                                                                            |
| 业务 PR  | [!113 feat(testframework): report zhanlu simulation execute case count](https://gitcode.com/openlibing/openlibing-sync/merge_requests/113)（已合入，merge commit `7b68a01`） |
| 流程模式 | Standard                                                                                                                                                                     |

## 需求范围

在既有的测试框架数据上报链路之外，新增**湛卢仿真用例执行数**的采集与上报：

- 数据源为 Doris 中湛卢仿真用例执行结果表，仅统计 `simulation_task_id` 非空的记录
- 按项目（`project_name`）分组，作为指标 `zhanlu_execute_case_count` 上报到特性看板
- 纳入既有 `testFrameworkReportJobHandler` 定时任务，与原有流水线指标上报一起执行

不包含：前端页面改动、原有流水线指标（`total_execution_count` 等）口径调整、历史数据回刷。

## 实现说明

| 层次     | 文件                                                                                              | 说明                                                                                                                                                                                                        |
| -------- | ------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 模型     | `CaseExecutionRecord`                                                                             | 新增用例执行记录模型，含 `simulationTaskId`、`projectName`、`pipelineRunId` 等字段                                                                                                                          |
| 查询     | `TestFrameworkDataMapper.querySimulationCaseRecordsByDate` + `mapper/TestFrameworkDataMapper.xml` | Doris 数据源；关联用例结果表、流水线运行表、流水线名称表、项目信息表；SQL 内过滤 `simulation_task_id IS NOT NULL AND != ''`                                                                                 |
| 服务     | `TestFrameworkReportService.zhanluExecuteReportWithDateRange`                                     | 按项目分组，`caseBuildExecutionMetricsForProject` 写入 `zhanlu_execute_case_count`（即该项目下满足过滤条件的记录数），逐项目调用 `FeatureReportHandler.reportFeatureData(projectName, "测试管理", metrics)` |
| 调度     | `TestFrameworkReportScheduler.testFrameworkReportJob`                                             | 在原 `executeReportWithDateRange` 之后增加 `zhanluExecuteReportWithDateRange` 调用；两者均成功才 `handleSuccess`，否则 `handleFail`                                                                         |
| 字段补全 | `PipelineExecutionRecord.simulationTaskId` + mapper 同步                                          | 原流水线链路补齐 `simulationTaskId` 字段                                                                                                                                                                    |

指标口径说明：`zhanlu_execute_case_count = 项目下 simulation_task_id 非空的用例执行记录数`。非空过滤在 SQL 层完成，服务层按分组记录数取值，因此与需求口径一致。

## 验证

| 项       | 结果                                                                                                                                                                                                                                                                                                     |
| -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 单测     | `TestFrameworkReportServiceTest#testZhanluExecuteReport_zhanluExecuteCaseCountMetric`：mock `querySimulationCaseRecordsByDate` 返回含 `simulationTaskId` 的 `CaseExecutionRecord`，调用 `zhanluExecuteReportWithDateRange` 后断言指标值，并断言流水线查询 `queryPipelineExecutionRecordsByDate` 未被使用 |
| 静态门禁 | spotless（google-java-format 1.35.0）、checkstyle、spotbugs、pmd 通过                                                                                                                                                                                                                                    |
| CI       | PR #113 流水线 `ci-pipeline-passed`，评审 `lgtm`/`approved`                                                                                                                                                                                                                                              |

## AI 错误与人工修正

| 问题                     | 表现                                                                                                                                                        | 修正                                                                                                                                                                                    |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 单测链路与指标归属不匹配 | 初版单测 mock 流水线查询并调用 `executeReportWithDateRange`，却断言只在湛卢链路写入的 `zhanlu_execute_case_count`，断言必然为 `null` 失败，且未覆盖新增功能 | 重写单测走湛卢链路（`querySimulationCaseRecordsByDate` + `zhanluExecuteReportWithDateRange`），指标值经 `Number` 转 `long` 再比较，并补充 `verify(..., never())` 断言流水线查询未被调用 |
| 提交前未执行 spotless    | CI pre-commit 阶段 spotless 改写 3 个 Java 文件导致失败                                                                                                     | 按 pom 中配置的 google-java-format 1.35.0（GOOGLE 风格）本地格式化后提交（`419574e`）                                                                                                   |

## 提交记录（openlibing-sync）

| 提交      | 说明                                                               |
| --------- | ------------------------------------------------------------------ |
| `8e80418` | 湛卢用例执行数指标（初版）                                         |
| `4f41801` | 新增 `CaseExecutionRecord`、mapper 查询与调度调用                  |
| `3ddd740` | 指标口径调整                                                       |
| `af096f8` | `buildExecutionMetricsForProject` 增加 `zhanlu_execute_case_count` |
| `419574e` | 按 google-java-format 格式化                                       |
| `82c1507` | 重写湛卢指标单测至湛卢链路                                         |
| `9123975` | 补充"流水线查询未被使用"断言                                       |
| `7b68a01` | PR #113 合入 master                                                |

## 结论

需求已闭环：湛卢仿真用例执行数随定时任务上报，指标口径与需求一致，单测覆盖新增链路，CI 与评审通过并合入 master。后续调整 `zhanlu_execute_case_count` 口径时，需同时关注 SQL 过滤条件与服务层取值逻辑。
