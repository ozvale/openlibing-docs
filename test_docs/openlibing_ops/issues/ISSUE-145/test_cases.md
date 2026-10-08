# 用例清单 — issue_145_门禁E2E执行时长保留2位小数

> 团队：IPD管理控制与测试仿真 | 月度：202610 | 版本：20261007 | issue 编号：145 | issue 标题：门禁E2E执行时长保留2位小数 | 用例总数：3（自动化 3 / 手工 0） | 更新日期：2026-10-08 | 由 testcase_pro 维护

> 月度版本树（进行中）：用例先落本 issue 目录（四类类型子目录与特性树同构），月底 consolidate 归集到 01~04 特性树；过程文档（测试策略/测试设计/测试串讲/测试反串讲/版本历史/测试报告）见本目录 测试过程数据/。

## 用例统计

| 用例等级 | 自动化 | 手工 | 合计 |
|------|------|------|------|
| P1 | 1 | 0 | 1 |
| P2 | 2 | 0 | 2 |
| **合计** | 3 | 0 | **3** |

## 用例清单

### 01_系统测试（3 条）

| 用例编号 | 用例标题 | 用例等级 | 执行方式 | 自动化方式 | 用例文本位置 | 用例脚本位置 |
|------|------|------|------|------|------|------|
| TC-ISSUE145-001 | PR门禁看板门禁E2E执行时长列保留2位小数全行断言 | P1 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_145_门禁E2E执行时长保留2位小数/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE145-001_PR门禁看板门禁E2E执行时长列保留2位小数全行断言.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE145-001_PR门禁看板门禁E2E执行时长列保留2位小数全行断言.md) | [src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue145_001.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue145_001.py) |
| TC-ISSUE145-002 | 门禁E2E执行时长含重试与不含重试列同行小数位一致性对比 | P2 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_145_门禁E2E执行时长保留2位小数/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE145-002_门禁E2E执行时长含重试与不含重试列同行小数位一致性对比.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE145-002_门禁E2E执行时长含重试与不含重试列同行小数位一致性对比.md) | [src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue145_002.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue145_002.py) |
| TC-ISSUE145-003 | PR门禁看板导出xlsx时长列格式与页面一致性验证 | P2 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_145_门禁E2E执行时长保留2位小数/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE145-003_PR门禁看板导出xlsx时长列格式与页面一致性验证.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE145-003_PR门禁看板导出xlsx时长列格式与页面一致性验证.md) | [src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue145_003.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue145_003.py) |

### 02_API测试（0 条）

（无）

### 03_DFX测试（0 条）

（无）

### 04_安全测试（0 条）

（无）

## 用例详情

### 01_系统测试

#### TC-ISSUE145-001 PR门禁看板门禁E2E执行时长列保留2位小数全行断言

**测试功能场景**：FP1：PR门禁看板主表「门禁E2E执行时长[平均](min)」「门禁E2E执行时长[最长](min)」列所有数值保留2位小数（Issue #145 修复验收核心：整数显示 x.00，无数据显示 --）

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-08<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/145<br>
**来源模块**：openlibing-ops/pr_gate_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_145_门禁E2E执行时长保留2位小数/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE145-001_PR门禁看板门禁E2E执行时长列保留2位小数全行断言.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE145-001_PR门禁看板门禁E2E执行时长列保留2位小数全行断言.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue145_001.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue145_001.py)

**前置条件**

- beta 已登录；BeiMing（projectId=300066）PR门禁看板主表在默认筛选（PR创建时间近30天）下有数据（页面探索基线：5 仓 5 行）
- 页面对象基线：`src/pages/ipd_management/ui/operations_maintenance/pr_gate_dashboard/pr_gate_dashboard_page.py`（collect_main_table_headers / collect_row_cells 采集方法）

**测试步骤**

1. 会话守卫校验后 URL 直连 `/apps/prAccessDashboard?projectId=300066`，等待 iframe `/ops/dashboard/pr-access/300066` 渲染
2. 采集主表表头，定位「门禁E2E执行时长[平均](min)」「门禁E2E执行时长[最长](min)」两列索引
3. 采集主表全部行的单元格文本，提取两列的每格数值
4. 断言每格非空值（非 `--`）匹配严格正则 `^\d+\.\d{2}$`（恰好2位小数）
5. 断言任何一格不出现裸整数（如 `30`）、1 位小数（如 `2.3`）、3 位及以上小数（如 `3.074`）
6. 边界断言：若某格原始值恰为整数（如 30 min），展示必须为 `30.00` 而非裸整数
7. `--` 空值显式豁免，不计入违规；记录全量行采集证据（含每行仓与四列值）

**预期结果**

- 含重试「门禁E2E执行时长[平均]/[最长]」两列所有非空数值均为2位小数格式
- 整数时长展示为 x.00，3 位以上小数原始值四舍五入到2位展示
- 任何一行任一列出现 1 位小数/裸整数/3 位小数即判失败

**备注**

- 设计方法：场景法（主流程全行遍历）+ 边界值（整数边界 30→30.00、3位小数四舍五入）+ 错误猜测（历史缺陷区：格式化逻辑缺失时裸值直出）
- 断言只针对格式不针对具体数值，规避数仓 T+1 同步导致的数据变化（1.7 风险表）
- 探索基线（2026-10-08）：两列当前全为2位小数，现场表现为已修复形态，本用例将断言固化为回归基线

#### TC-ISSUE145-002 门禁E2E执行时长含重试与不含重试列同行小数位一致性对比

**测试功能场景**：FP2：「门禁E2E执行时长」列组（含重试）与「门禁E2E执行时长(不含重试)」列组同行对比，小数位一致（Issue #145 标题验收标准：与不含重试列保留小数位一致）

**用例等级**：P2<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-08<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/145<br>
**来源模块**：openlibing-ops/pr_gate_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_145_门禁E2E执行时长保留2位小数/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE145-002_门禁E2E执行时长含重试与不含重试列同行小数位一致性对比.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE145-002_门禁E2E执行时长含重试与不含重试列同行小数位一致性对比.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue145_002.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue145_002.py)

**前置条件**

- beta 已登录；BeiMing（projectId=300066）PR门禁看板主表默认筛选下有数据
- 页面探索基线：不含重试两列当前仅 memcache 仓有值（6.53 / 8.72），其余行为 `--`

**测试步骤**

1. 打开 PR门禁看板（projectId=300066），采集主表表头，定位四个时长叶子列：门禁E2E执行时长[平均](min)、[最长](min)、[平均](min)(不含重试)、[最长](min)(不含重试)
2. 采集全部行四列单元格文本
3. 对每个仓行执行同行对比：任一列有非空值（非 `--`）时，断言同行列组内全部非空值匹配 `^\d+\.\d{2}$`
4. 断言含重试与不含重试列组小数位一致（同为2位小数，不出现一列 1 位另一列 2 位的混合）
5. 空值行（四列均 `--`）豁免；若不含重试两列全量行均无数据，用例输出明确 skip 结论（附采集证据）而非误判 pass
6. 边界断言：数值 `0.00` 与空值 `--` 语义区分（0.00 须为2位小数合法格式，-- 为无数据）

**预期结果**

- 含重试与不含重试四个时长列同行对比小数位一致，全部非空值为2位小数
- 样本不足（不含重试列无数据）时给出明确 skip 结论与证据，不产生误报

**备注**

- 设计方法：等价类（有效类2位小数一致 / 无效类同行小数位不一致）+ 边界值（空值 -- 豁免、0.00 语义）
- 风险缓解（1.7）：不含重试列样本不足场景显式 skip，避免空样本误 pass

#### TC-ISSUE145-003 PR门禁看板导出xlsx时长列格式与页面一致性验证

**测试功能场景**：FP3：PR门禁看板工具栏「导出」产物 xlsx 中门禁E2E执行时长相关列（含重试/不含重试四列）数值格式与页面展示一致，同为2位小数（防止修复仅覆盖页面渲染未覆盖导出链路）

**用例等级**：P2<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-08<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/145<br>
**来源模块**：openlibing-ops/pr_gate_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_145_门禁E2E执行时长保留2位小数/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE145-003_PR门禁看板导出xlsx时长列格式与页面一致性验证.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE145-003_PR门禁看板导出xlsx时长列格式与页面一致性验证.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue145_003.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue145_003.py)

**前置条件**

- beta 已登录；BeiMing（projectId=300066）PR门禁看板主表默认筛选下有数据
- 执行环境下载目录可写（本地执行凭证）；openpyxl 可用

**测试步骤**

1. 打开 PR门禁看板（projectId=300066），采集主表四个时长列的页面展示值（作为对照基线）
2. 点击工具栏「导出」按钮，等待 xlsx 下载完成
3. openpyxl 读取导出文件，定位门禁E2E执行时长四列（表头匹配含重试/不含重试分组）
4. 断言导出文件中四列所有非空数值与页面展示值一致且匹配 `^\d+\.\d{2}$`（或 Excel 数值类型时四舍五入到2位的字符串化表示一致）
5. 断言导出文件与页面同行同列对照无格式漂移（页面 2 位小数、导出裸整数/1 位小数即失败）
6. 保留导出文件路径与页面采集值对照表作为证据

**预期结果**

- 导出 xlsx 中门禁E2E执行时长相关列数值格式与页面展示一致，同为2位小数
- 导出值与页面值逐格对照无漂移

**备注**

- 设计方法：场景法（导出旅程端到端）+ 错误猜测（历史缺陷区：仅修页面渲染漏修导出格式）
- 风险缓解（1.7）：CI 环境下载目录不可写时标注 block 并说明，本地执行兜底
