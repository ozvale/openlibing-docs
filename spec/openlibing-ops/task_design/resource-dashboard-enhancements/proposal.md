# 资源运营看板能力增强（草稿）

## 需求背景

资源运营看板需要补齐热力图任务下钻、前端跳转所需仓库信息、运行分析排序和 PR 平均排队指标，提升资源问题定位效率。

## 功能描述

1. 资源运营看板热力图和折线图支持下钻排队任务、运行任务，前端传开始/结束时间，后端仅按该时间范围查询。
2. `common/detail` 的 `ops-pipeline-run-detail` 增加 `repoUrl`，保留已有 `platform` 等字段，供前端拼接跳转地址。
3. `common/detail` 的 `nightly-dashboard` 增加 `repoUrl`，与已有 `projectId/platform/pipelineId` 一起供前端拼接跳转地址。
4. `resource-operation/run-analysis` 的 `allocServers`、`usageServers` 均先按资源池名称、再按 IP 升序返回。
5. `common/detail` 的 `ops-project-resource-efficiency` 新增 `prAvgQueueMinutes`，与 `queueP90` 使用相同 run 级样本，单位为分钟。
6. `common/detail` 的 `ops-project-resource-efficiency` 新增可选 `engineeringScope`，传 `true` 时仅统计工程能力运营看板仓库范围内的数据。
7. `common/chart` 新增 `ops-pipeline-queue-p90`，按 PR/Nightly 返回全部流水线和各流水线的每日排队时长 P90 多折线数据。
8. `resource-operation/run-analysis` 新增顶层 `taskSummaries`，按 job 跨机器汇总卡时，原有 NPU 使用（占用）率、利用率及任务连线返回保持不变。

## 不做什么

- 不新增机器行下钻，仅调整热力图和折线图现有下钻的时间参数。
- 不由后端拼接完整跳转 URL。
- 不修改数据库表结构、ETL 或数据内容。
- 不调整现有一机多池的返回粒度。
- 不修改 `openlibing-ops-web`，仅补充前端联调文档。
- 不为任务卡时汇总新增接口或重复查询 run 切片。
- 不做与本需求无关的 SQL 重构或看板改造。

## 验收标准

- [ ] 下钻请求不再包含 `slotTime`、`slotGranularity`，任务列表和申请卡数均只使用 `startTime/endTime` 限定同一时间范围。
- [ ] 两类 detail 返回正确的 `repoUrl`，记录数不因仓库信息补充而放大。
- [ ] `run-analysis` 两类服务器列表均按池名升序、空池名最后、池内 IP 升序。
- [ ] `prAvgQueueMinutes` 按每个 PR run 最大 job 排队时长形成 run 级样本后求平均，保留两位小数，无样本为 `null`。
- [ ] `engineeringScope=true` 时项目列表/count 仅保留含运营仓的项目，PR 指标仅统计运营仓 run，GitHub run 额外受展示配置约束；缺省或 `false` 时行为不变。
- [ ] 排队 P90 趋势与平均卡时趋势使用相同 PR/Nightly 范围、日归属和日期刻度；每个 run 取最大 job 排队时长，全部流水线直接基于全量 run 样本计算 P90，单位分钟并保留两位小数。
- [ ] `taskSummaries` 每个 job 仅返回一条，跨机器累加原始卡时秒后统一换算和舍入，并返回涉及机器列表；旧有热力图和 `jobs[]` 行为不变。
- [ ] 相关单元测试和 Maven 编译通过，前端联调文档包含新增接口字段、示例和自测要求。

## 影响范围

- 业务仓：`openlibing-ops`
- 接口：`/common/detail`、`/common/chart`、`/resource-operation/run-analysis`
- 文档仓：仅本需求目录
- Issue：暂不关联，创建业务 PR 前再确认
