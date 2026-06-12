# Proposal: 排队Tab取消排队按钮增加权限判断

## 需求背景

流水线详情页「详情」Tab 的「编辑」按钮已实现权限判断（hasAuth + TipMemberListComp），无权限用户看到禁用按钮并展示权限提示。但「排队」Tab 的「取消排队」按钮缺少同样的权限控制，所有用户均可看到并点击该按钮，存在越权操作风险。

## 需求描述

为 `Queue.vue` 中「取消排队」按钮增加与 `Detail.vue` 一致的权限判断逻辑：有权限用户（project_manager / project_cie）可正常点击，无权限用户看到禁用按钮并展示 TipMemberListComp 提示。

## 验收标准

- [ ] 引入 `getUserRole` API 和 `TipMemberListComp` 组件
- [ ] 添加 `hasAuth` 状态和 `getCurrentProjectAuth` 方法，权限判断逻辑与 Detail.vue 一致
- [ ] 项目切换时同步刷新权限状态
- [ ] 有权限时显示可点击的「取消排队」按钮
- [ ] 无权限时显示禁用按钮 + TipMemberListComp 提示
- [ ] 未登录（app.user?.userId 为空）时跳过 getUserRole 调用
- [ ] ApiClient 403 处理中 needCheck=2 补全路由跳转到 noApplicationPermission

## 关联 Issue

openlibing/openlibing-docs#70
