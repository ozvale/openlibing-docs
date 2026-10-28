# Tasks：按仓库地址查询分支接口与 webhook/PR 重触发优化（openlibing-coderepo）

业务 Issue：openlibing/openlibing-coderepo#140；业务 PR：!196（sync-repo → release_20260923_iter2）。

## 实现步骤

- [x] 新增 `RepoService#internalQueryBranchListByUrl` 接口声明与 `RepoServiceImpl` 实现（精确匹配 → owner/repo 解析 → 令牌解析 → 平台实时分支）
- [x] 入参格式校验 `checkRepoUrlFormat`（编码态/含空白/非 http(s) 前缀 → 参数错误）
- [x] 平台分支查询失败按 HTTP 状态码转提示（404/401/403/其他）
- [x] `RepoController` 挂载 `GET /project-repo/query-repo-branch-by-url` 端点（网关鉴权路径）
- [x] `buildWebhookCreateBody` 取消评论事件订阅（gitee/gitcode `note_events=false`、github 移除 `issue_comment`）
- [x] 删除 `PrSyncCommentEventHandler` 及其测试
- [x] `PrSyncEventHandler` 源分支更新去重 key 追加 `last_commit.id`（`extractSourceCommitId`），消息 req_type 保持 `open`
- [x] 单元测试：`RepoServiceImplTest` 分支查询 7 场景 + webhook body 2 项；`PrSyncEventHandlerTest` 3 项（后按用户决定随回滚移除，行为由 CI 与手动验证兜底）
- [x] pre-commit 通用钩子对 4 个变更文件全部 Passed
- [x] Google Java Format 格式化修正（`chore(repo): apply google-java-format to PR changed files`），CI pre-commit 门禁转绿
- [x] GitCode 实测：MR 源分支 push 重新触发流水线（commit 粒度去重生效）、创建/更新事件 MQS 链路正常

## 验证记录

- 业务 PR：!196 CI `ci_state_passed=true`（pre-commit 门禁通过）
- 手动验证：`GET /project-repo/query-repo-branch-by-url?repoUrl=https://gitcode.com/openlibing-test/test0831.git` 返回分支列表；未录入地址返回 `repo not found`
