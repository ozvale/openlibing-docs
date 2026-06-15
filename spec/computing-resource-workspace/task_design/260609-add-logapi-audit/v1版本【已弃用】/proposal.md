# 项目空间操作日志归入 openlibing 审计 - Proposal

## 一、需求背景

当前 workspace 项目空间的操作日志采用手动调用 `ManageLogHelper.writeLog()` 的方式，仅写入日志入湖（JSON 到 `MANAGE_LOG` logger），未纳入 openlibing 统一审计体系，存在以下不足：

1. **无数据库落库**：日志仅入湖，无法在平台前端查询审计记录
2. **无新旧数据对比**：无法追溯操作前后的数据变化
3. **信息不完整**：缺少操作人三方账号、请求耗时、HTTP 方法/URI 等结构化字段
4. **手动调用易遗漏**：每个写操作方法需手动插入日志代码，容易遗漏或参数不一致

framework 已有成熟的 `@LogApi` 注解 + AOP 切面方案，实现了自动拦截、结构化记录、DB 双写 + 入湖，是 openlibing 审计体系的标准接入方式。本次改造将项目空间模块的操作日志归入 openlibing 审计体系，使用 `@LogApi` 方案替代手动调用，使项目空间操作日志可在管理中心统一查询和审计。

## 二、改造范围

- `ProjectSpaceServiceImpl`：6 个写操作方法加 `@LogApi` 注解，删除原 `ManageLogHelper.writeLog()` 调用
- `ApiKeyServiceImpl`：2 个写操作方法加 `@LogApi` 注解（当前无日志，补齐）
- `WorkspaceProjectLogHandler`（新增）：继承 `AbstractLogHandler`，实现项目空间模块的日志处理
- `GetLogsMapper`（新增）：日志表 insert + 查询
- `RequestBodyCachingFilter`（新增）：支持 AOP 读取 request body
- `LogOperationConstants`：补充 `operationModule` 常量（值为 `"灵枢"`，避免与 framework 的"项目空间管理"冲突）
- Apollo 配置中心：补充 `success.code`、`openlibing.domain` 配置
- 数据库：新建 `log_workspace_project` 日志表

**Framework 侧（需单独提 PR）**：

- `LogDataCollectionName.MANAGEMENT_LOG`：在 `business_log` JSON 中新增 `"灵枢": "log_workspace_project"`，使管理中心日志页面可查询
- `GetLogsMapper.xml`：在 `<sql id="tableName">` 白名单中新增 `log_workspace_project`，使 MyBatis 动态表名查询可通过校验

## 三、验收标准

### 功能验收

- [ ] 创建项目：记录操作人、新数据（项目详情 JSON）
- [ ] 删除项目：记录操作人、旧数据（删除前项目详情 JSON）
- [ ] 更新项目：记录操作人、旧数据 + 新数据
- [ ] 添加成员：记录操作人、新数据（仅成功添加的成员详情 JSON，0 成功时为空）
- [ ] 删除成员：记录操作人、旧数据（被删除成员信息）
- [ ] 更新成员角色：记录操作人、旧数据 + 新数据
- [ ] 创建 MAAS Key：记录操作人、新数据（keyUid + keyName，不含 keySecret）
- [ ] 删除 MAAS Key：记录操作人、旧数据（被删除 Key 信息，不含 keySha256）
- [ ] 日志正确写入 `log_workspace_project` 表
- [ ] 日志正确入湖（`MANAGE_LOG` logger），字段与 framework 一致（11 标准字段）
- [ ] 入湖日期格式 `yyyy-MM-dd HH:mm:ss`，与 framework 保持一致
- [ ] 操作失败时日志记录为"失败"，保留入参信息
- [ ] 原 `ManageLogHelper.writeLog()` 调用已全部移除
- [ ] `AddMembersResultVo.successMemberIds` 正确收集成功成员 ID

### 非功能验收

- [ ] 日志落库为异步执行（`CompletableFuture.runAsync`），不阻塞业务请求
- [ ] MAAS Key 相关日志中不包含 keySecret、keySha256 等敏感信息
- [ ] 现有单元测试全部通过
- [ ] `@ComponentScan` 包含 `com.openlibing.common.aspect`，`LoggerAspect` Bean 正常加载
- [ ] 管理中心日志页面的业务日志分类下可看到"灵枢"选项，点击后可查询到 workspace 审计日志（需 framework 侧 PR 合入后验证）

## 四、约束

- 不修改 `AbstractLogHandler`、`LoggerAspect`、`LogApi` 等 common 包代码
- 不修改前端接口契约（入参/出参不变）
- 不修改 `DataResult` 返回结构
- 日志表结构复用 framework 的 `log_*` 表标准字段，不新增自定义字段
- 本次只做项目空间模块（ProjectSpace + ApiKey），不涉及 Env/Task/Maas 模块
- framework 侧的 `LogDataCollectionName` 和 `GetLogsMapper.xml` 修改需单独提 PR，不纳入 workspace 仓的 PR
