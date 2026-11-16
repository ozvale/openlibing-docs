# #138 — 实现任务

## 进度: 7/7 complete

- [x] Task 1: 17 个业务 Controller 全量 `@LogApi` 覆盖（健康检查排除），4 个 `@Controller` 改 `@RestController`，新增通用操作常量（`b157bc31`）
- [x] Task 2: 81 处通用操作名替换为按端点具体常量，删除通用常量（`65d5000a`）
- [x] Task 3: 移除 55 个只读端点 `@LogApi`，审计只保留状态变更操作，删除查询类常量（`d4359c94`）
- [x] Task 4: 操作名常量值改中文描述（`2913d470`）
- [x] Task 5: 移除 14 个 Controller 的 41 个已废弃 `@LogApi` 注解块与 3 个 import，切到 `AbstractLogHandler` 模式（`a7e7bc1b`）
- [x] Task 6: `ScanLogHandler` 补齐 NOTICE/版本扫描/邮件审核匹配，裸 List 与共用 DTO 按路径限定；扩充 `OperationLogHandlerSupport` 取参工具与 `ScanLogHandlerTest`（`96c1578e`）
- [x] Task 7: 拆出 `NoticeScanLogHandler` / `VersionScanLogHandler` / `EmailReviewLogHandler`，`ScanLogHandler` 回退到审核/屏蔽/导出；新增 4 个测试含互斥守护（`24f55558`）

## 交付记录

| commit     | 日期       | 标题                                                                     | 关联      |
| ---------- | ---------- | ------------------------------------------------------------------------ | --------- |
| `b157bc31` | 2026-11-03 | feat(scan): add LogApi access logging to all web endpoints               | Refs #138 |
| `65d5000a` | 2026-11-06 | refactor(common): replace generic log operations with specific constants | —         |
| `d4359c94` | 2026-11-06 | refactor(common): drop audit log annotations on query-only endpoints     | —         |
| `2913d470` | 2026-11-06 | refactor(common): use Chinese text as log operation values               | —         |
| `a7e7bc1b` | 2026-11-10 | chore(log): remove deprecated @LogApi annotations from controllers       | —         |
| `96c1578e` | 2026-11-10 | feat(log): match notice/version/email endpoints in ScanLogHandler        | —         |
| `24f55558` | 2026-11-10 | refactor(log): split domain handlers out of ScanLogHandler               | —         |

- 分支：`ms_scan`（`openlibing-sca`）
- 说明：`65d5000a` / `d4359c94` / `2913d470` / `a7e7bc1b` / `96c1578e` / `24f55558` 的 commit message 未带 `Refs #138`，但均属本 issue 的日志能力演进链（同一 `@LogApi` → Handler 改造面）。
- 验证方式（代码内证据）：
  - `OperationLogHandlerDisjointTest#nonQueryEndpointsMatchExactlyOneHandler`：IssuePo、NOTICE 导出/补充、版本新增/启动/批量改定时、邮件新增、`/startBatch`、`/version/scan/deleteByIds`、`/email/review/delete` 均恰好命中 1 个 Handler
  - `#queryEndpointsMatchNoHandler`：NOTICE 状态查询、版本扫描查询零命中
  - `NoticeScanLogHandlerTest#matches_exportBatchAndSupplementDtos`、`#matches_startBatchRequiresRequestPath`
  - `VersionScanLogHandlerTest#matches_addStartAndScheduledDtos`、`#matches_deleteRequiresRequestPath`
  - `EmailReviewLogHandlerTest#matches_addDtoInList`、`#matches_deleteRequiresRequestPath`
  - `ScanLogHandlerTest#matches_reviewAndShieldDtosNotChineseModule`、`#matches_exportParamsAndScanossDelete`、`#before_oversizedReviewsSkipQuery`、`#after_patchReviewFillsEntityJsonNotOperationName`
  - 本轮为回溯补写文档，未执行 `mvn test`（测试通过性未验证）
- 遗留：
  - `LogOperationAndModule` 常量类已无引用，未删除
  - 注解移除后未命中任何 Handler 的状态变更端点是否仍有访问日志，未逐一核对（未验证）
  - 读接口按设计不记录，与 issue 原始「所有接口调用均记录」存在范围差异
