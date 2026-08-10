## Why

发布评审列表当前只展示评审状态与基本信息，用户无法在列表页直接查看某个评审单的操作历史记录（谁、在什么时间、做了什么操作），缺乏操作可追溯性。需要在评审列表的操作列新增"操作历史"入口，让用户快速查看评审单的完整操作轨迹。

## What Changes

- 在 `publishReviewColumns`（`config.ts`）的操作列（`operation` 列）新增一个"操作历史"图标按钮，点击后弹出弹窗。
- 弹窗内渲染一个分页表格，表头为：操作人（`operator_name`）、操作名称（`operation_name`）、操作时间（`operation_time`）。
- 表格支持分页（页码切换 + 每页条数切换），数据通过 `POST /base/queryReviewHistoryPage` 接口按 `reviewId` + 分页参数获取。
- 在前端 API 层（`PlatformRelease/url.ts` + `PlatformRelease/api.ts`）注册该接口的 URL 常量与请求函数。

## Capabilities

### New Capabilities

- `review-operation-history`: 发布评审操作历史查看能力。定义评审列表操作列中"操作历史"入口的显示规则、弹窗结构与分页表格的列契约，以及通过分页接口获取操作记录的调用契约。

### Modified Capabilities

无。`openspec/specs/` 当前仅有 `release-review-withdraw`（评审详情页回撤），与本次操作历史查看属于不同页面、不同行为，无 spec 级需求变更。

## Impact

- **受影响代码**：
  - `openlibing-web/apps/web-openlibing/src/views/Publish/publishReview/config.ts`：在 `publishReviewColumns` 的操作列 `icons` 数组中新增"操作历史"图标项（含 `fnName`、`auth`、`operationModule`），并新增 `operationHistoryColumns` 列定义（操作人/操作名称/操作时间三列）。
  - `openlibing-web/apps/web-openlibing/src/views/Publish/publishReview/index.vue`：新增操作历史弹窗（`el-dialog` + `publishTable`），新增弹窗状态（`showOperationHistoryDialog`）、当前评审单 ID、分页状态、请求函数；在 `functionsMap` 中注册 `openOperationHistoryDialog` 处理器。
  - `openlibing-web/apps/web-openlibing/src/api/PlatformRelease/url.ts`：新增 `QUERY_REVIEW_HISTORY_PAGE` URL 常量（`PLATFORM_RELEASE + '/base/queryReviewHistoryPage'`，与已有的 `GET_PUBLISH_HISTORY` 同 `/base/` 前缀分组）。
  - `openlibing-web/apps/web-openlibing/src/api/PlatformRelease/api.ts`：新增 `queryReviewHistoryPage` 请求函数（`apiClient.post`）。
- **受影响接口**：调用后端已有接口 `POST /base/queryReviewHistoryPage`（query 参数：`projectId`、`userId`；body：`reviewId`、`pageNum`、`pageSize`），前端新增 API 注册，无后端改动。
- **不受影响**：评审列表的数据加载逻辑、评审详情页、评审历史弹窗（已有的"评审历史"入口查询的是评审项历史 `queryReviewHistory`，与操作历史是不同数据源）、新增/复制/删除评审流程。
- **风险**：操作历史弹窗与已有的"评审历史"弹窗（`showHistoryDialog`）名称相近但数据源不同，需在 UI 文案与变量命名上区分（"操作历史" vs "评审历史"），避免用户与开发者混淆。