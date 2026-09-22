# Proposal: 引入 repo_key 解决多域名扫描数据筛选不可见问题

## 需求背景

`static_alarm_issue` 表在后端入库时被扫域名不同（例如 `test.gitcode.net` vs `gitcode.com`），导致同一仓库在不同域名下扫描的问题记录 `repo_url` 字段值不同。当用户按项目查询多仓问题时（`buildRepoCoordinatesCriteria`），后端从 `repo_info` 表拉取项目下所有仓库配置，构造 `repo_url $in` 条件。由于入库域名的差异，`repo_info` 中正式域的 `repo_url` 无法匹配测试域扫描入库的记录，造成部分分支数据在筛选时"消失"——数据库中存在但列表/筛选接口不可见。

## 解决方案

引入 `repo_key` 字段（格式：`{repoType}::{owner}::{repo}`，全小写），由 `RepoUrlParser.buildRepoKey()` 生成，域名无关。入库时写入该字段，查询时用 `repo_key $in` 替代原来的 `repo_url` 匹配逻辑，消除域名差异导致的数据不可见问题。

## 同期修复的配套问题

本次一并处理的 bug 和优化：

| 问题 | 描述 |
|------|------|
| code_flows 数据体积过大 | 单条约 22KB，精简调用链为 file + line + message 结构，截断时保留首尾关键节点 |
| count 接口 category 筛选失效 | `countIssues` 未将 category 条件传入查询 |
| filter 接口 category 筛选失效 | `filterOptions` 聚合管线未加入 category facet |
| category 不支持多选 | DTO 改为 `List<String> categories`，查询用 `$in` |
| suppress 处理只覆盖新建分支 | `updateExistingIssue` 中补回 suppress 自修复（SUPPRESSED_RESOLVED）逻辑 |

## 影响范围

- 仓库：`openlibing-codecheck`
- 模块：`StaticAlarmOperation`、`StaticAlarmQueryDTO`、`StaticAlarmServiceImpl`、`CodeQlSarifParser`
- 接口变化：VO 新增 `categories` 字段；`RepoCoordinate` 从 `repoUrl` 改为 `repoKey`
- 数据模型变化：`StaticAlarmIssueEntity` 新增 `repo_key` 字段
- 索引变化：新增 3 条 `repo_key` 前缀复合索引，废弃 3 条旧 `repo_url` 前缀索引（仅 Beta 环境已删除，生产待删除）
- 存量数据：通过 Liquibase CustomChange（`RepoKeyBackfillChange`）自动回填

## 验收标准

- [x] 入库时 `repo_key` 由 `RepoUrlParser.buildRepoKey()` 生成并写入文档
- [x] list/count/filter 接口用 `repo_key $in` 替代 `repo_url` 匹配，消除域名差异
- [x] code_flows 精简后单条数据体积从约 22KB 降至 1-2KB
- [x] count 接口 category 筛选正确
- [x] filter-options 接口返回 categories 维度
- [x] category 支持多选（`display_categories $in`）
- [x] 已 suppress 的问题再次扫描时自动翻转为 RESOLVED
- [x] 新索引 `idx_issue_repo_key_sort_*` 创建成功
- [x] 存量数据 repo_key 通过 CustomChange 自动回填（MongoDB 4.0 + eval 禁用环境适用）
- [x] toRepoUrl() 冗余函数已删除

## 关联

- 业务 PR: openlibing/openlibing-codecheck#282
