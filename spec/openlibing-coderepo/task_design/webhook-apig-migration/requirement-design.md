# Webhook 接入 APIG（白名单 + 限流）需求设计文档

> **状态勘误（2026-08-29）**：本需求的整体交付与最终方案以 `proposal.md` / `design.md` / `tasks.md` /
> `archive.md` 为准。两点说明：
> - 最终 APIG 后端入口统一为 `/apig/webhook/{platform}/repo`（本文件中早期草稿的 `/webhookEvent/apig/hooks/{platform}`
>   不作为最终路径）。
> - 阶段 3「废弃旧接口」已作为独立小需求交付（openlibing/openlibing-coderepo#153），5 个 `/webhookEvent/hooks/*`
>   旧接口已删除，webhook 事件流量全部收敛到 APIG 入口。

> 单仓 Standard 模式需求设计文档。仅涉及 `openlibing-coderepo-fork`（后端代码改造）+ 华为云 APIG 控制台配置（非代码）。
>
> 目标：将 3 个 webhook 接口（gitcode / gitee / github 各 1 个，不含 repoId）前置到 APIG，利用 APIG 的 IP 白名单 + 限流能力，确保只有 gitcode/gitee/github 出口 IP 能调用；同时改造 `refreshWebhookHandler` 定时任务，运行时把存量 webhook 链接（含 repoId 旧路径 + 旧直连 URL）统一迁移到新的 APIG 链接（不含 repoId）。
>
> **本次清理范围**：含 `{repoId}` 的 2 个旧路径接口（`/hooks/gitcode/{repoId}`、`/hooks/gitee/{repoId}`）废弃，APIG 不再发布，存量 webhook URL 全部迁移到不含 repoId 的新路径。后端 Controller 代码暂保留作为过渡兼容（兜底迁移遗漏），迁移完成后可删除。

## 1. 方案设计

### 1.1 背景与目标

当前 5 个 webhook 接口（含 2 个 `{repoId}` 兼容路径）直接暴露在 `openlibing-coderepo` 网关路径下（`https://www.openlibing.com/gateway/openlibing-coderepo/webhookEvent/hooks/{platform}`），任何能访问该域名的客户端都可调用，存在以下风险：

- **来源不可控**：无 IP 白名单，无法限制只有 gitcode/gitee/github 出口能触发。
- **无限流**：恶意或异常重试可能打垮 coderepo 服务。
- **认证弱**：webhook 自身签名校验在应用层（`MachineInterfaceAuthUtil`），网络层无前置过滤。

| 维度 | 目标 |
|------|------|
| 来源限制 | 仅 gitcode/gitee/github 出口 IP 段可调用 webhook（APIG IP 白名单） |
| 限流 | 单接口限流（APIG 流控策略），防止异常重试打垮服务 |
| 存量迁移 | `refreshWebhookHandler` 定时任务运行时把存量 webhook URL（含 repoId 旧路径 + 旧直连 URL）改为新的 APIG URL（不含 repoId） |
| 新增仓库 | 未创建 webhook 的代码仓直接按新的 APIG URL 生成 webhook |
| 路径统一 | 废弃含 `{repoId}` 的旧路径接口，APIG 只发布 3 个不含 repoId 的接口；全部 webhook 统一到不含 repoId 的新路径 |

### 1.2 涉及的 webhook 接口

来源：[WebHookEventController](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/WebHookEventController.java)

**新建 3 个 APIG 专用后端接口（不含 repoId，仅供 APIG 转发）**：

| # | 接口路径（apig） | 接口路径（后端） | 平台 | 说明 |
|---|----------------|----------------|------|------|
| 1 | `POST /webhook/gitcode/repo` | `POST /apig/webhook/gitcode/repo` | gitcode | 新增 |
| 2 | `POST /webhook/gitee/repo` | `POST /apig/webhook/gitee/repo` | gitee | 新增 |
| 3 | `POST /webhook/github/repo` | `POST /apig/webhook/github/repo` | github | 新增 |

注：需要在openlibing-gateway WebhookAuthFilter 中新增链接校验白名单：/apig/webhook/
同时在注释中声明：apig转发的webhook接口规范示例为：/apig/webhook/{platform}/repo以及/apig/webhook/{platform}/pipeline/{pipelineId}，其中repo和piepline表示具体业务场景


**保留的 5 个旧接口（仅增加日志，观察期后废弃）**：

| # | 接口路径（后端） | 平台 | 说明 |
|---|----------------|------|------|
| 1 | `POST /webhookEvent/hooks/gitcode` | gitcode | 旧直连路径，仅日志观察，观察期后废弃 |
| 2 | `POST /webhookEvent/hooks/gitcode/{repoId}` | gitcode | 含 repoId 旧路径，仅日志观察，观察期后废弃 |
| 3 | `POST /webhookEvent/hooks/gitee` | gitee | 旧直连路径，仅日志观察，观察期后废弃 |
| 4 | `POST /webhookEvent/hooks/gitee/{repoId}` | gitee | 含 repoId 旧路径，仅日志观察，观察期后废弃 |
| 5 | `POST /webhookEvent/hooks/github` | github | 旧直连路径，仅日志观察，观察期后废弃 |

> **物理隔离设计**：APIG 后端路径指向新建的 `/webhookEvent/apig/hooks/{platform}`，与旧接口 `/webhookEvent/hooks/` 完全分离。新接口只有 APIG 能转发到（webhook URL 已迁移到 APIG 的流量），旧接口只有直连请求会访问（webhook URL 未迁移的流量）。通过日志统计哪个接口有流量，即可 100% 判断迁移状态，无需依赖请求头。

### 1.3 整体架构

```
gitcode/gitee/github
        │ HTTPS POST（携带平台签名头）
        ▼
┌──────────────────────────────────────────┐
│  华为云 APIG                              │
│  ┌────────────────────────────────────┐  │
│  │ 3 个 API（POST，无认证，HTTPS）     │  │
│  │  前端路径 /coderepo/webhook/hooks/*│  │
│  │  后端路径 /webhookEvent/apig/hooks/*│  │
│  │  （不含 repoId，3 个平台各 1 个）  │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ 访问控制策略：IP 白名单            │  │
│  │   - gitcode 出口 IP 段             │  │
│  │   - gitee  出口 IP 段              │  │
│  │   - github 出口 IP 段              │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ 流控策略：单接口限流（按需配置）   │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
        │ 转发到新后端接口
        ▼
┌──────────────────────────────────────────┐
│  openlibing-coderepo-fork                │
│  WebHookEventController                  │
│  ┌────────────────────────────────────┐  │
│  │ 新接口（APIG 专用，3 个）          │  │
│  │ /webhookEvent/apig/hooks/{platform}│  │
│  │ → 日志 path=apig → 投递 MQ         │  │
│  └────────────────────────────────────┘  │
│  ┌────────────────────────────────────┐  │
│  │ 旧接口（5 个，仅日志观察）         │  │
│  │ /webhookEvent/hooks/{platform}     │  │
│  │ /webhookEvent/hooks/{platform}/{id}│  │
│  │ → 日志 path=direct/legacy          │  │
│  │ → 投递 MQ（兼容未迁移流量）        │  │
│  └────────────────────────────────────┘  │
└──────────────────────────────────────────┘
```

### 1.4 关键决策

| 决策点 | 选择 | 理由 |
|--------|------|------|
| APIG 认证方式 | 无认证 | webhook 由 git 平台主动调用，无法携带 APIG 鉴权凭证；来源控制交给 IP 白名单 |
| APIG API 数量 | 3 个（gitcode / gitee / github 各 1 个，不含 repoId） | 存量 webhook 全部迁移到不含 repoId 的新路径，无需保留 repoId 旧路径；APIG 只发布 3 个接口 |
| APIG 后端接口 | 新建 3 个专用接口 `/webhookEvent/apig/hooks/{platform}` | 物理隔离 APIG 流量与直连流量，通过日志统计接口路径即可 100% 判断迁移状态，无需依赖请求头，无需逐仓确认 webhook URL |
| 旧接口处理 | 5 个旧接口全部保留并增加日志，观察期后一次性废弃 | 不立即废弃，先通过日志观察确认旧接口无流量（存量 webhook 全部迁移完成），再一次性删除 Controller 代码 |
| 流量来源识别 | 通过接口路径物理隔离 | 新接口有流量 = 走 APIG（已迁移）；旧接口有流量 = 直连后端（未迁移）。比请求头方式更直观可靠 |
| webhook URL 配置 | 复用 `openlibing.coderepo.webhook.url`，Apollo 改值为 APIG URL | 改值后新创建的 webhook 自动走 APIG；存量 webhook 由定时任务迁移 |
| 存量迁移方式 | PATCH 就地更新 URL（复用 webhook id） | 沿用 `updateRepoWebhookForPushEvent` 的 PATCH 模式，避免删除重建导致中间态事件丢失 |
| 旧 webhook 识别 | URL 含 `openlibing-coderepo/webhookEvent/hooks/` 子串即视为 coderepo webhook | 既能匹配旧直连 URL，也能匹配含 repoId 的旧路径；新 APIG URL 不含该子串，不会误判 |
| local/beta 环境 | 迁移 | 测试环境需要验证 APIG 流程 |

### 1.5 流程模式与风险

**Standard 模式**。判定依据：

- 改动规模约 100-200 行（单模块、少量文件）。
- 单仓（`openlibing-coderepo-fork`）。
- 无 DB schema 变化、无新 REST API。
- 安全影响有限（IP 白名单在 APIG 侧，代码侧仅改 URL）。

| 风险 | 对策 |
|------|------|
| APIG URL 配置错误导致全部 webhook 失效 | Apollo 配置变更后先在单仓库（`repoId` 参数）验证，再全量执行 |
| github PATCH `config` 丢失 `content_type`/`secret` | 实现时先读原 webhook `config`，连同 `url` 一起回填 |
| 存量 webhook 迁移期间事件丢失 | 采用 PATCH 就地更新（非删除重建），webhook id 不变，中间态窗口最小 |
| gitcode/gitee/github 出口 IP 段变更 | IP 白名单由运维定期核对各平台官方文档更新 |
| 含 repoId 旧路径 webhook 迁移遗漏 | Controller 代码暂保留作为兜底；全量迁移后通过日志核对遗漏仓库并补迁 |
| 旧直连 URL 被外部嗅探后绕过 APIG 直调 | 迁移完成后，可后续在网关层封禁 `/webhookEvent/hooks/` 直连路径（本需求不含） |

### 1.6 回滚

- Apollo 将 `openlibing.coderepo.webhook.url` 改回旧直连 URL → `refreshWebhookHandler` 再次执行即可把 webhook URL 迁回（迁移逻辑双向生效）。
- APIG 侧下线 3 个 API 不影响后端接口，仅失去白名单与限流能力。

### 1.7 观察期与废弃策略

为确保迁移彻底、避免提前废弃旧接口导致事件丢失，采用**分阶段废弃**策略：

#### 阶段 1：迁移上线（本次需求交付）

- 新建 3 个 APIG 专用后端接口 `/webhookEvent/apig/hooks/{platform}`，与旧接口物理隔离。
- APIG 发布 3 个 API，后端路径指向新建的专用接口。
- 5 个旧接口（`/webhookEvent/hooks/`）保留不动，仅增加流量来源日志（见 3.4 节）。
- `refreshWebhookHandler` 全量执行，迁移存量 webhook URL 到 APIG URL。

#### 阶段 2：观察期（迁移上线后 1-2 周）

通过日志监控验证迁移彻底性，**两个指标同时满足**方可进入阶段 3：

| 指标 | 验证方式 | 期望结果 |
|------|---------|---------|
| 旧接口无流量 | 监控 5 个旧接口（`/webhookEvent/hooks/`）的访问日志，关注 `path=direct` 与 `path=legacy-with-repoId` 日志 | 观察期内无任何请求（说明存量 webhook 全部迁移完成，无直连后端流量） |
| 新接口有正常流量 | 监控 3 个新接口（`/webhookEvent/apig/hooks/`）的访问日志，关注 `path=apig` 日志 | 流量正常（与平台事件触发频率匹配，说明 APIG 链路畅通） |

**异常处理**：

- 若旧接口仍有 `path=direct` 流量：说明有存量 webhook URL 未迁移成功，通过日志定位 `repoId`（含 repoId 路径）或仓库信息，手动触发该仓库的 `refreshWebhookHandler`（传 `projectId` + `repoId` 参数）补迁。
- 若旧接口仍有 `path=legacy-with-repoId` 流量：同上，含 repoId 路径的 webhook 未迁移，需补迁。
- 若新接口无流量但旧接口有流量：检查 Apollo 配置是否正确切换为 APIG URL，或 `refreshWebhookHandler` 是否执行成功。

#### 阶段 3：废弃旧接口（观察期通过后，独立需求）

- 删除 `WebHookEventController` 中 5 个旧接口的 `@PostMapping` 方法（`/hooks/{platform}` 与 `/hooks/{platform}/{repoId}`）。
- 清理流量来源日志辅助方法（如不再需要区分来源）。
- 该阶段作为独立小需求交付，不在本次需求范围内。

> **本次需求范围**：仅包含阶段 1（新建 APIG 专用接口 + 迁移上线 + 日志埋点）。阶段 2（观察）与阶段 3（废弃）在本次需求交付后由运维/开发根据日志数据独立推进。

## 2. 实现逻辑设计

### 2.1 现状

[XxlJobHandler.refreshWebhookHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java#L280-L317) → `refreshUnconfiguredWebhooks` → `refreshSingleRepoWebhook` → 依次调用：

1. [autoSetCoderepoWebHook](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java#L4234-L4303)：拉取平台 webhook 列表 → 清理 beta 残留 → 新 URL 精确匹配则跳过 → 旧 URL 前缀匹配则去重后跳过 → 否则创建新 webhook。
2. [ensureCoderepoWebhookPushEventSubscribed](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java#L4342-L4413)：对已存在 coderepo webhook PATCH 补齐 push 事件订阅。

webhook URL 来自配置 `openlibing.coderepo.webhook.url`（[声明](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java#L272-L273)），模板形如 `https://www.openlibing.com/gateway/openlibing-coderepo/webhookEvent/hooks/%s`。

**现状缺陷**：`autoSetCoderepoWebHook` 在识别到旧 URL 前缀匹配时只做「去重清理 + 跳过创建」，不会更新 webhook 的 URL，导致存量 webhook 一直指向旧直连地址，迁移到 APIG 必须补齐「PATCH 更新 URL」分支。

### 2.2 配置变更（Apollo）

将 `openlibing.coderepo.webhook.url` 的值改为新的 APIG URL 模板：

```
https://<apig-host>/coderepo/webhook/hooks/%s
```

`%s` 仍由平台名替换（gitcode/gitee/github）。配置变更后：

- 新创建的 webhook 自动使用 APIG URL（不含 repoId）。
- 存量 webhook（含 repoId 旧路径 + 旧直连 URL）由下方定时任务逻辑统一迁移到不含 repoId 的新 APIG URL。

### 2.3 `autoSetCoderepoWebHook` 改造后主流程

```
autoSetCoderepoWebHook(repoInfo, org, repo):
  if 配置为空 → skip
  if local/beta 环境 → 沿用现有逻辑（cleanBeta + create），return

  newUrl = coderepoWebhookUrlTemplate.replace("%s", platform)   // 现为 APIG URL（不含 repoId）
  webhookList = getRepoWebhookList(...)

  if webhookList 为空 → createCoderepoWebhook（用 newUrl）; return

  cleanBetaWebhooks(webhookList, ...)

  // 1. newUrl 精确匹配 → 已迁移完成，跳过
  if 存在 w.url == newUrl → log "already migrated"; return

  // 2. 识别存量 coderepo webhook（URL 含 "openlibing-coderepo/webhookEvent/hooks/" 子串）
  //    覆盖两类存量 webhook：
  //    - 旧直连 URL（不含 repoId）：/gateway/openlibing-coderepo/webhookEvent/hooks/gitcode
  //    - 含 repoId 旧路径：/gateway/openlibing-coderepo/webhookEvent/hooks/gitcode/123
  coderepoWebhooks = webhookList.filter(w -> w.url 含 "openlibing-coderepo/webhookEvent/hooks/")

  if coderepoWebhooks 非空:
     // 存量 webhook 需迁移 URL：选一个保留（优先有有效 token 的），PATCH 更新 URL 到 newUrl，其余删除
     keepWebhook = 选定保留的 webhook（沿用 cleanDuplicateLegacyWebhooks 的选主逻辑）
     updateRepoWebhookUrl(platform, org, repo, keepWebhook, newUrl)   // 新增
     删除其余 coderepoWebhooks（去重）
     log "migrated coderepo webhook url"
     return

  // 3. 无 coderepo webhook（仅有非 coderepo 的其他 webhook）→ 创建新 webhook
  createCoderepoWebhook（用 newUrl）
```

**关键改动**：第 2 步是新增的「URL 迁移分支」。原逻辑在此处只会「跳过创建」，导致存量 webhook 一直指向旧 URL；改造后改为 PATCH 更新 URL，实现运行时迁移。

> **子串匹配覆盖两类存量 webhook**：现有「旧 URL 前缀匹配」判定用的是 `newUrl + "/"` 前缀（即 `新URL/{repoId}` 形式），只能识别含 repoId 的旧路径。改造后改用 `openlibing-coderepo/webhookEvent/hooks/` 子串匹配，可同时覆盖：
> - 旧直连 URL（不含 repoId）：`/gateway/openlibing-coderepo/webhookEvent/hooks/gitcode`
> - 含 repoId 旧路径：`/gateway/openlibing-coderepo/webhookEvent/hooks/gitcode/123`
>
> 两类存量 webhook 都会被 PATCH 更新到不含 repoId 的新 APIG URL（`/coderepo/webhook/hooks/{platform}`），实现路径统一。
>
> 新 APIG URL 不含 `openlibing-coderepo/webhookEvent/hooks/` 子串，不会误判为存量 webhook。

### 2.4 新增 `updateRepoWebhookUrl` 方法逻辑

参考 [updateRepoWebhookForPushEvent](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java#L4435-L4490) 的 PATCH 模式，新增 URL 更新方法。逻辑步骤：

1. 调用 `getAccessTokenForWebhook(platform, org, repo)` 获取 token；token 为空则记录 warn 并返回 false。
2. 按平台构造 PATCH 请求 URL（复用 `*_WEBHOOK_UPDATE_URL` 常量，与 update push event 同一 URL，HTTP 方法均为 PATCH）。
3. 按平台构造 PATCH body（见下表）。
4. `sendRequest("PATCH", url, body, headerMap)` 发送请求。
5. 响应 200 视为成功；非 200 记录 warn 并返回 false。

各平台 body 格式：

| 平台 | PATCH body | 说明 |
|------|-----------|------|
| gitee / gitcode | `{"url": "<newUrl>"}` | 平台保留未传字段（事件订阅、secret 等不变） |
| github | `{"config": {"url": "<newUrl>", "content_type": "<原值>", "secret": "<原值>"}}` | github URL 在 `config.url` 下；`content_type`、`secret` 必须连同回填，否则会被重置为默认值 |

token 获取、请求头构造、响应判断均与 `updateRepoWebhookForPushEvent` 保持一致：

- gitee / gitcode：`PRIVATE-TOKEN` 头
- github：`Authorization: Bearer` + `Accept: application/vnd.github+json` 头

> **github 注意**：PATCH `config` 时只传 `url` 会导致 `content_type`、`secret` 等字段被重置为默认值。实现时需先从 webhook 列表响应中读取原 `config.content_type`、`config.secret` 等，连同 `url` 一起回填，避免丢失原配置。由于现有 `RepoWebhook` 实体未映射 `config` 字段，需扩展实体（见第 4 节）或单独 GET 单个 webhook 详情获取 config。

### 2.5 `ensureCoderepoWebhookPushEventSubscribed` 同步调整

`ensureCoderepoWebhookPushEventSubscribed` 在 `autoSetCoderepoWebHook` 之后执行，用于对 coderepo webhook 补齐 push 事件订阅。其现有判定 coderepo webhook 的逻辑为「新 URL 精确匹配 + legacy URL 前缀匹配（`newUrl + "/"`）」：

- **迁移成功场景**：webhook URL 已更新为 newUrl（APIG URL），「新 URL 精确匹配」分支命中，push 事件补齐正常生效。
- **迁移失败场景**（PATCH 失败或 token 失效）：webhook URL 仍为旧路径（含 repoId 或旧直连），但 newUrl 已变为 APIG URL，`newUrl + "/"` 前缀无法匹配旧路径，导致 `ensureCoderepoWebhookPushEventSubscribed` 漏判，push 事件补齐失效。

**同步改造**：将 `ensureCoderepoWebhookPushEventSubscribed` 的 coderepo webhook 识别逻辑也改为「新 URL 精确匹配 + `openlibing-coderepo/webhookEvent/hooks/` 子串匹配」，与 `autoSetCoderepoWebHook` 保持一致。这样无论迁移是否成功，都能正确识别 coderepo webhook 并补齐 push 事件订阅。

> 改造点：[ensureCoderepoWebhookPushEventSubscribed](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java#L4364-L4375) 中筛选 `coderepoWebhooks` 的 filter 条件，将 `url.startsWith(legacyUrlPrefix)` 替换为 `url.contains("openlibing-coderepo/webhookEvent/hooks/")`。

### 2.6 `refreshWebhookHandler` 入口不变

[XxlJobHandler.refreshWebhookHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java#L280-L317) 的入参解析、`refreshUnconfiguredWebhooks`、`refreshSingleRepoWebhook` 调用链均不变。改造落在 `autoSetCoderepoWebHook` 与 `ensureCoderepoWebhookPushEventSubscribed` 内部，对外行为兼容：

- 不传参 → 全量扫描，存量 webhook 迁移 URL + 缺失 webhook 创建
- 传 `projectId` → 单项目范围迁移
- 传 `projectId` + `repoId` → 单仓库迁移

### 2.7 不改动的部分

- 5 个 webhook 接口的 Controller 逻辑、签名校验（`MachineInterfaceAuthUtil`）、MQ 投递逻辑不变（含 repoId 的 2 个接口保留作为兜底，APIG 不发布）。
- `cleanBetaWebhooks`、`cleanDuplicateLegacyWebhooks` 去重逻辑不变，复用现有选主与删除能力。
- `XxlJobHandler.java`、`WebHookEventController.java` 无需改动。

## 3. 类设计

### 3.1 涉及类清单

| 类 | 路径 | 改动类型 |
|----|------|---------|
| `RepoServiceImpl` | [RepoServiceImpl.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java) | 修改 + 新增方法 |
| `WebHookEventController` | [WebHookEventController.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/WebHookEventController.java) | 修改（增加流量来源日志） |
| `RepoWebhook` | [RepoWebhook.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/webhooks/RepoWebhook.java) | 新增字段（github config 映射） |
| `XxlJobHandler` | [XxlJobHandler.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java) | 不改动 |
| `MachineInterfaceAuthUtil` | [MachineInterfaceAuthUtil.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/utils/MachineInterfaceAuthUtil.java) | 不改动 |

### 3.2 `RepoServiceImpl` 改动方法

#### 3.2.1 修改 `autoSetCoderepoWebHook`

```java
public void autoSetCoderepoWebHook(RepoInfoEntity repoInfo, String org, String repo)
```

- 改动点：将原「旧 URL 前缀匹配（`newUrl + "/"`）」分支替换为「`openlibing-coderepo/webhookEvent/hooks/` 子串匹配」分支，覆盖含 repoId 旧路径与旧直连 URL 两类存量 webhook；在该分支中调用新增的 `updateRepoWebhookUrl` 完成 URL 迁移到不含 repoId 的新 APIG URL。
- 入参、返回值、前置校验（配置空跳过、local/beta 分支）均不变。

#### 3.2.2 修改 `ensureCoderepoWebhookPushEventSubscribed`

```java
public void ensureCoderepoWebhookPushEventSubscribed(RepoInfoEntity repoInfo, String org, String repo)
```

- 改动点：将筛选 `coderepoWebhooks` 的 filter 条件从「`url.startsWith(newUrl + "/")`」改为「`url.contains("openlibing-coderepo/webhookEvent/hooks/")`」，与 `autoSetCoderepoWebHook` 的识别逻辑保持一致。
- 理由：newUrl 变为 APIG URL 后，原 `newUrl + "/"` 前缀无法匹配含 repoId 的旧路径，迁移失败场景下会漏判。
- 入参、返回值、push 事件补齐逻辑（PATCH body 构造、`isPushEventSubscribed` 判断）均不变。

#### 3.2.3 新增 `updateRepoWebhookUrl`

```java
/**
 * 调用平台 PATCH 接口更新单个 webhook 的 URL，保留 webhook id 与其他配置不变。
 * 用于存量 webhook（含 repoId 旧路径 + 旧直连 URL）迁移到不含 repoId 的 APIG URL。
 *
 * @param platform 代码托管平台（gitee/gitcode/github）
 * @param org 组织
 * @param repo 仓库名
 * @param webhook 待更新的 webhook（需含 id；github 还需含 config）
 * @param newUrl 新的 webhook URL（不含 repoId）
 * @return true 更新成功；false 更新失败
 */
private boolean updateRepoWebhookUrl(
    String platform, String org, String repo, RepoWebhook webhook, String newUrl)
```

- 复用 `getAccessTokenForWebhook` 获取 token。
- 复用 `*_WEBHOOK_UPDATE_URL` 常量构造 URL。
- 调用 `sendRequest("PATCH", ...)` 发送请求。

#### 3.2.4 新增 `buildWebhookUrlUpdateBody`（github config 回填辅助）

```java
/**
 * 构造 webhook URL 更新的 PATCH body。
 * - gitee / gitcode：{"url": "<newUrl>"}
 * - github：{"config": {"url": "<newUrl>", "content_type": "<原值>", "secret": "<原值>"}}
 *           content_type / secret 从原 webhook config 读取回填，避免被重置。
 */
private String buildWebhookUrlUpdateBody(String platform, RepoWebhook webhook, String newUrl)
```

### 3.3 `RepoWebhook` 实体扩展

新增 `config` 字段以映射 github webhook 列表响应中的 `config` 对象，供 `updateRepoWebhookUrl` 读取原 `content_type`、`secret` 回填：

```java
/** github webhook 配置（url / content_type / secret 等），gitee/gitcode 不返回 */
@JSONField(name = "config")
private RepoWebhookConfig config;
```

新增内部类 `RepoWebhookConfig`：

```java
@Data
public static class RepoWebhookConfig {
  @JSONField(name = "url")
  private String url;

  @JSONField(name = "content_type")
  private String contentType;

  @JSONField(name = "secret")
  private String secret;
}
```

> gitee / gitcode webhook 响应不含 `config` 字段，反序列化时该字段为 null，不影响。

### 3.4 `WebHookEventController` 改动（新增 APIG 专用接口 + 流量来源日志）

#### 3.4.1 新增 3 个 APIG 专用接口方法

新增 3 个 `@PostMapping` 方法，路径为 `/webhookEvent/apig/hooks/{platform}`，仅供 APIG 转发调用：

```java
@PostMapping(value = {"/apig/hooks/gitcode"})
public String apigGitCodeWebhookEvent(HttpServletRequest request) {
  logWebhookSource("gitcode", "apig");
  // 复用现有 gitCodeWebhookEvent 的处理逻辑
  return handleGitCodeWebhook(request);
}

@PostMapping(value = {"/apig/hooks/gitee"})
public String apigGiteeWebhookEvent(HttpServletRequest request) {
  logWebhookSource("gitee", "apig");
  return handleGiteeWebhook(request);
}

@PostMapping(value = {"/apig/hooks/github"})
public String apigGithubWebhookEvent(HttpServletRequest request) {
  logWebhookSource("github", "apig");
  return handleGithubWebhook(request);
}
```

> **避免代码重复**：将现有 5 个旧接口的签名校验、MQ 投递等核心逻辑抽取为公共处理方法（如 `handleGitCodeWebhook`、`handleGiteeWebhook`、`handleGithubWebhook`），新旧接口均调用这些公共方法。这样新接口只多一行 `logWebhookSource` 调用，无逻辑重复。

#### 3.4.2 修改 5 个旧接口方法（增加日志）

现有 5 个旧接口方法在入口处增加 `logWebhookSource` 调用，核心逻辑改为调用抽取出的公共处理方法：

| 旧接口方法 | 日志调用 |
|---------|---------|
| `gitCodeWebhookEvent`（无 repoId 路径） | `logWebhookSource("gitcode", "direct")` |
| `gitCodeWebhookEvent`（含 repoId 路径） | `logWebhookSource("gitcode", "legacy-with-repoId")` |
| `giteeWebhookEvent`（无 repoId 路径） | `logWebhookSource("gitee", "direct")` |
| `giteeWebhookEvent`（含 repoId 路径） | `logWebhookSource("gitee", "legacy-with-repoId")` |
| `githubWebhookEvent` | `logWebhookSource("github", "direct")` |

> gitcode / gitee 的 `@PostMapping` 用 `{"/hooks/gitcode", "/hooks/gitcode/{repoId}"}` 合并映射，方法内通过 `repoId` 是否为空判断路径类型，日志的 `path` 字段相应取 `direct` 或 `legacy-with-repoId`。

#### 3.4.3 新增日志辅助方法

```java
/**
 * 记录 webhook 请求流量来源，用于观察 APIG 迁移彻底性。
 * 通过接口路径物理隔离区分流量来源：
 * - path=apig：请求来自 APIG 转发（webhook URL 已迁移到 APIG）
 * - path=direct：请求直连后端旧路径（webhook URL 未迁移，仍指向旧直连 URL）
 * - path=legacy-with-repoId：请求直连后端含 repoId 旧路径（webhook URL 未迁移）
 *
 * @param platform 代码托管平台
 * @param path 流量来源路径标识
 */
private void logWebhookSource(String platform, String path) {
  LOGGER.info(
      "webhook source stat, platform:{}, path:{}",
      platform, path);
}
```

#### 3.4.4 日志观察要点

观察期内通过 ELK / 日志检索统计：

- `path=apig` 的日志：正常流量，迁移成功，APIG 链路畅通。
- `path=direct` 的日志：旧直连路径有流量，说明有存量 webhook URL 未迁移到 APIG，需补迁。
- `path=legacy-with-repoId` 的日志：含 repoId 旧路径有流量，说明有存量 webhook URL 未迁移到 APIG，需补迁。

> 观察期内 `path=apig` 流量正常 + `path=direct` / `path=legacy-with-repoId` 流量为 0 → 迁移彻底，可进入阶段 3 废弃旧接口。

## 4. 数据模型设计

### 4.1 `RepoWebhook` 实体（平台 webhook 列表响应映射）

现有字段（不变）：

| 字段 | JSON 映射 | 类型 | 说明 |
|------|----------|------|------|
| `id` | `id` | String | webhook id |
| `url` | `url` | String | webhook URL（gitee/gitcode） |
| `password` | `password` | String | webhook 签名（gitee/gitcode） |
| `isPushEvents` | `push_events` | Boolean | push 事件订阅（gitee/gitcode） |
| `isTagPushEvents` | `tag_push_events` | Boolean | tag push 事件 |
| `isIssuesEvents` | `issues_events` | Boolean | issue 事件 |
| `isNoteEvents` | `note_events` | Boolean | note 事件 |
| `isMergeRequestsEvents` | `merge_requests_events` | Boolean | merge request 事件 |
| `events` | `events` | List\<String\> | github 事件列表 |
| `accessToken` | `access_token` | String | 访问 token |
| `encryptionType` | `encryption_type` | String | 加密类型 |

新增字段：

| 字段 | JSON 映射 | 类型 | 说明 |
|------|----------|------|------|
| `config` | `config` | RepoWebhookConfig | github webhook 配置（url/content_type/secret） |

### 4.2 配置项

| 配置项 | 来源 | 现值（示例） | 新值（示例） | 说明 |
|--------|------|-------------|-------------|------|
| `openlibing.coderepo.webhook.url` | Apollo | `https://www.openlibing.com/gateway/openlibing-coderepo/webhookEvent/hooks/%s` | `https://<apig-host>/coderepo/webhook/hooks/%s` | webhook 回调 URL 模板，`%s` 由平台名替换 |

其余配置项（`gitee.common.access_token`、`gitcode.common.access_token`、`openlibing.webhook.sign.account.description`、`security.part1`、`spring.profiles.active` 等）均不变。

### 4.3 无 DB schema 变化

本需求不涉及任何数据库表结构变更：

- `repo_info` 表无新增字段（webhook URL 不入库，每次都从平台拉取列表）。
- `machine_interface_account` 表无变更（webhook 签名密钥仍从该表读取）。
- 无新增表、无新增索引、无数据迁移。

### 4.4 平台 webhook API 响应结构（参考）

**gitee / gitcode** GET `/repos/{org}/{repo}/hooks` 响应元素：

```json
{
  "id": 12345,
  "url": "https://www.openlibing.com/gateway/openlibing-coderepo/webhookEvent/hooks/gitcode",
  "push_events": true,
  "tag_push_events": false,
  "merge_requests_events": true,
  "password": "***"
}
```

**github** GET `/repos/{org}/{repo}/hooks` 响应元素：

```json
{
  "id": 67890,
  "url": "https://api.github.com/repos/.../hooks/67890",
  "events": ["pull_request", "push"],
  "config": {
    "url": "https://www.openlibing.com/gateway/openlibing-coderepo/webhookEvent/hooks/github",
    "content_type": "json",
    "secret": "***"
  }
}
```

> 注意：github 响应中顶层 `url` 是 API 资源 URL（非 webhook 回调 URL），回调 URL 在 `config.url` 下。识别 coderepo webhook 时需用 `config.url` 而非顶层 `url`。当前代码 `RepoWebhook.url` 映射的是顶层 `url`，对 github 而言是 API URL，不等于回调 URL。

> **实现提醒**：github webhook 的回调 URL 识别与迁移需读取 `config.url`。现有 `RepoWebhook.url` 字段对 github 不能直接用于匹配 coderepo 回调 URL，实现时需在 github 分支中改用 `webhook.getConfig().getUrl()` 判定。

## 5. 性能设计

### 5.1 定时任务执行规模

`refreshWebhookHandler` 全量执行时遍历所有未配置 webhook 的代码仓（实际为所有 coderepo 接入仓库）。单仓库处理耗时主要消耗在平台 API 调用：

| 步骤 | API 调用 | 次数 |
|------|---------|------|
| `getRepoWebhookList` | GET 平台 webhook 列表 | 1 |
| `cleanBetaWebhooks` | DELETE beta webhook（按需） | 0~N |
| `cleanDuplicateLegacyWebhooks` | DELETE 多余旧 webhook（按需） | 0~N |
| `updateRepoWebhookUrl`（新增） | PATCH 更新 URL | 0 或 1 |
| `ensureCoderepoWebhookPushEventSubscribed` | GET webhook 列表 + PATCH（按需） | 1 + 0~1 |

单仓库迁移场景（存量 webhook 需迁移 URL）较改造前多 1 次 PATCH 调用，耗时增加可忽略（百毫秒级）。

### 5.2 并发与锁

- 现有 `refreshSingleRepoWebhook` 已按 `repoId` 加锁（`repoLockMap`），保证单仓库串行处理，本需求沿用。
- 平台 API 调用为串行，无新增并发压力。
- 多仓库间并发由 `asyncTaskExecutor` 线程池控制，线程池大小不变。

### 5.3 APIG 限流配置

- APIG 流控策略建议单接口 100 QPS（按实际压测调整），绑定到 3 个 API。
- coderepo 侧 webhook 接口本身为「接收 + 投递 MQ」轻量逻辑，MQ 异步消费，接口侧不会成为瓶颈。
- 平台 webhook 触发频率远低于 100 QPS，限流策略主要兜底异常重试场景。

### 5.4 平台 API 限流容忍

- gitee / gitcode / github 平台对 webhook 管理类 API（list/create/update/delete）有自身限流。
- 全量迁移时单仓库仅多 1 次 PATCH，不会触及平台限流阈值。
- 若仓库规模超大（>1 万），建议通过 `projectId` 参数分批迁移，避免单次任务执行过久。

### 5.5 日志量

- 迁移成功日志：每仓库 1 条 info（`migrated coderepo webhook url`）。
- 跳过日志：每仓库 1 条 info（`already migrated` 或 `legacy webhook already exist`）。
- 失败日志：每失败 1 条 warn，含 platform/org/repo/webhookId/statusCode，便于排查。

## 6. API 接口设计

### 6.1 coderepo webhook 接口（后端）

后端 Controller 共 8 个接口（3 个新建 APIG 专用 + 5 个旧接口保留观察）。详见 1.2 节。

**新增 3 个 APIG 专用接口**：

| # | 接口路径 | 平台 | 说明 |
|---|---------|------|------|
| 1 | `POST /webhookEvent/apig/hooks/gitcode` | gitcode | 新增，APIG 后端路径指向此接口 |
| 2 | `POST /webhookEvent/apig/hooks/gitee` | gitee | 新增，APIG 后端路径指向此接口 |
| 3 | `POST /webhookEvent/apig/hooks/github` | github | 新增，APIG 后端路径指向此接口 |

**保留 5 个旧接口（仅增加日志，观察期后废弃）**：路径与入参不变，详见 1.2 节。

> 新旧接口的核心处理逻辑（签名校验、MQ 投递）抽取为公共方法复用，无代码重复。

### 6.2 APIG API 配置（非代码，运维操作）

每个 API 按下表配置：

| 配置项 | 值 |
|--------|------|
| 请求方式 | POST |
| 安全认证 | 无认证 |
| 请求协议 | HTTPS |
| 前端路径 | 见下表 |
| 后端路径 | 见下表（指向新建的 APIG 专用接口） |
| 后端服务 | openlibing-coderepo 服务地址 |

**APIG 发布的 3 个 API（后端指向新接口）**：

| # | 前端路径（APIG 对外） | 后端路径（转发到 coderepo 新接口） |
|---|---------------------|---------------------------------|
| 1 | `/coderepo/webhook/hooks/gitcode` | `/webhookEvent/apig/hooks/gitcode` |
| 2 | `/coderepo/webhook/hooks/gitee` | `/webhookEvent/apig/hooks/gitee` |
| 3 | `/coderepo/webhook/hooks/github` | `/webhookEvent/apig/hooks/github` |

> **关键**：APIG 后端路径指向新建的 `/webhookEvent/apig/hooks/{platform}`，与旧接口 `/webhookEvent/hooks/` 物理隔离。这样：
> - webhook URL 已迁移到 APIG 的流量 → APIG 转发到新接口 → 日志 `path=apig`
> - webhook URL 未迁移（仍指向旧直连 URL）的流量 → 直连后端旧接口 → 日志 `path=direct` 或 `path=legacy-with-repoId`
>
> 通过日志统计接口路径即可 100% 判断迁移状态，无需依赖请求头，无需逐仓确认 webhook URL。

### 6.3 APIG 访问控制策略（IP 白名单）

- **策略类型**：IP 地址访问控制 → 允许访问
- **IP 白名单**：填入 gitcode / gitee / github 的出口 IP 段（由各平台官方文档提供，运维维护）
- **绑定**：将策略绑定到上述 3 个 API

### 6.4 APIG 流控策略（可选）

- **限流维度**：按 API 限流，建议单接口 100 QPS（按实际压测调整）
- **绑定**：将策略绑定到上述 3 个 API

### 6.5 APIG 发布

- 将 3 个 API 发布到生产环境（发布后对外可调用）
- 记录 APIG 对外访问域名（形如 `https://<apig-host>/coderepo/webhook/hooks/{platform}`），供代码侧 Apollo 配置使用

### 6.6 平台 webhook PATCH 接口（代码侧调用）

`updateRepoWebhookUrl` 调用的平台 API，复用现有 `*_WEBHOOK_UPDATE_URL` 常量：

| 平台 | PATCH URL | 请求头 | body |
|------|-----------|--------|------|
| gitee | `https://gitee.com/api/v5/repos/{org}/{repo}/hooks/{hookId}` | `PRIVATE-TOKEN: <token>` | `{"url": "<newUrl>"}` |
| gitcode | `https://api.gitcode.com/api/v5/repos/{org}/{repo}/hooks/{hookId}` | `PRIVATE-TOKEN: <token>` | `{"url": "<newUrl>"}` |
| github | `https://api.github.com/repos/{org}/{repo}/hooks/{hookId}` | `Authorization: Bearer <token>` + `Accept: application/vnd.github+json` | `{"config": {"url": "<newUrl>", "content_type": "<原值>", "secret": "<原值>"}}` |

- 响应 200 视为成功；非 200 记录 warn 并返回 false。
- 与 `updateRepoWebhookForPushEvent` 共用同一 PATCH URL，仅 body 不同。

## 7. 安全设计

### 7.1 网络层（APIG IP 白名单）

- 仅 gitcode / gitee / github 出口 IP 段可调用 webhook 接口，非白名单 IP 调用返回 403。
- IP 白名单由运维维护，定期核对各平台官方文档更新。
- 白名单策略绑定到 3 个 API，新增 API 需手动绑定。

### 7.2 网络层（APIG 限流）

- 单接口限流（建议 100 QPS），防止异常重试或恶意刷接口打垮 coderepo 服务。
- 限流策略绑定到 3 个 API。

### 7.3 应用层（webhook 签名校验，不变）

- 5 个 webhook 接口仍通过 [MachineInterfaceAuthUtil.webhookMachineInterfacePermissionAuth](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/utils/MachineInterfaceAuthUtil.java#L71) 校验平台签名头：
  - gitcode：`X-GitCode-Token`
  - gitee：`X-Gitee-Token`
  - github：`X-Hub-Signature-256`
- 签名密钥从 `machine_interface_account` 表读取，`SecurityUtil.decrypt` 解密后使用。
- APIG 无认证不代表应用层无认证，双重保障。

### 7.4 传输层（HTTPS）

- APIG 对外强制 HTTPS，平台到 APIG 链路加密。
- APIG 到后端 coderepo 的链路沿用现有网关 HTTPS 配置。

### 7.5 凭证安全

- `giteeWebhookToken`、`gitcodeWebhookToken` 加密存储于 Apollo，运行时 `SecurityUtil.decrypt(token, part1)` 解密。
- github token 通过 `commonService.getGithubToken` 获取，不复用静态配置。
- `getAccessTokenForWebhook` 优先级：仓库私有 token → 项目级 token → 公共 webhook token，与现有逻辑一致，不降低安全基线。
- PATCH 请求 token 放入请求头（`PRIVATE-TOKEN` / `Authorization: Bearer`），不放入 URL 参数（符合既有约束）。

### 7.6 github webhook config 回填安全

- github PATCH `config` 时必须回填 `content_type`、`secret`，否则会被重置为默认值，导致签名校验失败或 secret 丢失。
- `secret` 从原 webhook `config.secret` 读取（平台返回掩码或原值取决于平台策略），若返回为掩码则 PATCH 时省略 `secret` 字段（平台保留原值）。
- 实现时需验证 github GET hooks 列表返回的 `config.secret` 是否为原值：若为掩码（如 `******`），PATCH body 不传 `secret`，仅传 `url` + `content_type`。

### 7.7 旧接口废弃（阶段 3，后续独立需求）

- 本次需求迁移完成后，5 个旧接口（`/webhookEvent/hooks/` 路径下）仍可被外部嗅探后直调，绕过 APIG 白名单。
- 阶段 2 观察期通过后（见 1.7 节），在阶段 3 执行以下加固：
  - 删除 `WebHookEventController` 中 5 个旧接口的 `@PostMapping` 方法（`/hooks/{platform}` 与 `/hooks/{platform}/{repoId}`）
  - 网关层封禁 `/webhookEvent/hooks/` 直连路径（如仍需要）
  - 清理流量来源日志辅助方法（如不再需要区分来源）
- 阶段 3 作为独立小需求交付，不在本次需求范围内。

### 7.8 风险与对策汇总

| 风险 | 对策 |
|------|------|
| APIG URL 配置错误导致全部 webhook 失效 | Apollo 配置变更后先在单仓库（`repoId` 参数）验证，再全量执行 |
| github PATCH `config` 丢失 `content_type`/`secret` | 实现时先读原 webhook `config`，连同 `url` 一起回填；`secret` 为掩码时不传 |
| 存量 webhook 迁移期间事件丢失 | 采用 PATCH 就地更新（非删除重建），webhook id 不变，中间态窗口最小 |
| gitcode/gitee/github 出口 IP 段变更 | IP 白名单由运维定期核对各平台官方文档更新 |
| 含 repoId 旧路径 webhook 迁移遗漏 | Controller 代码暂保留作为兜底；全量迁移后通过日志核对遗漏仓库并补迁 |
| 旧直连 URL 被外部嗅探后绕过 APIG 直调 | 后续在网关层封禁 `/webhookEvent/hooks/` 直连路径（本需求不含） |
| 平台 token 失效导致 PATCH 失败 | `getAccessTokenForWebhook` 多级回退；PATCH 失败仅记录 warn，不影响其他仓库迁移 |

## 8. 验收标准

### 8.1 非代码（APIG 侧）

- [ ] 3 个 API 已创建（gitcode / gitee / github 各 1 个，不含 repoId），请求方式 POST、无认证、HTTPS。
- [ ] APIG 后端路径指向新建的 `/webhookEvent/apig/hooks/{platform}`（不是旧路径 `/webhookEvent/hooks/`）。
- [ ] 未发布含 `{repoId}` 的 API（确认 APIG 侧无对应 API）。
- [ ] IP 白名单策略已绑定到 3 个 API，仅 gitcode/gitee/github 出口 IP 可通过。
- [ ] 非白名单 IP 调用返回 403。
- [ ] 流控策略已绑定（如配置）。
- [ ] 3 个 API 已发布到生产环境。

### 8.2 代码（定时任务迁移）

- [ ] Apollo 配置 `openlibing.coderepo.webhook.url` 已改为 APIG URL（不含 repoId）。
- [ ] 新录入代码仓（无 webhook）：`refreshWebhookHandler` 执行后，平台侧新建 webhook 的 URL 为 APIG URL（不含 repoId）。
- [ ] 存量代码仓（webhook 指向旧直连 URL，不含 repoId）：`refreshWebhookHandler` 执行后，平台侧 webhook 的 URL 被更新为 APIG URL，webhook id 保留不变。
- [ ] 存量代码仓（webhook 指向含 repoId 的旧路径）：`refreshWebhookHandler` 执行后，平台侧 webhook 的 URL 被更新为 APIG URL（不含 repoId），webhook id 保留不变。
- [ ] 全量执行后，平台侧所有 coderepo webhook 的 URL 均不含 `{repoId}`，统一为 `https://<apig-host>/coderepo/webhook/hooks/{platform}`。
- [ ] 已迁移的代码仓再次执行 `refreshWebhookHandler`：跳过，不重复 PATCH。
- [ ] local/beta 环境：不执行迁移，沿用现有 `cleanBetaWebhooks` + 创建逻辑。
- [ ] github webhook 迁移后 `content_type`、`secret` 等原配置不丢失。
- [ ] 迁移后 `ensureCoderepoWebhookPushEventSubscribed` 仍能正常补齐 push 事件订阅。

### 8.3 代码（新接口与流量来源日志）

- [ ] 新增 3 个 APIG 专用接口 `/webhookEvent/apig/hooks/{platform}`，核心逻辑复用公共处理方法，无代码重复。
- [ ] 5 个旧接口方法入口处均调用 `logWebhookSource`，记录 `platform` / `path` 两字段。
- [ ] 新接口日志中 `path=apig`。
- [ ] 旧接口（不含 repoId）日志中 `path=direct`。
- [ ] 旧接口（含 repoId）日志中 `path=legacy-with-repoId`。

### 8.4 端到端

- [ ] gitcode/gitee/github 触发 push / pull request 事件 → APIG 放行 → coderepo 新接口收到并投递 MQ → 消费处理成功。
- [ ] coderepo 日志中对应请求 `path=apig`。
- [ ] 非白名单 IP 模拟调用 → APIG 拦截，coderepo 无日志。

### 8.5 观察期验收（阶段 2，本次需求交付后 1-2 周）

> 观察期验收不在本次需求交付范围，作为后续废弃旧接口（阶段 3）的前置条件。

- [ ] 观察期内新接口（`path=apig`）流量正常，与平台事件触发频率匹配。
- [ ] 观察期内旧接口（`path=direct`）流量为 0（说明无 webhook 直连后端旧路径）。
- [ ] 观察期内旧接口（`path=legacy-with-repoId`）流量为 0（说明无 webhook 直连后端含 repoId 旧路径）。
