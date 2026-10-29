# 用例清单 — issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)

> 团队：IPD管理控制与测试仿真 | 月度：202610 | 版本：20261030 | issue 编号：300 | issue 标题：【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景) | 用例总数：18（自动化 18 / 手工 0） | 更新日期：2026-10-28 | 由 testcase_pro 维护

> 月度版本树（进行中）：用例先落本 issue 目录（四类类型子目录与特性树同构），月底 consolidate 归集到 01~04 特性树；过程文档（测试策略/测试设计/需求串讲/测试反串讲/需求开发自验证/测试报告）见本目录 测试过程数据/。

## 用例统计

| 用例等级 | 自动化 | 手工 | 合计 |
|------|------|------|------|
| P0 | 18 | 0 | 18 |
| **合计** | 18 | 0 | **18** |

## 用例清单

### 01_系统测试（18 条）

| 用例编号 | 用例标题 | 用例等级 | 执行方式 | 自动化方式 | 用例文本位置 | 用例脚本位置 |
|------|------|------|------|------|------|------|
| TC-ISSUE300-001 | 资源运营看板使用率分析页面新增总卡数、使用卡数、等待卡数曲线图 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-001_资源运营看板使用率分析页面新增总卡数、使用卡数、等待卡数曲线图.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-001_资源运营看板使用率分析页面新增总卡数、使用卡数、等待卡数曲线图.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_001.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_001.py) |
| TC-ISSUE300-009 | 资源运营看板使用率分析页面查看总卡数、使用卡数、等待卡数曲线图下钻也面 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-009_资源运营看板使用率分析页面查看总卡数、使用卡数、等待卡数曲线图下钻也面.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-009_资源运营看板使用率分析页面查看总卡数、使用卡数、等待卡数曲线图下钻也面.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_009.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_009.py) |
| TC-ISSUE300-010 | 资源运营看板使用率分析页面总卡数等于资源池汇总卡数 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-010_资源运营看板使用率分析页面总卡数等于资源池汇总卡数.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-010_资源运营看板使用率分析页面总卡数等于资源池汇总卡数.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_010.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_010.py) |
| TC-ISSUE300-011 | 资源运营看板使用率分析页面总卡数与资源池筛选联动 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-011_资源运营看板使用率分析页面总卡数与资源池筛选联动.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-011_资源运营看板使用率分析页面总卡数与资源池筛选联动.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_011.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_011.py) |
| TC-ISSUE300-012 | 资源运营看板使用率分析页面使用卡数等于运行明细的申请卡数汇聚 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-012_资源运营看板使用率分析页面使用卡数等于运行明细的申请卡数汇聚.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-012_资源运营看板使用率分析页面使用卡数等于运行明细的申请卡数汇聚.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_012.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_012.py) |
| TC-ISSUE300-013 | 资源运营看板使用率分析页面等待卡数等于排队明细的申请卡数汇聚 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-013_资源运营看板使用率分析页面等待卡数等于排队明细的申请卡数汇聚.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-013_资源运营看板使用率分析页面等待卡数等于排队明细的申请卡数汇聚.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_013.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_013.py) |
| TC-ISSUE300-014 | 资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务增加申请卡数(张)字段 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-014_资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务增加申请卡数(张)字段.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-014_资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务增加申请卡数%28张%29字段.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_014.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_014.py) |
| TC-ISSUE300-015 | 资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务申请卡数(张)字段值计算 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-015_资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务申请卡数(张)字段值计算.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-015_资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务申请卡数%28张%29字段值计算.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_015.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_015.py) |
| TC-ISSUE300-016 | 资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务增加申请卡数(张)字段 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-016_资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务增加申请卡数(张)字段.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-016_资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务增加申请卡数%28张%29字段.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_016.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_016.py) |
| TC-ISSUE300-017 | 资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务申请卡数(张)字段值计算 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-017_资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务申请卡数(张)字段值计算.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-017_资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务申请卡数%28张%29字段值计算.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_017.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_017.py) |
| TC-ISSUE300-018 | 资源运营看板使用率分析页面的明细-排队任务页面github流水线任务增加申请卡数(张)字段 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-018_资源运营看板使用率分析页面的明细-排队任务页面github流水线任务增加申请卡数(张)字段.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-018_资源运营看板使用率分析页面的明细-排队任务页面github流水线任务增加申请卡数%28张%29字段.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_018.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_018.py) |
| TC-ISSUE300-019 | 资源运营看板使用率分析页面的明细-排队任务页面github流水线任务申请卡数(张)字段值计算 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-019_资源运营看板使用率分析页面的明细-排队任务页面github流水线任务申请卡数(张)字段值计算.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-019_资源运营看板使用率分析页面的明细-排队任务页面github流水线任务申请卡数%28张%29字段值计算.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_019.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_019.py) |
| TC-ISSUE300-020 | 资源运营看板使用率分析页面的明细-运行任务页面github流水线任务增加申请卡数(张)字段 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-020_资源运营看板使用率分析页面的明细-运行任务页面github流水线任务增加申请卡数(张)字段.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-020_资源运营看板使用率分析页面的明细-运行任务页面github流水线任务增加申请卡数%28张%29字段.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_020.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_020.py) |
| TC-ISSUE300-021 | 资源运营看板使用率分析页面的明细-运行任务页面github流水线任务申请卡数(张)字段值计算 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-021_资源运营看板使用率分析页面的明细-运行任务页面github流水线任务申请卡数(张)字段值计算.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-021_资源运营看板使用率分析页面的明细-运行任务页面github流水线任务申请卡数%28张%29字段值计算.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_021.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_021.py) |
| TC-ISSUE300-022 | 资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务增加申请卡数(张)字段 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-022_资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务增加申请卡数(张)字段.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-022_资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务增加申请卡数%28张%29字段.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_022.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_022.py) |
| TC-ISSUE300-023 | 资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务申请卡数(张)字段值计算 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-023_资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务申请卡数(张)字段值计算.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-023_资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务申请卡数%28张%29字段值计算.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_023.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_023.py) |
| TC-ISSUE300-024 | 资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务增加申请卡数(张)字段 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-024_资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务增加申请卡数(张)字段.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-024_资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务增加申请卡数%28张%29字段.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_024.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_024.py) |
| TC-ISSUE300-025 | 资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务申请卡数(张)字段值计算 | P0 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-025_资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务申请卡数(张)字段值计算.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-025_资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务申请卡数%28张%29字段值计算.md) | [src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_025.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_025.py) |

### 02_API测试（0 条）

（无）

### 03_DFX测试（0 条）

（无）

### 04_安全测试（0 条）

（无）

## 用例详情

### 01_系统测试

#### TC-ISSUE300-001 资源运营看板使用率分析页面新增总卡数、使用卡数、等待卡数曲线图

**测试功能场景**：测试设计脑图 > 使用率页面卡数曲线图（总卡数/使用卡数/等待卡数） > 资源运营看板使用率分析页面新增总卡数、使用卡数、等待卡数曲线图

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-26<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-趋势分析图

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-001_资源运营看板使用率分析页面新增总卡数、使用卡数、等待卡数曲线图.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-001_资源运营看板使用率分析页面新增总卡数、使用卡数、等待卡数曲线图.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_001.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_001.py)

**前置条件**：进入资源运营看板使用率分析页面

**测试步骤**：1. 查看总卡数、使用卡数、等待卡数图

**预期结果**：1. 总卡数、使用卡数、等待卡数图存在

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版，本节点为原 001「三条曲线，图例与tooltip完整渲染」的重写，内容以脑图最新版为准）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造（三条卡数曲线），待 20261030 迭代部署后执行
- 三条卡数曲线数值口径由 TC-ISSUE300-010~013 覆盖（总卡数/使用卡数/等待卡数计算与联动），本用例仅验证曲线图存在性

#### TC-ISSUE300-009 资源运营看板使用率分析页面查看总卡数、使用卡数、等待卡数曲线图下钻也面

**测试功能场景**：测试设计脑图 > 使用率页面卡数曲线图（总卡数/使用卡数/等待卡数） > 资源运营看板使用率分析页面查看总卡数、使用卡数、等待卡数曲线图下钻也面

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-趋势分析图

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-009_资源运营看板使用率分析页面查看总卡数、使用卡数、等待卡数曲线图下钻也面.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-009_资源运营看板使用率分析页面查看总卡数、使用卡数、等待卡数曲线图下钻也面.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_009.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_009.py)

**前置条件**：进入资源运营看板使用率分析页面

**测试步骤**：1. 点击总卡数、使用卡数、等待卡数图的值

**预期结果**：1. 进入任务明细页面

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造，待 20261030 迭代部署后执行
- 编号说明：脑图该节点 t 标注与第 1 节点重复为「TC-ISSUE300-001」（XMind 复制节点残留），按用例编号不可复用规则新编 009
- 脑图节点标题「下钻也面」为原文笔误（应为「下钻页面」），按用户脑图只读约束未改动，仅在此登记

#### TC-ISSUE300-010 资源运营看板使用率分析页面总卡数等于资源池汇总卡数

**测试功能场景**：测试设计脑图 > 使用率页面卡数曲线图（总卡数/使用卡数/等待卡数） > 资源运营看板使用率分析页面总卡数等于资源池汇总卡数

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-趋势分析图

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-010_资源运营看板使用率分析页面总卡数等于资源池汇总卡数.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-010_资源运营看板使用率分析页面总卡数等于资源池汇总卡数.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_010.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_010.py)

**前置条件**：进入资源运营看板使用率分析页面

**测试步骤**：1. 计算总卡数

**预期结果**

1. 总卡数等于资源池汇总卡数

```sql
SELECT SUM(actual_npu_num) AS total_actual_npu
FROM sdi_rd_efc_server_machine_hidevlab;
```

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造，待 20261030 迭代部署后执行
- 编号说明：脑图该节点 t 标注与第 1 节点重复为「TC-ISSUE300-001」（XMind 复制节点残留），按用例编号不可复用规则新编 010
- 对拍 SQL 为脑图定稿口径：总卡数 = 机器静态维表 `sdi_rd_efc_server_machine_hidevlab` 的 actual_npu_num 汇总（一卡多代折算），经 `src/utils/doris_client.py` 直连 Doris 核对，采用相对断言不硬编码绝对值

#### TC-ISSUE300-011 资源运营看板使用率分析页面总卡数与资源池筛选联动

**测试功能场景**：测试设计脑图 > 使用率页面卡数曲线图（总卡数/使用卡数/等待卡数） > 资源运营看板使用率分析页面总卡数与资源池筛选联动

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-趋势分析图

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-011_资源运营看板使用率分析页面总卡数与资源池筛选联动.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-011_资源运营看板使用率分析页面总卡数与资源池筛选联动.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_011.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_011.py)

**前置条件**：进入资源运营看板使用率分析页面

**测试步骤**：1. 筛选资源池，查看总卡数

**预期结果**

1. 总卡数与资源池筛选联动

```sql
SELECT resource_pool_name,
       COUNT(*) AS machine_cnt,
       SUM(actual_npu_num) AS total_actual_npu
FROM sdi_rd_efc_server_machine_hidevlab
GROUP BY resource_pool_name
ORDER BY total_actual_npu DESC;
```

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造，待 20261030 迭代部署后执行
- 编号说明：脑图该节点 t 标注与第 1 节点重复为「TC-ISSUE300-001」（XMind 复制节点残留），按用例编号不可复用规则新编 011
- 对拍 SQL 为脑图定稿口径：按资源池分组汇总 actual_npu_num，筛选某资源池后页面总卡数应与对应分组值一致

#### TC-ISSUE300-012 资源运营看板使用率分析页面使用卡数等于运行明细的申请卡数汇聚

**测试功能场景**：测试设计脑图 > 使用率页面卡数曲线图（总卡数/使用卡数/等待卡数） > 资源运营看板使用率分析页面使用卡数等于运行明细的申请卡数汇聚

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-趋势分析图

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-012_资源运营看板使用率分析页面使用卡数等于运行明细的申请卡数汇聚.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-012_资源运营看板使用率分析页面使用卡数等于运行明细的申请卡数汇聚.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_012.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_012.py)

**前置条件**：进入资源运营看板使用率分析页面

**测试步骤**：1. 计算使用卡数

**预期结果**：1. 使用卡数等于运行明细的申请卡数汇聚

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造，待 20261030 迭代部署后执行
- 编号说明：脑图该节点 t 标注与第 1 节点重复为「TC-ISSUE300-001」（XMind 复制节点残留），按用例编号不可复用规则新编 012
- 口径为脑图定稿：使用卡数 = 运行任务明细各 job 申请卡数汇聚（job 级申请卡数公式见 TC-ISSUE300-017/021/025），执行时打开任务明细运行任务页汇总比对

#### TC-ISSUE300-013 资源运营看板使用率分析页面等待卡数等于排队明细的申请卡数汇聚

**测试功能场景**：测试设计脑图 > 使用率页面卡数曲线图（总卡数/使用卡数/等待卡数） > 资源运营看板使用率分析页面等待卡数等于排队明细的申请卡数汇聚

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-趋势分析图

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-013_资源运营看板使用率分析页面等待卡数等于排队明细的申请卡数汇聚.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-013_资源运营看板使用率分析页面等待卡数等于排队明细的申请卡数汇聚.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_013.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_013.py)

**前置条件**：进入资源运营看板使用率分析页面

**测试步骤**：1. 计算申请卡数

**预期结果**：1. 等待卡数等于排队明细的申请卡数汇聚

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造，待 20261030 迭代部署后执行
- 编号说明：脑图该节点 t 标注与第 1 节点重复为「TC-ISSUE300-001」（XMind 复制节点残留），按用例编号不可复用规则新编 013
- 脑图步骤原文为「1.计算申请卡数」（指排队明细各 job 申请卡数汇聚），未改动；口径为脑图定稿：等待卡数 = 排队任务明细各 job 申请卡数汇聚（job 级申请卡数公式见 TC-ISSUE300-015/019/023）
- gitcode 存在无排队样本日（2026-10-19 排队秒为 0），等待卡数零值场景真实存在，执行时按实际样本核对

#### TC-ISSUE300-014 资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务增加申请卡数(张)字段

**测试功能场景**：测试设计脑图 > 明细页面页面增加申请卡数 > codearts > 资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务增加申请卡数(张)字段

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-任务明细

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-014_资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务增加申请卡数(张)字段.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-014_资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务增加申请卡数%28张%29字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_014.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_014.py)

**前置条件**：进入资源运营看板使用率分析页面的明细-排队任务页面

**测试步骤**：1. 查看codearts流水线任务的申请卡数(张)字段

**预期结果**：1. 申请卡数(张)字段存在

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造（明细页申请卡数列），待 20261030 迭代部署后执行
- 编号说明：脑图该节点无 t 标注，按顺序新编 014；列名「申请卡数(张)」与 issue 标题「任务实际申请卡数」一致

#### TC-ISSUE300-015 资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务申请卡数(张)字段值计算

**测试功能场景**：测试设计脑图 > 明细页面页面增加申请卡数 > codearts > 资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务申请卡数(张)字段值计算

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-任务明细

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-015_资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务申请卡数(张)字段值计算.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-015_资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务申请卡数%28张%29字段值计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_015.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_015.py)

**前置条件**：进入资源运营看板使用率分析页面的明细-排队任务页面

**测试步骤**：1. 查看codearts流水线任务的申请卡数(张)的值

**预期结果**

1. dwr_rd_efc_build_job_fact表job_name字段筛选任务名，job_start_time字段筛选开始时间，job_run_start_time字段筛选结束时间，npu_second的值除job_duration的值计算结果向下取整，下限为1与申请卡数一致

```sql
SELECT
    job_name,
    job_start_time,
    job_run_start_time,
    npu_second,
    job_duration,
    GREATEST(FLOOR(CAST(npu_second AS DOUBLE) / job_duration), 1) AS 申请卡数
FROM internal.openlibing.dwr_rd_efc_build_job_fact
WHERE job_name = 'UT_ARM_A2_Part_02'
  AND job_start_time > '2026-09-14 18:10:00'
  AND job_run_start_time < '2026-09-14 18:15:00'
  AND job_duration > 0;
```

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造，待 20261030 迭代部署后执行
- 编号说明：脑图该节点无 t 标注，按顺序新编 015
- 对拍 SQL 为脑图定稿口径：codearts 申请卡数 = GREATEST(FLOOR(npu_second/job_duration), 1)，数据源 `internal.openlibing.dwr_rd_efc_build_job_fact`；样本 job 名与时间窗以脑图 SQL 为准，执行时若样本不存在按同口径换样

#### TC-ISSUE300-016 资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务增加申请卡数(张)字段

**测试功能场景**：测试设计脑图 > 明细页面页面增加申请卡数 > codearts > 资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务增加申请卡数(张)字段

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-任务明细

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-016_资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务增加申请卡数(张)字段.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-016_资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务增加申请卡数%28张%29字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_016.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_016.py)

**前置条件**：进入资源运营看板使用率分析页面的明细-运行任务页面

**测试步骤**：1. 查看codearts流水线任务的申请卡数(张)字段

**预期结果**：1. 申请卡数(张)字段存在

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造（明细页申请卡数列），待 20261030 迭代部署后执行
- 编号说明：脑图该节点无 t 标注，按顺序新编 016

#### TC-ISSUE300-017 资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务申请卡数(张)字段值计算

**测试功能场景**：测试设计脑图 > 明细页面页面增加申请卡数 > codearts > 资源运营看板使用率分析页面的明细-排队任务页面codearts流水线任务申请卡数(张)字段值计算（脑图第 4 节点，标签与第 2 节点重复；实际场景以前置条件「明细-运行任务页面」为准）

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-任务明细

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-017_资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务申请卡数(张)字段值计算.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-017_资源运营看板使用率分析页面的明细-运行任务页面codearts流水线任务申请卡数%28张%29字段值计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_017.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_017.py)

**前置条件**：进入资源运营看板使用率分析页面的明细-运行任务页面

**测试步骤**：1. 查看codearts流水线任务的申请卡数(张)的值

**预期结果**

1. dwr_rd_efc_build_job_fact表job_name字段筛选任务名，job_run_start_time字段筛选开始时间，job_end_time字段筛选结束时间，npu_second的值除job_duration的值计算结果向下取整，下限为1与申请卡数一致

```sql
SELECT
    job_name,
    job_run_start_time,
    job_end_time,
    npu_second,
    job_duration,
    GREATEST(FLOOR(CAST(npu_second AS DOUBLE) / job_duration), 1) AS 申请卡数
FROM internal.openlibing.dwr_rd_efc_build_job_fact
WHERE job_name = 'UT_ARM_A2_Part_02'
  AND job_run_start_time > '2026-09-14 18:10:00'
  AND job_end_time < '2026-09-14 18:45:00'
  AND job_duration > 0;
```

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造，待 20261030 迭代部署后执行
- 编号说明：脑图该节点无 t 标注，按顺序新编 017
- 标题校正登记：脑图该节点标签与上一节点重复（均写「排队任务页面…字段值计算」），但其前置条件为「明细-运行任务页面」且 SQL 时间窗字段为 job_run_start_time/job_end_time（运行窗口），本用例标题按前置条件场景定为「运行任务页面」，脑图原文未改动
- 对拍 SQL 为脑图定稿口径：codearts 申请卡数 = GREATEST(FLOOR(npu_second/job_duration), 1)，数据源 `internal.openlibing.dwr_rd_efc_build_job_fact`

#### TC-ISSUE300-018 资源运营看板使用率分析页面的明细-排队任务页面github流水线任务增加申请卡数(张)字段

**测试功能场景**：测试设计脑图 > 明细页面页面增加申请卡数 > github > 资源运营看板使用率分析页面的明细-排队任务页面github流水线任务增加申请卡数(张)字段

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-任务明细

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-018_资源运营看板使用率分析页面的明细-排队任务页面github流水线任务增加申请卡数(张)字段.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-018_资源运营看板使用率分析页面的明细-排队任务页面github流水线任务增加申请卡数%28张%29字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_018.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_018.py)

**前置条件**：进入资源运营看板使用率分析页面的明细-排队任务页面

**测试步骤**：1. 查看github流水线任务的申请卡数(张)字段

**预期结果**：1. 申请卡数(张)字段存在

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造（明细页申请卡数列），待 20261030 迭代部署后执行
- 编号说明：脑图该节点无 t 标注，按顺序新编 018；列名「申请卡数(张)」与 issue 标题「任务实际申请卡数」一致

#### TC-ISSUE300-019 资源运营看板使用率分析页面的明细-排队任务页面github流水线任务申请卡数(张)字段值计算

**测试功能场景**：测试设计脑图 > 明细页面页面增加申请卡数 > github > 资源运营看板使用率分析页面的明细-排队任务页面github流水线任务申请卡数(张)字段值计算

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-任务明细

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-019_资源运营看板使用率分析页面的明细-排队任务页面github流水线任务申请卡数(张)字段值计算.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-019_资源运营看板使用率分析页面的明细-排队任务页面github流水线任务申请卡数%28张%29字段值计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_019.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_019.py)

**前置条件**：进入资源运营看板使用率分析页面的明细-排队任务页面

**测试步骤**：1. 查看github流水线任务的申请卡数(张)的值

**预期结果**

1. dwr_rd_efc_workflow_run_job_github_fact表job_name字段筛选任务名，job_start_time字段筛选开始时间，job_run_start_time字段筛选结束时间，npu_second的值除job_duration的值计算结果向下取整，下限为1与申请卡数一致

```sql
SELECT
    job_name,
    job_start_time,
    job_run_start_time,
    npu_second,
    job_duration,
    GREATEST(FLOOR(CAST(npu_second AS DOUBLE) / job_duration), 1) AS 申请卡数
FROM internal.openlibing.dwr_rd_efc_workflow_run_job_github_fact
WHERE job_name = 'forward / test / collect / collect'
  AND job_start_time > '2026-09-14 18:10:00'
  AND job_run_start_time < '2026-09-14 18:15:00'
  AND job_duration > 0;
```

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造，待 20261030 迭代部署后执行
- 编号说明：脑图该节点无 t 标注，按顺序新编 019
- 对拍 SQL 为脑图定稿口径：github 申请卡数 = GREATEST(FLOOR(npu_second/job_duration), 1)，数据源 `internal.openlibing.dwr_rd_efc_workflow_run_job_github_fact`

#### TC-ISSUE300-020 资源运营看板使用率分析页面的明细-运行任务页面github流水线任务增加申请卡数(张)字段

**测试功能场景**：测试设计脑图 > 明细页面页面增加申请卡数 > github > 资源运营看板使用率分析页面的明细-运行任务页面github流水线任务增加申请卡数(张)字段

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-任务明细

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-020_资源运营看板使用率分析页面的明细-运行任务页面github流水线任务增加申请卡数(张)字段.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-020_资源运营看板使用率分析页面的明细-运行任务页面github流水线任务增加申请卡数%28张%29字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_020.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_020.py)

**前置条件**：进入资源运营看板使用率分析页面的明细-运行任务页面

**测试步骤**：1. 查看github流水线任务的申请卡数(张)字段

**预期结果**：1. 申请卡数(张)字段存在

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造（明细页申请卡数列），待 20261030 迭代部署后执行
- 编号说明：脑图该节点无 t 标注，按顺序新编 020；列名「申请卡数(张)」与 issue 标题「任务实际申请卡数」一致

#### TC-ISSUE300-021 资源运营看板使用率分析页面的明细-运行任务页面github流水线任务申请卡数(张)字段值计算

**测试功能场景**：测试设计脑图 > 明细页面页面增加申请卡数 > github > 资源运营看板使用率分析页面的明细-排队任务页面github流水线任务申请卡数(张)字段值计算（脑图第 4 节点，标签与第 2 节点重复；实际场景以前置条件「明细-运行任务页面」为准）

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-任务明细

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-021_资源运营看板使用率分析页面的明细-运行任务页面github流水线任务申请卡数(张)字段值计算.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-021_资源运营看板使用率分析页面的明细-运行任务页面github流水线任务申请卡数%28张%29字段值计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_021.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_021.py)

**前置条件**：进入资源运营看板使用率分析页面的明细-运行任务页面

**测试步骤**：1. 查看github流水线任务的申请卡数(张)的值

**预期结果**

1. dwr_rd_efc_workflow_run_job_github_fact表job_name字段筛选任务名，job_run_start_time字段筛选开始时间，job_end_time字段筛选结束时间，npu_second的值除job_duration的值计算结果向下取整，下限为1与申请卡数一致

```sql
SELECT
    job_name,
    job_run_start_time,
    job_end_time,
    npu_second,
    job_duration,
    GREATEST(FLOOR(CAST(npu_second AS DOUBLE) / job_duration), 1) AS 申请卡数
FROM internal.openlibing.dwr_rd_efc_workflow_run_job_github_fact
WHERE job_name = 'forward / test / collect / collect'
  AND job_run_start_time > '2026-09-14 18:10:00'
  AND job_end_time < '2026-09-14 18:15:00'
  AND job_duration > 0;
```

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造，待 20261030 迭代部署后执行
- 编号说明：脑图该节点无 t 标注，按顺序新编 021
- 标题校正登记：脑图该节点标签与上一节点重复（均写「排队任务页面…字段值计算」），但其前置条件为「明细-运行任务页面」且 SQL 时间窗字段为 job_run_start_time/job_end_time（运行窗口），本用例标题按前置条件场景定为「运行任务页面」，脑图原文未改动
- 对拍 SQL 为脑图定稿口径：github 申请卡数 = GREATEST(FLOOR(npu_second/job_duration), 1)，数据源 `internal.openlibing.dwr_rd_efc_workflow_run_job_github_fact`

#### TC-ISSUE300-022 资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务增加申请卡数(张)字段

**测试功能场景**：测试设计脑图 > 明细页面页面增加申请卡数 > gitcode > 资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务增加申请卡数(张)字段

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-任务明细

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-022_资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务增加申请卡数(张)字段.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-022_资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务增加申请卡数%28张%29字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_022.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_022.py)

**前置条件**：进入资源运营看板使用率分析页面的明细-排队任务页面

**测试步骤**：1. 查看gitcode流水线任务的申请卡数(张)字段

**预期结果**：1. 申请卡数(张)字段存在

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造（明细页申请卡数列），待 20261030 迭代部署后执行
- 编号说明：脑图该节点无 t 标注，按顺序新编 022；列名「申请卡数(张)」与 issue 标题「任务实际申请卡数」一致

#### TC-ISSUE300-023 资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务申请卡数(张)字段值计算

**测试功能场景**：测试设计脑图 > 明细页面页面增加申请卡数 > gitcode > 资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务申请卡数(张)字段值计算

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-任务明细

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-023_资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务申请卡数(张)字段值计算.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-023_资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务申请卡数%28张%29字段值计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_023.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_023.py)

**前置条件**：进入资源运营看板使用率分析页面的明细-排队任务页面

**测试步骤**：1. 查看gitcode流水线任务的申请卡数(张)的值

**预期结果**

1. dwr_rd_efc_workflow_run_job_gitcode_fact表job_name字段筛选任务名，job_start_time字段筛选开始时间，job_run_start_time字段筛选结束时间，npu_second的值除job_duration的值计算结果向下取整，下限为1与申请卡数一致

```sql
SELECT
    job_name,
    job_start_time,
    job_run_start_time,
    npu_second,
    job_duration,
    GREATEST(FLOOR(CAST(npu_second AS DOUBLE) / job_duration), 1) AS 申请卡数
FROM internal.openlibing.dwr_rd_efc_workflow_run_job_gitcode_fact
WHERE job_name = 'SCA'
  AND job_start_time > '2026-09-14 18:10:00'
  AND job_run_start_time < '2026-09-14 18:15:00'
  AND job_duration > 0;
```

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造，待 20261030 迭代部署后执行
- 编号说明：脑图该节点无 t 标注，按顺序新编 023
- 对拍 SQL 为脑图定稿口径：gitcode 申请卡数 = GREATEST(FLOOR(npu_second/job_duration), 1)，数据源 `internal.openlibing.dwr_rd_efc_workflow_run_job_gitcode_fact`

#### TC-ISSUE300-024 资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务增加申请卡数(张)字段

**测试功能场景**：测试设计脑图 > 明细页面页面增加申请卡数 > gitcode > 资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务增加申请卡数(张)字段

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-任务明细

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-024_资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务增加申请卡数(张)字段.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-024_资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务增加申请卡数%28张%29字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_024.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_024.py)

**前置条件**：进入资源运营看板使用率分析页面的明细-运行任务页面

**测试步骤**：1. 查看gitcode流水线任务的申请卡数(张)字段

**预期结果**：1. 申请卡数(张)字段存在

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造（明细页申请卡数列），待 20261030 迭代部署后执行
- 编号说明：脑图该节点无 t 标注，按顺序新编 024；列名「申请卡数(张)」与 issue 标题「任务实际申请卡数」一致

#### TC-ISSUE300-025 资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务申请卡数(张)字段值计算

**测试功能场景**：测试设计脑图 > 明细页面页面增加申请卡数 > gitcode > 资源运营看板使用率分析页面的明细-排队任务页面gitcode流水线任务申请卡数(张)字段值计算（脑图第 4 节点，标签与第 2 节点重复；实际场景以前置条件「明细-运行任务页面」为准）

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：blocked<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-28<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/300<br>
**来源模块**：openlibing-ops/资源运营看板/使用率分析-任务明细

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261030/issue_300_【蓝区】【运营看板】下钻页面增加任务实际申请卡数(github、gitcode流水线代码化、codearts统一资源池场景)/01_系统测试/资源运营/资源运营看板/TC-ISSUE300-025_资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务申请卡数(张)字段值计算.md](01_系统测试/资源运营/资源运营看板/TC-ISSUE300-025_资源运营看板使用率分析页面的明细-运行任务页面gitcode流水线任务申请卡数%28张%29字段值计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_025.py](../../../../../../src/automation/ipd-management/ui/resource_operations/resource_operations_dashboard/usage_analysis/beta/test_tc_issue300_025.py)

**前置条件**：进入资源运营看板使用率分析页面的明细-运行任务页面

**测试步骤**：1. 查看gitcode流水线任务的申请卡数(张)的值

**预期结果**

1. dwr_rd_efc_workflow_run_job_gitcode_fact表job_name字段筛选任务名，job_run_start_time字段筛选开始时间，job_end_time字段筛选结束时间，npu_second的值除job_duration的值计算结果向下取整，下限为1与申请卡数一致

```sql
SELECT
    job_name,
    job_run_start_time,
    job_end_time,
    npu_second,
    job_duration,
    GREATEST(FLOOR(CAST(npu_second AS DOUBLE) / job_duration), 1) AS 申请卡数
FROM internal.openlibing.dwr_rd_efc_workflow_run_job_gitcode_fact
WHERE job_name = 'SCA'
  AND job_run_start_time > '2026-09-14 18:10:00'
  AND job_end_time < '2026-09-14 18:15:00'
  AND job_duration > 0;
```

**备注**

- 设计来源：测试设计脑图.xmind 对应节点（用户 2026-10-28 手工更新版）；用例等级 P0 暂定，待串讲确认；用例状态 blocked：beta 未部署本 issue 前端改造，待 20261030 迭代部署后执行
- 编号说明：脑图该节点无 t 标注，按顺序新编 025
- 标题校正登记：脑图该节点标签与上一节点重复（均写「排队任务页面…字段值计算」），但其前置条件为「明细-运行任务页面」且 SQL 时间窗字段为 job_run_start_time/job_end_time（运行窗口），本用例标题按前置条件场景定为「运行任务页面」，脑图原文未改动
- 对拍 SQL 为脑图定稿口径：gitcode 申请卡数 = GREATEST(FLOOR(npu_second/job_duration), 1)，数据源 `internal.openlibing.dwr_rd_efc_workflow_run_job_gitcode_fact`
