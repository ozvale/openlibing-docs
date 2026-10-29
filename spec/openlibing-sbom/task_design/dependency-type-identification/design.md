# dependency-type-identification — 技术设计

## 方案概述
在 SBOM 统计阶段（`CollectStatisticsStep`）从已持久化的 `SbomElementRelationship` 表中解析每个软件包的依赖类型（直接/间接），存入 `PackageStatistics` 新字段 `dependencyType`；同时在包查询接口与 SQL 层新增 `dependencyType` 可选过滤参数，向后兼容。

## 架构决策

### 决策 1：字段命名
- Java 字段：`dependencyType`（`Integer`，可为 null，便于未来扩展未知态）
- 数据库列名：`dependency_type`（修正 Issue 中的 `dependy_type` 拼写笔误）
- 取值：`0` = 直接依赖，`1` = 间接依赖，`3` = 直接/间接依赖

### 决策 2：解析算法
基于已持久化的 `SbomElementRelationship` 表（`SpdxReader` 已将 spdx-json 中所有 relationships 持久化），在 `CollectStatisticsStep.collectPackageStatistics` 中：

1. **识别根包集合**：遍历 `sbom.getSbomElementRelationships()`，找出 `relationshipType = DESCRIBES` 且 `elementId = "SPDXRef-DOCUMENT"` 的记录，其 `relatedElementId` 即根包 spdxId
2. **计算直接依赖集合 directDepSet**：
   - 子集 A = 根包通过 `DEPENDS_ON` 直接依赖的包（`elementId ∈ rootSet` 且 `relationshipType = DEPENDS_ON` → `relatedElementId` 入 A）
   - 子集 B = 没被任何包通过 `DEPENDS_ON` 依赖的包（即未作为任何 `DEPENDS_ON` 关系的 `relatedElementId` 出现的包）
   - `directDepSet = A ∪ B`
3. **赋值**：`pkg.spdxId ∈ directDepSpdxIdSet && pkg.spdxId ∈ dependedSpdxIdSet` → `dependencyType = 3`；`pkg.spdxId ∈ directDepSpdxIdSet` → `dependencyType = 0`；否则 → `dependencyType = 1`
4. **直接/间接依赖（3）**：包同时出现在 directSet 和 dependedSet 中

根包本身未被任何包 `DEPENDS_ON` 依赖（`DESCRIBES` 不属于 `DEPENDS_ON`），按规则 B 自动归为直接依赖（0），无需特殊处理。

### 决策 3：依赖关系来源
按 Issue 描述，依赖关系来源字段包括 `DEPENDS_ON` 和 `RUNTIME_DEPENDENCY_OF`。但分析后：
- `RUNTIME_DEPENDENCY_OF` 表示"X 是 Y 的运行时依赖"，方向与 `DEPENDS_ON` 相反（`X RUNTIME_DEPENDENCY_OF Y` 等价于 `Y DEPENDS_ON X`）
- 现有 `runtimeDepCount` 统计已覆盖运行时依赖计数（`CollectStatisticsStep.getPackageRuntimeDepSpdxIdList`）
- 依赖类型识别只关注 `DEPENDS_ON` 关系构建依赖树，避免方向歧义与重复统计

### 决策 4：过滤参数设计
- `QuerySbomPackagesRequest` 新增 `dependencyType`（`Integer`，可空）
- 3 个 SQL 方法新增过滤条件：`(:dependencyType IS NULL OR dependency_type = :dependencyType)`
- 不传时行为与变更前完全一致（向后兼容）
- 沿用项目现有 SQL 风格（`LIKE` 用 `\` 转义 + `ESCAPE '\\'`；布尔参数显式 `CAST` 已在现有 SQL 中体现，本次 `dependencyType` 是 `Integer` 无需 CAST）

## 涉及文件
| 文件 | 操作 | 说明 |
|------|------|------|
| `model/.../entity/PackageStatistics.java` | 修改 | 新增 `dependencyType` 字段 + Javadoc + getter/setter |
| `model/.../vo/sbom/PackageStatisticsVo.java` | 修改 | 新增 `dependencyType` 字段 + getter/setter + `fromPackage` 填充 |
| `model/.../request/sbom/QuerySbomPackagesRequest.java` | 修改 | 新增 `dependencyType` 字段 + getter/setter + toString |
| `dao/.../PackageRepository.java` | 修改 | 3 个 SQL 方法新增 `dependencyType` 参数 + 过滤条件 |
| `batch/.../step/CollectStatisticsStep.java` | 修改 | 新增 `collectPackageDependencyType` 方法 + 在 `collectPackageStatistics` 调用 |
| `sbom-web/.../service/sbom/impl/SbomServiceImpl.java` | 修改 | `getPackageInfoByNameForPage` / `getPackageGroupByNameForPage` 透传 `dependencyType` |
| `sbom-web/.../controller/SbomController.java` | 修改 | `querySbomPackagesDeprecated` 新增 `dependencyType` `@RequestParam` |

## 风险 & 缓解
- **风险 1**：根包识别失败（spdx-json 没有 `SPDXRef-DOCUMENT DESCRIBES` 关系）
  - 缓解：若根包集合为空，则子集 A 为空，所有包按"没被任何包 DEPENDS_ON 依赖"规则（子集 B）判断，逻辑自洽
- **风险 2**：循环依赖导致解析死循环
  - 缓解：本算法不递归遍历依赖链，只计算两层关系（根包→直接依赖、被依赖关系集合），不存在循环风险
- **风险 3**：Hibernate auto DDL 在生产环境未开启
  - 缓解：需确认生产环境 `ddl-auto` 配置；若需手动迁移，由运维补充 `ALTER TABLE package_statistics ADD COLUMN dependency_type INTEGER` 语句（不在本次代码改动范围）

## 跨仓影响
无。改动仅限 `openlibing-sbom` 仓。
