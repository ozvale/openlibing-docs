# 依赖包漏洞传递依赖查询 — pkg-vul-transitive-query

## 业务 Issue

- openlibing/openlibing-sbom#54 — 【openLiBing-Sbom】SBOM软件包详情下的CVE可展示当前组件依赖的开源组件的漏洞
- https://gitcode.com/openlibing/openlibing-sbom/issues/54
- Issue 状态：closed（创建者已关闭；spec 归档引用保留）

## 需求背景

`openlibing-sbom` 平台的 `queryPackageVulnerability` 接口原先仅支持查询**当前包自身**的漏洞，无法回答「这个包所在 SBOM 中，它的传递依赖是否也有漏洞」这类追溯问题。安全运营场景下，传递依赖漏洞往往是潜伏最深、影响最大的风险来源，缺乏传递依赖视角会迫使用户手工逐层下钻，效率低且容易遗漏。

### 性能约束

直接在线上用 PostgreSQL 递归 CTE 实时计算传递依赖闭包，会因 SBOM 中包与依赖关系规模大、层级深而出现严重性能问题（递归深度大、中间结果集膨胀、锁表风险）。因此本次同时引入**预计算物化缓存**：在 SBOM 导入流程中提前算好每个包的传递依赖闭包并落到 `package_dependency_cache` 表，在线查询时直接读缓存，避免递归 CTE。

### API 易用性

预计算缓存的触发接口最初设计为以 `sbomId` (UUID) 作为入参，但调用方（前端 / 运维）通常只知道 `productName`，需要先额外查询拿到 `sbomId`，使用不便。本次将其重构为以 `productName` 入参，内部解析 `sbomId` 后再触发预计算。

## 功能描述

### 功能一：queryPackageVulnerability 支持 scope 参数（关联 commit `900a70b6`）

在 `GET /queryPackageVulnerability` 接口新增 `scope` 查询参数，控制漏洞查询的覆盖范围：

| scope 取值 | 含义 | 数据来源 |
|-----------|------|---------|
| `SELF`（默认） | 仅当前包自身的漏洞 | 直接按 `packageId` 查 `package_vulnerability` |
| `DEPENDENCIES` | 仅传递依赖包的漏洞 | 读 `package_dependency_cache` 拿到传递依赖 ID 集合，按集合查漏洞 |
| `ALL` | 当前包 + 传递依赖包的漏洞 | 上述两者并集 |

- `scope` 参数可选，缺省 `SELF`，保持对既有调用方的兼容
- 非法 `scope` 值由 `VulQueryScope.parse()` 抛 `SbomRuntimeException`，Controller 兜底为 500
- `VulnerabilityVo` 新增 `name` / `version` 字段，便于前端在 `DEPENDENCIES` / `ALL` 场景下展示漏洞所属的包名与版本

### 功能二：传递依赖预计算缓存（关联 commit `900a70b6`）

新增 `PackageDependencyCache` entity（PostgreSQL `uuid[]` 数组列存储传递依赖 ID 集合）+ `DependencyGraphBuilder`（BFS 计算传递依赖闭包）+ `DependencyCacheService`（统一管理缓存的构建、查询、失效、刷新）。

`DependencyCacheService` 提供 3 个触发入口：

1. **同步入口** `precomputeForSbom(sbomId)` — hook 在 `SpdxReader.readSbomFile` 末尾，SBOM 导入完成后立即同步预计算
2. **异步入口** `PrecomputeDependencyCacheStep` — `readSbomJob` 中的 spring-batch step，作为同步入口的兜底（同步失败或漏算时由异步 step 补算）
3. **REST API** `POST /sbom-api/dependencyCache/refresh?productName=xxx` — 用于存量数据清洗或失败重试，HTTP 请求不阻塞等待预计算完成

#### DependencyGraphBuilder 实现要点

- BFS 遍历 `sbom_element_relationship` 表的 `DEPENDS_ON` 关系，排除 `RUNTIME_DEPENDENCY_OF`（避免反向边导致死循环）
- 使用 projection 查询 `PackageIdAndSpdxId`（只 select 必要字段），避免 N+1 查询和加载大 TEXT 字段
- 结果落到 `PackageDependencyCache`，主键为 `(sbom_id, package_id)`，传递依赖 ID 集合存到 `uuid[]` 数组列

#### 性能优化

- 漏洞查询按传递依赖 ID 集合过滤时，`findByPackageIdsInAndSeverityAndVulId` 改用 PostgreSQL `= ANY(uuid[])` 替代 JPA 默认的 `IN (...)`，避免长 IN list 导致的 SQL 解析与计划生成开销
- `SpdxReader.invalidateBySbom(sbomId)` 提供 SBOM 重新导入时的缓存失效入口，避免脏缓存

### 功能三：dependencyCache/refresh 入参重构（关联 commit `3c40ed82`）

将 `POST /dependencyCache/refresh` 接口入参从 `sbomId` (UUID) 改为 `productName` (String)：

- Controller 入参：`productName` 必传
- Service 层 `refreshDependencyCache(productName)` 内部先按 `productName` 查询 `sbomId`，再触发异步预计算
- 查不到 sbom 时抛 `SbomRuntimeException`，Controller 兜底为 HTTP 500
- 返回体新增 `productName` 字段，便于调用方核对
- 进程内本地锁（`ConcurrentHashMap`）按 `sbomId` 去重：同一 sbomId 已在处理时立即返回 `already_in_progress`，避免重复计算

## 不做

- 不引入分布式锁（Redis / DB 行锁）。`dependencyCache/refresh` 的去重只在单实例进程内用 `ConcurrentHashMap` 实现，避免过度设计；多实例部署时由调用方保证幂等
- 不修改既有 `queryPackageVulnerability` 接口的非 scope 参数语义（`packageId` / `severity` / `vulId` / `page` / `size` 行为不变）
- 不改变 `package_vulnerability` 表结构（漏洞数据来源不变）
- 不删除既有递归 CTE 查询路径（如其他模块依赖），仅本接口走缓存路径
- 不引入死信队列或重试框架，`PrecomputeDependencyCacheStep` 失败由 spring-batch 自带重试机制兜底
- 不修改 `sbom_element_relationship` 表结构（仅读取 `DEPENDS_ON` 关系）

## 验收标准

### 功能一：scope 参数

- [x] `GET /queryPackageVulnerability?packageId=xxx` 不传 `scope` 时按 `SELF` 处理（兼容既有调用）
- [x] `scope=SELF` 仅返回当前包漏洞
- [x] `scope=DEPENDENCIES` 仅返回传递依赖包漏洞
- [x] `scope=ALL` 返回当前包 + 传递依赖包漏洞（去重）
- [x] 非法 `scope` 值（如 `scope=FOO`）返回 HTTP 500 + 错误信息 `invalid scope: FOO`
- [x] `VulnerabilityVo` 在响应中携带 `name` / `version` 字段

### 功能二：传递依赖预计算缓存

- [x] `PackageDependencyCache` 表（PostgreSQL `uuid[]` 数组列）创建成功
- [x] SBOM 导入完成后 `SpdxReader.readSbomFile` 调用 `precomputeForSbom` 同步预计算
- [x] `readSbomJob` 中 `PrecomputeDependencyCacheStep` 异步兜底预计算
- [x] `DependencyGraphBuilder` 用 BFS 计算闭包，仅取 `DEPENDS_ON` 关系，排除 `RUNTIME_DEPENDENCY_OF`
- [x] BFS 使用 projection 查询 `PackageIdAndSpdxId`，不加载大 TEXT 字段
- [x] `findByPackageIdsInAndSeverityAndVulId` 用 `= ANY(uuid[])` 替代 `IN (...)`
- [x] `SpdxReader.invalidateBySbom(sbomId)` 在 SBOM 重新导入时清理过期缓存
- [x] `DependencyCacheServiceTest` 100% line coverage
- [x] `DependencyGraphBuilderTest` 100% line coverage
- [x] 既有 `SpdxReaderTest` / `SpdxWriteTest` 通过 mock `DependencyCacheService` 修复

### 功能三：dependencyCache/refresh 入参重构

- [x] `POST /dependencyCache/refresh?productName=xxx` 接口接受 `productName` 入参
- [x] Service 层先按 `productName` 查询 `sbomId`，再触发异步预计算
- [x] `productName` 查不到对应 sbom 时返回 HTTP 500
- [x] 同一 `sbomId` 重复触发时立即返回 `status=already_in_progress`，不重复计算
- [x] 响应体包含 `sbomId` / `productName` / `status` / `message` 字段

## 影响范围

| 文件 | 操作 | 归属功能 | 说明 |
|------|------|----------|------|
| `model/.../enums/VulQueryScope.java` | 新增 | 功能一 | SELF / DEPENDENCIES / ALL 枚举 + `parse()` 容错 |
| `model/.../entity/PackageDependencyCache.java` | 新增 | 功能二 | 缓存实体（`uuid[]` 数组列） |
| `model/.../pojo/dto/PackageIdAndSpdxId.java` | 新增 | 功能二 | projection DTO，避免 N+1 |
| `model/.../pojo/vo/sbom/VulnerabilityVo.java` | 修改 | 功能一 | 新增 `name` / `version` 字段 |
| `dao/PackageDependencyCacheRepository.java` | 新增 | 功能二 | 缓存 Repository |
| `dao/SbomElementRelationshipRepository.java` | 修改 | 功能二 | 新增 BFS 用的 projection 查询 |
| `dao/PackageRepository.java` | 修改 | 功能二 | 新增按 spdxId 集合查 packageId 的查询 |
| `dao/ExternalVulRefRepository.java` | 新增/修改 | 功能二 | `findByPackageIdsInAndSeverityAndVulId` 改用 `= ANY(uuid[])` |
| `api/sbom/SbomService.java` | 修改 | 一/三 | `queryPackageVulnerability` 增 `scope` 形参；`refreshDependencyCache` 改 `productName` 形参 |
| `controller/SbomController.java` | 修改 | 一/三 | `/queryPackageVulnerability` 增 `scope` 参数；`/dependencyCache/refresh` 改 `productName` |
| `service/sbom/impl/SbomServiceImpl.java` | 修改 | 一/二/三 | scope 分发逻辑、缓存查询集成、productName → sbomId 解析 |
| `service/sbom/impl/DependencyCacheService.java` | 新增 | 功能二 | 缓存管理服务（构建 / 查询 / 失效 / 刷新 + 去重锁） |
| `service/sbom/impl/DependencyGraphBuilder.java` | 新增 | 功能二 | BFS 传递依赖闭包计算 |
| `service/reader/impl/spdx/SpdxReader.java` | 修改 | 功能二 | hook `precomputeForSbom` + `invalidateBySbom` |
| `batch/step/PrecomputeDependencyCacheStep.java` | 新增 | 功能二 | spring-batch 异步预计算 step |
| `resources/spring-batch/sbom-read-job.xml` | 修改 | 功能二 | 注册 `PrecomputeDependencyCacheStep` 到 job |
| `test/.../controller/SbomControllerTest.java` | 修改 | 一/三 | 适配 scope 参数与 productName 入参 |
| `test/.../sbom/impl/DependencyCacheServiceTest.java` | 新增 | 功能二 | 100% line coverage |
| `test/.../sbom/impl/DependencyGraphBuilderTest.java` | 新增 | 功能二 | 100% line coverage |
| `test/.../sbom/impl/SbomServiceImplTest.java` | 修改 | 一/三 | 适配 scope 分发逻辑 |
| `test/.../reader/impl/spdx/SpdxReaderTest.java` | 修改 | 功能二 | mock `DependencyCacheService` |
| `test/.../reader/impl/spdx/SpdxWriteTest.java` | 修改 | 功能二 | mock `DependencyCacheService` |

- 业务仓：`openlibing-sbom`
- **涉及数据模型变更**：新增 `package_dependency_cache` 表（PostgreSQL `uuid[]` 数组列）
- **涉及外部接口变更**：`/queryPackageVulnerability` 新增 `scope` 参数（向后兼容，缺省 `SELF`）；新增 `/dependencyCache/refresh` 接口
- 不涉及其他仓的接口或契约变化

## 流程模式

Full 模式：完整 spec（proposal + design + tasks + archive）+ 实现 + 单元测试（100% line coverage）+ 数据模型变更 + 外部接口变更。
