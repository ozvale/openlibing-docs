# 新增 /querySbomPackagesMultiFilter 多选过滤查询接口 — 技术设计

## 方案概述

在既有 `querySbomPackages` 查询链上新增一套**独立的批量 DAO 方法**，支持多选过滤；Controller 新增 `POST /querySbomPackagesMultiFilter` 端点，出参映射与分组逻辑复用现有实现。旧接口的 DAO 层完全隔离，不受影响。

```
POST /sbom-api/querySbomPackagesMultiFilter  (@RequestBody QuerySbomPackagesMultiFilterRequest)
   └─ querySbomPackagesMultiFilter
        └─ getPackageInfoByNameForPageMultiFilter / getPackageGroupByNameForPageMultiFilter
             └─ getPackageInfoByNameForPageBatch / getPackagesByGroupPageBatch / countPackageGroupsBatch（新 DAO）
```

### 衍生接口：/querySbomPackagesVulCountSummary（V3 漏洞数量汇总）

与 `querySbomPackagesMultiFilter` 同需求衍生，**入参与 V2 完全一致**（复用 `QuerySbomPackagesMultiFilterRequest`），但对多选过滤条件下匹配的**全部软件包**按各漏洞等级数量做 SUM 汇总求和，不返回包列表、不分页。

```
POST /sbom-api/querySbomPackagesVulCountSummary  (@RequestBody QuerySbomPackagesMultiFilterRequest)
   └─ querySbomPackagesVulCountSummary
        └─ getVulCountSummaryMultiFilter
             └─ sumVulCountByMultiFilter（新 DAO，聚合 SUM）
```

## 架构决策

### 决策 1：多值参数用逗号分隔字符串 + `string_to_array`/`unnest` 展开（不绑 List）

项目历史上踩过 **Hibernate 6 + PostgreSQL JDBC 对 `List<String>` / 数组参数绑定报 `malformed array literal`** 的坑。因此多选参数在 Service 层拼接为逗号分隔字符串，DAO 层用 `string_to_array` / `unnest` 在 SQL 内展开，规避 JDBC 数组绑定缺陷。

```sql
-- includeVulSeverities 包含组：任一选中级别计数>0 即筛选出（组内 OR）
AND (:includeVulSeverities IS NULL OR :includeVulSeverities = ''
  OR (ps.critical_vul_count > 0 AND 'CRITICAL' = ANY(string_to_array(:includeVulSeverities, ',')))
  OR (ps.high_vul_count > 0    AND 'HIGH'    = ANY(string_to_array(:includeVulSeverities, ',')))
  OR (ps.medium_vul_count > 0  AND 'MEDIUM'  = ANY(string_to_array(:includeVulSeverities, ',')))
  OR (ps.low_vul_count > 0     AND 'LOW'     = ANY(string_to_array(:includeVulSeverities, ',')))
  OR (ps.none_vul_count > 0    AND 'NONE'    = ANY(string_to_array(:includeVulSeverities, ',')))
  OR (ps.unknown_vul_count > 0 AND 'UNKNOWN' = ANY(string_to_array(:includeVulSeverities, ','))))
-- excludeVulSeverities 排除组：任一选中级别计数>0 即排除（组内 OR，NOT 包裹）
AND (:excludeVulSeverities IS NULL OR :excludeVulSeverities = ''
  OR NOT (ps.critical_vul_count > 0 AND 'CRITICAL' = ANY(string_to_array(:excludeVulSeverities, ','))
      OR ps.high_vul_count > 0    AND 'HIGH'    = ANY(string_to_array(:excludeVulSeverities, ','))
      OR ps.medium_vul_count > 0  AND 'MEDIUM'  = ANY(string_to_array(:excludeVulSeverities, ','))
      OR ps.low_vul_count > 0     AND 'LOW'     = ANY(string_to_array(:excludeVulSeverities, ','))
      OR ps.none_vul_count > 0    AND 'NONE'    = ANY(string_to_array(:excludeVulSeverities, ','))
      OR ps.unknown_vul_count > 0 AND 'UNKNOWN' = ANY(string_to_array(:excludeVulSeverities, ','))))
-- licenseIds 多选：数组列 overlap
AND (:licenseIds IS NULL OR :licenseIds = '' OR ps.licenses && string_to_array(:licenseIds, ','))
-- licenseCount 单选：数量（枚举名直接匹配）
AND (:licenseCount IS NULL OR (:licenseCount = 'NO_LICENSE' AND ps.license_count = 0)
  OR (:licenseCount = 'SINGLE_LICENSE' AND ps.license_count = 1)
  OR (:licenseCount = 'MULTI_LICENSE' AND ps.license_count > 1))
-- licenseCompliance 单选：成分（枚举名直接匹配）
AND (:licenseCompliance IS NULL OR (:licenseCompliance = 'LEGAL' AND ps.is_legal_license = TRUE)
  OR (:licenseCompliance = 'ILLEGAL' AND ps.is_legal_license = FALSE))
-- dependencyTypes 多选
AND (:dependencyTypes IS NULL OR :dependencyTypes = '' OR dependency_type IN
  (SELECT unnest(string_to_array(:dependencyTypes, ',')::int[])))
```

### 决策 2：漏洞类型拆分为"包含 / 排除"两组，均基于各级别漏洞数量字段判断

原 `vulSeverities`（单值，按最高 severity）拆分为 `includeVulSeverities`（包含）与 `excludeVulSeverities`（排除）两组多选。判断包是否具有某级别漏洞不再依赖 `package_statistics.severity` 单一最高等级字段，而是逐级别用 `critical_vul_count` / `high_vul_count` / `medium_vul_count` / `low_vul_count` / `none_vul_count` / `unknown_vul_count` 计数判空（见决策 1 的 SQL 片段）。

- 包含组：任一选中级别计数 > 0 即命中筛选出（组内 OR）。
- 排除组：任一选中级别计数 > 0 即排除（组内 OR，整体 `NOT` 包裹），单选/多选下语义均正确。

注：曾考虑将排除组改写为"所选类型计数 = 0"的逐项形式，但多选时无论 OR / AND 连接都会在单选或多选场景引入语义错误，故保留 `NOT(组内 OR)` 形式。

### 决策 3：分组查询在 SQL 层分页，service 仅保留结果顺序

- 分组查询 `getPackagesByGroupPageBatch` 在 SQL 层按名称分组 + OFFSET/LIMIT 分页。
- service 用 `LinkedHashMap` 分组（保留插入顺序），并按名称/version 排序后分页返回。

### 决策 4：`isExactly` 布尔字段用 `@JsonProperty("isExactly")` 修复 Jackson 绑定

V2 DTO 字段名 `isExactly` 与 getter `getExactly()`（派生属性名 `exactly`）不一致，JSON 键 `isExactly` 无法被 Jackson 反序列化，导致精确匹配失效。在 getter 上加 `@JsonProperty("isExactly")` 强制映射。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `model/.../enums/LicenseCountFilter.java` | 新增 | NO_LICENSE/SINGLE_LICENSE/MULTI_LICENSE |
| `model/.../enums/LicenseComplianceFilter.java` | 新增 | LEGAL/ILLEGAL |
| `model/.../request/sbom/QuerySbomPackagesMultiFilterRequest.java` | 新增 | 多选请求 DTO |
| `dao/PackageRepository.java` | 修改 | 新增 3 个批量方法（query/count/groupPage） |
| `api/sbom/SbomService.java` | 修改 | 新增 2 个 MultiFilter 接口方法 |
| `service/sbom/impl/SbomServiceImpl.java` | 修改 | 实现多选过滤 + join 辅助方法 |
| `controller/SbomController.java` | 修改 | 新增端点 |
| `test/.../SbomServiceImplTest.java` | 修改 | 补多选用例 |
| `test/.../SbomControllerTest.java` | 修改 | 补新接口用例 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 数组参数绑定 `malformed array literal` | 多值用逗号字符串 + `string_to_array`/`unnest`，不绑定 List |
| 排除组多选语义易错 | 排除组用 `NOT(组内 OR)` 包裹，单选/多选下均正确 |
| 分组查询 `GROUP BY` 后引用未分组列 | 分组查询中漏洞计数用 `MAX(...)` 聚合函数包裹 |

## 跨仓影响

无。仅业务仓 `openlibing-sbom` 内部新增接口，不涉及其他仓接口/契约变化。

---

## V3 接口 /querySbomPackagesVulCountSummary 设计

### 接口定义

`POST /sbom-api/querySbomPackagesVulCountSummary`，`@RequestBody QuerySbomPackagesMultiFilterRequest`（与 V2 同一 DTO）。

### 入参

与 V2 使用同一 DTO：`productName`、`packageName`、`isExactly`、`includeVulSeverities`、`excludeVulSeverities`、`licenseCount`、`licenseCompliance`、`licenseIds`、`dependencyTypes`、`groupByPackage`、`page`/`size`。**但漏洞类型条件（`includeVulSeverities` / `excludeVulSeverities`）在本接口中被排除**——即使请求传入也不参与过滤；仅按其余过滤条件匹配软件包后汇总各级别漏洞数量。`groupByPackage` 与分页参数同样被忽略（聚合不分页、不分组）。

### 出参

`VulCountSummaryVo`：对过滤后全部匹配软件包的各级别漏洞数量求和汇总。

| 字段 | 类型 | 说明 |
|------|------|------|
| `criticalVulCount` | Long | CRITICAL 级别漏洞数量汇总（默认 0） |
| `highVulCount` | Long | HIGH 级别漏洞数量汇总（默认 0） |
| `mediumVulCount` | Long | MEDIUM 级别漏洞数量汇总（默认 0） |
| `lowVulCount` | Long | LOW 级别漏洞数量汇总（默认 0） |
| `noneVulCount` | Long | NONE 级别漏洞数量汇总（默认 0） |
| `unknownVulCount` | Long | UNKNOWN 级别漏洞数量汇总（默认 0） |

### 聚合 SQL 设计

新增 DAO `sumVulCountByMultiFilter`（[PackageRepository.java](file:///d:/projects/openlibing/openlibing-sbom/dao/src/main/java/org/opensourceway/sbom/dao/PackageRepository.java#L457-L503)）：

```sql
SELECT COALESCE(SUM(ps.critical_vul_count), 0),
       COALESCE(SUM(ps.high_vul_count), 0),
       COALESCE(SUM(ps.medium_vul_count), 0),
       COALESCE(SUM(ps.low_vul_count), 0),
       COALESCE(SUM(ps.none_vul_count), 0),
       COALESCE(SUM(ps.unknown_vul_count), 0)
FROM package p LEFT JOIN package_statistics ps ON p.id = ps.package_id
WHERE <过滤条件：与 V2 等价，但排除 include/excludeVulSeverities 漏洞类型片段>
```

- **全量聚合**：`SUM` + `COALESCE` 聚合全部匹配行，返回单行 6 个计数；SQL 无 `LIMIT/OFFSET`，DAO 无 `Pageable` 参数，因此**不受 V2 分页影响**，计算的是过滤条件下的全量漏洞总数。
- **返回结构**：Spring Data 对原生查询返回"行数组"结构（`List<Object[]>`，每行一个 `Object[]` 含 6 列）；service 取 `rows.get(0)` 逐列转 Long。
- **空结果**：`List` 为空时返回全 0 的 `VulCountSummaryVo`（字段默认 `0L`）。

### 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `model/.../vo/sbom/VulCountSummaryVo.java` | 新增 | 出参 VO，6 个漏洞等级 count，默认 0L |
| `dao/PackageRepository.java` | 修改 | 新增 `sumVulCountByMultiFilter` 聚合 DAO |
| `api/sbom/SbomService.java` | 修改 | 新增 `getVulCountSummaryMultiFilter` |
| `service/sbom/impl/SbomServiceImpl.java` | 修改 | 实现聚合 + `toLong` 工具方法 |
| `controller/SbomController.java` | 修改 | 新增 `querySbomPackagesVulCountSummary` 端点 |
| `test/.../SbomServiceImplTest.java` | 修改 | 补聚合用例（命中 / 空结果） |
| `test/.../SbomControllerTest.java` | 修改 | 补新接口用例 |

### 关键实现说明

1. **返回类型为 `List<Object[]>` 而非 `Object[]`**：Spring Data JPA 对原生查询以"行数组"返回，声明 `Object[]` 会导致实际得到 `Object[][]`，service 中 `(Number) sums[i]` 强转时报 `class [Ljava.lang.Object; cannot be cast to class java.lang.Number`。改为 `List<Object[]>` 后取第一行逐列转换。
2. **`toLong` 空值兜底**：`value == null ? 0L : ((Number) value).longValue()`，聚合列 null 转 0。
3. **VO 字段默认 `0L`**：空结果（无匹配包）时直接返回默认全 0 VO，避免前端收到 null 字段。
4. **排除漏洞类型条件**：V3 只按 `productName`/`packageName`/`isExactly`/`licenseCount`/`licenseCompliance`/`licenseIds`/`dependencyTypes` 过滤匹配软件包，`includeVulSeverities`/`excludeVulSeverities` 不参与过滤（DAO 已移除对应 SQL 片段与参数）。