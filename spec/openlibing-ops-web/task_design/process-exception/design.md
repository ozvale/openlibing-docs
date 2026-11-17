# 版本可用度备案（process-exception）— 技术设计

> 目标仓：`openlibing-ops-web` ｜ 模块：`src/views/process-exception/`
> 阅读顺序：先看「方案概述 → 目录与组件职责 → 数据流」，再按页面查看「页面明细」，最后看「样式规范 / 风险 / 自测清单」。

## 1. 方案概述

在 `openlibing-ops-web` 新增独立视图模块，用「单路由 + 页签容器」承载五个业务页面，避免为每个页签新增路由和权限判断：

- 页面组织：`/process-exception/:projectId?` 只注册一条路由，容器内部用 `defineAsyncComponent` + `KeepAlive` 切换五个页面。
- 数据入口：四个列表页共用同一套筛选字段配置、参数转换和 `base-table` 骨架。
- 权限口径：所有写操作按钮（编辑/撤回/删除/同意/拒绝/转移）完全由后端 `detail.actions` / `row.actions` 驱动。
- 交互形态：详情、新建/编辑、路径编辑使用侧滑抽屉；同意/拒绝、转移使用 480px 轻量弹窗；确认类操作使用 `ElMessageBox.confirm`。
- 状态管理：组织/项目/流水线/场景字典与待办总数集中在 `useExceptionStore`，按项目缓存，路径变更后主动失效。

## 2. 目录与组件职责

```text
src/
├── api/exception.ts                          # 22 个 /filing 接口函数
├── types/exception.ts                        # 平台/状态/路径/申请单/列表/actions 类型
├── stores/exception-store.ts                 # 待办总数 + 组织/项目/流水线/场景缓存
├── router/routes/modules/process-exception.ts
└── views/process-exception/
    ├── process-exception.vue                 # 页签容器 + 共享抽屉 + provide 上下文
    ├── config.ts                             # 字段配置、字段变体、参数转换、列配置
    ├── constants.ts                          # 枚举映射、流程节点配色、平台映射
    ├── detail-context.ts                     # InjectionKey + useExceptionDetail
    ├── utils.ts                              # 展示格式化与详情链接
    ├── hooks/use-exception-list.ts           # 列表查询/刷新/KeepAlive 生命周期
    ├── style.less                            # 分页、状态徽标、表格最小高度
    ├── my-applications.vue
    ├── pending-approvals.vue
    ├── approval-history.vue
    ├── exception-search.vue
    ├── pattern-config.vue
    └── components/
        ├── exception-search-form.vue
        ├── new-application-drawer.vue
        ├── exception-detail-drawer.vue
        ├── exception-flow-panel.vue
        ├── flow-scrollbar.vue
        ├── exception-opinion-dialog.vue
        ├── exception-transfer-dialog.vue
        ├── exception-status-badge.vue
        └── path-edit-drawer.vue
```

### 2.1 文件职责与对外 API

| 文件                            | 类型     | 对外 API / 关键导出                                                                                                                                                                                                                                                |
| ------------------------------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `process-exception.vue`         | 容器页面 | 无 props；提供 `EXCEPTION_DETAIL_KEY`；挂载时拉待办总数与项目字典                                                                                                                                                                                                  |
| `config.ts`                     | 纯配置   | `EXCEPTION_SEARCH_FIELDS`、`EXCEPTION_QUERY_SEARCH_FIELDS`、`EXCEPTION_PENDING_SEARCH_FIELDS`、`toExceptionPageReq`、`useExceptionPageReq`、4 组列配置                                                                                                             |
| `constants.ts`                  | 纯常量   | `EXCEPTION_STATUS_MAP/OPTIONS`、`EXCEPTION_OWNER_TYPE_MAP`、`EXCEPTION_ASSIGN_TYPE_MAP/OPTIONS`、`EXCEPTION_ACTION_MAP`、`EXCEPTION_MY_RESULT_MAP`、`EXCEPTION_NODE_STATUS_MAP`、`EXCEPTION_FLOW_NODE_STYLE`、`EXCEPTION_FLOW_LABEL_STYLE`、`PLATFORM_MAP/OPTIONS` |
| `detail-context.ts`             | 上下文   | `EXCEPTION_DETAIL_KEY`、`useExceptionDetail()`                                                                                                                                                                                                                     |
| `utils.ts`                      | 纯函数   | `formatPlatformUser`、`toPipelineOption`、`getProcessExceptionUrl`                                                                                                                                                                                                 |
| `hooks/use-exception-list.ts`   | 组合式   | `useExceptionList(tableRef, onRefresh?)` → `{ queryParams, initParams, handleSearch, handleReset }`                                                                                                                                                                |
| `exception-search-form.vue`     | 表单组件 | props `fields`；`v-model` 表单模型；emits `search` / `reset`；slot `extra`                                                                                                                                                                                         |
| `new-application-drawer.vue`    | 抽屉     | props `projectId?` / `pipelineId?`；emits `success`；expose `open(id?)`                                                                                                                                                                                            |
| `exception-detail-drawer.vue`   | 抽屉     | emits `refresh` / `edit`；expose `open(id)`                                                                                                                                                                                                                        |
| `exception-flow-panel.vue`      | 展示组件 | props `detail`                                                                                                                                                                                                                                                     |
| `flow-scrollbar.vue`            | 展示组件 | props `viewport?` / `dots` / `activeKey?`                                                                                                                                                                                                                          |
| `exception-opinion-dialog.vue`  | 弹窗     | model `visible`；props `mode` / `loading`；emits `confirm(opinion)`                                                                                                                                                                                                |
| `exception-transfer-dialog.vue` | 弹窗     | model `visible`；props `applicationId`；emits `success`                                                                                                                                                                                                            |
| `exception-status-badge.vue`    | 展示组件 | props `status?`                                                                                                                                                                                                                                                    |
| `path-edit-drawer.vue`          | 抽屉     | model `visible`；props `pathRow?`；emits `success`                                                                                                                                                                                                                 |

## 3. 路由与页面容器

### 3.1 路由

```ts
{
  name: 'ProcessException',
  path: '/process-exception/:projectId?',
  component: () => import('@/views/process-exception/process-exception.vue')
}
```

- 可选 `projectId` 作为列表默认项目与新申请的项目上下文。
- 支持 query：`?tab=<value>` 指定初始页签；`?id=<applicationId>` 直接打开详情（打开后从 URL 移除 `id`，避免刷新重复打开）。
- 路由未声明 `meta.title` / `meta.uemId`，菜单与埋点由上层路由/布局决定。

### 3.2 页签配置

| 顺序 | label            | value               | 组件                    | 权限              | 主要请求                    |
| ---- | ---------------- | ------------------- | ----------------------- | ----------------- | --------------------------- |
| 1    | 例外决策路径配置 | `pattern-config`    | `pattern-config.vue`    | `ops_filing_path` | `paths/page`                |
| 2    | 我的申请         | `my-applications`   | `my-applications.vue`   | 登录即可          | `applications/page`         |
| 3    | 待我审批         | `pending-approvals` | `pending-approvals.vue` | 登录即可          | `applications/pending/page` |
| 4    | 历史审批         | `approval-history`  | `approval-history.vue`  | 登录即可          | `applications/history/page` |
| 5    | 例外查询         | `exception-search`  | `exception-search.vue`  | 登录即可          | `applications/all/page`     |

- 默认页签 `my-applications`。
- 权限过滤：`userStore.user.permissions` 不含 `ops_filing_path` 时，`pattern-config` 不进入 `tabList`。
- 若 `route.query.tab` 指向无权限页签，`activeTab` 回退到默认页签；权限异步变化时 `watch(tabList)` 再兜底一次。

### 3.3 容器状态与生命周期

| 状态                                       | 类型             | 说明                                        |
| ------------------------------------------ | ---------------- | ------------------------------------------- |
| `activeTab`                                | `ref<string>`    | 当前页签，初值取 `route.query.tab` 或默认值 |
| `activeComponent`                          | `computed`       | 从 `tabList` 取当前页签组件                 |
| `detailRefreshToken`                       | `ref<number>`    | 详情动作成功后的刷新信号                    |
| `detailDrawerRef` / `applicationDrawerRef` | `useTemplateRef` | 两个共享抽屉实例                            |

挂载流程：

1. `exceptionStore.refreshPendingTotal()` 拉待办总数（`page=1, pageSize=1` 取 `total`）。
2. `exceptionStore.fetchProjects()` 预加载项目字典（全量）。
3. 若 `route.query.id` 为字符串，调用 `openDetail(id)`。
4. `openDetail` 内若仍存在 `route.query.id`，用 `router.replace` 清除该参数。

容器同时承载两个共享抽屉：

```vue
<exception-detail-drawer
  ref="detailDrawerRef"
  @refresh="handleDetailRefresh"
  @edit="openApplication"
/>
<new-application-drawer
  ref="applicationDrawerRef"
  @success="handleDetailRefresh"
/>
```

### 3.4 provide 上下文

```ts
interface ExceptionDetailContext {
  openDetail: (id: string) => void;
  openApplication: (id?: string) => void;
  refreshToken: Ref<number>;
}
```

- 子页面通过 `useExceptionDetail()` 注入，不需要逐层 emit。
- 详情内「编辑」通过 `emit('edit', id)` 交给容器，再调用 `openApplication(id)`。

## 4. 数据流与刷新时序

### 4.1 查看详情

1. 列表点击申请编号 → `openDetail(row.id)`。
2. 详情抽屉 `open(id)`：清空旧 `detail`、关闭子弹窗、打开抽屉、请求 `GET /filing/applications/{id}`。
3. 渲染流程面板、基本信息、审批记录、跟踪进展；底部按钮按 `detail.actions` 显隐。

### 4.2 详情动作后刷新

```text
详情动作成功
  → 重新拉取详情（approve / reject / transfer / withdraw）
  → emit('refresh')
  → 容器 detailRefreshToken++
  → useExceptionList 侦听 token
  → 激活中的列表 handleSearch() / onRefresh()
```

- 删除成功：直接关闭抽屉，再 `emit('refresh')`。
- 待我审批页额外在 `onRefresh` 中刷新待办总数，保证角标同步。

### 4.3 新建与编辑

- 新建：容器 `openApplication()` → 抽屉 `openCreate()` → 校验项目上下文 → 打开抽屉并并发加载项目上下文与字典。
- 编辑：容器 `openApplication(id)` → 抽屉 `open(id)` → 拉详情回填 → 加载字典（补齐当前场景）→ 重新匹配决策路径 → 回填节点审批人。
- 保存成功：`emit('success')` → 容器刷新当前列表。

### 4.4 列表刷新 Hook

```ts
const { queryParams, initParams, handleSearch, handleReset } = useExceptionList(tableRef, onRefresh?)
```

| 机制           | 行为                                                                                                        |
| -------------- | ----------------------------------------------------------------------------------------------------------- |
| 参数同步       | `useExceptionPageReq` 深度 watch `queryParams`，`flush: 'sync'` 写入 `initParams`，保证点击查询时参数已更新 |
| 查询           | `handleSearch()` 调用 `tableRef.search()`                                                                   |
| 重置           | `resetAll()` 后立即 `search()`                                                                              |
| KeepAlive 激活 | `onActivated` 执行 `onRefresh?.()` + `tableRef.getTableData()`                                              |
| 失活           | `onDeactivated` 置 `isActive = false`                                                                       |
| 详情刷新       | `watch(refreshToken)` 时仅在 `isActive` 状态重新查询                                                        |

## 5. 配置层

### 5.1 筛选字段模型

```ts
interface ExceptionSearchFieldConfig {
  key: keyof ExceptionSearchFormModel;
  label: string;
  type: "input" | "select" | "date" | "dateRange";
  placeholder?: string;
  options?: { label: string; value: string | number }[];
  optionsSource?: "pipelines" | "scenes" | "subScenes" | "projects";
  clearsKeys?: ExceptionSearchFieldConfig["key"][];
  disabled?: (model: ExceptionSearchFormModel) => boolean;
}
```

### 5.2 字段清单

| key          | label          | type      | optionsSource | 级联清空                      | 禁用条件 |
| ------------ | -------------- | --------- | ------------- | ----------------------------- | -------- |
| `keyword`    | 关键字         | input     | -             | -                             | -        |
| `title`      | 标题           | input     | -             | -                             | -        |
| `status`     | 状态           | select    | 常量          | -                             | -        |
| `projectId`  | 项目           | select    | projects      | pipelineId / scene / subScene | -        |
| `pipelineId` | Nightly 流水线 | select    | pipelines     | -                             | 未选项目 |
| `scene`      | 例外场景       | select    | scenes        | subScene                      | 未选项目 |
| `subScene`   | 例外子场景     | select    | subScenes     | -                             | 未选场景 |
| `dateRange`  | 申请日期       | dateRange | -             | -                             | -        |

### 5.3 字段变体

| 常量                              | 使用页面           | 差异                    |
| --------------------------------- | ------------------ | ----------------------- |
| `EXCEPTION_SEARCH_FIELDS`         | 我的申请           | 完整 8 字段，状态含草稿 |
| `EXCEPTION_QUERY_SEARCH_FIELDS`   | 历史审批、例外查询 | 状态选项过滤 `draft`    |
| `EXCEPTION_PENDING_SEARCH_FIELDS` | 待我审批           | 移除 `status` 字段      |

### 5.4 参数转换

- 表单模型保留 `dateRange: [start, end] | null`。
- `toExceptionPageReq` 解构后输出 `startDate / endDate`，其余字段原样透传。
- `useExceptionPageReq` 返回 `reactive` 的 `initParams`，由 `base-table` 作为初始查询参数；分页参数由 `base-table` 追加。

### 5.5 列配置

| 配置                        | 使用页面           | 列（prop / 宽度）                                                                                                                                                                  |
| --------------------------- | ------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `EXCEPTION_LIST_COLUMNS`    | 我的申请、例外查询 | `billNo` 190 固定左、`currentHandlerName` 100、`status` 100、`title` 180、`applicantName` 100、`applyTime` 160、`productName` 180、`scene` 140、`subScene` 150、`pipelineName` 160 |
| `EXCEPTION_PENDING_COLUMNS` | 待我审批           | 通用列 + `startDate`（例外时间）190                                                                                                                                                |
| `EXCEPTION_HISTORY_COLUMNS` | 历史审批           | 通用列 + `approveTime` 160、`myResult` 110                                                                                                                                         |
| `EXCEPTION_PATH_COLUMNS`    | 路径配置           | `productName` 180、`scene` 140、`subScene` 150、`nodes` 520                                                                                                                        |

## 6. 搜索表单组件

### 6.1 组件契约

```ts
interface Props {
  fields: ExceptionSearchFieldConfig[];
}
const model = defineModel<ExceptionSearchFormModel>({ required: true });
const emit = defineEmits<{ search: []; reset: [] }>();
```

### 6.2 布局

- `el-form` 自身作为 grid 容器：`grid-cols-[repeat(6,minmax(160px,1fr))] gap-x-3 gap-y-3 items-end`。
- `label-position="top"`：label 在控件上方，贴合设计稿。
- `el-form-item` 统一 `!mb-0 min-w-0`：去掉默认下边距，避免 grid 列被内容撑破。
- 6 列等宽后 8 个字段自然折成两行，按钮跟随流布局，不做 `auto` 列，避免「例外场景」被视口截断。
- 日期区间强制 `!w-full`（覆盖 EP 默认 220px 固定宽）。

### 6.3 控件映射

| type        | 控件             | 关键属性                                                                |
| ----------- | ---------------- | ----------------------------------------------------------------------- |
| `input`     | `el-input`       | `clearable`，placeholder 默认「请输入」                                 |
| `select`    | `el-select-v2`   | `clearable`；项目字段额外 `filterable` + loading                        |
| `dateRange` | `el-date-picker` | `type="daterange"`、`value-format="YYYY-MM-DD"`、`range-separator="至"` |
| `date`      | `el-date-picker` | `type="date"`                                                           |

### 6.4 字典与级联

- 项目选项来自 `exceptionStore.projects`，`projectsLoading` 透传到控件。
- 流水线 / 场景在 `model.projectId` 变化时拉取：

```ts
watch(
  () => model.value.projectId,
  (n, o) => {
    if (n !== o) fetchDicts();
  },
  { immediate: true },
);
```

- 场景选项 label 为 `场景（归属名称）`，value 为场景名，同时携带 `ownerType` 作为去重 key。
- 子场景由已加载场景按 `scene` 过滤、按 `subScene` 去重展开。
- 请求返回后校验 `projectId` 是否已变化，避免快速切换项目时旧响应覆盖新字典。
- KeepAlive：首次 `onActivated` 跳过（`watch immediate` 已拉过），后续激活重新拉取，保证路径配置修改后场景字典生效。

### 6.5 级联清空与重置

- 字段变化时执行 `clearsKeys`，把目标字段置为 `null`。
- 重置逻辑：`input` → `''`，其他 → `null`；`projectId` 恢复为 `route.params.projectId`；最后 `emit('reset')`，由页面触发 `table.resetAll()` 与查询。

## 7. 列表页统一骨架

```vue
<div class="h-full flex flex-col bg-white border border-[#e2e8f0] rounded-lg overflow-hidden">
  <div class="p-4 border-b border-[#e2e8f0] shrink-0">筛选区</div>
  <div class="flex items-center justify-between px-4 py-3 border-b border-[#e2e8f0] shrink-0">工具行（可选）</div>
  <base-table ... height="100%" :border="false" />
</div>
```

`base-table` 统一参数：

| prop           | 值                              |
| -------------- | ------------------------------- |
| `columns`      | 对应列配置                      |
| `request-api`  | 对应分页接口                    |
| `init-params`  | `useExceptionList().initParams` |
| `pager-config` | `{ pageSize: 20 }`              |
| `row-key`      | `id`                            |
| `height`       | `100%`                          |
| `border`       | `false`                         |

插槽规范：

| 插槽          | 用途                                                 |
| ------------- | ---------------------------------------------------- |
| `billNo`      | 渲染为 `el-button link type="primary"`，点击进详情   |
| `status`      | 统一使用 `exception-status-badge`                    |
| `productName` | 展示 `组织 / 项目`，空值用 `EMPTY_VALUE`             |
| `operation`   | 内嵌 `el-table-column`，用 `@vue-generic` 标注行类型 |
| `myResult`    | 历史审批专用，映射同意/拒绝标签                      |
| `startDate`   | 待我审批专用，展示 `开始 ~ 结束`                     |

## 8. 页面明细

### 8.1 我的申请 `my-applications.vue`

- 请求：`POST /filing/applications/page`。
- 筛选：完整 8 字段（状态含草稿）。
- 勾选列：`type="selection"`，`selectable` 仅当 `row.actions.canWithdraw || row.actions.canDelete`。
- 工具行：新建例外申请（`Plus`）、批量撤回（`Back`）、批量删除（`Delete`）；无勾选时后两者禁用。
- 行内操作：编辑 / 撤回 / 删除，分别按 `actions.canEdit / canWithdraw / canDelete` 禁用。
- 单条撤回：`ElMessageBox.confirm` → `withdrawExceptionApplication(id)` → 成功提示 → 查询。
- 批量撤回：过滤可撤回行 → 确认 → `Promise.allSettled` 逐条撤回 → 统计失败数提示 → 查询。
- 删除：确认文案区分单条/批量；调用 `deleteExceptionApplications(ids)`；若 `failed.length > 0`，按 `id → billNo` 映射拼接「编号：原因」提示；否则成功提示；最后查询。

### 8.2 待我审批 `pending-approvals.vue`

- 请求：`POST /filing/applications/pending/page`（本地包装 `getPendingList` 以匹配 `base-table` 的 `request-api` 签名）。
- 筛选：不含状态字段。
- 无工具行、无操作列；仅申请编号可进详情（审批统一在详情完成）。
- 例外时间列展示 `startDate ~ endDate`。
- `onRefresh` 注入 `exceptionStore.refreshPendingTotal`，激活或详情刷新后同步角标。

### 8.3 历史审批 `approval-history.vue`

- 请求：`POST /filing/applications/history/page`。
- 筛选：查询口径（状态不含草稿）。
- 列：通用列 + 审批完成时间 + 我的审批结果。
- `myResult` 映射：`approve → 同意 / success`，`reject → 拒绝 / danger`，空值展示 `EMPTY_VALUE`。
- 已删除单据由 `status` 徽标展示（`isDelete` 由列表字段承载时按后端口径展示）。

### 8.4 例外查询 `exception-search.vue`

- 请求：`POST /filing/applications/all/page`。
- 筛选：查询口径（状态不含草稿）。
- 列：通用列；不提供写操作与操作列。
- 该页签依赖后端「全员分页」接口；接口不可用时页面不可用（见风险）。

### 8.5 例外决策路径配置 `pattern-config.vue`

- 请求：`POST /filing/paths/page`；无筛选区。
- 工具行仅「新增决策路径」，右对齐。
- 节点流展示：
  - 每个节点一张卡片：角色名 + 候选人（最多展示 2 个），超出用 `+N` 标签，悬浮展示全部候选人。
  - `roleOnly` 节点展示「申请人提交时自选」。
  - 节点间用 `i-ep-right` 箭头连接。
- 操作：编辑 / 删除。
- 删除：确认文案包含「组织/项目 · 场景 - 子场景」；成功后 `clearScenes()` + 刷新。
- 抽屉懒挂载：`v-if="drawerVisible"` + `v-model:visible`，首次点击才创建组件。

## 9. 详情抽屉

### 9.1 组件契约

```ts
const emit = defineEmits<{ refresh: []; edit: [id: string] }>();
defineExpose({ open }); // open(id: string)
```

- `el-drawer size="95vw" destroy-on-close`。
- 头部：标题 + 单号（等宽字体）+ 状态徽标；无详情时展示「例外备案详情」。
- 内容区 `v-loading="detailLoading"`，整体纵向滚动；底部固定操作区。

### 9.2 内容结构

| 区块     | 数据来源                                                 | 展示                                                                  |
| -------- | -------------------------------------------------------- | --------------------------------------------------------------------- |
| 审批流程 | `detail.nodes`、`detail.currentNodeSeq`、`detail.status` | `exception-flow-panel`                                                |
| 基本信息 | `detail`                                                 | 3 列网格，key 112px；末尾补空位保证对齐                               |
| 例外说明 | `detail.description`                                     | 占满整行，`getCleanHtml` 净化后 `v-html`，`max-height=400px` 内部滚动 |
| 审批记录 | `detail.approvalRecords`                                 | 审批环节 / 结论标签 / 意见 / 审批人 / 时间                            |
| 跟踪进展 | `detail.tracks`                                          | 跟踪节点 / 操作类型 / 进展描述 / 操作人 / 时间                        |

基本信息字段顺序：标题、申请编号、状态、组织/项目、场景归属、例外场景、例外子场景、Nightly 流水线、例外开始时间、例外结束时间、申请人、当前处理人、申请时间。

映射规则：

- 审批环节：`nodeSeq → detail.nodes[].roleName`，找不到时「节点 N」。
- 操作类型：`EXCEPTION_ACTION_MAP`。
- 跟踪节点：无 `nodeSeq` 时，`submit → 提交备案`、`withdraw → 撤回申请`。
- 进展描述：`opinion || reason || EMPTY_VALUE`。

### 9.3 动作按钮矩阵

| 按钮     | 显示条件              | 交互                             | 接口              | 后置                                 |
| -------- | --------------------- | -------------------------------- | ----------------- | ------------------------------------ |
| 编辑     | `actions.canEdit`     | `emit('edit', id)`               | -                 | 容器打开编辑抽屉                     |
| 撤回     | `actions.canWithdraw` | 二次确认                         | `withdraw`        | 提示 + 重载详情 + refresh            |
| 删除     | `actions.canDelete`   | 二次确认                         | `delete`（单 id） | 成功关闭抽屉 + refresh；失败提示原因 |
| 拒绝     | `actions.canReject`   | 意见弹窗（必填）                 | `reject`          | 提示 + 重载 + refresh                |
| 同意     | `actions.canApprove`  | 意见弹窗（选填）                 | `approve`         | 提示 + 重载 + refresh                |
| 转移     | `actions.canTransfer` | 转移弹窗                         | `transfer`        | 弹窗内提示 + 重载 + refresh          |
| 复制链接 | `!actions.canEdit`    | `useClipboard({ legacy: true })` | -                 | 提示「复制成功」                     |

- 撤回/删除通过 `confirmAction` 统一封装 `ElMessageBox.confirm`。
- `actionLoading` 贯穿所有动作，请求期间禁用按钮并给 loading。

### 9.4 子弹窗

- `exception-opinion-dialog.vue`
  - props：`mode: 'approve' | 'reject'`、`loading`。
  - 顶部提示条：同意说明流转与生效规则；拒绝说明退回与可修改重提。
  - 文本域：`maxlength=200`，拒绝必填；确认时 `emit('confirm', opinion.trim())`。
- `exception-transfer-dialog.vue`
  - 平台选择 + 用户远程搜索（`searchExceptionUsers`），切换平台清空用户与选项。
  - 原因必填，`maxlength=200`。
  - 远程搜索使用 `searchToken` 丢弃过期响应。
  - 提交校验：平台、用户、原因三项；成功后关闭并 `emit('success')`。
  - 文案声明「不能选择自己」，当前未做前端用户维度校验（见风险）。

## 10. 审批流面板与滚动条

### 10.1 `exception-flow-panel.vue`

props：`detail: ExceptionApplicationDetail`。

节点状态推导：

```ts
withdrawn                      → 全部 pending
returned && node.status !== rejected → pending
node.status === approved       → passed
node.status === rejected       → rejected
filing && seq === currentNodeSeq → current
其他                            → pending
```

视觉规则：

| 状态     | 卡片            | 文字 | 连接线 / 箭头 | 圆点         |
| -------- | --------------- | ---- | ------------- | ------------ |
| passed   | 绿边白底        | 绿   | 绿            | 绿           |
| current  | 主色边 + 浅蓝底 | 主色 | 灰            | 主色（脉冲） |
| rejected | 红边 + 浅红底   | 红   | 红            | 红           |
| pending  | 灰边白底        | 灰   | 灰            | 浅灰         |

- 申请人卡片：可编辑时为 pending 态，否则 passed 态。
- 连接线：停止流转（撤回/退回）统一灰色实线；被拒绝节点到下一节点使用红色实线；其余用左右半段分别继承前后节点颜色。
- 连接线标签：仅在非停止流转且不可编辑时展示「审批中 / 待审批」。
- 节点右上角展示后端 `node.status` 文案（非 pending 时）。

### 10.2 `flow-scrollbar.vue`

props：`viewport?: HTMLElement`、`dots: FlowDot[]`、`activeKey?: string`。

- 仅当内容宽度超出视口 1px 时显示。
- 轨道 200×16px，滑块最小宽 20px；滑块宽度 = 视口/内容比例。
- 圆点位置按节点 DOM 中心相对内容宽度计算，找不到节点时退化为等分位置。
- 交互：点击轨道跳转、拖拽滑块、点击圆点平滑滚动到节点；`activeKey` 变化时自动滚动到当前节点。
- 监听视口 `scroll`、`useResizeObserver`，`onBeforeUnmount` 解绑。

## 11. 新建 / 编辑申请抽屉

### 11.1 组件契约

```ts
const props = defineProps<{ projectId?: number; pipelineId?: string }>();
const emit = defineEmits<{ success: [] }>();
defineExpose({ open }); // open(id?: string)
```

- `el-drawer size="95%" destroy-on-close`，`@closed="resetForm"`。
- 新建与编辑共用表单；标题「新建例外申请 / 编辑例外申请」。

### 11.2 打开流程

| 场景 | 步骤                                                                                                                                                                                        |
| ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 新建 | `resetForm` → 取 `props.projectId ?? Number(route.params.projectId)` → 无效则提示并终止 → 写入 `projectId` → 可选锁定 `pipelineId` → 打开抽屉 → 并发加载项目上下文与字典 → 上下文失败则关闭 |
| 编辑 | `resetForm` → 取详情 → `setSelectedProject` → 回填标题/说明/流水线/场景/子场景/时间 → `fetchDicts(当前场景兜底)` → `fetchMatchedPath` → 回填节点审批人（roleOnly 回填平台+用户+单选项）     |

### 11.3 表单模型

```ts
{
  projectId: number | null;
  productId: number;          // 0 表示全部
  ownerType: ExceptionOwnerType | '';
  pipelineId: string;
  scene: string;
  subScene: string;
  title: string;
  description: string;        // 富文本 HTML
  dateRange: string[];        // [start, end]
}
```

场景选择值使用 `ownerType:scene` 组合 key，选中时同时写回 `scene` 与 `ownerType`；子场景选项来自当前场景的 `subScenes`。

### 11.4 校验规则

| 字段       | 规则                                                                        | trigger |
| ---------- | --------------------------------------------------------------------------- | ------- |
| 流水线     | 必填                                                                        | change  |
| 例外场景   | 必填                                                                        | change  |
| 例外子场景 | 必填                                                                        | change  |
| 标题       | 必填，`maxlength=100` + 字数统计                                            | blur    |
| 例外时间   | 必填数组长度 2；结束 ≥ 开始；跨度 ≤365 天；不可选「今天 +365 天」之后的日期 | change  |
| 例外说明   | 富文本转纯文本后必填，≤20000 字                                             | change  |
| 节点审批人 | 每个节点必须能解析出审批人，否则 `ElMessage.warning` 阻止提交               | 提交时  |

### 11.5 决策路径匹配

```ts
productId = ownerType === "ALL" ? 0 : form.productId;
projectId = ownerType === "PROJECT" ? form.projectId : 0;
getExceptionPathPage({
  productId,
  projectId,
  scene,
  subScene,
  page: 1,
  pageSize: 100,
});
```

- 前端在返回记录中精确匹配 `productId + projectId + scene + subScene + !isDelete`。
- 命中后写入 `matchedNodes`，并为 `single` 节点默认选中第一个候选人；`multi` 生成候选人选项；`roleOnly` 不生成选项。
- 未命中：展示橙色提示「未配置决策路径，无法提交」，并禁用提交按钮。

### 11.6 节点渲染

| assignType | 审批人控件          | 规则                                           |
| ---------- | ------------------- | ---------------------------------------------- |
| `single`   | `el-select-v2`      | 默认唯一候选人，禁用不可改                     |
| `multi`    | `el-select-v2`      | 从候选人中选择                                 |
| `roleOnly` | 平台 + 远程用户搜索 | 平台变更清空用户与选项；远程搜索校验平台未变化 |

- 节点区横向滚动，节点序号圆点 + 角色名 + 配置方式 + 审批人；顶部右侧 `flow-scrollbar` 圆点导航。
- 节点连接线为灰线 + 箭头（新建申请中的静态流程预览）。

### 11.7 保存逻辑

```ts
buildPayload(draft) => {
  id?, projectId: form.projectId ?? 0, ownerType?, pipelineId, scene, subScene,
  title, description, startDate: dateRange[0] ?? '', endDate: dateRange[1] ?? '',
  draft, nodeAssignees
}
```

- 草稿：不校验表单与节点，直接保存。
- 提交：先 `formRef.validate()`，再校验节点审批人。
- 新建：
  - 草稿/提交都由 `createExceptionApplication(payload)` 处理，`draft` 字段区分语义。
- 编辑：
  - 先 `updateExceptionApplication(payload)`；
  - 若为提交，再调用 `submitExceptionApplication(id, { nodeAssignees })`。
- 成功：提示「草稿保存成功 / 提交成功」→ 关闭抽屉 → `emit('success')`。

### 11.8 富文本编辑器

- 使用 `defineAsyncComponent` 懒加载 `@/components/tinymce-editor.vue`，加载中显示遮罩。
- 加载失败提供 `errorComponent` 占位并提示「编辑器加载失败，请关闭后重试」。
- 说明字段支持格式化内容，但校验按纯文本计算。

## 12. 决策路径编辑抽屉

### 12.1 组件契约

```ts
const visible = defineModel<boolean>("visible", { default: false });
const props = defineProps<{ pathRow?: ExceptionPathItem }>();
const emit = defineEmits<{ success: [] }>();
```

- `el-drawer size="90%" destroy-on-close`。
- `editId = computed(() => props.pathRow?.id)`，新增与编辑共用。

### 12.2 表单与级联

| 字段       | 控件           | 规则                                                        |
| ---------- | -------------- | ----------------------------------------------------------- |
| 组织       | `el-select-v2` | 必填；选项含「全部」(0)                                     |
| 项目       | `el-select-v2` | 组织为「全部」时禁用并提交 0；否则按组织拉取，含「全部」(0) |
| 例外场景   | `el-input`     | 必填，≤64 字                                                |
| 例外子场景 | `el-input`     | 必填，≤64 字                                                |

- 编辑回填时若组织/项目不在当前字典中，动态补一个选项（label 用已有名称或 `组织 N` / `项目 N`）。
- 组织变更：清空项目、项目名、项目选项；组织非 0 时重新拉项目。

### 12.3 节点草稿模型

```ts
interface PathNodeDraft {
  roleName: string;
  assignType: ExceptionAssignType;
  candidates: ExceptionCandidate[];
  platform: string; // 候选人搜索平台，默认 gitcode
  userId: string; // 搜索结果当前选中
  userOptions: { value: string; label: string; accountName: string }[];
  loading: boolean;
}
```

### 12.4 节点编辑与约束

- 表格列：角色/职责、审批人配置方式、审批人员、删除。
- 新增节点：默认 `assignType = single`，至少保留 1 个节点，最多 10 个。
- 切换为 `roleOnly`：清空候选人、选中用户与选项。
- 候选人超过 1 人时，配置方式下拉禁用（避免 multi 被改成 single 造成数据不一致）。
- `single` 已有候选人时，平台/用户/添加按钮禁用。
- 添加候选人：必须已选人员；单节点 ≤50；同节点去重；跨节点同一 `userId` 不允许重复。
- 编辑回填：候选人深拷贝，`seq` 不直接使用，保存时重排。

### 12.5 保存

```ts
payload = {
  id?, productId,
  projectId: productId === 0 ? 0 : projectId,
  scene: trim, subScene: trim,
  nodes: nodes.map((node, i) => ({
    seq: i + 1,
    roleName: trim,
    assignType,
    candidates: candidates.map(({ platform, userId }) => ({ platform, userId }))
  }))
}
```

- 保存前：`formRef.validate()` + `validateNodes()`（节点数、角色名、候选人、上限、跨节点重复）。
- 统一调用 `updateExceptionPath`；成功提示「编辑成功 / 新增成功」→ 关闭 → `emit('success')`。
- 父页面收到成功后 `clearScenes()` 并刷新列表。

### 12.6 初始化时机

- `watch(visible, immediate)`：打开时 `initForm()` + `clearValidate()`；组织非 0 时拉项目。
- `onMounted` 拉组织字典。
- 组件由父页面 `v-if` 懒挂载，首次打开才创建实例。

## 13. 接口契约与请求规范

- 统一前缀：`${apiConfig.ops}/filing`。
- 全部函数返回 `Promise<ResultData<T>>`，分页返回 `ResultData<PagerData<T>>`。
- 页面使用 `to()` 解包：`const [err, res] = await to(api(...))`；`err` 存在直接返回，不重复提示。
- 成功提示保留在业务侧；错误提示由 HTTP 拦截器统一处理。
- 分页列表请求参数统一由 `ExceptionApplicationPageReq` 描述；`includeDeleted` 预留但列表页未显式使用。

关键响应字段：

| 类型      | 字段                                                                                                                                                                       |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 列表行    | `id/billNo/title/status/product*/project*/ownerType/scene/subScene/pipeline*/applicant*/applyTime/startDate/endDate/currentHandler*/approveTime/isDelete/actions/myResult` |
| 详情      | 列表行基础字段 + `description/submitTime/currentNodeSeq/currentHandler/nodes/approvalRecords/tracks`                                                                       |
| `actions` | `canEdit/canSubmit/canWithdraw/canDelete/canApprove/canReject/canTransfer`                                                                                                 |
| 删除响应  | `successIds: string[]`、`failed: { id, reason }[]`                                                                                                                         |
| 路径      | `id/productId/productName/projectId/projectName/scene/subScene/isDelete/createTime/nodes`                                                                                  |
| 节点      | `seq/roleName/assignType/candidates[{platform,userId,userName}]`                                                                                                           |

## 14. 类型、常量与 store

### 14.1 类型

- 平台：`ExceptionPlatform = gitcode | gitee | github | openubmc | uniportal`。
- 状态：`ExceptionStatus = draft | filing | approved | returned | withdrawn`。
- 节点状态：`pending | approved | rejected`。
- 动作：`submit | approve | reject | transfer | withdraw | auto_withdraw`。
- 分配方式：`single | multi | roleOnly`。
- 归属：`PROJECT | PRODUCT | ALL`。
- 申请单、路径、列表、详情、actions、删除/转移响应等见 `src/types/exception.ts`。

### 14.2 常量映射

| 常量                        | 内容                                                                         |
| --------------------------- | ---------------------------------------------------------------------------- |
| `EXCEPTION_STATUS_MAP`      | 草稿 default、备案中 running、已备案 success、已退回 failed、已撤回 canceled |
| `EXCEPTION_OWNER_TYPE_MAP`  | PROJECT 项目级、PRODUCT 组织级、ALL 全部级                                   |
| `EXCEPTION_ASSIGN_TYPE_MAP` | single 指定单个审批人、multi 配置多个审批人、roleOnly 申请人自选             |
| `EXCEPTION_ACTION_MAP`      | 提交/同意/拒绝/转移/撤回/超时自动撤回                                        |
| `EXCEPTION_MY_RESULT_MAP`   | approve 同意 success、reject 拒绝 danger                                     |
| `EXCEPTION_NODE_STATUS_MAP` | pending 待审批、approved 已同意、rejected 已拒绝                             |
| `PLATFORM_MAP`              | gitcode/gitee/github/openubmc/uniportal 展示名                               |

### 14.3 store

```ts
useExceptionStore() => {
  pendingTotal, refreshPendingTotal,
  products, productsLoading, fetchProducts,
  projects, projectsLoading, fetchProjects({ productId? }),
  fetchPipelines(projectId), fetchScenes(projectId), clearScenes
}
```

- `fetchProjects()` 全量结果缓存（`projectsLoaded`），带 `productId` 的查询不写缓存。
- `fetchPipelines/fetchScenes` 以 `projectId` 为 key 的 `Map` 缓存。
- `refreshPendingTotal` 使用 `page=1, pageSize=1`，只取 `total`。
- 路径保存/删除后 `clearScenes()`，避免场景归属变更后仍用旧字典。

## 15. 样式与布局规范

### 15.1 页面骨架

| 区域         | 类名 / 尺寸                                                               |
| ------------ | ------------------------------------------------------------------------- |
| 模块根       | `h-full flex flex-col bg-[#f2f3f5] overflow-hidden` + `process-exception` |
| 顶部页签     | `h-12 px-6 bg-white border-b border-[#e2e8f0] gap-7`                      |
| 激活页签     | `text-[#2563eb] font-semibold` + 2px 主色底条                             |
| 待办角标     | 18px 高、红色 `#dc2626`、`99+`、等宽字体                                  |
| 内容区       | `flex-1 min-h-0 p-5 px-6 pb-6 overflow-hidden`                            |
| 列表卡片     | `bg-white border border-[#e2e8f0] rounded-lg overflow-hidden`             |
| 筛选区       | `p-4 border-b border-[#e2e8f0]`                                           |
| 工具行       | `px-4 py-3 border-b border-[#e2e8f0]`                                     |
| 流程节点卡片 | `flex-1 basis-[200px] min-w-[200px] p-3.5 rounded-lg border`              |
| 连接段       | `w-[92px] h-12`                                                           |

### 15.2 抽屉与弹窗

| 组件      | 尺寸    | 说明                                      |
| --------- | ------- | ----------------------------------------- |
| 详情      | `95vw`  | `destroy-on-close`，头部/底部自定义       |
| 新建/编辑 | `95%`   | 两列 `el-row :gutter="20"`，标题/说明整行 |
| 路径编辑  | `90%`   | 组织/项目同行两列，场景/子场景整行        |
| 同意/拒绝 | `480px` | `append-to-body`，提示条 + 文本域         |
| 转移      | `480px` | `append-to-body`，平台+用户同行           |

### 15.3 设计稿 token 落地

| 语义                     | 值                                | 使用位置                         |
| ------------------------ | --------------------------------- | -------------------------------- |
| 主色                     | `#2563eb`                         | 激活页签、当前节点、链接、主按钮 |
| 主色浅底                 | `#eff6ff`                         | 当前节点卡片、提示条             |
| 成功                     | `#059669`                         | 已通过节点、成功标签             |
| 危险                     | `#dc2626`                         | 拒绝节点、待办角标、删除         |
| 警告                     | `#d97706`                         | 未配置路径提示                   |
| 页面底色                 | `#f2f3f5`                         | 模块背景                         |
| 卡片边框                 | `#e2e8f0`                         | 卡片、分区、表格外框             |
| 输入框边框               | `#dcdfe6`                         | 流程节点、默认边框               |
| 主文字 / 次文字 / 弱文字 | `#191919` / `#606266` / `#909399` | 标题 / label / 辅助信息          |

### 15.4 `style.less`

```less
.process-exception .pagination {
  padding: 10px 16px;
}
.process-exception [id^="base-table_"] {
  min-height: 0;
}
.exception-status-badge.status-badge {
  /* default / canceled 覆盖为 slate 色 */
}
```

- 由容器非 scoped 引入，作用到所有子页面的 `base-table` 分页与状态徽标。
- 组件私有样式保留在各自 `<style scoped>`（详情卡片、路径节点流、滚动条动画）。

## 16. 性能与体验

| 项         | 实现                                                          |
| ---------- | ------------------------------------------------------------- |
| 页签懒加载 | `defineAsyncComponent` 按需加载页面 chunk                     |
| 页签缓存   | `KeepAlive` 保留筛选与滚动状态；列表 `onActivated` 重新拉数据 |
| 抽屉懒挂载 | 路径编辑 `v-if` 首次打开才创建；所有抽屉 `destroy-on-close`   |
| 编辑器     | TinyMCE 异步 chunk，加载态与失败态兜底                        |
| 字典缓存   | store 按项目缓存流水线/场景；组织/项目全量缓存                |
| 远程搜索   | 转移弹窗 `searchToken`、roleOnly 平台校验，避免竞态覆盖       |
| 分页       | 统一 `pageSize: 20`，由 `base-table` 管理                     |
| 长内容     | 例外说明内部滚动；审批意见、进展描述 `show-overflow-tooltip`  |
| 防重复     | `actionLoading` / `submitting` / `loading` 控制按钮状态       |

## 17. 异常与边界

| 场景             | 处理                                                             |
| ---------------- | ---------------------------------------------------------------- |
| 请求失败         | `to()` 返回 err 后直接返回，提示由拦截器统一处理                 |
| 删除部分失败     | `failed[]` 映射申请编号 + 原因，`ElMessage.warning` 展示         |
| 批量撤回部分失败 | `Promise.allSettled` 统计 rejected 数量并提示                    |
| 无项目上下文新建 | `ElMessage.warning('缺少项目上下文，无法新建例外申请')` 并终止   |
| 未配置决策路径   | 橙色提示 + 禁用提交                                              |
| 节点审批人缺失   | 提交前 `ElMessage.warning('请选择各节点审批人')`                 |
| 路径节点非法     | 逐项提示节点序号与原因（角色/候选人/上限/重复）                  |
| 快速切换项目     | 字典响应回来校验 `projectId`，避免旧数据覆盖                     |
| 快速修改平台     | 远程搜索结果校验平台或 token，丢弃过期响应                       |
| 详情数据为空     | 头部回退标题，内容区不渲染                                       |
| 空值展示         | 统一 `EMPTY_VALUE`；路径列表组织/项目回退「全部组织 / 全部项目」 |

## 18. 已知缺口与风险

| 级别 | 项                          | 说明                                                                                              | 建议                                                                |
| ---- | --------------------------- | ------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- |
| 高   | 详情链接与路由不一致        | `getProcessExceptionUrl` 生成 `/apps/processException`，实际路由 `/process-exception/:projectId?` | 与网关/部署前缀确认后统一，否则复制链接打不开                       |
| 中   | 转移「不能选自己」未拦截    | 弹窗文案声明，但前端未校验当前用户                                                                | 后端已约束则保留，否则补 `currentHandler` 对比                      |
| 中   | 新建/编辑提交语义不对称     | 新建依赖 `create` 的 `draft:false` 直接提交；编辑需 `update` 后再 `submit`                        | 与后端确认 `create` 是否等价提交；如需统一可改为 create 后再 submit |
| 中   | 待办接口平台参数            | 早期接口要求 `platform` 必填，当前前端未传                                                        | 与后端联调确认                                                      |
| 中   | 例外查询依赖全员分页接口    | 页面直连 `applications/all/page`                                                                  | 后端未上线时该页签不可用                                            |
| 中   | 路径全量匹配                | 单次拉取 100 条后前端精确匹配                                                                     | 路径规模增长后需按项目查询接口，否则可能漏配                        |
| 低   | 页签未回写 URL              | 切换页签不更新 `query.tab`，刷新回默认页签                                                        | 如需可分享链接再补                                                  |
| 低   | 硬编码设计稿 hex            | 模板大量直接使用 `#2563eb/#e2e8f0` 等                                                             | 后续收敛到 EP 变量 / 语义 token                                     |
| 低   | 无单元测试                  | 状态推导、路径匹配、参数转换为纯函数但未覆盖                                                      | 补 `__tests__` 覆盖关键分支                                         |
| 低   | `approval-history.vue` 命名 | 与页签 value 同名，但与组件内「历史审批」语义一致                                                 | 保持现状                                                            |

## 19. 前端自测清单

| 类型      | 用例                                                                                 |
| --------- | ------------------------------------------------------------------------------------ |
| 路由      | `/process-exception`、带 `projectId`、`?tab=pending-approvals`、`?id=xxx` 直达       |
| 权限      | 有/无 `ops_filing_path` 时页签数量与默认页签                                         |
| 筛选      | 8 字段渲染；项目→流水线/场景→子场景联动；重置后项目保留路由值；分页与查询            |
| 我的申请  | 新建草稿、新建提交、编辑回填、单条/批量撤回、单条/批量删除、部分失败提示、勾选禁用   |
| 待我审批  | 列表加载、角标数、激活刷新、仅详情入口                                               |
| 历史/查询 | 状态无草稿、审批完成时间、我的审批结果标签、空值展示                                 |
| 详情      | actions 按钮显隐、流程四态、审批记录/跟踪映射、复制链接、撤回/删除确认               |
| 审批      | 同意选填意见、拒绝必填、转移平台+用户+原因校验、动作后列表刷新                       |
| 新建      | 无项目拦截、未配置路径禁提交、single/multi/roleOnly 选人、日期与说明校验、编辑器加载 |
| 路径      | 新增/编辑/删除、组织「全部」锁项目、节点 1~10、候选人 ≤50、跨节点重复拦截、seq 重排  |
| 兼容      | 抽屉关闭后重开状态复位、KeepAlive 切页后数据刷新、窄屏横向滚动条可用                 |

## 20. 涉及文件

| 文件                                                                   | 操作 | 说明                       |
| ---------------------------------------------------------------------- | ---- | -------------------------- |
| `src/api/exception.ts`                                                 | 新增 | `/filing` 接口集合         |
| `src/types/exception.ts`                                               | 新增 | 模块全部类型               |
| `src/stores/exception-store.ts`                                        | 新增 | 待办总数与字典缓存         |
| `src/router/routes/modules/process-exception.ts`                       | 新增 | 单路由注册                 |
| `src/views/process-exception/process-exception.vue`                    | 新增 | 页签容器与共享抽屉         |
| `src/views/process-exception/config.ts`                                | 新增 | 筛选字段、参数转换、列配置 |
| `src/views/process-exception/constants.ts`                             | 新增 | 枚举与视觉映射             |
| `src/views/process-exception/detail-context.ts`                        | 新增 | 容器上下文注入             |
| `src/views/process-exception/utils.ts`                                 | 新增 | 展示与链接工具             |
| `src/views/process-exception/hooks/use-exception-list.ts`              | 新增 | 列表查询与刷新             |
| `src/views/process-exception/style.less`                               | 新增 | 模块共享样式               |
| `src/views/process-exception/my-applications.vue`                      | 新增 | 我的申请                   |
| `src/views/process-exception/pending-approvals.vue`                    | 新增 | 待我审批                   |
| `src/views/process-exception/approval-history.vue`                     | 新增 | 历史审批                   |
| `src/views/process-exception/exception-search.vue`                     | 新增 | 例外查询                   |
| `src/views/process-exception/pattern-config.vue`                       | 新增 | 决策路径列表               |
| `src/views/process-exception/components/exception-search-form.vue`     | 新增 | 配置驱动筛选               |
| `src/views/process-exception/components/new-application-drawer.vue`    | 新增 | 新建/编辑申请              |
| `src/views/process-exception/components/exception-detail-drawer.vue`   | 新增 | 详情与动作                 |
| `src/views/process-exception/components/exception-flow-panel.vue`      | 新增 | 审批流程面板               |
| `src/views/process-exception/components/flow-scrollbar.vue`            | 新增 | 流程滚动条                 |
| `src/views/process-exception/components/exception-opinion-dialog.vue`  | 新增 | 同意/拒绝                  |
| `src/views/process-exception/components/exception-transfer-dialog.vue` | 新增 | 转移审批人                 |
| `src/views/process-exception/components/exception-status-badge.vue`    | 新增 | 状态徽标                   |
| `src/views/process-exception/components/path-edit-drawer.vue`          | 新增 | 路径新增/编辑              |

## 21. 验证方式

- 类型检查：`npm run type-check`（vue-tsc 增量）。
- Lint：改动文件由 lint-staged 处理。
- 手工自测：按「第 19 节 前端自测清单」执行。
- 接口联调：重点确认待办平台参数、全员分页接口、路径按项目查询能力、新建提交语义。
