# apollo-to-nacos-migration — 实现任务

## 进度: 11/11 complete

- [x] Task 1: 升级 `pom.xml` 中 `openlibing-common` 版本（1.0.19.5 → 1.0.20.0 → 1.0.20.1 → 1.0.20.4）
- [x] Task 2: 显式声明 `jakarta.ws.rs-api:3.1.0`（补偿 Apollo 传递依赖断裂）
- [x] Task 3: 改造 `OpenlibingCicdApplication.java`：移除 Apollo 注解与初始化器（含 import），加 `SnapShotSwitch.setIsSnapShot(false)` 静态块
- [x] Task 4: 改造 `application-beta.yaml`：Apollo 块 → Nacos `spring.config.import` + `cloud.nacos`（namespace=`openlibing-beta`）
- [x] Task 5: 改造 `application-gama.yaml`：Apollo 块 → Nacos（namespace=`openlibing-gamma`）
- [x] Task 6: 改造 `application-prod.yaml`：Apollo 块 → Nacos（独立 CSE 实例，namespace=`openlibing-prod`）
- [x] Task 7: `application.yaml` 追加 `spring.cloud.nacos.discovery.secure: true`
- [x] Task 8: 修改 `start.sh`：删除 `-Dapollo.cache.file.enable=false` 行
- [x] Task 9: 替换 `AuthInterceptor.java`、`ExcelUtils.java` 的 guava import 为 shaded 路径
- [x] Task 10: 替换 `CrossRegionServiceImpl.java`、`SafeRequestUtils.java` 的 Apollo StringUtils 为 commons-lang3
- [x] Task 11: `PipelineControllerTest` 增加 `@TestPropertySource` 适配 `@WebMvcTest` 切片

## 验证方式

- `mvn clean compile -DskipTests` 编译通过（guava/StringUtils/jakarta.ws.rs 替换无误）
- `mvn test` 单元测试通过（含 PipelineControllerTest 切片适配）
- head 分支全量 grep 核验：`com.ctrip.framework.apollo` 代码级引用零残留（仅 javadoc 注释提及）、原生 guava 零残留、`ConfigContextInitializer` 零残留
- 与 openlibing-codecheck 迁移完成态（cf6c48bd + PR 322）逐项对齐核验，迁移项全部覆盖

## 生成前约束清单

- [x] 只修改 openlibing-cicd 业务仓 + openlibing-docs/spec 目录
- [x] 遵循目标仓既有 yaml/java 注释与命名风格
- [x] 不做无关重构、无关格式化
- [x] 无硬编码凭证、敏感信息（CSE 地址为平台公共 endpoint，非凭证）
- [x] 行为变化（配置中心切换）通过编译 + 测试验证，部署验证由用户在 beta/gama/prod 环境完成
