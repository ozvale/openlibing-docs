# 测试用例 - ISSUE-109

> **模板版本**: v1.3
> **对应规则**: ai-rules/01-requirement-driven-test-design.md（第5节）、ai-rules/03-test-execution-and-report.md（第3节）

---

> **Issue编号**: ISSUE-109
> **Issue标题**: 【蓝区】【运营看板】资源运营看板建设
> **创建日期**: 2026-08-31
> **用例总数**: 20
> **手工用例**: 4
> **自动化用例**: 16
> **复用旧用例**: 0
> **新设计用例**: 20

### 执行信息

> 由**测试人员**填写。自动化用例的 Action 链接在此**统一填写一个**，无需每条用例重复填写。

| 字段 | 内容 |
|------|------|
| 自动化执行Action链接 | 本地 beta 执行（TEST_ENV=test + SECURITY_ENABLED=true，串行分 3 批；无 GitCode Action 流水线） |
| 手工执行人 | mth |
| 执行日期 | 2026-08-31 |

---

## 用例列表

| 用例编号 | 用例标题 | 所属功能点 | 用例类型 | 用例来源 | 用例等级 | 脚本位置 | 状态 |
|----------|----------|------------|----------|----------|----------|----------|------|
| TC-ISSUE109-001 | summary 接口 7 天窗口 KPI 数据结构与分组验证 | FP-2 KPI 汇总 | auto_api | new | L0 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_summary_001.py | active |
| TC-ISSUE109-002 | summary 接口 projectId 过滤验证 | FP-2 KPI 汇总 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_summary_001.py | active |
| TC-ISSUE109-003 | trend 接口 pool 维度分组与逐小时曲线验证 | FP-3 NPU 趋势 | auto_api | new | L0 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_trend_002.py | active |
| TC-ISSUE109-004 | trend 接口 gen 维度分组验证 | FP-3 NPU 趋势 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_trend_002.py | active |
| TC-ISSUE109-005 | heatmap 接口服务器骨架与分配数据验证 | FP-4 服务器热力图 | auto_api | new | L0 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_heatmap_003.py | active |
| TC-ISSUE109-006 | heatmap 接口空数据窗口补零验证 | FP-4 服务器热力图 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_heatmap_003.py | active |
| TC-ISSUE109-007 | run-analysis 有效 runId 状态机验证 | FP-5 运行分析 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_run_analysis_004.py | active |
| TC-ISSUE109-008 | run-analysis 无效 runId 空数据验证 | FP-5 运行分析 | auto_api | new | L2 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_run_analysis_004.py | active |
| TC-ISSUE109-009 | project-alloc-trend 接口曲线数据验证 | FP-6 项目下钻 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_project_trend_005.py | active |
| TC-ISSUE109-010 | 时间参数校验决策表验证（4 接口 × 5 非法场景） | FP-7 时间范围校验 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_time_validate_006.py | active |
| TC-ISSUE109-011 | 时间窗口边界值验证（6 天/7 天整） | FP-7 时间范围校验 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_time_validate_006.py | active |
| TC-ISSUE109-012 | run-analysis 必填参数校验验证 | FP-7 时间范围校验 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_run_analysis_004.py | active |
| TC-ISSUE109-013 | 数据管道新鲜度弱断言验证 | FP-8 数据管道 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_data_freshness_007.py | active |
| TC-ISSUE109-014 | 看板页面渲染与图表完整性验证 | FP-2/3/4/5/6 UI 层 | manual | new | L0 | — | active |
| TC-ISSUE109-015 | 时间选择器与维度切换交互验证 | FP-3/7 UI 层 | manual | new | L1 | — | active |
| TC-ISSUE109-016 | 热力图悬浮与抽屉交互验证 | FP-4 UI 层 | manual | new | L1 | — | active |
| TC-ISSUE109-017 | 无权限访问拦截验证 | FP-1 权限守卫 | manual | new | L1 | — | active |
| TC-ISSUE109-018 | 低权限账号纵向越权验证（5 接口） | FP-1 权限模型 | auto_sec | new | L0 | src/tests/openlibing/openlibing_ops/security/beta/resource_dashboard/test_security_resource_vertical_001.py | active |
| TC-ISSUE109-019 | 匿名与伪造 token 调用看板接口认证校验 | FP-1 权限模型 | auto_sec | new | L1 | src/tests/openlibing/openlibing_ops/security/beta/resource_dashboard/test_security_resource_auth_002.py | active |
| TC-ISSUE109-020 | 看板接口响应体敏感信息防护验证 | 敏感信息防护 | auto_sec | new | L2 | src/tests/openlibing/openlibing_ops/security/beta/resource_dashboard/test_security_resource_sensitive_003.py | active |

> **用例来源说明**：
> - `reuse`：复用已有用例，引用已有用例编号（在详情中"引用已有用例"字段标注），不重新归档
> - `new`：新设计用例，必须按规则 5.3 归档到模块用例文件与 case_list.md
> - **模块归档编号对照**：TC-ISSUE109-001~020 → `openlibing_ops_resource_dashboard_202608_001`~`020`（归档于 `assets/docs/openlibing/openlibing_ops/resource_dashboard/auto_test_cases.md` 与 `manual_test_cases.md`）
> - **复用检查结论**（2026-08-31）：已检索 `test_case.md` 全量用例及各模块用例目录，无 resource-operation / nRDashboard / npu_resource 相关用例（关键词仅命中 ISSUE-109 自身文档），resource_dashboard 为新建模块，全部按 new 设计

---

## 执行结果记录

> 本节由**测试人员**填写，AI 不得代填。执行结果未填写完整前，AI 不得生成测试报告（见规则 03 第4节）。
> **2026-08-31 回填说明**：自动化用例结果依据本地 beta 执行实测输出回填（junit 原始文件因存储层异常丢失，结果以本表为准）；手工用例 TC-014~017 由测试人员执行并确认结果。

| 用例编号 | 用例类型 | 执行结果 | 缺陷issue | 备注 |
|----------|----------|----------|------------|------|
| TC-ISSUE109-001 | auto_api | pass | — | KPI 四字段结构完整、cloud/lab 分组正确、npuNum 非负 |
| TC-ISSUE109-002 | auto_api | pass | — | projectId 过滤生效：过滤后 cloud:1/lab:1 ≤ 全量 cloud:3/lab:10 |
| TC-ISSUE109-003 | auto_api | pass | — | pool 分组曲线结构完整、labels 逐小时连续、数值 ∈ [0,100] |
| TC-ISSUE109-004 | auto_api | pass | — | gen 维度分组正常（基线 A2/A3/310P），结构与 pool 一致 |
| TC-ISSUE109-005 | auto_api | pass | — | 有数据窗口 servers 骨架完整、抽样存在非零分配值 |
| TC-ISSUE109-006 | auto_api | pass | — | 空数据窗口 HTTP 200 不报错、骨架完整、alloc/usage 全 0 |
| TC-ISSUE109-007 | auto_api | pass | — | 有效 runId 状态机完整，states ⊆ {QUEUING, RUNNING, NONE} |
| TC-ISSUE109-008 | auto_api | pass | — | 随机 runId 返回空结构（labels=[]/allocServers=[]/usageServers=[]）不报错 |
| TC-ISSUE109-009 | auto_api | pass | — | project-alloc-trend 逐小时申请次数与排队时长曲线结构正确 |
| TC-ISSUE109-010 | auto_api | fail | [#115](https://gitcode.com/openlibing/openlibing-ops/issues/115) | 20/20 非法时间场景返回 500 系统异常而非 40001；对照组 4 个合法请求均 200 正常（排除服务故障误判），确认缺陷存在 |
| TC-ISSUE109-011 | auto_api | pass | — | 6 天与 7 天整边界跨度均正常返回 200+数据 |
| TC-ISSUE109-012 | auto_api | pass | — | 缺 runId/projectId 均返回 40001 参数异常（基线保持，防回归） |
| TC-ISSUE109-013 | auto_api | pass | — | 当日数据管道有产出（cloud/lab 至少一组非空资源数据） |
| TC-ISSUE109-014 | manual | pass | — | 页面无白屏/控制台报错，KPI 卡片/趋势图/热力图/下钻折线图四类图表完整渲染，抽样数值与 API 层一致 |
| TC-ISSUE109-015 | manual | pass | — | 时间范围切换图表联动刷新正常，pool/gen 维度切换分组正确，超 7 天跨度被拦截且提示友好 |
| TC-ISSUE109-016 | manual | pass | — | 热力图悬浮浮层显示任务名/排队时长等 jobs 信息，机器详情抽屉正常打开、内容正确、可正常关闭 |
| TC-ISSUE109-017 | manual | pass | — | 无权限账号访问 /apps/nRDashboard?projectId=300036 重定向 noPermission 页并显示暂无权限提示（守卫生效正常） |
| TC-ISSUE109-018 | auto_sec | fail | [#114](https://gitcode.com/openlibing/openlibing-ops/issues/114) | p_tianyan（npu_resource=false，缺陷精确复现账号）会话内浏览器 fetch 5/5 接口越权成功返回 200+全量数据（heatmap 泄露 88 台服务器）；pub_LIBING 纯低权限对照 401 被拒（基础权限层有效，npu_resource 业务校验缺失） |
| TC-ISSUE109-019 | auto_sec | pass | — | 匿名与伪造 token 调用 5 接口均被 401 拒绝 |
| TC-ISSUE109-020 | auto_sec | pass | — | 5 接口响应体/响应头未泄露凭证类敏感字段（password/token/secret/密钥/手机号/邮箱） |

> **执行结果取值**：pass（通过）/ fail（失败）/ block（阻塞）/ skip（跳过）
> **执行批次说明**（2026-08-31 本地 beta 串行执行，规避 WAF 限流分 3 批）：
> - 批次1：12 条轻请求量 API 用例（TC-001~009/011~013）→ 12/12 pass，44.17s
> - 批次2：TC-010 时间校验决策表（24 请求）→ fail（缺陷 #115 闭环），47.65s
> - 批次3：3 条安全用例 → TC-019/020 pass；TC-018 fail（缺陷 #114 闭环，攻击路径已修正为 p_tianyan 主路径 + pub_LIBING 对照路径）
> - junit 证据：原 `execution_results/` 下 junit 文件（junit_api_batch1.xml、junit_api_batch2.xml、junit_security_batch3.xml、junit_security_019_020.xml、tc018_final.log）因 2026-08-31 存储层异常丢失，逐条结果以本表为准

---

## 手工用例详情

### TC-ISSUE109-014: 看板页面渲染与图表完整性验证

- **所属功能点**: FP-2/3/4/5/6 UI 层（页面渲染）
- **测试设计方法**: 场景法
- **用例类型**: 手工执行 (manual)
- **用例来源**: new
- **引用已有用例**: —
- **用例等级**: L0
- **前置条件**: 平台侧为测试账号开通 `npu_resource` 权限（当前 false；未开通时本用例 block）
- **测试步骤**:
  1. 登录 beta（https://beta.openlibing.com），进入 `/apps/nRDashboard?projectId=300036`
  2. 检查 KPI 卡片（池总量/资源总量/分配率/使用率，按 cloud/lab 分组）渲染
  3. 检查 NPU 趋势图（pool/gen 双维度）、服务器热力图、项目下钻折线图渲染
  4. 抽样核对图表数值与后端 API 返回（对照 TC-ISSUE109-001/003/005 结果）
- **预期结果**: 页面无白屏/控制台报错；四类图表完整渲染；抽样数值与 API 层一致

### TC-ISSUE109-015: 时间选择器与维度切换交互验证

- **所属功能点**: FP-3/7 UI 层（交互）
- **测试设计方法**: 场景法
- **用例类型**: 手工执行 (manual)
- **用例来源**: new
- **引用已有用例**: —
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE109-014
- **测试步骤**:
  1. 修改时间范围选择器（7 天内不同区间）
  2. 切换趋势图 pool ↔ gen 维度
  3. 尝试选择超过 7 天的时间跨度
- **预期结果**: 时间切换后各图表数据联动刷新；维度切换曲线分组正确变化；超 7 天跨度被拦截并提示（不得出现"系统异常"误导性报错）

### TC-ISSUE109-016: 热力图悬浮与抽屉交互验证

- **所属功能点**: FP-4 UI 层（交互）
- **测试设计方法**: 场景法
- **用例类型**: 手工执行 (manual)
- **用例来源**: new
- **引用已有用例**: —
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE109-014；热力图存在有分配数据的机器
- **测试步骤**:
  1. 悬浮热力图色块，查看任务详情浮层
  2. 打开机器详情抽屉，检查内容
  3. 关闭抽屉
- **预期结果**: 悬浮浮层显示任务名/排队时长等 jobs 信息；抽屉正常打开、内容正确、可正常关闭

### TC-ISSUE109-017: 无权限访问拦截验证

- **所属功能点**: FP-1 页面路由与权限守卫
- **测试设计方法**: 场景法（无权限用户路径）
- **用例类型**: 手工执行 (manual)
- **用例来源**: new
- **引用已有用例**: —
- **用例等级**: L1
- **前置条件**: 使用无 `npu_resource` 权限的账号（当前 p_tianyan 即为 false，或 pub_LIBING）
- **测试步骤**:
  1. 登录 beta 后直接访问 `/apps/nRDashboard?projectId=300036`
- **预期结果**: 重定向 noPermission 页，显示"暂无权限，可通过右侧12345联系客服"提示（端到端验证实测基线 CP-02：守卫生效正常）

---

## 自动化用例详情

### TC-ISSUE109-001: summary 接口 7 天窗口 KPI 数据结构与分组验证

- **所属功能点**: FP-2 KPI 汇总
- **测试设计方法**: 等价类划分（有效等价类）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_summary_001.py`
- **用例等级**: L0
- **前置条件**: beta 环境；API 会话有效；近 7 天内有资源数据
- **测试步骤**:
  1. 调用 `POST /gateway/openlibing-ops/resource-operation/summary`（近 7 天 startDate/endDate）
  2. 校验响应结构与 cloud/lab 分组
- **预期结果**: HTTP 200 + code=200；data 含 poolTotal/resourceTotal/allocRate/usageRate；分组键为 cloud/lab；resourceTotal 每组为 [{generation, npuNum}]，npuNum 非负

### TC-ISSUE109-002: summary 接口 projectId 过滤验证

- **所属功能点**: FP-2 KPI 汇总
- **测试设计方法**: 等价类划分（projectId 有/无对比）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_summary_001.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE109-001；projectId=300036 有数据
- **测试步骤**:
  1. 无 projectId 调用 summary 记录池总数
  2. projectId=300036 调用 summary 记录池总数
  3. 对比
- **预期结果**: 过滤后池总数 ≤ 全量（实测基线：全量 cloud:3 lab:10 → 过滤后 cloud:1 lab:1）

### TC-ISSUE109-003: trend 接口 pool 维度分组与逐小时曲线验证

- **所属功能点**: FP-3 NPU 趋势
- **测试设计方法**: 等价类划分（dim=pool）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_trend_002.py`
- **用例等级**: L0
- **前置条件**: 同 TC-ISSUE109-001
- **测试步骤**:
  1. 调用 `POST /resource-operation/trend`（dim=pool，7 天窗口）
  2. 校验 labels 逐小时连续与 pool 分组曲线
- **预期结果**: HTTP 200 + code=200；labels 为逐小时序列；data.pool 每组含 name + alloc[]/usage[]，长度与 labels 一致；数值 ∈ [0,100]

### TC-ISSUE109-004: trend 接口 gen 维度分组验证

- **所属功能点**: FP-3 NPU 趋势
- **测试设计方法**: 等价类划分（dim=gen）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_trend_002.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE109-001
- **测试步骤**:
  1. 调用 trend（dim=gen，7 天窗口）
  2. 校验 gen 分组
- **预期结果**: data.gen 为代际分组列表（实测基线：A2/A3/310P），结构与 pool 维度一致

### TC-ISSUE109-005: heatmap 接口服务器骨架与分配数据验证

- **所属功能点**: FP-4 服务器热力图
- **测试设计方法**: 等价类划分（有数据窗口）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_heatmap_003.py`
- **用例等级**: L0
- **前置条件**: 同 TC-ISSUE109-001；有数据窗口（如 2026-08-22 ~ 2026-08-23）
- **测试步骤**:
  1. 调用 `POST /resource-operation/heatmap`（有数据窗口）
  2. 校验 servers 骨架与抽样分配数据
- **预期结果**: HTTP 200 + code=200；servers 每台机含 ip/pool/gen + alloc[]/usage[]（alloc 含 jobs）；至少 1 台机 alloc 存在非零值（弱断言防数据波动误报）

### TC-ISSUE109-006: heatmap 接口空数据窗口补零验证

- **所属功能点**: FP-4 服务器热力图
- **测试设计方法**: 边界值分析（空数据窗口）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_heatmap_003.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE109-001；无数据窗口（未来日期或停更历史窗口）
- **测试步骤**:
  1. 调用 heatmap（空数据窗口）
  2. 校验骨架与补 0
- **预期结果**: HTTP 200 不报错；servers 骨架完整；alloc/usage 全 0（实测基线：CP-09）

### TC-ISSUE109-007: run-analysis 有效 runId 状态机验证

- **所属功能点**: FP-5 运行分析
- **测试设计方法**: 状态迁移测试（QUEUING/RUNNING/NONE）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_run_analysis_004.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE109-001；有效样本 runId（e1dcd94695414ab6a2aad29bff37ad3c）
- **测试步骤**:
  1. 调用 `POST /resource-operation/run-analysis`（runId + projectId=300036）
  2. 校验 labels 整点窗口与 jobs 状态机
- **预期结果**: HTTP 200 + code=200；labels 为整点序列；每台机 values + jobs[]（taskName/queueMinutes/npuHours/states[]）完整；states ⊆ {QUEUING, RUNNING, NONE}

### TC-ISSUE109-008: run-analysis 无效 runId 空数据验证

- **所属功能点**: FP-5 运行分析
- **测试设计方法**: 错误推测法（随机 runId）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_run_analysis_004.py`
- **用例等级**: L2
- **前置条件**: 同 TC-ISSUE109-001
- **测试步骤**:
  1. 调用 run-analysis（runId=随机 32 位十六进制不存在值）
- **预期结果**: HTTP 200 + code=200，空结构（labels=[] allocServers=[] usageServers=[]），不报错（实测基线：CP-11）

### TC-ISSUE109-009: project-alloc-trend 接口曲线数据验证

- **所属功能点**: FP-6 项目下钻
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_project_trend_005.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE109-001；projectId=300036 有申请数据
- **测试步骤**:
  1. 调用 `POST /resource-operation/project-alloc-trend`（projectId=300036 + 7 天窗口）
  2. 校验曲线结构
- **预期结果**: HTTP 200 + code=200；响应含逐小时申请次数与排队时长曲线，结构与类型正确（弱断言）

### TC-ISSUE109-010: 时间参数校验决策表验证（4 接口 × 5 非法场景）

- **所属功能点**: FP-7 时间范围校验
- **测试设计方法**: 决策表测试（5 非法场景 × 预期错误码）+ 边界对照
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_time_validate_006.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE109-001
- **测试步骤**:
  1. 对 summary/trend/heatmap/project-alloc-trend 分别传入：跨度超限（8 天）、大跨度（30 天）、时间倒置、缺 endDate、非法格式（yyyy/MM/dd）
  2. 合法 7 天窗口对照请求（排除服务故障误判）
- **预期结果**: 目标行为：code=40001 参数异常 + 具体原因。**当前已知缺陷基线**：返回 500 系统异常 = 缺陷 #115（open），执行预期 fail；修复后复测应转为 pass

### TC-ISSUE109-011: 时间窗口边界值验证（6 天/7 天整）

- **所属功能点**: FP-7 时间范围校验
- **测试设计方法**: 边界值分析（上边界 7 天整/边界内 6 天）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_time_validate_006.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE109-001
- **测试步骤**:
  1. 调用 summary（跨度恰好 7 天）
  2. 调用 summary（跨度 6 天）
- **预期结果**: 两种边界内跨度均 HTTP 200 + code=200 + 正常数据（实测基线：CP-13 对照组合法 7 天正常）

### TC-ISSUE109-012: run-analysis 必填参数校验验证

- **所属功能点**: FP-7 时间范围校验（必填参数）
- **测试设计方法**: 错误推测法（缺 runId / 缺 projectId）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_run_analysis_004.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE109-001
- **测试步骤**:
  1. 调用 run-analysis 省略 runId
  2. 调用 run-analysis 省略 projectId
- **预期结果**: code=40001 参数异常（实测基线：CP-12 当前正确——"流水线运行ID不能为空"，用例保护该基线防回归）

### TC-ISSUE109-013: 数据管道新鲜度弱断言验证

- **所属功能点**: FP-8 数据管道与数据正确性
- **测试设计方法**: 边界值分析（最近 24h 窗口）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/resource_dashboard/test_api_resource_data_freshness_007.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE109-001
- **测试步骤**:
  1. 调用 summary（昨日~今日窗口）
- **预期结果**: HTTP 200 + 至少一组（cloud 或 lab）非空资源数据（复测基线：08-30 已回填每日连续；曾停更风险见 verification_report.md CP-14）

### TC-ISSUE109-018: 低权限账号纵向越权验证（5 接口）

- **所属功能点**: FP-1 权限模型（后端层）
- **测试设计方法**: 纵向越权断言（assert_denied 方向，双攻击路径）
- **用例类型**: 自动化-安全 (auto_sec, vertical_check)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/resource_dashboard/test_security_resource_vertical_001.py`
- **用例等级**: L0
- **前置条件**: beta 环境（SECURITY_ENABLED=true，仅 test 环境）；主攻击账号 p_tianyan（admin 系统角色、npu_resource=false，缺陷 #114 精确复现账号）；对照账号 pub_LIBING（纯低权限）
- **测试步骤**:
  1. 接口连通性对照（排除服务故障误判）
  2. 主攻击路径：p_tianyan（npu_resource=false）会话内浏览器 fetch 5 个 API 合法参数请求（与缺陷 #114 复现方式一致）
  3. 对照攻击路径：pub_LIBING 独立会话登录后浏览器 fetch 同 5 个 API
  4. 断言拒绝方向（assert_denied）
- **预期结果**: 目标行为：401/403 或业务拒绝 code!=200。**当前已知缺陷基线**：主攻击路径返回 200 + 全量数据 = 缺陷 #114（open，发布阻塞项），执行预期 fail；修复后复测应转为 pass。注：pub_LIBING 对照路径 401 仅证明基础权限层拦截，npu_resource 业务权限校验判定以 p_tianyan 主路径为准（2026-08-31 执行实测确认）

### TC-ISSUE109-019: 匿名与伪造 token 调用看板接口认证校验

- **所属功能点**: FP-1 权限模型（认证层）
- **测试设计方法**: 认证校验断言
- **用例类型**: 自动化-安全 (auto_sec, auth_check)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/resource_dashboard/test_security_resource_auth_002.py`
- **用例等级**: L1
- **前置条件**: beta 环境
- **测试步骤**:
  1. 无 token 直连 5 个 API
  2. 携带伪造 token 直连
- **预期结果**: 401/403 拒绝（既有基线：匿名/伪造 token 服务端正确拒绝）

### TC-ISSUE109-020: 看板接口响应体敏感信息防护验证

- **所属功能点**: 敏感信息防护
- **测试设计方法**: 敏感信息扫描
- **用例类型**: 自动化-安全 (auto_sec, sensitive_data_check)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/resource_dashboard/test_security_resource_sensitive_003.py`
- **用例等级**: L2
- **前置条件**: beta 环境；p_tianyan 会话
- **测试步骤**:
  1. 调用 5 个 API 采集响应体与响应头
  2. 扫描敏感字段模式（password/token/secret/密钥/手机号/邮箱）
- **预期结果**: 响应体/响应头不泄露凭证类敏感字段（服务器 IP/池名/任务名为运营数据本身）

---

## 用例汇总

| 类型 | 数量 | 通过 | 失败 | 阻塞 | 跳过 |
|------|------|------|------|------|------|
| 手工用例 | 4 | 4 | 0 | 0 | 0 |
| 自动化-UI | 0 | 0 | 0 | 0 | 0 |
| 自动化-API | 13 | 12 | 1 | 0 | 0 |
| 自动化-性能 | 0 | 0 | 0 | 0 | 0 |
| 自动化-安全 | 3 | 2 | 1 | 0 | 0 |
| **合计** | **20** | **18** | **2** | **0** | **0** |

> 统计口径：20 条用例全部执行（18 pass + 2 fail，通过率 90%）；2 条 fail 均为已知缺陷闭环用例（TC-010 → #115、TC-018 → #114），缺陷 issue 链接已填写。

| 用例来源 | 数量 |
|----------|------|
| reuse（复用旧用例） | 0 |
| new（新设计用例） | 20 |

---

## 版本历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0 | 2026-08-31 | mth | 初始版本（20 条：13 auto_api + 3 auto_sec + 4 manual） |
| v1.1 | 2026-08-31 | mth | 本地 beta 执行回填：16 条自动化用例结果（14 pass + 2 fail）；TC-018 攻击路径修正为 p_tianyan 主路径（npu_resource=false 精确复现账号）+ pub_LIBING 对照路径；补充执行批次与 junit 证据说明 |
| v1.2 | 2026-08-31 | mth | 手工用例 TC-014~017 执行结果回填（4/4 pass，执行人 mth）；20 条用例全部执行完毕（18 pass + 2 fail），报告生成门槛校验通过 |
