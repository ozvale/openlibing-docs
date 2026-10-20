# Design: Nacos 迁移合入 release_20260910 与 springdoc WebFlux 修复

## 方案概述

本变更是 [apollo_eureka_to_nacos](../apollo_eureka_to_nacos/) 迁移在 `release_20260910` 发布线上的重新应用，并叠加 springdoc WebFlux 修复与 common-sdk 升级。整体分两部分：

1. **Nacos 迁移重放**：将 Apollo/Eureka → Nacos 的启动类改造与环境配置迁移，以新 commit（b903db4）形式提交到 `chentao_release_20260910` 分支。
2. **springdoc 修复**：通过 Maven exclusion + 显式依赖，把 openapi UI 从 servlet 栈切换到响应式栈（26ae45d）。

## 架构决策

### 决策 1：在迭代分支重新提交而非等待分支合并

**选择**：直接在 `chentao_release_20260910` 上以新 commit 重新应用迁移（基线 a6d3528）。

**原因**：

- 原迁移落在 `release_20260827_iter2` 分支线，`release_20260910` 基线（a6d3528 = master !188）的 gateway 配置仍为 Apollo
- release_20260910 迭代有独立发布窗口，不能等待旧分支线合并

### 决策 2：保留 `ConfigContextInitializer`

**选择**：与原迁移不同，本次保留 `GatewayApplication` 中的 `.initializers(new ConfigContextInitializer())` 调用。

**原因**：

- common-sdk 1.0.20.6 中的 `ConfigContextInitializer` 已兼容 Nacos 场景（由 sdk 内部适配）
- 只移除 Apollo 专属入口（`@EnableApolloConfig`），最小化改动范围

### 决策 3：关闭 Nacos 本地快照

**选择**：静态初始化块调用 `SnapShotSwitch.setIsSnapShot(false)`，与原迁移一致。

**原因**：

- 避免本地磁盘快照导致断连后配置漂移
- Nacos 不可达时行为可预测（`optional:nacos:` 前缀走本地配置兜底）

### 决策 4：springdoc 排除 + 显式引入 webflux-ui

**选择**：在 `openlibing-common` 依赖上排除 `springdoc-openapi-starter-webmvc-ui`，并显式引入 `springdoc-openapi-starter-webflux-ui 2.8.10`。

**原因**：

- gateway 是响应式应用，webmvc-ui（servlet 栈）不会自动装配 `/v3/api-docs` 与 swagger-ui 端点，访问返回 ErrorCode 5000000（NoResourceFoundException）
- 版本 2.8.10 与 common 中的 webmvc-ui 保持一致，避免版本漂移
- 仅修改 gateway 的 pom.xml，其他依赖 openlibing-common 的 servlet 栈服务不受影响

### 决策 5：Nacos 配置结构（与原迁移的差异）

本次配置在原迁移基础上调整：

- `spring.cloud.nacos` 节点下增加顶层 `server-addr`（config/discovery 各自节点同时保留显式 server-addr）
- `application.yaml` 新增 `spring.cloud.nacos.discovery.secure: true`（服务注册标记为安全协议）

```yaml
spring:
  config:
    import:
      - optional:nacos:application
      - optional:nacos:gateway
  cloud:
    nacos:
      server-addr: <CSE 实例地址>:8848
      config:
        server-addr: <同上>
        group: OPENLIBING
        namespace: openlibing-<env>
        file-extension: properties
      discovery:
        server-addr: <同上>
        group: OPENLIBING
        namespace: openlibing-<env>
```

环境隔离：beta/gamma 共用 CSE 实例 `ee0b6e65-...`（不同 namespace），prod 使用独立实例 `12a78981-...`。

## 涉及文件

| 文件                      | 关键改动                                                        |
| ------------------------- | --------------------------------------------------------------- |
| `pom.xml`                 | sdk 1.0.20.5 → 1.0.20.6；排除 webmvc-ui；新增 webflux-ui 2.8.10 |
| `GatewayApplication.java` | `@EnableApolloConfig` 移除；`SnapShotSwitch` 静态块新增         |
| `application-beta.yaml`   | Apollo meta → Nacos（namespace=`openlibing-beta`）              |
| `application-gama.yaml`   | Apollo meta → Nacos（namespace=`openlibing-gamma`）             |
| `application-prod.yaml`   | Apollo meta → Nacos（namespace=`openlibing-prod`）              |
| `application.yaml`        | 新增 `nacos.discovery.secure: true`                             |

## 风险 & 缓解

| 风险                                    | 缓解措施                                                   |
| --------------------------------------- | ---------------------------------------------------------- |
| 迁移配置与原 release 线存在漂移         | 对照 `apollo_eureka_to_nacos` spec 与本次 diff 逐项核对    |
| Nacos 不可达导致启动失败                | `optional:nacos:` 前缀保证本地配置兜底                     |
| webflux-ui 与 common 内 webmvc 配置冲突 | exclusion 确保 servlet 栈 starter 不进入 gateway classpath |
| 其他服务误用 webflux-ui                 | 仅 gateway pom 变更，common 未动                           |

## 验证记录

- `mvn -T1 clean compile -o` → BUILD SUCCESS（101 source files），见 commit 26ae45d
