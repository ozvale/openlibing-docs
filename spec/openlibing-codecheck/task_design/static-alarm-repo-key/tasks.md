# 【openLiBing】全量代码检查支持多语言sarif文件上传 - 实现任务

## openlibing-codecheck 仓库

### repo_key 归一化匹配

- [x] `RepoUrlParser` 新增 `buildRepoKey()` 静态方法，拼接 `repoType::owner::repo`（全小写）
- [x] `StaticAlarmIssueEntity` 新增 `@Field("repo_key") private String repoKey` 字段
- [x] `StaticAlarmQueryDTO.RepoCoordinate` 从 `repoUrl` 改为 `repoKey`
- [x] `StaticAlarmOperation.buildRepoCoordinatesCriteria` 改为 `repo_key $in` 匹配
- [x] `StaticAlarmOperation.buildFacetCriteria` 改为 `repo_key $in` 匹配
- [x] `StaticAlarmOperation.countIssuesByRepoCoordinates` 改为 `repo_key $in` 匹配
- [x] `StaticAlarmServiceImpl` 适配 `RepoCoordinate` 变更
- [x] 删除冗余方法 `toRepoUrl()`（已无调用点）

### 索引变更

- [x] 新增 `idx_issue_repo_key_sort_last_seen`（repo_key + last_seen_at）
- [x] 新增 `idx_issue_repo_key_sort_updated_at`（repo_key + updatedAt）
- [x] 新增 `idx_issue_repo_key_sort_severity`（repo_key + severity_rank）
- [x] Beta 环境手动删除废弃索引 `idx_issue_repo_url_sort_*`

### 存量数据回填

- [x] 创建 `RepoKeyBackfillChange`（CustomTaskChange），通过标准 MongoDB CRUD 遍历回填
- [x] 绕过华为云 RDS `eval()` 权限限制和 MongoDB 4.0 聚合管道限制
- [x] 创建 `static_alarm_repo_key_backfill.xml` changeset
- [x] 索引 changeset ID 更新为 `20260727_create_idx_repo_key_sort`

### code_flows 精简

- [x] `CodeQlSarifParser` 提取 codeFlows 时仅保留 file、line、message 字段
- [x] 截断超过阈值的调用链时保留前 15 + 后 15 节点，防止丢失汇聚点

### category 筛选修复与多选支持

- [x] `StaticAlarmQueryDTO` category 由 `String` 改为 `List<String> categories`
- [x] `countIssues` 补回 category 查询条件
- [x] `filterOptions` 聚合管线新增 categories facet
- [x] `StaticAlarmFilterOptionsVO` 新增 `categories` 字段

### suppress 状态同步

- [x] `StaticAlarmOperation.updateExistingIssue` 补回 `isSuppressed()` 判断逻辑
- [x] 新增 `SUPPRESSED_RESOLVED` 事件类型，与 FIXED/CLEANUP_RESOLVED 区分

## openlibing-docs 仓库

- [x] 生成 `proposal.md`（需求背景 + 验收标准）
- [x] 生成 `tasks.md`（本文件）
- [ ] 生成 `archive.md`（归档总结）
- [ ] 创建 docs Issue + docs PR

## 关联

- 业务 PR: openlibing/openlibing-codecheck#282
- FE 需求: 【openLiBing】全量代码检查支持多语言sarif文件上传
