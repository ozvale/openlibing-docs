# 2026-06-12 规则集权限误判修复提案

## 1. 需求背景

流水线工程师在平台管理中心已配置规则集相关权限，但进入规则集页面时仍显示无权限提示（ElMessage.warning），导致已授权用户无法正常使用规则集功能。

### 问题描述

- `RulesHome.vue` 中通过 `checkAuthCommunity` 接口检查用户是否为管理员
- 该接口返回的权限判断结果与平台管理中心配置的权限不一致
- 已授权用户被误判为无权限，弹出"当前账号无权限查看该项目下的规则集"警告

## 2. 验收标准

### 功能验收

- [x] 移除 `checkAuthCommunity` 接口调用
- [x] `isAdmin` 默认值改为 `true`
- [x] 清理不再使用的 `checkAuthCommunity` 和 `ElMessage` 导入
- [x] 已授权用户进入规则集页面不再弹出无权限警告

### 代码质量验收

- [x] 无未使用的导入残留
- [x] 代码格式符合 ESLint 规范

## 3. 变更范围

### 涉及模块

- **前端组件**: `apps/web-openlibing/src/views/RuleSetDirectory/CodeCheckRule/RulesHome.vue` — 移除权限检查逻辑

### 变更类型

- 缺陷修复（移除错误的权限检查接口调用）

## 4. 风险评估

- **风险等级**: 低
- **影响范围**: 仅涉及规则集目录页面权限判断逻辑
- **破坏性变更**: 无

## 5. 关联信息

- **Issue**: openlibing/openlibing-web#191
- **PR**: openlibing/openlibing-web#508
- **分支**: `dev-chenning-20260615-ruleAuth`
- **标签**: ai-assisted
