# Webhook 接入 APIG（白名单 + 限流）并下线废弃 hooks 接口

## 需求背景

当前 5 个 webhook 接口（gitcode / gitee / github，含 2 个带 `{repoId}` 的兼容路径）直接暴露在
`openlibing-coderepo` 网关路径下，存在以下风险：

- **来源不可控**：无 IP 白名单，无法限制只有代码托管平台出口 IP 能触发。
- **无限流**：恶意或异常重试可能打垮 coderepo 服务。
- **暴露 DB 主键**：`{repoId}` 出现在 URL 中，存在信息泄露风险。
- **认证偏弱**：webhook 签名校验仅在应用层，网络层无前置过滤。

为收敛风险，将 webhook 事件接口整体前置到华为云 APIG，利用 APIG 的 IP 白名单 + 限流能力，并在迁移彻底后
下线遗留的旧直连接口。

## 功能描述

**做什么（两个交付阶段）**

- 阶段 1（#143，「机机接口下线切换 apig」）：新增 3 个 APIG 专用后端接口，改造 `refreshWebhookHandler`
  定时任务，把存量 webhook 链接（含 `{repoId}` 旧路径 + 旧直连 URL）统一 PATCH 迁移到不含 `repoId` 的新
  APIG 链接；旧接口保留并增加流量来源日志用于观察期统计。
- 阶段 3（#153，「移除废弃的 legacy webhook hooks 接口」）：观察期通过后，彻底删除 5 个旧直连 hooks 接口
  及其相关无用方法，webhook 事件流量全部收敛到 APIG 专用入口 `/apig/webhook/{platform}/repo`。
- 阶段 4（#153 内：「下线机机接口账号相关四表」）：webhook 前置 APIG 后，机机接口账号/日志能力随之下线，
  清理 `machine_interface`、`machine_interface_account`、`machine_interface_log`、`machine_interface_permission`
  四张表相关代码，webhook 签名校验密钥与 webhook 创建签名密钥统一改读 Apollo 配置
  `webhook.secretKey`。

**不做什么**

- 不改动 webhook 事件处理核心逻辑（签名校验、头部提取、MQ 投递）。
- 不改动平台侧 webhook 配置数据结构本身，仅迁移 URL。
- 不新增除 APIG 之后的「第二个后端直连入口」。

## 验收标准

- [ ] `/webhookEvent/hooks/*` 5 个旧直连接口已从代码删除，不再对外暴露。
- [ ] 3 个新 APIG 专用接口 `/apig/webhook/{platform}/repo` 正常接收并处理 gitcode / gitee / github 事件。
- [ ] 存量 webhook URL 全部迁移到不含 `repoId` 的新 APIG 路径，含 `{repoId}` 的地址不再被平台调用。
- [ ] 单测用例由旧接口替换为新 APIG 入口，编译与测试通过。
- [ ] 机机接口账号相关的 `machine_interface` / `machine_interface_account` / `machine_interface_log` /
      `machine_interface_permission` 四表相关 mapper / 实体 / 常量 / XML 已从代码删除。
- [ ] webhook 签名校验与创建均从 Apollo 配置 `webhook.secretKey` 读取密钥，不再依赖机机接口账号表。
- [ ] 移除了机机接口调用日志记录（`machineInterfaceLog`），改由 APIG 接口调用日志承载。

## 影响范围

- 业务仓：`openlibing-coderepo-fork`
  - `WebHookEventController`（新增 APIG 入口、移除旧 hooks 接口、移除机机日志调用）
  - `RepoServiceImpl`（webhook URL 迁移；签名密钥改读 Apollo）
  - `RepoWebhook` 实体（github webhook config 字段）
  - `XxlJobHandler#refreshWebhookHandler`（定时迁移）
  - `WebhookAuthUtil`（移除账号表校验与日志，密钥改读 Apollo）
  - `WebHookEventControllerTest` / `WebhookAuthUtilTest` / `RepoServiceImplTest`
  - 删除机机接口相关文件：`MachineInterfaceAuthMapper`、`MachineInterfaceAccountMapper`（含 XML）、
    `MachineInterfaceEntity` / `MachineInterfaceAccountEntity` / `MachineInterfaceLogEntity`、
    `MachineInterfaceConstants` 及对应 mapper 单测
- 华为云 APIG 控制台（运维配置，非代码）：
  - 3 个 API 前端路径 + 后端指向新接口
  - IP 白名单访问控制策略、流控策略
- 网关：`openlibing-gateway` WebhookAuthFilter 放行 `/apig/webhook/` 前缀
