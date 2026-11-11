# Tasks · 黄蓝协同触发入口插件化改造及存量webhook功能清理

实现分支：`openlibing/openlibing-cicd`、`openlibing/pr-sync-action` 均为 `feat-pr-sync-trigger-events`

## openlibing-cicd（蓝区触发接口）

- [x] `PrSyncTriggerReqDTO` 增加 `triggerEvent` 可选字段，移除 accessToken（安全要求 #335）
- [x] `resolveTriggerEvent`：空白缺省 comment + trim/lowercase + 白名单校验（open/reopen/update/merge/comment），不做语义决策
- [x] req_type 原样透传进 MQS（`sendPrSyncMessage`），commit_id 随消息下发
- [x] 全 action 统一插 `YellowRegionPipelineEntity` 记录（START/WAIT_START）+ msgId 落库绑定
- [x] 幂等窗口（10 分钟带 msgId 非终态记录返回既有 msgId），判定先于限流
- [x] PR 维度限流（Redis SETNX 60 秒，fail-open，发送失败释放占位）
- [x] 发送失败记录置 FAILURE、返回 failureMessage
- [x] `upsertTriggerPrInfo` PR 元数据补全、`interruptNonTerminalPipeline` 打断旧非终态记录
- [x] 单元测试：v2 透传模型用例（CrossRegionServiceImplTest）、敏感字段用例（SensitiveFieldToStringTest）

## openlibing/pr-sync-action（蓝区 action 插件）

- [x] 删除生命周期旁路（CLOSED/MERGED SEND_OK 即成功）、触发即成功不轮询、trigger_events 过滤输入
- [x] `CANONICAL_TO_TRIGGER_EVENT` 统一词汇映射；CLOSED 事件 skipped 输出
- [x] `buildTriggerRequest`：payload 优先 + PR 详情反查补齐（comment 无 sha 场景）
- [x] commitId 来源接入（ATOMGIT_SHA / GITHUB_SHA / GITEE_COMMIT / payload head sha）
- [x] 统一链路：触发 → Poller 轮询（首延 2 秒）→ running/终态标签回写（去重）→ 终态输出
- [x] 失败输出恢复与 commitId 反查修复（d7feb27）

## 黄区消费端（契约约定，另行排期）

- [x] MQS 消息契约确认（req_type 五词 + commit_id）
- [ ] 黄区状态机三级对账实现（分支 HEAD == commit_id → MR 存在 → 门禁流水线在跑，缺哪补哪，SKIPPED 回执）
- [ ] 标记类（merge）目标 MR 状态置「已合入」幂等实现
- [ ] 存量服务端 webhook 自动触发链路清理下线

## 归档

- [x] spec artifact 落盘（proposal.md / design.md / tasks.md / archive.md）
- [x] docs 仓 PR 归档（关联 openlibing/openlibing-cicd#517）
