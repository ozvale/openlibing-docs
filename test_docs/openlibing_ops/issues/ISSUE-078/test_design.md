# 测试设计 - ISSUE-078

## 1. 设计概述

本Issue的测试设计基于开发设计文档（Nightly 流水线看板接口文档 v2026-07-24），覆盖以下功能点：明细失败任务类型字段及筛选、项目级汇总表格接口、主列表导出能力。

### 1.1 设计原则

- 手工用例与自动化用例分离
- 自动化用例需标注脚本位置
- 每个用例需记录用例类型
- 每个功能点需标注所采用的测试设计方法

### 1.2 用例类型定义

| 类型代码 | 类型名称 | 说明 |
|----------|----------|------|
| manual | 手工执行 | 需要人工操作执行 |
| auto_ui | 自动化-UI | UI自动化测试脚本 |
| auto_api | 自动化-API | API接口自动化测试脚本 |
| auto_perf | 自动化-性能 | 性能测试脚本 |
| auto_sec | 自动化-安全 | 安全测试脚本 |

### 1.3 测试设计方法

本设计采用以下方法（详见 AGENTS.md 规则 01 第 4 节）：

- [x] 等价类划分（Equivalence Partitioning）
- [x] 边界值分析（Boundary Value Analysis）
- [x] 决策表测试（Decision Table Testing）
- [ ] 状态迁移测试（State Transition Testing）
- [ ] 场景法（Use Case / Scenario Testing）
- [x] 错误推测法（Error Guessing）

## 2. 功能点分析

> 每个功能点必须能在开发设计文档中找到依据，禁止超出文档范围发散。

| 功能点 | 设计依据（开发设计文档章节） | 测试设计方法 | 测试类型 | 优先级 |
|--------|------------------------------|--------------|----------|--------|
| FP-01 明细新增 failedTaskType 字段 | 文档四、4.2 响应新增字段 | 等价类划分 | auto_api / auto_ui | L0 |
| FP-02 失败任务类型筛选（3 种枚举） | 文档四、4.1 failedTaskType 筛选枚举 | 等价类划分 + 决策表 | auto_api / auto_ui | L0 |
| FP-03 失败类型判定优先级 | 文档四、4.2 判定规则（构建>测试>其他） | 决策表测试 | auto_api | L1 |
| FP-04 项目级汇总接口（26 字段） | 文档三、3.1 查询与响应字段 | 等价类划分 + 字段完整性 | auto_api | L0 |
| FP-05 汇总返回结构（total 0/1） | 文档三、3.1 返回 PageResult 结构说明 | 边界值分析 | auto_api | L1 |
| FP-06 主列表导出 xlsx 文件流 | 文档二、2.2 导出 | 等价类划分 | auto_api / auto_ui | L0 |
| FP-07 汇总/明细暂不支持导出 | 文档五、变更提醒#2 | 错误推测法 | auto_ui | L1 |
| FP-08 汇总/明细接口响应时间 | 需求非功能要求（沿用通用阈值 avg<3s） | 错误推测法 | auto_perf | L1 |
| FP-09 汇总/导出接口未认证拒绝 | AGENTS.md 规则04 安全测试 | 等价类划分 | auto_sec | L1 |
| FP-10 认证校验（伪造 token） | AGENTS.md 规则04 4.2 认证校验 | 等价类划分 | auto_sec | L1 |
| FP-11 横向越权（跨项目数据隔离） | AGENTS.md 规则04 4.2 横向越权 | 等价类划分 | auto_sec | L1 |
| FP-12 传输安全（HTTPS + Cookie 属性） | AGENTS.md 规则04 4.2 传输安全 | 属性校验 | auto_sec | L1 |
| FP-13 CSRF 防护（导出接口变更请求） | AGENTS.md 规则04 4.2 CSRF 防护 | 等价类划分 | auto_sec | L1 |
| FP-14 敏感信息防护（响应不泄露凭证） | AGENTS.md 规则04 4.2 敏感信息防护 | 等价类划分 | auto_sec | L1 |

### 2.1 接口清单（设计依据）

| 接口 | 方法 | 路径 | category | 说明 |
|------|------|------|----------|------|
| 主列表 | POST | /common/detail | nightly-dashboard | 已有，新增导出 |
| 项目级汇总 | POST | /common/detail | nightly-dashboard-summary | 新增 |
| 流水线运行明细 | POST | /common/detail | nightly-dashboard-detail | 新增 failedTaskType |
| 主列表导出 | POST | /common/export/nightly-dashboard | — | 新增 |

## 2.2 安全测试设计（6 维度覆盖声明）

> 依据 AGENTS.md 规则 04 与 `.agents/skills/security-testing/SKILL.md`，对本期 3 个接口（汇总/明细/导出）逐一声明 6 个安全维度覆盖状态。

### 安全维度覆盖矩阵

| 安全维度 | 覆盖接口 | 覆盖用例 | 状态 | 不覆盖原因 |
|----------|----------|----------|------|-----------|
| 认证校验（auth_check） | 汇总/明细/导出 | TC-ISSUE078-016（未认证）、TC-ISSUE078-017（伪造 token） | ✅ 已覆盖 | — |
| 横向越权（horizontal_check） | 汇总/明细（跨 projectId） | TC-ISSUE078-018 | ✅ 已覆盖 | — |
| 纵向越权（vertical_check） | — | — | ⚠️ 豁免 | 低权限账号 `SECURITY_LOW_PRIV_PASS` 未配置，且 3 个接口均为登录用户可访问的数据查询/导出接口（非 admin 专属），无纵向权限差异 |
| 传输安全（transport_check） | 汇总/明细/导出 | TC-ISSUE078-019 | ✅ 已覆盖 | — |
| CSRF 防护（csrf_check） | 导出（变更类） | TC-ISSUE078-020 | ✅ 已覆盖 | 汇总/明细为查询类接口（POST 但无状态变更），按 security-testing 规范仅对变更类请求覆盖 CSRF |
| 敏感信息防护（sensitive_data_check） | 汇总/明细/导出 | TC-ISSUE078-021 | ✅ 已覆盖 | — |

> **设计评审说明**：纵向越权维度因低权限账号密码未配置（`SECURITY_LOW_PRIV_PASS` 为空，凭证经 Secrets 注入）而豁免；且本期接口对登录用户开放查询，不涉及 admin 专属操作。该豁免需在设计评审（人工审核闸门）中向测试人员说明并确认。

### 安全测试接口清单

| 接口 | 方法 | 路径 | 安全关注点 |
|------|------|------|-----------|
| 项目级汇总 | POST | /gateway/openlibing-ops/common/detail | 认证/横向越权/传输/敏感信息 |
| 流水线明细 | POST | /gateway/openlibing-ops/common/detail | 认证/横向越权/传输/敏感信息 |
| 主列表导出 | POST | /gateway/openlibing-ops/common/export/nightly-dashboard | 认证/CSRF/传输 |

### 双身份与凭证

| 角色 | 账号 | 用途 |
|------|------|------|
| 高权限 | `p_tianyan`（TEST_ENV 账号） | 对照基线：验证接口对合法用户可用 |
| 低权限 | `pub_LIBING` | 纵向越权（本期豁免，凭证未配置） |

## 3. 用例设计

### TC-ISSUE078-001: 明细接口返回 failedTaskType 字段

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-001 |
| 所属功能点 | FP-01 明细新增 failedTaskType 字段 |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_001.py |
| 优先级 | L0 |
| 前置条件 | 已登录 test 环境；存在流水线运行数据 |
| 测试步骤 | 1. 调用 POST /common/detail，category=nightly-dashboard-detail<br>2. 验证 HTTP 200 且 code==200<br>3. 验证每条记录包含 failedTaskType 字段<br>4. 验证 failedTaskType 取值在合法枚举内（构建任务/测试任务/其他任务/流水线未失败） |
| 预期结果 | 每条明细记录均含 failedTaskType 且取值合法 |

### TC-ISSUE078-002: 失败任务类型筛选-构建任务

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-002 |
| 所属功能点 | FP-02 失败任务类型筛选 |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_002.py |
| 优先级 | L0 |
| 前置条件 | 已登录 test 环境 |
| 测试步骤 | 1. 调用明细接口，failedTaskType="构建任务"<br>2. 验证 HTTP 200 且 code==200<br>3. 验证返回记录（若有）的 failedTaskType 均为"构建任务" |
| 预期结果 | 筛选"构建任务"仅返回构建任务失败的运行 |

### TC-ISSUE078-003: 失败任务类型筛选-测试任务

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-003 |
| 所属功能点 | FP-02 失败任务类型筛选 |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_002.py |
| 优先级 | L0 |
| 前置条件 | 已登录 test 环境 |
| 测试步骤 | 1. 调用明细接口，failedTaskType="测试任务"<br>2. 验证 HTTP 200 且 code==200<br>3. 验证返回记录（若有）的 failedTaskType 均为"测试任务" |
| 预期结果 | 筛选"测试任务"仅返回测试任务失败的运行 |

### TC-ISSUE078-004: 失败任务类型筛选-其他任务

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-004 |
| 所属功能点 | FP-02 失败任务类型筛选 |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_002.py |
| 优先级 | L0 |
| 前置条件 | 已登录 test 环境 |
| 测试步骤 | 1. 调用明细接口，failedTaskType="其他任务"<br>2. 验证 HTTP 200 且 code==200<br>3. 验证返回记录（若有）的 failedTaskType 均为"其他任务" |
| 预期结果 | 筛选"其他任务"仅返回其他任务失败的运行 |

### TC-ISSUE078-005: 失败任务类型不传/非法值不过滤

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-005 |
| 所属功能点 | FP-02 失败任务类型筛选 |
| 测试设计方法 | 边界值分析 + 错误推测法 |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_002.py |
| 优先级 | L1 |
| 前置条件 | 已登录 test 环境 |
| 测试步骤 | 1. 调用明细接口，不传 failedTaskType<br>2. 调用明细接口，failedTaskType="非法值"<br>3. 验证两种请求均返回 HTTP 200 且 code==200（不过滤） |
| 预期结果 | 不传/非法值时不进行失败类型过滤，正常返回明细 |

### TC-ISSUE078-006: 项目级汇总接口返回结构验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-006 |
| 所属功能点 | FP-04 项目级汇总接口 |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_summary_001.py |
| 优先级 | L0 |
| 前置条件 | 已登录 test 环境；projectId=300057 存在数据 |
| 测试步骤 | 1. 调用 POST /common/detail，category=nightly-dashboard-summary，projectId=300057，startDate/endDate 近一个月<br>2. 验证 HTTP 200 且 code==200<br>3. 验证 data 为 PageResult 结构（records/total/page/pageSize）<br>4. 验证 total 为 0 或 1，records 长度 0 或 1 |
| 预期结果 | 汇总接口返回 PageResult 结构，total 为 0 或 1 |

### TC-ISSUE078-007: 项目级汇总接口字段完整性（26 字段）

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-007 |
| 所属功能点 | FP-04 项目级汇总接口 |
| 测试设计方法 | 等价类划分 + 字段完整性 |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_summary_001.py |
| 优先级 | L0 |
| 前置条件 | 已登录 test 环境；汇总有数据（records 长度 1） |
| 测试步骤 | 1. 调用汇总接口获取 records[0]<br>2. 验证存在 projectId、projectName 字段<br>3. 验证存在 E2E 时长 5 字段（actualDurationP50/P90/P95/Avg/MaxMinutes）<br>4. 验证存在 efficiency 时长 5 字段<br>5. 验证存在 buildTime/testTime 各 5 字段<br>6. 验证存在 caseTotalCountP0/caseReleaseRateP0/casePassRateP0/casePassRate |
| 预期结果 | 汇总记录含 26 个字段且均为 number 类型 |

### TC-ISSUE078-008: 汇总接口无 projectId 参数行为

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-008 |
| 所属功能点 | FP-04 项目级汇总接口 |
| 测试设计方法 | 边界值分析 |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_summary_001.py |
| 优先级 | L1 |
| 前置条件 | 已登录 test 环境 |
| 测试步骤 | 1. 调用汇总接口，不传 projectId 仅传日期范围<br>2. 验证 HTTP 200 且 code==200<br>3. 验证 data 结构仍为 PageResult（total 0 或 1） |
| 预期结果 | 不传 projectId 时接口正常响应（返回 0 或 1 条汇总） |

### TC-ISSUE078-009: 主列表导出接口返回 xlsx 文件流

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-009 |
| 所属功能点 | FP-06 主列表导出 |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_export_001.py |
| 优先级 | L0 |
| 前置条件 | 已登录 test 环境 |
| 测试步骤 | 1. 调用 POST /common/export/nightly-dashboard，参数 projectId/startDate/endDate<br>2. 验证 HTTP 200<br>3. 验证响应 Content-Type 含 spreadsheetml 或 octet-stream<br>4. 验证响应体为二进制数据（非 JSON） |
| 预期结果 | 导出接口返回 xlsx 二进制文件流 |

### TC-ISSUE078-010: UI-失败任务类型列存在及取值合法

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-010 |
| 所属功能点 | FP-01 明细 failedTaskType 字段 |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_ui |
| 脚本位置 | src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/failure_type/test_ui_nightly_dashboard_failure_type_beta_001.py |
| 优先级 | L0 |
| 前置条件 | 已登录；已在 mindie 项目 Nightly 看板页面；iframe 已加载 |
| 测试步骤 | 1. 依赖 mindie_dashboard fixture<br>2. 验证表格包含"失败任务类型"列<br>3. 获取各行失败任务类型值<br>4. 验证值为合法枚举（构建/测试/其他/流水线未失败） |
| 预期结果 | 失败任务类型列存在且所有取值合法 |

### TC-ISSUE078-011: UI-未失败流水线展示"流水线未失败"

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-011 |
| 所属功能点 | FP-01 明细 failedTaskType 字段 |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_ui |
| 脚本位置 | src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/failure_type/test_ui_nightly_dashboard_failure_type_beta_001.py |
| 优先级 | L1 |
| 前置条件 | 已登录；已在 mindie 项目 Nightly 看板页面；iframe 已加载 |
| 测试步骤 | 1. 依赖 mindie_dashboard fixture<br>2. 获取失败任务类型列所有值<br>3. 验证存在"流水线未失败"或失败类型值 |
| 预期结果 | 成功流水线展示"流水线未失败"，失败流水线展示对应失败类型 |

### TC-ISSUE078-012: UI-失败任务类型筛选功能

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-012 |
| 所属功能点 | FP-02 失败任务类型筛选 |
| 测试设计方法 | 决策表测试 |
| 用例类型 | auto_ui |
| 脚本位置 | src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/failure_type/test_ui_nightly_dashboard_failure_type_beta_002.py |
| 优先级 | L0 |
| 前置条件 | 已登录；已在 mindie 项目 Nightly 看板页面；iframe 已加载；表格有数据 |
| 测试步骤 | 1. 依赖 mindie_dashboard fixture<br>2. 点击失败任务类型列筛选按钮<br>3. 获取筛选选项（应含构建任务/测试任务/其他任务）<br>4. 选择第一个选项<br>5. 验证筛选后各行值匹配筛选条件 |
| 预期结果 | 筛选选项存在，筛选后数据正确过滤 |

### TC-ISSUE078-013: UI-主列表导出按钮及下载验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-013 |
| 所属功能点 | FP-06 主列表导出 |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_ui |
| 脚本位置 | src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/export/test_ui_nightly_dashboard_export_beta_001.py |
| 优先级 | L0 |
| 前置条件 | 已登录；已在 mindie 项目 Nightly 看板页面；iframe 已加载 |
| 测试步骤 | 1. 依赖 mindie_dashboard fixture<br>2. 验证导出按钮存在<br>3. 点击导出按钮<br>4. 捕获下载文件<br>5. 验证文件名以 .xlsx 结尾 |
| 预期结果 | 导出按钮存在，点击后触发 xlsx 文件下载 |

### TC-ISSUE078-014: UI-项目级汇总无导出、流水线级有导出

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-014 |
| 所属功能点 | FP-07 汇总/明细暂不支持导出 |
| 测试设计方法 | 错误推测法 |
| 用例类型 | auto_ui |
| 脚本位置 | src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/export/test_ui_nightly_dashboard_export_beta_001.py |
| 优先级 | L1 |
| 前置条件 | 已登录；已在 mindie 项目 Nightly 看板页面；iframe 已加载 |
| 测试步骤 | 1. 依赖 mindie_dashboard fixture<br>2. 验证项目级汇总区域无导出按钮<br>3. 验证流水线级汇总区域有导出按钮 |
| 预期结果 | 项目级汇总无导出按钮，流水线级汇总有导出按钮 |

### TC-ISSUE078-015: 汇总接口响应时间验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-015 |
| 所属功能点 | FP-08 汇总接口响应时间 |
| 测试设计方法 | 错误推测法 |
| 用例类型 | auto_perf |
| 脚本位置 | src/tests/openlibing/openlibing_ops/performance/beta/nightly_dashboard/test_performance_nightly_dashboard_summary_001.py |
| 优先级 | L1 |
| 前置条件 | 已登录 test 环境 |
| 测试步骤 | 1. 重复调用汇总接口 10 次<br>2. 统计 avg/P95 响应时间<br>3. 验证 avg<3s 且 P95<5s，error_rate 为 0 |
| 预期结果 | 汇总接口平均响应 < 3s，P95 < 5s，无错误 |

### TC-ISSUE078-016: 汇总/导出接口未认证访问拒绝

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-016 |
| 所属功能点 | FP-09 安全验证 |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_sec |
| 脚本位置 | src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_001.py |
| 优先级 | L1 |
| 前置条件 | 已登录 test 环境 |
| 测试步骤 | 1. 不携带 token 调用汇总接口<br>2. 不携带 token 调用导出接口<br>3. 验证均返回 401/403 或业务拒绝 |
| 预期结果 | 未认证访问汇总/导出接口被拒绝 |

### TC-ISSUE078-017: 认证校验-伪造 token 请求

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-017 |
| 所属功能点 | FP-10 认证校验（伪造 token） |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_sec |
| 脚本位置 | src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_001.py |
| 优先级 | L1 |
| 前置条件 | 已登录 test 环境 |
| 测试步骤 | 1. 携带伪造 Authorization: Bearer fake_token 调用汇总接口<br>2. 携带伪造 token 调用明细接口<br>3. 携带伪造 token 调用导出接口<br>4. 验证均被拒绝（401/403/业务拒绝） |
| 预期结果 | 伪造 token 请求汇总/明细/导出接口均被拒绝 |

### TC-ISSUE078-018: 横向越权-跨项目数据隔离

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-018 |
| 所属功能点 | FP-11 横向越权（跨项目数据隔离） |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_sec |
| 脚本位置 | src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_002.py |
| 优先级 | L1 |
| 前置条件 | 已登录 test 环境；存在多个可访问项目 |
| 测试步骤 | 1. 以当前用户调用汇总接口 projectId=300036（MindIE）<br>2. 调用汇总接口 projectId=3（openlibing）<br>3. 验证两请求均正常返回且数据不同（项目数据隔离）<br>4. 尝试访问无权限 projectId，验证被拒绝或返回空 |
| 预期结果 | 不同 projectId 返回对应项目数据；无权限项目不泄露他人数据 |

### TC-ISSUE078-019: 传输安全-HTTPS 与 Cookie 属性

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-019 |
| 所属功能点 | FP-12 传输安全 |
| 测试设计方法 | 属性校验 |
| 用例类型 | auto_sec |
| 脚本位置 | src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_003.py |
| 优先级 | L1 |
| 前置条件 | 已登录 test 环境 |
| 测试步骤 | 1. 验证 3 个接口 URL 均为 https<br>2. 调用接口并检查 Set-Cookie 的 Secure/HttpOnly 属性<br>3. 汇总检查结果 |
| 预期结果 | 接口使用 HTTPS；会话 Cookie 具备 Secure/HttpOnly 属性 |

### TC-ISSUE078-020: CSRF 防护-导出接口变更请求

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-020 |
| 所属功能点 | FP-13 CSRF 防护 |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_sec |
| 脚本位置 | src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_003.py |
| 优先级 | L1 |
| 前置条件 | 已登录 test 环境 |
| 测试步骤 | 1. 调用导出接口时移除 CSRF token 头<br>2. 调用导出接口时携带伪造 CSRF token<br>3. 验证变更请求被拒绝（401/403/业务拒绝） |
| 预期结果 | 缺失/伪造 CSRF token 的导出请求被拒绝 |

### TC-ISSUE078-021: 敏感信息防护-响应不泄露凭证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE078-021 |
| 所属功能点 | FP-14 敏感信息防护 |
| 测试设计方法 | 等价类划分 |
| 用例类型 | auto_sec |
| 脚本位置 | src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_003.py |
| 优先级 | L1 |
| 前置条件 | 已登录 test 环境 |
| 测试步骤 | 1. 调用汇总/明细/导出接口获取响应<br>2. 检查响应体与响应头<br>3. 验证不包含 token/password/secret/密钥等敏感字段值 |
| 预期结果 | 接口响应不泄露 token、密码、密钥、Cookie 等敏感信息 |

## 4. 覆盖度说明

- 开发设计文档覆盖功能点数：3 大项（失败类型字段+筛选、汇总表格、导出）
- 本设计覆盖功能点数：3 大项全部覆盖（功能点 9 个 + 安全维度 5 个，共 21 条用例）
- 安全维度覆盖：6 维度中 5 维度已覆盖，纵向越权因低权限凭证未配置豁免（见 2.2 安全测试设计）
- 未覆盖功能点及原因：BUILD 标签变更（"编译任务"→"构建任务"）为前端文案变更，不在本期自动化范围，通过一致性检查备注说明

## 5. 版本历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0 | 2026-08-11 | tester-a | 初始版本 |
| v1.1 | 2026-08-12 | tester-a | 补充安全测试设计（6 维度覆盖声明），新增 TC-ISSUE078-017~021 安全用例 |
