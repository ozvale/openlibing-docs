# 用例清单 — issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现

> 团队：IPD管理控制与测试仿真 | 月度：202610 | 版本：20261015 | issue 编号：210 | issue 标题：【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现 | 用例总数：19（自动化 19 / 手工 0） | 更新日期：2026-10-15 | 由 testcase_pro 维护

> 月度版本树（进行中）：用例先落本 issue 目录（四类类型子目录与特性树同构），月底 consolidate 归集到 01~04 特性树；过程文档（测试策略/测试设计/测试串讲/测试反串讲/版本历史/测试报告）见本目录 测试过程数据/。

## 用例统计

| 用例等级 | 自动化 | 手工 | 合计   |
| -------- | ------ | ---- | ------ |
| P0       | 5      | 0    | 5      |
| P1       | 12     | 0    | 12     |
| P2       | 2      | 0    | 2      |
| **合计** | 19     | 0    | **19** |

## 用例清单

### 01_系统测试（11 条）

| 用例编号        | 用例标题                                        | 用例等级 | 执行方式 | 自动化方式 | 用例文本位置                                                                                                                                                                                                                                                                                                                                               | 用例脚本位置                                                                                                                                                                                                                                                        |
| --------------- | ----------------------------------------------- | -------- | -------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TC-ISSUE210-019 | 工程效率运营看板下线NPU利用率                   | P0       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-019_工程效率运营看板下线NPU利用率.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-019_工程效率运营看板下线NPU利用率.md)                                     | [src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_019.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_019.py) |
| TC-ISSUE210-020 | 工程效率运营看板新增NPU使用率字段               | P0       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-020_工程效率运营看板新增NPU使用率字段.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-020_工程效率运营看板新增NPU使用率字段.md)                             | [src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_020.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_020.py) |
| TC-ISSUE210-021 | 工程效率运营看板新增独占池NPU使用率字段         | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-021_工程效率运营看板新增独占池NPU使用率字段.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-021_工程效率运营看板新增独占池NPU使用率字段.md)                 | [src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_021.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_021.py) |
| TC-ISSUE210-022 | 工程效率运营看板新增共享池NPU使用率字段         | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-022_工程效率运营看板新增共享池NPU使用率字段.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-022_工程效率运营看板新增共享池NPU使用率字段.md)                 | [src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_022.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_022.py) |
| TC-ISSUE210-023 | 工程效率运营看板NPU使用率指标说明               | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-023_工程效率运营看板NPU使用率指标说明.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-023_工程效率运营看板NPU使用率指标说明.md)                             | [src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_023.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_023.py) |
| TC-ISSUE210-024 | 工程效率运营看板独占池NPU使用率指标说明（待定） | P2       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-024_工程效率运营看板独占池NPU使用率指标说明（待定）.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-024_工程效率运营看板独占池NPU使用率指标说明（待定）.md) | [src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_024.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_024.py) |
| TC-ISSUE210-025 | 工程效率运营看板共享池NPU使用率指标说明（待定） | P2       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-025_工程效率运营看板共享池NPU使用率指标说明（待定）.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-025_工程效率运营看板共享池NPU使用率指标说明（待定）.md) | [src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_025.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_025.py) |
| TC-ISSUE210-026 | 工程效率运营看板NPU使用率指标亮灯               | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-026_工程效率运营看板NPU使用率指标亮灯.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-026_工程效率运营看板NPU使用率指标亮灯.md)                             | [src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_026.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_026.py) |
| TC-ISSUE210-032 | 汇总资源池卡片信息准确                          | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-032_汇总资源池卡片信息准确.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-032_汇总资源池卡片信息准确.md)                                                   | [src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_032.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_032.py) |
| TC-ISSUE210-037 | 独占资源池卡片信息准确                          | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-037_独占资源池卡片信息准确.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-037_独占资源池卡片信息准确.md)                                                   | [src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_037.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_037.py) |
| TC-ISSUE210-039 | 共享资源池卡片信息准确                          | P1       | 自动化   | auto_ui    | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-039_共享资源池卡片信息准确.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-039_共享资源池卡片信息准确.md)                                                   | [src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_039.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_039.py) |

### 02_API测试（8 条）

| 用例编号        | 用例标题                                | 用例等级 | 执行方式 | 自动化方式 | 用例文本位置                                                                                                                                                                                                                                                                                                                             | 用例脚本位置                                                                                                                                                                                                                                                          |
| --------------- | --------------------------------------- | -------- | -------- | ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TC-ISSUE210-029 | 工程效率运营看板NPU使用率数据计算       | P0       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-029_工程效率运营看板NPU使用率数据计算.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-029_工程效率运营看板NPU使用率数据计算.md)             | [src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_029.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_029.py) |
| TC-ISSUE210-030 | 工程效率运营看板独占池NPU使用率数据计算 | P1       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-030_工程效率运营看板独占池NPU使用率数据计算.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-030_工程效率运营看板独占池NPU使用率数据计算.md) | [src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_030.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_030.py) |
| TC-ISSUE210-031 | 工程效率运营看板共享池NPU使用率数据计算 | P1       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-031_工程效率运营看板共享池NPU使用率数据计算.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-031_工程效率运营看板共享池NPU使用率数据计算.md) | [src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_031.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_031.py) |
| TC-ISSUE210-034 | NPU使用（占用）率计算                   | P0       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-034_NPU使用（占用）率计算.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-034_NPU使用（占用）率计算.md)                                     | [src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_034.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_034.py) |
| TC-ISSUE210-035 | NPU使用（占用）卡时计算                 | P1       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-035_NPU使用（占用）卡时计算.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-035_NPU使用（占用）卡时计算.md)                                 | [src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_035.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_035.py) |
| TC-ISSUE210-036 | 总卡时计算                              | P0       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-036_总卡时计算.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-036_总卡时计算.md)                                                           | [src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_036.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_036.py) |
| TC-ISSUE210-038 | 独占资源池数量统计                      | P1       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-038_独占资源池数量统计.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-038_独占资源池数量统计.md)                                           | [src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_038.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_038.py) |
| TC-ISSUE210-040 | 共享资源池数量统计                      | P1       | 自动化   | auto_api   | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-040_共享资源池数量统计.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-040_共享资源池数量统计.md)                                           | [src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_040.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_040.py) |

### 03_DFX测试（0 条）

（无）

### 04_安全测试（0 条）

（无）

## 用例详情

### 01_系统测试

#### TC-ISSUE210-019 工程效率运营看板下线NPU利用率

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板 > 工程效率运营看板下线NPU利用率

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-019_工程效率运营看板下线NPU利用率.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-019_工程效率运营看板下线NPU利用率.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_019.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_019.py)

**前置条件**：进入工程效率运营看板页面

**测试步骤**

1.查看NPU利用率字段
2.查看列设置NPU利用率字段

**预期结果**

1.NPU利用率字段不可见
2.NPU利用率字段不可见

#### TC-ISSUE210-020 工程效率运营看板新增NPU使用率字段

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板 > 工程效率运营看板新增NPU使用率字段

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-020_工程效率运营看板新增NPU使用率字段.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-020_工程效率运营看板新增NPU使用率字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_020.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_020.py)

**前置条件**：进入工程效率运营看板页面

**测试步骤**

1.查看NPU使用率字段
2.查看列设置NPU使用率字段
3.列设置去勾选NPU使用率字段，查看NPU使用率字段
4.列设置恢复默认，查看NPU使用率字段

**预期结果**

1.NPU使用率字段可见
2.NPU使用率字段可见
3.NPU使用率字段不可见
4.NPU使用率字段可见

#### TC-ISSUE210-021 工程效率运营看板新增独占池NPU使用率字段

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板 > 工程效率运营看板新增独占池NPU使用率字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-021_工程效率运营看板新增独占池NPU使用率字段.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-021_工程效率运营看板新增独占池NPU使用率字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_021.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_021.py)

**前置条件**：进入工程效率运营看板页面

**测试步骤**

1.查看共享池NPU使用率字段
2.查看列设置共享池NPU使用率字段
3.列设置勾选共享池NPU使用率字段，查看共享池NPU使用率字段
4.列设置恢复默认，查看共享池NPU使用率字段

**预期结果**

1.NPU使用率字段不可见
2.NPU使用率字段可见
3.NPU使用率字段可见
4.NPU使用率字段不可见

#### TC-ISSUE210-022 工程效率运营看板新增共享池NPU使用率字段

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板 > 工程效率运营看板新增共享池NPU使用率字段

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-022_工程效率运营看板新增共享池NPU使用率字段.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-022_工程效率运营看板新增共享池NPU使用率字段.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_022.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_022.py)

**前置条件**：进入工程效率运营看板页面

**测试步骤**

1.查看共享池NPU使用率字段
2.查看列设置共享池NPU使用率字段
3.列设置勾选共享池NPU使用率字段，查看共享池NPU使用率字段
4.列设置恢复默认，查看共享池NPU使用率字段

**预期结果**

1.NPU使用率字段不可见
2.NPU使用率字段可见
3.NPU使用率字段可见
4.NPU使用率字段不可见

#### TC-ISSUE210-023 工程效率运营看板NPU使用率指标说明

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板 > 工程效率运营看板NPU使用率指标说明

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-023_工程效率运营看板NPU使用率指标说明.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-023_工程效率运营看板NPU使用率指标说明.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_023.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_023.py)

**前置条件**：进入工程效率运营看板页面

**测试步骤**：1.查看NPU使用率指标说明

**预期结果**

使用率指标定义：NPU使用率表示统计周期内，资源池使用卡时，占资源池总卡时的比值。
使用率计算公式：NPU使用率 = Σ(NPU资源池使用卡时) / 资源池总卡时*100%
使用率达标判定：>= 30% 绿灯；< 30% & >= 15% 黄灯；< 15% 红灯

#### TC-ISSUE210-024 工程效率运营看板独占池NPU使用率指标说明（待定）

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板 > 工程效率运营看板独占池NPU使用率指标说明（待定）

**用例等级**：P2<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-024_工程效率运营看板独占池NPU使用率指标说明（待定）.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-024_工程效率运营看板独占池NPU使用率指标说明（待定）.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_024.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_024.py)

**前置条件**：进入工程效率运营看板页面

**测试步骤**：1.查看独占池NPU使用率指标说明

**预期结果**

独立池使用率指标定义：独立池NPU使用率表示统计周期内，独立池使用卡时，占独立池总卡时的比值。
独立池使用率计算公式：独立池NPU使用率 = Σ(独立池NPU使用卡时) / 独立池总卡时*100%
独立池使用率达标判定：>= 30% 绿灯；< 30% & >= 15% 黄灯；< 15% 红灯

#### TC-ISSUE210-025 工程效率运营看板共享池NPU使用率指标说明（待定）

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板 > 工程效率运营看板共享池NPU使用率指标说明（待定）

**用例等级**：P2<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-025_工程效率运营看板共享池NPU使用率指标说明（待定）.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-025_工程效率运营看板共享池NPU使用率指标说明（待定）.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_025.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_025.py)

**前置条件**：进入工程效率运营看板页面

**测试步骤**：1.查看共享池NPU使用率指标说明

**预期结果**

共享池使用率指标定义：共享池NPU使用率表示统计周期内，共享池使用卡时，占共享池总卡时的比值。
共享池使用率计算公式：共享池NPU使用率 = Σ(共享池NPU使用卡时) / 共享池总卡时*100%
共享池使用率达标判定：>= 30% 绿灯；< 30% & >= 10% 黄灯；< 10% 红灯

#### TC-ISSUE210-026 工程效率运营看板NPU使用率指标亮灯

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板 > 工程效率运营看板NPU使用率指标亮灯

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-026_工程效率运营看板NPU使用率指标亮灯.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-026_工程效率运营看板NPU使用率指标亮灯.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_026.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_026.py)

**前置条件**：进入工程效率运营看板页面

**测试步骤**：1.查看NPU使用率指标亮灯

**预期结果**：>= 30% 绿灯；< 30% & >= 15% 黄灯；< 15% 红灯

#### TC-ISSUE210-032 汇总资源池卡片信息准确

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板下钻资源环境-NPU资源 > 汇总资源池 > 汇总资源池卡片信息准确

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-032_汇总资源池卡片信息准确.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-032_汇总资源池卡片信息准确.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_032.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_032.py)

**前置条件**：进入工程效率运营看板下钻-资源环境-NPU资源页面

**测试步骤**：1.查看汇总资源池卡片

**预期结果**：汇总资源池卡片展示NPU使用（占用）率、NPU使用（占用）卡时、总卡时。

#### TC-ISSUE210-037 独占资源池卡片信息准确

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板下钻资源环境-NPU资源 > 独占资源池 > 独占资源池卡片信息准确

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-037_独占资源池卡片信息准确.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-037_独占资源池卡片信息准确.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_037.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_037.py)

**前置条件**：进入工程效率运营看板下钻-资源环境-NPU资源页面

**测试步骤**：1.查看独占资源池卡片

**预期结果**：汇总资源池卡片展示NPU使用（占用）率、NPU使用（占用）卡时、总卡时。并用列表展示各资源池名称、NPU使用（占用）率、NPU使用（占用）卡时、总卡时

#### TC-ISSUE210-039 共享资源池卡片信息准确

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板下钻资源环境-NPU资源 > 共享资源池 > 共享资源池卡片信息准确

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-039_共享资源池卡片信息准确.md](../01_系统测试/运营运维/工程能力运营看板/TC-ISSUE210-039_共享资源池卡片信息准确.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_039.py](../../../../../../../src/automation/ipd-management/ui/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_039.py)

**前置条件**：进入工程效率运营看板下钻-资源环境-NPU资源页面

**测试步骤**：1.查看共享资源池卡片

**预期结果**：汇总资源池卡片展示NPU使用（占用）率、NPU使用（占用）卡时、总卡时。并用列表展示各资源池名称、NPU使用（占用）率、NPU使用（占用）卡时、总卡时

### 02_API测试

#### TC-ISSUE210-029 工程效率运营看板NPU使用率数据计算

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板 > 工程效率运营看板NPU使用率数据计算

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-029_工程效率运营看板NPU使用率数据计算.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-029_工程效率运营看板NPU使用率数据计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_029.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_029.py)

**前置条件**：进入工程效率运营看板页面

**测试步骤**：1.计算NPU利用率

**预期结果**：1.工程效率运营看板看板下钻资源环境-NPU资源-汇总资源池的NPU使用率数据一致

#### TC-ISSUE210-030 工程效率运营看板独占池NPU使用率数据计算

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板 > 工程效率运营看板独占池NPU使用率数据计算

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-030_工程效率运营看板独占池NPU使用率数据计算.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-030_工程效率运营看板独占池NPU使用率数据计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_030.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_030.py)

**前置条件**：进入工程效率运营看板页面

**测试步骤**：1.计算独占池NPU利用率

**预期结果**：1.工程效率运营看板看板下钻资源环境-NPU资源-独占资源池的NPU使用率数据一致

#### TC-ISSUE210-031 工程效率运营看板共享池NPU使用率数据计算

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板 > 工程效率运营看板共享池NPU使用率数据计算

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-031_工程效率运营看板共享池NPU使用率数据计算.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-031_工程效率运营看板共享池NPU使用率数据计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_031.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_031.py)

**前置条件**：进入工程效率运营看板页面

**测试步骤**：1.计算共享池NPU利用率

**预期结果**：1.工程效率运营看板看板下钻资源环境-NPU资源-共享资源池的NPU使用率数据一致

#### TC-ISSUE210-034 NPU使用（占用）率计算

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板下钻资源环境-NPU资源 > 汇总资源池 > NPU使用（占用）率计算

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-034_NPU使用（占用）率计算.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-034_NPU使用（占用）率计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_034.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_034.py)

**前置条件**：进入工程效率运营看板下钻-资源环境-NPU资源页面

**测试步骤**：NPU使用（占用）率计算

**预期结果**：NPU使用率 = Σ(NPU资源池使用卡时) / 资源池总卡时*100%

#### TC-ISSUE210-035 NPU使用（占用）卡时计算

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板下钻资源环境-NPU资源 > 汇总资源池 > NPU使用（占用）卡时计算

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-035_NPU使用（占用）卡时计算.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-035_NPU使用（占用）卡时计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_035.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_035.py)

**前置条件**：进入工程效率运营看板下钻-资源环境-NPU资源页面

**测试步骤**：NPU使用（占用）卡时计算计算

**预期结果**：与dm_rd_efc_server_assign_resource_hour.assign_npu_hours字段汇聚拿到分配卡时一致

#### TC-ISSUE210-036 总卡时计算

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板下钻资源环境-NPU资源 > 汇总资源池 > 总卡时计算

**用例等级**：P0<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-036_总卡时计算.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-036_总卡时计算.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_036.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_036.py)

**前置条件**：进入工程效率运营看板下钻-资源环境-NPU资源页面

**测试步骤**：总卡时率计算

**预期结果**

通过sdi_rd_efc_server_machine_hidelab.resource_pool_name字段查看资源ip的归属
可以通过sdi_rd_efc_all_npu.actual_npu_num字段获取资源ip的总卡时

#### TC-ISSUE210-038 独占资源池数量统计

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板下钻资源环境-NPU资源 > 独占资源池 > 独占资源池数量统计

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-038_独占资源池数量统计.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-038_独占资源池数量统计.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_038.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_038.py)

**前置条件**：进入工程效率运营看板下钻-资源环境-NPU资源页面

**测试步骤**：1.统计独占资源池

**预期结果**：资源运营对应项目的资源池在dwi_rd_efc_project_resource_pool_relationdescription字段中只关联了单个项目的资源池

#### TC-ISSUE210-040 共享资源池数量统计

**测试功能场景**：测试设计脑图 > 工程效率运营看板看板下钻资源环境-NPU资源 > 共享资源池 > 共享资源池数量统计

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-13<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/210<br>
**来源模块**：openlibing-ops/engineering_capability_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261015/issue_210_【1015】【蓝区】【运营看板】工程能力运营看板-使用率指标实现/02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-040_共享资源池数量统计.md](../02_API测试/运营运维/工程能力运营看板/TC-ISSUE210-040_共享资源池数量统计.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_040.py](../../../../../../../src/automation/ipd-management/api/operations_maintenance/engineering_capability_dashboard/beta/test_tc_issue210_040.py)

**前置条件**：进入工程效率运营看板下钻-资源环境-NPU资源页面

**测试步骤**：1.统计共享资源池

**预期结果**：资源运营对应项目的资源池在dwi_rd_efc_project_resource_pool_relationdescription字段中只关联了多个项目的资源池
