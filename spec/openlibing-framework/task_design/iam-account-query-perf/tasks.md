# iam-account-query-perf — 实现任务

## 进度: 4/5 complete

- [x] Task 1: 现状基线分析 — 读取 `IAMAccountServiceImpl.queryAccount`（:784）与 `IAMAccountMapper.xml`，定位 `selectIAMAccounts` 三类问题：① 授权表全量子查询 left join + `select distinct` 笛卡尔膨胀；② `locate()` 不走索引；③ `ORDER BY CASE ... limit offset` 深分页。本仓无真实库，以静态分析 + H2 等价性测试落地基线，未做真实 EXPLAIN（timebox 内不可行）。
- [x] Task 2: SQL 重构 — 移除 `select distinct` 与两张授权表派生表 join，授权存在性改 `EXISTS` 相关子查询（`is_has_grant_user`/`is_has_grant_role` 语义与行数等价）。`name`/`user_name` 保持 `locate()` 任意子串语义（改造前缀匹配会改变功能，违背零变化约束），由等价性测试锁定。
- [x] Task 3: 新增索引 — `v1.0.1/iam_account_query_perf_index.xml` 新增 6 个索引：`iam_account(project_id, create_by)`、`iam_account(resource_id)`、`iam_account_grant_user(resource_id, validity_time)`、`iam_account_grant_user(grant_user_id, resource_id)`、`iam_account_grant_user_role(resource_id, validity_time)`、`iam_account_grant_user_role(grant_user_role, resource_id)`，均带 `tableExists`+`indexExists` 前置条件与 rollback。
- [x] Task 4: 验证 — H2 内存库等价性测试 `SelectIAMAccountsEquivalenceTest`（11 项：5 分支 + 过滤 + 分页 + 多授权去重 + 脏数据）+ Liquibase 迁移幂等测试 `IAMAccountQueryIndexMigrationTest`（2 项）；`mvn test` 相关 89 项通过，pre-commit 门禁通过。
- [ ] Task 5: 归档准备 — 真实库 EXPLAIN 复测（beta/prod）确认走索引、压测耗时对比。**待部署后补充，作为 PR #488 后续验证项。**
