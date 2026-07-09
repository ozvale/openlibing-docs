# suppression-review-optimize

## 关联

- 业务 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/63
- 业务仓：openlibing/openlibing-coderepo
- 目标分支：release_20260630_iter2
- 跨仓协同：openlibing/openlibing-codecheck（需同步改造）

## 需求背景

本月迭代需求，针对 `openlibing-coderepo` 仓 `release_20260630_iter2` 分支。需要优化现有的三方检查工具告警抑制注释检视能力，同时将该能力复用到 GitHub 平台。

### 现状问题

**第一点：告警抑制评论机制刷屏问题**

现有方案（`MergeRequestEventHandler.java`）每检测到一条告警抑制注释/注解就产生一条行级 PR 评论（POST `/api/v5/repos/:owner/:repo/pulls/:number/comments`，带 `start_position`+`position`），存在以下问题：

- 大量抑制注释导致评论刷屏，committer 审视困难
- rebase 后代码行号变化，行级评论易过期（虽然已有 `resolveExpiredComments` 自动 resolve，但评论数依然多）
- 每条评论独立 POST，API 调用开销大

**第二点：GitHub 平台能力缺失**

目前项目管理支持录入 GitHub token（`project_common_account_info` 表已有 `github_login`/`github_token` 字段），但代码仓管理流程中没有任何位置真正使用该 token：

- `CommonService` 无 `getGithubToken` 方法，全仓 0 处读取 `githubToken` 字段
- `WebHookEventController` 无 `/hooks/github` 端点，GitHub webhook 无法进入系统
- `MergeRequestEventHandler` 内几乎所有平台分支方法都没有 github 分支
- `RepoServiceImpl` 的 webhook 设置、分支同步、token 获取等链路对 github 全部走"跳过/兜底"分支
- `openlibing-codecheck` 仓的 `scanSuppression` 也只支持 gitcode/gitee

## 功能描述

### 第一点：告警抑制评论优化

将行级评论改为文件级评论表格汇总：

1. **评论形态变更**：POST `/api/v5/repos/:owner/:repo/pulls/:number/comments` 接口的 `position_type` 改为 `binary`，不再传 `start_position`/`position` 两个位置参数。
2. **表格汇总**：所有检测到的告警抑制注释尽量在同一个文件级评论中输出为一个表格，对当前 PR 的第一个修改文件提出。表格列：文件路径、行号（带跳转链接）、代码片段、工具。
3. **评论前说明**：表格前输出"【openlibing.ci】PR中识别到代码检查告警抑制__处，详情见下表，请Committer检视合理性"。
4. **字数超限分多条**：单条评论字数上限 65535，装不下时给该文件提多条评论，直到输出结束。接口返回的 id 表示本次评论 id，需持久化。
5. **UPDATE 事件编辑更新**：检测到代码推送 UPDATE 事件时，调用编辑评论接口 PATCH `/api/v5/repos/:owner/:repo/pulls/comments/:id`，直接将表格内容更新为 PR 变更中扫描到的最新告警抑制注释列表（不再按 commit sha 获取增量变更）。

### 第二点：GitHub 复用

整体审视代码仓，将该能力复用到 GitHub：

1. **GitHub webhook 接入**：新增 `/hooks/github` 端点，解析 `X-GitHub-Event` 头和 `X-Hub-Signature-256` 签名。
2. **GitHub token 链路打通**：`CommonService` 新增 `getGithubToken` 方法，`RepoServiceImpl` 修正 github 项目级 token 误用 gitcodeToken 的问题。
3. **GitHub PR 评论接口对接**：调研 GitHub 创建/编辑 PR 评论的 API（POST `/repos/{owner}/{repo}/pulls/{pr}/comments`、PATCH `/repos/{owner}/{repo}/pulls/comments/{id}`）。
4. **GitHub webhook 能力对比**：分析 GitHub webhook 与 GitCode webhook 的一致性与差异。
5. **codecheck 仓跨仓改动**：`openlibing-codecheck` 仓的 `scanSuppression` 需支持 github 平台扫描，且需在返回结果中携带"第一个修改文件"信息供 coderepo 挂载文件级评论。

### 附加交付物：工程指导文档

输出"例外备案与committer审核一体化"工程指导 md 文档，站在用户角度 100% 覆盖告警抑制注释的例外备案流程、committer 审核标准、工具识别范围与最佳实践。

## 验收标准

### 第一点

- [ ] CREATE 事件：告警抑制评论以文件级评论（position_type=binary）形式提交，所有抑制注释汇总为一个表格
- [ ] 表格列含：文件路径、行号（带跳转链接）、代码片段、工具
- [ ] 表格前有"【openlibing.ci】PR中识别到代码检查告警抑制__处，详情见下表，请Committer检视合理性"说明
- [ ] 单条评论超 65535 字符时自动拆分为多条
- [ ] 评论 id 持久化到 MySQL（雪花算法主键，含 repo_url/pr_number/文件路径/注释指纹/工具名称/评论id/创建时间/修改时间等字段）
- [ ] UPDATE 事件：调用 PATCH 编辑评论接口，将表格内容更新为最新扫描结果（不再按 commit sha 取增量）
- [ ] gitcode/gitee 双平台均验证通过

### 第二点

- [ ] `WebHookEventController` 新增 `/hooks/github` 端点，支持 `X-Hub-Signature-256` 签名校验
- [ ] `CommonService` 新增 `getGithubToken` 方法，`RepoServiceImpl` 修正 github token 链路
- [ ] `MergeRequestEventHandler` 所有平台分支方法补齐 github 适配
- [ ] `RepoServiceImpl` webhook 设置链路支持 github（createRepoWebhook/getRepoWebhookList/deleteRepoWebhook 等）
- [ ] `openlibing-codecheck` 仓 `scanSuppression` 支持 github 平台扫描
- [ ] GitHub PR 评论创建/编辑接口对接完成
- [ ] GitHub webhook 能力对比文档输出（在 design.md 中）

### 附加交付物

- [ ] 输出"例外备案与committer审核一体化"工程指导 md 文档，站在用户角度 100% 覆盖

## 影响范围

### 跨仓改动

| 仓 | 改动范围 |
|----|---------|
| `openlibing-coderepo` | webhook 入口、MergeRequestEventHandler、RepoServiceImpl、CommonService、ApplyRepoServiceImpl、新增评论记录表 |
| `openlibing-codecheck` | SuppressionScanServiceImpl 支持 github、SuppressionScanResult 扩展字段、CodePlateHelper 增加 GitHubHelper |

### 配置项新增

- `github.api.address`
- `github.common.access_token`
- `github.webhook.list.url` / `github.webhook.create.url` / `github.webhook.delete.url`
- `github.userInfo`（可选）

### 数据模型变更

- 新增 `pr_suppression_comment` 表（评论 id 持久化）

### 工程指导文档

- 输出"例外备案与committer审核一体化"工程指导 md 文档（站在用户角度 100% 覆盖）
