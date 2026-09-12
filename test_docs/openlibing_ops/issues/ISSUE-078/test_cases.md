# 测试用例 - ISSUE-078

> **Issue编号**: ISSUE-078
> **Issue标题**: 【蓝区】 Nightly流水线看板增加汇总数据展示、明细增加失败类型和导出能力
> **创建日期**: 2026-08-11
> **用例总数**: 21
> **手工用例**: 0
> **自动化用例**: 21
> **复用旧用例**: 0
> **新设计用例**: 21

### 执行信息

> 由**测试人员**填写。自动化用例的 Action 链接在此**统一填写一个**，无需每条用例重复填写。

| 字段                 | 内容                                                    |
| -------------------- | ------------------------------------------------------- |
| 自动化执行Action链接 | 本地 pytest 执行（gitcode action 待测试人员确认后补充） |
| 手工执行人           | —                                                       |
| 执行日期             | 2026-08-11                                              |

---

## 用例列表

| 用例编号        | 用例标题                            | 所属功能点 | 用例类型  | 用例来源 | 用例等级 | 脚本位置                                                                                                                      | 状态   |
| --------------- | ----------------------------------- | ---------- | --------- | -------- | -------- | ----------------------------------------------------------------------------------------------------------------------------- | ------ |
| TC-ISSUE078-001 | 明细接口返回 failedTaskType 字段    | FP-01      | auto_api  | new      | L0       | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_001.py                       | active |
| TC-ISSUE078-002 | 失败任务类型筛选-构建任务           | FP-02      | auto_api  | new      | L0       | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_002.py                       | active |
| TC-ISSUE078-003 | 失败任务类型筛选-测试任务           | FP-02      | auto_api  | new      | L0       | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_002.py                       | active |
| TC-ISSUE078-004 | 失败任务类型筛选-其他任务           | FP-02      | auto_api  | new      | L0       | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_002.py                       | active |
| TC-ISSUE078-005 | 失败任务类型不传/非法值不过滤       | FP-02      | auto_api  | new      | L1       | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_002.py                       | active |
| TC-ISSUE078-006 | 项目级汇总接口返回结构验证          | FP-04      | auto_api  | new      | L0       | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_summary_001.py                      | active |
| TC-ISSUE078-007 | 项目级汇总接口字段完整性（26 字段） | FP-04      | auto_api  | new      | L0       | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_summary_001.py                      | active |
| TC-ISSUE078-008 | 汇总接口无 projectId 参数行为       | FP-04      | auto_api  | new      | L1       | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_summary_001.py                      | active |
| TC-ISSUE078-009 | 主列表导出接口返回 xlsx 文件流      | FP-06      | auto_api  | new      | L0       | src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_export_001.py                       | active |
| TC-ISSUE078-010 | UI-失败任务类型列存在及取值合法     | FP-01      | auto_ui   | new      | L0       | src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/failure_type/test_ui_nightly_dashboard_failure_type_beta_001.py | active |
| TC-ISSUE078-011 | UI-未失败流水线展示"流水线未失败"   | FP-01      | auto_ui   | new      | L1       | src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/failure_type/test_ui_nightly_dashboard_failure_type_beta_001.py | active |
| TC-ISSUE078-012 | UI-失败任务类型筛选功能             | FP-02      | auto_ui   | new      | L0       | src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/failure_type/test_ui_nightly_dashboard_failure_type_beta_002.py | active |
| TC-ISSUE078-013 | UI-主列表导出按钮及下载验证         | FP-06      | auto_ui   | new      | L0       | src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/export/test_ui_nightly_dashboard_export_beta_001.py             | active |
| TC-ISSUE078-014 | UI-项目级汇总无导出、流水线级有导出 | FP-07      | auto_ui   | new      | L1       | src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/export/test_ui_nightly_dashboard_export_beta_001.py             | active |
| TC-ISSUE078-015 | 汇总接口响应时间验证                | FP-08      | auto_perf | new      | L1       | src/tests/openlibing/openlibing_ops/performance/beta/nightly_dashboard/test_performance_nightly_dashboard_summary_001.py      | active |
| TC-ISSUE078-016 | 汇总/导出接口未认证访问拒绝         | FP-09      | auto_sec  | new      | L1       | src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_001.py                    | active |
| TC-ISSUE078-017 | 认证校验-伪造 token 请求            | FP-10      | auto_sec  | new      | L1       | src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_001.py                    | active |
| TC-ISSUE078-018 | 横向越权-跨项目数据隔离             | FP-11      | auto_sec  | new      | L1       | src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_002.py                    | active |
| TC-ISSUE078-019 | 传输安全-HTTPS 与 Cookie 属性       | FP-12      | auto_sec  | new      | L1       | src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_003.py                    | active |
| TC-ISSUE078-020 | CSRF 防护-导出接口变更请求          | FP-13      | auto_sec  | new      | L1       | src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_003.py                    | active |
| TC-ISSUE078-021 | 敏感信息防护-响应不泄露凭证         | FP-14      | auto_sec  | new      | L1       | src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_003.py                    | active |

> **用例来源说明**：
>
> - `reuse`：复用已有用例，引用已有用例编号（在详情中"引用已有用例"字段标注），不重新归档
> - `new`：新设计用例，必须按规则 5.3 归档到模块用例文件与 case_list.md

---

## 执行结果记录

> 本节由**测试人员**确认后生效。以下为本地 pytest 实测结果（2026-08-11），Action 链接与缺陷 issue 待测试人员补充。

| 用例编号        | 用例类型  | 执行结果 | 缺陷issue        | 备注                                                                                  |
| --------------- | --------- | -------- | ---------------- | ------------------------------------------------------------------------------------- |
| TC-ISSUE078-001 | auto_api  | pass     | —                | 明细接口正常返回 failedTaskType 且取值合法                                            |
| TC-ISSUE078-002 | auto_api  | skip     | —                | 时间范围内无"构建任务"失败记录，跳过一致性校验                                        |
| TC-ISSUE078-003 | auto_api  | skip     | —                | 时间范围内无"测试任务"失败记录，跳过一致性校验                                        |
| TC-ISSUE078-004 | auto_api  | pass     | —                | 筛选"其他任务"返回记录均匹配                                                          |
| TC-ISSUE078-005 | auto_api  | fail     | [待测试人员创建] | 非法 failedTaskType 返回业务 code=500（文档约定"其他值不过滤"），疑似后端未容错       |
| TC-ISSUE078-006 | auto_api  | pass     | —                | 汇总接口返回 PageResult 结构，total 0/1 符合文档                                      |
| TC-ISSUE078-007 | auto_api  | pass     | —                | 26 字段完整；注意实测字段名为 caseReleaseCountP0（文档为 caseTotalCountP0），语义一致 |
| TC-ISSUE078-008 | auto_api  | fail     | [待测试人员创建] | 不传 projectId 返回业务 code=500（文档声明 projectId 可选），疑似后端缺省处理缺陷     |
| TC-ISSUE078-009 | auto_api  | pass     | —                | 导出接口返回 xlsx 文件流，Content-Type 正确                                           |
| TC-ISSUE078-010 | auto_ui   | pass     | —                | 失败任务类型列存在且取值合法                                                          |
| TC-ISSUE078-011 | auto_ui   | pass     | —                | 成功流水线展示"流水线未失败"                                                          |
| TC-ISSUE078-012 | auto_ui   | pass     | —                | 筛选选项存在，筛选后数据正确过滤                                                      |
| TC-ISSUE078-013 | auto_ui   | pass     | —                | 导出按钮存在，点击触发 xlsx 下载                                                      |
| TC-ISSUE078-014 | auto_ui   | pass     | —                | 项目级汇总无导出按钮，流水线级有导出按钮                                              |
| TC-ISSUE078-015 | auto_perf | pass     | —                | 汇总接口 avg<3s，P95<5s，error_rate 0                                                 |
| TC-ISSUE078-016 | auto_sec  | pass     | —                | 未认证访问汇总/导出接口均被拒绝（无 cookie 独立请求验证 401）                         |
| TC-ISSUE078-017 | auto_sec  | pass     | —                | 无会话下伪造 token 请求汇总/明细/导出接口均返回 401                                   |
| TC-ISSUE078-018 | auto_sec  | pass     | —                | 不同 projectId 数据隔离正确，无权限项目不泄露数据                                     |
| TC-ISSUE078-019 | auto_sec  | fail     | [待测试人员创建] | 会话 Cookie 缺 Secure/HttpOnly 属性（token、csrf-token-open-li-bing 均缺）            |
| TC-ISSUE078-020 | auto_sec  | fail     | [待测试人员创建] | 导出接口无 CSRF 防护：缺失/伪造 CSRF token 均返回有效 xlsx                            |
| TC-ISSUE078-021 | auto_sec  | pass     | —                | 汇总接口响应体/响应头未泄露敏感字段                                                   |

> **执行结果取值**：pass（通过）/ fail（失败）/ block（阻塞）/ skip（跳过）
> **填写要求**：
>
> - fail 用例必须创建并填写缺陷issue（gitcode 缺陷 issue 链接），否则不得生成报告
> - fail/block 用例必须填写 备注 说明原因

---

## 自动化用例详情

### TC-ISSUE078-001: 明细接口返回 failedTaskType 字段

- **所属功能点**: FP-01 明细新增 failedTaskType 字段
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_001.py`
- **用例等级**: L0
- **前置条件**: 已登录 test 环境；存在流水线运行数据
- **测试步骤**:
  1. 调用 POST /common/detail，category=nightly-dashboard-detail，带日期范围
  2. 验证 HTTP 200 且 code==200
  3. 验证每条记录包含 failedTaskType 字段
  4. 验证 failedTaskType 取值在合法枚举内
- **预期结果**: 每条明细记录均含 failedTaskType 且取值合法
- **执行结果**: pass

### TC-ISSUE078-002: 失败任务类型筛选-构建任务

- **所属功能点**: FP-02 失败任务类型筛选
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_002.py`
- **用例等级**: L0
- **前置条件**: 已登录 test 环境
- **测试步骤**:
  1. 调用明细接口，failedTaskType="构建任务"
  2. 验证 HTTP 200 且 code==200
  3. 验证返回记录（若有）的 failedTaskType 均为"构建任务"
- **预期结果**: 筛选"构建任务"仅返回构建任务失败的运行
- **执行结果**: skip（无构建任务失败记录）

### TC-ISSUE078-003: 失败任务类型筛选-测试任务

- **所属功能点**: FP-02 失败任务类型筛选
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_002.py`
- **用例等级**: L0
- **前置条件**: 已登录 test 环境
- **测试步骤**:
  1. 调用明细接口，failedTaskType="测试任务"
  2. 验证 HTTP 200 且 code==200
  3. 验证返回记录（若有）的 failedTaskType 均为"测试任务"
- **预期结果**: 筛选"测试任务"仅返回测试任务失败的运行
- **执行结果**: skip（无测试任务失败记录）

### TC-ISSUE078-004: 失败任务类型筛选-其他任务

- **所属功能点**: FP-02 失败任务类型筛选
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_002.py`
- **用例等级**: L0
- **前置条件**: 已登录 test 环境
- **测试步骤**:
  1. 调用明细接口，failedTaskType="其他任务"
  2. 验证 HTTP 200 且 code==200
  3. 验证返回记录（若有）的 failedTaskType 均为"其他任务"
- **预期结果**: 筛选"其他任务"仅返回其他任务失败的运行
- **执行结果**: pass

### TC-ISSUE078-005: 失败任务类型不传/非法值不过滤

- **所属功能点**: FP-02 失败任务类型筛选
- **测试设计方法**: 边界值分析 + 错误推测法
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_detail_002.py`
- **用例等级**: L1
- **前置条件**: 已登录 test 环境
- **测试步骤**:
  1. 调用明细接口，不传 failedTaskType
  2. 调用明细接口，failedTaskType="非法值"
  3. 验证两种请求均返回 HTTP 200 且 code==200（不过滤）
- **预期结果**: 不传/非法值时不进行失败类型过滤，正常返回明细
- **执行结果**: fail（不传正常；非法值返回业务 code=500，与文档"其他值不过滤"不符，疑似后端缺陷）

### TC-ISSUE078-006: 项目级汇总接口返回结构验证

- **所属功能点**: FP-04 项目级汇总接口
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_summary_001.py`
- **用例等级**: L0
- **前置条件**: 已登录 test 环境；projectId=300036 存在数据
- **测试步骤**:
  1. 调用 POST /common/detail，category=nightly-dashboard-summary，projectId=300036，日期近一个月
  2. 验证 HTTP 200 且 code==200
  3. 验证 data 为 PageResult 结构（records/total/page/pageSize）
  4. 验证 total 为 0 或 1，records 长度 0 或 1
- **预期结果**: 汇总接口返回 PageResult 结构，total 为 0 或 1
- **执行结果**: pass

### TC-ISSUE078-007: 项目级汇总接口字段完整性（26 字段）

- **所属功能点**: FP-04 项目级汇总接口
- **测试设计方法**: 等价类划分 + 字段完整性
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_summary_001.py`
- **用例等级**: L0
- **前置条件**: 已登录 test 环境；汇总有数据（records 长度 1）
- **测试步骤**:
  1. 调用汇总接口获取 records[0]
  2. 验证存在 projectId、projectName 字段
  3. 验证存在 actualDuration 系列 5 字段
  4. 验证存在 efficiencyDuration 系列 5 字段
  5. 验证存在 buildTime/testTime 系列各 5 字段
  6. 验证存在 caseReleaseCountP0/caseReleaseRateP0/casePassRateP0/casePassRate
- **预期结果**: 汇总记录含 26 个字段且均为 number 类型
- **执行结果**: pass（注意：实测字段名为 caseReleaseCountP0，与文档 caseTotalCountP0 存在命名差异，语义一致）

### TC-ISSUE078-008: 汇总接口无 projectId 参数行为

- **所属功能点**: FP-04 项目级汇总接口
- **测试设计方法**: 边界值分析
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_summary_001.py`
- **用例等级**: L1
- **前置条件**: 已登录 test 环境
- **测试步骤**:
  1. 调用汇总接口，不传 projectId 仅传日期范围
  2. 验证 HTTP 200 且 code==200
  3. 验证 data 结构仍为 PageResult（total 0 或 1）
- **预期结果**: 不传 projectId 时接口正常响应
- **执行结果**: fail（不传 projectId 返回业务 code=500"系统异常"，与文档声明"projectId 可选"不符，疑似后端缺陷）

### TC-ISSUE078-009: 主列表导出接口返回 xlsx 文件流

- **所属功能点**: FP-06 主列表导出
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/nightly_dashboard/test_api_nightly_dashboard_export_001.py`
- **用例等级**: L0
- **前置条件**: 已登录 test 环境
- **测试步骤**:
  1. 调用 POST /common/export/nightly-dashboard，参数 projectId/startDate/endDate
  2. 验证 HTTP 200
  3. 验证响应 Content-Type 含 spreadsheetml 或 octet-stream
  4. 验证响应体为二进制数据（非 JSON）
- **预期结果**: 导出接口返回 xlsx 二进制文件流
- **执行结果**: pass

### TC-ISSUE078-010: UI-失败任务类型列存在及取值合法

- **所属功能点**: FP-01 明细 failedTaskType 字段
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/failure_type/test_ui_nightly_dashboard_failure_type_beta_001.py`
- **用例等级**: L0
- **前置条件**: 已登录；已在 mindie 项目 Nightly 看板页面；iframe 已加载
- **测试步骤**:
  1. 依赖 mindie_dashboard fixture
  2. 验证表格包含"失败任务类型"列
  3. 获取各行失败任务类型值
  4. 验证值为合法枚举
- **预期结果**: 失败任务类型列存在且所有取值合法
- **执行结果**: pass

### TC-ISSUE078-011: UI-未失败流水线展示"流水线未失败"

- **所属功能点**: FP-01 明细 failedTaskType 字段
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/failure_type/test_ui_nightly_dashboard_failure_type_beta_001.py`
- **用例等级**: L1
- **前置条件**: 已登录；已在 mindie 项目 Nightly 看板页面；iframe 已加载
- **测试步骤**:
  1. 依赖 mindie_dashboard fixture
  2. 获取失败任务类型列所有值
  3. 验证存在"流水线未失败"或失败类型值
- **预期结果**: 成功流水线展示"流水线未失败"，失败流水线展示对应失败类型
- **执行结果**: pass

### TC-ISSUE078-012: UI-失败任务类型筛选功能

- **所属功能点**: FP-02 失败任务类型筛选
- **测试设计方法**: 决策表测试
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/failure_type/test_ui_nightly_dashboard_failure_type_beta_002.py`
- **用例等级**: L0
- **前置条件**: 已登录；已在 mindie 项目 Nightly 看板页面；iframe 已加载；表格有数据
- **测试步骤**:
  1. 依赖 mindie_dashboard fixture
  2. 点击失败任务类型列筛选按钮
  3. 获取筛选选项（应含构建任务/测试任务/其他任务）
  4. 选择第一个选项
  5. 验证筛选后各行值匹配筛选条件
- **预期结果**: 筛选选项存在，筛选后数据正确过滤
- **执行结果**: pass

### TC-ISSUE078-013: UI-主列表导出按钮及下载验证

- **所属功能点**: FP-06 主列表导出
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/export/test_ui_nightly_dashboard_export_beta_001.py`
- **用例等级**: L0
- **前置条件**: 已登录；已在 mindie 项目 Nightly 看板页面；iframe 已加载
- **测试步骤**:
  1. 依赖 mindie_dashboard fixture
  2. 验证导出按钮存在
  3. 点击导出按钮
  4. 捕获下载文件
  5. 验证文件名以 .xlsx 结尾
- **预期结果**: 导出按钮存在，点击后触发 xlsx 文件下载
- **执行结果**: pass

### TC-ISSUE078-014: UI-项目级汇总无导出、流水线级有导出

- **所属功能点**: FP-07 汇总/明细暂不支持导出
- **测试设计方法**: 错误推测法
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/nightly_dashboard/export/test_ui_nightly_dashboard_export_beta_001.py`
- **用例等级**: L1
- **前置条件**: 已登录；已在 mindie 项目 Nightly 看板页面；iframe 已加载
- **测试步骤**:
  1. 依赖 mindie_dashboard fixture
  2. 验证项目级汇总区域无导出按钮
  3. 验证流水线级汇总区域有导出按钮
- **预期结果**: 项目级汇总无导出按钮，流水线级汇总有导出按钮
- **执行结果**: pass

### TC-ISSUE078-015: 汇总接口响应时间验证

- **所属功能点**: FP-08 汇总接口响应时间
- **测试设计方法**: 错误推测法
- **用例类型**: 自动化-性能 (auto_perf)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/performance/beta/nightly_dashboard/test_performance_nightly_dashboard_summary_001.py`
- **用例等级**: L1
- **前置条件**: 已登录 test 环境
- **测试步骤**:
  1. 重复调用汇总接口 10 次
  2. 统计 avg/P95 响应时间
  3. 验证 avg<3s 且 P95<5s，error_rate 为 0
- **预期结果**: 汇总接口平均响应 < 3s，P95 < 5s，无错误
- **执行结果**: pass

### TC-ISSUE078-016: 汇总/导出接口未认证访问拒绝

- **所属功能点**: FP-09 安全验证
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_001.py`
- **用例等级**: L1
- **前置条件**: 已登录 test 环境
- **测试步骤**:
  1. 不携带 token 调用汇总接口
  2. 不携带 token 调用导出接口
  3. 验证均返回 401/403 或业务拒绝
- **预期结果**: 未认证访问汇总/导出接口被拒绝
- **执行结果**: pass

### TC-ISSUE078-017: 认证校验-伪造 token 请求

- **所属功能点**: FP-10 认证校验（伪造 token）
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_001.py`
- **用例等级**: L1
- **前置条件**: 已登录 test 环境
- **测试步骤**:
  1. 携带伪造 Authorization: Bearer fake_token 调用汇总接口
  2. 携带伪造 token 调用明细接口
  3. 携带伪造 token 调用导出接口
  4. 验证均被拒绝（401/403/业务拒绝）
- **预期结果**: 伪造 token 请求汇总/明细/导出接口均被拒绝
- **执行结果**: pass

### TC-ISSUE078-018: 横向越权-跨项目数据隔离

- **所属功能点**: FP-11 横向越权（跨项目数据隔离）
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_002.py`
- **用例等级**: L1
- **前置条件**: 已登录 test 环境；存在多个可访问项目
- **测试步骤**:
  1. 以当前用户调用汇总接口 projectId=300036（MindIE）
  2. 调用汇总接口 projectId=3（openlibing）
  3. 验证两请求均正常返回且数据不同（项目数据隔离）
  4. 尝试访问无权限 projectId，验证被拒绝或返回空
- **预期结果**: 不同 projectId 返回对应项目数据；无权限项目不泄露他人数据
- **执行结果**: pass

### TC-ISSUE078-019: 传输安全-HTTPS 与 Cookie 属性

- **所属功能点**: FP-12 传输安全
- **测试设计方法**: 属性校验
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_003.py`
- **用例等级**: L1
- **前置条件**: 已登录 test 环境
- **测试步骤**:
  1. 验证 3 个接口 URL 均为 https
  2. 调用接口并检查 Set-Cookie 的 Secure/HttpOnly 属性
  3. 汇总检查结果
- **预期结果**: 接口使用 HTTPS；会话 Cookie 具备 Secure/HttpOnly 属性
- **执行结果**: fail（Cookie 缺 Secure/HttpOnly，缺陷待创建）

### TC-ISSUE078-020: CSRF 防护-导出接口变更请求

- **所属功能点**: FP-13 CSRF 防护
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_003.py`
- **用例等级**: L1
- **前置条件**: 已登录 test 环境
- **测试步骤**:
  1. 调用导出接口时移除 CSRF token 头
  2. 调用导出接口时携带伪造 CSRF token
  3. 验证变更请求被拒绝（401/403/业务拒绝）
- **预期结果**: 缺失/伪造 CSRF token 的导出请求被拒绝
- **执行结果**: fail（导出接口无 CSRF 防护，缺陷待创建）

### TC-ISSUE078-021: 敏感信息防护-响应不泄露凭证

- **所属功能点**: FP-14 敏感信息防护
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/nightly_dashboard/test_security_nightly_dashboard_003.py`
- **用例等级**: L1
- **前置条件**: 已登录 test 环境
- **测试步骤**:
  1. 调用汇总/明细/导出接口获取响应
  2. 检查响应体与响应头
  3. 验证不包含 token/password/secret/密钥等敏感字段值
- **预期结果**: 接口响应不泄露 token、密码、密钥、Cookie 等敏感信息
- **执行结果**: pass

---

## 用例汇总

| 类型        | 数量   | 通过   | 失败  | 阻塞  | 跳过  |
| ----------- | ------ | ------ | ----- | ----- | ----- |
| 手工用例    | 0      | 0      | 0     | 0     | 0     |
| 自动化-UI   | 5      | 5      | 0     | 0     | 0     |
| 自动化-API  | 9      | 5      | 2     | 0     | 2     |
| 自动化-性能 | 1      | 1      | 0     | 0     | 0     |
| 自动化-安全 | 6      | 4      | 2     | 0     | 0     |
| **合计**    | **21** | **15** | **4** | **0** | **2** |

| 用例来源            | 数量 |
| ------------------- | ---- |
| reuse（复用旧用例） | 0    |
| new（新设计用例）   | 21   |

---

## 版本历史

| 版本 | 日期       | 修改人   | 修改内容                                                                             |
| ---- | ---------- | -------- | ------------------------------------------------------------------------------------ |
| v1.0 | 2026-08-11 | tester-a | 初始版本                                                                             |
| v1.1 | 2026-08-11 | tester-a | 回填本地 pytest 执行结果（pass 12 / fail 2 / skip 2）                                |
| v1.2 | 2026-08-12 | tester-a | 新增安全测试用例 TC-ISSUE078-017~021（认证伪造/横向越权/传输安全/CSRF/敏感信息防护） |
| v1.3 | 2026-08-12 | tester-a | 回填安全测试执行结果（017/018/021 pass；019/020 fail 缺陷待创建）                    |
