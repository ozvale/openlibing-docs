# Tasks: virus-scan-report-download

## Phase 1 调研

- [x] T1 确认接口契约：`GET /base/virusScanReport`，query 传 `projectId`、`reviewId`，响应为 word 二进制流
- [x] T2 确认按钮展示条件：`isDataOwner && virusScanStatus === 2`
- [x] T3 确认 `reviewPartHeader.vue` 现有 8 处使用，评估插槽扩展零回归可行性

## Phase 2 实现步骤

- [x] T4 `url.ts` 新增 `VIRUS_SCAN_REPORT_DOWNLOAD` 常量
- [x] T5 `api.ts` 新增 `getVirusScanReport` GET 封装
- [x] T6 `reviewPartHeader.vue` 新增可选具名 slot `headerAction`（`margin-left: auto` 靠右）
- [x] T7 `reviewDetail.vue` 制品信息标题行插入「病毒扫描报告下载」按钮（`type="primary"`、`:loading="downloadLoading"`）
- [x] T8 实现 `downloadVirusScanReport`：`ElMessageBox.confirm` → blob 请求 → `exportFile` 落盘
- [x] T9 下载期间按钮 loading，防止重复点击

## Phase 3 验证

- [x] T10 pre-commit 全钩子通过
- [x] T11 三点 diff 验证：4 文件 +70/-2，无基底污染
- [x] T12 用户自测：按钮展示条件、下载流程、word 文件落盘正常

## Phase 4 业务 PR

- [x] T13 推送 `lt-platform10-1` 分支到 fork 仓（`liting_0916/openlibing-web`）
- [x] T14 创建业务 PR（base: `release_20261019`，head: `liting_0916:lt-platform10-1`）→ [PR #819](https://gitcode.com/openlibing/openlibing-web/merge_requests/819)
- [x] T15 补打 `ai-assisted` 标签
- [ ] T16 在 [openlibing-platform-release Issue #63](https://gitcode.com/openlibing/openlibing-platform-release/issues/63) 页面手动关联 PR（GitCode CLI 不支持跨仓 PR 关联）

## Phase 5 归档

- [ ] T17 业务 PR 合入后，生成 `archive.md` 沉淀经验
- [ ] T18 通过 docs PR 提交归档（关联业务 Issue）

## Commit 关联表

| Task    | Commit      | 说明                       |
| ------- | ----------- | -------------------------- |
| T1-T9   | `103b15632` | 接口封装 + 插槽 + 下载流程 |
| T12     | `107fbc8fe` | 用户自测调整               |
| T13-T15 | -           | 业务 PR #819 创建          |
| T16-T18 | 待执行      | 手动关联 + 归档            |

Generated-by: GLM-5.3
