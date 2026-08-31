# Design: Apollo/Eureka 迁移至 Nacos

## 方案概述

将 openlibing-gateway 的配置中心与服务发现统一迁移到华为云 CSE Nacos 实例。Nacos 同时承担：

- **配置中心**：替代 Apollo，加载 `application` 和 `gateway` 两个 dataId 的配置
- **服务发现**：替代 Eureka，gateway 作为服务实例注册到 Nacos discovery

迁移通过 Spring Cloud Nacos starter 实现，配置由 `spring.cloud.nacos.config` 和 `spring.cloud.nacos.discovery` 节点驱动，环境隔离通过 `namespace` 字段区分（beta/gamma/prod）。

## 架构决策

### 决策 1：使用华为云 CSE Nacos 托管实例

**选择**：使用 HuaweiCloud CSE（Cloud Service Engine）提供的 Nacos 实例，而非自建 Nacos 集群。

**原因**：

- 公司内部已有 CSE 实例，运维由云平台承担
- 高可用由 CSE 保证，无需自建集群
- 各环境已分配独立 namespace（`openlibing-beta` / `openlibing-gamma` / `openlibing-prod`）

**实施**：

- beta / gamma 共用同一 CSE 实例（不同 namespace），server-addr 为 `ee0b6e65-...nacos.cn-southwest-2.cse.myhuaweicloud.com:8848`
- prod 使用独立 CSE 实例，server-addr 为 `12a78981-...nacos.cn-southwest-2.cse.myhuaweicloud.com:8848`

### 决策 2：关闭 Nacos 本地快照

**选择**：通过静态初始化块在 Spring 启动前调用 `SnapShotSwitch.setIsSnapShot(false)`。

**原因**：

- Nacos 客户端默认会在本地磁盘缓存配置快照，网络断连后下次启动可能加载旧快照
- gateway 是核心鉴权服务，配置漂移会导致登录回调、Redis key 等行为异常
- 关闭快照后，Nacos 不可达时直接走本地 `application.yaml`，行为可预测

**实施**：

```java
public class GatewayApplication {
  static {
    SnapShotSwitch.setIsSnapShot(false);
  }
  // ...
}
```

### 决策 3：使用 `optional:nacos:` 前缀的配置导入

**选择**：通过 `spring.config.import` 导入 `optional:nacos:application` 和 `optional:nacos:gateway` 两个 dataId。

**原因**：

- `optional:` 前缀确保 Nacos 不可达时服务仍可启动（走本地配置兜底）
- 显式导入 `application` 和 `gateway` 两个 dataId，与原 Apollo 的 `namespaces: application,gateway` 保持一致

**实施**：

```yaml
spring:
  config:
    import:
      - optional:nacos:application
      - optional:nacos:gateway
```

### 决策 4：保留 Jasypt 加密

**选择**：保留 `@EnableEncryptableProperties` 注解，未迁移到 Nacos 自带的配置加密能力。

**原因**：

- Jasypt 加密已在 `GithubAuthConfig` 等多个配置类中使用，迁移成本高
- Nacos 配置中包含 Jasypt 加密后的密文，gateway 启动时由 Jasypt 解密，与 Nacos 无关
- 减少迁移范围，避免引入新的密钥管理复杂度

### 决策 5：分批迁移三套环境

**选择**：beta/gamma 在 PR !181 中迁移（chentao），prod 在后续 PR !182 中迁移（LinYP300）。

**原因**：

- beta/gamma 是测试环境，可以先验证迁移脚本和 Nacos 连接性
- prod 涉及线上流量，需要独立 review 和发布窗口
- 两个 PR 落在同一发布分支 `release_20260827_iter2`，最终一起发布

## 涉及文件

### 业务仓文件变更

| 文件                                                           | 操作 | 关键改动                                                                                                       |
| -------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------- |
| `pom.xml`                                                      | 修改 | `openlibing-common-sdk` 1.0.19.5 → 1.0.20.4                                                                    |
| `src/main/java/com/openlibing/gateway/GatewayApplication.java` | 修改 | 移除 `@EnableApolloConfig`、`ConfigContextInitializer`；新增 `SnapShotSwitch.setIsSnapShot(false)` 静态块      |
| `src/main/resources/application-beta.yaml`                     | 修改 | Apollo meta → Nacos config+discovery，namespace=`openlibing-beta`                                              |
| `src/main/resources/application-gama.yaml`                     | 修改 | Apollo meta → Nacos config+discovery，namespace=`openlibing-gamma`                                             |
| `src/main/resources/application-prod.yaml`                     | 修改 | Apollo meta → Nacos config+discovery，namespace=`openlibing-prod`                                              |
| `start.sh`                                                     | 修改 | 移除 `-Dapollo.cache.file.enable=false` JVM 参数                                                               |
| `Dockerfile`                                                   | 修改 | 清华镜像源 JRE 正则：`OpenJDK21U-jre_x64_linux_hotspot_\d+\.\d+\.\d+_\d+\.tar\.gz` → `OpenJDK21[^"]*\.tar\.gz` |

### 配置参数对比

| 维度       | Apollo（迁移前）                                                                  | Nacos（迁移后）                                                              |
| ---------- | --------------------------------------------------------------------------------- | ---------------------------------------------------------------------------- |
| 配置入口   | `apollo.meta` + `apollo.bootstrap.namespaces`                                     | `spring.cloud.nacos.config.server-addr` + `spring.config.import`             |
| 命名空间   | `application,gateway`                                                             | `optional:nacos:application` + `optional:nacos:gateway`                      |
| 环境隔离   | meta URL 区分（`apollo-config.openlibing-beta` / `openlibing-gamma` / `default`） | namespace 区分（`openlibing-beta` / `openlibing-gamma` / `openlibing-prod`） |
| 服务发现   | Eureka（独立配置）                                                                | `spring.cloud.nacos.discovery`                                               |
| 本地缓存   | `apollo.cache.file.enable=false` 关闭                                             | `SnapShotSwitch.setIsSnapShot(false)` 关闭                                   |
| 配置 group | N/A                                                                               | `OPENLIBING`（CSE 实例统一 group）                                           |

## 启动流程对比

### 迁移前（Apollo + Eureka）

```
1. main() → SpringApplicationBuilder
2. .initializers(new ConfigContextInitializer())   ← Apollo 上下文初始化
3. @EnableApolloConfig                              ← Apollo 注解扫描
4. 加载 application-beta.yaml 的 apollo.meta 配置
5. Apollo 客户端连接 apollo-config.openlibing-beta.svc.cluster.local:8081
6. 拉取 application 和 gateway 两个 namespace 的配置
7. Eureka 客户端注册服务
```

### 迁移后（Nacos）

```
1. main() → SpringApplicationBuilder（无 ConfigContextInitializer）
2. 静态块执行 SnapShotSwitch.setIsSnapShot(false)   ← 关闭本地快照
3. spring.config.import 加载 optional:nacos:application 和 optional:nacos:gateway
4. spring.cloud.nacos.config 连接 CSE Nacos 拉取配置
5. spring.cloud.nacos.discovery 注册服务实例
```

## 风险 & 缓解

### 风险 1：Nacos 单点故障导致配置加载失败

**影响**：Nacos 不可达时，服务可能因配置缺失无法启动。

**缓解**：

- `optional:nacos:` 前缀保证 Nacos 不可达时本地配置可继续启动
- CSE 实例由华为云保障高可用，SLA 99.95%+
- 关键配置（如 server.port、数据库连接）已在 `application.yaml` 中保留本地兜底

### 风险 2：配置项迁移不完整

**影响**：原 Apollo 中某些 dataId/key 未迁移到 Nacos，启动时取不到默认值。

**缓解**：

- 迁移前需对照 Apollo `application` 和 `gateway` 两个 namespace 的所有 key 列表
- 运维侧在 Nacos 创建 `application` 和 `gateway` 两个 dataId（properties 格式）
- 启动后通过 `/actuator/env` 端点校验配置项加载情况

### 风险 3：服务发现兼容性

**影响**：Eureka 与 Nacos Discovery 的心跳、健康检查机制不同，可能影响上游服务调用。

**缓解**：

- gateway 主要作为被调用方（下游前端调用 gateway），服务发现注册即可
- 不依赖 Eureka 的客户端负载均衡（用 OkHttp 直连）
- 启动后通过 Nacos 控制台查看服务实例注册情况

### 风险 4：Dockerfile 镜像源正则过宽

**影响**：`OpenJDK21[^"]*\.tar\.gz` 可能匹配到非 JRE 包（如 JDK 包）。

**缓解**：

- 清华镜像源路径 `/Adoptium/21/jre/x64/linux/` 已限定为 JRE 目录
- `sort -V | tail -1` 选取最新版本，命名排序保证 JRE 包优先
- 构建后通过 `java -version` 校验 JRE 版本

## 跨仓影响

- **openlibing-common-sdk**：gateway 升级到 1.0.20.4，需确认 common 仓已发布该版本到 Maven 仓库
- **Nacos 运维**：CSE 实例上需提前创建 `openlibing-beta` / `openlibing-gamma` / `openlibing-prod` 三个 namespace，以及 `application` 和 `gateway` 两个 dataId（由运维侧操作，不属于代码仓变更）
- **CI/CD**：Dockerfile 变更后需重新构建基础镜像并推送到镜像仓库
