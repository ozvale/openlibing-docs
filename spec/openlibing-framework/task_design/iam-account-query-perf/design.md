# iam-account-query-perf — 技术设计

## 方案概述

在不改接口契约与返回结构的前提下，用「SQL 重构 + 索引补齐」消除 `selectIAMAccounts` 的偶发全表扫描与笛卡尔膨胀。不加缓存。

## 架构决策

1. **去 `distinct` join 膨胀**：原 SQL 用 2 个授权子查询 left join + `select distinct`，当授权表数据量大时中间结果膨胀。改为关联字段上做存在性判断（`EXISTS`/`IN` 或聚合子查询），保证每 iam 账户行数唯一。
2. **模糊匹配走索引**：`locate(#{name}, a.name) > 0` 与 `locate(#{userName}, a.user_name) > 0` 必须全表扫。业务上为「前缀包含」语义时改 `LIKE 'xxx%'` 可走 `(name)`/`(user_name)` 索引；若必须「任意子串」则保留 locate 但评估成本与索引兜底。最终语义以等价性测试锁定。
3. **分页排序**：`order by CASE ... create_time desc limit offset` 深分页成本高，先保留单表内 `create_time desc` + 索引，评估是否需 keyset 优化（接口契约不变前提下可选）。

## 涉及文件

| 文件                                                                      | 操作      | 说明                                |
| ------------------------------------------------------------------------- | --------- | ----------------------------------- |
| `src/main/resources/mapper/IAMAccountMapper.xml`                          | 修改      | `selectIAMAccounts` 的关联/查询重构 |
| `src/main/resources/db/changelog/v1.0.1/iam_account_query_perf_index.xml` | 新增      | 索引 changelog                      |
| `src/main/resources/db/changelog/db.changelog.xml`                        | 修改      | include 新 changelog                |
| `src/main/resources/h2/schema.sql`                                        | 修改      | 测试库对齐索引（如需）              |
| `src/test/java/.../IAM*Test.java`                                         | 修改/新增 | 重构后 SQL 行为测试                 |

## 风险 & 缓解

| 风险                                | 缓解                                                             |
| ----------------------------------- | ---------------------------------------------------------------- |
| SQL 重构结果与现网不一致            | 等价性对照：重构前后对同一数据执行、比对行集合与字段             |
| 索引变更影响 DML 性能 / 加锁        | 索引在低峰通过 Liquibase 执行；单列短索引，避免覆盖索引冗余      |
| 数据库迁移失败                      | changelog 版本号递增、不动已执行脚本；H2 对齐验证                |
| 偶发性慢的根因不在 SQL（如网络/GC） | Task 1 基线与 EXPLAIN 先行定位，若 SQL 非瓶颈则停止改 SQL 并反馈 |

## 跨仓影响

- 仅 `openlibing-framework` 后端 + `openlibing-docs` 文档。无接口契约变化，前端不受影响。
