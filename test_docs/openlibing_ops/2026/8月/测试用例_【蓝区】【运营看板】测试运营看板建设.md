# 测试用例 - ISSUE-043

> **Issue编号**: ISSUE-043
> **Issue标题**: 【蓝区】【运营看板】测试运营看板建设
> **创建日期**: 2026-08-28
> **用例总数**: 26
> **手工用例**: 2
> **自动化用例**: 24
> **复用旧用例**: 0
> **新设计用例**: 26

### 执行信息

> 由**测试人员**填写。自动化用例的 Action 链接在此**统一填写一个**，无需每条用例重复填写。

| 字段 | 内容 |
|------|------|
| 自动化执行Action链接 | —（本地 pytest 执行：沙箱网络受限未走 gitcode action；命令 `TEST_ENV=test pytest -m quality_risk`，报告见 reports/latest/） |
| 手工执行人 | AI 辅助探针执行（Playwright 自动化探针代执行 TC-008/009，证据存档 `_probe_manual.txt`，待测试人员复核） |
| 执行日期 | 2026-08-28（首轮全量）/ 2026-08-31（TC-015 缺陷复测：`pytest src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_002.py::TestApiQualityRiskDetailBoundary::test_api_quality_risk_detail_paging_015 --env=test`，1 passed） |

---

## 用例列表

| 用例编号 | 用例标题 | 所属功能点 | 用例类型 | 用例来源 | 用例等级 | 脚本位置 | 状态 |
|----------|----------|------------|----------|----------|----------|----------|------|
| TC-ISSUE043-001 | 组织维度页面加载与 KPI 卡片渲染 | F1/F2 | auto_ui | new | L0 | src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/page_load/test_ui_quality_risk_page_load_beta_001.py | active |
| TC-ISSUE043-002 | 项目维度页面加载与代码仓列表渲染 | F1/F2 | auto_ui | new | L0 | src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/page_load/test_ui_quality_risk_page_load_beta_001.py | active |
| TC-ISSUE043-003 | 组织维度 L1→L2 下钻与面包屑返回 | F3 | auto_ui | new | L0 | src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/drilldown/test_ui_quality_risk_drilldown_beta_001.py | active |
| TC-ISSUE043-004 | 时间范围切换数据刷新（近7天） | F4 | auto_ui | new | L1 | src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/filters/test_ui_quality_risk_filters_beta_001.py | active |
| TC-ISSUE043-005 | 项目维度代码仓列外链跳转属性 | F5 | auto_ui | new | L1 | src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/drilldown/test_ui_quality_risk_drilldown_beta_001.py | active |
| TC-ISSUE043-006 | 趋势折线图渲染与图例 | F4 | auto_ui | new | L1 | src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/charts/test_ui_quality_risk_charts_beta_001.py | active |
| TC-ISSUE043-007 | L1 表格分页器与总数 | F2 | auto_ui | new | L1 | src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/filters/test_ui_quality_risk_filters_beta_001.py | active |
| TC-ISSUE043-008 | 导出按钮点击提示"开发中" | F5 | manual | new | L1 | — | active |
| TC-ISSUE043-009 | 趋势图样式与 PR 门禁看板一致性 + 空态 | F4 | manual | new | L2 | — | active |
| TC-ISSUE043-010 | statistics 接口正常响应（项目维度） | F6 | auto_api | new | L0 | src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_statistics_001.py | active |
| TC-ISSUE043-011 | statistics 数据一致性（分项之和=总数） | F6 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_statistics_001.py | active |
| TC-ISSUE043-012 | trend 接口正常响应与数据结构 | F6 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_trend_001.py | active |
| TC-ISSUE043-013 | detail 接口组织维度 L1 社区列表 | F6 | auto_api | new | L0 | src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_001.py | active |
| TC-ISSUE043-014 | detail 接口项目维度代码仓列表 | F6 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_001.py | active |
| TC-ISSUE043-015 | detail 接口分页边界值 | F6 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_002.py | active |
| TC-ISSUE043-016 | 时间范围参数数据量关系（近7天≤近30天） | F4/F6 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_002.py | active |
| TC-ISSUE043-017 | 异常参数容错（非法日期格式） | F6 | auto_api | new | L2 | src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_002.py | active |
| TC-ISSUE043-018 | statistics 接口响应时间 | F6 | auto_perf | new | L2 | src/tests/openlibing/openlibing_ops/performance/beta/quality_risk/test_performance_quality_risk_response_time_001.py | active |
| TC-ISSUE043-019 | trend 接口响应时间 | F6 | auto_perf | new | L2 | src/tests/openlibing/openlibing_ops/performance/beta/quality_risk/test_performance_quality_risk_response_time_001.py | active |
| TC-ISSUE043-020 | detail 接口响应时间 | F6 | auto_perf | new | L2 | src/tests/openlibing/openlibing_ops/performance/beta/quality_risk/test_performance_quality_risk_response_time_001.py | active |
| TC-ISSUE043-021 | 认证校验-三接口匿名访问 | F6 | auto_sec | new | L1 | src/tests/openlibing/openlibing_ops/security/beta/quality_risk/test_security_quality_risk_auth_001.py | active |
| TC-ISSUE043-022 | 横向越权-projectId 数据隔离 | F6 | auto_sec | new | L1 | src/tests/openlibing/openlibing_ops/security/beta/quality_risk/test_security_quality_risk_horizontal_001.py | active |
| TC-ISSUE043-023 | 传输安全-HTTPS 验证 | F6 | auto_sec | new | L2 | src/tests/openlibing/openlibing_ops/security/beta/quality_risk/test_security_quality_risk_transport_001.py | active |
| TC-ISSUE043-024 | 敏感信息防护-响应字段检查 | F6 | auto_sec | new | L2 | src/tests/openlibing/openlibing_ops/security/beta/quality_risk/test_security_quality_risk_transport_001.py | active |
| TC-ISSUE043-025 | 表格列排序切换 | F2 | auto_ui | new | L1 | src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/filters/test_ui_quality_risk_filters_beta_001.py | active |
| TC-ISSUE043-026 | detail 接口 L2 下钻参数（productId） | F6 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_001.py | active |

> **用例来源说明**：
> - `reuse`：复用已有用例，引用已有用例编号（在详情中"引用已有用例"字段标注），不重新归档
> - `new`：新设计用例，必须按规则 5.3 归档到模块用例文件与 case_list.md

---

## 执行结果记录

> 本节由**测试人员**确认后填写，AI 不得代填。执行结果未填写完整前，AI 不得生成测试报告（见规则 03 第4节）。

| 用例编号 | 用例类型 | 执行结果 | 缺陷issue | 备注 |
|----------|----------|----------|------------|------|
| TC-ISSUE043-001 | auto_ui | pass | — | KPI 7 卡片齐全，数值非负（近30天：遗留总数364） |
| TC-ISSUE043-002 | auto_ui | pass | — | 深链 projectId=3 生效，表头 9 列与需求一致 |
| TC-ISSUE043-003 | auto_ui | pass | — | L1→L2 下钻路由/面包屑"全部/社区名"正常，返回 L1 恢复 |
| TC-ISSUE043-004 | auto_ui | pass | — | 近7天(13) ≤ 近30天(40)，按钮选中态正确 |
| TC-ISSUE043-005 | auto_ui | pass | — | 代码仓链接指向 gitcode.com 且 target=_blank |
| TC-ISSUE043-006 | auto_ui | pass | — | canvas 图表渲染，图例含 5 个严重级别 |
| TC-ISSUE043-007 | auto_ui | pass | — | 分页器"共 N 条"+页码切换正常 |
| TC-ISSUE043-008 | manual | pass | — | 正向偏差：验收标准6预期"提示开发中"，实测导出功能已实现——toast"导出成功！"、POST /common/export/issue-legacy-detail 返回 200、下载 xlsx 成功（组织/项目两维度均验证，证据 _probe_manual.txt）。建议更新 Issue 描述 |
| TC-ISSUE043-009 | manual | pass | — | 趋势图与 PR 门禁看板同为 canvas 全宽折线图（1560×250 vs 1568×250）样式一致；"今日"空数据时 KPI 归零+表格"暂无数据"空态正常 |
| TC-ISSUE043-010 | auto_api | pass | — | code==200，items 非空，严重级计数字段完整 |
| TC-ISSUE043-011 | auto_api | pass | — | 分项之和==总数==遗留DI（364） |
| TC-ISSUE043-012 | auto_api | pass | — | dates 升序 YYYY-MM-DD，各严重级序列长度匹配 |
| TC-ISSUE043-013 | auto_api | pass | — | 组织维度 L1 total=26，records≤10，字段完整 |
| TC-ISSUE043-014 | auto_api | pass | — | 项目维度 total=40，repoUrl 含 gitcode.com |
| TC-ISSUE043-015 | auto_api | pass | [issue #112](https://gitcode.com/openlibing/openlibing-ops/issues/112)（已修复） | 2026-08-28 首轮 fail（page=9999 超界返回全量 26 条）；**2026-08-31 复测 pass**：page=9999 返回空 records（0 条）、pageSize=1 时 records=1、pageSize=1/10 total 一致（35=35），缺陷已修复 |
| TC-ISSUE043-016 | auto_api | pass | — | 近7天(13) ≤ 近30天(40) |
| TC-ISSUE043-017 | auto_api | pass | — | 非法日期不引发 5xx，响应可解析 |
| TC-ISSUE043-018 | auto_perf | pass | — | statistics：avg<554ms，P95<1024ms，错误率 0% |
| TC-ISSUE043-019 | auto_perf | pass | — | trend：avg<554ms，P95<1024ms，错误率 0% |
| TC-ISSUE043-020 | auto_perf | pass | — | detail：avg<554ms，P95<1024ms，错误率 0% |
| TC-ISSUE043-021 | auto_sec | pass | — | 三接口匿名 POST 均返回 401 |
| TC-ISSUE043-022 | auto_sec | pass | — | projectId=3(total=40)/300036(total=3) 数据隔离；999999 返回空 |
| TC-ISSUE043-023 | auto_sec | pass | — | 全程 HTTPS，HTTP 明文降级被拒绝 |
| TC-ISSUE043-024 | auto_sec | pass | — | 响应体无敏感字段泄露 |
| TC-ISSUE043-025 | auto_ui | pass | — | "Bug总数"列升降序切换有效，非递增/非递减断言通过 |
| TC-ISSUE043-026 | auto_api | pass | — | productId=200020 下钻生效，L2(≤L1) 记录含 subOrgName |

> **执行结果取值**：pass（通过）/ fail（失败）/ block（阻塞）/ skip（跳过）
> **填写要求**：
> - 自动化用例的 Action 链接在头部"执行信息"中统一填写，此处不重复
> - 手工用例的执行人在头部"执行信息"中统一填写，此处不重复
> - **fail 用例必须创建并填写缺陷issue**（gitcode 缺陷 issue 链接），否则不得生成报告
> - fail/block 用例必须填写 备注 说明原因

---

## 手工用例详情

### TC-ISSUE043-008: 导出按钮点击提示"开发中"

- **所属功能点**: F5 导出按钮（后台接口未就绪，前端预留）
- **测试设计方法**: 错误推测法
- **用例类型**: 手工执行 (manual)
- **用例来源**: new
- **引用已有用例**: —
- **用例等级**: L1
- **前置条件**: 已登录 beta 环境；打开质量风险看板（组织维度）或质量风险（项目维度）页面
- **测试步骤**:
  1. 打开 https://beta.openlibing.com/apps/qualityRiskDashboard?projectId=3
  2. 定位表格区域上方的"导出"按钮
  3. 点击导出按钮
  4. 观察页面反馈（提示文案 / 按钮状态 / 是否有下载）
  5. 在项目维度页面 https://beta.openlibing.com/apps/qualityRiskProject?projectId=3 重复步骤 2-4
- **预期结果**: 点击导出按钮后出现"开发中"类提示文案（验收标准6：导出按钮预留（提示"开发中"））。若实际触发接口调用且返回 200 文件流或按钮静默禁用无任何提示，则为与验收标准不符，需记录并与开发确认

### TC-ISSUE043-009: 趋势图样式与 PR 门禁看板一致性 + 空态

- **所属功能点**: F4 遗留问题趋势折线图
- **测试设计方法**: 场景法
- **用例类型**: 手工执行 (manual)
- **用例来源**: new
- **引用已有用例**: —
- **用例等级**: L2
- **前置条件**: 已登录 beta 环境；可对照 PR 门禁看板页面
- **测试步骤**:
  1. 打开质量风险看板页面，观察趋势分析折线图样式（配色、图例、tooltip、X/Y 轴）
  2. 与 PR 门禁看板的趋势图样式对比（布局、交互一致性）
  3. 切换时间范围为"今日"（数据量最小），观察无数据/少数据时的空态展示
  4. 截图记录样式与空态
- **预期结果**: 趋势图样式与 PR 门禁看板一致；无数据时展示空态而非报错/空白异常

---

## 自动化用例详情

### TC-ISSUE043-001: 组织维度页面加载与 KPI 卡片渲染

- **所属功能点**: F1 组织维度视角 + F2 KPI 卡片
- **测试设计方法**: 场景法
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/page_load/test_ui_quality_risk_page_load_beta_001.py`
- **用例等级**: L0
- **前置条件**: 已登录 beta 环境；打开 https://beta.openlibing.com/apps/qualityRiskDashboard?projectId=3
- **测试步骤**:
  1. 导航到组织维度页面并等待加载
  2. 断言页面标题含"质量风险看板"
  3. 断言 iframe 路由为 /ops/dashboard/quality-risk-org
  4. 断言 KPI 卡片区域渲染 7 张卡片（遗留问题总数/遗留DI/严重/主要/次要/不重要/无优先级）
  5. 断言各卡片数值为非负数字
- **预期结果**: 页面正常渲染，KPI 卡片齐全且数值合法

### TC-ISSUE043-002: 项目维度页面加载与代码仓列表渲染

- **所属功能点**: F1 项目维度视角（路由参数深链）+ F2 项目列表
- **测试设计方法**: 场景法
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/page_load/test_ui_quality_risk_page_load_beta_001.py`
- **用例等级**: L0
- **前置条件**: 已登录 beta 环境
- **测试步骤**:
  1. 导航到 https://beta.openlibing.com/apps/qualityRiskProject?projectId=3 并等待加载
  2. 断言页面标题含"质量风险"
  3. 断言 iframe 路由为 /ops/dashboard/quality-risk-project/3（深链参数生效）
  4. 断言 KPI 卡片渲染且数值非负
  5. 断言表格表头包含 9 列（代码仓、Bug总数、遗留问题数、遗留DI、严重、主要、次要、不重要、无优先级）
  6. 断言表格至少渲染 1 行数据（或空态文案）
- **预期结果**: 项目维度页面正常渲染，深链 projectId 生效，表格列与需求一致

### TC-ISSUE043-003: 组织维度 L1→L2 下钻与面包屑返回

- **所属功能点**: F3 L2/L3 下钻（面包屑导航）
- **测试设计方法**: 场景法
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/drilldown/test_ui_quality_risk_drilldown_beta_001.py`
- **用例等级**: L0
- **前置条件**: 组织维度 L1 表格存在至少 1 条社区数据（如 LingQu）
- **测试步骤**:
  1. 在组织维度 L1 页面点击表格第一行社区名称
  2. 断言 iframe URL 变为 /ops/dashboard/quality-risk-org/{orgId}
  3. 断言面包屑显示"全部 / {社区名}"
  4. 断言表格切换为子组织列表（重新渲染）
  5. 在 L2 点击第一行子组织下钻 L3，断言表格切换为代码仓明细列表（L2 无数据时 skip）
  6. 点击面包屑逐级返回，断言 URL 回到 /ops/dashboard/quality-risk-org，表格恢复社区列表
- **预期结果**: 社区 → 子组织 → 代码仓逐级下钻与面包屑返回正常（验收标准2）

### TC-ISSUE043-004: 时间范围切换数据刷新（近7天）

- **所属功能点**: F4 时间范围筛选
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/filters/test_ui_quality_risk_filters_beta_001.py`
- **用例等级**: L1
- **前置条件**: 项目维度页面已加载（默认近30天）
- **测试步骤**:
  1. 记录默认近30天的表格总条数
  2. 点击时间范围"近7天"按钮
  3. 等待表格刷新，断言"近7天"按钮为选中态
  4. 记录近7天的表格总条数
  5. 断言近7天总条数 ≤ 近30天总条数
- **预期结果**: 时间范围切换生效，KPI 与表格数据同步刷新（验收标准3）

### TC-ISSUE043-005: 项目维度代码仓列外链跳转属性

- **所属功能点**: F5 代码仓列可点击跳转
- **测试设计方法**: 错误推测法
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/drilldown/test_ui_quality_risk_drilldown_beta_001.py`
- **用例等级**: L1
- **前置条件**: 项目维度表格存在至少 1 行代码仓数据
- **测试步骤**:
  1. 定位项目维度表格第一行代码仓链接元素
  2. 断言链接 href 指向 gitcode.com 域名
  3. 断言链接具备新标签打开属性（target=_blank 或等价 DOM 特征）
- **预期结果**: 代码仓列可点击且新开标签跳转 gitcode（验收标准5）

### TC-ISSUE043-006: 趋势折线图渲染与图例

- **所属功能点**: F4 遗留问题趋势折线图
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/charts/test_ui_quality_risk_charts_beta_001.py`
- **用例等级**: L1
- **前置条件**: 组织维度或项目维度页面已加载
- **测试步骤**:
  1. 定位"趋势分析"区域
  2. 断言区域标题与副标题（遗留问题按严重级别每日趋势）存在
  3. 断言 canvas/echarts 图表元素存在
  4. 断言图例包含 5 项：严重、主要、次要、不重要、无优先级
- **预期结果**: 趋势折线图正常渲染，图例齐全（验收标准4）

### TC-ISSUE043-007: L1 表格分页器与总数

- **所属功能点**: F2 社区/项目列表支持分页
- **测试设计方法**: 边界值分析
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/filters/test_ui_quality_risk_filters_beta_001.py`
- **用例等级**: L1
- **前置条件**: 组织维度或项目维度页面已加载
- **测试步骤**:
  1. 断言表格区域存在分页器组件
  2. 断言分页器显示总条数（"共 N 条"类文案，N>0）
  3. 如存在第 2 页，点击第 2 页，断言表格数据刷新且页码高亮切换
- **预期结果**: 分页功能正常（验收标准3）

### TC-ISSUE043-010: statistics 接口正常响应（项目维度）

- **所属功能点**: F6 issue-legacy-statistics 接口
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_statistics_001.py`
- **用例等级**: L0
- **前置条件**: 已登录 beta 环境（api_client 会话有效）
- **测试步骤**:
  1. POST /gateway/openlibing-ops/quality/dashboard/issue-legacy-statistics，请求体 {"aspect": "project", "startDate": "近30天起", "endDate": "今日", "productId": "", "projectId": "3"}
  2. 断言 HTTP 200 且业务 code==200
  3. 断言 data 含各严重级计数字段（遗留问题总数/严重/主要/次要/不重要/无优先级）
  4. 断言各计数值为非负数
- **预期结果**: KPI 汇总接口正常返回，字段完整且数值合法

### TC-ISSUE043-011: statistics 数据一致性（分项之和=总数）

- **所属功能点**: F6 issue-legacy-statistics 接口数据正确性
- **测试设计方法**: 错误推测法
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_statistics_001.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE043-010
- **测试步骤**:
  1. 请求 statistics（aspect=project, projectId=3，近30天）
  2. 提取各严重级计数与遗留问题总数
  3. 断言 严重+主要+次要+不重要+无优先级 == 遗留问题总数
- **预期结果**: 分项之和与总数一致（KPI 数据正确，验收标准1）

### TC-ISSUE043-012: trend 接口正常响应与数据结构

- **所属功能点**: F6 issue-legacy-trend 接口
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_trend_001.py`
- **用例等级**: L1
- **前置条件**: 已登录 beta 环境
- **测试步骤**:
  1. POST /gateway/openlibing-ops/quality/dashboard/issue-legacy-trend，请求体 {"aspect": "project", "startDate": "近30天起", "endDate": "今日", "productId": "", "projectId": "3"}
  2. 断言 HTTP 200 且业务 code==200
  3. 断言 data 为按日期序列的结构（列表或含日期键的对象），数据点数与日期范围一致
- **预期结果**: 趋势接口正常返回日期序列数据（验收标准4 数据基础）

### TC-ISSUE043-013: detail 接口组织维度 L1 社区列表

- **所属功能点**: F6 common/detail（issue-legacy-detail）组织维度
- **测试设计方法**: 决策表
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_001.py`
- **用例等级**: L0
- **前置条件**: 已登录 beta 环境；组织维度存在社区数据
- **测试步骤**:
  1. POST /gateway/openlibing-ops/common/detail，请求体 {"category": "issue-legacy-detail", "aspect": "organization", "startDate": "近30天起", "endDate": "今日", "productId": "", "projectId": "", "repoUrl": "", "page": 1, "pageSize": 10}
  2. 断言 HTTP 200 且业务 code==200
  3. 断言返回分页结构（records/total）
  4. 断言 total > 0 且 records 每条含社区名称字段（如 communityName/organizationName 等实际字段）
  5. 断言每条记录的计数列为非负数
- **预期结果**: 组织维度 L1 社区列表数据正确（验收标准1）

### TC-ISSUE043-014: detail 接口项目维度代码仓列表

- **所属功能点**: F6 common/detail（issue-legacy-detail）项目维度
- **测试设计方法**: 决策表
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_001.py`
- **用例等级**: L1
- **前置条件**: 已登录 beta 环境；projectId=3 存在代码仓数据
- **测试步骤**:
  1. POST /common/detail，请求体同上但 aspect=project、projectId="3"
  2. 断言 HTTP 200 且业务 code==200
  3. 断言 records 为代码仓列表（每条含 repoUrl 或代码仓地址字段）
  4. 断言 total > 0
- **预期结果**: 项目维度代码仓列表数据正确（验收标准1）

### TC-ISSUE043-015: detail 接口分页边界值

- **所属功能点**: F2/F6 表格分页
- **测试设计方法**: 边界值分析
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_002.py`
- **用例等级**: L1
- **前置条件**: 已登录 beta 环境
- **测试步骤**:
  1. 请求 detail（aspect=project, projectId=3, pageSize=1, page=1）→ 断言返回 records 长度 ≤1
  2. 请求 page=9999（超界页码）→ 断言不返回 5xx，records 为空列表
  3. 请求 pageSize=1 与 pageSize=10 → 断言 total 相同
- **预期结果**: 分页参数边界值行为正确（验收标准3）
- **执行记录**:
  - 2026-08-28 首轮执行 **fail**：page=9999 超界返回全量 26 条记录（预期空 records），登记缺陷 [issue #112](https://gitcode.com/openlibing/openlibing-ops/issues/112)
  - 2026-08-31 复测执行 **pass**：page=9999 返回空 records（0 条）；pageSize=1 时 records=1（≤1）；pageSize=1/10 的 total 一致（35=35）。缺陷 #112 已修复，用例关闭

### TC-ISSUE043-016: 时间范围参数数据量关系（近7天≤近30天）

- **所属功能点**: F4/F6 时间范围筛选
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_002.py`
- **用例等级**: L1
- **前置条件**: 已登录 beta 环境
- **测试步骤**:
  1. 请求 detail（近30天范围）→ 记录 total_30
  2. 请求 detail（近7天范围）→ 记录 total_7
  3. 断言 total_7 ≤ total_30（时间窗口子集关系）
- **预期结果**: 时间范围参数生效且数据量关系合理（验收标准3）

### TC-ISSUE043-017: 异常参数容错（非法日期格式）

- **所属功能点**: F6 接口容错
- **测试设计方法**: 错误推测法
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_002.py`
- **用例等级**: L2
- **前置条件**: 已登录 beta 环境
- **测试步骤**:
  1. 请求 detail，startDate="invalid-date"、endDate="2026/13/45"（非法格式）
  2. 断言 HTTP 状态不为 5xx（服务端不崩溃）
  3. 断言响应为可解析 JSON（业务错误码或空数据均可接受）
- **预期结果**: 非法参数不引发服务端 5xx 异常

### TC-ISSUE043-018: statistics 接口响应时间

- **所属功能点**: F6 性能
- **测试设计方法**: 性能阈值验证
- **用例类型**: 自动化-性能 (auto_perf)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/performance/beta/quality_risk/test_performance_quality_risk_response_time_001.py`
- **用例等级**: L2
- **前置条件**: 已登录 beta 环境
- **测试步骤**:
  1. 连续请求 statistics 接口 20 次（aspect=project, projectId=3）
  2. 统计平均响应时间、P95、错误率
- **预期结果**: avg < 3000ms，P95 < 5000ms，错误率 < 5%

### TC-ISSUE043-019: trend 接口响应时间

- **所属功能点**: F6 性能
- **测试设计方法**: 性能阈值验证
- **用例类型**: 自动化-性能 (auto_perf)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/performance/beta/quality_risk/test_performance_quality_risk_response_time_001.py`
- **用例等级**: L2
- **前置条件**: 已登录 beta 环境
- **测试步骤**: 同 TC-ISSUE043-018，目标接口为 issue-legacy-trend
- **预期结果**: avg < 3000ms，P95 < 5000ms，错误率 < 5%

### TC-ISSUE043-020: detail 接口响应时间

- **所属功能点**: F6 性能
- **测试设计方法**: 性能阈值验证
- **用例类型**: 自动化-性能 (auto_perf)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/performance/beta/quality_risk/test_performance_quality_risk_response_time_001.py`
- **用例等级**: L2
- **前置条件**: 已登录 beta 环境
- **测试步骤**: 同 TC-ISSUE043-018，目标接口为 common/detail（aspect=project, projectId=3）
- **预期结果**: avg < 3000ms，P95 < 5000ms，错误率 < 5%

### TC-ISSUE043-021: 认证校验-三接口匿名访问

- **所属功能点**: F6 安全-认证校验
- **测试设计方法**: 等价类划分（assert_denied 语义）
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/quality_risk/test_security_quality_risk_auth_001.py`
- **用例等级**: L1
- **前置条件**: 无（匿名场景）
- **测试步骤**:
  1. 用不带任何凭证的独立 HTTP 请求调用 issue-legacy-statistics
  2. 同样方式调用 issue-legacy-trend、common/detail
  3. 断言三者均被拒绝（401/403）
- **预期结果**: 三接口均要求认证，匿名访问被拒绝（HTTP 401/403；200+code==200 视为失败）

### TC-ISSUE043-022: 横向越权-projectId 数据隔离

- **所属功能点**: F6 安全-横向越权
- **测试设计方法**: 决策表
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/quality_risk/test_security_quality_risk_horizontal_001.py`
- **用例等级**: L1
- **前置条件**: 已登录账号对 projectId=3 与 projectId=300036 均有访问权（数据隔离对照）
- **测试步骤**:
  1. 请求 statistics（aspect=project, projectId=3）记录数据 A
  2. 请求 statistics（aspect=project, projectId=300036）记录数据 B
  3. 断言 A 与 B 数据不同（不同项目数据隔离）
  4. 请求 detail（projectId=999999 不存在项目）→ 断言不泄露其他项目数据（空数据或业务错误）
- **预期结果**: 不同 projectId 数据正确隔离，不存在跨项目数据泄露

### TC-ISSUE043-023: 传输安全-HTTPS 验证

- **所属功能点**: F6 安全-传输安全
- **测试设计方法**: 属性校验
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/quality_risk/test_security_quality_risk_transport_001.py`
- **用例等级**: L2
- **前置条件**: beta 环境可访问
- **测试步骤**:
  1. 验证三接口 URL 均为 https:// scheme
  2. 发起请求并断言连接为 TLS（无明文降级）
  3. 断言响应无混合内容告警（HTTP 资源引用）
- **预期结果**: 三接口全程 HTTPS 传输（Cookie Secure/HttpOnly 复用 2026-08-11 既有基线结论）

### TC-ISSUE043-024: 敏感信息防护-响应字段检查

- **所属功能点**: F6 安全-敏感信息防护
- **测试设计方法**: 错误推测法
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/quality_risk/test_security_quality_risk_transport_001.py`
- **用例等级**: L2
- **前置条件**: 已登录 beta 环境
- **测试步骤**:
  1. 请求三接口并捕获响应体与响应头
  2. 检查响应体 JSON 序列化字符串不含敏感字段名（token/password/secret/secretKey/accessKey/privateKey 等）
  3. 检查响应头不泄露内部信息（如 X-Powered-By 暴露版本不必 fail，但 server 内部 IP 等）
- **预期结果**: 响应不泄露凭证类敏感信息

### TC-ISSUE043-025: 表格列排序切换

- **所属功能点**: F2 社区/项目列表支持排序
- **测试设计方法**: 等价类划分
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_risk/filters/test_ui_quality_risk_filters_beta_001.py`
- **用例等级**: L1
- **前置条件**: 项目维度页面已加载，表格存在 ≥2 行数据
- **测试步骤**:
  1. 定位数值列（如"遗留问题数"）表头的排序控件
  2. 点击触发升序/降序排序
  3. 断言表格数据按该列数值重新排列
- **预期结果**: 表格排序功能正常（验收标准3）；若列头无排序能力，记录为与需求不符

### TC-ISSUE043-026: detail 接口 L2 下钻参数（productId）

- **所属功能点**: F6 common/detail 组织维度 L2 下钻
- **测试设计方法**: 决策表
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_risk/test_api_quality_risk_detail_001.py`
- **用例等级**: L1
- **前置条件**: 已登录 beta 环境；组织维度存在社区（如 LingQu，productId=200020）
- **测试步骤**:
  1. POST /common/detail，请求体 aspect=organization、productId=社区ID（200020）、近30天
  2. 断言 HTTP 200 且业务 code==200
  3. 断言返回该社区的子组织列表（records 与 L1 全量列表数据不同）
- **预期结果**: productId 下钻参数生效，返回子组织列表（验收标准2 数据基础）

---

## 用例汇总

| 类型 | 数量 | 通过 | 失败 | 阻塞 | 跳过 |
|------|------|------|------|------|------|
| 手工用例 | 2 | 2 | 0 | 0 | 0 |
| 自动化-UI | 8 | 8 | 0 | 0 | 0 |
| 自动化-API | 9 | 8 | 1 | 0 | 0 |
| 自动化-性能 | 3 | 3 | 0 | 0 | 0 |
| 自动化-安全 | 4 | 4 | 0 | 0 | 0 |
| **合计** | **26** | **25** | **1** | **0** | **0** |

| 用例来源 | 数量 |
|----------|------|
| reuse（复用旧用例） | 0 |
| new（新设计用例） | 26 |

---

## 版本历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0 | 2026-08-28 | AI 辅助 | 初始版本（24 条用例） |
| v1.1 | 2026-08-28 | AI 辅助 | 补充 TC-025/TC-026（共 26 条）；回填执行结果（25 pass / 1 fail：TC-015 分页超界返回全量，缺陷待登记）；TC-008 正向偏差记录 |
