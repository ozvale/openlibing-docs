# design: 升级 openlibing-common 至 1.0.21.2-SNAPSHOT（Boot4/Jackson3 适配）

> Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/450
> 参考实现: codecheck eb57e25d、coderepo b08c581c

## 1. 方案设计

复刻 codecheck eb57e25d 的升级路径，在 operation_log_architecture_v2 分支上将 common 从 1.0.21.1-SNAPSHOT 升至 1.0.21.2-SNAPSHOT（Boot 4.1.1 / Spring Framework 7 / Jackson 3）。依赖管理策略：拆除所有与 Boot BOM 冲突的钉扎（spring-framework-bom、Boot starter 版本、junit、mockito），交由 common 引入的 spring-boot-dependencies 4.1.1 统一仲裁；构建插件同步升版（surefire 3.5.5、spring-boot-maven-plugin 4.1.1）。

分支上 5 个 LogHandler（Image/PipelineConfig/PipelineWhiteList/PrAccessLabel/Shortcut）已是 matches/before/after 新契约，与 1.0.21.2 的 AbstractLogHandler 签名一致，预计编译期零适配（与 codecheck 需要重写 Handler 不同）。

## 2. 实现逻辑设计

- Jackson 2→3：包名迁移 com.fasterxml.jackson.core/databind → tools.jackson.core/databind；annotation 包（com.fasterxml.jackson.annotation）在 Jackson 3 中保留原包名，无需改动；`JsonProcessingException` → `JacksonException`（unchecked）；自定义反序列化器 `JsonDeserializer` → `ValueDeserializer`，兜底异常改用 `MismatchedInputException.from(...)` 工厂
- Rabbit 重试：spring-rabbit 4.1.1 移除 `RetryInterceptorBuilder.maxAttempts(int)`，改用 `maxRetries(int)`（委托 Spring Core RetryPolicy，总尝试 = 1 + maxRetries）。旧 `maxAttempts(3)` 语义为总尝试 3 次，等价改写为 `maxRetries(2)`，同步修正注释
- yaml 变更：新增 `spring.jackson.use-jackson2-defaults: true`（复刻 codecheck，保持 Jackson 2 序列化默认行为，减少 Boot 4 Jackson 3 行为差异）。曾评估 feign 块内 ribbon 配置为死配置并删除，后按用户要求恢复保留（后续需求需在 feign 块追加配置），该项维持原状
- 测试切片迁移：Boot 4 将 `@WebMvcTest` 从 spring-boot-test-autoconfigure 拆到独立构件，pom 新增 test 依赖 `spring-boot-starter-webmvc-test`（版本由 Boot BOM 仲裁），PipelineControllerTest 的 import 迁至 `org.springframework.boot.webmvc.test.autoconfigure`
- mybatis-plus 传递升级：common BOM 将 mybatis-plus 从 3.5.10.1 带到 3.5.17（spring-boot3-starter → spring-boot4-starter）。3.5.17 中 `AbstractWrapper.in()` 在构建期即解析 Lambda 列名，纯 Mockito 单测若无实体元数据会抛 "can not find lambda cache"。按仓内既有模式在 ImageServiceImplTest.deleteImage 中补 `TableInfoHelper.initTableInfo(...)` 初始化 ImageDetailEntity 元数据
- **BETA 运行时异常修复（首版部署后发现）**：Boot 3 时代的 starter 自动配置引用 Boot 3 内部类（Boot 4 已模块化移包），导致启动期 NoClassDefFoundError。三处修复：(1) `redisson-spring-boot-starter:3.25.0` → `redisson` core（BOM 仲裁 3.45.1）——RedisConfig 已手动 `Redisson.create()` 装配 RedissonClient、spring-data-redis 走 Jedis 连接工厂，starter 自动配置纯多余且是崩溃元凶；(2) `springdoc` 2.8.10 拆钉扎 → BOM 3.1.1（Boot 4 线，cicd main 零代码引用）；(3) `pagehelper` 2.1.0 → 4.1.1（官方 Boot 4 线，基于 mybatis-spring-boot-starter 4.0.1，保留原 mybatis 排除与 mybatis-plus 共存）

## 3. 类设计

| 类                                                                                | 改动                                                                                    |
| --------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| StringOrListDeserializer / StringScalarDeserializer                               | JsonDeserializer → ValueDeserializer，异常类型适配                                      |
| RabbitConnectionFactoryConfig                                                     | maxAttempts(3) → maxRetries(2)，注释修正                                                |
| HwCloudClient / HwBuildClient / PipelineStatusThirdPartyApiClient                 | ObjectMapper 及异常捕获类型包名迁移                                                     |
| PipelineEventConsumer / PipelineLogQuerySupport / PipelineServiceImpl / ErrorCode | import 包名迁移、异常类型迁移                                                           |
| OperationLogHandlerSupport 及 5 个 LogHandler                                     | 无需改动，编译验证                                                                      |
| PipelineControllerTest                                                            | @WebMvcTest import 迁至 Boot 4 新包                                                     |
| ImageServiceImplTest                                                              | deleteImage 补 TableInfoHelper.initTableInfo（适配 mybatis-plus 3.5.17 构建期列名解析） |

## 4. 数据模型设计

无变化。不涉及数据库 schema、Entity、DTO 结构变动。

## 5. 性能设计

无变化。Jackson 3 与 spring-rabbit 4.1.1 均为常规升版，无额外开销路径；消费端重试参数（总尝试 3 次、退避 1s/2s/封顶 5s、耗尽后 republish 60s 延迟队列）保持与升级前一致。

## 6. API接口设计

无变化。Controller 层零改动，无对外接口签名变动，无需前端适配。

## 7. 安全设计

升级动机即安全整改：修复 common 传递引入的开源漏洞与高危 License（jackson、spring-webmvc、logback 等）。cicd 无 mongodb 依赖，codecheck 发现的 spring-boot 4 与 mongodb 4.0 不兼容问题在本仓不适用。其余安全姿态（SSL 证书校验、请求体上限、凭证解密）不受本次升级影响，回归验证覆盖华为云 API 连通性。
