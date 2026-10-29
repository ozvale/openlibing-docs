# Proposal: virus-scan-report-download

## 背景与现象

`openlibing-web` 发布评审详情页（`Publish/publishReview/detail`）制品信息区已展示病毒扫描状态，但用户无法直接获取病毒扫描报告原文，需线下找安全团队要文档，效率低且无留痕。

## 需求目标

在发布评审详情页-制品信息标题行右侧增加「病毒扫描报告下载」按钮，调用 `GET /base/virusScanReport`（参数：`projectId`、`reviewId`）下载 word 格式报告。

| 目标            | 验收点                                                                                     |
| --------------- | ------------------------------------------------------------------------------------------ |
| 下载入口        | 制品信息标题行右侧展示「病毒扫描报告下载」按钮                                             |
| 展示条件        | 仅 `isDataOwner`（数据责任人）且 `virusScanStatus === 2`（扫描完成）时展示                 |
| 下载确认        | 点击按钮弹出 `ElMessageBox.confirm` 二次确认                                               |
| 报告下载        | 确认后调 `GET /base/virusScanReport`，以 blob 方式下载，文件名 `病毒扫描报告{时间戳}.docx` |
| 下载中状态      | 请求期间按钮 `loading`，防止重复点击                                                       |
| header 布局复用 | `reviewPartHeader.vue` 增加可选具名 slot `headerAction`，不影响其他 8 处既有使用           |

## 不在本次范围

- 病毒扫描报告内容生成逻辑（后端职责）
- 非责任人的下载权限开放
- 报告在线预览（仅下载）

## 关联 Issue

- `https://gitcode.com/openlibing/openlibing-platform-release/issues/63`（跨仓关联，由用户在 Issue 页面手动关联）

## 关联 PR

- 业务 PR：`openlibing/openlibing-web` [PR #819](https://gitcode.com/openlibing/openlibing-web/merge_requests/819)（`feat(publishReview): add virus scan report download`）
- docs PR：本 PR

## 关联 commit

- `103b15632` `feat(publishReview): add virus scan report download in review detail`
- `107fbc8fe` `fix(publishReview): adjust virus scan report download button`（用户自测调整）

Generated-by: GLM-5.3
