# #138 — 技术设计

## 方案概述

访问日志能力最终由 openlibing-common SDK 的 `OperationLogAspect` 统一采集（来源、路径、脱敏参数、结果、耗时），业务仓只负责「哪些入口需要记录、记录时补哪些业务字段」。实现路径经历三次收敛：注解全覆盖 → 只记录状态变更 → 注解废弃后改为按 DTO 匹配的 `AbstractLogHandler`，并按业务域拆分为 4 个互斥 Handler。

## 演进与最终形态

| 阶段         | commit     | 形态                                                                                         | 结果                             |
| ------------ | ---------- | -------------------------------------------------------------------------------------------- | -------------------------------- |
| 注解全覆盖   | `b157bc31` | 17 个业务 Controller 全量 `@LogApi`（健康检查排除），4 个 `@Controller` 改 `@RestController` | 建立基础留痕；操作名为通用动词   |
| 操作名细化   | `65d5000a` | 81 处通用操作名 → 按端点具体常量                                                             | 日志可读性提升                   |
| 只记状态变更 | `d4359c94` | 移除 55 个只读端点注解                                                                       | 降低日志量，聚焦审计价值         |
| 操作名中文化 | `2913d470` | 常量值改中文                                                                                 | 与中文模块名对齐，页面直接可读   |
| 切换 Handler | `a7e7bc1b` | 移除 41 个 `@LogApi` 块与 3 个 import                                                        | 顺应 SDK 废弃注解，改按 DTO 匹配 |
| 补齐匹配     | `96c1578e` | `ScanLogHandler` 增加 NOTICE/版本/邮件入口                                                   | 注解移除后不丢日志               |
| 按域拆分     | `24f55558` | 拆出 3 个域 Handler + 互斥测试                                                               | 避免 `matches()` 长链与多命中    |

最终：`OperationLogAspect` + `ScanLogHandler` / `NoticeScanLogHandler` / `VersionScanLogHandler` / `EmailReviewLogHandler` 四个 bean。

## 数据流（最终形态）

```
HTTP 请求
  └─ OperationLogAspect（openlibing-common）
       ├─ before：遍历所有 AbstractLogHandler
       │     ├─ matches(context) 命中数 == 1 → 调用该 handler.before() 取旧数据快照
       │     └─ 命中数 != 1 → 不补数（多命中记 error 日志）
       ├─ 业务方法执行
       │     └─ 返回 ResponseEntity(code/message/data)
       └─ after：同一 handler.after(context, OperationLogBizFields)
             ├─ 公共字段（路径、参数、结果、耗时、IP 等）由切面/SDK 填
             └─ 业务字段（projectId / resourceId / resourceName / oldData / newData）
                  由 handler 回查实体填充
```

## 架构决策

| 决策                                                        | 理由                                                                                                      |
| ----------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| D1 复用 SDK `OperationLogAspect`，不自研 Filter/Interceptor | 与平台日志落库、展示、脱敏链路一致，避免重复建设                                                          |
| D2 只记录状态变更类操作                                     | 查询量级远大于写操作，全量留痕收益低、存储与性能成本高；审计重点是新增/删除/修改/导出/下载/刷新/触发      |
| D3 `@LogApi` 废弃后改为按请求 DTO 匹配                      | 注解方案与 SDK 新能力冲突；DTO 匹配不侵入 Controller，且可在 handler 内回查实体做新旧数据快照             |
| D4 裸 `List<String>` 与共用 DTO 入口用请求路径限定          | 类型无法区分入口（版本删除/邮件删除、`/startBatch` 与状态查询共用 DTO），只靠 DTO 会误记查询接口          |
| D5 按业务域拆成多个 Handler 且保持互斥                      | 切面只在「恰好一个 handler 命中」时补数，长 `                                                             |     | `链易漏维护；拆分后每域可独立测试，并用`OperationLogHandlerDisjointTest` 守护互斥 |
| D6 快照集合限 100 条，超限写省略标记                        | 避免批量操作把大集合写入日志，控制日志体积（`OperationLogHandlerSupport.MAX_SNAPSHOT_ITEMS` / `OMITTED`） |
| D7 操作名常量中文化                                         | `operation_module` 已是中文，操作类型同步中文，日志页面无需翻译映射                                       |

## 涉及文件

| 文件                                                                                    | 操作 | 说明                                                                                                                             |
| --------------------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/sca/analysis/controller/BinaryLicenseController.java`     | 修改 | 注解阶段加注解并改 `@RestController`；后续替换操作名、移除查询注解、最终移除 `@LogApi`                                           |
| `src/main/java/com/openlibing/sca/analysis/controller/ConfirmReviewController.java`     | 修改 | 同上（审核入口，后由 `ScanLogHandler` 按 DTO 覆盖）                                                                              |
| `src/main/java/com/openlibing/sca/analysis/controller/DashboardReportController.java`   | 删除 | `b157bc31` 为 `/dashboard/backfill` 加注解；`5cbfa2ba`（#141）整类删除                                                           |
| `src/main/java/com/openlibing/sca/analysis/controller/FileController.java`              | 修改 | 改 `@RestController`，加/移注解                                                                                                  |
| `src/main/java/com/openlibing/sca/analysis/controller/LicenseController.java`           | 修改 | 改 `@RestController`，加/移注解                                                                                                  |
| `src/main/java/com/openlibing/sca/analysis/controller/MeasureController.java`           | 修改 | 改 `@RestController`，加/移注解                                                                                                  |
| `src/main/java/com/openlibing/sca/analysis/controller/OpenConfirmReviewController.java` | 修改 | 加/移注解                                                                                                                        |
| `src/main/java/com/openlibing/sca/analysis/controller/OpenPersonScanController.java`    | 修改 | 加/移注解                                                                                                                        |
| `src/main/java/com/openlibing/sca/analysis/controller/OpenScanController.java`          | 修改 | 加/移注解（注解数量最多）                                                                                                        |
| `src/main/java/com/openlibing/sca/analysis/controller/ScanossShieldController.java`     | 修改 | 加/移注解                                                                                                                        |
| `src/main/java/com/openlibing/sca/analysis/controller/ShieldRoleController.java`        | 修改 | 加/移注解                                                                                                                        |
| `src/main/java/com/openlibing/sca/analysis/controller/TblScancodeInfoController.java`   | 修改 | 加/移注解                                                                                                                        |
| `src/main/java/com/openlibing/sca/dm/controller/EmailReviewController.java`             | 修改 | 加/移注解                                                                                                                        |
| `src/main/java/com/openlibing/sca/dm/controller/IntegrationApiController.java`          | 修改 | 加/移注解                                                                                                                        |
| `src/main/java/com/openlibing/sca/dm/controller/ManualVersionScanController.java`       | 修改 | 加/移注解                                                                                                                        |
| `src/main/java/com/openlibing/sca/dm/controller/OpenScanDMController.java`              | 修改 | 加/移注解                                                                                                                        |
| `src/main/java/com/openlibing/sca/dm/controller/ProjectNoticeScanController.java`       | 修改 | 加/移注解                                                                                                                        |
| `src/main/java/com/openlibing/sca/common/constants/LogOperationAndModule.java`          | 修改 | 新增通用常量 → 细化为端点常量 → 删除查询常量 → 值改中文；最终无引用                                                              |
| `src/main/java/com/openlibing/sca/common/aop/OperationLogHandlerSupport.java`           | 修改 | 扩充取参工具：`firstDtoInList`（List 内首个 DTO）、`firstStringList`（裸 `List<String>`）、`requestPathEndsWith`（请求路径限定） |
| `src/main/java/com/openlibing/sca/common/aop/ScanLogHandler.java`                       | 修改 | 审核/转审/屏蔽/导出补数；中期扩展 NOTICE/版本/邮件匹配，后期回退                                                                 |
| `src/main/java/com/openlibing/sca/common/aop/NoticeScanLogHandler.java`                 | 新增 | NOTICE 导出、批量导出、补充、`/startBatch` 匹配                                                                                  |
| `src/main/java/com/openlibing/sca/common/aop/VersionScanLogHandler.java`                | 新增 | 版本扫描新增/启动/批量改定时/删除匹配                                                                                            |
| `src/main/java/com/openlibing/sca/common/aop/EmailReviewLogHandler.java`                | 新增 | 邮件审核新增/删除匹配                                                                                                            |
| `src/test/java/com/openlibing/sca/common/aop/ScanLogHandlerTest.java`                   | 修改 | `96c1578e` 增加 NOTICE/版本/邮件匹配用例（+81 行）；`24f55558` 随拆分移出这些用例，保留审核/屏蔽/导出与快照断言                  |
| `src/test/java/com/openlibing/sca/common/aop/NoticeScanLogHandlerTest.java`             | 新增 | NOTICE 匹配与路径限定                                                                                                            |
| `src/test/java/com/openlibing/sca/common/aop/VersionScanLogHandlerTest.java`            | 新增 | 版本扫描匹配与路径限定                                                                                                           |
| `src/test/java/com/openlibing/sca/common/aop/EmailReviewLogHandlerTest.java`            | 新增 | 邮件审核匹配与路径限定                                                                                                           |
| `src/test/java/com/openlibing/sca/common/aop/OperationLogHandlerDisjointTest.java`      | 新增 | 非查询入口恰好命中一个 handler、查询入口零命中                                                                                   |

## 风险 & 缓解

| 风险                                        | 缓解                                                                                      |
| ------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 多个 Handler 同时命中导致切面跳过补数       | `OperationLogHandlerDisjointTest` 守护互斥；新增 Handler 必须补该测试                     |
| 注解移除后部分状态变更端点无日志            | `96c1578e` 补齐 NOTICE/版本/邮件；其余端点未逐一核对（未验证），需按 Handler 覆盖清单复核 |
| 裸 `List<String>` / 共用 DTO 误命中查询入口 | `requestPathEndsWith` 路径限定 + 对应单测                                                 |
| 批量操作把大集合写入日志                    | `MAX_SNAPSHOT_ITEMS=100`，超限写 `{"_omitted": ...}`                                      |
| 中文操作名影响既有检索/看板                 | 检索条件与看板需按中文值更新（外部配置，未验证）                                          |
| 日志写失败影响业务                          | Handler 内 `before`/`after` 捕获 `RuntimeException` 并 `warn`，不阻断业务                 |
| `LogOperationAndModule` 死代码误导维护      | 已记录为遗留项，建议后续清理                                                              |

## 跨仓影响

依赖 openlibing-common SDK（`com.openlibing.common.aspect.logapi.AbstractLogHandler`、`OperationLogAspect`、`OperationLogContext`、`OperationLogBizFields`、`OperationLogParams`）。日志落库与页面展示由平台侧消费 `log_scan_center`；操作名由英文改中文后，平台检索/报表如需枚举值需同步。spec 文档归档 openlibing-docs 仓（本目录）。
