# batch-approval

## 需求背景
`AiToolApplicationRecordService.approveApplication` 仅支持单条审批，管理员批量操作时需逐条点击，效率低下。

## 功能描述
新增批量审批接口 `batchApprove`，传入多个记录 ID 和统一审批动作，事务性执行（全部成功或全部回滚）。

## 验收标准
- [ ] 支持传入多个 ID + 统一 action（APPROVED/REJECTED）+ remarks
- [ ] 预检查：记录不存在 / 状态非 PENDING / 余量不足 → 返回详细错误明细，不执行任何修改
- [ ] 全部通过预检查后，逐条更新状态并提交
- [ ] 预检查失败时返回每条错误记录的 id + reason

## 影响范围
- 新增 `BatchApprovalRequestDTO`
- 修改 `AiToolApplicationRecordService`（新增 `batchApprove` 方法）
- 修改 `AiToolApplicationRecord`（app 层委托）
