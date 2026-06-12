# openlibing-simulation AI Memory

本文档保存 `openlibing-simulation` 代码仓可长期复用的 AI 开发规则。当前为初始版本，后续从需求 `archive.md` 中提炼。

## 仓库定位

`openlibing-simulation` 负责 OpenLibing 仿真服务平台的节点资源调度、任务管理和引擎配置管理等功能。系统基于 Spring Boot 3.4.5 + Java 21 构建，提供仿真环境的一站式管理能力。

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 涉及 Controller 层开发时，必须在对应的 `xxx_design.md` 中补充 API 设计说明后再实现。
- 需求完成后，必须在 `archive.md` 记录 AI 错误、人工修正和可复用规则。
- 所有 Controller 必须使用 `@RestController` 和 `@RequestMapping` 注解。
- 所有跨域请求使用 `@CrossOrigin(origins = "*", maxAge = 3600)` 注解。
- 统一使用项目自定义的 `ResponseEntity` 作为响应封装类。

## 技术栈规范

### 框架版本

| 组件 | 版本 | 说明 |
|------|------|------|
| Java | 21 | 必选 |
| Spring Boot | 3.4.5 | 必选 |
| MyBatis | 3.0.4 | ORM 框架 |
| MyBatis Plus | 3.5.x | 扩展 ORM |
| Liquibase | - | 数据库迁移 |
| JSch | 0.2.16 | SSH 连接 |

### 响应封装

统一使用 `ResponseEntity` 作为 API 响应封装：

```java
ResponseEntity(code, message, data)
ResponseEntity(code, message, data, total)  // 分页场景
```

常用响应码定义在 `ResponseCodeEnum` 中：

| 枚举值 | code | messageCn | 使用场景 |
|--------|------|-----------|---------|
| SUCCESS | 200 | 成功 | 正常响应 |
| BAD_REQUEST | 400 | 请求异常 | 参数校验失败 |
| BAD_REQUEST_PARAM | 40001 | 请求参数异常 | 参数格式错误 |
| NO_LOGIN | 401 | 没有登录 | 未认证 |
| NO_PERMISSION | 403 | 没有权限 | 无权限访问 |
| ERROR | 500 | 系统异常 | 服务器内部错误 |

### 代码规范

- 所有 Java 文件必须包含华为版权头：
```java
/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 * 版权所有 (c) 华为技术有限公司  2026-2026.
 */
```

- 使用 `@Slf4j` 替代 `Logger` 声明
- 使用 Lombok 注解（`@Data`、`@Getter`、`@Setter`、`@AllArgsConstructor`、`@NoArgsConstructor`）
- Controller 方法必须添加 Javadoc 注释，包含参数和返回值说明
- 使用 `jakarta.validation.Valid` 进行参数校验

### API 设计规范

- RESTful 风格 URL 设计
- 基础路径：`/simulation/v2/`
- Controller 路径前缀示例：
  - 节点管理：`/simulation/v2/node/manage`
  - Qemu 任务：`/simulation/qemu`
- 使用 `@RequestParam`、`@RequestBody`、`@PathVariable` 明确标注参数来源
- POST/PUT 请求使用 JSON 请求体，GET/DELETE 请求使用查询参数

### 数据库规范

- 使用 Liquibase 进行数据库版本管理
- XML 迁移文件放在 `src/main/resources/db/changelog/v1.0.0/` 目录
- 表命名规范：t_ + 模块名 + 下划线分隔
- 字段命名：下划线分隔（与 Java 驼峰命名自动转换）
- 必须包含 `create_time`、`last_modify_time` 审计字段

## 常见 AI 错误与规避

| 错误模式 | 规避规则 | 来源需求 |
| --- | --- | --- |
| 使用 Spring 原生 `ResponseEntity<T>` 而非项目自定义 | 必须导入 `com.openlibing.simulation.entity.ResponseEntity`，全局搜索确保无残留 | 通用规范 |
| MyBatis XML mapper 路径配置错误 | 确保 `application.yaml` 中 `mybatis.mapper-locations` 配置正确，路径为 `classpath:mapper/*.xml` | 通用规范 |
| Liquibase 迁移脚本格式错误 | XML 文件必须包含正确的 `changeSet` 属性（id、author），每个 changeSet 需有唯一标识 | 通用规范 |
| 使用 JSch 未处理异常导致线程阻塞 | SSH 操作必须使用异步处理或设置超时时间，避免长时间阻塞 | Qemu 任务 |
| 分布式锁未正确释放 | 确保锁获取和释放成对出现，使用 try-finally 保证锁释放 | 节点管理 |
| 配置文件敏感信息硬编码 | 使用 `@EnableEncryptableProperties` 和 Jasypt 加密敏感配置 | 通用规范 |
| 跨域配置遗漏导致前端无法访问 | 确保 Controller 或全局配置中包含 `@CrossOrigin` 注解 | 通用规范 |
| 分页查询未设置合理的 pageSize 上限 | 分页接口必须校验 pageSize，最大不超过 100 | 通用规范 |
| Javadoc 功能描述与标签间缺少空行 | Javadoc 中功能描述与 `@param`/`@return`/`@throws` 标签之间必须有一个空行 | matrixserver-qemu-deploy |
| 行宽超过120窄字符 | Java 代码行宽不超过120个窄字符，方法签名过长时拆分参数到下一行（8空格缩进） | matrixserver-qemu-deploy |
| 使用 `null` 返回值而非 `Optional` | 方法返回可能为空的值时使用 `Optional<T>`，调用方用 `orElse`/`isPresent` 处理；禁止 `Optional.get()` 和 `Optional` 赋值为 `null` | matrixserver-qemu-deploy |
| 局部变量声明远离首次使用位置 | 局部变量应声明在接近首次使用的行，避免在方法开头集中声明 | matrixserver-qemu-deploy |
| `public static final` 常量缺少 Javadoc | 每个 `public`/`protected` 修饰的 `static final` 字段必须有 Javadoc 注释，描述功能含义而非仅重复变量名 | matrixserver-qemu-deploy |
| 方法间多余空行 | 方法之间仅保留一个空行，减少不必要的空行保持代码紧凑 | matrixserver-qemu-deploy |
| 未使用的 import 语句残留 | 每次修改后检查并删除未使用的 import 语句 | matrixserver-qemu-deploy |

## 模块职责边界

### Controller 层

- 负责 HTTP 请求接收和响应
- 参数校验和转换
- 调用 Service 层完成业务逻辑
- 不直接操作数据库

### Service 层

- 业务逻辑处理
- 事务管理
- 调用 Mapper 层完成数据访问
- 异常处理和转换

### Mapper 层

- 数据库 CRUD 操作
- XML mapper 文件定义复杂 SQL
- MyBatis Plus 条件构造器使用

## 安全约束

- 管理接口需验证用户权限
- 敏感操作需记录操作日志
- 密码等敏感信息加密存储
- SQL 注入防护：使用参数化查询

## 性能考虑

- 批量操作需设置合理的批量大小（建议不超过 100）
- 大数据量查询必须分页
- 远程操作（JSch）需设置超时
- 合理使用缓存减少数据库访问