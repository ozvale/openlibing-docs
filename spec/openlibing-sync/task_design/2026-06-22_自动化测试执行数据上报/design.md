# 自动化测试执行数据上报 — 技术设计

## 方案概述
通过新增定时任务（每日凌晨1点），自动收集测试框架运行数据（下载量、使用项目/流水线、执行次数），并通过运维框架提供的接口上报到特性看板。

## 架构决策
1. **数据采集策略**：通过 GitCode API 获取框架下载量，通过数据库查询获取执行数据
2. **调度方式**：复用现有的 XxlJob 定时任务体系
3. **上报接口**：使用 `openlibing-framework/manage/feature-dashboard/report` 接口

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/main/java/com/openlibing/sync/app/event/TestFrameworkReportScheduler.java` | 新增 | 定时任务调度器 |
| `src/main/java/com/openlibing/sync/domain/strategy/TestFrameworkReportService.java` | 新增 | 数据采集与上报服务 |
| `src/main/java/com/openlibing/sync/infrastructure/request/FeatureReportClient.java` | 新增 | 上报接口客户端 |
| `src/main/resources/application.yaml` | 修改 | 添加配置参数 |

## 核心流程

### 1. 执行框架下载使用量采集
- 调用 GitCode API: `https://docs.gitcode.com/docs/apis/get-api-v-5-repos-owner-repo-download-statistics`
- 涉及项目：
  - pytest 测试框架: `https://gitcode.com/openlibing/openlibing-pytest-executor.git`
  - uniatuos 测试框架: `https://gitcode.com/openlibing/openlibing-tep-executor.git`

### 2. 使用项目/流水线查询
先查询前一天的流水线执行记录，以及对应流水线信息及测试框架
```sql
SELECT
        tc.pipeline_id, tc.pipeline_run_id, tc.frame_type
        FROM sdi_rd_efc_test_case_result_raw_codearts tc LEFT JOIN
        dwi_rd_efc_pipeline_run pr ON tc.pipeline_run_id = pr.pipeline_run_id WHERE
        pr.pipeline_start_time >= #{startDate} AND pr.pipeline_start_time <![CDATA[<]]> #{endDate} GROUP BY
        tc.pipeline_run_id
```
在查询流水线的所属项目/社区信息
```sql
SELECT
    pd.product_id,
    pd.product_name,
    pi.project_id,
    p.project_name,
    pi.pipeline_id,
    pi.pipeline_name
FROM sdi_rd_efc_pipeline_name_raw_codearts pi
JOIN sdi_hw_project_info hp ON hp.hw_project_id = pi.project_id
JOIN sdi_project_info p ON p.project_id = hp.project_id
JOIN sdi_product_info pd ON p.product_id = pd.product_id
WHERE pi.pipeline_id IN ()
```

### 根据2中查询到的流水线执行的列表数据进行统计


### 4. 数据上报
- 接口地址: `openlibing-framework/manage/feature-dashboard/report`
- 请求方式: POST
- 请求体结构:
```json
{
  "community": "MindIE",
  "feature": "测试框架",
  "business_metrics": {
    "pytest_download_count": 100,
    "tep_download_count": 50,
    "pipeline_usage_count": 15,
    "total_execution_count": 1000,
    "pytest_frame_usage": 700,
    "tep_frame_usage": 300
  },
  "timestamp": "2026-06-05T14:30:25.123Z"
}
```

## 风险 & 缓解

| 风险 | 缓解策略 |
|------|----------|
| GitCode API 调用失败 | 添加重试机制和降级处理，记录失败日志 |
| 数据库查询超时 | 添加查询超时配置，优化 SQL 语句 |
| 上报接口不可用 | 数据本地缓存，下次重试上报 |
| 数据一致性问题 | 使用事务保证数据完整性 |

## 跨仓影响
- **openlibing-framework**：依赖其提供的上报接口
- **openlibing-pytest-executor / openlibing-tep-executor**：数据来源（下载量统计）