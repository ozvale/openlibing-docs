# 【openlibing-sbom】软件成分分析页面中标识主被动依赖-go语言 — EDEVOPS 设计文档

---

## 1. 方案设计

### 1.1 背景

openlibing-sbom 软件成分分析页面中，当前未区分软件包的直接依赖与间接依赖属性。开源管理中，主被动依赖管理原则差异较大，需在 SBOM 解析统计阶段从 spdx-json 的 `DEPENDS_ON` / `DESCRIBES` 关系元数据层面识别每个软件包的依赖类型（直接/间接），并在包查询接口支持按依赖类型过滤，便于前端展示与运营筛选。

关联 Issue: [#51](https://gitcode.com/openlibing/openlibing-sbom/issues/51)

### 1.2 方案概述

在 `PackageStatistics` 实体新增 `dependencyType` 字段（`Integer`，`0`=直接依赖，`1`=间接依赖，`3`=直接/间接依赖，可扩展）。在 `CollectStatisticsStep` 统计阶段从已持久化的 `SbomElementRelationship` 表中解析每个软件包的依赖类型，赋值后随 `PackageStatistics` 落库。同时在包查询接口 `querySbomPackageList` / `querySbomPackages` 入参新增 `dependencyType` 可选过滤参数，返回的 `PackageStatisticsVo` 包含 `dependencyType` 字段。

### 1.3 方案架构

```
openlibing-sbom
┌──────────────────────┐
│ SpdxReader            │ ← spdx-json 导入时解析 relationships，持久化到
│ (已有，不改动)        │    SbomElementRelationship 表
│                      │
│          │           │
│          ▼           │
│ CollectStatistics     │
│ Step                 │
│ ┌──────────────────┐ │
│ │ calcRootSpdxIds   │ │ ← 识别根包: SPDXRef-DOCUMENT DESCRIBES root
│ │ calcDependedSet   │ │ ← 计算被任何包 DEPENDS_ON 依赖的集合
│ │ calcDirectDepSet  │ │ ← 直接依赖 = 根包DEPENDS_ON ∪ 未被任何包DEPENDS_ON
│ │ collectDepType    │ │ ← pkg ∈ directSet → 0，否则 → 1
│ └──────────────────┘ │
│          │           │
│          ▼           │
│ PackageStatistics     │ ← 新增 dependency_type 列
│ (PostgreSQL)         │
└──────────────────────┘
                      │
        ┌─────────────┴─────────────┐
        ▼                           ▼
 QuerySbomPackages            PackageStatisticsVo
 Request.dependencyType       Vo.dependencyType
        │                           │
        ▼                           ▼
PackageRepository              getPackageInfoByName
 (3 个 SQL 新增过滤)            ForPage / getPackages
                                ByGroupPage / count
                                PackageGroups
```

### 1.4 关键技术决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 字段命名 | `dependencyType` / `dependency_type` | 修正 Issue 中 `dependy_type` 拼写笔误，遵循 Java 驼峰规范 |
| 数据类型 | `Integer`（可空） | 兼容旧数据（存量行值为 `NULL`）；可选过滤参数 `null` = 不过滤 |
| 解析数据源 | `SbomElementRelationship` 表 | `SpdxReader` 已将 spdx-json 所有 relationships 持久化，无需重复解析 |
| 解析时机 | `CollectStatisticsStep.collectPackageStatistics` 循环外计算一次 | 所有包共享同一份 `directDepSpdxIdSet`，避免每轮循环重复解析 |
| 根包识别 | `SPDXRef-DOCUMENT` + `DESCRIBES` | SPDX 2.3 规范定义：`DESCRIBES` 关系从 Document 指向被描述的根包 |
| 依赖关系来源 | 仅 `DEPENDS_ON`，不用 `RUNTIME_DEPENDENCY_OF` | `RUNTIME_DEPENDENCY_OF` 方向与 `DEPENDS_ON` 相反（X RUNTIME_DEPENDENCY_OF Y ≡ Y DEPENDS_ON X），混合使用引入方向歧义与重复统计 |
| 无依赖包归属 | 直接依赖（0） | 未出现在任何 `DEPENDS_ON` 关系的 `relatedElementId` 中 → 逻辑上对该 SBOM 是"直接存在"的包 |
| 既直接又间接 | 标识为 3（直接/间接依赖） | 包同时在 `directDepSpdxIdSet` 和 `dependedSpdxIdSet` 中 → 3 |
| 过滤参数设计 | `(:dependencyType IS NULL OR dependency_type = :dependencyType)` | 不传时向后兼容，与项目既有 `IS NULL OR` 模式一致 |
| DDL 方式 | Hibernate auto DDL | 与项目既有实体字段新增方式一致，无需手动迁移脚本 |

---

## 2. 实现逻辑设计

### 2.1 依赖类型解析流程

```
CollectStatisticsStep.collectPackageStatistics(sbom)
  │
  ├─ 1. directDepSpdxIdSet = calculateDirectDepSpdxIdSet(sbom)
  │     │
  │     ├─ 1.1 rootSpdxIdSet = calculateRootSpdxIdSet(relationships)
  │     │     遍历 relationships:
  │     │       elementId == "SPDXRef-DOCUMENT"
  │     │       && relationshipType == "DESCRIBES"
  │     │       → relatedElementId 加入 rootSpdxIdSet
  │     │
  │     ├─ 1.2 dependedSpdxIdSet = calculateDependedSpdxIdSet(relationships)
  │     │     遍历 relationships:
  │     │       relationshipType == "DEPENDS_ON"
  │     │       → relatedElementId 加入 dependedSpdxIdSet
  │     │
  │     ├─ 1.3 子集 A：根包 DEPENDS_ON 的包
  │     │     relationships 中 elementId ∈ rootSpdxIdSet
  │     │     && relationshipType == "DEPENDS_ON"
  │     │     → relatedElementId 加入 directDepSpdxIdSet
  │     │
  │     └─ 1.4 子集 B：没被任何包 DEPENDS_ON 依赖的包
  │           sbom.packages 中 spdxId ∉ dependedSpdxIdSet
  │           → spdxId 加入 directDepSpdxIdSet
  │
  └─ 2. for each pkg in sbom.packages:
        collectPackageDependencyType(statistics, pkg, directDepSpdxIdSet, dependedSpdxIdSet)
          pkg.spdxId ∈ directDepSpdxIdSet && ∈ dependedSpdxIdSet → statistics.dependencyType = 3
          pkg.spdxId ∈ directDepSpdxIdSet && ∉ dependedSpdxIdSet → statistics.dependencyType = 0
          否则 → statistics.dependencyType = 1
```

### 2.2 根包识别示例

```
spdx-json relationships:
  SPDXRef-DOCUMENT DESCRIBES SPDXRef-Package-A     → A 是根包
  SPDXRef-Package-A DEPENDS_ON SPDXRef-Package-B    → B 是 A 的直接依赖
  SPDXRef-Package-B DEPENDS_ON SPDXRef-Package-C    → C 是 A 的间接依赖

解析结果:
  rootSpdxIdSet     = {A}
  dependedSpdxIdSet = {B, C}
  directDepSpdxIdSet = {A (未在任何 DEPENDS_ON 的 relatedElementId 出现), B (根包 DEPENDS_ON)} = {A, B}
  → A.dependencyType = 0 (直接依赖，不在 dependedSet 中)
  → B.dependencyType = 3 (直接/间接依赖，在 directSet 且在 dependedSet 中)
  → C.dependencyType = 1 (间接依赖)
```

### 2.3 边界场景处理

| 场景 | 处理 |
|------|------|
| `SbomElementRelationship` 为空 | `calculateDirectDepSpdxIdSet` 返回空集合 → 所有包 `spdxId ∉ ∅` → 全部 dependencyType=1。但实际上所有包也未被任何包 DEPENDS_ON → 此场景用空集合结果正确（无数据结构依赖，逻辑自洽） |
| 无 `SPDXRef-DOCUMENT` DESCRIBES 关系 | `rootSpdxIdSet` 为空 → 子集 A 为空 → 仅子集 B 生效（所有未出现在 depended 集合的包 = 直接依赖） |
| 无 `DEPENDS_ON` 关系 | `dependedSpdxIdSet` 为空 → 子集 A 为空 → 所有包都未出现在 depended 集合中 → 全部归直接依赖（0） |
| 既直接又间接（如包 B 既是根包直接依赖，也被包 C DEPENDS_ON） | `B ∈ directDepSpdxIdSet` 且 `B ∈ dependedSpdxIdSet` → 3 |

### 2.4 查询接口过滤流程

```
GET /sbom-api/querySbomPackages?dependencyType=0
  │
  ├─ SbomController.querySbomPackagesDeprecated()
  │     req.setDependencyType(dependencyType)  // Integer, 可空
  │
  ├─ SbomServiceImpl.getPackageInfoByNameForPage(req)
  │     传递 req.getDependencyType()
  │
  ├─ PackageRepository.getPackageInfoByNameForPage(..., dependencyType, pageable)
  │     SQL: AND (:dependencyType IS NULL OR dependency_type = :dependencyType)
  │
  └─ PackageStatisticsVo.fromPackage()
        vo.setDependencyType(statistics.getDependencyType())
```

### 2.5 异常处理

| 场景 | 处理 |
|------|------|
| `SbomElementRelationship` 为 null | `calculateDirectDepSpdxIdSet` 中 `ObjectUtils.isEmpty(relationships)` 判断 → 返回空集合 → 所有包依赖类型由子集 B 判定 |
| `relationshipType` 为 null | `StringUtils.equals(null, "DEPENDS_ON")` → false → 自动跳过 |
| `elementId` 为 null | `StringUtils.equals(null, "SPDXRef-DOCUMENT")` → false → 根包识别集合可能为空 → 由子集 B 兜底 |
| `pkg.getSpdxId()` 为 null | `directDepSpdxIdSet.contains(null)` → false → 该包归间接依赖（1） |

---

## 3. 类设计

### 3.1 修改类

| 类 | 模块 | 路径 | 变更 |
|----|------|------|------|
| `PackageStatistics` | model | `model/.../entity/PackageStatistics.java` | 新增 `dependencyType` 字段（`Integer`）+ Javadoc + getter/setter |
| `CollectStatisticsStep` | batch | `batch/.../step/CollectStatisticsStep.java` | 新增 4 个私有方法 + 在 `collectPackageStatistics` 中调用 |
| `PackageStatisticsVo` | model | `model/.../vo/sbom/PackageStatisticsVo.java` | 新增 `dependencyType` 字段 + getter/setter + `fromPackage` 填充 |
| `QuerySbomPackagesRequest` | model | `model/.../request/sbom/QuerySbomPackagesRequest.java` | 新增 `dependencyType` 字段（`Integer`）+ getter/setter + toString |
| `PackageRepository` | dao | `dao/.../PackageRepository.java` | `getPackageInfoByNameForPage` / `getPackagesByGroupPage` / `countPackageGroups` 3 个方法新增 `dependencyType` 参数 + SQL 过滤条件 |
| `SbomServiceImpl` | sbom-web | `sbom-web/.../service/sbom/impl/SbomServiceImpl.java` | `getPackageInfoByNameForPage` / `getPackageGroupByNameForPage` 透传 `req.getDependencyType()` |
| `SbomController` | sbom-web | `sbom-web/.../controller/SbomController.java` | `querySbomPackagesDeprecated` 新增 `@RequestParam(required = false) Integer dependencyType` |

### 3.2 不存在新增类

本次改动仅在现有 7 个类上做增量修改，不新增类。

### 3.3 CollectStatisticsStep 新增方法详情

```
class: CollectStatisticsStep
package: org.opensourceway.sbom.batch.step
路径: batch/.../step/CollectStatisticsStep.java

新增方法:
  Set<String> calculateDirectDepSpdxIdSet(Sbom sbom)
    职责: 计算直接依赖的 spdxId 集合（入口方法）
    复杂度: O(N)，N = relationships 数量 + packages 数量
    行数: 22

  Set<String> calculateRootSpdxIdSet(List<SbomElementRelationship> relationships)
    职责: 识别根包 spdxId 集合（SPDXRef-DOCUMENT DESCRIBES）
    过滤条件: elementId == "SPDXRef-DOCUMENT" && relationshipType == "DESCRIBES"
    行数: 7

  Set<String> calculateDependedSpdxIdSet(List<SbomElementRelationship> relationships)
    职责: 计算被任何包 DEPENDS_ON 依赖的 spdxId 集合
    过滤条件: relationshipType == "DEPENDS_ON"
    行数: 6

  void collectPackageDependencyType(PackageStatistics, Package, Set<String>)
    职责: 填充单包的依赖类型（∈ directSet → 0，否则 → 1）
    行数: 3
```

---

## 4. 数据模型设计

### 4.1 涉及的数据库表

| 表 | 数据库 | 用途 |
|----|--------|------|
| `package_statistics` | PostgreSQL (sbom) | 新增 `dependency_type` 列存储依赖类型（Hibernate auto DDL 自动建列） |
| `sbom_element_relationship` | PostgreSQL (sbom) | 已存在，`SpdxReader` 持久化的 spdx relationships，`CollectStatisticsStep` 读取用于解析依赖类型 |

### 4.2 新增列

```sql
-- package_statistics 表新增列（Hibernate auto DDL 自动生成，此处仅示意）
ALTER TABLE package_statistics ADD COLUMN dependency_type INTEGER;

-- 列约束
-- dependency_type: INTEGER, nullable
-- 取值: 0 = 直接依赖, 1 = 间接依赖, 3 = 直接/间接依赖, NULL = 存量数据未填充
```

### 4.3 核心查询 SQL

```sql
-- 按 dependencyType 过滤包列表（3 个方法公用同一条件）
SELECT p.*
FROM package p
LEFT JOIN package_statistics ps ON p.id = ps.package_id
WHERE ...
  AND (:dependencyType IS NULL OR ps.dependency_type = :dependencyType)
ORDER BY ...
```

`IS NULL OR` 模式保证不传参数时行为与变更前一致（向后兼容）。该模式已在项目内 `vulSeverity`、`noLicense`、`licenseId` 等参数中广泛使用。

### 4.4 API 返回数据结构

```json
{
  "content": [
    {
      "id": "123",
      "name": "curl",
      "version": "7.88.1",
      "statistics": {
        "dependencyType": 0,
        "criticalVulCount": 0,
        "depCount": 2,
        "runtimeDepCount": 0,
        "licenseCount": 1
      }
    }
  ],
  "total": 1
}
```

新增字段：`statistics.dependencyType`（`Integer`，`0` / `1` / `3`）。

---

## 5. 性能设计

### 5.1 解析性能优化

| 优化点 | 说明 |
|--------|------|
| 循环外计算 | `calculateDirectDepSpdxIdSet` 在 `forEach` 循环外执行一次，循环内仅做 `Set.contains()` O(1) 查询 |
| 流式聚合 | 使用 `Stream.filter().map().collect(Collectors.toSet())` 单次遍历构建集合，避免多次循环 |
| 数据结构 | `HashSet` O(1) 查找，`Set.contains()` 判断依赖类型 |
| 复杂度 | `O(N)`，N = relationships 数量 + packages 数量（典型 SPDX 文档数千条关系，子毫秒级完成） |

### 5.2 SQL 查询性能

| 优化点 | 说明 |
|--------|------|
| `IS NULL OR` 短路 | PostgreSQL 对 `:param IS NULL` 使用短路求值，传 NULL 时不检查 `dependency_type = NULL` |
| LEFT JOIN 不变 | `LEFT JOIN package_statistics` 已存在于现有 3 个查询中，不新增 JOIN |
| 索引建议 | `package_statistics.dependency_type` 列可建索引加速过滤查询（非本次改动范围） |

### 5.3 请求量评估

| 指标 | 估算 |
|------|------|
| 解析触发 | `CollectStatisticsStep` 每个 SBOM 扫描触发一次 |
| 单次解析 records | ~数千条 relationships + ~数百个 packages |
| 单次解析耗时 | < 1ms（纯内存 Set 操作） |
| 查询过滤 | `dependencyType` 参数用户按需传入，频率不高于现有查询 |

---

## 6. API 接口设计

### 6.1 修改接口

#### `GET /sbom-api/querySbomPackages`

- **功能**：查询 SBOM 软件包列表（分组模式），新增按依赖类型过滤
- **变更类型**：新增可选请求参数
- **新增参数**：
  - `dependencyType`（`Integer`，可选）：`0` 仅返回直接依赖包，`1` 仅返回间接依赖包，`3` 仅返回直接/间接依赖包，不传返回全部
- **响应变更**：`statistics` 字段新增 `dependencyType`（`Integer`）
- **向后兼容**：是。不传 `dependencyType` 时行为与变更前完全一致

### 6.2 请求参数变更明细

| 参数 | 类型 | 必填 | 变更 | 说明 |
|------|------|------|------|------|
| `productName` | String | 是 | 无 | 社区名称 |
| `packageName` | String | 否 | 无 | 包名（支持模糊搜索） |
| `isExactly` | Boolean | 否 | 无 | 是否精确匹配 |
| `vulSeverity` | String | 否 | 无 | 漏洞级别过滤 |
| `noLicense` | Boolean | 否 | 无 | 无许可证过滤 |
| `multiLicense` | Boolean | 否 | 无 | 多许可证过滤 |
| `isLegalLicense` | Boolean | 否 | 无 | 合法许可证过滤 |
| `licenseId` | String | 否 | 无 | 许可证 ID 过滤 |
| `dependencyType` | Integer | 否 | **新增** | `0`=直接依赖，`1`=间接依赖，`null`=不过滤 |
| `groupByPackage` | Boolean | 否 | 无 | 是否按包聚合 |
| `page` | Integer | 否 | 无 | 页码 |
| `size` | Integer | 否 | 无 | 每页数量 |

### 6.3 响应字段变更明细

`PackageStatisticsVo` 新增字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| `dependencyType` | Integer | `0`=直接依赖，`1`=间接依赖，`3`=直接/间接依赖。存量数据可能为 `null` |

---

## 7. 安全设计

### 7.1 鉴权

继承原有鉴权逻辑。`/sbom-api/querySbomPackages` 路径由网关统一鉴权，不新增鉴权点。

### 7.2 敏感信息

- 依赖类型字段仅包含 `0` / `1` 枚举值，不涉及用户信息或敏感数据
- 无硬编码凭证、Token、appkey

### 7.3 输入安全

| 输入点 | 风险 | 缓解 |
|--------|------|------|
| `dependencyType` 参数 | 非法值（如 -1、999） | `Integer` 类型直接传参，SQL 仅做等值匹配 `= :dependencyType`，非法值匹配不到结果，不产生注入风险 |

### 7.4 审计日志

无新增日志点。`CollectStatisticsStep` 中 `collectPackageDependencyType` 方法仅做内存赋值，不产生日志。

---

## 8. 测试设计

### 8.1 测试策略

按 `ai_memory.md` 规则，UT 在 Phase 4 阶段补充，覆盖 `CollectStatisticsStepTest`。

### 8.2 测试场景

| 场景 | 输入 | 预期 |
|------|------|------|
| 根包识别 | spdx-json 包含 `SPDXRef-DOCUMENT DESCRIBES A` | A.dependencyType = 0 |
| 直接依赖 | 根包 A DEPENDS_ON B，B 未被其他包 DEPENDS_ON | B.dependencyType = 0 |
| 间接依赖 | 直接依赖 B DEPENDS_ON C | C.dependencyType = 1 |
| 无依赖包 | 包 D 未出现在任何 DEPENDS_ON 关系中 | D.dependencyType = 0 |
| 既直接又间接 | 根包 A DEPENDS_ON B，包 C 也 DEPENDS_ON B | B.dependencyType = 3 |
| 无 DESCRIBES 关系 | spdx-json 无 `SPDXRef-DOCUMENT DESCRIBES` | 所有包由子集 B 判定 |
| 无 DEPENDS_ON 关系 | spdx-json 无 `DEPENDS_ON` | 所有包 dependencyType = 0 |
| 空 relationships | `SbomElementRelationship` 列表为空 | 所有包 dependencyType 正常赋值（子集 B 兜底） |
| 过滤参数 dependencyType=0 | API 传 `dependencyType=0` | 仅返回 dependencyType=0 的包 |
| 过滤参数 dependencyType=null | API 不传 `dependencyType` | 返回所有包（向后兼容） |
| VO 填充 | PackageStatistics.dependencyType = 1 | PackageStatisticsVo.dependencyType = 1 |
