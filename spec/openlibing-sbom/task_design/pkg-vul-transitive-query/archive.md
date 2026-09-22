# 依赖包漏洞传递依赖查询 — 归档

## 关联

- 业务仓: `openlibing/openlibing-sbom`
- 业务分支: `feat-query-pkg-vul-transitive-deps`
- 业务 Issue: openlibing/openlibing-sbom#54 (https://gitcode.com/openlibing/openlibing-sbom/issues/54，已 closed)
- 业务 PR: 待创建（用户自测确认后进入 Phase 4）
- docs PR: openlibing/openlibing-docs#701 (https://gitcode.com/openlibing/openlibing-docs/merge_requests/701)

## 交付历程

业务分支 `feat-query-pkg-vul-transitive-deps` 上 2 轮"依赖包漏洞查询"主题的 AI 编码交付（不含分支上其他无关 commit，如 dependency-type / spdx / statistics / release 合并等）：

- commit `900a70b6` (2026-07-28) **feat(sbom): support transitive deps query for package vulnerability** — 核心交付，22 文件 +1822/-204：
  - 新增 `VulQueryScope` 枚举（SELF / DEPENDENCIES / ALL）+ `parse()` 容错
  - 新增 `PackageDependencyCache` entity（PostgreSQL `uuid[]` 数组列）
  - 新增 `PackageIdAndSpdxId` projection DTO，避免 N+1 与大 TEXT 字段加载
  - 新增 `DependencyGraphBuilder`：BFS 传递依赖闭包计算（仅 `DEPENDS_ON`，排除 `RUNTIME_DEPENDENCY_OF`）
  - 新增 `DependencyCacheService`：3 个触发入口（同步 hook / 异步 step / REST API）+ 进程内 `ConcurrentHashMap` 去重锁 + 缓存失效入口
  - 新增 `PrecomputeDependencyCacheStep`（spring-batch），注册到 `sbom-read-job.xml`
  - 优化 `findByPackageIdsInAndSeverityAndVulId` 改用 `= ANY(uuid[])` 替代 `IN (...)`
  - `SpdxReader` hook `precomputeForSbom` + 新增 `invalidateBySbom`
  - `VulnerabilityVo` 新增 `name` / `version` 字段
  - `SbomService` / `SbomController` 接口签名扩展 `scope` 参数
  - `SbomServiceImpl` 实现 `scope` 分发逻辑
  - 单元测试 `DependencyCacheServiceTest` + `DependencyGraphBuilderTest` 100% line coverage
  - 修复 `SpdxReaderTest` / `SpdxWriteTest` 通过 mock `DependencyCacheService`
  - Co-authored-by: Trae ✓ Generated-by: glm-5.2 ✓

- commit `3c40ed82` (2026-07-29) **refactor(sbom): use productName as dependency cache refresh param** — REST API 入参重构，3 文件 +36/-22：
  - `POST /dependencyCache/refresh` 入参从 `sbomId` (UUID) 改为 `productName` (String)
  - `SbomServiceImpl.refreshDependencyCache(productName)` 内部先按 `productName` 查 `sbomId`，再触发异步预计算
  - 查不到 sbom 时抛 `SbomRuntimeException`，Controller 兜底为 HTTP 500
  - 返回体新增 `productName` 字段，便于调用方核对
  - Co-authored-by: Trae ✓ Generated-by: glm-5.2 ✓

## 用户自测反馈

本轮交付按计划完成，未触发重大返工。`3c40ed82` 是 `900a70b6` 交付后的小幅 API 易用性重构（`sbomId` → `productName` 入参），属于 Phase 3 用户反馈后的迭代调整，独立提交 commit（未 amend）。

## 最终验证

- **编译**：`mvn -o -DskipTests compile` 通过
- **单元测试**：
  - `DependencyCacheServiceTest` 100% line coverage
  - `DependencyGraphBuilderTest` 100% line coverage
  - `SbomControllerTest` / `SbomServiceImplTest` 适配 `scope` 参数与 `productName` 入参后通过
  - `SpdxReaderTest` / `SpdxWriteTest` 通过 mock `DependencyCacheService` 修复后通过
- **静态约束自检**：
  - [x] 仅修改 `openlibing-sbom` 业务仓与 `openlibing-docs` 归档仓
  - [x] 遵循目标仓既有 spring-batch job 模式与 Repository 风格
  - [x] 无硬编码凭证 / 敏感信息 / 危险默认值 / 注入风险
  - [x] 行为变化（新增 scope 参数 + 新增 REST API）有完整测试覆盖
  - [x] 数据模型变更（`package_dependency_cache` 表 + `uuid[]` 数组列）有对应 entity 与 Repository

## 设计偏差与取舍

| 项 | 原计划 | 实际交付 | 说明 |
|----|--------|----------|------|
| `dependencyCache/refresh` 入参 | `sbomId` (UUID) | `productName` (String) | `900a70b6` 初版用 `sbomId`，`3c40ed82` 重构为 `productName`，原因是调用方通常只知道 `productName`，强迫先查 `sbomId` 增加调用成本。该接口为同期新增，无既有调用方依赖，可安全重构 |
| 去重锁实现 | 未明确 | 进程内 `ConcurrentHashMap<sbomId, status>` | 不引入 Redis / DB 行锁，避免过度设计；多实例部署时由调用方保证幂等，重复触发只会重复计算（`upsert` 幂等），不会数据损坏 |
| BFS 反向边处理 | 未明确 | 仅遍历 `DEPENDS_ON`，严格排除 `RUNTIME_DEPENDENCY_OF` | 排除反向边让依赖图退化为 DAG，保证 BFS 可终止，避免环导致死循环 |

其余设计决策与原方案一致，无其他偏差。

## 可复用经验

1. **传递依赖闭包预计算优于在线递归 CTE**：SBOM 中包与依赖关系规模大、层级深时，递归 CTE 性能不可控（递归深度大、中间结果集膨胀、执行计划不稳定）。预计算物化缓存把成本前置到导入时一次性付出，在线查询降为单表主键查询。
2. **PostgreSQL `uuid[]` 数组列 + `= ANY(uuid[])` 替代长 `IN (...)`**：当 Collection 参数规模大（数百到数千）时，JPA 默认的 `IN (?, ?, ...)` 会导致 SQL 解析与计划生成开销显著。`uuid[]` 数组列配合 `= ANY(uuid[])` 操作符可被 PostgreSQL planner 更稳定地优化，参数固定为单个数组。
3. **BFS 用 projection 查询避免 N+1**：图遍历场景中，循环内查询关系数据时务必用 projection DTO 只 select 必要字段，避免加载大 TEXT 字段（如 `sbom_element_relationship` 的描述字段）与 N+1 查询。
4. **图遍历排除反向边让其退化为 DAG**：当关系表中同时存在正向（`DEPENDS_ON`）与反向（`RUNTIME_DEPENDENCY_OF`）关系时，BFS/DFS 必须明确只遍历一种方向，避免形成环导致死循环。
5. **缓存预计算的多触发入口模式**：同步入口（hook 在主流程末尾，小数据量立即可查）+ 异步 step（spring-batch 兜底，大数据量或同步失败时补算）+ REST API（存量数据清洗 / 失败重试）。三入口覆盖不同场景，去重锁防止重复计算。
6. **进程内去重锁的适用边界**：单实例部署可用 `ConcurrentHashMap` 实现去重；多实例部署时进程内锁失效，但若底层操作幂等（如 `upsert`），重复触发只会重复计算不会数据损坏，可接受。需要严格去重时再引入 Redis 或 DB 行锁，避免过度设计。

以上经验同步沉淀到 `openlibing-docs/spec/openlibing-sbom/ai_memory.md`（追加到既有规则库）。

## 归档日期

2026-07-31
