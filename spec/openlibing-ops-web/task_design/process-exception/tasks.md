# 版本可用度备案（process-exception）— 实现任务

> 模块根：`openlibing-ops-web/src/views/process-exception/`
> 进度：17/17 代码交付完成（开放风险与联调项见 design §18）
> 说明：任务按前端依赖顺序拆分，每项包含目标、涉及文件、实现要点、依赖、验收与自测点。复选框表示代码已交付，验证记录见文末。

## 任务地图

```text
基础层      T1 类型与接口 → T2 store → T3 常量/工具/上下文/路由
列表层      T4 配置层 → T5 列表 Hook → T6 搜索表单
页面层      T7 我的申请 → T8 待我审批 → T9 历史审批 → T10 例外查询
详情层      T11 状态徽标 + 详情骨架 → T12 流程面板 + 滚动条 → T13 审批弹窗与动作闭环
表单层      T14 新建/编辑申请 → T15 路径列表 + 路径编辑
集成层      T16 页签容器整合 → T17 样式统一与收尾验证
```

依赖约束：

- T1 是所有任务的类型与接口前提；T2/T3 依赖 T1。
- T5 依赖 T4；T6 依赖 T2、T4（与 T5 并行）；T7~T10 依赖 T5 + T6。
- T11 依赖 T1/T3；T12 依赖 T11 的 `detail` 数据结构约定；T13 依赖 T12。
- T14 依赖 T2/T4/T6（字典、路径匹配、搜索表单）；T15 依赖 T1/T2/T3（类型、字典、常量）。
- T16 依赖 T7~T15 全部页面组件；T17 最后执行，不改业务语义。

---

## T1 类型定义与接口层

- [x] **目标**：建立 `/filing` 域的类型契约与全部接口函数，保证后续页面只依赖类型和函数，不直接拼 URL。
- **涉及文件**：`src/types/exception.ts`、`src/api/exception.ts`
- **实现要点**：
  - 基础类型：`ExceptionPlatform`（gitcode/gitee/github/openubmc/uniportal）、`ExceptionStatus`（draft/filing/approved/returned/withdrawn）、`ExceptionNodeStatus`、`ExceptionAction`、`ExceptionAssignType`、`ExceptionOwnerType`。
  - 实体类型：`ExceptionProduct`、`ExceptionProject`、`ExceptionProjectContext`、`ExceptionScene`、`ExceptionPathItem`、`ExceptionPathNode`、`ExceptionCandidate`、`ExceptionApplicationItem`、`ExceptionApplicationDetail`、`ExceptionApprovalRecord`、`ExceptionTrack`。
  - 请求/响应类型：`ExceptionApplicationPageReq`、`ExceptionPathPageReq`、`ExceptionApplicationPayload`、`ExceptionNodeAssignee`、`ExceptionActions`、`ExceptionDeleteResult`、`ExceptionTransferReq`、`ExceptionUserSearchItem`。
  - 分页统一使用 `PagerData<T>`，响应统一 `ResultData<T>`；`actions` 字段声明为可选，避免列表/详情缺失时报类型错。
  - 接口函数统一 `baseURL = apiConfig.ops + '/filing'`，函数名以 `Exception` 命名空间前缀，避免与其他模块冲突。
  - 覆盖 23 个函数：字典 6（含用户搜索）、路径 3、申请单 8、详情 1、轨迹 1、列表 4。
- **依赖**：无
- **验收**：
  - 所有页面需要的字段都有类型声明，无 `any` 兜底。
  - 接口路径与后端契约一致，分页接口统一 `POST`；待办 `platform`、新建提交语义等待联调项见 design §18。
- **自测点**：`TS` 编译通过；控制台无类型告警。

---

## T2 字典与待办 store

- [x] **目标**：把跨页面复用的组织/项目/流水线/场景字典与待办总数收敛到 Pinia，减少重复请求并支持缓存失效。
- **涉及文件**：`src/stores/exception-store.ts`
- **实现要点**：
  - 状态：`pendingTotal`、`products` + `productsLoading`、`projects` + `projectsLoading`、`pipelineCache: Map<number, ...>`、`sceneCache: Map<number, ...>`。
  - `refreshPendingTotal()`：`page=1, pageSize=1` 只取 `total`，不保存列表。
  - `fetchProjects({ productId? })`：无 `productId` 时全量加载并标记 `projectsLoaded`，重复调用直接返回缓存；带 `productId` 的查询不写全量缓存。
  - `fetchPipelines(projectId)` / `fetchScenes(projectId)`：按项目缓存，命中即返回；失败时清空对应 key，允许下次重试。
  - `clearScenes()`：清空场景缓存，路径保存/删除后调用。
- **依赖**：T1
- **验收**：同一项目重复进入页面不重复请求字典；待办角标可在任意页面刷新。
- **自测点**：路径新增后进入「我的申请」，场景下拉出现新场景。

---

## T3 常量、工具、详情上下文与路由

- [x] **目标**：提供模块级枚举映射、展示工具、容器上下文契约和路由入口。
- **涉及文件**：`src/views/process-exception/constants.ts`、`src/views/process-exception/utils.ts`、`src/views/process-exception/detail-context.ts`、`src/router/routes/modules/process-exception.ts`
- **实现要点**：
  - 枚举映射：状态（default/running/success/failed/canceled）、归属类型、分配方式、动作、我的审批结果、节点状态、平台。
  - 流程视觉：`EXCEPTION_FLOW_NODE_STYLE` / `EXCEPTION_FLOW_LABEL_STYLE` 统一维护 passed/current/rejected/pending 的边框、背景、文字、连接线。
  - `formatPlatformUser(user)`：`平台 · 姓名`，缺失回退 `userId` 或 `EMPTY_VALUE`。
  - `toPipelineOption(pipeline)`：统一流水线下拉结构。
  - `getProcessExceptionUrl(id)`：生成详情复制链接（当前与路由存在偏差，见风险）。
  - `EXCEPTION_DETAIL_KEY` + `useExceptionDetail()`：类型化 inject，缺失时抛错，避免静默失败。
  - 路由：`/process-exception/:projectId?`，`name = ProcessException`，懒加载容器。
- **依赖**：T1
- **验收**：五个页面能 import 到同一套常量；容器外误用 `useExceptionDetail` 能快速暴露。
- **自测点**：路由直达、刷新不 404。

---

## T4 列表配置层

- [x] **目标**：用配置描述四个列表的筛选、参数转换与列，避免四份重复模板。
- **涉及文件**：`src/views/process-exception/config.ts`
- **实现要点**：
  - 定义 `ExceptionSearchFieldConfig` 与 `ExceptionSearchFormModel`，字段支持 `type/options/optionsSource/clearsKeys/disabled`。
  - 8 个基础字段：`keyword`、`title`、`status`、`projectId`、`pipelineId`、`scene`、`subScene`、`dateRange`。
  - 三种变体：完整版（我的申请）、查询版（历史/例外查询，状态去掉 `draft`）、待办版（去掉状态）。
  - 级联声明：`projectId.clearsKeys = [pipelineId, scene, subScene]`，`scene.clearsKeys = [subScene]`。
  - 禁用声明：`pipelineId/scene` 依赖 `projectId`，`subScene` 依赖 `scene`。
  - `toExceptionPageReq(payload)`：`dateRange → startDate/endDate`，其余透传。
  - `useExceptionPageReq(getModel)`：返回 `reactive` 的 `initParams`，深度 watch，`flush: 'sync'`。
  - 四组列：通用 10 列、待办 +例外时间、历史 +审批完成时间/我的结果、路径 4 列，宽度与固定列按设计稿。
- **依赖**：T1
- **验收**：新增一个筛选项只需改配置；四个页面列的宽度、顺序一致。
- **自测点**：日期区间查询参数为 `YYYY-MM-DD`；切页后列不错位。

---

## T5 列表 Hook

- [x] **目标**：统一列表查询、重置、KeepAlive 激活刷新和详情动作后的刷新。
- **涉及文件**：`src/views/process-exception/hooks/use-exception-list.ts`
- **实现要点**：
  - 接收 `tableRef` 与可选 `onRefresh`，暴露 `{ queryParams, initParams, handleSearch, handleReset }`。
  - 初始 `queryParams.projectId` 取 `route.params.projectId`（有值才写入）。
  - `handleSearch()` 调用 `tableRef.search()`；`handleReset()` 先 `resetAll()` 再查询。
  - `onActivated`：`isActive = true`，执行 `onRefresh?.()` + `tableRef.getTableData()`。
  - `onDeactivated`：`isActive = false`。
  - `watch(refreshToken)`：仅在激活状态重新查询，避免非当前页签发请求。
- **依赖**：T4
- **验收**：切换页签后列表数据刷新，筛选条件保留；详情动作后当前列表刷新。
- **自测点**：连续快速切页不发重复请求（以真实 `onActivated` 次数为准）。

---

## T6 配置驱动搜索表单

- [x] **目标**：实现一个表单组件服务四个列表，负责渲染、级联、字典、重置，不承载业务查询。
- **涉及文件**：`src/views/process-exception/components/exception-search-form.vue`
- **实现要点**：
  - `props.fields` + `defineModel` 表单模型；`emit('search')` / `emit('reset')`；右侧 `extra` 插槽。
  - 布局：`el-form` 作为 6 列 grid，`label-position="top"`，表单项 `!mb-0 min-w-0`，日期区间 `!w-full`。
  - 控件：input → `el-input`；select → `el-select-v2`；dateRange → `el-date-picker`（`YYYY-MM-DD`）。
  - 项目下拉来自 store 并支持 `filterable`；流水线/场景/子场景由组件内部拉取与派生。
  - 项目变化重新拉取字典，并在响应后校验 `projectId` 未变化，防止竞态覆盖。
  - 字段变化执行 `clearsKeys`；重置时 input 置 `''`、其他置 `null`，项目恢复路由值，然后 emit reset。
  - KeepAlive：首次激活跳过，后续激活重拉字典，保证路径变更后场景更新。
- **依赖**：T2、T4
- **验收**：8 字段在两行内完整展示；级联与重置符合预期；无重复请求。
- **自测点**：窄屏下不出现控件截断（横向由页面滚动承接）。

---

## T7 我的申请页

- [x] **目标**：完成申请单的主入口列表与全部行级/批量写操作。
- **涉及文件**：`src/views/process-exception/my-applications.vue`
- **实现要点**：
  - `base-table` 接 `getMyApplicationPage`，列用 `EXCEPTION_LIST_COLUMNS`，`pageSize: 20`。
  - 勾选列 `selectable` 仅当 `actions.canWithdraw || actions.canDelete`。
  - 工具行：新建（`openApplication()`）、批量撤回、批量删除；无勾选禁用。
  - 行内操作：编辑/撤回/删除，按 `row.actions` 禁用，不隐藏（保证列宽稳定）。
  - 单条撤回/删除走确认；批量撤回用 `Promise.allSettled` 统计失败数。
  - 删除部分失败：`failed[]` 映射 `id → billNo`，输出「编号：原因」。
  - 操作完成统一 `handleSearch()`；新建/编辑成功通过 `emit('success')` 由容器刷新。
- **依赖**：T5、T6
- **验收**：actions 为 false 的按钮不可点；批量操作只处理有权限的行。
- **自测点**：删除 2 条成功 1 条失败时提示准确。

---

## T8 待我审批页与角标

- [x] **目标**：提供审批待办列表，并保持页签角标与列表一致。
- **涉及文件**：`src/views/process-exception/pending-approvals.vue`
- **实现要点**：
  - `base-table` 接 `getPendingList`（本地包装，匹配 `base-table` 的 request 签名）。
  - 列用 `EXCEPTION_PENDING_COLUMNS`，`startDate` 插槽展示 `开始 ~ 结束`。
  - 筛选用 `EXCEPTION_PENDING_SEARCH_FIELDS`（无状态）。
  - 无工具行、无操作列，仅申请编号可进详情。
  - `useExceptionList(..., refreshPendingTotal)`：激活或详情刷新后同步角标。
- **依赖**：T5、T6
- **验收**：审批完成后角标数减一；列表与角标口径一致。
- **自测点**：空列表时角标为 0，不显示。

---

## T9 历史审批页

- [x] **目标**：展示已处理审批记录与个人审批结果。
- **涉及文件**：`src/views/process-exception/approval-history.vue`
- **实现要点**：
  - 接 `getHistoryApplicationPage`，列用 `EXCEPTION_HISTORY_COLUMNS`。
  - 筛选用 `EXCEPTION_QUERY_SEARCH_FIELDS`（状态不含草稿）。
  - `myResult` 插槽：`approve → 同意（success）`、`reject → 拒绝（danger）`、空值 `EMPTY_VALUE`。
  - 仅查看，不提供写操作。
- **依赖**：T5、T6
- **验收**：审批完成时间与我的结果正确展示。
- **自测点**：无审批结果的记录不显示错误标签。

---

## T10 例外查询页

- [x] **目标**：提供全员例外备案查询能力。
- **涉及文件**：`src/views/process-exception/exception-search.vue`
- **实现要点**：
  - 接 `getAllApplicationPage`，列用 `EXCEPTION_LIST_COLUMNS`。
  - 筛选用 `EXCEPTION_QUERY_SEARCH_FIELDS`（无草稿）。
  - 无操作列、无工具行；申请编号可进详情（受详情 actions 限制）。
  - 与我的申请保持同一列宽与空值规范。
- **依赖**：T5、T6
- **验收**：可查到非本人申请；草稿不出现。
- **自测点**：接口未上线时页面给出统一错误提示，不白屏。

---

## T11 状态徽标与详情骨架

- [x] **目标**：实现状态徽标与详情抽屉的静态结构、数据加载和基础映射。
- **涉及文件**：`src/views/process-exception/components/exception-status-badge.vue`、`exception-detail-drawer.vue`
- **实现要点**：
  - 徽标：`status` 映射到 EP tag 类型与 `status-dot`；未知状态回退 default。
  - 抽屉：`size="95vw" destroy-on-close`，`defineExpose({ open })`，`open(id)` 重置状态后加载详情。
  - 头部：标题、单号、状态徽标；空详情回退「例外备案详情」。
  - 基本信息：3 列网格，key 112px，末尾补空位保持对齐；例外说明整行、`getCleanHtml` 后 `v-html`、内部滚动。
  - 审批记录：`approvalRecords` → 环节名（`nodeSeq → roleName`）、结论、意见、审批人、时间。
  - 跟踪进展：`tracks` → 节点名（`submit/withdraw` 特殊映射）、动作、描述、操作人、时间。
  - 提供 `refresh` / `edit` 事件出口与底部按钮占位。
- **依赖**：T1、T3
- **验收**：任意状态详情可打开；长文本不撑破布局。
- **自测点**：`description` 含 HTML 时正常渲染且被净化。

---

## T12 审批流程面板与滚动条

- [x] **目标**：把节点数据转为设计稿要求的四态流程条，并支持横向浏览。
- **涉及文件**：`exception-flow-panel.vue`、`flow-scrollbar.vue`
- **实现要点**：
  - 状态推导：撤回全 pending；退回时仅 rejected 节点保持 rejected；`approved/rejected` 按节点；`filing && seq === currentNodeSeq` 为 current；其余 pending。
  - 申请人卡片：可编辑时 pending，否则 passed。
  - 连接线：停止流转统一灰；rejected 后一段红；其余左右半段继承前后节点色；标签只在可流转且不可编辑时展示「审批中/待审批」。
  - 节点卡片宽度 `basis-[200px] min-w-[200px]`，连接段 `92×48`，横向滚动。
  - `flow-scrollbar`：内容宽度 > 视口 1px 才显示；滑块宽度按比例、最小 20px；圆点按节点中心定位；点击/拖拽/圆点跳转；监听 scroll + ResizeObserver。
- **依赖**：T11
- **验收**：五种申请状态与节点组合下颜色、连线、标签正确。
- **自测点**：节点很多时滚动条可用，当前节点自动滚入视野。

---

## T13 审批弹窗与动作闭环

- [x] **目标**：完成同意/拒绝/转移三个动作弹窗，并把详情按钮矩阵接到接口。
- **涉及文件**：`exception-opinion-dialog.vue`、`exception-transfer-dialog.vue`、`exception-detail-drawer.vue`
- **实现要点**：
  - 意见弹窗：`mode: approve | reject`；拒绝必填、200 字上限；顶部说明同意生效与拒绝退回规则。
  - 转移弹窗：平台 + 用户远程搜索 + 原因必填；平台切换清空用户；`searchToken` 丢弃过期响应；提交校验三项。
  - 详情按钮矩阵：edit / withdraw / delete / reject / approve / transfer / copyLink，全部按 `actions` 展示。
  - 撤回、删除走 `ElMessageBox.confirm`；删除成功关闭抽屉；其余动作成功后重载详情 + `emit('refresh')`。
  - `actionLoading` 全局防重复；复制链接使用 `useClipboard({ legacy: true })`。
- **依赖**：T11、T12
- **验收**：每个动作只触发一次请求；成功/失败提示准确；列表与角标刷新。
- **自测点**：拒绝不填意见无法提交；转移不选人员无法提交。

---

## T14 新建/编辑申请抽屉

- [x] **目标**：完成申请单的创建、编辑、草稿、提交与节点审批人配置。
- **涉及文件**：`components/new-application-drawer.vue`
- **实现要点**：
  - props `projectId?` / `pipelineId?`；expose `open(id?)`；`size="95%"`，关闭重置。
  - 项目上下文：`props.projectId ?? route.params.projectId`，缺失提示并终止；异步 `getExceptionProjectContext` 失败关闭抽屉。
  - 字典：组织/项目、流水线、场景（value 为 `ownerType:scene`）、子场景；编辑时对当前场景做兜底补齐。
  - 路径匹配：`productId` 按 ALL=0、PROJECT=项目、PRODUCT=组织；请求 `paths/page` `pageSize=100` 后前端精确匹配 `productId/projectId/scene/subScene/!isDelete`；未命中提示并禁用提交。
  - 节点：single 默认唯一候选人且禁用；multi 下拉；roleOnly 平台 + 远程搜索，平台切换清空。
  - 校验：流水线/场景/子场景必填；标题 ≤100；日期必填、结束≥开始、跨度≤365 天、上限今天+365；说明纯文本必填且 ≤20000；提交前校验所有节点审批人。
  - 保存：草稿不校验直接存；新建用 `create` 的 `draft` 语义；编辑先 `update`，再按需 `submit`；已撤回/已退回单据在 `actions` 允许时复用同一流程；成功关闭并 `emit('success')`。
  - TinyMCE 异步加载，含 loading 与失败占位。
- **依赖**：T2、T4、T6
- **验收**：草稿、提交、编辑、回填、路径未配置、日期越界六类场景均符合预期。
- **自测点**：编辑草稿后提交，节点审批人回填正确。

---

## T15 路径列表与路径编辑抽屉

- [x] **目标**：完成例外决策路径的增删改与节点候选人配置。
- **涉及文件**：`pattern-config.vue`、`components/path-edit-drawer.vue`
- **实现要点**：
  - 列表：`paths/page`，无筛选；节点流卡片最多展示 2 个候选人，超出 `+N` 悬浮全量；`roleOnly` 展示「申请人提交时自选」。
  - 抽屉：`size="90%"`，`v-model:visible` + `pathRow`；父页面 `v-if` 懒挂载。
  - 组织/项目：组织含「全部」(0)；组织为 0 时项目禁用并提交 0；组织变化清空项目并重拉项目。
  - 节点：1~10 个；`roleOnly` 清空候选人；候选人 >1 时锁定分配方式；single 已有候选人时禁用添加。
  - 候选人：单节点 ≤50、同节点去重、跨节点同一 `userId` 不允许重复；远程搜索带平台。
  - 保存：校验表单 + 节点规则；按数组顺序重排 `seq`；候选人只提交 `platform + userId`；统一 `updateExceptionPath`。
  - 删除：确认文案含组织/项目/场景；成功后父页面 `clearScenes()` + 刷新。
- **依赖**：T1、T2、T3
- **验收**：10 个节点、50 人边界可拦；跨节点重复可拦；编辑回填 `seq` 重排正确。
- **自测点**：删除路径后新建申请不再匹配到该路径。

---

## T16 页签容器整合

- [x] **目标**：把五个页面、两个共享抽屉、权限、query 参数和刷新信号整合成单入口。
- **涉及文件**：`process-exception.vue`
- **实现要点**：
  - `allTabs` 用 `defineAsyncComponent`；`tabList` 按 `ops_filing_path` 过滤；`activeTab` 读取 `?tab=` 并校验权限。
  - 页签 UI：高 48px、白底、下边框、激活主色下划线；待办角标 `99+`。
  - 内容区 `KeepAlive`，`component :is` + `:key="activeTab"`。
  - provide `openDetail / openApplication / refreshToken`。
  - 挂载：刷新待办总数、预加载项目、处理 `?id=` 并清理 URL。
  - 详情 `@refresh` 递增 token、`@edit` 打开编辑；新建/编辑 `@success` 递增 token。
- **依赖**：T7~T15
- **验收**：单入口可完成全流程；权限、query、刷新、缓存均正常。
- **自测点**：`?id=` 刷新页面只打开一次详情。

---

## T17 样式统一与收尾验证

- [x] **目标**：按设计稿统一列表卡片、抽屉、流程条与状态色，完成静态检查和边界收口。
- **涉及文件**：`style.less`、各页面/组件 `<style scoped>`、模板类名
- **实现要点**：
  - 页面统一 `#f2f3f5` 背景 + 单卡片布局（筛选区 / 工具行 / 表格）。
  - 分页内边距、表格最小高度、状态徽标 default/canceled 覆盖写入 `style.less`。
  - 流程节点、连接线、滚动条、抽屉头部/底部的设计稿尺寸与颜色落地。
  - 空值统一 `EMPTY_VALUE`；长文本 tooltip；表格操作列内嵌写法统一。
  - 导入路径、未使用变量、类型断言、可选链清理；单文件 ≤400 行。
- **依赖**：T16
- **验收**：五个页面视觉一致；无控制台告警；类型检查与 Lint 通过。
- **自测点**：窄屏、长标题、空列表、超长说明四种极端数据下布局不破。

---

## 端到端验收路径

1. 进入 `/process-exception` → 默认「我的申请」→ 新建草稿 → 再次编辑并提交。
2. 切换到具备审批权限的用户 → 「待我审批」角标 +1 → 打开详情 → 同意。
3. 「历史审批」看到我的审批结果；「例外查询」可查到该单。
4. 详情内验证撤回/删除/转移在不同 `actions` 下的显隐。
5. 路径配置新增一条路径 → 返回新建申请，场景下拉与路径匹配生效。
6. 删除该路径 → 新建申请提示未配置路径。

## 验证记录

以下为交付时记录的历史验证结果：

- `npm run type-check`：通过（exit 0）。
- `npm run lint`：通过（0 warnings / 0 errors，范围为本模块改动文件）。
- 单文件行数：模块内 `.vue` 文件均 ≤400 行。
- 手工自测：页签切换、筛选与重置、详情打开、审批动作、路径编辑抽屉、KeepAlive 激活刷新。

## 未覆盖项

- 模块未新增单元测试；状态推导、路径匹配、分页参数转换等纯逻辑目前依赖手工验证。
- 本次文档整理未重新执行构建、类型检查与 Lint，结果以交付时记录为准。
