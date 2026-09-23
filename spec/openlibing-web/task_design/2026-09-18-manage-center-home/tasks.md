# 2026-09-18 管理中心首页落地页 - 任务清单

## 实现步骤

- [x] manageRouter.ts 新增 `/manageCenter/home` 路由（name: `manageCenterHome`，auth: `manage_config`）
- [x] `/manageCenter` redirect 由 `roleManagement` 改为 `home`
- [x] 新建 Home/index.vue：Hero 欢迎区（分时段问候语 + 用户名 + 日期 + 内联 SVG 插画，min-height 300px）
- [x] Hero 插画由 CDN 图片改为内联 SVG（修复图片加载失败）
- [x] 实现 8 张能力卡片（组织管理/权限管理/机机管理/日志审计/运营运维/AI 工具/漏洞挖掘/帮助中心）
- [x] 实现 `canAccessRoute`：通过 `router.resolve({ name }).meta?.auth` 读取权限并与 `app.user?.permissions` 比对
- [x] 卡片配置 `routes` 数组，`visibleCapabilities` computed 按 `some` 过滤，无权限卡片不渲染
- [x] 左侧菜单新增"首页"一级菜单项（Monitor 图标）
- [x] 帮助中心由二级子菜单改为一级菜单项
- [x] 菜单美化：彩色 SVG 图标（9 主题色 class）+ hover 过渡 + 激活态高亮 + 子菜单项圆点
- [x] ESLint 验证通过
- [x] 提交代码并推送远端（commit: `f9d6d08f`，分支 `jzcfork/202609managerediect`）
- [ ] 创建业务 PR 并打 `ai-assisted` 标签
- [ ] 关联业务 Issue
- [ ] 归档 archive.md（Phase 5 用户触发后）
