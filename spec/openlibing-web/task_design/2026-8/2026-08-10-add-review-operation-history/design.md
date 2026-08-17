## Context

发布评审列表页（`publishReview/index.vue`）已有成熟的弹窗 + 分页表格模式：评审历史弹窗（`showHistoryDialog`）通过 `publishTable` 组件渲染 `publishHistoryColumns` 列定义，数据来自 `getPublishHistory`（`GET /base/queryReviewHistory`，不分页）。本次新增的"操作历史"弹窗在交互结构上与之同构（弹窗 + 表格 + 数据请求），但数据源不同（`POST /base/queryReviewHistoryPage`，分页），因此需要独立的弹窗状态与分页逻辑，不能复用评审历史的无分页请求路径。

API 层（`PlatformRelease/url.ts` + `api.ts`）已有统一的 URL 常量 + 请求函数注册模式，同 `/base/` 前缀下已有 `GET_PUBLISH_HISTORY`，新增 `queryReviewHistoryPage` 沿用相同注册位置与方法风格。

## Goals / Non-Goals

**Goals:**

- 弹窗内表格复用已有 `publishTable.vue` 组件，支持分页（页码切换 + 每页条数切换），与评审列表主表格的交互体验一致。
- 弹窗状态与已有"评审历史"弹窗完全隔离，避免数据源混淆。
- API 注册遵循现有 `PlatformRelease` 模块的模式，保持一致性。

**Non-Goals:**

- 不修改已有的"评审历史"弹窗逻辑与 `getPublishHistory` 接口。
- 不对操作历史表格做排序、筛选、导出等扩展（需求未提及）。
- 不修改 `publishTable.vue` 通用组件（它已支持分页 props，直接传入即可）。

## Decisions

### 决策 1：复用 `publishTable.vue` 渲染弹窗表格

**选择**：弹窗内表格复用 `publishTable.vue`，通过 `:data-list`、`:columns`、`:pagination` props 传入数据，监听 `@current-page-change` 与 `@size-change` 事件触发分页请求。

**理由**：`publishTable.vue` 已封装 `el-table` + `el-pagination` 的分页逻辑，评审历史弹窗也是这样用的（只是传了 `:hidePagination="true"`）。复用它可零成本获得分页能力、空状态占位、列渲染一致性。

**备选**：直接在弹窗内写 `el-table` + `el-pagination`。放弃——会与主表格的样式与交互产生分歧，增加维护成本。

### 决策 2：弹窗状态独立，不复用评审历史弹窗的状态

**选择**：在 `index.vue` 新增一套独立的状态变量：`showOperationHistoryDialog`、`operationHistoryList`、`operationHistoryPagination`（含 `pageNum`、`pageSize`、`pageSizes`、`total`）、`currentOperationHistoryReviewId`，与已有的 `showHistoryDialog` / `historyList` 完全隔离。

**理由**：两个弹窗数据源不同（`queryReviewHistory` 不分页 vs `queryReviewHistoryPage` 分页）、列定义不同、参数不同。复用状态会导致条件分支扩散到所有相关函数，违反职责单一原则。

**备选**：合并为一套弹窗状态，通过 `dialogMode` 区分。放弃——会让 `publishTable` 的 props 绑定变成三元表达式，可读性差且容易引入 bug。

### 决策 3：API 注册为 POST，参数走 query + body 双通道

**选择**：在 `url.ts` 新增 `QUERY_REVIEW_HISTORY_PAGE = PLATFORM_RELEASE + '/base/queryReviewHistoryPage'`，放在 `GET_PUBLISH_HISTORY` 附近。在 `api.ts` 新增 `queryReviewHistoryPage: RequestFunc = (a, s) => apiClient.post(urls.QUERY_REVIEW_HISTORY_PAGE, a, s)`。调用时 `{ params: { projectId, userId }, data: { reviewId, pageNum, pageSize } }`。

**理由**：Apifox 文档定义该方法为 `POST`，query 参数为 `projectId` + `userId`，body 为 `reviewId` + `pageNum` + `pageSize`。这与 `getPublishReview` 的调用模式完全一致（`{ params: {...}, data: {...} }`），`ApiClient` 已支持该参数结构。`userId` 从 `app.user.userId` 获取（与评审历史弹窗中 `getPublishHistory` 不传 `userId` 不同，本次按文档要求显式传递）。

**备选**：把 `reviewId` 也放到 query。放弃——与 Apifox 文档的参数位置不符。

### 决策 4：列定义放在 `config.ts`，与 `publishHistoryColumns` 并列导出

**选择**：在 `config.ts` 新增 `operationHistoryColumns`（三列：操作人 `operator_name`、操作名称 `operation_name`、操作时间 `operation_time`），导出后在 `index.vue` 导入。

**理由**：列定义集中管理是现有模式（`publishReviewColumns`、`publishHistoryColumns` 等都在 `config.ts`）。集中放置便于统一调整列顺序与样式，避免在 Vue 组件中内联散列配置。

### 决策 5：操作入口通过 `functionsMap` 路由，沿用已有事件机制

**选择**：在 `publishReviewColumns` 的操作列 `icons` 数组中新增一项 `{ label: '操作历史', icon: 'iconfont icon-...', fnName: 'openOperationHistoryDialog', auth: 'platform_release_base', type: 'icon', operationModule: '查看操作历史' }`，在 `functionsMap` 中注册 `openOperationHistoryDialog` 处理器，复用已有的 `handleCellClick` → `functionsMap[fnName]` 路由机制。

**理由**：这是操作列所有图标（复制、评审历史、删除）的统一路由方式，新增入口必须遵循同一机制，否则需要改 `publishTable.vue` 的事件分发逻辑，成本不可接受。

## Risks / Trade-offs

- **[风险] "操作历史"与"评审历史"文案易混** → 弹窗标题用"操作历史"（区别于已有的"评审历史"），变量命名统一加 `OperationHistory` 前缀，`fnName` 用 `openOperationHistoryDialog`（区别于已有的 `openHistoryDialog`）。
- **[风险] 接口响应结构未在 Apifox 中定义 jsonSchema** → 响应体按平台统一分页结构 `{ code, data: { list, total } }` 处理（与 `getPublishReview` 响应结构一致）。若后端实际返回结构不同，在 apply 阶段通过实际响应验证并调整取值路径。
- **[风险] `userId` 传值** → Apifox 文档标注 `userId` 为 query 参数且非必填，但示例值为完整用户 ID 字符串。前端从 `app.user.userId` 取值传入；若该字段在当前应用上下文中不可用，降级为不传（接口应仍可工作，因为后端可通过会话/token 解析用户）。
