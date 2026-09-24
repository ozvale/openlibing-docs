# Design：按仓库地址查询分支接口与 webhook/PR 重触发优化（openlibing-coderepo）

关联：proposal.md（同目录）、业务 Issue openlibing/openlibing-coderepo#140、业务 PR !196。

## 1. 方案设计

三项改动全部复用既有构建块，不引入新依赖：

1. **按仓库地址查询分支**：repo_url 精确匹配 `repo_info`（`selectByRepoUrl`，跨项目取最近录入行）→ `CommonService#getProjectAndRepoNameFromUrl` 解析 owner/repo → `CommonService#getAccessToken` 服务端内部解析生效令牌（仓库私有 → 项目级 → 全局公共，令牌不出服务端）→ `PlatformBranchClientFactory` 按平台实时拉取分支。放 `RepoController`（`/project-repo/query-repo-branch-by-url`，网关层鉴权），而非 `/internal` 命名空间——后者被 `openlibing-common` 的 `InternalAuthFilter`（URI contains `internal.auth.path-prefix`，要求 `X-Internal-Token` 头）拦截。
2. **webhook 评论订阅下线**：仅改创建侧 `buildWebhookCreateBody` 的请求体（gitee/gitcode 布尔位、github events 数组）；更新侧（`buildGiteeGitcodePushEventUpdateBody` / `buildGithubPushEventUpdateBody`）保持只补 `push` 事件并保留存量订阅，不影响已录入仓库。
3. **PR 重触发**：`PrSyncEventHandler` 的去重 key 由「PR 粒度」升级为「PR + commit 粒度」——源分支更新（内部 `SOURCE_UPDATE`）的去重 key 追加 `last_commit.id`，消息 `req_type` 仍归一为 `open`，黄区消费端零改动。

## 2. 实现逻辑设计

- `internalQueryBranchListByUrl(repoUrl)`：
  1. 空参 → `paramError`；trim 后 `checkRepoUrlFormat` 格式校验（编码事故显性化，见 §7）；
  2. `selectByRepoUrl` 精确匹配（逐字符等值，不做 `.git` 后缀归一化），空 → `repo not found`；
  3. `getClient(platform)` 不支持 → `unsupported platform`；
  4. 解析 owner/repo（substring，异常/空值 → `repoUrl 与所属平台不匹配`）；
  5. `getAccessToken` 为空 → `该仓库无可用访问令牌`；
  6. `listBranches` 抛 `IOException` → 按 message 中的 HTTP 状态码（正则 `(?:status code |status: |HTTP )(\d{3})`）转换提示：404 → `repo not found on <platform>`、401/403 → `access token invalid or unauthorized`、429 等原样透传；
  7. 空列表 → 成功返回 + message `repo has no branches`；正常 → 分支列表。
- `PrSyncEventHandler#processWebhookEvent`：`SOURCE_UPDATE` 时提取 commit id（新增 `extractSourceCommitId`：gitcode 取 `object_attributes.last_commit.id`、github 取 `pull_request.head.sha`、gitee 无可靠字段返回 null 走原 PR 粒度去重），`acquireEventLock` 追加后缀。
- `createRepoWebhook` / `createCoderepoWebhook` 共用的 `buildWebhookCreateBody`：gitee/gitcode `setIsNoteEvents(false)`；github events 改为 `["pull_request","push"]`。
- 删除 `PrSyncCommentEventHandler`（评论事件处理器，随评论订阅下线一并移除）。

## 3. 类设计

| 类                                       | 变更                                                                                                                                                           |
| ---------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RepoController`                         | +`GET /query-repo-branch-by-url` 端点（`queryBranchListByUrl`，无 userId，网关鉴权）                                                                           |
| `RepoService` / `RepoServiceImpl`        | +`internalQueryBranchListByUrl`、`checkRepoUrlFormat`、`resolveBranchApiFailureMessage`、常量 `BRANCH_API_STATUS_CODE_PATTERN` / `REPO_URL_WHITESPACE_PATTERN` |
| `RepoServiceImpl#buildWebhookCreateBody` | 评论事件取消订阅                                                                                                                                               |
| `PrSyncEventHandler`                     | 去重 key 追加 commit 后缀、+`extractSourceCommitId`                                                                                                            |
| `PrSyncCommentEventHandler`              | 删除                                                                                                                                                           |

## 4. 数据模型设计

无表结构变更。数据面只读 `repo_info`（经既有 mapper），不新增字段。

## 5. 性能设计

- 分支查询为按需实时调用，单次 1~N 次（分页）平台 API；无新增定时/常驻开销。
- PR 重触发频率上升（每次 push 均触发），由既有的 30 分钟 commit 粒度去重兜底平台重试投递；黄区流水线并发量预期与「每次 push 重跑」的产品语义一致。

## 6. API 接口设计

`GET /project-repo/query-repo-branch-by-url?repoUrl=<完整git地址>`

| 场景                                  | 返回                                                        |
| ------------------------------------- | ----------------------------------------------------------- |
| 正常                                  | success，data = `[{name, isDefault}]`                       |
| repoUrl 未录入                        | 失败：`repo not found`                                      |
| 编码态入参 / 含空白 / 非 http(s) 前缀 | 400 参数错误（明确指出原因）                                |
| 平台 404                              | 失败：`repo not found on <platform> (HTTP 404)`             |
| token 无效                            | 失败：`access token invalid or unauthorized (HTTP 401/403)` |
| 无可用令牌                            | 失败：`该仓库无可用访问令牌，请先配置项目或仓库令牌`        |
| 平台不支持                            | 失败：`unsupported platform: <platform>`                    |
| 无分支                                | 成功 + message `repo has no branches` + data 空列表         |

响应统一 `DataResult` 包装；错误码沿用 `paramError`(400)/`failureMessage`。

## 7. 安全设计

- 接口不返回令牌信息：令牌在服务端内部解密使用（`CommonService#getAccessToken` 链路）。
- 鉴权由网关层完成（无 userId 参数、无横向越权校验，依赖网关对路径的防护策略——已与使用方确认）。
- 入参格式校验同时承担注入面收敛：查询走 MyBatis `#{}` 预编译参数。
- webhook 请求体不含敏感信息；签名密钥仍走 `webhookSecretKey` 解密链路。
