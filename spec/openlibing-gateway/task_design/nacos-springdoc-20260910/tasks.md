# Tasks: Nacos 迁移合入 release_20260910 与 springdoc WebFlux 修复

## 进度: 4/6 complete

### 阶段 1：代码变更 ✅

- [x] Task 1: 重新应用 Nacos 迁移到 release_20260910 分支
  - commit: b903db4（基线 a6d3528）
  - 内容: 移除 `@EnableApolloConfig`、新增 `SnapShotSwitch` 静态块、beta/gama/prod 三套 yaml 迁移、sdk 升级 1.0.20.6、`discovery.secure: true`
  - 注意: 与原迁移（!181）不同，保留 `ConfigContextInitializer`（由 common-sdk 1.0.20.6 提供）

- [x] Task 2: springdoc webmvc-ui → webflux-ui 修复
  - commit: 26ae45d
  - 内容: pom.xml 排除 `springdoc-openapi-starter-webmvc-ui`，显式引入 `springdoc-openapi-starter-webflux-ui 2.8.10`
  - 关联: codechentao/openlibing-gateway#4

- [x] Task 3: 本地编译验证
  - `mvn -T1 clean compile -o` → BUILD SUCCESS（101 source files）

- [x] Task 4: 推送分支并创建 PR
  - 分支: `codechentao:chentao_release_20260910` → `openlibing:release_20260910`
  - PR: openlibing/openlibing-gateway#189（标签 `ai-assisted`，2 commits，+72/-18，6 文件）

### 阶段 2：发布验证 ⏳

- [ ] Task 5: PR 合并与 CI 通过
  - 确认流水线通过（仓库开启 only_allow_merge_if_pipeline_succeeds）
  - 评审人审批后合入 release_20260910

- [ ] Task 6: 环境部署验证
  - beta/gama/prod 启动后确认: Nacos 配置加载、服务注册、swagger UI 可访问、Apollo 无残留
  - 完成标准: 发布后稳定运行无异常

## 关联 PR

- openlibing/openlibing-gateway#189: `chentao_release_20260910` → `release_20260910`（本变更）
- 原始迁移: !181 / !182 → `release_20260827_iter2`（见 [apollo_eureka_to_nacos](../apollo_eureka_to_nacos/)）

## 备注

- 本变更是原迁移在 release_20260910 发布线的重放，迁移方案细节见 [design.md](design.md) 与原 spec
- Task 6 为发布后运维侧验证，不在代码仓 commit 中体现
