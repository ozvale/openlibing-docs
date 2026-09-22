# 项目空间操作日志归入 openlibing 审计 - Design V2（跨库改造）

> 本文档为 V2 版本，核心变更：日志表从 workspace 数据库迁移到 framework 数据库，日志写入从直接 DB insert 改为 Feign 调用 framework 微服务接口。

## 一、V1 → V2 变更原因

V1 方案中，workspace 通过本地 `GetLogsMapper.insert()` 直接将日志写入 workspace 数据库的 `log_workspace_project` 表。但 framework 管理中心的日志查询页面连接的是 framework 数据库，无法查询到 workspace 数据库中的日志表。

**解决方案**：将日志表建在 framework 数据库中，workspace 通过 framework 提供的内部微服务接口 `/internal-server/add/microservices/log` 写入日志。

## 二、变更对比

| 项目 | V1（原方案） | V2（本方案） |
|------|-------------|-------------|
| 日志表名 | `log_workspace_project` | `log_computing_resource_workspace_project` |
| 日志表所在数据库 | workspace 数据库 | framework 数据库 |
| 建表方式 | workspace Liquibase | framework Liquibase |
| 日志写入方式 | `GetLogsMapper.insert()` 直接写 DB | Feign 调用 `/internal-server/add/microservices/log` |
| workspace 本地 GetLogsMapper | 保留（insert） | 删除（不再需要） |
| workspace 本地 GetLogsMapper.xml | 保留（insert + 白名单） | 删除（不再需要） |
| 入湖方式 | `ManageLogHelper.writeLog()` | `ManageLogHelper.writeLog()`（V1 已完成，V2 无变化） |
| Framework 侧注册 | MANAGEMENT_LOG + 白名单 | MANAGEMENT_LOG + 白名单 + Liquibase 建表 |

## 三、整体流程

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
  └─ saveLog():
      ├─ Feign 调用 framework 接口 → 写入 framework 数据库（DB 落库）
      └─ ManageLogHelper.writeLog() → 写入本地 operate.log（入湖）
        │
        ▼
Framework /internal-server/add/microservices/log
  ├─ getTableName(tableFlag=2, tableDescription="灵枢") → "log_computing_resource_workspace_project"
  ├─ 组装 LogsDetailVO（18 个 DB 字段 + logLakeData="success"）
  └─ getLogsMapper.insert() → 写入 framework 数据库
      注意：framework 接口不做入湖，入湖由各服务本地 operate.log 负责
```

## 四、详细设计

### 4.1 Framework 侧：Liquibase 建表

在 framework 仓库新增 Liquibase 脚本，创建 `log_computing_resource_workspace_project` 表。

**文件**：`openlibing-framework/src/main/resources/db/changelog/v1.0.1/log_computing_resource_workspace_project.xml`

**表结构**：与 framework 中其他业务日志表（`log_iam_info`、`log_tool`、`log_space_permission` 等）保持一致：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<databaseChangeLog
        xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
        xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
        xsi:schemaLocation="http://www.liquibase.org/xml/ns/dbchangelog
                        http://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-4.0.xsd">
    <changeSet id="20260612_add_log_computing_resource_workspace_project" author="l00957468">
        <preConditions onFail="MARK_RAN">
            <not>
                <tableExists tableName="log_computing_resource_workspace_project"/>
            </not>
        </preConditions>

        <createTable tableName="log_computing_resource_workspace_project" remarks="灵枢项目空间审计日志表">
            <column name="id" type="VARCHAR(255)" remarks="唯一标识">
                <constraints primaryKey="true" primaryKeyName="pk_log_cr_workspace_project"/>
            </column>
            <column name="operation_date" type="DATETIME" remarks="日期"/>
            <column name="log_code" type="VARCHAR(255)" remarks="状态码"/>
            <column name="operation_module" type="VARCHAR(255)" remarks="操作模块"/>
            <column name="user_name" type="VARCHAR(255)" remarks="用户名"/>
            <column name="user_id" type="VARCHAR(255)" remarks="用户ID"/>
            <column name="operation" type="VARCHAR(255)" remarks="操作类型"/>
            <column name="old_data" type="TEXT" remarks="操作前数据"/>
            <column name="new_data" type="TEXT" remarks="操作后数据"/>
            <column name="remark" type="VARCHAR(255)" remarks="备注"/>
            <column name="log_message" type="VARCHAR(255)" remarks="结果消息"/>
            <column name="is_detail" type="VARCHAR(255)" remarks="是否具有数据详情"/>
            <column name="ex_message" type="TEXT" remarks="异常信息"/>
            <column name="params" type="VARCHAR(500)" remarks="请求参数"/>
            <column name="account_id" type="VARCHAR(255)" remarks="操作人三方账号id"/>
            <column name="account_platform" type="VARCHAR(255)" remarks="操作人三方账号平台"/>
            <column name="log_result" type="VARCHAR(20)" remarks="操作结果"/>
            <column name="account_name" type="VARCHAR(255)" remarks="操作人三方账号名称"/>
        </createTable>

        <sql>
            ALTER TABLE log_computing_resource_workspace_project
                CONVERT TO CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci;
        </sql>

        <rollback>
            <dropTable tableName="log_computing_resource_workspace_project" cascadeConstraints="true"/>
        </rollback>
    </changeSet>
</databaseChangeLog>
```

**db.changelog.xml 注册**：在 `openlibing-framework/src/main/resources/db/changelog/db.changelog.xml` 中添加：

```xml
<include file="v1.0.1/log_computing_resource_workspace_project.xml" relativeToChangelogFile="true"/>
```

### 4.2 Framework 侧：MANAGEMENT_LOG 注册

**文件**：`com.openlibing.framework.common.log.LogDataCollectionName`

在 `MANAGEMENT_LOG` 常量的 `business_log` JSON 中新增：

```json
"灵枢": "log_computing_resource_workspace_project"
```

**作用**：
- 前端日志页面业务日志分类下显示"灵枢"选项
- `LoggingServiceImpl` 根据 `operationModule="灵枢"` 找到表名 `log_computing_resource_workspace_project`
- `/internal-server/add/microservices/log` 接口根据 `tableDescription="灵枢"` + `tableFlag=2` 找到表名写入

### 4.3 Framework 侧：GetLogsMapper.xml 白名单

**文件**：`openlibing-framework/src/main/resources/mapper/GetLogsMapper.xml`

在 `<sql id="tableName">` 的 `<choose>` 中新增：

```xml
<when test="tableName == 'log_computing_resource_workspace_project'">
    log_computing_resource_workspace_project
</when>
```

**作用**：MyBatis 动态表名白名单，insert 和查询都需要匹配白名单。

### 4.4 Workspace 侧：FrameworkClient 新增方法

**文件**：`com.workspace.business.client.FrameworkClient`

新增调用 framework 日志接口的方法：

```java
/**
 * Add microservice log via framework internal API.
 *
 * @param microservicesLogDTO log data
 * @return DataResult with log ID
 */
@PostMapping("/internal-server/add/microservices/log")
DataResult<String> addMicroservicesLog(@RequestBody MicroservicesLogDTO microservicesLogDTO);
```

### 4.5 Workspace 侧：MicroservicesLogDTO 字段来源与校验

#### 4.5.1 用户面字段（requestMethod 等）——可以从 HttpServletRequest 获取

framework 的 `MicroservicesLogDTO` 有 `@NotBlank` 校验的用户面字段（requestMethod、requestUri、httpUserAgent 等），这些字段**不需要填默认值**，因为 `AbstractLogHandler.encapsulatingDataLakeInfo()` 已经从 `HttpServletRequest` 中提取了这些字段并设进了 `LogsDetailVO`：

```java
// AbstractLogHandler.encapsulatingDataLakeInfo() 中已有：
logsDetailVO.setRequestMethod(request.getMethod());
logsDetailVO.setRequestUri(request.getRequestURI());
logsDetailVO.setRequestLength(request.getContentLength());
logsDetailVO.setHttpUserAgent(request.getHeader("User-Agent"));
// ... 等等
```

所以在 `buildMicroservicesLogDTO` 时，直接从 `LogsDetailVO` 复制即可，`@NotBlank` 校验不会成为问题。

#### 4.5.2 三方账号字段——需从 UserContext 补全

`AbstractLogHandler.encapsulatingInfoFromRequest()` 从 JWT Cookie 解析三方账号信息，但 **JWT 中不包含 `accountPlatform`**。workspace 的 JWT 解析（`OpenlibingAuthInterceptor.parseJwtToken`）返回值中 `accountPlatform=""`。

**数据来源对比**：

| 字段 | `AbstractLogHandler` 从 JWT 解析 | `UserContext` (ThreadLocal) | `workspace_user_info` 表 |
|------|------|------|------|
| `userId` | ✅ JWT 有 | ✅ 有 | ✅ 有 |
| `userName` | ✅ JWT 有 | ✅ 有 | ✅ 有 |
| `accountId` | ✅ JWT 有 | ✅ 有（来自 /get-user-info） | ✅ 有 |
| `accountName` | ✅ JWT 有 | ✅ 有（来自 /get-user-info） | ✅ 有 |
| `accountPlatform` | ❌ **JWT 没有** | ✅ 有（来自 /get-user-info） | ✅ 有 |
| `operatorIp` | ✅ `request.getRemoteAddr()` | ✅ `clientIp` | ❌ 没有 |

**解决方案**：在 `buildMicroservicesLogDTO` 中，三方账号字段**优先从 `LogsDetailVO` 取，缺失时从 `UserContext` 补全**：

```java
// 三方账号字段：优先 LogsDetailVO，降级 UserContext
dto.setAccountId(StringUtils.isNotBlank(vo.getAccountId())
    ? vo.getAccountId() : UserContext.getAccountId());
dto.setAccountName(StringUtils.isNotBlank(vo.getAccountName())
    ? vo.getAccountName() : UserContext.getAccountName());
dto.setAccountPlatform(StringUtils.isNotBlank(vo.getAccountPlatform())
    ? vo.getAccountPlatform() : UserContext.getAccountPlatform());
dto.setOperatorIp(StringUtils.isNotBlank(vo.getOperatorIp())
    ? vo.getOperatorIp() : UserContext.getClientIp());
```

**背景**：`UserContext` 中的完整三方账号信息来自 `OpenlibingAuthInterceptor` → 调用 framework `/get-user-info` 接口 → 响应中 `currentUserInfo` 包含 `accountId`、`accountName`、`accountPlatform`。JWT 是该接口调不通时的降级方案，不含 `accountPlatform`。

#### 4.5.3 完整字段映射

**DB 字段**（18 列，会入库）：

| 字段 | 值来源 | framework insert 对应列 |
|------|--------|----------------------|
| `operationDate` | `LogsDetailVO.operationDate` | `operation_date` |
| `logCode` | `LogsDetailVO.logCode` | `log_code` |
| `logResult` | `LogsDetailVO.logResult` | `log_result` |
| `operationModule` | `LogsDetailVO.operationModule` | `operation_module` |
| `userName` | `LogsDetailVO.userName` | `user_name` |
| `userId` | `LogsDetailVO.userId` | `user_id` |
| `operation` | `LogsDetailVO.operation` | `operation` |
| `oldData` | `LogsDetailVO.oldData` | `old_data` |
| `newData` | `LogsDetailVO.newData` | `new_data` |
| `remark` | `LogsDetailVO.remark` | `remark` |
| `logMessage` | `LogsDetailVO.logMessage` | `log_message` |
| `isDetail` | `LogsDetailVO.isDetail` | `is_detail` |
| `exMessage` | `LogsDetailVO.exMessage` | `ex_message` |
| `params` | `LogsDetailVO.params` | `params` |
| `accountId` | `LogsDetailVO` 降级 `UserContext` | `account_id` |
| `accountPlatform` | `LogsDetailVO` 降级 `UserContext` | `account_platform` |
| `accountName` | `LogsDetailVO` 降级 `UserContext` | `account_name` |
| `operatorIp` | `LogsDetailVO` 降级 `UserContext` | —（不入库） |

**路由字段**（不入库，用于 framework 内部路由）：

| 字段 | 值 | 说明 |
|------|-----|------|
| `tableFlag` | 固定 `2` | 业务日志 |
| `tableDescription` | 固定 `"灵枢"` | 对应 MANAGEMENT_LOG JSON 中的 key |

**用户面字段**（不入库，`AbstractLogHandler` 已从 `HttpServletRequest` 提取到 `LogsDetailVO`）：

| 字段 | 来源 | 说明 |
|------|------|------|
| `requestMethod` | `request.getMethod()` | 已在 `LogsDetailVO` 中 |
| `requestUri` | `request.getRequestURI()` | 同上 |
| `requestLength` | `request.getContentLength()` | 同上 |
| `bodyBytesSent` | — | 同上 |
| `requestTime` | — | 同上 |
| `httpUserAgent` | `request.getHeader("User-Agent")` | 同上 |
| `upstreamResponseLength` | — | 同上 |
| `contentLength` | — | 同上 |
| `host` | — | 同上 |
| `upstreamAddr` | — | 同上 |
| `timeLocal` | — | 同上 |
| `serverProtocol` | — | 同上 |
| `contentType` | — | 同上 |
| `scheme` | — | 同上 |
| `httpXForwardedFor` | — | 同上 |

### 4.6 Workspace 侧：WorkspaceProjectLogHandler.saveLog 改造

**改造前**（V1）：

```java
@Override
protected void saveLog(String tableName, LogsDetailVO logsDetailVO) {
    int insert = getLogsMapper.insert(logsDetailVO, tableName);
    if (insert != 1) {
        log.info("insert {} log error", tableName);
    }
    ManageLogHelper.writeLog(tableName, logsDetailVO);
}
```

**改造后**（V2）：

```java
@Autowired
private FrameworkClient frameworkClient;

@Override
protected void saveLog(String tableName, LogsDetailVO logsDetailVO) {
    try {
        MicroservicesLogDTO dto = buildMicroservicesLogDTO(logsDetailVO);
        DataResult<String> result = frameworkClient.addMicroservicesLog(dto);
        if (result == null || !String.valueOf(ResultStatusConstant.SUCCESS.getCode()).equals(
                String.valueOf(result.getCode()))) {
            log.warn("Failed to write log via framework API: {}", result);
        }
    } catch (Exception e) {
        log.warn("Failed to call framework log API: {}", e.getMessage());
    }
    // 入湖仍由 workspace 本地处理
    ManageLogHelper.writeLog(tableName, logsDetailVO);
}

private MicroservicesLogDTO buildMicroservicesLogDTO(LogsDetailVO vo) {
    MicroservicesLogDTO dto = new MicroservicesLogDTO();
    // 路由字段
    dto.setTableFlag(2);  // 业务日志
    dto.setTableDescription("灵枢");
    // DB 字段（18 列）
    dto.setOperationDate(vo.getOperationDate());
    dto.setLogCode(vo.getLogCode());
    dto.setLogResult(vo.getLogResult());
    dto.setOperationModule(vo.getOperationModule());
    dto.setUserName(vo.getUserName());
    dto.setUserId(vo.getUserId());
    dto.setOperation(vo.getOperation());
    dto.setOldData(vo.getOldData());
    dto.setNewData(vo.getNewData());
    dto.setRemark(vo.getRemark());
    dto.setLogMessage(vo.getLogMessage());
    dto.setIsDetail(vo.getIsDetail());
    dto.setExMessage(vo.getExMessage());
    dto.setParams(vo.getParams());
    // 三方账号字段：优先 LogsDetailVO，降级 UserContext（JWT 不含 accountPlatform）
    dto.setAccountId(StringUtils.isNotBlank(vo.getAccountId())
        ? vo.getAccountId() : UserContext.getAccountId());
    dto.setAccountPlatform(StringUtils.isNotBlank(vo.getAccountPlatform())
        ? vo.getAccountPlatform() : UserContext.getAccountPlatform());
    dto.setAccountName(StringUtils.isNotBlank(vo.getAccountName())
        ? vo.getAccountName() : UserContext.getAccountName());
    dto.setOperatorIp(StringUtils.isNotBlank(vo.getOperatorIp())
        ? vo.getOperatorIp() : UserContext.getClientIp());
    // 用户面字段：AbstractLogHandler 已从 HttpServletRequest 提取到 LogsDetailVO
    dto.setRequestMethod(vo.getRequestMethod());
    dto.setRequestUri(vo.getRequestUri());
    dto.setRequestLength(vo.getRequestLength());
    dto.setBodyBytesSent(vo.getBodyBytesSent());
    dto.setRequestTime(vo.getRequestTime());
    dto.setHttpUserAgent(vo.getHttpUserAgent());
    dto.setUpstreamResponseLength(vo.getUpstreamResponseLength());
    dto.setContentLength(vo.getContentLength());
    dto.setHost(vo.getHost());
    dto.setUpstreamAddr(vo.getUpstreamAddr());
    dto.setTimeLocal(vo.getTimeLocal());
    dto.setServerProtocol(vo.getServerProtocol());
    dto.setContentType(vo.getContentType());
    dto.setScheme(vo.getScheme());
    dto.setHttpXForwardedFor(vo.getHttpXForwardedFor());
    return dto;
}
```

### 4.7 Workspace 侧：删除本地日志写入组件

以下 V1 中新增的组件在 V2 中不再需要：

| 文件 | 操作 | 原因 |
|------|------|------|
| `GetLogsMapper.java` | 删除 | 不再直接写 DB |
| `GetLogsMapper.xml` | 删除 | 不再直接写 DB |
| `project-tables.xml` 中的 `log_workspace_project` changeSet | 删除 | 表建在 framework 数据库 |

### 4.8 Workspace 侧：常量更新

**文件**：`LogOperationConstants`

```java
// 表名常量更新
public static final String LOG_WORKSPACE_PROJECT = "log_computing_resource_workspace_project";
```

**@LogApi 注解中的 tableName 同步更新**：

```java
@LogApi(tableName = LOG_WORKSPACE_PROJECT, ...)
```

### 4.9 入湖方式

**入湖由 workspace 本地负责，V1 已完成，V2 无需改动**：

- framework 的 `/internal-server/add/microservices/log` 接口**不做入湖**（不调用 `ManageLogHelper.writeLog()`）
- framework 接口虽然设置了 `logLakeData="success"`，但这个字段不在 DB 表中，只是 `LogsDetailVO` 的一个内存字段，insert 后即丢弃
- 入湖的实际机制：各服务通过 `ManageLogHelper.writeLog()` 将 JSON 写入 `MANAGE_LOG` logger → logback 的 `MANAGE_LOG_FILE` appender 写入本地 `operate.log` → 外部日志采集管道从 `operate.log` 拉取入湖
- workspace 的 `ManageLogHelper.writeLog()` 已在 V1 中对齐 framework 的 11 字段格式和 `yyyy-MM-dd HH:mm:ss` 日期格式，V2 保持不变

## 五、涉及文件清单

### Framework 仓库

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `db/changelog/v1.0.1/log_computing_resource_workspace_project.xml` | 新增 | Liquibase 建表脚本 |
| `db/changelog/db.changelog.xml` | 修改 | include 新建表脚本 |
| `LogDataCollectionName.java` | 修改 | MANAGEMENT_LOG 新增 `"灵枢": "log_computing_resource_workspace_project"` |
| `GetLogsMapper.xml` | 修改 | 白名单新增 `log_computing_resource_workspace_project` |

### Workspace 仓库

| 文件 | 改动类型 | 说明 |
|------|---------|------|
| `FrameworkClient.java` | 修改 | 新增 `addMicroservicesLog()` 方法 |
| `MicroservicesLogDTO.java` | 新增 | Feign 请求 DTO（镜像 framework） |
| `WorkspaceProjectLogHandler.java` | 修改 | saveLog 改为 Feign 调用，删除 GetLogsMapper 依赖，新增 FrameworkClient 依赖 |
| `LogOperationConstants.java` | 修改 | `LOG_WORKSPACE_PROJECT` 值改为 `log_computing_resource_workspace_project` |
| `ProjectSpaceServiceImpl.java` | 修改 | @LogApi tableName 更新 |
| `ApiKeyServiceImpl.java` | 修改 | @LogApi tableName 更新 |
| `GetLogsMapper.java` | 删除 | 不再需要 |
| `GetLogsMapper.xml` | 删除 | 不再需要 |
| `project-tables.xml` | 修改 | 删除 `log_workspace_project` changeSet |

## 六、风险点

| 风险 | 应对 |
|------|------|
| JWT 中不含 `accountPlatform`，导致 `LogsDetailVO.accountPlatform` 为空 | `buildMicroservicesLogDTO` 中降级从 `UserContext` 获取（`/get-user-info` 接口已补全） |
| Feign 调用失败导致日志丢失 | catch 异常 + WARN 日志，不影响业务主流程；入湖仍由本地 `operate.log` 保障 |
| 两个仓库需协调发布顺序 | framework 先发布（建表 + 注册），workspace 后发布（调用接口） |
| `log_computing_resource_workspace_project` 表名较长 | 与 framework 其他表命名风格一致（如 `log_platform_release_open_euler`），可接受 |

## 七、发布顺序

1. **Framework 先发布**：建表 + MANAGEMENT_LOG 注册 + 白名单注册
2. **Workspace 后发布**：删除本地 GetLogsMapper + 改用 Feign 调用

## 八、验证方式

1. 创建项目 → framework 数据库 `log_computing_resource_workspace_project` 表有新记录，newData 有项目详情
2. 更新项目 → oldData + newData 都有值
3. 删除项目 → oldData 有值，newData 为空
4. 添加成员 → newData 只记录成功成员详情
5. Feign 调用异常 → 业务不中断，WARN 日志输出
6. 管理中心日志页面 → 业务日志分类下有"灵枢"选项，可查询到审计日志
