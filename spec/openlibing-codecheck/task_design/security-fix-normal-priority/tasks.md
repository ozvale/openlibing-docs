# Tasks: codecheck 一般优先级安全问题批次修复

## 进度：0/44（spec 已生成，编码未开始）

## 批次 1 — 日志、敏感信息与常量（#386、#400、#215、#399）

- [ ] 1. #386 修改 `src/main/resources/log4j2-spring.xml`
  - `MANAGE_LOG_FILE` 的 `PatternLayout` 改为 `%enc{%msg}{CRLF}%n`
  - 保持 `charset="UTF-8"` 与滚动策略不变

- [ ] 2. #386 修改 `common/utils/ManageLogHelper.java`
  - 对 `operatorIp`、`objectType`、`operationType` 等自由文本字段调用 `LogSanitizer.sanitize`
  - 不改变 JSON 字段名与结构

- [ ] 3. #386/#400 扩展既有 `common/util/LogSanitizer.java`（注意包路径为 `common/util`，不是 `common/utils`）
  - 保持既有 `sanitize(null) -> null` 语义不变
  - 新增 `sanitize(String, int)` 最大长度截断重载（默认调用方可传 512）
  - 扩展 `LogSanitizerTest`：null、`\r\n`、`\t`、控制字符、超长文本、非正数上限

- [ ] 4. #386 补充 `ManageLogHelperTest`
  - 输入含 `\r\n`、`\t`、控制字符时输出不含真实换行
  - 正常 JSON 输出字段完整

- [ ] 5. #400 修改 `business/service/impl/SuppressionScanServiceImpl.java`
  - `API response code is not 0` 日志不再打印完整 `responseBody`，改为状态码/长度
  - IO / JSON 异常日志保留异常类型与前 10 帧堆栈摘要，省略 message（避免响应体/URL 原文）
  - 不再把异常对象直接作为 throwable 传入，避免 message 原文随堆栈输出
  - `platform` 等上下文参数统一 `LogSanitizer.sanitize`

- [ ] 6. #400 补充/验证日志测试
  - 异常消息含 URL/token/响应片段时日志中不出现原文
  - 异常类型与堆栈仍可定位问题
  - 正常解析逻辑与返回值不变

- [ ] 7. #215 修改 `common/enums/ProjectConstant.java`
  - `Role` 增加 `PLATFORM_OPERATOR = "platform_operator"`
  - `Role` 增加 `COMMUNITY_MANAGER = "community_manager"`

- [ ] 8. #215/#399 修改 `common/utils/codecheck/AuthUtils.java`
  - 增加 `isSystemAdmin(String role)` 集中判断方法
  - 替换 206/212/374/375 行角色字面量

- [ ] 9. #215/#399 扩展既有 `AuthUtilsTest`（不新建测试类）
  - `isSystemAdmin` 覆盖 admin / platform_operator → true
  - community_manager / 普通角色 / null / 空串 → false
  - 鉴权入口对上述角色结果与修改前一致

- [ ] 10. #399 统一 admin 判断（5 组共 9 处）
  - `business/impl/SensitiveDelegateImpl.java:746` 使用 `ProjectConstant.Role.ADMIN`
  - `checkPermission` 保留 null guard，去掉空集合短路与重复 `queryByUserId` 调用；空列表、platform_operator、普通角色结果均不变
  - `business/operation/common/CommonOperation.java:298/312`
  - `business/operation/sensitive/CheckPermissionOperation.java:40/46`

- [ ] 11. #399 补充 `SensitiveDelegateImplTest`
  - admin / platform_operator / 普通用户权限结果与修改前一致
  - 空角色列表、null 角色列表、空 userId 不抛异常

- [ ] 12. 批次 1 验证
  - `mvn test -Dtest=ManageLogHelperTest,LogSanitizerTest,AuthUtilsTest,SensitiveDelegateImplTest`
  - `mvn -DskipTests clean compile`

## 批次 2 — 输入校验（#385、#373）

- [ ] 13. #385 修改 `ProblemshieldController.java`
  - `shieldSubmit` / `shieldReferral` / `shieldRevoke` 的 `@RequestBody` 加 `@Valid`

- [ ] 14. #385 修改 `RuleController.java`
  - `updateRule` 的 `@RequestBody` 加 `@Valid`

- [ ] 15. #385 修改 `FileDownLoadController.java`
  - `exportBoardByFile` 的 `@RequestBody` 加 `@Valid`

- [ ] 16. #385 修改 `UpdateRuleModel.java`
  - `@NotBlank taskId`
  - `@Min(1) projectId`
  - `@NotBlank repoName`
  - `@NotEmpty ruleSets`

- [ ] 17. #385 修改 `ShieldModel.java` / `IdArray.java`
  - `shieldType`、`reason` 增加 `@Size(max = 512)`
  - 保留 `notifyType` 的 `@NotBlank`

- [ ] 18. #373 修改 `QueryTaskSummaryMachineApiModel.java`
  - `pageNum`：`@Min(1)`
  - `pageSize`：`@Min(1) @Max(100)`
  - 新增 `@AssertTrue` 校验分页参数成对出现

- [ ] 19. #373 修改 `MachineApiCheckboardController.java` / `HwApigController.java`
  - 入参加 `@Valid`

- [ ] 20. #373 修改 `FullSummaryOperation.java`
  - skip 使用 long 计算
  - `skip < 0` 抛 `PageSkipException`
  - 分页参数缺失时走 #365 统一上限策略

- [ ] 21. #373 补 `StaticAlarmServiceImpl.searchRepos` 回归测试
  - 现有 `Math.max(1, Math.min(limit, 50))` 裁剪保持不变
  - 覆盖 `limit=0`、`limit=-1`、`limit=51`、正常值
  - 当前 Controller 未暴露 `limit` 入参，不做新增参数改造

- [ ] 22. 批次 2 验证
  - `ProblemshieldControllerTest`、`RuleControllerTest`、`FileDownLoadControllerTest`
  - `MachineApiCheckboardControllerTest`、`HwApigControllerTest`
  - 新增非法入参用例：缺字段、`projectId=0`、`pageSize=101`、只传一个分页参数
  - `mvn -DskipTests clean compile`

## 批次 3 — 配置化（#202）

- [ ] 23. 新增 `common/config/CodePlatformProperties.java`
  - `gitcode-web-base-url`
  - `gitee-web-base-url`
  - `gitcode-api-base-url`
  - `mail-from-name`
  - `mail-from-address`

- [ ] 24. 修改 `CheckboardDelegateImpl.java`
  - `buildUserUrl` 使用配置项

- [ ] 25. 修改 `ProblemshieldDelegateImpl.java`
  - 用户主页 URL 使用配置项

- [ ] 26. 修改 `PipelineDelegateImpl.java`
  - GitCode API 地址使用配置项
  - 默认发件账号使用配置项
  - 动态 `api.<repoType>.com` 改为白名单 Map

- [ ] 27. 批次 3 验证
  - 配置覆盖后 URL/邮箱生效
  - 默认配置行为不变
  - 确认 `.mvn/settings.xml` 无改动

## 批次 4 — 审计日志（#363）

- [ ] 28. 核对 12 个写接口与现有 Handler 的覆盖矩阵
  - 已覆盖：规则集（`RuleSetLogHandler`）、敏感词（`SensitiveLogHandler`）
  - 待补：shield 6 个接口、`assign-owner`、`default/template`、`modify/createUser`

- [ ] 29. 新增 `common/aop/ShieldLogHandler.java`
  - `matches`：`ShieldModel` / `IdArray` / `AuditModel`
  - `before`：按 `detailsId` 回查问题状态
  - `after`：填 projectId、resourceId、newData
  - 不记录屏蔽原因全文

- [ ] 30. 新增 `common/aop/StaticAlarmAssignLogHandler.java`
  - `matches`：assign-owner 入参
  - `before/after`：记录问题 ID 列表与责任人变化

- [ ] 31. 扩展 `common/aop/RuleSetLogHandler.java`
  - 覆盖 `default/template` 散参
  - 覆盖 `modify/createUser` 散参

- [ ] 32. 输出网关菜单 `write_log` 配置清单
  - 12 个接口的 URL 与菜单绑定关系
  - 交部署侧配置，代码仓不修改框架库表

- [ ] 33. 批次 4 验证
  - `ShieldLogHandlerTest`、`StaticAlarmAssignLogHandlerTest`
  - `RuleSetLogHandlerTest` 扩展用例
  - 联调验证操作日志可查询到操作者、时间、对象、结果

## 批次 5 — 资源上限（最后实施）

> 参数已按建议值确认：见 `design.md` §1.3 批次 5 已确认参数（#365 分页上限、#364 导出上限、#247 SARIF 上限）。
> #247 不支持 `0 = 不限制`；0/负数启动校验失败并告警。

- [ ] 34. #365 新增 `common/utils/PageParams.java` 并接入 10 个端点
  - 机机 summary `/machine-api/v1/codecheck/full/task/result/summary`
  - APIG summary `/apig/v1/machine-api/v1/codecheck/full/task/result/summary`
  - 记录列表 `/machine-api/v1/full-codecheck-record/list`（`queryFullSummaryList`）
  - 静态告警汇总
  - FOSS 查询/导出
  - 敏感词规则
  - 规则查询
  - 自定义屏蔽
  - 工作台
  - metrics
  - 原 Webhook Mongo 查询 `/ci-portal/webhook/codecheck/v1/find/by/mongoDB` 已由提交 `bdc9636b` 删除 `WebhookController` 下线，不纳入

- [ ] 35. #364 导出上限
  - `StaticAlarmServiceImpl.writeExcelInBatches` 增加总行数上限
  - `FileDownloadDelegateImpl.exportDetailToFile` 增加分片数/字节数上限
  - `FileDownloadDelegateImpl.exportFossScanDetail` 增加行数上限
  - `ExcelReportImpl` 单任务超限直接失败

- [ ] 36. #247 SARIF 上限
  - `SarifParseServiceImpl.parseAllUrls` 校验 `obsUrls` 数量，超过 `max-urls` 整批拒绝，不截断
  - `downloadAndParse` 使用 `LimitedInputStream`
  - 增加 runs / results 上限，按单 URL 隔离失败

- [ ] 37. #247 配置合法性校验
  - `max-urls` / `max-file-bytes` / `max-runs` / `max-results` 均要求 `>= 1`
  - 0 或负数启动校验失败并告警，不支持 `0 = 不限制`

- [ ] 38. #247 新增 `common/io/LimitedInputStream.java` 及单测
  - 读取超过阈值抛 `IOException`
  - 覆盖刚好等于阈值、超过阈值、底层流提前结束
  - 关闭时正确释放底层流

- [ ] 39. #365/#364 FOSS 正则防护回归验证
  - 现有 `FossScanOperation` 已使用 `Pattern.quote(...)` + `MAX_REGEX_PARAM_LENGTH`
  - 覆盖 `filePath` / `componentName` 含 `.`、`*`、`[`、`(` 等元字符时按字面量匹配
  - 超长参数跳过正则过滤并记录 warn
  - 本项只补测试，不重复改造已有防护

- [ ] 40. 批次 5 验证
  - `PageParamsTest`、`LimitedInputStreamTest`
  - `SarifParseServiceImplTest` 超限场景（整批拒绝 / 单 URL 隔离）
  - 导出相关测试
  - FOSS 正则回归测试
  - `mvn test` 全量通过

## 交付

- [ ] 41. 每批一次 commit，commit message 关联对应 Issue
- [ ] 42. 每批一个业务 PR，PR 描述贴对应 Issue 链接
- [ ] 43. 补 Issue 评论：修复方案 + 测试场景
- [ ] 44. 更新本文档进度与验证结果
