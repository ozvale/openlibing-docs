# 测试设计 - ISSUE-111

> **模板版本**: v1.0
> **对应规则**: ai-rules/01-requirement-driven-test-design.md
> **输入**: test_strategy.md + requirement_analysis.md + page_exploration.md（后两者因 2026-08-31 存储层异常丢失，设计输入已固化于本文件与 test_strategy.md）

---

## 1. 设计概述

本Issue的测试设计基于 Issue 111 需求正文（业务规则经测试人员确认以 beta 实际系统探索为业务输入）与页面探索报告，覆盖以下功能点：项目/组织双维度看板展示（F1/F2）、遗留问题数计算口径（F3）、汇总-明细数据一致性（F4）、时间范围四档切换（F5）、明细分页（F6）、全量导出（F7）、关联指标展示（F8）、趋势接口契约冒烟（F9）、接口安全三维度（F10/F11/F12）、组织维度菜单入口（F13）、UI 交互细节（F14）。

### 1.1 设计原则

- 手工用例与自动化用例分离
- 自动化用例需标注脚本位置
- 每个用例需记录用例类型
- 每个功能点需标注所采用的测试设计方法
- 优先自动化：17 个自动化用例 / 2 个手工用例

### 1.2 用例类型定义

| 类型代码 | 类型名称 | 说明 |
|----------|----------|------|
| manual | 手工执行 | 需要人工操作执行 |
| auto_ui | 自动化-UI | UI自动化测试脚本 |
| auto_api | 自动化-API | API接口自动化测试脚本 |
| auto_perf | 自动化-性能 | 性能测试脚本 |
| auto_sec | 自动化-安全 | 安全测试脚本 |

### 1.3 测试设计方法

本设计采用以下方法（详见 ai-rules/01-requirement-driven-test-design.md 第4节）：

- [x] 等价类划分（Equivalence Partitioning）— 时间范围四档输入域、计数数值域
- [x] 边界值分析（Boundary Value Analysis）— 日期边界（today-6 vs today-7）、分页边界（末页不足10条）
- [x] 决策表测试（Decision Table Testing）— 维度 × 接口参数组合
- [ ] 状态迁移测试（State Transition Testing）— 看板为无状态查询，无状态机
- [x] 场景法（Use Case / Scenario Testing）— 登录→导航→看板→切换→导出端到端流程
- [x] 错误推测法（Error Guessing）— 无凭证/低权限访问、非法参数

### 1.4 关键设计决策表（维度 × 接口参数）

依据探索报告 §4 接口契约：

| 条件/动作 | issue-legacy-statistics | issue-legacy-trend | common/detail | 备注 |
|-----------|--------------------------|---------------------|---------------|------|
| 项目维度 | `aspect="project"` + `projectId="3"` | `aspect="project"` + `projectId="3"` | `aspect="project"` + `projectId="3"` | 请求体含 `productId:""` |
| 组织维度 | `aspect="all"` + `projectId=""` | `aspect="organization"` + `projectId=""` | `aspect="organization"` + `projectId=""` | 请求体含 `productId:""` |
| detail 专有 | — | — | `category="issue-legacy-detail"` + `repoUrl=""` + `page/pageSize` | 分页参数仅 detail 有 |
| export 专有 | — | — | 同 detail 但**无** page/pageSize | 全量导出 |

> 设计含义：三个查询接口共用一套日期参数（startDate/endDate），维度参数取值不同。用例需分别断言两维度参数组合正确（statistics 的 `all` 与 trend/detail 的 `organization` 不一致，按实测契约断言）。

## 2. 功能点分析

> 每个功能点必须能在需求基线（Issue 正文 + 测试人员确认的实测契约）中找到依据，**禁止超出范围发散**。

| 功能点 | 设计依据 | 测试设计方法 | 测试类型 | 优先级 |
|--------|----------|--------------|----------|--------|
| F1 项目维度看板入口与页面展示 | Issue 3.2（测试管理菜单）+ 探索 §2/§3 | 场景法 | auto_ui | L0 |
| F2 组织维度看板页面展示 | Issue 3.2（测试运营菜单）+ 探索 §2/§3 | 场景法 | auto_ui | L0 |
| F3 遗留问题数计算口径（五级求和，权重均为1） | Issue 3.1 + 探索 §6 实测公式 | 等价类划分（计数数值域）+ 边界值（零值分量） | auto_api | L0 |
| F4 汇总与明细数据一致性 | Issue 3.1/3.3 + 探索 §4 契约 | 场景法（数据流对照） | auto_api | L0 |
| F5 明细时间范围四档切换 | Issue 3.4 + 探索 §5 参数映射 | 等价类划分（四档输入域）+ 边界值（日期边界与区间包含单调性） | auto_api + auto_ui | L0 |
| F6 明细列表分页 | Issue 3.3 明细展示 + 探索 §3（10条/页） | 边界值分析（page/pageSize/末页） | auto_api + auto_ui | L1 |
| F7 全量导出 | Issue 3.3 明细数据 + 探索 §4.4 | 场景法（导出流程） | auto_api + auto_ui | L1 |
| F8 关联指标展示（Bug总数/遗留DI/五级卡片） | Issue 3.3 + 探索 §7 术语映射 | 等价类划分（字段类型域） | auto_api + auto_ui | L1 |
| F9 趋势接口契约结构（页面加载依赖） | Issue 3.3（趋势另行设计，仅冒烟）+ 探索 §4.2 | 等价类划分（契约结构） | auto_api | L2 |
| F10 看板接口认证校验 | AGENTS.md 规则 04（auth_check） | 错误推测法 | auto_sec | L1 |
| F11 看板接口纵向越权校验 | AGENTS.md 规则 04（vertical_check） | 错误推测法 | auto_sec | L1 |
| F12 看板接口敏感信息防护 | AGENTS.md 规则 04（sensitive_data_check） | 错误推测法 | auto_sec | L2 |
| F13 组织维度"测试运营"菜单入口 | Issue 3.2（菜单入口）+ 探索 §8 发现#1 | 场景法 | manual | L1 |
| F14 UI 交互细节（日期区间/弹层重叠/维度筛选器） | 探索 §3/§8 发现#3 | 错误推测法 | manual | L2 |

## 3. 用例设计

### TC-ISSUE111-001: 项目维度汇总接口契约与遗留问题数公式验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-001 |
| 所属功能点 | F3 遗留问题数计算口径 / F1 项目维度 |
| 测试设计方法 | 等价类划分 + 边界值（零值分量） |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_statistics_001.py |
| 优先级 | L0 |
| 前置条件 | beta 环境已登录（高权限 p_tianyan）；项目维度近30天存在数据（实测 25） |
| 测试步骤 | 1. POST `/gateway/openlibing-ops/quality/dashboard/issue-legacy-statistics`，body=`{"aspect":"project","startDate":"<today-29>","endDate":"<today>","productId":"","projectId":"3"}`<br>2. 校验响应 code=200<br>3. 校验 `data.summary` 含 8 个计数字段<br>4. 断言 `issueLegacyCount == issueCriticalCount + issueMajorCount + issueMinorCount + issueTrivialCount + issueNopriorityCount`<br>5. 断言各计数字段 ≥ 0（整数类型） |
| 预期结果 | code=200；summary 字段完整；遗留问题数等于五级计数之和（权重均为1，与 Issue 3.1 口径一致）；`items` 允许为 null（探索 §8 发现#5） |

### TC-ISSUE111-002: 组织维度汇总接口契约与遗留问题数公式验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-002 |
| 所属功能点 | F3 遗留问题数计算口径 / F2 组织维度 |
| 测试设计方法 | 等价类划分 + 边界值 |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_statistics_001.py |
| 优先级 | L0 |
| 前置条件 | 同 TC-ISSUE111-001 |
| 测试步骤 | 1. POST 同接口，body=`{"aspect":"all","startDate":"<today-29>","endDate":"<today>","productId":"","projectId":""}`<br>2. 校验 code=200 与 summary 字段完整性<br>3. 断言五级求和公式<br>4. 断言 `issueLegacyDiCount` 为两位小数字符串格式 |
| 预期结果 | code=200；组织维度（aspect=all）汇总返回合计行；公式成立；DI 格式如 "397.00" |

### TC-ISSUE111-003: 汇总卡片与明细全量求和一致性验证（项目维度）

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-003 |
| 所属功能点 | F4 汇总-明细一致性 / F3 公式 |
| 测试设计方法 | 场景法（数据流对照） |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_consistency_002.py |
| 优先级 | L0 |
| 前置条件 | 同 TC-ISSUE111-001；项目维度明细 total ≥ 10（触发分页，实测 35） |
| 测试步骤 | 1. 调 statistics（项目维度近30天）取 summary 各字段值<br>2. 循环调 detail（page=1..N，pageSize=10）拉取全量 records<br>3. 对全量 records 逐行断言五级求和公式<br>4. 全量求和（Bug总数/遗留数/五级计数/DI）与 summary 对照 |
| 预期结果 | 分页拉取行数之和 == detail total == 汇总口径；每行满足公式；全量求和与 summary 各字段一致 |

### TC-ISSUE111-004: 汇总卡片与明细全量求和一致性验证（组织维度）

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-004 |
| 所属功能点 | F4 汇总-明细一致性 |
| 测试设计方法 | 场景法（数据流对照） |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_consistency_002.py |
| 优先级 | L0 |
| 前置条件 | 同 TC-ISSUE111-002；组织维度明细 total ≥ 10（实测 31） |
| 测试步骤 | 1. statistics（aspect=all 近30天）取 summary<br>2. detail（aspect=organization）分页拉全量（行含 productName/projectName，repoUrl 为 null）<br>3. 逐行公式断言 + 全量求和与 summary 对照 |
| 预期结果 | 组织维度全量求和与 summary 一致；行字段结构与探索 §4.3 契约一致 |

### TC-ISSUE111-005: 时间范围四档参数映射与区间单调性验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-005 |
| 所属功能点 | F5 时间范围切换 |
| 测试设计方法 | 等价类划分（四档输入域）+ 边界值（startDate=today-6/29/89） |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_time_range_003.py |
| 优先级 | L0 |
| 前置条件 | 同 TC-ISSUE111-001 |
| 测试步骤 | 1. 依据探索 §5 映射表计算四档日期：今日(today,today)、近7天(today-6,today)、近30天(today-29,today)、近90天(today-89,today)<br>2. 分别调 statistics（项目维度）<br>3. 断言四档响应 code=200 且 issueLegacyCount ≥ 0<br>4. 断言区间包含关系下单调不减：今日 ≤ 近7天 ≤ 近30天 ≤ 近90天 |
| 预期结果 | 四档均正常返回；因区间包含（今日⊆7天⊆30天⊆90天），遗留数单调不减（探索实测 0/7/25/66） |

### TC-ISSUE111-006: 明细分页参数与翻页数据不重叠验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-006 |
| 所属功能点 | F6 明细列表分页 |
| 测试设计方法 | 边界值分析（page=1、末页、pageSize=10） |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_detail_004.py |
| 优先级 | L1 |
| 前置条件 | 项目维度近30天 total ≥ 20（分页至少 3 页） |
| 测试步骤 | 1. detail 请求 page=1、pageSize=10 → 断言 records 长度=10<br>2. page=2 → 断言记录与第 1 页无重叠（按行键 repoUrl 比对）<br>3. 末页 page=ceil(total/10) → 断言 records 长度 = total - 10*(page-1)（末页不足 10 条边界）<br>4. 断言分页元数据 total/page/pageSize 回显正确 |
| 预期结果 | 首页 10 条、末页余数条数正确、跨页无重叠、total 与实际行数一致 |

### TC-ISSUE111-007: 全量导出与明细一致性及文件结构验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-007 |
| 所属功能点 | F7 全量导出 |
| 测试设计方法 | 场景法（导出流程） |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_export_005.py |
| 优先级 | L1 |
| 前置条件 | 同 TC-ISSUE111-001；导出近90天项目维度（实测 48 行全量） |
| 测试步骤 | 1. POST `/common/export/issue-legacy-detail`（category=issue-legacy-detail，近90天，项目维度，无 page/pageSize）<br>2. 校验响应为 xlsx 文件流（Content-Type / 文件名 `Issue遗留问题明细_*.xlsx`）<br>3. 解析 xlsx：Sheet 名「Issue遗留问题明细」，11 列（社区/子组织/分组/代码仓/Bug总数/遗留问题数/遗留DI/严重/主要/次要/不重要/无优先级——按探索 §4.4 实测列序）<br>4. 断言数据行数 == detail 近90天 total（全量，不受分页限制） |
| 预期结果 | 文件流正确、列结构完整、行数等于明细 total（导出全量语义） |

### TC-ISSUE111-008: 趋势接口契约结构冒烟验证（两维度）

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-008 |
| 所属功能点 | F9 趋势接口契约 |
| 测试设计方法 | 等价类划分（契约结构） |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_trend_006.py |
| 优先级 | L2 |
| 前置条件 | 同 TC-ISSUE111-001 |
| 测试步骤 | 1. POST issue-legacy-trend（aspect=project，近30天）→ 断言 code=200、`data.dates` 非空且长度=30、`trendGroups[]` 每组含 `trendList[]`<br>2. aspect=organization（近30天）→ 同结构断言<br>3. 校验 trendList 长度与 dates 一致 |
| 预期结果 | 两维度趋势接口契约结构完整（数据正确性属"趋势图另行设计"范围，不做断言） |

### TC-ISSUE111-009: 关联指标字段完整性与数值格式验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-009 |
| 所属功能点 | F8 关联指标展示 |
| 测试设计方法 | 等价类划分（字段类型域） |
| 用例类型 | auto_api |
| 脚本位置 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_fields_007.py |
| 优先级 | L1 |
| 前置条件 | 同 TC-ISSUE111-001 |
| 测试步骤 | 1. statistics 两维度响应中校验字段集：issueBugCount/issueLegacyCount/issueLegacyDiCount/issueCriticalCount/issueMajorCount/issueMinorCount/issueTrivialCount/issueNopriorityCount<br>2. 断言计数类字段为非负整数<br>3. 断言 issueLegacyDiCount 为字符串且匹配 `^\d+\.\d{2}$`<br>4. 记录 issueBugCount 与 issueLegacyCount 的关系（当前实测相等，作为 R6 观察项，不断言） |
| 预期结果 | 8 个指标字段齐全、类型正确、DI 格式两位小数；R6 统计口径差异记录为观察项 |

### TC-ISSUE111-010: 项目维度看板菜单入口与页面展示验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-010 |
| 所属功能点 | F1 项目维度看板展示 |
| 测试设计方法 | 场景法 |
| 用例类型 | auto_ui |
| 脚本位置 | src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_project_001.py |
| 优先级 | L0 |
| 前置条件 | beta 已登录（p_tianyan） |
| 测试步骤 | 1. 展开侧边栏「测试管理」→ 点击「质量风险」菜单<br>2. 断言页面 URL 为 `/apps/qualityRiskProject?projectId=3`<br>3. 断言 iframe（`quality-risk-project`）加载完成<br>4. 断言 7 张汇总卡片渲染（遗留问题总数/遗留DI/严重问题/主要问题/次要问题/不重要问题/无优先级问题）<br>5. 断言明细表格列头（代码仓/Bug总数/遗留问题数/遗留DI/严重/主要/次要/不重要/无优先级）与默认时间范围控件存在 |
| 预期结果 | 菜单可达、页面与 iframe 正常加载、卡片与表格结构完整 |

### TC-ISSUE111-011: 组织维度看板直达 URL 加载与展示验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-011 |
| 所属功能点 | F2 组织维度看板展示 |
| 测试设计方法 | 场景法 |
| 用例类型 | auto_ui |
| 脚本位置 | src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_org_002.py |
| 优先级 | L0 |
| 前置条件 | beta 已登录（p_tianyan）；组织看板存在数据 |
| 测试步骤 | 1. 直达 `https://beta.openlibing.com/ops/dashboard/quality-risk-org`（菜单入口缺失，见策略风险#1）<br>2. 首载若"暂无数据"（框架 503），刷新重试（≤3 次）<br>3. 断言 7 张汇总卡片渲染且数值非空<br>4. 断言社区列表表格列头（社区/子组织/分组/Bug总数/遗留问题数/遗留DI/严重/主要/次要/不重要/无优先级）与维度筛选器「全部」存在 |
| 预期结果 | 组织看板加载成功、卡片与社区列表结构完整（菜单入口缺失单独反馈开发） |

### TC-ISSUE111-012: UI 时间范围四档切换与三接口联动验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-012 |
| 所属功能点 | F5 时间范围切换（UI 层） |
| 测试设计方法 | 等价类划分（四档）+ 边界值 |
| 用例类型 | auto_ui |
| 脚本位置 | src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_time_range_003.py |
| 优先级 | L0 |
| 前置条件 | 项目维度看板已打开 |
| 测试步骤 | 1. iframe 内依次点击「近7天」「近30天」「近90天」「今日」（"今日"点击容错处理弹层重叠）<br>2. 每次切换后抓包断言 statistics 请求体 startDate/endDate 与映射表一致<br>3. 断言切换触发 statistics + trend + detail 三接口重查<br>4. 断言卡片数值随档位变化（今日 ≤ 近90天） |
| 预期结果 | 四档切换均触发正确参数的三接口重查；卡片数值与档位数据一致 |

### TC-ISSUE111-013: UI 卡片展示值与 API 返回一致性验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-013 |
| 所属功能点 | F8 关联指标展示（前后端层） / F4 一致性 |
| 测试设计方法 | 场景法（前后端对照） |
| 用例类型 | auto_ui |
| 脚本位置 | src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_data_consistency_004.py |
| 优先级 | L1 |
| 前置条件 | 项目维度看板已打开（默认近30天） |
| 测试步骤 | 1. 抓取页面 statistics 接口响应 summary<br>2. 读取 7 张卡片显示文本（数字部分）<br>3. 逐卡片断言 UI 显示值 == 接口返回对应字段值<br>4. 抓取 detail 响应，断言表格首行各列文本 == records[0] 对应字段 |
| 预期结果 | 前端展示与接口数据一致（遗留问题总数/遗留DI/各级别卡片） |

### TC-ISSUE111-014: UI 明细分页翻页与导出下载验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-014 |
| 所属功能点 | F6 分页（UI 层）/ F7 导出（UI 层） |
| 测试设计方法 | 边界值分析 + 场景法 |
| 用例类型 | auto_ui |
| 脚本位置 | src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_detail_export_005.py |
| 优先级 | L1 |
| 前置条件 | 项目维度看板已打开；明细 total > 10 |
| 测试步骤 | 1. 断言分页组件显示（10条/页）与总数<br>2. 点击下一页 → 断言表格数据刷新且与第 1 页不同<br>3. 点击「导出」→ 等待下载事件<br>4. 断言下载文件名匹配 `Issue遗留问题明细_*.xlsx` 且文件非空 |
| 预期结果 | 分页翻页数据正确刷新；导出按钮触发 xlsx 下载且文件非空 |

### TC-ISSUE111-015: 匿名与伪造 token 调用看板接口被拒绝验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-015 |
| 所属功能点 | F10 认证校验 |
| 测试设计方法 | 错误推测法 |
| 用例类型 | auto_sec |
| 脚本位置 | src/tests/openlibing/openlibing_ops/security/beta/quality_dashboard/test_security_quality_dashboard_auth_001.py |
| 优先级 | L1 |
| 前置条件 | SECURITY_ENABLED=true 且 test 环境；4 个看板接口清单（探索 §4） |
| 测试步骤 | 1. 不携带任何凭证调用 4 个接口（statistics/trend/detail/export）<br>2. 携带伪造 token（随机字符串）调用同样 4 个接口<br>3. 按规则 04 断言方向：401/403 → 通过；200+code==200 → 失败（越权） |
| 预期结果 | 匿名与伪造 token 请求均被服务端拒绝（assert_denied 语义） |

### TC-ISSUE111-016: 低权限账号调用看板接口被拒绝验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-016 |
| 所属功能点 | F11 纵向越权 |
| 测试设计方法 | 错误推测法（双身份对照） |
| 用例类型 | auto_sec |
| 脚本位置 | src/tests/openlibing/openlibing_ops/security/beta/quality_dashboard/test_security_quality_dashboard_vertical_002.py |
| 优先级 | L1 |
| 前置条件 | 低权限账号 `pub_LIBING`（.env `SECURITY_LOW_PRIV_*`）保持纯低权限；高权限 `p_tianyan` 作对照基线 |
| 测试步骤 | 1. 高权限调用 4 个接口 → 断言 200+code=200（合法基线可用）<br>2. 低权限以同参数调用 4 个接口<br>3. 断言方向：401/403 → 通过；200+code==200 → 失败（越权成功，视为缺陷） |
| 预期结果 | 低权限账号被拒绝（高权限对照基线正常，参考 2026-08-11 验证基线模式） |

### TC-ISSUE111-017: 看板接口响应体敏感信息防护验证

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-017 |
| 所属功能点 | F12 敏感信息防护 |
| 测试设计方法 | 错误推测法 |
| 用例类型 | auto_sec |
| 脚本位置 | src/tests/openlibing/openlibing_ops/security/beta/quality_dashboard/test_security_quality_dashboard_sensitive_003.py |
| 优先级 | L2 |
| 前置条件 | 高权限正常调用 4 个接口获取响应体 |
| 测试步骤 | 1. 以高权限调用 4 个接口取响应文本<br>2. 扫描敏感模式：token/password/secret/key/手机号/邮箱等字段值泄漏（repoUrl、社区名等业务数据不计入）<br>3. 校验响应头不回显 Set-Cookie 凭证类异常 |
| 预期结果 | 响应体不包含凭证/密钥/个人敏感信息字段 |

### TC-ISSUE111-018: 组织维度「测试运营」菜单入口验证（待部署）

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-018 |
| 所属功能点 | F13 组织维度菜单入口 |
| 测试设计方法 | 场景法 |
| 用例类型 | manual |
| 脚本位置 | — |
| 优先级 | L1 |
| 前置条件 | 开发补充部署侧边栏「测试运营」菜单（当前缺失，探索 §8 发现#1） |
| 测试步骤 | 1. 登录 beta，检查侧边栏是否出现「测试运营」菜单组<br>2. 展开并点击组织维度看板菜单项<br>3. 断言跳转组织质量风险看板页面 |
| 预期结果 | 「测试运营」菜单存在且入口可达组织看板（当前 block：菜单未部署） |

### TC-ISSUE111-019: UI 交互细节验证（日期区间选择/弹层重叠/维度筛选器）

| 字段 | 内容 |
|------|------|
| 用例编号 | TC-ISSUE111-019 |
| 所属功能点 | F14 UI 交互细节 |
| 测试设计方法 | 错误推测法 |
| 用例类型 | manual |
| 脚本位置 | — |
| 优先级 | L2 |
| 前置条件 | 组织与项目维度看板均可访问 |
| 测试步骤 | 1. 使用日期区间选择器自定义起止日期，检查查询刷新<br>2. 观察"今日"切换时日期弹层与控件重叠现象（探索发现#3）是否影响操作<br>3. 组织维度操作维度筛选器「全部」下拉，观察选项与刷新<br>4. 检查两维度页面在 1920/1440 宽度下布局正常 |
| 预期结果 | 自定义区间生效；弹层重叠不阻塞操作（若阻塞记录缺陷）；筛选器与布局正常 |

## 4. 覆盖度说明

- 需求基线功能点数（R1-R7）：7
- 本设计覆盖功能点数：7（R1→F2/F13、R2→F1、R3→F3、R4→F4/F8、R5→F5、R6→F9 观察项+TC-009、R7→TC-001/003 零值分量公式断言）
- 未覆盖及原因：
  - R6 统计口径（Bug-Report 类型/标签过滤）为后台过滤逻辑，黑盒不可直接观测 → 以 issueBugCount 与 issueLegacyCount 关系作观察项记录，不断言
  - R7 无严重级别按"一般"统计：实测实现为独立"无优先级"分桶（探索 §7 注2），因权重均为1总数不受影响 → 差异作为观察项反馈开发，公式断言退化为零值分量验证
  - 趋势图数据设计与正确性：Issue 明示另行设计，不在本期范围（仅 F9 契约冒烟）
  - 性能：Issue 非功能需求留空，不覆盖（策略 §4 已声明）
- 安全 6 维度覆盖声明见 test_strategy.md §5.2（覆盖 auth/vertical/sensitive，CSRF/横向/传输不覆盖并说明原因）

## 5. 版本历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0 | 2026-08-31 | AI Agent | 初始版本（14 功能点 / 19 用例：9 API + 5 UI + 3 安全 + 2 手工） |
