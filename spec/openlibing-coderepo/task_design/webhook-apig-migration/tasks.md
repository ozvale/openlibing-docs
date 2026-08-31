# Webhook 接入 APIG 并下线废弃 hooks 接口 — 实现任务

## 进度: 3/3 complete

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

### 阶段 4（#153 内，「下线机机接口账号相关四表」）— complete

- [x] `WebhookAuthUtil` 移除账号表校验（`queryMachineInterfaceAccountByAccountId`）与机机日志
      （`machineInterfaceLog`），签名密钥改读 Apollo `webhook.secretKey`
- [x] `RepoServiceImpl.resolveWebhookSign` 由查账号表改为解密 Apollo 密钥，移除 `webhookDescription` 字段与
      `MachineInterfaceAccountMapper` 注入
- [x] `WebHookEventController` 移除 3 处 `machineInterfaceLog(request)` 调用
- [x] 删除机机四表相关代码：`MachineInterfaceAuthMapper` / `MachineInterfaceAccountMapper`（含 XML）、
      `MachineInterfaceEntity` / `MachineInterfaceAccountEntity` / `MachineInterfaceLogEntity`、
      `MachineInterfaceConstants`、`MachineInterfaceAuthMapperTest` / `MachineInterfaceAccountMapperTest`
- [x] 重写 `WebhookAuthUtilTest`，`RepoServiceImplTest` 移除账号 mapper 引用
- [x] 编译通过、相关单测通过、pre-commit 检查通过，提交推送（commit `7323f03`）
