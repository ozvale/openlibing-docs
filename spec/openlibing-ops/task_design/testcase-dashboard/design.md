# 测试用例看板 后端设计文档

> 目标仓：`openlibing-ops`（后端）
> 数据底座：Doris，分层 `dwi(明细) → dwr(事实宽表) → dm(汇总/维度)`，ETL 由 DolphinScheduler/SeaTunnel 调度

本文件为测试用例看板的单一权威技术方案，覆盖需求、口径、数据模型、ETL 脚本、接口设计、SQL 与代码文件清单，所有内容均内联，无需查阅其他文件。

---

## 1. 需求概述

构建「测试用例看板」，以 **社区/组织（product）→ 项目（project）→ 用例路径目录树（仓库→分支→目录→文件）→ 用例详情** 的层级，展示测试用例执行质量：

- 总览 KPI：测试用例总数、通过用例数、失败用例数、执行率、通过率。
- 趋势：通过率/执行率趋势（整体、各社区各一张图，双指标，均跟随树节点定位）。
- 分布：各社区测试用例分布（通过/失败/未执行三状态拆分）、用例状态分布环形图。
- 列表：项目结构树（懒加载）、文件下用例列表、用例执行明细、社区/项目列表。

数据来源为流水线用例执行结果明细表 `dwi_rd_efc_test_case_result`，复用现有项目/社区维度 `dm_rd_efc_project_pipeline_relation` 完成上卷。

### 1.1 高保真页面功能拆解

| 页面区域 | 功能 | 数据诉求 | 接口 |
| --- | --- | --- | --- |
| 社区/组织总览 | KPI 卡片 | 社区级去重用例数、通过/失败数、执行率、通过率 | `POST /common/card` |
| 通过率/执行率趋势 | 折线图（整体 + 分社区，双指标） | 按天粒度：通过 / 已执行 / 总次数 | `POST /common/chart` |
| 各社区测试用例分布 | 堆叠柱图 | 各社区按最新结果拆分：通过 / 失败 / 未执行 | `POST /common/chart` |
| 用例状态分布 | 环形图 | 全量用例按最新结果：通过 / 失败 / 未执行 | `POST /common/chart` |
| 社区/组织列表 | 分页表格 | 每个项目 总用例、通过、失败、执行率、通过率（按项目分页，含所属社区信息） | `POST /common/detail` |
| 项目结构树 | 树形导航（懒加载） | `product→project→repo→branch→dir→file` 逐层展开 | `POST /testcase/path/tree` |
| 子节点列表 | 表格（点击名称跳转节点详情） | 选中节点的直接子节点：名称、类型、总用例、通过、失败、执行率、通过率 | `POST /common/detail` |
| 文件下用例列表 | 分页表格 | 文件下用例执行次数、通过/失败、P50/P90 耗时、平均 NPU 消耗 | `POST /common/detail` |
| 用例执行明细 | 分页表格 | 单次执行的任务/起止时间/结果/时长/NPU 消耗 | `POST /common/detail` |

时间筛选：今日 / 近 7 / 30 / 90 天 / 自定义，按 `end_time` 过滤。

---

## 2. 现状盘点与项目信息复用

复用现有资产，不新建项目/社区维度：

| 表 | 说明 | 复用点 |
| --- | --- | --- |
| `dwi_rd_efc_test_case_result` | 用例执行结果明细（源） | 唯一事实来源：`result` 1成功/0失败/2跳过/3未执行，`level` 0:P0/1:P1/2:P2/3:P3，`type` 测试类型（上游新增透传） |
| `dm_rd_efc_project_pipeline_relation` | 组织×项目×平台×流水线映射 | 已冗余 `product_name/product_id/project_name/project_id/pipeline_name/pipeline_type`，`pipeline_id → 项目/社区` |
| `dwi_rd_efc_pipeline_run_step` | 流水线 step 明细 | `testcase_job_id → job_id`，关联资源事实表的中转 |
| `dwr_rd_efc_pipeline_run_job_fact` | Job 执行事实 | `job_id/job_name/npu_second`（NPU 卡·秒） |

平台→项目映射主路径：`pipeline_id → dm_rd_efc_project_pipeline_relation`，已含 `platform`（codearts/gitcode/github）。

「社区」= `product_name`；「项目」= `project_name`。关系表已把两级名称冗余好，接口查询零 JOIN。

---

## 3. 口径定义

| 项 | 口径 |
| --- | --- |
| 用例唯一键 `case_key` | `MD5(repo_url\|repo_branch\|case_file_path\|case_file_name\|class_name\|case_number)`。用原始 `case_file_path+case_file_name`（非归一后的 `full_file_path`）；**含分支**（跨分支视为不同用例）；**不含项目/社区**，隔离由 UNIQUE KEY 前置 `product_id+project_id` 实现 |
| 总用例数（去重） | `COUNT(DISTINCT case_key)` |
| 通过/失败/跳过（卡片 / 社区项目列表 / 社区分布 / 状态分布） | **每用例最新结果口径**：窗口内每 `case_key` 取 `end_time` 最新一条，按该条 `result` 计数 |
| 通过/失败/跳过（文件列表 / 趋势） | 次数口径 `COUNT(IF(result=?,1,NULL))` |
| 未执行（分布类图表） | 最新结果口径下 `未执行 = 跳过(result=2) + 未执行(result=3)`，与通过/失败并列三态 |
| 状态枚举 | `1成功 / 0失败 / 2跳过 / 3未执行` |
| 优先级 | `level`：`0:P0 / 1:P1 / 2:P2 / 3:P3` |
| 测试类型 | `type`：功能/性能/可靠性/兼容性/精度 |
| 执行时长 | 单次 `time`(秒)；文件列表 P50/P90 用 `PERCENTILE(time, 0.5/0.9)` 查询期计算，不物化 |
| 通过率/执行率 | `执行率=已执行/总数`；`通过率=通过/已执行`；`已执行=通过+失败+跳过`（分母为 0 时返回 0） |
| 时间窗口 | 按 `end_time∈[startTime, endTime]`（UTC，界面 +8h 补偿）过滤 |
| NPU 资源 | **仅消耗量** `npu_second/3600`(卡时)，取自 `dwr_rd_efc_pipeline_run_job_fact`；不采集 vCPU |
| 组织名 | 统一 `product_name`（fact / tree_node 两表一致） |

要点：

- **不建最新结果快照表**：卡片与社区项目列表的「通过/失败」为窗口内每用例最新结果，该值随窗口变化，查询期 `ROW_NUMBER() OVER(PARTITION BY case_key ORDER BY end_time DESC)` 取 `rn=1`，不物化。
- **目录树是纯结构**：树节点表只存结构（类型/层级/路径/名称），不含计数与时间。计数与明细由前端拿到树结构后，另行调用卡片/图表/详情接口按定位字段 + 时间窗口聚合。
- **趋势是次数口径**：每日 `通过次数 / 已执行次数`，查询期从 fact 按 `DATE_FORMAT(end_time,'%Y-%m-%d')` 分组聚合。

---

## 4. 数据模型

### 4.1 分层与表清单

```text
dwi_rd_efc_test_case_result (源明细，本次新增 type 列透传)
   │ ETL-1  JOIN dm_rd_efc_project_pipeline_relation（组织/项目/流水线名称与类型）
   │        JOIN dwi_rd_efc_pipeline_run_step + dwr_rd_efc_pipeline_run_job_fact（job_id/job_name/npu_second）
   │        计算 case_key / full_file_path
   ▼
dwr_rd_efc_test_case_fact (事实宽表，一执行一行) ← 卡片/列表/趋势/分布/明细 唯一数据源
   └─ ETL-3 → dm_rd_efc_test_case_tree_node (目录树结构，不含计数/时间)
```

| 层 | 表名 | 粒度 | 用途 | 增/复用 |
| --- | --- | --- | --- | --- |
| DWI | `dwi_rd_efc_test_case_result` | 一次执行 | 源明细 | 复用（上游补 `type` 列） |
| DM | `dm_rd_efc_project_pipeline_relation` | 组织×项目×平台×流水线 | 项目/流水线映射 | 复用维度 |
| DWR | `dwr_rd_efc_test_case_fact` | 一次执行 | 事实宽表，下游唯一数据源 | **新增** |
| DM | `dm_rd_efc_test_case_tree_node` | 节点 | 详情页树结构 | **新增** |

### 4.2 源明细表 `dwi_rd_efc_test_case_result`（上游提供，本次仅新增 `type` 列透传）

```sql
CREATE TABLE `dwi_rd_efc_test_case_result` (
  `repo_url` varchar(500) NULL COMMENT '代码仓库地址',
  `repo_branch` varchar(100) NULL COMMENT '代码仓库分支',
  `case_file_path` varchar(2048) NULL COMMENT '用例代码路径',
  `case_file_name` varchar(255) NULL COMMENT '用例文件名称',
  `class_name` varchar(500) NULL COMMENT '用例所属类名',
  `case_number` varchar(100) NULL COMMENT '测试用例编号',
  `origin` tinyint NULL DEFAULT "0" COMMENT '数据来源 0:codearts;1:gitcode;2:github',
  `pipeline_id` varchar(32) NULL COMMENT '流水线ID（数据来源标识）',
  `pipeline_run_id` varchar(32) NULL COMMENT '流水线执行记录ID',
  `testcase_job_id` varchar(64) NULL COMMENT '真实任务ID（未执行任务可能为空）',
  `level` varchar(8) NULL COMMENT '用例级别，0:P0;1:P1;2:P2;3:P3',
  `type` varchar(32) NULL COMMENT '测试类型：功能测试/性能测试/可靠性测试/兼容性测试/精度测试（上游新增透传）',
  `result` int NULL COMMENT '用例结果：1:成功/0:失败/3:未执行/2:skip（跳过）',
  `start_time` datetime NULL COMMENT '用例开始执行时间（UTC时间）',
  `end_time` datetime NULL COMMENT '用例结束执行时间（UTC时间）',
  `time` int NULL COMMENT '用例执行耗时（单位：秒）',
  `failure_message` varchar(2048) NULL COMMENT '断言失败原因',
  `failure_type` varchar(255) NULL COMMENT '失败异常类型（如：AssertionError）',
  `error_message` varchar(2048) NULL COMMENT '代码运行时异常'
) ENGINE=OLAP
UNIQUE KEY(`repo_url`, `repo_branch`, `case_file_path`, `case_file_name`, `class_name`, `case_number`, `origin`, `pipeline_id`, `pipeline_run_id`, `testcase_job_id`)
COMMENT '流水线用例执行结果表'
DISTRIBUTED BY HASH(`repo_url`) BUCKETS 10
PROPERTIES (
"replication_allocation" = "tag.location.default: 2",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true"
);
```

### 4.3 项目-流水线关系表 `dm_rd_efc_project_pipeline_relation`（复用维度）

```sql
CREATE TABLE `dm_rd_efc_project_pipeline_relation` (
  `product_id` int NOT NULL COMMENT 'openlibing组织id',
  `project_id` int NOT NULL COMMENT 'openlibing项目id',
  `platform` varchar(8) not null comment '平台（codearts/gitcode/github）',
  `pipeline_project` varchar(512) NOT NULL COMMENT '流水线所属项目',
  `pipeline_id` varchar(64) NOT NULL COMMENT '流水线/workflow ID',
  `product_name` varchar(512) not null comment '组织名',
  `project_name` varchar(512) not null comment '项目名',
  `pipeline_name` varchar(512) not null comment '流水线名称',
  `pipeline_type` varchar(32) not null comment '流水线类型'
) ENGINE=OLAP
UNIQUE KEY(`product_id`,`project_id`, `platform`, `pipeline_project`, `pipeline_id`)
DISTRIBUTED BY HASH(`platform`, `pipeline_project`) BUCKETS 10
PROPERTIES (
"replication_allocation" = "tag.location.default: 2",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true"
);
```

该表由上游维度表清洗而来，本需求仅消费不维护：

```sql
insert into dm_rd_efc_project_pipeline_relation
select distinct
    pd.product_id, pj.project_id, 'codearts',
    r.project_id as pipeline_project, r.pipeline_id,
    pd.product_name, pj.project_name, r.pipeline_name,
    case
        when LOWER(r.pipeline_name) like 'pr%' then 'PR'
        when LOWER(r.pipeline_name) like 'nightly%' then 'NIGHTLY'
        else 'OTHER'
    END AS pipeline_type
from sdi_rd_efc_pipeline_run_clean_codearts r
join sdi_hw_project_info hp on hp.hw_project_id = r.project_id
join sdi_project_info pj on pj.project_id = hp.project_id
join sdi_product_info pd on pj.product_id = pd.product_id;
```

### 4.4 事实宽表 `dwr_rd_efc_test_case_fact`（新增）

```sql
CREATE TABLE `dwr_rd_efc_test_case_fact` (
    `product_id`        int           NULL COMMENT '社区(产品)id',
    `project_id`        int           NULL COMMENT 'openlibing项目id',
    `case_key`          varchar(64)   NULL COMMENT '用例唯一键 MD5(repo_url|repo_branch|case_file_path|case_file_name|class_name|case_number)',
    `pipeline_id`       varchar(128)  NULL COMMENT '流水线ID',
    `pipeline_run_id`   varchar(128)  NULL COMMENT '流水线执行记录ID',
    `job_id`            varchar(128)  NULL COMMENT '执行用例任务id（未执行为空串）',
    `repo_url`          varchar(512)  NULL COMMENT '代码仓库地址',
    `repo_branch`       varchar(100)  NULL COMMENT '代码仓库分支',
    `case_file_path`    varchar(2048) NULL COMMENT '用例代码路径',
    `case_file_name`    varchar(255)  NULL COMMENT '用例文件名称',
    `class_name`        varchar(500)  NULL COMMENT '用例所属类名',
    `case_number`       varchar(100)  NULL COMMENT '测试用例编号',
    `full_file_path`    varchar(2048) NULL COMMENT '完整文件路径=case_file_path(+"/"+case_file_name 若未含)',
    `project_name`      varchar(128)  NULL COMMENT '项目名',
    `product_name`      varchar(128)  NULL COMMENT '社区/组织名称',
    `repo_name`         varchar(128)  NULL COMMENT '仓库名(提取)',
    `pipeline_name`     varchar(512)  NULL COMMENT '流水线名称',
    `pipeline_type`     varchar(32)   NULL COMMENT '流水线类型',
    `job_name`          varchar(512)  NULL COMMENT '任务名(执行明细「任务」列)',
    `level`             varchar(8)    NULL COMMENT '用例优先级 0:P0;1:P1;2:P2;3:P3',
    `type`              varchar(32)   NULL COMMENT '测试类型：功能测试/性能测试/可靠性测试/兼容性测试/精度测试',
    `result`            int           NULL COMMENT '1成功/0失败/3未执行/2skip',
    `start_time`        datetime      NULL COMMENT '开始时间',
    `end_time`          datetime      NULL COMMENT '结束时间',
    `time`              int           NULL COMMENT '耗时(秒)',
    `failure_message`   varchar(2048) NULL COMMENT '断言失败原因',
    `failure_type`      varchar(255)  NULL COMMENT '失败异常类型',
    `error_message`     varchar(2048) NULL COMMENT '运行时异常',
    `npu_second`        double        NULL COMMENT 'NPU消耗量(卡·秒)'
) ENGINE=OLAP
UNIQUE KEY(`product_id`,`project_id`,`case_key`,`pipeline_id`, `pipeline_run_id`, `job_id`)
COMMENT '测试用例执行事实宽表(DWR)'
DISTRIBUTED BY HASH(`case_key`) BUCKETS 10
PROPERTIES (
"replication_allocation" = "tag.location.default: 2",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true"
);
```

- 仅 NPU 资源列 `npu_second`，不采集 vCPU。
- `case_key` 为分布键，`product_id+project_id` 前置实现跨项目/社区隔离。
- 不落 `stat_date`，趋势/分区按 `DATE(end_time)` 派生。
- `full_file_path` 与树节点表 `node_path` 严格一致，作目录树下钻 key。

### 4.5 树节点结构表 `dm_rd_efc_test_case_tree_node`（新增）

纯结构表，**不含计数与时间**：

```sql
CREATE TABLE `dm_rd_efc_test_case_tree_node` (
  `node_key`      varchar(32)   NULL COMMENT '根据其他主键生成的md值',
  `node_type`     varchar(16)   NULL COMMENT 'product/project/repo/branch/dir/file',
  `product_id`    int           NULL COMMENT '社区(产品)id',
  `project_id`    int           NULL COMMENT 'openlibing项目id(product层为0)',
  `repo_url`      varchar(500)  NULL COMMENT '仓库地址(product/project以上为空串)',
  `repo_branch`   varchar(100)  NULL COMMENT '分支(branch及以下非空;product/project/repo为空串)',
  `node_path`     varchar(2048) NULL COMMENT '路径前缀(含完整文件名;product/project/repo/branch为空串)',
  `node_level`    int           NULL COMMENT 'product=0,project=1,repo=2,branch=3,dir/file从4起递增',
  `product_name`  varchar(255)  NULL COMMENT '社区/组织名称',
  `project_name`  varchar(255)  NULL COMMENT '项目名称',
  `repo_name`     varchar(255)  NULL COMMENT '仓库名'
) ENGINE=OLAP
UNIQUE KEY(`node_key`, `node_type`, `product_id`, `project_id`, `repo_url`, `repo_branch`, `node_path`)
COMMENT '测试用例目录树节点结构(DM,含社区/项目/仓库/分支/目录/文件,不含计数)'
DISTRIBUTED BY HASH(`repo_url`) BUCKETS 8
PROPERTIES (
"replication_allocation" = "tag.location.default: 2",
"storage_format" = "V2",
"enable_unique_key_merge_on_write" = "true",
"light_schema_change" = "true"
);
```

**节点语义**：

| node_type | 含义 | node_path | node_level |
| --- | --- | --- | --- |
| product | 社区/组织（顶层） | `''` | 0 |
| project | 项目 | `''` | 1 |
| repo | 代码仓 | `''` | 2 |
| branch | 分支 | `''` | 3 |
| dir | 目录 | `tests/unit` | ≥4 递增 |
| file | 文件（叶子） | `tests/unit/test.py` | ≥4 递增 |

- `node_key = MD5(node_type|product_id|project_id|repo_url|repo_branch|node_path)`，UNIQUE KEY 首列，懒加载时父节点等值定位用。
- `file` 节点 `node_path` 与 `fact.full_file_path` 严格一致，作下钻 key。
- 展开子节点：请求只传父节点 `nodeKey`，服务端两段式查询（nodeKey 定位父行 → `node_level = 父level+1` 逐级补齐定位条件），一次一级。
- `node_name` 不落库，前端按 `node_type` 从 `product_name/project_name/repo_name/node_path` 末段取展示名。

---

## 5. ETL 清洗脚本

### 5.1 ETL-1  dwi → dwr 事实宽表

`job_id/job_name/npu_second` 来自 `dwr_rd_efc_pipeline_run_job_fact`（经 `dwi_rd_efc_pipeline_run_step` 由 `testcase_job_id → job_id` 映射）：

```sql
insert into dwr_rd_efc_test_case_fact
WITH base AS (
    SELECT
        r.project_id, r.product_id, r.project_name, r.product_name,
        r.pipeline_name, r.pipeline_type,
        t.repo_url, t.repo_branch, t.case_file_path, t.case_file_name,
        t.class_name, t.case_number, t.pipeline_id, t.pipeline_run_id,
        t.level, t.type, t.result, t.start_time, t.end_time, t.time,
        t.failure_message, t.failure_type, t.error_message,
        COALESCE(f.job_id, '')           AS job_id,
        f.job_name                       AS job_name,
        CAST(f.npu_second AS DOUBLE)     AS npu_second,
        CASE
            WHEN t.case_file_name IS NULL OR t.case_file_name = '' THEN REPLACE(t.case_file_path, '\\', '/')
            WHEN t.case_file_path LIKE CONCAT('%/', t.case_file_name) OR t.case_file_path = t.case_file_name
                 THEN REPLACE(t.case_file_path, '\\', '/')
            ELSE CONCAT(REPLACE(t.case_file_path, '\\', '/'), '/', t.case_file_name)
        END AS full_file_path
    FROM dwi_rd_efc_test_case_result t
    JOIN dm_rd_efc_project_pipeline_relation r
          ON t.pipeline_id = r.pipeline_id
    LEFT JOIN dwi_rd_efc_pipeline_run_step j
          ON t.testcase_job_id = j.testcase_job_id
    LEFT JOIN dwr_rd_efc_pipeline_run_job_fact f
          ON j.job_id = f.job_id
)
SELECT
    product_id, project_id,
    MD5(CONCAT_WS('|', repo_url, repo_branch, case_file_path, case_file_name, class_name, case_number)) AS case_key,
    pipeline_id, pipeline_run_id, job_id,
    repo_url, repo_branch, case_file_path, case_file_name, class_name, case_number, full_file_path,
    project_name, product_name,
    SUBSTRING_INDEX(REPLACE(repo_url, '.git', ''), '/', -1) AS repo_name,
    pipeline_name, pipeline_type, job_name, level, type, result,
    start_time, end_time, time, failure_message, failure_type, error_message, npu_second
FROM base;
```

### 5.2 ETL-3  目录树节点清洗

从事实表去重「文件」集合，逐文件展开祖先链（`product→project→repo→branch→dir…file`），落库由 UNIQUE KEY 自动去重：

```sql
insert into dm_rd_efc_test_case_tree_node
WITH testcase AS (
    SELECT DISTINCT product_id, product_name, project_id, project_name,
                    repo_url, repo_branch, repo_name, full_file_path
    FROM dwr_rd_efc_test_case_fact
    WHERE repo_url IS NOT NULL AND repo_url <> ''
      AND full_file_path IS NOT NULL AND full_file_path <> ''
),
path_data AS (
    SELECT product_id, product_name, project_id, project_name,
           repo_url, repo_branch, repo_name,
           split_by_string(full_file_path, '/') AS segs
    FROM testcase
),
node AS (
    SELECT 'product' AS node_type, product_id, 0 AS project_id, '' AS repo_url, '' AS repo_branch, '' AS node_path, 0 AS node_level, product_name, '' AS project_name, '' AS repo_name
    FROM testcase
    UNION ALL
    SELECT 'project', product_id, project_id, '', '', '', 1, product_name, project_name, ''
    FROM testcase
    UNION ALL
    SELECT 'repo', product_id, project_id, repo_url, '', '', 2, product_name, project_name, repo_name
    FROM testcase
    UNION ALL
    SELECT 'branch', product_id, project_id, repo_url, repo_branch, '', 3, product_name, project_name, repo_name
    FROM testcase
    UNION ALL
    SELECT
        CASE WHEN pos = array_size(segs) - 1 THEN 'file' ELSE 'dir' END AS node_type,
        product_id, project_id, repo_url, repo_branch,
        array_join(array_slice(segs, 1, pos + 1), '/') AS node_path,
        pos + 4                                        AS node_level,
        product_name, project_name, repo_name
    FROM path_data
    LATERAL VIEW explode(array_range(0, array_size(segs))) pe AS pos
)
SELECT MD5(CONCAT_WS('|', node_type, CAST(product_id AS CHAR), CAST(project_id AS CHAR),
                     repo_url, repo_branch, node_path)) AS node_key,
       node_type, product_id, project_id, repo_url, repo_branch, node_path, node_level,
       product_name, project_name, repo_name
FROM node;
```

> Dwarf/dir 的 `node_path` 用 Doris `split_by_string + array_slice + array_join` 逐级切出前缀；`node_level = pos + 4`。

---

## 6. 接口设计

### 6.1 复用与抽象总览

openlibing-ops 已有一套「归一化端点 + 工厂 + 多态请求体」模式，本需求复用该模式：

- **分页详情类**（文件下用例列表、用例执行明细、社区/项目列表）：复用 `POST /common/detail`，通过 `category` 多态路由到不同 `DetailService`。
- **卡片类**（总览 KPI）：新增归一化端点 `POST /common/card`。
- **趋势/分布类**（通过率趋势、社区分布）：新增归一化端点 `POST /common/chart`（一次一张图）。
- **目录树**（父节点定位 → 返回直接子节点，非分页导航）：独立接口 `POST /testcase/path/tree`，不复用分页详情接口。

整体路由机制统一为「`category` 多态反序列化 + 工厂枚举路由」：

- `DetailReq` / `CardReq` / `ChartReq` 均通过 `@JsonTypeInfo(use = NAME, property = "category")` + `@JsonSubTypes` 反序列化到具体子类。
- 工厂（`RepoDetailFactory` / `CardHandleFactory` / `ChartHandleFactory`）按 `category` 对应的枚举从 `Map<Enum, Service<?>>` 取处理器。

统一响应包装 `Result<T>`：

```java
public class Result<T> {
  private final int code;           // 200 成功
  private final String messageCn;   // 中文消息
  private final String messageEn;   // 英文消息
  private T data;                   // 响应数据
}
```

分页包装 `PageResult<R>`：`records`（数据列表）、`total`（总记录数）、`pageSize`（每页大小）、`page`（当前页）。

### 6.2 通用卡片 `POST /common/card`

**请求基类**（继承 `TimeReq`，仅保留 `category`）：

```java
@JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "category", defaultImpl = CardReq.class, visible = true)
@JsonSubTypes({ @JsonSubTypes.Type(value = TestCaseOverviewCardReq.class, name = "testcase-overview") })
public class CardReq extends TimeReq {
  private String category;
}
```

**本需求卡片请求子类**（携带子路径定位字段）：

```java
public class TestCaseOverviewCardReq extends CardReq {
  private Integer productId;   // 社区（可选，null=全量）
  private Integer projectId;   // 项目（可选，null=全量）
  private String  repoUrl;     // 仓库（可选）
  private String  repoBranch;  // 分支（可选）
  private String  nodePath;    // 节点路径（dir/file 层有效）
  private String  nodeType;    // file=等值匹配，dir 等=前缀匹配
}
```

**响应**（一组指标卡）：

```java
public class CardResp { private List<CardItem> cards; }

public class CardItem {
  private String       metric;      // 稳定指标标识，如 total_cases / pass_rate
  private String       name;        // 展示名
  private Object       value;       // 当前值（Double / String / Integer）
  private String       unit;        // 单位：个 / %
  private Integer      precision;   // 保留小数位
  private Double       delta;       // 变化量（可选，本需求暂未使用）
  private Double       deltaRate;   // 变化率（可选）
  private String       tendency;    // up / down / flat（可选）
  private List<Double> sparkline;   // 迷你趋势点（可选）
}
```

**服务与工厂**：

```java
public interface CardService<T extends CardReq> {
  CardCommonEnum type();
  List<CardItem> queryCards(T req);
}
```

### 6.3 通用趋势图 `POST /common/chart`

**一次请求只返回一张图**，各图独立请求、互不影响。

**请求基类**（继承 `TimeReq`，仅保留 `category`）：

```java
@JsonTypeInfo(use = JsonTypeInfo.Id.NAME, property = "category", defaultImpl = ChartReq.class, visible = true)
@JsonSubTypes({
  @JsonSubTypes.Type(value = TestCasePassRateTrendReq.class, name = "testcase-pass-rate-trend"),
  @JsonSubTypes.Type(value = TestCaseCommunityPassRateTrendReq.class, name = "testcase-community-pass-rate-trend"),
  @JsonSubTypes.Type(value = TestCaseCommunityDistributionReq.class, name = "testcase-community-distribution"),
  @JsonSubTypes.Type(value = TestCaseStatusDistributionReq.class, name = "testcase-status-distribution"),
})
public class ChartReq extends TimeReq {
  private String category;
}
```

**本需求趋势请求子类**（携带子路径定位字段，与卡片子类一致；整体趋势 / 各社区趋势 / 各社区分布 / 状态分布四个子类字段相同，仅 `category` 不同）：

```java
public class TestCasePassRateTrendReq extends ChartReq {
  private Integer productId;
  private Integer projectId;
  private String  repoUrl;
  private String  repoBranch;
  private String  nodePath;
  private String  nodeType;
}

public class TestCaseCommunityPassRateTrendReq extends ChartReq {
  private Integer productId;
  private Integer projectId;
  private String  repoUrl;
  private String  repoBranch;
  private String  nodePath;
  private String  nodeType;
}

public class TestCaseCommunityDistributionReq extends ChartReq {
  private Integer productId;
  private Integer projectId;
  private String  repoUrl;
  private String  repoBranch;
  private String  nodePath;
  private String  nodeType;
}

public class TestCaseStatusDistributionReq extends ChartReq {
  private Integer productId;
  private Integer projectId;
  private String  repoUrl;
  private String  repoBranch;
  private String  nodePath;
  private String  nodeType;
}
```

**响应（单张图）**：

```java
public class ChartResp {
  private String       title;       // 图表标题
  private List<String> xAxis;       // 横轴（日期/分类/扇区名）
  private List<Series> series;
}
// 图类型（line/bar/donut）与数值格式（percent/number）由前端按 category 自行控制，后端不返回

public class Series {
  private String       name;
  private List<Object> data;        // 与 xAxis 对齐，缺失补 0；趋势图为 RatePoint 对象
  private String       color;       // 可选
}

// 趋势图数据点：单点同时携带两个比率
public class RatePoint {
  private double passRate;  // 通过率（0-100）
  private double execRate;  // 执行率（0-100）
}
```

**服务与工厂**：

```java
public interface ChartService<T extends ChartReq> {
  ChartCommonEnum type();
  ChartResp       queryChart(T req);   // 返回单张图
}
```

### 6.4 目录树懒加载 `POST /testcase/path/tree`

独立接口，**仅返回树结构（不含计数与时间）**。右侧卡片/图表/列表数据由前端拿到结构后，另行调用本节其余接口获取。

**控制器**：

```java
@RestController
@RequestMapping("/testcase")
public class TestCaseBoardController {
  @PostMapping("/path/tree")
  public Result<TestCasePathTreeResp> queryPathTree(@Validated @RequestBody TestCasePathTreeReq req) {
    return Result.success(testCasePathTreeService.queryTree(req));
  }
}
```

**请求**（父节点定位两种方式，nodeKey 优先；不含时间窗口）：

```java
public class TestCasePathTreeReq {
  private String  nodeKey;    // 方式一（树内展开）：父节点唯一键（取上一轮响应的 nodeKey）
  // 方式二（主页面直跳详情，无 nodeKey）：定位参数组合，按传参深度逐级定位
  private Integer productId;  // 社区 id，定位起点
  private Integer projectId;  // 传入后定位到 project 层
  private String  repoUrl;    // 传入后定位到 repo 层
  private String  repoBranch; // 传入后定位到 branch 层
  private String  nodePath;   // 传入后定位到 dir/file 层（node_level = 路径段数 + 3）
}
```

**响应**：

```java
public class TestCasePathTreeResp {
  private List<Node> nodes;

  @Data
  public static class Node {
    private String  nodeKey;    // 节点唯一键，展开子节点时回传
    private String  nodeType;
    private Integer nodeLevel;
    private String  nodePath;
    private Integer productId;
    private Integer projectId;
    private String  repoUrl;
    private String  repoBranch;
    private String  productName;
    private String  projectName;
    private String  repoName;
  }
}
```

**服务实现**（两段式：先定位父节点行——nodeKey 等值或定位参数组合等值，再按父行构造子节点条件；均为 MyBatis-Plus 单表查询）：

```java
public TestCasePathTreeResp queryTree(TestCasePathTreeReq req) {
  // 根请求：返回 node_level=0 全部 product
  if (hasText(req.getNodeKey()))        parent = selectByKey(req.getNodeKey());      // 方式一：node_key 等值（UNIQUE KEY 首列）
  else if (req.getProductId() != null)  parent = selectByLocator(req);               // 方式二：主页面直跳定位参数组合
  else                                  return selectList(wrapper.eq(getNodeLevel, 0));
  if (parent == null) return empty();

  // 方式二定位规则：仅 productId → level=0；+projectId → 1；+repoUrl → 2；+repoBranch → 3；
  // +nodePath → level=路径段数+3（dir/file 层，与 ETL 的 pos+4 口径一致），
  // 各层未涉及字段按表约定取空值等值匹配（project_id=0 / repo_url='' / node_path=''）

  // 第二段：子层 = 父层+1，按父行逐级补齐定位条件（两种方式一致）
  int childLevel = parent.getNodeLevel() + 1;
  wrapper.eq(getNodeLevel, childLevel);
  wrapper.eq(getProductId, parent.getProductId());
  if (childLevel >= 2) wrapper.eq(getProjectId,  parent.getProjectId());
  if (childLevel >= 3) wrapper.eq(getRepoUrl,    parent.getRepoUrl());
  if (childLevel >= 4) wrapper.eq(getRepoBranch, parent.getRepoBranch());
  if (childLevel >= 5) wrapper.likeRight(getNodePath, parent.getNodePath() + "/");
  return treeNodeMapper.selectList(wrapper);
}
```

### 6.5 接口映射总表

| 页面功能 | 端点 | category | 处理器 | 查询方式 |
| --- | --- | --- | --- | --- |
| 总览 KPI 卡片 | `POST /common/card` | `testcase-overview` | `TestCaseOverviewCardService` | fact 聚合（窗口函数） |
| 通过率/执行率趋势（整体） | `POST /common/chart` | `testcase-pass-rate-trend` | `TestCasePassRateTrendService` | fact 聚合 |
| 通过率/执行率趋势（各社区） | `POST /common/chart` | `testcase-community-pass-rate-trend` | `TestCaseCommunityPassRateTrendService` | fact 聚合 |
| 各社区用例分布 | `POST /common/chart` | `testcase-community-distribution` | `TestCaseCommunityDistributionService` | fact 聚合（窗口函数） |
| 用例状态分布 | `POST /common/chart` | `testcase-status-distribution` | `TestCaseStatusDistributionService` | fact 聚合（窗口函数） |
| 目录树懒加载 | `POST /testcase/path/tree` | —（独立，无 category） | `TestCasePathTreeService` | tree_node 单表（MyBatis-Plus） |
| 文件下用例列表 | `POST /common/detail` | `testcase-file-case-list` | `TestCaseFileCaseListDetailService` | fact 聚合（XML） |
| 用例执行明细 | `POST /common/detail` | `testcase-case-run-detail` | `TestCaseCaseRunDetailService` | fact 单表（MyBatis-Plus） |
| 社区/项目列表 | `POST /common/detail` | `testcase-community-project-list` | `TestCaseCommunityProjectListService` | fact 聚合（XML） |
| 子节点列表 | `POST /common/detail` | `testcase-child-node-list` | `TestCaseChildNodeListDetailService` | tree 定位 + fact 聚合（XML 动态分组） |

### 6.6 公共路径过滤片段 `testCasePathFilter`

聚合类查询共用同一套路径定位过滤，在 `DwrRdEfcTestCaseFactMapper.xml` 中以 `<sql>` 片段复用：

```xml
<sql id="testCasePathFilter">
    <if test="req.productId != null">
        AND product_id = #{req.productId}
    </if>
    <if test="req.projectId != null">
        AND project_id = #{req.projectId}
    </if>
    <if test="req.repoUrl != null and req.repoUrl != ''">
        AND repo_url = #{req.repoUrl}
    </if>
    <if test="req.repoBranch != null and req.repoBranch != ''">
        AND repo_branch = #{req.repoBranch}
    </if>
    <if test="req.nodePath != null and req.nodePath != ''">
        <choose>
            <when test="req.nodeType == 'file'">
                AND full_file_path = #{req.nodePath}
            </when>
            <otherwise>
                AND full_file_path LIKE CONCAT(#{req.nodePath}, '/%')
            </otherwise>
        </choose>
    </if>
</sql>
```

所有聚合 SQL 均以 `end_time ∈ [startTime, endTime]` 首列过滤（时间窗口），并 `<include refid="testCasePathFilter"/>`。

### 6.7 各处理器 SQL 与实现

**① 总览 KPI 卡片 `testcase-overview`（每用例最新结果口径，输出 5 项指标）**

```sql
SELECT
    COUNT(*)                        AS totalCases,
    COUNT(IF(result = 1, 1, NULL))  AS passedCases,
    COUNT(IF(result = 0, 1, NULL))  AS failedCases,
    COUNT(IF(result = 2, 1, NULL))  AS skipCases
FROM (
    SELECT case_key, result,
           ROW_NUMBER() OVER (PARTITION BY case_key ORDER BY end_time DESC) AS rn
    FROM dwr_rd_efc_test_case_fact
    WHERE 1 = 1
      [AND end_time >= #{req.startTime} AND end_time <= #{req.endTime}]
      <include refid="testCasePathFilter"/>
) t
WHERE rn = 1
```

Service 层由 `total/passed/failed/skip` 计算 `executed = passed + failed + skip`，输出 5 张卡片：

| metric | name | 口径 |
| --- | --- | --- |
| `total_cases` | 测试用例总数 | `totalCases` |
| `passed_cases` | 通过用例数 | `passedCases` |
| `failed_cases` | 失败用例数 | `failedCases` |
| `exec_rate` | 执行率 | `executed / totalCases`（百分比，2 位小数） |
| `pass_rate` | 通过率 | `passedCases / executed`（百分比，2 位小数） |

**② 整体通过率/执行率趋势 `testcase-pass-rate-trend`（次数口径，逐日，无社区维度）**

```sql
SELECT
    DATE_FORMAT(end_time, '%Y-%m-%d')  AS statDate,
    SUM(IF(result = 1, 1, 0))          AS passedCnt,
    SUM(IF(result IN (0, 1, 2), 1, 0)) AS executedCnt,
    COUNT(*)                           AS totalCnt
FROM dwr_rd_efc_test_case_fact
WHERE 1 = 1
  [AND end_time >= #{req.startTime} AND end_time <= #{req.endTime}]
  <include refid="testCasePathFilter"/>
GROUP BY DATE_FORMAT(end_time, '%Y-%m-%d')
ORDER BY statDate
```

Service 层组装：`xAxis=日期序列`，仅 1 条 `series=[{name:'整体', data:[RatePoint…]}]`。每个数据点为 `RatePoint{passRate, execRate}` 双比率对象：通过率 = `passedCnt/executedCnt`，执行率 = `executedCnt/totalCnt`（分母为 0 返回 0）。统计范围跟随路径定位参数（点击树节点后按节点范围统计）。

**③ 各社区通过率/执行率趋势 `testcase-community-pass-rate-trend`（次数口径，逐日×逐社区）**

```sql
SELECT
    DATE_FORMAT(end_time, '%Y-%m-%d')  AS statDate,
    product_id                         AS productId,
    MAX(product_name)                  AS productName,
    SUM(IF(result = 1, 1, 0))          AS passedCnt,
    SUM(IF(result IN (0, 1, 2), 1, 0)) AS executedCnt,
    COUNT(*)                           AS totalCnt
FROM dwr_rd_efc_test_case_fact
WHERE 1 = 1
  [AND end_time >= #{req.startTime} AND end_time <= #{req.endTime}]
  <include refid="testCasePathFilter"/>
GROUP BY DATE_FORMAT(end_time, '%Y-%m-%d'), product_id
ORDER BY statDate
```

Service 层组装：`xAxis=日期序列`，每个社区 1 条系列（无「整体」系列，空名归「未知」），数据点为 `RatePoint{passRate, execRate}`，同一社区同日多行求和后算率，缺失日期补 `{0, 0}`。统计范围同样跟随路径定位参数。

**④ 各社区用例分布 `testcase-community-distribution`（每用例最新结果，三状态拆分）**

```sql
SELECT
    product_name                          AS productName,
    COUNT(IF(result = 1, 1, NULL))        AS passedCnt,
    COUNT(IF(result = 0, 1, NULL))        AS failedCnt,
    COUNT(IF(result IN (2, 3), 1, NULL))  AS notExecutedCnt
FROM (
    SELECT product_id, product_name, case_key, result,
           ROW_NUMBER() OVER (PARTITION BY product_id, case_key ORDER BY end_time DESC) AS rn
    FROM dwr_rd_efc_test_case_fact
    WHERE 1 = 1
      [AND end_time >= #{req.startTime} AND end_time <= #{req.endTime}]
      <include refid="testCasePathFilter"/>
) t
WHERE rn = 1
GROUP BY product_id, product_name
ORDER BY COUNT(*) DESC
```

Service 层组装 1 张 `bar` 图（可堆叠渲染）：`xAxis=社区名（按用例总数降序，空名归「未知」）`，`series=[{name:'通过'}, {name:'失败'}, {name:'未执行'}]` 三条系列。未执行 = 跳过 + 未执行。

**⑤ 用例状态分布 `testcase-status-distribution`（每用例最新结果，三状态计数）**

```sql
SELECT
    COUNT(IF(result = 1, 1, NULL))        AS passedCnt,
    COUNT(IF(result = 0, 1, NULL))        AS failedCnt,
    COUNT(IF(result IN (2, 3), 1, NULL))  AS notExecutedCnt
FROM (
    SELECT case_key, result,
           ROW_NUMBER() OVER (PARTITION BY case_key ORDER BY end_time DESC) AS rn
    FROM dwr_rd_efc_test_case_fact
    WHERE 1 = 1
      [AND end_time >= #{req.startTime} AND end_time <= #{req.endTime}]
      <include refid="testCasePathFilter"/>
) t
WHERE rn = 1
```

Service 层组装 1 张 `donut` 图：`xAxis=['通过','失败','未执行']`（扇区名），`series=[{name:'用例数', data:[passedCnt, failedCnt, notExecutedCnt]}]`，`data` 与 `xAxis` 下标一一对应。未执行 = 跳过 + 未执行。

**⑥ 文件下用例列表 `testcase-file-case-list`（一用例一行，窗口内次数 + P50/P90 + 平均 NPU 卡时，分页）**

```sql
SELECT
    case_key              AS caseKey,
    MAX(case_number)      AS caseNumber,
    MAX(class_name)       AS className,
    MAX(`level`)          AS level,
    MAX(`type`)           AS type,
    MAX(repo_name)        AS repoName,
    MAX(repo_branch)      AS repoBranch,
    MAX(full_file_path)   AS fullFilePath,
    COUNT(*)              AS runCnt,
    COUNT(IF(result = 1, 1, NULL)) AS passedCnt,
    COUNT(IF(result = 0, 1, NULL)) AS failedCnt,
    COUNT(IF(result = 2, 1, NULL)) AS skipCnt,
    PERCENTILE(`time`, 0.5)        AS durationP50,
    PERCENTILE(`time`, 0.9)        AS durationP90,
    AVG(npu_second)                AS avgNpuSecond
FROM dwr_rd_efc_test_case_fact
WHERE 1 = 1
  <include refid="testCasePathFilter"/>
  [AND end_time >= #{req.startTime} AND end_time <= #{req.endTime}]
GROUP BY case_key
ORDER BY case_key
LIMIT #{req.pageSize} OFFSET #{offset}
```

分页总数：`SELECT COUNT(DISTINCT case_key) ... <include refid="testCasePathFilter"/> [时间过滤]`。

返回字段：`caseKey, caseNumber, className, level, type, repoName, repoBranch, fullFilePath, runCnt, passedCnt, failedCnt, skipCnt, durationP50, durationP90, avgNpuConsumption`。NPU 换算统一在 Service 层用 `NumberUtil.secondsToHours(avgNpuSecond)`（卡·秒 → 卡·时，保留 2 位小数），SQL 只取原始 `avgNpuSecond`。

**⑦ 用例执行明细 `testcase-case-run-detail`（单次执行，`end_time DESC` 倒序，分页）**

MyBatis-Plus `selectPage` 单表查询（不写 SQL）：

```java
LambdaQueryWrapper<DwrRdEfcTestCaseFact> wrapper = new LambdaQueryWrapper<>();
wrapper.eq(DwrRdEfcTestCaseFact::getCaseKey, req.getCaseKey());
if (req.getStartTime() != null && req.getEndTime() != null) {
  wrapper.ge(DwrRdEfcTestCaseFact::getEndTime, req.getStartTime())
         .le(DwrRdEfcTestCaseFact::getEndTime, req.getEndTime());
}
wrapper.orderByDesc(DwrRdEfcTestCaseFact::getEndTime);
Page<DwrRdEfcTestCaseFact> page = factMapper.selectPage(new Page<>(page, pageSize), wrapper);
```

返回字段：`level, type, jobName, startTime, endTime, pipelineType, result, time, npuConsumption`。NPU 换算与其他接口一致，用 `NumberUtil.secondsToHours(npu_second)`（卡·秒 → 卡·时，保留 2 位小数），npu_second 为空返回 null。

**⑧ 社区/项目列表 `testcase-community-project-list`（按项目真分页，返回分组结构 + 社区合计）**

分页 SQL（每页 `pageSize` 个项目行；`total` 用独立 count 按项目计数）：

```sql
SELECT
    product_id                     AS productId,
    product_name                   AS productName,
    project_id                     AS projectId,
    project_name                   AS projectName,
    COUNT(*)                       AS totalCases,
    COUNT(IF(result = 1, 1, NULL)) AS passedCases,
    COUNT(IF(result = 0, 1, NULL)) AS failedCases,
    COUNT(IF(result = 2, 1, NULL)) AS skipCases
FROM (
    SELECT product_id, product_name, project_id, project_name, case_key, result,
           ROW_NUMBER() OVER (PARTITION BY project_id, case_key ORDER BY end_time DESC) AS rn
    FROM dwr_rd_efc_test_case_fact
    WHERE 1 = 1
      [AND end_time >= #{req.startTime} AND end_time <= #{req.endTime}]
) t
WHERE rn = 1
GROUP BY product_id, product_name, project_id, project_name
ORDER BY product_name, project_name, product_id, project_id
LIMIT #{req.pageSize} OFFSET #{offset}
```

```sql
-- 项目总数（按项目计数）
SELECT COUNT(*)
FROM (
    SELECT product_id, project_id
    FROM dwr_rd_efc_test_case_fact
    WHERE 1 = 1
      [AND end_time >= #{req.startTime} AND end_time <= #{req.endTime}]
    GROUP BY product_id, project_id
) t
```

社区合计（`selectCommunityTotalList`）：对当前页涉及的社区 id（`product_id IN (...)`）做社区维度全量聚合，口径与项目统计一致（按 `project_id + case_key` 取每用例最新结果后按 `product_id` 汇总），保证合计为社区全量值而非仅当前页：

```sql
SELECT
    product_id                     AS productId,
    product_name                   AS productName,
    COUNT(*)                       AS totalCases,
    COUNT(IF(result = 1, 1, NULL)) AS passedCases,
    COUNT(IF(result = 0, 1, NULL)) AS failedCases,
    COUNT(IF(result = 2, 1, NULL)) AS skipCases
FROM (
    SELECT product_id, product_name, project_id, case_key, result,
           ROW_NUMBER() OVER (PARTITION BY project_id, case_key ORDER BY end_time DESC) AS rn
    FROM dwr_rd_efc_test_case_fact
    WHERE 1 = 1
      [AND end_time >= #{req.startTime} AND end_time <= #{req.endTime}]
      AND product_id IN (#{page 涉及的社区 id 列表})
) t
WHERE rn = 1
GROUP BY product_id, product_name
```

Service 层：先取当前页项目行，按 `productId` 分组为「一社区一行」；社区行含社区合计（全量口径，`executed=通过+失败+跳过`，执行率=`executed/total`，通过率=`passed/executed`）与项目子列表 `projects[]`（仅当前页）。`total` 为项目总数（非社区数），按 `page/pageSize` 真分页。`skip` 仅内部算率，不在列表展示。

返回结构：`records[]` 一社区一行 `{productId/productName/totalCases/passedCases/failedCases/executionRate/passRate/projects[]}`，`projects[]` 元素为 `{projectId/projectName/totalCases/passedCases/failedCases/executionRate/passRate}`。

**⑨ 子节点列表 `testcase-child-node-list`（定位节点直接子节点：结构 + 统计，全量返回）**

请求 `TestCaseChildNodeListReq extends DetailReq`：父节点定位与目录树一致（`nodeKey` 优先，否则 `productId[+projectId+repoUrl+repoBranch+nodePath]` 逐级定位；均不传返回空）。

实现两段式，避免逐子节点 N+1 查询：

1. **结构**：复用 `TestCasePathTreeService.queryTree`（树请求透传 `nodeKey` 与定位参数）取直接子节点列表。
2. **统计**：一条动态分组 SQL 聚合，`groupMode` 由子层 `nodeType` 推导（project→`project`、repo→`repo`、branch→`branch`、dir/file→`path`）。统计过滤范围 = **子节点定位字段去掉子层自身分组键**（project 层不带 projectId、repo 层不带 repoUrl、branch 层不带 repoBranch；path 层另带父目录前缀，父为 branch 直下时前缀为空串由过滤片段忽略），`path` 模式下 `pathSegments = 子节点 nodePath 段数`。SQL 用两层派生表：内层 `g` 按模式计算 `groupKey`（choose 仅一处），外层统一做 `ROW_NUMBER` 取每用例最新结果：

```sql
SELECT
    groupKey,
    COUNT(*)                       AS totalCases,
    COUNT(IF(result = 1, 1, NULL))  AS passedCases,
    COUNT(IF(result = 0, 1, NULL))  AS failedCases,
    COUNT(IF(result = 2, 1, NULL))  AS skipCases
FROM (
    SELECT groupKey, case_key, result,
           ROW_NUMBER() OVER (PARTITION BY groupKey, case_key ORDER BY end_time DESC) AS rn
    FROM (
        SELECT case_key, result, end_time,
            <choose>
                <when test="groupMode == 'project'">CAST(project_id AS CHAR)</when>
                <when test="groupMode == 'repo'">repo_url</when>
                <when test="groupMode == 'branch'">repo_branch</when>
                <otherwise>SUBSTRING_INDEX(full_file_path, '/', #{pathSegments})</otherwise>
            </choose>
            AS groupKey
        FROM dwr_rd_efc_test_case_fact
        WHERE 1 = 1
          [AND end_time >= #{req.startTime} AND end_time <= #{req.endTime}]
          <include refid="testCasePathFilter"/>   <!-- 过滤字段为服务层推导后的父节点范围 -->
    ) g
) t
WHERE rn = 1
GROUP BY groupKey
```

Service 层内存合并：`groupKey` 与子节点匹配键（project→`String.valueOf(projectId)`、repo→`repoUrl`、branch→`repoBranch`、path→`nodePath`）对齐，无统计数据的子节点计数补 0；每行输出结构字段（`nodeKey/nodeType/nodeLevel/name/nodePath/定位字段`）+ 统计字段（`totalCases/passedCases/failedCases`，`executed=通过+失败+跳过`，执行率/通过率同⑦口径）。`name` 按层级取：project→项目名、repo→仓库名、branch→分支名、dir/file→路径末段。

---

## 7. 性能设计要点

1. **宽表 + 冗余**：维度（社区/项目/平台/流水线名/job 名）一次性焊进 `fact`，接口查询零 JOIN，符合「允许违反范式」。
2. **单表查询**：目录树与用例执行明细走 MyBatis-Plus `BaseMapper + QueryWrapper`；其余聚合场景每个处理器 1 个简明 SQL（单表、无 JOIN）。
3. **去重一次算**：`case_key` MD5 在 ETL-1 预计算，fact `DISTRIBUTED BY HASH(case_key)`，`case_key` 过滤/去重 colocate。
4. **最新结果查询期物化**：不建 `latest` 快照表，卡片/社区项目列表用 `ROW_NUMBER() OVER(PARTITION BY case_key ORDER BY end_time DESC)` 取 `rn=1`，量级为窗口内用例数。
5. **树结构表不含时变计数**：`tree_node` 只存结构（行数稳定），计数从 fact 动态聚合；建议对 `fact.full_file_path`、`end_time` 建倒排索引 / BloomFilter。
6. **时间过滤下推**：所有窗口查询首列过滤 `end_time`（UTC，界面 +8h 补偿），命中分区裁剪（若按天分区）。
7. **SQL 片段复用**：路径定位过滤统一为 `<sql id="testCasePathFilter"/>`，避免多查询重复。
8. **排序字段白名单**：列表排序字段（如有）在 mapper 层白名单映射，杜绝 SQL 注入与无效排序。

---

## 8. 待确认事项

| 编号 | 事项 | 说明 |
| --- | --- | --- |
| T1 | 测试类型来源 | 上游 `dwi_rd_efc_test_case_result` 需新增 `type` 列（SeaTunnel 透传）后方可用 |
| T2 | 状态 5 态 | 当前为 4 态（`1/0/2/3`）；`running/aborted` 需上游采集层补齐后扩展 |
| T3 | NPU 使用量/使用率 | 本期仅消耗量 `npu_second`；使用量/使用率待上游补列后再算 |

---

## 9. 验证方式

1. 建表后跑 ETL-1、ETL-3，抽查：
   - `SELECT COUNT(*) FROM dwr_rd_efc_test_case_fact WHERE product_name IS NULL;`（映射后应为 0 或已知兜底）
   - `SELECT COUNT(*) FROM dm_rd_efc_test_case_tree_node GROUP BY node_type,product_id,project_id,repo_url,repo_branch,node_path HAVING COUNT(*)>1;`（应空，唯一键兜底）
2. 树一致性：某 `file` 节点 `node_path` 能在 fact 命中 `full_file_path` 等值记录；dir 节点前缀能命中 `LIKE '前缀/%'`。
3. 口径一致性：从 fact 手算某窗口 `total/passed/failed` 与卡片接口返回一致。
4. 接口联调：
   - `POST /common/card`（`testcase-overview`）
   - `POST /common/chart`（`testcase-pass-rate-trend` / `testcase-community-distribution` / `testcase-status-distribution`）
   - `POST /common/detail`（`testcase-file-case-list` / `testcase-case-run-detail` / `testcase-community-project-list`）
   - `POST /testcase/path/tree`
5. 性能：beta 环境压测文件下用例列表分页、树结构懒加载（窗口 90 天），确认单次查询无 JOIN、无明细大表跨日全扫。

---

## 10. 代码文件清单

### 10.1 控制器

| 文件 | 说明 |
| --- | --- |
| `api/controller/CommonController.java` | 新增 `POST /common/card`、`POST /common/chart`（`/common/detail` 为既有） |
| `api/controller/TestCaseBoardController.java` | 新增 `POST /testcase/path/tree` |

### 10.2 请求 / 响应（API）

| 文件 | 说明 |
| --- | --- |
| `api/request/common/card/CardReq.java` | 卡片请求基类（仅 `category`） |
| `api/request/common/card/TestCaseOverviewCardReq.java` | 总览卡片请求 |
| `api/request/common/chart/ChartReq.java` | 趋势请求基类（仅 `category`） |
| `api/request/common/chart/TestCasePassRateTrendReq.java` | 通过率趋势请求 |
| `api/request/common/chart/TestCaseCommunityDistributionReq.java` | 社区分布请求 |
| `api/request/common/chart/TestCaseStatusDistributionReq.java` | 状态分布请求 |
| `api/request/common/detail/TestCaseFileCaseListReq.java` | 文件下用例列表请求 |
| `api/request/common/detail/TestCaseCaseRunDetailReq.java` | 用例执行明细请求 |
| `api/request/common/detail/TestCaseCommunityProjectListReq.java` | 社区/项目列表请求 |
| `api/request/testcase/TestCasePathTreeReq.java` | 目录树请求 |
| `api/response/common/card/CardResp.java` / `CardItem.java` | 卡片响应 |
| `api/response/common/chart/ChartResp.java` / `Series.java` / `RatePoint.java` | 趋势图响应（RatePoint 为趋势双比率数据点） |
| `api/response/common/detail/TestCaseFileCaseListResp.java` | 文件列表响应 |
| `api/response/common/detail/TestCaseCaseRunDetailResp.java` | 执行明细响应 |
| `api/response/common/detail/TestCaseCommunityProjectListResp.java` | 社区/项目列表响应 |
| `api/response/testcase/TestCasePathTreeResp.java` | 目录树响应 |

### 10.3 领域模型 / Mapper

| 文件 | 说明 |
| --- | --- |
| `domain/model/testcase/DwrRdEfcTestCaseFact.java` | fact 实体 |
| `domain/model/testcase/DmRdEfcTestCaseTreeNode.java` | 树节点实体 |
| `domain/model/testcase/aggregate/TestCaseOverviewAggregate.java` | 总览聚合 VO |
| `domain/model/testcase/aggregate/TestCasePassRateTrendAggregate.java` | 各社区趋势聚合 VO |
| `domain/model/testcase/aggregate/TestCaseOverallPassRateTrendAggregate.java` | 整体趋势聚合 VO |
| `domain/model/testcase/aggregate/TestCaseCommunityDistributionAggregate.java` | 分布聚合 VO |
| `domain/model/testcase/aggregate/TestCaseStatusDistributionAggregate.java` | 状态分布聚合 VO |
| `domain/model/testcase/aggregate/TestCaseFileCaseAggregate.java` | 文件列表聚合 VO |
| `domain/model/testcase/aggregate/TestCaseCommunityProjectAggregate.java` | 社区项目聚合 VO |
| `domain/mapper/testcase/DwrRdEfcTestCaseFactMapper.java` | fact Mapper 接口（聚合走 XML） |
| `domain/mapper/testcase/DmRdEfcTestCaseTreeNodeMapper.java` | 树节点 Mapper（MyBatis-Plus） |
| `resources/mapper/DwrRdEfcTestCaseFactMapper.xml` | fact 聚合 SQL（含 `testCasePathFilter` 片段） |

### 10.4 服务 / 工厂 / 枚举

| 文件 | 说明 |
| --- | --- |
| `domain/service/common/CardService.java` / `ChartService.java` | 卡片/趋势处理器接口 |
| `app/service/testcase/TestCaseOverviewCardService.java` | 总览卡片 |
| `app/service/testcase/TestCasePassRateTrendService.java` | 整体通过率/执行率趋势 |
| `app/service/testcase/TestCaseCommunityPassRateTrendService.java` | 各社区通过率/执行率趋势 |
| `app/service/testcase/TestCaseCommunityDistributionService.java` | 社区分布（三状态） |
| `app/service/testcase/TestCaseStatusDistributionService.java` | 状态分布（环形图） |
| `app/service/testcase/TestCasePathTreeService.java` | 目录树 |
| `app/service/testcase/TestCaseFileCaseListDetailService.java` | 文件下用例列表 |
| `app/service/testcase/TestCaseCaseRunDetailService.java` | 用例执行明细 |
| `app/service/testcase/TestCaseCommunityProjectListService.java` | 社区/项目列表 |
| `infrastructure/enumeration/common/CardCommonEnum.java` | `testcase-overview` |
| `infrastructure/enumeration/common/ChartCommonEnum.java` | `testcase-pass-rate-trend` / `testcase-community-pass-rate-trend` / `testcase-community-distribution` / `testcase-status-distribution` |
| `infrastructure/enumeration/common/DetailCommonEnum.java` | 追加 `testcase-file-case-list` / `testcase-case-run-detail` / `testcase-community-project-list` / `testcase-child-node-list` |