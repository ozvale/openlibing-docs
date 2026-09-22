# bug_fix_0606 — 归档

## 关联
- 业务 Issue: https://gitcode.com/openlibing/openlibing-ops/issues/42
- 业务 PR: https://gitcode.com/openlibing/openlibing-ops/merge_requests/82

## 交付历程
- commit `b26f344`: 修复测试用例结果映射错误并补齐NPU/successCount汇总
- commit `1de73b8`: 提取TestcaseQueryParams参数对象统一管理查询参数
- commit `0b6bf28`: filter test jobs in pipeline summary aggregation，增加 testJobIds 过滤
- commit `7a405f8`: correct job status comparison from success to COMPLETED，修正状态匹配
- commit `f24a7f8`: replace null return with empty string in resolvePipelineName，统一 null/blank 处理

## 用户自测反馈
- 发现 `resolvePipelineName` 返回 null 时 `isTestJob` 边界不严谨 → 修复 commit `f24a7f8`，改用 `StringUtils.hasText` + 空字符串返回值

## 最终验证
- PR CI 通过（ci-pipeline-passed）
- PR 已合入 release_20260611_iter1
- 接口返回的 vCpu/NPU 消耗与明细之和一致

## 设计偏差与取舍
- 进行了防御性优化：将 `resolvePipelineName` 返回值从 null 改为空字符串，`isTestJob` 空判断从 `== null` 改为 `StringUtils.hasText`。经分析对实际逻辑无影响，属于健壮性提升。

## 可复用经验
- 无

## 归档日期
2026-06-09
