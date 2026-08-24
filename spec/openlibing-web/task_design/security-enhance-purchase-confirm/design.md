# security-enhance-purchase-confirm — 技术设计

## 方案概述

在 `CustomRuleConfig.vue` 的 `submitForm()` 最前置增加安全增强规则检测与购买确认弹窗，检测逻辑与后端分类规则对齐（`ruleTages` 包含 `security_enhance`）。

## 架构决策

| 决策 | 说明 | 原因 |
|------|------|------|
| 前端本地判定（方案 A） | 用 `handleSubmitData()` 产出的最终 `ruleIds` 与已加载 `ruleList` 匹配 `ruleTages` | 用户可勾选的规则必然在已加载列表中；零额外请求。已评估方案 B（保存前调接口反查全量标签），因复杂度高、覆盖的是用户不可见规则而放弃 |
| 挂载点在 `submitForm()` 最前置 | 购买确认先于"复制到社区"确认弹窗 | 三种保存场景（add/copy/config）共用单一入口，统一拦截 |
| 后端判定依据 `ruleTages` | 接口返回的单条规则无独立 `ruleSecurity` 字段；后端 `RuleDelegateImpl#filterByCriteria` 用 `ruleTages.toLowerCase().contains("security_enhance")` 分类 | 与后端逻辑保持一致，避免前后端分类口径不一致 |
| 纯前端确认，不调购买接口 | 信任用户"已购买"确认 | 平台暂无购买状态查询接口，需求也仅要求提示确认 |

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/web-openlibing/src/views/RuleSetDirectory/CodeCheckRule/children/CustomRuleConfig.vue` | 修改 | 新增检测函数 + 重构 `submitForm()` 增加弹窗前置拦截（约 40 行） |

## 实现要点

1. 新增 `getSecurityEnhanceRules(ruleIdsStr)`：解析最终保存的 `ruleIds` 字符串，在 `ruleList` 中筛选 `ruleTages?.toLowerCase().includes('security_enhance')` 的规则
2. `submitForm()` 重构为：先构建 `doSubmit()`（内含原复制确认 + 提交逻辑），保存前检测，命中则 `ElMessageBox.confirm`（确认 → `doSubmit()`；取消 → 静默中断），未命中直接 `doSubmit()`
3. 弹窗文案含命中规则条数，按钮：`已购买，继续保存` / `未购买`，type: warning，与页面现有弹窗风格一致

## 风险 & 缓解

- 已知局限：基于规则集带入但未加载到当前分页的规则不在检测范围内（用户未见过/未勾选这些规则，符合交互实际）；如需全量覆盖需后端支持，本期不做
- 行为变化风险：新增弹窗可能影响既有保存操作路径 → 验收标准第 4 条保证未勾选增强规则时行为与现状完全一致

## 跨仓影响

无。仅前端单文件，不改后端、不改接口契约。
