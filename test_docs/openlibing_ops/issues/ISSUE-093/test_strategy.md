# 测试策略 - ISSUE-093

## 1. Issue 信息

| 字段       | 内容                                                                  |
| ---------- | --------------------------------------------------------------------- |
| Issue编号  | ISSUE-093                                                             |
| Issue标题  | 【蓝区】【运营看板】GitHub workflow中job数据采集&workflow排队数据计算 |
| 关联需求   | https://gitcode.com/openlibing/openlibing-ops/issues/93               |
| 所属微服务 | openlibing-ops                                                        |
| 所属模块   | operation_dashboard（开源项目运营看板数据链路）                       |
| 负责人     | tester-a                                                              |
| 创建日期   | 2026-08-29                                                            |
| 状态       | 进行中                                                                |

## 2. 需求摘要

> 提炼自 Issue 描述（开发设计文档以 Issue 正文为准，无附加附件）。

需求内容共 2 条（数据层交付）：

1. **采集 workflow 中 job 数据**：对 GitHub workflow 的 job 级明细数据进行采集入库。
2. **workflow 的排队时间根据 job 的排队时间计算**：workflow 级排队时长由其下 job 的排队时长推导（落表注释口径：`dwi_rd_efc_workflow_run_raw_github.pending_duration` = "workflow 排队时间，任务的最长排队时间"）。

数据链路（实测梳理）：

```
raw_workflow_runs_job_github（job 原始 JSON）
  → sdi_rd_efc_workflow_run_job_github（job 清洗层，GitHub 原生字段 created_at/started_at/completed_at）
  → dwi_rd_efc_workflow_run_job_github（job 标准层）
  → dwr_rd_efc_workflow_run_job_github_fact（job 事实层，含 job_pending_duration/job_duration）
       ↑ workflow 级排队时间落表于 dwi_rd_efc_workflow_run_raw_github.pending_duration
       ↓ DM 消费层（dm_rd_efc_repo_sum_pipeline_statistics_day 等，运营看板数据源）
```

> Issue 标题语境为"运营看板"，即该数据最终服务于开源项目运营看板（`/apps/oSPDashboard`，业务接口 `POST /gateway/openlibing-ops/manage/common/detail`）。

## 3. 测试目标

- 验证 job 数据采集链路完整且持续活跃：raw/SDI/DWI/DWR 四层有数据、字段完整、数据新鲜
- 验证 job 排队时长计算口径：`job_pending_duration = job_run_start_time − job_start_time`
- 验证 workflow 排队时间计算口径：workflow 排队时间 = 该 run 下所有 job 排队时长的最大值
- 验证端到端消费链路：GitHub workflow 排队数据是否进入 DM 聚合层并透出至运营看板 API

## 4. 测试范围

| 测试类型     | 是否覆盖            | 说明                                                                                    |
| ------------ | ------------------- | --------------------------------------------------------------------------------------- |
| UI功能测试   | 否                  | 排队时间为数据层交付，看板前端暂无排队字段展示（API 层验证已覆盖透出情况）              |
| API接口测试  | 是                  | 运营看板 `manage/common/detail`、Nightly 看板 `common/detail` 字段透出验证（test 环境） |
| 性能测试     | 否                  | 数据链路批处理任务，无接口性能验收要求（Issue 未提及）                                  |
| 安全测试     | 否                  | 无新增对外接口，复用既有鉴权体系（Issue 未提及）                                        |
| 数据链路验证 | 是（本 Issue 核心） | Doris 各层数据完整性、口径正确性、新鲜度验证（经由 mcp_doris-mcp）                      |

## 5. 测试策略

### 5.1 手工测试

- 本期无手工用例。数据层验证通过 Doris 查询自动化覆盖，看板字段透出通过 API 自动化覆盖。

### 5.2 自动化测试

- **数据链路层**（Doris，test 环境）：
  - `src/tests/openlibing/openlibing_ops/api/beta/operation_dashboard/`：数据采集链路验证（四层表存在性与新鲜度、job 粒度完整性）
  - 排队时间计算口径验证（job 口径 + workflow 口径匹配率）
  - 依赖 `mcp_doris-mcp` 执行 SQL 的能力作为验证通道（自动化脚本断言查询结果）
- **API 层**（test 环境）：
  - 运营看板汇总接口 `POST /gateway/openlibing-ops/manage/common/detail` 字段探查与数据返回
- 自动化用例归档位置: `assets/docs/openlibing/openlibing_ops/issues/ISSUE-093/test_cases.md`
- 自动化脚本位置: `src/tests/openlibing/openlibing_ops/api/beta/operation_dashboard/`

### 5.3 用例复用原则

- 已查询 `openlibing_ops` 模块用例文件（`test_case.md`，共 139 条）：无 job 数据采集/排队时间相关既有用例，本 Issue 用例全部新建
- Nightly 看板既有用例（`nightly_dashboard` 模块）覆盖 `failedTaskType`/汇总等字段，与本 Issue 排队字段无交集，不复用

## 6. 风险与约束

| 风险                                                          | 影响                                         | 缓解措施                                                     |
| ------------------------------------------------------------- | -------------------------------------------- | ------------------------------------------------------------ |
| DM 聚合层 GitHub 排队字段全零（实测发现）                     | 端到端链路断点，看板无法展示 GitHub 排队时间 | 如实记录为发现项，反馈开发确认 DM ETL 是否纳入 GitHub job 源 |
| 运营看板 API 无排队字段（实测发现）                           | 看板层无排队数据消费点                       | 记录为发现项；看板展示可能属后续迭代范围                     |
| workflow 排队与 job 最长排队存在 6/3279 条偏差（99.82% 匹配） | 口径理解偏差或重试/matrix 任务影响           | 用例断言采用匹配率阈值（≥99%）而非逐条强一致                 |
| 看板 JS 静态资源偶发 503                                      | UI/API 探查受阻                              | API 直连探测 + 浏览器探查重试机制                            |
| Doris SQL 安全校验拦截复杂嵌套/UNION 查询                     | 自动化脚本查询受限                           | 脚本内拆分为简单查询分步断言                                 |

## 7. 依赖与前置条件

- 依赖1：test/beta 环境可访问（beta.openlibing.com），登录凭证已在 `.env` 配置
- 依赖2：Doris `openlibing` 库可查询（经 mcp_doris-mcp），GitHub 4 仓（sgl-kernel-npu/sglang/vllm-ascend/triton-ascend）持续有 workflow 运行
- 依赖3：GitHub workflow job 采集任务（数仓侧）处于运行状态

## 8. 版本历史

| 版本 | 日期       | 修改人   | 修改内容                       |
| ---- | ---------- | -------- | ------------------------------ |
| v1.0 | 2026-08-29 | tester-a | 初始版本（含端到端预验证证据） |
