# security-enhance-purchase-confirm — 实现任务

## 进度: 0/4 complete

- [ ] Task 1: 在 `openlibing-web` 新建开发分支 `feat-security-enhance-purchase-confirm`（基于 `origin/master`）
- [ ] Task 2: `CustomRuleConfig.vue` 新增 `getSecurityEnhanceRules()` 检测函数
- [ ] Task 3: 重构 `submitForm()`：抽出 `doSubmit()`，前置购买确认弹窗（已购买→继续；未购买→中断）
- [ ] Task 4: 验证 — `pnpm lint`（改动文件）+ `pnpm check:type`，自检生成前约束清单

## 验证方式

- ESLint 通过（改动文件无 lint 错误）
- `vue-tsc` 类型检查通过
- 本仓无单测基础设施（AGENTS.md 明确），行为验证依赖用户自测（新增/复制/修改 × 勾选/未勾选增强规则 × 已购买/未购买 共 8 条路径，重点覆盖验收标准 5 条）
