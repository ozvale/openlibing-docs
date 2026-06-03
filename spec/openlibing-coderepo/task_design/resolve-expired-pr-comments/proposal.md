# resolve-expired-pr-comments

## 需求背景

在 PR UPDATE 事件处理中，当有新代码推送后，之前由 coderepo 服务发布的代码检视意见（suppression 评论）可能已过期。GitCode 平台会自动在过期评论下添加包含 `commits/detail/` 和 `/diffs?` 链接的 reply。这些过期意见应自动置为已解决，避免干扰开发者。

## 功能描述

- UPDATE 事件时，在发新评论之后，检查已有检视意见是否过期
- 分页获取 PR 下所有 diff_comment（GET `/api/v5/repos/:owner/:repo/pulls/:number/comments`，参数 page、per_page=100、comment_type=diff_comment）
- 筛选由公共账号发布的 suppression 评论（body 以 `【openlibing.ci】` 开头 + user.login 匹配 project_common_account_info 表中配置的公共账号）
- 检查同一 discussion 下是否存在过期 reply（body 同时包含 `commits/detail/` 和 `/diffs?`）
- 调用 PUT 接口将过期 discussion 置为已解决（PUT `/api/v5/repos/:owner/:repo/pulls/:number/comments/:discussion_id`，body `{"resolved": true}`）

## 验收标准

- [ ] UPDATE 事件触发时，自动检查并解决已过期的 PR 检视意见
- [ ] 仅筛选由公共账号发布的 suppression 评论，不影响其他评论
- [ ] 仅当 discussion 下存在含 `commits/detail/` + `/diffs?` 的 reply 时才视为过期
- [ ] 分页遍历保证获取所有 diff_comment
- [ ] 解决过期评论步骤在发新评论之后执行，确保 GitCode 已完成自动回复
- [ ] 不影响 CREATE 事件和现有 suppression 扫描逻辑

## 影响范围

- `MergeRequestEventHandler` 类（单文件）
