# 项目空间操作日志归入 openlibing 审计 - Tasks

## Task 1: 基础设施搭建

- [x] 1.1 新建 `RequestBodyCachingFilter`，包装 POST/PUT 请求为 `ContentCachingRequestWrapper`
- [x] 1.2 新建 `GetLogsMapper` 接口，定义 `insert` 方法
- [x] 1.3 新建 `GetLogsMapper.xml`，实现 insert SQL + tableName 白名单（新增 `log_workspace_project`）
- [x] 1.4 Apollo 配置中心补充 `success.code` 和 `openlibing.domain` 配置（与 framework 保持一致，通过 `@Value` 注入）
- [x] 1.5 数据库执行 DDL，创建 `log_workspace_project` 表及索引（Liquibase `project-tables.xml`）

## Task 2: 常量定义

- [x] 2.1 在 `LogOperationConstants` 中修改 `OPERATION_MODULE_WORKSPACE_PROJECT` 值为 `"灵枢"`（原为"项目空间"，改为"灵枢"以避免与 framework 的"项目空间管理"冲突）
- [x] 2.2 在 `LogOperationConstants` 中新增 `OPERATION_CREATE_MAAS_KEY = "CREATE_MAAS_KEY"`
- [x] 2.3 在 `LogOperationConstants` 中新增 `OPERATION_DELETE_MAAS_KEY = "DELETE_MAAS_KEY"`
- [x] 2.4 在 `LogOperationConstants` 中新增 `LOG_WORKSPACE_PROJECT = "log_workspace_project"`（Handler 注解和入湖用）

## Task 3: WorkspaceProjectLogHandler 实现

- [x] 3.1 新建 `WorkspaceProjectLogHandler`，继承 `AbstractLogHandler`
- [x] 3.2 实现 `@PostConstruct init()`，注册到 `LoggerAspect`（key = `OPERATION_MODULE_WORKSPACE_PROJECT`）
- [x] 3.3 实现 `getOldData()`：
  - CREATE_PROJECT / ADD_MEMBER / CREATE_API_KEY → 返回空
  - DELETE_PROJECT / UPDATE_PROJECT → 查 `projectSpaceMapper.selectById`
  - REMOVE_MEMBER / UPDATE_MEMBER_ROLE → 查 `projectMemberMapper.selectById`
  - DELETE_API_KEY → 查 `projectApiKeyMapper.selectById`，脱敏 keySha256
- [x] 3.4 实现 `encapsulatingLogsDetailVO()`：
  - 各操作类型设置 remark、isDetail、oldData、newData
  - 成功时 newData 从 DB 重新查询（确保数据一致性）
  - ADD_MEMBER 成功时：只记录成功成员详情（从 `successMemberIds` 查 DB），0 成功则 newData 为空
  - 失败时保留 params，过滤敏感字段
- [x] 3.5 实现 `saveLog()`：调用 `getLogsMapper.insert` + `ManageLogHelper.writeLog` 入湖
- [x] 3.6 实现辅助方法：参数提取（extractProjectId / extractMemberId / extractApiKeyId）、敏感信息过滤（sanitizeParams）

## Task 4: ServiceImpl 改造

- [x] 4.1 `ProjectSpaceServiceImpl.createProject` 加 `@LogApi` 注解，删除 `ManageLogHelper.writeLog` 调用
- [x] 4.2 `ProjectSpaceServiceImpl.deleteProject` 加 `@LogApi` 注解，删除 `ManageLogHelper.writeLog` 调用
- [x] 4.3 `ProjectSpaceServiceImpl.updateProject` 加 `@LogApi` 注解，删除 `ManageLogHelper.writeLog` 调用
- [x] 4.4 `ProjectSpaceServiceImpl.addMembers` 加 `@LogApi` 注解，删除 `ManageLogHelper.writeLog` 调用
- [x] 4.5 `ProjectSpaceServiceImpl.removeMember` 加 `@LogApi` 注解，删除 `ManageLogHelper.writeLog` 调用
- [x] 4.6 `ProjectSpaceServiceImpl.updateMemberRole` 加 `@LogApi` 注解，删除 `ManageLogHelper.writeLog` 调用
- [x] 4.7 `ApiKeyServiceImpl.createApiKey` 加 `@LogApi` 注解
- [x] 4.8 `ApiKeyServiceImpl.deleteApiKey` 加 `@LogApi` 注解

## Task 5: 入湖字段与格式对齐

- [x] 5.1 `ManageLogHelper.writeLog(String, LogsDetailVO)` 新增重载方法，入湖字段对齐 framework 的 11 个字段
- [x] 5.2 日期格式统一为 `yyyy-MM-dd HH:mm:ss`（`SimpleDateFormat`，与 framework 一致）
- [x] 5.3 入湖 `object_id` 保持小写 `o`（与 framework 实际一致）
- [x] 5.4 入湖只写 framework 标准字段，`old_data`/`new_data`/`params`/`remark` 等仅存 DB

## Task 6: 添加成员 DTO 与 Service 适配

- [x] 6.1 `AddMembersResultVo` 新增 `successMemberIds`（`List<Long>`）字段，存储成功添加的成员 ID
- [x] 6.2 `ProjectSpaceServiceImpl.processMemberAdditions` 在成功添加/恢复成员后收集 memberId 到 `successMemberIds`
- [x] 6.3 `insertNewMember` 方法改为返回 `ProjectMember`（获取 MyBatis-Plus 回填的 ID）
- [x] 6.4 `WorkspaceProjectLogHandler.extractAddMemberResult` 只取 `successMemberIds`，查 DB 获取成员详情写入 newData

## Task 7: Bean 扫描与配置

- [x] 7.1 `@ComponentScan` 增加 `com.openlibing.common.aspect` 包，确保 `LoggerAspect` Bean 被扫描到
- [x] 7.2 `application.yaml` 补充 `success.code` 和 `openlibing.domain` 默认值（生产环境由 Apollo 覆盖）

## Task 8: UT 适配

- [x] 8.1 `ProjectSpaceServiceImplTest` 补充 `successMemberIds` 断言（成功场景断言非空，失败场景断言空）
- [x] 8.2 Mock `projectMemberMapper.insert` 模拟 MyBatis-Plus ID 回填（`lenient().doAnswer`）
- [x] 8.3 `softDeletedMember` 测试数据补充 `setId(testMemberId)`

## Task 9: 验证

- [ ] 9.1 创建项目 → 验证 `log_workspace_project` 表 newData 有项目详情
- [ ] 9.2 更新项目 → 验证 oldData + newData 都有值
- [ ] 9.3 删除项目 → 验证 oldData 有值，newData 为空
- [ ] 9.4 添加成员 → 验证 newData 只记录成功成员详情，0 成功时为空
- [ ] 9.5 删除成员 → 验证 oldData 有被删除成员信息
- [ ] 9.6 更新成员角色 → 验证 oldData + newData 角色变化
- [ ] 9.7 创建 API Key → 验证 newData 不含 keySecret/appCode
- [ ] 9.8 删除 API Key → 验证 oldData 不含 keySha256
- [ ] 9.9 操作失败 → 验证 logResult="失败"，params 保留入参
- [ ] 9.10 检查 `MANAGE_LOG` logger 输出，确认入湖字段与 framework 一致（11 字段）、日期格式 `yyyy-MM-dd HH:mm:ss`
- [ ] 9.11 运行全量单元测试，确认无回归

## Task 10: Framework 侧注册（管理中心日志页面可查询）

> 前提：workspace 侧日志写入 `log_workspace_project` 表已正常工作。本 Task 在 framework 仓库操作，需单独提 PR。

- [ ] 10.1 在 `LogDataCollectionName.MANAGEMENT_LOG` 的 `business_log` JSON 中新增 `"灵枢": "log_workspace_project"`，使前端日志页面的业务日志分类下显示"灵枢"选项，点击后查询 `log_workspace_project` 表
- [ ] 10.2 在 framework 的 `GetLogsMapper.xml` 的 `<sql id="tableName">` 白名单中新增 `<when test="tableName == 'log_workspace_project'">log_workspace_project</when>`，使 MyBatis 动态表名查询可通过白名单校验
- [ ] 10.3 在管理中心前端日志页面验证：业务日志分类下出现"灵枢"选项，点击后可查询到 workspace 的审计日志
