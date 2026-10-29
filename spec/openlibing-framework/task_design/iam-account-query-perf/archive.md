# iam-account-query-perf — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-framework/issues/116
- 业务 PR: https://gitcode.com/openlibing/openlibing-framework/pull/488（已合并）
- docs PR: 本文档所属 PR

## 交付历程

| commit     | 说明                                                                                                                     |
| ---------- | ------------------------------------------------------------------------------------------------------------------------ |
| `349f09d0` | `perf(iam)`: selectIAMAccounts 去 distinct/join 膨胀，改 EXISTS 相关子查询；新增 6 索引 changelog；等价性 + 迁移幂等测试 |
| `e4755a83` | `test(iam)`: 分页用例补确定性排序；seed 增多授权账号去重断言；迁移测试清 changelog 重估 indexExists 前置条件             |
| `8ca74a41` | `test(iam)`: 补 user_basic_info 重复 userId 脏数据场景等价性用例                                                         |

## 平台 AI 检视闭环

PR #488 收到 6 条 AI 检视意见，全部合理评估并回复：

- **已修复（resolve）**：
  - 分页等价性用例缺 `order by`（顺序不确定）→ 拆分 ORDER_BY/ORDER_PAGE，分页用确定性排序
  - 幂等测试未真验证 `indexExists`（DATABASECHANGELOG 短路）→ 清空 changelog 后重跑重估 preCondition
  - seed 无账号同时拥 ≥2 条有效授权 → 新增 c1 账号 + 绝对期望断言
- **测试佐证（已回复，人工审阅）**：
  - `distinct` 移除后 `user_basic_info` join 倍增风险 → 脏数据重复 userId 用例佐证新旧一致
- **解释评估（已回复，人工审阅）**：
  - 索引前置列 project_id vs create_by → 前端恒传 projectId（DTO @NotNull），维持现状
  - 硬编码 SQL 未加载 mapper XML → 本仓无 MyBatis 集成测试基础设施、旧 SQL 已删除，以字符串 oracle 等价性兜底

## 用户自测反馈

- 未反馈功能问题；进入 Phase 4 前确认自测完成。

## 最终验证

- 等价性测试 11 项通过（5 grantStatus 分支 + projectId/name/userName 过滤 + 分页 + 多授权去重 + 脏数据）
- Liquibase 迁移测试 2 项通过（建索引幂等重估 + 缺表安全跳过）
- IAM 相关单测 89 项通过；pre-commit 门禁（Spotless/CheckStyle/SpotBugs/PMD/gitleaks）通过
- PR #488 已合并，CI 通过

## 设计偏差与取舍

- **不带缓存**：仅 SQL 重构 + 索引，避免一致性与失效成本。
- **保留 `locate()` 任意子串语义**：不改造前缀匹配，守住"功能零变化"承诺（检视与方案早期曾评估走索引）。
- **不加 keyset 深分页**：等价改造成本高、首屏只取前 10 条，收益待真实库确认。
- **模糊匹配 `name`/`user_name` 未建索引**：仅搜索时生效，非首屏路径；覆盖会浪费存储与写放大。
- **方案文档中的 `H2 schema.sql` 对齐项未改**：iam_account 等表由外部 DBA 维护，H2 仅有测试专用建表，无生产 schema 可对齐。

## 未决验证（需部署后跟进）

- 真实库 EXPLAIN 复测确认索引命中、规避 `ALL` 分支 OR 结构退化为全表扫的风险。
- beta/prod 埋点对比优化前后 `selectIAMAccounts` P95/P99 耗时，验证 LCP 改善。

## 可复用经验

- **等价性测试以"旧 SQL 字符串为 oracle"**：业务 SQL 重构无法在无真实库的仓内做 EXPLAIN 时，用 H2 同一 seed 跑新旧两句全分支比对，是最低成本的功能零变化证明。
- **Liquibase 幂等测试必须重估 preCondition**：第二次 `liquibase.update()` 会被 DATABASECHANGELOG 短路，不验证 `indexExists`；需清 changelog 后重跑才能真正验证前置条件。
- **`OR ... 分支 + 复合索引`**：`a.create_by=? or exists(...)` 结构优化器通常不走单列/复合索引，优化此类查询优先考虑拆 UNION 或保证覆盖热点分支；本次以"前端恒传必填过滤字段"为索引设计依据。

## 归档日期

2026-10-28
