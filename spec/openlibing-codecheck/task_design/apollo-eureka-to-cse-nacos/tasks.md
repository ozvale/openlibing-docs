# Tasks: 自建 Apollo、Eureka 服务替换为华为云 CSE 服务（nacos）

## 进度: 6/6 complete

- [x] Task 1: 升级 `openlibing-common-sdk` 到 1.0.20.4，调整 mongodb-starter 依赖排除
- [x] Task 2: 启动类移除 `@EnableApolloConfig` / `ConfigContextInitializer`，启用 Nacos `SnapShotSwitch`
- [x] Task 3: beta / gama / prod 环境 yaml 迁移到 Nacos（`spring.config.import` + `spring.cloud.nacos`）
- [x] Task 4: `application.yaml` 增加 `spring.cloud.nacos.discovery.secure=true`
- [x] Task 5: 修复依赖差异（guava → nacos-shaded、`javax.annotation` → `org.jetbrains.annotations`）
- [x] Task 6: 清理 Apollo 死配置（start.sh / GlobalExceptionHandler / CodeCheckCollectionName）

## 验证

- [x] 构建编译通过
- [x] beta 环境启动验证（随 CI）