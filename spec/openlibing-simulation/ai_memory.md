# openlibing-simulation AI Memory

本文档保存 `openlibing-simulation` 代码仓可长期复用的 AI 开发规则，来源为仓库内 `AGENTS.md` 与历史需求 `archive.md`。

**基线**：本文件与代码基线 `master@4f22896` 对齐。规则与代码不一致时，以代码和仓库内 `AGENTS.md` 为准，并回头修正本文件。

## 仓库定位

`openlibing-simulation` 是 OpenLibing 仿真服务平台（蓝区）的**业务服务层**，不包含前端资源。提供仿真引擎、qcow 镜像、服务器/附件等资源管理，以及 Qemu 任务编排、节点管理、YAML 配置管理、仿真验证任务与运营数据上报等能力。

所有能力通过 RESTful API 暴露，依赖 `openlibing-common` SDK 提供的基础组件（统一安全工具、动态数据源基建、加解密等），并调用 `openlibing-framework` 的运营看板接口完成数据上报。

- 服务端口：`8108`
- 数据库：MySQL + Doris（动态数据源）
- 容器基线：OpenEuler 24.03 LTS SP1 + JRE 21 + RASP

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 涉及 Controller 层开发时，必须在对应的 `xxx_design.md` 中补充 API 设计说明后再实现。
- 需求完成后，必须在 `archive.md` 记录 AI 错误、人工修正和可复用规则。
- 所有 Controller 必须使用 `@RestController` 和 `@RequestMapping` 注解，方法必须写 Javadoc（含参数与返回值说明）。
- 统一使用项目自定义的 `com.openlibing.simulation.entity.ResponseEntity` 作为响应封装，**禁止**误用 Spring 原生 `org.springframework.http.ResponseEntity`。
- 删除类接口统一使用 **POST**（`/xxx/delete`），id 通过 `@RequestParam("id")` 传入，不要擅自改成 `RequestMethod.DELETE`。
- 操作者（机机身份）从请求头 `X-Openlibing-User` 获取，请求头名必须常量化。
- 本仓代码中**未使用** `@CrossOrigin`，不要新增跨域注解。
- 需要某种功能时优先复用既有实现；新增前先搜索 `src/main/java/` 中是否已有同类工具类、Service 方法或 Mapper 查询。

## 技术栈规范

### 框架版本

| 组件              | 版本                            | 说明                                       |
| ----------------- | ------------------------------- | ------------------------------------------ |
| Java              | 21                              | 必选                                       |
| Spring Boot       | 3.4.5                           | Web（SERVLET）                             |
| MyBatis           | 3.5.19（starter 3.0.4）         | ORM 框架                                   |
| MyBatis-Plus      | 由 `openlibing-common` 传递     | 分页、BlockAttack、字段自动填充            |
| Liquibase         | -                               | 数据库迁移                                 |
| JSch              | `com.github.mwiede:jsch` 2.28.5 | SSH / SCP；enforcer 禁止低于 2.28.5        |
| PageHelper        | 6.1.0                           | 分页                                       |
| fastjson2         | 2.0.56                          | 统一 JSON 库，已在 pom 中排除 fastjson 1.x |
| EasyExcel         | 4.0.3                           | Excel 导入导出                             |
| springdoc-openapi | 2.8.10                          | `/swagger-ui.html`                         |
| 华为云 OBS SDK    | esdk-obs-java-bundle 3.24.12    | 对象存储                                   |
| openlibing-common | 1.0.21.0                        | 内部基础 SDK                               |
| JaCoCo            | 0.8.11                          | 行覆盖率门限 20%                           |

### 响应封装

统一使用 `ResponseEntity`：

```java
ResponseEntity(code, message, data)
ResponseEntity(code, message, data, total)  // 分页场景
```

响应码定义在 `ResponseCodeEnum`：

| 枚举值              | code  | messageCn      | 使用场景         |
| ------------------- | ----- | -------------- | ---------------- |
| SUCCESS             | 200   | 成功           | 正常响应         |
| BAD_REQUEST         | 400   | 请求异常       | 参数校验失败     |
| BAD_REQUEST_PARAM   | 40001 | 请求参数异常   | 参数格式错误     |
| BAD_REQUEST_UNKNOWN | 40002 | 未知的处理类型 | 处理类型无法识别 |
| NO_LOGIN            | 401   | 没有登录       | 未认证           |
| NO_PERMISSION       | 403   | 没有权限       | 无权限访问       |
| ERROR               | 500   | 系统异常       | 服务器内部错误   |
| ERROR_QUERY         | 50001 | 查询异常       | 查询失败         |

### API 设计规范

- RESTful 风格 URL 设计。
- 路径前缀：
  - 资源管理：`/simulation/manage/{engine|qcow|server|attachment}`
  - Qemu 任务：`/simulation/qemu`
  - 健康检查：`/simulation/health-check`
- 使用 `@RequestParam`、`@RequestBody`、`@PathVariable` 明确标注参数来源。
- 请求体参数校验使用 `@Validated @RequestBody`。
- 历史文档中出现过的 `/simulation/v2/` 前缀在代码中**不存在**，不要沿用。

### 代码规范

- 所有 Java 文件必须包含华为版权头：

```java
/*
 * Copyright (c) Huawei Technologies Co., Ltd. 2026-2026. All rights reserved.
 * 版权所有 (c) 华为技术有限公司  2026-2026.
 */
```

- 使用 `@Slf4j` 替代手写 `Logger` 声明；禁止用 `System.out.println` 输出业务日志。
- 使用 Lombok 注解（`@Data`、`@Getter`、`@Setter`、`@AllArgsConstructor`、`@NoArgsConstructor`）。
- 单行宽度不超过 120 字符，避免无关的格式化和 import 重排。
- 本仓**未配置** Spotless / Checkstyle / PMD / SpotBugs，请勿引入新的格式化或静态检查插件，保持与所在文件现有风格一致。

### 数据库规范

- Liquibase changelog 位于 `src/main/resources/db/changelog/v1.0.0/`，并在 `db.changelog.xml` 中注册。
- 每个 `changeSet` 必须有唯一 `id` 与 `author`；**已执行过的 changeSet 不得修改**。
- 表命名：`t_` + 模块名 + 下划线分隔；字段下划线命名。
- 审计字段为 `create_time` / `update_time`，由 MyBatis-Plus `MetaObjectHandler` 自动填充（**不是** `last_modify_time`）。
- MyBatis XML 放在 `src/main/resources/mapper/`，命名与 Mapper 接口一致。
- 动态 `UPDATE` 的 `<set>` + `<if>` 全空时会生成非法 SQL，被 `BlockAttackInnerInterceptor` 拦截报 `MybatisPlusException: Failed to process`；Service 层更新接口须先校验"至少一个可更新字段非空"。
- primitive 类型（`boolean` / `double`）字段不能写成 `<if test="xxx != null">`（恒为真），应无条件赋值。
- 分页查询必须设置合理的 `pageSize` 上限（建议不超过 100）。
- 动态数据源：访问指定库的方法加 `@DataSource(DataSourceEnum.MYSQL/DORIS)`（默认 `DORIS`）；上下文由 `DynamicDataSourceContextHolder` 维护，**异步 / 新线程中必须显式传递**，否则会串库。

## 安全约束

- **SQL 注入**：使用 MyBatis 参数绑定 `#{}`，禁止拼接 SQL 字符串。
- **命令注入**：涉及 SSH / SCP / UNZIP / DOCKER 的命令拼接点必须使用 `ShellEscapeUtils` 做转义与白名单校验，禁止直接拼接用户输入（CWE-78）。
- **路径遍历**：文件名 / 路径使用 `ShellEscapeUtils.SAFE_FILE_NAME_PATTERN` / `SAFE_FILE_PATH_PATTERN` 校验。
- **日志泄露**：日志经 `SensitiveDataConverter` 脱敏（密码、密钥、Token、IP:Port）；审计 logger `MANAGE_LOG` 为保留真实 IP 的白名单，不要随意加入。
- **密钥管理**：AK / SK、内部认证 Token 等在配置中以 `SecurityUtil.encrypt(明文, part1)` 密文存储，运行时 `SecurityUtil.decrypt` 解密；禁止硬编码明文凭证。
- **内部认证**：`InternalSimulationAuthFilter` 校验 `X-Openlibing-Internal-Token`，并要求存在 `X-Openlibing-User` 机机身份头；启用但密钥缺失或解密失败时**必须 fail-closed 拒绝**，不得改为放行。
- **内部密钥比较**：必须使用 `MessageDigest.isEqual()` 常量时间比较，不要改成 `String.equals()`。
- **敏感配置**：使用 `@EnableEncryptableProperties` + Jasypt；`.mvn/settings.xml` 必须以 `${openlibing_mvn_repo_username}` 占位形式保留，禁止提交明文账号密码。
- **JSON**：统一使用 fastjson2（`com.alibaba.fastjson2`），不要引入 fastjson 1.x。

## 工具类使用规范

| 场景         | 使用                                                             |
| ------------ | ---------------------------------------------------------------- |
| SSH / SCP    | `utils/JschUtil`                                                 |
| 对象存储     | `client/ObsUtilClient`                                           |
| HTTP 调用    | `utils/HttpUtils`                                                |
| 日期时间     | `utils/DateTimeUtils`                                            |
| 文件操作     | `utils/FileUtil`                                                 |
| 分页         | `utils/Pages`                                                    |
| 通用工具     | `utils/CommmonUtils`（类名为三字母 m 的现状拼写，不要"纠正"）    |
| 加解密       | `utils/AesGcmUtil`、`openlibing-common` 的 `SecurityUtil`        |
| Shell 安全   | `utils/ShellEscapeUtils`                                         |
| 敏感信息脱敏 | `utils/SensitiveDataConverter`（在 `logback-spring.xml` 中注册） |

## 模块职责边界

### Controller 层

- 负责 HTTP 请求接收和响应
- 参数校验和转换
- 调用 Service 层完成业务逻辑
- 不直接操作数据库，不写业务逻辑

### Service 层

- 业务逻辑处理与事务边界
- 通过 `@Autowired` 注入 Mapper、其他 Service、Feign Client
- 异常处理和转换

### Mapper 层

- 数据库 CRUD 操作
- XML mapper 文件定义复杂 SQL
- MyBatis-Plus 条件构造器使用

### 异常处理

- 业务异常使用 `exception/ServiceException`、`exception/TaskUsingException`。
- 全局由 `exception/GlobalExceptionHandler`（`@ControllerAdvice`）统一拦截并返回 `ResponseEntity`，Controller 中不要大范围 try-catch 吞异常。
- `RuntimeException` 统一返回 `code = 500` + 固定 message `Internal Server Error`，不要把内部异常信息透出给调用方。

## 常见 AI 错误与规避

| 错误模式                                                    | 规避规则                                                                                     | 来源需求          |
| ----------------------------------------------------------- | -------------------------------------------------------------------------------------------- | ----------------- |
| 使用 Spring 原生 `ResponseEntity<T>` 而非项目自定义         | 必须导入 `com.openlibing.simulation.entity.ResponseEntity`，全局搜索确保无残留               | 通用规范          |
| MyBatis XML mapper 路径配置错误                             | 保持 `application.yaml` 中 `mybatis.mapper-locations: classpath:mapper/*.xml` 与文件位置一致 | 通用规范          |
| Liquibase changeSet 缺 id/author 或标识重复                 | 每个 `changeSet` 必须有唯一 `id` + `author`，且不修改已执行脚本                              | 通用规范          |
| 使用 JSch 未处理异常导致线程阻塞                            | SSH / SCP 必须设置超时或异步处理，避免长时间阻塞                                             | Qemu 任务         |
| 分布式锁未正确释放                                          | 获取与释放成对出现，`try-finally` 保证释放，释放时带 ownerToken 校验                         | 节点管理          |
| 动态 `UPDATE` 的 `<set>`+`<if>` 全空生成非法 SQL            | Service 层更新接口先校验"至少一个可更新字段非空"                                             | sim-resource-crud |
| primitive `boolean`/`double` 写成 `<if test="xxx != null">` | primitive 字段无条件赋值，不放进 `<if>`                                                      | sim-resource-crud |
| 删除接口被改成 `RequestMethod.DELETE`                       | 本仓删除接口统一 POST，与调用方 / 网关约定一致                                               | sim-resource-crud |
| 配置文件敏感信息硬编码                                      | 使用 `SecurityUtil.encrypt` 密文存储，运行时解密                                             | 通用规范          |
| 沿用已废弃的 `/simulation/v2/` 前缀或已下线的 Controller    | 以当前代码为准：仅 6 个 Controller，见系统设计索引                                           | 通用规范          |
| 提交前未清理检查告警                                        | 提交前 CodeCheck / SCA 告警必须清零                                                          | 通用规范          |

## 性能考虑

- 批量操作需设置合理的批量大小（建议不超过 100）
- 大数据量查询必须分页，并设置 `pageSize` 上限
- 远程操作（JSch / SCP）需设置超时
- 合理使用缓存减少数据库访问

## 质量门禁

| 门禁               | 作用         | 失败条件                                                                          |
| ------------------ | ------------ | --------------------------------------------------------------------------------- |
| JaCoCo             | 单测覆盖率   | 行覆盖率（LINE COVEREDRATIO）< 0.20                                               |
| maven-enforcer     | 依赖治理     | `RequireUpperBoundDeps` 上界冲突、重复版本声明、`com.github.mwiede:jsch < 2.28.5` |
| gitleaks           | 敏感信息     | 检出密钥 / Token / 私钥                                                           |
| platform CodeCheck | 静态代码检查 | 存在未解决的检查告警（提交前必须清零）                                            |
| sca-pr-scan        | 依赖安全扫描 | 扫描发现高危问题                                                                  |

**注意**：`maven-surefire-plugin` 配置了 `testFailureIgnore=true`，测试失败**不会**让构建失败。判断测试是否真的通过，必须查 `target/surefire-reports/` 或 `scripts/ut-report.sh` 的输出，不能只看构建结果。

## 提交前检查清单

1. `mvn clean test` 通过，并核对 `target/surefire-reports/`（不要只看 BUILD 结果）。
2. `mvn jacoco:report`，确认行覆盖率不低于 20%。
3. `pre-commit run --all-files` 全部通过。
4. CodeCheck / SCA 告警清零。
5. 确认无硬编码密钥、无 `.mvn/settings.xml` 明文改动、无超 500KB 文件。
6. 本轮交付为单个 commit，commit message 遵循 Conventional Commits 并附 `Co-authored-by` / `Generated-by` 尾注。
