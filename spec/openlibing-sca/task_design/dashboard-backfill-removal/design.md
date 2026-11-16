# #141 — 技术设计

## 方案概述

以「删除接口及其专有依赖」替代「补授权后保留」：整体移除 `DashboardReportController`（唯一职责是 backfill 端点）、`DashboardBackfillService`（内存任务表 + 异步补录循环）、`DashboardBackfillRequest` / `DashboardBackfillTaskStatus`（仅服务该链路），消除垂直越权面与不可达异常分支；每日报表任务 `DashboardReportSchedule` 独立保留。

## 改动前后对比

```
改动前
  POST /dashboard/backfill
    └─ DashboardReportController#backfill
         ├─ 日期范围校验（2021-06-19 ~ 昨天）
         ├─ catch (PermissionException)   # 不可达死代码
         └─ DashboardBackfillService#submit
               ├─ ConcurrentHashMap<String, DashboardBackfillTaskStatus>（内存）
               ├─ @Async 逐日循环 → DashboardReportSchedule 统计 → 上报
               └─ 仅按 taskId 防重（无身份/角色校验）

改动后
  （无 /dashboard/backfill 路由）
  DashboardReportSchedule#doJob（@Scheduled cron 每日 01:00）不受影响
```

## 架构决策

| 决策                              | 理由                                                                                                                                                                                    |
| --------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 选择下线而非补超管校验         | 该接口无业务使用方（commit 说明「manual dashboard backfill interface is no longer used」），移除是消除越权面的最小实现；补校验需先重建可信身份基座（issue 已注明 JWT 重构后无鉴权组件） |
| D2 同步删除 DTO 与任务状态类      | 三者仅被 backfill 链路引用，保留会成为死代码并掩盖「补录能力仍存在」的事实                                                                                                              |
| D3 保留 `DashboardReportSchedule` | 每日 cron 报表是独立职责（`@Scheduled` + 统计上报），不依赖被删类，删除会误伤正常报表                                                                                                   |
| D4 不做数据库迁移                 | 补录任务状态原为进程内 `ConcurrentHashMap`，无专属表；`DashboardReportSchedule` 本身不建表                                                                                              |
| D5 不顺手改统计口径/日志          | 与漏洞无关，避免无关重构                                                                                                                                                                |

## 涉及文件

| 文件                                                                                  | 操作 | 说明                                        |
| ------------------------------------------------------------------------------------- | ---- | ------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/controller/DashboardReportController.java` | 删除 | 仅含 `/dashboard/backfill` 端点（96 行）    |
| `src/main/java/com/openlibing/sca/common/domain/DashboardBackfillRequest.java`        | 删除 | 补录入参（startDate/endDate/userId，30 行） |
| `src/main/java/com/openlibing/sca/common/domain/DashboardBackfillTaskStatus.java`     | 删除 | 内存任务状态（73 行）                       |
| `src/main/java/com/openlibing/sca/common/schedule/DashboardBackfillService.java`      | 删除 | 任务创建/防重/异步逐日补录（154 行）        |

## 风险 & 缓解

| 风险                         | 缓解                                                                                  |
| ---------------------------- | ------------------------------------------------------------------------------------- |
| 外部仍有调用方，升级后报 404 | 删除前确认接口无业务使用（commit 说明）；需在发布说明中标注接口下线（跨仓确认未验证） |
| 运维确有历史补数需求         | 需另行设计受控补数方案（如带超管鉴权+审计的一次性任务），不在本 issue 范围            |
| 误删每日报表能力             | `DashboardReportSchedule` 未改动，cron 配置 `job.cron.dashboard.report.task` 保持     |
| 编译期残留引用               | 删除后全仓检索 `DashboardBackfill` 无命中；`DashboardReportSchedule` 不反向依赖被删类 |

## 跨仓影响

无代码级跨仓依赖。`POST /dashboard/backfill` 若被前端页面或运维脚本调用，需同步下线（未验证调用方清单）。spec 文档归档 openlibing-docs 仓（本目录）。
