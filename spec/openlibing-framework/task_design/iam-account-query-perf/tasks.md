# iam-account-query-perf — 实现任务

## 进度: 0/5 complete

- [ ] Task 1: 现状基线分析 — 读取 `IAMAccountServiceImpl.queryAccount` 与 `IAMAccountMapper.xml`，对 `selectIAMAccounts` 的 3 个典型参数组合（ALL / FROMME / TOME + 分页）分别 EXPLAIN，记录基线 plan 与耗时
- [ ] Task 2: SQL 重构 — 移除 `select distinct` 导致的笛卡尔膨胀，授权关联改子查询/聚合（保持 `is_has_grant_user`/`is_has_grant_role` 语义与行数等价），`name`/`user_name` 模糊匹配评估改用 `LIKE 'xxx%'` 前缀匹配以走索引
- [ ] Task 3: 新增索引 — `db/changelog/v1.0.1/` 下新增 changelog：`iam_account(project_id, create_by)`、`iam_account(name)`、授权表 `iam_account_grant_user(resource_id, validity_time)`、`iam_account_grant_user_role(resource_id, validity_time)`（以实际 EXPLAIN 依据为准）
- [ ] Task 4: 验证 — H2 测试库 + 单测覆盖重构后 SQL；`mvn` 相关测试与编译；EXPLAIN 复测确认走索引；等价性对照（重构前后行集合一致）
- [ ] Task 5: 归档准备 — commit 说明、验证结果汇总，供 Phase 5 archive.md 使用
