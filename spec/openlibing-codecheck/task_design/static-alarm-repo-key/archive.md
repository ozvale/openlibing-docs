# 【openLiBing】全量代码检查支持多语言sarif文件上传 — 归档

## 1. 背景摘要

`static_alarm_issue` 表中 `repo_url` 字段保留了扫描时的原始域名，导致同一仓库在测试域（`test.gitcode.net`）和正式域（`gitcode.com`）扫描出的记录使用不同的 `repo_url`。后端按项目多仓查询时，从 `repo_info` 表构造 `repo_url $in` 条件，测试域入库的记录无法被匹配，造成分支/分类筛选"数据不可见"。

本次引入 `repo_key` 字段（格式：`{repoType}::{owner}::{repo}`，全小写，域名无关），在入库和查询两侧统一使用该字段做匹配。同期修复了 code_flows 体积过大、category 筛选失效/不支持多选、suppress 状态不同步等问题。

## 2. 改动清单

### 2.1 openlibing-codecheck（分支 `codeql-feat-yym`）

| 文件 | 操作 | 说明 |
|------|------|------|
| `common/util/repo/RepoUrlParser.java` | 修改 | 新增 `buildRepoKey()` 静态方法；删除冗余 `toRepoUrl()` |
| `business/entity/alarm/StaticAlarmIssueEntity.java` | 修改 | 新增 `@Field("repo_key") private String repoKey` |
| `business/entity/dto/alarm/StaticAlarmQueryDTO.java` | 修改 | `RepoCoordinate` 的 `repoUrl` → `repoKey`；category 改为 `List<String>` |
| `business/operation/alarm/StaticAlarmOperation.java` | 修改 | 3 处查询条件 `repo_url $in` → `repo_key $in`；count/filter 补回 category 筛选；updateExistingIssue 补回 suppress 处理 |
| `business/service/impl/alarm/StaticAlarmServiceImpl.java` | 修改 | 适配 `RepoCoordinate` 变更 |
| `business/service/parser/CodeQlSarifParser.java` | 修改 | code_flows 精简为 file+line+message；截断保留首尾节点 |
| `common/config/mongo/changelog/RepoKeyBackfillChange.java` | 新增 | CustomTaskChange，通过标准 CRUD 遍历回填存量 repo_key |
| `resources/db/changelog/mongo/v1.0.0/static_alarm_index.xml` | 修改 | 新增 `idx_issue_repo_key_sort_*` 3 条复合索引；changeset ID 更新 |
| `resources/db/changelog/mongo/v1.0.0/static_alarm_repo_key_backfill.xml` | 新增 | 引用 `RepoKeyBackfillChange` 的 changeset |
| `resources/db/changelog/db.mongodb.changelog.xml` | 修改 | 新增 include 引入回填 changeset |

### 2.2 openlibing-docs（分支 `spec/openlibing-codecheck/static-alarm-repo-key`）

| 文件 | 操作 | 说明 |
|------|------|------|
| `spec/openlibing-codecheck/task_design/static-alarm-repo-key/proposal.md` | 新增 | 需求背景 + 验收标准 |
| `spec/openlibing-codecheck/task_design/static-alarm-repo-key/tasks.md` | 新增 | 实现任务清单 |
| `spec/openlibing-codecheck/task_design/static-alarm-repo-key/archive.md` | 新增 | 本文件 |

## 3. 关联 PR

| 仓 | PR | 状态 |
|------|------|------|
| `openlibing-codecheck` | https://gitcode.com/openlibing/openlibing-codecheck/pull/282 | 已创建 |
| `openlibing-docs` | <待填> | 待创建（Phase 5） |

## 4. 关键决策记录

### 4.1 为什么新增 repo_key 而不是归一化 repo_url 值

最初考虑直接归一化 `repo_url` 的取值语义（写入时统一域名），只需覆盖存量字段。但 `repo_url` 在前端有展示用途，不能修改其原始值。因此采用"新增专门的匹配字段 + repo_url 保留原样做展示"方案，新增 3 条 repo_key 前缀索引。

### 4.2 为什么不能用 Liquibase eval() 回填

华为云 RDS MongoDB 禁用了 `eval()` 命令权限。聚合管道 update（`$concat` + `$toLower`）需要 MongoDB 4.2+，当前生产为 4.0.28 不支持。最终采用 `CustomTaskChange`（Java 代码通过标准 CRUD 遍历回填），Liquibase changeset 执行一次后自动跳过。

### 4.3 为什么旧 repo_url 索引不能在 Liquibase 里自动删除

`failOnError="false"` 对 MongoDB 扩展不生效，且 `dropIndexes` 在索引不存在时会中断 Liquibase 执行。已改为手动在对应环境执行删除，不在 Liquibase changeset 中管理。

## 5. 部署注意事项

1. **索引**：部署后确认 `idx_issue_repo_key_sort_*` 3 条索引创建成功
2. **存量回填**：`RepoKeyBackfillChange` 会在 Liquibase update 时自动执行（仅一次，`DATABASECHANGELOG` 记录后跳过）
3. **旧索引清理**：生产环境部署后手动删除 `idx_issue_repo_url_sort_*` 3 条索引（Beta 已删）
4. **新数据**：应用代码已在入库时写入 `repo_key`，无需额外处理

## 6. 经验沉淀

### 6.1 查询匹配键应独立于展示字段

`repo_url` 既是展示字段又是查询匹配键，导致"保留原始域名"与"跨域名匹配"的矛盾不可调和。任何有展示需求的字段不应同时承担查询匹配职责——应为匹配逻辑设计专用的归一化键。

### 6.2 MongoDB 4.0 + RDS 受限环境的 Liquibase 回填策略

当 `eval()` 被禁用且聚合管道 update 不可用时，`CustomTaskChange` 是唯一能在 Liquibase 内自动完成存量回填的方式。虽然写法比纯 XML/脚本重，但满足"部署时自动执行一次"的运维要求。

### 6.3 调用链截断应保留首尾

`code_flows` 截断时如果只保留前 N 步，会丢掉调用链末端的"汇聚点"（实际漏洞触发位置）。正确的做法是保留前 15 + 后 15 节点，中间省略部分用占位符表示。
