# PR信息获取数据源切换 — 技术设计

## 方案概述

数据采集从 xxl-job 单体任务切换为 dolphinscheduler 编排 + seatunnel 采集的分离架构，openlibing-ops 后端适配新增的两张数据表。

## 数据架构变更

### 采集链路对比

```
旧方案:
  xxl-job 定时触发 → 直接调用 Git API → 写入 sdi 层 → 聚合到 dwi/dm 层

新方案:
  dolphinscheduler 编排 →
    ├── seatunnel 采集 → raw 层
    ├── 清洗任务 → sdi 层
    └── 聚合任务 → dwi/dm 层
```

### 新增表 DDL

#### dwi_rd_efc_pr_workflow_run

```sql
CREATE TABLE `dwi_rd_efc_pr_workflow_run` (
   `repo_url` varchar(512) NULL COMMENT '仓库链接',
   `number` int NULL COMMENT 'pr编号',
   `commit_sha` varchar(64) NULL COMMENT '提交sha',
   `workflow_run_id` bigint NULL COMMENT '工作流id',
   `commit_time` datetime NULL COMMENT '提交时间',
   `workflow_name` text NULL COMMENT '工作流名称',
   `conclusion` varchar(50) NULL COMMENT '工作流执行结果',
   `run_started_time` datetime NULL COMMENT '工作流运行开始时间',
   `run_end_time` datetime NULL COMMENT '工作流运行结束时间',
   `duration` int NULL COMMENT '工作流运行时间',
   `max_duration` int NULL COMMENT '工作流运行最大时间',
   `access_conclusion` varchar(32) NULL COMMENT '门禁结论'
) ENGINE=OLAP
UNIQUE KEY(`repo_url`, `number`, `commit_sha`, `workflow_run_id`)
COMMENT 'pr的workflow运行记录表'
DISTRIBUTED BY HASH(`repo_url`) BUCKETS 10
```

#### sdi_rd_efc_pipeline_run_pr_relation_codearts

```sql
CREATE TABLE `sdi_rd_efc_pipeline_run_pr_relation_codearts` (
   `project_id` varchar(32) NULL COMMENT '华为云项目id',
   `pipeline_id` varchar(32) NULL COMMENT '流水线 ID',
   `pipeline_run_id` varchar(32) NULL COMMENT '流水线运行实例 ID',
   `git_url` varchar(512) NULL COMMENT 'Git 仓库地址',
   `pipeline_name` varchar(512) NULL COMMENT '流水线名称',
   `git_type` varchar(32) NULL COMMENT 'Git 平台类型',
   `pr_id` varchar(32) NULL COMMENT 'MR 合入请求 ID'
) ENGINE=OLAP
UNIQUE KEY(`project_id`, `pipeline_id`, `pipeline_run_id`, `git_url`)
COMMENT '流水线与PR关联关系表-从codearts解析'
DISTRIBUTED BY HASH(`pipeline_id`) BUCKETS 8
```

## 后端代码变更

### 接口变更

| 变更项 | 旧 | 新 |
|--------|----|----|
| URL | `GET /pipeline/info/{prId}` | `GET /pipeline/info` |
| 参数 | `@PathVariable Long prId` | `@RequestParam String repoUrl` + `@RequestParam Integer number` |
| PipelineHandle 签名 | `queryPipelineInfo(Long prId, String pipelineStatus)` | `queryPipelineInfo(String repoUrl, Integer number, String pipelineStatus)` |

### 新增类

| 类 | 说明 |
|----|------|
| `DwiRdEfcPrWorkflowRun` | `dwi_rd_efc_pr_workflow_run` Entity |
| `DwiRdEfcPrWorkflowRunMapper` | Mapper |
| `DwiRdEfcPrWorkflowRunService` | Service 接口 |
| `DwiRdEfcPrWorkflowRunServiceImpl` | Service 实现 |
| `SdiRdEfcPipelineRunPrRelationCodearts` | `sdi_rd_efc_pipeline_run_pr_relation_codearts` Entity |
| `SdiRdEfcPipelineRunPrRelationCodeartsMapper` | Mapper |
| `SdiRdEfcPipelineRunPrRelationCodeartsService` | Service 接口 |
| `SdiRdEfcPipelineRunPrRelationCodeartsServiceImpl` | Service 实现 |
| `WorkflowNewHandleImpl` | 新 workflow Handle，type="workflow" |

### 修改类

| 类 | 变更说明 |
|----|----------|
| `PipelineHandle` | 接口方法签名变更 |
| `PipelineController` | URL 和参数变更 |
| `PipelineHandleImpl` | PR 绑定查询从 `SdiPrPipelineRelation` 切换到 `SdiRdEfcPipelineRunPrRelationCodearts` |
| `WorkflowHandleImpl` | type 从 `"workflow"` 改为 `"workflow_old"` |

### 数据查询映射

**PipelineHandleImpl** 新查询逻辑：
```
repoUrl + number → sdi_rd_efc_pipeline_run_pr_relation_codearts (git_url + pr_id)
  → pipeline_run_id → dwr_rd_efc_pipeline_run_fact → 组装 PipelineRunInfoResp
```

**WorkflowNewHandleImpl** 新查询逻辑：
```
repoUrl + number → dwi_rd_efc_pr_workflow_run (repo_url + number)
  → 按 commit_sha 分组 → 组装 WorkflowInfoResp
```

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `domain/model/pipeline/DwiRdEfcPrWorkflowRun.java` | 新增 | Entity |
| `domain/mapper/pipeline/DwiRdEfcPrWorkflowRunMapper.java` | 新增 | Mapper |
| `domain/service/pipeline/DwiRdEfcPrWorkflowRunService.java` | 新增 | Service 接口 |
| `domain/service/pipeline/impl/DwiRdEfcPrWorkflowRunServiceImpl.java` | 新增 | Service 实现 |
| `domain/model/pipeline/SdiRdEfcPipelineRunPrRelationCodearts.java` | 新增 | Entity |
| `domain/mapper/pipeline/SdiRdEfcPipelineRunPrRelationCodeartsMapper.java` | 新增 | Mapper |
| `domain/service/pipeline/SdiRdEfcPipelineRunPrRelationCodeartsService.java` | 新增 | Service 接口 |
| `domain/service/pipeline/impl/SdiRdEfcPipelineRunPrRelationCodeartsServiceImpl.java` | 新增 | Service 实现 |
| `app/service/pipeline/impl/WorkflowNewHandleImpl.java` | 新增 | 新 workflow Handle |
| `app/service/pipeline/PipelineHandle.java` | 修改 | 接口签名 |
| `api/controller/PipelineController.java` | 修改 | URL + 参数 |
| `app/service/pipeline/impl/PipelineHandleImpl.java` | 修改 | 切换查询表 |
| `app/service/pipeline/impl/WorkflowHandleImpl.java` | 修改 | type 改为 workflow_old |

## 风险 & 缓解

| 风险 | 缓解措施 |
|------|----------|
| 接口参数变更导致调用方不兼容 | 前端同步更新 repoUrl + number 参数 |
| 新表数据未就绪时查询为空 | 旧 workflow_old 保留，可回退 |
| CodeArts pr_id 为 String 类型，与旧 Long 类型不兼容 | PipelineHandleImpl 中 pr_id 以 String 匹配 |

## 跨仓影响

无。本次变更仅涉及 openlibing-ops 单仓。
