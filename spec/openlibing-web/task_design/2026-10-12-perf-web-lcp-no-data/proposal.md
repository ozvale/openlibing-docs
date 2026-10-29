# Proposal: perf-web-lcp-no-data

## Why

web-openlibing 前端首屏 LCP（Largest Contentful Paint）偏大：表格空数据加载期间立即渲染的空态图片（no-data.png，20KB × 多份重复）在数据返回前成为 LCP 元素，导致 LCP 时间被图片网络请求拖慢；同时 CVE 管理页所有页签组件同步打包加载，进一步推迟了首屏可渲染内容。本变更对当前分支 `perf-web-lcp-no-data` 的性能优化内容进行规格化沉淀。

## What Changes

- **表格首屏骨架屏**：`myTable.vue` 新增 `loading` prop；当"外部加载中 且 数据列表为空"时，表格渲染纯 CSS 占位骨架行（灰条动画），替代立即渲染的 Empty 空态图，避免空态图片成为 LCP 元素；数据已有（翻页/筛选/刷新）时骨架不启用，仍由外部 `v-loading` 遮罩提示，行为与旧版一致。
- **页面级骨架屏（用户管理）**：权限管理的用户列表页采用同一骨架方案，`usersLoading` 初始即为 true（首屏即骨架），请求以 `fetchUsersData` 统一入口包装并在 `finally` 兜底结束加载，防止请求异常时骨架卡死。
- **空态图片资源整合**：`majun`、`sca` 等模块各自重复携带的 no-data.png（20KB）统一收敛为 `@/assets/images/common/no-data.png` 并压缩至 4KB，构建产物不再重复包含多份相同图片。
- **CVE 非默认页签异步加载**：CVE 管理页（cveManager.vue）中非默认展示的页签组件（cveConfigure / cvePerception / cveRepair）改为 `defineAsyncComponent` 懒加载，默认页签（cveAllview）保持同步加载，缩短首屏 JS 解析与渲染时间。
- **加载遮罩条件化**：CVE 各页面表格的 `v-loading` 增加"已有数据"前置条件（`v-loading="loading && list.length > 0"`），空数据加载时由骨架行承担加载提示，避免遮罩与骨架叠加。

## Capabilities

### New Capabilities

- `web-lcp-optimization`: web-openlibing 首屏加载性能优化的行为规格，覆盖三方面：① 列表/表格空数据加载期间的首屏骨架渲染策略（何时显示骨架、骨架行为、异常兜底）；② 空态图片资源的统一来源约束；③ 页面内非默认页签组件的异步加载策略。

### Modified Capabilities

（无 — `openspec/specs/` 中现有能力均与前端首屏加载行为无关，本变更不修改它们的需求。）

## Impact

- **代码**：`apps/web-openlibing/src/components/myTable.vue`、`src/views/authorityManagement/user.vue`、`src/views/cve/`（cveManager.vue 及 14 个 cve 页面的 v-loading 条件）、`src/majun/src/components/Empty.vue`、`src/majun/src/components/echart.vue`、`src/sca/src/components/Empty.vue`
- **资源**：删除 `src/assets/sca/no-data.png`、`src/majun/src/assets/images/no-data.png`、`src/sca/src/assets/no-data.png`，统一使用 `src/assets/images/common/no-data.png`（压缩至约 4KB）
- **用户可感知行为**：空数据表格首次加载显示骨架动画（替代空白表格/空态图）；CVE 非默认页签首次点击时组件按需加载（可能有一次性的轻微加载等待）；空态图片整体加载更快
- **兼容性**：`myTable.vue` 新增 `loading` prop 默认值为 `false`，未传该 prop 的现有调用方行为完全不变（无破坏性变更）
