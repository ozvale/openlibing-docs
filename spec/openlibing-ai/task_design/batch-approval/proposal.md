# AiToolApplicationRecordService 新增批量审批功能

## 需求背景
当前 `AiToolApplicationRecordService.approveApplication` 方法仅支持逐条审批。
审批人需要对每条待审批记录逐一操作，当待审批记录较多时操作效率低下。

## 功能描述
新增批量审批接口，支持一次性对多条申请记录执行统一的审批操作（全部通过/全部拒绝），
共用一条审批备注。

### 做什么
- 新增 `approveApplicationsBatch` 方法，接收 ID 列表 + 统一 action + 统一 remarks
- 遍历每条记录执行审批逻辑，与现有单条审批保持一致
- 返回每条记录的处理结果（成功/跳过/失败及原因）

### 不做什么
- 不支持每条记录独立设置不同 action 或 remarks
- 不修改现有 `approveApplication` 单条审批方法
- 不新增数据库表或字段

## 验收标准
- [ ] 新增批量审批接口 `approveApplicationsBatch`，接收 ID 列表 + 统一 action + 统一 remarks
- [ ] 校验每条记录申请状态为 `PENDING`，非 PENDING 状态的记录返回跳过提示
- [ ] `APPROVED` 时检查每条记录对应社区工具余量
- [ ] 记录审批人工号和审批时间/拒绝时间
- [ ] 返回每条记录的处理结果（成功/跳过/失败及原因）
- [ ] 对应单元测试覆盖主要场景

## 影响范围
- `AiToolApplicationRecordService.java` — 新增 `approveApplicationsBatch` 方法
- 新增 `BatchApprovalRequestDTO.java` — 批量审批请求 DTO
- `AiToolApplicationRecordServiceTest.java` — 新增测试用例

## 关联 Issue
openlibing/openlibing-ai#41
