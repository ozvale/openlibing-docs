# 【openlibing-web】SBOM 成分分析页制品列表重构 — 技术设计

## 页面结构

```
CompositionAnalysis/index.vue
├── 版块一：制品信息（productDisplayData 制品列表表格，首屏展示）
│   ├── 表头漏斗筛选：HeaderFilterPopover（多选面板 / License 面板 / 包名搜索插槽）
│   ├── 动态属性列：由 queryProductFilterFields 字段聚合生成，caret 排序
│   ├── 漏洞风险列：总数 + 各级别胶囊徽标（单行省略）
│   └── 解析状态列：tag + tooltip 更新时间
├── 版块二：软件成分（下钻明细，详情展开时自动收起版块一为选中行预览）
├── CategorySearch 汇总条：两版块各一组，含 inline IncludeExcludeFilter
└── 排序：SortPopover 面板排序 + caret 排序（全局单字段）
```

## 新增组件职责

| 组件                               | 职责                                                                                                                    |
| ---------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| `HeaderFilterPopover.vue`          | 表头漏斗弹层；内置多选面板模式（搜索/全选/数量徽标），或通过插槽注入自定义面板（License、包名）；`v-model:visible` 受控 |
| `IncludeExcludePanel.vue`          | 包含/排除三态面板，自 `IncludeExcludeFilter` 拆出以便复用；互斥选择、快捷全选、count 徽标、草稿模式                     |
| `SortPopover.vue`                  | 字段 + 方向的草稿式排序面板                                                                                             |
| `IncludeExcludeFilter.vue`（重构） | 新增 `iconOnly`（表头仅漏斗图标）与 `inline`（无弹层嵌入 CategorySearch）两种形态                                       |

## CategorySearch 扩展

- 新增 `custom` 条件类型：通过 `editor-<field>` 插槽注入自定义编辑器，支持 `hasValue` / `formatValue` 自定义判断与展示
- 条件值类型扩展为 `Record<string, string[]>`（如漏洞级别包含/排除一对值）
- `CategorySearchEditor` 选项支持 count 徽标展示
- `Repos/ColumnFilter.vue` 做值类型收窄兼容，不影响仓库页既有行为

## 新增接口

| 接口                          | 请求 | 入参要点                                                                                  |
| ----------------------------- | ---- | ----------------------------------------------------------------------------------------- |
| `queryProductListMultiFilter` | POST | `filters` 对象（各筛选项值数组）、`pageNum`（从 0 起）、`pageSize`、`sortField`/`sortDir` |
| `queryProductFilterFields`    | POST | 当前筛选条件透传，返回各筛选项可选值 + 数量聚合，驱动动态列与选项列表                     |

## 关键技术决策

| 决策                 | 说明                                                                                                             |
| -------------------- | ---------------------------------------------------------------------------------------------------------------- |
| 筛选查询 GET 改 POST | 全选场景筛选条件可达上千项，POST body 避免 URL 超长 414（`queryProductFields` 系列均走 POST）                    |
| 弹层统一草稿模式     | 所有弹层面板本地维护 draft，点击确定才 emit 更新并触发查询；面板按需挂载，打开时以最新值初始化                   |
| 表头内嵌筛选布局     | 列头采用 `header-with-filter` 布局，漏斗图标 `@click.stop` 防止触发表头排序                                      |
| 解析状态按标签分组   | FAILED / FAILED_FINISH 等标签合并为分组选项，value 逗号拼接展示、提交时按 `expandScanStatusFilterValues` 展开    |
| 表格高度固定         | 首次渲染时按 10 行高度测量一次并固定，防止翻页/列变化时表格跳动                                                  |
| 轮询健壮性           | 解析状态轮询用 setTimeout 链式调度替代 setInterval，活跃标志与 timer 分离，keep-alive activated/deactivated 启停 |
| 版块互斥展开         | 筛选变更自动展开对应版块；下钻时 `productDisplayData` 收起为选中一行预览，保证上下文不丢失                       |
| 动态列排序           | 动态属性列使用原生 caret 排序；与 SortPopover 全局单字段排序互斥同步                                             |

## 影响面分析

- 核心改动集中在 `SbomManagement/CompositionAnalysis/` 目录，公共组件改动仅 `CategorySearch`（向后兼容扩展）与 `Repos/ColumnFilter.vue`（类型收窄兼容）
- `sbomHome.vue` 仅移除单 tab 包装，路由与菜单不变
- API 层仅新增两个 POST 接口定义，既有接口不变
