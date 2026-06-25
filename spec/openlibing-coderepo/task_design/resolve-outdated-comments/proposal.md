# resolve-outdated-comments

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-coderepo/issues/59
- 业务仓: `openlibing-coderepo`（fork: `yanzhaohong/openlibing-coderepo`，主仓: `openlibing/openlibing-coderepo`）
- 目标合入分支: `release_20260630_iter2`

## 需求背景

openlibing-coderepo 在 PR 检视场景中会下发 diff_comment 检视意见。当 PR 源分支推送新 commit 后，部分 diff 评论会因为对应代码行已变化而变为过期（outdated）状态。这些过期的检视意见应当自动置为已解决，避免人工清理成本，并保持 PR 检视列表整洁。

## 功能描述

利用 GitCode 查询 PR 评论接口对 `comment_type=diff_comment` 新增的 `is_outdated` 字段，直接判断检视意见是否过期，并在 PR UPDATE 事件触发时自动将这些过期的 diff_comment 所在的 discussion 调用 PUT 接口置为 `resolved=true`。

判定逻辑只依赖 `is_outdated` 字段，不区分评论来源（公共账号或普通用户）与评论内容。

### 接口要求

查询 PR 评论接口路径传参需包含：
- `page`、`per_page`、`comment_type=diff_comment`
- **新增 `view=all`**：确保返回所有评论（含已解决/已过期），否则默认视图可能不返回过期评论

### 触发时机

仅在 PR UPDATE 事件（source 分支推送新 commit）触发，与现有 suppression 评论下发逻辑解耦，互不阻塞。

### 过期判定逻辑

1. 调用 GET `/v5/repos/{owner}/{repo}/pulls/{prNumber}/comments` 拉取所有 diff_comment（含 `view=all`）
2. 当评论的 `is_outdated == true` 时，将其所在 discussion 标记为待 resolve（按 `discussion_id` 去重）
3. 调用 PUT `/v5/repos/{owner}/{repo}/pulls/{prNumber}/comments/{discussionId}` 设置 `resolved=true`

## 验收标准

- [ ] PR UPDATE 事件触发后，`is_outdated=true` 的 diff_comment 被自动置为已解决
- [ ] 查询评论接口传参包含 `view=all`，能正确返回过期评论
- [ ] 仅处理 `comment_type=diff_comment` 类型的评论
- [ ] PR CREATE 事件不触发该逻辑
- [ ] 单元测试覆盖关键路径（过期判定、未过期跳过、CREATE 跳过、空评论跳过、URL 构造）
- [ ] 异常情况（接口失败、token 失效）不阻塞主流程，仅打印日志
- [ ] 不引入无关重构（仅修改 handler 与对应测试）

## 影响范围

- 业务仓：`openlibing-coderepo`
- 主要修改文件：
  - `src/main/java/com/openlibing/coderepo/business/handler/MergeRequestEventHandler.java`（新增 `resolveExpiredComments`、`fetchPrDiffComments`、`resolveSingleDiscussion` 方法；在 `handle` 中 UPDATE 事件后调用）
  - `src/test/java/com/openlibing/coderepo/business/handler/MergeRequestEventHandlerTest.java`（补充相关测试）
- 不涉及数据库 schema 变化
- 不涉及外部接口契约变化（仅利用 GitCode 现有接口的新参数）
- 不引入新依赖

## 不做什么

- 不重构 `getAccessToken` 等无关方法（保持 master 现状）
- 不区分评论来源（不查公共账号、不匹配 body 前缀），仅按 `is_outdated` 判定
- 不处理 Gitee 平台（暂仅支持 GitCode，与现有 suppression 评论逻辑一致）
- 不修改 suppression 评论下发逻辑
