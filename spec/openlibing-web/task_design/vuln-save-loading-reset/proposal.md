# 需求背景

## 需求描述

修复 0-day 漏洞新增/编辑弹窗（addVuln.vue）在保存请求失败后按钮 loading 状态未重置的问题：请求失败（网络错误/接口报错）时 Promise 走入 reject 分支，原代码只在 `.then()` 中重置 `btnLoading`，导致按钮持续显示转圈、无法再次提交，只能刷新页面恢复。

## 关联 Issue

- [openlibing/openlibing-web#300](https://gitcode.com/openlibing/openlibing-web/issues/300)（[缺陷]: 0-day漏洞保存提示失败之后，按钮仍然显示圈圈）

## 验收标准

1. ✅ 新增漏洞弹窗：保存请求失败后按钮 loading 消失，恢复可点击，可再次提交
2. ✅ 编辑漏洞弹窗：同上验证
3. ✅ 请求成功场景回归：正常提交路径（成功提示、emit refresh、关闭弹窗）不受影响

## 变更范围

- `apps/web-openlibing/src/views/Vulnerability0Day/vulnerabilityView/addVuln.vue`（+28 / -20）

## 优先级

中（交互阻断类缺陷：失败后无法重试）

## 关联 PR

- [PR #795 fix(vuln): 新增/编辑漏洞弹窗请求失败时重置按钮loading状态](https://gitcode.com/openlibing/openlibing-web/pull/795)（已合入 release_20260923，2026-09-22）
