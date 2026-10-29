# Tasks: 安全编译选项扫描结果支持导出（前端）

## 实现步骤

- [x] 1. `url.ts`：新增 `BUILD_ARTIFACT_SEC_OPTION_DETAIL_EXPORT = SECURITY + '/build-artifact/sec-option/detail/export'`
- [x] 2. `api.ts`：新增 `buildArtifactSecOptionDetailExport` 请求函数（POST 封装，沿用 `RequestFunc` 签名）
- [x] 3. `PackageDetailView.vue`：工具栏新增「导出扫描结果」按钮（`Download` 图标 + `exportLoading` loading 态）
- [x] 4. `PackageDetailView.vue`：实现 `handleExport`——参数获取（`useAppStore().projectInfo` + `props.row.id`）与防重复点击
- [x] 5. `PackageDetailView.vue`：`projectId`/`recordId` 缺失时 `ElMessage.warning` 提示并返回（检视意见修复：原为静默 return）
- [x] 6. `PackageDetailView.vue`：调用导出接口（`disabledLoading: true`），无任务 ID 时 `ElMessage.error` 提示
- [x] 7. `PackageDetailView.vue`：`notifyHostExportTask` 上报导出中心事件；返回 `false` 时降级提示「后台任务已创建，但未检测到导出中心，请稍后手动查看」（检视意见修复：原为无条件提示成功）
- [x] 8. `finally` 恢复 `exportLoading`，接口异常由请求拦截器统一提示

## 验证记录

- [x] PR 流水线 PR-pipeline_openlibing-cicd-web#394：构建 / 病毒扫描 / 安全编码扫描全部 COMPLETED
- [x] AI 代码审查：P0-P2 = 0，2 处 P3 建议均已采纳并追加 commit `cb37989`
