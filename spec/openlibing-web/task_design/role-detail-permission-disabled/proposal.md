# role-detail-permission-disabled

## 需求背景

角色管理页面（`/views/authorityManagement/role.vue`）支持三种弹窗模式：添加角色（add）、编辑角色（update）、查看角色（detail）。在「查看角色」模式下，表单其他输入项已通过 `:disabled="dialogType === 'detail'"` 实现禁用，但权限设置树（`el-tree`）的复选框仍可勾选/取消勾选，导致查看模式下存在误操作风险。同时，Element Plus 默认的 disabled+checked 复选框样式为浅灰背景 + 浅灰勾，与未勾选状态视觉差异不明显，已勾选的权限节点不够直观。

## 功能描述

- 在「查看角色」弹窗模式下，将权限设置树所有节点的复选框置为 disabled，不可勾选
- 优化 disabled 状态下复选框的 CSS 样式，使勾选状态更直观明显
- 不影响「添加角色」「编辑角色」模式下复选框的勾选行为

## 验收标准

- [ ] 「查看角色」弹窗：权限设置树所有节点复选框置灰，鼠标点击无反应
- [ ] 「查看角色」弹窗：已勾选节点显示蓝底白勾，未勾选节点显示浅灰底，两者视觉对比明显
- [ ] 「添加角色」弹窗：复选框可正常勾选/取消
- [ ] 「编辑角色」弹窗：复选框可正常勾选/取消，已勾选状态正确回显

## 影响范围

- 模块：`openlibing-web` 仓 `apps/web-openlibing/src/views/authorityManagement/role.vue`
- 文件：仅 1 个文件修改
- 接口：无后端接口变化
- 数据：无数据模型变化
