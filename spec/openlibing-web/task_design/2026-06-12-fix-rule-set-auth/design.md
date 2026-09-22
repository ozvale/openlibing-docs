# 2026-06-12 规则集权限误判修复 - 技术方案

## 1. 问题根因

`RulesHome.vue` 在 `watch(app.projectInfo)` 回调中调用 `checkAdmin()` 函数，该函数通过 `checkAuthCommunity` 接口判断用户是否为管理员。接口返回 `false` 时设置 `isAdmin = false` 并弹出无权限警告。但该接口的权限判断逻辑与平台管理中心配置不一致，导致已授权用户被误判。

## 2. 修复方案

移除 `checkAuthCommunity` 接口调用，将 `isAdmin` 默认值设为 `true`。权限判断交由子组件（`RulesList`、`Rules`、`RulesSetPermission`）内部自行处理。

### 具体变更

| 文件 | 变更内容 |
|------|---------|
| `RulesHome.vue` | 删除 `checkAdmin` 函数 |
| `RulesHome.vue` | 删除 `checkAuthCommunity` 导入 |
| `RulesHome.vue` | 删除 `ElMessage` 导入 |
| `RulesHome.vue` | `isAdmin` 默认值从 `false` 改为 `true` |
| `RulesHome.vue` | watch 回调中移除 `await checkAdmin()` 调用 |

## 3. 影响范围

- `isAdmin` prop 传递给 `RulesList`、`Rules`、`RulesSetPermission` 三个子组件
- 修改后 `isAdmin` 始终为 `true`，子组件中依赖该 prop 的逻辑需确认兼容性
- 不涉及后端接口变更

## 4. 回退方案

如需回退，恢复 `checkAdmin` 函数及相关导入即可。
