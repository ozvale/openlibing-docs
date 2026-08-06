# 新增 /querySbomPackagesMultiFilter 多选过滤查询接口 — 技术设计

## 方案概述

在既有 `querySbomPackages` 查询链上新增一套**独立的批量 DAO 方法**，支持多选过滤；Controller 新增 `POST /querySbomPackagesMultiFilter` 端点，出参映射与分组逻辑复用现有实现。旧接口的 DAO 层完全隔离，不受影响。

```
POST /sbom-api/querySbomPackagesMultiFilter  (@RequestBody QuerySbomPackagesMultiFilterRequest)
   └─ querySbomPackagesMultiFilter
        └─ getPackageInfoByNameForPageMultiFilter / getPackageGroupByNameForPageMultiFilter
             └─ getPackageInfoByNameForPageBatch / getPackagesByGroupPageBatch / countPackageGroupsBatch（新 DAO）
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