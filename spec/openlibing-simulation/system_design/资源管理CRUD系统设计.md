# 资源管理 CRUD 系统设计

> 本文与代码基线 `master@4f22896` 对齐。所有结论均标注来源文件与行号。

## 1. 系统定位

资源管理 CRUD 是 `openlibing-simulation` 面向管理端的**基础台账能力**，为仿真平台维护四类可复用资源：仿真引擎、qcow 镜像、服务器台账（含扩展信息）、资源附件。

该能力只负责「元数据增删改」——**不含列表查询、不含文件上传下载、不含资源使用状态流转**。文件实体存放在 OBS 中，本模块只维护附件元数据。

## 2. 业务边界

| 边界类型   | 说明                                                                             |
| ---------- | -------------------------------------------------------------------------------- |
| 上游调用方 | 管理端前端（经 APIG）；写操作依赖请求头 `X-Openlibing-User` 提供操作者身份       |
| 下游依赖   | MySQL（四张表）、`InternalSimulationAuthFilter`（认证）                          |
| 对外接口   | 11 个 POST 接口，前缀 `/simulation/manage/{engine,qcow,server,attachment}`       |
| 不提供     | 列表/详情查询接口（查询能力由 `EngineInfoService`、Qemu 任务链路等其它模块提供） |
| 事务与并发 | **未使用** `@Transactional`，**未使用**分布式锁                                  |

## 3. 接口清单

四组 Controller 均为 `@RestController`，方法级统一 `RequestMethod.POST`。**删除接口一律 POST + `@RequestParam("id")`**，不使用 HTTP DELETE。

| Controller                     | 类级前缀                        | 接口                                                                                        | 行号                                          |
| ------------------------------ | ------------------------------- | ------------------------------------------------------------------------------------------- | --------------------------------------------- |
| `EngineResourceController`     | `/simulation/manage/engine`     | `add` / `update` / `delete`                                                                 | `EngineResourceController.java:31, 45-74`     |
| `QcowResourceController`       | `/simulation/manage/qcow`       | `add` / `update` / `delete`                                                                 | `QcowResourceController.java:31, 45-74`       |
| `ServerResourceController`     | `/simulation/manage/server`     | `basic/add`、`basic/update`、`basic/delete`、`extend/add`、`extend/update`、`extend/delete` | `ServerResourceController.java:32, 46-111`    |
| `AttachmentResourceController` | `/simulation/manage/attachment` | `add` / `update` / `delete`                                                                 | `AttachmentResourceController.java:31, 45-74` |

新增与更新使用 `@Validated @RequestBody`，删除使用 `@RequestParam("id")`。

### 3.1 操作者传递

| 环节            | 实现                                                                                                                                                                                                                                             |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 请求头名        | `X-Openlibing-User`，各 Controller 内以私有常量 `OPERATOR_HEADER` 定义（`EngineResourceController.java:33`、`QcowResourceController.java:33`、`ServerResourceController.java:34`、`AttachmentResourceController.java:33`），**未抽到公共常量类** |
| Controller 读取 | `@RequestHeader(value = OPERATOR_HEADER, required = false) String operator`，作为 `creator` 传给 Service                                                                                                                                         |
| 头缺失时        | Controller 不报错（`required = false`），由 Service 层对 `creator` 做非空校验并返回 400                                                                                                                                                          |
| 认证侧          | `InternalSimulationAuthFilter` 在 `security.internal-auth.enabled=true` 时要求该头非空（`InternalSimulationAuthFilter.java:149-154`）                                                                                                            |
| 权限校验        | 这四组接口**未做**「仅创建者可操作」校验；`Constans.PERMISSION_CHECK_ERROR`（`Constans.java:24`）在本模块无引用                                                                                                                                  |

**注意一处不一致**：`server/extend/add` 的 Controller 方法**没有** `@RequestHeader` 参数（`ServerResourceController.java:83-87`），`t_server_extend_info` 表也没有 creator 列，即扩展信息新增不采集操作者。其余 3 个新增接口均采集。

## 4. Service 校验规则

四组 Service 的失败分支**统一返回 `ResponseEntity(400, "...")`**，不抛业务异常。

### 4.1 Engine（`EngineResourceServiceImpl.java:28-74`）

| 方法                         | 校验链                                                                                                                                                                                                                                                                               |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `addEngine(entity, creator)` | `entity == null` → 400 `engine is required`；`name`/`productLineId`/`supportScene`/`engineType` 任一为空 → 400 `engine name/productLineId/supportScene/engineType are required`；`creator` 空 → 400 `creator is required`；然后 `setId(UUID)`、`setCreator(creator)`、`insertEngine` |
| `updateEngine(entity)`       | `entity == null \|\| id 空` → 400 `engine id is required`；影响行数 `== 0` → 400 `ENGINE_NOT_EXIST`                                                                                                                                                                                  |
| `deleteEngine(id)`           | `id` 空 → 400 `engine id is required`；影响行数 `== 0` → 400 `ENGINE_NOT_EXIST`                                                                                                                                                                                                      |

### 4.2 Qcow（`QcowResourceServiceImpl.java:28-74`）

| 方法                       | 校验链                                                                                                                                                            |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `addQcow(entity, creator)` | `entity == null` → 400 `qcow is required`；`name`/`productLineId` 任一为空 → 400 `qcow name/productLineId are required`；`creator` 空 → 400 `creator is required` |
| `updateQcow(entity)`       | `entity == null \|\| id 空` → 400 `qcow id is required`；影响行数 `== 0` → 400 `QCOW_NOT_EXIST`                                                                   |
| `deleteQcow(id)`           | `id` 空 → 400 `qcow id is required`；影响行数 `== 0` → 400 `QCOW_NOT_EXIST`                                                                                       |

### 4.3 Server（`ServerResourceServiceImpl.java:29-114`）

| 方法                         | 校验链                                                                                                                                         |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------- |
| `addServer(entity, creator)` | `entity == null \|\| ip 空` → 400 `server ip is required`；`creator` 空 → 400 `creator is required`                                            |
| `updateServer(entity)`       | `entity == null \|\| id 空` → 400 `server id is required`；影响行数 `== 0` → 400 `SERVER_NOT_EXIST`                                            |
| `deleteServer(id)`           | `id` 空 → 400 `server id is required`；影响行数 `== 0` → 400 `SERVER_NOT_EXIST`                                                                |
| `addServerExtend(entity)`    | `entity == null` → 400 `server extend is required`；`serverId` 空 → 400 `server id is required`；`extendKey` 空 → 400 `extend key is required` |
| `updateServerExtend(entity)` | `entity == null \|\| id 空` → 400 `server extend id is required`；影响行数 `== 0` → 400 `EXTEND_NOT_EXIST`                                     |
| `deleteServerExtend(id)`     | `id` 空 → 400 `server extend id is required`；影响行数 `== 0` → 400 `EXTEND_NOT_EXIST`                                                         |

### 4.4 Attachment（`AttachmentResourceServiceImpl.java:29-76`）

| 方法                             | 校验链                                                                                                                                                                                                                             |
| -------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `addAttachment(entity, creator)` | `entity == null` → 400 `attachment is required`；`resourceId` 空 → 400 `resourceId is required`；`creator` 空 → 400 `creator is required`；然后 `setId(UUID)`、`setCreateBy(creator)`、`setCreateTime(DateTimeUtils.getCurrent())` |
| `updateAttachment(entity)`       | `entity == null \|\| id 空` → 400 `attachment id is required`；影响行数 `== 0` → 400 `ATTACHMENT_NOT_EXIST`                                                                                                                        |
| `deleteAttachment(id)`           | `id` 空 → 400 `attachment id is required`；影响行数 `== 0` → 400 `ATTACHMENT_NOT_EXIST`                                                                                                                                            |

### 4.5 四组共有特征

| 特征                           | 现状                                                                                                                                                    |
| ------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 唯一性校验                     | **均无**。`EngineBasicInfoMapper.getEngineByName` / `QcowInfoMapper.getQcowByName` 存在，但调用方是 `QemuTaskServiceImpl`（名称解析），不用于 CRUD 去重 |
| 「至少一个可更新字段非空」校验 | **均未显式实现**，安全性依赖 XML 的 `<set>` 是否含无条件列（见 §6.3）                                                                                   |
| 事务                           | 无 `@Transactional`                                                                                                                                     |
| 分布式锁                       | 无                                                                                                                                                      |
| 响应码                         | 全部使用**字面量** `200` / `400`，**未引用** `enums/ResponseCodeEnum`                                                                                   |

## 5. 领域模型与表映射

### 5.1 横向对比

| 维度         | Engine                             | Qcow             | Server basic                             | Server extend          | Attachment                                |
| ------------ | ---------------------------------- | ---------------- | ---------------------------------------- | ---------------------- | ----------------------------------------- |
| 表           | `t_engine_basic_info`              | `t_qcow_info`    | `t_server_basic_info`                    | `t_server_extend_info` | `t_resource_attachment`                   |
| Mapper       | `EngineBasicInfoMapper`            | `QcowInfoMapper` | `ServerResourceMapper`                   | 同左                   | `ResourceAttachmentMapper`                |
| 删除方式     | 物理 DELETE                        | 物理 DELETE      | **逻辑删除**                             | 物理 DELETE            | 物理 DELETE                               |
| 主键         | Java 侧 UUID（32 位）              | 同左             | 同左                                     | 同左                   | 同左                                      |
| 审计时间填充 | SQL `now()`                        | SQL `now()`      | SQL `now()`                              | SQL `now()`            | **Java 侧** `DateTimeUtils.getCurrent()`  |
| 审计字段名   | `create_time` / `last_modify_time` | 同左             | 同左                                     | 同左                   | `create_time`（**VARCHAR**）/ `create_by` |
| 逻辑删除标志 | 无                                 | 无               | `is_deleted`（表中存在，实体无对应字段） | 无                     | 无                                        |

### 5.2 主键与审计字段生成方式

- **主键**：全部由 Java 侧 `CommmonUtils.getUuid()` 生成（`CommmonUtils.java:23-25`，`UUID.randomUUID().toString().replace("-", "")`），在 ServiceImpl 的 add 方法中 `setId(...)`。既不使用数据库自增，也不使用 MyBatis-Plus ID 策略。
- **审计时间**：四组 Mapper 都是**手写 XML 的普通 MyBatis Mapper（非 `BaseMapper`）**，因此 `MyBatisPlusConfig.java:46-59` 中的 `MetaObjectHandler`（`strictInsertFill("createTime"/"updateTime")`）**对这四组业务不生效**。实际填充方式见上表。
- **Attachment 的时间是字符串**：`t_resource_attachment.create_time` 类型为 `VARCHAR(255)`，由 `DateTimeUtils.getCurrent()`（格式 `yyyy-MM-dd HH:mm:ss`）赋值。

### 5.3 逻辑删除 vs 物理删除

| 维度     | `server/basic/delete`                                                                                                                                 | `server/extend/delete`                                          |
| -------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------- |
| Javadoc  | 「删除服务器台账记录（逻辑删除）」（`ServerResourceController.java:66-69`）                                                                           | 「删除服务器扩展信息（物理删除）」（`:101-106`）                |
| 实际 SQL | `UPDATE t_server_basic_info SET is_deleted = "1", last_modify_time = now() WHERE id = #{id} AND is_deleted = "0"`（`ServerResourceMapper.xml:51-56`） | `DELETE FROM t_server_extend_info WHERE id = #{id}`（`:80-83`） |
| 重复删除 | `WHERE` 带 `is_deleted = "0"`，二次删除影响 0 行 → 400 `SERVER_NOT_EXIST`                                                                             | 二次删除影响 0 行 → 400 `EXTEND_NOT_EXIST`                      |
| 实体暴露 | `ServerBasicInfoEntity` **没有** `isDeleted` 字段，标志仅存在于 SQL 与表结构中                                                                        | 表无 `is_deleted` 列                                            |

Engine / Qcow / Attachment 三组均为 `DELETE FROM ... WHERE id = #{id}`，物理删除，且表中无 `is_deleted` 列。

## 6. 数据库操作细节

### 6.1 建表脚本

| 表                      | changelog                               | changeSet id                            | author    |
| ----------------------- | --------------------------------------- | --------------------------------------- | --------- |
| `t_engine_basic_info`   | `v1.0.0/t_engine_basic_info.xml:9-61`   | `20260422_create_t_engine_basic_info`   | wangxiang |
| `t_qcow_info`           | `v1.0.0/t_qcow_info.xml:9-42`           | `20260806_create_t_qcow_info`           | ligao     |
| `t_server_basic_info`   | `v1.0.0/t_server_basic_info.xml:9-68`   | `20260422_create_t_server_basic_info`   | wangxiang |
| `t_server_extend_info`  | `v1.0.0/t_server_extend_info.xml:9-38`  | `20260422_create_t_server_extend_info`  | wangxiang |
| `t_resource_attachment` | `v1.0.0/t_resource_attachment.xml:9-40` | `20260422_create_t_resource_attachment` | wangxiang |

### 6.2 实体与表字段的不一致点

| 表/实体                     | 现象                                                                                                                                                                                          |
| --------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EngineBasicInfoEntity`     | `uploadFileName`、`fileSize`、`decompressedSize` 三个字段在建表脚本与 insert/update SQL 中**均无对应列**，属「实体有、表无、SQL 无」的悬空字段                                                |
| `EngineBasicInfoMapper.xml` | resultMap 把 `is_default` 映射到 `property="default"`（`:17`），而 insert SQL 使用 `#{isDefault}`（`:215`），同一列两种属性名                                                                 |
| `ServerBasicInfoEntity`     | `usingCount`、`isEnoughCPUMemory`、`computingLabServerId`、`serverExtendInfos` 未参与 insert/update；表中 `hidevlab_task_id`、`computingLab_server_id`、`computingLab_task_id` 三列无实体字段 |
| `ResourceAttachmentMapper`  | 同时标注 `@Mapper` 与 `@Service`（`ResourceAttachmentMapper.java:21-22`），与其余三个 Mapper（仅 `@Mapper`）风格不一致                                                                        |
| 时间精度                    | `t_server_basic_info` 的 `create_time`/`last_modify_time` 为 `TIMESTAMP`，`t_server_extend_info`、`t_qcow_info`、`t_engine_basic_info` 为 `TIMESTAMP(6)`                                      |

### 6.3 `<set>` 空值风险（重要）

MyBatis 的 `<set>` 若所有 `<if>` 均不成立，会生成 `UPDATE t_x SET WHERE id = ?` 这类非法 SQL，被 MyBatis-Plus 的 `BlockAttackInnerInterceptor` 或数据库拦截。

| 表             | `<set>` 是否有无条件列兜底                                                                                                           | 结论       |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------ | ---------- |
| Engine         | 恒有 `is_default = #{isDefault}` 与 `last_modify_time = now()`（`EngineBasicInfoMapper.xml:219-235`）                                | 安全       |
| Qcow           | 恒有 `last_modify_time = now()`（`QcowInfoMapper.xml:33-43`）                                                                        | 安全       |
| Server basic   | 恒有 `overcommit_ratio = #{overcommitRatio}`（primitive，符合规范）与 `last_modify_time = now()`（`ServerResourceMapper.xml:21-49`） | 安全       |
| Server extend  | 恒有 `last_modify_time = now()`（`ServerResourceMapper.xml:67-78`）                                                                  | 安全       |
| **Attachment** | **全部由 `<if test="xxx != null">` 组成，无任何无条件列**（`ResourceAttachmentMapper.xml:33-46`）                                    | **有风险** |

而 `AttachmentResourceServiceImpl.updateAttachment` 只校验了 `id` 非空，**未做「至少一个可更新字段非空」校验**。因此请求体仅传 `id` 时会拼出非法 SQL，异常经 `GlobalExceptionHandler` 兜成 `code=500`（而非业务 400）。这与 `AGENTS.md` 中「Service 层更新接口必须先校验至少一个可更新字段非空」的规范不一致。

## 7. 动态数据源

**这四组 Controller / Service / ServiceImpl / Mapper 中没有任何 `@DataSource` 注解。**

- `aop/DataSource.java:24-29` 定义注解（`@Target({METHOD, TYPE})`，默认值 `DataSourceEnum.DORIS`），`DataSourceAspect` 仅在存在注解时切换数据源；
- 四个模块的 `service` 包内 grep `@DataSource` / `DataSourceEnum` / `DynamicDataSourceContextHolder` 均**零命中**；
- `DataSourceConfig.java:79-97` 只注册了 `@Primary` 的 `mysqlDataSource`（Hikari，密码经 `SecurityUtil.decrypt(password, part1)` 解密），**没有 Doris 数据源 Bean**。

因此在当前代码状态下，这些接口实际访问的是 `@Primary` 的主数据源。注解机制存在但未被使用。

## 8. 响应与异常

### 8.1 统一响应体

使用项目自定义 `com.openlibing.simulation.entity.ResponseEntity`（`entity/ResponseEntity.java:18-76`），字段为 `code`（默认 200）、`message`（默认 `success`）、`data`、`total`。

成功时 message 统一取 `Constans.SUCCESS = "success"`（`Constans.java:74`）。

### 8.2 响应码现状

| 场景         | 实际取值                        | 说明                                                                                                     |
| ------------ | ------------------------------- | -------------------------------------------------------------------------------------------------------- |
| 成功         | `200`（字面量）                 | 未使用 `ResponseCodeEnum.SUCCESS`                                                                        |
| 参数校验失败 | `400`（字面量）                 | 未使用 `ResponseCodeEnum.BAD_REQUEST`                                                                    |
| 记录不存在   | `400` + 各模块私有 message 常量 | `ENGINE_NOT_EXIST` / `QCOW_NOT_EXIST` / `SERVER_NOT_EXIST` / `EXTEND_NOT_EXIST` / `ATTACHMENT_NOT_EXIST` |
| 数据库异常   | `500` + `Internal Server Error` | 由 `GlobalExceptionHandler` 统一转换                                                                     |

`enums/ResponseCodeEnum` 定义了 `SUCCESS(200)`、`BAD_REQUEST(400)`、`BAD_REQUEST_PARAM(40001)`、`BAD_REQUEST_UNKNOWN(40002)`、`NO_LOGIN(401)`、`NO_PERMISSION(403)`、`ERROR(500)`、`ERROR_QUERY(50001)`，但**在本模块中未被引用**。

### 8.3 异常处理路径

- 这四组 Service **不抛业务异常**：`exception/ServiceException` 与 `TaskUsingException` 在本模块无 `throw` / `catch`；
- Controller 内**无 try-catch**；
- `GlobalExceptionHandler`（`@ControllerAdvice`，`GlobalExceptionHandler.java:23-58`）只兜 `RuntimeException` 与 `Exception`，两者都固定返回 `code=500` + `message="Internal Server Error"`，真实异常只写日志，**不透出内部信息**。

## 9. 单元测试

| 测试类                                          | 用例数 | 覆盖范围                                                                                                                                 |
| ----------------------------------------------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------- |
| `EngineResourceServiceImplTest.java:31-113`     | 9      | add 成功/缺必填/缺 creator、update 成功/缺 id/记录不存在、delete 成功/不存在/空 id                                                       |
| `QcowResourceServiceImplTest.java:31-105`       | 8      | add 与 update 同上；delete 缺「空 id」用例                                                                                               |
| `ServerResourceServiceImplTest.java:32-128`     | 10     | basic 的 add/update/delete 全覆盖；extend 仅覆盖 `addServerExtend` 成功与缺 key，**未覆盖** `updateServerExtend` 与 `deleteServerExtend` |
| `AttachmentResourceServiceImplTest.java:31-106` | 8      | add/update/delete 常规路径                                                                                                               |

四个测试类均为 JUnit 5 + Mockito，`@InjectMocks` ServiceImpl + `@Mock` Mapper，属纯 Mock 单测。**Controller 层无测试**（`controller/` 下仅有 `HealthControllerTest`、`QemuTaskControllerTest`）。
