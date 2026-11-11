# Archive · 黄蓝协同触发入口插件化改造及存量webhook功能清理

- 归档日期：2026-11-11
- FE 需求名称：【黄蓝协同】黄蓝协同触发入口插件化改造及存量webhook功能清理
- 关联 Issue：
  - openlibing/openlibing-cicd#517：https://gitcode.com/openlibing/openlibing-cicd/issues/517
  - openlibing/pr-sync-action#29：https://gitcode.com/openlibing/pr-sync-action/issues/29
- 开发分支：两仓 `feat-pr-sync-trigger-events`（action HEAD: d7feb27）
- 本目录文档：[proposal.md](proposal.md) · [design.md](design.md) · [tasks.md](tasks.md)

## 需求回顾

PR 同步触发入口插件化：事件触发与否由流水线 workflow 的 `on` 监听配置唯一决定；action 插件与 openlibing-cicd 零事件语义（收到即透传）；黄区状态机解释类型并保证可重放；清理存量服务端 webhook 自动触发链路。

## 最终实现摘要

- **openlibing-cicd**（蓝区触发接口）：`POST /pr-sync/trigger` 入参 `triggerEvent` 仅白名单校验（open/reopen/update/merge/comment，缺省 comment），req_type 原样透传进 MQS；全 action 统一插 START/WAIT_START 记录并绑定 msgId 落库；10 分钟幂等窗口（在途返回既有 msgId，先于限流）；60 秒 PR 维度限流（Redis SETNX，fail-open）；发送失败置 FAILURE 并释放限流占位。v1 决策逻辑（resolvePrSyncReqType、close/merge 旁路）无残留。
- **openlibing/pr-sync-action**（蓝区插件）：统一链路（触发 → 轮询 → 标签回写 → 终态输出），无生命周期旁路、无 trigger_events 过滤输入；triggerEvent 统一词汇映射（CLOSED skipped，GitHub closed+merged→merge）；commitId 反查补齐（comment 无 sha 走 PR 详情反查，失败退化纯轮询）。
- **黄区契约**：req_type 五词 + commit_id；对账类三级对账、标记类改 MR 状态；两条铁律——重复消息不产生副作用、每条消息必有回执。

## 关键决策沉淀

1. 事件词汇采用统一五词（open/reopen/update/merge/comment），而非 HTML v2 草案的原始 payload action 名：屏蔽 GitCode/Gitee/GitHub 平台差异，全链路词汇一致，黄区契约简单。
2. 幂等与限流职责分离：重复触发由 10 分钟 msgId 幂等窗承接（返回既有 msgId）；限流只防频次（拒绝文案），幂等判定先于限流。
3. merge 事件也统一插流水线记录并进轮询（区别于 v1 旁路），消息有回执、状态可查询，消除非终态滞留。
4. CLOSED 事件插件侧 skipped：关闭语义由 merge / 黄区标记类覆盖，避免无 MR 可同步的无效触发。

## 测试与质量

- 单元测试：`CrossRegionServiceImplTest`（v2 透传模型用例）、`SensitiveFieldToStringTest`（无 accessToken 断言）、action 插件统一链路用例。
- 关键回归点：缺省 triggerEvent 等价 comment；非法值拒绝且不发 MQS；幂等先于限流；merge 也插记录；无 SEND_OK 短路；closed+merged 归一化 merge。

## 遗留事项

- 黄区状态机三级对账与标记类幂等实现（tasks.md 中未勾选项），由黄区消费端仓另行排期。
- 存量服务端 webhook 自动触发链路的清理下线需与黄区/流水线平台协同发布，注意发布顺序（先确认无在途 webhook 触发后再下线）。
- 本机 gitcode CLI 存在企业代理自签名证书导致的 TLS 校验失败问题，临时以 `NODE_TLS_REJECT_UNAUTHORIZED=0` 规避，长期建议配置 `NODE_EXTRA_CA_CERTS` 指向公司根证书。
