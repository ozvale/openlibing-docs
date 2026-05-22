# batch-approval — 技术设计

## 方案概述
在 `AiToolApplicationRecordService` 中新增 `approveApplicationsBatch` 方法，
接收 `List<Long> ids` + `action` + `remarks`，遍历执行与单条审批一致的逻辑，
收集每条处理结果后汇总返回。

## 架构决策

### DTO 设计
- 新增 `BatchApprovalRequestDTO`，字段：`List<Long> ids`、`String action`、`String remarks`
- 返回结果新增 `BatchApprovalResultDTO`，字段：`Long id`、`String status`（SUCCESS/SKIPPED/FAILED）、`String message`

### 审批逻辑复用
- 每条记录的审批逻辑与现有 `approveApplication` 保持一致
- 区别：不再每条都抛异常阻断，改为记录失败并继续处理下一条

### 关键设计决策
| 决策点 | 选择 | 原因 |
|--------|------|------|
| 失败是否阻断后续 | 不阻断，记录错误继续 | 批量操作不应因一条失败而全部回滚 |
| action 是否支持混合 | 不支持，统一 action | 需求确认为统一操作模式 |
| 返回结构 | 逐条结果 + 汇总 | 审批人需要知道每条记录的具体处理结果 |
| 事务 | 无事务，逐条提交 | 与现有单条审批行为一致 |

## 涉及文件
| 文件 | 操作 | 说明 |
|------|------|------|
| `api/dto/BatchApprovalRequestDTO.java` | 新增 | 批量审批请求 DTO |
| `domain/aitool/service/AiToolApplicationRecordService.java` | 修改 | 新增 `approveApplicationsBatch` 方法 |
| `test/.../service/AiToolApplicationRecordServiceTest.java` | 修改 | 新增批量审批测试用例 |

## 风险 & 缓解
| 风险 | 缓解 |
|------|------|
| 大批量 ID 可能导致处理时间过长 | 建议前端限制单次批量数量（如 ≤50），后端不做硬限制但记录日志 |
| 部分成功后状态不一致 | 返回详细结果让调用方知晓，与现有逐条操作行为一致 |
