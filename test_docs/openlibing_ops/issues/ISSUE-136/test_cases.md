# 用例清单 — issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等

> 团队：IPD管理控制与测试仿真 | 月度：202609 | 版本：20260923 | issue 编号：136 | issue 标题：【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等 | 用例总数：15（自动化 14 / 手工 1） | 更新日期：2026-09-23 | 由 testcase_pro 维护

> 月度版本树（进行中）：用例先落本 issue 目录（四类类型子目录与特性树同构），月底 consolidate 归集到 01~04 特性树；过程文档（测试策略/测试设计/测试串讲/测试反串讲/版本历史/测试报告）见本目录 测试过程数据/。

## 用例统计

| 用例等级 | 自动化 | 手工 | 合计 |
|------|------|------|------|
| P0 | 8 | 0 | 8 |
| P1 | 6 | 1 | 7 |
| **合计** | 14 | 1 | **15** |

## 用例清单

### 01_系统测试（15 条）

| 用例编号 | 用例标题 | 用例等级 | 执行方式 | 自动化方式 | 用例文本位置 | 用例脚本位置 |
|------|------|------|------|------|------|------|
| TC-ISSUE136-013 | GitHub PR门禁看板加载与表头断言（空态容错） | P1 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/数字化运营/GitHub PR门禁看板/TC-ISSUE136-013_GitHub PR门禁看板加载与表头断言（空态容错）.md](../01_系统测试/数字化运营/GitHub%20PR门禁看板/TC-ISSUE136-013_GitHub%20PR门禁看板加载与表头断言（空态容错）.md) | [src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/beta/baseline/test_tc_issue136_013.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/beta/baseline/test_tc_issue136_013.py) |
| TC-ISSUE136-011 | PR门禁看板加载与指标基线断言 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE136-011_PR门禁看板加载与指标基线断言.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE136-011_PR门禁看板加载与指标基线断言.md) | [src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/baseline/test_tc_issue136_011.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/baseline/test_tc_issue136_011.py) |
| TC-ISSUE136-012 | PR门禁看板指标名称与指标管理一致性验证 | P1 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE136-012_PR门禁看板指标名称与指标管理一致性验证.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE136-012_PR门禁看板指标名称与指标管理一致性验证.md) | [src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/consistency/test_tc_issue136_012.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/consistency/test_tc_issue136_012.py) |
| TC-ISSUE136-001 | 开源项目运营看板加载与主页表格渲染验证 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-001_开源项目运营看板加载与主页表格渲染验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-001_开源项目运营看板加载与主页表格渲染验证.md) | [src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/load/test_tc_issue136_001.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/load/test_tc_issue136_001.py) |
| TC-ISSUE136-002 | 开源项目运营看板主页表格表头指标全量断言 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-002_开源项目运营看板主页表格表头指标全量断言.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-002_开源项目运营看板主页表格表头指标全量断言.md) | [src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/header/test_tc_issue136_002.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/header/test_tc_issue136_002.py) |
| TC-ISSUE136-003 | oSP·PR流水线运营指标与PR门禁看板对齐验证 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-003_oSP·PR流水线运营指标与PR门禁看板对齐验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-003_oSP·PR流水线运营指标与PR门禁看板对齐验证.md) | [src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/alignment/test_tc_issue136_003.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/alignment/test_tc_issue136_003.py) |
| TC-ISSUE136-004 | oSP·Nightly流水线运营指标与Nightly流水线看板对齐验证 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-004_oSP·Nightly流水线运营指标与Nightly流水线看板对齐验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-004_oSP·Nightly流水线运营指标与Nightly流水线看板对齐验证.md) | [src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/alignment/test_tc_issue136_004.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/alignment/test_tc_issue136_004.py) |
| TC-ISSUE136-005 | oSP既有独有指标列存在性回归验证 | P1 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-005_oSP既有独有指标列存在性回归验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-005_oSP既有独有指标列存在性回归验证.md) | [src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/alignment/test_tc_issue136_005.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/alignment/test_tc_issue136_005.py) |
| TC-ISSUE136-006 | oSP主页表格全指标列解释存在性验证 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-006_oSP主页表格全指标列解释存在性验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-006_oSP主页表格全指标列解释存在性验证.md) | [src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/tooltips/test_tc_issue136_006.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/tooltips/test_tc_issue136_006.py) |
| TC-ISSUE136-007 | oSP主页表格指标解释触发与内容非空验证 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-007_oSP主页表格指标解释触发与内容非空验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-007_oSP主页表格指标解释触发与内容非空验证.md) | [src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/tooltips/test_tc_issue136_007.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/tooltips/test_tc_issue136_007.py) |
| TC-ISSUE136-008 | oSP指标解释内容与指标管理定义一致性验证 | P1 | 手工 | — | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-008_oSP指标解释内容与指标管理定义一致性验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-008_oSP指标解释内容与指标管理定义一致性验证.md) | — |
| TC-ISSUE136-009 | oSP下钻明细「项目运营明细」加载与指标一致性验证 | P1 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-009_oSP下钻明细「项目运营明细」加载与指标一致性验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-009_oSP下钻明细「项目运营明细」加载与指标一致性验证.md) | [src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/drilldown/test_tc_issue136_009.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/drilldown/test_tc_issue136_009.py) |
| TC-ISSUE136-010 | oSP指标名称与指标管理已上线指标一致性验证 | P1 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-010_oSP指标名称与指标管理已上线指标一致性验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-010_oSP指标名称与指标管理已上线指标一致性验证.md) | [src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/consistency/test_tc_issue136_010.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/consistency/test_tc_issue136_010.py) |
| TC-ISSUE136-014 | 测试资源消耗看板加载与指标基线断言 | P1 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/测试资源消耗看板/TC-ISSUE136-014_测试资源消耗看板加载与指标基线断言.md](../01_系统测试/运营运维/测试资源消耗看板/TC-ISSUE136-014_测试资源消耗看板加载与指标基线断言.md) | [src/automation/ipd-management/ui/operations_maintenance/test_resource_consumption_dashboard/beta/baseline/test_tc_issue136_014.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/test_resource_consumption_dashboard/beta/baseline/test_tc_issue136_014.py) |
| TC-ISSUE136-015 | 指标管理列表加载与关键指标存在性验证 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/研发运营看板管理/TC-ISSUE136-015_指标管理列表加载与关键指标存在性验证.md](../01_系统测试/运营运维/研发运营看板管理/TC-ISSUE136-015_指标管理列表加载与关键指标存在性验证.md) | [src/automation/ipd-management/ui/operations_maintenance/rd_operations_dashboard_management/beta/metric_list/test_tc_issue136_015.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/rd_operations_dashboard_management/beta/metric_list/test_tc_issue136_015.py) |

### 02_API测试（0 条）

（无）

### 03_DFX测试（0 条）

（无）

### 04_安全测试（0 条）

（无）

## 用例详情

### 01_系统测试

#### TC-ISSUE136-013 GitHub PR门禁看板加载与表头断言（空态容错）

**测试功能场景**：FP1-b：GitHub PR门禁看板加载与表头基线（当前 Workflow 0 条空态，数据断言容错）

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/github_pr_gate_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/数字化运营/GitHub PR门禁看板/TC-ISSUE136-013_GitHub PR门禁看板加载与表头断言（空态容错）.md](../01_系统测试/数字化运营/GitHub%20PR门禁看板/TC-ISSUE136-013_GitHub%20PR门禁看板加载与表头断言（空态容错）.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/beta/baseline/test_tc_issue136_013.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/beta/baseline/test_tc_issue136_013.py)

**前置条件**：- beta 已登录；MindIE（projectId=300036）GitHub Workflow 数据为空（探索基线：总可选 0 条，表格共 0 条）

**测试步骤**

1. 会话守卫校验后 URL 直连 `/apps/githubPrWorkflowDashboard?projectId=300036`，等待 iframe `/ops/dashboard/github/300036` 渲染
2. 断言筛选区：Workflow创建时间/PR创建时间、代码仓、执行状态、数据获取时间
3. 断言 Workflow 筛选器呈现（上限 50 条，总可选 0 条文案）
4. 断言图表区空态呈现：排队时长(min)、执行时长(min)、PR E2E总时长(min) 三图表「暂无数据」
5. 断言主表表头渲染：代码仓、PR闭环时长(min)、门禁E2E执行时长(min)、Workflow名称、运行次数、Workflow E2E P50/P90/P95(min)、排队时长(min) P50/P90/P95、执行时长(min) P50/P90/P95、PR合入时长(min)、E2E达标率（表头在空态下不渲染时记录证据并跳过该项，不判失败）
6. 断言「P50、P90、P95含义说明」链接、配置/列设置/导出按钮存在
7. 断言主表空态「暂无数据」与分页「共 0 条」呈现

**预期结果**

- 看板完整加载，筛选区/图表区/工具栏/说明链接齐备
- 空态呈现规范（暂无数据 + 共 0 条），无报错、无空白塌陷
- 表头列名因 FP1 指标管理口径统一的等价变更可接受

**备注**：- 空态容错原则（1.7 风险表）：表头断言为主，数据断言条件跳过；若后续环境补充 Workflow 数据，数据断言自动生效

#### TC-ISSUE136-011 PR门禁看板加载与指标基线断言

**测试功能场景**：FP1-b：PR门禁看板加载与筛选/图表/主表指标基线（对接指标管理后不破坏既有呈现）

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/pr_gate_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE136-011_PR门禁看板加载与指标基线断言.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE136-011_PR门禁看板加载与指标基线断言.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/baseline/test_tc_issue136_011.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/baseline/test_tc_issue136_011.py)

**前置条件**：- beta 已登录；MindIE（projectId=300036）PR门禁数据存在（最活跃 5 仓：MindIE-Motor/MindIE-SD/FlashGen/MindIE-LLM 等）

**测试步骤**

1. 会话守卫校验后 URL 直连 `/apps/prAccessDashboard?projectId=300036`，等待 iframe `/ops/dashboard/pr-access/300036` 渲染
2. 断言筛选区：PR创建时间、流水线状态、开源类型、数据获取时间
3. 断言趋势分析图表区：默认展示最活跃 5 仓提示文案与代码仓选择器
4. 断言图表区指标：PR总数(个)、门禁E2E执行时长[平均](min)、代码检查任务时长[平均](min)、编译任务时长[平均](min)、测试任务时长[平均](min)、编译任务并发数、测试任务并发数（含「详情」入口）
5. 断言主表「代码仓指标汇总统计」列组结构：代码仓、托管平台、代码量(L)、PR数量（总数/开启中/已关闭/已合入/强制合入数）、门禁E2E执行（时长[平均/最长]、[平均/最长](不含重试)）、编译任务（时长[平均/最长]、排队时长[平均/最长]）、测试任务（时长[平均/最长]、排队时长[平均/最长]）、代码检查任务（时长[平均/最长]）、备注
6. 断言「P50、P90、P95含义说明」链接、配置/列设置/导出按钮存在
7. 断言数据行非空（至少 1 个代码仓行）

**预期结果**

- 看板完整加载，筛选区/图表区/主表/工具栏/说明链接齐备
- 主表列组结构完整，数据行非空
- 列名因 FP1 指标管理口径统一的等价变更可接受（须可回溯至指标管理已上线指标）

**备注**：- PR门禁看板为 FP2 对齐的参照看板之一（另一为 Nightly流水线看板），其列名变更将同步影响 TC-ISSUE136-003 交集基线

#### TC-ISSUE136-012 PR门禁看板指标名称与指标管理一致性验证

**测试功能场景**：FP1-c：PR门禁看板指标名称与指标管理（已上线指标）口径一致

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/pr_gate_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE136-012_PR门禁看板指标名称与指标管理一致性验证.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE136-012_PR门禁看板指标名称与指标管理一致性验证.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/consistency/test_tc_issue136_012.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/consistency/test_tc_issue136_012.py)

**前置条件**：- PR门禁看板已加载（TC-ISSUE136-011）；指标管理已上线指标清单已采集

**测试步骤**

1. 采集 PR门禁看板主表 + 图表区全部指标名称（复用 TC-ISSUE136-011 证据）
2. 预处理：剥离统计口径后缀（[平均]/[最长]/[P50]/[P90]/[P95]）与单位后缀（(min)/(个)）
3. 与指标管理**已上线**指标名称清单建立映射（完全一致或互为包含）
4. 断言核心指标必须映射成功：PR流水线执行次数（10001）、PR执行时长（10002）、PR代码检查任务时长（10003）、PR构建任务时长（10004）、PR测试任务时长（10005）、PR构建/测试任务并发数（10008/10009）、版本可用度（10018）
5. 未映射清单输出登记

**预期结果**

- 核心指标全部与指标管理已上线指标建立映射且名称一致
- 已知矛盾点消除（改造前「编译任务时长」vs 指标管理「PR构建任务时长」、「门禁E2E执行时长」vs「PR执行时长」口径分裂，改造后统一）
- 未映射清单仅含无对应指标管理条目的运营统计列（如代码量(L)、PR数量分组计数），并已登记

**备注**：- 与 TC-ISSUE136-010 同构（对象换为 PR门禁看板），断言模式与预处理规则保持一致

#### TC-ISSUE136-001 开源项目运营看板加载与主页表格渲染验证

**测试功能场景**：FP1-b：oSP 看板整体加载与主页表格渲染（对接指标管理后不破坏基本呈现）

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/osp_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-001_开源项目运营看板加载与主页表格渲染验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-001_开源项目运营看板加载与主页表格渲染验证.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/load/test_tc_issue136_001.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/load/test_tc_issue136_001.py)

**前置条件**

- beta 环境已部署本需求功能；账号 p_tianyan 可登录
- 测试项目 MindIE（projectId=300036）存在社区/子组织运营数据（探索基线 34 条/4 页）

**测试步骤**

1. 会话守卫校验（get-user-info 探测，失效自动重登），URL 直连 `/apps/oSPDashboard?projectId=300036`（不依赖侧边栏菜单点击）
2. 等待应用 iframe 挂载并轮询 iframe 内容渲染（上限 45s；不稳定时降级直连 iframe URL `/ops/dashboard/open-source-project`）
3. 验证「开源项目运营总览」主页表格标题与表格容器已渲染
4. 验证筛选区存在：时间范围筛选、PR流水线状态筛选
5. 验证工具栏存在：导出、列设置、全屏
6. 验证表格数据行数 > 0，分页器存在且总数显示正确（基线 34 条，容差随数据增长）
7. 验证尾部「开源分类定义」链接存在

**预期结果**

- iframe 内容完整渲染，主页表格标题「开源项目运营总览」可见
- 时间范围/PR流水线状态筛选、导出/列设置/全屏按钮均存在
- 数据行非空，分页器总数与表格实际条数一致
- 「开源分类定义」链接存在

**备注**：- 探索踩坑（exploration_tmp/page_exploration.md §7）：beta 会话 ~30s 失效需守卫；iframe 渲染不稳定需轮询+重试；菜单点击有可见性陷阱，统一 URL 直连

#### TC-ISSUE136-002 开源项目运营看板主页表格表头指标全量断言

**测试功能场景**：FP1-b/FP2 前置基线：oSP 主页表格表头区块结构与指标列全量采集断言

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/osp_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-002_开源项目运营看板主页表格表头指标全量断言.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-002_开源项目运营看板主页表格表头指标全量断言.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/header/test_tc_issue136_002.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/header/test_tc_issue136_002.py)

**前置条件**

- 同 TC-ISSUE136-001（oSP 看板已加载，主页表格已渲染）
- 探索基线（2026-09-22 改造前）区块结构已登记

**测试步骤**

1. 在主页表格 DOM 中采集全部表头列名（含分组表头与叶子列，处理「列设置」隐藏列时以默认展示列为准）
2. 按区块断言结构完整：代码仓运营、issue运营、PR流水线运营（含门禁E2E执行/时长/资源总消耗分组）、Nightly流水线运营、备注
3. 断言关键既有指标列不丢失：代码仓数量、已部署门禁代码仓数量、分支数量、tag数量、贡献者人数；issue数量（总数/开启中/已关闭）、PR数量（已合入/强制合入数）；门禁E2E执行次数、版本可用度、成功率、P0测试用例通过率、门禁E2E执行时长[平均/最长](min)、编译任务时长[平均](min)、测试任务时长[平均](min)、代码检查任务时长[平均](min)、PR闭环时长[平均/最长](min)；流水线E2E执行时长[平均/最长](min)、流水线E2E执行时长[平均](min)(不含重试)、流水线E2E执行成功率、编译任务成功率、测试任务成功率
4. 全量列名清单写入执行证据（供 -003/-004/-010 对齐与一致性断言复用）

**预期结果**

- 五个区块结构完整，各区块列齐备
- 关键既有指标列全部存在（列名因 FP1/FP2 指标名称统一而变更时，允许等价变更，但每列仍可回溯至指标管理已上线指标，见 TC-ISSUE136-010）
- 全量列名清单已落盘

**备注**：- 预期变更处理：FP2 对齐若新增缺失列（不含重试时长/排队时长/最长时长等），属需求预期变更，更新基线不判失败；断言核心为「区块完整 + 既有列不丢失」

#### TC-ISSUE136-003 oSP·PR流水线运营指标与PR门禁看板对齐验证

**测试功能场景**：FP2-a：oSP 看板「PR流水线运营」区块与 PR门禁看板指标对齐（Issue 特性详情 2-1)）

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/osp_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-003_oSP·PR流水线运营指标与PR门禁看板对齐验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-003_oSP·PR流水线运营指标与PR门禁看板对齐验证.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/alignment/test_tc_issue136_003.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/alignment/test_tc_issue136_003.py)

**前置条件**

- oSP 看板与 PR门禁看板均可加载（同 TC-ISSUE136-001/-011）
- MindIE 项目两看板均有数据

**测试步骤**

1. 采集 oSP 主页表格「PR流水线运营」区块全部指标列名（复用 TC-ISSUE136-002 证据）
2. 采集 PR门禁看板主表「代码仓指标汇总统计」全部指标列名与图表区指标名（复用 TC-ISSUE136-011 证据）
3. 建立共有指标交集清单（探索基线交集：门禁E2E执行时长[平均/最长](min)、编译任务时长[平均](min)、测试任务时长[平均](min)、代码检查任务时长[平均](min)、PR数量（已合入/强制合入数）相关口径）
4. 逐项断言：交集内每一指标在两个看板中的名称**逐字一致**（含单位与统计口径后缀）
5. 输出差异报告：oSP 缺失列清单（PR门禁看板有而 oSP 无）、oSP 独有列清单（登记为证据，见 TC-ISSUE136-005）

**预期结果**

- 交集内所有共有指标名称在两看板间逐字一致（含 (min)/[平均]/[最长] 等口径后缀）
- oSP「PR流水线运营」区块既有指标列无丢失
- 差异报告已输出（缺失列补齐与否属 1.7 风险表登记的待确认项，不单独判失败）

**备注**

- 设计依据：Issue 特性详情 2-1)「开源项目运营看板在PR流水线运营和Nightly流水线运营这两部分可以和数字化运营的Nightly流水线看板、PR门禁看板指标对齐」
- 若指标名称按指标管理口径统一（如「编译任务时长」→「PR构建任务时长」），两看板应同步变更且保持一致

#### TC-ISSUE136-004 oSP·Nightly流水线运营指标与Nightly流水线看板对齐验证

**测试功能场景**：FP2-b：oSP 看板「Nightly流水线运营」区块与 Nightly流水线看板指标对齐（Issue 特性详情 2-1)）

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/osp_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-004_oSP·Nightly流水线运营指标与Nightly流水线看板对齐验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-004_oSP·Nightly流水线运营指标与Nightly流水线看板对齐验证.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/alignment/test_tc_issue136_004.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/alignment/test_tc_issue136_004.py)

**前置条件**：- oSP 看板与 Nightly流水线看板均可加载；MindIE 项目 Nightly 数据齐备（项目级汇总 + 流水线级 2 条）

**测试步骤**

1. 采集 oSP 主页表格「Nightly流水线运营」区块全部指标列名（复用 TC-ISSUE136-002 证据）
2. 采集 Nightly流水线看板项目级汇总表与图表区全部指标名（复用既有 Nightly 用例表头证据：项目级汇总 22 列/流水线级汇总 24 列基线）
3. 建立共有指标交集清单（探索基线交集：流水线E2E执行时长[平均/最长](min)、流水线E2E执行时长[平均](min)(不含重试)、编译任务时长[平均/最长](min)、测试任务时长[平均/最长](min)、流水线E2E执行成功率、编译任务成功率、测试任务成功率、版本可用度）
4. 逐项断言：交集内每一指标在两个看板中的名称**逐字一致**（含单位与统计口径后缀）
5. 输出差异报告：oSP 缺失列清单（编译任务排队时长[P90]、编译任务执行时长[P90]、P0测试用例执行数/执行率、测试用例通过率、执行频次等探索基线缺失项）、oSP 独有列清单

**预期结果**

- 交集内所有共有指标名称在两看板间逐字一致
- oSP「Nightly流水线运营」区块既有指标列无丢失
- 差异报告已输出（缺失列补齐与否属待确认项，不单独判失败）

**备注**：- 设计依据：Issue 特性详情 2-1)；Nightly 看板侧列名同时受 FP1 指标管理口径影响，两看板应同步变更且保持一致

#### TC-ISSUE136-005 oSP既有独有指标列存在性回归验证

**测试功能场景**：FP2-c：指标对齐改造不误删 oSP 既有独有指标列（错误推测：对齐改造引入删列回归）

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/osp_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-005_oSP既有独有指标列存在性回归验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-005_oSP既有独有指标列存在性回归验证.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/alignment/test_tc_issue136_005.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/alignment/test_tc_issue136_005.py)

**前置条件**：- 同 TC-ISSUE136-002（oSP 主页表格表头已采集）

**测试步骤**

1. 从表头清单中定位探索基线登记的 oSP 独有指标列：PR闭环时长[平均](min)、PR闭环时长[最长](min)、资源总消耗 vCPU(核时)、NPU(卡时)、Memory(GB*h)
2. 逐列断言表头存在（列名因指标管理口径统一的等价变更可接受，见 TC-ISSUE136-010 映射）
3. 抽取一行数据（如 MindIE 行）验证独有指标列有值或规范的空值渲染（`--`）

**预期结果**

- PR闭环时长[平均/最长]、资源总消耗（vCPU/NPU/Memory）列均存在
- 数据行渲染正常（数值或 `--` 空值占位），无整列空白/塌陷

**备注**：- 独有列保留与否已在 1.7 风险表登记为串讲待确认项；本用例按「对齐不引入删列」设计，若开发确认按需求删除独有列，本用例基线随需求变更更新

#### TC-ISSUE136-006 oSP主页表格全指标列解释存在性验证

**测试功能场景**：FP3-a：oSP 主页表格所有指标列均有指标解释（Issue 特性详情 2-2)，DOM 载体探测

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/osp_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-006_oSP主页表格全指标列解释存在性验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-006_oSP主页表格全指标列解释存在性验证.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/tooltips/test_tc_issue136_006.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/tooltips/test_tc_issue136_006.py)

**前置条件**

- 同 TC-ISSUE136-002（oSP 主页表格表头已采集）
- 探索基线证据：改造前 7 看板表头 title 属性/tooltip 触发器/弹层均为 0（FP3 需求依据）

**测试步骤**

1. 取主页表格全部列，按等价类划分：标识列（社区/子组织/分组）与备注列豁免，其余为**指标列**（必须断言对象）
2. 逐指标列探测解释载体（三者其一即视为存在）：
   - 表头单元格 `title` 属性非空
   - 表头内 tooltip 触发元素（如 `.el-tooltip__trigger`、`aria-describedby`、帮助图标 `?`/`i` 图标）
   - 表头附带的说明链接/文案元素
3. 汇总输出「无解释指标列」清单
4. 断言清单为空

**预期结果**

- 主页表格所有指标列（代码仓运营/issue运营/PR流水线运营/Nightly流水线运营区块全部数据列）均存在至少一种解释载体
- 「无解释指标列」清单为空；非空则失败并附清单证据

**备注**：- 不限定实现形式（tooltip/弹层/链接均可，见 1.7 风险表）；探测方法沉淀自探索脚本 explore_136_tips.py / explore_136_title.py

#### TC-ISSUE136-007 oSP主页表格指标解释触发与内容非空验证

**测试功能场景**：FP3-b：指标解释可通过交互触发且内容非空（hover 场景法）

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/osp_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-007_oSP主页表格指标解释触发与内容非空验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-007_oSP主页表格指标解释触发与内容非空验证.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/tooltips/test_tc_issue136_007.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/tooltips/test_tc_issue136_007.py)

**前置条件**

- 同 TC-ISSUE136-006（解释载体存在）
- 指标列解释交互形式已实现（tooltip 类或弹层类）

**测试步骤**

1. 取 TC-ISSUE136-006 判定的指标列清单，逐列（或按区块抽样，每区块不少于 2 列）执行触发：
   - 载体为 tooltip：hover 表头触发元素，等待 `el-popper`/tooltip 弹层出现
   - 载体为链接/文案：点击/聚焦并捕获展开内容
   - 载体为 `title` 属性：直接读取属性值
2. 断言解释内容**非空**且**不等于列名本身**（解释应包含定义/公式/口径等增量信息）
3. 记录每列解释文本样本（供 TC-ISSUE136-008 人工比对复用）

**预期结果**

- 每个被测指标列的解释均可通过交互触发并成功捕获
- 解释内容非空、非纯列名重复
- 解释文本样本已落盘

**备注**：- hover 后弹层定位需处理 el-popper 挂载于 body 的场景（探索踩坑：弹层不在表头 DOM 子树内）

#### TC-ISSUE136-008 oSP指标解释内容与指标管理定义一致性验证

**测试功能场景**：FP3-c + FP1：指标解释内容与指标管理中指标定义/公式/判断规则一致（人工比对）

**用例等级**：P1<br>
**执行方式**：手工<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/osp_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-008_oSP指标解释内容与指标管理定义一致性验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-008_oSP指标解释内容与指标管理定义一致性验证.md)<br>
**用例脚本位置**：—

**前置条件**

- TC-ISSUE136-006/-007 已通过（解释存在且可触发），解释文本样本已落盘
- 指标管理列表可访问（/manageCenter/rDDashboard），88 条指标基线数据可查（exploration_tmp/explore_results_osp.json）

**测试步骤**

1. 从解释文本样本中选取关键指标抽查（不少于 10 个，覆盖：PR流水线执行次数、PR执行时长[P90]、PR代码检查任务时长、PR构建任务时长、PR测试任务时长、版本可用度、Nightly CI执行时长、资源消耗类、issue/PR 数量类、成功率类）
2. 逐项在指标管理中定位对应指标（按指标名称/指标Code），比对其「指标定义/公式」「达标判定」「判断规则」字段
3. 断言解释内容与指标管理定义语义一致（允许格式化差异，不允许口径/公式/阈值矛盾）
4. 重点验证红黄绿灯规则类指标（如 PR执行时长[P90]：≤阈值绿灯、>阈值且≤阈值×1.2 黄灯、>阈值×1.2 红灯、阈值默认 60min）的解释是否完整传达判断规则
5. 记录不一致项清单

**预期结果**

- 抽查的全部指标解释内容与指标管理定义/公式/判断规则语义一致
- 不一致项清单为空；非空项逐条登记（口径矛盾/公式错误/规则缺失分类）

**备注**

- 手工用例：解释文本与定义的语义一致性比对含主观判断，不做全自动化断言；自动化前置样本由 -007 产出
- 复用易用性用例 openlibing_ops_usability_202609_093（帮助小图标及信息验证）、openlibing_ops_usability_202609_036（字段含义清晰性验证）作为易用性维度补充

#### TC-ISSUE136-009 oSP下钻明细「项目运营明细」加载与指标一致性验证

**测试功能场景**：波及回归：FP1/FP2 改造后 oSP 下钻明细页加载与指标呈现一致性

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/osp_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-009_oSP下钻明细「项目运营明细」加载与指标一致性验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-009_oSP下钻明细「项目运营明细」加载与指标一致性验证.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/drilldown/test_tc_issue136_009.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/drilldown/test_tc_issue136_009.py)

**前置条件**：- oSP 主页表格已渲染且有可下钻数据行（如 MindIE 行）

**测试步骤**

1. 点击主页表格 MindIE 数据行，等待「MindIE项目运营明细」下钻页加载
2. 断言四个 tab 存在：代码仓运营、PR流水线运营、Nightly流水线运营、issue运营
3. 切换每个 tab，断言 tab 内容加载（表格/图表渲染，无空白）
4. 断言辅助图表存在：托管代码仓占比、分支数量 top5、贡献者人数 top5
5. 断言代码仓列表列齐备：代码仓、托管平台、分支数量、tag数量、贡献者人数、语言占比、是否已部署门禁
6. 比对下钻页「PR流水线运营」「Nightly流水线运营」tab 指标名称与主页表格同区块指标名称一致（同指标同名，含口径后缀）

**预期结果**

- 下钻页加载成功，四 tab 齐备且内容渲染
- 辅助图表与代码仓列表列齐备
- 下钻页与主页表格的同名指标名称一致（FP2 对齐口径统一后应同步体现）

**备注**：- 下钻触发方式为行点击（探索实测）；若行点击改为链接/按钮，以实际交互元素为准

#### TC-ISSUE136-010 oSP指标名称与指标管理已上线指标一致性验证

**测试功能场景**：FP1-c：oSP 看板指标名称与指标管理（已上线指标）口径一致（指标定义对接指标管理的呈现层断言）

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/osp_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-010_oSP指标名称与指标管理已上线指标一致性验证.md](../01_系统测试/运营运维/开源项目运营看板/TC-ISSUE136-010_oSP指标名称与指标管理已上线指标一致性验证.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/consistency/test_tc_issue136_010.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/open_source_project_dashboard/beta/consistency/test_tc_issue136_010.py)

**前置条件**：- oSP 主页表格表头已采集（TC-ISSUE136-002）；指标管理列表可访问且已采集全量指标清单（状态字段区分已上线/待上线，基线 88 条）

**测试步骤**

1. 取 oSP「PR流水线运营」「Nightly流水线运营」区块全部指标列名，预处理：剥离统计口径后缀（[平均]/[最长]/[P90]）与单位后缀（(min)/(核时)/(卡时)/(GB*h) 等）
2. 取指标管理**已上线**状态指标名称清单（待上线指标仅登记不参与断言）
3. 逐列建立映射：预处理后列名与指标管理指标名**完全一致**，或互为包含（列名含指标名/指标名含列名）
4. 断言：
   - 与 PR门禁看板/Nightly流水线看板共有的指标（TC-ISSUE136-003/-004 交集清单，must-map 集）**必须**建立映射且名称一致，任一未映射即失败
   - 其余列（oSP 独有运营指标）未建立映射的仅输出登记清单
5. 输出映射结果与未映射清单

**预期结果**

- must-map 集内全部指标与指标管理已上线指标建立映射且名称一致
- 已知口径矛盾点消除（改造前「编译任务时长」对应指标管理「PR构建任务时长」等矛盾，改造后列名与指标管理口径统一）
- 未映射清单仅含 oSP 独有运营指标（如资源总消耗类），并已登记

**备注**

- FP1 一致性断言限定已上线指标的原因见 1.7 风险表（指标管理存在待上线指标 10014/10015/10016/10017/10020 等）
- 指标管理清单采集复用 TC-ISSUE136-015 的数据源

#### TC-ISSUE136-014 测试资源消耗看板加载与指标基线断言

**测试功能场景**：FP1-b：测试资源看板（消耗）加载与指标卡/趋势/列表基线（对接指标管理后不破坏既有呈现）

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/test_resource_consumption_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/测试资源消耗看板/TC-ISSUE136-014_测试资源消耗看板加载与指标基线断言.md](../01_系统测试/运营运维/测试资源消耗看板/TC-ISSUE136-014_测试资源消耗看板加载与指标基线断言.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/test_resource_consumption_dashboard/beta/baseline/test_tc_issue136_014.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/test_resource_consumption_dashboard/beta/baseline/test_tc_issue136_014.py)

**前置条件**：- beta 已登录；MindIE（projectId=300036）社区列表数据存在（探索基线 57 条）

**测试步骤**

1. 会话守卫校验后 URL 直连 `/apps/tRCDashboard?projectId=300036`，等待 iframe `/ops/dashboard/test-dashboard` 渲染
2. 断言时间快捷筛选：今日、近7天、近30天、近90天
3. 断言 4 个指标卡：测试任务vCPU消耗、测试任务NPU消耗、测试用例vCPU消耗、测试用例NPU消耗（含单位 核时/卡时）
4. 断言 2 个趋势图标题：测试任务vCPU消耗趋势、测试任务NPU消耗趋势
5. 断言表格/卡片视图切换控件与「社区列表」表格
6. 断言表格列：社区、子组织/分组、测试任务vCPU消耗(核时)、测试任务NPU消耗(卡时)、测试用例vCPU消耗(核时)、测试用例NPU消耗(卡时)
7. 断言分页器存在且总数显示（基线 57 条，容差随数据增长），数据行非空

**预期结果**

- 看板完整加载，快捷筛选/指标卡/趋势图/视图切换/表格列/分页齐备
- 指标卡与表格列名因 FP1 指标管理口径统一的等价变更可接受（须可回溯至指标管理指标）

**备注**：- Issue 原文称「测试资源看板」，实际特性目录与菜单名为「测试资源消耗看板」，二者为同一对象（见 1.2 需求摘要）

#### TC-ISSUE136-015 指标管理列表加载与关键指标存在性验证

**测试功能场景**：FP1-a：指标管理数据源基线（5 看板指标定义对接的来源系统，只读断言）

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-09-22<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/136<br>
**来源模块**：openlibing-ops/rd_operations_dashboard_management

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202609/20260923/issue_136_【蓝区】【运营看板】开源项目运营看板优化-指标定义对接指标管理、指标名称统一等/01_系统测试/运营运维/研发运营看板管理/TC-ISSUE136-015_指标管理列表加载与关键指标存在性验证.md](../01_系统测试/运营运维/研发运营看板管理/TC-ISSUE136-015_指标管理列表加载与关键指标存在性验证.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/rd_operations_dashboard_management/beta/metric_list/test_tc_issue136_015.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/rd_operations_dashboard_management/beta/metric_list/test_tc_issue136_015.py)

**前置条件**

- beta 已登录，账号具备管理中心访问权限（p_tianyan）
- 指标管理已有指标数据（探索基线 88 条/5 页）

**测试步骤**

1. 会话守卫校验后 URL 直连 `/manageCenter/rDDashboard`，等待 iframe `/ops/management/metric` 渲染
2. 断言列表表头字段：指标名称、指标Code、领域、主题、应用类型、指标类型、维度、达标判定、判断规则、参考链接、状态、指标责任人、修改时间、最后修改人、操作
3. 断言关键指标存在（名称或指标Code 二选一命中）：
   - PR流水线执行次数（10001）
   - PR执行时长[P90]（10002，含红黄绿灯判断规则文案）
   - PR代码检查任务时长（10003）、PR构建任务时长（10004）、PR测试任务时长（10005）
   - PR构建/测试任务并发数（10008/10009）
   - 版本可用度（10018）、Nightly CI执行时长（10019）
4. 断言状态列取值合法：已上线 / 待上线（等价类：两类状态均应可见）
5. 断言操作能力入口存在（仅存在性，**不执行写操作**）：新增指标按钮、行操作（编辑/上线|下线/删除）
6. 断言筛选器存在：指标名称、领域主题、维度；分页器存在且可翻页（基线 5 页/88 条，容差随数据变化）
7. 采集全量指标清单（分页遍历，含名称/Code/状态字段）落盘，供 TC-ISSUE136-010/-012 一致性断言复用

**预期结果**

- 列表完整加载，15 个表头字段齐备
- 关键指标（10001~10005、10008/10009、10018、10019）全部存在，PR执行时长[P90] 含红黄绿灯判断规则
- 状态列取值仅含已上线/待上线；操作与筛选入口齐备
- 全量指标清单已落盘

**备注**：- 只读用例：新增/编辑/上线/下线/删除均为写操作，不在本 issue 范围（Issue 仅要求看板从指标管理**获取**定义），禁止执行
