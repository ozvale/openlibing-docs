# Design: perf-web-lcp-no-data

## Context

web-openlibing（Vue 3 + Element Plus，多入口 monorepo 应用）存在三类拖慢首屏 LCP 的因素，均在当前分支 `perf-web-lcp-no-data` 上已完成实现，本文档记录其技术决策：

1. **空态图片成为 LCP 元素**：表格空数据加载期间，Element Plus 表格立即渲染 `#empty` 插槽中的 Empty 空态组件，其中的 no-data.png 是独立网络请求（且 majun、sca 模块各重复携带一份 20KB 副本），图片请求晚于文本内容，成为 LCP 元素并拉长 LCP 时间。
2. **CVE 管理页全量同步加载**：cveManager.vue 同步 import 全部 4 个页签组件（cveAllview / cveConfigure / cvePerception / cveRepair），非默认页签的 JS 也参与首屏解析执行。
3. **加载提示叠加**：各页面表格同时挂 `v-loading` 遮罩；空数据首屏时遮罩覆盖在空态图上，视觉冗余且不减少 LCP 候选元素。

参考实现：仓库内 Repos 页已有"表格骨架行"成熟方案，本次复用其视觉与动画规范。

## Goals / Non-Goals

**Goals:**

- 空数据首屏加载期间消除空态图片这一 LCP 候选元素，用纯 CSS 骨架行替代（零网络请求）
- 空态图片资源去重并压缩（20KB × 4 份 → 4KB × 1 份）
- 非默认页签组件移出首屏同步加载链路
- 保证翻页/筛选已有数据时的加载体验与优化前一致，不引入行为回归

**Non-Goals:**

- 不做构建产物分析工具引入、路由级代码分割等更大范围的首屏优化
- 不修改全局样式表（main.css 的 devui-icomoon `font-display` 覆盖曾尝试后回退，见 Risks）
- 不改动后端接口与数据加载时序

## Decisions

### D1: 骨架行以"注入占位数据行 + CSS 选择器"实现，而非独立骨架组件

向表格数据源注入 `__isSkeleton` 标记的占位行，通过 `row-class-name` / `cell-class-name` 定位，在单元格上用 `::after` 画灰条动画；单元格文字 `visibility: hidden`。

- **理由**：复用 Element Plus 表格自身的渲染与布局，骨架行视觉与真实行完全对齐（列宽、行高一致），且实现集中在组件内一个样式块；独立骨架组件需要重复模拟表头/列布局，维护成本高。
- **备选**：`v-loading` + 自定义骨架 DOM、或 `el-skeleton` 嵌套 —— 均无法精确对齐表格列布局，弃用。
- **启用条件收敛为单一计算属性**：`loading && 数据为空`。数据非空时不注入占位行，`displayData` 直接透传原数据，保证翻页/筛选路径零改动。

### D2: `loading` 作为可选 prop 由外部页面显式传入

`myTable.vue` 新增 `loading` prop（默认 `false`）。页面侧同时将 `v-loading` 条件化为 `v-loading="loading && list.length > 0"`。

- **理由**：表格组件无法可靠感知外部请求状态；可选 prop 保证未传 prop 的既有调用方（全仓其他表格）行为完全不变，可渐进接入。
- **备选**：表格内部拦截空数据渲染 —— 侵入 Element Plus 的 empty 插槽时机，且无法区分"首屏加载"与"查询结果为空"，弃用。

### D3: 页面级骨架用统一的请求包装函数兜底

用户管理页（user.vue）将三类用户列表请求（user / system / black）的调用收敛到 `fetchUsersData(fetchFn)`，`usersLoading` 初始为 `true`（首屏即骨架），`finally` 中结束加载。

- **理由**：该页有 3 个请求入口（初始、搜索、翻页），逐一设置 loading 易遗漏；`finally` 兜底保证请求异常时骨架必然消失。顺带将删除逻辑的三元分支重构为 delMap，并修复 black 类型缺分支的隐患。
- **风险提示**：该提交混入了删除逻辑重构（非性能必需），评审时按独立改动看待。

### D4: 非默认页签用 `defineAsyncComponent` 而非路由级懒加载

cveManager.vue 的 cveConfigure / cvePerception / cveRepair 改为 `defineAsyncComponent(() => import(...))`，默认页签 cveAllview 保持同步 import。

- **理由**：页签切换在同一页面内完成，不走路由；`defineAsyncComponent` 粒度恰好匹配"首次激活才加载"的诉求，改动仅限组件注册处。Vite 自动对动态 import 做代码分割。
- **备选**：整个 cveManager 路由懒加载 —— 已是路由级 import，继续拆收益低且影响面大，弃用。

### D5: 空态图片收敛到单一公共路径并压缩

`majun`、`sca` 模块的 Empty 组件及 echart 空态统一改引 `@/assets/images/common/no-data.png`（压缩 20837B → 4020B），删除三处副本。

- **理由**：Vite 对静态 import 的同一路径资源只打包一份；压缩对 4KB 级别的示意图无可见质量损失。

## Risks / Trade-offs

- [骨架态与真实数据切换瞬间的闪烁] → 骨架行仅在"数据为空"时注入，数据到达后一次性替换为真实行；灰条动画与 Repos 页方案一致，视觉过渡可接受
- [异步页签首次点击的加载等待] → Vite 分包体积小（单页签组件），等待在百毫秒级；如需消除可后续加页签级预加载，暂不做
- [全局字体覆盖回退留下性能尾巴] → devui-icomoon `font-display: swap` 覆盖曾实现（移至 @import 之后、符合 CSS 规范），最终决定回退以保持全局样式表不动；LCP 主要收益来自异步页签，此项收益让渡
- [`:deep` 选择器依赖 Element Plus 单元格类名结构] → 选择器限定在 `.is-skeleton-loading` 作用域内且仅命中 `__isSkeleton` 占位行，组件升级时受影响面可控
- [user.vue 提交混入删除逻辑重构] → 行为等价重构（delMap 补齐 black 分支），已在 D3 中说明

## Migration Plan

本变更随分支 `perf-web-lcp-no-data` 直接合入，无数据迁移。回滚策略：所有改动均为前端组件/资源层，revert 对应提交即可；未传 `loading` prop 的表格调用方不受任何影响。

## Open Questions

无。
