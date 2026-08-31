# Webhook 接入 APIG 并下线废弃 hooks 接口 — 技术设计

## 方案概述

将 webhook 事件接口前置到华为云 APIG（IP 白名单 + 限流），存量 webhook URL 分阶段迁移到不含 `repoId`
的新路径 `/apig/webhook/{platform}/repo`；迁移彻底后删除 5 个旧直连 `/webhookEvent/hooks/*` 接口，
所有流量收敛到 APIG 单向入口。

## 架构决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 入口路径 | `/apig/webhook/{platform}/repo`（不含 repoId） | 与旧 `/webhookEvent/hooks/` 物理隔离，易于通过日志 100% 判断迁移状态 |
| 平台标识 | gitcode / gitee / github | 与存量 WebHookEventController 平台枚举一致 |
| 旧接口处置 | 阶段 1 保留加日志，阶段 3 直接删除 | 观察期通过后再下线，避免事件丢失 |
| webhook URL 迁移 | PATCH 就地更新 URL（webhook id 不变） | 中间态窗口最小，平台侧无需重建 |
| github config 回填 | 迁移时回填 `content_type` / `secret` | 避免 PATCH 后被平台重置为默认值导致签名校验失败 |

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `business/controller/WebHookEventController.java` | 修改 | 阶段 1 新增 `apigGitCodeWebhookEvent` / `apigGiteeWebhookEvent` / `apigGithubWebhookEvent`，抽取 `handleGitCodeWebhook` / `handleGiteeWebhook` / `handleGithubWebhook` 公共方法 + `logWebhookSource` 流量来源日志；阶段 3 删除 5 个 `/webhookEvent/hooks/*` 接口及相关多余 import |
| `business/service/impl/RepoServiceImpl.java` | 修改 | 拆分 `autoSetCoderepoWebHook`，新增 `LEGACY_CODEREPO_WEBHOOK_URL_MARKER`、`migrateLegacyCoderepoWebhooks`、`updateRepoWebhookUrl`、`buildWebhookUrlUpdateBody`；阶段 4 `resolveWebhookSign` 由查账号表改为解密 Apollo 密钥，删除 `webhookDescription` 字段与 `MachineInterfaceAccountMapper` 注入 |
| mapper / 实体 / 常量 / XML（机机四表） | 删除 | 阶段 4 删除 `MachineInterfaceAuthMapper` / `MachineInterfaceAccountMapper`（含 XML）、`MachineInterfaceEntity` / `MachineInterfaceAccountEntity` / `MachineInterfaceLogEntity`、`MachineInterfaceConstants` |
| `common/utils/WebhookAuthUtilTest.java` | 修改 | 阶段 4 重写以适配 Apollo 密钥鉴权 |
| `service/impl/RepoServiceImplTest.java` | 修改 | 阶段 4 移除账号 mapper 引用 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 存量 URL 未迁移导致旧接口仍有流量 | 观察期通过两个指标（旧接口零流量、新接口有流量）再进入阶段 3 删除 |
| 迁移后事件丢失 | PATCH 就地更新 3 步（隔离生产分支 / 定时任务 / 日志监控），webhook id 不变 |
| github 签名校验失败 | PATCH 回填 `content_type` + `secret`，`secret` 不落日志 |

## 跨仓影响

- `openlibing-gateway` 的 WebhookAuthFilter 需放行 `/apig/webhook/` 前缀。
- 华为云 APIG 控制台：3 个 API + IP 白名单 + 流控策略（运维配置，非代码）。