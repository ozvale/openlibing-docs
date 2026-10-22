# 无权限提示优化 — 实现任务

## 进度: 0/6 complete

- [ ] Task 1: 新增 `src/utils/noPermissionGuide.ts` 纯函数（`filterApplicableRoleGroups` / `buildApplyGuide`）
- [ ] Task 2: `NoPermissionPopover.vue` 角色组展示应用过滤（仅保留 project/repo/general，空态条件改过滤后为空）
- [ ] Task 3: `NoPermissionPopover.vue` 申请指引渲染可点击链接（项目级→权限申请页；仓库级→代码仓成员管理；无 repoId 降级纯文本）
- [ ] Task 4: `Repos/index.vue` 支持 `showRepoUserManage=1` query 自动打开仓库成员管理 + URL 清理
- [ ] Task 5: 新增 `src/utils/__tests__/noPermissionGuide.spec.ts` 单测
- [ ] Task 6: 验证（lint / typecheck / 相关单测）
