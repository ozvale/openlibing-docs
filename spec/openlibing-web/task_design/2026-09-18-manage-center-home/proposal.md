# 2026-09-18 管理中心首页落地页提案

## 1. 需求背景

管理中心路由 `/manageCenter` 原先 redirect 到 `/manageCenter/roleManagement`（权限管理页），缺少一个管理后台首页。管理员进入管理中心时直接落到具体功能页，没有整体概览与导航入口，体验不友好。

### 问题描述

- `/manageCenter` 无落地首页，redirect 指向具体功能页（roleManagement）
- 管理中心各业务模块（组织/权限/机机/日志/运营运维/AI 工具/漏洞挖掘/帮助中心）能力分散，缺少统一的模块入口聚合视图
- 落地页若对所有模块入口一视同仁展示，无权限用户会看到大量不可用的入口卡片
- 左侧菜单原有样式单调（无彩色图标、无 hover 反馈），整体观感偏简陋

## 2. 验收标准

### 功能验收

- [x] `/manageCenter` redirect 改为 `/manageCenter/home`
- [x] 新增路由 `/manageCenter/home`（name: `manageCenterHome`，meta.auth: `manage_config`）
- [x] 首页含 Hero 欢迎区：问候语（按时段变化）+ 用户名 + 当前日期 + 内联 SVG 插画，min-height 300px
- [x] 首页含 8 张能力卡片：组织管理 / 权限管理 / 机机管理 / 日志审计 / 运营运维 / AI 工具 / 漏洞挖掘 / 帮助中心
- [x] 能力卡片按用户权限动态过滤显示：
  - 通过 `router.resolve({ name }).meta?.auth` 读取对应模块路由的权限标识
  - 与 `app.user?.permissions` 比对，无权限的卡片不渲染
  - 路由无 auth 要求、或仅要求 `manage_config`（进入管理中心本身即具备）时默认可见
  - 卡片对应模块下任一子路由有权限即显示该卡片
- [x] 左侧菜单新增"首页"一级菜单项（Monitor 图标），点击跳转 `manageCenterHome`
- [x] 帮助中心由二级子菜单改为一级菜单项，图标保留
- [x] 左侧菜单美化：彩色 SVG 图标（9 个主题色 class）、子菜单标题 hover 圆角过渡、激活态高亮、子菜单项前置圆点

### 代码质量验收

- [x] ESLint 验证通过（`npx eslint src/views/manageCenter/Home/index.vue`）
- [x] 无未使用导入残留、无外部图片依赖（Hero 使用内联 SVG，避免 CDN 加载失败）

## 3. 变更范围

### 涉及模块

- **路由配置**: `apps/web-openlibing/src/router/manageRouter.ts` — 新增 home 路由 + redirect 调整
- **新增页面**: `apps/web-openlibing/src/views/manageCenter/Home/index.vue` — 管理中心首页（Hero + 能力卡片 + 权限过滤）
- **管理中心布局**: `apps/web-openlibing/src/views/manageCenter/index.vue` — 首页菜单项 + 菜单美化

### 变更类型

- 新功能（首页落地页 + 权限过滤）
- 体验优化（菜单美化）

## 4. 风险评估

- **风险等级**: 低
- **影响范围**: 管理中心入口跳转行为（redirect 变更）、左侧菜单视觉样式；不涉及后端接口变更
- **破坏性变更**: 无（`manageCenterHome` 权限要求与原 redirect 目标一致，均为 `manage_config` 级别；菜单跳转机制不变，仍通过 `router.push({ name })`）

## 5. 关联信息

- **分支**: `jzcfork/202609managerediect`
- **Commit**: `f9d6d08f`
- **标签**: ai-assisted（创建 PR 时补打）
- **流程模式**: Light（纯前端视觉 + 权限过滤，用户确认；spec 文件为用户主动要求补充生成）
