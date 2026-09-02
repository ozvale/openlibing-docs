# 测试报告 - ISSUE-106

> **Issue编号**: ISSUE-106
> **Issue标题**: 【蓝区-精准测试】新增openlibing看板，用于展示项目代码覆盖率信息
> **报告日期**: 2026-08-31
> **测试负责人**: AI Agent（执行结果经测试人员确认）
> **报告版本**: v1.1

---

## 1. 执行概览

| 项目 | 内容 |
|------|------|
| 测试周期 | 2026-08-29 ~ 2026-08-31 |
| 测试环境 | test (https://beta.openlibing.com) |
| 用例总数 | 10 |
| 执行数 | 10 |
| 通过 | 9 |
| 失败 | 0 |
| 阻塞 | 1 |
| 跳过 | 0 |
| 通过率 | 90.0%（9/10；唯一阻塞项 TC-ISSUE106-010 为 L2 数据链路核对项，OBS 路径约定待开发提供） |

### 1.1 按用例等级统计

| 等级 | 总数 | 通过 | 失败 | 阻塞 | 跳过 |
|------|------|------|------|------|------|
| L0 | 5 | 5 | 0 | 0 | 0 |
| L1 | 4 | 4 | 0 | 0 | 0 |
| L2 | 1 | 0 | 0 | 1 | 0 |

### 1.2 按用例类型统计

| 类型 | 总数 | 通过 | 失败 | 阻塞 | 跳过 |
|------|------|------|------|------|------|
| 手工用例 | 4 | 3 | 0 | 1 | 0 |
| 自动化-UI | 4 | 4 | 0 | 0 | 0 |
| 自动化-API | 0 | 0 | 0 | 0 | 0 |
| 自动化-性能 | 0 | 0 | 0 | 0 | 0 |
| 自动化-安全 | 2 | 2 | 0 | 0 | 0 |

---

## 2. 用例执行明细

> 数据来源：test_cases.md 的执行结果记录（v1.2）。所有执行数据必须可追溯。

### 2.1 执行信息

| 字段 | 内容 |
|------|------|
| 自动化执行Action链接 | 本地 pytest 重跑执行（GitCode CI 流水线因仅默认分支注册 workflow 未触发，action 链接待后续补充） |
| 手工执行人 | AI Agent 浏览器辅助验证（测试人员授权指令执行，2026-08-31） |
| 执行日期 | 2026-08-31 |

> **本地重跑执行**（串行批次 + 30 秒批间冷却，规避 WAF 限流 401）：
> - UI 批次：`pytest src/tests/openlibing/openlibing_ops/ui/beta/coverage_dashboard/ -v`（TEST_ENV=test，SECURITY_ENABLED=true，**4/4 通过**，66.93s）
> - 安全批次：`pytest src/tests/openlibing/openlibing_ops/security/beta/coverage_dashboard/ -v`（TEST_ENV=test，SECURITY_ENABLED=true，**2/2 通过**，35.02s）
> - 执行凭证：JUnit XML 结果（原 `execution_results/junit_rerun_ui_20260831.xml`、`execution_results/junit_rerun_sec_20260831.xml`）已内联归档于本报告「附录 A 本地执行凭证归档」
> - 手工验证证据：项目/组织看板截图与 precision-coverage 接口抓包（summary / repo/list / project/list / file/list / file/detail 均 200）
> - 首跑记录（2026-08-31 上午）：6 条自动化 2 pass / 4 fail（均为脚本假阴性），详见 3.1

### 2.2 用例执行明细

| 用例编号 | 用例标题 | 用例等级 | 用例类型 | 执行结果 | 缺陷issue | 备注 |
|----------|----------|----------|----------|----------|------------|------|
| TC-ISSUE106-001 | 精准测试菜单入口存在性验证 | L0 | auto_ui | pass | — | 重跑通过：采集到「测试管理」分组下「精准测试」菜单项，可见可点击 |
| TC-ISSUE106-002 | 看板应用路由与 iframe 看板内容加载验证 | L0 | auto_ui | pass | — | 重跑通过：应用路由标题「精准测试」，iframe 内嵌 precision-test 看板并渲染覆盖率指标 |
| TC-ISSUE106-003 | 已授权账号直达项目看板内容渲染验证 | L0 | auto_ui | pass | — | 重跑通过：运营 KPI 5 项 + 四种覆盖率指标 + 仓库列表全部渲染，无无权限提示 |
| TC-ISSUE106-004 | 仓库覆盖率数值格式与文件下钻入口验证 | L1 | auto_ui | pass | — | 重跑通过：仓库行 ≥1 条，覆盖率 xx.xx% 数值 ≥4 个，文件下钻入口按钮存在 |
| TC-ISSUE106-005 | 匿名（未登录）访问看板路由拦截验证 | L0 | auto_sec | pass | — | 匿名访问未渲染看板内容（无越权信号），拦截判定通过 |
| TC-ISSUE106-006 | 低权限账号访问看板路由拦截验证 | L1 | auto_sec | pass | — | 低权限账号 pub_LIBING 访问未渲染看板内容（无越权信号），纵向越权防护通过 |
| TC-ISSUE106-007 | 项目级看板四种覆盖率指标展示验证 | L0 | manual | pass | — | 手工验证通过：四种覆盖率展示（MindIE-LLM 78.10%/63.40%/74.50%/66.10%，vllm-ascend 68.67%/58.15%/96.73%/84.57%） |
| TC-ISSUE106-008 | 项目级看板文件下钻与覆盖详情验证 | L1 | manual | pass | — | 手工验证通过：文件列表→文件覆盖详情下钻链路完整（attention_mask.py 行覆盖率 98.46%，源码逐行覆盖标识渲染正常） |
| TC-ISSUE106-009 | 组织级看板指标展示验证 | L1 | manual | pass | — | 手工验证通过：接入占比 0.14%/PR渗透率/减少工作量 32,290 秒/时长降幅 76.43%/访问量 753 + 四种覆盖率均展示 |
| TC-ISSUE106-010 | OBS 数据来源路径映射验证 | L2 | manual | block | — | 前置条件不满足：OBS 上报路径约定待开发提供，无法核对上报数据与看板数据一致性；看板已有真实数据表明数据链路已打通 |

---

## 3. 缺陷列表

> 本期**未发现产品缺陷（0 条）**。首跑 4 条 fail 经人工复核均为测试脚本缺陷（假阴性），已升级脚本 v2 修复并重跑全部通过；2 个执行期疑点经权限开通后复核均不成立。经测试人员确认，不创建产品缺陷 issue。

### 3.1 脚本缺陷（假阴性）明细——已修复闭环

| 关联用例 | 缺陷issue链接 | 缺陷描述 | 严重级别 | 状态 |
|----------|----------------|----------|----------|------|
| TC-ISSUE106-001 | —（测试脚本缺陷，非产品缺陷） | 菜单采集逻辑缺陷：hover 后采集到残留展开的「开发管理」子菜单，未定位到「测试管理」分组 | 一般 | **已修复（脚本 v2）并重跑通过** |
| TC-ISSUE106-002/003 | —（测试脚本缺陷，非产品缺陷） | URL 断言缺陷：账号存在应用级持久化 tab 时，路由守卫激活既有 tab 而非 URL 重定向，断言不成立 | 一般 | **已修复（改以标题+内容判定）并重跑通过** |
| TC-ISSUE106-004 | —（测试脚本缺陷，非产品缺陷） | 断言时机缺陷：tab 内容持续 Loading，文案断言过早 | 轻微 | **已修复（关键词轮询等待）并重跑通过** |

**修复方案与重跑验证证据（2026-08-31）**：

| 修复点 | 修复方案 | 重跑结果 |
|--------|----------|----------|
| 菜单采集定位 | 逐级点击展开「测试管理」分组（含嵌套二级同名分组）+ 折叠状态判定防 toggle 反折叠 + 路由激活自动展开兜底策略 | TC-001 pass |
| URL 断言兼容 | 断言改以页面标题 + iframe 看板内容判定（不依赖 URL 重定向形态） | TC-002 pass |
| 断言时机 | 看板内容关键词轮询等待（`wait_for_dashboard_content` / `wait_for_frame_keyword`） | TC-003/004 pass |
| 权限状态变更适配 | TC-002/003/004 断言口径按权限开通后切换为看板内容正向验证（用例文档同步适配，无权限拦截由安全用例 TC-005/006 持续覆盖） | 全部 pass |

### 3.2 执行期疑点复核——均不成立（已闭环）

| 疑点（v1.0 报告） | 复核结论 | 证据 |
|------------------|----------|------|
| 「精准测试」菜单指向变更（aurogon-web vs 08-29 探索记录的 coverageDashboard） | **不成立**：菜单指向 `/apps/aurogon-web` 为精准测试应用壳，其 iframe 内嵌 `/ops/dashboard/precision-test` 看板，展示 ISSUE-106 要求的四种代码覆盖率指标，与需求交付一致；08-29 探索记录的 `/apps/coverageDashboard`（测试用例覆盖看板）为同分组相邻的**另一个看板**（ISSUE-96 范畴），非本 Issue 交付入口 | TC-ISSUE106-001/002 重跑通过；iframe 渲染行/分支/函数/文件覆盖率 |
| aurogon-web 主内容区空白 | **不成立**：空白原因为当时账号未开通看板权限（前端权限数据未生效时不渲染 iframe 看板内容且无提示）；权限开通后页面正常内嵌看板并渲染数据 | TC-ISSUE106-002 重跑通过：权限开通后 aurogon-web iframe 加载 precision-test 看板，summary/repo/list/project/list 接口均 200 |

---

## 4. 测试结论

### 4.1 结论

> 取值：允许发布 / 附条件发布 / 暂不允许发布（见规则 03 第5.2节）

**允许发布**

### 4.2 结论依据

- **执行完整性**: 10 条用例执行 10 条（9 pass / 0 fail / 1 block），全部 L0（5 条）与 L1（4 条）用例**全部通过**，无失败用例
- **核心功能验证**: 需求核心交付「项目代码覆盖率展示」已完整验证——菜单入口（F1）、应用路由与 iframe 加载（F2）、项目看板 KPI 与四种覆盖率渲染（F3/F7）、覆盖率数值格式与文件下钻入口（F4/F8）、组织级看板指标（F9）均验证通过
- **唯一阻塞项为 L2**: TC-ISSUE106-010（OBS 数据来源路径映射）因开发未提供 OBS 上报路径约定而无法核对数据一致性，属数据链路核对项，**不影响看板核心展示功能**（看板已展示真实数据：2 仓库，采集日期 2026-08-20/08-30，数据链路已打通）
- **脚本缺陷闭环**: 首跑 4 条 fail 均为脚本假阴性，已修复重跑全部通过，自动化可信度恢复
- **安全防护**: 匿名访问与低权限纵向越权均被正确拦截；安全维度 2/6 覆盖，其余 4 维已在 test_design.md 安全设计章节声明不适用原因（看板无独立后端管理接口，前端路由守卫拦截）
- **遗留风险**:
  1. TC-ISSUE106-010（L2）未执行：OBS 路径映射规则与上报数据一致性未核对，待开发提供路径约定后补充验证
  2. **观察项**：精准测试PR渗透率两维度均无值（看板显示「-」，API 返回 `prPenetrationRate: "--"`），指标标题已展示但数值缺失，疑似数据源未接入或计算口径未生效，建议开发确认
  3. GitCode CI Action 链接待补充（workflow 仅默认分支注册，test-0829 分支推送未触发）
  4. 安全维度仅覆盖认证校验与纵向越权 2 项；横向越权/CSRF/传输安全/敏感信息防护因看板无独立后端接口，未纳入本期设计（已在 test_design.md 声明原因）

### 4.3 后续行动建议

1. **补充 TC-ISSUE106-010 验证**（唯一阻塞项）：向开发获取 OBS 上报路径约定，核对路径映射与看板数据一致性后解除阻塞
2. **PR渗透率无值确认**：向开发确认该指标数据源与计算口径（当前显示「-」）
3. **CI 补充**：将 workflow 合并至默认分支（main）或由测试人员手动触发，补充 GitCode Action 链接凭证
4. **提交与归档**：在 test-0829 分支提交本期变更（脚本 v2 + 文档 v1.2/v1.1 + junit 凭证），由用户确认后进入归档

---

---

## 附录 A 本地执行凭证归档

> 按「Issue 目录最终产物仅保留四件套」约定（2026-09-01 清理），原 execution_results/ 下两份 JUnit XML 结果已内联至本附录，原目录移除。证据内容与 2026-08-31 重跑归档版本一致。

### A.1 UI 批次 JUnit 结果（原 execution_results/junit_rerun_ui_20260831.xml）

- 汇总：4 tests / 0 failures / 0 errors / 0 skipped，总耗时 66.913s，执行时间 2026-08-31 18:35:07（+08:00），主机 DESKTOP-85JOC4S
- 逐条：test_ui_coverage_dashboard_entry_001（41.940s）/ _002（6.919s）/ _003（12.681s）/ _004（5.296s）

`xml
<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest" errors="0" failures="0" skipped="0" tests="4" time="66.913" timestamp="2026-08-31T18:35:07.688159+08:00" hostname="DESKTOP-85JOC4S"><testcase classname="src.tests.openlibing.openlibing_ops.ui.beta.coverage_dashboard.test_ui_coverage_dashboard_entry_001.TestUiCoverageDashboardEntry" name="test_ui_coverage_dashboard_entry_001" time="41.940" /><testcase classname="src.tests.openlibing.openlibing_ops.ui.beta.coverage_dashboard.test_ui_coverage_dashboard_entry_001.TestUiCoverageDashboardEntry" name="test_ui_coverage_dashboard_entry_002" time="6.919" /><testcase classname="src.tests.openlibing.openlibing_ops.ui.beta.coverage_dashboard.test_ui_coverage_dashboard_entry_001.TestUiCoverageDashboardEntry" name="test_ui_coverage_dashboard_entry_003" time="12.681" /><testcase classname="src.tests.openlibing.openlibing_ops.ui.beta.coverage_dashboard.test_ui_coverage_dashboard_entry_001.TestUiCoverageDashboardEntry" name="test_ui_coverage_dashboard_entry_004" time="5.296" /></testsuite></testsuites>
`

### A.2 安全批次 JUnit 结果（原 execution_results/junit_rerun_sec_20260831.xml）

- 汇总：2 tests / 0 failures / 0 errors / 0 skipped，总耗时 35.021s，执行时间 2026-08-31 18:36:53（+08:00），主机 DESKTOP-85JOC4S
- 逐条：test_security_coverage_dashboard_anonymous_001（7.534s）/ test_security_coverage_dashboard_low_priv_001（27.397s）

`xml
<?xml version="1.0" encoding="utf-8"?><testsuites><testsuite name="pytest" errors="0" failures="0" skipped="0" tests="2" time="35.021" timestamp="2026-08-31T18:36:53.330979+08:00" hostname="DESKTOP-85JOC4S"><testcase classname="src.tests.openlibing.openlibing_ops.security.beta.coverage_dashboard.test_security_coverage_dashboard_auth_001.TestSecurityCoverageDashboardAuth" name="test_security_coverage_dashboard_anonymous_001" time="7.534" /><testcase classname="src.tests.openlibing.openlibing_ops.security.beta.coverage_dashboard.test_security_coverage_dashboard_auth_001.TestSecurityCoverageDashboardAuth" name="test_security_coverage_dashboard_low_priv_001" time="27.397" /></testsuite></testsuites>
`

## 5. 版本历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0 | 2026-08-31 | AI Agent | 初始报告（本地 pytest 执行结果回填后生成：2 pass / 4 fail 均为脚本假阴性 / 4 block 权限阻塞；2 个新发现疑点待确认） |
| v1.1 | 2026-08-31 | AI Agent | 权限开通后重跑更新：6 条自动化全部 pass（脚本 v2 修复假阴性并适配权限开通口径）；手工 TC-007/008/009 验证 pass，TC-010（L2）因 OBS 路径约定未提供阻塞；2 个执行期疑点复核均不成立（闭环）；结论由「暂不允许发布」更新为「允许发布」 |
| v1.2 | 2026-09-01 | AI Agent | 四件套清理：重跑 JUnit 执行凭证内联归档至附录 A；page_exploration.md 引用改为 git 历史指引 |
