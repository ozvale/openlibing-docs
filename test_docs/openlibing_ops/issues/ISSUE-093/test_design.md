# 测试设计 - ISSUE-093

## 1. 设计概述

本Issue的测试设计基于 Issue 需求描述（2 条数据层交付）与实测数据链路，覆盖以下功能点：job 数据采集入库、job 排队时长计算、workflow 排队时间计算、DM/看板端到端消费。

### 1.1 设计原则

- 手工用例与自动化用例分离
- 自动化用例需标注脚本位置
- 每个用例需记录用例类型
- 每个功能点需标注所采用的测试设计方法

### 1.2 用例类型定义

| 类型代码  | 类型名称    | 说明                  |
| --------- | ----------- | --------------------- |
| manual    | 手工执行    | 需要人工操作执行      |
| auto_ui   | 自动化-UI   | UI自动化测试脚本      |
| auto_api  | 自动化-API  | API接口自动化测试脚本 |
| auto_perf | 自动化-性能 | 性能测试脚本          |
| auto_sec  | 自动化-安全 | 安全测试脚本          |

### 1.3 测试设计方法

本设计采用以下方法（详见 ai-rules/01-requirement-driven-test-design.md 第4节）：

- [x] 等价类划分（Equivalence Partitioning）：按平台（GitHub/GitCode）、job 状态（排队中/运行/完成）划分数据域
- [x] 边界值分析（Boundary Value）：排队时长为 0（无排队）与极大值（127,476s 实测）的边界记录验证
- [x] 场景法（Use Case / Scenario Testing）：数据从采集到看板消费的端到端链路场景
- [x] 错误推测法（Error Guessing）：DM 聚合漏掉 GitHub 源、API 字段缺失等风险点
- [ ] 决策表测试（Decision Table Testing）
- [ ] 状态迁移测试（State Transition Testing）

## 2. 功能点分析

> 每个功能点必须能在开发设计文档（Issue 正文）中找到依据，禁止超出文档范围发散。

| 功能点                                     | 设计依据（开发设计文档章节）                                                  | 测试设计方法             | 测试类型                   | 优先级 |
| ------------------------------------------ | ----------------------------------------------------------------------------- | ------------------------ | -------------------------- | ------ |
| FP-01 job 数据采集入库（四层链路）         | Issue 需求内容第 1 条"采集workflow 中job数据"                                 | 等价类划分               | auto_api（Doris 查询断言） | L0     |
| FP-02 job 排队时长计算口径                 | Issue 需求内容第 2 条（job 排队时间为计算输入）                               | 边界值分析 + 等价类      | auto_api（Doris 查询断言） | L1     |
| FP-03 workflow 排队时间 = job 最长排队时间 | Issue 需求内容第 2 条"workflow的排队时间根据job的排队时间计算" + 落表注释口径 | 等价类划分（匹配率验证） | auto_api（Doris 查询断言） | L0     |
| FP-04 DM 聚合层 GitHub 排队数据消费        | Issue 标题"运营看板"（数据消费场景）                                          | 场景法 + 错误推测        | auto_api（Doris 查询断言） | L1     |
| FP-05 运营看板 API 排队字段透出            | Issue 标题"运营看板"（数据消费场景）                                          | 场景法                   | auto_api                   | L2     |

## 3. 用例设计

### TC-ISSUE093-001: job 数据采集链路完整性验证（四层表有数据且新鲜）

| 字段         | 内容                                                                                                                                                                                                                                |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE093-001                                                                                                                                                                                                                     |
| 所属功能点   | FP-01 job 数据采集入库                                                                                                                                                                                                              |
| 测试设计方法 | 等价类划分                                                                                                                                                                                                                          |
| 用例类型     | auto_api                                                                                                                                                                                                                            |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/operation_dashboard/test_api_ops_data_pipeline_001.py`                                                                                                                                |
| 优先级       | L0                                                                                                                                                                                                                                  |
| 前置条件     | Doris openlibing 库可查询；GitHub 4 仓有 workflow 运行                                                                                                                                                                              |
| 测试步骤     | 1. 查询 `raw_workflow_runs_job_github` 按仓库统计 job 数、run 数、最新 create_time<br>2. 查询 `dwi_rd_efc_workflow_run_job_github` 最新 completed_at<br>3. 查询 `dwr_rd_efc_workflow_run_job_github_fact` 总行数与最新 job_end_time |
| 预期结果     | 三层均有数据；raw 层覆盖 4 个 GitHub 仓库且 job 记录无重复（distinct job = count）；DWR 事实表记录 > 100 万且最新数据在 24h 内（采集活跃）                                                                                          |

### TC-ISSUE093-002: job 排队时长计算口径验证

| 字段         | 内容                                                                                                                                                               |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 用例编号     | TC-ISSUE093-002                                                                                                                                                    |
| 所属功能点   | FP-02 job 排队时长计算                                                                                                                                             |
| 测试设计方法 | 边界值分析 + 等价类                                                                                                                                                |
| 用例类型     | auto_api                                                                                                                                                           |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/operation_dashboard/test_api_ops_data_pipeline_002.py`                                                               |
| 优先级       | L1                                                                                                                                                                 |
| 前置条件     | FP-01 通过                                                                                                                                                         |
| 测试步骤     | 1. 抽取 `job_pending_duration` 最高的 5 条 job<br>2. 逐条计算 `job_run_start_time − job_start_time`（秒）<br>3. 抽取 `job_pending_duration = 0` 的记录验证零值边界 |
| 预期结果     | 抽样记录的 `job_pending_duration` 与 `job_run_start_time − job_start_time` 差值精确一致（含 0 值边界）；差值为负或为 NULL 的记录不存在                             |

### TC-ISSUE093-003: workflow 排队时间与 job 最长排队匹配率验证

| 字段         | 内容                                                                                                                                                                                                                   |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE093-003                                                                                                                                                                                                        |
| 所属功能点   | FP-03 workflow 排队时间计算                                                                                                                                                                                            |
| 测试设计方法 | 等价类划分（全量匹配率）                                                                                                                                                                                               |
| 用例类型     | auto_api                                                                                                                                                                                                               |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/operation_dashboard/test_api_ops_data_pipeline_003.py`                                                                                                                   |
| 优先级       | L0                                                                                                                                                                                                                     |
| 前置条件     | FP-01 通过                                                                                                                                                                                                             |
| 测试步骤     | 1. JOIN `dwi_rd_efc_workflow_run_raw_github` 与 `dwr_rd_efc_workflow_run_job_github_fact`（按 workflow_run_id）<br>2. 按 run 分组计算 max(job_pending_duration)<br>3. 统计 workflow pending_duration 与之不等的 run 数 |
| 预期结果     | 匹配率 ≥ 99%（实测基线 99.82%，3279 个 run 中 6 条偏差，偏差源于重试/matrix 任务追加）；偏差记录数 ≤ 20                                                                                                                |

### TC-ISSUE093-004: DM 聚合层 GitHub 排队数据消费验证

| 字段         | 内容                                                                                                                                                                                            |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE093-004                                                                                                                                                                                 |
| 所属功能点   | FP-04 DM 聚合层消费                                                                                                                                                                             |
| 测试设计方法 | 场景法 + 错误推测                                                                                                                                                                               |
| 用例类型     | auto_api                                                                                                                                                                                        |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/operation_dashboard/test_api_ops_data_pipeline_004.py`                                                                                            |
| 优先级       | L1                                                                                                                                                                                              |
| 前置条件     | FP-03 通过                                                                                                                                                                                      |
| 测试步骤     | 1. 查询 `dm_rd_efc_repo_sum_pipeline_statistics_day` 中 GitHub 4 仓的 build/dt pending 字段<br>2. 查询同表 GitCode 仓库对应字段作为对照<br>3. 对比 DWI/DWR 层 GitHub 有非零排队数据与 DM 层取值 |
| 预期结果     | GitHub 仓在 DM 层的排队字段应有非零聚合值（与源层排队数据一致）；**实测为全零 → 预期不成立，判定 fail（需反馈开发）**                                                                           |

### TC-ISSUE093-005: 运营看板 API 排队字段透出验证

| 字段         | 内容                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE093-005                                                                                                                                                                                                                                                                                                                                                                                                                    |
| 所属功能点   | FP-05 看板 API 字段透出                                                                                                                                                                                                                                                                                                                                                                                                            |
| 测试设计方法 | 场景法                                                                                                                                                                                                                                                                                                                                                                                                                             |
| 用例类型     | auto_api                                                                                                                                                                                                                                                                                                                                                                                                                           |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/operation_dashboard/test_api_ops_dashboard_fields_005.py`                                                                                                                                                                                                                                                                                                                            |
| 优先级       | L2                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| 前置条件     | test 环境已登录（api_client 可用）                                                                                                                                                                                                                                                                                                                                                                                                 |
| 测试步骤     | 1. POST `/gateway/openlibing-ops/common/detail`（category=github-pr-workflow-main，repoIds=[402051]）获取 GitHub PR workflow 级明细<br>2. 检查 records 字段集合中 8 个目标字段（queueP50/queueP90/queueP95、execP50/execP90/execP95、prMergeDuration、e2ePassRate）的透出情况<br>3. 校验取值语义（分位单调 P50≤P90≤P95、存在非空排队数据、仓级字段取值合法）                                                                       |
| 预期结果     | queueP50/queueP90/queueP95（排队时间）、execP50/execP90/execP95（合入时间）、prMergeDuration（PR合入时长）、e2ePassRate（E2E达标率）全部透出且取值语义合法；**实测（2026-08-31，透出口径修正后复跑 3/3 passed）：通过——透出位置为 github-pr-workflow-main 明细接口（此前按项目级汇总/Nightly 看板探查未命中，系透出位置判断偏差，调用实例由测试人员提供并归档 exploration_assets/github_pr_workflow_main_example_20260831.json）** |

## 4. 覆盖度说明

- 开发设计文档（Issue 正文）覆盖功能点数：2（job 采集、workflow 排队计算）
- 本设计覆盖功能点数：2 全覆盖，另依据"运营看板"标题语境延伸 2 个消费层验证点（FP-04/FP-05）
- 未覆盖功能点及原因：无。看板 UI 展示样式、导出等不在本 Issue 文字范围内

## 5. 版本历史

| 版本 | 日期       | 修改人   | 修改内容                                                                                                                                                                                                                                                                                                                                                                                                                        |
| ---- | ---------- | -------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.0 | 2026-08-29 | tester-a | 初始版本                                                                                                                                                                                                                                                                                                                                                                                                                        |
| v1.1 | 2026-08-31 | AI Agent | 按测试人员决策删除 Doris 直连用例 TC-ISSUE093-001~004（设计条目保留作历史口径）；TC-005 验证口径按看板真实字段名修正：queueP50/queueP90/queueP95（排队时间）、execP50/execP90/execP95（合入时间）、prMergeDuration（PR合入时长）、e2ePassRate（E2E达标率）；补充 2026-08-31 字段探查证据（API 5 接口 + 浏览器 3 看板页面均未命中）                                                                                              |
| v1.2 | 2026-08-31 | AI Agent | TC-005 透出接口口径修正（依据测试人员调用实例）：排队/合入字段透出于 `common/detail`（category=github-pr-workflow-main，workflow 级明细，repoIds 过滤）而非项目级汇总/Nightly 看板——此前未命中系透出位置判断偏差；实测 8 个字段全部透出且取值语义合法（分位单调、排队数据非空），复跑 3/3 passed，FP-05 验证通过，"是否属本期范围"待确认项关闭；调用实例归档 `exploration_assets/github_pr_workflow_main_example_20260831.json` |
