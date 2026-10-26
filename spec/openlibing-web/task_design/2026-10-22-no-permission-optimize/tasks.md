# 无权限提示优化 — 实现任务

## 进度: 0/5 complete

- [ ] Task 1: 新增 `src/utils/noPermissionGuide.ts` 纯函数 `buildApplyGuide`（判别联合：system/product 返回 notice 型整行说明；project/repo 返回 guide 型跳转链接；general 人工客服）
- [ ] Task 2: `NoPermissionPopover.vue` 申请指引按类型分两支渲染（notice 型整行说明不带标签；guide 型带「申请指引：」+ 可点击链接，无 repoId 降级纯文本）
- [ ] Task 3: `Repos/index.vue` 支持 `showRepoUserManage=1` query 自动打开仓库成员管理（route watcher + projectInfo watcher 双路径，防重入）+ URL 清理
- [ ] Task 4: 角色组展示不做任何级别过滤（全部级别展示），空态保持 `rolesByLevel` 为空判断
- [ ] Task 5: 新增 `src/utils/__tests__/noPermissionGuide.spec.ts` 单测 + 验证（lint / typecheck / 单测）
