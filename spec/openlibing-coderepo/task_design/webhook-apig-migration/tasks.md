# Webhook 接入 APIG 并下线废弃 hooks 接口 — 实现任务

## 进度: 2/2 complete

### 阶段 1（#143，「机机接口下线切换 apig」）— complete

- [x] `WebHookEventController` 新增 3 个 APIG 专用接口 `/apig/webhook/{platform}/repo`
- [x] 抽取 `handleGitCodeWebhook` / `handleGiteeWebhook` / `handleGithubWebhook` 公共方法，旧接口共用
- [x] 新增流量来源日志 `logWebhookSource`（apig / direct / legacy-with-repoId）
- [x] `RepoWebhook` 实体新增 `config` 字段及 `RepoWebhookConfig` 内部类，`secret` 加 `@ToString.Exclude`
- [x] `RepoServiceImpl` 拆分 `autoSetCoderepoWebHook`，新增 `LEGACY_CODEREPO_WEBHOOK_URL_MARKER`、
      `migrateLegacyCoderepoWebhooks`、`updateRepoWebhookUrl`、`buildWebhookUrlUpdateBody`
- [x] `refreshWebhookHandler` 运行时把存量 webhook URL（含 repoId 旧路径 + 旧直连 URL）PATCH 迁移到新 APIG 链接
- [x] 网关 WebhookAuthFilter 放行 `/apig/webhook/` 前缀
- [x] 华为云 APIG 发布 3 个 API + IP 白名单 + 流控策略（运维）

### 阶段 3（#153，「移除废弃的 legacy webhook hooks 接口」）— complete

- [x] 删除 5 个旧直连接口：`/webhookEvent/hooks/gitcode`、`/webhookEvent/hooks/gitcode/{repoId}`、
      `/webhookEvent/hooks/gitee`、`/webhookEvent/hooks/gitee/{repoId}`、`/webhookEvent/hooks/github`
- [x] 清理相关无用方法、多余 `@PathVariable` / `StringUtils` 引用
- [x] `WebHookEventControllerTest` 旧接口用例替换为 APIG 入口用例
- [x] 编译通过（`mvn -T 4 -DskipTests compile`），单测通过，pre-commit 检查通过
- [x] 提交推送并创建业务 PR（openlibing/openlibing-coderepo#153）