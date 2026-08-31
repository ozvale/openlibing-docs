# Webhook 接入 APIG 并下线废弃 hooks 接口 — 归档

## 关联

- 业务 PR #143（阶段 1 迁移上线）：https://gitcode.com/openlibing/openlibing-coderepo/pull/143
- 业务 PR #153（阶段 3 移除废弃 hooks 接口 + 阶段 4 下线机机四表）：https://gitcode.com/openlibing/openlibing-coderepo/pull/153
  - 提交 `d89bff5`：`refactor(webhook): remove deprecated legacy webhook endpoints`（阶段 3）
  - 提交 `7323f03`：`refactor(webhook): 下线机机接口四表，webhook 鉴权改读 Apollo 密钥`（阶段 4）
- docs PR：本 PR（合并本归档文档）

## 交付历程

- #143（阶段 1）：新增 3 个 APIG 专用接口 `/apig/webhook/{platform}/repo`，抽取公共处理方法，新增
  `logWebhookSource` 流量来源日志；`RepoServiceImpl` 拆分 `autoSetCoderepoWebHook` 并新增
  `migrateLegacyCoderepoWebhooks` / `updateRepoWebhookUrl` / `buildWebhookUrlUpdateBody`；
  `RepoWebhook` 新增 `config` + `RepoWebhookConfig`；`refreshWebhookHandler` 定时迁移存量 webhook URL 到不含
  repoId 的 APIG 链接；5 个旧接口保留并增加来源日志用于观察期统计。
- #153（阶段 3）：观察期通过后删除 5 个旧直连 `/webhookEvent/hooks/*` 接口（gitcode / gitee / github，含 2 个
  `{repoId}` 兼容路径）及相关无用方法、多余引用；`WebHookEventControllerTest` 旧接口用例替换为 APIG 入口用例。
- #153（阶段 4）：webhook 前置 APIG 后，机机接口账号/日志能力随之下线。`WebhookAuthUtil` 移除账号表
  校验与机机日志（`machineInterfaceLog`），签名密钥改读 Apollo `webhook.secretKey`；
  `RepoServiceImpl.resolveWebhookSign` 由查账号表改为解密 Apollo 密钥，并移除 `webhookDescription` 字段与
  `MachineInterfaceAccountMapper` 注入；`WebHookEventController` 移除 3 处机机日志调用；删除
  `machine_interface` / `machine_interface_account` / `machine_interface_log` / `machine_interface_permission`
  四表相关 mapper / 实体 / 常量 / XML 及对应 mapper 单测。
- #153（阶段 4 补充）：消除 `MachineInterface` 残留语义，签名鉴权工具类 `MachineInterfaceAuthUtil` 重命名为
  `WebhookAuthUtil`（测试类同步为 `WebhookAuthUtilTest`），方法 `webhookMachineInterfacePermissionAuth` 精简为
  `webhookAuth`；仓库内已无任何 `MachineInterface` 语义（commit `58d47d0`）。

## 用户自测反馈

- 无（阶段 3 为纯删除 + 用例替换，编译与 pre-commit 通过后直接交付）。
- 阶段 4 经评估确认除既定 3 点（账号校验、secretKey 改 Apollo、日志去除）外，`RepoServiceImpl.resolveWebhookSign`
  同样依赖机机账号表，一并改为 Apollo 并清理，未涉及其他遗漏点。

## 最终验证

- 编译：`mvn test-compile` 通过。
- 单元测试：`WebHookEventControllerTest`、`WebhookAuthUtilTest`、`RepoServiceImplTest` 通过（共 159 项）。
- pre-commit 检查通过（spotless / checkstyle / spotbugs / pmd / gitleaks）。

## 设计偏差与取舍

- 阶段 3 前，需求设计文档中 APIG 路径曾记为 `/webhookEvent/apig/hooks/{platform}`；最终实施统一为
  `/apig/webhook/{platform}/repo`（见 `proposal.md` / `design.md` 的最终验收与架构章节），以实际代码为准。
- 阶段 4 中，`webhook.secretKey` 为 Apollo 配置中心项（与 `security.part1`、
  `gitee.common.access_token` 一致，本地 yaml 不落盘），需运维在 Apollo 配置 AES 加密后的密钥，运行时
  `SecurityUtil.decrypt(key, part1)` 解密；`machine_interface_permission` 表无独立实体/XML，其鉴权逻辑即体现在
  账号查询校验上，随账号表清理一并覆盖。

## 可复用经验

- webhook 类接口迁移到 APIG 采用「分阶段：迁移上线 → 观察 → 下线旧接口」策略，通过流量来源日志
  （apig / direct / legacy-with-repoId）100% 量化迁移进度后再删旧接口，避免事件丢失。
- 下线能力（如表）时，除了显式的接口/方法外，还要系统性检索该能力隐式依赖点（如创建侧 `resolveWebhookSign`
  也会读账号表），避免遗漏。
- 无其他需沉淀到 ai_memory 的经验。

## 归档日期

2026-08-29
