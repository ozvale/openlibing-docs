# Proposal: fix-repos-project-switch-params

## 背景与现象

`openlibing-web` 仓 `apps/web-openlibing/src/views/Repos/index.vue` 在「项目切换」场景下存在两个历史遗留问题，导致页面状态错乱、URL 参数残留、分支管理 tab 数据陈旧：

1. **URL 参数残留**：从「代码规模详情」（`metricType=...` 等）切回 Repos tab 后再切到另一个项目，URL 上仍带着旧项目的 `repoId / branchName / pipelineRunId / metricType`。回到 Repos tab 时 `router.push(fullPath)` 会把这些参数重新带回，页面错误地进入"代码规模详情"视图而非默认的"代码仓管理"。
2. **分支管理 tab 数据陈旧**：切换项目后，"分支管理"tab 仍显示旧项目的分支列表。原因是 `branches.vue` 只在 `onMounted` 拉一次分支数据，没有监听 `projectInfo` 变化。
3. **watch projectInfo 误重置**：`Content.vue` 的 `getProject` 与 `ProjectSelect.onMounted` 各自调用一次 `setProjectInfo`，传入的是同一个 `projectId` 但每次都是新对象引用，触发 `projectInfo` watcher 把 `autoGoBranch` 已恢复的"分支管理 + 代码规模详情"状态打回"代码仓管理"tab。

## 根因

- `watch(projectInfo)` 没有 `oldValue.projectId === newValue.projectId` 早退分支，导致同 `projectId` 的 ref 变化也执行重置。
- 切项目时清理 URL 走 `needResetUrlQuery + onActivated` 组合：`onActivated` 只在 keep-alive 复用场景触发，**顶部 ProjectSelect 切项目（非 keep-alive 切换）不触发**，导致 URL 残留。
- `branches.vue` 生命周期未与 `projectInfo` 绑定，切换项目后不会主动重拉分支数据。

## 需求目标

| 目标                         | 验收点                                                                                                                       |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| URL 参数不残留               | 切项目后 URL 不带旧项目 `repoId / branchName / pipelineRunId / metricType`                                                   |
| 分支管理 tab 数据正确        | 切项目后"分支管理"tab 显示新项目的分支列表                                                                                   |
| Repos 路由上切项目           | URL 立即清理（`router.replace`）                                                                                             |
| 其他 tab 上切项目            | `tabbarStore` 中 Repos tab 的 `query / fullPath` 也同步清理，避免点回 Repos tab 时 `router.push(fullPath)` 带回旧参数        |
| 首次加载保留参数             | URL 上的 `repoId / branchName / pipelineRunId / metricType` 保留，供 `autoGoBranch` 在异步回调里读取并恢复"代码规模详情"状态 |
| 同 projectId 不同 ref 不重置 | `Content.vue getProject` 与 `ProjectSelect.onMounted` 重复 `setProjectInfo`（同 `projectId`、新 ref）不重置已恢复的 tab 状态 |

## 不在本次范围

- `branches.vue` 内部数据加载逻辑改造（本次仅强制重建触发其 `onMounted`）
- `autoGoBranch` 的异步恢复逻辑（本次仅保证 URL 参数不被错误清理）
- 多 tab 同步策略的统一治理（仅针对 Repos tab）

## 关联 Issue

待业务 PR 创建时补关联（跨仓 PR 由用户在 Issue 页面手动关联）。

## 关联 PR

- 业务 PR：`openlibing/openlibing-web` PR（待创建）
- docs PR：待创建

## 关联 commit

- `46017219a28f2cb9d9f1b4003d6fd6a3c504686a` `fix(repos): clean metrics url params and refresh branches on project switch`

Generated-by: GLM-5.2
