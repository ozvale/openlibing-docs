# Proposal · 黄蓝协同触发入口插件化改造及存量webhook功能清理

- FE 需求名称：【黄蓝协同】黄蓝协同触发入口插件化改造及存量webhook功能清理
- 日期：2026-11-10（归档 2026-11-11）
- 涉及仓库：`openlibing/openlibing-cicd`（Java，蓝区触发接口）、`openlibing/pr-sync-action`（TypeScript，蓝区 action 插件）、黄区 MQS 消费端（契约约定）
- 关联 Issue：
  - https://gitcode.com/openlibing/openlibing-cicd/issues/517
  - https://gitcode.com/openlibing/pr-sync-action/issues/29
- 开发分支：两仓 `feat-pr-sync-trigger-events`（action HEAD: d7feb27）

## 需求背景

原设计中 PR 事件的同步触发时机写死在服务端：创建 PR / 推提交经服务端 webhook 自动触发 PR 同步，插件仅轮询打标签。用户需要触发时机由使用方按需控制（例如创建 PR 不触发、评论单独触发），触发入口必须插件化、可配置。

## 改造方向（v2 统一触发模型）

- 事件入口唯一开关 = 流水线 workflow 的 `on` 监听配置；监听了什么事件，什么事件就触发同步。
- action 插件与 openlibing-cicd **零事件语义**：不关注事件类型，收到即透传（`triggerEvent` 统一词汇：open / reopen / update / merge / comment）。
- 黄区用状态机解释类型并保证可重放（对账类三级对账 / 标记类改 MR 状态）。
- 清理存量服务端 webhook 自动触发链路（创建 PR / 推提交直发）；push webhook 直发链路保留，与插件触发在黄区幂等共存。

## 验收标准

1. 触发同步仅由 workflow `on` 监听配置决定，存量 webhook 自动触发链路已清理。
2. 插件无 `trigger_events` 事件过滤输入；所有命中事件统一链路（触发 → 轮询 → 标签 → 终态输出），无旁路。
3. `triggerEvent` 缺省等价 comment；非法值参数错误且不发 MQS、不产生流水线记录。
4. cicd 幂等窗口命中返回既有 msgId（判定先于限流）；60 秒 PR 维度限流，Redis 异常 fail-open。
5. 全 action 统一插 `yellow_region_pipeline` 记录（START/WAIT_START）并绑定 msgId；MQS 发送失败记录置 FAILURE、释放限流占位。
6. MQS 消息不携带 access_token；触发接口经 OIDC 认证；account 记录真实触发人。
