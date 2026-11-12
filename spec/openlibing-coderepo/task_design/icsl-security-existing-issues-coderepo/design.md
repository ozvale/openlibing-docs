# Design：【openLiBing】ICSL安全送检存量issue整改-coderepo

> 需求 Issue：[openlibing/openlibing-codecheck#401](https://gitcode.com/openlibing/openlibing-codecheck/issues/401)（FE 需求锚点；5 个存量问题见 §1.3）
>
> 目标分支：`release_20261116_iter1`
>
> 代码基线：`master`（`ac7ea8c5`）
>
> 文档状态：设计归档（Phase 1.5）；截至 2026-11-11，5 个修复 PR 均为 open，合入后关闭对应子 issue。

## 1. 方案设计

### 1.1 背景与目标

本需求承接 ICSL 安全送检存量问题清单，对 openlibing-coderepo 仓剩余的 5 个安全问题进行集中整改。5 个问题分布在三类链路上：

- **不可信输入进入出站 URL**：三方 API 路径段注入（#282）、Webhook 入口坐标未校验（#288）；
- **不可信输入进入查询语句/查询结构**：SQL LIKE 通配符（#286）、GitHub GraphQL 字符串拼接（#287）；
- **生产环境暴露面**：Swagger 调试端点公网可达（#225）。

目标是在不改变对外 HTTP 接口契约的前提下，完成 5 个问题的修复、单测覆盖与流水线验证，并为后续同类问题提供可复用的统一校验入口。

### 1.2 总体思路：按链路分层收口

按"不可信输入到达 sink 的链路位置"分层治理，同一层复用同一套校验/构造逻辑，避免逐点打补丁造成口径漂移：

| 层                   | 治理目标                                               | 覆盖问题   |
| -------------------- | ------------------------------------------------------ | ---------- |
| L1 出站 URL 公共出口 | 路径段统一编码 + 拒绝 `.`/`..`，非法取值 fail-closed   | #282       |
| L2 入口坐标校验      | webhook / SIG / token 探测等入口在出站前做路径段白名单 | #282、#288 |
| L3 查询语义收敛      | LIKE 通配符按字面量匹配；GraphQL 输入与语句结构隔离    | #286、#287 |
| L4 暴露面收敛        | 生产环境关闭 Swagger 调试端点，保留非生产环境能力      | #225       |

### 1.3 问题与整改映射

| 序号 | 问题                                | 子 Issue                                                              | 修复 PR                                                                       | 风险等级 | 整改方案摘要                                                                |
| ---- | ----------------------------------- | --------------------------------------------------------------------- | ----------------------------------------------------------------------------- | -------- | --------------------------------------------------------------------------- |
| 1    | 三方 API 出站路径段注入（`.`/`..`） | [#282](https://gitcode.com/openlibing/openlibing-coderepo/issues/282) | [!306](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/306) | 中       | 公共 `ApiUrlUtil` 拒绝点段；MergeRequest / SIG / token 探测入口补坐标白名单 |
| 2    | 仓库/分支列表 LIKE 通配符未转义     | [#286](https://gitcode.com/openlibing/openlibing-coderepo/issues/286) | [!309](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/309) | 低       | 新增 `SqlLikeUtil`，查询实体组装前统一转义 `\`/`%`/`_`                      |
| 3    | GitHub GraphQL 查询字符串拼接       | [#287](https://gitcode.com/openlibing/openlibing-coderepo/issues/287) | [!310](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/310) | 低       | reviewThreads 查询与 resolveReviewThread mutation 改为 GraphQL variables    |
| 4    | Webhook 入口仓库坐标未校验          | [#288](https://gitcode.com/openlibing/openlibing-coderepo/issues/288) | [!311](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/311) | 低       | 新增 `RepoUrlUtil.isLegalCoordinate`；PrSync / Notify 入口校验后再出站      |
| 5    | 生产环境 Swagger 调试端点暴露       | [#225](https://gitcode.com/openlibing/openlibing-coderepo/issues/225) | [!303](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/303) | 中       | `application-prod.yaml` 关闭 `springdoc.api-docs` 与 `springdoc.swagger-ui` |

### 1.4 关键设计决策

| 决策                            | 内容                                                                                                          | 依据                                                                       |
| ------------------------------- | ------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------- |
| 公共出口 + 入口双重防线         | `ApiUrlUtil` 在公共出口拒绝 `.`/`..`；各入口再用 `SigInfoClient`/`RepoUrlUtil` 做坐标白名单，非法直接丢弃事件 | 单点入口校验容易漏新增链路；公共出口可兜底全部 `ApiUrlUtil` 调用方         |
| 非法输入 fail-closed            | 路径段/坐标非法时抛异常或丢弃事件，不发起平台请求、不发送 MQ                                                  | 携令牌请求被规范化到非预期端点属于不可接受副作用；宁可丢事件也不能错发请求 |
| owner 兼容嵌套分组              | 校验 owner 时按 `/` 拆分后逐段白名单，允许 `group/sub` 形式                                                   | GitCode/Gitee 支持嵌套分组；简单拒绝 `/` 会误伤合法仓库                    |
| LIKE 只收敛语义，不引入转义 SQL | SQL 继续使用 `#{}` 参数占位，仅对 `\`/`%`/`_` 做字面量转义                                                    | 原问题不是 SQL 注入；目标是消除通配符放大匹配范围与潜在大范围扫描          |
| GraphQL 用 variables 而非转义   | 查询/mutation 语句改为固定文本，外部取值全部走 `variables`                                                    | 转义依赖字符集完备性；variables 从结构上消除注入面                         |
| Swagger 仅关闭生产              | 只改 `application-prod.yaml`，保留 beta/gama/本地 Swagger 能力与依赖                                          | 最小化变更面；非生产环境仍有接口文档诉求；生产暴露面通过配置关闭即可收敛   |
| 不改对外 HTTP 契约              | 不新增接口、不改响应结构；仅对非法输入返回既有失败语义                                                        | 前端与外部调用方无需适配，降低发布风险                                     |

### 1.5 范围与非范围

**范围内**

- #282 三方 API 出站路径段注入（含 `ApiUrlUtil` 公共出口与各入口校验）；
- #286 仓库/分支列表 LIKE 通配符转义；
- #287 GitHub GraphQL 查询/mutation variables 化；
- #288 PrSync / Notify webhook 入口坐标校验；
- #225 生产环境 Swagger 调试端点关闭。

**范围外（本次不处理）**

- 排查表中 #4 OBS object key 未拒绝 `..`：OBS key 为扁平字符串，无目录遍历语义，按可接受风险登记；
- 排查表中 #5 邮件标题 CRLF：标题仅由已校验坐标与日期构成，无可达外部输入，按可接受风险登记；
- 其他仓库（codecheck/cicd/sbom 等）的存量问题由各自需求跟踪；
- 网关 `/manage` 路由策略调整：属于环境侧配置，作为 #225 的部署验收项，不在代码仓内修改。

## 2. 实现逻辑设计

### 2.1 出站路径段注入（#282 / !306）

**公共出口**

- `ApiUrlUtil.apiUrlBuilder` / `appendPathSegments` 增加路径段校验：取值为 `.` 或 `..` 时抛 `IllegalArgumentException`，不再交给 OkHttp 做相对路径规范化；
- 全部三方平台出站 URL 统一经 `ApiUrlUtil` 分段编码，HTTP 方法与端点后缀保持代码硬编码。

**入口校验**

| 入口                                         | 校验点                                                              | 处理方式                                                                            |
| -------------------------------------------- | ------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `MergeRequestEventHandler`                   | webhook 报文解析出 owner/repo 后、`preCommitCheck` 与任何出站调用前 | `SigInfoClient.isLegalOwner` + `isLegalSegment`；非法丢弃事件并记 `[SECURITY]` 告警 |
| `RepoServiceImpl`（sig-info.yaml）           | YAML 中 `repos` 条目的 owner/repo 入库前                            | 路径段白名单校验；非法条目跳过                                                      |
| `RepoServiceImpl`（SIG MQ 入库）             | 调用平台仓库详情前                                                  | 再次校验坐标；非法直接跳过                                                          |
| `RepoServiceImpl.checkTokenPermission`       | 新增仓库场景（repoId 为空）使用请求体 `repoUrl` 前                  | 复用 `checkRepoAddress`：协议/host/端口归一化精确匹配 + `isLegalRepoUrlPath`        |
| `SigDefaultParamBuilder.fetchRepoDetail`     | 拉取平台仓库详情前                                                  | owner/repo 非法返回 empty，不发起请求                                               |
| `TokenPermissionEvaluator.resolveMemberRole` | 成员角色查询前                                                      | owner/repo 非法按探测失败处理，不发起请求                                           |

**实现要点**

- `SigInfoClient.isLegalSegment` 统一拒绝 `.` 与 `..`，并保持字符白名单 `^[A-Za-z0-9._-]+$`；
- 新增 `SigInfoClient.isLegalOwner`，兼容 `group/sub` 嵌套分组；
- `WebhookUrlUtil` 复用同一 `isLegalSegment` 口径，删除重复的单点判断；
- PR files 分页参数由手工 `apiUrl + "?per_page=100"` 改为 `HttpUrl.Builder.setQueryParameter`。

**失败语义**：路径段非法时抛异常或丢弃事件，不发起任何平台请求；合法坐标行为与修复前一致。

### 2.2 LIKE 通配符转义（#286 / !309）

**实现**

- 新增 `SqlLikeUtil.escape`：按 `\` → `%` → `_` 顺序转义，返回可直接放入 `#{}` 参数的值；
- `RepoServiceImpl.buildRepoQueryEntity` 对 `repoNameLike` / `repoUrlLike` / `repoOwnerLike` 先转义；
- 两个 `buildProjectBranchQueryEntity` 重载（列表查询与 filter-meta）对 `repoUrlLike` / `branchNameLike` 先转义；
- 分维度预览的 `copyRepoQueryEntity` / `copyProjectBranchQueryEntity` 只拷贝已转义值，不重复转义；
- `RepoCoordinateResolverImpl` 复用 `SqlLikeUtil`，删除原私有 `escapeLike`，保证转义口径单一来源。

**边界说明**

- SQL 保持 `like concat('%', #{value}, '%')` 参数化，不存在 SQL 注入；
- 输入 `%`/`_` 时由"通配符"变为"字面量"，包含通配符的查询结果会收窄，属于预期语义修正；
- 不含通配符的普通关键字查询结果与修复前一致。

### 2.3 GraphQL variables 化（#287 / !310）

**实现**

- reviewThreads 查询改为固定语句：

  ```graphql
  query($owner: String!, $repo: String!, $prNumber: Int!, $pageSize: Int!, $after: String) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $prNumber) {
        reviewThreads(first: $pageSize, after: $after) { ... }
      }
    }
  }
  ```

- resolveReviewThread mutation 改为固定语句 + `$threadId`；
- 请求体统一为 `{ "query": <固定语句>, "variables": { ... } }`；
- 分页首次 `after` 为 null，后续使用上一页 `endCursor`；最大页数逻辑不变。

**失败语义**：GraphQL 错误处理、HTTP 状态判断、日志与重试逻辑保持不变；语句结构错误不再可能由外部输入引入。

### 2.4 Webhook 入口坐标校验（#288 / !311）

**统一校验入口**

- `RepoUrlUtil.isLegalCoordinate(owner, repo)`：owner 走 `isLegalOwner`（允许 `group/sub`），repo 走 `isLegalSegment`；
- `RepoUrlUtil.isLegalSegment`：复用 `SigInfoClient.isLegalSegment`，并显式拒绝单点段 `.`；
- 拒绝空值、空白、`..`、`.`、`?`、`#`、空格及白名单外字符。

**处理链路**

| Handler                    | 校验时机                                    | 非法处理                                                               |
| -------------------------- | ------------------------------------------- | ---------------------------------------------------------------------- |
| `PrSyncEventHandler`       | 解析出 owner/repo 后、去重锁与 token 反查前 | 记 `[SECURITY]` 告警，直接 return，不占用去重键、不查 token、不发送 MQ |
| `NotifyConfigEventHandler` | 解析出 owner/repo 后、读取仓库 YAML 前      | 记 `[SECURITY]` 告警，直接 return，不发起平台请求                      |

**范围说明**

- `PushEventHandler` 的 payload repoUrl 仅用于反查已录入仓库，后续使用数据库中的 `repo_url`，不直接构造出站 URL，本次不修改；
- `MergeRequestEventHandler` 已由 !306 统一校验，本次不重复修改；
- `RepoUrlUtil.isLegalOwner` 与 !306 的 `SigInfoClient.isLegalOwner` 逻辑一致；两条分支合并后可后续收敛到 `SigInfoClient`，本次为降低分支冲突风险保留独立入口。

### 2.5 生产环境 Swagger 收敛（#225 / !303）

- `application-prod.yaml` 增加：

  ```yaml
  springdoc:
    api-docs:
      enabled: false
    swagger-ui:
      enabled: false
  ```

- 保留既有 `springdoc.swagger-ui.url` / `oauth2RedirectUrl` 配置文本（仅作为非生产环境参考），生产环境因开关关闭不再注册 `/v3/api-docs`、`/swagger-ui/**`；
- `pom.xml` 依赖、Controller `@Operation` 注解、beta/gama/本地配置全部保留；
- 部署验收：生产环境访问 `/v3/api-docs`、`/swagger-ui/index.html` 返回 404；beta 环境 Swagger UI 仍可访问；网关 `/manage` 路由策略由环境侧复核。

## 3. 类设计

| 模块     | 类                           | 动作                                                         |
| -------- | ---------------------------- | ------------------------------------------------------------ |
| URL 构造 | `ApiUrlUtil`                 | `apiUrlBuilder` / `appendPathSegments` 拒绝 `.`/`..`         |
|          | `WebhookUrlUtil`             | 复用统一 `isLegalSegment` 口径                               |
|          | `SigDefaultParamBuilder`     | 拉取仓库详情前校验 owner/repo                                |
|          | `TokenPermissionEvaluator`   | 角色查询前校验 owner/repo                                    |
| 坐标校验 | `SigInfoClient`              | `isLegalSegment` 增加单点拒绝；新增 `isLegalOwner`           |
|          | `RepoUrlUtil`                | 新增 `isLegalCoordinate` / `isLegalOwner` / `isLegalSegment` |
| 查询     | `RepoServiceImpl`            | LIKE 字段转义；SIG 坐标校验；check-token-permission 地址校验 |
|          | `RepoCoordinateResolverImpl` | 复用 `SqlLikeUtil`，删除重复转义                             |
|          | `SqlLikeUtil`（新增）        | LIKE 通配符转义单一来源                                      |
| Webhook  | `MergeRequestEventHandler`   | 坐标校验；PR files 查询参数 builder 化                       |
|          | `PrSyncEventHandler`         | 入口坐标校验                                                 |
|          | `NotifyConfigEventHandler`   | 入口坐标校验                                                 |
| GraphQL  | `MergeRequestEventHandler`   | 固定查询/mutation + variables                                |
| 配置     | `application-prod.yaml`      | 关闭生产 Swagger 端点                                        |

**测试类**

- `ApiUrlUtilTest`、`SigInfoClientTest`、`SigDefaultParamBuilderTest`、`TokenPermissionEvaluatorTest`、`MergeRequestEventHandlerTest`（!306）；
- `SqlLikeUtilTest`、`RepoServiceImplLikeEscapeTest`（!309）；
- `MergeRequestEventHandlerGraphqlTest`（!310）；
- `RepoUrlUtilTest`、`PrSyncEventHandlerTest`（!311）。

## 4. 数据模型设计

本次整改无新增表、无表结构变更、无数据迁移。

| 项         | 变更                                                                     | 备注                                                            |
| ---------- | ------------------------------------------------------------------------ | --------------------------------------------------------------- |
| 数据库表   | 无                                                                       | 不新增字段、不改索引                                            |
| 查询实体   | `RepoInfoEntity` / `ProjectBranchQueryEntity` 的 LIKE 字段在内存中先转义 | 仅影响 SQL 参数值，不改变持久化数据                             |
| 配置项     | `application-prod.yaml` 新增两个 springdoc 开关                          | 无新增配置 key、无配置中心变更                                  |
| 存量数据   | 无需清洗                                                                 | `repo_info.repo_url` 已由历史整改校验；新增入口继续拦截非法坐标 |
| Redis / MQ | 无变更                                                                   | 本次不新增缓存键、不改消息结构                                  |

## 5. 性能设计

- **路径段校验**：`ApiUrlUtil` 与入口坐标校验均为 O(路径段数) 的字符串判断，无额外网络与数据库开销；非法输入在入口 fail-closed，避免无效出站请求。
- **LIKE 转义**：单次字符串三次替换，O(n) 且 n 为查询关键字长度；转义后 `%`/`_` 按字面量匹配，可减少通配符导致的大范围扫描，索引使用方式不变。
- **GraphQL variables**：请求体仅增加一个 `variables` 对象，分页次数与每页大小不变；无额外往返。
- **Webhook 校验**：在去重与 token 反查前执行，非法事件提前返回，减少 Redis/DB/平台 API 调用。
- **Swagger 关闭**：生产环境不再注册调试端点，减少启动期端点扫描与运行时暴露面，对业务接口无性能影响。

## 6. API接口设计

本次不新增对外 HTTP 接口，不改变请求/响应结构。行为变化如下：

| 接口/入口                                      | 变化                                                                                      | 影响方          | 状态           |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------- | --------------- | -------------- |
| `/check-token-permission`（新增仓库场景）      | `repoUrl` 含 query/fragment/userInfo、`.`/`..` 段或非法字符时返回既有失败文案，不调用平台 | 前端/外部调用方 | !306 open      |
| `/query-repo`、`/query-project-branch`         | `*Like` 字段中的 `%`/`_` 按字面量匹配，结果集可能收窄；响应结构不变                       | 前端无感        | !309 open      |
| Webhook 入口（MergeRequest / PrSync / Notify） | 非法坐标事件被丢弃，HTTP 入口仍返回原有受理结果；不改变回调协议                           | 平台侧无感      | !306/!311 open |
| GitHub 检视意见解决链路                        | 出站 GraphQL 请求改为 `query + variables` 结构，对外无接口变化                            | 无              | !310 open      |
| 生产 Swagger                                   | `/v3/api-docs`、`/swagger-ui/**` 返回 404；beta/gama/本地不变                             | 运维/开发       | !303 open      |

## 7. 安全设计

### 7.1 威胁与 CWE 映射

| 问题         | CWE               | 攻击面                                               | 整改后的控制                                |
| ------------ | ----------------- | ---------------------------------------------------- | ------------------------------------------- |
| 路径段注入   | CWE-22            | webhook / SIG / token 探测的 owner/repo 进入平台 URL | 入口白名单 + 公共出口拒绝点段 + fail-closed |
| LIKE 通配符  | CWE-20            | 仓库/分支列表模糊筛选                                | 通配符转义，按字面量匹配                    |
| GraphQL 拼接 | CWE-943           | GitHub reviewThreads / resolveReviewThread           | 固定语句 + variables                        |
| Webhook 坐标 | CWE-22            | PrSync / Notify 报文 owner/repo                      | 入口坐标校验 + 丢弃事件                     |
| Swagger 暴露 | CWE-489 / CWE-215 | 生产调试端点                                         | 生产环境关闭 springdoc 端点                 |

### 7.2 安全基线

1. **出站 URL**：统一 `ApiUrlUtil` 分段编码；路径段拒绝 `.`/`..`；平台 host 精确匹配；凭证只走请求头。
2. **入口校验**：webhook/SIG/token 探测坐标先过字符白名单；owner 支持嵌套分组但逐段校验；非法 fail-closed。
3. **查询安全**：SQL 全参数化 + LIKE 通配符转义；排序字段继续走白名单；GraphQL 外部取值全部 variables 化。
4. **日志安全**：非法坐标告警使用 `LogSanitizer` 净化，避免 CRLF 日志注入。
5. **暴露面**：生产关闭 Swagger 调试端点；非生产保留文档能力；网关 `/manage` 路由由环境侧复核。

### 7.3 残余风险与验收

- **残余风险**：
  - Webhook 报文本身经过 HMAC 验签，坐标校验为纵深防御；平台命名规则与 token 反查仍是一层约束；
  - `RepoUrlUtil.isLegalOwner` 与 `SigInfoClient.isLegalOwner` 存在短期重复实现，合并后收敛；
  - #225 的实际可达性还取决于网关 `/manage` 路由，需环境侧确认生产 404。
- **验收标准**：
  1. 5 个子 Issue 对应的 PR 均合入 `release_20261116_iter1`；
  2. 路径段/坐标非法时无平台请求、无 MQ 发送；
  3. LIKE 普通关键字查询结果不变，含通配符输入按字面量匹配；
  4. GraphQL 请求语句不包含外部取值；
  5. 生产 `/v3/api-docs`、`/swagger-ui/**` 返回 404，beta Swagger UI 正常；
  6. 相关单测、pre-commit 与流水线全部通过，对外 HTTP 契约无变化。
