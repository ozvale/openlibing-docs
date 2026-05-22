# batch-approval — 实现任务

## 进度: 3/3 complete

- [x] Task 1: 新增 `BatchApprovalRequestDTO.java` — 包含 `List<Long> ids`、`String action`、`String remarks`
- [x] Task 2: 在 `AiToolApplicationRecordService.java` 新增 `batchApprove` 方法 — 批量审批核心逻辑
- [x] Task 3: 在 `AiToolApplicationRecordServiceTest.java` 新增批量审批测试用例（8 个）

## 验证方式
- ⚠️ Maven 测试因制品仓库认证问题无法在本机执行，需在 CI 环境验证
