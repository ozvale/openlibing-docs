# 【openlibing-sbom】自建apollo、eureka服务替换为华为云CSE服务（nacos）— EDEVOPS 设计文档

---

## 1. 方案设计

### 1.1 背景

为统一平台基础服务架构，提升配置管理及服务注册发现能力，将 openlibing-sbom 现有自建 Apollo 配置中心与 Eureka 服务发现迁移至华为云 CSE（Nacos）服务。迁移后 sbom 不再维护独立的配置中心与服务注册组件，统一纳入平台运维体系，满足持续演进需求。

关联 Issue: [#62](https://gitcode.com/openlibing/openlibing-sbom/issues/62)
FE 需求名称：自建apollo、eureka服务替换为华为云CSE服务（nacos）

Issue 62 的迁移指南以 `openlibing-platform-release` 为示例项目，本设计文档将该指南适配到 `openlibing-sbom` 仓的实际情况（`.properties` 配置格式、dev/prod/gama 三个 profile）。

### 1.2 方案概述

通过升级 `openlibing-common` 到 **1.0.20.0**（传递引入 `spring-cloud-starter-alibaba-nacos-config/discovery:2025.0.0.0` + `nacos-client:3.0.3`），将 sbom 的配置中心从 Apollo 切换为 Nacos Config、服务发现从 Eureka 切换为 Nacos Discovery。改动范围限定在 pom 依赖、启动类、3 个 profile 配置文件、公共配置文件、启动脚本，**不修改业务代码**。迁移后：
- 配置通过 Nacos Config Data ID（`application-local`/`application` + `sbom`）动态加载
- 服务通过 Nacos Discovery 注册（dev HTTP / prod+gama HTTPS secure）
- 启动类新增 `SnapShotSwitch.setIsSnapShot(false)` 静态块禁止配置落盘快照
- 删除 sbom 自有的 `ConfigContextInitializer`（原 trustStore 加载类，由配置中心统一管理）

### 1.3 方案架构

```
迁移前                                  迁移后
┌───────────────────────────┐         ┌───────────────────────────┐
│ SbomManagerApplication    │         │ SbomManagerApplication    │
│  ├ ConfigContextInitializer│ ──X──→ │  ├ SnapShotSwitch(false)  │ ← 新增静态块
│  │  (trustStore env 加载)  │  删除   │  └ (无 ConfigContext...)  │
│  └ @ComponentScan         │         │                           │
└─────────────┬─────────────┘         └─────────────┬─────────────┘
              │                                     │
   ┌──────────┴──────────┐              ┌──────────┴──────────┐
   ▼                     ▼              ▼                     ▼
Apollo Client        Eureka Client   Nacos Config         Nacos Discovery
(app.id=xxx,         (registry with  (spring.cloud.nacos  (spring.cloud.nacos
 cache.file.enable)   eureka.client.*) .config.*)           .discovery.*)
   │                     │              │                     │
   ▼                     ▼              ▼                     ▼
自建 Apollo            自建 Eureka     华为云 CSE Nacos      华为云 CSE Nacos
(配置中心)            (服务注册)       (Config Data ID)      (Service Registry)

profile:                profile:
  dev   → eureka only      dev   → nacos (1.95.74.1:31252, namespace=beta, 无 secure)
  prod  → apollo+eureka    prod  → nacos (华为云CSE, namespace=prod, secure=true)
  gama  → apollo+eureka    gama  → nacos (华为云CSE, namespace=gamma, secure=true)
```

### 1.4 关键技术决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| nacos 依赖引入方式 | 升级 `openlibing-common` 到 1.0.20.0（传递引入） | Issue 62 指南明确：1.0.20.0 已传递 `spring-cloud-starter-alibaba-nacos-config/discovery:2025.0.0.0` + `nacos-client:3.0.3`，无需手动声明 nacos 依赖 |
| BOM 管理 | 不添加 `spring-cloud-alibaba-dependencies` BOM | openlibing-common 1.0.20.0 已传递管理 nacos 版本，手动加 BOM 会引入版本冲突风险 |
| eureka-client 处理 | 从 `sbom-web/pom.xml` 移除直接依赖 | 迁移到 Nacos Discovery 后不再需要；openlibing-common 已不再传递 eureka-client |
| apollo/eureka 版本声明 | 清理根 pom 中 `<properties>` 与 `<dependencyManagement>` 里的 `apollo-client` / `eureka-client` 版本 | 已无引用，保留为死代码 |
| 配置格式 | 保持 `.properties`（不转 yaml） | sbom 既有配置风格统一为 properties，保持向后兼容与团队习惯；与 openlibing-cicd 的 yaml 风格不同，但仓内一致优先 |
| SnapShotSwitch | 启动类静态块 `SnapShotSwitch.setIsSnapShot(false)` | 禁止 nacos-client 在本地生成 `${user.home}/nacos/` 配置快照文件，避免容器环境文件残留 + 配置泄漏风险 |
| ConfigContextInitializer | 删除 | 原从 `TRUST_STORE` 环境变量加载 SSL trustStore 到 Spring Context；迁移 Nacos 后 trustStore 仍由 JVM 参数 `-Djavax.net.ssl.trustStore` 加载（start 脚本保留），Spring 层的 ContextInitializer 不再需要 |
| trustStore 加载 | 保留 start 脚本 `-Djavax.net.ssl.trustStore=${TRUST_STORE}` | JVM 级 SSL 信任库与配置中心无关，仍需 trustStore 访问 HTTPS 资源（Nacos HTTPS、外部 API） |
| dev profile server-addr | `1.95.74.1:31252`（测试环境 Nacos） | dev 是 HTTP，不配 `secure`，使用测试环境本地化 Nacos 地址 |
| prod/gama profile server-addr | `ee0b6e65-...nacos.cn-southwest-2.cse.myhuaweicloud.com:8848`（华为云 CSE Nacos） | prod/gama 统一使用华为云 CSE Nacos 实例 |
| prod/gama discovery.secure | `true` | prod/gama 注册为 HTTPS（`server.ssl.enabled=true`），discovery 需告知 Nacos 服务是 HTTPS，否则网关路由 HTTP 到 HTTPS 服务会握手失败 |
| dev discovery.secure | 不配置（默认 false） | dev `server.ssl.enabled=false`，HTTP 注册 |
| namespace 命名 | `openlibing-beta` / `openlibing-prod` / `openlibing-gamma` | 与 Issue 62 指南一致，三环境隔离配置 |
| config group | `OPENLIBING` | 平台统一 group 命名，便于跨服务配置聚合管理 |
| config Data ID | `application-local` + `sbom`（dev）/ `application` + `sbom`（prod/gama） | `application*` 为平台公共配置，`sbom` 为 sbom 专属配置；dev 用 `application-local` 本地化配置，prod/gama 用 `application` 平台配置 |
| spring.config.import | `optional:nacos:xxx` | `optional:` 前缀保证 Data ID 不存在时启动不失败（向后兼容存量环境） |
| 配置加密 | 保留 Jasypt `@EnableEncryptableProperties` | 已有加密机制不变，`KEY_STORE_PASSWORD` 等仍通过 Jasypt + 环境变量注入 |

---

## 2. 实现逻辑设计

### 2.1 整体迁移流程

```
1. pom 依赖调整
   ├─ 根 pom: openlibing-common 1.0.18.x → 1.0.20.0
   ├─ 根 pom: 删除 <apollo.version> / <eureka.version> 属性
   ├─ 根 pom: 删除 dependencyManagement 中 apollo-client / eureka-client 声明
   └─ sbom-web/pom.xml: 删除 spring-cloud-starter-netflix-eureka-client 直接依赖
       ↓ (openlibing-common 1.0.20.0 传递引入 nacos config/discovery)
2. 启动类调整 (SbomManagerApplication.java)
   ├─ 新增 import com.alibaba.nacos.client.config.utils.SnapShotSwitch
   ├─ 新增 static { SnapShotSwitch.setIsSnapShot(false); }
   └─ 删除 ConfigContextInitializer import + addInitializers(new ConfigContextInitializer()) 调用
       ↓
3. 配置文件调整 (3 profile + 公共)
   ├─ application.properties: 删除 apollo.app.id
   ├─ application-dev.properties: 删 eureka.* → 加 nacos config+discovery (beta, 无 secure)
   ├─ application-prod.properties: 删 eureka.* + apollo.* → 加 nacos config+discovery (prod, secure=true)
   └─ application-gama.properties: 删 eureka.* + apollo.* → 加 nacos config+discovery (gamma, secure=true)
       ↓
4. 启动脚本调整 (start-openlibing-sbom.sh)
   └─ 删除 -Dapollo.cache.file.enable=false 参数（保留 trustStore 等其他 JVM 参数）
       ↓
5. 删除 ConfigContextInitializer.java
   └─ cache/.../config/ConfigContextInitializer.java 整文件删除
       ↓
6. 编译验证 mvn clean compile -pl sbom-web -am → BUILD SUCCESS
```

### 2.2 Nacos 配置加载机制

```
Spring Boot 启动
  │
  ├─ 1. 加载 application.properties (公共配置, 无 profile)
  │     └─ APPLICATION_ID 等保留 (不动)
  │
  ├─ 2. 加载 application-{profile}.properties
  │     ├─ spring.config.import=optional:nacos:application[-local],optional:nacos:sbom
  │     │   ↓
  │     │   触发 NacosConfigDataLocationResolver 解析
  │     │   ↓
  │     │   从 Nacos 拉取 Data ID:
  │     │     - application / application-local (group=OPENLIBING, namespace=openlibing-{profile})
  │     │     - sbom (group=OPENLIBING, namespace=openlibing-{profile})
  │     │   ↓
  │     │   合并到 Spring Environment (优先级高于本地 application-{profile}.properties)
  │     │
  │     ├─ spring.cloud.nacos.config.server-addr     → Nacos Config 服务端
  │     ├─ spring.cloud.nacos.config.namespace      → 环境隔离 (beta/prod/gamma)
  │     ├─ spring.cloud.nacos.config.group           → OPENLIBING
  │     ├─ spring.cloud.nacos.config.file-extension → properties
  │     │
  │     ├─ spring.cloud.nacos.discovery.server-addr → Nacos Discovery 服务端
  │     ├─ spring.cloud.nacos.discovery.namespace   → 环境隔离
  │     ├─ spring.cloud.nacos.discovery.group        → OPENLIBING
  │     └─ spring.cloud.nacos.discovery.secure       → (仅 prod/gama) HTTPS 注册
  │
  ├─ 3. SnapShotSwitch.setIsSnapShot(false) (静态块, 类加载时执行)
  │     └─ 禁止 nacos-client 写本地快照文件 ${user.home}/nacos/
  │
  └─ 4. Nacos Discovery 自动注册
        └─ 服务实例注册到 Nacos (sbom service)
           dev:  HTTP  注册 (secure 未配置)
           prod: HTTPS 注册 (secure=true, server.ssl.enabled=true)
           gama: HTTPS 注册 (secure=true, server.ssl.enabled=true)
```

### 2.3 各 profile 配置对比

| 配置项 | dev (beta) | prod | gama (gamma) |
|--------|------------|------|--------------|
| `spring.config.import` | `optional:nacos:application-local,optional:nacos:sbom` | `optional:nacos:application,optional:nacos:sbom` | `optional:nacos:application,optional:nacos:sbom` |
| `spring.cloud.nacos.server-addr` | `1.95.74.1:31252` | `ee0b6e65-...myhuaweicloud.com:8848` | `ee0b6e65-...myhuaweicloud.com:8848` |
| `config.server-addr` | 同上 | 同上 | 同上 |
| `config.namespace` | `openlibing-beta` | `openlibing-prod` | `openlibing-gamma` |
| `config.group` | `OPENLIBING` | `OPENLIBING` | `OPENLIBING` |
| `config.file-extension` | `properties` | `properties` | `properties` |
| `discovery.server-addr` | 同上 | 同上 | 同上 |
| `discovery.namespace` | `openlibing-beta` | `openlibing-prod` | `openlibing-gamma` |
| `discovery.group` | `OPENLIBING` | `OPENLIBING` | `OPENLIBING` |
| `discovery.secure` | 不配置（默认 false，HTTP） | `true`（HTTPS） | `true`（HTTPS） |
| `server.ssl.enabled` | `false` | `true` | `true` |
| `server.ssl.key-store` | 不配置 | `/opt/app/openlibing/cert/openlibing.pfx` | 同 prod |
| `server.ssl.key-store-password` | 不配置 | `${KEY_STORE_PASSWORD}` (Jasypt) | 同 prod |

### 2.4 配置项删除清单

| 文件 | 删除的配置项 |
|------|--------------|
| `application.properties` | `apollo.app.id=xxx`（Apollo 应用标识） |
| `application-dev.properties` | `eureka.client.*` / `eureka.instance.*`（Eureka 注册配置） |
| `application-prod.properties` | `eureka.client.*` / `eureka.instance.*` + `apollo.*`（Apollo meta + cache） |
| `application-gama.properties` | `eureka.client.*` / `eureka.instance.*` + `apollo.*` |
| `start-openlibing-sbom.sh` | `-Dapollo.cache.file.enable=false` JVM 参数 |

### 2.5 启动顺序与 SnapShotSwitch 时机

```
JVM 启动
  ├─ -Djavax.net.ssl.trustStore=${TRUST_STORE}  (JVM 级 trustStore 加载, 保留)
  └─ java -jar openlibing-sbom-1.0.0.jar
       │
       ├─ 类加载 SbomManagerApplication
       │   └─ static {} 执行 SnapShotSwitch.setIsSnapShot(false)
       │      ↓ (在 nacos-client 初始化前禁用快照)
       │
       ├─ SpringApplication.run
       │   ├─ 加载 application.properties + application-{profile}.properties
       │   ├─ NacosConfigDataLocationResolver 触发拉取 (此时 SnapShotSwitch 已 false, 不写本地)
       │   ├─ NacosDiscoveryClient 初始化 + 注册
       │   └─ 业务 Bean 初始化
       │
       └─ Sbom service has started
```

### 2.6 边界场景处理

| 场景 | 处理 |
|------|------|
| Nacos Config Data ID 不存在 | `spring.config.import=optional:nacos:xxx` 的 `optional:` 前缀保证启动不失败，使用本地 properties 兜底 |
| Nacos 服务端不可达 | nacos-client 默认重试 + 超时，最终启动失败（与 Apollo 不可达行为一致）；prod/gama 走华为云 CSE SLB，高可用 |
| namespace 配置错误 | 拉取到错误 namespace 的配置，可能导致业务异常；需运维在 Nacos 各 namespace 预配置 `application`/`sbom` Data ID |
| `KEY_STORE_PASSWORD` 未注入 | Jasypt 解密失败，`server.ssl.key-store-password` 为空，SSL 初始化失败（prod/gama 启动报错） |
| trustStore 环境变量未设置 | JVM 启动失败（`-Djavax.net.ssl.trustStore=${TRUST_STORE}` 解析失败）；与迁移前行为一致 |
| dev 误配 secure=true | dev `server.ssl.enabled=false`，discovery.secure=true 会告知 Nacos 服务是 HTTPS，但实际 HTTP，网关路由失败 → dev 不配 secure（默认 false） |
| prod/gama 漏配 secure=true | 服务以 HTTPS 启动但注册为 HTTP，网关 HTTP 路由到 HTTPS 端口握手失败 → prod/gama 必须配 secure=true |

---

## 3. 类设计

### 3.1 修改类清单

| 类/文件 | 模块 | 路径 | 变更 |
|---------|------|------|------|
| 根 `pom.xml` | 根 | `pom.xml` | `openlibing-common` 升级到 1.0.20.0；删除 `<apollo.version>` / `<eureka.version>` 属性；删除 `dependencyManagement` 中 `apollo-client` / `eureka-client` 声明 |
| `sbom-web/pom.xml` | sbom-web | `sbom-web/pom.xml` | 删除 `spring-cloud-starter-netflix-eureka-client` 直接依赖 |
| `SbomManagerApplication` | sbom-web | `sbom-web/.../SbomManagerApplication.java` | 新增 `SnapShotSwitch` import + 静态块；移除 `ConfigContextInitializer` import 与 `addInitializers` 调用 |
| `application.properties` | sbom-web | `sbom-web/.../resources/application.properties` | 删除 `apollo.app.id` 配置项 |
| `application-dev.properties` | sbom-web | `sbom-web/.../resources/application-dev.properties` | 删 eureka 配置 → 加 nacos config+discovery（beta，无 secure） |
| `application-prod.properties` | sbom-web | `sbom-web/.../resources/application-prod.properties` | 删 eureka+apollo → 加 nacos config+discovery（prod，secure=true） |
| `application-gama.properties` | sbom-web | `sbom-web/.../resources/application-gama.properties` | 删 eureka+apollo → 加 nacos config+discovery（gamma，secure=true） |
| `start-openlibing-sbom.sh` | 根 | `start-openlibing-sbom.sh` | 删除 `-Dapollo.cache.file.enable=false` 参数 |

### 3.2 删除类

| 类 | 模块 | 路径 | 原职责 | 删除原因 |
|----|------|------|--------|----------|
| `ConfigContextInitializer` | cache | `cache/.../config/ConfigContextInitializer.java` | `ApplicationContextInitializer`，从 `TRUST_STORE` 环境变量加载 SSL trustStore 到 Spring Context | 迁移 Nacos 后 trustStore 由 JVM 参数加载（start 脚本保留 `-Djavax.net.ssl.trustStore`），Spring 层初始化器冗余 |

### 3.3 SbomManagerApplication 变更详情

```java
// 新增 import
import com.alibaba.nacos.client.config.utils.SnapShotSwitch;

// 新增静态块（类加载时执行，先于 Spring 初始化）
static {
  SnapShotSwitch.setIsSnapShot(false);
}

// 删除（原 ConfigContextInitializer 相关）
// import org.opensourceway.sbom.cache.config.ConfigContextInitializer;
// application.addInitializers(new ConfigContextInitializer());

// 保留
// @SpringBootApplication / @ImportResource / @ComponentScan / @EnableEncryptableProperties
// @EnableAsync / @EnableFeignClients / configure() / main()
```

### 3.4 不新增类

本次改动不新增任何业务类，仅在现有文件做增量修改 + 删除 1 个类。

---

## 4. 数据模型设计

### 4.1 数据库变更

**无数据库变更**。本次迁移仅涉及配置中心与服务发现组件替换，不涉及 sbom 业务表结构。

### 4.2 Nacos 配置中心数据设计

| Data ID | group | namespace | 内容 | 维护方 |
|---------|-------|-----------|------|--------|
| `application` | `OPENLIBING` | `openlibing-prod` / `openlibing-gamma` | 平台公共配置（多服务共享） | 平台运维 |
| `application-local` | `OPENLIBING` | `openlibing-beta` | dev 本地化公共配置 | 平台运维 |
| `sbom` | `OPENLIBING` | `openlibing-beta` / `openlibing-prod` / `openlibing-gamma` | sbom 专属配置（数据源、quartz、swagger 等） | sbom 运维 |

> 注：Nacos 上的 Data ID 内容需由运维在华为云 CSE Nacos 各 namespace 预先配置，不在本 PR 范围内。

### 4.3 服务注册数据

| 环境 | 注册服务名 | 注册协议 | namespace |
|------|-----------|----------|-----------|
| dev (beta) | openlibing-sbom | HTTP | openlibing-beta |
| prod | openlibing-sbom | HTTPS | openlibing-prod |
| gama (gamma) | openlibing-sbom | HTTPS | openlibing-gamma |

---

## 5. 性能设计

### 5.1 启动性能

| 指标 | 迁移前（Apollo+Eureka） | 迁移后（Nacos） |
|------|------------------------|-----------------|
| 配置拉取 | Apollo meta server 拉取 + 本地 cache 文件 | Nacos Config 一次拉取（无本地快照） |
| 服务注册 | Eureka client 心跳注册 | Nacos Discovery 一次注册 + 心跳 |
| 启动耗时影响 | 基线 | 持平或略快（Nacos 长连接 + 无本地 cache 文件 IO） |
| SnapShotSwitch | N/A | 禁用本地快照写盘，减少容器文件 IO |

### 5.2 运行时性能

| 指标 | 说明 |
|------|------|
| 配置监听 | Nacos Config 长轮询监听变更，配置热更新延迟 < 1s |
| 服务发现 | Nacos Discovery 订阅服务列表，变更推送 < 3s |
| 心跳 | Nacos client 5s 心跳保活，15s 标记不健康，30s 摘除 |

### 5.3 资源占用

| 资源 | 影响 |
|------|------|
| 内存 | nacos-client 3.0.3 常驻 ~10MB（与 apollo-client + eureka-client 合计相当） |
| 磁盘 | SnapShotSwitch=false 后无 `${user.home}/nacos/` 快照文件，容器无状态 |
| 网络 | 长连接 + 心跳，单实例 ~1KB/s |

---

## 6. API 接口设计

### 6.1 变更概述

**无 API 变更**。本次迁移仅涉及配置中心与服务发现基础设施替换，sbom 对外业务接口（`/sbom-api/*`）签名、入参、响应均不变。

### 6.2 服务发现影响

| 消费方 | 迁移前 | 迁移后 |
|--------|--------|--------|
| 网关路由 openlibing-sbom | 从 Eureka 获取实例列表 | 从 Nacos Discovery 获取实例列表 |
| Feign 跨服务调用 | 通过 Eureka 服务发现 | 通过 Nacos Discovery 服务发现（`@EnableFeignClients` 不变） |

### 6.3 向后兼容性

| 场景 | 行为 |
|------|------|
| 网关未升级（仍查 Eureka） | 找不到 openlibing-sbom 实例 → 路由失败 → 需网关同步迁移到 Nacos Discovery |
| 配置中心切换期间 | Nacos Data ID 未预配置 → `optional:` 前缀保证启动，使用本地 properties 兜底（部分配置缺失） |
| 业务接口调用方 | 无感知，接口签名不变 |

> 注：本迁移需与网关、其他依赖 sbom 服务的消费方协同上线（统一切换到 Nacos Discovery）。

---

## 7. 安全设计

### 7.1 鉴权

继承原有鉴权逻辑。Nacos Config 拉取需 Nacos 命名空间访问权限（华为云 CSE IAM 鉴权），由运维在 Nacos 控制台配置访问凭证。

### 7.2 敏感信息

| 敏感项 | 处理 |
|--------|------|
| `KEY_STORE_PASSWORD` | Jasypt 加密 + 环境变量注入（`@EnableEncryptableProperties` 保留） |
| `TRUST_STORE` | 环境变量 → JVM 参数 `-Djavax.net.ssl.trustStore`（start 脚本保留） |
| Nacos 凭证 | 不在 properties 硬编码，由华为云 CSE 内网鉴权 / RAM 角色 |
| DB 密码 | `${DB_PASSWORD}` 环境变量（start 脚本 `DB_PASSWORD_FILE` 读取，保留） |

### 7.3 通信安全

| 通信链路 | 加密 |
|----------|------|
| sbom ↔ Nacos Config | dev HTTP（内网测试）；prod/gama HTTPS（华为云 CSE TLS） |
| sbom ↔ Nacos Discovery | 同上 |
| 网关 ↔ sbom | dev HTTP；prod/gama HTTPS（`server.ssl.enabled=true` + `discovery.secure=true`） |
| sbom ↔ PostgreSQL | JDBC（`spring.datasource.url`，配置在 Nacos `sbom` Data ID） |

### 7.4 输入安全

| 风险点 | 缓解 |
|--------|------|
| Nacos Data ID 被篡改 | 华为云 CSE Nacos 控制台权限管控 + 配置变更审计 |
| 配置快照泄漏 | `SnapShotSwitch.setIsSnapShot(false)` 禁止本地快照，容器无敏感文件残留 |
| trustStore 泄漏 | trustStore 路径由环境变量注入，不进入镜像 |

### 7.5 审计日志

无新增日志点。Nacos 配置变更由 Nacos 控制台审计；sbom 启动日志保留 `Sbom service has started`。

---

## 8. 测试设计

### 8.1 测试策略

按 `ai_memory.md` 规则，本变更属配置类迁移，无业务行为变化，UT 不强制。验证以**编译验证 + 配置项静态检查 + 各环境启动验证**为主。

### 8.2 验证场景

| 场景 | 验证方式 | 预期 |
|------|----------|------|
| 编译通过 | `mvn clean compile -pl sbom-web -am` | BUILD SUCCESS（移除 eureka-client + 删除 ConfigContextInitializer 后无编译错误） |
| 配置项清理 - apollo | `grep -r "apollo" sbom-web/src/main/resources/` | 仅 `application.properties` 无 `apollo.app.id`，dev/prod/gama 无 `apollo.*` |
| 配置项清理 - eureka | `grep -r "eureka" sbom-web/src/main/resources/` | 4 个 properties 无 `eureka.*` |
| 配置项新增 - nacos config | `grep "spring.cloud.nacos.config" application-*.properties` | dev/prod/gama 各含 5 个 config key（server-addr/group/namespace/file-extension） |
| 配置项新增 - nacos discovery | `grep "spring.cloud.nacos.discovery" application-*.properties` | dev 4 个 + prod/gama 5 个（含 secure=true） |
| 启动脚本 | `grep "apollo" start-openlibing-sbom.sh` | 无匹配（`-Dapollo.cache.file.enable` 已删除） |
| SnapShotSwitch 静态块 | `grep "SnapShotSwitch" SbomManagerApplication.java` | import + static 块存在 |
| ConfigContextInitializer 删除 | `find cache -name ConfigContextInitializer.java` | 无文件 |
| 残留引用检查 | `grep -r "ConfigContextInitializer" sbom-web/ cache/` | 无引用（编译通过佐证） |
| sbom-web/pom.xml | `grep "eureka-client" sbom-web/pom.xml` | 无直接依赖 |
| dev 启动（beta Nacos） | `--spring.profiles.active=dev` 启动 | 注册到 `openlibing-beta` namespace，HTTP 注册，日志 `Sbom service has started` |
| prod 启动（华为云 Nacos） | `--spring.profiles.active=prod` 启动 | 注册到 `openlibing-prod`，HTTPS 注册（secure=true） |
| gama 启动（华为云 Nacos） | `--spring.profiles.active=gama` 启动 | 注册到 `openlibing-gamma`，HTTPS 注册 |
| 配置热更新 | Nacos 控制台修改 `sbom` Data ID | sbom 监听到变更并刷新（无需重启） |

### 8.3 回归测试

| 场景 | 预期 |
|------|------|
| sbom 业务接口（`/sbom-api/querySbomPackageList` 等） | 行为与迁移前一致 |
| Quartz 定时任务（prod/gama `spring.quartz.auto-startup=true`） | 正常调度 |
| Feign 跨服务调用 | 通过 Nacos Discovery 发现目标服务，调用成功 |
| 数据库读写 | 正常（数据源配置在 Nacos `sbom` Data ID） |

---

## 9. 与代码实现的一致性核对

本设计文档基于 `openlibing-sbom` `feat/nacos-migration` 分支（已合并到 `sbom-dev`）实际代码实现，关键核对点：

| 核对点 | 代码实现 | 文档对应章节 |
|--------|----------|--------------|
| openlibing-common 版本 | 1.0.20.0 | §1.4 / §2.1 |
| nacos 依赖引入方式 | 传递引入（无手动声明） | §1.4 |
| eureka-client 处理 | sbom-web/pom.xml 已移除 | §2.1 / §3.1 |
| SnapShotSwitch | `SbomManagerApplication` 静态块 | §2.2 / §2.5 / §3.3 |
| ConfigContextInitializer | 已删除，无残留引用 | §2.1 / §3.2 |
| dev nacos server-addr | `1.95.74.1:31252` | §2.3 |
| prod/gama nacos server-addr | `ee0b6e65-...myhuaweicloud.com:8848` | §2.3 |
| namespace | `openlibing-beta` / `openlibing-prod` / `openlibing-gamma` | §2.3 |
| discovery.secure | dev 不配置 / prod+gama `true` | §2.3 / §1.4 |
| spring.config.import | `optional:nacos:application[-local],optional:nacos:sbom` | §2.2 / §2.3 |
| 启动脚本 apollo 参数 | 已删除 `-Dapollo.cache.file.enable` | §2.4 |
| trustStore JVM 参数 | 保留 `-Djavax.net.ssl.trustStore=${TRUST_STORE}` | §1.4 / §2.5 |
| 配置格式 | `.properties`（未转 yaml） | §1.4 |
| 业务代码改动 | 无（仅配置 + 依赖 + 启动类） | §1.2 |

> 注：commit `02892cc6`（feat/nacos-migration）为本需求的代码实现，已合并到 sbom-dev（merge commit `e8cec63b`）。
