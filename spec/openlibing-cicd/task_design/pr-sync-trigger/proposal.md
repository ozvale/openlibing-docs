# PR 同步触发接口与失败信息展示

FE 需求：【黄蓝协同】黄蓝协同新增映射实时校验及失败信息展示功能

## 需求背景

黄蓝协同（跨仓 PR 同步）链路中，同步失败时缺少结构化的失败信息回传，前端无法实时展示错误码与构建详情；源仓侧同步依赖 webhook 单一触发链路，需要支持 action 插件主动触发同步并补齐源分支等同步要素。

## 功能描述

- pipeline-status 回调新增 extension 扩展字段：支持回写错误码与构建流水线链接
- 新增 PR 同步主动触发接口 `POST /cross-region/pr-sync/trigger`：校验必填参数，支持 gitcode/gitee/github 三平台，中断旧的非终态流水线并创建新记录，返回 msgId
- MQS 消息补充 tgt_branch（源分支）与统一 account 字段，req_type=compile 对齐 coderepo 消费契约
- PR 元数据（gitee_pr_info）按全局 id + 平台补全落库，保证同步状态轮询可见
- action 插件（独立仓）：评论事件主动触发 + 平台 API 反查 PR 全局 id

## 验收标准

- [ ] 触发接口校验必填参数并返回 msgId，流水线记录 WAIT_START 状态可轮询
- [ ] extension 字段正确落库并可经 pipelineInfo 查询展示
- [ ] MQS 发送失败时新流水线记录置为 FAILURE，避免轮询悬挂
- [ ] 单元测试覆盖新增逻辑并通过（CrossRegionServiceImplTest 73 用例）
