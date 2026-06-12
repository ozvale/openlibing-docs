# Archive: 排队Tab取消排队按钮增加权限判断

## 需求概述

流水线详情页「排队」Tab 的「取消排队」按钮缺少权限判断，所有用户均可操作。需与「详情」Tab 的「编辑」按钮对齐，增加 hasAuth + TipMemberListComp 权限控制。

## 实现总结

### Queue.vue 权限判断

- 引入 `getUserRole` 和 `TipMemberListComp`
- 添加 `hasAuth` ref 和 `getCurrentProjectAuth` 方法
- 模板中使用 `v-if="hasAuth"` / `v-else` 区分有权限和无权限状态
- 无权限时显示禁用按钮 + TipMemberListComp 提示

### Detail.vue 修正

- 移除 `getCurrentProjectAuth` 中 Turing 项目限制（projectId !== 300_033），使权限判断对所有项目生效
- 增加 `app.user?.userId` 前置判断，未登录时跳过 getUserRole 调用

### ApiClient.ts 重构

- 提取 `getHostBus()` 集中管理 wujie bus 获取
- 提取 `navigateToRoute()` 统一微前端/独立路由跳转
- 403 处理 needCheck=2 补全路由跳转到 noApplicationPermission
- 改善 sourceTokenMap / loading / timer 类型安全
- 修复 autoLoginPlatform 多余分号

## 关联

- 业务 Issue: openlibing/openlibing-cicd-web#24
- 业务 PR: openlibing/openlibing-cicd-web#44

## 经验沉淀

- 权限判断模式（hasAuth + TipMemberListComp + getCurrentProjectAuth）已在 Detail.vue 和 Queue.vue 中使用，后续新增操作按钮时应同步增加
- `app.user?.userId` 前置判断可避免未登录时发送无意义请求
- `navigateToRoute()` 统一了微前端和独立模式的路由跳转，后续新增路由跳转点应复用此方法
