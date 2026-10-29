# 实现步骤

- [x] metric 仓基于 origin/main 新建 `fix-metric-dict-codes-limit` 分支
- [x] `MetricDictQueryReq.codes` 加 `@Size(max = 200)`，`getEnabledDict` 加 `@Valid`
- [x] metric `GlobalExceptionHandler` 补充 `MethodArgumentNotValidException` 处理
- [x] ops 仓基于 origin/main 新建 `fix-pagesize-upper-limit` 分支
- [x] 7 个无上限请求类 pageSize 加 `@Max`（`DetailReq`/`OpsOverviewMainReq`/`OpsRepoDetailReq`/`OpsResourceRunReq`/`ExternalRepoIssueDetailReq`/`IssueLegacyStatisticsDto`/`ReportDataQueryReq`）
- [x] 两仓 `compile` + `spotless:apply` 通过
- [ ] 用户自测确认
- [ ] 用户确认后分别提交 commit
- [ ] 创建业务 PR（ops 关联 #240，metric 跨仓关联 #248/#209）并打 `ai-assisted` 标签
- [ ] 前端配套修复（另行处理）：工程能力看板 pageSize 999 改循环分页
