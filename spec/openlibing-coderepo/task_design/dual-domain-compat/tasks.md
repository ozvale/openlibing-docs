# Tasks：GitCode 与 AtomGit 双域名兼容（openlibing-coderepo 黄蓝协同 PrSync 链路）

业务 Issue：openlibing/openlibing-coderepo#259；业务 PR：!281（fix/dev → release_20261029_iter2，已合入）。

## 实现步骤

- [x] `PrSyncEventHandler` 注入 `RepoCoordinateResolver`
- [x] 新增 `resolveRegisteredRepoUrl(PrInfo)`：token 反查前按坐标兜底归一 repoUrl（未命中保持原样）
- [x] `PrSyncPushEventHandler` 口径对齐确认（已有 `9c3bdeff` 坐标兜底，无改动）
- [x] `PrSyncEventHandlerTest` 新增 2 个跨域名方向用例；handler 相关 45 个用例全部通过
- [x] 顺带修复 `MergeRequestEventHandlerTest` 残留 `repoInfoMapper` 引用导致的测试编译失败
- [x] 业务 PR !281 提交（fix/dev → release_20261029_iter2），评审通过（approved + lgtm）并合入

## 验证记录

- 单元测试：handler 相关 45 个用例全部通过（含 2 个跨域名新用例）
- 业务 PR !281 CI 门禁通过，2026-10-29 合入 release_20261029_iter2
