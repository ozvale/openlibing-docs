# Tasks: fix-repos-project-switch-params

## Phase 1 调研

- [x] T1 复现 URL 参数残留问题（从代码规模详情切回 Repos tab → 切项目 → 回 Repos tab）
- [x] T2 复现分支管理 tab 数据陈旧问题（切项目 → 切到分支管理 tab）
- [x] T3 定位根因：`watch(projectInfo)` 无 `projectId` 早退分支 + `needResetUrlQuery + onActivated` 在非 keep-alive 切换不触发 + `branches.vue` 无 `projectInfo` 监听

## Phase 2 实现步骤

- [x] T4 在 `Repos/index.vue` 引入 `useTabbarStore`
- [x] T5 在 `watch(projectInfo)` 增加 `oldValue.projectId === newValue.projectId` 早退分支
- [x] T6 移除 `needResetUrlQuery.value = true`（替换为同步清理策略）
- [x] T7 当前路由为 `repos` 时用 `router.replace` 清 URL（保留 `projectId`）
- [x] T8 当前路由非 `repos` 时用 `tabbarStore.addTab` 覆盖 Repos tab 的 `query / fullPath`
- [x] T9 切项目时 `branchPaneKey.value += 1` 强制重建 `branches.vue`
- [x] T10 保留首次加载时的 URL 参数路径（`oldValue?.projectId` 为空时不清理）

## Phase 3 验证

- [x] T11 首次加载（带 URL 参数）→ `autoGoBranch` 恢复"代码规模详情"状态正常
- [x] T12 同 `projectId` 不同 ref（`Content.vue getProject` + `ProjectSelect.onMounted`）→ 不重置 tab 状态
- [x] T13 在 Repos 路由上切项目 → URL 立即清理
- [x] T14 在其他 tab 上切项目 → `tabbarStore` 中 Repos tab 的 `query / fullPath` 同步清理
- [x] T15 切项目后切到"分支管理"tab → 显示新项目的分支列表
- [x] T16 切项目后点回 Repos tab → `router.push(fullPath)` 不带回旧项目的 `metrics` 参数

## Phase 4 业务 PR

- [ ] T17 推送 `dev-chenning-20260923-bug` 分支到 fork 仓
- [ ] T18 创建业务 PR（base: `release_20260916`，head: `weixin_45521051:dev-chenning-20260923-bug`）
- [ ] T19 PR 标题：`fix(repos): clean metrics url params and refresh branches on project switch`
- [ ] T20 补打 `ai-assisted` 标签
- [ ] T21 在 Issue 页面手动关联 PR（GitCode CLI 不支持跨仓 PR 关联）

## Phase 5 归档

- [ ] T22 业务 PR 合入后，生成 `archive.md` 沉淀经验
- [ ] T23 通过 docs PR 提交归档（关联业务 Issue）

## Commit 关联表

| Task    | Commit                                     | 说明                                 |
| ------- | ------------------------------------------ | ------------------------------------ |
| T1-T16  | `46017219a28f2cb9d9f1b4003d6fd6a3c504686a` | 单 commit 完成调研 + 实现 + 自测验证 |
| T17-T21 | 待执行                                     | 业务 PR 创建                         |
| T22-T23 | 待执行                                     | Phase 5 归档                         |

Generated-by: GLM-5.2
