# Proposal: Apollo/Eureka 迁移至 Nacos

## 需求背景

openlibing-gateway 原使用 Apollo 作为配置中心、Eureka 作为服务发现组件。为统一基础设施、降低多组件运维成本，本期将配置中心与服务发现统一迁移到华为云 CSE Nacos 实例，由 Nacos 同时承担配置加载和服务发现职责。

迁移驱动因素：

1. **基础设施统一**：Apollo + Eureka 两套组件需独立运维，迁移到 Nacos 后由 CSE 托管，减少自维护负担。
2. **环境隔离一致性**：beta / gamma / prod 三套环境均使用 Nacos，通过 `namespace` 字段隔离（`openlibing-beta` / `openlibing-gamma` / `openlibing-prod`），统一 group=`OPENLIBING`。
3. **common-sdk 升级配套**：`openlibing-common-sdk` 已在新版本中提供 Nacos 集成支持，gateway 需配套升级依赖版本。

## 功能描述

### 做什么

- 移除 Apollo 客户端入口（`@EnableApolloConfig` 注解、`ConfigContextInitializer` 初始化器）
- 移除启动脚本中的 Apollo JVM 参数（`-Dapollo.cache.file.enable=false`）
- 新增 Nacos 配置中心与服务发现配置（`spring.cloud.nacos.config` + `spring.cloud.nacos.discovery`）
- 关闭 Nacos 本地快照（`SnapShotSwitch.setIsSnapShot(false)`），避免本地缓存导致配置漂移
- 升级 `openlibing-common-sdk` 依赖版本（1.0.19.5 → 1.0.20.4）
- 调整 Dockerfile 清华镜像源 JRE 下载正则，适配 Adoptium 新版本文件命名

### 不做什么

- 不修改业务代码（Controller / Service / Mapper 层保持不变）
- 不修改数据库 schema
- 不修改第三方鉴权、Redis、JWT 等业务配置
- 不在本期引入额外的服务网格或网关路由变更

## 验收标准

- [ ] beta 环境服务启动后能从 Nacos（namespace=`openlibing-beta`）加载 `application` 和 `gateway` 两个配置
- [ ] gamma 环境服务启动后能从 Nacos（namespace=`openlibing-gamma`）加载配置
- [ ] prod 环境服务启动后能从 Nacos（namespace=`openlibing-prod`）加载配置
- [ ] 服务发现正常注册到 Nacos（`spring.cloud.nacos.discovery` 生效）
- [ ] Apollo 相关 bean / 注解 / 配置项在启动日志中不再出现
- [ ] Nacos 连接失败时服务能优雅降级（`optional:nacos:` 前缀保证本地配置可继续启动）
- [ ] 升级后的 `openlibing-common-sdk 1.0.20.4` 与 gateway 现有代码兼容
- [ ] Docker 构建可成功下载 JRE 21 包，新正则匹配 `OpenJDK21*.tar.gz` 命名格式

## 影响范围

### 业务仓文件

| 文件                                                           | 操作 | 说明                                                   |
| -------------------------------------------------------------- | ---- | ------------------------------------------------------ |
| `pom.xml`                                                      | 修改 | common-sdk 版本升级（1.0.19.5 → 1.0.20.4）             |
| `src/main/java/com/openlibing/gateway/GatewayApplication.java` | 修改 | 移除 Apollo 注解和初始化器；新增 SnapShotSwitch 静态块 |
| `src/main/resources/application-beta.yaml`                     | 修改 | Apollo meta → Nacos config + discovery                 |
| `src/main/resources/application-gama.yaml`                     | 修改 | Apollo meta → Nacos config + discovery                 |
| `src/main/resources/application-prod.yaml`                     | 修改 | Apollo meta → Nacos config + discovery                 |
| `start.sh`                                                     | 修改 | 移除 `-Dapollo.cache.file.enable=false` JVM 参数       |
| `Dockerfile`                                                   | 修改 | 清华镜像源 JRE 下载正则调整                            |

### 跨仓影响

- **openlibing-common-sdk**：gateway 升级到 1.0.20.4，需 common 仓已发布对应版本到 Maven 仓库
- **Nacos 配置导入**：beta/gamma/prod 三套 Nacos 命名空间需提前创建 `application` 和 `gateway` 两个 dataId，配置内容需与原 Apollo 配置一致（运维侧操作）
- **部署链路**：start.sh 与 Dockerfile 调整后需重新构建镜像并发布到镜像仓库
