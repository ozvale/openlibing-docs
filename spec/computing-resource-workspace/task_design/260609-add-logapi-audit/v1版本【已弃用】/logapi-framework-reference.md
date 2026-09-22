# LogApi 审计日志框架实现参考

本文档总结 openlibing-common + openlibing-framework 中 LogApi 审计日志的完整实现方式，供后续新模块接入参考。

---

## 1. 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│  openlibing-common（公共依赖包）                               │
│                                                              │
│  @LogApi 注解         定义注解属性（表名、模块、操作类型等）       │
│  LoggerAspect         AOP 切面，拦截 @LogApi 方法              │
│  AbstractLogHandler   抽象 Handler，封装通用逻辑                │
│  RecordLogsDTO        切面 → Handler 的数据传输对象             │
│  LogsDetailVO         日志详情 VO，最终落库/入湖的数据结构        │
│  JwtUtils             JWT 解析工具                             │
│  UserInfoConstants    JWT 字段名常量                            │
└─────────────────────────────────────────────────────────────┘
        ↕ 依赖
┌─────────────────────────────────────────────────────────────┐
│  openlibing-framework（业务服务）                              │
│                                                              │
│  XxxLogHandler       具体 Handler 实现（按模块拆分）            │
│  GetLogsMapper       日志表 Mapper（insert + 查询）            │
│  GetLogsMapper.xml   Mapper XML（动态表名 + CRUD）             │
│  ManageLogHelper     日志入湖工具类                            │
│  LogDataCollectionName   日志表名常量                          │
│  LogOperationAndModule   操作模块 + 操作类型常量                │
│  ServiceImpl         业务方法标注 @LogApi                      │
└─────────────────────────────────────────────────────────────┘
```

---

## 2. common 层核心类

### 2.1 @LogApi 注解

**位置**：`com.openlibing.common.aspect.logapi.LogApi`

```java
@Target(ElementType.METHOD)
@Retention(RetentionPolicy.RUNTIME)
@Documented
public @interface LogApi {
    String tableName();                          // 日志落库表名（必填）
    String operationModule();                    // 操作模块（必填，如"项目"、"用户管理"）
    String operation();                          // 操作类型（必填，如"新增项目"）
    String projectNamePath()  default "2";       // 方法参数中项目名的路径
    String projectName()      default "projectName";
    String repoNamePath()     default "2";
    String repoName()         default "repoName";
    String branchNamePath()   default "2";
    String branchName()       default "branchName";
    String remarkPath()       default "2";       // 备注参数路径
    String remark()           default "remark";
    boolean isExport()        default false;     // 是否导出操作
    boolean isBackData()      default false;     // 是否记录返回数据
    boolean isSendAlarm()     default false;     // 是否发送告警
    String sendAlarmTopicUrn() default "";       // 告警主题URN
}
```

**关键属性说明**：

| 属性 | 必填 | 说明 |
|------|------|------|
| `tableName` | 是 | 日志表名，对应 `GetLogsMapper.xml` 白名单中的表 |
| `operationModule` | 是 | 操作模块名，同时是 Handler 注册到 `LoggerAspect.logHandlerMap` 的 key |
| `operation` | 是 | 操作类型，Handler 内按此字段分发不同逻辑 |
| `remarkPath` | 否 | 方法参数中备注字段的类全限定名，`"2"` 表示不提取 |
| `isBackData` | 否 | `true` 时跳过 `externalDataLogInfo`（备注提取），由 Handler 自行封装 |

### 2.2 LoggerAspect 切面

**位置**：`com.openlibing.common.aspect.logapi.LoggerAspect`

**核心结构**：

```java
@Aspect
@Component
public class LoggerAspect {
    // Handler 注册表：key=operationModule, value=AbstractLogHandler
    private final HashMap<String, AbstractLogHandler> logHandlerMap = new HashMap<>();

    // ThreadLocal 存储
    private static final ThreadLocal<Map<String, Object>> PARAMS_MAP;  // 方法参数名→值
    private static final ThreadLocal<Long> START_TIME;                  // 请求开始时间

    // 切点：空方法，供子类扩展或直接使用
    @Pointcut("@annotation(com.openlibing.common.aspect.logapi.LogApi)")
    public void serviceLogging() {}

    @Before("serviceLogging()")
    public void doBefore(JoinPoint joinPoint) {
        // 1. 记录开始时间
        // 2. 使用 DefaultParameterNameDiscoverer 获取方法参数名
        // 3. 构建 paramsMap（参数名→参数值）存入 ThreadLocal
    }

    @AfterReturning(pointcut = "serviceLogging()", returning = "result")
    public void doAfterReturning(JoinPoint joinPoint, Object result) {
        // 1. 从 @LogApi 注解获取 operationModule
        // 2. 从 logHandlerMap 查找对应 Handler
        // 3. 调用 handler.getOldDataJsonString() 获取旧数据
        // 4. 构建 RecordLogsDTO（args + resultMap + oldDataJsonString + paramsMap + startTime）
        // 5. 调用 handler.recordLogs(recordLogsDTO, logApi)
    }

    @AfterThrowing(pointcut = "serviceLogging()", throwing = "ex")
    public void doAfterThrowing(JoinPoint joinPoint, Exception ex) {
        // 记录异常信息到日志
    }

    // Handler 注册方法
    public void registerLogHandler(String operationModule, AbstractLogHandler handler) {
        logHandlerMap.put(operationModule, handler);
    }
}
```

**关键行为**：

- `doBefore`：使用 `DefaultParameterNameDiscoverer` 获取方法参数名，构建 `paramsMap`。**要求编译时保留参数名**（`-parameters` 编译选项）。
- `doAfterReturning`：将方法返回值通过 fastjson2 序列化为 `Map`（`resultMap`），从中提取 `code`/`msg`/`data` 字段。
- `doAfterThrowing`：仅记录日志，不调用 Handler。

### 2.3 AbstractLogHandler 抽象类

**位置**：`com.openlibing.common.aspect.logapi.AbstractLogHandler`

**三个抽象方法**：

```java
// 获取操作前的旧数据 JSON
protected abstract String getOldData(String operation, Map<String, Object> paramsMap);

// 封装日志详情（新旧数据、备注等）
protected abstract void encapsulatingLogsDetailVO(String operation,
    String oldDataJsonString, LogsDetailVO logsDetailVO, Map resultMap);

// 保存日志（DB + 入湖）
protected abstract void saveLog(String tableName, LogsDetailVO logsDetailVO);
```

**主流程方法 `recordLogs()`**：

```java
public void recordLogs(RecordLogsDTO recordLogsDTO, LogApi logApi) {
    // 1. 获取 HttpServletRequest
    // 2. 封装关键信息 → LogsDetailVO
    //    ├─ encapsulatingBasic(): UUID、时间、模块、操作、状态码、成功/失败
    //    ├─ encapsulatingInfoFromRequest(): 从 Cookie["token"] 解析 JWT → userId/userName/accountId/accountPlatform/accountName
    //    └─ encapsulatingDataLakeInfo(): 入湖额外数据（请求方式、URL、UA、域名等）
    // 3. 如果 !isBackData，提取备注信息
    // 4. 调用 encapsulatingLogsDetailVO()（子类实现）
    // 5. 截取 params 到 400 字符
    // 6. 异步保存：CompletableFuture.runAsync(() -> saveLog())
}
```

**通用逻辑详解**：

#### encapsulatingBasic — 封装基本信息

- 生成 UUID 作为日志 ID
- 从 `@LogApi` 注解读取 `operationModule`、`operation`
- 从 `resultMap` 提取 `code`/`msg`/`exMessage`
- 根据 `success.code` 配置判断成功/失败：
  - 成功：`logResult="成功"`，**清空 params**（有新旧数据可追溯）
  - 失败：`logResult="失败"`，保留 params

#### encapsulatingInfoFromRequest — 从请求获取用户信息

```java
// 从 Cookie 中找 "token"
for (Cookie cookie : request.getCookies()) {
    if ("token".equals(cookie.getName())) {
        token = cookie.getValue();
    }
}
// 从 JWT 中提取
String userId = JwtUtils.getClaimByName(token, FIELD_USER_ID).as(String.class);
String userName = JwtUtils.getClaimByName(token, FIELD_USER_NAME).as(String.class);
String accountId = JwtUtils.getClaimByName(token, FIELD_ACCOUNT_ID).as(String.class);
String accountPlatform = JwtUtils.getClaimByName(token, FIELD_ACCOUNT_PLATFORM).as(String.class);
String accountName = JwtUtils.getClaimByName(token, FIELD_ACCOUNT_NAME).as(String.class);
```

**注意**：如果 Cookie 中没有 `token`，所有用户信息字段都会为 null。

#### encapsulatingDataLakeInfo — 封装入湖数据

额外记录：requestMethod、requestUri、requestLength、httpUserAgent、host、upstreamAddr、timeLocal、serverProtocol、contentType、scheme、httpXForwardedFor。入湖标识 `logLakeData` 为 `"success"` 或 `"failure"`。

#### paramValue — 从方法参数中提取值

```java
protected String paramValue(String paramPath, String paramName, List<Object> args) {
    // paramPath = "2" → 返回空（表示不提取）
    // paramPath = 类全限定名 → 遍历 args 找到该类型的参数
    //   paramName 为空 → 返回整个对象的 JSON
    //   paramName 非空 → 返回对象中指定字段的值
}
```

### 2.4 RecordLogsDTO

**位置**：`com.openlibing.common.pojo.dto.RecordLogsDTO`

| 字段 | 类型 | 说明 |
|------|------|------|
| `args` | `List<Object>` | 方法参数列表 |
| `resultMap` | `Map` | 方法返回值（fastjson2 序列化为 Map） |
| `oldDataJsonString` | `String` | 旧数据 JSON |
| `paramsMap` | `Map<String, Object>` | 方法参数名→值映射 |
| `startTime` | `long` | 请求开始时间 |

### 2.5 LogsDetailVO

**位置**：`com.openlibing.common.pojo.vo.LogsDetailVO`

**核心字段**（对应日志表列）：

| 字段 | 数据库列 | 说明 |
|------|---------|------|
| `id` | `id` | UUID |
| `operationDate` | `operation_date` | 操作时间 |
| `logCode` | `log_code` | 接口返回码 |
| `logResult` | `log_result` | "成功"/"失败" |
| `operationModule` | `operation_module` | 操作模块 |
| `userName` | `user_name` | 操作人用户名 |
| `userId` | `user_id` | 操作人用户ID |
| `operation` | `operation` | 操作类型 |
| `oldData` | `old_data` | 操作前数据 JSON |
| `newData` | `new_data` | 操作后数据 JSON |
| `remark` | `remark` | 备注 |
| `logMessage` | `log_message` | 接口返回消息 |
| `isDetail` | `is_detail` | 是否有详情 |
| `params` | `params` | 请求入参（失败时保留） |
| `accountId` | `account_id` | 三方账号ID |
| `accountPlatform` | `account_platform` | 三方账号平台 |
| `accountName` | `account_name` | 三方账号名 |
| `operatorIp` | — | 操作IP（不入库，仅入湖） |
| `requestMethod` | — | HTTP 方法（仅入湖） |
| `requestUri` | — | 请求 URI（仅入湖） |
| `requestTime` | — | 请求耗时 ms（仅入湖） |
| `host` | — | 域名（仅入湖） |
| `logLakeData` | — | 入湖标识（仅入湖） |

---

## 3. framework 层实现

### 3.1 Handler 实现模式

framework 中有 20 个 Handler，每个对应一个操作模块。核心模式一致：

```java
@Slf4j
@Component
public class XxxLogHandler extends AbstractLogHandler {
    @Autowired
    GetLogsMapper getLogsMapper;

    @Autowired
    XxxMapper xxxMapper;  // 业务 Mapper，用于查旧数据

    @PostConstruct
    public void init() {
        LoggerAspect logApiAspect = applicationContext.getBean(LoggerAspect.class);
        logApiAspect.registerLogHandler(OPERATION_MODULE_XXX, this);
    }

    @Override
    protected String getOldData(String operation, Map<String, Object> paramsMap) {
        // 按 operation 分发，查 DB 获取旧数据
    }

    @Override
    protected void encapsulatingLogsDetailVO(String operation, String oldDataJsonString,
        LogsDetailVO logsDetailVO, Map resultMap) {
        // 按 operation 分发，设置 remark/isDetail/oldData/newData
        // 成功时：从 resultMap 或重新查库获取新数据
        // 失败时：保留 params，过滤敏感字段
    }

    @Override
    protected void saveLog(String tableName, LogsDetailVO logsDetailVO) {
        getLogsMapper.insert(logsDetailVO, tableName);
        ManageLogHelper.writeLog(tableName, logsDetailVO);
    }
}
```

**典型 Handler 列表**：

| Handler | operationModule | 日志表 |
|---------|----------------|--------|
| `ProjectLogHandler` | "项目" | `log_project` |
| `SpaceUserLogHandler` | "项目与仓库成员管理" | `log_space_permission` |
| `PermissionRoleLogHandler` | "角色管理" | `log_permission_config` |
| `CmcLogHandler` | "技术委员会管理" | `log_cmc_info` |
| `WikiLogHandler` | "帮助文档" | `log_wiki` |
| `IamLogHandler` | "账号纳管" | `log_iam_info` |
| `ToolInfoLogHandler` | "工具管理" | `log_tool` |

### 3.2 getOldData 常见模式

```java
// 模式1：新增操作 → 返回空
if (ADD_XXX.equals(operation)) {
    return "";
}

// 模式2：修改/删除操作 → 从 paramsMap 提取 ID → 查库
if (UPDATE_XXX.equals(operation) || DELETE_XXX.equals(operation)) {
    Integer id = Integer.valueOf(String.valueOf(paramsMap.get("id")));
    XxxEntity entity = xxxMapper.selectById(id);
    return entity != null ? JSON.toJSONString(entity) : "";
}

// 模式3：特殊操作 → 用 oldData 字段临时封装 remark
if (SYNC_XXX.equals(operation)) {
    return "手动同步XXX的成员";  // 在 encapsulatingLogsDetailVO 中赋给 remark
}
```

**paramsMap 的 key**：由 `LoggerAspect.doBefore` 使用 `DefaultParameterNameDiscoverer` 获取的方法参数名。例如方法签名 `updateProject(Integer projectId, UpdateProjectRequest request)` → `paramsMap` 包含 `"projectId"` 和 `"request"` 两个 key。

### 3.3 encapsulatingLogsDetailVO 常见模式

```java
String logCode = logsDetailVO.getLogCode();
boolean isSuccess = String.valueOf(ResultStatusConstant.SUCCESS.getCode()).equals(logCode);

// 新增操作
if (ADD_XXX.equals(operation)) {
    logsDetailVO.setRemark("新增XXX");
    if (isSuccess) {
        logsDetailVO.setIsDetail("true");
        logsDetailVO.setOldData("");
        // 从 resultMap.data 获取新数据 ID，重新查库
        Integer id = (Integer) resultMap.get("data");
        logsDetailVO.setNewData(JSON.toJSONString(xxxMapper.selectById(id)));
    } else {
        // 失败时过滤敏感字段
        logsDetailVO.setParams(sanitizeParams(logsDetailVO.getParams()));
    }
    return;
}

// 修改操作
if (UPDATE_XXX.equals(operation)) {
    logsDetailVO.setRemark("修改XXX");
    if (isSuccess) {
        logsDetailVO.setIsDetail("true");
        logsDetailVO.setOldData(oldDataJsonString);
        // 从 oldDataJsonString 提取 ID，重新查库获取新数据
        JSONObject jsonObj = JSONObject.parseObject(oldDataJsonString);
        Integer id = (Integer) jsonObj.get("id");
        logsDetailVO.setNewData(JSON.toJSONString(xxxMapper.selectById(id)));
    }
    return;
}

// 删除操作
if (DELETE_XXX.equals(operation)) {
    logsDetailVO.setRemark("删除XXX");
    if (isSuccess) {
        logsDetailVO.setIsDetail("true");
        logsDetailVO.setOldData(oldDataJsonString);
        logsDetailVO.setNewData("");
    }
}
```

### 3.4 GetLogsMapper

**接口**：`com.openlibing.framework.business.mapper.GetLogsMapper`

```java
@Mapper
public interface GetLogsMapper {
    int insert(@Param("groupLog") LogsDetailVO groupLog, @Param("tableName") String tableName);
    List<LogsDetailVO> getTableShardLogslist(@Param("loggingModel") LoggingModel loggingModel,
        @Param("tableName") String tableName, @Param("start") int start, @Param("pageSize") int pageSize);
    long countTableShardLogs(@Param("loggingModel") LoggingModel loggingModel, @Param("tableName") String tableName);
    List<LogsDetailVO> getCombinedLogs(@Param("tables") List<String> tables,
        @Param("loggingModel") LoggingModel loggingModel, @Param("start") int start, @Param("pageSize") int pageSize);
    long countCombinedLogs(@Param("tables") List<String> tables, @Param("loggingModel") LoggingModel loggingModel);
    LogSpecificVO getSpecificLogDetail(@Param("logId") String logId, @Param("tableName") String tableName);
    List<String> getLogOperations(@Param("tableName") String tableName);
}
```

**XML 关键设计**：

- **动态表名**：通过 `<choose>` 白名单实现，防止 SQL 注入
- **insert**：所有 `log_*` 表结构一致，insert 语句通用
- **查询**：支持按操作类型、时间范围、用户ID、三方账号、执行结果、数据内容、备注等条件筛选
- **合并查询**：`UNION ALL` 跨多表分页查询

### 3.5 ManageLogHelper（framework 版）

**位置**：`com.openlibing.framework.common.utils.ManageLogHelper`

```java
public static void writeLog(String tableName, LogsDetailVO logsDetailVO) {
    Map<String, Object> entity = convertToManageLogLakeEntity(logsDetailVO);
    entity.put("Object_id", tableName);
    MANAGE_LOG_LOGGER.info(JSON.toJSONString(entity, NULL_TO_EMPTY_STRING_FILTER, JSONWriter.Feature.WriteNulls));
}
```

将 `LogsDetailVO` 转换为入湖格式的 Map，写入 `MANAGE_LOG` logger。入湖字段与 DB 字段不完全一致（如 `operator` 对应 `accountId`，`object_type` 对应 `operationModule`）。

### 3.6 常量定义

**LogDataCollectionName**：日志表名常量 + `MANAGEMENT_LOG` JSON 配置（模块名→表名映射，用于前端查询）

**LogOperationAndModule**：操作模块常量（如 `OPERATION_MODULE_PROJECT = "项目"`）+ 操作类型常量（如 `ADD_PROJECT = "新增项目"`）

---

## 4. 接入新模块的步骤

### Step 1：定义常量

```java
// 在常量类中新增
public static final String OPERATION_MODULE_XXX = "XXX模块";
public static final String ADD_XXX = "新增XXX";
public static final String UPDATE_XXX = "修改XXX";
public static final String DELETE_XXX = "删除XXX";
public static final String XXX_LOG = "log_xxx";
```

### Step 2：建表

```sql
CREATE TABLE log_xxx (
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
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
```

### Step 3：GetLogsMapper.xml 白名单

在 `<sql id="tableName">` 的 `<choose>` 中新增：

```xml
<when test="tableName == 'log_xxx'">
    log_xxx
</when>
```

### Step 4：创建 Handler

```java
@Slf4j
@Component
public class XxxLogHandler extends AbstractLogHandler {
    @Autowired private GetLogsMapper getLogsMapper;
    @Autowired private XxxMapper xxxMapper;

    @PostConstruct
    public void init() {
        LoggerAspect logApiAspect = applicationContext.getBean(LoggerAspect.class);
        logApiAspect.registerLogHandler(OPERATION_MODULE_XXX, this);
    }

    @Override
    protected String getOldData(String operation, Map<String, Object> paramsMap) { ... }

    @Override
    protected void encapsulatingLogsDetailVO(String operation, String oldDataJsonString,
        LogsDetailVO logsDetailVO, Map resultMap) { ... }

    @Override
    protected void saveLog(String tableName, LogsDetailVO logsDetailVO) {
        getLogsMapper.insert(logsDetailVO, tableName);
        ManageLogHelper.writeLog(tableName, logsDetailVO);
    }
}
```

### Step 5：在 ServiceImpl 方法上标注注解

```java
@LogApi(tableName = XxxConstants.XXX_LOG,
    operationModule = XxxConstants.OPERATION_MODULE_XXX,
    operation = XxxConstants.ADD_XXX)
public DataResult<Xxx> addXxx(XxxRequest request) { ... }
```

### Step 6：配置

```yaml
success:
  code: "200"           # 与 DataResult.success() 的 code 值一致
openlibing:
  domain: "https://xxx"  # 系统域名，入湖数据需要
```

---

## 5. 注意事项

### 5.1 编译参数

`LoggerAspect.doBefore` 使用 `DefaultParameterNameDiscoverer` 获取方法参数名。**必须确保编译时保留参数名**：

- Maven：`maven-compiler-plugin` 配置 `<parameters>true</parameters>`
- 否则 `paramsMap` 的 key 会是 `arg0`, `arg1`，导致 `getOldData` 中 `paramsMap.get("projectId")` 取不到值

### 5.2 DataResult 序列化

`LoggerAspect.doAfterReturning` 将返回值通过 fastjson2 序列化为 Map，从中提取 `code`/`msg`/`data`。需确保：

- `DataResult` 的 `code` 字段类型与 `success.code` 配置一致（通常 code 为 Integer 200，配置为字符串 `"200"`，`AbstractLogHandler` 会做 `toString()` 比较）
- `DataResult.data` 的类型能被正确序列化

### 5.3 Cookie token

`AbstractLogHandler` 从 `Cookie["token"]` 解析 JWT。如果请求不带 Cookie（如内部调用、API Key 鉴权），用户信息字段会为空。需要确认业务场景是否都有 Cookie。

### 5.4 异步保存

`saveLog` 在 `CompletableFuture.runAsync()` 中执行，**不受业务事务回滚影响**。这意味着即使业务回滚，日志仍会写入。这是设计意图：审计日志需要记录失败操作。

### 5.5 敏感信息脱敏

Handler 中必须在以下位置做脱敏：

- `getOldData`：查到的实体中如有敏感字段（token、secret、密码），置 null 后再 JSON 序列化
- `encapsulatingLogsDetailVO`：失败时保留的 `params`，需过滤敏感字段
- `newData`：新增/修改后的数据，同样需要脱敏

### 5.6 批量操作

批量操作（如批量添加成员）的日志策略：

- `getOldData`：返回空（新增操作）
- `newData`：记录批量操作结果摘要（成功数量 + 成功项列表），而非逐条记录
- 参见 `SpaceUserLogHandler.handleProjectUser` 中 `ADD_PROJECT_USER` 的处理方式

### 5.7 日志表白名单

`GetLogsMapper.xml` 的 `<choose>` 是硬编码白名单，新增日志表必须同步更新 XML。这是为了防止 SQL 注入（动态表名不能直接拼接）。
