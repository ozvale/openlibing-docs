# optimize-enrich-revision-info — 实现任务

## 进度: 0/4 complete

- [ ] Task 1: 优化 IncDetailsOperation.enrichRevisionInfo — 先筛选满足 defectStatus 条件的 defectId，再仅用 defectId 查询 INC_SHIELD_DETAIL
- [ ] Task 2: 优化 FullDetailsOperation.enrichRevisionInfo MR 模式 — 同 Task 1 逻辑
- [ ] Task 3: 新增 Liquibase changeSet — inc_shield_detail 的 defectId 索引 + task_inc_result_details 新复合索引
- [ ] Task 4: 新增 Liquibase changeSet — 删除 task_inc_result_details 的 4 个冗余索引
