# 批量修复 11 个看板缺陷 — 实现任务

## 进度: 9/11 complete

- [x] 144: PipelineStatusEnum SKIPPED/IGNORED result 置 false
- [x] 145: RepoPrPipelineDetailResp access 系列改 2 位小数
- [x] 161: 已回退（用户确认 issue 提错，非代码问题）
- [x] 166: OpsMainStatMapper.unified_npu_stat 区分流水线归属项目（PR 按 repo、Nightly 按 relation，与 ops-resource-detail 同口径）
- [x] 164: 已回退（用户确认本批不做）
- [x] 157: 使用率分析时间跨度回显 — 前端改动点已写入 design.md（本次不改前端代码，待前端实现）
- [ ] 168: PR执行时长P90 口径对齐（用户自行确认代码后处理）
- [x] 149: nightly-dashboard-summary projectId 下推优化
- [ ] 146/152/158: gitcode PR 关联需 ETL 侧补桥表（DS 无 gitcode 分支，已确认根因）
- [ ] 编译 + 相关单测 + commit（等用户确认后提交）
