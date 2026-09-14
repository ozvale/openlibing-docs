# 资源运营看板 — 后端实现设计

## 1. 需求概述

在 `openlibing-ops` 中新增「资源运营看板」，面向开源项目 CI 算力运营场景，展示项目绑定资源池的 **NPU 分配与使用全景**（步长 1 小时）。

看板包含 4 个核心区块 + 3 级下钻链路（来自高保真页面 `ResourceOverview0818.html` / `PoolDrawer.html`）：

| 区块                   | 内容                                                                                       | 计算口径（来自《资源运营看板说明》）                                                                                                                                       |
| ---------------------- | ------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 资源总览 KPI 卡片      | 资源池总量、资源总量、NPU 分配率、NPU 使用率（均按 华为云/实验室 分开展示）                | ① 资源池总量：按 `location`（云上/实验室）统计 distinct 资源池数；② 资源总量：按 `generation` 统计卡数；③ NPU 分配率 = 分配卡时 / 总卡时；④ NPU 使用率 = 使用卡时 / 总卡时 |
| NPU 趋势图             | 分配曲线 + 使用曲线，X 轴 1 小时，支持按 **资源池 / 代际** 两个维度切换                    | 逐小时按维度分组聚合分配率、使用率                                                                                                                                         |
| 服务器 NPU 热力图      | 效率分析图（分配率 − 使用率）+ 分配率图 + 使用率图，Y 轴服务器、X 轴 1 小时                | 单机单小时分配率 / 使用率 / 效率                                                                                                                                           |
| 资源池明细（下钻）     | 资源池列表（类型徽标 + 使用项目 chips + 分配率/使用率），展开显示该池机器明细表            | 按资源池聚合 + 机器级明细                                                                                                                                                  |
| 项目资源效率（下钻）   | 项目级效率表：PR 资源排队时长[P90]、PR NPU 消耗、NPU 使用率                                | ① 排队时长 P90：PR 流水线测试任务 job 从申请资源到分配成功的等待时长 P90（近 24h）；② NPU 消耗：PR 运行卡时合计                                                            |
| 流水线资源效率（下钻） | 项目下钻抽屉内：项目概要 + 流水线资源分配热力 + 流水线资源效率表（含「查看运行明细」操作） | 按流水线聚合排队时长 P90、分配卡时、运行次数                                                                                                                               |
| 流水线运行明细（下钻） | 单流水线运行列表：运行 ID、结束时间、排队时长、NPU 消耗、状态 + NPU 分配率/使用率分析      | 按运行（pipeline_run）聚合，队列卡时、排队时长、状态来自运行事实表                                                                                                         |

**关键约束**

- 时间范围：默认昨天，最多 7 天，不允许超过 7 天。
- 项目隔离：每个项目只能看到自己绑定的资源池（`dwi_rd_efc_project_resource_pool_relation`），`projectId` 为空时展示全部。

---

## 2. 现状分析与复用点

### 2.1 现有相关接口（可复用）

| 接口                                                                                            | 说明                                                   | 复用方式                                                      |
| ----------------------------------------------------------------------------------------------- | ------------------------------------------------------ | ------------------------------------------------------------- |
| `POST /resource/summary`、`POST /resource/trend`（ResourceController）                          | 资源消耗看板（CPU/NPU 核时），业务语义与"运营看板"不同 | 不直接复用业务，仅复用其分层/编码风格                         |
| `POST /ops-overview/resource-summary`（OpsOverviewController）                                  | 按项目+类型返回 NPU 消耗卡片汇总                       | 提供了 NPU 率类指标计算范式（`queryNpuAllSummary`），口径参考 |
| `POST /common/detail`（CommonController）+ `DetailService` + `RepoDetailFactory`                | 通用详情查询分发，按 `category` 路由                   | **下钻链路直接走该通道**，新增 category                       |
| `POST /common/refresh-time`（ModuleRefreshTimeService + `tbl_ops_module_ds_workflow_relation`） | 按 module 查 DS workflow 最近成功执行时间              | **看板刷新时间直接复用**，仅需新增一行 module 配置            |

### 2.2 现有数据表（数据源）

数据源表（`table.sql`，S/D/M 分层）：

| 表                                          | 层级 | 用途                                                                                                                                                                                                                                                                                                                                                                                          |
| ------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dm_rd_efc_server_resource_hour`            | M    | **看板唯一数据源（核心宽表）**：`statistic_period`、`server_ip`、`resource_pool_id`、`machine_id`、`resource_pool_name`、`generation`、`location`、`total_npu_num`、`assign_npu_hours`、`used_npu_hours`、`total_npu_hours`。**pool/gen/location/total 全部维度已冗余进事实表，主查询无需再 JOIN 维度表**。看板所有指标（KPI 静态指标 + 动态率值 + 趋势 + 热力图 + 资源池明细）均**单表直查** |
| `dwi_rd_efc_project_resource_pool_relation` | D    | 项目-资源池绑定：`resource_pool_id`、`project_id`、`resource_pool_name`、`description`（源表描述）、`total_npu_num`、`scene`、**`project_name`（解析自 description，行内冗余）**、`create_time`（项目隔离/项目 chips）                                                                                                                                                                        |
| `dwr_rd_efc_resource_npu_detail`            | D    | **任务×小时切片最底层明细（运行分析专用）**：`platform`(codearts/gitcode/github)、`pipeline_id`、`pipeline_run_id`、`job_id`、`job_name`、`slot_time`、`job_start_time`/`job_run_start_time`/`job_end_time`、`job_pending_duration`、`assign_npu_second`、**`server_ip`**、`job_current_slot_pending_seconds`/`job_current_slot_running_seconds`                                              |

> **数据源前提**：`dm_rd_efc_server_resource_hour`（宽表）与 `dwr_rd_efc_resource_npu_detail` 为新增数据源，由外部 DS 清洗工作流产出，DDL/清洗工作流不在本仓实现范围内。宽表逐台逐时全量写入（`server_ip` 与机器绑定、唯一键含 `server_ip`，含无任务小时也落一行 `total_npu_hours`），KPI 静态指标（资源池总量/资源总量）直接由宽表 DISTINCT 聚合得出；同一 `(resource_pool_id, server_ip)` 组合下 `total_npu_num` 冗余值一致，避免统计卡数重复。三张平台任务事实表（codearts/gitcode/github）分别由对应平台的 dwi 层数据支撑，数据已可查询；`dwr_rd_efc_resource_npu_detail` 由这三张事实表按小时切片汇聚产出。

**3 级下钻数据源（复用现有表）**：

| 表                                         | 层级 | 用途                                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ------------------------------------------ | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dwi_rd_project_pipeline_relation`         | D    | 项目↔流水线关联：`project_id`、`pipeline_id`、`repo_id`（现有 `OpsResourceDetailMapper` 已使用）                                                                                                                                                                                                                                                                                                                                            |
| `dwr_rd_efc_pipeline_run_fact`             | D    | **运行级事实（仅 codearts）**：`pipeline_run_id`、`pipeline_name`、`pipeline_status`、`pipeline_start_time/end_time`、`dt_pending_duration`/`dt_max_pending_duration`、`npu_second`/`dt_npu_second`、`dt_count` 等。**下钻链路已不再依赖此表**：PR 流水线集合识别、流水线名/状态展示均改由 `dwr_rd_efc_resource_npu_detail` 的 `pipeline_name`/`pipeline_status` 提供（覆盖三平台）                                                         |
| `dwr_rd_efc_pipeline_run_job_fact`         | D    | **codearts 平台任务事实**：`pipeline_id`/`pipeline_run_id`/`job_id`、`job_name`、`job_type`、`job_status`、`job_start_time`/`job_run_start_time`/`job_end_time`、`job_pending_duration`、`npu_second`、**`server_ip`**（数据源，汇聚产出任务×小时切片）                                                                                                                                                                                     |
| `dwr_rd_efc_workflow_run_job_gitcode_fact` | D    | **gitcode 平台任务事实**：`workflow_id`/`workflow_run_id`（映射自 pipeline_id/pipeline_run_id）、`job_id`、`job_name`、`job_type`、`job_status`、`job_start_time`/`job_run_start_time`/`job_end_time`、`job_pending_duration`、`npu_second`、**`server_ip`**（数据源，汇聚产出任务×小时切片）                                                                                                                                               |
| `dwr_rd_efc_workflow_run_job_github_fact`  | D    | **github 平台任务事实**：`workflow_id`/`workflow_run_id`/`job_id`（bigint，映射自 pipeline_id/pipeline_run_id/job_id）、`job_name`、`job_type`、`job_status`、`job_start_time`/`job_run_start_time`/`job_end_time`、`job_pending_duration`、`npu_second`、**`server_ip`**（数据源，汇聚产出任务×小时切片）                                                                                                                                  |
| `dwr_rd_efc_resource_npu_detail`           | D    | **跨三平台任务×小时切片（由上述三张平台任务事实表按小时切片汇聚）**：`platform`(codearts/gitcode/github)、`pipeline_id`、`pipeline_run_id`、`pipeline_name`、`pipeline_status`、`job_id`、`job_name`、`slot_time`、job 级时间/排队/卡时字段、**`server_ip`**、切片排队/运行秒数。**自带 `platform` + `pipeline_name` + `pipeline_status`，4.8 项目/流水线/运行明细的 PR 识别与流水线名/状态展示、4.8.1 运行分析均直接查此表（覆盖三平台）** |
| `sdi_version_pipeline_base_info`           | D    | Nightly 流水线维度：`project_id`、`pipeline_id`、`name`（现有 Nightly 聚合已使用）                                                                                                                                                                                                                                                                                                                                                          |

> 说明：下钻链路完全复用现有事实表与 `dwi_rd_project_pipeline_relation`，无需新增表。PR 流水线按现有约定 `lower(pipeline_name) LIKE 'pr%'` 识别（参考 `OpsResourceDetailMapper.xml` PR 分支），Nightly 走 `sdi_version_pipeline_base_info`。

> **任务→机器映射与平台路由**：运行级事实表（`run_fact`）无 `server_ip`，任务→分配机器/排队/运行时段的映射来自**平台任务事实表**（codearts/gitcode/github 各一张，job 级、每任务一行，自带 `server_ip` + `job_name` + `job_start_time`/`job_run_start_time`/`job_end_time` + `job_pending_duration` + `npu_second`）。`dwr_rd_efc_resource_npu_detail` 是上述三张事实表按小时切片汇聚的跨平台汇总，自带 `platform`，4.8.1 先用它确定流水线所属平台，再**路由到对应平台事实表**查询任务明细（避免按 `pipeline_id` 单表过滤导致跨平台串任务）。

### 2.3 复用组件

- `TimeReq`（`startDate/endDate` 自动推导 `startTime/endTime`）作为所有看板请求基类；
- `Result` / `PageResult` 统一响应；
- `NumberUtil.truncateRate` / `NumberUtil.roundDecimal` 统一率值与小数处理；
- `DetailCommonEnum` + `DetailReq` `@JsonSubTypes` 注册新下钻类型；
- Mapper XML 的 CTE + `IFNULL/NULLIF` 防除零写法（参考 `OpsNpuAllDetailMapper.xml`）。

---

## 3. 总体方案

### 3.1 数据查询方案

以 `dm_rd_efc_server_resource_hour`（已含 pool/gen/location/total 全部维度的宽表）为**唯一数据源**：项目过滤 JOIN `dwi_rd_efc_project_resource_pool_relation`，**不 JOIN 任何维度表**。静态指标（资源池总量/资源总量）与动态指标（分配/使用率、趋势、热力图）全部由该表聚合得到。

- 无新增表、无新增 ETL；单表 SQL 无 JOIN、无重复聚合风险；数据量（服务器 × ≤168 小时）单表查询开销可忽略。
- KPI 静态指标（资源池总量/资源总量）从宽表按 `location`/`generation` **先 DISTINCT 机器再聚合**（避免按小时重复）。

### 3.2 分层架构

```
前端 (ops-web)
   │  POST /resource-operation/{summary|trend|heatmap|run-analysis}
   │  POST /common/detail
   │      category=ops-resource-pool-detail        (资源池明细)
   │      category=ops-project-resource-efficiency (项目资源效率)
   │      category=ops-pipeline-resource-efficiency (流水线资源效率)
   │      category=ops-pipeline-run-detail          (流水线运行明细)
   │  POST /common/refresh-time
   ▼
Controller
   ├─ ResourceOperationController (新增, /resource-operation, 4 个接口)
   └─ CommonController (复用, /common/detail)
   ▼
Service
   ├─ ResourceOperationService (新增, KPI/趋势/热力图/运行分析合并)
   └─ DetailService 实现（新增 4 个，由 RepoDetailFactory 自动注册）
       ├─ OpsResourcePoolDetailDetailService
       ├─ OpsProjectResourceEfficiencyDetailService
       ├─ OpsPipelineResourceEfficiencyDetailService
       └─ OpsPipelineRunDetailDetailService
   ▼
Mapper
   ├─ ResourceOperationMapper (新增, 资源池维度+小时事实 SQL, 含热力图 cells)
   └─ ResourceEfficiencyMapper (新增, 下钻链路 SQL, 复用运行/任务事实表)
   ▼
Doris
   ├─ dm_rd_efc_server_resource_hour        (唯一数据源, 含 pool/gen/location/total 维度)
   ├─ dwi_rd_efc_project_resource_pool_relation (项目-资源池隔离)
   ├─ dwi_rd_project_pipeline_relation      (项目-流水线关联, 下钻)
   ├─ dwr_rd_efc_pipeline_run_fact          (运行级事实, 运行明细表 4.8)
   ├─ dwr_rd_efc_resource_npu_detail        (任务×小时切片, 跨三平台汇总, 4.8.1 按 pipeline_run_id 直接查询组装任务连线与状态)
   └─ dwr_rd_efc_pipeline_run_job_fact
      + dwr_rd_efc_workflow_run_job_gitcode_fact
      + dwr_rd_efc_workflow_run_job_github_fact (三张平台任务事实表, 汇聚产出 npu_detail 切片, 4.8.1 不再直接路由)
```

---

## 4. 接口设计

> 通用说明：请求均 `@PostMapping` + `@RequestBody` + `@Validated`，响应统一 `Result<T>`；时间范围为**闭区间**，服务端校验 `startDate <= endDate` 且跨度 ≤ 7 天。

### 4.1 KPI 汇总

**`POST /resource-operation/summary`**

请求 `ResourceOperationSummaryReq extends TimeReq`：

```json
{ "projectId": 100, "startDate": "2026-08-16", "endDate": "2026-08-16" }
```

| 字段                | 类型      | 必填 | 说明                  |
| ------------------- | --------- | ---- | --------------------- |
| projectId           | Integer   | 否   | 为空时展示全部资源池  |
| startDate / endDate | LocalDate | 是   | 默认昨天，跨度 ≤ 7 天 |

响应 `ResourceOperationSummaryResp`：

```json
{
  "poolTotal": { "cloud": 1, "lab": 2 },
  "resourceTotal": {
    "cloud": [
      { "generation": "A5", "npuNum": 1 },
      { "generation": "A3", "npuNum": 2 }
    ],
    "lab": [{ "generation": "A5", "npuNum": 1 }]
  },
  "allocRate": { "cloud": 86.4, "lab": 71.2 },
  "usageRate": { "cloud": 63.8, "lab": 47.5 }
}
```

口径说明：

- **静态指标 `poolTotal` / `resourceTotal`**：从宽表 `dm_rd_efc_server_resource_hour` 直接聚合：
  - 资源池总量 = `COUNT(DISTINCT resource_pool_id)`，按 `location` 分组；
  - 资源总量（代际卡数）= **先 `DISTINCT (resource_pool_id, server_ip)` 再 `SUM(total_npu_num)`**，按 `generation` 分组（避免每小时每台机器重复累加卡数）；
  - 两个静态指标聚合时必须限定时间范围（取范围内出现过的机器集合）。
- **动态指标 `allocRate` / `usageRate`**：从宽表按 `location` 聚合：`SUM(assign_npu_hours)/SUM(total_npu_hours)`、`SUM(used_npu_hours)/SUM(total_npu_hours)`（`location` 已在宽表行内，无需 JOIN 维度表）；
- `location` 取值以宽表注释为准（`云上/实验室`），后端原样返回作 key，前端映射展示「华为云/实验室」。

### 4.2 NPU 趋势图

**`POST /resource-operation/trend`**

请求 `ResourceOperationTrendReq extends TimeReq`：

```json
{
  "projectId": 100,
  "startDate": "2026-08-10",
  "endDate": "2026-08-16",
  "dim": "pool"
}
```

| 字段                | 类型      | 必填 | 说明                                                                |
| ------------------- | --------- | ---- | ------------------------------------------------------------------- |
| projectId           | Integer   | 否   | 为空展示全部                                                        |
| startDate / endDate | LocalDate | 是   | 跨度 ≤ 7 天                                                         |
| dim                 | String    | 否   | `pool`（默认）/ `gen`；响应始终返回两个维度，便于前端免重复请求切换 |

响应 `ResourceOperationTrendResp`（X 轴小时刻度 + 各分组分配/使用曲线）：

```json
{
  "labels": ["2026-08-10 00:00", "2026-08-10 01:00", "...", "2026-08-16 23:00"],
  "pool": [
    {
      "name": "华为云",
      "alloc": [22, 20, 18, "..."],
      "usage": [12, 11, 10, "..."]
    },
    {
      "name": "实验室 A",
      "alloc": [10, 8, 6, "..."],
      "usage": [6, 5, 4, "..."]
    }
  ],
  "gen": [
    { "name": "A5", "alloc": [16, 14, 12, "..."], "usage": [10, 9, 8, "..."] },
    { "name": "A3", "alloc": [12, 10, 9, "..."], "usage": [8, 7, 6, "..."] }
  ]
}
```

口径：逐小时按分组聚合，`alloc = SUM(assign)/SUM(total)`，`usage = SUM(used)/SUM(total)`；`dim=pool` 按宽表 `resource_pool_name` 分组，`dim=gen` 按宽表 `generation` 分组（**分组列已在事实表行内，直接 `GROUP BY`，无维度 JOIN**）。缺失小时补 `0`，保证数组长度与 `labels` 对齐。

### 4.3 服务器 NPU 热力图

**`POST /resource-operation/heatmap`**

请求 `ResourceOperationHeatmapReq extends TimeReq`：

| 字段                | 类型      | 必填 | 说明                                                                         |
| ------------------- | --------- | ---- | ---------------------------------------------------------------------------- |
| projectId           | Integer   | 否   | 为空展示全部                                                                 |
| resourcePoolId      | Long      | 否   | **下钻抽屉复用**：指定资源池时仅返回该池服务器，供 PoolDrawer 内嵌热力图使用 |
| startDate / endDate | LocalDate | 是   | 默认昨天，跨度 ≤ 7 天                                                        |

响应 `ResourceOperationHeatmapResp`：

```json
{
  "labels": ["2026-08-16 00:00", "2026-08-16 01:00", "..."],
  "servers": [
    {
      "ip": "10.10.5.21",
      "pool": "华为云",
      "gen": "A5",
      "alloc": [22, 20, 18, "..."],
      "usage": [14, 12, 10, "..."]
    }
  ]
}
```

口径：单机单小时 `alloc = assign/total`、`usage = used/total`；**效率 = alloc − usage**，由前端根据两份数组计算（与高保真一致，效率图沿用分配率 0-100 色阶）。

> 宽表按 `(resource_pool_id, server_ip, statistic_period)` 唯一：`resourcePoolId` 参数为空时按 `resource_pool_id` 分组返回全部机器（同名 IP 多池时各池独立一行，`pool` 字段取该行 `resource_pool_name`）；`resourcePoolId` 非空时（PoolDrawer 复用）直接 `WHERE resource_pool_id = #{resourcePoolId}`，一机多池不再重复。

### 4.4 资源池明细（下钻，复用 /common/detail）

**`POST /common/detail`**，`category = ops-resource-pool-detail`。

请求 `OpsResourcePoolDetailDetailReq extends DetailReq`（继承 `TimeReq`，含分页/排序字段）：

```json
{
  "category": "ops-resource-pool-detail",
  "projectId": 100,
  "startDate": "2026-08-16",
  "endDate": "2026-08-16",
  "page": 1,
  "pageSize": 10,
  "sortField": "allocRate",
  "sortRule": "DESC"
}
```

响应 `PageResult<OpsResourcePoolDetailDetailResp>`，每条 = 一个资源池：

```json
{
  "resourcePoolId": 1,
  "resourcePoolName": "华为云资源池",
  "location": "cloud",
  "allocRate": 86.4,
  "usageRate": 66.2,
  "projectNames": ["MindIE", "MindSpeed", "PTA", "openlibing"],
  "machines": [
    {
      "ip": "10.10.5.21",
      "totalNpuHours": 24.0,
      "assignNpuHours": 21.1,
      "usedNpuHours": 18.6,
      "allocRate": 88.0,
      "usageRate": 78.0
    }
  ]
}
```

- `allocRate`/`usageRate`：**直接按宽表 `resource_pool_id` 聚合**，时间范围内 `SUM(assign)/SUM(total)`、`SUM(used)/SUM(total)`；`resourcePoolName`/`location` 取自宽表行内（`GROUP BY resource_pool_id` 任取一行）；
- `projectNames`：该池绑定的项目名 chips（`dwi_rd_efc_project_resource_pool_relation` 行内 `project_name`，按 `resource_pool_id` 聚合、去重）；
- `machines`：该池机器级明细（IP + 总/分配/使用卡时 + 分配率/使用率），时间范围内按 `(resource_pool_id, server_ip)` 聚合；
- 排序白名单：`allocRate / usageRate / totalNpuHours / serverIp`（前端字段映射，参考 `SortFieldValidator` 模式）。
- **PoolDrawer 内嵌热力图复用**：抽屉展开某池后，前端用 `resourcePoolId` 再调一次 `POST /resource-operation/heatmap`（4.3），即可渲染该池的机器热力图，无需额外下钻接口。

### 4.5 刷新时间（复用）

复用 `POST /common/refresh-time`，在 `tbl_ops_module_ds_workflow_relation` 新增一行：

```
module = resource_operation_dashboard
module_name = 资源运营看板
workflow_code = <清洗 dm_rd_efc_server_resource_hour 的 DS workflow_code>
```

---

## 4.6 项目资源效率（一级下钻，复用 /common/detail）

> 高保真主页底部「项目资源效率」表。点击行 → 二级下钻（4.7）。

**`POST /common/detail`**，`category = ops-project-resource-efficiency`。

请求 `OpsProjectResourceEfficiencyReq extends DetailReq`：

```json
{
  "category": "ops-project-resource-efficiency",
  "projectName": "open", // 模糊搜索，可空
  "startDate": "2026-08-16",
  "endDate": "2026-08-16",
  "page": 1,
  "pageSize": 10,
  "sortField": "queueP90",
  "sortRule": "DESC"
}
```

| 字段                | 类型      | 必填 | 说明                               |
| ------------------- | --------- | ---- | ---------------------------------- |
| projectName         | String    | 否   | 项目名模糊搜索（复用 `name` 字段） |
| startDate / endDate | LocalDate | 是   | 默认昨天，跨度 ≤ 7 天              |
| sortField           | String    | 否   | `queueP90 / npuUsageRate`          |

响应 `PageResult<OpsProjectResourceEfficiencyResp>`，每条 = 一个项目：

```json
{
  "projectId": 100,
  "projectName": "openlibing",
  "queueP90": 12.6, // PR 资源排队时长(测试任务)[P90](min)
  "npuAllocHours": 18.4, // PR NPU 分配(卡时)
  "npuUsageRate": 64.1, // NPU 使用率(%)
  "resourcePools": ["昇腾统一资源池-CICD"] // 项目关联资源池名称（项目下钻顶部框 pills，去重）
}
```

口径与数据源：

- 项目集合 = 绑定资源池的项目（`dwi_rd_efc_project_resource_pool_relation`，`project_id`/`project_name` 均在行内）；`projectId` 非空时单项目展示；
- `queueP90` = 时间范围内该项目 **PR** 流水线的 **DT 测试任务**排队时长 P90：来自 `dwr_rd_efc_resource_npu_detail`，取 `job_type='DT'` 任务（按 `pipeline_id/pipeline_run_id/job_id` 去重）的 `job_pending_duration` P90 / 60，按 `job_start_time` 落窗（全窗口 startDate~endDate）；PR 流水线集合沿用 `dwr_rd_efc_pipeline_run_fact` 的 `lower(pipeline_name) LIKE 'pr%'` 识别；
- `npuAllocHours` = 该项目 **PR** 流水线任务 NPU 分配卡时：来自 `dwr_rd_efc_resource_npu_detail`，`SUM(assign_npu_second)/3600`，按 `job_start_time` 落窗（全窗口 startDate~endDate）；PR 流水线集合同上由 run_fact 的 pr% 识别；
- `npuUsageRate` = 该项目关联资源池的 NPU 使用率（复用 4.1 的 usageRate 口径，按绑定资源池聚合 `SUM(used)/SUM(total)`）；
- `resourcePools` = `dwi_rd_efc_project_resource_pool_relation` 按 `project_id` 取的 `resource_pool_name` 去重列表（数据侧已解析，直接取行内列）。

### 4.7 流水线资源效率（二级下钻，复用 /common/detail）

> 点击项目行进入项目下钻抽屉，抽屉内「流水线资源效率」表（PR/Nightly 可切换），含「查看运行明细」操作 → 三级下钻（4.8）。

**`POST /common/detail`**，`category = ops-pipeline-resource-efficiency`。

请求 `OpsPipelineResourceEfficiencyReq extends DetailReq`：

```json
{
  "category": "ops-pipeline-resource-efficiency",
  "projectId": 100,
  "pipelineType": "PR", // PR / Nightly，默认 PR
  "startDate": "2026-08-16",
  "endDate": "2026-08-16",
  "page": 1,
  "pageSize": 10,
  "sortField": "queueP90",
  "sortRule": "DESC"
}
```

响应 `PageResult<OpsPipelineResourceEfficiencyResp>`，每条 = 一个流水线：

```json
{
  "pipelineId": 123,
  "pipelineName": "pr-gate-ut",
  "type": "PR",
  "queueP90": 15.2, // PR 资源排队时长(测试任务)[P90](min)
  "allocHours": 18.4, // 分配卡时
  "runNum": 36 // 运行次数
}
```

口径与数据源：

- PR：`dwi_rd_project_pipeline_relation`（`project_id`）JOIN `dwr_rd_efc_pipeline_run_fact`，`lower(pipeline_name) LIKE 'pr%'`；
- Nightly：`sdi_version_pipeline_base_info`（`project_id`）JOIN `dwr_rd_efc_pipeline_run_fact`（复用 `OpsResourceDetailMapper` Nightly 分支约定）；
- `queueP90` = 该流水线的 **DT 测试任务**排队时长 P90：来自 `dwr_rd_efc_resource_npu_detail`，取 `job_type='DT'` 任务（按 `pipeline_id/pipeline_run_id/job_id` 去重）的 `job_pending_duration` P90 / 60，按 `job_start_time` 落窗（全窗口 startDate~endDate）；> 10 min 由前端标告警色；
- `allocHours` = 该流水线任务 NPU 分配卡时：来自 `dwr_rd_efc_resource_npu_detail`，`SUM(assign_npu_second)/3600`，按 `job_start_time` 落窗（全窗口 startDate~endDate）；
- `runNum` = 运行次数：`dwr_rd_efc_resource_npu_detail` 按流水线 `COUNT(DISTINCT pipeline_run_id)`；
- 排序白名单：`queueP90 / allocHours / runNum / pipelineName`。

### 4.8 流水线运行明细（三级下钻，复用 /common/detail）

> 点击「查看运行明细」→ 抽屉内切换为「流水线运行分析」面板：面包屑（项目效率 > 项目 > 流水线运行分析）+ 流水线运行明细表 + NPU 分配率/使用率分析图。分析图数据（任务连线 + 机器×小时 cells）由 4.8.1 的**单接口**一次返回，前端不再二次请求。

**`POST /common/detail`**，`category = ops-pipeline-run-detail`。

请求 `OpsPipelineRunDetailReq extends DetailReq`：

```json
{
  "category": "ops-pipeline-run-detail",
  "projectId": 100,
  "pipelineId": 123,
  "startDate": "2026-08-16",
  "endDate": "2026-08-16",
  "page": 1,
  "pageSize": 20,
  "sortField": "endTime",
  "sortRule": "DESC"
}
```

响应 `PageResult<OpsPipelineRunDetailResp>`，每条 = 一次运行（**列与高保真「流水线运行明细」表一一对应**）：

```json
{
  "runId": "86231", // 运行 ID（前端展示 #86231，取 pipeline_run_id）
  "platform": "codearts", // 平台（codearts/gitcode/github）
  "pipelineName": "pr-gate-ut",
  "endTime": "2026-08-12 15:42:34", // 运行结束时间（含秒）
  "queueMinutes": 18.6, // 资源排队时长(min)(测试任务)
  "npuHours": 6.2, // NPU 消耗(卡时)
  "status": "success"
}
```

口径与数据源（**npu_detail 单表驱动，无连表，覆盖 codearts/gitcode/github 三平台**）：

- 运行列表与指标（runId/platform/pipelineName/status/endTime/queueMinutes/npuHours）均来自 `dwr_rd_efc_resource_npu_detail`（`pipeline_id` + 运行起始 `MIN(job_start_time)` 落窗）；
- `runId` = `pipeline_run_id`（按 `pipeline_run_id` 分组）；
- `platform` = `MAX(platform)`；`pipelineName` = `MAX(pipeline_name)`；`status` = `MAX(pipeline_status)`（npu_detail 已冗余流水线名与状态，全平台可直接展示）；
- `endTime` = 运行结束时间 = `MAX(job_end_time)`，格式 `yyyy-MM-dd HH:mm:ss`（含秒，原样返回不去秒）；
- `queueMinutes` = 该运行 **DT 测试任务**排队时长合计：`npu_detail` 按 `pipeline_run_id/job_id` 去重后 `SUM(job_pending_duration) / 60`；
- `npuHours` = `SUM(assign_npu_second)/3600`（该运行全部任务切片合计）；
- 排序白名单：`endTime / queueMinutes / npuHours / runId / pipelineName / status`（均来自 npu_detail 聚合结果，SQL 内排序分页）。

### 4.8.1 流水线运行分析（「查看运行明细」面板同屏数据）

> 高保真中「查看运行明细」面板 = **运行明细表 + NPU 分配率分析热力 + NPU 使用率分析热力**，三者同屏。分析图数据（机器×小时 cells + 任务排队/运行连线 + 每任务各时间段状态）由**单个接口一次返回**，前端不再二次调用 heatmap。

**`POST /resource-operation/run-analysis`**（新增，独立 REST 接口，不进 `/common/detail`）。

请求 `OpsPipelineRunAnalysisReq`（**只传一次流水线运行 ID**，后端按该次运行的时间窗口分析，无需时间范围参数）：

```json
{
  "runId": "86231"
}
```

**时间窗口（labels）**：由该次运行起止时间（来自任务切片表 `dwr_rd_efc_resource_npu_detail`：运行起 = `MIN(job_start_time)`、运行止 = `MAX(job_end_time)`，覆盖 codearts/gitcode/github）对齐整点生成——起始向下取整点、结束非整点向上进位（含边界整点）。例：任务运行 `2026-08-20 16:34:49 - 2026-08-20 17:34:49` → `labels` = `2026-08-20 16:00` / `17:00` / `18:00`；结束整点 `17:00:00` → `16:00` / `17:00`。运行未结束时结束按当前时间处理。

响应 `OpsPipelineRunAnalysisResp`（复合结构，一次返回分配率/使用率热力，**分配与使用数据拆分**；任务连线 jobs 按 `serverIp` 挂载到对应机器单元格下，每个任务带 `states[]` 标识各时间段状态）：

```json
{
  "labels": ["2026-08-20 16:00", "2026-08-20 17:00", "2026-08-20 18:00"],
  "allocServers": [
    {
      "ip": "10.10.5.21",
      "pool": "昇腾统一资源池-CICD",
      "gen": "A5",
      "values": [12.5, 88.3, 0.0], // 逐小时分配率(%)，与 labels 对齐，缺失补 0
      "jobs": [
        {
          "runId": "86231", // pipeline_run_id，用于关联 4.8 明细表选中行
          "taskName": "unit_test", // job_name
          "queueStart": "16:34", // 排队开始 = job_start_time（创建/申请时间）
          "queueEnd": "16:49", // 排队结束 = job_run_start_time（开始运行时间）
          "runEnd": "17:34", // 运行结束 = job_end_time
          "queueMinutes": 15.0, // job_pending_duration / 60
          "npuHours": 6.2, // SUM(assign_npu_second)/3600
          "serverIp": "10.10.5.21", // 分配机器（切片 server_ip，与所在 ServerCell 的 ip 一致）
          "states": ["QUEUING", "RUNNING", "NONE"] // 各时间段状态，与 labels 对齐
        }
      ]
    }
  ],
  "usageServers": [
    {
      "ip": "10.10.5.21",
      "pool": "昇腾统一资源池-CICD",
      "gen": "A5",
      "values": [9.2, 61.0, 0.0] // 逐小时使用率(%)
    }
  ]
}
```

> 注：`usageServers` 与 `allocServers` 同构，各自携带该机器 `jobs`（同一份任务连线在分配/使用两份里各出现一次）。

口径与数据源：

- 运行时间窗与任务连线（`jobs` + `states[]`）：**`dwr_rd_efc_resource_npu_detail` 任务×小时切片**，按 `pipeline_run_id` 一次取该运行全部任务切片；**时间窗口 = `MIN(job_start_time)`（运行起）/ `MAX(job_end_time)`（运行止），不再依赖运行事实表 `dwr_rd_efc_pipeline_run_fact`**（该表仅 codearts 且到 npu_detail 有过滤丢失，npu_detail 覆盖 codearts/gitcode/github）；按 job 分组聚合：job 级字段（`job_name`/`job_start_time`/`job_run_start_time`/`job_end_time`/`job_pending_duration`）取首行，`npuHours` = 切片 `assign_npu_second` 求和 / 3600；每任务逐整点段判定状态（与 `labels` 对齐）：该段切片排队秒（`job_current_slot_pending_seconds`）> 0 → `QUEUING`，否则运行秒（`job_current_slot_running_seconds`）> 0 → `RUNNING`，否则 `NONE`；
- `allocServers` / `usageServers`（机器×小时 cells，**分配与使用拆分**）：**`dm_rd_efc_server_resource_hour` 宽表**，**仅本次运行涉及机器**（jobs 按 `serverIp` 分组后得到机器集合）+ 运行窗口，复用 4.3 heatmap 口径（`resourcePoolId` 不传），`labels` 与各机器 `values[]` 逐小时对齐、缺失小时补 0；`allocServers[].values` 为分配率、`usageServers[].values` 为使用率，机器元数据（ip/pool/gen）两份各自携带；
- `queueStart` = `job_start_time`（创建/申请时间），`queueEnd` = `job_run_start_time`（开始运行时间），`runEnd` = `job_end_time`；**排队时段 = [queueStart, queueEnd)，运行时段 = [queueEnd, runEnd)**；前端转 HH:MM 后按窗口 1 小时/格定位连线；
- `queueMinutes` = `job_pending_duration / 60`（数据方按排队时段计算，与时间差一致）；
- `taskName` = `job_name`，`serverIp` = `server_ip`（切片自带）；
- Service 层：先取运行时间窗（npu_detail `MIN(job_start_time)`/`MAX(job_end_time)`）算整点窗口，再取切片组装 jobs/states 并按 `serverIp` 分组，最后查宽表热力（仅涉及机器 + 窗口），一次返回。

---

## 5. 后端实现设计

### 5.1 新增文件清单

| 层                         | 文件                                                                                                                                              | 说明                                                                                                                                             |
| -------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| api/controller             | `ResourceOperationController.java`                                                                                                                | `@RequestMapping("/resource-operation")`，4 个接口                                                                                               |
| api/request/ops            | `ResourceOperationSummaryReq.java` / `ResourceOperationTrendReq.java` / `ResourceOperationHeatmapReq.java` / `OpsPipelineRunAnalysisReq.java`     | summary/trend/heatmap 继承 `TimeReq`（heatmap 另含 `resourcePoolId`）；run-analysis 独立，仅含 `runId`                                           |
| api/request/common/detail  | `OpsResourcePoolDetailDetailReq.java`                                                                                                             | 继承 `DetailReq`，含 `projectId` + 排序字段                                                                                                      |
| api/request/common/detail  | `OpsProjectResourceEfficiencyReq.java` / `OpsPipelineResourceEfficiencyReq.java` / `OpsPipelineRunDetailReq.java`                                 | 下钻请求，继承 `DetailReq`（projectName / pipelineType / pipelineId）                                                                            |
| api/response/ops           | `ResourceOperationSummaryResp.java` / `ResourceOperationTrendResp.java` / `ResourceOperationHeatmapResp.java` / `OpsPipelineRunAnalysisResp.java` | 响应 DTO（run-analysis 为复合结构，见 4.8.1）                                                                                                    |
| api/response/common/detail | `OpsResourcePoolDetailDetailResp.java`                                                                                                            | 含嵌套 `MachineDetail`                                                                                                                           |
| api/response/common/detail | `OpsProjectResourceEfficiencyResp.java` / `OpsPipelineResourceEfficiencyResp.java` / `OpsPipelineRunDetailResp.java`                              | 下钻响应 DTO                                                                                                                                     |
| app/service/ops            | `ResourceOperationService.java`                                                                                                                   | KPI/趋势/热力图/运行分析合并逻辑                                                                                                                 |
| domain/service/repo/impl   | `OpsResourcePoolDetailDetailService.java`                                                                                                         | 实现 `DetailService`，复用 `CommonController`                                                                                                    |
| domain/service/repo/impl   | `OpsProjectResourceEfficiencyDetailService.java` / `OpsPipelineResourceEfficiencyDetailService.java` / `OpsPipelineRunDetailDetailService.java`   | 下钻 `DetailService`（由 `RepoDetailFactory` 自动注册）                                                                                          |
| domain/mapper/ops          | `ResourceOperationMapper.java`                                                                                                                    | **宽表单源** Mapper（Summary 静态+动态 / Trend / Heatmap / PoolDetail / 机器明细，全部单表聚合，维度在行内）                                     |
| domain/mapper/ops          | `ResourceEfficiencyMapper.java`                                                                                                                   | 下钻链路 Mapper（运行事实表 + 任务切片 npu_detail）                                                                                              |
| resources/mapper           | `ResourceOperationMapper.xml` / `ResourceEfficiencyMapper.xml`                                                                                    | SQL                                                                                                                                              |
| 修改                       | `DetailCommonEnum.java`                                                                                                                           | 新增 4 个 category：`OPS_RESOURCE_POOL_DETAIL`、`OPS_PROJECT_RESOURCE_EFFICIENCY`、`OPS_PIPELINE_RESOURCE_EFFICIENCY`、`OPS_PIPELINE_RUN_DETAIL` |
| 修改                       | `DetailReq.java`                                                                                                                                  | `@JsonSubTypes` 注册 4 个新类型（name 与 enum 一致）                                                                                             |

### 5.2 Mapper SQL 公共骨架

所有查询共用同一套项目隔离 CTE；**全部指标直接查宽表行内列，无任何维度 JOIN**：

```sql
-- 项目资源池过滤（唯一公共 CTE）
project_pool AS (
    SELECT resource_pool_id
    FROM dwi_rd_efc_project_resource_pool_relation
    <if test="req.projectId != null">
        WHERE project_id = #{req.projectId}
    </if>
)
-- 主查询直接以宽表为源：dimension 列（resource_pool_name / generation / location / total_npu_num）都在行内
-- FROM dm_rd_efc_server_resource_hour h
-- <if test="req.projectId != null"> WHERE h.resource_pool_id IN (SELECT resource_pool_id FROM project_pool) </if>
```

> 注意：宽表列名已是下划线风格（`resource_pool_name`），无需驼峰别名；一机多池（同一 `server_ip` 对应多 `resource_pool_id` 行）时，按 `resource_pool_id` 聚合是准确的，仅按 `server_ip` 聚合（热力图不传 `resourcePoolId`）时各池独立成行、不叠加。

### 5.3 Summary SQL（示例）

```sql
-- 静态指标：资源池总量 / 资源总量（宽表单源，先 DISTINCT 机器避免按小时重复）
-- 先取时间范围内出现的机器集合（每机器一行，保留 location/generation/total_npu_num 冗余列）
WITH machine_snapshot AS (
    SELECT
        resource_pool_id,
        server_ip,
        location,
        generation,
        total_npu_num
    FROM dm_rd_efc_server_resource_hour
    WHERE statistic_period BETWEEN #{req.startTime} AND #{req.endTime}
    <if test="req.projectId != null">
        AND resource_pool_id IN (SELECT resource_pool_id FROM project_pool)
    </if>
    GROUP BY resource_pool_id, server_ip, location, generation, total_npu_num
)
SELECT
    location,
    generation,
    COUNT(DISTINCT resource_pool_id) AS pool_total,
    SUM(IFNULL(total_npu_num, 0)) AS npu_num
FROM machine_snapshot
GROUP BY location, generation;

-- 动态指标：分配率 / 使用率（宽表直查，按小时 SUM 卡时，无维度 JOIN）
SELECT
    h.location,
    SUM(IFNULL(h.assign_npu_hours, 0)) AS assign_hours,
    SUM(IFNULL(h.used_npu_hours, 0))  AS used_hours,
    SUM(IFNULL(h.total_npu_hours, 0)) AS total_hours
FROM dm_rd_efc_server_resource_hour h
WHERE h.statistic_period BETWEEN #{req.startTime} AND #{req.endTime}
<if test="req.projectId != null">
    AND h.resource_pool_id IN (SELECT resource_pool_id FROM project_pool)
</if>
GROUP BY h.location;
```

Service 中计算 `allocRate = assign_hours / NULLIF(total_hours, 0)`，`usageRate = used_hours / NULLIF(total_hours, 0)`，用 `NumberUtil.truncateRate` 处理。

### 5.4 趋势/热力图组装逻辑

- 趋势：Service 按 `labels`（起始日 00:00 至结束日 23:00，逐小时）生成刻度；Mapper 返回 `(statistic_period, group_name, alloc, usage)` 行；Service 映射为「分组 → 定长数组」（缺失小时补 `0`）。
- 热力图：Mapper 返回 `(server_ip, statistic_period, pool, gen, alloc, usage)` 行；Service 按 `server_ip` 组装 `alloc[]/usage[]` 数组，附 `pool/gen` 元信息。

### 5.5 参数校验

- `startDate/endDate` 必填；`startDate > endDate` 抛 `IllegalArgumentException`；
- 跨度 > 7 天抛 `IllegalArgumentException`（与需求「不允许超过 7 天」一致）；
- `dim` 仅接受 `pool/gen`，非法值回退 `pool`；
- 下钻排序字段走 `SortFieldValidator` 白名单。

### 5.6 错误处理与空数据

- 复用全局 `@ControllerAdvice` 异常处理，返回 `Result.fail`；
- 无数据时返回空结构（`poolTotal` 全 0、`arrays` 全 0、`servers` 空数组），不报错。

---

## 6. 影响范围

| 影响项   | 说明                                                                                      |
| -------- | ----------------------------------------------------------------------------------------- |
| 新增表   | 无，数据源复用 `dm_rd_efc_server_resource_hour` 宽表                                      |
| 新增接口 | `POST /resource-operation/summary                                                         | trend | heatmap | run-analysis`（新增 controller） |
| 复用接口 | `POST /common/detail`（新增 category）、`POST /common/refresh-time`（新增 module 配置行） |
| 修改文件 | `DetailCommonEnum.java`、`DetailReq.java`（均为增量）                                     |
| 现有接口 | 无影响，完全新增                                                                          |
| 前端     | ops-web 新增资源运营看板页面，对接上述接口                                                |

### 6.1 依赖与风险

| 风险/依赖                  | 说明                                                                                                                                                                                                                                                            | 缓解                                                                                                                                         |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 源数据未落库               | 看板依赖外部 DS 清洗工作流产出的宽表（`dm_rd_efc_server_resource_hour`）与任务切片（`dwr_rd_efc_resource_npu_detail`），openlibing-ops 当前无引用                                                                                                               | 实施步骤 1 先验证数据可用性；无数据时接口返回空结构不报错                                                                                    |
| `total_npu_num` 冗余一致性 | 宽表每小时每行冗余 `total_npu_num`，直接 SUM 会按小时重复累加卡数                                                                                                                                                                                               | 静态卡数统计**先 `DISTINCT (resource_pool_id, server_ip)` 再 SUM**（见 5.3 machine_snapshot CTE）；动态率值按小时 SUM 卡时不受影响           |
| 一机多池展示语义           | 同一 `server_ip` 归属多池时宽表有多个 `(resource_pool_id, server_ip)` 行                                                                                                                                                                                        | 按 `resource_pool_id` 聚合精确无误；仅按 `server_ip` 聚合（热力图不传 `resourcePoolId`）时各池独立成行，前端按 `resourcePoolId` 过滤即可收敛 |
| `job_run_start_time` 口径  | 4.8.1 排队结束点取 `job_run_start_time`；已与数据方确认语义：`job_start_time`=创建/申请时间、`job_run_start_time`=开始运行时间、`job_end_time`=运行结束时间，**排队时段 = [job_start_time, job_run_start_time)，运行时段 = [job_run_start_time, job_end_time)** | job 级时长字段取任务切片首行（勿把切片秒数当总量），切片秒数仅用于判定各整点段排队/运行状态                                                  |
| 任务状态判定数据源         | 4.8.1 任务连线与 states[] 直接取 `dwr_rd_efc_resource_npu_detail` 任务×小时切片（按 `pipeline_run_id`），不再按 platform 路由平台事实表；切片自带 `platform` 供问题定位                                                                                         | 切片排队秒/运行秒分别聚合到整点段判定 QUEUING/RUNNING，无则 NONE；宽表热力仅查本次运行涉及机器 + 窗口，控制返回量                            |
| 分组数不可控               | 趋势图按 `resource_pool_name`/`generation` 分组，服务器规模大时曲线条数多                                                                                                                                                                                       | 后端不做截断（看板全量展示语义），前端图例支持点击隐藏；后续可加分组 topN 演进                                                               |

---

## 7. 测试计划

| 类型     | 用例                                                                                                                                             |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------------------ |
| 参数校验 | 跨度 > 7 天报错；startDate > endDate 报错；dim 非法回退默认                                                                                      |
| Summary  | 按 location 的资源池数/卡数统计正确（DISTINCT 机器后再 SUM 卡数，不按小时重复）；分配率/使用率分子分母先聚合再相除；除零（total=0）返回 0 不报错 |
| Trend    | 小时刻度对齐（1 天 24 点、7 天 168 点）；缺失小时补 0；pool/gen 两维度分组正确                                                                   |
| Heatmap  | 单机单小时 alloc/usage 正确；多天数组长度与 labels 一致                                                                                          |
| 下钻     | 分页总数正确；项目 chips 去重；机器明细按 IP 聚合；排序白名单生效                                                                                |
| 复用链路 | `/common/detail` 按 category 正确路由到新 DetailService                                                                                          |

---

## 8. 实施步骤

| 步骤 | 内容                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1    | 验证源表数据可用：`dm_rd_efc_server_resource_hour` 有 assign/used/total 且小时整点、维度字段（pool/gen/location/total_npu_num/machine_id）完整、逐台逐时全量写入；`dwr_rd_efc_resource_npu_detail` 任务×小时切片可查询且含 `pipeline_run_id`/`server_ip`/切片排队与运行秒数（4.8.1 直接依赖）；核对 `job_run_start_time` 语义（创建/申请 → 开始运行 → 结束，排队 = [job_start_time, job_run_start_time)、运行 = [job_run_start_time, job_end_time)） |
| 2    | 新增 Request/Response DTO                                                                                                                                                                                                                                                                                                                                                                                                                            |
| 3    | 新增 `ResourceOperationMapper` + XML（Summary 静态+动态 / Trend / Heatmap / PoolDetail / 机器明细，宽表单源）                                                                                                                                                                                                                                                                                                                                        |
| 4    | 新增 `ResourceOperationService`，实现 KPI/趋势/热力图组装与校验                                                                                                                                                                                                                                                                                                                                                                                      |
| 5    | 注册 `DetailCommonEnum`（`OPS_RESOURCE_POOL_DETAIL` / `OPS_PROJECT_RESOURCE_EFFICIENCY` / `OPS_PIPELINE_RESOURCE_EFFICIENCY` / `OPS_PIPELINE_RUN_DETAIL`）+ `DetailReq` `@JsonSubTypes`，新增对应 4 个 `DetailService`                                                                                                                                                                                                                               |
| 6    | 新增 `ResourceOperationController`（summary / trend / heatmap / run-analysis 4 个接口）                                                                                                                                                                                                                                                                                                                                                              |
| 7    | 在 `tbl_ops_module_ds_workflow_relation` 配置刷新时间 module                                                                                                                                                                                                                                                                                                                                                                                         |
| 8    | 补充 UT（见测试计划），联调高保真页面（含「查看运行明细」面板）                                                                                                                                                                                                                                                                                                                                                                                      |
