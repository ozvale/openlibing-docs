# iam-account-query-perf — 技术设计

## 方案概述

在不改接口契约与返回结构的前提下，用「SQL 重构 + 索引补齐」消除 `selectIAMAccounts` 的偶发全表扫描与笛卡尔膨胀。不加缓存。

## 架构决策

1. **去 `distinct` 与 join 膨胀**：原 SQL 用 2 张授权表全量子查询 left join + `select distinct`，账号×有效用户授权×有效角色授权产生笛卡尔中间态。改为授权存在性用 `EXISTS` 相关子查询判定（`is_has_grant_user`/`is_has_grant_role`），每个账号固定 1 行，天然无需 distinct。
   - 相关子查询走 `(resource_id, validity_time)` 索引反查，避免授权表全量物化。
2. **模糊匹配**：`locate(#{name}, a.name) > 0` 保持任意子串语义不变（改造为前缀匹配会改变功能，违背"零变化"承诺），未新增 name 索引；该过滤仅在用户显式输入时生效，非首屏路径。
3. **分页排序**：`order by CASE WHEN create_by ... create_time desc limit offset` 交互不变；`(project_id, create_by)` 覆盖首屏（前端恒传 projectId）过滤与排序，未引入 keyset 深分页改造（等价成本高、收益待真实库确认）。

## 涉及文件

| 文件                                                                      | 操作 | 说明                                                            |
| ------------------------------------------------------------------------- | ---- | --------------------------------------------------------------- |
| `src/main/resources/mapper/IAMAccountMapper.xml`                          | 修改 | `selectIAMAccounts` 授权关联改 EXISTS 相关子查询，去掉 distinct |
| `src/main/resources/db/changelog/v1.0.1/iam_account_query_perf_index.xml` | 新增 | 6 个索引，`tableExists`/`indexExists` 前置条件 + rollback       |
| `src/main/resources/db/changelog/db.changelog.xml`                        | 修改 | include 新 changelog                                            |
| `src/test/java/.../mapper/SelectIAMAccountsEquivalenceTest.java`          | 新增 | 旧/新 SQL 等价性测试（11 项）                                   |
| `src/test/java/.../config/IAMAccountQueryIndexMigrationTest.java`         | 新增 | Liquibase 迁移幂等/缺表跳过测试（2 项）                         |

## 风险 & 缓解

| 风险                                             | 缓解                                                                                                                       |
| ------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| SQL 重构结果与现网不一致                         | 等价性测试：同一 seed 下旧/新 SQL 全分支比对，含多授权去重与脏数据场景                                                     |
| `user_basic_info.user_id` 无唯一约束时可致行倍增 | 已由等价性脏数据用例佐证（同名不同 email 的重复行 distinct 本不去重，新旧一致）；生产环境 user_id 业务上唯一，风险窗口极窄 |
| 索引前置列 project_id 与主过滤 create_by 的顺序  | 前端恒传 projectId（DTO `@NotNull`），复合索引可命中；ALL 分支 OR 结构本就走不了单列索引，不增冗余索引                     |
| 数据库迁移失败/重复                              | changelog 幂等：`indexExists` 前置条件 + 迁移测试清 changelog 重估验证；不动已执行脚本                                     |
| 偶发根因不在 SQL                                 | 已排除：queryAccount 单查询无缓存/串行依赖，主因即 SQL 结构                                                                |

## 未决验证（部署后跟进）

- 真实库 EXPLAIN 复测确认索引命中、基线耗时对比（本仓无真实库连接，测试只能在 H2 验证等价性）。

## 跨仓影响

- 仅 `openlibing-framework` 后端 + `openlibing-docs` 文档。无接口契约/返回结构变化，前端不受影响。
- 关联业务 Issue：https://gitcode.com/openlibing/openlibing-framework/issues/116（子项）
- 业务 PR：https://gitcode.com/openlibing/openlibing-framework/pull/488
