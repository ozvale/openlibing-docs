# 需求背景

## 业务场景

openlibing-web 主应用侧边栏菜单（`apps/web-openlibing/src/router/routes/modules/menu.ts`）。「测试管理」功能即将下线，需要在菜单入口向用户提前预告，避免用户继续投入并产生迁移成本。

## 问题痛点

1. 功能下线缺乏预告机制：直接移除菜单会让存量用户突兀地找不到入口，无过渡期提示。
2. 此前菜单 meta 不支持附加渲染，缺少在菜单项旁挂载徽标/气泡的通用途径。

## 需求目标

在「测试管理」菜单项上挂载 `OfflineNotice` 组件，通过 `meta.extraRender` 以函数式组件返回 VNode，使侧边栏展示灰色 OFF 徽标，hover 弹出即将下线的预告气泡。

## 验收标准

### 功能验收

1. 侧边栏「测试管理」菜单项旁渲染灰色下线预告图标（OFF 徽标样式）。
2. hover 图标弹出 popover，提示该功能即将下线。
3. 菜单项本身的图标、标题与点击跳转行为不受影响。

### 非功能验收

1. `OfflineNotice` 复用既有通用组件，不新增重复实现。
2. 通过 Prettier / ESLint / pre-commit 检查。

## 关联分支

openlibing-web `feat-test-management-offline-notice`（commit edba53991）

## 期望交付时间

2026-11-06
