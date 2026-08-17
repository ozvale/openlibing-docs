# apollo-eureka-to-nacos

## 需求背景

对应业务 Issue：openlibing/openlibing-sbom#62
FE 需求名称：自建apollo、eureka服务替换为华为云CSE服务（nacos）

为统一平台基础服务架构，提升配置管理及服务注册发现能力，将现有自建 Apollo 配置中心与 Eureka 服务发现迁移至华为云 CSE（Nacos）服务，并同步调整 openlibing-sbom 仓的相关服务配置，满足平台统一运维和持续演进需求。

Issue 62 的迁移指南以 `openlibing-platform-release` 为示例项目，本变更需将该指南适配到 `openlibing-sbom` 仓的实际情况（`.properties` 配置格式、dev/prod/gama 三个 profile）。

## 功能描述

### 做什么

1. **pom 依赖调整**：升级 `openlibing-common` 到 **1.0.20.0**（依赖树确认 1.0.20.0 已传递引入 `spring-cloud-starter-alibaba-nacos-config/discovery:2025.0.0.0` + `nacos-client:3.0.3`，无需手动声明 nacos 依赖，也无需添加 `spring-cloud-alibaba-dependencies` BOM）；从 `sbom-web/pom.xml` 移除 `spring-cloud-starter-netflix-eureka-client` 直接依赖；清理根 pom 中不再使用的 `apollo-client` / `eureka-client` 版本声明。
2. **启动类调整**（`SbomManagerApplication.java`）：新增 `SnapShotSwitch.setIsSnapShot(false)` 静态块（配置中心数据不落盘）；**删除** sbom 自己的 `ConfigContextInitializer`（原从环境变量 TRUST_STORE 加载 SSL trustStore，迁移到 Nacos 后由配置中心统一管理，不再需要）及 `SbomManagerApplication` 中其 import 与 `addInitializers` 调用。
3. **配置文件调整**（3 个 profile `.properties` 文件，`application.properties` 公共配置仅删除 apollo 的 app.id）：
   - `application-dev.properties`：移除 eureka 配置，新增 Nacos 配置（namespace=openlibing-beta，server-addr=1.95.74.1:31252，不配 secure 因 dev 是 HTTP）。
   - `application-prod.properties`：移除 eureka + apollo 配置，新增 Nacos 配置（namespace=openlibing-prod，server-addr=华为云 CSE Nacos，secure=true 注册为 HTTPS）。
   - `application-gama.properties`：移除 eureka + apollo 配置，新增 Nacos 配置（namespace=openlibing-gamma，server-addr=华为云 CSE Nacos，secure=true 注册为 HTTPS）。
4. **启动脚本调整**（`start-openlibing-sbom.sh`）：删除 `-Dapollo.cache.file.enable=false` JVM 参数。

### 不做什么

- 不修改 sbom 业务代码（Grep 确认 Java 源码无 apollo/eureka/nacos 硬编码引用）。
- 不添加 `spring-cloud-alibaba-dependencies` BOM（openlibing-common 1.0.20.0 已传递管理 nacos 版本）。
- 不引入单元测试（配置类迁移，无行为变化可测，按 ai_memory 规则 UT 在 Phase 4 生成；本变更属配置迁移，必要时再补）。
- 不修改 `application.properties` 中已存在的 `APPLICATION_ID`（保留原值）。

## 验收标准

- [ ] `mvn clean compile -pl sbom-web -am` 编译通过（移除 eureka-client 依赖 + 删除 ConfigContextInitializer 后无编译错误）。
- [ ] 4 个 `.properties` 文件不再包含 `apollo.*` 和 `eureka.*` 配置项。
- [ ] 4 个 `.properties` 文件包含完整的 `spring.cloud.nacos.config.*` 和 `spring.cloud.nacos.discovery.*` 配置。
- [ ] `start-openlibing-sbom.sh` 不再包含 `-Dapollo.cache.file.enable` 参数。
- [ ] `SbomManagerApplication.java` 包含 `SnapShotSwitch.setIsSnapShot(false)` 静态块。
- [ ] `ConfigContextInitializer.java` 已删除，`SbomManagerApplication` 无残留引用（编译通过）。
- [ ] `sbom-web/pom.xml` 不再直接依赖 `spring-cloud-starter-netflix-eureka-client`。
- [ ] 改动仅限 `openlibing-sbom` 业务仓指定文件，无无关重构。

## 影响范围

| 文件                                                                                    | 操作 | 说明                                                                    |
| --------------------------------------------------------------------------------------- | ---- | ----------------------------------------------------------------------- |
| `pom.xml`（根）                                                                         | 修改 | 升级 openlibing-common 到 1.0.20.0；清理 apollo/eureka 版本声明         |
| `sbom-web/pom.xml`                                                                      | 修改 | 移除 spring-cloud-starter-netflix-eureka-client 依赖                    |
| `sbom-web/src/main/java/org/opensourceway/sbom/SbomManagerApplication.java`             | 修改 | 新增 SnapShotSwitch 静态块；移除 ConfigContextInitializer import 与调用 |
| `sbom-web/src/main/resources/application.properties`                                    | 修改 | 删除 apollo app.id 配置项                                               |
| `sbom-web/src/main/resources/application-dev.properties`                                | 修改 | eureka → nacos（beta + 本地地址，无 secure）                            |
| `sbom-web/src/main/resources/application-prod.properties`                               | 修改 | eureka + apollo → nacos（prod + 华为云，secure=true）                   |
| `sbom-web/src/main/resources/application-gama.properties`                               | 修改 | eureka + apollo → nacos（gamma + 华为云，secure=true）                  |
| `start-openlibing-sbom.sh`                                                              | 修改 | 删除 apollo cache JVM 参数                                              |
| `cache/src/main/java/org/opensourceway/sbom/cache/config/ConfigContextInitializer.java` | 删除 | 原 trustStore 加载类，迁移后不再需要                                    |

## 跨仓影响

无跨仓代码改动。本变更仅限 `openlibing-sbom` 仓内部配置迁移。配置中心实际数据（Nacos 上的 sbom / application Data ID 内容）需由运维在华为云 CSE Nacos 各 namespace 预先配置，不在本 PR 范围内。
