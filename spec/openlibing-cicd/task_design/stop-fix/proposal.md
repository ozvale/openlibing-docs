# 黄蓝协同 stop 接口修复 — 需求背景与验收标准

## 需求背景

黄蓝协同流水线在执行 stop（停止）操作时，原接口存在以下问题：

1. **重复提交被去重拦截**：stop 操作复用了 start 的提交链路，`BlueYellowPipelineServiceImpl#checkDuplicateAndTimeout` 在检测到已存在相同 `blueRecordId + blueRecordTaskId` 的记录时会拒绝提交，导致同一流水线任务无法发起停止操作。
2. **缺少黄区执行记录定位字段**：stop 操作需要让黄区精确定位"要停止哪条执行记录"，但原 DTO/VO/Mapper 缺少 `yellowRecordId` 字段，黄区无法区分本次 stop 对应哪一条黄区执行记录。
3. **复用 start 的 reset 逻辑会清空关键定位字段**：原有 `resetForRetry` 在重置时会清空 `yellow_record_id / start_time / end_time / yellow_pipeline_url`，对 stop 场景不适用——stop 必须保留这些字段供黄区定位。
4. **stop 对不存在的记录静默成功**（检视阶段发现）：`exist == null` 时对所有 actionType 统一返回 `success("new", false)`，stop 对无记录任务会继续走 `saveOrResetRecord`（UPDATE 0 行静默无效）→ `dispatchMqsMessage`（发孤儿 stop 指令）→ `handleMqsResult`（UPDATE 0 行但返回 success），调用方误判 stop 已生效。

## 期望行为

- stop 操作允许复用已存在的 task 记录，不被去重逻辑拦截。
- stop 重置记录时仅更新 `status / mqs_send_time / fail_message / action_type`，保留 `yellow_record_id` 等黄区定位字段。
- MQS payload 透传 `yellowRecordId`，黄区消费时据此定位需停止的执行记录。
- 查询接口 `CrossRegionQueryVO` 返回 `yellowRecordId`，便于后续状态跟踪。
- stop 对不存在的记录直接返回失败，不下发无效 MQS 消息。

## 验收标准

- [ ] 同一 `blueRecordId + blueRecordTaskId` 在流水线运行中发起 stop 操作，能成功提交并下发到黄区。
- [ ] stop 操作不影响后续 start/retry 的正常去重逻辑。
- [ ] 黄区收到的 MQS 消息中包含 `yellowRecordId`，可据此定位需停止的执行记录。
- [ ] 查询接口返回 `yellowRecordId` 字段。
- [ ] stop 后再次发起 start 时仍能正常创建新记录。
- [ ] stop 对不存在的 `blueRecordId + blueRecordTaskId` 返回失败，不下发 MQS。

## 影响范围

- 模块：`cross-region`（黄蓝协同）
- 接口：黄蓝协同 start/stop 接口
- 数据库：无 schema 变更（`yellow_record_id` 字段已存在，仅 mapper 补充查询）
- 部署：无特殊影响
- 安全：无鉴权/凭证/输入校验变更

## 关联

- 业务 Issue: openlibing/openlibing-cicd#137
- 业务 PR: openlibing/openlibing-cicd!413 (merged)
