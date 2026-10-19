# 批量修复 mth@121800 提交的 11 个看板缺陷

## 需求背景

mth@121800（qq_42589833）提交并指派给 nane 的 11 个 open 状态缺陷（#144 #145 #146 #149 #152 #157 #158 #161 #164 #166 #168），涉及 PR 流水线看板、Nightly 看板、工程能力看板、资源环境看板、NPU 使用率分析等多个模块。本次统一修复。

## 功能描述（按 issue）

| #   | 问题                                           | 修复方向                                                                                                                                      |
| --- | ---------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 144 | 构建任务未执行，看板显示执行成功               | PipelineStatusEnum 中 SKIPPED/IGNORED 的 result 置 false，未执行任务不再显示成功                                                              |
| 145 | 门禁E2E执行时长小数位与(不含重试)不一致        | access 系列时长改 2 位小数（timeNumberConvertTwo）                                                                                            |
| 146 | 未拿到 gitcode 的排队时长                      | 排查 gitcode PR run 关联与排队字段取值（数据链路）                                                                                            |
| 149 | Nightly KPI/分位汇总接口 P95 间歇超 1s         | nightly-dashboard-summary 查询优化（CTE 下推/缓存）                                                                                           |
| 152 | gitcode 漏采，看板与 gitcode 数量不一致        | 排查 gitcode run/PR 关联桥表数据                                                                                                              |
| 157 | nightly 使用率分析未展示时间跨度               | 响应回显时间跨度                                                                                                                              |
| 158 | PR 看板未采集 gitcode 构建/测试测试数据        | 排查 gitcode 用例数据链路                                                                                                                     |
| 161 | main 接口 productName 全为 null                | ~~join 维表补齐~~ **已回退：issue 提错，非代码问题**                                                                                          |
| 164 | codearts 流水线跳转错位                        | ~~统一/修正跳转 URL 参数来源~~ **已回退：本批不做**                                                                                           |
| 166 | NPU 平均消耗(卡时)错误，Nightly/整体资源值异常 | **已修复**：OpsMainStatMapper.unified_npu_stat 区分流水线归属项目（PR 按 repo 项目、Nightly 按 relation 项目，与 ops-resource-detail 同口径） |
| 168 | PR执行时长[P90]与PR流水线数据不一致            | 对齐 P90 样本口径                                                                                                                             |

## 验收标准

- [ ] 各 issue 对应看板数值/展示符合 issue 描述预期
- [ ] 编译通过，相关单测通过
- [ ] 用户自测确认

## 影响范围

- openlibing-ops：PipelineStatusEnum、RepoPrPipelineDetailResp、PrInfoResp、DmProjectQualityOverviewDayMapper、OpsMainStatMapper、OpsResourceDetailMapper、NightlyPipelineDashboardMapper 等
- 部分 issue（146/152/158/149）依赖 ETL 数据链路，后端可修部分先行修复，数据侧配合项记录在案

## 关联 Issue

https://gitcode.com/openlibing/openlibing-ops/issues/144
https://gitcode.com/openlibing/openlibing-ops/issues/145
https://gitcode.com/openlibing/openlibing-ops/issues/146
https://gitcode.com/openlibing/openlibing-ops/issues/149
https://gitcode.com/openlibing/openlibing-ops/issues/152
https://gitcode.com/openlibing/openlibing-ops/issues/157
https://gitcode.com/openlibing/openlibing-ops/issues/158
https://gitcode.com/openlibing/openlibing-ops/issues/161
https://gitcode.com/openlibing/openlibing-ops/issues/164
https://gitcode.com/openlibing/openlibing-ops/issues/166
https://gitcode.com/openlibing/openlibing-ops/issues/168
