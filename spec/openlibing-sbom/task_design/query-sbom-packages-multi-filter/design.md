# 新增 /querySbomPackagesMultiFilter 多选过滤+排序查询接口 — 技术设计

## 方案概述

在既有 `querySbomPackages` 查询链上新增一套**独立的批量 DAO 方法**，支持多选过滤与排序；Controller 新增 `POST /querySbomPackagesMultiFilter` 端点，出参映射与分组逻辑复用现有实现。旧接口的 DAO 层完全隔离，不受影响。

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
-- vulSeverities 多选：组内 OR
AND (:vulSeverities IS NULL OR :vulSeverities = '' OR ps.severity IN
  (SELECT unnest(string_to_array(:vulSeverities, ','))))
-- licenseIds 多选：数组列 overlap
AND (:licenseIds IS NULL OR :licenseIds = '' OR ps.licenses && string_to_array(:licenseIds, ','))
-- licenseFilters 多选：枚举 code 逐项命中
AND (:licenseFilters IS NULL OR :licenseFilters = '' OR EXISTS (
  SELECT 1 FROM unnest(string_to_array(:licenseFilters, ',')::int[]) AS f
  WHERE (f=1 AND ps.license_count=0) OR (f=2 AND ps.license_count=1)
     OR (f=3 AND ps.license_count>1) OR (f=4 AND ps.is_legal_license=TRUE)
     OR (f=5 AND ps.is_legal_license=FALSE)))
-- dependencyTypes 多选
AND (:dependencyTypes IS NULL OR :dependencyTypes = '' OR dependency_type IN
  (SELECT unnest(string_to_array(:dependencyTypes, ',')::int[])))
```

### 决策 2：排序字段用白名单枚举 + CASE 表达式，方向用乘数实现（防 SQL 注入）

`sortField` 映射到 `package_statistics` 的漏洞数量列，用 `CASE` 表达式而非直接拼接用户输入；`sortDir` 方向用 `×(-1)` 在单个 ORDER BY 表达式中实现正/倒序。未指定排序字段时 CASE 全为 NULL，自动回退默认名称排序。

```sql
ORDER BY (CASE WHEN :sortField='critical' THEN ps.critical_vul_count
          ... ELSE NULL END)
  * (CASE WHEN :sortDir='DESC' THEN -1 ELSE 1 END) ASC,
  CASE WHEN p.name LIKE '.%' THEN 2 ELSE 1 END ASC, p.name COLLATE "C" ASC
```

### 决策 3：分组查询排序在 SQL 层完成，service 仅保留结果顺序

- 内层子查询 `GROUP BY name,version` 后按 `MAX(漏洞数量)` 排序 + OFFSET/LIMIT 决定哪些组上页。
- 外层查询按单个包漏洞数量排序返回，保证返回顺序即排序顺序。
- service 用 `LinkedHashMap` 分组（保留插入顺序），**仅当未指定 `sortField` 时才按名称重排**，否则保留 DAO 排序结果。

### 决策 4：`isExactly` 布尔字段用 `@JsonProperty("isExactly")` 修复 Jackson 绑定

V2 DTO 字段名 `isExactly` 与 getter `getExactly()`（派生属性名 `exactly`）不一致，JSON 键 `isExactly` 无法被 Jackson 反序列化，导致精确匹配失效。在 getter 上加 `@JsonProperty("isExactly")` 强制映射。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `model/.../enums/LicenseFilterEnum.java` | 新增 | NO_LICENSE/SINGLE_LICENSE/MULTI_LICENSE/LEGAL/ILLEGAL，code 1-5 |
| `model/.../enums/PackageSortField.java` | 新增 | CRITICAL/HIGH/MEDIUM/LOW/NONE/UNKNOWN_VUL_COUNT |
| `model/.../request/sbom/QuerySbomPackagesMultiFilterRequest.java` | 新增 | 多选请求 DTO |
| `dao/PackageRepository.java` | 修改 | 新增 3 个批量方法（query/count/groupPage） |
| `api/sbom/SbomService.java` | 修改 | 新增 2 个 MultiFilter 接口方法 |
| `service/sbom/impl/SbomServiceImpl.java` | 修改 | 实现多选/排序 + join 辅助方法 |
| `controller/SbomController.java` | 修改 | 新增端点 |
| `test/.../SbomServiceImplTest.java` | 修改 | 补多选/排序用例 |
| `test/.../SbomControllerTest.java` | 修改 | 补新接口用例 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 数组参数绑定 `malformed array literal` | 多值用逗号字符串 + `string_to_array`/`unnest`，不绑定 List |
| SQL 注入（排序字段） | `sortField` 白名单枚举 + CASE 表达式 |
| 分组排序被 service 覆盖 | service 仅在 `sortField==null` 时按名称重排 |
| 原 `noLicense`+`multiLicense` 同传为 AND 语义 | 新接口 `licenseFilters` 多选为 OR，前端不同时勾选，标注语义差异 |
| 分组查询 `GROUP BY` 后引用未分组列 | 排序键用 `MAX(...)` 聚合函数包裹 |

## 跨仓影响

无。仅业务仓 `openlibing-sbom` 内部新增接口，不涉及其他仓接口/契约变化。