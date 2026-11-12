# 流水线任务明细增加机器/资源池 — 技术设计

## 方案概述

任务明细分页主查询保持不变；在分页结果返回后，按当页 jobIds **一次批量**查询资源申请信息（仅 `npu_num > 0`），左连机器静态维表取资源池，在 Service 内按 `(pipeline_run_id, 统一 job_id)` 分组、按 IP 去重与 IPv4 数值序排序，填充到响应的 `machines` 成对数组。

## 关键决策

| 决策 | 结论 | 原因 |
|---|---|---|
| 机器数据源 | `dwi_rd_efc_resource_apply_info`，限定 `npu_num > 0` | 需求指定；申请表按「任务 × 机器申请」记录，`npu_num > 0` 可排除纯 CPU 申请 |
| codearts job_id | 经 `sdi_rd_efc_pipeline_run_clean_codearts` 按 `(pipeline_run_id, step_build_job_id)` 反查统一 `job_id` | 申请表 job_id 形如 `<step_build_job_id>_<daily_build_number>`，与任务明细统一 job_id 不一致；实测 2026-11-04 当日 codearts 申请行 180/180 可解析 |
| gitcode/github job_id | 直接使用申请表 job_id | 实测与统一 job_id 一致（如 github `124587304768`） |
| 查询位置 | 分页主查询之后，按当页 jobIds 批量查询 | 避免 1:N JOIN 放大行数/总数；固定 3 次 SQL（count + 分页 + 机器），无 N+1 |
| 输出结构 | 单个 `machines` 成对数组，不使用 IP/资源池两个平行数组 | 多机且部分池缺失时平行数组无法对齐 |
| 排序 | 后端按 IPv4 四段数值序排序 | 保证分页/重复请求顺序稳定，前端不二次排序 |
| 去重 | 同 job 同 IP 只保留一条，优先保留非空池 | 申请表同一 job/IP 可能多条申请记录 |
| 空值口径 | 无记录 `[]`；有 IP 无池 `null` | 不隐藏 IP，也避免 null 与空串混用 |

## 数据流

```text
queryDetail
  ├─ countPrPipelineJobDetail(req)                     # 总数（父行口径，不变）
  ├─ queryPrPipelineJobDetail(req)                     # 当页任务（LIMIT/OFFSET，不变）
  └─ fillMachines(req, records)                        # 新增，仅当页有记录时执行
       └─ queryJobMachines(req, pageJobIds)
            ├─ codearts_job_map: sdi_rd_efc_pipeline_run_clean_codearts（仅本 run）
            ├─ 申请表 a: dwi_rd_efc_resource_apply_info (npu_num > 0)
            └─ LEFT JOIN machine_pool: sdi_rd_efc_server_machine_hidevlab
```

## 接口契约（向后兼容的增量字段）

```json
{
  "jobId": "ba49531e343948068a510c88c55c16d7",
  "machines": [
    { "serverIp": "172.16.0.121", "resourcePoolName": "Ascend统一资源池-贵阳" }
  ]
}
```

- 无资源记录：`"machines": []`
- 有 IP 无资源池：`"machines": [{"serverIp": "172.16.0.50", "resourcePoolName": null}]`

## 关键 SQL 口径

```sql
WITH codearts_job_map AS (
    SELECT DISTINCT pipeline_run_id, step_build_job_id, job_id
    FROM sdi_rd_efc_pipeline_run_clean_codearts
    WHERE pipeline_run_id = #{req.pipelineRunId}
      AND step_build_job_id IS NOT NULL AND step_build_job_id <> ''
),
machine_pool AS (
    SELECT TRIM(server_ip) AS server_ip, MAX(resource_pool_name) AS resource_pool_name
    FROM sdi_rd_efc_server_machine_hidevlab
    WHERE server_ip IS NOT NULL AND TRIM(server_ip) <> ''
    GROUP BY TRIM(server_ip)
)
SELECT DISTINCT
    COALESCE(c.job_id, a.job_id) AS job_id,
    a.pipeline_run_id,
    TRIM(a.server_ip) AS server_ip,
    m.resource_pool_name
FROM dwi_rd_efc_resource_apply_info a
LEFT JOIN codearts_job_map c
    ON c.pipeline_run_id = a.pipeline_run_id
   AND c.step_build_job_id = SUBSTRING_INDEX(a.job_id, '_', 1)
LEFT JOIN machine_pool m ON m.server_ip = TRIM(a.server_ip)
WHERE a.pipeline_run_id = #{req.pipelineRunId}
  AND a.npu_num > 0
  AND a.job_id IS NOT NULL
  AND a.server_ip IS NOT NULL
  AND TRIM(a.server_ip) <> ''
  AND COALESCE(c.job_id, a.job_id) IN (当页 jobIds)
ORDER BY job_id, server_ip
```

## 涉及文件

| 文件 | 操作 | 说明 |
|---|---|---|
| `openlibing-ops/src/main/java/.../OpsPrPipelineJobDetailResp.java` | 修改 | 新增 `machines` 与嵌套 `MachineDetail` |
| `openlibing-ops/src/main/java/.../OpsPrPipelineJobDetailMapper.java` | 修改 | 新增 `queryJobMachines(req, jobIds)` 与 `JobMachineRow` |
| `openlibing-ops/src/main/resources/mapper/OpsPrPipelineJobDetailMapper.xml` | 修改 | 新增 `jobMachineMap` 与 `queryJobMachines`（申请表 + codearts 映射 + 机器维表） |
| `openlibing-ops/src/main/java/.../OpsPrPipelineJobDetailDetailService.java` | 修改 | 分页后批量填充、分组、去重、IPv4 排序、空值口径 |
| `openlibing-ops/src/test/.../OpsPrPipelineJobDetailMapperXmlTest.java` | 修改 | XML 结构/解耦断言 |
| `openlibing-ops/src/test/.../OpsPrPipelineJobDetailDetailServiceTest.java` | 修改 | 多机配对、去重、空值、排序、批量作用域等 13 个用例 |

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| 1:N JOIN 导致分页/总数失真 | 机器查询与分页主查询解耦，固定 3 次 SQL；已用真实数据验证 total 不变 |
| codearts job_id 口径不一致 | 通过 `sdi_rd_efc_pipeline_run_clean_codearts` 映射；2026-11-04 当日 180/180 覆盖，单元测试与真实数据验证 |
| 同名 `server_ip` 字段比较错误 | 两侧均带表别名并 `TRIM`，XML 测试断言 `ON m.server_ip = TRIM(a.server_ip)` |
| 机器维表同一 IP 多行 | 子查询按 `TRIM(server_ip)` 聚合 `MAX(resource_pool_name)`，避免 JOIN 放大 |
| 上游数据缺失 | 申请表/机器表缺失时返回 `[]` 或 `null`，不影响任务行；建议对空值率做监控 |
| 性能 | 机器查询只扫当页（≤100 个 jobIds）且按 run 收敛；实测接口 313–397ms（首请求冷启动 710ms） |

## 跨仓影响

`openlibing-ops-web` 需在任务明细表格新增一列「机器/资源池」（`IP（pool）` 单条、多机首条 + `+N`、空 `-`）。当前工作区前端快照早于 #294，缺少 `pr-pipeline-job-detail.vue`，故本次未落地；后端接口契约已就绪。
