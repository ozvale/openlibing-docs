# filter-meta 组合扫描合并 — 归档记录

- 归档日期：2026-11-27
- 业务 Issue：<https://gitcode.com/openlibing/openlibing-cicd/issues/569>
- 模式：Standard；两仓同构实现
- 详细设计：[design.md](design.md) ｜ 评审串讲：[design-review.html](design-review.html) ｜ 任务清单：[tasks.md](tasks.md)
- 本次变更无后端 HTTP 接口变动，未生成 api.md

## 交付结果

| 仓库                | PR                                                                  | 状态                       | merge head                                 |
| ------------------- | ------------------------------------------------------------------- | -------------------------- | ------------------------------------------ |
| openlibing-cicd     | [!715](https://gitcode.com/openlibing/openlibing-cicd/pull/715)     | 已合入（2026-11-27 16:38） | `c658db9a32b08e70e0e7bc3536e04054064920d6` |
| openlibing-coderepo | [!365](https://gitcode.com/openlibing/openlibing-coderepo/pull/365) | 已合入（2026-11-27 16:38） | `e8ba3bccd40a079c962c2706409c701aa9e7eb35` |

业务 commit（每仓 3 轮：初版 + 两轮检视修复）：

- cicd：`a4264fea8` → `029ca39a1` → `f0ed3398f`
- coderepo：`be764f9e` → `797982b2` → `1d666f26`

## 方案落地摘要

5 次 GROUP BY 全扫描 → 2 次：1 次 combo 扫描（`selectFilterMetaCombo`，`GROUP BY user_name, resource_name, ip, log_result LIMIT 10000`）+ 1 次 moduleId 专用查询（沿用 `selectFilterMetaGroupBy`）；4 个值维度候选列表在应用侧从 combo 行拆分聚合，与 30s TTL 缓存叠加。零 DDL、接口无变化。

## 检视闭环摘要

| PR            | 意见数               | 修复 | 回复说明（不修）                                                                                                  | resolve |
| ------------- | -------------------- | ---- | ----------------------------------------------------------------------------------------------------------------- | ------- |
| cicd !715     | 7（行内 5 / 顶层 2） | 4    | 3（其中 1 条明确拒绝：排序统一——两路径共用同一 `toFilterMetaItems` 重载与三级 comparator，moduleId 保持 DB 顺序） | 5/5     |
| coderepo !365 | 9（行内 7 / 顶层 2） | 7    | 2                                                                                                                 | 7/7     |

检视修复后相对初版设计的关键实现决策（已回写 design.md 决策表）：

1. combo 仅在请求含 ≥2 个值维度时启用；单值维度直走 `selectFilterMetaGroupBy`；
2. selectedValues >1000 超限校验前移到任何 DB 查询之前统一预检；
3. collation 归一化：IN 匹配、归并 key、排序 value 均按 `Locale.ROOT` 小写（对齐 `utf8mb4_*_ci`；重音不敏感未实现，代码注释注明；展示值经 displayNames 保留原文）；
4. 维度键静态常量表 `FILTER_META_DIMENSION_KEYS`，`otherKeys` 行循环外预计算；
5. 熔断回退（`COMBO_ROW_LIMIT` = 10000）不变；
6. 其他维度过滤语义确认为严格 IN（存在 selectedValues 则行值必须命中集合，null / 空串天然不命中即跳过）。

## 验证证据

| 仓库                | 单元测试          | 增量行覆盖率（门禁 ≥80%） |
| ------------------- | ----------------- | ------------------------- |
| openlibing-cicd     | 2195 用例全部通过 | 98.00%                    |
| openlibing-coderepo | 1869 用例全部通过 | 97.12%                    |

覆盖率测量口径：`.agents/scripts/incremental_coverage.py`（merge-base 圈定改动行 + JaCoCo 报告），与 CI `ut.yml` diff-cover 同口径。

## 经验沉淀

- 应用侧拆分替代单 SQL 多 WHERE：一条 combo SQL 无法表达「每个维度 skip 自身」的 4 种过滤语义，应用侧按行拆分聚合是唯一保真路径；MySQL `_ci` collation 对应 Java 侧 `Locale.ROOT` 小写归一（重音不敏感除外）。
- 熔断阈值（行数 == LIMIT 即回退旧路径）让「性能优化」具备最坏情形正确性兜底，可作为同类改写模板。
- docs 归档陷阱：`git reset --soft` 对齐 upstream 新基线时，会把 upstream 侧删除的文件以 staged deletion 形式带入暂存区，提交前必须 `git restore --staged` 剔除，避免 docs PR 混入无关删除。
