# 发布评审文件校验说明

- 发布仓：`openlibing-web`
- 发布分支：`release_20260616_hotfix`
- 远端 commit：`ca3ccc8c`（完整 SHA：`ca3ccc8ca8130e90dedb72bac363cf9ba2f82714`）
- 报告路径：`release_docs/openlibing-web/release_20260616_hotfix/ca3ccc8c/openlibing_web_release_report.md`
- 生成日期：2026-06-16

## 校验结果

- 合入 `release_20260616_hotfix` 的 PR 数量：**2**
- 已解析关联 issue：**1** 条（去重后）
- 缺失 issue 的合入 PR：**0** 条

## 合入 PR 清单

| PR | 标题 | 责任人 | 关联 issue |
| --- | --- | --- | --- |
| !519 | 优化代码检查详情页展示 | ningxinlong | openlibing-codecheck#103 |
| !520 | fix(security): upgrade form-data and vite for CVE-2026-12143/CVE-2026-53571 | ningxinlong | openlibing-codecheck#103 |

## 已纳入发布报告的 issue

- `#103`（PR !519、!520，责任人 ningxinlong）：[需求]: 版本级（nightly）流水线支持开源代码检测工具结果可视，并能采集数据支撑运营

## 说明

- 本次仅统计直接合入 `release_20260616_hotfix` 的 PR。
- PR !519 为静态检查页面功能交付，PR !520 为合入后安全扫描依赖漏洞修复（form-data、vite）。
- 两个 PR 关联同一 issue `#103`，发布报告按规范去重保留一行。
- 上一版 commit `ce547e1e`（仅含 !519）已被 `ca3ccc8c` 替代。

## 建议 docs issue 标题

`[需求]: openlibing-web仓20260616热修复发布`
