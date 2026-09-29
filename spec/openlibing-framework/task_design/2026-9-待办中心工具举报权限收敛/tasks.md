# 待办中心工具举报审批权限收敛 — 实现任务

## 进度: 4/4 complete

### Task 1: Controller 接口签名收敛

- [x] `ToolReportController` 待办中心查询接口 `userId` 由 `required = false` 改为 `required = true`
- [x] 新增「维度」参数区分 `pending` / `history` / `all`

### Task 2: Service 权限判定实现

- [x] `ToolReportService` 接口签名同步更新，`userId` 必填 + 维度参数
- [x] `ToolReportServiceImpl.queryReportList` 增加按维度 + 工具管理者判定的早返回分支（非管理者在 `pending`/`history` 维度返回空列表）

### Task 3: 单元测试补充

- [x] `ToolReportServiceImplTest` 新增「非工具管理者 × pending 维度」返回空列表用例
- [x] `ToolReportServiceImplTest` 新增「工具管理者 × pending 维度」返回待审批列表用例

### Task 4: 验证

- [x] `mvn spotless:check test-compile` 通过
- [x] 单元测试全量通过
- [x] PR 合入 `release_20260923_iter2`，head: `m0_47969702:fix_20260923_iter2_zq` → base: `release_20260923_iter2`
