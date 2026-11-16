# #138 — Web 接口调用访问日志能力建设

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/138
（【安全】【安全隐私】Web Service 接口调用未记录访问日志，当前状态 closed，标签「安全问题」）

问题类型：安全隐私 / 安全审计合规，要求接口调用可追溯。

现状（issue 核实结论）：`openlibing-sca` 共 18 个 Controller（`analysis` 13 个、`dm` 5 个），仅存在零散业务日志，全仓无统一请求日志 Filter/Interceptor/AOP，接口调用行为无统一留痕。

风险与影响：

1. 越权调用、异常批量调用、注入攻击尝试等安全事件发生后无法回溯调用记录，缺少审计证据；
2. 涉及扫描结果查询、文件下载、确认评审等用户/隐私数据接口缺少访问留痕，不满足等保/审计的「日志记录」控制项；
3. 无法基于访问日志做异常行为检测（调用频率、来源、参数异常）。

## 功能描述

本 issue 分多轮演进，最终形态以「SDK 切面 + 按 DTO 匹配的日志补数 Handler」为准（`@LogApi` 方案已被 SDK 废弃）：

**阶段一：注解全覆盖（`b157bc31`）**

1. 17 个业务 Controller（18 个 Controller 中排除 `HealthCheckController`）全量标注 `@LogApi`（含 `tableName = LogDataCollectionName.SCAN_CENTER_LOG`、`operationModule`、`operation`），由 SDK `OperationLogAspect` 记录来源、路径、脱敏参数、结果与耗时；
2. 4 个仍为 `@Controller` 的类（`BinaryLicenseController`、`FileController`、`LicenseController`、`MeasureController`）改为 `@RestController`，使切面生效；
3. 新增通用操作常量 `QUERY` / `EXPORT` / `DOWNLOAD` / `ADD` / `DELETE` / `UPDATE` / `REFRESH` / `TRIGGER_SCAN`；
4. 健康检查接口按设计排除。

**阶段二：操作名细化（`65d5000a`）**

16 个 Controller 中 81 处通用操作名替换为按端点的业务具体常量（如 `EXPORT_NOTICE_FILE`、`EFFECTIVE_FILTER_RULE`），并删除不再使用的通用常量。

**阶段三：只记录状态变更（`d4359c94`）**

移除 13 个 Controller 中 55 个只读端点（列表、详情、统计、文件查看查询）的 `@LogApi`，审计日志只记录新增、删除、修改、导出、下载、刷新、触发类操作，并删除查询类常量。

**阶段四：操作名中文化（`2913d470`）**

`LogOperationAndModule` 常量值由英文 snake_case 改为中文描述（如 `add_filter_rule` → `新增屏蔽规则`），与已中文化的 `operationModule` 对齐，日志页面直接展示中文；Controller 按常量名引用，无需改动。

**阶段五：切换到 Handler 模式并移除注解（`a7e7bc1b`）**

`@LogApi` 在 `openlibing-common` 中已废弃，操作日志改由基于 `AbstractLogHandler` 的 Handler 按请求 DTO 匹配记录。移除 14 个 Controller 中 41 个 `@LogApi` 注解块与 3 个相关 import。

**阶段六：补齐 NOTICE/版本扫描/邮件审核匹配（`96c1578e`）**

`ScanLogHandler.matches()` 增加 `ProjectNoticeExportPo`、`ProjectNoticeBatchExportPo`、`ProjectNoticeScanSupplementPo`、`ManualVersionScanAddPo`、`ManualVersionScanStartPo`（List 内）、`ManualVersionScanScheduledBatchPo`、`EmailReviewAddPo`（List 内），并对裸 `List<String>` 入参（版本扫描删除、邮件审核删除）与和状态查询共用 DTO 的 `/startBatch` 用请求路径限定；扩充 `OperationLogHandlerSupport` 取参工具（`firstDtoInList` / `firstStringList` / `requestPathEndsWith`），并新增 `ScanLogHandlerTest`。

**阶段七：按域拆分 Handler（`24f55558`）**

`OperationLogAspect` 注入全部 `AbstractLogHandler` 且只在「恰好一个命中」时补数，故把 NOTICE 扫描、手动版本扫描、邮件审核匹配拆为 `NoticeScanLogHandler`、`VersionScanLogHandler`、`EmailReviewLogHandler`；`ScanLogHandler` 回归审核、屏蔽规则、导出补数。新增三个 Handler 单测与 `OperationLogHandlerDisjointTest` 守护互斥契约。

**最终形态（当前 `ms_scan` 代码）**

- 仓库内已无 `@LogApi` 注解（仅 `ScanLogHandler` javadoc 提及历史方案）；
- 访问日志由 SDK `OperationLogAspect` + 4 个 `AbstractLogHandler` 实现子类按 DTO/请求路径匹配记录：`ScanLogHandler`、`NoticeScanLogHandler`、`VersionScanLogHandler`、`EmailReviewLogHandler`；
- `LogOperationAndModule` 仍保留中文常量，但已无引用（阶段二/三/五移除注解后成为未使用常量）。

**不做什么**：

- 未新增自研 Filter/Interceptor 形式的访问日志组件（复用 SDK 切面）；
- 未记录读接口调用（阶段三有意收敛为「只记录状态变更操作」，与 issue 原始「所有接口调用均记录」不同，见验收标准）；
- 未回补历史访问日志；
- 未删除已成死代码的 `LogOperationAndModule` 常量类；
- 健康检查接口不纳入。

## 验收标准

- [x] 状态变更类接口具备访问日志（注解阶段全量覆盖，后由 4 个 Handler 接管；代码证据：`OperationLogHandlerDisjointTest#nonQueryEndpointsMatchExactlyOneHandler`）
- [x] 日志 Handler 命中互斥，避免切面因多 Handler 命中而跳过补数（`OperationLogHandlerDisjointTest#nonQueryEndpointsMatchExactlyOneHandler` / `#queryEndpointsMatchNoHandler`）
- [x] 裸 `List<String>` 与共用 DTO 入口按请求路径区分，不误记查询接口（`NoticeScanLogHandlerTest#matches_startBatchRequiresRequestPath`、`VersionScanLogHandlerTest#matches_deleteRequiresRequestPath`、`EmailReviewLogHandlerTest#matches_deleteRequiresRequestPath`）
- [x] NOTICE 导出/批量导出/补充、版本扫描新增/启动/批量改定时/删除、邮件审核新增/删除均纳入匹配（`NoticeScanLogHandlerTest#matches_exportBatchAndSupplementDtos`、`VersionScanLogHandlerTest#matches_addStartAndScheduledDtos`、`EmailReviewLogHandlerTest#matches_addDtoInList`）
- [x] 审核/转审/屏蔽规则/导出补数逻辑保持（`ScanLogHandlerTest#matches_reviewAndShieldDtosNotChineseModule`、`#matches_exportParamsAndScanossDelete`、`#after_patchReviewFillsEntityJsonNotOperationName` 等）
- [ ] 「所有对外 Web 接口调用均有访问日志记录」：读接口按设计不记录；`a7e7bc1b` 移除注解后，未命中任何 Handler 的状态变更端点不再有访问日志（本轮未逐一核对受影响端点清单，未验证）
- [ ] 「日志包含来源、参数摘要（脱敏）、结果、耗时」：由 SDK 切面提供，脱敏字段清单未在仓内核对（未验证）
- [ ] 「敏感字段不落明文日志」：由 SDK 与 `sensitive-log-redaction`（#155）、`request-param-log-whitelist`（#161）承接，本 issue 未单独验证
- [ ] 「日志无性能明显劣化」：未做压测（未验证）

## 影响范围

- 业务仓 `openlibing-sca`：`analysis` / `dm` 共 16 个 Controller 的日志注解（最终仅剩 `@RestController`）、`common/constants/LogOperationAndModule`、`common/aop` 下 4 个 Handler + `OperationLogHandlerSupport`，以及 5 个 Handler 单测
- 接口 / 契约：`@LogApi` 非运行时契约，接口入参/返回不变；`DashboardReportController` 的注解随 #141 一并移除
- 配置 / schema：未新增表；沿用 `log_scan_center`（`db/changelog/v1.0.0/log-table.xml`，含 `operation_module` / `operation` / `params` / `log_result` 等列）与 SDK 落库链路
- 行为变化：操作日志记录范围由「全接口」收敛为「状态变更类接口」；操作类型列由英文码改为中文描述
