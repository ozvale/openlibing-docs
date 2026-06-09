# PR 合入门禁触发与 pipeline_status 回调

## 需求背景
openlibing-cicd 需要支持 PR 合入全流程的门禁触发机制：
1. 蓝区脚本通过独立接口触发黄区门禁流水线（替代人工在 webhook 评论区发 `compile#openlibing`）
2. 黄区门禁完成后通过 webhook 回调 `pipeline_status` 作为执行结果，避免轮询

## 功能描述

### 接口一：POST /cross-region/compile
- 接收 `CompileTriggerReqDTO`，内含 org/repo/pr/分支等完整 PR 信息
- 创建/重用 `gitee_pr_info` 记录
- 写入 `yellow_region_pipeline`（status=START）
- 构造 MQS 消息发送到黄区
- 添加 SC-START 标签

### 接口二：PUT /cross-region/pipeline-status
- 接收黄区回传的 GitCode Merge Request Webhook JSON（含 `pipeline_status` 字段）
- 提取 `pipeline_status` 作为门禁流水线最终执行结果
- 更新 `yellow_region_pipeline` 状态
- 不打标签，`pipeline_status` 不入库

### CrossRegionStartReqDTO 扩展
- 新增 `actionType`（操作类型）、`executeSchemeName`（执行方案名称）
- 完整链路：DTO → BlueYellowPipeline Entity → MQS Payload → DB

## 验收标准
- [ ] POST /cross-region/compile 可触发黄区门禁流水线
- [ ] PUT /cross-region/pipeline-status 正确解析 pipeline_status 并更新状态
- [ ] actionType/executeSchemeName 完整落库并通过 MQS 传递
- [ ] 不打标签、不存 pipeline_status
- [ ] 所有 64 个测试通过

## 影响范围
- `openlibing-cicd` 业务仓
- 涉及模块：cross-region（黄蓝协同）、blue-yellow-pipeline（新架构）
