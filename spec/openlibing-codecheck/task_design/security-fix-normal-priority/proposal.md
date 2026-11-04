# Proposal: codecheck 一般优先级安全问题批次修复（11 项）

## 需求背景

`openlibing/openlibing-codecheck` 当前存在 12 个打开状态、优先级为「一般」的安全问题（`issue_type=安全问题`，`issue_priority_detail.title=一般`）。其中 #249（RabbitMQ 消息无签名）经确认**暂不修复**，本批次实际覆盖 11 项。问题来源包括：计算生态型应用 TOP 问题、计算 IT 应用安全编码要求、拒绝服务资源滥用排查、威胁分析、SecInfo 源码扫描、审计日志排查、墨菲安全扫描（含 2026-11-03 新增的 #399 / #400）。

本批次按主题拆分为 5 个批次实施，前 3 批可直接编码，第 4 批为审计日志补齐，依赖网关菜单元数据配置；第 5 批涉及资源上限默认值，需先确认参数后实施。

### 问题清单

| Issue                                                                  | 主题                                     | 类型    | 当前代码状态                                                  |
| ---------------------------------------------------------------------- | ---------------------------------------- | ------- | ------------------------------------------------------------- |
| [#386](https://gitcode.com/openlibing/openlibing-codecheck/issues/386) | 日志注入                                 | CWE-117 | `MANAGE_LOG_FILE` appender 仍为裸 `%msg%n`                    |
| [#385](https://gitcode.com/openlibing/openlibing-codecheck/issues/385) | 5 处接口参数未校验                       | CWE-20  | 三个 Controller 未加 `@Valid`                                 |
| [#373](https://gitcode.com/openlibing/openlibing-codecheck/issues/373) | 机机接口分页参数未校验                   | CWE-20  | `QueryTaskSummaryMachineApiModel` 无范围约束，`@Valid` 未启用 |
| [#365](https://gitcode.com/openlibing/openlibing-codecheck/issues/365) | pageSize 无上限（11 处链路，实际 10 条） | CWE-400 | 分页模型无上限，空参走全量查询                                |
| [#364](https://gitcode.com/openlibing/openlibing-codecheck/issues/364) | 本地文件保存/导出无大小限制              | CWE-400 | 导出与合并链路无总行数/文件大小上限                           |
| [#215](https://gitcode.com/openlibing/openlibing-codecheck/issues/215) | AuthUtils 角色字符串硬编码               | CWE-511 | `"admin"` / `"platform_operator"` 字面量仍在                  |
| [#399](https://gitcode.com/openlibing/openlibing-codecheck/issues/399) | 带 admin 操作的控制语句                  | CWE-511 | 4 处 admin 判断散落，含冗余空集合判断                         |
| [#400](https://gitcode.com/openlibing/openlibing-codecheck/issues/400) | 调试信息不明确导致敏感信息泄露           | CWE-209 | `SuppressionScanServiceImpl` 记录完整响应体与异常栈           |
| [#363](https://gitcode.com/openlibing/openlibing-codecheck/issues/363) | 12 个非查询接口无审计日志                | CWE-778 | 部分接口已有 common 操作日志 Handler，shield 等仍未覆盖       |
| [#202](https://gitcode.com/openlibing/openlibing-codecheck/issues/202) | 源码及配置硬编码公网地址/邮箱            | CWE-798 | 平台域名、API 地址、通知邮箱仍散落硬编码                      |
| [#247](https://gitcode.com/openlibing/openlibing-codecheck/issues/247) | SARIF 下载解析无界                       | CWE-400 | 仅记录规模，未设置 URL/文件/runs/results 上限                 |

> #249（RabbitMQ 消息无签名）经确认暂不修复，保留 Issue 打开，后续单独评估，不计入本次范围。

## 功能描述

### 做什么

1. **批次 1（日志与常量）**
   - #386：`log4j2-spring.xml` 的 `MANAGE_LOG_FILE` PatternLayout 改为 `%enc{%msg}{CRLF}%n`；`ManageLogHelper` 对自由文本字段增加净化防御。
   - #400：`SuppressionScanServiceImpl` 不再打印完整响应体与异常栈，改为打印脱敏后的异常摘要与安全的状态码/长度信息。
   - #215：在 `ProjectConstant.Role` 补充 `PLATFORM_OPERATOR`、`COMMUNITY_MANAGER`，替换 `AuthUtils` 及同类角色字面量。
   - #399：统一 4 处 admin 判断为角色常量与集中校验方法，移除冗余的空集合外层判断。

2. **批次 2（输入校验）**
   - #385：`shieldSubmit` / `shieldReferral` / `shieldRevoke`、`updateRule`、`exportBoardByFile` 增加 `@Valid`；`UpdateRuleModel` 补 `taskId` / `projectId` / `repoName` / `ruleSets` 约束；`ShieldModel` / `IdArray` 对可选字段补长度上限。
   - #373：`QueryTaskSummaryMachineApiModel` 补 `pageNum` / `pageSize` 范围约束与“同时存在或同时为空”校验；Controller 加 `@Valid`；`FullSummaryOperation` 使用 long 计算 skip，负值抛 `PageSkipException`。

3. **批次 3（配置化）**
   - #202：新增 `CodePlatformProperties`，将 `gitcode.com` / `gitee.com` / `api.gitcode.com` / 通知邮箱改为配置项；动态拼接 `api.<repoType>.com` 改为白名单查表。
   - **`.mvn/settings.xml` 不修改**（用户明确要求）。

4. **批次 4（审计日志补齐）**
   - #363：核对 12 个写接口的 common 操作日志 Handler 覆盖情况；新增 shield 系列与 assign-owner 的 Handler，补齐 default/template、modify/createUser 的匹配规则；配套网关菜单 `write_log` 配置（部署侧）。
   - 现有 `RuleSetLogHandler`、`SensitiveLogHandler` 已覆盖规则集与敏感词写入，优先复用，不重复造轮子。

5. **批次 5（资源上限，最后实施）**
   - #365：新增统一分页工具 `PageParams`，对 10 条链路补齐 pageSize 上限（原 Webhook Mongo 查询接口已下线，不纳入）；机机接口不传分页时使用可配置硬上限，不再全量查询。
   - #364：导出链路增加总行数、文件大小、合并分片上限；超限标记导出失败并返回明确提示。
   - #247：SARIF 解析增加 URL 数量、单文件大小、runs 数量、results 数量上限，超限按 URL 隔离失败。

### 不做什么

- 不修改 `.mvn/settings.xml`（DevCloud 私有制品仓地址保留现状）。
- 不修改 `.gitcode/workflows`（当前已无硬编码 http 地址）。
- 不修改数据库 schema、不新增业务依赖。
- 不做与安全修复无关的重构、格式化或命名调整。
- #249（RabbitMQ 消息无签名）暂不修复，保留 Issue 打开，后续单独评估。
- #365 / #364 / #247 的默认上限值需用户确认后写入设计，不在代码中写死不可配置常量。
- #363 只补代码侧 Handler；网关菜单 `write_log` 与框架库表配置由部署侧完成，不在业务仓修改。

## 验收标准

### 批次 1

- [ ] #386：构造含 `\r\n` 的操作日志输入，`operate.log` 中不产生真实换行，日志行不可被伪造。
- [ ] #386：正常操作日志格式、字段内容不变。
- [ ] #215：`AuthUtils` 中不再存在 `"admin"` / `"platform_operator"` / `"community_manager"` 字面量。
- [ ] #215：管理员、平台运营、社区管理员、普通用户的鉴权结果与修改前一致。
- [ ] #399：4 处 admin 判断均使用角色常量，且 `checkPermission` 不再有冗余空集合外层判断。
- [ ] #399：敏感词权限校验对 admin / 非 admin 用户结果与修改前一致。
- [ ] #400：IO/JSON 异常日志不再输出完整响应体与异常栈，仅输出脱敏摘要。
- [ ] #400：正常响应解析与失败返回行为不变。

### 批次 2

- [ ] #385：`shieldSubmit` 缺失 `notifyType` 返回 400 或 `50001`，不执行写操作。
- [ ] #385：`shieldReferral` / `shieldRevoke` 缺失 `notifyType`、`updateRule` 缺失 `taskId`、`exportBoardByFile` 缺失必填字段均被拒绝。
- [ ] #385：合法请求行为不变，现有 Controller 测试通过。
- [ ] #373：机机接口 `pageNum=0`、`pageSize=101`、仅传一个分页参数均返回参数错误。
- [ ] #373：`pageNum=Integer.MAX_VALUE` 不再产生负 skip 或 500。
- [ ] #373：合法分页查询结果与修改前一致。

### 批次 3

- [ ] #202：三个 Delegate 中不再出现硬编码平台域名、API 地址、通知邮箱字面量。
- [ ] #202：通过配置覆盖默认值后，用户主页 URL、GitCode API、通知邮箱均按配置生效。
- [ ] #202：默认配置下行为与修改前一致。
- [ ] #202：`.mvn/settings.xml` 无改动。

### 批次 4

- [ ] #363：12 个写接口逐一核对，shield 6 个接口、`assign-owner`、`default/template`、`modify/createUser` 在操作日志中有记录。
- [ ] #363：规则集、敏感词相关接口复用现有 Handler，不产生重复日志。
- [ ] #363：网关菜单 `write_log` 配置完成后，实际操作可在操作日志中查询到操作者、时间、对象与结果。
- [ ] #363：未命中菜单打标的接口有明确清单，交由部署侧补齐。

### 批次 5（最后）

- [ ] #365：10 条链路在 pageSize 超上限、为空、为负数时均被限制或拒绝，不再触发全量查询。
- [ ] #365：机机接口不传分页时返回条数不超过约定上限，日志包含截断提示。
- [ ] #364：导出总行数/文件大小/分片数超过上限时导出失败并给出明确原因；未超限行为不变。
- [ ] #247：URL 数、单文件大小、runs、results 超过上限时该 URL 独立失败，其余 URL 正常入库。
- [ ] 批次 5 的默认上限值已获用户确认。

### 通用

- [ ] 相关单测与全量 `mvn test` 通过。
- [ ] 编译 `mvn -DskipTests clean compile` 通过。
- [ ] 每个批次对应一个业务 PR，PR 关联对应 Issue。

## 影响范围

- **修改文件（预估）**：
  - 批次 1：`src/main/resources/log4j2-spring.xml`、`ManageLogHelper.java`、`SuppressionScanServiceImpl.java`、`AuthUtils.java`、`ProjectConstant.java`、`SensitiveDelegateImpl.java`、`CommonOperation.java`、`CheckPermissionOperation.java`
  - 批次 2：`ProblemshieldController.java`、`RuleController.java`、`FileDownLoadController.java`、`UpdateRuleModel.java`、`ShieldModel.java`、`IdArray.java`、`QueryTaskSummaryMachineApiModel.java`、`MachineApiCheckboardController.java`、`HwApigController.java`、`FullSummaryOperation.java`
  - 批次 3：`CheckboardDelegateImpl.java`、`ProblemshieldDelegateImpl.java`、`PipelineDelegateImpl.java`、新增 `CodePlatformProperties.java`
  - 批次 4：`ProblemshieldController.java`、`StaticAlarmController.java`、`RuleController.java`、新增 `ShieldLogHandler.java`、新增 `StaticAlarmAssignLogHandler.java`、`RuleSetLogHandler.java`、`SensitiveLogHandler.java`
  - 批次 5：`PageParams.java`、`FossScanOperation.java`、`QueryFossScanModel.java`、`QuerySensitiveRuleModel.java`、`RuleModel.java`、`SelfShieldModel.java`、`WorkbenchOperaton.java`、`IncDetailsOperation.java`、`FullDetailsOperation.java`、`StaticAlarmSummaryOperation.java`、`StaticAlarmServiceImpl.java`、`FileDownloadDelegateImpl.java`、`ExcelReportImpl.java`、`SarifParseServiceImpl.java`
- **接口/契约变化**：无路径与签名变化；部分接口对非法入参从“静默接受”变为 400/403/50001。
- **数据库/Schema**：无。
- **依赖**：无新增。
- **配置**：新增 `codecheck.platform.*`、`codecheck.notification.*`、`codecheck.export.*`、`codecheck.alarm.sarif.*` 配置项。

## 批次安排

| 批次      | Issue                  | 前置条件                      |
| --------- | ---------------------- | ----------------------------- |
| 1         | #386、#400、#215、#399 | 无                            |
| 2         | #385、#373             | 无                            |
| 3         | #202                   | 无                            |
| 4         | #363                   | 网关菜单 `write_log` 配置配合 |
| 5（最后） | #365、#364、#247       | 确认上限默认值                |

## 关联

- 业务仓：`openlibing/openlibing-codecheck`
- 业务 Issue：
  - https://gitcode.com/openlibing/openlibing-codecheck/issues/386
  - https://gitcode.com/openlibing/openlibing-codecheck/issues/385
  - https://gitcode.com/openlibing/openlibing-codecheck/issues/373
  - https://gitcode.com/openlibing/openlibing-codecheck/issues/365
  - https://gitcode.com/openlibing/openlibing-codecheck/issues/364
  - https://gitcode.com/openlibing/openlibing-codecheck/issues/215
  - https://gitcode.com/openlibing/openlibing-codecheck/issues/399
  - https://gitcode.com/openlibing/openlibing-codecheck/issues/400
  - https://gitcode.com/openlibing/openlibing-codecheck/issues/363
  - https://gitcode.com/openlibing/openlibing-codecheck/issues/202
  - https://gitcode.com/openlibing/openlibing-codecheck/issues/247
- 暂不修复 Issue：
  - https://gitcode.com/openlibing/openlibing-codecheck/issues/249
- 业务 PR：<待创建>
- Docs PR：<待创建>
