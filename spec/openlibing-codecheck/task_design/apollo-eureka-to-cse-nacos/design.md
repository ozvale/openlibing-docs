# Design: 自建 Apollo、Eureka 服务替换为华为云 CSE 服务（nacos）

## 技术方案

依赖 `openlibing-common-sdk` 1.0.20.4 提供的 Nacos 配置/注册能力，通过 Spring Boot 标准 `spring.config.import` + `spring.cloud.nacos` 替换 Apollo bootstrap 与 Eureka。

### 配置中心迁移

- **加载方式**：`spring.config.import=optional:nacos:<namespace>`，依次加载 `application` / `framework` / `cicd` / `codecheck` / `xxl-job` 五个命名空间，`.properties` 后缀
- **Nacos 元数据**（beta / gama / prod 各自独立）：
  - `server-addr`: 各环境独立的 CSE Nacos 地址（`*.nacos.cn-southwest-2.cse.myhuaweicloud.com:8848`）
  - `group`: `OPENLIBING`
  - `namespace`: `openlibing-beta` / `openlibing-gamma` / `openlibing-prod`
  - `file-extension`: `properties`
- **安全**：`application.yaml` 增加 `spring.cloud.nacos.discovery.secure=true`，注册/拉取走安全通道

### 服务注册迁移

Eureka 不再使用，改为 Nacos Discovery。依赖 common 包即可，无需保留 eureka-client 依赖。

### 依赖适配

| 变更 | 说明 |
| ---- | ---- |
| `openlibing-common-sdk` 1.0.19.9 → 1.0.20.4 | 升级到支持 Nacos 的 common 版本 |
| mongodb-starter 排除 `mongodb-driver-core/sync/reactivestreams/crypt/bson` | 由 common 包统一管理，避免版本冲突 |
| `com.google.common.*` → `com.alibaba.nacos.shaded.com.google.common.*` | guava 由 Nacos 别名引入（Lists / Strings），修复依赖缺失 |
| `javax.annotation.Nullable` → `org.jetbrains.annotations.Nullable` | common 包统一注解规范 |

### Apollo 死配置清理

| 文件 | 清理内容 |
| ---- | -------- |
| `start.sh` | 移除 `-Dapollo.cache.file.enable=false` |
| `GlobalExceptionHandler` | 移除 apollo 相关异常处理（21 行） |
| `CodeCheckCollectionName` | 移除无用枚举（3 项） |
| `OpenlibingCodecheckApplication` | 移除 `@EnableApolloConfig` 与 `ConfigContextInitializer`，启用 Nacos `SnapShotSwitch`（关闭快照） |

## 涉及文件

| 文件 | 操作 | 说明 |
| ---- | ---- | ---- |
| `pom.xml` | 修改 | common-sdk 版本升级；mongodb-starter 排除 driver 依赖 |
| `OpenlibingCodecheckApplication.java` | 修改 | 移除 Apollo 注解/初始化器，新增 SnapShotSwitch 关闭 |
| `application.yaml` | 修改 | 增加 nacos discovery.secure |
| `application-beta.yaml` / `application-gama.yaml` / `application-prod.yaml` | 修改 | apollo → nacos 配置迁移（gama 为新增接入） |
| `CheckboardDelegateImpl` / `DatarecoveryDelegateImpl` / `ScheduleDelegateImpl` / `XxlJobHandler` | 修改 | guava 导入改为 nacos-shaded |
| `CodeCheckCollectionName` / `GlobalExceptionHandler` | 修改 | 移除 apollo 相关无用代码 |
| `CommonHelper` | 修改 | `javax.annotation.Nullable` → `org.jetbrains.annotations.Nullable` |
| `start.sh` | 修改 | 移除 apollo cache 参数 |

## 风险 & 缓解

- **配置文件迁移遗漏**：各环境 namespace / server-addr 均需在 CSE 上预置对应配置集，否则启动拉取失败。缓解：迁移前核对各环境 Nacos 配置集已就绪。
- **common 包版本冲突**：mongodb / guava 依赖由 common 统一管理，存在驱动版本与服务端不兼容风险。缓解：以 common 1.0.20.4 锁定版本为准，构建期校验。
- **注册地址消费方变化**：Eureka 下线的前提下，服务间调用地址改由 Nacos 注册表提供。缓解：随 common 包双注册逻辑平滑切换，验证跨服务调用。

## 跨仓影响

- 依赖 `openlibing/commons`（openlibing-common-sdk 1.0.20.4）的 Nacos 能力
- 与 openlibing 体系其他服务（cicd / coderepo / framework 等）同批迁移，需协调各环境 Nacos 配置集
  
## 测试

- 构建校验：`mvn -DskipTests package` 编译通过
- 启动验证：beta 环境启动成功，能从 Nacos 拉取配置并完成注册（随 CI 流水线验证）