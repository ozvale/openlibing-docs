# 2026-06-12 规则集权限误判修复 - 任务清单

## 实现步骤

- [x] 移除 `RulesHome.vue` 中 `checkAdmin` 函数
- [x] 移除 watch 回调中 `await checkAdmin()` 调用
- [x] 将 `isAdmin` 默认值从 `ref(false)` 改为 `ref(true)`
- [x] 清理 `checkAuthCommunity` 导入
- [x] 清理 `ElMessage` 导入
- [x] 提交代码并推送远端
- [x] 创建业务 PR（openlibing/openlibing-web#508）
- [x] 关联业务 Issue（openlibing/openlibing-web#191）
