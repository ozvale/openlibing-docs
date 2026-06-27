# 看板数据支持小时级刷新并支持页面展示刷新时间 — 技术设计

## 1. 需求概述

openlibing-ops 看板页面的数据由 DolphinScheduler 定时调度 workflow 采集和清洗，数据刷新粒度从原来的天级提升到小时级。前端各模块需要展示当前数据的刷新时间，让用户直观了解数据的时效性。

## 2. 方案选型

### 2.1 方案对比

| 方案 | 描述 | 评价 |
|------|------|------|
| **A: 配置表 + 查 DS MySQL（推荐）** | 新建配置表存 module→workflow_code 映射，后端根据 module 查 DS MySQL 的 workflow_instance 表获取最新执行时间 | ✅ 数据准确、侵入性小、维护简单 |
| B: 直接调 DS REST API | 后端通过 DS Open API 查询 workflow 执行记录 | ❌ 增加网络依赖和鉴权复杂度，openlibing-ops 当前无 DS 依赖 |
| C: 查 Doris 已有表时间字段 | 从 Doris 各表的数据时间字段推断刷新时间 | ❌ 各表时间字段含义不统一，无法精确对应 DS workflow 执行时间 |
| D: 在 Doris 中建配置表 | 将配置表建在 Doris 中 | ❌ 配置表数据量极小、变更频繁，不适合 OLAP 引擎 |

### 2.2 推荐方案：方案 A

```
┌──────────────┐     module      ┌──────────────────┐   workflow_code   ┌──────────────────────┐
│  前端页面      │ ──────────→    │  openlibing-ops   │ ──────────────→  │  DS MySQL             │
│  (ops-web)    │    ← 刷新时间   │  (Spring Boot)    │                  │  (只读数据源)           │
└──────────────┘                 │                   │                  │                      │
                                 │  ① 查配置表获取    │                  │  t_ds_workflow_       │
                                 │     workflow_code  │                  │  definition           │
                                 │  ② 查 DS 实例表    │                  │                      │
                                 │     获取最新执行时间 │                  │  t_ds_workflow_       │
                                 └──────────────────┘                  │  instance             │
                                          │                            └──────────────────────┘
                                          │ 查询
                                          ▼
                                 ┌──────────────────┐
                                 │  MySQL 配置表      │
                                 │  (openlibing-ops  │
                                 │   主数据源)        │
                                 │  code_ops_module_ │
                                 │  refresh_config   │
                                 └──────────────────┘
```

## 3. 配置表设计

### 3.1 表结构

表名：`tbl_ops_module_ds_workflow_relation`

```sql
CREATE TABLE `tbl_ops_module_ds_workflow_relation` (
  `id`            BIGINT       NOT NULL AUTO_INCREMENT COMMENT '自增主键',
  `module`        VARCHAR(128) NOT NULL COMMENT '前端模块标识，如 pipeline_dashboard、repo_overview',
  `module_name`   VARCHAR(256) DEFAULT NULL COMMENT '模块中文名，用于展示和运维',
  `project_code`  BIGINT       NOT NULL COMMENT 'DS 项目编码（t_ds_project.code）',
  `workflow_code` BIGINT       NOT NULL COMMENT 'DS 工作流定义编码（t_ds_workflow_definition.code）',
  `description`   VARCHAR(512) DEFAULT NULL COMMENT '备注说明',
  `create_time`   DATETIME     NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `update_time`   DATETIME     DEFAULT NULL ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_module` (`module`),
  KEY `idx_workflow` (`project_code`, `workflow_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='ops 页面模块与 DS workflow 映射关系表';
```

### 3.2 设计说明

- `module`：前端传的标识，如 `pipeline_dashboard`、`repo_overview`、`resource_usage` 等
- 一个 module 对应一个 DS workflow（即一个数据刷新任务）
- 如果某个页面依赖多个 workflow 的数据，可以插入多条记录共用同一个 module，查询时取最晚的执行时间
- 表前缀 `tbl_ops_` 与现有 ops 业务表命名风格一致
- 表名 `tbl_ops_module_ds_workflow_relation` 明确表达"ops 模块与 DS workflow 的映射关系"

### 3.3 初始数据示例

```sql
INSERT INTO tbl_ops_module_ds_workflow_relation (module, module_name, project_code, workflow_code, description)
VALUES
('pipeline_dashboard', '流水线看板', 123456, 10001, '流水线数据采集与清洗'),
('repo_overview',     '仓库概览',   123456, 10002, '仓库数据采集与清洗'),
('resource_usage',    '资源消耗',   123456, 10003, '资源消耗数据采集'),
('pr_dashboard',      'PR 看板',    123456, 10004, 'PR 数据采集与清洗');
```

## 4. 后端实现

### 4.1 新增文件清单

| 层 | 文件 | 说明 |
|----|------|------|
| domain/model | `TblOpsModuleDsWorkflowRelation.java` | 配置表 Entity |
| domain/mapper | `TblOpsModuleDsWorkflowRelationMapper.java` | 配置表 Mapper（MyBatis-Plus） |
| domain/mapper | `DsWorkflowInstanceMapper.java` | DS 实例表 Mapper（指向 DS MySQL 数据源） |
| api/request | `ModuleRefreshTimeReq.java` | 请求体 |
| api/response | `ModuleRefreshTimeResp.java` | 响应体 |
| app/service | `ModuleRefreshTimeService.java` | 核心查询 Service |
| api/controller | `ModuleRefreshTimeController.java` | 对外接口 |

### 4.2 接口定义

**接口：** `POST /module/refresh-time`

**请求体：**
```json
{
  "modules": ["pipeline_dashboard", "repo_overview"]
}
```

**响应体：**
```json
{
  "code": 200,
  "messageCn": "操作成功",
  "data": [
    {
      "module": "pipeline_dashboard",
      "refreshTime": "2026-06-17 10:30:00",
      "workflowName": "pipeline_data_collect",
      "state": "SUCCESS"
    },
    {
      "module": "repo_overview",
      "refreshTime": "2026-06-17 10:25:00",
      "workflowName": "repo_data_collect",
      "state": "SUCCESS"
    }
  ]
}
```

**接口风格说明：**
- 使用 `@PostMapping` + `@RequestBody`，与现有项目风格一致（参考 PipelineController、RepoController）
- 返回使用 `Result.success()` 包装，与现有统一响应格式一致
- 支持批量查询，前端可一次传入当前页面所有模块

### 4.3 核心查询逻辑

```
1. 接收前端 modules 列表
2. 查 code_ops_module_refresh_config 获取对应的 (project_code, workflow_code) 列表
3. 对每个 workflow_code，查 DS MySQL 的 t_ds_workflow_instance：
   SELECT end_time, state
   FROM t_ds_workflow_instance
   WHERE workflow_definition_code = ?
     AND state = 7  -- 只取成功状态的实例
   ORDER BY end_time DESC
   LIMIT 1
4. 组装结果返回
```

**优化点：**
- 批量查询：使用 `WHERE workflow_definition_code IN (...)` 一次查出所有 workflow 的最新实例，减少 SQL 次数
- 刷新时间取 `end_time`（workflow 执行完成的时间），比 `start_time` 更合理
- 只取 `state = 7`（SUCCESS）的实例，避免展示失败任务的过时时间

### 4.4 DS MySQL 数据源

DS MySQL 数据源已在 Apollo 上配置，无需在本地 yaml 中处理。后端通过多数据源配置将 `DsWorkflowInstanceMapper` 指向 DS MySQL 即可。

涉及 DS 的两张核心表（只读）：

**`t_ds_workflow_definition`** — 工作流定义表

| 字段 | 类型 | 说明 |
|------|------|------|
| `code` | bigint | 工作流唯一编码（跨版本稳定） |
| `name` | varchar(255) | 工作流名称 |
| `project_code` | bigint | 所属项目编码 |

**`t_ds_workflow_instance`** — 工作流实例表

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | int | 自增主键 |
| `workflow_definition_code` | bigint | 关联的工作流定义编码 |
| `state` | tinyint | 状态（7=SUCCESS） |
| `start_time` | datetime | 开始时间 |
| `end_time` | datetime | 结束时间 |

## 5. 前端使用方式

前端在每个页面加载时（或定时刷新时），调用该接口获取当前页面各模块的刷新时间，展示在页面角落或表头附近。

```javascript
// 页面加载时
const modules = getCurrentPageModules()
const res = await fetch('/module/refresh-time', { modules })
res.data.forEach(item => {
  renderRefreshTime(item.module, item.refreshTime)
})
```

## 6. 影响范围

| 影响项 | 说明 |
|--------|------|
| 新增表 | `tbl_ops_module_ds_workflow_relation`（MySQL，openlibing-ops 主数据源） |
| 新增接口 | `POST /module/refresh-time` |
| 新增数据源 | DS MySQL（Apollo 已配置，仅新增 Mapper 指向） |
| 现有接口 | 无影响，完全新增 |
| 前端 | 需要新增刷新时间展示逻辑 |

## 7. 实施步骤

| 步骤 | 内容 |
|------|------|
| 1 | 在 MySQL 中建表 `tbl_ops_module_ds_workflow_relation` |
| 2 | 录入初始的 module → workflow_code 映射数据 |
| 3 | 新增 Entity：`TblOpsModuleDsWorkflowRelation` |
| 4 | 新增 Mapper：`TblOpsModuleDsWorkflowRelationMapper`（主数据源）、`DsWorkflowInstanceMapper`（DS 数据源） |
| 5 | 新增 Request/Response：`ModuleRefreshTimeReq`、`ModuleRefreshTimeResp` |
| 6 | 新增 Service：`ModuleRefreshTimeService` |
| 7 | 新增 Controller：`ModuleRefreshTimeController` |
| 8 | 前端对接接口，展示刷新时间 |
