# 测试设计 - ISSUE-109

> **模板版本**: v1.0
> **对应规则**: ai-rules/01-requirement-driven-test-design.md
> **生成阶段**: Stage 4（测试设计 + 用例生成）

---

## 1. 设计概述

本Issue的测试设计基于页面探索功能基线（Issue 设计文档信息不足，功能基线以 `page_exploration.md` 实测为准，见 `requirement_analysis.md` 第 3 节声明），覆盖以下功能点：FP-1 页面路由与权限守卫、FP-2 KPI 汇总、FP-3 NPU 趋势、FP-4 服务器热力图、FP-5 运行分析、FP-6 项目下钻、FP-7 时间范围校验、FP-8 数据管道与数据正确性。

### 1.1 设计原则

- 手工用例与自动化用例分离
- 自动化用例需标注脚本位置
- 每个用例需记录用例类型
- 每个功能点需标注所采用的测试设计方法
- 已知缺陷（#114/#115）用例按"预期失败基线"设计，形成修复验证闭环

### 1.2 用例类型定义

| 类型代码 | 类型名称    | 说明                                                                          |
| -------- | ----------- | ----------------------------------------------------------------------------- |
| manual   | 手工执行    | 需要人工操作执行（本Issue为UI层交互，因账号无看板权限且视觉验证不适合自动化） |
| auto_api | 自动化-API  | API接口自动化测试脚本                                                         |
| auto_sec | 自动化-安全 | 安全测试脚本（纵向越权/认证校验/敏感信息防护）                                |

### 1.3 测试设计方法

本设计采用以下方法（详见 ai-rules/01-requirement-driven-test-design.md 第4节）：

- [x] 等价类划分（Equivalence Partitioning）— API 功能验证（有效/无效输入、projectId 有/无）
- [x] 边界值分析（Boundary Value Analysis）— 时间窗口 7 天限制（6 天/7 天整/8 天）、空数据窗口
- [x] 决策表测试（Decision Table Testing）— 时间参数校验多场景组合（跨度/倒置/缺失/格式 × 预期错误码）
- [x] 状态迁移测试（State Transition Testing）— run-analysis 任务状态机（QUEUING/RUNNING/NONE）
- [x] 场景法（Use Case / Scenario Testing）— UI 端到端交互、无权限访问拦截
- [x] 错误推测法（Error Guessing）— 无效 runId、缺必填参数

## 2. 功能点分析

> 每个功能点必须能在需求基线中找到依据（Issue 原文 + 页面探索实测），**禁止超出范围发散**。

| 功能点                            | 设计依据（requirement_analysis.md / page_exploration.md）                                               | 测试设计方法                  | 测试类型          | 优先级 |
| --------------------------------- | ------------------------------------------------------------------------------------------------------- | ----------------------------- | ----------------- | ------ |
| FP-1 页面路由与权限守卫           | requirement_analysis.md §5 FP-1；page_exploration.md §1（权限码 npu_resource、noPermission 重定向实测） | 场景法 + 纵向越权断言         | manual + auto_sec | P0     |
| FP-2 KPI 汇总 summary             | page_exploration.md §2.2（summary 请求/响应结构、cloud:3池 lab:10池实测）                               | 等价类（有/无 projectId）     | auto_api          | P0     |
| FP-3 NPU 趋势 trend               | page_exploration.md §2.2（dim: pool/gen、12 池/3 代际、逐小时 labels、补 0、截断）                      | 等价类（双维度）              | auto_api          | P0     |
| FP-4 服务器热力图 heatmap         | page_exploration.md §2.2（88 机器骨架/62 台有数据、alloc+jobs、空窗口补 0）                             | 等价类 + 边界值（空数据窗口） | auto_api          | P0     |
| FP-5 运行分析 run-analysis        | page_exploration.md §2.2（runId/projectId 必填 40001、状态机 QUEUING/NONE、无效 runId 空数据）          | 状态迁移 + 错误推测           | auto_api          | P1     |
| FP-6 项目下钻 project-alloc-trend | page_exploration.md §2.2（逐小时申请次数+排队时长）                                                     | 等价类                        | auto_api          | P1     |
| FP-7 时间范围校验                 | verification_report.md CP-13（5 种非法参数实测全 500）；page_exploration.md §2.2 TimeReq                | 决策表 + 边界值               | auto_api          | P1     |
| FP-8 数据管道与数据正确性         | verification_report.md CP-14（08-18~~08-30 每日连续复测恢复）；FP-02~~04 API 数据抽查                   | 边界值（数据窗口）+ 场景法    | auto_api          | P1     |

## 3. 用例设计

> 完整用例清单见 `test_cases.md`（四件套唯一产物约定，机器可读 test_cases.json 已于 2026-09-01 移除）。此处按功能点给出代表性设计。

### TC-ISSUE109-001: summary 接口 7 天窗口 KPI 数据结构与分组验证

| 字段         | 内容                                                                                                                                                                                                      |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-001                                                                                                                                                                                           |
| 所属功能点   | FP-2 KPI 汇总                                                                                                                                                                                             |
| 测试设计方法 | 等价类划分（有效等价类：7 天合法窗口）                                                                                                                                                                    |
| 用例类型     | auto_api                                                                                                                                                                                                  |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_summary_001.py`                                                                                                        |
| 优先级       | P0                                                                                                                                                                                                        |
| 前置条件     | beta 环境；p_tianyan 已登录（API 会话有效）；近 7 天内有资源数据                                                                                                                                          |
| 测试步骤     | 1. 调用 `POST /gateway/openlibing-ops/resource-operation/summary`，body 含近 7 天 startDate/endDate<br>2. 解析响应 code/data<br>3. 校验 poolTotal/resourceTotal/allocRate/usageRate 结构与 cloud/lab 分组 |
| 预期结果     | 1. HTTP 200，code=200<br>2. data 包含 poolTotal、resourceTotal、allocRate、usageRate 四字段<br>3. 分组键为 cloud 与 lab<br>4. resourceTotal 每组为 [{generation, npuNum}] 列表，npuNum 为非负数           |

### TC-ISSUE109-002: summary 接口 projectId 过滤验证

| 字段         | 内容                                                                                                                             |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-002                                                                                                                  |
| 所属功能点   | FP-2 KPI 汇总                                                                                                                    |
| 测试设计方法 | 等价类划分（projectId 有效值 vs 省略）                                                                                           |
| 用例类型     | auto_api                                                                                                                         |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_summary_001.py`                               |
| 优先级       | P1                                                                                                                               |
| 前置条件     | 同 TC-ISSUE109-001；projectId=300036 存在资源数据                                                                                |
| 测试步骤     | 1. 相同时间窗口调用 summary（无 projectId）记录池总数<br>2. 调用 summary（projectId=300036）记录池总数<br>3. 对比两次结果        |
| 预期结果     | projectId=300036 的池总数 ≤ 全量池总数；过滤后数据仅包含该项目可见资源池（实测基线：全量 cloud:3 lab:10 → 过滤后 cloud:1 lab:1） |

### TC-ISSUE109-003: trend 接口 pool 维度分组与逐小时曲线验证

| 字段         | 内容                                                                                                                                                                                                                             |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-003                                                                                                                                                                                                                  |
| 所属功能点   | FP-3 NPU 趋势                                                                                                                                                                                                                    |
| 测试设计方法 | 等价类划分（dim=pool 有效等价类）                                                                                                                                                                                                |
| 用例类型     | auto_api                                                                                                                                                                                                                         |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_trend_002.py`                                                                                                                                 |
| 优先级       | P0                                                                                                                                                                                                                               |
| 前置条件     | 同 TC-ISSUE109-001                                                                                                                                                                                                               |
| 测试步骤     | 1. 调用 `POST /resource-operation/trend`，dim=pool，7 天窗口<br>2. 校验 labels 逐小时连续性（yyyy-MM-dd HH:mm 格式）<br>3. 校验 pool 分组曲线结构                                                                                |
| 预期结果     | 1. HTTP 200，code=200<br>2. labels 为逐小时时间序列（7 天窗口应为 168 个点，含补 0 小时）<br>3. data.pool 为分组列表，每组含 name + alloc[]/usage[] 百分比数组，长度与 labels 一致<br>4. alloc/usage 数值 ∈ [0, 100]（截断生效） |

### TC-ISSUE109-004: trend 接口 gen 维度分组验证

| 字段         | 内容                                                                                             |
| ------------ | ------------------------------------------------------------------------------------------------ |
| 用例编号     | TC-ISSUE109-004                                                                                  |
| 所属功能点   | FP-3 NPU 趋势                                                                                    |
| 测试设计方法 | 等价类划分（dim=gen 有效等价类）                                                                 |
| 用例类型     | auto_api                                                                                         |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_trend_002.py` |
| 优先级       | P1                                                                                               |
| 前置条件     | 同 TC-ISSUE109-001                                                                               |
| 测试步骤     | 1. 调用 trend，dim=gen，7 天窗口<br>2. 校验 gen 分组                                             |
| 预期结果     | data.gen 为代际分组列表（实测基线：A2/A3/310P 三组），结构与 pool 维度一致                       |

### TC-ISSUE109-005: heatmap 接口服务器骨架与分配数据验证

| 字段         | 内容                                                                                                                                                                                                                    |
| ------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-005                                                                                                                                                                                                         |
| 所属功能点   | FP-4 服务器热力图                                                                                                                                                                                                       |
| 测试设计方法 | 等价类划分（有数据窗口有效等价类）                                                                                                                                                                                      |
| 用例类型     | auto_api                                                                                                                                                                                                                |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_heatmap_003.py`                                                                                                                      |
| 优先级       | P0                                                                                                                                                                                                                      |
| 前置条件     | 同 TC-ISSUE109-001；选择已确认有数据的窗口（如 2026-08-22 ~ 2026-08-23）                                                                                                                                                |
| 测试步骤     | 1. 调用 `POST /resource-operation/heatmap`，有数据窗口<br>2. 校验 servers 骨架字段<br>3. 抽样校验分配数据                                                                                                               |
| 预期结果     | 1. HTTP 200，code=200<br>2. data.servers 每台机含 ip/pool/gen + alloc[]/usage[]（alloc 元素含率值与 jobs 悬浮任务）<br>3. 有分配数据的机器 alloc 数组存在非零值（弱断言：至少 1 台机 alloc 有非零值，避免数据波动误报） |

### TC-ISSUE109-006: heatmap 接口空数据窗口补零验证

| 字段         | 内容                                                                                                                               |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-006                                                                                                                    |
| 所属功能点   | FP-4 服务器热力图                                                                                                                  |
| 测试设计方法 | 边界值分析（无数据窗口边界：停更窗口/未来日期）                                                                                    |
| 用例类型     | auto_api                                                                                                                           |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_heatmap_003.py`                                 |
| 优先级       | P1                                                                                                                                 |
| 前置条件     | 同 TC-ISSUE109-001；选择无数据窗口（未来日期或停更历史窗口）                                                                       |
| 测试步骤     | 1. 调用 heatmap，空数据窗口<br>2. 校验骨架返回与补 0 行为                                                                          |
| 预期结果     | 1. HTTP 200，不报错（实测基线：CP-09 停更窗口返回骨架补 0）<br>2. servers 骨架完整，alloc/usage 全 0<br>3. alloc_nonzero_total = 0 |

### TC-ISSUE109-007: run-analysis 有效 runId 状态机验证

| 字段         | 内容                                                                                                                                                                                    |
| ------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-007                                                                                                                                                                         |
| 所属功能点   | FP-5 运行分析                                                                                                                                                                           |
| 测试设计方法 | 状态迁移测试（任务状态机 QUEUING/RUNNING/NONE）                                                                                                                                         |
| 用例类型     | auto_api                                                                                                                                                                                |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_run_analysis_004.py`                                                                                 |
| 优先级       | P1                                                                                                                                                                                      |
| 前置条件     | 同 TC-ISSUE109-001；有效样本 runId（探索基线：e1dcd94695414ab6a2aad29bff37ad3c）                                                                                                        |
| 测试步骤     | 1. 调用 `POST /resource-operation/run-analysis`，runId + projectId=300036<br>2. 校验 labels 整点窗口<br>3. 校验 allocServers/usageServers 与 jobs 状态                                  |
| 预期结果     | 1. HTTP 200，code=200<br>2. labels 为运行时段整点序列<br>3. 每台机 values 数组与 jobs[]（taskName/queueMinutes/npuHours/states[]）结构完整<br>4. states 取值 ⊆ {QUEUING, RUNNING, NONE} |

### TC-ISSUE109-008: run-analysis 无效 runId 空数据验证

| 字段         | 内容                                                                                                        |
| ------------ | ----------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-008                                                                                             |
| 所属功能点   | FP-5 运行分析                                                                                               |
| 测试设计方法 | 错误推测法（不存在/随机 runId）                                                                             |
| 用例类型     | auto_api                                                                                                    |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_run_analysis_004.py`     |
| 优先级       | P2                                                                                                          |
| 前置条件     | 同 TC-ISSUE109-001                                                                                          |
| 测试步骤     | 1. 调用 run-analysis，runId=随机 32 位十六进制（不存在）<br>2. 校验响应                                     |
| 预期结果     | HTTP 200，code=200，data 返回空结构（labels=[] allocServers=[] usageServers=[]），不报错（实测基线：CP-11） |

### TC-ISSUE109-009: project-alloc-trend 接口曲线数据验证

| 字段         | 内容                                                                                                           |
| ------------ | -------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-009                                                                                                |
| 所属功能点   | FP-6 项目下钻                                                                                                  |
| 测试设计方法 | 等价类划分                                                                                                     |
| 用例类型     | auto_api                                                                                                       |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_project_trend_005.py`       |
| 优先级       | P1                                                                                                             |
| 前置条件     | 同 TC-ISSUE109-001；projectId=300036 有申请数据                                                                |
| 测试步骤     | 1. 调用 `POST /resource-operation/project-alloc-trend`，projectId=300036 + 7 天窗口<br>2. 校验曲线结构         |
| 预期结果     | 1. HTTP 200，code=200<br>2. 响应含逐小时申请次数与排队时长曲线数据，时间点与窗口一致（弱断言：结构与类型正确） |

### TC-ISSUE109-010: 时间参数校验决策表验证（4 接口 × 5 非法场景）

| 字段         | 内容                                                                                                                                                                                                                                  |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-010                                                                                                                                                                                                                       |
| 所属功能点   | FP-7 时间范围校验                                                                                                                                                                                                                     |
| 测试设计方法 | 决策表测试（条件：跨度超限/时间倒置/缺 endDate/非法格式 × 动作：预期错误码）                                                                                                                                                          |
| 用例类型     | auto_api                                                                                                                                                                                                                              |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_time_validate_006.py`                                                                                                                              |
| 优先级       | P1                                                                                                                                                                                                                                    |
| 前置条件     | 同 TC-ISSUE109-001                                                                                                                                                                                                                    |
| 测试步骤     | 1. 对 summary/trend/heatmap/project-alloc-trend 四接口分别传入 5 种非法时间参数：跨度超限（8 天）、时间倒置、缺 endDate、非法格式（yyyy/MM/dd）、大跨度（30 天）<br>2. 校验响应错误码<br>3. 合法 7 天窗口对照（排除服务整体故障误判） |
| 预期结果     | **目标行为**：返回 code=40001 参数异常并携带具体原因（对照同工程 @NotBlank 校验正确表现）。**当前已知缺陷基线**：实际返回 500 系统异常 = 缺陷 #115（open），本用例失败即确认缺陷存在，修复后应转为通过                                |

### TC-ISSUE109-011: 时间窗口边界值验证（6 天/7 天整）

| 字段         | 内容                                                                                                     |
| ------------ | -------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-011                                                                                          |
| 所属功能点   | FP-7 时间范围校验                                                                                        |
| 测试设计方法 | 边界值分析（上边界 7 天整、边界内 6 天）                                                                 |
| 用例类型     | auto_api                                                                                                 |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_time_validate_006.py` |
| 优先级       | P1                                                                                                       |
| 前置条件     | 同 TC-ISSUE109-001                                                                                       |
| 测试步骤     | 1. 调用 summary，时间跨度恰好 7 天（如 08-25 ~ 08-31）<br>2. 调用 summary，时间跨度 6 天<br>3. 校验响应  |
| 预期结果     | 两种边界内跨度均返回 HTTP 200 + code=200 + 正常数据（实测基线：CP-13 对照组合法 7 天窗口正常）           |

### TC-ISSUE109-012: run-analysis 必填参数校验验证

| 字段         | 内容                                                                                                                      |
| ------------ | ------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-012                                                                                                           |
| 所属功能点   | FP-7 时间范围校验（必填参数）                                                                                             |
| 测试设计方法 | 错误推测法（缺 runId / 缺 projectId）                                                                                     |
| 用例类型     | auto_api                                                                                                                  |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_run_analysis_004.py`                   |
| 优先级       | P1                                                                                                                        |
| 前置条件     | 同 TC-ISSUE109-001                                                                                                        |
| 测试步骤     | 1. 调用 run-analysis，省略 runId<br>2. 调用 run-analysis，省略 projectId<br>3. 校验响应错误码                             |
| 预期结果     | 返回 code=40001 参数异常（实测基线：CP-12 缺 runId 返回"流水线运行ID不能为空"——当前正确行为，用例保护该基线不被回归破坏） |

### TC-ISSUE109-013: 数据管道新鲜度弱断言验证

| 字段         | 内容                                                                                                                                                    |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-013                                                                                                                                         |
| 所属功能点   | FP-8 数据管道与数据正确性                                                                                                                               |
| 测试设计方法 | 边界值分析（最近 24h 数据窗口）                                                                                                                         |
| 用例类型     | auto_api                                                                                                                                                |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_data_freshness_007.py`                                               |
| 优先级       | P1                                                                                                                                                      |
| 前置条件     | 同 TC-ISSUE109-001                                                                                                                                      |
| 测试步骤     | 1. 调用 summary，窗口=昨日~今日<br>2. 校验数据非空（管道有产出）                                                                                        |
| 预期结果     | HTTP 200 + 至少一组（cloud 或 lab）返回非空资源数据（复测基线：08-30 已回填，每日连续；曾停更风险已有 Doris 核查记录，见 verification_report.md CP-14） |

### TC-ISSUE109-014: 看板页面渲染与图表完整性验证（手工）

| 字段         | 内容                                                                                                                                         |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-014                                                                                                                              |
| 所属功能点   | FP-2/3/4/5/6 UI 层                                                                                                                           |
| 测试设计方法 | 场景法（端到端页面浏览）                                                                                                                     |
| 用例类型     | manual                                                                                                                                       |
| 脚本位置     | —                                                                                                                                            |
| 优先级       | P0                                                                                                                                           |
| 前置条件     | 平台侧为测试账号开通 `npu_resource` 权限（当前 false，未开通时本用例 block）                                                                 |
| 测试步骤     | 1. 登录 beta，进入 `/apps/nRDashboard?projectId=300036`<br>2. 检查 KPI 卡片、趋势图、热力图、折线图渲染<br>3. 核对各图表与 5 个 API 数据口径 |
| 预期结果     | 页面无白屏/报错；四类图表完整渲染；数据与 API 层验证结果一致                                                                                 |

### TC-ISSUE109-015: 时间选择器与维度切换交互验证（手工）

| 字段         | 内容                                                                                         |
| ------------ | -------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-015                                                                              |
| 所属功能点   | FP-3/7 UI 层                                                                                 |
| 测试设计方法 | 场景法                                                                                       |
| 用例类型     | manual                                                                                       |
| 脚本位置     | —                                                                                            |
| 优先级       | P1                                                                                           |
| 前置条件     | 同 TC-ISSUE109-014                                                                           |
| 测试步骤     | 1. 修改时间范围选择器（7 天内切换）<br>2. 切换趋势图 pool/gen 维度<br>3. 尝试选择超 7 天跨度 |
| 预期结果     | 时间切换后图表数据联动刷新；维度切换正常；超 7 天选择被拦截并给出友好提示                    |

### TC-ISSUE109-016: 热力图悬浮与抽屉交互验证（手工）

| 字段         | 内容                                                 |
| ------------ | ---------------------------------------------------- |
| 用例编号     | TC-ISSUE109-016                                      |
| 所属功能点   | FP-4 UI 层                                           |
| 测试设计方法 | 场景法                                               |
| 用例类型     | manual                                               |
| 脚本位置     | —                                                    |
| 优先级       | P1                                                   |
| 前置条件     | 同 TC-ISSUE109-014；热力图存在有数据机器             |
| 测试步骤     | 1. 悬浮热力图色块查看任务详情<br>2. 打开机器详情抽屉 |
| 预期结果     | 悬浮显示任务名/排队时长等信息；抽屉正常打开与关闭    |

### TC-ISSUE109-017: 无权限访问拦截验证（手工）

| 字段         | 内容                                                                       |
| ------------ | -------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-017                                                            |
| 所属功能点   | FP-1 页面路由与权限守卫                                                    |
| 测试设计方法 | 场景法（无权限用户路径）                                                   |
| 用例类型     | manual                                                                     |
| 脚本位置     | —                                                                          |
| 优先级       | P1                                                                         |
| 前置条件     | 使用无 `npu_resource` 权限的账号（如当前 p_tianyan 或 pub_LIBING）         |
| 测试步骤     | 1. 登录后直接访问 `/apps/nRDashboard?projectId=300036`                     |
| 预期结果     | 重定向 noPermission 页，提示"暂无权限"（实测基线：CP-02 前端守卫生效正常） |

### TC-ISSUE109-018: 低权限账号纵向越权验证（5 接口）

| 字段         | 内容                                                                                                                                                                                                                |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-018                                                                                                                                                                                                     |
| 所属功能点   | FP-1 权限模型（后端层）                                                                                                                                                                                             |
| 测试设计方法 | 纵向越权断言（低权限调用应被拒绝）                                                                                                                                                                                  |
| 用例类型     | auto_sec（vertical_check）                                                                                                                                                                                          |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/security/beta/resource_dashboard/test_security_resource_vertical_001.py`                                                                                                       |
| 优先级       | P0                                                                                                                                                                                                                  |
| 前置条件     | beta 环境（SECURITY_ENABLED=true，仅 test 环境）；低权限账号 pub_LIBING（无 npu_resource 权限）                                                                                                                     |
| 测试步骤     | 1. 以低权限账号登录（或使用已配置 token）<br>2. 依次直连 5 个 API（summary/trend/heatmap/run-analysis/project-alloc-trend）合法参数<br>3. 断言拒绝方向                                                              |
| 预期结果     | **目标行为**（assert_denied 语义）：返回 401/403（通过）或业务拒绝 code!=200（通过）。**当前已知缺陷基线**：实际返回 200 + 全量数据 = 缺陷 #114（open，发布阻塞项），本用例失败即确认越权缺陷存在，修复后应转为通过 |

### TC-ISSUE109-019: 匿名与伪造 token 调用看板接口认证校验

| 字段         | 内容                                                                                                      |
| ------------ | --------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-019                                                                                           |
| 所属功能点   | FP-1 权限模型（认证层）                                                                                   |
| 测试设计方法 | 认证校验断言（无 token / 伪造 token）                                                                     |
| 用例类型     | auto_sec（auth_check）                                                                                    |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/security/beta/resource_dashboard/test_security_resource_auth_002.py` |
| 优先级       | P1                                                                                                        |
| 前置条件     | beta 环境                                                                                                 |
| 测试步骤     | 1. 无任何 token 直连 5 个 API<br>2. 携带伪造 token 直连                                                   |
| 预期结果     | 401/403 拒绝（实测基线：既有安全框架验证"匿名/伪造 token 服务端正确拒绝"）                                |

### TC-ISSUE109-020: 看板接口响应体敏感信息防护验证

| 字段         | 内容                                                                                                           |
| ------------ | -------------------------------------------------------------------------------------------------------------- |
| 用例编号     | TC-ISSUE109-020                                                                                                |
| 所属功能点   | 敏感信息防护                                                                                                   |
| 测试设计方法 | 敏感信息扫描（响应体/响应头）                                                                                  |
| 用例类型     | auto_sec（sensitive_data_check）                                                                               |
| 脚本位置     | `src/tests/openlibing/openlibing_ops/security/beta/resource_dashboard/test_security_resource_sensitive_003.py` |
| 优先级       | P2                                                                                                             |
| 前置条件     | beta 环境；p_tianyan 会话                                                                                      |
| 测试步骤     | 1. 调用 5 个 API 采集响应体与响应头<br>2. 扫描敏感字段模式（password/token/secret/密钥/手机号/邮箱等）         |
| 预期结果     | 响应体/响应头不泄露凭证类敏感字段（服务器 IP/池名/任务名为运营数据本身，不算泄露）                             |

## 4. 安全维度覆盖声明（规则 04 强制）

| 维度         | Marker               | 覆盖状态                  | 说明                                                                                                                                                                                                           |
| ------------ | -------------------- | ------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 认证校验     | auth_check           | ✅ 覆盖                   | TC-ISSUE109-019（匿名/伪造 token）                                                                                                                                                                             |
| CSRF 防护    | csrf_check           | ⛔ 不覆盖（声明原因）     | 5 个接口均为 POST 查询接口，无状态变更操作（查询类），CSRF 攻击收益低；且既有基线已发现 Token Cookie 缺 SameSite 属性（信息性发现，建议加 SameSite=Lax）。本 Issue 不重复设计 CSRF 用例                        |
| 纵向越权     | vertical_check       | ✅ 覆盖                   | TC-ISSUE109-018（低权限账号直连 5 API，已知缺陷 #114 核心验证）                                                                                                                                                |
| 横向越权     | horizontal_check     | ⛔ 不单独覆盖（声明原因） | 接口无任何鉴权（#114），横向（同级账号跨 projectId）与纵向（无权限账号）缺陷面完全重合——无 projectId 参数即可取全量数据。由 TC-ISSUE109-018 统一验证"应被拒绝"方向，横向隔离用例待 #114 修复（引入鉴权后）补充 |
| 传输安全     | transport_check      | ⛔ 不覆盖（声明原因）     | HTTPS 强制 + Cookie Secure/HttpOnly 已在仓库既有安全基线用例覆盖并验证通过（2026-08-11 基线），本 Issue 不重复设计                                                                                             |
| 敏感信息防护 | sensitive_data_check | ✅ 覆盖                   | TC-ISSUE109-020                                                                                                                                                                                                |

## 5. 页面对象与 Fixture 依赖

| 依赖               | 类型                       | 来源 | 用途                                                                         |
| ------------------ | -------------------------- | ---- | ---------------------------------------------------------------------------- |
| `api_client`       | conftest fixture（模块级） | 既有 | API 用例发送请求（基于浏览器会话，自动携带 Cookie）                          |
| `security_checker` | conftest fixture（模块级） | 既有 | 安全用例双身份模型（高/低权限）与断言                                        |
| `network_monitor`  | conftest fixture           | 既有 | 请求/响应采集（敏感信息扫描用）                                              |
| settings           | `core.settings`            | 既有 | URL/账号/凭证读取（禁止硬编码）                                              |
| 页面对象           | —                          | —    | 本 Issue 无 auto_ui 用例（UI 层因账号权限阻塞设计为 manual），不新建页面对象 |

## 6. 覆盖度说明

- 需求基线功能点数：8（FP-1 ~ FP-8）
- 本设计覆盖功能点数：8（100%）
- 未覆盖功能点及原因：无。性能维度不覆盖（策略 §4 已声明：Issue 无性能约束、低频查询场景）
- 已知缺陷基线：2 条（#114 越权 / #115 错误码），分别由 TC-ISSUE109-018 / TC-ISSUE109-010 形成修复验证闭环

## 7. 版本历史

| 版本 | 日期       | 修改人 | 修改内容                                                   |
| ---- | ---------- | ------ | ---------------------------------------------------------- |
| v1.0 | 2026-08-31 | mth    | 初始版本（20 条用例：13 auto_api + 3 auto_sec + 4 manual） |
