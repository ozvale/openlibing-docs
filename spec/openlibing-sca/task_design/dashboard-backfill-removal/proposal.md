# #141 — /dashboard/backfill 运营看板补录接口缺失授权（接口下线）

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/141
（【安全】【Argus】/dashboard/backfill 运营看板补录接口缺失授权：声明仅超管但匿名/低权限均可触发全量数据补录上报，CWE-862 垂直越权，中危，当前状态 closed）

来源：Argus 扫描批次 `openlibingsca-20261103130601-016`（置信度已验证，可利用性可实际利用）。

主位置：`src/main/java/com/openlibing/sca/analysis/controller/DashboardReportController.java:52`（`backfill`）。

现状（issue 核实结论）：

- `backfill` 仅接收 `@RequestBody DashboardBackfillRequest`，无任何权限注解/身份解析，只做日期范围校验（2021-06-19 ~ 昨天）后直接创建并执行补录任务；
- `DashboardBackfillService` 无权限逻辑，仅按 taskId 防重；任务状态存内存 `ConcurrentHashMap`；
- `DashboardBackfillRequest.userId` 注释称「用于鉴权」，实际仅用于日志，完全信任客户端提交的 userId；
- `catch (PermissionException)` 为不可达死代码，造成「已有权限保护」的假象。

风险与影响：

- 任意匿名/低权限用户可触发 2021-06-19 以来逐日重放统计并上报运营看板，造成向上汇报的运营数据失真；
- 无全局频次/并发限制，可创建任意多个 taskId 并行补录，放大 MySQL/MongoDB/Feign 资源消耗；
- 补录数值由服务端统计生成，攻击者不能直接篡改数值本身，但可反复触发。

## 功能描述

本 issue 采用**接口下线**方案（而非补授权后保留）：

**做什么**：

1. 删除 `POST /dashboard/backfill` 端点及其承载类 `DashboardReportController`（96 行）；
2. 同步删除仅被该链路使用的 `DashboardBackfillService`（154 行，含内存任务表与异步补录循环）、`DashboardBackfillRequest`（30 行）、`DashboardBackfillTaskStatus`（73 行）；
3. 保留 `DashboardReportSchedule` 每日 cron 报表任务（`@Scheduled(cron = "${job.cron.dashboard.report.task:0 0 1 * * ?}")`），其职责为定时上报，不依赖被删类。

**不做什么**：

- 不重建超管校验后保留该接口（issue P0 的另一条路径，本次选择移除攻击面）；
- 不实现 P1 的全局并发/频控与日期区间幂等去重（接口已不存在）；
- 不实现 P2 的补录审计日志与异常调用告警（接口已不存在）；
- 未落地 issue 建议的「统一 RBAC 注解覆盖所有管理类写端点」系统性整改（由 `shield-role-api-authz`（#145）、`open-api-authz-hardening`（#156）等分批承接，本轮未覆盖）；
- 不改动 `DashboardReportSchedule` 的统计口径与上报逻辑。

## 验收标准

> issue 原验收项假设「补校验后保留接口」；本轮为下线方案，验收按「不可达」重述。

- [x] 匿名（无令牌）调用 `POST /dashboard/backfill` 不再可达：Spring 无该路由，返回 404（`DashboardReportController` 已删除，代码内无 `/dashboard/backfill` 映射）
- [x] 低权限账号调用不再可达（同上）
- [x] 超管亦不可调用：接口下线，issue 原「超管调用返回 200 且 taskId 非空」不适用
- [x] 服务端不再存在「信任客户端提交 userId」的补录路径（`DashboardBackfillRequest` / `DashboardBackfillService` 已删除）
- [x] `catch(PermissionException)` 死代码随类删除，userId「用于鉴权」的错误注释一并消失
- [x] 无残留引用：全仓检索 `DashboardBackfill` 无命中（仅剩无关的 `IntegrationApiServiceImpl#backfillPrHeadCommitId`、`ProjectNoticeScan*` 的 notice 回填等）
- [x] 每日看板报表任务保留（`DashboardReportSchedule` 仍存在且带 cron）
- [ ] 统一管理端点 RBAC 门禁（issue P1/P2，本轮未覆盖，见兄弟目录 `shield-role-api-authz`）
- [ ] 外部调用方（前端/运维脚本）已停止调用该接口（需跨仓确认，未验证）
- [ ] 历史补录需求的替代运维手段（如确需补数，需另行设计，未验证）

## 影响范围

- 业务仓 `openlibing-sca`：删除 `analysis/controller/DashboardReportController.java`、`common/domain/DashboardBackfillRequest.java`、`common/domain/DashboardBackfillTaskStatus.java`、`common/schedule/DashboardBackfillService.java`（合计 353 行删除）
- 接口 / 契约：移除 `POST /dashboard/backfill`（破坏性变更，调用方将收到 404）
- 配置 / schema：无变化，无数据迁移（任务状态原为内存存储）
- 行为变化：运营看板不再提供手工历史补录入口；每日 cron 上报不受影响
