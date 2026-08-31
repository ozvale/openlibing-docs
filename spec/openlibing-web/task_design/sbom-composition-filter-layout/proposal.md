# 【openlibing-web】SBOM 成分分析筛选栏布局优化

## 需求背景

SBOM 成分分析页（CompositionAnalysis）筛选区在完成包含/排除筛选改造（见 `sbom-composition-filter`）后，筛选条件增多。在浏览器缩放（如 125%）或小屏宽度下，筛选下拉与右侧操作按钮（查询/重置/全量导出）挤在同一行内被压缩变形，按钮被换行挤下移，筛选控件宽度被压缩导致选项文字截断，影响可用性。

本次优化对筛选栏布局进行重构：筛选区与操作按钮区分离，筛选项支持自动换行且不被压缩，操作按钮固定在第一行右上角。

## 功能描述

- 拆分 `.search-params` 为两个子区域：
  - `.search-filters`：筛选条件区，占据剩余宽度（flex: 1），支持 flex-wrap 自动换行
  - `.search-actions`：操作按钮区，固定不换行（flex-shrink: 0），始终位于第一行右上角
- 筛选项（.query-item）设置 `flex-shrink: 0`，缩放时按自身宽度换行而不是被压缩
- 缩小各筛选项宽度以适配换行布局：
  - License：240px → 180px
  - License 数量：240px → 180px
  - License 合规性：240px → 180px
  - 漏洞级别（IncludeExcludeFilter trigger-width）：240px → 180px
  - 依赖类型：240px → 160px
  - package：300px → 240px

## 不做什么

- 不修改任何筛选逻辑、接口入参与数据流（纯样式/布局调整）
- 不修改 IncludeExcludeFilter 组件内部实现（仅调整 trigger-width 传参）
- 不修改后端接口与数据库

## 验收标准

- [x] 125% 缩放下筛选下拉不被压缩，按自身宽度自动换行
- [x] 操作按钮（查询/重置/全量导出）固定在第一行右上角，不随筛选换行下移
- [x] 各筛选项宽度按新规范生效（License/License 数量/License 合规性/漏洞级别 180px，依赖类型 160px，package 240px）
- [x] 100% 缩放下布局正常，筛选功能（防抖、查询、重置、导出）行为不变

## 影响范围

| 文件                                                                         | 操作 | 说明                                         |
| ---------------------------------------------------------------------------- | ---- | -------------------------------------------- |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/index.vue` | 修改 | 筛选区模板结构调整 + 筛选栏样式（+173/-139） |

## 关联提交

- `34b6b3a0` fix(sbom): 优化成分分析筛选栏布局，修复缩放时挤压

## 关联 Issue

- https://gitcode.com/openlibing/openlibing-sbom/issues/65
