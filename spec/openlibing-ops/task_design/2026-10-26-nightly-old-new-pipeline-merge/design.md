# Nightly 流水线新旧切换历史数据合并方案（方案 J 最终版）

- 关联 Issue：https://gitcode.com/openlibing/openlibing-ops/issues/289
- 目标仓库：`openlibing-ops`、`openlibing-ops-web`、`openlibing-docs`
- 涉及数据层：Doris、DolphinScheduler
- 文档状态：方案 J 最终实现设计，待评审
- 编写日期：2026-10-27

---

## 1. 需求白话版

### 1.1 切换前

某条 Nightly 流水线叫 `X`，`pipeline_id = A`。它每天正常跑，看板上能看到 `X` 的执行次数、成功率、时长、版本可用度等历史数据。

### 1.2 切换后

为了切 pytest：

- 旧流水线 `A` 改名为 `old_X`；
- 新流水线改名为 `X`，`pipeline_id = B`；
- 新流水线在正式切换前，已经用 `X` 这个名字跑过一段时间 pytest 调试。

### 1.3 看板现在的问题

看板按 `pipeline_id` 统计，于是：

1. 旧流水线 `A` 被当成 `old_X` 或直接判成 `OTHER`，历史数据从 Nightly 看板消失；
2. 新流水线 `B` 从第一次调试开始的数据全部被算成正式 Nightly 数据；
3. 看板上看起来像 `X` 的历史被清空，然后突然出现一段调试数据。

### 1.4 期望效果

对业务来说，`X` 还是同一条流水线，只是中间换了 ID。看板应该表现为：

- 切换前的数据来自旧流水线 `A`；
- 切换后的数据来自新流水线 `B`；
- 新流水线 `B` 在切换前的 pytest 调试运行不计入正式 Nightly 指标；
- 日期范围跨切换点时，一条逻辑流水线 `X` 的曲线是连续的；
- 点开明细时，旧运行和新运行都能看到，且跳转链接仍然指向实际运行的流水线。

涉及页面：

- Nightly 流水线看板（图表、汇总、明细、下钻）；
- 工程能力运营看板（Nightly 明细、资源环境 Nightly、主表 Nightly 指标）；
- 开源项目运营看板（Nightly 汇总、Nightly 明细，与 Nightly 看板共用后端口径）。

---

## 2. 约束和前提

### 2.1 约束

1. 接口性能优先，不能在查询时大量扫事实表、做复杂 join 或多轮查询；
2. 允许新建 DM 维度表、DM 汇总表；
3. 不在现有事实表、DM 表、relation 表上加稀疏列，避免大量 null。

### 2.2 前提

1. `dm_rd_efc_project_pipeline_relation` 的 `NIGHTLY` 识别默认是正确的。relation 识别错属于 relation 任务的问题，本方案不额外做兜底。
2. 新表可以像现有 `dm_rd_efc_build_dim_nightly_pipeline_day` 一样每次全量刷新，不做增量。
3. 映射表数据很少，当前由开发/运营手动维护，后续规范后再考虑自动化。
4. 工程能力运营看板只展示到昨天，不展示今天，允许预聚合滞后。
5. 逻辑日宽表只存分子、分母，不存率字段，查询时计算。

---

## 3. 最终表设计

只保留 **3 张新表**：

| 表                                       | 作用                                           | 数据量                             |
| ---------------------------------------- | ---------------------------------------------- | ---------------------------------- |
| `dm_rd_efc_nightly_pipeline_alias`       | 逻辑流水线下所有实际流水线的映射和有效时间区间 | 很少，只维护发生过切换的逻辑流水线 |
| `dm_rd_efc_nightly_pipeline_logical_run` | 逻辑运行事实表，保证分位数、明细准确           | 与 Nightly 运行数同量级            |
| `dm_rd_efc_nightly_pipeline_logical_day` | 逻辑日汇总宽表，含运行、用例、资源指标         | 逻辑流水线数 × 天数                |

不再建：

- `dm_rd_efc_nightly_pipeline_dim`
- `dm_rd_efc_nightly_testcase_logical_day`
- `dm_rd_efc_nightly_pipeline_resource_day`

---

## 4. 表结构设计

> 最终建表语句、字段类型、字段顺序、唯一键以 `docs/table.sql` 为准；本节 DDL 仅用于说明设计意图。

### 4.1 逻辑流水线映射表 `dm_rd_efc_nightly_pipeline_alias`

**设计原则**

- 只维护发生过切换的逻辑流水线；
- 一条逻辑流水线下的所有实际流水线 ID 都写进来，包括旧 ID、中间 ID、当前新 ID；
- 每个实际 ID 用 `valid_from / valid_to` 表示有效区间；
- 支持多次改名，不依赖“旧 ID → 新 ID”的单跳映射；
- 唯一键包含 `pipeline_project`，因为同一 openlibing 项目下，`pipeline_project` 才是流水线真正归属的项目；
- alias 同时存 `logical_pipeline_name`，取当前新流水线名称；
- 表数据由人工维护，数据量很小。

```sql
CREATE TABLE IF NOT EXISTS dm_rd_efc_nightly_pipeline_alias (
  project_id            INT          NOT NULL COMMENT 'openlibing 项目ID',
  pipeline_project      VARCHAR(512) NOT NULL COMMENT '流水线项目：codearts 为华为云项目ID，gitcode/github 为 repo_url',
  platform              VARCHAR(20)  NOT NULL COMMENT 'codearts/gitcode/github',
  pipeline_id           VARCHAR(64)  NOT NULL COMMENT '实际流水线ID，包括旧ID、中间ID、当前新ID',
  logical_pipeline_id   VARCHAR(64)  NOT NULL COMMENT '逻辑流水线ID，通常是最终新流水线ID',
  logical_pipeline_name VARCHAR(512) NOT NULL COMMENT '逻辑流水线名称，填当前新流水线名称',
  valid_from            DATETIME     NOT NULL DEFAULT '1970-01-01 00:00:00' COMMENT '生效开始，左闭',
  valid_to              DATETIME     NOT NULL DEFAULT '9999-12-31 23:59:59' COMMENT '生效结束，右开'
) ENGINE=OLAP
UNIQUE KEY(project_id, pipeline_project, platform, pipeline_id)
COMMENT 'Nightly 逻辑流水线映射，人工维护'
DISTRIBUTED BY HASH(project_id) BUCKETS 1
PROPERTIES ("replication_allocation" = "tag.location.default: 2");
```

**单次切换示例**

逻辑流水线 `X`：

| project_id | pipeline_project        | platform | logical_pipeline_id | pipeline_id | valid_from          | valid_to            |
| ---------- | ----------------------- | -------- | ------------------- | ----------- | ------------------- | ------------------- |
| 1          | 华为云项目ID或 repo_url | codearts | B（新 ID）          | A（旧 ID）  | 1970-01-01          | 2026-10-01 10:00:00 |
| 1          | 华为云项目ID或 repo_url | codearts | B（新 ID）          | B（新 ID）  | 2026-10-01 10:00:00 | 9999-12-31          |

规则：

- 旧 ID 在切换时间点之前有效；
- 新 ID 在切换时间点之后有效；
- 新流水线切换前的调试运行落在 `valid_from` 之前，自动排除；
- 旧流水线切换后的运行落在 `valid_to` 之后，自动排除；
- 区间采用左闭右开 `[valid_from, valid_to)`，切换时间点只归新流水线。

**多次切换示例**

逻辑流水线 `X`：A → B → C

| pipeline_project        | logical_pipeline_id | pipeline_id | valid_from          | valid_to            |
| ----------------------- | ------------------- | ----------- | ------------------- | ------------------- |
| 华为云项目ID或 repo_url | C                   | A           | 1970-01-01          | 2026-08-01 10:00:00 |
| 华为云项目ID或 repo_url | C                   | B           | 2026-08-01 10:00:00 | 2026-10-01 10:00:00 |
| 华为云项目ID或 repo_url | C                   | C           | 2026-10-01 10:00:00 | 9999-12-31          |

这样不需要递归解析，也不会出现多次改名不适配。

**人工维护方式**

1. 先查候选映射：
   ```sql
   SELECT
     platform,
     pipeline_id,
     MAX(pipeline_name) AS pipeline_name,
     MAX(end_time) AS last_end_time
   FROM dwr_rd_efc_pipeline_run_unified
   WHERE platform IN ('codearts', 'gitcode')
   GROUP BY platform, pipeline_id
   ORDER BY platform, pipeline_name;
   ```
2. 找到 `old_X` 和 `X` 对应的实际 ID；
3. 按有效区间写入 alias；
4. 用下面 SQL 校验区间没有重叠、没有空洞：
   ```sql
   SELECT
     logical_pipeline_id,
     pipeline_id,
     valid_from,
     valid_to,
     LEAD(valid_from) OVER (
       PARTITION BY project_id, platform, logical_pipeline_id
       ORDER BY valid_from
     ) AS next_valid_from
   FROM dm_rd_efc_nightly_pipeline_alias
   ORDER BY project_id, platform, logical_pipeline_id, valid_from;
   ```
   `valid_to` 应等于下一行的 `valid_from`；最后一行 `valid_to` 应为 `9999-12-31`。

### 4.2 逻辑运行事实表 `dm_rd_efc_nightly_pipeline_logical_run`

**作用**

- 一行 = 一条实际运行，保留实际 `pipeline_id` 和实际 `pipeline_run_id`；
- 增加 `logical_pipeline_id`，供看板按逻辑流水线聚合；
- 是 Nightly 列表分位数、最长时长、明细下钻的准确数据来源；
- 每次全量刷新。

```sql
CREATE TABLE IF NOT EXISTS dm_rd_efc_nightly_pipeline_logical_run (
  project_id                   INT          NOT NULL COMMENT 'openlibing 项目ID',
  pipeline_project             VARCHAR(512) NOT NULL COMMENT '流水线项目：codearts 为华为云项目ID，gitcode 为 repo_url',
  platform                     VARCHAR(20)  NOT NULL COMMENT '平台：codearts/gitcode',
  pipeline_id                  VARCHAR(64)  NOT NULL COMMENT '实际流水线ID',
  pipeline_run_id              VARCHAR(64)  NOT NULL COMMENT '实际运行ID',
  run_date                     DATE         NOT NULL COMMENT '运行日期，取运行结束时间所在日期',
  logical_pipeline_id          VARCHAR(64)  NOT NULL COMMENT '逻辑流水线ID',
  logical_pipeline_name        VARCHAR(512) NULL COMMENT '逻辑流水线名称',
  pipeline_run_number          INT          NULL,
  pipeline_name                VARCHAR(512) NULL,
  pipeline_status              VARCHAR(32)  NULL,
  pipeline_run_starttime       DATETIME     NULL,
  pipeline_run_endtime         DATETIME     NULL,
  actual_duration_ms           BIGINT       NULL,
  efficiency_duration_ms       BIGINT       NULL,
  build_count                  INT          NULL,
  build_pass_count             INT          NULL,
  build_avg_time_ms            DECIMAL(20,2) NULL,
  build_max_time_ms            BIGINT       NULL,
  build_min_time_ms            BIGINT       NULL,
  test_count                   INT          NULL,
  test_pass_count              INT          NULL,
  test_avg_time_ms             DECIMAL(20,2) NULL,
  test_max_time_ms             BIGINT       NULL,
  test_min_time_ms             BIGINT       NULL,
  build_pending_duration_ms    BIGINT       NULL,
  test_pending_duration_ms     BIGINT       NULL,
  build_execution_duration_ms  BIGINT       NULL,
  test_execution_duration_ms   BIGINT       NULL,
  is_version_available         TINYINT      NULL,
  case_total_count             INT          NULL,
  case_release_count           INT          NULL,
  case_run_count               INT          NULL,
  case_skip_count              INT          NULL,
  case_run_pass_count          INT          NULL,
  case_run_fail_count          INT          NULL,
  case_release_rate            DECIMAL(10,4) NULL,
  case_pass_rate               DECIMAL(10,4) NULL,
  case_total_count_p0          INT          NULL,
  case_release_count_p0        INT          NULL,
  case_run_count_p0            INT          NULL,
  case_run_pass_count_p0       INT          NULL,
  case_run_fail_count_p0       INT          NULL,
  case_release_rate_p0         DECIMAL(10,4) NULL,
  case_pass_rate_p0            DECIMAL(10,4) NULL
) ENGINE=OLAP
UNIQUE KEY(project_id, pipeline_project, platform, pipeline_id, pipeline_run_id, run_date)
COMMENT 'Nightly 逻辑运行事实表'
DISTRIBUTED BY HASH(pipeline_run_id) BUCKETS 10
PROPERTIES (
  "replication_allocation" = "tag.location.default: 2",
  "enable_unique_key_merge_on_write" = "true"
);
```

说明：

- 唯一键 `(project_id, pipeline_project, platform, pipeline_id, pipeline_run_id, run_date)` 保证一条实际运行只有一行。
- `logical_pipeline_id` 是值列，全量刷新时会按最新 alias 重新归属。
- 全量刷新可以避免“映射变更后要单独回刷”的复杂流程。

### 4.3 逻辑日汇总宽表 `dm_rd_efc_nightly_pipeline_logical_day`

**作用**

- 一行 = 一条逻辑流水线 + 一天；
- 同时存储运行指标、用例指标、资源指标；
- 只存分子、分母，不存率字段；
- 每次全量刷新。

```sql
CREATE TABLE IF NOT EXISTS dm_rd_efc_nightly_pipeline_logical_day (
  project_id              INT          NOT NULL,
  pipeline_project        VARCHAR(512) NOT NULL,
  platform                VARCHAR(20)  NOT NULL,
  logical_pipeline_id     VARCHAR(64)  NOT NULL,
  run_date                DATE         NOT NULL,
  logical_pipeline_name   VARCHAR(512) NULL,

  -- 运行指标
  run_count               INT          NULL,
  run_success_count       INT          NULL,
  build_count             INT          NULL,
  build_pass_count        INT          NULL,
  test_count              INT          NULL,
  test_pass_count         INT          NULL,
  is_version_available    TINYINT      NULL,
  e2e_duration_ms         BIGINT       NULL,
  efficiency_duration_ms  BIGINT       NULL,
  build_avg_time_ms       BIGINT       NULL,
  build_max_time_ms       BIGINT       NULL,
  test_avg_time_ms        BIGINT       NULL,
  test_max_time_ms        BIGINT       NULL,

  -- 用例指标（当天选中的运行）
  case_run_id             VARCHAR(64)  NULL,
  case_pipeline_status    VARCHAR(32)  NULL,
  case_total_count        INT          NULL,
  case_release_count      INT          NULL,
  case_run_count          INT          NULL,
  case_skip_count         INT          NULL,
  case_run_pass_count     INT          NULL,
  case_run_fail_count     INT          NULL,
  case_total_count_p0     INT          NULL,
  case_release_count_p0   INT          NULL,
  case_run_count_p0       INT          NULL,
  case_run_pass_count_p0  INT          NULL,
  case_run_fail_count_p0  INT          NULL,

  -- 资源指标
  resource_run_count      INT          NULL,
  cpu_seconds             DOUBLE       NULL,
  npu_seconds             DOUBLE       NULL,
  memory_seconds          DOUBLE       NULL
) ENGINE=OLAP
UNIQUE KEY(project_id, pipeline_project, platform, logical_pipeline_id, run_date)
COMMENT 'Nightly 逻辑流水线日汇总宽表'
DISTRIBUTED BY HASH(logical_pipeline_id) BUCKETS 4
PROPERTIES (
  "replication_allocation" = "tag.location.default: 2",
  "enable_unique_key_merge_on_write" = "true"
);
```

说明：

- 率字段（成功率、构建成功率、测试成功率、用例率）不存，查询时用分子/分母计算。
- 用例字段和资源字段都与“逻辑流水线 + 日期”同粒度，可以合并。
- 项目级表 `dwi_project_nightly_resource_day`、`dwi_project_resource_indicator_day` 从这张表汇总生成。

---

## 5. 逻辑流水线清单怎么来

不建 dim 表，直接从 relation 取：

```sql
SELECT
  r.project_id,
  r.platform,
  r.pipeline_id AS logical_pipeline_id,
  MAX(r.pipeline_name) AS logical_pipeline_name,
  MAX(r.pipeline_project) AS pipeline_project
FROM dm_rd_efc_project_pipeline_relation r
WHERE r.pipeline_type = 'NIGHTLY'
GROUP BY r.project_id, r.platform, r.pipeline_id;
```

说明：

- 普通未切换流水线直接在 relation 里。
- 切换后的新流水线也在 relation 里，名称已经是新名称。
- 旧 ID 改名后不满足 `nightly%` 规则，relation 会判成 `OTHER`，所以列表查询直接用 `NIGHTLY` 即可，不需要再查 alias。
- 如果以后 relation 规则把旧 ID 也判成 `NIGHTLY`，需要重新加回 alias 排除。
- 这里默认 relation 是正确的。

---

## 6. ETL 任务设计

建议新增工作流：`[job][dm][nightly]逻辑流水线数据构建`

> 下面 SQL 只说明取数逻辑。正式开发时 `INSERT` 必须显式写列名，字段顺序和类型以 `docs/table.sql` 为准，避免字段顺序不一致。

任务顺序：

1. 全量刷新逻辑运行事实表；
2. 全量刷新逻辑日汇总宽表；
3. 刷新工程能力项目级预聚合表。

映射表由人工维护，不放进日常 ETL。

### 6.1 全量刷新逻辑运行事实表

```sql
TRUNCATE TABLE dm_rd_efc_nightly_pipeline_logical_run;

WITH pipeline_binding AS (
  SELECT DISTINCT
    project_id,
    pipeline_project,
    platform,
    pipeline_id
  FROM dm_rd_efc_project_pipeline_relation
)
INSERT INTO dm_rd_efc_nightly_pipeline_logical_run
SELECT
  b.project_id,
  b.pipeline_project,
  b.platform,
  f.pipeline_id,
  f.pipeline_run_id,
  DATE(f.pipeline_run_endtime),
  COALESCE(a.logical_pipeline_id, f.pipeline_id) AS logical_pipeline_id,
  COALESCE(a.logical_pipeline_name, lr.pipeline_name) AS logical_pipeline_name,
  f.pipeline_run_number,
  f.pipeline_name,
  f.pipeline_status,
  f.pipeline_run_starttime,
  f.pipeline_run_endtime,
  f.actual_duration_ms,
  f.efficiency_duration_ms,
  f.build_count,
  f.build_pass_count,
  f.build_avg_time_ms,
  f.build_max_time_ms,
  f.build_min_time_ms,
  f.test_count,
  f.test_pass_count,
  f.test_avg_time_ms,
  f.test_max_time_ms,
  f.test_min_time_ms,
  f.build_pending_duration_ms,
  f.test_pending_duration_ms,
  f.build_execution_duration_ms,
  f.test_execution_duration_ms,
  f.is_version_available,
  f.case_total_count,
  f.case_release_count,
  f.case_run_count,
  f.case_skip_count,
  f.case_run_pass_count,
  f.case_run_fail_count,
  f.case_release_rate,
  f.case_pass_rate,
  f.case_total_count_p0,
  f.case_release_count_p0,
  f.case_run_count_p0,
  f.case_run_pass_count_p0,
  f.case_run_fail_count_p0,
  f.case_release_rate_p0,
  f.case_pass_rate_p0
FROM dwr_rd_efc_build_fact_nightly_test_case_pipeline_run f
JOIN pipeline_binding b
  ON b.pipeline_id = f.pipeline_id
LEFT JOIN dm_rd_efc_nightly_pipeline_alias a
  ON a.project_id = b.project_id
 AND a.pipeline_project = b.pipeline_project
 AND a.platform = b.platform
 AND a.pipeline_id = f.pipeline_id
JOIN dm_rd_efc_project_pipeline_relation lr
  ON lr.project_id = b.project_id
 AND lr.platform = b.platform
 AND lr.pipeline_id = COALESCE(a.logical_pipeline_id, f.pipeline_id)
 AND lr.pipeline_type = 'NIGHTLY'
WHERE f.pipeline_run_endtime IS NOT NULL
  AND (
    a.pipeline_id IS NULL
    OR (
      a.valid_from <= f.pipeline_run_endtime
      AND a.valid_to > f.pipeline_run_endtime
    )
  );
```

核心逻辑：

1. 先用实际流水线 ID 在 relation 里找到它所属的 `project_id`、`pipeline_project`、`platform`（不区分 `pipeline_type`）。
2. 再按 `(project_id, pipeline_project, platform, pipeline_id)` 关联 alias。因为一个 `pipeline_project` 可能对应多个 openlibing 项目，alias 必须带上项目维度关联，否则同一条运行会在多个项目间被重复放大。
3. 如果实际流水线在 alias 中：
   - 只有在 `[valid_from, valid_to)` 区间内才保留；
   - 区间外的运行直接不要；
   - 用 `a.logical_pipeline_id` 去 relation 找当前新流水线的名称。
4. 如果实际流水线不在 alias 中：
   - 普通未切换流水线，全部保留；
   - 用实际 `pipeline_id` 去 relation 找名称。
5. `logical_pipeline_id`：
   - alias 命中时用 `a.logical_pipeline_id`；
   - alias 未命中时用实际 `pipeline_id`。

这里的关键是：

- 旧流水线切换后的运行，落在 `valid_to` 之后，被排除；
- 新流水线切换前的调试运行，落在 `valid_from` 之前，被排除；
- 中间多代流水线按各自区间保留；
- 不需要增量，不需要回刷状态。
- relation 默认正确，不做额外兜底。

### 6.2 全量刷新逻辑日汇总宽表

```sql
TRUNCATE TABLE dm_rd_efc_nightly_pipeline_logical_day;

WITH pipeline_binding AS (
  SELECT DISTINCT
    project_id,
    pipeline_project,
    platform,
    pipeline_id
  FROM dm_rd_efc_project_pipeline_relation
),
metrics AS (
  SELECT
    project_id,
    pipeline_project,
    platform,
    logical_pipeline_id,
    MAX(logical_pipeline_name) AS logical_pipeline_name,
    run_date,
    COUNT(1) AS run_count,
    SUM(CASE WHEN pipeline_status = 'COMPLETED' THEN 1 ELSE 0 END) AS run_success_count,
    SUM(build_count) AS build_count,
    SUM(build_pass_count) AS build_pass_count,
    SUM(test_count) AS test_count,
    SUM(test_pass_count) AS test_pass_count,
    MAX(is_version_available) AS is_version_available,
    ROUND(AVG(actual_duration_ms)) AS e2e_duration_ms,
    ROUND(AVG(efficiency_duration_ms)) AS efficiency_duration_ms,
    ROUND(AVG(build_avg_time_ms)) AS build_avg_time_ms,
    MAX(build_max_time_ms) AS build_max_time_ms,
    ROUND(AVG(test_avg_time_ms)) AS test_avg_time_ms,
    MAX(test_max_time_ms) AS test_max_time_ms
  FROM dm_rd_efc_nightly_pipeline_logical_run
  GROUP BY project_id, pipeline_project, platform, logical_pipeline_id, run_date
),
case_ranked AS (
  SELECT
    project_id,
    pipeline_project,
    platform,
    logical_pipeline_id,
    logical_pipeline_name,
    run_date,
    pipeline_run_id,
    pipeline_status,
    case_total_count,
    case_release_count,
    case_run_count,
    case_skip_count,
    case_run_pass_count,
    case_run_fail_count,
    case_total_count_p0,
    case_release_count_p0,
    case_run_count_p0,
    case_run_pass_count_p0,
    case_run_fail_count_p0,
    ROW_NUMBER() OVER (
      PARTITION BY project_id, pipeline_project, platform, logical_pipeline_id, run_date
      ORDER BY CASE WHEN pipeline_status = 'COMPLETED' THEN 0 ELSE 1 END,
               pipeline_run_endtime DESC
    ) AS rn
  FROM dm_rd_efc_nightly_pipeline_logical_run
),
case_selected AS (
  SELECT * FROM case_ranked WHERE rn = 1
),
resource AS (
  SELECT
    b.project_id,
    b.pipeline_project,
    b.platform,
    COALESCE(a.logical_pipeline_id, u.pipeline_id) AS logical_pipeline_id,
    MAX(COALESCE(a.logical_pipeline_name, lr.pipeline_name)) AS logical_pipeline_name,
    DATE(COALESCE(u.end_time, u.start_time)) AS run_date,
    COUNT(DISTINCT u.pipeline_run_id) AS resource_run_count,
    SUM(CAST(u.cpu_second AS DOUBLE)) AS cpu_seconds,
    SUM(CAST(u.npu_second AS DOUBLE)) AS npu_seconds,
    SUM(CAST(u.memory_second AS DOUBLE)) AS memory_seconds
  FROM dwr_rd_efc_pipeline_run_unified u
  JOIN pipeline_binding b
    ON b.pipeline_id = u.pipeline_id
   AND b.platform = u.platform
  LEFT JOIN dm_rd_efc_nightly_pipeline_alias a
    ON a.project_id = b.project_id
   AND a.pipeline_project = b.pipeline_project
   AND a.platform = b.platform
   AND a.pipeline_id = u.pipeline_id
  JOIN dm_rd_efc_project_pipeline_relation lr
    ON lr.project_id = b.project_id
   AND lr.platform = b.platform
   AND lr.pipeline_id = COALESCE(a.logical_pipeline_id, u.pipeline_id)
   AND lr.pipeline_type = 'NIGHTLY'
  WHERE (a.pipeline_id IS NULL
    OR (
      a.valid_from <= COALESCE(u.end_time, u.start_time)
      AND a.valid_to > COALESCE(u.end_time, u.start_time)
    ))
    AND u.platform IN ('codearts', 'gitcode')
  GROUP BY
    b.project_id,
    b.pipeline_project,
    b.platform,
    COALESCE(a.logical_pipeline_id, u.pipeline_id),
    DATE(COALESCE(u.end_time, u.start_time))
)
INSERT INTO dm_rd_efc_nightly_pipeline_logical_day
SELECT
  COALESCE(m.project_id, c.project_id, r.project_id),
  COALESCE(m.pipeline_project, c.pipeline_project, r.pipeline_project),
  COALESCE(m.platform, c.platform, r.platform),
  COALESCE(m.logical_pipeline_id, c.logical_pipeline_id, r.logical_pipeline_id),
  COALESCE(m.run_date, c.run_date, r.run_date),
  COALESCE(m.logical_pipeline_name, c.logical_pipeline_name, r.logical_pipeline_name, ''),
  m.run_count, m.run_success_count,
  m.build_count, m.build_pass_count, m.test_count, m.test_pass_count,
  m.is_version_available,
  m.e2e_duration_ms, m.efficiency_duration_ms,
  m.build_avg_time_ms, m.build_max_time_ms, m.test_avg_time_ms, m.test_max_time_ms,
  c.pipeline_run_id AS case_run_id,
  c.pipeline_status AS case_pipeline_status,
  c.case_total_count, c.case_release_count, c.case_run_count, c.case_skip_count,
  c.case_run_pass_count, c.case_run_fail_count,
  c.case_total_count_p0, c.case_release_count_p0, c.case_run_count_p0,
  c.case_run_pass_count_p0, c.case_run_fail_count_p0,
  r.resource_run_count, r.cpu_seconds, r.npu_seconds, r.memory_seconds
FROM metrics m
FULL OUTER JOIN case_selected c
  ON m.project_id = c.project_id
 AND m.pipeline_project = c.pipeline_project
 AND m.platform = c.platform
 AND m.logical_pipeline_id = c.logical_pipeline_id
 AND m.run_date = c.run_date
FULL OUTER JOIN resource r
  ON COALESCE(m.project_id, c.project_id) = r.project_id
 AND COALESCE(m.pipeline_project, c.pipeline_project) = r.pipeline_project
 AND COALESCE(m.platform, c.platform) = r.platform
 AND COALESCE(m.logical_pipeline_id, c.logical_pipeline_id) = r.logical_pipeline_id
 AND COALESCE(m.run_date, c.run_date) = r.run_date;
```

说明：

- 全量刷新，不做增量。
- 率字段不写，查询时用分子/分母算。
- 资源运行数来自运行统一表，Nightly 运行数来自测试事实表，两者不保证相等。
- 正式脚本见 `tasks.md` 3.3、3.4：`INSERT` 显式写列名；日汇总用 `all_keys + LEFT JOIN` 替代 `FULL OUTER JOIN`，避免 Doris 复杂 join 条件。

### 6.3 工程能力项目级预聚合

任务：`Nightly流水线资源消耗日聚合`（`177531009881440`）

- 从 `dm_rd_efc_nightly_pipeline_logical_day` 汇总到项目级：

```sql
TRUNCATE TABLE dwi_project_nightly_resource_day;

INSERT INTO dwi_project_nightly_resource_day
SELECT
  r.project_id,
  r.run_date,
  spi.project_name,
  spi.product_id,
  NULL,
  SUM(r.cpu_seconds),
  SUM(r.npu_seconds),
  SUM(r.memory_seconds),
  NOW()
FROM dm_rd_efc_nightly_pipeline_logical_day r
LEFT JOIN sdi_project_info spi ON r.project_id = spi.project_id
WHERE r.run_date <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
GROUP BY r.project_id, r.run_date, spi.project_name, spi.product_id;
```

任务：`工程能力看板数据汇总`（`177531067754848`）

- `nightly_stats` 从日汇总宽表汇总：

```sql
nightly_stats AS (
  SELECT
    project_id,
    run_date AS stat_date,
    CAST(SUM(build_pass_count) AS DOUBLE) / CAST(NULLIF(SUM(build_count), 0) AS DOUBLE) AS nightly_build_success_rate,
    CAST(MAX(is_version_available) AS DOUBLE) AS nightly_version_availability_rate
  FROM dm_rd_efc_nightly_pipeline_logical_day
  WHERE run_date <= DATE_SUB(CURRENT_DATE(), INTERVAL 1 DAY)
  GROUP BY project_id, run_date
)
```

- 资源消耗继续使用 `dwi_project_nightly_resource_day`。
- 工程能力运营看板只展示到昨天，不展示今天。

---

## 7. 查询层改造

### 7.1 Nightly 看板

**`NightlyPipelineDashboardMapper.xml`**

| 原数据源                                               | 新数据源                                                                           |
| ------------------------------------------------------ | ---------------------------------------------------------------------------------- |
| `dm_rd_efc_project_pipeline_relation`                  | `dm_rd_efc_project_pipeline_relation`（`NIGHTLY`，旧 ID 为 OTHER，不需要额外排除） |
| `dwr_rd_efc_build_fact_nightly_test_case_pipeline_run` | `dm_rd_efc_nightly_pipeline_logical_run`                                           |
| `dm_rd_efc_build_dim_nightly_pipeline_day`             | `dm_rd_efc_nightly_pipeline_logical_day`                                           |
| `dm_rd_efc_build_dim_test_case_nightly_pipeline_day`   | `dm_rd_efc_nightly_pipeline_logical_day`（用例字段）                               |

改造点：

- `selected_pipelines` 从 relation `NIGHTLY` 取（旧 ID 为 OTHER，不需要额外排除）。
- 运行次数、成功率、分位数、构建/测试统计从逻辑运行表聚合。
- 版本可用度从日汇总宽表按逻辑流水线 + 日期去重。
- 最新用例从日汇总宽表按逻辑流水线取最新日期行。
- 输出 `pipeline_id` 使用 `logical_pipeline_id`。
- 率字段在 SQL 里用分子/分母计算。
- GitHub Nightly 保持原 raw workflow 分支，不进入逻辑运行表。

**`DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper.xml`**

- 明细、count 改为直接查 `dm_rd_efc_nightly_pipeline_logical_run`。
- 按 `logical_pipeline_id` 查询，返回实际 `pipeline_id` / `pipeline_run_id` 用于跳转。

### 7.2 Nightly 图表

**`PipelineHandleImpl.java`**

- `queryVersionPipeline` 改为从 relation `NIGHTLY` 取（旧 ID 为 OTHER，不需要额外排除）。
- `queryPipelineRunData` 改为从 `dm_rd_efc_nightly_pipeline_logical_day` 取。
- `queryVersionAvailabilityRate` 改为从日汇总宽表取。
- `queryTestCaseData` 改为从日汇总宽表用例字段取。

**相关 Mapper**

- `DmRdEfcBuildDimNightlyPipelineDayMapper.xml`
- `DmRdEfcBuildDimTestCaseNightlyPipelineDayMapper.xml`
- `DwiVersionPipelineInfoMapper.xml`

统一改为查 `dm_rd_efc_nightly_pipeline_logical_day`。

### 7.3 工程能力看板

**`OpsNightlyDetailMapper.xml`**

- 流水线集合：relation `NIGHTLY`（旧 ID 为 OTHER，不需要额外排除）。
- 编译成功率：`dm_rd_efc_nightly_pipeline_logical_run`。
- 版本可用度：`dm_rd_efc_nightly_pipeline_logical_day`。
- 明细、汇总、count 全部按 `logical_pipeline_id`。
- 率字段在 SQL 里计算。

**`OpsResourceDetailMapper.xml`**

- Nightly 明细、count、卡片汇总改为查 `dm_rd_efc_nightly_pipeline_logical_day` 的 `cpu_seconds/npu_seconds/memory_seconds`。
- 按 `logical_pipeline_id` 聚合，不再查 `dwr_rd_efc_pipeline_run_unified`。
- PR 分支不动。

**`OpsResourceRunMapper.xml`**

- 低 QPS 明细弹窗，仍查 `dwr_rd_efc_pipeline_run_unified`。
- 通过 alias 有效区间展开：
  ```sql
  JOIN dm_rd_efc_nightly_pipeline_alias a
    ON a.pipeline_id = u.pipeline_id
   AND a.platform = u.platform
   AND a.logical_pipeline_id = #{req.pipelineId}
   AND a.valid_from <= COALESCE(u.end_time, u.start_time)
   AND a.valid_to   >  COALESCE(u.end_time, u.start_time)
  UNION ALL
  SELECT ...
  FROM dwr_rd_efc_pipeline_run_unified u
  WHERE u.pipeline_id = #{req.pipelineId}
    AND NOT EXISTS (
      SELECT 1
      FROM dm_rd_efc_nightly_pipeline_alias x
      WHERE x.logical_pipeline_id = #{req.pipelineId}
    )
  ```
- 返回实际 `pipeline_id` 用于拼跳转 URL。

**`OpsMainStatMapper.xml`**

- `selected_pipelines` 改为 relation `NIGHTLY`（旧 ID 为 OTHER，不需要额外排除）。
- `pipeline_version_avail` 改为日汇总宽表。
- `resource_sum` 继续读 `dwi_project_resource_indicator_day`。

### 7.4 开源项目运营看板

**`DwiProjectStatisticsMapper.xml`**

- 用例最新数据、版本可用度改为查 `dm_rd_efc_nightly_pipeline_logical_day`。
- 流水线集合改为 relation `NIGHTLY`（旧 ID 为 OTHER，不需要额外排除）。

### 7.5 前端

预期不需要改前端：

- 接口 category、字段名、分页结构保持不变；
- 列表返回一条逻辑流水线；
- 明细返回实际 `pipeline_id`，跳转逻辑保持原样；
- 率字段由后端 SQL 计算后返回。

---

## 8. 调度设计

### 8.1 逻辑运行/日汇总

- 跟随流水线信息任务每小时全量刷新；
- 每次 `TRUNCATE` 后 `INSERT` 全量数据；
- 与现有 `dm_rd_efc_build_dim_nightly_pipeline_day` 的全量模式一致；
- 这样映射修改后下一次刷新自动生效，不需要单独回刷。

### 8.2 工程能力项目级预聚合

- 每天跑一次，现网约凌晨 3~4 点执行；
- 只汇总到昨天，不展示今天；
- 不需要和逻辑运行/日汇总任务固定错峰，允许比逻辑日汇总滞后。

### 8.3 映射维护

- 当前由开发手动维护；
- 每次切换完成后补充 alias；
- 后续规范统一后再考虑自动化生成。

---

## 9. 接口性能设计

1. **列表、图表、汇总**
   - 查 relation + 日汇总宽表，小表查询，不再 join 大事实表。
2. **Nightly 明细**
   - 分位数、最长时长基于运行级数据，查 `dm_rd_efc_nightly_pipeline_logical_run`；
   - 按逻辑流水线 + `run_date` 范围过滤。
3. **工程能力资源环境**
   - 直接查日汇总宽表资源字段，不再扫全量运行统一表。
4. **资源运行弹窗**
   - 低 QPS，允许查运行统一表，通过 alias 区间和日期范围过滤。
5. **表设计**
   - 两张表都不做分区，数据量小，暂不自动清理；
   - 唯一键保证重跑幂等；
   - bucket 数按实际数据量调整。
6. **接口基线**
   - 上线前对比改造前后主要接口 P95；
   - 逻辑日汇总类接口应优于改造前。

---

## 10. 查询简化收益

### 10.1 当前 Mapper 复杂度

| Mapper                                                  | 当前行数 | join 数 | CTE 数 |
| ------------------------------------------------------- | -------: | ------: | -----: |
| `NightlyPipelineDashboardMapper.xml`                    |      653 |      11 |      5 |
| `DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper.xml` |      438 |       7 |      0 |
| `OpsNightlyDetailMapper.xml`                            |      385 |      21 |      9 |
| `OpsResourceDetailMapper.xml`                           |      607 |      24 |     15 |
| `OpsMainStatMapper.xml`                                 |      578 |      34 |     16 |
| `DwiProjectStatisticsMapper.xml`                        |      294 |      13 |      5 |
| `DmRdEfcBuildDimNightlyPipelineDayMapper.xml`           |      144 |       5 |      0 |
| `DmRdEfcBuildDimTestCaseNightlyPipelineDayMapper.xml`   |       61 |       1 |      0 |

### 10.2 实际实现结果（2026-10-28）

| 文件                                                    | 改造后行数 | 增减 |
| ------------------------------------------------------- | ---------: | ---: |
| `NightlyPipelineDashboardMapper.xml`                    |        664 |   +5 |
| `DwrRdEfcBuildFactNightlyTestCasePipelineRunMapper.xml` |        444 |   +6 |
| `OpsNightlyDetailMapper.xml`                            |        240 | -145 |
| `OpsResourceDetailMapper.xml`                           |        558 |  -49 |
| `OpsMainStatMapper.xml`                                 |        578 |    0 |
| `DwiProjectStatisticsMapper.xml`                        |        299 |   +5 |
| `DmRdEfcBuildDimNightlyPipelineDayMapper.xml`           |        149 |   +5 |
| `DmRdEfcBuildDimTestCaseNightlyPipelineDayMapper.xml`   |         65 |   +4 |
| `DwiVersionPipelineInfoMapper.xml`                      |        445 |  -48 |
| `OpsResourceRunMapper.xml`                              |         79 |  +20 |

实际结论：

- 行数下降主要来自 `OpsNightlyDetailMapper`（抽公共 `<sql>` 片段）和 `OpsResourceDetailMapper`（不再扫运行统一表）。
- 其他 Mapper 主要是“换表 + 补别名映射 + 率字段现算”，行数基本持平或略增。
- 真正的收益是不再扫描大事实表，而不是 Mapper 行数普遍下降。
- 原 10.1/10.2 的预估偏乐观，以本节实际结果为准。

### 10.3 结论

- alias 只维护切换过的逻辑流水线，数据很少；
- 逻辑流水线清单复用 relation，不需要 dim 表；
- 逻辑运行表、日汇总宽表全量刷新，不需要增量/回刷状态；
- 3 张表、3 个 ETL 步骤，比 6 张表方案更简单；
- 查询层性能收益集中在工程能力 Nightly 明细和资源环境，代码行数不一定下降。

---

## 11. 验证方案

1. **映射区间校验**
   - `valid_to` 是否等于下一行 `valid_from`；
   - 最后一行 `valid_to` 是否为 `9999-12-31`；
   - 每个实际 `pipeline_id` 是否只出现一次。

2. **逻辑运行完整性**
   - 旧流水线 `valid_to` 之前的运行全部进入逻辑运行表；
   - 新流水线 `valid_from` 之前的调试运行不在逻辑运行表；
   - 中间代流水线按各自区间保留。

3. **未切换流水线不受影响**
   - 改造前后执行次数、成功率、时长分位数一致。

4. **日汇总与运行一致**
   - 日汇总 `run_count` 等于逻辑运行表按逻辑流水线 + 日期计数；
   - 版本可用度按逻辑流水线 + 日期去重后一致。

5. **汇总与明细一致**
   - Nightly 看板列表执行次数与明细列表总数一致；
   - 工程能力 Nightly 明细与卡片汇总一致。

6. **下钻链接**
   - 旧运行打开旧流水线实际运行；
   - 新运行打开新流水线实际运行。

7. **接口性能**
   - 对比改造前后 P95；
   - 工程能力资源环境 Nightly 应有明显下降。

---

## 12. 方案自查

### 12.1 仍然存在的风险

| 风险                                     | 说明                                                                                                  | 处理                                                                                               |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- |
| alias 手动维护错误                       | 区间或逻辑名称写错会导致数据多算、漏算或展示名称错误                                                  | 上线前用区间校验 SQL 和名称核对；后续自动化                                                        |
| pipeline_id 可能对应多个 openlibing 项目 | 一个 `pipeline_project` 可能对应多个 `project_id`，按 `pipeline_id` 单独关联 alias 会放大运行数       | ETL 先从 relation 取 `(project_id, pipeline_project, platform, pipeline_id)`，再按这四列关联 alias |
| pipeline_id 跨平台重复                   | 事实表本身没有 platform，通过 relation 按 `pipeline_id` 取平台                                        | 已改为 relation 绑定平台；relation 中不存在的流水线需人工确认                                      |
| 旧流水线历史依赖事实表保留               | 事实表只重新写入当前 `NIGHTLY` 判定命中的运行，不清理历史；旧流水线改名为 `old_` 后历史行必须继续保留 | 依赖事实表保留历史；上线前确认任务没有 `TRUNCATE`/删除历史，否则逻辑运行表无法回溯旧数据           |
| 全量刷新成本                             | 逻辑运行表数据量大，每小时全量可能较重                                                                | 先按现网全量模式跑，观察任务耗时；后续可优化                                                       |
| 图表流水线列表来源变化                   | 从 `sdi_version_pipeline_base_info` 改为 relation                                                     | 上线前对比两个集合                                                                                 |
| 运行数与资源运行数不一致                 | 两个来源不同                                                                                          | 接口验收时明确口径                                                                                 |
| 时间边界                                 | 切换时间点按半开区间归新流水线                                                                        | 与业务确认                                                                                         |

### 12.2 已解决/已确认

- alias 增加 `platform`；
- alias 主键增加 `pipeline_project`；
- alias 增加 `logical_pipeline_name`，存当前新流水线名称；
- alias 存逻辑流水线下所有实际流水线，支持多次改名；
- 三张新表去掉 `update_time`；
- relation 识别默认正确，不额外兜底；
- 映射手动维护，后续自动化；
- 逻辑运行表/日汇总全量刷新，不做增量；
- 流水线信息每小时跑，工程能力每天凌晨 3~4 点跑昨天；
- 两张表都不做分区，数据量小，暂不自动清理；
- 切换时间点按半开区间归新流水线已确认；
- 全量刷新先上线观察耗时，跑太慢再优化；
- 宽表只存分子分母，率在查询时计算；
- 全量刷新不会因为映射变更产生回刷问题。

---

## 13. 实施顺序

1. DBA 创建 3 张表。
2. 开发/运营按切换情况维护 alias。
3. 新增逻辑运行表全量刷新任务。
4. 新增逻辑日汇总宽表全量刷新任务。
5. 改造工程能力项目级预聚合任务。
6. 改造 Nightly 看板 Mapper。
7. 改造工程能力 Mapper。
8. 改造开源项目运营看板 Mapper。
9. 改造图表查询。
10. 接口压测和数据一致性验证。

---

## 14. 已确认问题

| 问题                               | 结论                                                        |
| ---------------------------------- | ----------------------------------------------------------- |
| 逻辑运行表是否保留 730 天          | 不保留，表不做分区、不自动清理；现在数据少，先不删          |
| alias 区间由谁维护                 | 当前由开发维护，后续再自动化                                |
| 工程能力项目级预聚合几点跑         | 不需要固定错峰时间，它只跑昨天的数据，现网约凌晨 3~4 点执行 |
| 切换时间点按半开区间归新流水线     | 可以接受                                                    |
| 逻辑运行表每小时全量刷新是否可接受 | 先上线任务，跑太慢再优化；现有任务都是全量跑，耗时可控      |
