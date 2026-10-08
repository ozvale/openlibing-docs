# 用例清单 — issue_144_构建任务未执行，看板显示执行成功

> 团队：IPD管理控制与测试仿真 | 月度：202610 | 版本：20261007 | issue 编号：144 | issue 标题：构建任务未执行，看板显示执行成功 | 用例总数：4（自动化 3 / 手工 1） | 更新日期：2026-10-08 | 由 testcase_pro 维护

> 月度版本树（进行中）：用例先落本 issue 目录（四类类型子目录与特性树同构），月底 consolidate 归集到 01~04 特性树；过程文档（测试策略/测试设计/测试串讲/测试反串讲/版本历史/测试报告）见本目录 测试过程数据/。

## 用例统计

| 用例等级 | 自动化 | 手工 | 合计 |
|------|------|------|------|
| P1 | 2 | 1 | 3 |
| P2 | 1 | 0 | 1 |
| **合计** | 3 | 1 | **4** |

## 用例清单

### 01_系统测试（2 条）

| 用例编号 | 用例标题 | 用例等级 | 执行方式 | 自动化方式 | 用例文本位置 | 用例脚本位置 |
|------|------|------|------|------|------|------|
| TC-ISSUE144-002 | PR门禁看板流水线状态筛选结果与真实状态一致性验证 | P1 | 自动化 | auto_ui | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_144_构建任务未执行，看板显示执行成功/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE144-002_PR门禁看板流水线状态筛选结果与真实状态一致性验证.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE144-002_PR门禁看板流水线状态筛选结果与真实状态一致性验证.md) | [src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue144_002.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue144_002.py) |
| TC-ISSUE144-004 | 现场抽样仓构建任务记录与看板状态展示人工对照 | P1 | 手工 | — | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_144_构建任务未执行，看板显示执行成功/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE144-004_现场抽样仓构建任务记录与看板状态展示人工对照.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE144-004_现场抽样仓构建任务记录与看板状态展示人工对照.md) | — |

### 02_API测试（2 条）

| 用例编号 | 用例标题 | 用例等级 | 执行方式 | 自动化方式 | 用例文本位置 | 用例脚本位置 |
|------|------|------|------|------|------|------|
| TC-ISSUE144-001 | pipeline接口无构建run记录PR不得默认返回成功状态 | P1 | 自动化 | auto_api | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_144_构建任务未执行，看板显示执行成功/02_API测试/数字化运营/PR门禁看板/TC-ISSUE144-001_pipeline接口无构建run记录PR不得默认返回成功状态.md](../02_API测试/数字化运营/PR门禁看板/TC-ISSUE144-001_pipeline接口无构建run记录PR不得默认返回成功状态.md) | [src/automation/ipd-management/api/digital_operations/pr_gate_dashboard/beta/test_tc_issue144_001.py](../../../../../../../src/automation/ipd-management/api/digital_operations/pr_gate_dashboard/beta/test_tc_issue144_001.py) |
| TC-ISSUE144-003 | 数仓统一表run状态与看板接口数据一致性核验 | P2 | 自动化 | auto_api | [assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_144_构建任务未执行，看板显示执行成功/02_API测试/数字化运营/PR门禁看板/TC-ISSUE144-003_数仓统一表run状态与看板接口数据一致性核验.md](../02_API测试/数字化运营/PR门禁看板/TC-ISSUE144-003_数仓统一表run状态与看板接口数据一致性核验.md) | [src/automation/ipd-management/api/digital_operations/pr_gate_dashboard/beta/test_tc_issue144_003.py](../../../../../../../src/automation/ipd-management/api/digital_operations/pr_gate_dashboard/beta/test_tc_issue144_003.py) |

### 03_DFX测试（0 条）

（无）

### 04_安全测试（0 条）

（无）

## 用例详情

### 01_系统测试

#### TC-ISSUE144-002 PR门禁看板流水线状态筛选结果与真实状态一致性验证

**测试功能场景**：FP2：PR门禁看板「流水线状态」筛选器（成功/失败）筛选后主表数据与真实构建任务状态一致——构建任务未执行的仓/PR 不得出现在「成功」筛选结果中（Issue #144 修复验收 UI 面）

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_ui<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-08<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/144<br>
**来源模块**：openlibing-ops/pr_gate_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_144_构建任务未执行，看板显示执行成功/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE144-002_PR门禁看板流水线状态筛选结果与真实状态一致性验证.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE144-002_PR门禁看板流水线状态筛选结果与真实状态一致性验证.md)<br>
**用例脚本位置**：[src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue144_002.py](../../../../../../../src/automation/ipd-management/ui/digital_operations/pr_gate_dashboard/beta/test_tc_issue144_002.py)

**前置条件**

- beta 已登录；BeiMing（projectId=300066）PR门禁看板可加载，主表默认筛选下有数据
- 页面探索基线（2026-10-08）：筛选区含「流水线状态」筛选器，取值：成功 / 失败
- 页面对象基线：`pr_gate_dashboard_page.py`（collect_main_table_headers / collect_row_cells）

**测试步骤**

1. 打开 PR门禁看板（projectId=300066），采集主表基线（无筛选状态下的全部行与仓清单）
2. 「流水线状态」筛选器选择「成功」，等待主表刷新，采集筛选后全部行
3. 「流水线状态」筛选器选择「失败」，等待主表刷新，采集筛选后全部行
4. 断言筛选=成功的行集合：每行对应仓必须有真实成功状态的构建 run 记录（与 pipeline/info 接口或桥表数据交叉核对），无构建执行记录的仓不得出现在成功结果中
5. 断言筛选=失败的行集合：每行对应仓必须有真实失败状态的构建 run 记录
6. 断言成功与失败结果集无交集、且均为基线行集合的子集（无筛选缓存陈旧数据混入）
7. 边界断言：仓库整体无流水线数据（时长列 `--`）的仓不得计入成功筛选结果
8. 保留三态（无筛选/成功/失败）主表采集证据

**预期结果**

- 「流水线状态」筛选=成功/失败的结果与真实构建任务状态一致
- 构建任务未执行的仓不出现在成功筛选结果中（缺陷本体 UI 直证）
- 成功/失败结果集互斥且为基线子集，无陈旧缓存误报

**备注**

- 设计方法：场景法（筛选旅程）+ 判定表（条件：有run×状态值 / 无run → 动作：入选对应筛选 / 不得入选成功）+ 错误猜测（筛选缓存陈旧数据）
- 主表无任务状态列（页面探索结论），筛选正确性通过「筛选结果 ↔ 接口/数仓真实状态」交叉核对承载

#### TC-ISSUE144-004 现场抽样仓构建任务记录与看板状态展示人工对照

**测试功能场景**：FP4：现场抽样——测试人员在 gitcode 侧确认「构建任务未执行」的真实样本仓/PR，对照 PR门禁看板状态展示，验证修复后不再出现「未执行却显示成功」（覆盖自动化无法主动构造的真实缺陷场景）

**用例等级**：P1<br>
**执行方式**：手工<br>
**用例类型**：系统测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-08<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/144<br>
**来源模块**：openlibing-ops/pr_gate_dashboard

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_144_构建任务未执行，看板显示执行成功/01_系统测试/数字化运营/PR门禁看板/TC-ISSUE144-004_现场抽样仓构建任务记录与看板状态展示人工对照.md](../01_系统测试/数字化运营/PR门禁看板/TC-ISSUE144-004_现场抽样仓构建任务记录与看板状态展示人工对照.md)<br>
**用例脚本位置**：—

**前置条件**

- 测试人员可访问 beta PR门禁看板（projectId=300066）与 gitcode 仓库构建任务记录页
- 测试人员已定位/确认至少一个「构建任务未执行」的样本仓或 PR（原始缺陷 Issue 未记录具体 PR，样本由测试人员现场确认）

**测试步骤**

1. 在 gitcode 侧查看目标仓库近期 PR 与构建任务（流水线）执行记录，确认某个仓/PR 无构建任务执行记录（或仅有非成功终态）
2. 打开 beta PR门禁看板（projectId=300066），使用「流水线状态」筛选与主表定位该仓/PR 的状态展示
3. 对照核验：无构建任务执行记录的仓/PR，看板不得展示或统计为「执行成功」
4. 同法抽 1~2 个有成功构建记录的仓作正向对照（应显示成功）
5. 登记执行记录：样本仓、PR 号、gitcode 实际状态、看板展示状态、对照结论

**预期结果**

- 构建任务未执行的样本：看板不出现「执行成功」展示（空态或如实状态）
- 有成功构建记录的正向对照样本：看板正常显示成功
- 抽样对照结论与自动化用例结论一致

**备注**

- 设计方法：场景法（S3 旅程：现场四方交叉验证的人工环节）
- 执行人：测试人员（AI 不得代执行），执行结果登记于测试报告.md 执行明细与执行记录跟踪表.xlsx
- 原始缺陷场景（具体哪个 PR/仓未执行）Issue 未记录（1.7 风险表），本用例由测试人员现场定位样本，是修复验证置信度的最终兜底

### 02_API测试

#### TC-ISSUE144-001 pipeline接口无构建run记录PR不得默认返回成功状态

**测试功能场景**：FP1：POST /gateway/openlibing-ops/pipeline/info（type=pipeline）返回的 run 状态与真实构建任务执行状态一致——有 run 如实映射成功/失败，无 run 不得默认/回退为「成功」（Issue #144 缺陷机理直证）

**用例等级**：P1<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-08<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/144<br>
**来源模块**：openlibing-ops/pipeline_info

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_144_构建任务未执行，看板显示执行成功/02_API测试/数字化运营/PR门禁看板/TC-ISSUE144-001_pipeline接口无构建run记录PR不得默认返回成功状态.md](../02_API测试/数字化运营/PR门禁看板/TC-ISSUE144-001_pipeline接口无构建run记录PR不得默认返回成功状态.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/digital_operations/pr_gate_dashboard/beta/test_tc_issue144_001.py](../../../../../../../src/automation/ipd-management/api/digital_operations/pr_gate_dashboard/beta/test_tc_issue144_001.py)

**前置条件**

- beta 已登录（api_client 会话）；doris 桥表 `internal.openlibing.sdi_rd_efc_pipeline_run_pr_relation_codearts`（git_type='gitcode'）可查询项目 300066 近30天 PR 关联 run 记录
- 桥表中存在有构建 run 的 PR 样本（探索基线：memcache 等仓有 run 数据）

**测试步骤**

1. 查询桥表获得项目 300066 近30天 PR 集合，按「有构建 run」「无构建 run」分为两组样本（无 run 组若无现成样本则记录证据并按备注处理）
2. 对有 run 的 PR 样本：POST /gateway/openlibing-ops/pipeline/info，请求体 {type: pipeline, url: <仓库URL>, prNumber: <PR号>}，断言 HTTP 200 且业务 code=200
3. 断言返回 run 集合的状态字段与桥表记录的真实状态一致（逐 run 对照）
4. 对无 run 的 PR 样本：断言接口返回空 run 集合或显式「未执行」语义，绝不出现状态=成功的 run 记录
5. 状态枚举完备性断言：全部返回 run 的状态值属于合法状态集合（成功/失败/运行中/取消/未执行等），不存在无 run 却映射为成功的非法状态迁移
6. 保留两组样本的接口返回与桥表查询对照证据

**预期结果**

- 有构建 run 的 PR：接口返回状态与真实执行状态逐条一致
- 无构建 run 的 PR：接口不得默认/回退返回成功状态（空集合或未执行语义）
- 状态枚举完备，不存在「未执行→成功」的非法状态映射（缺陷本体场景）

**备注**

- 设计方法：等价类（状态有效类：成功/失败/未执行；无效回退类：无数据→默认成功）+ 状态迁移（未执行→运行中→成功/失败，非法迁移即缺陷）+ 判定表（有run×状态值→如实展示；无run→空/未执行，禁止成功）
- 风险缓解（1.7）：beta 若无现成「无构建 run」样本，记录证据后以有 run 样本的状态一致性 + 枚举完备性断言承载，手工用例 TC-ISSUE144-004 补充现场对照
- type 契约沿 TC-ISSUE135-001 备注：gitcode 仓库走 type=pipeline

#### TC-ISSUE144-003 数仓统一表run状态与看板接口数据一致性核验

**测试功能场景**：FP3：数仓统一表 gitcode 流水线 run 状态记录与 pipeline/info 接口返回数据三方一致性核验——看板状态展示的正确性以数仓为真值源（Issue #144 修复验证数据面）

**用例等级**：P2<br>
**执行方式**：自动化<br>
**自动化方式**：auto_api<br>
**用例类型**：API测试<br>
**用例状态**：active<br>
**用例作者**：AI 辅助测试<br>
**创建时间**：2026-10-08<br>
**关联需求**：https://gitcode.com/openlibing/openlibing-ops/issues/144<br>
**来源模块**：openlibing-ops/pipeline_info

**用例文本位置**：[assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261007/issue_144_构建任务未执行，看板显示执行成功/02_API测试/数字化运营/PR门禁看板/TC-ISSUE144-003_数仓统一表run状态与看板接口数据一致性核验.md](../02_API测试/数字化运营/PR门禁看板/TC-ISSUE144-003_数仓统一表run状态与看板接口数据一致性核验.md)<br>
**用例脚本位置**：[src/automation/ipd-management/api/digital_operations/pr_gate_dashboard/beta/test_tc_issue144_003.py](../../../../../../../src/automation/ipd-management/api/digital_operations/pr_gate_dashboard/beta/test_tc_issue144_003.py)

**前置条件**

- beta 已登录（api_client 会话）；doris 统一表（gitcode 流水线 run/job，TC-ISSUE135-007 同源）与桥表连接可用
- 数仓存在项目 300066 近30天 gitcode 流水线 run 记录

**测试步骤**

1. doris 查询统一表项目 300066 近30天 gitcode run 状态分布（按状态分组计数）
2. 抽取统一表中若干 PR（含不同状态值），逐 PR 调用 pipeline/info（type=pipeline）获取接口侧 run 集合
3. 断言接口返回的 run 数量、pipeline_run_id 集合、状态字段与统一表记录一致（容忍 T+1 同步滞后窗口，参照 TC-ISSUE135-016 时效基线）
4. 断言统一表中无构建 run 的 PR 在接口返回中不产生成功态记录（防默认成功回退）
5. 断言统一表状态字段值域合法（成功/失败/运行中/取消等），无脏值映射为成功
6. 保留 doris 查询结果与接口返回对照证据

**预期结果**

- 接口返回的 run 集合与数仓统一表真实记录一致（数量/ID/状态三方对齐）
- 无 run 的 PR 不在接口中产生成功态记录，状态值域合法
- 一致性核验在容忍窗口内通过，无瞬时不一致误报

**备注**

- 设计方法：一致性核验（交叉比对：数仓真值源 ↔ 接口呈现）+ 场景法（S2 旅程）
- 风险缓解（1.7）：doris 连接不可用时标注 block 并说明；T+1 时效容忍度注明（桥表/统一表既有滞后窗口）
- 数据链路完备性前置由基线回归 TC-ISSUE135-007（统一表 run/job 完备性）、TC-ISSUE135-008（桥表 PR↔run 关联）承载
