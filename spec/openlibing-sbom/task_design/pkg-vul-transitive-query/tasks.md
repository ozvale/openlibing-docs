# 依赖包漏洞传递依赖查询 — 实现任务

## 进度: 17/17 complete

### 功能一：queryPackageVulnerability 支持 scope 参数（commit `900a70b6`）

- [x] Task 1: 新增 `VulQueryScope` 枚举（`SELF` / `DEPENDENCIES` / `ALL`），实现 `parse(String)` 静态工厂方法（null/blank 返回 `SELF`，非法值抛 `SbomRuntimeException`）
- [x] Task 2: 扩展 `VulnerabilityVo`，新增 `name` / `version` 字段，用于 `DEPENDENCIES` / `ALL` 场景下展示漏洞所属包名与版本
- [x] Task 3: `SbomService.queryPackageVulnerability` 接口签名新增 `scope` 形参
- [x] Task 4: `SbomController.queryVulnerabilityByPackageId` 接口新增 `scope` 查询参数（`required=false, defaultValue="SELF"`），向后兼容
- [x] Task 5: `SbomServiceImpl.queryPackageVulnerability` 实现 `scope` 分发逻辑（`SELF` 直查 / `DEPENDENCIES` 走缓存 / `ALL` 并集去重）

### 功能二：传递依赖预计算缓存（commit `900a70b6`）

- [x] Task 6: 新增 `PackageDependencyCache` entity，`dependencyIds` 字段用 PostgreSQL `uuid[]` 数组列；主键 `(sbom_id, package_id)`
- [x] Task 7: 新增 `PackageDependencyCacheRepository`，提供 `findBySbomIdAndPackageId` / `deleteBySbomId` / `save` 等
- [x] Task 8: 新增 `PackageIdAndSpdxId` projection DTO，用于 BFS 中只 select 必要字段
- [x] Task 9: `SbomElementRelationshipRepository` 新增 projection 查询方法，按 `(sbomId, packageId)` 查 `DEPENDS_ON` 目标
- [x] Task 10: `PackageRepository` 新增按 `spdxId` 集合查 `packageId` 的方法
- [x] Task 11: `ExternalVulRefRepository.findByPackageIdsInAndSeverityAndVulId` 改用 PostgreSQL `= ANY(uuid[])` 替代 `IN (...)`，避免长 IN list 性能问题
- [x] Task 12: 新增 `DependencyGraphBuilder`，实现 BFS 传递依赖闭包计算（仅遍历 `DEPENDS_ON`，排除 `RUNTIME_DEPENDENCY_OF`；用 projection 查询避免 N+1 和加载大 TEXT 字段）
- [x] Task 13: 新增 `DependencyCacheService`，提供 3 个触发入口：
  - 同步入口 `precomputeForSbom(sbomId)` hook 在 `SpdxReader.readSbomFile` 末尾
  - 异步入口 `PrecomputeDependencyCacheStep`（spring-batch step）
  - REST API `refreshDependencyCache(productName)` 用 `ConcurrentHashMap<sbomId, status>` 去重
  - 缓存失效入口 `invalidateBySbom(sbomId)`
- [x] Task 14: `SpdxReader` 修改：hook `precomputeForSbom` 在 `readSbomFile` 末尾；新增 `invalidateBySbom(sbomId)` 供 SBOM 重新导入时调用
- [x] Task 15: 新增 `PrecomputeDependencyCacheStep`（spring-batch step），并在 `sbom-read-job.xml` 中注册到 `readSbomJob`，作为同步入口的兜底

### 功能三：dependencyCache/refresh 入参重构（commit `3c40ed82`）

- [x] Task 16: `SbomService.refreshDependencyCache` 接口签名从 `sbomId` (UUID) 改为 `productName` (String)；`SbomController.refreshDependencyCache` 入参对应调整；返回体新增 `productName` 字段
- [x] Task 17: `SbomServiceImpl.refreshDependencyCache(productName)` 实现：先按 `productName` 查 `sbomId`（查不到抛 `SbomRuntimeException`），再用 `ConcurrentHashMap<sbomId, status>` 去重触发异步预计算

## 验证方式

### 功能一

- `mvn test -pl sbom-web "-Dtest=SbomControllerTest"` 通过
- `mvn test -pl sbom-web "-Dtest=SbomServiceImplTest"` 通过
- 手动验证 `scope=SELF` / `DEPENDENCIES` / `ALL` / 非法值四种场景

### 功能二

- `mvn test -pl sbom-web "-Dtest=DependencyCacheServiceTest"` 通过，100% line coverage
- `mvn test -pl sbom-web "-Dtest=DependencyGraphBuilderTest"` 通过，100% line coverage
- `mvn test -pl sbom-web "-Dtest=SpdxReaderTest,SpdxWriteTest"` 通过（已 mock `DependencyCacheService`）
- 端到端验证：导入 SBOM 后查询 `scope=DEPENDENCIES` 能返回传递依赖漏洞

### 功能三

- `mvn test -pl sbom-web "-Dtest=SbomControllerTest"` 通过
- 手动验证 `productName` 入参、查不到 sbom 时返回 500、重复触发返回 `already_in_progress`

## 关联

- 业务仓: `openlibing-sbom`
- 业务分支: `feat-query-pkg-vul-transitive-deps`
- 业务 Issue: openlibing/openlibing-sbom#54 (https://gitcode.com/openlibing/openlibing-sbom/issues/54)
- 关联 commit:
  - `900a70b6` feat(sbom): support transitive deps query for package vulnerability（2026-07-28，核心交付，22 文件 +1822/-204）
  - `3c40ed82` refactor(sbom): use productName as dependency cache refresh param（2026-07-29，REST API 入参重构，3 文件 +36/-22）
- 参考实现: spring-batch `readSbomJob` 既有 step 模式
- 数据模型变更: 新增 `package_dependency_cache` 表（PostgreSQL `uuid[]` 数组列）
- 外部接口变更: `/queryPackageVulnerability` 新增 `scope` 参数（向后兼容）；新增 `/dependencyCache/refresh` 接口
