# 测试报告采集 正式环境 DolphinScheduler 创建清单

> 关联设计：[design.md](design.md)（v3.1）
> 目标环境：DS 正式环境（prod，`https://1.95.67.5:12345/dolphinscheduler`）
> 触发前提：**测试环境全链路调通（采集+清洗+ops REST 消费）并经测试/PM 确认后**，才在生产测试
> 执行人：用户（DS 控制台手动创建）；Doris DDL 由 DBA 执行

---

## 0. 正式环境已核实事实（2026-09-10 实测，作为创建参照）

| 项 | 值 |
| --- | --- |
| 项目 | `openlibing`，projectCode = `169400948446944` |
| 被依赖编排 | `[workflow][raw->dwi]PR&workflow数据获取`（176230008422726），已有定时：cron `0 0 0,6-23,5 * * ? *`（小时 0、5~23 整点，1~4 点不跑） |
| SeaTunnel 任务部署 | `taskType=SEATUNNEL`、`workerGroup=default`、`environmentCode=169409665039072`（openlibing-prod）、`useCustom=true`、`deployMode=cluster`、`startupScript=seatunnel.sh`、`taskExecuteType=BATCH`、`failRetryTimes=0` |
| 项目参数（已存在） | `openlibing_doris_url` / `openlibing_doris_driver` / `openlibing_doris_username` / `openlibing_doris_password` / `OBS_AK` / `OBS_SK`（既有 SeaTunnel 任务「获取测试用例数据」已引用） |
| DEPENDENT 任务格式参照 | codearts 编排（169579299839168）内任务「PR&workflow数据获取」（176365918863712），见 4.2 |
| SUB_WORKFLOW 任务格式参照 | PR&workflow 编排（176230008422726）内各 SUB_WORKFLOW 任务，见 4.3 |
| 测试环境已验证工作流 | ①「测试报告原始数据采集-调试-codearts-20260909」（183798696421280，v4）、②「测试报告数据清洗-调试-codearts-20260909」（183813929879456，v3）——本清单 rawScript 以其为准，仅把窗口参数化 |

---

## 1. 前置条件（按序完成，缺一不可）

| # | 项 | 内容 | 执行方 | 核对点 |
| --- | --- | --- | --- | --- |
| 1.1 | Doris 正式库建表 | `dm_rd_efc_template_registry`（design 6.1）、`raw_test_report`（design 6.3，**含 `source_end_time` 列**）、`sdi_rd_efc_test_report_triton_model_performance`（design 6.4，**含 `source_end_time` 列**） | DBA | DDL 含 `source_end_time datetime`；sdi 表唯一键为五元组 |
| 1.2 | 模板登记 | INSERT `dm_rd_efc_template_registry`（design 7.5 登记清单），`pipeline_ids` 填实际流水线白名单（逗号分隔） | 开发 | `table_type='test_report'`、`status=1`；漏配 `pipeline_ids` 则采集不生效 |
| 1.3 | SeaTunnel 插件 jar | `TestReportReader`（`transform/readtestreport`）构建 → 上传 OBS 桶 → SeaTunnel 服务加载/重启（与测试环境验证版 v4 同版） | 开发 | 测试库 raw 采集已用该插件跑通后再上正式 |
| 1.4 | DS 参数 | 复用既有项目参数（0 节已核实存在）；**新增工作流全局参数 `${report_window_hours}=24`**（工作流①/② 各配一份） | 用户 | 不配则 rawScript 中 `${report_window_hours}` 无值 |

> 注意：正式环境**不要**给工作流①/② 单独设置定时（它们是被 SUB_WORKFLOW 调用的子工作流，仅编排设 cron）。

---

## 2. 创建工作流①「[job][raw->raw][openlibing]测试报告原始数据采集」

### 2.1 基本信息

| 配置项 | 值 |
| --- | --- |
| 项目 | openlibing（169400948446944） |
| 工作流名称 | `[job][raw->raw][openlibing]测试报告原始数据采集` |
| 描述 | 测试报告 OBS → raw_test_report（增量：状态完成+时间窗口+反查+重试时间比较） |
| 全局参数 | `report_window_hours = 24` |
| 租户/worker | tenantCode `dolphinscheduler`、workerGroup `default` |
| 定时 | **不设置**（子工作流，由编排触发） |

### 2.2 SeaTunnel 任务「测试报告原始数据采集」

| 配置项 | 值 |
| --- | --- |
| taskType | SEATUNNEL |
| workerGroup / environmentCode | default / `169409665039072`（openlibing-prod） |
| useCustom / deployMode / startupScript | true / cluster / seatunnel.sh |
| taskExecuteType / failRetryTimes | BATCH / 0 |
| rawScript | 见 2.3（基于测试环境 v4，窗口参数化） |

### 2.3 rawScript（正式版）

```hocon
# 工作流① 正式版：OBS → raw_test_report
# 增量判定：状态完成 + 时间窗口 + 反查 + 重试时间比较（source_end_time）
# 与测试环境验证版（v4）一致；仅反查/时间窗口由硬编码 24 改为 ${report_window_hours}
env {
  execution.parallelism = 1
  job.mode = "BATCH"
  checkpoint.interval = 30000
  checkpoint.timeout = 900000
}

source {
  Jdbc {
    plugin_output = "pending_pipeline"
    url = "${openlibing_doris_url}"
    driver = "${openlibing_doris_driver}"
    username = "${openlibing_doris_username}"
    password = "${openlibing_doris_password}"
    query = """
      /* 三平台 UNION：codearts / github / gitcode 各自映射三 ID + 起止时间 + repoUrl */
      /* 反查 raw_test_report：未落库 OR 源表 end_time > 已落库 source_end_time（重试判定） */
      SELECT 'codearts' AS platform,
             t.pipeline_id AS pipelineId, t.pipeline_run_id AS pipelineRunId,
             CONCAT(t.step_build_job_id, '_', REPLACE(t.step_daily_build_number, '.', '_')) AS jobId,
             t.git_url AS repoUrl,
             t.pipeline_start_time AS workflowStartTime, t.pipeline_end_time AS workflowEndTime
      FROM sdi_rd_efc_pipeline_run_clean_codearts t
      JOIN ( SELECT model_code, SPLIT_BY_STRING(pipeline_ids, ',') AS pids
             FROM dm_rd_efc_template_registry
             WHERE table_type = 'test_report' AND status = 1 AND pipeline_ids IS NOT NULL AND pipeline_ids <> ''
               AND model_code = 'triton_model_performance'
      ) cfg
      LEFT JOIN ( SELECT pipeline_id, pipeline_run_id, job_id,
                         MAX(source_end_time) AS max_source_end_time
                  FROM raw_test_report
                  WHERE create_time > NOW() - INTERVAL ${report_window_hours} HOUR
                  GROUP BY pipeline_id, pipeline_run_id, job_id
      ) d
        ON t.pipeline_id = d.pipeline_id AND t.pipeline_run_id = d.pipeline_run_id
       AND CONCAT(t.step_build_job_id, '_', REPLACE(t.step_daily_build_number, '.', '_')) = d.job_id
      WHERE (d.pipeline_id IS NULL OR t.pipeline_end_time > d.max_source_end_time)
        AND ARRAY_CONTAINS(cfg.pids, t.pipeline_id)
        AND t.pipeline_start_time > NOW() - INTERVAL ${report_window_hours} HOUR
        AND t.pipeline_status = 'COMPLETED'
        AND LOWER(t.job_name) LIKE 'test%'

      UNION ALL

      /* GitHub：workflow 级数字 ID；job 目录 = {workflow_id}/{run_id}/{workflow_job_id} */
      SELECT 'github' AS platform,
             CAST(r.workflow_id AS STRING) AS pipelineId,
             CAST(j.workflow_run_id AS STRING) AS pipelineRunId,
             CAST(j.workflow_job_id AS STRING) AS jobId,
             j.repo_url AS repoUrl,
             r.run_started_at AS workflowStartTime, r.updated_at AS workflowEndTime
      FROM sdi_rd_efc_workflow_run_job_github j
      LEFT JOIN sdi_rd_efc_workflow_run_raw_github r ON j.workflow_run_id = r.run_id
      JOIN ( SELECT model_code, SPLIT_BY_STRING(pipeline_ids, ',') AS pids
             FROM dm_rd_efc_template_registry
             WHERE table_type = 'test_report' AND status = 1 AND pipeline_ids IS NOT NULL AND pipeline_ids <> ''
               AND model_code = 'triton_model_performance'
      ) cfg
      LEFT JOIN ( SELECT pipeline_id, pipeline_run_id, job_id,
                         MAX(source_end_time) AS max_source_end_time
                  FROM raw_test_report
                  WHERE create_time > NOW() - INTERVAL ${report_window_hours} HOUR
                  GROUP BY pipeline_id, pipeline_run_id, job_id
      ) d
        ON CAST(r.workflow_id AS STRING) = d.pipeline_id
       AND CAST(j.workflow_run_id AS STRING) = d.pipeline_run_id
       AND CAST(j.workflow_job_id AS STRING) = d.job_id
      WHERE (d.pipeline_id IS NULL OR r.updated_at > d.max_source_end_time)
        AND ARRAY_CONTAINS(cfg.pids, CAST(r.workflow_id AS STRING))
        AND r.run_started_at > NOW() - INTERVAL ${report_window_hours} HOUR
        AND j.status = 'completed'
        AND LOWER(j.job_name) LIKE 'test%'

      UNION ALL

      /* GitCode：hex ID；job 目录 = {workflow_id}/{workflow_run_id}/{job_id} */
      SELECT 'gitcode' AS platform,
             t.workflow_id AS pipelineId, t.workflow_run_id AS pipelineRunId,
             t.job_id AS jobId,
             t.repo_url AS repoUrl,
             t.start_time AS workflowStartTime, t.end_time AS workflowEndTime
      FROM sdi_rd_efc_workflow_run_raw_gitcode t
      JOIN ( SELECT model_code, SPLIT_BY_STRING(pipeline_ids, ',') AS pids
             FROM dm_rd_efc_template_registry
             WHERE table_type = 'test_report' AND status = 1 AND pipeline_ids IS NOT NULL AND pipeline_ids <> ''
               AND model_code = 'triton_model_performance'
      ) cfg
      LEFT JOIN ( SELECT pipeline_id, pipeline_run_id, job_id,
                         MAX(source_end_time) AS max_source_end_time
                  FROM raw_test_report
                  WHERE create_time > NOW() - INTERVAL ${report_window_hours} HOUR
                  GROUP BY pipeline_id, pipeline_run_id, job_id
      ) d
        ON t.workflow_id = d.pipeline_id AND t.workflow_run_id = d.pipeline_run_id
       AND t.job_id = d.job_id
      WHERE (d.pipeline_id IS NULL OR t.end_time > d.max_source_end_time)
        AND ARRAY_CONTAINS(cfg.pids, t.workflow_id)
        AND t.start_time > NOW() - INTERVAL ${report_window_hours} HOUR
        AND t.status = 'COMPLETED'
        AND LOWER(t.job_name) LIKE 'test%'
    """
  }
}

transform {
  TestReportReader {
    plugin_input = ["pending_pipeline"]
    plugin_output = "raw_report_rows"
    ak = "${OBS_AK}"
    sk = "${OBS_SK}"
    endPoint = "obs.cn-southwest-2.myhuaweicloud.com"
    bucketName = "op-case-result"
    prefix = "testcase-metadata"
    templateCode = "triton-model-performance"
    pipelineIdField = "pipelineId"
    pipelineRunIdField = "pipelineRunId"
    jobIdField = "jobId"
    sourceEndTimeField = "workflowEndTime"
    outputFieldName = "RawJson"
  }
}

sink {
  Jdbc {
    plugin_input = ["raw_report_rows"]
    url = "${openlibing_doris_url}"
    driver = "${openlibing_doris_driver}"
    username = "${openlibing_doris_username}"
    password = "${openlibing_doris_password}"
    query = """
      INSERT INTO raw_test_report (
        pipeline_id, pipeline_run_id, job_id, report_file_name, model_code, data_json,
        source_end_time, create_time
      ) VALUES (?, ?, ?, ?, 'triton_model_performance', ?, ?, NOW());
    """
    auto_commit = true
    batch_size = 100
  }
}
```

---

## 3. 创建工作流②「[job][raw->sdi][openlibing]测试报告数据清洗」

### 3.1 基本信息

| 配置项 | 值 |
| --- | --- |
| 项目 | openlibing（169400948446944） |
| 工作流名称 | `[job][raw->sdi][openlibing]测试报告数据清洗` |
| 描述 | raw_test_report → sdi_rd_efc_test_report_triton_model_performance（未清洗 OR raw 更新判定） |
| 全局参数 | `report_window_hours = 24` |
| 租户/worker | tenantCode `dolphinscheduler`、workerGroup `default` |
| 定时 | **不设置**（子工作流，由编排触发） |

### 3.2 SeaTunnel 任务「测试报告数据清洗」

| 配置项 | 值 |
| --- | --- |
| taskType | SEATUNNEL |
| workerGroup / environmentCode | default / `169409665039072`（openlibing-prod） |
| useCustom / deployMode / startupScript | true / cluster / seatunnel.sh |
| taskExecuteType / failRetryTimes | BATCH / 0 |
| rawScript | 见 3.3（基于测试环境 v3，窗口参数化） |

### 3.3 rawScript（正式版）

```hocon
# 工作流② 正式版：raw_test_report → sdi_rd_efc_test_report_triton_model_performance
# 增量判定：未清洗 OR raw.source_end_time > 已清洗 source_end_time（重试重采后 raw 更新 → 重清洗）
# 与测试环境验证版（v3）一致；仅反查/时间窗口由硬编码 24 改为 ${report_window_hours}
env {
  execution.parallelism = 1
  job.mode = "BATCH"
  checkpoint.interval = 30000
  checkpoint.timeout = 900000
}

source {
  Jdbc {
    plugin_output = "report_detail"
    url = "${openlibing_doris_url}"
    driver = "${openlibing_doris_driver}"
    username = "${openlibing_doris_username}"
    password = "${openlibing_doris_password}"
    query = """
      SELECT y.pipeline_id, y.pipeline_run_id, y.job_id, y.report_file_name,
             y.record_seq,
             COALESCE(y.repo_url, s.repo_url)                    AS repo_url,
             COALESCE(y.workflow_start_time, s.wf_start_time)    AS workflow_start_time,
             COALESCE(y.workflow_end_time,   s.wf_end_time)      AS workflow_end_time,
             y.source_end_time, y.model_name, y.model_config,
             y.eager_device_time, y.inductor_device_time
      FROM (
        -- 层3：ROW_NUMBER + JSON 提取（在 LATERAL VIEW 结果之上）
        SELECT x.pipeline_id, x.pipeline_run_id, x.job_id, x.report_file_name,
               ROW_NUMBER() OVER (
                 PARTITION BY x.pipeline_id, x.pipeline_run_id, x.job_id, x.report_file_name
                 ORDER BY x.el
               ) AS record_seq,
               JSON_EXTRACT_STRING(x.el, '$.model_name')           AS model_name,
               JSON_EXTRACT_STRING(x.el, '$.model_config')         AS model_config,
               CAST(JSON_EXTRACT_STRING(x.el, '$.eager_device_time')    AS DOUBLE) AS eager_device_time,
               CAST(JSON_EXTRACT_STRING(x.el, '$.inductor_device_time') AS DOUBLE) AS inductor_device_time,
               x.repo_url, x.workflow_start_time, x.workflow_end_time, x.source_end_time
        FROM (
          -- 层2：LATERAL VIEW EXPLODE
          SELECT r.pipeline_id, r.pipeline_run_id, r.job_id, r.report_file_name, e.el,
                 r.repo_url, r.workflow_start_time, r.workflow_end_time, r.source_end_time
          FROM (
            -- 层1：raw + 反查排除（未清洗 OR raw.source_end_time > 已清洗 source_end_time）
            SELECT r.pipeline_id, r.pipeline_run_id, r.job_id, r.report_file_name, r.data_json,
                   NULL AS repo_url, NULL AS workflow_start_time, NULL AS workflow_end_time,
                   r.source_end_time
            FROM raw_test_report r
            LEFT JOIN ( -- 反查：窗口内已清洗的（四元组）排除 + 重试时间比较
              SELECT pipeline_id, pipeline_run_id, job_id, report_file_name,
                     MAX(source_end_time) AS max_source_end_time
              FROM sdi_rd_efc_test_report_triton_model_performance
              WHERE report_upload_time > NOW() - INTERVAL ${report_window_hours} HOUR
              GROUP BY pipeline_id, pipeline_run_id, job_id, report_file_name
            ) s
              ON r.pipeline_id = s.pipeline_id AND r.pipeline_run_id = s.pipeline_run_id
             AND r.job_id = s.job_id AND r.report_file_name = s.report_file_name
            WHERE (s.pipeline_id IS NULL OR r.source_end_time > s.max_source_end_time)
              AND r.create_time > NOW() - INTERVAL ${report_window_hours} HOUR
              AND r.model_code = 'triton_model_performance'
          ) r
          LATERAL VIEW EXPLODE_JSON_ARRAY_JSON(r.data_json) e AS el
        ) x
      ) y
      LEFT JOIN ( -- 归属字段兜底：三平台来源表 JOIN（codearts / github / gitcode，只取已完成记录）
        SELECT pipeline_id, pipeline_run_id,
               CONCAT(step_build_job_id, '_', REPLACE(step_daily_build_number, '.', '_')) AS job_id,
               git_url AS repo_url,
               pipeline_start_time AS wf_start_time, pipeline_end_time AS wf_end_time
        FROM sdi_rd_efc_pipeline_run_clean_codearts
        WHERE pipeline_end_time > NOW() - INTERVAL ${report_window_hours} HOUR
          AND pipeline_status = 'COMPLETED'
        UNION ALL
        SELECT CAST(r.workflow_id AS STRING) AS pipeline_id,
               CAST(j.workflow_run_id AS STRING) AS pipeline_run_id,
               CAST(j.workflow_job_id AS STRING) AS job_id,
               j.repo_url,
               r.run_started_at AS wf_start_time, r.updated_at AS wf_end_time
        FROM sdi_rd_efc_workflow_run_job_github j
        LEFT JOIN sdi_rd_efc_workflow_run_raw_github r ON j.workflow_run_id = r.run_id
        WHERE r.run_started_at > NOW() - INTERVAL ${report_window_hours} HOUR
          AND j.status = 'completed'
        UNION ALL
        SELECT workflow_id AS pipeline_id, workflow_run_id AS pipeline_run_id, job_id,
               repo_url, start_time AS wf_start_time, end_time AS wf_end_time
        FROM sdi_rd_efc_workflow_run_raw_gitcode
        WHERE start_time > NOW() - INTERVAL ${report_window_hours} HOUR
          AND status = 'COMPLETED'
      ) s
        ON y.pipeline_id = s.pipeline_id AND y.pipeline_run_id = s.pipeline_run_id
       AND y.job_id = s.job_id
      ORDER BY y.report_file_name, y.record_seq
    """
  }
}

sink {
  Jdbc {
    plugin_input = ["report_detail"]
    url = "${openlibing_doris_url}"
    driver = "${openlibing_doris_driver}"
    username = "${openlibing_doris_username}"
    password = "${openlibing_doris_password}"
    query = """
      INSERT INTO sdi_rd_efc_test_report_triton_model_performance (
        pipeline_id, pipeline_run_id, job_id, report_file_name, record_seq,
        repo_url, workflow_start_time, workflow_end_time, source_end_time, report_upload_time,
        model_name, model_config, eager_device_time, inductor_device_time
      ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, NOW(), ?, ?, ?, ?);
    """
    auto_commit = true
    batch_size = 100
  }
}
```

---

## 4. 创建编排「[workflow][openlibing]测试报告采集编排」

> 架构决策：**独立编排 + DEPENDENT 逻辑依赖**，不物理塞入现有编排（理由见 [design.md](design.md) 3 节/13 章 R10/R11）。

### 4.1 基本信息与调度

| 配置项 | 值 |
| --- | --- |
| 项目 | openlibing（169400948446944） |
| 工作流名称 | `[workflow][openlibing]测试报告采集编排` |
| 描述 | DEPENDENT 等待三平台执行记录采集完成 → 串行触发测试报告 raw 采集 → sdi 清洗 |
| 调度（cron） | `0 0 * * * ? *`（每小时整点，与三平台采集编排同拍；**1~4 点三平台不跑，DEPENDENT 会等待/失败，见 4.5 提示**） |
| timezoneId | `Asia/Shanghai` |
| failureStrategy | CONTINUE |
| warningType | FAILURE |
| warningGroupId | 2 |
| workflowInstancePriority | MEDIUM |
| workerGroup / tenantCode | default / `dolphinscheduler` |
| environmentCode | -1 |
| 失败重试 | 不设（DEPENDENT 由调度下小时自然补偿） |

### 4.2 任务节点 T1：DEPENDENT「等待三平台执行记录采集完成」

| 配置项 | 值 |
| --- | --- |
| taskType | DEPENDENT |
| dependence.checkInterval | 30（秒） |
| dependence.failurePolicy | `DEPENDENT_FAILURE_FAILURE` |
| dependence.relation | AND |
| dependTaskList[0].relation | AND |
| dependItemList[0].dependentType | `DEPENDENT_ON_WORKFLOW` |
| dependItemList[0].projectCode | `169400948446944` |
| dependItemList[0].definitionCode | `176230008422726`（`[workflow][raw->dwi]PR&workflow数据获取`） |
| dependItemList[0].depTaskCode | `0`（依赖整个工作流） |
| dependItemList[0].cycle | `hour` |
| dependItemList[0].dateValue | `currentHour`（当前小时） |
| dependItemList[0].state | 空（默认成功） |
| dependItemList[0].parameterPassing | false |

> 与正式环境既有 DEPENDENT（codearts 编排 169579299839168 内任务 176365918863712）完全同构，仅定义指向改为依赖 176230008422726。

### 4.3 任务节点 T2 / T3：SUB_WORKFLOW

| 配置项 | 值（T2） | 值（T3） |
| --- | --- | --- |
| 任务名称 | `测试报告原始数据采集` | `测试报告数据清洗` |
| taskType | SUB_WORKFLOW | SUB_WORKFLOW |
| taskParams.workflowDefinitionCode | 第 2 节创建的工作流① code | 第 3 节创建的工作流② code |
| workerGroup / environmentCode | default / `169409665039072` | default / `169409665039072` |
| failRetryTimes | 0 | 0 |
| taskExecuteType | BATCH | BATCH |

### 4.4 任务关系（taskRelationList）

| 前驱（preTaskCode） | 后继（postTaskCode） | 说明 |
| --- | --- | --- |
| 0（起点） | T1 DEPENDENT | 编排从等待三平台采集开始 |
| T1 DEPENDENT | T2 SUB_WORKFLOW① | DEPENDENT 通过后才采 raw |
| T2 SUB_WORKFLOW① | T3 SUB_WORKFLOW② | 清洗依赖 raw 采集完成 |

串行链路：`DEPENDENT → 工作流①（raw 采集）→ 工作流②（sdi 清洗）`。

### 4.5 注意事项

- **1~4 点错位提示**：三平台采集编排 cron 为 `0 0 0,6-23,5 * * ? *`（1~4 点不运行），DEPENDENT 在 1~4 点无"当前小时成功"实例。若编排 cron 用 `0 0 * * * ? *`，1~4 点 DEPENDENT 将等待直至超时/失败（产生失败告警）。可选优化：编排 cron 跟随三平台改为 `0 0 0,5-23 * * ? *`，与三平台同拍、避免 1~4 点空等（设计文档原案为每小时整点，二者均可，业务可择一）。
- 编排失败（如三平台编排失败）由 DEPENDENT failurePolicy 传导；下小时自然补偿。

---

## 5. 生产测试验证清单（创建完成后）

| # | 验证项 | 方法/预期 |
| --- | --- | --- |
| 5.1 | 编排调度触发 | 到点观察编排实例：DEPENDENT 先处于等待，三平台编排当前小时成功后 DEPENDENT 通过 |
| 5.2 | raw 采集 | 工作流① 执行成功，`raw_test_report` 出现新数据（`data_json` 与 OBS 原文一致） |
| 5.3 | sdi 清洗 | 工作流② 执行成功，`sdi_rd_efc_test_report_triton_model_performance` 出现记录（`record_seq` 连续、归属字段已补齐） |
| 5.4 | ops 消费 | `POST /report/data/query`（modelCode=triton_model_performance）命中正式环境数据 |
| 5.5 | 幂等 | 重复触发编排/工作流，raw/sdi 行数不翻倍（UNIQUE KEY + 反查） |
| 5.6 | 重试语义 | 对某流水线重试后，源表 end_time 更新 → 下轮工作流①/② 判定重采/重清洗（source_end_time 变新），同键覆盖无重复行 |
| 5.7 | 并发错位 | 连续 2 小时观察：测试报告编排与三平台编排、codearts 编排无实例重叠冲突 |
| 5.8 | 失败告警 | 模拟三平台编排失败 → 本编排告警组 2 收到失败通知，下小时恢复 |

---

## 6. 关联归档

- 设计：[design.md](design.md)（v3.1）
- 测试环境验证版工作流（测试项目 wl_test）：① 183798696421280（v4）、② 183813929879456（v3）
- 数据模型 DDL 与登记清单：design 6.1/6.3/6.4/7.5
