# batch-approval — 最终归档

## 关联
- **Issue**: openlibing/openlibing-ai#41
- **PR**: openlibing/openlibing-ai#122
- **Commit**: aeb8c9c
- **分支**: feat/batch-approval → master-mcc-0521（已合入）
- **归档日期**: 2026-05-22

## 变更摘要
在 `AiToolApplicationRecordService` 新增 `batchApprove` 批量审批方法，支持一次性对多条 AI 工具申请记录执行统一的审批操作（APPROVED/REJECTED）。

### 新增文件
- `BatchApprovalRequestDTO.java` — 批量审批请求 DTO
- `BatchApprovalResultDTO.java` — 批量审批结果 DTO（含 BatchApprovalItem）

### 修改文件
- `AiToolApplicationRecordService.java` — 新增 `batchApprove` 方法
- `AiToolApplicationRecordServiceTest.java` — 8 个测试用例

## 验收结果
- [x] 新增批量审批接口 `batchApprove`，接收 ID 列表 + 统一 action + 统一 remarks
- [x] 非 PENDING 状态记录返回失败提示，不阻断后续
- [x] APPROVED 时检查工具余量
- [x] 记录审批人工号和审批/拒绝时间
- [x] 返回 BatchApprovalResultDTO 含逐条结果和汇总计数
- [x] 8 个单元测试覆盖主要场景
