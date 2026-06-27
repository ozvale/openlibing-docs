# 项目空间操作日志归入 openlibing 审计 - Tasks V2（跨库改造）

> 本文档为 V2 版本，基于 design-v2.md。核心变更：日志表从 workspace 数据库迁移到 framework 数据库，日志写入从直接 DB insert 改为 Feign 调用 framework 微服务接口。

## Task 1: 基础设施搭建

- [ ] 1.1 新建 `RequestBodyCachingFilter`，包装 POST/PUT 请求为 `ContentCachingRequestWrapper`
- [ ] 1.2 Apollo 配置中心补充 `success.code` 和 `openlibing.domain` 配置（与 framework 保持一致，通过 `@Value` 注入）

## Task 2: 常量定义

- [ ] 2.1 在 `LogOperationConstants` 中修改 `OPERATION_MODULE_WORKSPACE_PROJECT` 值为 `"灵枢"`（原为"项目空间"，改为"灵枢"以避免与 framework 的"项目空间管理"冲突）
- [ ] 2.2 在 `LogOperationConstants` 中新增 `OPERATION_CREATE_MAAS_KEY = "CREATE_MAAS_KEY"`
- [ ] 2.3 在 `LogOperationConstants` 中新增 `OPERATION_DELETE_MAAS_KEY = "DELETE_MAAS_KEY"`
- [ ] 2.4 在 `LogOperationConstants` 中修改 `LOG_WORKSPACE_PROJECT = "log_computing_resource_workspace_project"`（V1 为 `log_workspace_project`，V2 表名变更）

## Task 3: WorkspaceProjectLogHandler 实现

- [ ] 3.1 新建 `WorkspaceProjectLogHandler`，继承 `AbstractLogHandler`
- [ ] 3.2 实现 `@PostConstruct init()`，注册到 `LoggerAspect`（key = `OPERATION_MODULE_WORKSPACE_PROJECT`）
- [ ] 3.3 实现 `getOldData()`：
  - CREATE_PROJECT / ADD_MEMBER / CREATE_API_KEY → 返回空
  - DELETE_PROJECT / UPDATE_PROJECT → 查 `projectSpaceMapper.selectById`
  - REMOVE_MEMBER / UPDATE_MEMBER_ROLE → 查 `projectMemberMapper.selectById`
  - DELETE_API_KEY → 查 `projectApiKeyMapper.selectById`，脱敏 keySha256
- [ ] 3.4 实现 `encapsulatingLogsDetailVO()`：
  - 各操作类型设置 remark、isDetail、oldData、newData
  - 成功时 newData 从 DB 重新查询（确保数据一致性）
  - ADD_MEMBER 成功时：只记录成功成员详情（从 `successMemberIds` 查 DB），0 成功则 newData 为空
  - 失败时保留 params，过滤敏感字段
- [ ] 3.5 实现 `saveLog()`：Feign 调用 `frameworkClient.addMicroservicesLog()` + `ManageLogHelper.writeLog` 入湖（不再使用 `getLogsMapper.insert`）
- [ ] 3.6 实现 `buildMicroservicesLogDTO()`：将 `LogsDetailVO` 转换为 `MicroservicesLogDTO`
  - 路由字段：`tableFlag=2`，`tableDescription="灵枢"`
  - DB 字段（18 列）：从 `LogsDetailVO` 复制
  - 三方账号字段：优先 `LogsDetailVO`，降级 `UserContext`（JWT 不含 `accountPlatform`，需从 `/get-user-info` 接口补全的 `UserContext` 获取）
  - 用户面字段：从 `LogsDetailVO` 复制（`AbstractLogHandler.encapsulatingDataLakeInfo()` 已从 `HttpServletRequest` 提取）
- [ ] 3.7 实现辅助方法：参数提取（extractProjectId / extractMemberId / extractApiKeyId）、敏感信息过滤（sanitizeParams）

## Task 4: FrameworkClient 新增方法

- [ ] 4.1 在 `FrameworkClient` 中新增 `addMicroservicesLog(@RequestBody MicroservicesLogDTO dto)` 方法，调用 `/internal-server/add/microservices/log`

## Task 5: MicroservicesLogDTO

- [ ] 5.1 新建 `MicroservicesLogDTO`（镜像 framework 的 DTO），包含所有字段及校验注解（与 framework 保持一致，确保 Feign 序列化/反序列化正确）

## Task 6: ServiceImpl 改造

- [ ] 6.1 `ProjectSpaceServiceImpl.createProject` 加 `@LogApi` 注解（tableName = `LOG_WORKSPACE_PROJECT`），删除 `ManageLogHelper.writeLog` 调用
- [ ] 6.2 `ProjectSpaceServiceImpl.deleteProject` 加 `@LogApi` 注解，删除 `ManageLogHelper.writeLog` 调用
- [ ] 6.3 `ProjectSpaceServiceImpl.updateProject` 加 `@LogApi` 注解，删除 `ManageLogHelper.writeLog` 调用
- [ ] 6.4 `ProjectSpaceServiceImpl.addMembers` 加 `@LogApi` 注解，删除 `ManageLogHelper.writeLog` 调用
- [ ] 6.5 `ProjectSpaceServiceImpl.removeMember` 加 `@LogApi` 注解，删除 `ManageLogHelper.writeLog` 调用
- [ ] 6.6 `ProjectSpaceServiceImpl.updateMemberRole` 加 `@LogApi` 注解，删除 `ManageLogHelper.writeLog` 调用
- [ ] 6.7 `ApiKeyServiceImpl.createApiKey` 加 `@LogApi` 注解
- [ ] 6.8 `ApiKeyServiceImpl.deleteApiKey` 加 `@LogApi` 注解

## Task 7: 添加成员 DTO 与 Service 适配

- [ ] 7.1 `AddMembersResultVo` 新增 `successMemberIds`（`List<Long>`）字段，存储成功添加的成员 ID
- [ ] 7.2 `ProjectSpaceServiceImpl.processMemberAdditions` 在成功添加/恢复成员后收集 memberId 到 `successMemberIds`
- [ ] 7.3 `insertNewMember` 方法改为返回 `ProjectMember`（获取 MyBatis-Plus 回填的 ID）
- [ ] 7.4 `WorkspaceProjectLogHandler.extractAddMemberResult` 只取 `successMemberIds`，查 DB 获取成员详情写入 newData

## Task 8: 删除 V1 本地日志写入组件

- [ ] 8.1 删除 `GetLogsMapper.java`（不再直接写 DB）
- [ ] 8.2 删除 `GetLogsMapper.xml`（不再直接写 DB）
- [ ] 8.3 在 `project-tables.xml` 中新增 drop table changeSet 删除 `log_workspace_project` 表（后续由手动清理相关 changeSet，保证生产 Liquibase 记录干净）

## Task 9: Bean 扫描与配置

- [ ] 9.1 `@ComponentScan` 增加 `com.openlibing.common.aspect` 包，确保 `LoggerAspect` Bean 被扫描到
- [ ] 9.2 `application.yaml` 补充 `success.code` 和 `openlibing.domain` 默认值（生产环境由 Apollo 覆盖）

## Task 10: UT 适配

- [ ] 10.1 `ProjectSpaceServiceImplTest` 补充 `successMemberIds` 断言（成功场景断言非空，失败场景断言空）
- [ ] 10.2 Mock `projectMemberMapper.insert` 模拟 MyBatis-Plus ID 回填（`lenient().doAnswer`）
- [ ] 10.3 `softDeletedMember` 测试数据补充 `setId(testMemberId)`
- [ ] 10.4 `WorkspaceProjectLogHandlerTest` Mock `FrameworkClient.addMicroservicesLog()` 替代原 `GetLogsMapper.insert()`

## Task 11: Framework 侧（需单独提 PR）

> 前提：workspace 侧代码已就绪。本 Task 在 framework 仓库操作，需单独提 PR。framework 必须先于 workspace 发布。

- [ ] 11.1 新建 Liquibase 脚本 `log_computing_resource_workspace_project.xml`，表结构与 framework 其他业务日志表一致（18 列，utf8mb4）
- [ ] 11.2 在 `db.changelog.xml` 中 include 新建表脚本
- [ ] 11.3 在 `LogDataCollectionName.MANAGEMENT_LOG` 的 `business_log` JSON 中新增 `"灵枢": "log_computing_resource_workspace_project"`
- [ ] 11.4 在 framework 的 `GetLogsMapper.xml` 的 `<sql id="tableName">` 白名单中新增 `<when test="tableName == 'log_computing_resource_workspace_project'">log_computing_resource_workspace_project</when>`

## Task 12: 验证

- [ ] 12.1 创建项目 → 验证 framework 数据库 `log_computing_resource_workspace_project` 表 newData 有项目详情
- [ ] 12.2 更新项目 → 验证 oldData + newData 都有值
- [ ] 12.3 删除项目 → 验证 oldData 有值，newData 为空
- [ ] 12.4 添加成员 → 验证 newData 只记录成功成员详情，0 成功时为空
- [ ] 12.5 删除成员 → 验证 oldData 有被删除成员信息
- [ ] 12.6 更新成员角色 → 验证 oldData + newData 角色变化
- [ ] 12.7 创建 API Key → 验证 newData 不含 keySecret/appCode
- [ ] 12.8 删除 API Key → 验证 oldData 不含 keySha256
- [ ] 12.9 操作失败 → 验证 logResult="失败"，params 保留入参
- [ ] 12.10 Feign 调用异常 → 验证业务不中断，WARN 日志输出
- [ ] 12.11 三方账号字段验证 → accountId / accountName / accountPlatform 正确填充（accountPlatform 从 UserContext 降级获取）
- [ ] 12.12 检查 `MANAGE_LOG` logger 输出，确认入湖字段与 framework 一致（11 字段）、日期格式 `yyyy-MM-dd HH:mm:ss`
- [ ] 12.13 管理中心日志页面 → 业务日志分类下有"灵枢"选项，可查询到审计日志（需 framework 侧 PR 合入后验证）
- [ ] 12.14 运行全量单元测试，确认无回归
