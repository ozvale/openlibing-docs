## 1. API 层注册操作历史分页接口

- [x] 1.1 在 `openlibing-web/apps/web-openlibing/src/api/url.ts` 中新增常量 `export const GET_PUBLISH_REVIEW_OPERATION_HISTORY = PLATFORM_RELEASE + '/base/queryReviewHistoryPage';`，放在 `/base/` 前缀接口（如 `GET_PUBLISH_REVIEW_DETAIL_BY_ID`）附近。
- [x] 1.2 在 `openlibing-web/apps/web-openlibing/src/api/api.ts` 中新增请求函数 `export const getPublishReviewOperationHistory: RequestFunc = (a, s) => apiClient.post(urls.GET_PUBLISH_REVIEW_OPERATION_HISTORY, a, s);`，放在 `getPublishReviewDetailById` 等发布评审接口附近。

## 2. 列定义

- [x] 2.1 在 `openlibing-web/apps/web-openlibing/src/views/Publish/publishReview/config.ts` 中新增 `const operationHistoryColumns = ref([...])`，包含三列：操作名称（`prop: 'operationName'`）、操作人（`prop: 'operatorName'`）、操作时间（`prop: 'operationTime'`, `type: 'date'`）。
- [x] 2.2 在 `config.ts` 文件末尾的 `export { ... }` 语句中加入 `operationHistoryColumns` 导出。

## 3. reviewDetail.vue 操作历史状态与请求逻辑

- [x] 3.1 在 `reviewDetail.vue` 的 `<script setup>` 导入区，从 `@/api/api` 导入 `getPublishReviewOperationHistory`，从 `../config.ts` 导入 `operationHistoryColumns`（与既有 `publishWarehouseColumns` 导入同行）。
- [x] 3.2 新增操作历史状态变量：`operationHistoryList`（`ref([])`）、`operationHistoryPagination`（`ref({ pageNum: 1, pageSize: 10, pageSizes: [10, 20, 50, 100], total: 0 })`）、`isOperationHistoryLoaded`（`ref(false)`，防轮询重复首拉）。
- [x] 3.3 新增 `getOperationHistoryData` 函数：调用 `getPublishReviewOperationHistory({ params: { projectId: app.projectInfo?.projectId, userId: app?.user?.userId }, data: { reviewId: route.query.reviewId || dataList.value?.id || '', pageNum: operationHistoryPagination.value.pageNum, pageSize: operationHistoryPagination.value.pageSize } }, { enabledAuth: active.value })`，成功（`code === 200`）时从 `data.list`/`data.total` 填充列表与 `total`，失败或异常时清空列表、`total=0` 并 `ElMessage.error`。
- [x] 3.4 新增 `refreshOperationHistory` 函数：重置 `operationHistoryPagination.value.pageNum = 1`，调用 `getOperationHistoryData()`（用于状态变更后刷新）。
- [x] 3.5 新增 `operationHistoryCurrentPageChange(val)` 与 `operationHistorySizeChange(val)`：前者更新 `pageNum` 后请求；后者更新 `pageSize`、重置 `pageNum=1` 后请求。

## 4. 接口调用时机接入

- [x] 4.1 在 `getDetailData` 的成功回调（`code === 200` 分支）内，当存在有效 `reviewId`（`route.query.reviewId` 或 `data.id`）且 `!isOperationHistoryLoaded.value` 时，置 `isOperationHistoryLoaded.value = true` 并调用 `getOperationHistoryData()`；不在每次轮询触发时重复调用。
- [x] 4.2 在 `saveReview` 成功 `ElMessage` 的 `onClose` 回调中（已有 `getDetailData()` 调用处）追加 `refreshOperationHistory()`。
- [x] 4.3 在 `submitReview` 成功 `ElMessage` 的 `onClose` 回调中追加 `refreshOperationHistory()`。
- [x] 4.4 在 `handleWithdrawReview` 成功 `ElMessage` 的 `onClose` 回调中追加 `refreshOperationHistory()`。
- [x] 4.5 在 `handlePublishDecision` 成功 `ElMessage` 的 `onClose` 回调中追加 `refreshOperationHistory()`。
- [x] 4.6 在 `handlePublishVulnNotice` 成功 `ElMessage` 的 `onClose` 回调中追加 `refreshOperationHistory()`。
- [x] 4.7 在 `watch(() => app.projectInfo)` 回调中（项目切换触发详情重载前）重置 `isOperationHistoryLoaded.value = false`，确保切换评审单/项目后可重新首拉。

## 5. reviewDetail.vue 操作历史模块模板

- [x] 5.1 在 `reviewDetail.vue` 模板中、`buttons` 区（`<div class="buttons" ...>`）之前新增"操作历史"模块：`<div class="detail-part">` 内放 `<reviewPartHeader label="操作历史" prop="operationHistory" :is-hide="isPartHide.operationHistory" @toggle-part="togglePartShow" />` + `<div v-show="!isPartHide.operationHistory" class="part"><publishTable :data-list="operationHistoryList" :columns="operationHistoryColumns" :pagination="operationHistoryPagination" @current-page-change="operationHistoryCurrentPageChange" @size-change="operationHistorySizeChange" /></div>`。
- [x] 5.2 在 `isPartHide` ref 初始对象中新增 `operationHistory: false`（默认展开），与既有 `baseInfo: false` 同级。

## 6. 验证

- [x] 6.1 对改动文件（`url.ts`、`api.ts`、`config.ts`、`reviewDetail.vue`）运行 lint / 类型检查，确认无新增错误。
- [x] 6.2 手动验证：① 详情页底部出现"操作历史"模块且默认展开；② 模块头可折叠/展开；③ 表格展示操作名称/操作人/操作时间三列；④ 进入已存在评审单详情时自动加载第一页；⑤ 切换页码触发新请求；⑥ 切换每页条数回到第一页；⑦ 保存/发起/撤回/发布决策/发布漏洞公告成功后操作历史自动回到第一页刷新；⑧ 20s 状态轮询期间操作历史不重复请求；⑨ 复制新建评审单时操作历史正常加载第一页，首条记录为"新建"操作；⑩ 接口失败时提示错误且不阻塞详情页其他模块。
- [x] 6.3 联调确认接口响应列表项字段名与 `operationHistoryColumns` 的 `prop`（`operationName`/`operatorName`/`operationTime`）一致；若不符，仅调整 `config.ts` 的 `prop` 值。
