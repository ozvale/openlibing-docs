# 2026-08-17 管理中心返回主页按钮提案

## 1. 需求背景

管理中心（`manageCenter/index.vue`）是独立于主框架的独立布局页面，用户从主页进入管理中心后，缺少直观的返回主页入口，只能依赖浏览器回退，导航体验不完整。

### 需求描述

- 在管理中心侧边栏底部新增"返回主页"按钮
- 点击后跳转回主页（根路由 `/`）
- 按钮与既有"收起菜单"按钮风格统一，支持菜单折叠/展开两种形态

## 2. 验收标准

### 功能验收

- [x] 侧边栏底部"收起菜单"按钮上方新增"返回主页"按钮（HomeFilled 图标）
- [x] 菜单展开时显示图标 + "返回主页"文字；折叠时仅显示图标
- [x] 点击按钮跳转回根路由 `/`（主页）
- [x] 复用 `.collapse-btn` 既有样式（固定位置、hover 效果），视觉与折叠按钮一致
- [x] 管理中心既有菜单导航、收起/展开功能不受影响

### 代码质量验收

- [x] 单文件变更，纯新增模板元素 + 1 个导航函数 + 1 个图标导入
- [x] 代码格式符合 ESLint 规范

## 3. 变更范围

### 涉及模块

- **前端组件**: `apps/web-openlibing/src/views/manageCenter/index.vue` — 新增返回主页按钮（+11/-2）

### 变更类型

- 体验优化（导航入口补充）

## 4. 风险评估

- **风险等级**: 低
- **影响范围**: 仅管理中心侧边栏新增一个静态按钮，不触及既有路由守卫与菜单逻辑
- **破坏性变更**: 无

## 5. 关联信息

- **业务仓**: dyy-1/openlibing-web_9915（openlibing-web fork 仓）
- **业务仓分支**: `feat-back-to-user-button`
- **Commit**: `dc051199` feat(manageCenter): add back-to-user button in management center
- **标签**: ai-assisted
- **业务 Issue**: https://gitcode.com/openlibing/openlibing-web/issues/276
