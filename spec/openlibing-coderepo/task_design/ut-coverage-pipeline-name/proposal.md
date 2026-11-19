# 提案：UT 覆盖率详情页补齐来源流水线信息

## 背景与问题

[Issue #249](https://gitcode.com/openlibing/openlibing-coderepo/issues/249)：「代码仓管理--分支管理」UT 覆盖率详情页（文件级明细下钻）缺少**检查时间、流水线名称、流水线编号**，用户无法判断覆盖率数据是哪次检测、由哪条流水线产生。与本仓 #219（代码度量下钻页同类问题，已修）口径应保持一致。

## 现状核实结论（截至 2026-11-12，基于 release_20261116_iter1 分支）

| 缺失项 | 后端现状 | 结论 |
| --- | --- | --- |
| 检查时间 | `getFileDetail` 已返回 `checkTime` 字段（取 `code_ut_record.detection_completed_at`），**但该列自 2026-09-23 后为 NULL**——插件标准 JSON 从未上报 `detectionCompletedAt` 元数据；此前少数早期记录「有值」是后端 `parseDateTime` 的 `new Date()` 空值兜底产生的假时间（≈create_time），该兜底已在 `379bed9e`（Refs #189）中刻意移除（避免假时间失真展示与打乱排序），移除后暴露数据源缺失 | 数据源缺失（插件侧），随本次插件补齐真实打点；前端渲染已随 MR 879 实现，label 需统一为「扫描时间」 |
| 流水线编号 | 已返回 `runNumber` 字段 + `pipelineLink`，**但 `run_number` 列值为 NULL**（生产库截图实证）——插件标准 JSON 从未上报 `runNumber` 元数据 | 同上，插件侧补齐（取 `ATOMGIT_RUN_NUMBER`）；前端渲染已实现 |
| 流水线名称 | **数据缺失**：报告 JSON 无该元数据、`code_ut_record` 无列、VO 无字段、上报 DTO 不携带 | 本设计主体：补齐「插件 JSON 元数据 → 解析入库 → 明细接口返回 → 前端展示」链路 |

## 方案概述

对齐同仓 code metrics 既有先例（`code_metrics_record.pipeline_name`，changeSet `20261016_add_pipeline_name_to_code_metrics_record`，由插件端上报）：

1. **插件（upload-ut-action）**：覆盖率标准 JSON 元数据区一次性补齐三个缺失字段——`runNumber`（`ATOMGIT_RUN_NUMBER`）、`pipelineName`（`ATOMGIT_WORKFLOW`）、`detectionCompletedAt`（组装完成时刻）——后端解析/入库链路已存在（runNumber/detectionCompletedAt）或仅加一个 case（pipelineName），dist 重建发版；
2. **后端（openlibing-coderepo）**：`code_ut_record` 加列 `pipeline_name` → 流式解析 `case "pipelineName"` 抽取 → 入库 → 明细接口 VO 返回 `pipelineName`；
3. **前端（openlibing-web）**：详情页信息条整体对齐 code metrics 下钻页口径——「扫描时间」（checkTime，label 由「检查时间」统一为「扫描时间」，移除同源重复的「检测时间」）+「流水线：{pipelineName} #{runNumber}」组合跳转链接，名称缺失退化为仅编号；

不采用「上报请求参数传 pipelineName」：`runNumber`/`commitId` 均走 JSON 元数据链路（请求参数与 JSON 内容保持单一数据来源），metrics 先例同为 JSON 元数据（`CodeMetricsPayload.pipelineName`）。

## 变更范围

| 仓 | 改动 |
| --- | --- |
| upload-ut-action | CoverageNormalizer 元数据 + index.js 上下文注入 + 测试 + dist 重建 + 版本升级 |
| openlibing-coderepo | Liquibase 加列 + 解析/实体/VO/Service + 单测 |
| openlibing-web | UtCoverageDetailDialog 信息条对齐 metrics 口径：扫描时间 label 统一（移除同源重复的检测时间）+ 流水线名称+编号组合展示 |

## 验收标准

1. 新版插件上报后：详情页展示扫描时间、流水线（名称 + 编号组合链接），与 code metrics 下钻页信息口径一致；
2. 旧版插件/历史记录（JSON 无新增字段）：明细接口 `pipelineName`/`runNumber`/`checkTime` 返回空，前端流水线段与扫描时间兜底 `--`，不影响既有功能；存量数据不做刷数回填；
3. 上报契约零破坏：请求 DTO 不变，幂等清理与定位逻辑不变；
4. 单测覆盖「有 pipelineName」「无 pipelineName（历史/旧插件）」两条解析与返回路径；
5. 上报解析失败落失败记录的路径不受影响（失败记录不带 pipelineName，与 runNumber/commitId 同口径）。
