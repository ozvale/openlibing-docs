# 测试用例 - ISSUE-111

> **模板版本**: v1.2
> **对应规则**: ai-rules/01-requirement-driven-test-design.md（第5节）、ai-rules/03-test-execution-and-report.md（第3节）

---

> **Issue编号**: ISSUE-111
> **Issue标题**: 【蓝区】【运营看板】测试运营看板-测试质量看板（遗留问题）建设
> **创建日期**: 2026-08-31
> **用例总数**: 19
> **手工用例**: 2
> **自动化用例**: 17
> **复用旧用例**: 0
> **新设计用例**: 19

### 执行信息

> 由**测试人员**填写。自动化用例的 Action 链接在此**统一填写一个**，无需每条用例重复填写。

| 字段 | 内容 |
|------|------|
| 自动化执行Action链接 | —（本地 pytest 执行：GitCode 流水线仅 main 分支注册，当前 test-0829 分支无法触发 action；执行证据已内联归档于 test_report.md「附录 A 本地执行凭证归档」） |
| 手工执行人 | 测试人员（会话用户）：TC-018/TC-019 已于 2026-08-31 人工执行并回填 |
| 执行日期 | 2026-08-31 |

---

## 用例列表

| 用例编号 | 用例标题 | 所属功能点 | 用例类型 | 用例来源 | 用例等级 | 脚本位置 | 状态 |
|----------|----------|------------|----------|----------|----------|----------|------|
| TC-ISSUE111-001 | 项目维度汇总接口契约与遗留问题数公式验证 | F3 计算口径 | auto_api | new | L0 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_statistics_001.py | active |
| TC-ISSUE111-002 | 组织维度汇总接口契约与遗留问题数公式验证 | F3 计算口径 | auto_api | new | L0 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_statistics_001.py | active |
| TC-ISSUE111-003 | 汇总卡片与明细全量求和一致性验证（项目维度） | F4 汇总-明细一致性 | auto_api | new | L0 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_consistency_002.py | active |
| TC-ISSUE111-004 | 汇总卡片与明细全量求和一致性验证（组织维度） | F4 汇总-明细一致性 | auto_api | new | L0 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_consistency_002.py | active |
| TC-ISSUE111-005 | 时间范围四档参数映射与区间单调性验证 | F5 时间范围切换 | auto_api | new | L0 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_time_range_003.py | active |
| TC-ISSUE111-006 | 明细分页参数与翻页数据不重叠验证 | F6 明细分页 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_detail_004.py | active |
| TC-ISSUE111-007 | 全量导出与明细一致性及文件结构验证 | F7 全量导出 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_export_005.py | active |
| TC-ISSUE111-008 | 趋势接口契约结构冒烟验证（两维度） | F9 趋势契约冒烟 | auto_api | new | L2 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_trend_006.py | active |
| TC-ISSUE111-009 | 关联指标字段完整性与数值格式验证 | F8 关联指标 | auto_api | new | L1 | src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_fields_007.py | active |
| TC-ISSUE111-010 | 项目维度看板菜单入口与页面展示验证 | F1 项目维度看板 | auto_ui | new | L0 | src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_project_001.py | active |
| TC-ISSUE111-011 | 组织维度看板直达 URL 加载与展示验证 | F2 组织维度看板 | auto_ui | new | L0 | src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_org_002.py | active |
| TC-ISSUE111-012 | UI 时间范围四档切换与三接口联动验证 | F5 时间范围切换(UI) | auto_ui | new | L0 | src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_time_range_003.py | active |
| TC-ISSUE111-013 | UI 卡片展示值与 API 返回一致性验证 | F8 关联指标(UI) | auto_ui | new | L1 | src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_data_consistency_004.py | active |
| TC-ISSUE111-014 | UI 明细分页翻页与导出下载验证 | F6/F7 分页导出(UI) | auto_ui | new | L1 | src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_detail_export_005.py | active |
| TC-ISSUE111-015 | 匿名与伪造 token 调用看板接口被拒绝验证 | F10 认证校验 | auto_sec | new | L1 | src/tests/openlibing/openlibing_ops/security/beta/quality_dashboard/test_security_quality_dashboard_auth_001.py | active |
| TC-ISSUE111-016 | 低权限账号调用看板接口被拒绝验证 | F11 纵向越权 | auto_sec | new | L1 | src/tests/openlibing/openlibing_ops/security/beta/quality_dashboard/test_security_quality_dashboard_vertical_002.py | active |
| TC-ISSUE111-017 | 看板接口响应体敏感信息防护验证 | F12 敏感信息防护 | auto_sec | new | L2 | src/tests/openlibing/openlibing_ops/security/beta/quality_dashboard/test_security_quality_dashboard_sensitive_003.py | active |
| TC-ISSUE111-018 | 组织维度「测试运营」菜单入口验证（待部署） | F13 组织菜单入口 | manual | new | L1 | — | active |
| TC-ISSUE111-019 | UI 交互细节验证（日期区间/弹层/筛选器） | F14 UI 交互细节 | manual | new | L2 | — | active |

> **用例来源说明**：
> - `reuse`：复用已有用例，引用已有用例编号（在详情中"引用已有用例"字段标注），不重新归档
> - `new`：新设计用例，必须按规则 5.3 归档到模块用例文件与 case_list.md
> - **模块归档编号对照**：TC-ISSUE111-001~019 → `openlibing_ops_quality_dashboard_202608_001`~`019`（归档于 `assets/docs/openlibing/openlibing_ops/test_case.md`，openlibing_ops 为历史非标准目录统一清单）
> - **复用检查结论**（2026-08-31）：已检索 `test_case.md` 全量 154 条用例，无质量风险看板 / issue-legacy / 遗留问题相关用例，全部按 new 设计

---

## 执行结果记录

> 本节由**测试人员**填写，AI 不得代填。执行结果未填写完整前，AI 不得生成测试报告（见规则 03 第4节）。

| 用例编号 | 用例类型 | 执行结果 | 缺陷issue | 备注                                                                               |
|----------|----------|------|------------|----------------------------------------------------------------------------------|
| TC-ISSUE111-001 | auto_api | pass | — | summary 8 字段契约+五级求和公式成立；R6观察: issueBugCount=25 == issueLegacyCount=25            |
| TC-ISSUE111-002 | auto_api | pass | — | 组织维度合计行 name=「合计」，公式成立，DI="397.00" 两位小数格式正确                                      |
| TC-ISSUE111-003 | auto_api | pass | — | 项目维度分页全量拉取求和与 summary 一致                                                         |
| TC-ISSUE111-004 | auto_api | pass | — | 组织维度全量求和与 summary 一致；行结构符合契约                                                     |
| TC-ISSUE111-005 | auto_api | pass | — | 四档参数映射正确；单调性成立（今日0/近7天7/近30天25/近90天66）                                           |
| TC-ISSUE111-006 | auto_api | pass | — | total=35、末页=4、首页10条、第2页10条、末页5条，跨页无重叠                                            |
| TC-ISSUE111-007 | auto_api | pass | — | 导出48行/11列/Sheet「Issue遗留问题明细」，与明细 total=48 一致（全量语义）                               |
| TC-ISSUE111-008 | auto_api | pass | — | 两维度趋势契约结构完整（dates=30，trendList 长度一致）                                             |
| TC-ISSUE111-009 | auto_api | pass | — | 字段齐全类型正确；R6观察: 项目 25/25/25.00，组织 397/397/397.00（bug==legacy 恒等，待 Issue 3.1 口径确认） |
| TC-ISSUE111-010 | auto_ui | pass | — | 菜单入口可达（测试管理→质量风险），7卡片/趋势图/明细表/分页/导出结构完整                                          |
| TC-ISSUE111-011 | auto_ui | pass | — | 组织维度直达加载正常，卡片值 397/397.00/0/0/0/0/397                                            |
| TC-ISSUE111-012 | auto_ui | pass | — | 四档切换参数正确、三接口联动重查、卡片数值单调不减                                                        |
| TC-ISSUE111-013 | auto_ui | pass | — | 7 张卡片值 == statistics summary 字段；明细首行各列 == detail records[0]                      |
| TC-ISSUE111-014 | auto_ui | pass | — | total=35 翻页生效；导出 Issue遗留问题明细_*.xlsx(5531B) 非空                                    |
| TC-ISSUE111-015 | auto_sec | pass | — | 匿名/伪造token × 4接口全部 401 正确拒绝                                                      |
| TC-ISSUE111-016 | auto_sec | pass | — | 高权限基线 4/4 可用；低权限 pub_LIBING 完整凭证调用 4 接口全部 401 正确拒绝（无纵向越权）                        |
| TC-ISSUE111-017 | auto_sec | pass | — | 4 接口响应无 token/密码/密钥/手机号/邮箱泄露                                                     |
| TC-ISSUE111-018 | manual | pass | — | 「测试运营」菜单已补充部署，入口可达组织维度质量风险看板（测试人员人工验证）              |
| TC-ISSUE111-019 | manual | pass | — | 交互细节均正常：自定义区间生效、弹层重叠不阻塞操作、维度筛选器正常、分辨率布局无错乱（测试人员人工验证） |

> **执行结果取值**：pass（通过）/ fail（失败）/ block（阻塞）/ skip（跳过）
> **填写要求**：
> - 自动化用例的 Action 链接在头部"执行信息"中统一填写，此处不重复
> - 手工用例的执行人在头部"执行信息"中统一填写，此处不重复
> - **fail 用例必须创建并填写缺陷issue**（gitcode 缺陷 issue 链接），否则不得生成报告
> - fail/block 用例必须填写 备注 说明原因

---

## 手工用例详情

### TC-ISSUE111-018: 组织维度「测试运营」菜单入口验证（待部署）

- **所属功能点**: F13 组织维度菜单入口
- **测试设计方法**: 场景法
- **用例类型**: 手工执行 (manual)
- **用例来源**: new
- **引用已有用例**: —
- **用例等级**: L1
- **前置条件**: 开发补充部署侧边栏「测试运营」菜单（当前 beta 缺失，页面探索发现#1）
- **测试步骤**:
  1. 登录 beta.openlibing.com，检查侧边栏是否出现「测试运营」菜单组
  2. 展开并点击组织维度质量风险看板菜单项
  3. 断言页面跳转至组织质量风险看板
- **预期结果**: 「测试运营」菜单存在且入口可达组织看板页面（当前阻塞：菜单未部署，仅直达 URL 可访问）

---

### TC-ISSUE111-019: UI 交互细节验证（日期区间选择/弹层重叠/维度筛选器）

- **所属功能点**: F14 UI 交互细节
- **测试设计方法**: 错误推测法
- **用例类型**: 手工执行 (manual)
- **用例来源**: new
- **引用已有用例**: —
- **用例等级**: L2
- **前置条件**: 组织与项目维度看板均可访问（高权限账号）
- **测试步骤**:
  1. 使用日期区间选择器自定义起止日期，检查查询自动刷新与结果正确
  2. 观察"今日"档位切换时日期选择弹层与控件重叠现象是否影响操作（探索发现#3）
  3. 在组织维度操作维度筛选器「全部」下拉，观察选项内容与数据刷新
  4. 分别在 1920×1080 与 1440×900 分辨率下检查两维度看板布局
- **预期结果**: 自定义区间生效且数据刷新；弹层重叠不阻塞操作（若阻塞操作记录缺陷）；维度筛选器行为正常；常见分辨率布局无错乱

---

## 自动化用例详情

### TC-ISSUE111-001: 项目维度汇总接口契约与遗留问题数公式验证

- **所属功能点**: F3 遗留问题数计算口径 / F1 项目维度
- **测试设计方法**: 等价类划分 + 边界值（零值分量）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_statistics_001.py`
- **用例等级**: L0
- **前置条件**: beta 环境已登录（高权限 p_tianyan）；项目维度近30天存在数据
- **测试步骤**:
  1. POST `/gateway/openlibing-ops/quality/dashboard/issue-legacy-statistics`，body=`{"aspect":"project","startDate":"<today-29>","endDate":"<today>","productId":"","projectId":"3"}`
  2. 校验响应 code=200 与 `data.summary` 8 个计数字段完整
  3. 断言 `issueLegacyCount == issueCriticalCount + issueMajorCount + issueMinorCount + issueTrivialCount + issueNopriorityCount`
  4. 断言各计数字段为非负整数；`items` 允许为 null
- **预期结果**: code=200；字段完整；遗留问题数等于五级计数之和（各级权重 1，与 Issue 3.1 口径一致）

---

### TC-ISSUE111-002: 组织维度汇总接口契约与遗留问题数公式验证

- **所属功能点**: F3 遗留问题数计算口径 / F2 组织维度
- **测试设计方法**: 等价类划分 + 边界值
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_statistics_001.py`
- **用例等级**: L0
- **前置条件**: 同 TC-ISSUE111-001
- **测试步骤**:
  1. POST 同接口，body=`{"aspect":"all","startDate":"<today-29>","endDate":"<today>","productId":"","projectId":""}`
  2. 校验 code=200 与 summary 字段完整性
  3. 断言五级求和公式成立
  4. 断言 `issueLegacyDiCount` 匹配两位小数字符串格式
- **预期结果**: 组织维度（aspect=all）返回合计行；公式成立；DI 格式如 "397.00"

---

### TC-ISSUE111-003: 汇总卡片与明细全量求和一致性验证（项目维度）

- **所属功能点**: F4 汇总-明细数据一致性
- **测试设计方法**: 场景法（数据流对照）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_consistency_002.py`
- **用例等级**: L0
- **前置条件**: 项目维度近30天明细 total ≥ 10（触发分页拉取）
- **测试步骤**:
  1. 调 statistics（项目维度近30天）取 summary 各字段值
  2. 循环调 `/common/detail`（page=1..N，pageSize=10）拉取全量 records
  3. 对全量 records 逐行断言五级求和公式
  4. 全量求和各计数字段与 summary 对照
- **预期结果**: 分页拉取总行数 == detail total；每行满足公式；全量求和与 summary 一致

---

### TC-ISSUE111-004: 汇总卡片与明细全量求和一致性验证（组织维度）

- **所属功能点**: F4 汇总-明细数据一致性
- **测试设计方法**: 场景法（数据流对照）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_consistency_002.py`
- **用例等级**: L0
- **前置条件**: 组织维度近30天明细 total ≥ 10
- **测试步骤**:
  1. statistics（aspect=all 近30天）取 summary
  2. detail（aspect=organization，category=issue-legacy-detail）分页拉全量
  3. 断言行字段结构（productName/projectName 计数字段，repoUrl 为 null）
  4. 逐行公式断言 + 全量求和与 summary 对照
- **预期结果**: 组织维度全量求和与 summary 一致；行结构与契约一致

---

### TC-ISSUE111-005: 时间范围四档参数映射与区间单调性验证

- **所属功能点**: F5 明细数据时间范围切换
- **测试设计方法**: 等价类划分（四档输入域）+ 边界值（startDate=today-6/29/89）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_time_range_003.py`
- **用例等级**: L0
- **前置条件**: 同 TC-ISSUE111-001
- **测试步骤**:
  1. 计算四档日期：今日(today,today)、近7天(today-6,today)、近30天(today-29,today)、近90天(today-89,today)
  2. 分别调 statistics（项目维度），断言 code=200
  3. 断言各档 issueLegacyCount ≥ 0
  4. 断言区间包含下单调不减：今日 ≤ 近7天 ≤ 近30天 ≤ 近90天
- **预期结果**: 四档参数映射正确（与探索 §5 实测一致）；遗留数单调不减（实测 0/7/25/66）

---

### TC-ISSUE111-006: 明细分页参数与翻页数据不重叠验证

- **所属功能点**: F6 明细列表分页
- **测试设计方法**: 边界值分析（page=1、末页、pageSize=10）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_detail_004.py`
- **用例等级**: L1
- **前置条件**: 项目维度近30天 total ≥ 20（至少 3 页）
- **测试步骤**:
  1. detail page=1、pageSize=10 → 断言 records 长度 =10
  2. page=2 → 断言与第 1 页记录无重叠（按行键 repoUrl 比对）
  3. 末页 → 断言 records 长度 = total - 10*(末页-1)
  4. 断言分页元数据 total/page/pageSize 回显正确
- **预期结果**: 首页满页、末页余数正确、跨页无重叠、total 与实际行数一致

---

### TC-ISSUE111-007: 全量导出与明细一致性及文件结构验证

- **所属功能点**: F7 全量导出
- **测试设计方法**: 场景法（导出流程）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_export_005.py`
- **用例等级**: L1
- **前置条件**: 项目维度近90天存在数据
- **测试步骤**:
  1. POST `/gateway/openlibing-ops/common/export/issue-legacy-detail`（近90天、项目维度、无分页参数）
  2. 校验响应为文件流，文件名匹配 `Issue遗留问题明细_*.xlsx`
  3. 解析 xlsx：Sheet「Issue遗留问题明细」，11 列结构完整
  4. 断言数据行数 == detail 近90天 total（全量语义）
- **预期结果**: 文件流正确、列结构完整、导出行数等于明细 total 不受分页限制

---

### TC-ISSUE111-008: 趋势接口契约结构冒烟验证（两维度）

- **所属功能点**: F9 趋势接口契约（页面加载依赖）
- **测试设计方法**: 等价类划分（契约结构）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_trend_006.py`
- **用例等级**: L2
- **前置条件**: 同 TC-ISSUE111-001
- **测试步骤**:
  1. POST issue-legacy-trend（aspect=project，近30天）→ 断言 `data.dates` 长度=30、`trendGroups[]` 每组含 `trendList[]` 且长度与 dates 一致
  2. aspect=organization（近30天）→ 同结构断言
- **预期结果**: 两维度趋势接口契约结构完整（数据正确性属趋势图另行设计范围，不断言）

---

### TC-ISSUE111-009: 关联指标字段完整性与数值格式验证

- **所属功能点**: F8 关联指标展示
- **测试设计方法**: 等价类划分（字段类型域）
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/quality_dashboard/test_api_quality_dashboard_fields_007.py`
- **用例等级**: L1
- **前置条件**: 同 TC-ISSUE111-001
- **测试步骤**:
  1. 两维度 statistics 响应校验 8 个字段存在（issueBugCount/issueLegacyCount/issueLegacyDiCount/五级计数）
  2. 断言计数类字段为非负整数
  3. 断言 issueLegacyDiCount 匹配 `^\d+\.\d{2}$`
  4. 记录 issueBugCount 与 issueLegacyCount 关系（R6 观察项，不断言）
- **预期结果**: 字段齐全、类型正确、DI 两位小数；R6 口径关系输出至测试日志

---

### TC-ISSUE111-010: 项目维度看板菜单入口与页面展示验证

- **所属功能点**: F1 项目维度看板入口与页面展示
- **测试设计方法**: 场景法
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_project_001.py`
- **用例等级**: L0
- **前置条件**: beta 已登录（p_tianyan）
- **测试步骤**:
  1. 展开侧边栏「测试管理」→ 点击「质量风险」
  2. 断言 URL 为 `/apps/qualityRiskProject?projectId=3`
  3. 断言 iframe（quality-risk-project）加载完成
  4. 断言 7 张汇总卡片与明细表列头、时间范围控件存在
- **预期结果**: 菜单可达、页面加载正常、卡片与表格结构完整

---

### TC-ISSUE111-011: 组织维度看板直达 URL 加载与展示验证

- **所属功能点**: F2 组织维度看板页面展示
- **测试设计方法**: 场景法
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_org_002.py`
- **用例等级**: L0
- **前置条件**: beta 已登录；组织看板存在数据
- **测试步骤**:
  1. 直达 `https://beta.openlibing.com/ops/dashboard/quality-risk-org`
  2. 若首载"暂无数据"（框架 503），刷新重试（≤3 次）
  3. 断言 7 张卡片渲染且数值非空
  4. 断言社区列表列头与维度筛选器「全部」存在
- **预期结果**: 组织看板加载成功、卡片与社区列表结构完整（菜单入口缺失单独反馈）

---

### TC-ISSUE111-012: UI 时间范围四档切换与三接口联动验证

- **所属功能点**: F5 时间范围切换（UI 层）
- **测试设计方法**: 等价类划分（四档）+ 边界值
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_time_range_003.py`
- **用例等级**: L0
- **前置条件**: 项目维度看板已打开
- **测试步骤**:
  1. iframe 内依次点击「近7天」「近30天」「近90天」「今日」（"今日"容错处理弹层）
  2. 每次切换抓包断言 statistics 请求 startDate/endDate 与映射表一致
  3. 断言每次切换触发 statistics + trend + detail 三接口重查
  4. 断言卡片数值随档位非递减
- **预期结果**: 四档切换参数正确、三接口联动重查、卡片数值与档位一致

---

### TC-ISSUE111-013: UI 卡片展示值与 API 返回一致性验证

- **所属功能点**: F8 关联指标展示（前后端层）
- **测试设计方法**: 场景法（前后端对照）
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_data_consistency_004.py`
- **用例等级**: L1
- **前置条件**: 项目维度看板已打开（默认近30天）
- **测试步骤**:
  1. 抓取页面 statistics 响应 summary
  2. 读取 7 张卡片显示数值
  3. 逐卡片断言 UI 值 == 接口对应字段值
  4. 抓取 detail 响应，断言表格首行各列文本 == records[0] 对应字段
- **预期结果**: 前端展示与接口数据完全一致

---

### TC-ISSUE111-014: UI 明细分页翻页与导出下载验证

- **所属功能点**: F6 分页（UI 层）/ F7 导出（UI 层）
- **测试设计方法**: 边界值分析 + 场景法
- **用例类型**: 自动化-UI (auto_ui)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/ui/beta/quality_dashboard/test_ui_quality_dashboard_detail_export_005.py`
- **用例等级**: L1
- **前置条件**: 项目维度看板已打开；明细 total > 10
- **测试步骤**:
  1. 断言分页组件（10条/页）与总数显示
  2. 点击下一页 → 断言表格数据刷新且与第 1 页不同
  3. 点击「导出」→ 捕获下载事件
  4. 断言下载文件名匹配 `Issue遗留问题明细_*.xlsx` 且文件非空
- **预期结果**: 分页翻页刷新正确；导出触发 xlsx 下载且文件非空

---

### TC-ISSUE111-015: 匿名与伪造 token 调用看板接口被拒绝验证

- **所属功能点**: F10 看板接口认证校验
- **测试设计方法**: 错误推测法
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/quality_dashboard/test_security_quality_dashboard_auth_001.py`
- **用例等级**: L1
- **前置条件**: SECURITY_ENABLED=true 且 test 环境；4 个看板接口契约已知
- **测试步骤**:
  1. 无任何凭证调用 4 个接口
  2. 携带伪造 token（随机字符串）调用同样 4 个接口
  3. 按 assert_denied 语义断言：401/403 通过；200+code==200 失败
- **预期结果**: 匿名与伪造 token 均被服务端拒绝

---

### TC-ISSUE111-016: 低权限账号调用看板接口被拒绝验证

- **所属功能点**: F11 看板接口纵向越权校验
- **测试设计方法**: 错误推测法（双身份对照）
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/quality_dashboard/test_security_quality_dashboard_vertical_002.py`
- **用例等级**: L1
- **前置条件**: 低权限账号 pub_LIBING（纯低权限）；高权限 p_tianyan 作基线
- **测试步骤**:
  1. 高权限调用 4 个接口 → 断言 200+code=200（基线可用）
  2. 低权限以同参数调用 4 个接口
  3. 断言：401/403 通过；200+code==200 失败（越权，视为缺陷）
- **预期结果**: 低权限被拒绝、高权限基线正常

---

### TC-ISSUE111-017: 看板接口响应体敏感信息防护验证

- **所属功能点**: F12 看板接口敏感信息防护
- **测试设计方法**: 错误推测法
- **用例类型**: 自动化-安全 (auto_sec)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/security/beta/quality_dashboard/test_security_quality_dashboard_sensitive_003.py`
- **用例等级**: L2
- **前置条件**: 高权限正常调用 4 个接口取响应
- **测试步骤**:
  1. 收集 4 个接口响应文本
  2. 扫描敏感模式：token/password/secret/key/手机号/邮箱泄漏（业务数据 repoUrl/社区名不计入）
  3. 校验响应头无异常凭证回显
- **预期结果**: 响应体不含凭证/密钥/个人敏感信息

---

## 用例汇总

| 类型 | 数量 | 通过 | 失败 | 阻塞 | 跳过 |
|------|------|------|------|------|------|
| 手工用例 | 2 | 2 | 0 | 0 | 0 |
| 自动化-UI | 5 | 5 | 0 | 0 | 0 |
| 自动化-API | 9 | 9 | 0 | 0 | 0 |
| 自动化-性能 | 0 | 0 | 0 | 0 | 0 |
| 自动化-安全 | 3 | 3 | 0 | 0 | 0 |
| **合计** | **19** | **19** | **0** | **0** | **0** |

| 用例来源 | 数量 |
|----------|------|
| reuse（复用旧用例） | 0 |
| new（新设计用例） | 19 |

---

## 版本历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0 | 2026-08-31 | AI Agent | 初始版本（19 用例：9 API + 5 UI + 3 安全 + 2 手工，全部 new） |
| v1.1 | 2026-08-31 | AI Agent（经测试人员确认授权） | 回填执行结果：自动化 17/17 pass（本地 pytest，beta 环境）；TC-018 block（菜单未部署）；TC-019 待人工执行 |
| v1.2 | 2026-08-31 | 测试人员 + AI Agent | 手工用例执行完毕：TC-018 pass（菜单已部署入口可达）、TC-019 pass（交互细节正常）；19/19 全部通过 |
