# 2026-08-26 用户管理页小屏布局错位修复提案

## 1. 需求背景

用户管理页（`authorityManagement/user.vue`）在小屏（窄窗口）模式下布局错位：

### 问题描述

- 账号类型表单项固定 `width: 500px`，小屏下溢出容器
- header 区域多个筛选元素横向排布，小屏下拥挤挤压
- 表格各列未设置宽度，小屏时列被压缩，gitCode/gitee/openUBMC 账号用户名列表头文字挤压不完整
- 分页组件页码过多，小屏下出现换行与横向滚动

## 2. 验收标准

### 功能验收

- [x] 账号类型表单项改为弹性宽度（280px~500px），小屏不溢出
- [x] header 小屏下自动换行（flex-wrap + row-gap 12px），元素不再拥挤
- [x] 表格各列设置 min-width，小屏下列宽不被过度压缩；openUBMC 账号用户名列固定 width=220 保证表头完整展示
- [x] 表格内容超出列宽时换行展示（默认行为，未启用 show-overflow-tooltip）
- [x] 分页 pager-count 设为 5，小屏下一行展示，无换行无横向滚动
- [x] 大屏模式下页面布局与功能不受影响

### 代码质量验收

- [x] 单文件变更，纯模板属性与 CSS 调整，无逻辑/接口/数据变更
- [x] 代码格式符合 ESLint 规范

## 3. 变更范围

### 涉及模块

- **前端组件**: `apps/web-openlibing/src/views/authorityManagement/user.vue` — 表单项弹性宽度、header 换行、表格列宽、分页 pager-count（+25/-3）

### 变更类型

- 缺陷修复（小屏响应式布局）

## 4. 风险评估

- **风险等级**: 低
- **影响范围**: 仅用户管理页布局表现，数据交互与权限逻辑不变
- **破坏性变更**: 无
- **备注**: 窄屏下表格列超出容器总宽时出现表格自身横向滚动（Element Plus 表格默认行为），属预期兜底

## 5. 关联信息

- **业务仓分支**: `fix-user-layout`
- **Commit**: `c4bb8a9f` fix(user): 修复用户管理页小屏模式下布局错位问题
- **标签**: ai-assisted
- **业务 Issue**: https://gitcode.com/openlibing/openlibing-framework/issues/82
