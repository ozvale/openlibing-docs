# tool-report-sla — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-framework/issues/82
- 业务 PR: https://gitcode.com/openlibing/openlibing-web/pulls/684
- docs PR: <待创建后补齐>

## 交付历程

- commit `142d8be1f53a3fc25270d3a4d8afd717897726af`: 工具管理-工具举报增加审核截止时间以及审核时间是否超时已自动下架 — 待办中心两个列表新增 SLA 两列
- commit `a74c7b12304af6a980259248e782d4b826dc9e1f`: 工具管理-工具举报部分需求联调 — 修复 pendingReviewCount 递减
- commit `aff3984e028603e71e6eff00552da7c9e32298d0`: 工具详情-优化 — 修复详情页举报状态显示逻辑

## 用户自测反馈

无返工，一次交付通过。

## 最终验证

- 待办中心 → 工具举报申请列表：「审核截止时间」「是否已超时自动下架」列正常展示 ✅
- 待办中心 → 工具举报审核列表：同上，审核通过后 `pendingReviewCount` 正确递减 ✅
- 工具市场详情页：举报状态 `0/1/2` 分别显示对应元素，异常值不回退 ✅

## 设计偏差与取舍

无偏差。代码改动与设计文档一致。

## 可复用经验

- Vue 模板中使用 `v-if`/`v-else-if`/`v-else` 链时，对于状态值是封闭枚举集合的场景，应改用显式 `v-if` 判断每个状态值，避免后端返回异常值时错误回退到默认分支。
- 待办中心类页面提交审核操作后，应同步递减所有相关的待办计数（如 `pendingReviewCount`、`toolReportCount`），避免计数与实际待办数量不一致。

## 归档日期

2026-08-12
