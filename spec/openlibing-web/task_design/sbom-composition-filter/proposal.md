# 【openlibing-web】SBOM 成分分析筛选区改造

## 需求背景

SBOM 成分分析页（CompositionAnalysis）筛选区原仅支持单选漏洞级别、License 数量等字段，无法表达"只看高危+致命"或"排除未知漏洞"等包含/排除语义。同时筛选过程缺乏各级别漏洞数量反馈，用户难以判断筛选范围。本次改造引入包含/排除双多选面板、漏洞数量汇总、多选防抖等能力，提升筛选体验与数据可读性。

## 功能描述

- 漏洞级别筛选：从单选 el-select 改为 IncludeExcludeFilter 组件（el-popover 面板），支持"包含"与"排除"两组多选，同一级别三态互斥（不筛/包含/排除）
- 漏洞数量汇总：筛选变化时调用 querySbomPackagesVulCountSummary 接口（入参与列表查询相同），返回各级别漏洞数量，展示在面板对应级别名后（括号包裹）
- licenseCount 下拉改为多选（字段名不变，值改数组）
- licenseCompliance 筛选改为单选
- 移除漏洞级别"不涉及(NA)"选项
- 多选下拉（License、License 数量、依赖类型）@change 防抖 400ms，避免连续勾选每选一项就发一次请求
- IncludeExcludeFilter trigger 视觉对齐 el-select（placeholder 浅灰 #A8ABB2、有值文字 #606266、有清除图标）
- 面板内选项交互：点级别名切换选中、点包含/排除按钮可再次点击取消、未选中行 hover 浅灰、选中行 hover 加深背景
- 导出按钮文案由"导出"改为"全量导出"

## 不做什么

- 不修改后端接口契约（querySbomPackagesVulCountSummary 为已有后端接口，前端仅接入）
- 不修改数据库 schema
- 不改造排序逻辑（排序已迁移至表格头部 ColumnFilter，本次不涉及）
- 不修改导出弹窗逻辑（仅改按钮文案）

## 验收标准

- [x] 漏洞级别筛选支持包含/排除两组多选，同一级别三态互斥
- [x] 面板内各级别后展示对应漏洞数量（括号包裹），数量随筛选变化刷新
- [x] 首次进入页面即展示漏洞数量汇总
- [x] 多选下拉连续勾选时只发一次请求（400ms 防抖）
- [x] 翻页、改 pageSize 不触发数量汇总接口
- [x] licenseCount 支持多选，值传数组
- [x] licenseCompliance 为单选
- [x] 漏洞级别"不涉及"选项已移除
- [x] IncludeExcludeFilter trigger 视觉与 el-select 一致（placeholder/有值文字色）
- [x] 面板内点已选中按钮可取消选中
- [x] trigger 有值时显示清除图标，点击清空并查询
- [x] 导出按钮文案为"全量导出"

## 影响范围

| 文件                                                                                                  | 操作     | 说明                                                 |
| ----------------------------------------------------------------------------------------------------- | -------- | ---------------------------------------------------- |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/index.vue`                          | 修改     | 筛选区模板、queryInfo、queryList、防抖、汇总接口调用 |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/IncludeExcludeFilter.vue` | **新增** | 包含/排除双多选筛选面板组件                          |
| `apps/web-openlibing/src/api/sbom/api.ts`                                                             | 修改     | 新增 querySbomPackagesVulCountSummary 请求函数       |
| `apps/web-openlibing/src/api/sbom/url.ts`                                                             | 修改     | 新增 QUERY_SBOM_PACKAGES_VUL_COUNT_SUMMARY 常量      |

## 关联提交

- `d39a7877` fix(sbom): licenseCompliance 筛选改为单选
- `26cae664` refactor(sbom): 移除漏洞级别筛选的"不涉及"选项
- `e7e072a3` feat(sbom): 新增 querySbomPackagesVulCountSummary 接口定义
- `68be75a5` feat(sbom): 漏洞级别筛选补充数量汇总展示与多选防抖
- `46aa4646` feat(sbom): IncludeExcludeFilter 交互优化与导出文案调整
- `3613f524` feat(sbom): licenseCount 改多选与 IncludeExcludeFilter 视觉对齐
