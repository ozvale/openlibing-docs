# Nightly 流水线版本级优先统计口径 — 技术设计

## 方案概述

在两个 mapper 的「项目 Nightly 流水线集合」CTE 内完成平台识别、版本级分类与项目级回退；下游聚合（`pipeline_build_rate`、`nightly_rate`、下钻 list/count/summary）零改动。接口、前端、ETL 均不变。

## 口径定义

| 项        | 定义                                                                                          |
| --------- | --------------------------------------------------------------------------------------------- |
| Base 集合 | 项目下 `dm_rd_efc_project_pipeline_relation.pipeline_type='NIGHTLY'` 的流水线                 |
| 版本级    | 仅非 GitHub：`LOWER(pipeline_name) LIKE 'nightly-version-pipeline%'`                          |
| 组件级    | 仅非 GitHub：其余全部（= 非版本级）                                                           |
| GitHub    | 不判定级别，始终保留                                                                          |
| 回退      | 配置口径：项目存在非 GitHub 版本级 → 非 GitHub 只留版本级；否则留全部非 GitHub；GitHub 恒保留 |

集合表达式：`is_github = 1 OR is_version_level = has_version_level`。

## 架构决策

### 决策 1：分类放在 mapper SQL，而不是 ETL 加字段或 Java 层过滤

- ETL 加 `pipeline_level` 字段需要跨团队排期，本仓无法闭环；
- Java 层过滤需要额外查询并把 pipelineId 列表下发，分页/计数复杂度上升；
- 当前两种命名前缀都落在 `pipeline_type='NIGHTLY'`（上游 ETL 按 `LOWER(pipeline_name) LIKE 'nightly%'` 推导），消费侧做一次二分即可，零 schema 变更。

### 决策 2：GitHub 不参与版本级/组件级约束

GitHub workflow 命名规则未在数据层沉淀；若套用前缀，可能整体误判为组件级并改变混合项目数值。选择"GitHub 始终保留"，GitHub 版本可用度分支保持原样（不 join 过滤集合），行为与改造前严格一致。

### 决策 3：回退采用配置口径

只要 relation 中存在非 GitHub 版本级流水线即只统计版本级，不按时间窗内是否有运行数据回退。代价是"有版本级配置但窗口内无数据"时指标为 NULL，需作为预期行为并做数据治理；换来集合跨时间窗稳定、count 接口无需引入事实表。

### 决策 4：聚合口径不变

仍为逐流水线 `AVG(ROUND(率,4))`（等权平均），不改为 `SUM(available_days)/SUM(total_days)`；本次仅收敛集合，避免引入第二个口径变量。

## 技术实现

### 主表 `OpsMainStatMapper.xml`

`selected_pipelines` 拆为 3 个 CTE（最终名保持不变）：

```sql
nightly_pipelines_all AS (
    SELECT r.project_id, r.pipeline_id, MAX(r.pipeline_name) AS name,
           MAX(CASE WHEN r.platform = 'github' THEN 1 ELSE 0 END) AS is_github,
           MAX(CASE WHEN r.platform <> 'github'
                     AND LOWER(r.pipeline_name) LIKE 'nightly-version-pipeline%'
                    THEN 1 ELSE 0 END) AS is_version_level
    FROM dm_rd_efc_project_pipeline_relation r
    WHERE r.pipeline_type = 'NIGHTLY'
      /* projectIds 下推 */
    GROUP BY r.project_id, r.pipeline_id
),
nightly_project_scope AS (
    SELECT project_id, MAX(is_version_level) AS has_version_level
    FROM nightly_pipelines_all
    WHERE is_github = 0
    GROUP BY project_id
),
selected_pipelines AS (
    SELECT a.project_id, a.pipeline_id, a.name
    FROM nightly_pipelines_all a
    LEFT JOIN nightly_project_scope s ON s.project_id = a.project_id
    WHERE a.is_github = 1
       OR a.is_version_level = IFNULL(s.has_version_level, 0)
)
```

GitHub 版本可用度分支保持原样；`pipeline_build_rate`、`nightly_rate`、`nightly_count`、`nightly_npu_stat` 不改。

### 下钻 `OpsNightlyDetailMapper.xml`

`nightlySelectedPipelinesCte` 扩为相同 3 个 CTE（片段名不变，4 个 select 的 include 零改动），其中 scope 为单行聚合 + `CROSS JOIN`：

```sql
nightly_pipelines_all AS (
    SELECT r.pipeline_id, MAX(r.platform) AS platform,
           MAX(r.pipeline_name) AS pipeline_name,
           MAX(CASE WHEN r.platform = 'github' THEN 1 ELSE 0 END) AS is_github,
           MAX(CASE WHEN r.platform <> 'github'
                     AND LOWER(r.pipeline_name) LIKE 'nightly-version-pipeline%'
                    THEN 1 ELSE 0 END) AS is_version_level
    FROM dm_rd_efc_project_pipeline_relation r
    WHERE r.pipeline_type = 'NIGHTLY' AND r.project_id = #{req.projectId}
    GROUP BY r.pipeline_id
),
nightly_project_scope AS (
    SELECT MAX(is_version_level) AS has_version_level
    FROM nightly_pipelines_all WHERE is_github = 0
),
selected_pipelines AS (
    SELECT p.pipeline_id, p.platform, p.pipeline_name
    FROM nightly_pipelines_all p
    CROSS JOIN nightly_project_scope s
    WHERE p.is_github = 1
       OR p.is_version_level = IFNULL(s.has_version_level, 0)
)
```

GitHub 版本可用度分支保持原样。

### 注意点

- 必须使用**正向 CASE** 打标；`pipeline_name` 为 NULL/空串时落组件级，禁止 `NOT LIKE`（NULL 会丢行）。
- 统一 `LOWER()` 比较，Doris `LIKE` 区分大小写。
- 平台标记用聚合前 `CASE`：任一平台命中 GitHub 即视为 GitHub 行（保守保留）。

## 行为变化矩阵

| 项目类型              | 改前        | 改后                 | 数值 |
| --------------------- | ----------- | -------------------- | ---- |
| 纯版本级（非 GitHub） | 全部        | 版本级               | 不变 |
| 纯组件级（非 GitHub） | 全部        | 全部                 | 不变 |
| CodeArts 混合         | 全部        | 仅版本级             | 变化 |
| 仅 GitHub             | 全部 GitHub | 全部 GitHub          | 不变 |
| GitHub + 组件级       | 全部        | 全部                 | 不变 |
| GitHub + 版本级       | 全部        | 版本级 + 全部 GitHub | 变化 |
| 无 NIGHTLY            | 空          | 空                   | 不变 |

## 涉及文件

| 文件                                                                                                   | 操作                    |
| ------------------------------------------------------------------------------------------------------ | ----------------------- |
| `openlibing-ops/src/main/resources/mapper/OpsMainStatMapper.xml`                                       | 修改（集合 CTE + 注释） |
| `openlibing-ops/src/main/resources/mapper/OpsNightlyDetailMapper.xml`                                  | 修改（集合 CTE + 注释） |
| `openlibing-ops/src/test/java/com/openlibing/ops/domain/mapper/ops/OpsMainStatMapperXmlTest.java`      | 新增                    |
| `openlibing-ops/src/test/java/com/openlibing/ops/domain/mapper/ops/OpsNightlyDetailMapperXmlTest.java` | 新增                    |

## 风险 & 缓解

| 风险                                   | 缓解                                                       |
| -------------------------------------- | ---------------------------------------------------------- |
| 混合项目指标与灯号变化                 | 口径变更说明；数据校验 SQL 输出混合项目清单                |
| 版本级配置存在但窗口无数据 → 指标 NULL | 作为配置口径预期行为；数据治理清理停用流水线               |
| 命名大小写/NULL 异常                   | `LOWER()` + 正向 CASE + 数据校验                           |
| 两份复制 CTE 漂移                      | 单测断言两 mapper 前缀字面量一致                           |
| 资源指标被误改                         | 单测断言 `nightly_count`/`nightly_npu_stat` 不引用过滤集合 |

## 跨仓影响

无。前端与接口契约不变；ETL 不变。
