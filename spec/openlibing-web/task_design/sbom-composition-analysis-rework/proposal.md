# 【openlibing-web】SBOM 成分分析页制品列表重构

## 需求背景

SBOM 成分分析页（CompositionAnalysis）此前的首屏为动态属性表单 + 确认/重置按钮，筛选能力分散在页面顶部固定筛选栏中，存在以下问题：

- 动态属性表单交互成本高，用户无法直接浏览制品列表与整体风险概况
- 筛选项集中在页面顶部，离数据表距离远；License/package/漏洞级别等筛选项数量增加后顶部拥挤（见 `sbom-composition-filter`、`sbom-composition-filter-layout` 两轮改造的延续问题）
- 制品表格缺少动态属性列、解析状态、漏洞风险分布等关键信息的一屏呈现
- 筛选条件全选场景下 GET 请求 URL 超长导致 414

本次对成分分析页进行整体重构：以"制品列表"为第一屏，筛选能力下沉到表头内嵌漏斗弹层与 CategorySearch 汇总条，新增制品多条件筛选分页查询接口对接。

## 功能描述

### 制品列表首屏

- 原"制品信息"动态表单版块替换为制品列表表格，列包括：
  - 制品名称（含包名表头漏斗筛选：关键字 + 精准查询）
  - 动态属性列（由 `queryProductFilterFields` 返回字段聚合生成，支持原生 caret 排序）
  - 解析状态（tag 展示，tooltip 悬浮显示解析更新时间）
  - 依赖包数量
  - License 数量（去重提示）
  - 漏洞风险（总数 + 各级别胶囊徽标，横向单行省略）
  - 详情入口
- 支持分页（10/20/30）与表头 caret 排序；表格高度按首屏 10 行固定，防切页跳动

### 筛选体系

- 双版块（制品信息 / 软件成分）各自维护一组 CategorySearch 多条件汇总条
- 可筛选列头内嵌漏斗弹层（`HeaderFilterPopover`）：多选面板 + 搜索 + 数量徽标 + 全选
- License IDs/数量/合规性三项筛选合并为 License 列头一个面板
- 漏洞级别包含/排除筛选同时支持列头图标入口（`iconOnly`）与 CategorySearch 内联（`inline`）两种形态
- 筛选字段选项与数量由 `queryProductFilterFields` 按当前筛选条件聚合返回，任何条件变更都重新查询

### 排序与版块交互

- 新增 `SortPopover` 面板排序（漏洞总数/各级别、License 数量/合规性），与 caret 排序共存，全局单字段排序
- 双版块互斥展开/收起：筛选变更自动展开对应版块；详情下钻后制品表收起为选中一行预览并展开成分数据
- 保留解析状态轮询与漏洞刷新完成通知（含"刷新页面数据"按钮）

### 新增接口

| 接口                                   | 方法 | 用途                                                         |
| -------------------------------------- | ---- | ------------------------------------------------------------ |
| `sbom-api/queryProductListMultiFilter` | POST | 制品多条件筛选分页查询（filters 对象、sortField/sortDir）    |
| `sbom-api/queryProductFilterFields`    | POST | 按当前筛选条件聚合各筛选项可选值与数量，驱动动态列与选项列表 |

## 不做什么

- 不修改后端接口实现与数据库（仅前端对接已有新接口）
- 不改动软件成分下钻明细的业务逻辑
- 不调整 SBOM 首页（sbomHome）除移除单 tab 包装外的其他结构

## 验收标准

- [ ] 制品列表首屏正常渲染，动态属性列/解析状态/漏洞风险/依赖包数量/License 数量展示正确
- [ ] 表头漏斗筛选（多选/搜索/全选/数量徽标）可用，License 面板、包名搜索、漏洞级别包含排除生效
- [ ] CategorySearch 汇总条双版块各自生效，值格式化与清除正确
- [ ] 面板排序与 caret 排序共存，全局单字段排序正确
- [ ] 全选筛选条件后查询不再出现 414
- [ ] 双版块互斥展开/收起、下钻收起预览、筛选自动展开行为正确
- [ ] 解析状态轮询与刷新通知在页面切换/keep-alive 场景下正常启停

## 影响范围

| 文件                                                                                                  | 操作 | 说明                                                 |
| ----------------------------------------------------------------------------------------------------- | ---- | ---------------------------------------------------- |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/index.vue`                          | 重构 | 制品列表首屏 + 双版块互斥展开 + 轮询（+2400 行左右） |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/HeaderFilterPopover.vue`  | 新增 | 表头漏斗弹层组件                                     |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/IncludeExcludePanel.vue`  | 新增 | 包含/排除三态面板（自 IncludeExcludeFilter 拆出）    |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/SortPopover.vue`          | 新增 | 字段排序面板                                         |
| `apps/web-openlibing/src/views/SbomManagement/CompositionAnalysis/component/IncludeExcludeFilter.vue` | 重构 | 新增 iconOnly / inline 两种形态                      |
| `apps/web-openlibing/src/components/CategorySearch/CategorySearch.vue`                                | 修改 | 新增 custom 类型与插槽机制                           |
| `apps/web-openlibing/src/components/CategorySearch/CategorySearchEditor.vue`                          | 修改 | 选项支持数量徽标                                     |
| `apps/web-openlibing/src/components/CategorySearch/types.ts`                                          | 修改 | 值类型扩展为 Record<string, string[]>                |
| `apps/web-openlibing/src/views/Repos/components/ColumnFilter.vue`                                     | 修改 | 值类型收窄兼容                                       |
| `apps/web-openlibing/src/views/SbomManagement/sbomHome.vue`                                           | 修改 | 移除单 tab 包装                                      |
| `apps/web-openlibing/src/api/sbom/api.ts` / `url.ts`                                                  | 修改 | 新增两个接口定义                                     |

## 关联提交

- 分支 `dev-chenning-20260923-sbom`（含 `b97d7333` 制品列表首屏重建、`0754538d` 表头筛选、`7550e2a4` License 面板、`ff2e56d4` language/purl 列与表头多选、`e2c493db` GET 改 POST 避免 414 等）

## 关联 Issue

- https://gitcode.com/openlibing/openlibing-sbom/issues/75
