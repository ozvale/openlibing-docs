# 用例清单 — issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示

> 团队：IPD管理控制与测试仿真 | 月度：202610 | 版本：20261015 | issue 编号：211 | issue 标题：【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示 | 用例总数：19（自动化 19 / 手工 0） | 更新日期：2026-10-15 | 由 testcase_pro 维护

> 月度版本树（进行中）：用例先落本 issue 目录（四类类型子目录与特性树同构），月底 consolidate 归集到 01~04 特性树；过程文档（测试策略/测试设计/测试串讲/测试反串讲/版本历史/测试报告）见本目录 测试过程数据/。

## 用例统计

| 用例等级 | 自动化 | 手工 | 合计   |
| -------- | ------ | ---- | ------ |
| P0       | 2      | 0    | 2      |
| P1       | 15     | 0    | 15     |
| P2       | 2      | 0    | 2      |
| **合计** | 19     | 0    | **19** |

## 用例清单

### 01_系统测试（13 条）

| 用例编号        | 用例标题                                                                                   | 用例等级 | 执行方式 | 自动化方式 | 用例文本位置                                                                                                                                                                                                                                                                                                                                                                                  | 用例脚本位置                                                                                                                                                                                                                                            |
| --------------- | ------------------------------------------------------------------------------------------ | -------- | -------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TC-ISSUE211-022 | 资源运营看板项目效率表格下钻新增“PR NPU使用（占用）平均消耗（卡时）”字段                   | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-022_项目效率表格下钻新增PRNPU使用（占用）平均消耗（卡时）字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-022_项目效率表格下钻新增PRNPU使用（占用）平均消耗（卡时）字段.md)           | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_022.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_022.py) |
| TC-ISSUE211-025 | 资源运营看板项目效率表格下钻流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）趋势图      | P2       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-025_流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）趋势图.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-025_流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）趋势图.md)           | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_025.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_025.py) |
| TC-ISSUE211-026 | 资源运营看板项目效率表格下钻流水线效率Nightly表格新增NPU使用（占用）平均消耗（卡时）趋势图 | P2       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-026_流水线效率Nightly表格新增NPU使用（占用）平均消耗（卡时）趋势图.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-026_流水线效率Nightly表格新增NPU使用（占用）平均消耗（卡时）趋势图.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_026.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_026.py) |
| TC-ISSUE211-041 | 资源运营看板新增“PR NPU使用（占用）平均消耗（卡时）”字段                                   | P0       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-041_新增PRNPU使用（占用）平均消耗（卡时）字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-041_新增PRNPU使用（占用）平均消耗（卡时）字段.md)                                           | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_041.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_041.py) |
| TC-ISSUE211-042 | 资源运营看板新增“共享池NPU利用率”字段                                                      | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-042_新增共享池NPU利用率字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-042_新增共享池NPU利用率字段.md)                                                                               | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_042.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_042.py) |
| TC-ISSUE211-043 | 资源运营看板新增“独占池NPU利用率”字段                                                      | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-043_新增独占池NPU利用率字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-043_新增独占池NPU利用率字段.md)                                                                               | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_043.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_043.py) |
| TC-ISSUE211-044 | 资源运营看板新增“NPU使用率”字段                                                            | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-044_新增NPU使用率字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-044_新增NPU使用率字段.md)                                                                                           | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_044.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_044.py) |
| TC-ISSUE211-045 | 资源运营看板新增“共享池NPU使用率”字段                                                      | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-045_新增共享池NPU使用率字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-045_新增共享池NPU使用率字段.md)                                                                               | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_045.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_045.py) |
| TC-ISSUE211-046 | 资源运营看板新增“独占池NPU使用率”字段                                                      | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-046_新增独占池NPU使用率字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-046_新增独占池NPU使用率字段.md)                                                                               | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_046.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_046.py) |
| TC-ISSUE211-047 | “PR NPU使用（占用）平均消耗（卡时）”字段排序                                               | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-047_PRNPU使用（占用）平均消耗（卡时）字段排序.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-047_PRNPU使用（占用）平均消耗（卡时）字段排序.md)                                           | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_047.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_047.py) |
| TC-ISSUE211-048 | “NPU使用率”字段排序                                                                        | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-048_NPU使用率字段排序.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-048_NPU使用率字段排序.md)                                                                                           | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_048.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_048.py) |
| TC-ISSUE211-049 | 资源运营看板项目效率表格下钻流水线效率PR表格新增“NPU使用（占用）平均消耗（卡时）”字段      | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-049_流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-049_流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）字段.md)               | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_049.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_049.py) |
| TC-ISSUE211-055 | 资源运营看板项目效率表格下钻流水线效率Nightly表格新增“NPU使用（占用）平均消耗（卡时）”字段 | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-055_流水线效率Nightly表格新增NPU使用（占用）平均消耗（卡时）字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-055_流水线效率Nightly表格新增NPU使用（占用）平均消耗（卡时）字段.md)     | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_055.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_055.py) |

### 02_API测试（6 条）

| 用例编号        | 用例标题                                   | 用例等级 | 执行方式 | 自动化方式 | 用例文本位置                                                                                                                                                                                                                                                                                                                                  | 用例脚本位置                                                                                                                                                                                                                                              |
| --------------- | ------------------------------------------ | -------- | -------- | ---------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TC-ISSUE211-028 | “PR NPU使用（占用）平均消耗（卡时）”值计算 | P0       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/02_API测试/资源运营/资源运营看板/TC-ISSUE211-028_PRNPU使用（占用）平均消耗（卡时）值计算.md](../02_API测试/资源运营/资源运营看板/TC-ISSUE211-028_PRNPU使用（占用）平均消耗（卡时）值计算.md) | [src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_028.py](../../../../../../../src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_028.py) |
| TC-ISSUE211-029 | “NPU使用率”字段计算                        | P1       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/02_API测试/资源运营/资源运营看板/TC-ISSUE211-029_NPU使用率字段计算.md](../02_API测试/资源运营/资源运营看板/TC-ISSUE211-029_NPU使用率字段计算.md)                                             | [src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_029.py](../../../../../../../src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_029.py) |
| TC-ISSUE211-030 | “独占池NPU使用率”字段计算                  | P1       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/02_API测试/资源运营/资源运营看板/TC-ISSUE211-030_独占池NPU使用率字段计算.md](../02_API测试/资源运营/资源运营看板/TC-ISSUE211-030_独占池NPU使用率字段计算.md)                                 | [src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_030.py](../../../../../../../src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_030.py) |
| TC-ISSUE211-031 | “共享池NPU使用率”字段计算                  | P1       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/02_API测试/资源运营/资源运营看板/TC-ISSUE211-031_共享池NPU使用率字段计算.md](../02_API测试/资源运营/资源运营看板/TC-ISSUE211-031_共享池NPU使用率字段计算.md)                                 | [src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_031.py](../../../../../../../src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_031.py) |
| TC-ISSUE211-032 | “独占池NPU利用率”字段计算                  | P1       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/02_API测试/资源运营/资源运营看板/TC-ISSUE211-032_独占池NPU利用率字段计算.md](../02_API测试/资源运营/资源运营看板/TC-ISSUE211-032_独占池NPU利用率字段计算.md)                                 | [src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_032.py](../../../../../../../src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_032.py) |
| TC-ISSUE211-033 | “共享池NPU利用率”字段计算                  | P1       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/02_API测试/资源运营/资源运营看板/TC-ISSUE211-033_共享池NPU利用率字段计算.md](../02_API测试/资源运营/资源运营看板/TC-ISSUE211-033_共享池NPU利用率字段计算.md)                                 | [src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_033.py](../../../../../../../src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_033.py) |

### 03_DFX测试（0 条）

（无）

### 04_安全测试（0 条）

（无）

## 用例详情

### 01_系统测试

#### TC-ISSUE211-022 资源运营看板项目效率表格下钻新增“PR NPU使用（占用）平均消耗（卡时）”字段

**测试功能场景**：设计脑图 › 项目下钻总览 › 资源运营看板项目效率表格下钻新增“PR NPU使用（占用）平均消耗（卡时）”字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-022_项目效率表格下钻新增PRNPU使用（占用）平均消耗（卡时）字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-022_项目效率表格下钻新增PRNPU使用（占用）平均消耗（卡时）字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_022.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_022.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**

1. 项目效率表格查看“PR NPU使用（占用）平均消耗（卡时）”字段
2. 列设置去勾选“PR NPU使用（占用）平均消耗（卡时）”字段，项目效率表格查看“PR NPU使用（占用）平均消耗（卡时）”字段
3. 恢复列设置默认字段，项目效率表格查看“PR NPU使用（占用）平均消耗（卡时）”字段

**预期结果**

1. ”PR NPU使用（占用）平均消耗（卡时）”字段可见
2. ”PR NPU使用（占用）平均消耗（卡时）”字段不可见
3. ”PR NPU使用（占用）平均消耗（卡时）”字段可见

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-025 资源运营看板项目效率表格下钻流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）趋势图

**测试功能场景**：设计脑图 › PR › 资源运营看板项目效率表格下钻流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）趋势图

**用例等级**：P2<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-025_流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）趋势图.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-025_流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）趋势图.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_025.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_025.py)

**前置条件**：进入资源运营看板项目效率表格下钻流水线效率PR表格页面

**测试步骤**

1. 资源运营看板项目效率表格下钻流水线效率PR表格查看NPU使用（占用）平均消耗（卡时）趋势图
2. 筛选时间，查看NPU使用（占用）平均消耗（卡时）趋势图时间范围

**预期结果**

1. ”流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）趋势图存在
2. 查看NPU使用（占用）平均消耗（卡时）趋势图时间范围与筛选时间一致

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-026 资源运营看板项目效率表格下钻流水线效率Nightly表格新增NPU使用（占用）平均消耗（卡时）趋势图

**测试功能场景**：设计脑图 › Nightly › 资源运营看板项目效率表格下钻流水线效率Nightly表格新增NPU使用（占用）平均消耗（卡时）趋势图

**用例等级**：P2<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-026_流水线效率Nightly表格新增NPU使用（占用）平均消耗（卡时）趋势图.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-026_流水线效率Nightly表格新增NPU使用（占用）平均消耗（卡时）趋势图.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_026.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_026.py)

**前置条件**：进入资源运营看板项目效率表格下钻流水线效率PR表格页面

**测试步骤**

1. 资源运营看板项目效率表格下钻流水线效率Nightly表格查看NPU使用（占用）平均消耗（卡时）趋势图
2. 筛选时间，查看NPU使用（占用）平均消耗（卡时）趋势图时间范围

**预期结果**

1. ”流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）趋势图存在
2. 查看NPU使用（占用）平均消耗（卡时）趋势图时间范围与筛选时间一致

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）
- 脑图前置与预期 1 原文写「PR表格」（Nightly 趋势图节点），原文保留

#### TC-ISSUE211-041 资源运营看板新增“PR NPU使用（占用）平均消耗（卡时）”字段

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › 资源运营看板新增“PR NPU使用（占用）平均消耗（卡时）”字段

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-041_新增PRNPU使用（占用）平均消耗（卡时）字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-041_新增PRNPU使用（占用）平均消耗（卡时）字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_041.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_041.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**

1. 项目效率表格查看“PR NPU使用（占用）平均消耗（卡时）”字段
2. 列设置去勾选“PR NPU使用（占用）平均消耗（卡时）”字段，项目效率表格查看“PR NPU使用（占用）平均消耗（卡时）”字段
3. 恢复列设置默认字段，项目效率表格查看“PR NPU使用（占用）平均消耗（卡时）”字段

**预期结果**

1. ”PR NPU使用（占用）平均消耗（卡时）”字段可见
2. ”PR NPU使用（占用）平均消耗（卡时）”字段不可见
3. ”PR NPU使用（占用）平均消耗（卡时）”字段可见

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-042 资源运营看板新增“共享池NPU利用率”字段

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › 资源运营看板新增“共享池NPU利用率”字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-042_新增共享池NPU利用率字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-042_新增共享池NPU利用率字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_042.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_042.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**

1. 项目效率表格查看“共享池NPU利用率”字段
2. 列设置去勾选“共享池NPU利用率”字段，项目效率表格查看“共享池NPU利用率”字段
3. 恢复列设置默认字段，项目效率表格查看“共享池NPU利用率”字段

**预期结果**

1. ”共享池NPU利用率”字段不可见
2. ”共享池NPU利用率”字段可见
3. ”共享池NPU利用率”字段不可见

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-043 资源运营看板新增“独占池NPU利用率”字段

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › 资源运营看板新增“独占池NPU利用率”字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-043_新增独占池NPU利用率字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-043_新增独占池NPU利用率字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_043.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_043.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**

1. 项目效率表格查看“独占池NPU利用率”字段
2. 列设置去勾选“独占池NPU利用率”字段，项目效率表格查看“独占池NPU利用率”字段
3. 恢复列设置默认字段，项目效率表格查看“独占池NPU利用率”字段

**预期结果**

1. ”独占池NPU利用率”字段不可见
2. ”独占池NPU利用率”字段可见
3. ”独占池NPU利用率”字段不可见

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-044 资源运营看板新增“NPU使用率”字段

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › 资源运营看板新增“NPU使用率”字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-044_新增NPU使用率字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-044_新增NPU使用率字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_044.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_044.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**

1. 项目效率表格查看“NPU使用率”字段
2. 列设置去勾选“NPU使用率”字段，项目效率表格查看“NPU使用率”字段
3. 恢复列设置默认字段，项目效率表格查看“NPU使用率”字段

**预期结果**

1. ”NPU使用率”字段可见
2. ”NPU使用率”字段不可见
3. ”NPU使用率”字段可见

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-045 资源运营看板新增“共享池NPU使用率”字段

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › 资源运营看板新增“共享池NPU使用率”字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-045_新增共享池NPU使用率字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-045_新增共享池NPU使用率字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_045.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_045.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**

1. 项目效率表格查看“共享池NPU使用率”字段
2. 列设置去勾选“共享池NPU使用率”字段，项目效率表格查看“共享池NPU使用率”字段
3. 恢复列设置默认字段，项目效率表格查看“共享池NPU使用率”字段

**预期结果**

1. ”共享池NPU使用率”字段不可见
2. ”共享池NPU使用率”字段可见
3. ”共享池NPU使用率”字段不可见

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-046 资源运营看板新增“独占池NPU使用率”字段

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › 资源运营看板新增“独占池NPU使用率”字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-046_新增独占池NPU使用率字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-046_新增独占池NPU使用率字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_046.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_046.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**

1. 项目效率表格查看“独占池NPU使用率”字段
2. 列设置去勾选“独占池NPU使用率”字段，项目效率表格查看“独占池NPU使用率”字段
3. 恢复列设置默认字段，项目效率表格查看“独占池NPU使用率”字段

**预期结果**

1. ”独占池NPU使用率”字段不可见
2. ”独占池NPU使用率”字段可见
3. ”独占池NPU使用率”字段不可见

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）
- 脑图预期原文编号为「1./1./1.」，已按 1/2/3 呈现，文字未改

#### TC-ISSUE211-047 “PR NPU使用（占用）平均消耗（卡时）”字段排序

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › “PR NPU使用（占用）平均消耗（卡时）”字段排序

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-047_PRNPU使用（占用）平均消耗（卡时）字段排序.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-047_PRNPU使用（占用）平均消耗（卡时）字段排序.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_047.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_047.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**：1. “PR NPU使用（占用）平均消耗（卡时）”字段排序

**预期结果**：1. “PR NPU使用（占用）平均消耗（卡时）”字段排序功能正常

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-048 “NPU使用率”字段排序

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › “NPU使用率”字段排序

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-048_NPU使用率字段排序.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-048_NPU使用率字段排序.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_048.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_048.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**：1. “NPU使用率”字段排序

**预期结果**：1. “NPU使用率”字段排序正常

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-049 资源运营看板项目效率表格下钻流水线效率PR表格新增“NPU使用（占用）平均消耗（卡时）”字段

**测试功能场景**：设计脑图 › PR › 资源运营看板项目效率表格下钻流水线效率PR表格新增“NPU使用（占用）平均消耗（卡时）”字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-049_流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-049_流水线效率PR表格新增NPU使用（占用）平均消耗（卡时）字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_049.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_049.py)

**前置条件**：进入资源运营看板项目效率表格下钻流水线效率PR表格页面

**测试步骤**

1. 资源运营看板项目效率表格下钻流水线效率PR表格查看“NPU使用（占用）平均消耗（卡时）”字段
2. 列设置去勾选“NPU使用（占用）平均消耗（卡时）”字段，项目效率表格查看“NPU使用（占用）平均消耗（卡时）”字段
3. 恢复列设置默认字段，项目效率表格查看“NPU使用（占用）平均消耗（卡时）”字段

**预期结果**

1. ”NPU使用（占用）平均消耗（卡时）”字段可见
2. ”NPU使用（占用）平均消耗（卡时）”字段不可见
3. ”NPU使用（占用）平均消耗（卡时）”字段可见

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-055 资源运营看板项目效率表格下钻流水线效率Nightly表格新增“NPU使用（占用）平均消耗（卡时）”字段

**测试功能场景**：设计脑图 › Nightly › 资源运营看板项目效率表格下钻流水线效率Nightly表格新增“NPU使用（占用）平均消耗（卡时）”字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/01_系统测试/资源运营/资源运营看板/TC-ISSUE211-055_流水线效率Nightly表格新增NPU使用（占用）平均消耗（卡时）字段.md](../01_系统测试/资源运营/资源运营看板/TC-ISSUE211-055_流水线效率Nightly表格新增NPU使用（占用）平均消耗（卡时）字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_055.py](../../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_055.py)

**前置条件**：进入资源运营看板项目效率表格下钻流水线效率Nightly表格页面

**测试步骤**

1. 资源运营看板项目效率表格下钻流水线效率Nightly表格查看“NPU使用（占用）平均消耗（卡时）”字段
2. 列设置去勾选“NPU使用（占用）平均消耗（卡时）”字段，项目效率表格查看“NPU使用（占用）平均消耗（卡时）”字段
3. 恢复列设置默认字段，项目效率表格查看“NPU使用（占用）平均消耗（卡时）”字段

**预期结果**

1. ”NPU使用（占用）平均消耗（卡时）”字段可见
2. ”NPU使用（占用）平均消耗（卡时）”字段不可见
3. ”NPU使用（占用）平均消耗（卡时）”字段可见

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

### 02_API测试

#### TC-ISSUE211-028 “PR NPU使用（占用）平均消耗（卡时）”值计算

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › “PR NPU使用（占用）平均消耗（卡时）”值计算

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/02_API测试/资源运营/资源运营看板/TC-ISSUE211-028_PRNPU使用（占用）平均消耗（卡时）值计算.md](../02_API测试/资源运营/资源运营看板/TC-ISSUE211-028_PRNPU使用（占用）平均消耗（卡时）值计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_028.py](../../../../../../../src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_028.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**：1. “PR NPU使用（占用）平均消耗（卡时）”值计算

**预期结果**：1. “PR NPU使用（占用）平均消耗（卡时）”等于NPU 使用(占用)(卡时)/运行次数

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-029 “NPU使用率”字段计算

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › “NPU使用率”字段计算

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/02_API测试/资源运营/资源运营看板/TC-ISSUE211-029_NPU使用率字段计算.md](../02_API测试/资源运营/资源运营看板/TC-ISSUE211-029_NPU使用率字段计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_029.py](../../../../../../../src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_029.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**：1. “NPU使用率”字段计算

**预期结果**：1. NPU使用率等于Σ(NPU资源池使用卡时) / 资源池总卡时*100%

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-030 “独占池NPU使用率”字段计算

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › “独占池NPU使用率”字段计算

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/02_API测试/资源运营/资源运营看板/TC-ISSUE211-030_独占池NPU使用率字段计算.md](../02_API测试/资源运营/资源运营看板/TC-ISSUE211-030_独占池NPU使用率字段计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_030.py](../../../../../../../src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_030.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**：1. “独占池NPU使用率”字段计算

**预期结果**：1. 独占池NPU使用率等于Σ(独占NPU资源池使用卡时) / 独占资源池总卡时*100%

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-031 “共享池NPU使用率”字段计算

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › “共享池NPU使用率”字段计算

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/02_API测试/资源运营/资源运营看板/TC-ISSUE211-031_共享池NPU使用率字段计算.md](../02_API测试/资源运营/资源运营看板/TC-ISSUE211-031_共享池NPU使用率字段计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_031.py](../../../../../../../src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_031.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**：1. “共享池NPU使用率”字段计算

**预期结果**：1. 共享池NPU使用率等于Σ(共享NPU资源池使用卡时) / 共享资源池总卡时*100%

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）

#### TC-ISSUE211-032 “独占池NPU利用率”字段计算

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › “独占池NPU利用率”字段计算

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/02_API测试/资源运营/资源运营看板/TC-ISSUE211-032_独占池NPU利用率字段计算.md](../02_API测试/资源运营/资源运营看板/TC-ISSUE211-032_独占池NPU利用率字段计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_032.py](../../../../../../../src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_032.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**：1. “独占池NPU利用率”字段计算

**预期结果**：1. 独占池NPU使用率等于Σ(独占NPU资源池利用（卡时) / 独占资源池总卡时*100%

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）
- 脑图预期原文「利用（卡时)」括号不配对，原文保留

#### TC-ISSUE211-033 “共享池NPU利用率”字段计算

**测试功能场景**：设计脑图 › 资源运营看板项目效率表格 › “共享池NPU利用率”字段计算

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-15<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/211<br>
**来源模块**：openlibing-ops/resource_operations_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_211_【1015】【蓝区】【运营看板】资源运营看板看板优化-PR的NPU平均消耗卡时展示/02_API测试/资源运营/资源运营看板/TC-ISSUE211-033_共享池NPU利用率字段计算.md](../02_API测试/资源运营/资源运营看板/TC-ISSUE211-033_共享池NPU利用率字段计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_033.py](../../../../../../../src/automation/ipd-management/api/resource_operations/resource_operations_dashboard/beta/test_tc_issue211_033.py)

**前置条件**：进入资源运营看板的资源总览页面

**测试步骤**：1. “共享池NPU利用率”字段计算

**预期结果**：1. 共享池NPU使用率等于Σ(共享NPU资源池利用卡时) / 共享资源池总卡时*100%

**备注**

- blocked：本 issue 后端实现与前端改造未部署 beta（2026-10-12 走查均未启动），部署后执行
- v5.2 按用户要求完全按设计脑图节点原文重新生成（标题/前置条件/测试步骤/预期结果与脑图逐字一致）
