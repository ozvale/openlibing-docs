# Proposal: 自建 Apollo、Eureka 服务替换为华为云 CSE 服务（nacos）

## 需求背景

openlibing 体系自建的 Apollo 配置中心与 Eureka 服务发现逐步下线，各服务需迁移到华为云 CSE 提供的 Nacos（配置中心 + 注册中心）。openlibing-codecheck 作为支撑研发流程的核心服务，同样需要完成配置与注册的替换，跟随 `openlibing-common-sdk` 版本升级到 Nacos 体系。

## 需求范围

- **替换范围**：
  - 配置中心：自建 Apollo → 华为云 CSE Nacos Config
  - 服务注册/发现：Eureka → 华为云 CSE Nacos Discovery
- **目标环境**：beta / gama / prod 三个环境均需接入 Nacos（server-addr / group / namespace）
- **依赖**：`openlibing-common-sdk` 版本升级到 `1.0.20.4`（Nacos 能力版本）
- **不做的内容**：
  - 不改变业务接口与数据模型
  - 不强求一次完成代码考古重构，仅随 common 包规范做必要适配

## 验收标准

- [x] 启动类移除 `@EnableApolloConfig` / `ConfigContextInitializer`，Spring 通过 `spring.config.import` 加载 Nacos 配置
- [x] beta / gama / prod 三个环境 yaml 均配置 Nacos server-addr / group=OPENLIBING / namespace / file-extension
- [x] `application.yaml` 开启 `spring.cloud.nacos.discovery.secure=true`
- [x] 依赖 `mongodb-driver-*` 从 spring-boot mongodb starter 排除，由 common 包统一管理
- [x] 编译通过，去除依赖差异（guava → nacos-shaded、`javax.annotation` → `org.jetbrains.annotations`）
- [x] 清理 Apollo 相关死配置（`-Dapollo.cache.file.enable`、GlobalExceptionHandler 中 apollo 异常处理、CodeCheckCollectionName 中无用枚举）
- [x] 启动可正常从 Nacos 拉取配置并注册到 Nacos

## 关联

- 业务 PR: openlibing/openlibing-codecheck#322