# 2026-08-26 新增项目表单组织/项目下拉框搜索提案

## 1. 需求背景

新增项目表单（`projectAddEditForm.vue`，type='create' 时展示）中的组织下拉框和项目级联下拉框仅支持滚动浏览选择。组织与项目数量较多时，用户需在长列表中逐项查找，选择效率低。

### 需求描述

- 组织下拉框（`el-select`）支持输入关键字筛选组织
- 项目下拉框（`el-cascader`）支持输入关键字搜索项目

## 2. 验收标准

### 功能验收

- [x] 组织下拉框输入关键字后，选项列表按关键字过滤展示
- [x] 项目级联下拉框输入关键字后，可搜索并定位到匹配的项目节点
- [x] 不输入关键字时，两下拉框保持原有浏览选择行为不变
- [x] 编辑项目场景（type='edit'，不展示组织/项目下拉框）不受影响

### 代码质量验收

- [x] 仅模板属性添加，无逻辑/接口/数据变更
- [x] 代码格式符合 ESLint 规范

## 3. 变更范围

### 涉及模块

- **前端组件**: `apps/web-openlibing/src/views/Project/projectAddEditForm.vue` — 组织/项目下拉框添加 `filterable` 属性（+2）

### 变更类型

- 体验优化（Element Plus 组件属性启用）

## 4. 风险评估

- **风险等级**: 低
- **影响范围**: 仅新增项目表单的组织/项目选择交互
- **破坏性变更**: 无

## 5. 关联信息

- **业务仓分支**: `feat-project-search`
- **Commit**: `acc8c038` feat(project): 新增项目表单组织和项目下拉框搜索功能
- **标签**: ai-assisted
- **业务 Issue**: https://gitcode.com/openlibing/openlibing-framework/issues/82
