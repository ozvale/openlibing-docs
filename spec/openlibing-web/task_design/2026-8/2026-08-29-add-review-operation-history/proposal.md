## Why

发布评审详情页（`reviewDetail.vue`）当前展示了基本信息、制品信息、附件信息、评审信息、发布信息、漏洞信息等模块，但缺少该评审单的操作历史记录。用户在详情页无法直观看到"谁、在什么时间、对该评审单做了什么操作"的操作轨迹，缺乏详情页级别的操作可追溯性。需要在详情页底部新增一个内联的操作历史模块，让用户在浏览评审详情时即可查看完整操作轨迹，无需跳转或弹窗。

## What Changes

- 在 `reviewDetail.vue` 底部新增"操作历史"模块（`detail-part` + `reviewPartHeader` 可折叠头），结构与页面已有的"基本信息""制品信息"等模块保持一致，默认展开。
- 模块内使用已有的 `publishTable` 组件渲染一个支持分页的表格，表头三列：操作名称（`operationName`）、操作人（`operatorName`）、操作时间（`operationTime`，`type: 'date'`）。
- 分页行为：页码切换 + 每页条数切换（切换每页条数时回到第一页），通过 `publishTable` 的 `pagination` prop 与 `currentPageChange` / `sizeChange` 事件驱动。
- 数据通过 `POST /base/queryReviewHistoryPage` 接口获取，请求 query 参数含 `projectId` 与 `userId`，body 含 `reviewId`、`pageNum`、`pageSize`。
- 接口调用时机设计：
  - 详情数据首次加载成功且存在 `reviewId` 时，拉取操作历史第一页；
  - 详情页内的状态变更操作（保存评审、发起评审、撤回评审、发布决策、发布漏洞公告）成功后，重置到第一页刷新操作历史；
  - 分页切换时按新页码/每页条数拉取对应页；
  - **不**在 20s 状态轮询（`startReleaseInterval`）中重复拉取操作历史，避免与状态轮询耦合。
- 在前端 API 层注册该接口的 URL 常量与请求函数。

## Capabilities

### New Capabilities

- `review-detail-operation-history`: 发布评审详情页操作历史查看能力。定义详情页底部操作历史模块的显示规则、可折叠头行为、分页表格的列契约、通过分页接口获取操作记录的调用时机与可观察行为。

### Modified Capabilities

无。本次变更仅新增详情页内联模块，不改变其他已有行为。

## Impact

- **受影响代码**：
  - `openlibing-web/apps/web-openlibing/src/views/Publish/publishReview/detail/reviewDetail.vue`：在模板底部新增"操作历史"模块（`detail-part` + `reviewPartHeader` + `publishTable`）；在 `<script setup>` 新增操作历史状态（列表、分页）、请求函数、分页事件处理、在详情加载成功与各状态变更操作成功回调中触发刷新。
  - `openlibing-web/apps/web-openlibing/src/views/Publish/publishReview/detail/components/`：无需新增组件，复用已有的 `publishTable` 与 `reviewPartHeader`。
  - `openlibing-web/apps/web-openlibing/src/views/Publish/publishReview/config.ts`：新增 `operationHistoryColumns`（操作名称/操作人/操作时间三列），并导出。
  - `openlibing-web/apps/web-openlibing/src/api/url.ts`：新增 `GET_PUBLISH_REVIEW_OPERATION_HISTORY` URL 常量（`PLATFORM_RELEASE + '/base/queryReviewHistoryPage'`，与已有 `/base/` 前缀接口同组）。
  - `openlibing-web/apps/web-openlibing/src/api/api.ts`：新增 `getPublishReviewOperationHistory` 请求函数（`apiClient.post`），与已有发布评审接口同文件。
- **受影响接口**：调用后端已有接口 `POST /base/queryReviewHistoryPage`（query：`projectId`、`userId`；body：`reviewId`、`pageNum`、`pageSize`），前端新增 API 注册，无后端改动。
- **不受影响**：评审详情页已有的基本信息/制品/附件/评审/发布/漏洞模块及其数据加载逻辑、20s 状态轮询、复制评审、保存/发起/撤回/发布决策/漏洞公告的业务逻辑本身。
- **风险**：
  - Apifox 中该接口的响应 `jsonSchema` 为空对象，响应列表项字段名（`operationName`/`operatorName`/`operationTime`）需在联调时与后端确认，若字段名不符需在 `config.ts` 列定义中调整 `prop`。
  - 操作历史拉取需与 20s 状态轮询解耦，避免每次轮询重复请求操作历史造成冗余流量；本次设计通过"仅在详情首次加载与状态变更操作成功后刷新"控制调用时机。
