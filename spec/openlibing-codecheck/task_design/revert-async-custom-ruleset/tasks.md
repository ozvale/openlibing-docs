# Tasks: 回退 customProjectRuleSet 异步改造为同步

## 实现步骤

- [x] 1. 将 `RuleDelegateImpl.customProjectRuleSet()` 从异步回退为同步执行
  - 移除 `handleAsyncRuleSetCreation()` 调用
  - 恢复同步调用 `getMultiResponse()`，成功后执行规则集同步逻辑
  - 返回华为云真实 `templateId` 而非 `taskId`

- [x] 2. 删除异步相关方法
  - `handleAsyncRuleSetCreation()` - 异步创建规则集主方法
  - `generateTaskId()` - 生成异步任务 ID
  - `saveTaskStatus()` - 保存异步任务状态到 Redis
  - `syncRuleSetAfterCreation()` - 异步回调中的同步方法（逻辑内联到 `customProjectRuleSet`）

- [x] 3. 清理不再使用的依赖
  - 移除 `RuleSetTaskStatus` import
  - 移除 `TaskLockUtil` import 和字段
  - 移除 `SecureRandom` import 和 `SECURE_RANDOM` 字段
  - 移除 `Date` import

- [ ] 4. 验证测试
  - 调用 `/project/ruleSet/custom` 接口导入规则集，验证返回真实 templateId
  - 进入规则集设置页面，验证 `/rules/setting/account` 接口正常
  - 验证安全增强类规则过滤提示正常显示
