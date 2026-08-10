## 1. API 层注册操作历史分页接口

- [x] 1.1 在 `openlibing-web/apps/web-openlibing/src/api/PlatformRelease/url.ts` 中新增常量 `QUERY_REVIEW_HISTORY_PAGE = PLATFORM_RELEASE + '/base/queryReviewHistoryPage'`，放在 `GET_PUBLISH_HISTORY` 附近（同 `/base/` 前缀分组）。
- [x] 1.2 在 `openlibing-web/apps/web-openlibing/src/api/PlatformRelease/api.ts` 中新增请求函数 `export const queryReviewHistoryPage: RequestFunc = (a, s) => apiClient.post(urls.QUERY_REVIEW_HISTORY_PAGE, a, s);`，放在 `getPublishHistory` 附近。

## 2. 列定义与操作入口配置

- [x] 2.1 在 `openlibing-web/apps/web-openlibing/src/views/Publish/publishReview/config.ts` 中新增 `operationHistoryColumns`（`ref`），包含三列：操作人（`prop: 'operator_name'`）、操作名称（`prop: 'operation_name'`）、操作时间（`prop: 'operation_time'`，`type: 'date'`），并在文件末尾 `export` 中导出。
- [x] 2.2 在 `config.ts` 的 `publishReviewColumns` 操作列 `icons` 数组中新增一项：`{ label: '操作历史', icon: 'iconfont icon-rili' 或其他合适图标, fnName: 'openOperationHistoryDialog', auth: 'platform_release_base', type: 'icon', operationModule: '查看操作历史' }`，放在"评审历史"图标之后。

## 3. index.vue 实现操作历史弹窗

- [x] 3.1 在 `index.vue` 的 `<script setup>` 中从 `@/api/PlatformRelease/api.js`（或 `.ts`，与现有导入风格一致）导入 `queryReviewHistoryPage`；从 `./config.ts` 导入 `operationHistoryColumns`。
- [x] 3.2 新增弹窗状态变量：`showOperationHistoryDialog`（`ref(false)`）、`operationHistoryList`（`ref([])`）、`operationHistoryPagination`（`ref({ pageNum: 1, pageSize: 10, pageSizes: [10, 20, 50, 100], total: 0 })`）、`currentOperationHistoryReviewId`（`ref(null)`）。
- [x] 3.3 新增 `getOperationHistoryData` 函数：调用 `queryReviewHistoryPage({ params: { projectId: app.projectInfo?.projectId, userId: app?.user?.userId }, data: { reviewId: currentOperationHistoryReviewId.value, pageNum: operationHistoryPagination.value.pageNum, pageSize: operationHistoryPagination.value.pageSize } })`，成功时（`code === 200`）从 `data.list` / `data.total` 填充 `operationHistoryList` 与 `operationHistoryPagination.total`，失败时清空列表与 total 并 `ElMessage.error`。
- [x] 3.4 新增 `openOperationHistoryDialog` 函数（接收 `(prop, rowInfo)`）：设置 `currentOperationHistoryReviewId.value = rowInfo.id`、重置 `operationHistoryPagination.pageNum = 1`、`showOperationHistoryDialog.value = true`，然后调用 `getOperationHistoryData()`。
- [x] 3.5 新增 `operationHistoryCurrentPageChange(val)` 与 `operationHistorySizeChange(val)` 函数：分别更新 `pageNum` / `pageSize`（sizeChange 时重置 `pageNum = 1`），然后调用 `getOperationHistoryData()`。
- [x] 3.6 在 `functionsMap` 中注册 `openOperationHistoryDialog: (prop, rowInfo) => openOperationHistoryDialog(prop, rowInfo)`。
- [x] 3.7 在模板中已有"评审历史"弹窗之后新增操作历史弹窗：`<el-dialog v-model="showOperationHistoryDialog" title="操作历史" width="63%" class="dialog-common" :close-on-click-modal="false" @close="showOperationHistoryDialog = false">`，内部放 `<publishTable :data-list="operationHistoryList" :columns="operationHistoryColumns" :pagination="operationHistoryPagination" @current-page-change="operationHistoryCurrentPageChange" @size-change="operationHistorySizeChange" />`。

## 4. 验证

- [x] 4.1 对改动的文件（`url.ts`、`api.ts`、`config.ts`、`index.vue`）运行 lint / 类型检查，确认无新增错误。
- [x] 4.2 手动验证：① 操作列出现"操作历史"图标；② 点击图标弹出"操作历史"弹窗并自动加载第一页数据；③ 表格展示操作人/操作名称/操作时间三列；④ 切换页码触发新请求；⑤ 切换每页条数回到第一页；⑥ 接口失败时提示错误且不阻塞弹窗；⑦ 关闭弹窗不影响评审列表数据。