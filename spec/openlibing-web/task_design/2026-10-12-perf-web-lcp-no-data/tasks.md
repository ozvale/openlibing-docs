# Tasks: perf-web-lcp-no-data

> 说明：本变更对应的代码实现已在分支 `perf-web-lcp-no-data`（7 个提交，基准 54b51882）上完成。以下任务以"核对实现与规格一致 + 补齐验证"为主。

## 1. 核对表格首屏骨架（对应 Requirement: 空数据加载期间渲染首屏骨架行）

- [x] 1.1 `myTable.vue` 新增 `loading` prop（默认 false），`showSkeleton` / `displayData` 计算属性按"loading 且数据为空"注入占位行，行数取分页大小或 10
- [x] 1.2 骨架行样式块限定在 `.is-skeleton-loading` 作用域，`::after` 灰条动画 + 单元格文字隐藏，正常数据行不受影响
- [x] 1.3 CVE 各页面（cveOperationLog / cveRepair / cveData / cveStock 等 14 处）`v-loading` 条件化为 `loading && list.length > 0`，并同步传入 `:loading`
- [x] 1.4 验证：首次进入各接入页面显示骨架行动画、无空态图片请求；翻页/筛选已有数据时仅显示遮罩；加载结束数据为空回落 Empty 空态

## 2. 核对骨架行不可交互（对应 Requirement: 骨架占位行不可交互）

- [x] 2.1 `checkSelectable` 排除 `__isSkeleton` 行，骨架行复选框不可选中
- [x] 2.2 验证：骨架态下复选框不可勾选、行点击无响应；数据返回后真实行交互正常

## 3. 核对加载状态异常兜底（对应 Requirement: 加载状态异常兜底）

- [x] 3.1 user.vue 增加 `fetchUsersData(fetchFn)` 统一请求入口，`finally` 兜底结束 `usersLoading`，初始即为 true；搜索/翻页路径统一走该入口
- [x] 3.2 验证：模拟接口失败（网络断开或返回异常），骨架行消失且页面不卡死，可重新发起查询

## 4. 核对空态图片资源统一（对应 Requirement: 空态图片资源统一来源）

- [x] 4.1 majun/Empty.vue、majun/echart.vue、sca/Empty.vue 统一改引 `@/assets/images/common/no-data.png`
- [x] 4.2 删除 `src/assets/sca/no-data.png`、`src/majun/src/assets/images/no-data.png`、`src/sca/src/assets/no-data.png` 三处副本；公共图片压缩至约 4KB
- [x] 4.3 验证：构建产物中仅含一份 no-data.png；各模块空态展示正常无 404

## 5. 核对页签异步加载（对应 Requirement: 页面内非默认页签异步加载）

- [x] 5.1 cveManager.vue 中 cveConfigure / cvePerception / cveRepair 改为 `defineAsyncComponent` 动态 import，cveAllview 保持同步
- [x] 5.2 验证：首屏网络面板确认非默认页签分包不随首屏加载；首次点击各页签正常渲染、二次切换无重复请求

## 6. 验证与收尾

- [x] 6.1 本地构建通过（`pnpm build`），无新增构建警告/错误
- [x] 6.2 用 Lighthouse / Performance 面板对比优化前后首屏 LCP，记录收益数据
- [x] 6.3 `openspec validate --strict` 通过后归档本变更
