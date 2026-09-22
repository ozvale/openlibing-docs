# optimize-enrich-revision-info

## 需求背景

enrichRevisionInfo 方法在查询 INC_SHIELD_DETAIL 表时，使用了 `defectId + defectStatus` 的复合条件。其中 defectStatus 的过滤（"2"已忽略/"3"审核中）可以前置到内存中完成，从而简化数据库查询条件为仅用 defectId，配合新增的 defectId 索引提升查询性能。

同时 task_inc_result_details 集合存在冗余索引，需要整合为更精准的复合索引以覆盖实际查询模式。

## 功能描述

**做**：
- 优化 IncDetailsOperation.enrichRevisionInfo：先从 defectVos 中筛选满足 defectStatus 条件的记录，提取 defectId，再仅用 defectId 查询 INC_SHIELD_DETAIL
- 优化 FullDetailsOperation.enrichRevisionInfo MR 模式：同上逻辑
- 为 inc_shield_detail 集合新增 defectId 索引（Liquibase）
- 为 task_inc_result_details 集合新增复合索引 idx_task_uuid_status_filepath_line
- 删除 task_inc_result_details 集合的 4 个冗余索引

**不做**：
- 不修改 FULL_SHIELD_DETAIL 相关查询逻辑
- 不修改外部接口

## 验收标准

- [ ] enrichRevisionInfo 查询 INC_SHIELD_DETAIL 时仅用 defectId 作为条件
- [ ] inc_shield_detail 集合新增 defectId 索引
- [ ] task_inc_result_details 集合新增 idx_task_uuid_status_filepath_line 索引（含 collation）
- [ ] task_inc_result_details 集合删除 4 个冗余索引
- [ ] 编译通过

## 影响范围

- IncDetailsOperation.java（查询逻辑优化）
- FullDetailsOperation.java（MR 模式查询逻辑优化）
- code_check_task_inc_index.xml（新增索引 changeSet）
