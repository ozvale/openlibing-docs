# apollo-to-nacos-migration

## 需求背景

openlibing 体系正将自建 Apollo 配置中心 + Eureka 服务发现统一替换为华为云 CSE Nacos（配置 + 注册一体化），以保持技术栈一致并下线自建 Apollo/Eureka 运维成本。openlibing-codecheck 仓已完成同模式迁移，openlibing-cicd 仓需按相同模式改造。

迁移依据：`apollo-eureka-to-cse-nacos-migration` skill（openlibing-ai-engineering/personal-skills/common/nacos）。

FE 需求名称：自建apollo、eureka服务替换为华为云CSE服务（nacos）

## 功能描述

**做什么**：

- 升级 `openlibing-common` 1.0.19.5 → 1.0.20.4（内置 Nacos 依赖，移除 Apollo/Eureka 传递依赖）
- 启动类 `OpenlibingCicdApplication` 移除 `@EnableApolloConfig` 与 `ConfigContextInitializer`，新增静态代码块关闭 Nacos 配置快照落盘（`SnapShotSwitch.setIsSnapShot(false)`）
- `application-beta.yaml` / `application-gama.yaml` / `application-prod.yaml` 三个环境 profile 全部由 Apollo 块改为 Nacos `spring.config.import` + `cloud.nacos`（config + discovery）
- `application.yaml` 追加 `spring.cloud.nacos.discovery.secure: true`，注册为 HTTPS 服务
- `start.sh` 删除 `-Dapollo.cache.file.enable=false` JVM 参数
- 业务代码中 `com.google.common.*` 引用改为 `com.alibaba.nacos.shaded.com.google.common.*`（AuthInterceptor、ExcelUtils）
- Apollo 的 `StringUtils` 引用改为 `org.apache.commons.lang3.StringUtils`（CrossRegionServiceImpl、SafeRequestUtils）
- 显式声明 `jakarta.ws.rs-api:3.1.0`（原为 Apollo 传递依赖，Apollo 移除后需补偿）
- `PipelineControllerTest` 增加 `@TestPropertySource` 禁用 Nacos 配置导入检查，适配 `@WebMvcTest` 切片上下文

**不做什么**：

- 不新建 `application-local.yaml`（仓库无此文件，本地开发沿用 beta namespace）
- 不清理 `parameter_verification_exception_type` 死配置（仓库中未发现该配置使用）
- 不清理 `OPLB_ACCESS_TOKEN` 未使用常量（仓库中未发现该常量）
- 不替换 `javax.annotation.Nullable`（仓库中未发现该引用）
- 不做 mongodb driver exclusion（仓库无 mongodb 依赖，走 MyBatis）

## 验收标准

- [x] `mvn clean compile -DskipTests` 通过（guava 包路径替换无误）
- [x] `mvn test` 相关单元测试通过（含 PipelineControllerTest 适配）
- [x] 启动类无 `@EnableApolloConfig` 与 `ConfigContextInitializer`（含 import）
- [x] `application-beta.yaml` 使用 Nacos `spring.config.import`，namespace 为 `openlibing-beta`
- [x] `application-gama.yaml` 使用 Nacos `spring.config.import`，namespace 为 `openlibing-gamma`
- [x] `application-prod.yaml` 使用 Nacos `spring.config.import`，namespace 为 `openlibing-prod`（独立 CSE 实例）
- [x] `application.yaml` 含 `spring.cloud.nacos.discovery.secure: true`
- [x] `start.sh` 不再含 `-Dapollo.cache.file.enable=false`
- [x] `AuthInterceptor.java` 与 `ExcelUtils.java` 的 guava import 已替换为 shaded 路径
- [x] Apollo 的 `StringUtils` 引用已替换为 commons-lang3
- [x] 业务代码无任何 `com.ctrip.framework.apollo` 代码级引用（仅剩 javadoc 注释提及）

## 影响范围

**受影响模块/文件**（12 个）：

- `pom.xml`
- `src/main/java/com/openlibing/cicd/OpenlibingCicdApplication.java`
- `src/main/java/com/openlibing/cicd/business/service/impl/CrossRegionServiceImpl.java`
- `src/main/java/com/openlibing/cicd/common/auth/AuthInterceptor.java`
- `src/main/java/com/openlibing/cicd/common/utils/ExcelUtils.java`
- `src/main/java/com/openlibing/cicd/common/utils/SafeRequestUtils.java`
- `src/main/resources/application.yaml`
- `src/main/resources/application-beta.yaml`
- `src/main/resources/application-gama.yaml`
- `src/main/resources/application-prod.yaml`
- `src/test/java/.../controller/PipelineControllerTest.java`
- `start.sh`

**部署影响**：beta / gama / prod 三环境部署后需确认 Nacos 连通性、服务注册、配置拉取正常，及 CSE 网关 HTTPS 调用（`secure: true`）正常。
