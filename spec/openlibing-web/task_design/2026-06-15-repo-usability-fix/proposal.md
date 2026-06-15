# 2026-06-15 代码仓管理易用性问题修复提案

## 1. 需求背景

代码仓管理模块存在多个前端易用性问题，影响用户操作体验：

- ContactInformation 组件切换联系人类型时，清空了已输入的账号登录名，且未触发搜索刷新
- Repos 页面仓库 URL 自动完成选择后，未清除校验错误提示，也未自动带出仓库名称
- repoUserManage 页面切换联系人类型时不应清空已输入的登录名

### 问题描述

1. **ContactInformation 组件**：`handleSelectChange` 函数在切换联系人类型时无条件清空 `accountLogin`，且不调用 `getFormInfor` 触发搜索，导致切换后数据不刷新
2. **Repos/index.vue**：仓库 URL 使用自动完成选择后，表单校验错误提示未清除，仓库名称也未自动填充
3. **repoUserManage.vue**：作为仓库用户管理场景，切换联系人类型时不应清空已输入的登录名

## 2. 验收标准

### 功能验收

- [x] ContactInformation 组件切换联系人类型时触发搜索刷新
- [x] ContactInformation 组件支持 `keepInputOnSwitch` 属性，控制切换时是否保留输入
- [x] Repos 页面仓库 URL 自动完成选择后清除校验错误提示
- [x] Repos 页面仓库 URL 自动完成选择后自动带出仓库名称
- [x] repoUserManage 页面切换联系人类型时保留已输入的登录名

### 代码质量验收

- [x] 代码逻辑正确，无副作用
- [x] 新增 prop 有合理的默认值，向后兼容

## 3. 变更范围

### 涉及模块

- **前端组件**: `apps/web-openlibing/src/components/ContactInformation.vue`
- **前端页面**: `apps/web-openlibing/src/views/Repos/index.vue`
- **前端页面**: `apps/web-openlibing/src/views/Repos/repoUserManage.vue`

### 变更类型

- Bug 修复 / 易用性优化

## 4. 风险评估

- **风险等级**: 低
- **影响范围**: 仅涉及前端交互逻辑优化
- **破坏性变更**: 无（新增 prop 有默认值，完全向后兼容）

## 5. 关联信息

- **Issue**: [#195](https://gitcode.com/openlibing/openlibing-web/issues/195)
- **PR**: [#512](https://gitcode.com/openlibing/openlibing-web/merge_requests/512)
- **分支**: `dev-chenning-20260615-repo-DTS` → `release_20260615`
- **标签**: ai-assisted
