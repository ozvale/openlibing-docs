# suppression-review-optimize — 实现任务

## 关联

- 业务 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/63
- proposal：同目录 `proposal.md`
- design：同目录 `design.md`

## 进度: 0/42 complete

---

## M1 — codecheck 仓：扫描响应扩展（跨仓）

- [ ] T1.1 `SuppressionScanServiceImpl.scanSuppressionComments` 在 CREATE 分支 `fetchPrFiles` 后，记录 `diffs[0].statistic.new_path` 作为 `firstChangedFile`
- [ ] T1.2 `SuppressionScanController` 响应结构外层新增 `firstChangedFile` 字段（保持 `code`/`result` 不变）
- [ ] T1.3 UPDATE 事件改为全量扫描（不再走 `scanCompareDiff` 增量），与 coderepo 新方案对齐
- [ ] T1.4 单元测试：验证 CREATE/UPDATE 响应均含 `firstChangedFile`

## M2 — coderepo 仓：评论记录表与 CREATE 文件级评论

- [ ] T2.1 新增 Liquibase changelog `changeset_pr_suppression_comment.xml`，建 `pr_suppression_comment` 表（含用户指定 9 字段 + 建议补充 6 字段）
- [ ] T2.2 新增 `PrSuppressionCommentEntity` 实体类
- [ ] T2.3 新增 `PrSuppressionCommentMapper` 接口与 XML，提供 `insert`/`batchInsert`/`updateByCommentId`/`queryByRepoAndPr`/`updateStatus`
- [ ] T2.4 新增 `PrSuppressionCommentService`/`PrSuppressionCommentServiceImpl`
- [ ] T2.5 新增 `SuppressionCommentBuilder` 工具类：`buildTableBody`/`splitByCharLimit`/`buildFileLevelRequest`
- [ ] T2.6 `MergeRequestEventHandler.callSuppressionScan` 解析响应中的 `firstChangedFile`，存入 `PrInfo`
- [ ] T2.7 `MergeRequestEventHandler.buildCommentApiUrl` 增加 gitcode/gitee 文件级评论 URL（保持现有 URL，请求体改造）
- [ ] T2.8 `MergeRequestEventHandler.buildRequestBody` 改造：gitcode/gitee 请求体用 `body`/`path`/`position_type=binary`，不再传 `start_position`/`position`
- [ ] T2.9 `MergeRequestEventHandler.postSuppressionComments` 改造：聚合同 PR 所有抑制注释为一个表格，按字数拆分多条，逐条 POST
- [ ] T2.10 POST 成功后解析响应 `id`，调用 `PrSuppressionCommentService.saveComments` 持久化（comment_seq 递增）
- [ ] T2.11 单元测试：CREATE 事件表格拼接、字数拆分、持久化

## M3 — coderepo 仓：UPDATE PATCH 编辑

- [ ] T3.1 `HttpRequestUtil` 新增 `sendPatch(url, jsonBody, headerMap)` 方法
- [ ] T3.2 `MergeRequestEventHandler` 新增 `editSuppressionComments` 方法：按 `repo_url+pr_number+file_path` 查询已有评论记录
- [ ] T3.3 `editSuppressionComments` 逐条 PATCH 编辑（按 comment_seq 顺序），更新记录 `update_time`/`last_scan_count`/`last_commit_sha`/`suppression_fingerprint`
- [ ] T3.4 评论数量变化处理：新评论更少时 DELETE 多余记录或标记 `deleted`；新评论更多时 POST 新增并 INSERT 记录
- [ ] T3.5 PATCH 404 异常恢复：降级为 POST 新建，旧记录标记 `lost`
- [ ] T3.6 `MergeRequestEventHandler.handle` 中 UPDATE 分支改为调用 `editSuppressionComments`，不再调用 `resolveExpiredComments`（过渡期保留 resolve 处理历史行级评论）
- [ ] T3.7 `callSuppressionScan` UPDATE 事件不再传 `commitShas`
- [ ] T3.8 单元测试：UPDATE 编辑、数量变化、404 降级

## M4 — codecheck 仓：GitHub 扫描支持（跨仓）

- [ ] T4.1 codecheck 配置项新增 `github.api.address=https://api.github.com`
- [ ] T4.2 `SuppressionScanServiceImpl.fetchPrFiles` 增加 github 分支，调 `GET https://api.github.com/repos/{owner}/{repo}/pulls/{pr}/files`，header 用 `Authorization: Bearer <token>`
- [ ] T4.3 新增 `parseGithubPatch` 方法，将 GitHub `patch` 文本解析成内部 `diffs[].content.text[]` 格式
- [ ] T4.4 `CodePlateHelper.getCodePlate` 增加 github 识别
- [ ] T4.5 新增 `GithubHelper`/`GithubPlate` 类，参照 `GitCodeHelper`/`GitCodePlate`
- [ ] T4.6 单元测试：GitHub PR 文件解析、扫描

## M5 — coderepo 仓：GitHub webhook 接入与 Handler 适配

- [ ] T5.1 apollo 配置新增 `github.api.address`、`github.common.access_token`
- [ ] T5.2 `WebHookEventController` 新增 `POST /webhookEvent/hooks/github` 端点，解析 `X-GitHub-Event`/`X-Hub-Signature-256`/`X-GitHub-Delivery` 头
- [ ] T5.3 `MachineInterfaceAuthUtil.webhookMachineInterfacePermissionAuth` 按 platform 路由签名头（gitcode→`X-GitCode-Signature-256`、gitee→`X-Gitee-Token`、github→`X-Hub-Signature-256`）
- [ ] T5.4 `WebHookEventHandler` 接口新增 `Set<String> supportedEventTypes()` 默认方法（旧方法 `@Deprecated` 保留兼容）
- [ ] T5.5 `WebHookEventServiceImpl.dispatchEvent` 改为检查 `eventType ∈ supportedEventTypes()`
- [ ] T5.6 `MergeRequestEventHandler.supportedEventTypes` 返回 `{"Merge Request Hook","pull_request"}`
- [ ] T5.7 新增 `GithubWebhookPayloadParser`，封装 GitHub payload 解析（extractAction/extractPrInfo/extractCommitShas/hasActualCodeChange）
- [ ] T5.8 `MergeRequestEventHandler` 所有 extract* 方法增加 github 分支或委托 `GithubWebhookPayloadParser`
- [ ] T5.9 `CommonService`/`CommonServiceImpl` 新增 `getGithubToken(Integer projectId, boolean isDefault)` 方法
- [ ] T5.10 `MergeRequestEventHandler.getProjectToken` 增加 github 分支
- [ ] T5.11 `MergeRequestEventHandler.buildCommentApiUrl` 增加 github 分支（URL 用 `githubApiUrl + "/repos/..."`）
- [ ] T5.12 `MergeRequestEventHandler.buildRequestBody` 新增 `buildGithubRequestBody`（`body`/`path`/`subject_type=file`）
- [ ] T5.13 `MergeRequestEventHandler.sendCommentRequest` header 按 platform 切换（github 用 `Authorization: Bearer` + `Accept: application/vnd.github+json`）
- [ ] T5.14 `sendPatchRequest` 同样按 platform 切换 header
- [ ] T5.15 `ApplyRepoServiceImpl.repoConfig` 删除 line 382-383 的 github 早 return
- [ ] T5.16 集成测试：GitHub webhook 签名校验、PR 创建/更新事件端到端

## M6 — coderepo 仓：RepoServiceImpl GitHub 能力补齐

- [ ] T6.1 `RepoServiceImpl` 新增 `@Value("${github.api.address}")`/`@Value("${github.common.access_token}")`/`@Value("${github.webhook.list.url}")`/`@Value("${github.webhook.create.url}")`/`@Value("${github.webhook.delete.url}")` 字段
- [ ] T6.2 `getRepoAccessToken`（line 2296-2301）修正 github 项目级 token 误用 `getGitcodeToken` 的问题
- [ ] T6.3 `getRepoAccessToken`（line 2306-2307）公共 token 回退改为 `githubCommonToken`
- [ ] T6.4 `getProjectToken`（line 3835-3846）增加 github 分支
- [ ] T6.5 `getAccessTokenForWebhook`（line 3898-3933）回退分支增加 github
- [ ] T6.6 `getRepoWebhookList` 增加 github 分支，调 GitHub hooks API
- [ ] T6.7 `createRepoWebhook`/`createCoderepoWebhook` 增加 github 分支，body 用 `config:{url,content_type,secret}`+`events` 嵌套结构
- [ ] T6.8 `deleteRepoWebhook`/`deleteRepoWebhookWithToken` 增加 github 分支
- [ ] T6.9 apollo 配置新增 `github.webhook.list.url`/`github.webhook.create.url`/`github.webhook.delete.url`
- [ ] T6.10 集成测试：GitHub 仓库录入后 webhook 自动设置成功

## M7 — 工程指导文档与集成测试

- [ ] T7.1 输出"例外备案与committer审核一体化"工程指导文档（同目录 `exception-approval-and-committer-review-guide.md`）
- [ ] T7.2 gitcode 平台端到端测试：CREATE 文件级评论 + UPDATE PATCH 编辑
- [ ] T7.3 gitee 平台端到端测试：CREATE 文件级评论 + UPDATE PATCH 编辑
- [ ] T7.4 github 平台端到端测试：CREATE 文件级评论 + UPDATE PATCH 编辑
- [ ] T7.5 字数超限拆分测试：构造 >65535 字符的扫描结果，验证拆分正确性
- [ ] T7.6 异常恢复测试：手动删除平台评论后 UPDATE，验证 404 降级 POST

---

## 注意事项

1. **跨仓协同**：M1/M4 在 `openlibing-codecheck` 仓，M2/M3/M5/M6 在 `openlibing-coderepo` 仓。两个仓需同步推进，M2 依赖 M1，M5 依赖 M4。
2. **分支隔离**：业务仓基于 `release_20260630_iter2` 分支开发；codecheck 仓需确认对应迭代分支。
3. **过渡期兼容**：UPDATE 事件的 `resolveExpiredComments` 保留处理历史行级评论，新评论走文件级 PATCH 编辑，两套机制并存。
4. **配置项**：apollo 配置变更需与运维同步，`github.common.access_token` 需加密存储。
5. **GitHub subject_type=file**：依赖 GitHub 2023 年新增能力，需确认目标 GitHub 实例（github.com 或 GitHub Enterprise）版本支持。
