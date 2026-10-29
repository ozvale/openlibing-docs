# apollo-to-nacos-migration — 技术设计

## 方案概述

按 `apollo-eureka-to-cse-nacos-migration` skill 的标准迁移模式，将 openlibing-cicd 仓从 Apollo（配置）+ Eureka（发现）迁移到华为云 CSE Nacos（配置 + 注册一体化），改动覆盖依赖、启动类、三环境 profile、guava shaded 包路径与 Apollo 工具类替换。

## 架构决策

| 决策                                  | 说明                                                                                                                                                                                    |
| ------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| common 版本 1.0.19.5 → 1.0.20.4       | 1.0.20.x 内置 Nacos 客户端并移除 Apollo/Eureka 传递依赖。计划阶段拟用 1.0.19.8，实施中随平台统一升级最终定在 1.0.20.4（经 1.0.20.0 → 1.0.20.1 → 1.0.20.4 三次递进）                     |
| 配置集加载顺序反转                    | Nacos `spring.config.import` 为后加载覆盖前加载，与 Apollo 相反。cicd 的加载序定为 `application → framework → cicd → xxl-job`，服务自身 data-id（cicd）位于框架配置之后以获得最高优先级 |
| `SnapShotSwitch.setIsSnapShot(false)` | 关闭 Nacos 客户端本地快照落盘，对齐平台容器化部署规范，避免配置快照残留在 PVC                                                                                                           |
| `jakarta.ws.rs-api:3.1.0` 显式声明    | 6 个业务文件直接 import `jakarta.ws.rs.*`（如 `MediaType`），此前靠 Apollo 传递依赖提供；Apollo 移除后传递链断裂，必须显式补偿                                                          |
| guava 走 Nacos shaded 包              | `com.google.common.*` → `com.alibaba.nacos.shaded.com.google.common.*`，避免与新引入的 guava 版本冲突（AuthInterceptor、ExcelUtils）                                                    |
| Apollo StringUtils → commons-lang3    | Apollo 移除后其 `com.ctrip.framework.apollo.common.utils.StringUtils` 不再可用，等价替换为 `org.apache.commons.lang3.StringUtils`（CrossRegionServiceImpl、SafeRequestUtils）           |
| `discovery.secure: true`              | CSE 侧 HTTPS 注册，保证 Feign/网关调用走 HTTPS                                                                                                                                          |
| prod 独立 CSE 实例                    | prod 使用与 beta/gamma 不同的 CSE engine 地址 + `openlibing-prod` namespace，隔离生产配置                                                                                               |
| 测试切片适配                          | `@WebMvcTest` 切片不含 Nacos 自动配置，用 `@TestPropertySource` 显式关闭 `spring.config.import` 检查，避免 UT 启动失败                                                                  |

## 涉及文件

| 文件                           | 操作 | 说明                                                                               |
| ------------------------------ | ---- | ---------------------------------------------------------------------------------- |
| pom.xml                        | 修改 | common 1.0.19.5 → 1.0.20.4；新增 jakarta.ws.rs-api 3.1.0                           |
| OpenlibingCicdApplication.java | 修改 | 移除 `@EnableApolloConfig`、`ConfigContextInitializer`；新增 SnapShotSwitch 静态块 |
| application-beta.yaml          | 修改 | Apollo 块 → Nacos（namespace=openlibing-beta）                                     |
| application-gama.yaml          | 修改 | Apollo 块 → Nacos（namespace=openlibing-gamma）                                    |
| application-prod.yaml          | 修改 | Apollo 块 → Nacos（独立 CSE 实例，namespace=openlibing-prod）                      |
| application.yaml               | 修改 | 追加 `spring.cloud.nacos.discovery.secure: true`                                   |
| AuthInterceptor.java           | 修改 | guava import → shaded 路径                                                         |
| ExcelUtils.java                | 修改 | guava import → shaded 路径                                                         |
| CrossRegionServiceImpl.java    | 修改 | Apollo StringUtils → commons-lang3                                                 |
| SafeRequestUtils.java          | 修改 | Apollo StringUtils → commons-lang3                                                 |
| PipelineControllerTest.java    | 修改 | `@TestPropertySource` 关闭 config import 检查                                      |
| start.sh                       | 修改 | 删除 `-Dapollo.cache.file.enable=false`                                            |

## 风险 & 缓解

| 风险                                                | 缓解                                                |
| --------------------------------------------------- | --------------------------------------------------- |
| 配置集顺序错误导致配置覆盖关系反转                  | 严格按 skill §4.4 反转顺序，人工核对 data-id 加载序 |
| Apollo 传递依赖断裂引发编译失败（jakarta.ws.rs 等） | 编译验证 + 显式声明 `jakarta.ws.rs-api`             |
| prod 迁移窗口风险                                   | prod 迁移为独立 commit（484c221f），可单独回滚      |
| UT 因 Nacos 自动配置启动失败                        | `@TestPropertySource` 切片级禁用                    |
| Nacos 客户端快照残留                                | 启动类静态块关闭快照                                |

## 跨仓影响

- 依赖 `openlibing-common` 1.0.20.4（平台公共件已发布，无需本仓改动）
- 与 openlibing-codecheck 迁移模式完全对齐（codecheck 完成态 = cf6c48bd + PR 322）
- 无对外接口/契约变化，无 schema 变更
