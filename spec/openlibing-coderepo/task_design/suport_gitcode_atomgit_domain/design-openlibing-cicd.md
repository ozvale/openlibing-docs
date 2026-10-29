# 设计文档：openlibing-cicd 适配 gitcode.com / atomgit.com 双域名

> 关联需求：`requiremnt_desc.md`（gitcode 代码仓新增域名 atomgit.com，两者均解析为 gitcode 平台）

## 1. 背景与目标

GitCode 代码仓新增域名 `atomgit.com`，与 `gitcode.com` 同属 gitcode 平台。本仓（流水线 / webhook / 事件触发 / 自动建 Issue / 防投毒与 SCA 巡检 / 跨区协作）存在大量散落的"URL → 平台"判定，atomgit URL 目前会被判为 gitee、判为未知平台直接跳过、或被入参校验拒绝，需逐一适配。

> 佐证：`.gitcode/workflows/*.yml` 中 runner 注入的环境变量前缀即为 `ATOMGIT_*`，印证 atomgit 是 gitcode 平台的域名形态之一。

## 2. 现状分析（整仓扫描结论）

### 2.1 已支持 / 域名无关，无需修改

| 位置                                                                 | 说明                                                                                                                                                                                                       |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `common/constants/RepoType.java`（L15-24）                           | 平台常量 `GITEE/GITCODE/GITHUB`，值域不变，无需新增                                                                                                                                                        |
| `common/config/WorkflowCoverageConfig.java`（L23-24）                | `workflow.coverage.gitcode.api-base` 已配置化，全仓唯一 API 域名配置化的地方                                                                                                                               |
| `business/service/impl/SecOptionScanServiceImpl.java`（L839-891）    | `buildPipelineLink` / `extractOwnerRepo` / `normalizeRepoUrl` 等域名无关（HTTP_DOMAIN_PATTERN 直接从上报 gitUrl 提取），设计上已兼容多域名                                                                 |
| `business/service/impl/WorkflowCoverageServiceImpl.java`（L758-781） | `parseOwnerFromUrl` / `parseRepoNameFromUrl` 域名无关                                                                                                                                                      |
| `business/listener/PipelineFailEmailConsumer.java`（L327-363）       | `extractOwnerFromUrl` / `extractRepoNameFromUrl` 域名无关（但平台推导 `deriveRepoTypeFromUrl` 需改，见 4.8）                                                                                               |
| `business/service/impl/RepoFileServiceImpl.java`                     | 按入参 repoType 选 API，不做 URL 域名判断                                                                                                                                                                  |
| `business/client/PipelineStatusThirdPartyApiClient.java`             | L210/L265 为 `platform=="gitee" ? gitee : gitcode` 二选一，上游 repoType 传对即兼容                                                                                                                        |
| 各处 `url.split("/")[3]/[4]` 提取 owner/repo                         | 索引 3/4 与域名无关（`PipelineServiceImpl` L747/L4216、`XxlJobHandler` L547/L1003、`PipelineEventConsumer` L425/L909、`PipelineStartEventHandler` L180/L634/L649、`PrServiceImpl` L292/L342 等）           |
| `business/vo/secoption/`、`business/dto/secoption/`                  | 逻辑无需改，仅注释硬写 gitcode.com 格式（`SecOptionFileDetailVO` L27、`SecOptionFilingVO` L88-89、`SecOptionOverviewVO` L75、`SecOptionFilingDTO` L37、`SecOptionOverviewQueryDTO` L36），建议顺手更新文案 |

### 2.2 未适配点

见第 4 节。按影响分两类：**功能性阻断**（atomgit 仓核心链路不可用）与**功能降级**（部分能力失效或走错平台）。

## 3. 适配方案

1. **收敛统一判定（推荐落地形式）**：在 `common/constants/RepoType.java` 新增静态工具方法 `platformFromUrl(String url)`（域名白名单：`gitcode.com`、`gitcode.net`、`atomgit.com` → gitcode；`gitee.com` → gitee；`github.com` → github；未命中返回空串），替换各处散落的 `contains("gitcode.com")` 三元式与 `split("/")[2]` 域名分段推断。
   - 若希望改动面最小，也可不做收敛，逐点追加 `contains("atomgit.com")` 判断（下方逐点给出两种等价改法）。
2. **平台标识值不变**：不新增常量，atomgit 归入 gitcode。
3. **正则与校验规则同步放开**：URL 正则、Bean Validation `@Pattern` 等结构性校验需显式加入 `atomgit\.com`。

## 4. 代码修改点

### 4.1 P0：`business/dto/pipeline/PipelineRelationDTO.java`（L102-105）

现状：`@Pattern(regexp = "https://gitcode\\.com.*\\.git")` 硬编码校验 bisectRepo 地址，atomgit 仓的 bisect 入参被 Bean Validation 直接拒绝，且报错文案未提及 atomgit。

改法：正则改为 `https://(?:gitcode|atomgit)\\.com.*\\.git`，报错文案同步更新。

### 4.2 P0：`business/service/impl/GitCodeIssueClient.java`（L39-40）

现状：`GITCODE_PATTERN = Pattern.compile("https://gitcode\\.(?:com|net)/([^/]+)/([^/]+?)(\\.git)?/?$")`，atomgit URL 匹配失败 → owner/repo 为空 → 自动建 Issue 直接报 Invalid repo URL。

改法：正则加入 `atomgit\.com`：`https://(?:gitcode\.(?:com|net)|atomgit\.com)/...`。

### 4.3 P0：`business/service/impl/PipelineEventTriggerServiceImpl.java#groupReposByPlatform`（L168-189）

现状：`contains("gitcode.com") || contains("gitcode.net")` → gitcode；`contains("gitee.com")` → gitee；否则 warn "Unknown platform" 并 `continue`。**atomgit 仓被直接跳过，事件触发自动建 Issue 对 atomgit 完全失效**。

改法：gitcode 分支追加 `|| repoUrl.contains("atomgit.com")`，或改用 3.1 的 `RepoType.platformFromUrl`。

### 4.4 P0：`business/service/impl/PipelineServiceImpl.java`（4 处）

| 行号                                       | 场景                  | 现状与后果                                                                                                                                                                                         | 改法                                                          |
| ------------------------------------------ | --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------- |
| L756（`enrichPipelineRunInfo`）            | repoType 入库         | `contains("gitcode.com") ? "gitcode" : "gitee"`，atomgit 入库为 gitee，连锁影响 token 获取、PR 标签等下游                                                                                          | 追加 atomgit 判断（或 `RepoType.platformFromUrl`）            |
| L4225（`queryPrTitle`）                    | PR 标题查询前缀       | atomgit 仓错误调用 Gitee API（404/鉴权失败）                                                                                                                                                       | 同上                                                          |
| L1271-1275（`verifyRepoPipelineWebhook`）  | webhook 回调 URL 选择 | 域名分段 `split("/")[2].split("\\.")[0]` 推断 platform，atomgit 得 `"atomgit"`，`RepoType.GITCODE.equals(platform)` 失配 → **错选 `openlibing.gitee.webhook.pipeline.url`**，webhook 校验/设置全错 | 用 `RepoType.platformFromUrl`（或域名白名单映射）替换分段推断 |
| L2136-2145（`updatePipelineRepoWebhooks`） | 同上                  | 同上                                                                                                                                                                                               | 同上                                                          |

### 4.5 P0：`common/job/XxlJobHandler.java`（L557、L1012）

现状：`repoUrl.contains("gitcode.com") ? "gitcode" : "gitee"`（两处同构，L547/L1003 为 owner/repo 解析无需改）。atomgit 仓 repoType 入库错误。

改法：追加 atomgit 判断（或 `RepoType.platformFromUrl`）。

### 4.6 P1：`business/service/impl/IssueClientFactory.java#getIssueClient`（L30-41）

现状：`repoUrl.contains("gitcode")` → GitCodeIssueClient。注意匹配的是 `gitcode` 而非 `gitcode.com`——**`atomgit.com` 不包含子串 `gitcode`**，返回 empty，atomgit 仓建 Issue 无客户端可用。

改法：改为域名白名单匹配（`gitcode.com` / `gitcode.net` / `atomgit.com`），或 `RepoType.platformFromUrl`。

### 4.7 P1：`business/service/impl/RepoServiceImpl.java#getEventTriggerTemplate`（L296-306）

现状：`contains("gitcode.com")` → fetchGitCodeTemplateInfo，否则 gitee，否则报"暂不支持该代码仓平台"。atomgit 仓拉不到事件触发模板（issue 类型/标签/用户列表）。

改法：gitcode 分支追加 atomgit 判断。另 L247（`verifyRepoWebhook`）同样是域名分段推断 platform，建议一并收敛（下游为 gitee/gitcode 二选一，现状"歪打正着"，但语义失真）。

### 4.8 P1：`business/listener/PipelineFailEmailConsumer.java#deriveRepoTypeFromUrl`（L371-390）

现状：截取 host 后按 `contains("gitee")` / `contains("gitcode")` / `contains("github")` 推导，atomgit host 判不出，返回 empty，失败邮件中 owner/repo 平台推导为空。

改法：加一行 `if (host.contains("atomgit")) { return Optional.of("gitcode"); }`。

### 4.9 P1：`business/service/impl/CrossRegionServiceImpl.java#parseUrl`（L824-840）

现状：PR URL 正则 `(https://(?:gitee|gitcode)\\.com/([^/]+)/([^/]+)/(?:pulls|merge_requests)/([0-9]+)(?:/?.*)?)` 不含 atomgit，跨区协作 PR 页面 URL 解析为空。

改法：域名部分改为 `(?:gitee|gitcode)\.com|atomgit\.com`。

另：同文件 `getRepoAccessToken`（L2297、L2308）为 `url.contains("gitee.")` 之外取 gitcode token，atomgit 行为恰好正确；建议顺手显式化（非阻塞）。

### 4.10 P1：`business/service/impl/WebhookRefreshService.java`（L810-816、L946-953、L842-846）

| 行号                                                         | 场景                                                                | 现状与后果                                                                                                  | 改法                                                                                                     |
| ------------------------------------------------------------ | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| L810-816（`extractOrgKey`）、L946-953（`parseRepoIdentity`） | platform 字段优先、域名分段推断兜底，白名单仅 GITCODE/GITEE         | repo_info.platform 已存 `gitcode` 时主路径 OK（依赖 DB 数据质量）；域名兜底下 atomgit 直接 return null 被拒 | 兜底推断改用 `RepoType.platformFromUrl`                                                                  |
| L842-846（`buildRepoUrl`）                                   | orgAll 扫描时用 `gitcode.prefix`（单一 gitcode.com 前缀）拼 repoUrl | 若 atomgit 组织纳入扫描，atomgit 仓会被拼成 gitcode.com 假地址                                              | **需决策**（见第 6 节）：按组织来源区分前缀，或引入 `atomgit.prefix` 配置，或本期不支持 atomgit 组织扫描 |

## 5. 配置变更

| 配置项                                                                              | 变更          | 说明                                                                                                |
| ----------------------------------------------------------------------------------- | ------------- | --------------------------------------------------------------------------------------------------- |
| `openlibing.gitcode.webhook.pipeline.url` / `openlibing.gitee.webhook.pipeline.url` | 不变          | 回调路径固定（`/hooks/gitcode/{pipelineId}` 等），与来源仓域名无关，仅 4.4 的 platform 选择逻辑需修 |
| `gitcode.prefix`（WebhookRefreshService 用）                                        | 视第 6 节决策 | 若支持 atomgit 组织扫描则需新增 atomgit 前缀配置                                                    |
| `workflow.coverage.gitcode.api-base`                                                | 不变          | 已配置化，默认 `https://api.gitcode.com/api/v5`                                                     |

## 6. 待确认点（不确定项）

1. **atomgit 仓开放 API 是否与 `api.gitcode.com` 同构**？影响以下硬编码 API 域名（共 9 处，若共用则全部不改；若独立则需按仓库 host 动态路由，架构级改动）：
   - `GitCodeIssueClient` L37 `GITCODE_API_URL`（建 Issue）
   - `RepoServiceImpl` L51 `GITCODE_URL`（issue 类型/标签/成员）
   - `RepoFileServiceImpl` L34 `GITCODE_API`（读仓库文件）
   - `WebhookRefreshService` L70/L73（列举组织仓 / 用户信息）
   - `PipelineStatusThirdPartyApiClient` L72-79（PR 标签）
   - `PipelineServiceImpl` L5998（commit status 回写）、L6580（getGitcodePrDetail）
   - `PipelineEventConsumer` L486、L1021（PR operate_logs / merged PR 列表）
   - `XxlJobHandler` L806、L821（邀请接受/列表）
2. **`buildRepoUrl`（WebhookRefreshService L842-846）是否需要支持 atomgit 组织扫描**？涉及 `gitcode.prefix` 配置与新前缀来源。
3. **`WorkflowCoverageServiceImpl` L541 `body.setPlatform("gitcode")`** 为查 coderepo 的固定平台参数：需确认 atomgit 仓在 coderepo 登记的 platform 值也是 `gitcode`（是则不改）。
4. **DB 存量数据**：`WebhookRefreshService` 主路径依赖 `repo_info.platform` 字段已正确存 `gitcode`，atomgit 仓入库链路（coderepo 仓 4.5 `checkRepoAddress` 修复后）才能保证，需两仓配合上线。
5. （可选）`CrossRegionServiceImpl#getRepoAccessToken` "非 gitee 即 gitcode" 的隐式语义显式化。

## 7. 测试补充建议

- `PipelineRelationDTO` 校验：atomgit 合法 / 非法地址用例。
- `GitCodeIssueClientTest`：atomgit URL 提取 owner/repo 用例。
- `PipelineEventTriggerServiceImplTest`、`WebhookRefreshServiceTest`、`PipelineServiceImplTest`：atomgit 分组 / webhook 选择 / repoType 用例。
- `CrossRegionServiceImpl` parseUrl：atomgit PR URL 解析用例。
- 现有测试 fixture 大量使用 gitcode.com（如 `BranchServiceImplTest` L38 反射注入 GITCODE_PR_PREFIX），适配后行为不变，可选补充参数化用例。

## 8. 影响面与兼容性

- 数据库：无 DDL 变更；`repoType`/`platform` 字段值域不变（atomgit 归 gitcode）。
- 接口：`PipelineRelationDTO` 入参校验规则放开（对外表现为更多合法入参，向后兼容）。
- 行为变化：仅 atomgit URL 场景从"误判 gitee / 跳过 / 拒绝"变为"正确走 gitcode 链路"；既有 gitcode.com / gitee / github 行为不变。
- 上线依赖：atomgit 仓需先经 coderepo 仓改造后正常登记（platform=gitcode），本仓各链路才能闭环。
