# 【openlibing-web】SBOM 成分分析筛选移入表头并支持排序 — 技术设计

> 跨仓影响：本需求同时改动 `openlibing-web`（主，前端交互）与 `openlibing-sbom`
> （排序契约与 SQL）。spec 归档在 openlibing-web 名下，openlibing-sbom 侧改动在本文件说明。

## 一、前端设计（openlibing-web）

### 1.1 组件结构

`CompositionAnalysis/index.vue` 单页改造 + 新增 1 个轻量组件：

```
CompositionAnalysis/
├── index.vue                        # 移除 search-filters；列头插槽 + sort-change
├── component/
│   ├── IncludeExcludeFilter.vue     # 漏洞级别三态面板（复用，新增 icon-only 触发形态）
│   └── HeaderFilterPopover.vue      # 新增：表头漏斗触发器 + popover 容器
```

### 1.2 HeaderFilterPopover（新组件）

职责：表头内的漏斗图标触发器，统一高亮/弹出交互，不承载具体筛选控件。

- Props：`active`（是否命中筛选/排序值，控制图标高亮）、`popperWidth`。
- 插槽：默认插槽放筛选面板内容（el-select / IncludeExcludeFilter / el-input / 开关等）。
- 结构：`el-popover(trigger=click, placement=bottom-start)` + reference 为漏斗图标
  （`@element-plus/icons-vue#Filter`，与用户抓取的 svg 漏斗同形）。
- 图标状态：`active` 时 `#409eff`，否则 `#a8abb2`；hover 提示列名。
- 注意：popover 内的 el-select / el-input 点击事件不要冒泡导致 popover 关闭
  （popover trigger=click 时需 `popper-options` 或内容区阻止冒泡，实现时验证）。

### 1.3 各列表头插槽映射

| 列                                | header 插槽内容                                                                                                                                                                                                            |
| --------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 软件包名称                        | HeaderFilterPopover：el-input(packageName, enter/clear 触发查询) + el-switch(isExactly) + el-switch(groupByPackage, @change=handleGroupByChange，带 tooltip「合并列表中软件包名称和版本的重复项」)                         |
| 版本                              | 无                                                                                                                                                                                                                         |
| 依赖类型                          | HeaderFilterPopover：多选 el-select(dependencyTypes, @change=debouncedFilterChange)                                                                                                                                        |
| 漏洞风险数值                      | HeaderFilterPopover：IncludeExcludeFilter(icon-only) + 排序区（el-radio：级别 6 项复用 `sortFieldList` 映射 + 升/降序）                                                                                                    |
| License                           | HeaderFilterPopover：el-select(licenseIds 多选, 防抖) + el-select(licenseCount 多选, 防抖) + el-select(licenseCompliance 单选) + 排序区（el-radio：License数量/LICENSE_COUNT、License合规性/LICENSE_COMPLIANCE + 升/降序） |
| 编号 / Supplier / 来源信息 / 更多 | 无                                                                                                                                                                                                                         |

- 依赖类型表头文案不变；面板内选项文案沿用现状（直接依赖/间接依赖/直接/间接依赖）。
- IncludeExcludeFilter 增加 `iconOnly` 形态：reference 渲染为漏斗图标而非 180px trigger，
  面板/确认/清空逻辑复用（`change` 事件仍回调 `handleFilterChange`）。

### 1.4 排序交互

- 软件包名称、依赖类型列：`sortable="custom"`，标准 `caret-wrapper` 升降序；
  `@sort-change` 回调统一处理（`prop` → 后端 sortField 映射，`order=null` → 清除排序）。
- 漏洞风险数值、License 列：面板内排序选择器（字段 + 方向），选中即生效；
  列头显示排序方向指示箭头（↑/↓ 小图标）；面板内提供「取消排序」。
- 排序状态变化统一回调：重置 `pageInfo.pageNum = 1` → `queryList(true)`（刷新漏洞汇总）。
- 排序字段映射（前端 → 后端）：

  | 前端 prop            | sortField                                                                                                   |
  | -------------------- | ----------------------------------------------------------------------------------------------------------- |
  | name                 | NAME                                                                                                        |
  | dependencyType       | DEPENDENCY_TYPE                                                                                             |
  | vulCount（级别选择） | CRITICAL_VUL_COUNT / HIGH_VUL_COUNT / MEDIUM_VUL_COUNT / LOW_VUL_COUNT / NONE_VUL_COUNT / UNKNOWN_VUL_COUNT |
  | licenseCount         | LICENSE_COUNT                                                                                               |
  | licenseCompliance    | LICENSE_COMPLIANCE                                                                                          |

  sortDir：`asc` / `desc`。

### 1.5 查询参数与状态

- `queryInfo` 字段不变；`queryList()` 组参不变，仅新增：
  `if (sortState.field) { param.sortField = ...; param.sortDir = ...; }`
- `sortState = reactive({ field: '', dir: '' })`。
- 漏洞数量汇总 `querySbomPackagesVulCountSummary` 入参不带排序字段（后端忽略亦可）。

### 1.6 样式

- 表头漏斗图标与列名间距 4px；popover 宽度按内容 320–420px。
- 移除 `.search-filters` 相关样式；`.search-actions` 改为靠右排列。
- 列头排序指示箭头复用 el-table caret 样式或简单 el-icon。

## 二、后端设计（openlibing-sbom）

### 2.1 契约变化

`QuerySbomPackagesMultiFilterRequest` 新增：

```java
/** 排序字段白名单枚举名，null 表示默认排序。 */
private String sortField;
/** 排序方向：asc / desc，sortField 非空时必填，默认 desc。 */
private String sortDir;
```

白名单（新增枚举 `PackageSortField`，放在 model 模块 enums 包）：

```
NAME, DEPENDENCY_TYPE, LICENSE_COUNT, LICENSE_COMPLIANCE,
CRITICAL_VUL_COUNT, HIGH_VUL_COUNT, MEDIUM_VUL_COUNT,
LOW_VUL_COUNT, NONE_VUL_COUNT, UNKNOWN_VUL_COUNT
```

非法值 → 抛 `OpenSourceException`（400 语义），不进入 SQL。

### 2.2 SQL 动态排序（native @Query 无法参数化列名，采用 CASE 展开方案）

`getPackageInfoByNameForPageBatch`（非分组）ORDER BY 改为：

```sql
ORDER BY
  -- 文本类字段（NAME）两个方向
  CASE WHEN :sortField = 'NAME'  AND :sortDir = 'asc'  THEN p.name END ASC NULLS LAST,
  CASE WHEN :sortField = 'NAME'  AND :sortDir = 'desc' THEN p.name END DESC NULLS LAST,
  -- 数值类字段两个方向（critical/high/medium/low/none/unknown_vul_count、ps.license_count）
  CASE WHEN :sortField = 'CRITICAL_VUL_COUNT' AND :sortDir = 'asc'  THEN ps.critical_vul_count END ASC NULLS LAST,
  ...（其余 5 个 vul count + LICENSE_COUNT 同型）
  -- 整型/布尔字段
  CASE WHEN :sortField = 'DEPENDENCY_TYPE'   AND :sortDir = 'asc'  THEN p.dependency_type END ASC NULLS LAST,
  CASE WHEN :sortField = 'LICENSE_COMPLIANCE' AND :sortDir = 'asc' THEN ps.is_legal_license END ASC NULLS LAST,
  ...（desc 同型）
  -- 默认排序保持现状（隐藏 . 开头包名）
  CASE WHEN p.name LIKE '.%' THEN 2 ELSE 1 END ASC,
  p.name COLLATE "C" ASC
```

要点：

- 同方向同一 CASE 内所有分支必须同类型 → 按「文本 / 数值(bigint) / 整型(int)/布尔」分块，
  每块 × 2 方向，`NULLS LAST` 保证 null（未命中字段）不参与排序。
- countQuery 不含 ORDER BY，无需改动。
- `sortDir` 入参统一小写（service 层规范化）。

`getPackagesByGroupPageBatch`（分组）子查询改为：

```sql
SELECT COALESCE(p2.name,''), COALESCE(p2.version,''), <聚合别名...>
FROM package p2 LEFT JOIN package_statistics ps2 ...
GROUP BY name, version
ORDER BY <动态聚合 CASE 块同上（引用聚合列）>, 默认排序
OFFSET ... FETCH ...
```

聚合口径（与用户确认的排序语义一致）：

| sortField          | 组内聚合                                                |
| ------------------ | ------------------------------------------------------- |
| 漏洞各级别         | `SUM(ps2.<level>_vul_count)`                            |
| LICENSE_COUNT      | `MAX(ps2.license_count)`                                |
| LICENSE_COMPLIANCE | `MIN(ps2.is_legal_license)`（组内含非认证即视为非认证） |
| DEPENDENCY_TYPE    | `MAX(ps2.dependency_type)`（直接/间接 = 2 最大）        |
| NAME               | `COALESCE(p2.name,'')`                                  |

### 2.3 Service 层

- `SbomServiceImpl#getPackageInfoByNameForPageMultiFilter`：规范化 sortDir（null/非法→desc）、
  sortField 白名单校验后透传；无排序字段时传 null（SQL 走默认分支，行为与现状一致）。
- `getPackageGroupByNameForPageMultiFilter`：
  - 无排序字段：保留现有 Java 侧 `groups.sort(name, version)`（行为不变）。
  - 有排序字段：按聚合值在 Java 侧对 `groups` 排序（与 SQL 子查询排序口径一致），
    保证分组页内顺序与翻页窗口一致；并列时按 name、version 兜底。

### 2.4 影响面与兼容性

- `querySbomPackagesVulCountSummary` 不受影响（不排序）。
- 旧调用方（不传 sortField/sortDir）行为完全不变。
- 涉及文件：
  - `model/.../QuerySbomPackagesMultiFilterRequest.java`（+2 字段 + getter/setter + toString）
  - `model/.../enums/PackageSortField.java`（新增）
  - `dao/.../PackageRepository.java`（2 个 @Query 的 ORDER BY / 子查询改造）
  - `sbom-web/.../SbomServiceImpl.java`（透传 + 分组 Java 排序）
  - 测试：`SbomServiceImplTest`（排序透传、白名单、分组聚合排序）、`SbomControllerTest`（请求 DTO 新字段）

## 三、接口契约变化汇总

`POST /sbom-api/querySbomPackagesMultiFilter` 请求体新增两个**可选**字段：

| 字段      | 类型   | 说明                                |
| --------- | ------ | ----------------------------------- |
| sortField | string | 枚举白名单，见 2.1；不传 = 默认排序 |
| sortDir   | string | `asc` / `desc`，默认 `desc`         |

前后端字段名/取值以此为准，PR 描述与 design.md 同步。

## 四、测试与验证

| 层         | 方式                                                                                       |
| ---------- | ------------------------------------------------------------------------------------------ |
| 后端单测   | `SbomServiceImplTest` / `SbomControllerTest` 新增用例（scripts/run-mvn.py）                |
| 前端       | pnpm build（web-openlibing）+ 现有 vitest 不回归                                           |
| pre-commit | 两仓对改动文件执行 `pre-commit run --files <files>`                                        |
| 测试环境   | 用户手动合并到 beta/gamma 源仓分支部署，gamma 页面逐项验证（筛选/排序/翻页/合并展示/导出） |
