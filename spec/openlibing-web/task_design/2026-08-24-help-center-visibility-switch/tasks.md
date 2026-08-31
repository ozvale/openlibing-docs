# 2026-08-24 帮助中心文档可见性开关 - 任务清单

## 实现步骤

- [x] helpCenter.vue 标题行右侧新增"管理中心文档"el-switch 开关
- [x] 新增 `hasManageConfigPermission` 计算属性（`manage_config` 权限判断）
- [x] 新增 `visibilityValue` 可写计算属性（int 型 1/0，未取到默认 0）
- [x] 新增 `handleVisibilityChange`：调用 `updateHelpCenterFile` 保存，成功后刷新文件树与详情，失败回滚
- [x] 开关显示条件追加 `isManageCenterRoute`（URL 在 `/manageCenter` 路径下）
- [x] manageRouter.ts 新增 `/manageCenter/helpCenterSetting` 路由
- [x] manageCenter/index.vue 左侧菜单新增"帮助中心 → 帮助文档"入口
- [x] `handleNodeClick` 的 `router.push` 增加 `isComponentActive` 激活守卫
- [x] 修复 pre-commit 缓存损坏问题并使 `pre-commit run --all-files` 全部通过
- [x] 提交代码并推送远端（commits: `51ee95e1`、`1df589e8`，分支 `jzcfork/202608help`）
- [ ] 创建业务 PR 并打 `ai-assisted` 标签
- [ ] 关联业务 Issue
- [ ] 归档 archive.md（Phase 5 用户触发后）
