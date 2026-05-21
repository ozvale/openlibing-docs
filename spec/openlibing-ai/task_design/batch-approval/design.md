# batch-approval — 技术设计

## 方案概述
在 `AiToolApplicationRecordService` 新增 `batchApprove(List<Long> ids, String action, String remarks, String userId)` 方法。先预检查全部记录，任一条不通过则返回错误明细；全通过后逐条更新。

## 架构决策
- **预检查优先**：避免部分成功部分失败的回滚复杂性
- **复用现有审批逻辑**：每条记录状态更新方式与 `approveApplication` 保持一致
- **不做邮件通知**：批量操作暂不触发邮件，避免邮件风暴

## 涉及文件
| 文件 | 操作 | 说明 |
|------|------|------|
| api/dto/BatchApprovalRequestDTO.java | 新增 | 批量审批请求 DTO（ids + action + remarks）|
| domain/aitool/service/AiToolApplicationRecordService.java | 修改 | 新增 batchApprove 方法 |
| app/AiToolApplicationRecord.java | 修改 | 新增委托方法 |

## 风险 & 缓解
- 批量 ID 过多可能导致长事务 → 建议前端限制单次最多 100 条
- 余量检查基于当前快照，并发场景下可能超发 → 与现有单条审批面临相同问题，不在本次范围
