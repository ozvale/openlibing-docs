# proposal: 代码度量分支表快照列（metrics-latest-snapshot）

## 需求背景

代码仓管理-分支管理查询接口（`POST /openlibing-coderepo/repo/branch/list`、`POST /openlibing-coderepo/project-repo/query-repo-branch`）在拼装页面展示的 5 个代码度量指标（代码规模 / 平均代码行数 / 平均圈复杂度 / 总代码重复率 / 总文件重复率）时存在性能问题：

1. 度量 SQL `selectLatestByGitUrls` 无 latest 语义，每次查询返回涉及仓**所有分支 × 所有历史扫描**记录（含 `metrics_data_json` 大 JSON 列）；
2. Java 侧 `buildMergedMetricsVO` 从新到旧逐条解析历史 JSON 做跨记录补齐，翻每页重复付全价；
3. 按度量排序时全量拉分支 + 全历史度量记录，内存排序 + 内存分页，无法下推 SQL。

**方案**：将 5 个指标值直接落为 `repo_branch` 分支表冗余列（对齐 UT 行覆盖率先例），查询零拼接、排序下推 SQL；写入侧上报入库后同步刷列；存量由定时任务刷入。`code_metrics_record` 与 `metrics_data_json` 原文保留不动（详情页与 codecheck 机机接口继续使用）。

**范围**：仅 `openlibing-coderepo` 单仓；前端零改动；UT 三列与代码检查告警数（staticAlertCount，存 codecheck Mongo）本次不改动，记后续优化。

## 验收标准

1. 分支管理页三个场景（全部分支 / 单仓 / Tag）指标展示正常，点击指标跳转详情正常（走详情接口"不传 runId → 兜底最新成功记录"路径），列表值与详情数据同源一致；
2. 查询接口度量部分每次请求 DB 仅返回每 (git_url, branch_name) 1 条记录（列表链路不再访问 `code_metrics_record`）；
3. 度量排序为 SQL `ORDER BY` 下推，内存排序路径删除；
4. 新上报成功后分支表 5 列同步更新为本次快照值；
5. 刷数任务执行后存量分支 5 列补齐，任务幂等（二次刷全部 skip）、支持全量/定向两种模式反复刷；
6. `metrics_data_json` 内容保持上报原样，codecheck 机机接口 `/metrics/code/latest-by-commit/batch` 回归通过；
7. 本地编译 + 相关单测通过；pre-commit 对全部改动文件通过。
