# resolve-expired-pr-comments — 实现任务

## 进度: 3/3 complete

- [x] Task 1: PrInfo 新增 projectId 字段，setupPrInfoAndExtractCommits 中从 RepoInfoEntity 获取 projectId
- [x] Task 2: 新增 fetchPrDiffComments、isExpiredReplyBody、resolveExpiredComments、resolveSingleDiscussion、getCommonAccountLogin 方法
- [x] Task 3: handle() 方法中 UPDATE 事件时在 postSuppressionComments 之后调用 resolveExpiredComments
