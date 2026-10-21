# 用例清单 — issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化

> 团队：IPD管理控制与测试仿真 | 月度：202610 | 版本：20261019 | issue 编号：205 | issue 标题：【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化 | 用例总数：11（自动化 11 / 手工 0） | 更新日期：2026-10-20 | 由 testcase_pro 维护

> 月度版本树（进行中）：用例先落本 issue 目录（四类类型子目录与特性树同构），月底 consolidate 归集到 01~04 特性树；过程文档（测试策略/测试设计/需求串讲/测试反串讲/需求开发自验证/测试报告）见本目录 测试过程数据/。

## 用例统计

| 用例等级 | 自动化 | 手工 | 合计   |
| -------- | ------ | ---- | ------ |
| P1       | 11     | 0    | 11     |
| **合计** | 11     | 0    | **11** |

## 用例清单

### 01_系统测试（11 条）

| 用例编号        | 用例标题                                                            | 用例等级 | 执行方式 | 自动化方式 | 用例文本位置                                                                                                                                                                                                                                                                                                                                                                                                                                                             | 用例脚本位置                                                                                                                                                                                                                                                                                                           |
| --------------- | ------------------------------------------------------------------- | -------- | -------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TC-ISSUE205-065 | Github PR门禁看板代码仓指标汇总表默认不展示PR闭环时长               | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-065_Github PR门禁看板代码仓指标汇总表默认不展示PR闭环时长.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-065_Github%20PR门禁看板代码仓指标汇总表默认不展示PR闭环时长.md)                                         | [src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_065.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_065.py)                                     |
| TC-ISSUE205-066 | Github PR门禁看板代码仓指标汇总表默认不展示PR合入时长               | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-066_Github PR门禁看板代码仓指标汇总表默认不展示PR合入时长.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-066_Github%20PR门禁看板代码仓指标汇总表默认不展示PR合入时长.md)                                         | [src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_066.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_066.py)                                     |
| TC-ISSUE205-067 | Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[平均](min)字段 | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-067_Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[平均](min)字段.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-067_Github%20PR门禁看板代码仓指标汇总表新增门禁E2E执行时长%5B平均%5D%28min%29字段.md)     | [src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_067.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_067.py)                                     |
| TC-ISSUE205-068 | Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[P95](min)字段  | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-068_Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[P95](min)字段.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-068_Github%20PR门禁看板代码仓指标汇总表新增门禁E2E执行时长%5BP95%5D%28min%29字段.md)       | [src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_068.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_068.py)                                     |
| TC-ISSUE205-069 | Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[P90](min)字段  | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-069_Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[P90](min)字段.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-069_Github%20PR门禁看板代码仓指标汇总表新增门禁E2E执行时长%5BP90%5D%28min%29字段.md)       | [src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_069.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_069.py)                                     |
| TC-ISSUE205-070 | Github PR门禁看板代码仓指标汇总表新增PR总数字段                     | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-070_Github PR门禁看板代码仓指标汇总表新增PR总数字段.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-070_Github%20PR门禁看板代码仓指标汇总表新增PR总数字段.md)                                                     | [src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_070.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_070.py)                                     |
| TC-ISSUE205-071 | Github PR门禁看板代码仓指标汇总表执行状态筛选                       | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-071_Github PR门禁看板代码仓指标汇总表执行状态筛选.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-071_Github%20PR门禁看板代码仓指标汇总表执行状态筛选.md)                                                         | [src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_071.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_071.py)                                     |
| TC-ISSUE205-072 | Github PR门禁看板代码仓指标明细表默认不展示PR闭环时长(min)          | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标明细表/TC-ISSUE205-072_Github PR门禁看板代码仓指标明细表默认不展示PR闭环时长(min).md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标明细表/TC-ISSUE205-072_Github%20PR门禁看板代码仓指标明细表默认不展示PR闭环时长%28min%29.md)                           | [src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail/beta/test_tc_issue205_072.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail/beta/test_tc_issue205_072.py)                                       |
| TC-ISSUE205-073 | Github PR门禁看板代码仓指标明细表默认不展示PR合入时长(min)          | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标明细表/TC-ISSUE205-073_Github PR门禁看板代码仓指标明细表默认不展示PR合入时长(min).md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标明细表/TC-ISSUE205-073_Github%20PR门禁看板代码仓指标明细表默认不展示PR合入时长%28min%29.md)                           | [src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail/beta/test_tc_issue205_073.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail/beta/test_tc_issue205_073.py)                                       |
| TC-ISSUE205-074 | Github PR门禁看板代码仓指标明细表下钻workflow详情显示正确           | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标明细表下钻workflow详情/TC-ISSUE205-074_Github PR门禁看板代码仓指标明细表下钻workflow详情显示正确.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标明细表下钻workflow详情/TC-ISSUE205-074_Github%20PR门禁看板代码仓指标明细表下钻workflow详情显示正确.md) | [src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail_workflow_drilldown/beta/test_tc_issue205_074.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail_workflow_drilldown/beta/test_tc_issue205_074.py) |
| TC-ISSUE205-075 | Github PR门禁看板代码仓指标明细表下钻workflow详情数据获取           | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标明细表下钻workflow详情/TC-ISSUE205-075_Github PR门禁看板代码仓指标明细表下钻workflow详情数据获取.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标明细表下钻workflow详情/TC-ISSUE205-075_Github%20PR门禁看板代码仓指标明细表下钻workflow详情数据获取.md) | [src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail_workflow_drilldown/beta/test_tc_issue205_075.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail_workflow_drilldown/beta/test_tc_issue205_075.py) |

### 02_API测试（0 条）

（无）

### 03_DFX测试（0 条）

（无）

### 04_安全测试（0 条）

（无）

## 用例详情

### 01_系统测试

#### TC-ISSUE205-065 Github PR门禁看板代码仓指标汇总表默认不展示PR闭环时长

**测试功能场景**：脑图路径 Github PR门禁看板代码仓指标汇总表：Github PR门禁看板代码仓指标汇总表默认不展示PR闭环时长

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：passed<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-17<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/205<br>
**来源模块**：openlibing-ops/数字化运营/GitHub PR门禁看板代码仓指标汇总表

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-065_Github PR门禁看板代码仓指标汇总表默认不展示PR闭环时长.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-065_Github%20PR门禁看板代码仓指标汇总表默认不展示PR闭环时长.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_065.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_065.py)

**前置条件**：进入Github PR门禁看板代码仓指标汇总表页面

**测试步骤**

1.查看PR闭环时长
2.列设置查看PR闭环时长
3.列设置勾选PR闭环时长，查看PR闭环时长
4.列设置恢复默认，查看PR闭环时长
5.导出Github PR门禁看板代码仓指标汇总表，查看PR闭环时长

**预期结果**

1.PR闭环时长字段不可见
2.PR闭环时长字段可见
3.PR闭环时长字段可见
4.PR闭环时长字段不可见
5.PR闭环时长数字段可见

**备注**

- 设计来源：用户手工维护的 测试设计脑图.xmind 对应节点（原文照录）；用例等级为暂定（脑图未标注），待串讲确认；2026-10-20 beta 环境 pytest 自动化执行通过（执行凭证 assets/reports/latest/test_report.json）
- 预期结果含「数字段」为脑图原文笔误，实指「字段」（不修改脑图）

#### TC-ISSUE205-066 Github PR门禁看板代码仓指标汇总表默认不展示PR合入时长

**测试功能场景**：脑图路径 Github PR门禁看板代码仓指标汇总表：Github PR门禁看板代码仓指标汇总表默认不展示PR合入时长

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：passed<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-17<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/205<br>
**来源模块**：openlibing-ops/数字化运营/GitHub PR门禁看板代码仓指标汇总表

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-066_Github PR门禁看板代码仓指标汇总表默认不展示PR合入时长.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-066_Github%20PR门禁看板代码仓指标汇总表默认不展示PR合入时长.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_066.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_066.py)

**前置条件**：进入Github PR门禁看板代码仓指标汇总表页面

**测试步骤**

1.查看PR合入时长
2.列设置查看PR合入时长
3.列设置勾选PR合入时长，查看PR合入时长
4.列设置恢复默认，查看PR合入时长
5.导出Github PR门禁看板代码仓指标汇总表，查看PR合入时长

**预期结果**

1.PR合入时长字段不可见
2.PR合入时长字段可见
3.PR合入时长字段可见
4.PR合入时长字段不可见
5.PR合入时长数字段可见

**备注**

- 设计来源：用户手工维护的 测试设计脑图.xmind 对应节点（原文照录）；用例等级为暂定（脑图未标注），待串讲确认；2026-10-20 beta 环境 pytest 自动化执行通过（执行凭证 assets/reports/latest/test_report.json）
- 预期结果含「数字段」为脑图原文笔误，实指「字段」（不修改脑图）

#### TC-ISSUE205-067 Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[平均](min)字段

**测试功能场景**：脑图路径 Github PR门禁看板代码仓指标汇总表：Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[平均](min)字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：passed<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-17<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/205<br>
**来源模块**：openlibing-ops/数字化运营/GitHub PR门禁看板代码仓指标汇总表

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-067_Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[平均](min)字段.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-067_Github%20PR门禁看板代码仓指标汇总表新增门禁E2E执行时长%5B平均%5D%28min%29字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_067.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_067.py)

**前置条件**：进入Github PR门禁看板代码仓指标汇总表页面

**测试步骤**

1.查看门禁E2E执行时长[平均](min)
2.列设置查看门禁E2E执行时长[平均](min)
3.列设置勾选门禁E2E执行时长[平均](min)，查看门禁E2E执行时长[平均](min)
4.列设置恢复默认，查看门禁E2E执行时长[平均](min)
5.导出Github PR门禁看板代码仓指标汇总表，查看门禁E2E执行时长[平均](min)

**预期结果**

1.门禁E2E执行时长[平均](min)字段不可见
2.门禁E2E执行时长[平均](min)字段可见
3.门禁E2E执行时长[平均](min)字段可见
4.门禁E2E执行时长[平均](min)字段不可见
5.门禁E2E执行时长[平均](min)数字段可见

**备注**

- 设计来源：用户手工维护的 测试设计脑图.xmind 对应节点（原文照录）；用例等级为暂定（脑图未标注），待串讲确认；2026-10-20 beta 环境 pytest 自动化执行通过（执行凭证 assets/reports/latest/test_report.json）
- 关联历史缺陷 #280（门禁E2E执行时长(min)平均值、P90、P95计算错误，已关闭）本次回归通过
- 预期结果含「数字段」为脑图原文笔误，实指「字段」（不修改脑图）

#### TC-ISSUE205-068 Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[P95](min)字段

**测试功能场景**：脑图路径 Github PR门禁看板代码仓指标汇总表：Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[P95](min)字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：passed<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-17<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/205<br>
**来源模块**：openlibing-ops/数字化运营/GitHub PR门禁看板代码仓指标汇总表

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-068_Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[P95](min)字段.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-068_Github%20PR门禁看板代码仓指标汇总表新增门禁E2E执行时长%5BP95%5D%28min%29字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_068.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_068.py)

**前置条件**：进入Github PR门禁看板代码仓指标汇总表页面

**测试步骤**

1.查看门禁E2E执行时长[P95](min)
2.列设置查看门禁E2E执行时长[P95](min)
3.列设置勾选门禁E2E执行时长[P95](min))，查看门禁E2E执行时长[P95](min)
4.列设置恢复默认，查看门禁E2E执行时长[P95](min)
5.导出Github PR门禁看板代码仓指标汇总表，查看门禁E2E执行时长[P95](min)

**预期结果**

1.门禁E2E执行时长[P95](min)字段不可见
2.门禁E2E执行时长[P95](min)字段可见
3.门禁E2E执行时长[P95](min)字段可见
4.门禁E2E执行时长[P95](min)字段不可见
5.门禁E2E执行时长[P95](min)字段可见

**备注**

- 设计来源：用户手工维护的 测试设计脑图.xmind 对应节点（原文照录）；用例等级为暂定（脑图未标注），待串讲确认；2026-10-20 beta 环境 pytest 自动化执行通过（执行凭证 assets/reports/latest/test_report.json）
- 关联历史缺陷 #280（门禁E2E执行时长(min)平均值、P90、P95计算错误，已关闭）本次回归通过
- 测试步骤 3 含「[P95](min))」多余右括号为脑图原文笔误（不修改脑图）

#### TC-ISSUE205-069 Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[P90](min)字段

**测试功能场景**：脑图路径 Github PR门禁看板代码仓指标汇总表：Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[P90](min)字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：passed<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-17<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/205<br>
**来源模块**：openlibing-ops/数字化运营/GitHub PR门禁看板代码仓指标汇总表

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-069_Github PR门禁看板代码仓指标汇总表新增门禁E2E执行时长[P90](min)字段.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-069_Github%20PR门禁看板代码仓指标汇总表新增门禁E2E执行时长%5BP90%5D%28min%29字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_069.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_069.py)

**前置条件**：进入Github PR门禁看板代码仓指标汇总表页面

**测试步骤**

1.查看门禁E2E执行时长[P90](min)
2.列设置查看门禁E2E执行时长[P90](min)
3.列设置去勾选门禁E2E执行时长[P90](min)，查看门禁E2E执行时长[P90](min)
4.列设置恢复默认，查看门禁E2E执行时长[P90](min)
5.导出Github PR门禁看板代码仓指标汇总表，查看门禁E2E执行时长[P90](min)

**预期结果**

1.门禁E2E执行时长[P90](min)字段可见
2.门禁E2E执行时长[P90](min)段可见
3.门禁E2E执行时长[P90](min)字段不可见
4.门禁E2E执行时长[P90](min)字段可见
5.门禁E2E执行时长[P90](min)字段可见

**备注**

- 设计来源：用户手工维护的 测试设计脑图.xmind 对应节点（原文照录）；用例等级为暂定（脑图未标注），待串讲确认；2026-10-20 beta 环境 pytest 自动化执行通过（执行凭证 assets/reports/latest/test_report.json）
- 关联历史缺陷 #280（门禁E2E执行时长(min)平均值、P90、P95计算错误，已关闭）本次回归通过
- 预期结果含「段可见」为脑图原文笔误，实指「字段可见」（不修改脑图）

#### TC-ISSUE205-070 Github PR门禁看板代码仓指标汇总表新增PR总数字段

**测试功能场景**：脑图路径 Github PR门禁看板代码仓指标汇总表：Github PR门禁看板代码仓指标汇总表新增PR总数字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-17<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/205<br>
**来源模块**：openlibing-ops/数字化运营/GitHub PR门禁看板代码仓指标汇总表

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-070_Github PR门禁看板代码仓指标汇总表新增PR总数字段.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-070_Github%20PR门禁看板代码仓指标汇总表新增PR总数字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_070.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_070.py)

**前置条件**：进入Github PR门禁看板代码仓指标汇总表页面

**测试步骤**

1.查看PR总数
2.列设置查看PR总数
3.列设置去勾选PR总数
4.列设置恢复默认，查看PR总数
5.导出Github PR门禁看板代码仓指标汇总表，查看PR总数

**预期结果**

1.PR总数字段可见
2.PR总数段可见
3.PR总数字段置灰，不可去勾选
4.PR总数字段可见
5.PR总数字段可见

**备注**

- 设计来源：用户手工维护的 测试设计脑图.xmind 对应节点（原文照录）；用例等级为暂定（脑图未标注），待串讲确认；用例状态 blocked：beta 未部署 PR总数字段（汇总表 PR总数列未上线），待部署后执行
- 预期结果含「数字段」为脑图原文笔误，实指「字段」（不修改脑图）
- 预期结果含「段可见」为脑图原文笔误，实指「字段可见」（不修改脑图）
- PR总数列为固定展示列，列设置中置灰不可取消勾选（脑图预期 3 原文）

#### TC-ISSUE205-071 Github PR门禁看板代码仓指标汇总表执行状态筛选

**测试功能场景**：脑图路径 Github PR门禁看板代码仓指标汇总表：Github PR门禁看板代码仓指标汇总表执行状态筛选

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-17<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/205<br>
**来源模块**：openlibing-ops/数字化运营/GitHub PR门禁看板代码仓指标汇总表

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标汇总表/TC-ISSUE205-071_Github PR门禁看板代码仓指标汇总表执行状态筛选.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标汇总表/TC-ISSUE205-071_Github%20PR门禁看板代码仓指标汇总表执行状态筛选.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_071.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_summary/beta/test_tc_issue205_071.py)

**前置条件**：进入Github PR门禁看板代码仓指标汇总表页面

**测试步骤**

1.执行状态筛选
2.导出Github PR门禁看板代码仓指标汇总表

**预期结果**

1.执行状态筛选正常
2.Github PR门禁看板代码仓指标汇总表导出数据为筛选后的数据

**备注**：- 设计来源：用户手工维护的 测试设计脑图.xmind 对应节点（原文照录）；用例等级为暂定（脑图未标注），待串讲确认；用例状态 blocked：beta 未部署执行状态筛选功能，待部署后执行

#### TC-ISSUE205-072 Github PR门禁看板代码仓指标明细表默认不展示PR闭环时长(min)

**测试功能场景**：脑图路径 Github PR门禁看板代码仓指标明细表：Github PR门禁看板代码仓指标明细表默认不展示PR闭环时长(min)

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-17<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/205<br>
**来源模块**：openlibing-ops/数字化运营/GitHub PR门禁看板代码仓指标明细表

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标明细表/TC-ISSUE205-072_Github PR门禁看板代码仓指标明细表默认不展示PR闭环时长(min).md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标明细表/TC-ISSUE205-072_Github%20PR门禁看板代码仓指标明细表默认不展示PR闭环时长%28min%29.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail/beta/test_tc_issue205_072.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail/beta/test_tc_issue205_072.py)

**前置条件**：Github PR门禁看板代码仓指标明细表

**测试步骤**

1.查看PR闭环时长
2.列设置查看PR闭环时长
3.列设置勾选PR闭环时长，查看PR闭环时长
4.列设置恢复默认，查看PR闭环时长
5.导出Github PR门禁看板代码仓指标汇总表，查看PR闭环时长

**预期结果**

1.PR闭环时长字段不可见
2.PR闭环时长字段可见
3.PR闭环时长字段可见
4.PR闭环时长字段不可见
5.PR闭环时长数字段可见

**备注**

- 设计来源：用户手工维护的 测试设计脑图.xmind 对应节点（原文照录）；用例等级为暂定（脑图未标注），待串讲确认；用例状态 blocked：beta 未部署代码仓指标明细表，待部署后执行
- 预期结果含「数字段」为脑图原文笔误，实指「字段」（不修改脑图）
- 节点归属「代码仓指标明细表」分支，步骤 5 导出对象写「汇总表」为脑图原文，执行时以明细表导出为准（不修改脑图）

#### TC-ISSUE205-073 Github PR门禁看板代码仓指标明细表默认不展示PR合入时长(min)

**测试功能场景**：脑图路径 Github PR门禁看板代码仓指标明细表：Github PR门禁看板代码仓指标明细表默认不展示PR合入时长(min)

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-17<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/205<br>
**来源模块**：openlibing-ops/数字化运营/GitHub PR门禁看板代码仓指标明细表

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标明细表/TC-ISSUE205-073_Github PR门禁看板代码仓指标明细表默认不展示PR合入时长(min).md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标明细表/TC-ISSUE205-073_Github%20PR门禁看板代码仓指标明细表默认不展示PR合入时长%28min%29.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail/beta/test_tc_issue205_073.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail/beta/test_tc_issue205_073.py)

**前置条件**：Github PR门禁看板代码仓指标明细表

**测试步骤**

1.查看PR合入时长
2.列设置查看PR合入时长
3.列设置勾选PR合入时长，查看PR合入时长
4.列设置恢复默认，查看PR合入时长
5.导出Github PR门禁看板代码仓指标汇总表，查看PR合入时长

**预期结果**

1.PR合入时长字段不可见
2.PR合入时长字段可见
3.PR合入时长字段可见
4.PR合入时长字段不可见
5.PR合入时长数字段可见

**备注**

- 设计来源：用户手工维护的 测试设计脑图.xmind 对应节点（原文照录）；用例等级为暂定（脑图未标注），待串讲确认；用例状态 blocked：beta 未部署代码仓指标明细表，待部署后执行
- 预期结果含「数字段」为脑图原文笔误，实指「字段」（不修改脑图）
- 节点归属「代码仓指标明细表」分支，步骤 5 导出对象写「汇总表」为脑图原文，执行时以明细表导出为准（不修改脑图）

#### TC-ISSUE205-074 Github PR门禁看板代码仓指标明细表下钻workflow详情显示正确

**测试功能场景**：脑图路径 Github PR门禁看板代码仓指标明细表下钻workflow详情：Github PR门禁看板代码仓指标明细表下钻workflow详情显示正确

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-17<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/205<br>
**来源模块**：openlibing-ops/数字化运营/GitHub PR门禁看板代码仓指标明细表下钻workflow详情

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标明细表下钻workflow详情/TC-ISSUE205-074_Github PR门禁看板代码仓指标明细表下钻workflow详情显示正确.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标明细表下钻workflow详情/TC-ISSUE205-074_Github%20PR门禁看板代码仓指标明细表下钻workflow详情显示正确.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail_workflow_drilldown/beta/test_tc_issue205_074.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail_workflow_drilldown/beta/test_tc_issue205_074.py)

**前置条件**：进入Github PR门禁看板代码仓指标明细表下钻workflow详情页面

**测试步骤**：1.查看Github PR门禁看板代码仓指标明细表下钻workflow详情

**预期结果**：列表展示workflow明细，字段分别有job名称、创建时间、运行时间、结束时间、状态。job名称、状态支持筛选、创建时间、运行时间、结束时间支持排序

**备注**：- 设计来源：用户手工维护的 测试设计脑图.xmind 对应节点（原文照录）；用例等级为暂定（脑图未标注），待串讲确认；用例状态 blocked：beta 未部署明细表下钻 workflow 详情，待部署后执行

#### TC-ISSUE205-075 Github PR门禁看板代码仓指标明细表下钻workflow详情数据获取

**测试功能场景**：脑图路径 Github PR门禁看板代码仓指标明细表下钻workflow详情：Github PR门禁看板代码仓指标明细表下钻workflow详情数据获取

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-17<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/205<br>
**来源模块**：openlibing-ops/数字化运营/GitHub PR门禁看板代码仓指标明细表下钻workflow详情

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/01_系统测试/数字化运营/GitHub PR门禁看板代码仓指标明细表下钻workflow详情/TC-ISSUE205-075_Github PR门禁看板代码仓指标明细表下钻workflow详情数据获取.md](01_系统测试/数字化运营/GitHub%20PR门禁看板代码仓指标明细表下钻workflow详情/TC-ISSUE205-075_Github%20PR门禁看板代码仓指标明细表下钻workflow详情数据获取.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail_workflow_drilldown/beta/test_tc_issue205_075.py](../../../../../../src/automation/ipd-management/ui/digital_operations/github_pr_gate_dashboard/repo_metrics_detail_workflow_drilldown/beta/test_tc_issue205_075.py)

**前置条件**：进入Github PR门禁看板代码仓指标明细表下钻workflow详情页面

**测试步骤**：1.Github PR门禁看板代码仓指标明细表下钻workflow详情数据获取

**预期结果**：与workflow数据一致

**备注**

- 设计来源：用户手工维护的 测试设计脑图.xmind 对应节点（原文照录）；用例等级为暂定（脑图未标注），待串讲确认；用例状态 blocked：beta 未部署明细表下钻 workflow 详情，待部署后执行
- 关联历史缺陷 #281（job未执行但状态标记为失败，已关闭）待部署后回归
