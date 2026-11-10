# Design：代码仓管理平台适配（github-gitcode-adaptation）

> 关联 proposal：同目录 proposal.md。改动收敛于 openlibing-coderepo 单仓，前端零改动，对外 HTTP 接口契约零变化。

## 1. 方案设计

### 1.1 根因与修复思路

| #   | 问题                         | 根因                                                                                                                                                                                              | 修复思路                                                                                                                                                                                               |
| --- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | GitHub 仓默认分支永远为空    | GitHub 默认分支是仓库级属性（`GET /repos/{owner}/{repo}` 的 `default_branch`），分支列表 API 无默认分支标记；现有落库链路 `updateDefaultBranchInfo` 从分支列表找 `isDefault=true`，对 GitHub 恒空 | 客户端内适配（方案 B）：`GithubBranchClient.listBranches()` 取回分支列表后追加 1 次仓库详情调用，回标匹配分支的 `isDefault`。`PlatformBranchClient` 接口语义不变，同步链路与机机接口等消费方无感知受益 |
| 2   | GitHub 分支增删无感知        | webhook 创建 events 缺 `create`/`delete`；且 GitHub 分支增删走独立事件（payload 与 push 结构不同），无消费 handler                                                                                | 创建/刷新双侧补齐事件订阅 + 新增 `GithubBranchChangeEventHandler` 消费，复用 `syncSingleBranch` 幂等增量同步                                                                                           |
| 3   | GitCode webhook 刷新勾选失败 | GitCode `PATCH hooks/{id}` 新增 `url` 必填校验（实测 400 `'url': param is missing`），服务端 PATCH 只发 `{"push_events": true}`                                                                   | gitcode 分支 PATCH body 补传 webhook 现有回调地址；gitee 分支保持不变                                                                                                                                  |

### 1.2 涉及服务范围

openlibing-coderepo 单仓。前端 openlibing-web 无改动（默认分支列表列/编辑回显走既有数据链路，后端修复后自然生效）。

## 2. 实现逻辑设计

### 2.1 需求 1：GitHub 默认分支回标

```
GithubBranchClient.listBranches(owner, repo, accessToken)
  ├─ 1. github.getGithubRepoBranches(...)            // 既有分页拉取，不变
  ├─ 2. 分支列表为空 → 直接返回（短路，不调仓库详情）
  ├─ 3. defaultBranch = github.getGithubRepoDefaultBranch(owner, repo, accessToken)
  │      └─ GET /repos/{owner}/{repo} → 解析 default_branch
  │         失败（网络/403/404/字段缺失/空白）→ warn 日志 + 返回 null（降级不抛异常）
  └─ 4. defaultBranch 非空 → name 精确匹配的分支 setIsDefault(true)；未匹配保持原样
```

边界：仓库详情失败降级为现状语义，不阻断分支列表返回；分支名精确匹配（GitHub 分支名全仓唯一）。

### 2.2 需求 2：GitHub 分支增删 webhook 同步

**创建侧**：`buildWebhookCreateBody` GitHub 分支 events 由 `["pull_request", "push"]` 补齐为 `["pull_request", "push", "create", "delete"]`。gitee/gitcode 分支不变（push 事件经 before/after 全零 SHA 天然携带分支增删）。

**消费侧**（新增 `GithubBranchChangeEventHandler`）：

```
/apig/webhook/github/repo（既有验签+MQ）→ 消费幂等（既有）→ dispatchEvent
  → GithubBranchChangeEventHandler.handle
       ├─ eventType ∈ {"create","delete"}（supportedEventTypes 保证）
       ├─ ref_type != "branch" → 跳过（tag 忽略）
       ├─ ref 即分支名（GitHub create/delete payload 无 refs/heads/ 前缀）
       ├─ repository.clone_url / html_url → 坐标反查已注册仓库（多行全命中）
       └─ 逐行 syncSingleBranch(repoInfo, "system", branchName, created/deleted)
            create → INSERT IGNORE 幂等插入；delete → 按 repoId+branchName 删除
```

边界：`ping` 事件无 handler 匹配安全跳过；payload 缺字段跳过并 warn；单仓失败不中断其余；平台重试由投递 ID 去重 + 消费幂等 + 业务幂等三层兜底。

**刷新侧**（存量 webhook，XXL-Job `refreshWebhookHandler` → `ensureCoderepoWebhookPushEventSubscribed`）：

- GitHub 判定扩展：`isPushEventSubscribed` 由"含 push"改为"push/create/delete 齐备"，任一缺失即 PATCH；
- `buildGithubPushEventUpdateBody`：events 保留 pull_request / issue_comment / push 并补齐 create/delete（PATCH events 为全量覆盖，必须保留原订阅）；
- gitee/gitcode 判定不变。

### 2.3 需求 3：GitCode PATCH body 修复

```
updateRepoWebhookForPushEvent
  ├─ gitee   → {"push_events": true}                            // 不变
  └─ gitcode → {"url": webhook.getUrl(), "push_events": true}   // 修复点
```

实测依据：PATCH 缺 url → 400；携带 url + push_events → 200 生效；未传 password 平台保留原签名密钥；url 取列表响应顶层 url 回传原值幂等。

## 3. 类设计

### 3.1 修改的类

| 类                                            | 修改                                                                                                                                                                                                                                                           |
| --------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `common/utils/Github`                         | 新增 `getGithubRepoDefaultBranch(owner, repo, accessToken)`：GET /repos/{owner}/{repo} 解析 `default_branch`；失败 warn + null                                                                                                                                 |
| `business/platform/branch/GithubBranchClient` | `listBranches()` 尾部回标逻辑（空列表短路 + 匹配置 isDefault）                                                                                                                                                                                                 |
| `business/service/impl/RepoServiceImpl`       | ① `buildWebhookCreateBody` GitHub events 补 create/delete；② `buildGithubPushEventUpdateBody` 补齐并更新 javadoc；③ `isPushEventSubscribed` GitHub 三事件齐备判定；④ 新增 `buildGitcodePushEventUpdateBody(RepoWebhook)`，gitcode 分支改调（gitee 沿用原方法） |

### 3.2 新增的类

| 类                                                                                           | 职责                                                                                                                                                                                                                     |
| -------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `business/handler/GithubBranchChangeEventHandler`（`@Component` 实现 `WebHookEventHandler`） | GitHub 分支创建/删除事件消费。`supportedEventTypes={"create","delete"}`；设计对齐 `PushEventHandler`（候选 URL 收集 clone_url→html_url、坐标反查去重、单仓失败隔离），注入 `RepoCoordinateResolver` 与 `RepoServiceImpl` |

分发器 `WebHookEventServiceImpl` 按 `supportedEventTypes()` 集合路由，新 handler 注册即生效，分发器零改动。

## 4. 数据模型设计

不涉及。`repo_info.default_branch_name` / `project_repo_info.default_branch_name` / `repo_branch.is_default` 三处字段沿用，无表结构、索引变化与迁移。

默认分支有效写入时机仅为全量分支同步（`syncRepoBranch` → `updateDefaultBranchInfo` 三表回写）：录入保存后自动同步、手动「同步仓库」。录入 insert 落 null（前端不入参）；编辑不触碰该字段（动态 SQL 跳过）；webhook 单分支同步只增删分支行。存量 GitHub 仓空数据由修复部署后的下一次全量同步自然回填。

## 5. 性能设计

| 场景                 | 策略                                                                                                                                                   |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 需求 1 追加出站调用  | `listBranches` 每次 +1 次 `GET /repos/{owner}/{repo}`（与分页数无关）；触发路径为全量同步与机机接口；空分支列表短路；GitHub 限流（5000 req/h）余量充足 |
| create/delete 事件量 | 分支级操作事件，频率远低于 push；PR 评论 webhook 也会收到（共用创建 body），接收端无匹配 handler 安全忽略                                              |
| 刷新任务             | GitHub 三事件判定为列表内存判断，无额外请求；仅缺失才 PATCH，已齐备 skipped                                                                            |
| 单分支增量同步       | `syncSingleBranch` 纯 DB 操作，无叠加开销                                                                                                              |

## 6. API 接口设计

对外 HTTP 接口：无新增、无变更。行为级增强（需在接口文档标注）：

| 接口                                                                     | 行为变化                                                      |
| ------------------------------------------------------------------------ | ------------------------------------------------------------- |
| `GET /openlibing-coderepo/project-repo/query-repo-branch-by-url`（机机） | GitHub 仓分支列表默认分支 `isDefault` 由恒空变为正确标记      |
| `POST /apig/webhook/github/repo`                                         | 新增接收 `create`/`delete` 事件类型（验签/投递/幂等链路复用） |

出站平台 API 变化：GitHub 仓库详情 GET（新增调用）、GitHub hooks 创建/PATCH events 补齐、GitCode hooks PATCH body 补 url。错误码无新增（GitCode PATCH 失败保留既有 failed 计数与 responseBody 失败日志）。

## 7. 安全设计

- webhook 接收链路复用既有 `WebhookAuthUtil` 验签（X-Hub-Signature-256 + secret），create/delete 与其他事件同一校验路径；
- 新 handler 防御性解析：`ref_type` 白名单（仅 branch）、`ref` 非空校验、URL 候选空白跳过；分支名入库走 MyBatis 参数化，无拼接注入面；
- 出站 URL 继续走 `WebhookUrlUtil` 路径段白名单（CWE-22 防护不变）；PATCH body 的 url 为平台列表响应原值回传，无用户可控输入；
- PATCH 不传 password，平台保留原签名密钥（实测确认）；令牌日志经 `LogSanitizer` 脱敏；
- 仓库详情失败静默降级，防 GitHub 单点故障放大为同步链路不可用。

## 8. 验证方式

1. 单测：`GithubBranchClient`（回标/降级）、`GithubBranchChangeEventHandler`（create/delete/tag 忽略/未注册仓/多仓/异常隔离）、`RepoServiceImpl` webhook 创建/刷新 body 断言（三平台）；
2. beta：部署修改后服务 → XXL-Job 手动触发 `refreshWebhookHandler`（可先传 projectId/repoId 小范围）→ 平台侧确认 GitCode「推送事件」勾选、GitHub events 含 create/delete → GitHub 平台建删分支验证列表自动增删 → 录入 GitHub 公共仓验证默认分支回填与机机接口标记 → gitee/gitcode 回归。
