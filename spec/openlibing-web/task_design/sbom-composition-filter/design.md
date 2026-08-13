# 【openlibing-web】SBOM 成分分析筛选区改造 — 技术设计

## 组件设计：IncludeExcludeFilter

基于 el-popover 实现的包含/排除双多选筛选面板。

### Props

| Prop         | 类型                 | 默认     | 说明                                  |
| ------------ | -------------------- | -------- | ------------------------------------- |
| include      | Array                | []       | v-model:include，包含的值数组         |
| exclude      | Array                | []       | v-model:exclude，排除的值数组         |
| options      | Array<{label,value}> | []       | 选项列表                              |
| countMap     | Object               | {}       | 各选项对应的数量，key 为 option.value |
| placeholder  | String               | '请选择' | trigger 占位文本                      |
| title        | String               | '筛选'   | 面板标题                              |
| triggerWidth | Number               | 240      | trigger 宽度                          |
| panelWidth   | Number               | 360      | 面板宽度                              |

### 交互模型

- 三态：none / include / exclude，同一值互斥
- 点级别名：none → include；include/exclude → none
- 点"包含"按钮：当前 include → none；否则 → include
- 点"排除"按钮：当前 exclude → none；否则 → exclude
- 草稿模式：打开面板同步 props 到草稿，勾选只改草稿；点确定才 emit 并触发查询；点清空直接 emit；点外部关闭不 emit
- trigger 摘要：`含:X,Y 排:Z`，有值时显示清除图标（CircleClose），点击清空并查询

### 视觉规范

- trigger：placeholder `#A8ABB2`，有值文字 `#606266`，对齐 el-select
- 面板行：
  - 未选中 hover `#F5F7FA`
  - 包含态背景 `rgba(94,124,224,0.1)`，hover 加深至 `0.18`
  - 排除态背景 `rgba(245,108,108,0.1)`，hover 加深至 `0.18`
- 级别名/数量：包含态 `#5E7CE0` 加粗，排除态 `#F56C6C` 加粗

## 接口接入：querySbomPackagesVulCountSummary

- URL：`POST /sbom-api/querySbomPackagesVulCountSummary`
- 入参：与列表查询 querySbomPackagesMultiFilter 相同的筛选参数（不含分页）
- 出参：
  ```json
  {
    "criticalVulCount": 0,
    "highVulCount": 0,
    "mediumVulCount": 0,
    "lowVulCount": 0,
    "noneVulCount": 0,
    "unknownVulCount": 0
  }
  ```
- 字段映射到漏洞级别 prop：

| 接口字段         | 级别 prop | 显示                         |
| ---------------- | --------- | ---------------------------- |
| criticalVulCount | CRITICAL  | 致命漏洞                     |
| highVulCount     | HIGH      | 高危漏洞                     |
| mediumVulCount   | MEDIUM    | 中危漏洞                     |
| lowVulCount      | LOW       | 低危漏洞                     |
| noneVulCount     | NONE      | 无风险漏洞                   |
| unknownVulCount  | UNKNOWN   | 未知漏洞                     |
| —                | NA        | 不涉及（已移除，不展示数量） |

## 触发规则

| 操作                                                        | 列表查询 | 数量汇总 |
| ----------------------------------------------------------- | -------- | -------- |
| 筛选变化（License/数量/级别/依赖类型/合规性/包名/合并展示） | ✓        | ✓        |
| 翻页（@current-change）                                     | ✓        | ✗        |
| 改 pageSize（@size-change）                                 | ✓        | ✗        |
| 首次加载                                                    | ✓        | ✓        |

## 防抖策略

- 多选 el-select（licenseIds、licenseCount、dependencyTypes）`@change` 绑定 `debouncedFilterChange = _.debounce(handleFilterChange, 400)`
- 单选下拉、IncludeExcludeFilter 确定、packageName 回车/clear → 立即触发 `handleFilterChange`
- 防抖仅合并连续勾选，不影响翻页与单次操作

## 数据流

```
用户勾选 → 草稿更新 → 点确定 → emit update:include/exclude + change
  → index.vue handleFilterChange → queryList(true)
    → querySbomPackagesMultiFilter（列表）
    → querySbomPackagesVulCountSummary（汇总）→ vulCountSummary
      → vulCountMap (computed) → IncludeExcludeFilter :count-map
```

## queryInfo 字段变化

| 字段                 | 改造前         | 改造后                                                 |
| -------------------- | -------------- | ------------------------------------------------------ |
| vulSeverities        | string（单选） | 移除，拆为 includeVulSeverities / excludeVulSeverities |
| includeVulSeverities | —              | []（多选数组）                                         |
| excludeVulSeverities | —              | []（多选数组）                                         |
| licenseCount         | string（单选） | []（多选数组，字段名不变）                             |
| licenseCompliance    | string（多选） | string（改回单选）                                     |
