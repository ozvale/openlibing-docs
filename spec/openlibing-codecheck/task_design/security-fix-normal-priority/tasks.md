# Tasks: codecheck 一般优先级安全问题批次修复

## 进度：0/38（spec 已生成，编码未开始）

## 批次 1 — 日志、敏感信息与常量（#386、#400、#215、#399）

- [ ] 1. #386 修改 `src/main/resources/log4j2-spring.xml`
  - `MANAGE_LOG_FILE` 的 `PatternLayout` 改为 `%enc{%msg}{CRLF}%n`
  - 保持 `charset="UTF-8"` 与滚动策略不变

- [ ] 2. #386 修改 `common/utils/ManageLogHelper.java`
  - 对 `operatorIp`、`objectType`、`operationType` 等自由文本字段调用 `LogSanitizer.sanitize`
  - 不改变 JSON 字段名与结构

- [ ] 3. #386 新增/补充 `ManageLogHelperTest`
  - 输入含 `\r\n`、`\t`、控制字符时输出不含真实换行
  - 正常 JSON 输出字段完整

- [ ] 4. #400 修改 `business/service/impl/SuppressionScanServiceImpl.java`
  - `API response code is not 0` 日志不再打印完整 `responseBody`，改为状态码/长度
  - IO / JSON 异常日志不再传 `e`，改为 `LogSanitizer.sanitize(e.getMessage())`
  - `platform` 参数统一 `LogSanitizer.sanitize`

- [ ] 5. #400 补充/验证日志测试
  - 异常消息含 URL/token/响应片段时日志中不出现原文
  - 正常解析逻辑与返回值不变

- [ ] 6. #215 修改 `common/enums/ProjectConstant.java`
  - `Role` 增加 `PLATFORM_OPERATOR = "platform_operator"`
  - `Role` 增加 `COMMUNITY_MANAGER = "community_manager"`

- [ ] 7. #215/#399 修改 `common/utils/codecheck/AuthUtils.java`
  - 增加 `isSystemAdmin(String role)` 集中判断方法
  - 替换 206/212/374/375 行角色字面量

- [ ] 8. #399 统一 admin 判断
  - `business/impl/SensitiveDelegateImpl.java:746` 使用 `ProjectConstant.Role.ADMIN`
  - 简化 `checkPermission` 的 `CollectionUtils.isNotEmpty` 外层判断
  - `business/operation/common/CommonOperation.java:298/312`
  - `business/operation/sensitive/CheckPermissionOperation.java:40/46`

- [ ] 9. #399 补充 `SensitiveDelegateImplTest`
  - admin / platform_operator / 普通用户权限结果与修改前一致
  - 空角色列表、空 userId 不抛异常

- [ ] 10. 批次 1 验证
  - `mvn test -Dtest=ManageLogHelperTest,AuthUtilsTest,SensitiveDelegateImplTest`
  - `mvn -DskipTests clean compile`

## 批次 2 — 输入校验（#385、#373）

- [ ] 11. #385 修改 `ProblemshieldController.java`
  - `shieldSubmit` / `shieldReferral` / `shieldRevoke` 的 `@RequestBody` 加 `@Valid`

- [ ] 12. #385 修改 `RuleController.java`
  - `updateRule` 的 `@RequestBody` 加 `@Valid`

- [ ] 13. #385 修改 `FileDownLoadController.java`
  - `exportBoardByFile` 的 `@RequestBody` 加 `@Valid`

- [ ] 14. #385 修改 `UpdateRuleModel.java`
  - `@NotBlank taskId`
  - `@Min(1) projectId`
  - `@NotBlank repoName`
  - `@NotEmpty ruleSets`

- [ ] 15. #385 修改 `ShieldModel.java` / `IdArray.java`
  - `shieldType`、`reason` 增加 `@Size(max = 512)`
  - 保留 `notifyType` 的 `@NotBlank`

- [ ] 16. #373 修改 `QueryTaskSummaryMachineApiModel.java`
  - `pageNum`：`@Min(1)`
  - `pageSize`：`@Min(1) @Max(100)`
  - 新增 `@AssertTrue` 校验分页参数成对出现

- [ ] 17. #373 修改 `MachineApiCheckboardController.java` / `HwApigController.java`
  - 入参加 `@Valid`

- [ ] 18. #373 修改 `FullSummaryOperation.java`
  - skip 使用 long 计算
  - `skip < 0` 抛 `PageSkipException`
  - 分页参数缺失时走 #365 统一上限策略

- [ ] 19. 批次 2 验证
  - `ProblemshieldControllerTest`、`RuleControllerTest`、`FileDownLoadControllerTest`
  - `MachineApiCheckboardControllerTest`、`HwApigControllerTest`
  - 新增非法入参用例：缺字段、`projectId=0`、`pageSize=101`、只传一个分页参数
  - `mvn -DskipTests clean compile`

## 批次 3 — 配置化（#202）

- [ ] 20. 新增 `common/config/CodePlatformProperties.java`
  - `gitcode-web-base-url`
  - `gitee-web-base-url`
  - `gitcode-api-base-url`
  - `mail-from-name`
  - `mail-from-address`

- [ ] 21. 修改 `CheckboardDelegateImpl.java`
  - `buildUserUrl` 使用配置项

- [ ] 22. 修改 `ProblemshieldDelegateImpl.java`
  - 用户主页 URL 使用配置项

- [ ] 23. 修改 `PipelineDelegateImpl.java`
  - GitCode API 地址使用配置项
  - 默认发件账号使用配置项
  - 动态 `api.<repoType>.com` 改为白名单 Map

- [ ] 24. 批次 3 验证
  - 配置覆盖后 URL/邮箱生效
  - 默认配置行为不变
  - 确认 `.mvn/settings.xml` 无改动

## 批次 4 — 审计日志（#363）

- [ ] 25. 核对 12 个写接口与现有 Handler 的覆盖矩阵
  - 已覆盖：规则集（`RuleSetLogHandler`）、敏感词（`SensitiveLogHandler`）
  - 待补：shield 6 个接口、`assign-owner`、`default/template`、`modify/createUser`

- [ ] 26. 新增 `common/aop/ShieldLogHandler.java`
  - `matches`：`ShieldModel` / `IdArray` / `AuditModel`
  - `before`：按 `detailsId` 回查问题状态
  - `after`：填 projectId、resourceId、newData
  - 不记录屏蔽原因全文

- [ ] 27. 新增 `common/aop/StaticAlarmAssignLogHandler.java`
  - `matches`：assign-owner 入参
  - `before/after`：记录问题 ID 列表与责任人变化

- [ ] 28. 扩展 `common/aop/RuleSetLogHandler.java`
  - 覆盖 `default/template` 散参
  - 覆盖 `modify/createUser` 散参

- [ ] 29. 输出网关菜单 `write_log` 配置清单
  - 12 个接口的 URL 与菜单绑定关系
  - 交部署侧配置，代码仓不修改框架库表

- [ ] 30. 批次 4 验证
  - `ShieldLogHandlerTest`、`StaticAlarmAssignLogHandlerTest`
  - `RuleSetLogHandlerTest` 扩展用例
  - 联调验证操作日志可查询到操作者、时间、对象、结果

## 批次 5 — 资源上限（最后实施）

> 实施前必须确认：见 `design.md` §1.3 批次 5 待确认项（#365 分页上限、#364 导出上限、#247 SARIF 上限）。

- [ ] 31. #365 新增 `common/utils/PageParams.java` 并接入 10 条链路（原 Webhook Mongo 查询接口已下线，不纳入）
  - 机机 summary / APIG summary
  - 静态告警汇总
  - FOSS 查询/导出
  - 敏感词规则
  - 规则查询
  - 自定义屏蔽
  - 工作台
  - metrics

- [ ] 32. #364 导出上限
  - `StaticAlarmServiceImpl.writeExcelInBatches` 增加总行数上限
  - `FileDownloadDelegateImpl.exportDetailToFile` 增加分片数/字节数上限
  - `FileDownloadDelegateImpl.exportFossScanDetail` 增加行数上限
  - `ExcelReportImpl` 单任务超限直接失败

- [ ] 33. #247 SARIF 上限
  - `SarifParseServiceImpl.parseAllUrls` 增加 URL 数上限
  - `downloadAndParse` 使用 `LimitedInputStream`
  - 增加 runs / results 上限

- [ ] 34. 批次 5 验证
  - `PageParamsTest`
  - `SarifParseServiceImplTest` 超限场景
  - 导出相关测试
  - `mvn test` 全量通过

## 交付

- [ ] 35. 每批一次 commit，commit message 关联对应 Issue
- [ ] 36. 每批一个业务 PR，PR 描述贴对应 Issue 链接
- [ ] 37. 补 Issue 评论：修复方案 + 测试场景
- [ ] 38. 更新本文档进度与验证结果
