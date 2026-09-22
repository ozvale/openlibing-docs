# 实现任务

## Task 1: 移除"tag 名称校验"列

**文件**: `apps/web-openlibing/src/views/Publish/publishReview/detail/components/releaseArtifacts.vue`

- [x] 删除 `<el-table-column label="tag名称校验" prop="tagValidationResult">` 整段（含 `el-tooltip` 与 `el-else-if` 分支、空值兜底）
- [x] 删除辅助函数 `getTagResult(val)`
- [x] 删除辅助函数 `getTagResultDetailTip(val)`
- [x] 确认其余表格列（产物名、验证时间等）展示不受影响

## Task 2: "同意发布"按钮加病毒扫描约束

**文件**: `apps/web-openlibing/src/views/Publish/publishReview/detail/reviewDetail.vue`

- [x] 在"同意发布"按钮模板上新增 `:disabled="dataList.virusScanStatus !== 2"`
- [x] 保留既有 `v-if`、`type="primary"`、`v-uem-record`、`@click="handlePublishDecision"` 等属性不变
- [x] 验证 virusScanStatus 取值语义：2 表示扫描完成

## Task 3: SYNC_PROJECT_USER 接口前缀修正

**文件**: `apps/web-openlibing/src/api/url.ts`

- [x] 将 `export const SYNC_PROJECT_USER = CODE_REPO + '/sync-user/sync-project-user';` 改为 `export const SYNC_PROJECT_USER = FRAME_WORK + '/sync-user/sync-project-user';`
- [x] 确认 `FRAME_WORK` 常量在同一文件中已定义
- [x] 确认下游调用方（同步项目用户功能入口）路径切换后正常工作

## Task 4: 质量门禁

- [x] 本地 pre-commit run（SKIP=pnpm-setup）通过
  - trailing-whitespace / end-of-file-fixer / check-merge-conflict / check-added-large-files / detect-private-key / gitleaks → Passed
  - Prettier Format → Passed
  - ESLint Check → Passed
- [x] commit 提交：`c74e579ae fix(publishReview): gate publish button by virus scan and drop tag column`
- [x] commit 提交：`f09e216af fix(api): point SYNC_PROJECT_USER to FRAME_WORK service domain`
- [x] 推送至 fork 仓 `liting_0916/openlibing-web` 的 `lt-platform09-2` 分支
