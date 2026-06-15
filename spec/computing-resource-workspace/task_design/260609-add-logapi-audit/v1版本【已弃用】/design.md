# 项目空间操作日志归入 openlibing 审计 - Design

## 一、现状分析

### 当前日志方案

workspace 项目空间使用 `ManageLogHelper.writeLog()` 手动记录日志，仅写入 `MANAGE_LOG` logger（日志入湖）：

```java
ManageLogHelper.writeLog(LogOperationConstants.OPERATION_CREATE_PROJECT,
    LogOperationConstants.OBJECT_TYPE_PROJECT, LogOperationConstants.RESULT_SUCCESS,
    String.valueOf(projectSpace.getId()));
```

记录的信息仅包含：operationType、objectType、operationResult、objectId、operator、operatorIp。

### 目标方案

使用 `@LogApi` 注解 + AOP 切面，自动拦截并记录结构化审计日志，双写 DB + 入湖。

## 二、架构设计

### 整体流程

```
ServiceImpl 方法标注 @LogApi
        │
        ▼
LoggerAspect (AOP 切面)
  ├─ @Before: 记录开始时间 + 构建参数 Map → ThreadLocal
  ├─ @AfterReturning: 正常返回 → 查找 Handler → recordLogs()
  └─ @AfterThrowing: 异常 → 记录异常信息
        │
        ▼
WorkspaceProjectLogHandler (按 operationModule 分发)
  ├─ getOldData(): 查询操作前的旧数据
  ├─ encapsulatingLogsDetailVO(): 封装新旧数据、备注
  └─ saveLog(): 异步双写 DB + 入湖
```

### 鉴权兼容性

`AbstractLogHandler.encapsulatingInfoFromRequest` 从 `Cookie["token"]` 解析 JWT 获取用户信息。workspace 的 `OpenlibingAuthInterceptor` 同样从 `Cookie["token"]` 解析 JWT，字段名一致（`UserInfoConstants.FIELD_USER_ID` 等）。**无需额外适配**。

## 三、详细设计

### 3.1 新增：WorkspaceProjectLogHandler

继承 `AbstractLogHandler`，注册到 `LoggerAspect`，处理项目空间所有操作类型的日志。

```java
@Slf4j
@Component
public class WorkspaceProjectLogHandler extends AbstractLogHandler {
    @Autowired
    private GetLogsMapper getLogsMapper;

    @Autowired
    private ProjectSpaceMapper projectSpaceMapper;

    @Autowired
    private ProjectMemberMapper projectMemberMapper;

    @Autowired
    private ProjectApiKeyMapper projectApiKeyMapper;

    @PostConstruct
    public void init() {
        LoggerAspect logApiAspect = applicationContext.getBean(LoggerAspect.class);
        logApiAspect.registerLogHandler(OPERATION_MODULE_WORKSPACE_PROJECT, this);
    }
}
```

### 3.2 操作类型与日志策略

| 操作 | operation 常量 | getOldData | encapsulatingLogsDetailVO | 备注 |
|------|---------------|------------|--------------------------|------|
| 创建项目 | `CREATE_PROJECT` | 返回空 | newData=项目详情JSON | 新增无旧数据 |
| 删除项目 | `DELETE_PROJECT` | 查项目详情JSON | oldData=旧数据, newData=空 | 删除无新数据 |
| 更新项目 | `UPDATE_PROJECT` | 查项目详情JSON | oldData=旧数据, newData=新数据 | 新旧对比 |
| 添加成员 | `ADD_MEMBER` | 返回空 | newData=成员信息JSON | 批量添加记录总量 |
| 删除成员 | `REMOVE_MEMBER` | 查成员详情JSON | oldData=旧数据, newData=空 | |
| 更新成员角色 | `UPDATE_MEMBER_ROLE` | 查成员详情JSON | oldData=旧数据, newData=新数据 | 新旧对比 |
| 创建 MAAS Key | `CREATE_MAAS_KEY` | 返回空 | newData={keyUid, keyName} | 不含 keySecret |
| 删除 MAAS Key | `DELETE_MAAS_KEY` | 查Key信息JSON | oldData={keyUid, keyName}, newData=空 | 不含 keySha256 |

### 3.3 getOldData 实现

```java
@Override
protected String getOldData(String operation, Map<String, Object> paramsMap) {
    switch (operation) {
        case CREATE_PROJECT:
        case ADD_MEMBER:
        case CREATE_MAAS_KEY:
            return "";  // 新增操作无旧数据

        case DELETE_PROJECT:
        case UPDATE_PROJECT: {
            Integer projectId = extractProjectId(paramsMap);
            ProjectSpace project = projectSpaceMapper.selectById(projectId);
            return project != null ? JSON.toJSONString(project) : "";
        }

        case REMOVE_MEMBER:
        case UPDATE_MEMBER_ROLE: {
            Long memberId = extractMemberId(paramsMap);
            ProjectMember member = projectMemberMapper.selectById(memberId);
            return member != null ? JSON.toJSONString(member) : "";
        }

        case DELETE_MAAS_KEY: {
            Long keyId = extractApiKeyId(paramsMap);
            ProjectApiKey key = projectApiKeyMapper.selectById(keyId);
            if (key != null) {
                key.setKeySha256(null);  // 脱敏
                return JSON.toJSONString(key);
            }
            return "";
        }

        default:
            return "";
    }
}
```

**参数提取说明**：`paramsMap` 由 `LoggerAspect.doBefore` 构建，key 为方法参数名，value 为参数值。需要根据各方法的参数签名提取 projectId/memberId/keyId。

### 3.4 encapsulatingLogsDetailVO 实现（更新）

ADD_MEMBER 的 `newData` 只记录**成功添加的成员详情**，与 framework 的 `SpaceUserLogHandler.handleProjectUser` 保持一致：

```java
case ADD_MEMBER:
    logsDetailVO.setRemark("添加成员");
    if (isSuccess) {
        logsDetailVO.setIsDetail("true");
        logsDetailVO.setOldData("");
        logsDetailVO.setNewData(extractAddMemberResult(resultMap));
    }
    break;
```

`extractAddMemberResult` 从 `resultMap.data` 取 `AddMembersResultVo.successMemberIds`，查 DB 获取成员详情：

```java
private String extractAddMemberResult(Map resultMap) {
    Object data = resultMap.get("data");
    if (data instanceof AddMembersResultVo vo) {
        List<Long> memberIds = vo.getSuccessMemberIds();
        if (memberIds != null && !memberIds.isEmpty()) {
            List<ProjectMember> members = projectMemberMapper.selectBatchIds(memberIds);
            return JSON.toJSONString(members);
        }
    }
    return "";  // 0 成功时 newData 为空
}
```

**设计决策**：接口返回 200 就算成功，0 个成员成功也记录日志（newData 为空），与 framework 对齐。

### 3.5 saveLog 实现

```java
@Override
protected void saveLog(String tableName, LogsDetailVO logsDetailVO) {
    int insert = getLogsMapper.insert(logsDetailVO, tableName);
    if (insert != 1) {
        log.info("insert {} log error", tableName);
    }
    // 日志入湖
    ManageLogHelper.writeLog(tableName, logsDetailVO);
}
```

**入湖字段对齐**：`ManageLogHelper.writeLog(String, LogsDetailVO)` 将 `LogsDetailVO` 转换为 framework 标准的 11 字段 Map 入湖，字段和格式与 framework 保持一致：

| 入湖字段 | 来源 | 格式 |
|---------|------|------|
| `log_print_time` | `operationDate` | `yyyy-MM-dd HH:mm:ss`（`SimpleDateFormat`） |
| `operator_ip` | `operatorIp` | - |
| `operator` | `userName` | - |
| `operator_id` | `userId` | - |
| `operation_type` | `operation` | - |
| `operation_module` | `operationModule` | - |
| `operation_result` | `logResult` | 成功/失败 |
| `object_id` | `tableName` | 小写 `o` |
| `account_id` | `accountId` | - |
| `account_name` | `accountName` | - |
| `account_platform` | `accountPlatform` | - |

**不入湖的字段**：`old_data`、`new_data`、`params`、`remark`、`is_detail`、`log_code`、`log_message`、`ex_message`、`request_method`、`request_uri`、`request_time` 等，仅写入 DB。

### 3.6 @LogApi 注解使用

**ProjectSpaceServiceImpl**：

```java
@LogApi(tableName = "log_workspace_project",
    operationModule = OPERATION_MODULE_WORKSPACE_PROJECT,
    operation = CREATE_PROJECT)
public DataResult<ProjectSpace> createProject(CreateProjectRequest request) { ... }

@LogApi(tableName = "log_workspace_project",
    operationModule = OPERATION_MODULE_WORKSPACE_PROJECT,
    operation = DELETE_PROJECT)
public DataResult<Void> deleteProject(Integer projectId) { ... }

@LogApi(tableName = "log_workspace_project",
    operationModule = OPERATION_MODULE_WORKSPACE_PROJECT,
    operation = UPDATE_PROJECT)
public DataResult<Void> updateProject(Integer projectId, UpdateProjectRequest request) { ... }

@LogApi(tableName = "log_workspace_project",
    operationModule = OPERATION_MODULE_WORKSPACE_PROJECT,
    operation = ADD_MEMBER)
public DataResult<AddMembersResultVo> addMembers(Integer projectId, AddMemberRequest request) { ... }

@LogApi(tableName = "log_workspace_project",
    operationModule = OPERATION_MODULE_WORKSPACE_PROJECT,
    operation = REMOVE_MEMBER)
public DataResult<Void> removeMember(Long memberId) { ... }

@LogApi(tableName = "log_workspace_project",
    operationModule = OPERATION_MODULE_WORKSPACE_PROJECT,
    operation = UPDATE_MEMBER_ROLE)
public DataResult<Void> updateMemberRole(Long memberId, String role) { ... }
```

**ApiKeyServiceImpl**：

```java
@LogApi(tableName = "log_workspace_project",
    operationModule = OPERATION_MODULE_WORKSPACE_PROJECT,
    operation = CREATE_MAAS_KEY)
public DataResult<ApiKeyVo> createApiKey(Integer projectId, CreateApiKeyRequest request) { ... }

@LogApi(tableName = "log_workspace_project",
    operationModule = OPERATION_MODULE_WORKSPACE_PROJECT,
    operation = DELETE_MAAS_KEY)
public DataResult<Void> deleteApiKey(Long keyId) { ... }
```

### 3.7 新增：GetLogsMapper

参照 framework 的 `GetLogsMapper`，实现日志表 insert + 查询。XML 中 tableName 白名单新增 `log_workspace_project`。

```java
@Mapper
public interface GetLogsMapper {
    int insert(@Param("groupLog") LogsDetailVO groupLog, @Param("tableName") String tableName);
}
```

### 3.8 新增：RequestBodyCachingFilter

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class RequestBodyCachingFilter extends OncePerRequestFilter {
    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response,
        FilterChain filterChain) throws ServletException, IOException {
        if ("POST".equals(request.getMethod()) || "PUT".equals(request.getMethod())) {
            ContentCachingRequestWrapper wrappedRequest = new ContentCachingRequestWrapper(request);
            filterChain.doFilter(wrappedRequest, response);
        } else {
            filterChain.doFilter(request, response);
        }
    }
}
```

### 3.9 常量补充

在 `LogOperationConstants` 中新增：

```java
/** Operation module for workspace project. */
public static final String OPERATION_MODULE_WORKSPACE_PROJECT = "灵枢";

/** Operation type for creating MAAS Key. */
public static final String OPERATION_CREATE_MAAS_KEY = "CREATE_MAAS_KEY";

/** Operation type for deleting MAAS Key. */
public static final String OPERATION_DELETE_MAAS_KEY = "DELETE_MAAS_KEY";

/** Log table name for workspace project. */
public static final String LOG_WORKSPACE_PROJECT = "log_workspace_project";
```

### 3.10 AddMembersResultVo 适配

新增 `successMemberIds` 字段，用于 Handler 提取成功添加的成员 ID：

```java
// AddMembersResultVo 新增字段
private List<Long> successMemberIds = new ArrayList<>();

public void addSuccessMemberId(Long memberId) {
    successMemberIds.add(memberId);
}
```

**设计决策**：`failedMembers` 和 `successCount` 保留不动（前端在用），新增 `successMemberIds` 仅供审计日志使用。`ProjectSpaceServiceImpl.insertNewMember` 改为返回 `ProjectMember`（获取 MyBatis-Plus 回填的 ID），在 `processMemberAdditions` 中成功添加/恢复成员后收集 memberId。

### 3.11 Bean 扫描补充

workspace 的 `@ComponentScan` 原本只配置了 `com.openlibing.common.config`，需要增加 `com.openlibing.common.aspect` 以确保 `LoggerAspect` Bean 被扫描到，否则启动报 `BeanCreationException`。

### 3.12 配置补充

`AbstractLogHandler` 通过 `@Value` 注入以下配置项，与 framework 保持一致，在 Apollo 配置中心添加：

| 配置项 | 值 | 说明 |
|--------|---|------|
| `success.code` | `200` | 与 `DataResult.success()` 的 code 值一致，用于判断操作成功/失败 |
| `openlibing.domain` | `https://<workspace域名>` | 入湖数据的 host 字段 |

framework 的这两个配置也在 Apollo 中，不在本地 yaml。

### 3.11 数据库建表

```sql
CREATE TABLE log_workspace_project (
    id VARCHAR(64) PRIMARY KEY,
    operation_date DATETIME,
    log_code VARCHAR(32),
    operation_module VARCHAR(64),
    user_name VARCHAR(128),
    user_id VARCHAR(64),
    operation VARCHAR(64),
    old_data TEXT,
    new_data TEXT,
    remark VARCHAR(256),
    log_message VARCHAR(512),
    is_detail VARCHAR(8),
    ex_message TEXT,
    params TEXT,
    account_id VARCHAR(64),
    account_platform VARCHAR(32),
    log_result VARCHAR(16),
    account_name VARCHAR(128)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='项目空间审计日志表';

CREATE INDEX idx_log_ws_project_date ON log_workspace_project(operation_date);
CREATE INDEX idx_log_ws_project_user ON log_workspace_project(user_id);
CREATE INDEX idx_log_ws_project_operation ON log_workspace_project(operation);
```

## 四、敏感信息脱敏策略

| 数据 | 脱敏处理 |
|------|---------|
| API Key 的 keySecret | 创建时 newData 中不包含 keySecret，仅记录 keyUid + keyName |
| API Key 的 keySha256 | 旧数据/新数据中置 null |
| API Key 的 appCode | 不记录 |
| 请求入参 params | 失败时保留，但过滤 keySecret/keySha256/appCode 字段 |

## 五、涉及文件清单

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `WorkspaceProjectLogHandler.java` | 新增 | 项目空间日志 Handler |
| `GetLogsMapper.java` | 新增 | 日志表 Mapper 接口 |
| `GetLogsMapper.xml` | 新增 | 日志表 Mapper XML（insert + 查询） |
| `RequestBodyCachingFilter.java` | 新增 | Request Body 缓存 Filter |
| `ProjectSpaceServiceImpl.java` | 修改 | 加 @LogApi 注解 + 删除 ManageLogHelper 调用 + insertNewMember 返回 ProjectMember + 收集 successMemberIds |
| `ApiKeyServiceImpl.java` | 修改 | 加 @LogApi 注解 |
| `AddMembersResultVo.java` | 修改 | 新增 `successMemberIds` 字段 |
| `LogOperationConstants.java` | 修改 | 补充 operationModule + API Key 操作常量 + LOG_WORKSPACE_PROJECT |
| `ManageLogHelper.java` | 修改 | 新增 `writeLog(String, LogsDetailVO)` 重载方法，入湖字段对齐 framework |
| `application.yaml` | 修改 | 补充 success.code + openlibing.domain 默认值 |
| `WorkspaceApplication.java` | 修改 | @ComponentScan 增加 `com.openlibing.common.aspect` |
| `project-tables.xml` | 修改 | Liquibase DDL：创建 `log_workspace_project` 表及索引 |
| `ProjectSpaceServiceImplTest.java` | 修改 | UT 适配 successMemberIds 断言 |

## 六、Framework 侧注册（管理中心日志页面可查询）

workspace 的日志写入 `log_workspace_project` 表后，若要在管理中心前端日志页面查询到，需在 framework 侧完成两处注册：

### 6.1 LogDataCollectionName.MANAGEMENT_LOG 注册

**文件**：`com.openlibing.framework.common.log.LogDataCollectionName`

在 `MANAGEMENT_LOG` 常量的 `business_log` JSON 中新增：

```json
"灵枢": "log_workspace_project"
```

**作用**：`LoggingServiceImpl.getLogConfig(flag, operationModule)` 解析此 JSON，根据前端传的 `operationModule="灵枢"` 找到表名 `log_workspace_project`，然后查询该表。前端日志页面的业务日志分类下会显示"灵枢"选项。

**调用链路**：
```
前端选择"业务日志" → 选择"灵枢"模块
    → LoggingServiceImpl.getLoggingDetail(flag="2", operationModule="灵枢")
    → getLogConfig("2", "灵枢") → 解析 MANAGEMENT_LOG → 得到 "log_workspace_project"
    → GetLogsMapper.getTableShardLogslist(tableName="log_workspace_project", ...)
    → MyBatis <choose> 白名单匹配 → 执行 SQL 查询
```

### 6.2 GetLogsMapper.xml 白名单注册

**文件**：`com.openlibing.framework.business.mapper.GetLogsMapper`（对应 XML：`GetLogsMapper.xml`）

在 `<sql id="tableName">` 的 `<choose>` 中新增：

```xml
<when test="tableName == 'log_workspace_project'">
    log_workspace_project
</when>
```

**作用**：MyBatis 动态表名白名单，防止 SQL 注入。`tableName` 参数只有匹配到某个 `<when>` 条件才会被拼入 SQL，否则返回空导致查询失败。

**注意**：workspace 自身的 `GetLogsMapper.xml` 已有此白名单（用于 insert），但 framework 的 `GetLogsMapper.xml` 是独立的（用于查询），需要单独添加。

## 七、风险点

| 风险 | 应对 |
|------|------|
| `DataResult` 序列化为 Map 时 `code` 字段名不一致 | 验证 fastjson2 序列化 `DataResult` 后 `code` 字段是否为 Integer 类型，与 `success.code` 配置匹配 |
| `paramsMap` 中参数名与预期不符 | `LoggerAspect.doBefore` 使用 `DefaultParameterNameDiscoverer` 获取参数名，需确认编译时保留参数名（`-parameters` 编译选项） |
| 添加成员是批量操作，newData 如何记录 | 与 framework 对齐：只记录成功添加的成员详情（从 `successMemberIds` 查 DB），0 成功时 newData 为空 |
| `LoggerAspect` Bean 未被扫描 | `@ComponentScan` 需包含 `com.openlibing.common.aspect` 包 |
| 日期格式不一致 | 入湖日期统一使用 `SimpleDateFormat("yyyy-MM-dd HH:mm:ss")`，与 framework 保持一致 |
| framework 侧注册需单独提 PR | `LogDataCollectionName.MANAGEMENT_LOG` 和 `GetLogsMapper.xml` 属于 framework 仓库代码，需在 framework 仓单独提 PR，与 workspace 仓的 PR 独立 |

## 八、验证方式

1. 创建项目 → 查 `log_workspace_project` 表，验证 newData 有项目详情
2. 更新项目 → 验证 oldData + newData 都有值且内容正确
3. 删除项目 → 验证 oldData 有值，newData 为空
4. 添加成员 → 验证 newData 记录添加结果
5. 创建 API Key → 验证 newData 不含 keySecret
6. 操作失败 → 验证 logResult="失败"，params 保留入参
7. 检查 `MANAGE_LOG` logger 输出，确认入湖数据完整
