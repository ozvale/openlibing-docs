## Context

### 合法合规模块路由与视图结构

`openlibing-web` 的合法合规模块（sca）下有三个核心路由，由 `menu.ts` 定义：

- `componentAnalysis` — 版本扫描（列表 + 详情共用路由，通过组件内 `isDetail` 状态切换）
- `PRComponentAnalysis` — PR 扫描（列表 + 详情共用路由，通过组件内 `isDetail` 状态切换）
- `queryExportRecord` — 导出查询页（独立路由，也可作为弹窗内嵌）

父级 `sca` 路由 redirect 到 `componentAnalysis`。三个子路由的 `meta.title` 均为「合法合规」，`hideInMenu: true`（仅左侧导航栏隐藏，tabbar 仍显示）。

### 导出触发与跳转链路

1. 用户在 `componentAnalysis` / `PRComponentAnalysis` 的列表或详情页点击「导出」按钮
2. 触发 `exportTipComponent.vue` 弹窗，显示「Excel导出提交成功」
3. 用户点击弹窗内「查看导出记录」按钮，调用 `jumpToQueryRec()` → `this.$router.push({ name: 'queryExportRecord' })`
4. 跳转到导出查询页，展示导出记录列表

### 问题根因

导出查询页缺少返回路径，且：

1. **无来源上下文**：`jumpToQueryRec()` 跳转时未记录用户从哪个页面（列表/详情）来，返回时无法精准回到来源
2. **详情上下文丢失**：合法合规列表与详情共用路由，详情状态（选中的 git 仓库、PR 通过/未通过、平台等）保存在组件实例的 `data()` 中，路由切换后组件销毁，详情上下文丢失
3. **无效来源场景**：用户切换项目、刷新浏览器、在导出查询页切换其他菜单后再回来，都应该回退到合法合规默认列表，而非误用旧来源

### 相关代码位置

- `stores/app.ts:330-380` — `scaExportFrom` / `scaPendingRestore` 状态定义与方法
- `stores/app.ts:setupRouter` — `router.afterEach` 钩子注册
- `stores/app.ts:projectInfo watcher` — 项目切换清理
- `queryExportRecord/index.vue:handleBack()` — 返回按钮逻辑
- `exportTipComponent.vue:jumpToQueryRec()` — 来源上下文捕获
- `componentAnalysis/index.vue:provide()` — 版本扫描上下文暴露
- `PRComponentAnalysis/components/openSourceCompliance/index.vue:provide() + mounted()` — PR 扫描上下文暴露与恢复
- `PRComponentAnalysis/index.vue:created() + mounted()` — PR 详情预置与兜底清理

**已确认产品约束：**

1. 返回按钮仅独立路由页面显示，弹窗内嵌时不显示
2. 切换项目 → 返回到合法合规默认列表
3. 刷新浏览器 → 返回到合法合规默认列表（`scaExportFrom` 为内存态，刷新即丢失）
4. 在导出查询页切换其他菜单后再回来点返回 → 返回到合法合规默认列表
5. 点击合法合规菜单（左侧导航栏或 tabbar）→ 直接打开合法合规列表（由 sca 父路由 redirect 到 componentAnalysis 保证，本次不修改）
6. 返回按钮只需考虑上一步页面是点击导出的场景，其他场景回退到默认列表
7. 合法合规列表和对应详情共用路由，返回详情需恢复详情上下文

## Goals / Non-Goals

**Goals:**

- 导出查询页新增返回按钮，位于列表内容上方左对齐
- 点击返回按钮精准回到上一次导出的来源页面（列表或详情）
- 返回详情时恢复进入详情时的上下文参数，避免详情页无数据
- 切换项目、刷新浏览器、切换其他菜单后再回来等无效来源场景，回退到合法合规默认列表
- 返回按钮仅在独立路由页面显示，弹窗内嵌时不显示
- 独立路由页面增加白色背景与 20px 内边距，弹窗内嵌样式不变

**Non-Goals:**

- 不修改 tabbar 持久化机制（已知遗留：刷新后点 tabbar 可能跳到导出查询页，不在本次范围）
- 不修改 `exportTipComponent.vue` 的弹窗 UI 与交互
- 不修改导出查询页的列表数据加载逻辑
- 不为其他模块（如代码检查）的导出功能添加返回按钮
- 不修改后端导出接口
- 不修改路由定义（不新增路由、不改 meta）

## Decisions

### D1：双状态设计（scaExportFrom + scaPendingRestore）

**选择：** 使用两个独立的内存态状态，而非单一状态。

- `scaExportFrom`：用户点击导出时记录的来源上下文（路由名、是否详情、详情参数快照、projectId）。在导出查询页存续期间保留，离开导出查询页时清空。
- `scaPendingRestore`：用户点击返回按钮后、目标页面 mount 消费前暂存的待恢复详情快照。目标页面 mount 时消费并清空。

**理由：**

- `scaExportFrom` 用于「判断返回目标」，需要在导出查询页存续期间持续存在；`scaPendingRestore` 用于「传递恢复数据」，只需在目标页面 mount 前短暂存在
- 职责分离：`scaExportFrom` 的清空时机（离开导出查询页）与 `scaPendingRestore` 的清空时机（目标页面 mount）不同
- 避免单一状态在清空时丢失返回目标信息

**备选：** 单一 `scaExportContext` 状态 — 清空时机难以统一，且需要在返回按钮点击后立即清空，但目标页面 mount 时仍需读取，时序耦合严重。

### D2：内存态而非持久化

**选择：** `scaExportFrom` 与 `scaPendingRestore` 均为 Pinia 内存态，不配置 `persist`。

**理由：**

- 产品约束：刷新浏览器后返回按钮应回退到合法合规默认列表。内存态刷新即丢失，天然满足此约束
- 避免持久化导致的脏状态残留（如用户关闭浏览器后重新打开，旧来源不应保留）
- 与 `app.projectInfo` 的持久化策略一致（项目信息持久化，但导出上下文不持久化）

**备选：** sessionStorage 持久化 — 刷新后仍保留来源，需额外逻辑判断「刷新」场景，复杂度高且不符合产品约束。

### D3：router.afterEach 清空 scaExportFrom

**选择：** 在 `stores/app.ts` 的 `setupRouter` 中注册 `router.afterEach`，检测到从 `queryExportRecord` 离开时清空 `scaExportFrom`。

**理由：**

- 产品约束：在导出查询页切换其他菜单后再回来点返回，应回退到默认列表
- `afterEach` 能捕获所有路由离开场景（点左侧菜单、点 tabbar、浏览器后退、`router.push`）
- 清空 `scaExportFrom` 后，下次回到导出查询页时 `handleBack()` 检测到空来源，自然走默认列表分支

**备选：** 在 `queryExportRecord` 的 `beforeRouteLeave` 中清空 — 需修改组件，且 `beforeRouteLeave` 在路由被强制跳转时可能不触发；`afterEach` 更可靠。

### D4：provide/inject 传递导出上下文

**选择：** `componentAnalysis/index.vue` 与 `openSourceCompliance/index.vue` 通过 `provide()` 暴露一个返回当前页面上下文的 getter 函数，`exportTipComponent.vue` 通过 `inject` 调用 getter 获取快照。

**理由：**

- `exportTipComponent.vue` 是深层子组件，直接访问父级 `data()` 需要层层 props 传递或 `$parent` 链，侵入性大
- `provide` 的 getter 函数在 `inject` 调用时才执行，能拿到调用时刻的最新状态（如用户在详情页切换了 git 仓库后再点导出）
- getter 返回快照对象（深拷贝关键参数），避免后续父组件状态变化影响已捕获的快照

**备选：**

- 直接 `provide` 状态对象而非 getter — 状态变化时 inject 拿到的是响应式引用，可能在 inject 时刻与导出时刻之间被修改
- 使用 Vuex/Pinia 存储详情上下文 — 过度设计，详情上下文是页面局部状态，不应提升到全局

### D5：created 预置 isDetail + mounted 兜底清理

**选择：** `PRComponentAnalysis/index.vue` 在 `created()` 检测 `scaPendingRestore`，若需恢复详情则预置 `isDetail = true`；在 `mounted()` 兜底清理 `scaPendingRestore`。

**理由：**

- Vue 生命周期：`created` → 父组件 `mounted` → 子组件 `mounted` → 父组件 `mounted` 完成。子组件 `openSourceCompliance.mounted()` 先于父组件 `mounted()` 执行
- `created` 预置 `isDetail` 确保首次渲染就是详情视图，避免列表→详情闪烁
- 子组件 `mounted` 消费 `scaPendingRestore` 后调用 `clearScaPendingRestore`；父组件 `mounted` 兜底清理，防止子组件未消费时 `scaPendingRestore` 残留导致下次进入误设 `isDetail`

**备选：** 仅在子组件 `mounted` 恢复 — 首次渲染时 `isDetail` 为 `false`（列表视图），子组件 `mounted` 后再切换为详情，会有闪烁。

### D6：getDetail 参数顺序调整（checkedProp 先于 chooseGitObject）

**选择：** 在 `openSourceCompliance/index.vue` 的 `getDetail()` 中，先设置 `checkedProp`（映射到 `chooseProp`），再设置 `chooseGitObject`。

**理由：**

- `openSourceDetail.vue` 的 `watch(chooseGitObject, { deep: true })` 触发时读取 `this.chooseProp` 决定 `passStatus`
- 若先设 `chooseGitObject`，watch 触发时 `chooseProp` 还是旧值，导致 `passStatus` 错误，详情页查询参数不对、无数据
- 先设 `checkedProp` 确保 watch 触发时 `chooseProp` 已是正确值

### D7：inDialog prop 区分渲染场景

**选择：** `queryExportRecord/index.vue` 新增 `inDialog` prop（默认 `false`），`isPageMode` computed 返回 `!this.inDialog`，返回按钮与白色背景样式仅在 `isPageMode` 为 `true` 时生效。`layout/index.vue` 弹窗内 `<queryExportRecord :in-dialog="true" />`。

**理由：**

- 同一组件被两种场景复用：独立路由页面（显示返回按钮）与弹窗内嵌（不显示返回按钮）
- 依赖 `this.$route.name` 不可靠：在导出查询页本身打开弹窗时，路由 name 仍是 `queryExportRecord`，会误判
- prop 显式传递，调用方明确意图，无歧义

**备选：**

- 依赖 `this.$route.name === 'queryExportRecord'` — 弹窗在导出查询页打开时失效
- 拆分为两个组件 — 代码重复，维护成本高

### D8：项目切换清理

**选择：** `stores/app.ts` 的 `projectInfo` watcher 检测到 `projectId` 变化时，清空 `scaExportFrom` 与 `scaPendingRestore`。

**理由：**

- 产品约束：切换项目后返回按钮应回退到合法合规默认列表
- `scaExportFrom` 中的 `projectId` 是来源项目的快照，切换项目后旧来源失效
- `scaPendingRestore` 同理，目标页面 mount 时会读取错误的 projectId

## Risks / Trade-offs

| 风险                                                                 | 缓解                                                                                                                                                       |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `scaExportFrom` 为内存态，浏览器刷新后丢失                           | 符合产品约束：刷新后返回按钮回退到默认列表                                                                                                                 |
| `router.afterEach` 清空 `scaExportFrom` 可能影响其他逻辑             | `afterEach` 仅在从 `queryExportRecord` 离开时触发清空，其他路由不受影响                                                                                    |
| `scaPendingRestore` 残留导致下次进入误设 `isDetail`                  | 父组件 `mounted` 兜底清理；子组件 `mounted` 正常消费后立即清空                                                                                             |
| `provide/inject` getter 返回快照后，父组件状态变化导致快照与实际不符 | getter 在 `jumpToQueryRec` 调用时刻执行，捕获的是导出瞬间的状态；用户返回后若状态已变（如其他 tab 修改了数据），详情页基于快照重新查询，与首次进入行为一致 |
| `inDialog` prop 默认 `false`，调用方忘记传递                         | 仅 `layout/index.vue` 一处弹窗调用，已显式传递 `:in-dialog="true"`；其他路由页面不传则默认 `false`，符合预期                                               |
| tabbar 遗留问题：刷新后点 tabbar「合法合规」可能跳到导出查询页       | 不在本次范围，需后续给 `queryExportRecord` 路由 meta 加 `hideInTab: true` 或调整 sca 子路由 `fullPathKey`                                                  |
| `getDetail` 参数顺序调整可能影响其他调用方                           | `getDetail` 仅在 `openSourceCompliance/index.vue` 内部与 `mounted` 恢复时调用，顺序调整对调用方透明                                                        |

## Migration Plan

纯前端发布，无数据迁移。部署后：

1. 用户在合法合规列表/详情点击导出 → 弹窗提示成功
2. 用户点击「查看导出记录」→ 跳转导出查询页，`scaExportFrom` 记录来源上下文
3. 用户查看导出记录后点击「返回」按钮
   - 若来源有效（同项目、未切换菜单、未刷新）→ 返回到来源页面（列表或详情），详情恢复上下文
   - 若来源无效（切换项目、刷新、切换过其他菜单）→ 返回到合法合规默认列表
4. 弹窗内打开导出查询页时，返回按钮不显示，样式与原有弹窗一致

**回滚：**

- 移除 `queryExportRecord/index.vue` 的返回按钮、`handleBack`、`inDialog` prop、`isPageMode` computed、白色背景样式
- 移除 `stores/app.ts` 的 `scaExportFrom` / `scaPendingRestore` 状态、方法、`afterEach` 钩子、项目切换清理
- 移除 `exportTipComponent.vue` 的 `inject` 与来源捕获逻辑
- 移除 `componentAnalysis/index.vue` 与 `openSourceCompliance/index.vue` 的 `provide` 与 `mounted` 恢复逻辑
- 移除 `PRComponentAnalysis/index.vue` 的 `created` 预置与 `mounted` 兜底清理
- 移除 `layout/index.vue` 的 `:in-dialog="true"` prop

## Open Questions

（无 — 本次为前端导航能力增强，变更范围清晰，产品约束已明确，技术方案已验证。）
