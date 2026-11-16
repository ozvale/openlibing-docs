# #141 — 实现任务

## 进度: 3/3 complete

- [x] Task 1: 删除 `DashboardReportController`（`POST /dashboard/backfill` 端点）与 `DashboardBackfillRequest` / `DashboardBackfillTaskStatus`（`5cbfa2ba`）
- [x] Task 2: 删除 `DashboardBackfillService`（内存任务表 + 异步逐日补录），确认 `DashboardReportSchedule` 不受影响（`5cbfa2ba`）
- [x] Task 3: 全仓检索残留引用（`DashboardBackfill` 零命中）并交付 commit（`5cbfa2ba`）

## 交付记录

| commit     | 日期       | 标题                                                                    | 关联 |
| ---------- | ---------- | ----------------------------------------------------------------------- | ---- |
| `5cbfa2ba` | 2026-11-05 | chore(analysis): remove unused /dashboard/backfill endpoint and helpers | —    |

- 分支：`ms_scan`（`openlibing-sca`）
- 说明：commit message 未带 `Refs #141`（该 issue 以「下线接口」方式闭环，非补鉴权）。
- 验证方式（代码内证据）：
  - 删除统计：4 文件、353 行删除（`git show --stat 5cbfa2ba`）
  - 残留检索：`DashboardBackfill` 在 `src/` 无命中；`DashboardReportSchedule` 仍存在且含 `@Scheduled(cron = "${job.cron.dashboard.report.task:0 0 1 * * ?}")`
  - 本轮为回溯补写文档，未执行 `mvn test`（编译/测试通过性未验证）
- 未覆盖：统一 RBAC 门禁（见 `shield-role-api-authz`）、外部调用方下线确认、历史补录替代方案
