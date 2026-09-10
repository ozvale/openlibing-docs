# Proposal: Nacos 迁移合入 release_20260910 与 springdoc WebFlux 修复

## 需求背景

openlibing-gateway 的 Apollo/Eureka → Nacos 迁移最初在 `release_20260827_iter2` 分支线完成（详见 [apollo_eureka_to_nacos](../apollo_eureka_to_nacos/) spec，PR !181/!182），但该变更未进入 `release_20260910` 基线（master 仍为 Apollo 配置）。

本期（release_20260910 迭代）需要：

1. **重新应用 Nacos 迁移**：将配置中心（Apollo）与服务发现（Eureka）迁移变更在 `chentao_release_20260910` 分支上重新提交，使 release_20260910 发布线具备 Nacos 能力。
2. **修复 springdoc 依赖**：openlibing-gateway 是响应式应用，但通过 openlibing-common 继承了 servlet 栈的 `springdoc-openapi-starter-webmvc-ui`，导致 swagger 端点不可用（访问 `/manage/v3/swagger-ui/index.html` 返回 ErrorCode 5000000）。
3. **升级 common-sdk**：`openlibing-common-sdk` 1.0.20.5 → 1.0.20.6。

## 功能描述

### 做什么

- 移除 `@EnableApolloConfig` 注解，新增 `SnapShotSwitch.setIsSnapShot(false)` 静态块关闭 Nacos 本地快照
- beta / gama / prod 三套环境配置从 Apollo meta 迁移到 `spring.cloud.nacos.config` + `spring.cloud.nacos.discovery`
- `application.yaml` 新增 `spring.cloud.nacos.discovery.secure: true`
- 从 openlibing-common 依赖中排除 `springdoc-openapi-starter-webmvc-ui`，显式引入 `springdoc-openapi-starter-webflux-ui 2.8.10`
- 升级 `openlibing-common-sdk` 至 1.0.20.6

### 不做什么

- 不修改业务代码（Controller / Service / Mapper 层）
- 不修改数据库 schema
- 不修改路由、鉴权、Redis、JWT 等业务配置
- 不调整 start.sh / Dockerfile（原迁移中的脚本调整不在本次范围）

## 验收标准

- [ ] 本地编译通过（`mvn clean compile`）
- [ ] beta/gama/prod 环境启动后从对应 Nacos namespace（`openlibing-beta` / `openlibing-gamma` / `openlibing-prod`）加载 `application` 和 `gateway` 两个 dataId 配置
- [ ] 服务实例注册到 Nacos discovery
- [ ] 启动日志中不再出现 Apollo 客户端初始化记录
- [ ] swagger UI（`/manage/v3/swagger-ui/index.html`）可正常访问
- [ ] openlibing-common-sdk 1.0.20.6 与 gateway 现有代码兼容
- [ ] 依赖树中不再出现 `springdoc-openapi-starter-webmvc-ui`

## 影响范围

### 业务仓文件

| 文件                                                           | 操作 | 说明                                                      |
| -------------------------------------------------------------- | ---- | --------------------------------------------------------- |
| `pom.xml`                                                      | 修改 | sdk 1.0.20.5 → 1.0.20.6；排除 webmvc-ui；引入 webflux-ui  |
| `src/main/java/com/openlibing/gateway/GatewayApplication.java` | 修改 | 移除 `@EnableApolloConfig`；新增 SnapShotSwitch 静态块    |
| `src/main/resources/application-beta.yaml`                     | 修改 | Apollo meta → Nacos config + discovery（namespace=beta）  |
| `src/main/resources/application-gama.yaml`                     | 修改 | Apollo meta → Nacos config + discovery（namespace=gamma） |
| `src/main/resources/application-prod.yaml`                     | 修改 | Apollo meta → Nacos config + discovery（namespace=prod）  |
| `src/main/resources/application.yaml`                          | 修改 | 新增 `nacos.discovery.secure: true`                       |

### 跨仓影响

- **openlibing-common-sdk**：需 1.0.20.6 已发布到 Maven 仓库
- **Nacos 运维**：三个 namespace 下 `application` / `gateway` 两个 dataId 需已配置（沿用原迁移已完成的部分）
- **发布链路**：合入 release_20260910 后随迭代发布

## 关联

- 业务 PR: openlibing/openlibing-gateway#189（`codechentao:chentao_release_20260910` → `release_20260910`）
- 原始迁移 spec: [apollo_eureka_to_nacos](../apollo_eureka_to_nacos/)
- springdoc 修复关联 issue: codechentao/openlibing-gateway#4
