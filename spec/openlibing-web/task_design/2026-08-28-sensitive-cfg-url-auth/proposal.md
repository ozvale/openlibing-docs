# 2026-08-28 敏感词集操作页 URL 权限校验加固提案

## 1. 需求背景

敏感词集的新建/复制/编辑/查询页面（`CustomRuleConfig.vue`）此前仅依赖列表页按钮入口的权限控制。非管理员用户通过浏览器地址栏直接输入操作页 URL 时，页面未校验操作级权限即完成初始化并放行，形成前端越权访问入口。

### 问题描述

- 操作页初始化链路无操作级权限校验，URL 直接进入即可绕过列表页按钮的权限约束
- 页面初始化依赖全局 store（`appStore.operationPermissions`）的权限数据，URL 直接进入时全局权限接口可能尚未就绪，数据缺失时被误放行
- 切换项目后 store 中仍是旧项目的权限缓存，用户在已失去权限的项目下仍可停留在操作页

## 2. 验收标准

### 功能验收

- [x] URL 直接访问 add/copy/edit/query 操作页时，无对应操作权限则提示"无操作权限"并跳回敏感词集列表页
- [x] 有权限用户 URL 直接访问操作页功能正常，不受影响
- [x] 权限数据优先读取全局 store，未就绪时主动调用 `getOperationPermissions` 从后端拉取
- [x] 后端拉取失败时按无权限处理（fail-closed），不静默放行
- [x] 切换项目后按新项目重新校验权限，无权限时自动跳回列表页
- [x] 快速连续切换项目时，仅采纳最新一次校验结果（防竞态）
- [x] 拒绝跳转后列表页内容区正常渲染，无空白
- [x] config（查看）操作维持原有行为，不做操作级校验

### 代码质量验收

- [x] 单文件变更（`CustomRuleConfig.vue`），无接口、路由、数据模型变化
- [x] 权限解析逻辑与 `SensitiveDict/Content.vue` 既有解析逻辑保持一致

## 3. 变更范围

### 涉及模块

- **前端组件**: `apps/web-openlibing/src/views/SensitiveDict/CustomRuleConfig.vue` — 新增操作级权限校验逻辑（+108/-3）

### 变更类型

- 安全缺陷修复（前端越权访问拦截）

## 4. 风险评估

- **风险等级**: 低
- **影响范围**: 仅敏感词集操作页（add/copy/edit/query）的进入权限判断，列表页与查看页行为不变
- **破坏性变更**: 无

## 5. 关联信息

- **业务仓分支**: `fix-sensitiveCfg-url-auth`
- **Commit**: `ecb41b98` fix(sensitive-dict): block URL access to rule-set page without permission
- **标签**: ai-assisted
- **业务 Issue**: https://gitcode.com/openlibing/openlibing-web/issues/163
