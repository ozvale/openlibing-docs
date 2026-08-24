# security-enhance-purchase-confirm — 实现任务

## 进度: 4/10 complete

### 前端（openlibing-web，已完成）

- [x] Task 1: 在 `openlibing-web` 新建开发分支 `feat-security-enhance-purchase-confirm`（基于 `origin/master`）
- [x] Task 2: `CustomRuleConfig.vue` 新增 `getSecurityEnhanceRules()` 检测函数
- [x] Task 3: 重构 `submitForm()`：抽出 `doSubmit()`，前置购买确认弹窗（已购买→继续；未购买→中断）
- [x] Task 4: 验证 — ESLint（改动文件）+ vue-tsc 通过

### 后端（openlibing-codecheck，2026-08-24 范围扩展）

- [ ] Task 5: 在 `openlibing-codecheck` 新建开发分支（基于 `origin/master`）
- [ ] Task 6: `RestCodeCheckUtil#customTaskRuleSet` 错误分支：原始报错日志 + "未购买安全增强包"识别翻译 + `Integer.parseInt` 加固
- [ ] Task 7: `RestCodeCheckUtil#listCriterions` 错误体识别（签名加 `throws BusinessException`）+ `RuleDelegateImpl#getAccountRulesBySet` 捕获透出
- [ ] Task 8: `RestCodeCheckUtilTest` 补 5 个用例（未购买×2、非数字错误码、普通错误回归、正常体回归）
- [ ] Task 9: 验证 — `mvn test`（RestCodeCheckUtilTest + RuleDelegateImplTest 相关用例）+ 编译通过
- [ ] Task 10: 更新 docs PR（spec 扩充）并交付后端 diff 摘要

## 验证方式

- 前端：ESLint / vue-tsc 通过（本仓无单测基础设施，行为验证依赖用户自测）
- 后端：Maven 单测（RestCodeCheckUtilTest 新增用例 + 既有用例回归）+ 全量编译
