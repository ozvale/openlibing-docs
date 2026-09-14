## Context

发布评审详情页 `reviewDetail.vue` 是一个以"模块折叠头 + 内容区"为结构模式的长页面（基本信息/制品信息/附件信息/评审信息/发布信息/漏洞信息），每个模块用 `reviewPartHeader`（`prop` + `:is-hide` + `@toggle-part`）驱动折叠，折叠态存于 `isPartHide` ref。页面已有 20s 状态轮询（`startReleaseInterval`/`clearReleaseInterval`），当 `reviewStatus` 处于发布中等执行态时轮询 `getDetailData()` 刷新状态。详情数据通过 `getPublishReviewDetailById` 获取，成功后会回写 URL `reviewId`。

页面已引入通用表格组件 `publishTable`（`../components/publishTable.vue`），该组件支持 `:data-list`、`:columns`、`:pagination`、`:hide-pagination`，并对外抛出 `currentPageChange` 与 `sizeChange` 事件；列定义集中在 `../config.ts`，分页对象结构约定为 `{ pageNum, pageSize, pageSizes, total }`，分页接口响应约定为 `{ code, data: { list, total } }`（参考列表页 `getPublishReview` 用法）。前端 API 集中在 `@/api/api.ts`（函数）与 `@/api/url.ts`（URL 常量，按 `PLATFORM_RELEASE + '/base/...'` 分组）。

后端接口 `POST /base/queryReviewHistoryPage` 已存在于 Apifox（项目 `openlibing-platform-release`，endpoint id 497499199），但响应 `jsonSchema` 为空对象，请求 body 示例为 `{ reviewId, pageNum, pageSize }`，query 参数含 `userId`、`projectId`。

## Goals / Non-Goals

**Goals:**

- 在详情页底部以与既有模块一致的结构新增"操作历史"内联模块，复用 `publishTable` 与 `reviewPartHeader`，零新组件。
- 复用详情页已有的 `reviewId`、`app.projectInfo.projectId`、`app.user.userId` 上下文，无需额外数据来源。
- 操作历史请求与 20s 状态轮询彻底解耦，只在有意义的时机（首次加载 / 状态变更后 / 分页切换）请求。

**Non-Goals:**

- 不改变 20s 状态轮询的逻辑与触发条件。
- 不改变保存/发起/撤回/发布决策/发布漏洞公告等业务逻辑本身，仅在它们的成功回调后追加操作历史刷新。
- 不在列表页（`publishReview/index.vue`）增加任何操作历史入口——本设计仅针对详情页。
- 不引入新的 UI 组件库或新依赖。

## Decisions

### Decision 1: 模块放置位置与结构

**选择**：在 `reviewDetail.vue` 模板末尾、`buttons` 区之前新增一个 `detail-part`，结构与既有模块完全一致（`reviewPartHeader` + `v-show` 内容区 + `publishTable`），`isPartHide` 增加默认展开项。

**理由**：详情页所有同级模块都遵循这一结构，保持一致性可让用户预期一致、折叠行为复用现有 `togglePartShow`，无需新增交互代码。放在 `buttons` 之前保证操作历史作为信息展示模块出现在页面主体内、操作按钮区之下不被覆盖。

**备选**：放在 `buttons` 之后——会让"保存/发起评审"按钮脱离主体内容流，且按钮区当前仅在 `reviewStatus === -1`（新建态）出现，放其后会导致操作历史在新建态时视觉位置漂浮，故不采用。

### Decision 2: 列定义归属与字段命名

**选择**：在 `config.ts` 新增 `operationHistoryColumns`（`ref`）三列：操作名称（`prop: 'operationName'`）、操作人（`prop: 'operatorName'`）、操作时间（`prop: 'operationTime'`, `type: 'date'`），并在 `export` 中导出；`reviewDetail.vue` 从 `config.ts` 导入使用。

**理由**：详情页所有列定义都集中在 `config.ts`（`publishWarehouseColumns`、`publishHistoryColumns` 等），集中管理便于统一调整；`type: 'date'` 复用 `publishTable` 内置的日期渲染（带日历图标），与详情页其他日期列风格一致。字段名采用 camelCase，与 `config.ts` 既有列（`itemContent`/`reviewerName`/`createTime`）命名风格一致。

**备选**：直接在 `reviewDetail.vue` 内联列定义——破坏集中管理约定，且详情页其他表格都从 `config.ts` 引入，不一致，故不采用。

**字段名风险**：Apifox 响应 `jsonSchema` 为空，`operationName`/`operatorName`/`operationTime` 为依据命名风格推断的约定，联调时若后端返回字段名不同（如 `operation_name` 蛇形），只需调整 `config.ts` 中 `prop`，不影响其他代码。

### Decision 3: API 注册位置

**选择**：在 `@/api/url.ts` 新增 `GET_PUBLISH_REVIEW_OPERATION_HISTORY = PLATFORM_RELEASE + '/base/queryReviewHistoryPage'`，放在同 `/base/` 前缀接口（如 `GET_PUBLISH_REVIEW_DETAIL_BY_ID`）附近；在 `@/api/api.ts` 新增 `export const getPublishReviewOperationHistory: RequestFunc = (a, s) => apiClient.post(urls.GET_PUBLISH_REVIEW_OPERATION_HISTORY, a, s);`，与 `getPublishReviewDetailById` 等发布评审接口同文件。

**理由**：`reviewDetail.vue` 已从 `@/api/api` 导入 `getPublishReviewDetailById` 等函数，新增接口同文件导入路径最短、与既有发布评审接口内聚；`url.ts` 按 `/base/` 前缀分组是既有约定。

**备选**：放在 `@/api/PlatformRelease/api.ts`——`reviewDetail.vue` 当前未从该路径导入，会引入新导入路径，且 `@/api/api.ts` 已是详情页所用发布评审接口的聚合入口，故不采用。

### Decision 4: 调用时机与防重复策略

**选择**：

1. 首次加载：在 `getDetailData` 成功回调内、当确认存在有效 `reviewId`（响应 `data.id` 或 URL `reviewId`）时，调用一次操作历史第一页；用一个 `isOperationHistoryLoaded` ref 标记防重复，避免轮询导致的重复首拉。
2. 状态变更后：在 `saveReview`/`submitReview`/`handleWithdrawReview`/`handlePublishDecision`/`handlePublishVulnNotice` 的成功 `ElMessage` `onClose` 回调中（这些回调原本就调用 `getDetailData()`），追加 `refreshOperationHistory()`（重置 `pageNum=1` 后请求）。
3. 分页切换：`operationHistoryCurrentPageChange` 更新 `pageNum` 后请求；`operationHistorySizeChange` 重置 `pageNum=1` 并更新 `pageSize` 后请求。

**理由**：状态变更操作的 `onClose` 回调已统一调用 `getDetailData()` 刷新详情，在此时机一并刷新操作历史符合"操作发生后即可见新记录"的语义；`isOperationHistoryLoaded` 防重复避免轮询场景下重复首拉（轮询只刷详情数据，不刷操作历史）。

**备选**：把操作历史请求放进 `getDetailData` 每次都调——会被 20s 轮询高频触发，产生大量冗余请求，违背"操作历史是低频变更数据"的事实，故不采用。备选：用 `watch(reviewId)` 驱动——`reviewId` 来自 URL，且 `getDetailData` 成功后还会 `router.push` 写回 `reviewId`，`watch` 会在 URL 写回时二次触发；同时与既有命令式数据加载风格不一致，故不采用。

### Decision 5: 复制评审场景的处理

**选择**：复制评审（URL 含 `copySourceReviewId`）新建评审单时，后端在复制时已创建新评审记录并分配 `reviewId`，同时记录一条"新建"操作。因此进入详情页时该新 `reviewId` 已存在，操作历史按 Decision 1 的首次加载逻辑正常拉取第一页，表格首条记录为"新建"操作；无需对复制场景做特殊空状态处理。

**理由**：复制操作在后端即创建新评审单并记录"新建"操作历史，新评审单的 `reviewId` 在进入详情页时已可用，操作历史属于该新评审单而非源评审单，直接拉取语义正确，无需等待"保存"。

**备选**：复制场景展示空状态待保存后刷新——与后端"复制即创建并记录新建操作"的事实不符，会导致用户看不到本应存在的"新建"记录，故不采用。

## Risks / Trade-offs

- **[接口响应字段名未知]** → Apifox 响应 `jsonSchema` 为空，`operationName`/`operatorName`/`operationTime` 为推断值。**缓解**：联调阶段用一次真实请求确认字段名，若不符只改 `config.ts` 的 `prop`，列定义集中可控。
- **[分页响应结构未知]** → 假设响应为 `{ code, data: { list, total } }`（与 `getPublishReview` 一致）。**缓解**：若后端返回 `{ data: { rows, total } }` 等异构结构，在 `getOperationHistoryData` 内做一次兼容映射即可，不影响组件层。
- **[状态变更后刷新依赖 `onClose` 时机]** → `ElMessage` 的 `onClose` 在消息关闭时触发，若用户快速操作可能延迟刷新。**缓解**：与详情数据刷新（`getDetailData`）共用同一 `onClose` 时机，保持两者一致；若需更及时可改用 `.then` 内同步刷新，但当前与既有模式保持一致优先。
- **[轮询与首拉标记耦合]** → `isOperationHistoryLoaded` 在组件卸载或切换评审单时需重置，否则切换评审单后不会重新首拉。**缓解**：在 `watch(app.projectInfo)`（切换项目触发详情重载）中重置该标记；详情页是路由级组件，切换评审单会重新挂载，标记随之重建，风险低。

## Migration Plan

- 纯前端增量改动，无数据迁移、无后端改动，部署即生效。
- 回滚策略：删除新增的"操作历史"模块模板段、`getOperationHistoryData` 等函数、`config.ts` 的 `operationHistoryColumns`、`url.ts`/`api.ts` 的新增常量与函数即可完全回滚，不影响其他功能。

## Open Questions

- 操作历史列表项是否需要按 `operationTime` 倒序展示？当前假设后端已按时间倒序返回分页数据，若后端默认正序需在前端排序或要求后端调整。该问题不改变 spec、列定义或调用时机，可在联调时确认。
