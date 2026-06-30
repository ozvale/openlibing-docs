# Nightly 流水线看板下钻页面增加 E2E 执行时长（不含重试）列 — 最终归档

## 需求溯源

- 需求 Issue：[openlibing/openlibing-ops#50](https://gitcode.com/openlibing/openlibing-ops/issues/50) — Nightly流水线增加E2E执行时长（去除重试）展示
- 涉及仓库：`openlibing-ops`（后端）、`openlibing-ops-web`（前端）
- 目标分支：`release_20260630_iter2`

## 交付清单

### 业务 PR

| 仓库 | PR | 链接 | 提交数 |
|------|-----|------|--------|
| openlibing-ops | #98 | https://gitcode.com/openlibing/openlibing-ops/pulls/98 | 4 |
| openlibing-ops-web | #66 | https://gitcode.com/openlibing/openlibing-ops-web/pulls/66 | 3 |

### cherry-pick 提交清单

#### openlibing-ops PR #98（基于 release_20260630_iter2）

| 原 SHA | 说明 |
|--------|------|
| `b19d1e4` | feat: 版本级流水线看板新增E2E执行平均时长(去除重试)指标 |
| `fb103fb` | docs(issue): 新增ETL设计文档 |
| `f42bf46` | feat: repo pipeline 看板重写（含 5 个 E2E efficiency unit test） |
| `ae36875` | feat(pipeline): NightlyPipelineDetailResp 新增 efficiencyDurationMinutes 字段 |

#### openlibing-ops-web PR #66（基于 release_20260630_iter2）

| 原 SHA | 说明 |
|--------|------|
| `915d7b5` | feat: 版本级看板 E2E 执行平均时长 chart 接入 |
| `5173710` | feat: 版本级看板 E2E 列定义 + tips 文案 |
| `cc8b30c` | feat(dashboard): nightly pipeline 看板 E2E 列与 unit test 扩展 |

### 未带入的提交

`feature_50` 分支从 `develop_new` / `dev_ljp_0616` / `f30066145` / `feat/pr-dashboard-metrics` / `beta` 等同步过来的非 E2E 相关提交均未带入本次 PR，包括：
- ops-overview 模块（dev_ljp_0616 同步）
- refresh-time 修复、CI 配置调整、Table 重命名等其他改动
- engineering-capability 模块前端重构
- `fb9eee8` nightly 下钻明细页 E2E 列改动（Task 4 延期）

## 完成度

| 任务 | 状态 | 落地位置 |
|------|------|---------|
| Task 1: Mapper XML resultMap + SELECT | ✅ 完成 | ops PR #98（ae36875） |
| Task 2: Dwr Model 新增字段 | ✅ 完成 | ops PR #98（ae36875） |
| Task 3: NightlyPipelineDetailResp 新增字段 | ✅ 完成 | ops PR #98（ae36875） |
| Task 4: 下钻明细页新增列 | ⏸ 延期 | 由后续独立 issue 跟进 |

**整体完成度：3/4**

## 字段命名约定

后端 VO → 前端列定义统一使用 camelCase：

| 字段 | 层级 | 类型 |
|------|------|------|
| `efficiencyDurationMinutes` | NightlyPipelineDetailResp | BigDecimal |
| `efficiencyDurationAvgMinutes` | NightlyPipelineDashboardResp | BigDecimal |
| `avgEfficiencyDuration` | VersionPipelineChartResp.PipelineInfoDayChart | BigDecimal |

## 验证状态

- [x] cherry-pick 应用后 working tree clean
- [x] 后端字段 `efficiencyDurationMinutes` 在目标文件中存在
- [x] 前端列定义在 `version-pipeline-columns.ts` 中存在
- [ ] 待执行：Maven build + unit test
- [ ] 待执行：前后端联调验证 drill-down detail 链路
- [ ] 待执行：Task 4 的下钻明细页前端实现

## 后续待办

1. 业务 PR 合入 `release_20260630_iter2` 后，发布该 release
2. Task 4（前端下钻明细页 E2E 列）由独立 PR/Issue 跟进
3. ETL 任务验证：`efficiency_duration_ms` 字段是否被正确填充（旧记录可能为 NULL）

## 文档版本

- v1.0 — 2026-06-30 — 初次归档