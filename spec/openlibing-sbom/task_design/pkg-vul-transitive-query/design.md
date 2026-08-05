# 依赖包漏洞传递依赖查询 — 技术设计

## 方案概述

本次改动包含三个相关功能：

1. **scope 参数支持**：`queryPackageVulnerability` 接口新增 `scope` 参数（SELF / DEPENDENCIES / ALL），控制漏洞查询的覆盖范围，默认 SELF 向后兼容。
2. **传递依赖预计算缓存**：新增 `PackageDependencyCache` 表 + `DependencyGraphBuilder`（BFS）+ `DependencyCacheService`，在 SBOM 导入流程中预计算每个包的传递依赖闭包并落库，在线查询直接读缓存，避免递归 CTE 的性能问题。
3. **dependencyCache/refresh 入参重构**：REST API 入参从 `sbomId` (UUID) 改为 `productName` (String)，提升易用性。

## 架构决策

### 功能一：scope 参数

| 决策 | 选择 | 原因 |
|------|------|------|
| scope 取值 | `SELF` / `DEPENDENCIES` / `ALL` 三值枚举 | 覆盖典型场景：仅看当前包 / 仅看传递依赖 / 全部。`ALL` 内部为前两者并集，不引入第四种「差集」语义，避免接口膨胀 |
| 默认值 | `SELF` | 向后兼容，既有调用方不传 `scope` 时行为不变 |
| 实现方式 | 枚举 + `parse(String)` 静态工厂 | 集中处理 null/blank/非法值，非法值抛 `SbomRuntimeException` 由 Controller 兜底为 500；避免在 Controller / Service 多处分散判断 |
| `VulnerabilityVo` 扩展 | 新增 `name` / `version` 字段 | `DEPENDENCIES` / `ALL` 场景下漏洞来源是多个不同包，前端需要展示漏洞归属的包名与版本；`SELF` 场景下冗余但无害 |
| scope=ALL 去重 | DB 层 `UNION` + `DISTINCT` | 避免内存合并去重，让 PostgreSQL 完成；同时保证分页正确 |

### 功能二：传递依赖预计算缓存

#### 决策 1：物化缓存而非在线递归 CTE

- **选择**：在 SBOM 导入时预计算传递依赖闭包，落到 `package_dependency_cache` 表，在线查询直接读缓存
- **原因**：递归 CTE 在 SBOM 大、依赖层级深时性能不可控（递归深度大、中间结果集膨胀、执行计划不稳定）。预计算把成本前置到导入时一次性付出，在线查询降为单表主键查询
- **代价**：缓存需要维护一致性（SBOM 重新导入时失效 + 重算），但 SBOM 重新导入是低频事件，可接受

#### 决策 2：传递依赖 ID 集合用 PostgreSQL `uuid[]` 数组列

- **选择**：`PackageDependencyCache.dependencyIds` 字段类型为 `uuid[]`（PostgreSQL 原生数组类型）
- **原因**：
  - 传递依赖 ID 集合是只读的（写入后只整体替换，不修改单个元素），适合数组语义
  - PostgreSQL `uuid[]` 配合 `= ANY(uuid[])` 操作符在漏洞查询时可被索引高效利用，避免长 `IN (...)` list 的 SQL 解析与计划生成开销
  - 相比 JSONB 数组，`uuid[]` 类型校验更严格，存储更紧凑
- **对比**：单独的关联表 `(package_id, dependency_id)` 会在查询时需要 JOIN，对分页查询不友好

#### 决策 3：BFS 而非 DFS

- **选择**：`DependencyGraphBuilder` 用 BFS 遍历 `DEPENDS_ON` 关系
- **原因**：
  - BFS 天然避免递归栈溢出（SBOM 层级深时 DFS 递归可能爆栈）
  - BFS 用队列迭代，便于控制内存（可设上限阈值）
  - BFS 结果顺序与依赖层级一致，便于后续按层排序展示（若需要）

#### 决策 4：Projection 查询避免 N+1

- **选择**：BFS 中查询关系数据时使用 `PackageIdAndSpdxId` projection DTO，只 select 必要字段
- **原因**：
  - `sbom_element_relationship` 表含 TEXT 字段（如关系描述、外部引用），全量加载浪费内存
  - projection 让 JPA 只 select 需要的列，减少 IO 与内存压力
  - 避免循环中重复 `findById` 导致的 N+1 查询

#### 决策 5：仅取 DEPENDS_ON，排除 RUNTIME_DEPENDENCY_OF

- **选择**：BFS 只遍历 `relationship_type = 'DEPENDS_ON'` 的边，排除 `RUNTIME_DEPENDENCY_OF`
- **原因**：
  - `DEPENDS_ON` 是 SBOM 标准的静态依赖关系，是漏洞传递的合法路径
  - `RUNTIME_DEPENDENCY_OF` 是反向关系（"X 是 Y 的运行时依赖"），若一起遍历会导致图中出现反向边，可能形成环或重复计算
  - 排除反向边让图退化为 DAG，BFS 可终止

#### 决策 6：三触发入口

- **选择**：`DependencyCacheService` 提供 3 个触发入口
  - **同步入口** `precomputeForSbom(sbomId)` — hook 在 `SpdxReader.readSbomFile` 末尾
  - **异步入口** `PrecomputeDependencyCacheStep` — `readSbomJob` 中的 spring-batch step
  - **REST API** `POST /dependencyCache/refresh`
- **原因**：
  - 同步入口让小 SBOM 导入后立即可查传递依赖漏洞，无需等异步 step
  - 异步 step 作为兜底，当同步入口失败或漏算时由 spring-batch 补算（spring-batch 自带重试机制）
  - REST API 用于存量数据清洗（已导入但缺缓存的旧 SBOM）或失败重试
- **去重**：REST API 用进程内 `ConcurrentHashMap<sbomId, status>` 去重，同一 sbomId 已在处理时立即返回 `already_in_progress`

#### 决策 7：`= ANY(uuid[])` 替代 `IN (...)`

- **选择**：`ExternalVulRefRepository.findByPackageIdsInAndSeverityAndVulId` 改用 PostgreSQL `= ANY(uuid[])` 操作符
- **原因**：
  - JPA 默认对 Collection 参数生成 `IN (?, ?, ?, ...)`，当传递依赖 ID 集合很大（数百到数千）时，SQL 解析与计划生成开销显著
  - `= ANY(uuid[])` 是 PostgreSQL 推荐的大集合过滤方式，参数固定为单个数组，可被 planner 更稳定地优化
  - 配合 `uuid[]` 数组列存储，类型一致无需转换

#### 决策 8：缓存失效入口

- **选择**：`SpdxReader.invalidateBySbom(sbomId)` 提供 SBOM 重新导入时的缓存失效
- **原因**：
  - SBOM 重新导入后，包与依赖关系可能完全变化，旧缓存必须失效
  - 失效 + 重算放在导入流程内自动完成，避免运维手动清表

### 功能三：dependencyCache/refresh 入参重构

| 决策 | 选择 | 原因 |
|------|------|------|
| 入参类型 | `productName` (String) 替代 `sbomId` (UUID) | 调用方（前端 / 运维）通常只知道 `productName`，强迫先查 `sbomId` 增加调用成本；`productName` 是业务语义的稳定标识 |
| sbomId 解析 | Service 层按 `productName` 查询 `sbomId` 后再触发预计算 | Controller 不直接接触 sbomId，保持接口契约的纯业务语义 |
| 查不到 sbom | 抛 `SbomRuntimeException`，Controller 兜底 500 | 暴露清晰错误，避免 Controller 层分散判断 |
| 返回体 | `{sbomId, productName, status, message}` | `productName` 让调用方核对入参，`status` 区分 `accepted` / `already_in_progress` |
| 去重粒度 | 仍按 `sbomId` 去重（而非 `productName`） | 同一 sbomId 可能对应多个 `productName`（罕见但可能），按 sbomId 去重更精确 |

## 涉及文件

| 文件 | 操作 | 归属功能 | 说明 |
|------|------|----------|------|
| `model/.../enums/VulQueryScope.java` | 新增 | 一 | SELF / DEPENDENCIES / ALL 枚举 + `parse()` 容错 |
| `model/.../entity/PackageDependencyCache.java` | 新增 | 二 | 缓存实体，`uuid[]` 数组列 |
| `model/.../pojo/dto/PackageIdAndSpdxId.java` | 新增 | 二 | projection DTO |
| `model/.../pojo/vo/sbom/VulnerabilityVo.java` | 修改 | 一 | 新增 `name` / `version` 字段 |
| `dao/PackageDependencyCacheRepository.java` | 新增 | 二 | 缓存 Repository |
| `dao/SbomElementRelationshipRepository.java` | 修改 | 二 | 新增 projection 查询方法 |
| `dao/PackageRepository.java` | 修改 | 二 | 新增按 spdxId 集合查 packageId 的方法 |
| `dao/ExternalVulRefRepository.java` | 修改 | 二 | `findByPackageIdsInAndSeverityAndVulId` 改用 `= ANY(uuid[])` |
| `api/sbom/SbomService.java` | 修改 | 一/三 | 接口签名调整 |
| `controller/SbomController.java` | 修改 | 一/三 | 接口参数与签名调整 |
| `service/sbom/impl/SbomServiceImpl.java` | 修改 | 一/二/三 | scope 分发、缓存查询集成、productName → sbomId 解析 |
| `service/sbom/impl/DependencyCacheService.java` | 新增 | 二 | 缓存管理服务（构建 / 查询 / 失效 / 刷新 + 去重锁） |
| `service/sbom/impl/DependencyGraphBuilder.java` | 新增 | 二 | BFS 传递依赖闭包计算 |
| `service/reader/impl/spdx/SpdxReader.java` | 修改 | 二 | hook `precomputeForSbom` + `invalidateBySbom` |
| `batch/step/PrecomputeDependencyCacheStep.java` | 新增 | 二 | spring-batch 异步预计算 step |
| `resources/spring-batch/sbom-read-job.xml` | 修改 | 二 | 注册 step 到 job |
| `test/.../controller/SbomControllerTest.java` | 修改 | 一/三 | 适配参数变化 |
| `test/.../sbom/impl/DependencyCacheServiceTest.java` | 新增 | 二 | 100% line coverage |
| `test/.../sbom/impl/DependencyGraphBuilderTest.java` | 新增 | 二 | 100% line coverage |
| `test/.../sbom/impl/SbomServiceImplTest.java` | 修改 | 一/三 | 适配 scope 分发逻辑 |
| `test/.../reader/impl/spdx/SpdxReaderTest.java` | 修改 | 二 | mock `DependencyCacheService` |
| `test/.../reader/impl/spdx/SpdxWriteTest.java` | 修改 | 二 | mock `DependencyCacheService` |

## 关键代码结构

### VulQueryScope（功能一）

```java
public enum VulQueryScope {
  SELF, DEPENDENCIES, ALL;

  public static VulQueryScope parse(String scope) {
    if (StringUtils.isBlank(scope)) {
      return SELF;  // 默认值
    }
    try {
      return VulQueryScope.valueOf(scope.trim().toUpperCase(Locale.ROOT));
    } catch (IllegalArgumentException e) {
      throw new SbomRuntimeException("invalid scope: %s".formatted(scope));
    }
  }
}
```

### SbomController 接口签名（功能一、三）

```java
// 功能一：scope 参数
@GetMapping("/queryPackageVulnerability")
public ResponseEntity queryVulnerabilityByPackageId(
    @RequestParam("packageId") String packageId,
    @RequestParam(required = false) String severity,
    @RequestParam(required = false) String vulId,
    @RequestParam(name = "scope", required = false, defaultValue = "SELF") String scope,
    @RequestParam(name = "page", required = false, defaultValue = "0") Integer page,
    @RequestParam(name = "size", required = false, defaultValue = "15") Integer size) {
  PageVo<VulnerabilityVo> vulnerabilities =
      sbomService.queryPackageVulnerability(packageId, severity, vulId, scope, pageable);
  // ...
}

// 功能三：productName 入参
@PostMapping("/dependencyCache/refresh")
public ResponseEntity refreshDependencyCache(
    @RequestParam(name = "productName", required = true) String productName) {
  Map<String, Object> result = sbomService.refreshDependencyCache(productName);
  // 返回 {sbomId, productName, status, message}
}
```

### DependencyGraphBuilder（功能二）

```java
@Component
public class DependencyGraphBuilder {
  /**
   * BFS 计算 sbomId 下 packageId 的传递依赖闭包。
   * 仅遍历 DEPENDS_ON 关系，排除 RUNTIME_DEPENDENCY_OF。
   * 用 projection 查询避免 N+1 和加载大 TEXT 字段。
   */
  public Set<UUID> buildTransitiveDeps(UUID sbomId, UUID packageId) {
    Set<UUID> visited = new HashSet<>();
    Queue<UUID> queue = new ArrayDeque<>();
    queue.add(packageId);
    while (!queue.isEmpty()) {
      UUID current = queue.poll();
      if (!visited.add(current)) continue;  // 已访问
      // projection 查询：只 select packageId 与 spdxId
      List<PackageIdAndSpdxId> deps =
          sbomElementRelationshipRepository.findDependsOnTargets(sbomId, current);
      for (PackageIdAndSpdxId dep : deps) {
        queue.add(dep.getPackageId());
      }
    }
    visited.remove(packageId);  // 排除自身
    return visited;
  }
}
```

### DependencyCacheService（功能二）

```java
@Service
public class DependencyCacheService {
  // 进程内去重锁（按 sbomId）
  private final ConcurrentHashMap<UUID, Boolean> inProgress = new ConcurrentHashMap<>();

  /** 同步入口：SBOM 导入完成后调用。 */
  public void precomputeForSbom(UUID sbomId) {
    List<UUID> packageIds = packageRepository.findPackageIdsBySbomId(sbomId);
    for (UUID packageId : packageIds) {
      Set<UUID> deps = dependencyGraphBuilder.buildTransitiveDeps(sbomId, packageId);
      upsertCache(sbomId, packageId, deps);
    }
  }

  /** REST API 入口：异步预计算，立即返回。 */
  public Map<String, Object> refreshDependencyCache(String productName) {
    UUID sbomId = sbomRepository.findSbomIdByProductName(productName)
        .orElseThrow(() -> new SbomRuntimeException("sbom not found for product: " + productName));
    if (inProgress.putIfAbsent(sbomId, true) != null) {
      return Map.of("sbomId", sbomId, "productName", productName,
          "status", "already_in_progress", "message", "cache refresh already running");
    }
    // 异步触发预计算（不阻塞 HTTP）
    executor.submit(() -> {
      try {
        precomputeForSbom(sbomId);
      } finally {
        inProgress.remove(sbomId);
      }
    });
    return Map.of("sbomId", sbomId, "productName", productName,
        "status", "accepted", "message", "cache refresh dispatched");
  }

  /** 缓存失效：SBOM 重新导入时调用。 */
  public void invalidateBySbom(UUID sbomId) {
    packageDependencyCacheRepository.deleteBySbomId(sbomId);
  }
}
```

### ExternalVulRefRepository 优化（功能二）

```java
// 改用 = ANY(uuid[]) 替代 IN (...)
@Query(value = """
    SELECT v.* FROM external_vul_ref v
    WHERE v.package_id = ANY(:packageIds)
      AND (:severity IS NULL OR v.severity = :severity)
      AND (:vulId IS NULL OR v.vul_id = :vulId)
    """, nativeQuery = true)
List<VulnerabilityVo> findByPackageIdsInAndSeverityAndVulId(
    @Param("packageIds") UUID[] packageIds,
    @Param("severity") String severity,
    @Param("vulId") String vulId,
    Pageable pageable);
```

## 数据流

### SBOM 导入时预计算缓存

```
SBOM 文件上传
  ↓ SpdxReader.readSbomFile
  ↓ 解析包与关系，写入 package / sbom_element_relationship
  ↓ hook: DependencyCacheService.precomputeForSbom(sbomId)  ← 同步入口
  ↓   └→ 遍历 package 列表
  ↓        └→ DependencyGraphBuilder.buildTransitiveDeps(sbomId, packageId)
  ↓              ├→ BFS 遍历 DEPENDS_ON（排除 RUNTIME_DEPENDENCY_OF）
  ↓              ├→ projection 查询 PackageIdAndSpdxId（避免 N+1）
  ↓              └→ 返回传递依赖 ID 集合
  ↓        └→ upsert package_dependency_cache (sbom_id, package_id, dependency_ids uuid[])
  ↓
  ↓ readSbomJob 继续
  ↓ ... PrecomputeDependencyCacheStep  ← 异步兜底
  ↓   └→ 同样调用 precomputeForSbom，对同步入口漏算的包补算
  ↓
  ↓ SBOM 导入完成

# SBOM 重新导入时
SpdxReader.readSbomFile
  ↓ DependencyCacheService.invalidateBySbom(sbomId)  ← 先失效
  ↓ 重新解析写入
  ↓ precomputeForSbom(sbomId)  ← 再重算
```

### 在线漏洞查询（scope 分发）

```
GET /queryPackageVulnerability?packageId=xxx&scope=DEPENDENCIES&page=0&size=15
  ↓ SbomController
  ↓ SbomService.queryPackageVulnerability(packageId, severity, vulId, scope, pageable)
  ↓ VulQueryScope.parse(scope) → DEPENDENCIES
  ↓ switch(scope):
       SELF        → 直接按 packageId 查 external_vul_ref
       DEPENDENCIES → package_dependency_cache.findByPackageId(packageId)
                       → 拿到 dependency_ids (uuid[])
                       → external_vul_ref.findByPackageIdsInAndSeverityAndVulId(
                            packageIds = dependency_ids, severity, vulId, pageable)
                          （= ANY(uuid[]) 优化查询）
       ALL         → SELF + DEPENDENCIES 结果 UNION（DB 层去重 + 分页）
  ↓ 返回 PageVo<VulnerabilityVo>（含 name/version 字段）
```

### REST API 触发缓存刷新

```
POST /dependencyCache/refresh?productName=xxx
  ↓ SbomController
  ↓ SbomService.refreshDependencyCache(productName)
  ↓ sbomRepository.findSbomIdByProductName(productName)
       → 查不到：抛 SbomRuntimeException → Controller 返回 500
       → 查到：sbomId
  ↓ inProgress.putIfAbsent(sbomId, true)
       → 已存在：返回 {status=already_in_progress}
       → 不存在：异步执行 precomputeForSbom(sbomId)
  ↓ 立即返回 {sbomId, productName, status=accepted, message=...}
  ↓ （异步）precomputeForSbom 完成后 inProgress.remove(sbomId)
```

## 风险 & 缓解

### 性能

| 风险 | 缓解 |
|------|------|
| SBOM 规模大时同步预计算阻塞导入流程 | 同步入口只算小 SBOM；大 SBOM 走异步 step 兜底，spring-batch 自带 chunk 处理 |
| 传递依赖 ID 集合过大导致 `uuid[]` 单行过大 | PostgreSQL `uuid[]` 单行理论上无硬上限（受 `block_size` 约束），传递依赖闭包通常在数百到数千级别，单行可控；超大规模场景后续可考虑分片存储 |
| BFS 内存爆炸（极深依赖链） | BFS 用迭代队列而非递归，避免栈溢出；后续可加 `visited.size()` 上限阈值告警 |
| `= ANY(uuid[])` 在集合极大时仍慢 | 已加 `package_id` 索引；超大集合场景可后续引入物化视图或预聚合 |

### 一致性

| 风险 | 缓解 |
|------|------|
| SBOM 重新导入后缓存未失效 | `SpdxReader` 在导入开始时调 `invalidateBySbom`，导入完成时调 `precomputeForSbom`，两步都在事务边界内 |
| 同步入口失败导致缓存缺失 | 异步 step `PrecomputeDependencyCacheStep` 兜底补算；spring-batch 重试机制覆盖瞬时故障 |
| REST API 重复触发导致重复计算 | `ConcurrentHashMap<sbomId, status>` 进程内去重，同一 sbomId 已在处理时立即返回 `already_in_progress` |
| 多实例部署时去重失效 | `ConcurrentHashMap` 仅单实例有效；多实例部署由调用方保证幂等（重复触发只会重复计算，不会数据损坏，因为 `upsert` 是幂等的） |

### 接口兼容性

| 风险 | 缓解 |
|------|------|
| 既有调用方不传 `scope` 行为变化 | 默认 `SELF` 保持向后兼容，行为与原接口一致 |
| `dependencyCache/refresh` 入参从 `sbomId` 改为 `productName` 是破坏性变更 | 该接口为本次同期新增，无既有调用方依赖，可安全重构 |
| `VulnerabilityVo` 新增字段破坏旧前端 | 新增字段是向后兼容的（旧前端忽略未知字段） |

### 数据完整性

| 风险 | 缓解 |
|------|------|
| `package_dependency_cache` 表数据与 `sbom_element_relationship` 漂移 | 缓存失效入口 + 重算机制保证最终一致；运维可通过 REST API 手动触发重算 |
| BFS 漏算某些传递依赖 | 严格按 `DEPENDS_ON` 关系遍历，排除 `RUNTIME_DEPENDENCY_OF` 是设计决策（非 bug）；测试覆盖多种图结构（链 / 树 / DAG / 环） |

## 跨仓影响

无。改动仅限 `openlibing-sbom` 单仓，不涉及其他仓的接口或契约变化。

`/queryPackageVulnerability` 接口的新增 `scope` 参数是向后兼容的（缺省 `SELF`），既有调用方无需修改。`/dependencyCache/refresh` 是本次同期新增的接口，无既有调用方依赖。
