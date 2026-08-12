## 1. API 层注册回撤接口

- [x] 1.1 在 `openlibing-web/apps/web-openlibing/src/api/url.ts` 中新增常量 `WITHDRAW_RELEASE_REVIEW = PLATFORM_RELEASE + '/base/withdrawReleaseReview'`，放在 `SUBMIT_PUBLISH_REVIEW` 附近（同 `/base/` 前缀分组）。
- [x] 1.2 在 `openlibing-web/apps/web-openlibing/src/api/api.ts` 中新增请求函数 `export const withdrawReleaseReview: RequestFunc = (a, s) => apiClient.post(urls.WITHDRAW_RELEASE_REVIEW, a, s);`，放在 `submitPublishReview` 附近。

## 2. reviewDetail.vue 实现回撤按钮与逻辑

- [x] 2.1 在 `reviewDetail.vue` 的 `<script setup>` 中导入 `withdrawReleaseReview`（来自 `@/api/api`）和 `ElMessageBox`（来自 `element-plus`，与已有的 `ElMessage` 同源导入）。
- [x] 2.2 新增 `canWithdrawReview` computed：`isDataOwner.value && dataList.value?.reviewStatus !== -1`，复用已有 `isDataOwner`。
- [x] 2.3 新增 `withdrawLoading` ref（`ref(false)`），用于按钮 loading 状态。
- [x] 2.4 新增 `handleWithdrawReview` 函数：弹 `ElMessageBox.confirm` 二次确认 → 置 `withdrawLoading = true` → 调用 `withdrawReleaseReview({ params: { projectId: app.projectInfo?.projectId, userId: app?.user?.userId, id: dataList.value?.id } })` → `code === 200` 时 `ElMessage.success` + `getDetailData()` 刷新 → `.finally` 中重置 `withdrawLoading = false`；失败时 `ElMessage.error` 且不刷新。
- [x] 2.5 在模板第 4-9 行"基本信息"的 `<reviewPartHeader>` 外包一层 `<div class="header-row">`，内含 `<reviewPartHeader>` 和回撤按钮 `<el-button v-if="canWithdrawReview" :loading="withdrawLoading" @click="handleWithdrawReview">回撤</el-button>`。按钮通过 `margin-left: auto` 靠右对齐。**不修改 `reviewPartHeader.vue`**。
- [x] 2.6 在 `<style>` 中新增 `.header-row { display: flex; align-items: center; }`，并给 `.header-row` 内的按钮补 `margin-bottom: 15px`（与 `reviewPartHeader` 根元素的 `margin-bottom` 对齐，避免两者底部错位）。

## 3. 验证

- [x] 3.1 对改动的文件（`url.ts`、`api.ts`、`reviewDetail.vue`）运行 lint / 类型检查，确认无新增错误。
- [x] 3.2 手动验证：① 评审单为"新建"状态时按钮不显示；② 当前用户非创建者时按钮不显示；③ 非新建 + 创建者时按钮显示且靠右；④ 点击按钮弹出二次确认；⑤ 确认后调用接口成功并刷新页面；⑥ 接口失败时提示错误且不刷新。
