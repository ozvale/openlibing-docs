# 测试策略 — issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化

> **模板版本**: v3.5
> **对应规则**: AGENTS.md「规则 01 — 需求驱动的测试策略与设计」+「月度版本工作模式」
> **使用说明**: 由 `python src/utils/version_tracker.py new-issue` 自动生成到
> `assets/testcase_pro/IPD管理控制与测试仿真/05_202610/20261019/issue_205_【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化/测试过程数据/`；
> 过程文档目录承载四件套归档（测试策略 / 测试设计 / case_list.md / 测试报告.md），
> 另含 需求串讲 / 测试反串讲 / 版本历史；用例本体为 issue 目录内逐用例 `.md`，
> 执行结果见同目录 `测试报告.md` 与版本目录 `执行记录跟踪表.xlsx`

---

> 团队：IPD管理控制与测试仿真 | 月度：202610 | 版本发布日期：20261019 | issue 编号：205 | issue 标题：【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化
> 文档状态：已执行（v1.4：2026-10-20 beta 环境核查后 pytest 自动化执行 5 通过 / 6 阻塞，测试结论「附条件发布」，见 test_report.md） | 创建日期：2026-10-14 | 负责人：AI 辅助测试

> **⚠ 用例范围收敛说明（2026-10-17，版本历史 v1.3）**：经用户确认，本 issue 用例集**严格以用户手工维护的 测试设计脑图.xmind 为唯一口径**。用户已于 2026-10-17 将脑图重写为 GitHub PR门禁看板口径 **11 个用例节点**（代码仓指标汇总表 7 / 代码仓指标明细表 2 / 明细表下钻 workflow 详情 2），逐字生成 TC-ISSUE205-065~~075（01_系统测试/数字化运营，auto_ui）。
> 此前各版用例（TC-ISSUE205-001~~024 早期 24 条、TC-ISSUE205-025~064 三看板 40 条）均已按用户决定**整批移除**（用例编号不回收不复用）；下文 §2.2/§2.3/§2.4 中引用的上述编号及 FP-xx 追溯矩阵、风险/待串讲项中的对应引用随之**全部退役**，仅保留为需求背景参考。
> 当前生效用例清单以 issue 级 `case_list.md`（11 条）与 `执行记录跟踪表.xlsx`（11 行）为准。

---

## 1. 测试策略

> 业务输入**唯一来源**为 gitcode issue 内的开发设计文档，AI/测试人员必须实际读取链接，禁止超出文档范围发散。

### 1.1 Issue 信息

| 字段       | 内容                                                                           |
| ---------- | ------------------------------------------------------------------------------ |
| Issue编号  | 205                                                                            |
| Issue标题  | 【蓝区】【运营看板】GitHub PR门禁看板增加PR门禁E2E执行时长、下钻能力增强等优化 |
| 关联需求   | https://gitcode.com/openlibing/openlibing-ops/issues/205                       |
| 所属团队   | IPD管理控制与测试仿真                                                          |
| 所属微服务 | openlibing-ops                                                                 |
| 所属模块   | 数字化运营 / GitHub PR门禁看板                                                 |
| 负责人     | AI 辅助测试                                                                    |
| 创建日期   | 2026-10-14                                                                     |

### 1.2 需求摘要

> 从开发设计文档提炼，**禁止超出文档范围**。

**业务背景**：根据和业务交流识别 GitHub PR门禁看板优化内容；配合业务实际作业质量过程进行看板调整，提升看板运营能力。

**需求原文功能点**（涉及看板：openlibing-数字化运营-GitHub PR门禁看板，含 workflow 运行明细、PR 明细下钻）：

| #   | 需求条目                                                                                             | 场景                  |
| --- | ---------------------------------------------------------------------------------------------------- | --------------------- |
| 1   | workflow运行明细页面增加 job 任务下钻展示能力、增加 job 任务统计时长                                 | workflow 运行明细下钻 |
| 2   | 根据成功失败状态筛选时，CI E2E 时间需要跟随变化                                                      | 主表状态筛选          |
| 3   | 「CI E2E时长(min)」改为「PR门禁E2E执行时长」且区分 P50 P90 P95                                       | 主表列                |
| 4   | 默认隐藏「PR闭环时长」                                                                               | 主表列                |
| 5   | 「门禁E2E执行时长」支持 平均、P90、P95 数据展示，默认展示 P90 数据                                   | 主表列                |
| 6   | 「PR闭环时长」下钻表格中「PR闭环时长」「PR合入时长」默认不展示                                       | PR 明细表             |
| 7   | PR 合入时长(min) 有负值：计算 PR 合入时长时去掉「push」类型 workflow，防止出现负值                   | PR 明细 / 主表        |
| 8   | 「门禁E2E执行时长」下钻表格中增加「门禁E2E执行时长」字段；workflow 相关指标增加说明                  | PR 明细表 / 指标说明  |
| 9   | 增加「PR总数」字段，支持跳转（跳转结果和现在的 PR E2E 时长一样）；「PR E2E时长」不支持跳转、默认隐藏 | 主表列 / 跳转         |

> 注：需求原文「二」节小条编号缺 2)（原文如此）；条目 3（标题"区分 P50 P90 P95"）与条目 5（"平均、P90、P95、默认 P90"）分位集合表述不一致，见 §2.3 待确认项 #1。

**代码走查映射**（后端 `origin/release_20261019` + 前端 `origin/beta`，2026-10-14 走查；两仓均为**改造前**代码）：

| 需求条目              | 前端落点                                                                                                                                                                                                                                              | 后端落点                                                                                                                                                                                                                                                                                       | 接口 / category                                                                                               |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------- |
| 条目1（job 下钻）     | `dashboard/github/components/workflow-run-drawer.vue` + `config.ts` `githubWorkflowRunColumns`（运行ID runId / 关联PR relatePr / 执行时间 execTime / 状态 status / E2E时长 e2eMin / 排队时长 queueMin / 执行时长 execMin，现无 job 级列）             | `OpsGithubWorkflowRunDetailResp`（runId/htmlUrl/relatePr/relatePrUrls/execTime/status/e2eMin/queueMin/execMin）；`DwiRdEfcPrWorkflowRun` 无 job 级数据（需新建数据源）                                                                                                                         | POST /common/detail，category=`github-workflow-run`；job 下钻需新增接口/列（待定稿）                          |
| 条目2（状态联动）     | `github-dashboard.vue` status 下拉（成功/失败）→ 传 `status` 参数                                                                                                                                                                                     | `OpsGithubMainDetailReq.status`；`queryMain` 中 status 过滤仅作用 workflow 聚合，`pr_ci_e2e_agg`（AVG(max_duration)/60）**无 status 过滤** = 联动缺口                                                                                                                                          | POST /common/detail，category=`github-pr-workflow-main`；POST /ops/github/chart（`OpsGithubChartReq.status`） |
| 条目3/5（改名+分位）  | `config.ts:73` `ciE2eTime` 现列名「门禁E2E执行时长(min)」（disabled 固定列）                                                                                                                                                                          | `OpsGithubMainDetailResp.ciE2eTime`；SQL 仅平均口径；主表已有 `PERCENTILE(...,0.5/0.9/0.95)` 先例（workflowE2eP50/P90、queueP50/90/95、execP50/90/95）                                                                                                                                         | POST /common/detail，category=`github-pr-workflow-main`                                                       |
| 条目4（PR闭环隐藏）   | `config.ts:66` `prE2eDuration`「PR闭环时长(min)」（disabled 固定列，现 defaultShow）                                                                                                                                                                  | `OpsGithubMainDetailResp.prE2eDuration`（@ExcelProperty「PR闭环时长(min)」）                                                                                                                                                                                                                   | category=`github-pr-workflow-main`                                                                            |
| 条目6（PR明细默认列） | `config.ts` `githubPrDetailColumns`：`prE2eTime`「PR闭环时长(min)」(:208)、`prMergeTime`「PR合入时长(min)」(:211) 均 defaultShow:true → 需默认不展示                                                                                                  | `OpsGithubPrDetailResp.prE2eTime/prMergeTime`                                                                                                                                                                                                                                                  | POST /common/detail，category=`github-pr-detail`                                                              |
| 条目7（负值）         | PR 明细「PR合入时长」+ 主表 `prMergeDuration`「PR合入时长(min)」                                                                                                                                                                                      | `queryPrDetail` `pr_merge_time=TIMESTAMPDIFF(SECOND,MAX(pw.run_end_time),p.merged_at)/60`；`queryMain` `pr_merge_agg`（pwmax2=MAX(run_end_time) GROUP BY repo_url,number）；负值源=push 触发 workflow 在 merged_at 后结束；`DwiRdEfcPrWorkflowRun` **无 event/trigger 字段**（过滤口径待定稿） | category=`github-pr-detail` / `github-pr-workflow-main`                                                       |
| 条目8（新字段+说明）  | `githubPrDetailColumns` `gateAvgTime`「Workflow执行平均时长(min)」(:209)、`gateSingleTime`「Workflow执行最长时长(min)」(:210)；`metric-tips.ts` `githubMetricTips{prE2eDuration,ciE2eTime,e2ePassRate}` + `metricCode{code:10067}`（prMergeDuration） | `OpsGithubPrDetailResp`（新增「门禁E2E执行时长」字段待命名；现 gateAvgTime/gateSingleTime=SQL AVG(duration)/MAX(duration)）                                                                                                                                                                    | category=`github-pr-detail`                                                                                   |
| 条目9（PR总数/跳转）  | `github-table.vue:46-51` `prE2eDuration` 值可点击 → `openPrDetail`(:134) → `pr-detail-drawer`（现跳转）；`runCount` → `openWorkflowRun`                                                                                                               | `queryMain` 现无 prCount（需从 `sdi_rd_efc_pr_info_raw_github` 计数；命名先例 `ProjectDetailResp.prCount`）                                                                                                                                                                                    | category=`github-pr-workflow-main`                                                                            |
| 横切（导出）          | `api/dashboard/github.ts` `exportGithubMain/exportGithubPrDetail/exportGithubWorkflowRun`                                                                                                                                                             | `OpsGithubController:128/144`（POST /ops/github/export/main\|pr-detail\|workflow-run），导出列由各 Resp `@ExcelProperty` 驱动；`OpsGithubService.EXPORT_MAX_ROWS=100000`                                                                                                                       | POST /ops/github/export/*                                                                                     |

**关键既有实现事实**：

- 主表 `githubMainColumns` 固定列（disabled）：代码仓 repoName、PR闭环时长(min) prE2eDuration、门禁E2E执行时长(min) ciE2eTime、Workflow名称 workflowName、运行次数 runCount、PR合入时长(min) prMergeDuration、E2E达标率 e2ePassRate；`SPAN_PROPS` 合并单元格含 repoName/prE2eDuration/ciE2eTime/prMergeDuration/e2ePassRate
- 主表可配列：Workflow E2E P50/P90（workflowE2eP50/P90）、排队时长(min) 组 P50/P90/P95、执行时长(min) 组 P50/P90/P95
- PR 明细 `githubPrDetailColumns` 现有列：PR编号 prNumber / 创建时间 createTime / 合入时间 mergeTime / PR标题 title / 状态 status（已合入 merged·开启中 open·已关闭 closed）/ 是否强制合入 forceMerge / 门禁是否成功 gateSuccess / PR闭环时长(min) prE2eTime / Workflow执行平均时长(min) gateAvgTime / Workflow执行最长时长(min) gateSingleTime / PR合入时长(min) prMergeTime / 源分支 sourceBranch / 目标分支 targetBranch / 创建人 creator（pipeStartTime @ExcelIgnore）
- workflow 运行明细 `githubWorkflowRunColumns` 状态枚举：success/failure/skipped/cancelled/startup_failure/action_required
- 图表：POST /ops/github/chart，chartType=`queue`/`exec`/`prE2e`（`OpsGithubChartResp.queueP50..execP95/prE2eData`；`github-chart.vue:94`「PR E2E总时长(min)」）
- 指标说明现状：`metric-tips.ts`（prE2eDuration「Σ每个PR的 E2E执行时长 / 当期统计周期内已合入的PR总数」、ciE2eTime「各个 CI E2E时长的平均值 / Σ各个CI E2E执行时长 / CI总数」、e2ePassRate「CI E2E达成目标时长的比例」）；PR合入时长走指标字典 metricCode code=10067
- E2E 达标率配置（本次不涉改）：GET /ops/github/e2e-target + `e2e-config-modal.vue`「PR门禁E2E达标时长配置」
- category 枚举（`DetailCommonEnum`）：`github-pr-workflow-main` / `github-pr-detail` / `github-workflow-run` 均已存在，本次 job 下钻可能新增接口或 category
- 状态筛选主链路：`github-dashboard.vue` `status` 传入 `OpsGithubMainDetailReq.status` 与 `OpsGithubChartReq.status`

**异常场景**：无 job 数据的 workflow run / 无 PR 的仓空态兜底（既有 TC-ISSUE136-013 空态容错基线）；旧用户列设置 localStorage 记忆含将隐藏列 prop（prE2eDuration/prE2eTime/prMergeTime）时的兼容降级；PR 合入时长历史负值样本回归；status 筛选后 ciE2e 聚合无除零/空值异常。

### 1.3 测试目标

1. 验证主表「门禁E2E执行时长」列改造符合定稿：改名（PR门禁E2E执行时长/门禁E2E执行时长）、平均/P90/P95（或 P50/P90/P95）分位展示、默认展示 P90
2. 验证「PR闭环时长」主表默认隐藏且不再支持跳转，列设置可恢复展示
3. 验证「PR总数」列新增、默认展示、点击跳转 PR 明细（与原 PR E2E 时长跳转一致）
4. 验证按成功/失败状态筛选时 CI E2E 时间（门禁E2E执行时长）跟随变化，且与接口/数仓口径一致
5. 验证 workflow 运行明细新增 job 任务下钻与 job 统计时长；PR 明细新增「门禁E2E执行时长」字段、workflow 相关指标说明（tooltip）可查看
6. 验证 PR 合入时长计算排除 push 类型 workflow 后全行无负值（主表 + PR 明细）
7. 验证 PR 明细「PR闭环时长」「PR合入时长」默认不展示；导出列与定稿一致
8. 涉改接口响应时间不劣化，安全维度不引入新风险

### 1.4 测试范围

| 测试类型    | 是否覆盖 | 说明                                                                                                                                                                                                                                          |
| ----------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| UI功能测试  | 是       | 覆盖主表列结构/默认展示/跳转、状态筛选联动、workflow 运行明细 job 下钻、PR 明细列调整与说明、负值清零、空态兜底（new 11 条 + 易用性复用 6 条）                                                                                                |
| API接口测试 | 是       | 3 个 detail category + chart + job 下钻接口字段结构断言、状态联动、PR合入口径、分位口径 Doris 对拍、导出列断言（new 8 条）                                                                                                                    |
| DFX测试     | 是       | 涉改端点响应时间基线断言（new 1 条；模式复用既有响应时间用例）                                                                                                                                                                                |
| 安全测试    | 是       | 6 维度：认证 ✓ / 横向越权 ✓ / 传输安全 ✓ / 敏感信息 ✓（new 4 条）；纵向越权 豁免（运营看板为团队级只读看板，登录用户可见性一致，无角色分级数据面，评审确认）；CSRF 豁免（涉改接口均为只读查询/导出下载，无状态变更语义，与 issue_206 同口径） |

### 1.5 测试策略

- 手工测试：无独立手工用例；6 条易用性复用用例（手工）在串讲时人工评审确认覆盖新列结构下的列设置/记忆/列宽/指标说明体验
- 自动化测试：24 条 new 用例全部自动化（auto_ui 11 / auto_api 8 / auto_perf 1 / auto_sec 4）；脚本位置 `src/automation/ipd-management/{ui|api|perf|sec}/digital_operations/github_pr_gate_dashboard/beta/`（目录不随版本树移动，登记在用例 .md「脚本位置」字段）；页面对象复用扩展 `src/pages/ipd_management/ui/operations_maintenance/github_pr_gate_dashboard/github_pr_gate_dashboard_page.py`
- 断言隔离策略：API 用例通过**字段映射表**引用后端字段名（新增字段命名待定稿，见 §2.3 #6），命名定稿时仅改映射表不改用例；UI 列断言用**表头文案 + defaultShow 状态**而非固定列数，避免列数波动导致脆弱断言；PR合入时长断言方向固定为「全行非负」+ 口径对拍，规避历史数据回刷差异

### 1.6 复用检查（强制）

> 设计用例前必须检索：特性树 `assets/testcase_pro/IPD管理控制与测试仿真/{01~04 类型目录}/` 与
> `01_系统测试/通用功能/易用性/` 易用性通用库；可覆盖的测试点**直接复用**，标注 reuse。

| 检索范围                                                | 可复用用例                                                                                                                                                  | 复用结论                                                                 |
| ------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------ |
| 特性树 01_系统测试/数字化运营/GitHub PR门禁看板（1 条） | TC-ISSUE136-013（加载与表头断言·空态容错）断言对象为旧表头列结构，为**回归影响对象**（见 1.7）；无新功能点可复用                                            | 需新建 11 条 UI 用例                                                     |
| 特性树 01_系统测试/数字化运营/PR门禁看板（5 条）        | 看板不同（gitcode PR门禁看板）；TC-ISSUE145-001~003（门禁E2E执行时长 2 位小数）对象为 PR门禁看板主表，不受本次 GitHub PR门禁看板改造影响                    | 不复用、不回归                                                           |
| 特性树 02_API测试/数字化运营/PR门禁看板（9 条）         | TC-ISSUE135-005（pipeline github 类型兼容基线）对象为 pipeline 接口，不受本次影响；无 github 看板 detail/chart 字段结构变更类可复用用例                     | 需新建 8 条 API 用例                                                     |
| 特性树 03_DFX测试                                       | 既有响应时间基线用例模式可复用（TC-ISSUE135-017 / TC-ISSUE078-015 同类）                                                                                    | 新建 1 条 DFX 用例（模式复用）                                           |
| 特性树 04_安全测试/数字化运营/PR门禁看板                | TC-ISSUE135-018（未认证访问拒绝）模式可复用，对象为 pipeline 接口；本次涉改接口集合不同                                                                     | 新建 4 条安全用例（模式复用，对象为 github 3 category + chart/job 接口） |
| 易用性通用库 01_系统测试/通用功能/易用性/               | openlibing_ops_usability_202609_098（列设置）、_051（定制项记忆）、_052（列宽合理）、_053（列宽调整拖动）、_093（帮助小图标及信息）、_094（提示信息正确性） | **reuse 6 条**，覆盖新列/隐藏列的列设置与记忆体验、指标说明 tooltip 体验 |

**结论**：new 24（UI 11 · API 8 · DFX 1 · 安全 4）+ reuse 6（易用性）+ 回归登记 1（TC-ISSUE136-013）。

### 1.7 风险与约束

| 风险                                                                                                                                  | 影响                          | 缓解措施                                                                                                           |
| ------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------- | ------------------------------------------------------------------------------------------------------------------ |
| 分位集合歧义：条目3「区分 P50 P90 P95」vs 条目5「平均、P90、P95，默认 P90」                                                           | 列结构与断言方向不确定        | §2.3 #1 串讲定稿；TC-ISSUE205-001/002/012/018 按「平均/P90/P95 默认 P90」（正文口径）为主断言，映射表登记 P50 候选 |
| 命名歧义：需求"CI E2E时长(min)"与现列名「门禁E2E执行时长(min)」(ciE2eTime)、「PR门禁E2E执行时长」vs 条目8「门禁E2E执行时长」          | 表头文案断言失败              | §2.3 #2；表头断言用「正则候选集」（PR门禁E2E执行时长/门禁E2E执行时长）+ 映射表定稿                                 |
| 「PR E2E时长」(条目9) 与「PR闭环时长」(条目4) 是否同一列 prE2eDuration                                                                | 隐藏/去跳转断言对象错误       | §2.3 #3；TC-ISSUE205-003/004 按同列设计（隐藏+去跳转+PR总数接替跳转），串讲确认                                    |
| job 任务下钻数据源未定（数仓无 job 级表，仅精准测试 `dwi_rd_efc_precision_workflow_job`）                                             | job 用例无法执行/断言列名不齐 | §2.3 #4；TC-ISSUE205-006/016 按「run→job 下钻列表 + job 统计时长」语义设计，列名/接口经映射表对齐                  |
| PR合入时长 push 过滤口径未定（`DwiRdEfcPrWorkflowRun` 无 event/trigger 字段；按 workflow_name 排除 or 数仓加字段）                    | 口径对拍方向不确定            | §2.3 #5；TC-ISSUE205-009 断「全行非负」硬断言，015 对拍口径串讲定稿                                                |
| 后端新增字段命名与旧 ciE2eTime 处理未定                                                                                               | API 字段断言返工              | §2.3 #6；012/013/014 经字段映射表隔离                                                                              |
| 既有用例断言失效：TC-ISSUE136-013（表头基线含旧列结构）                                                                               | 归集后回归失败误报            | 回归登记 1 条；新用例一律表头文案断言；既有用例更新走规则 02（不擅自改写）                                         |
| 旧用户列设置 localStorage 记忆含将隐藏列 prop（prE2eDuration/prE2eTime/prMergeTime）                                                  | 幽灵列/渲染异常               | TC-ISSUE205-003/007 显式覆盖记忆降级；复用 usability_051                                                           |
| 前后端实现未合入 beta（2026-10-14 走查：后端 origin/release_20261019 止于 20260923、前端无 release_20261019、origin/beta 亦为改造前） | 用例全部无法执行              | 全部用例状态标 blocked，待部署后执行；断言经映射表隔离                                                             |
| 安全用例触发 WAF 封禁（历史经验：客户端 IP 封禁 18-49 分钟）                                                                          | 批次连锁失败                  | 安全用例串行、每 5 条一批、批间 30s 冷却；CSRF 维度豁免不发攻击请求                                                |
| 负值样本依赖：修复上线后界面无负值可验                                                                                                | 「防负值」验证退化为恒真      | TC-ISSUE205-009 全行非负断言 + 015 SQL 口径对拍（验证 push 已排除）双保险                                          |

### 1.8 依赖与前置条件

- beta 环境（beta.openlibing.com）部署本 issue 前后端实现（后端合入 release_20261019 迭代、前端 beta 分支），当前未部署 → blocked
- 测试账号：具备 GitHub PR门禁看板查看权限的账号 A；跨项目越权对照账号 B（无目标项目权限）
- 样本数据（beta）：有 workflow 运行记录与关联 PR 的 GitHub 数据源项目（执行前页面探索确认 projectId）；含 push 触发 workflow 的仓（负值复现/口径验证样本）；workflow 数据为空的项目（空态兜底，如 MindIE projectId=300036 基线）
- Doris 基线（只读 SELECT）：`sdi_rd_efc_workflow_run_raw_github` + `dwi_rd_efc_pr_workflow_run` + `sdi_rd_efc_pr_info_raw_github`（PR合入时长/PR总数/分位口径对拍），对拍窗口取 beta 有数据的最近完整自然月
- 统计窗口：startDate/endDate 日期区间参数（与既有 GitHub 看板用例一致）

---

## 2. 测试设计概要

> 详细设计见同目录 测试设计脑图.xmind（逐用例三节点：前置条件 / 测试步骤 / 预期结果），用例本体为 issue 目录内逐用例 .md。

### 2.1 用例统计

| 维度                                        | new    | reuse       | P0     | P1     | P2    | 执行方式           |
| ------------------------------------------- | ------ | ----------- | ------ | ------ | ----- | ------------------ |
| 01_系统测试（数字化运营/GitHub PR门禁看板） | 11     | 6（易用性） | 7      | 2      | 2     | 全自动化 auto_ui   |
| 02_API测试（数字化运营/GitHub PR门禁看板）  | 8      | —           | 4      | 3      | 1     | 全自动化 auto_api  |
| 03_DFX测试（数字化运营/GitHub PR门禁看板）  | 1      | —           | —      | 1      | —     | 全自动化 auto_perf |
| 04_安全测试（数字化运营/GitHub PR门禁看板） | 4      | —           | —      | 4      | —     | 全自动化 auto_sec  |
| 合计                                        | **24** | **6**       | **11** | **10** | **3** | 自动化 24 / 手工 0 |

### 2.2 功能点 → 用例映射

| FP    | 功能点                                                | new 用例                       | 复用                      |
| ----- | ----------------------------------------------------- | ------------------------------ | ------------------------- |
| FP-01 | workflow 运行明细 job 任务下钻与统计时长（条目1）     | TC-ISSUE205-006、016           | —                         |
| FP-02 | 状态筛选（成功/失败）CI E2E 时间联动（条目2）         | TC-ISSUE205-005、013、019      | —                         |
| FP-03 | 门禁E2E执行时长改名/分位展示/默认 P90（条目3/5）      | TC-ISSUE205-001、002、012、018 | —                         |
| FP-04 | PR闭环时长主表默认隐藏、去跳转（条目4/9）             | TC-ISSUE205-003                | usability_098/051         |
| FP-05 | PR明细「PR闭环时长」「PR合入时长」默认不展示（条目6） | TC-ISSUE205-007                | usability_098/051         |
| FP-06 | PR合入时长去 push 口径、无负值（条目7）               | TC-ISSUE205-009、015           | —                         |
| FP-07 | PR明细新增「门禁E2E执行时长」字段（条目8）            | TC-ISSUE205-008、014           | —                         |
| FP-08 | workflow 相关指标说明（条目8）                        | TC-ISSUE205-010                | usability_093/094         |
| FP-09 | PR总数列新增与跳转 PR明细（条目9）                    | TC-ISSUE205-004、013           | —                         |
| FP-10 | 导出列同步（横切）                                    | TC-ISSUE205-017                | —                         |
| FP-11 | 空数据兜底与渲染回归                                  | TC-ISSUE205-011                | —                         |
| FP-12 | 涉改接口性能基线                                      | TC-ISSUE205-020                | 模式：TC-ISSUE135-017     |
| FP-13 | 涉改接口安全                                          | TC-ISSUE205-021~024            | 模式：TC-ISSUE078-016~021 |

### 2.3 待评审确认项（串讲澄清）

| #   | 待确认项                                                                                                                                                                        | 影响                                   |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------- |
| 1   | 「PR门禁E2E执行时长」分位集合：条目3"区分 P50 P90 P95" vs 条目5"平均、P90、P95，默认 P90"——P50 是否在列？平均是否保留？默认列哪个？                                             | TC-ISSUE205-001/002/012/018 断言方向   |
| 2   | 指标命名：现列「门禁E2E执行时长(min)」(ciE2eTime) 与需求"CI E2E时长(min)"是否同一指标；最终列名「PR门禁E2E执行时长」还是「门禁E2E执行时长」（条目8用后者）                      | TC-ISSUE205-001/010/012 表头与字段断言 |
| 3   | 「PR E2E时长」(条目9) 与「PR闭环时长」(条目4) 是否同一列（prE2eDuration）；PR总数跳转目标"和现在的PR E2E时长一样"是否即 PR 明细抽屉                                             | TC-ISSUE205-003/004                    |
| 4   | job 任务下钻：数据来源（数仓无 job 级表）；下钻层级（run 内展开 / 二级抽屉）；job 统计时长口径（Σjob 时长 / wall time）；展示列与字段命名                                       | TC-ISSUE205-006/016                    |
| 5   | PR合入时长去 push 口径：按 workflow 触发类型过滤（数仓需加 event 字段）还是 workflow_name 排除清单；修复范围（主表 prMergeDuration + PR明细 prMergeTime）；历史负值数据是否回刷 | TC-ISSUE205-009/015                    |
| 6   | 后端新增字段命名（分位字段 / PR总数 prCount / PR明细门禁E2E执行时长）与旧 ciE2eTime 字段处理（物理删除 / 保留）                                                                 | TC-ISSUE205-012/013/014 映射表         |
| 7   | PR明细「门禁E2E执行时长」口径：每 PR 门禁E2E执行 平均/单次/最长（现 gateAvgTime/gateSingleTime 为 Workflow 执行平均/最长）                                                      | TC-ISSUE205-008/014                    |
| 8   | 导出口径：默认隐藏列（PR闭环时长/PR合入时长）是否导出；新增列（PR总数/门禁E2E执行时长）导出文案与顺序                                                                           | TC-ISSUE205-017                        |

### 2.4 一致性检查结论（2026-10-14，test-design-consistency 七维检查）

| #   | 检查维度                                    | 结论                                                                                                                                                                               |
| --- | ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | 需求条目 → 功能点覆盖                       | ✅ 通过：需求 9 条目 → FP-01~FP-13 全覆盖（条目1→FP-01；条目2→FP-02；条目3/5→FP-03；条目4/9→FP-04/FP-09；条目6→FP-05；条目7→FP-06；条目8→FP-07/FP-08），覆盖率 9/9（100%）         |
| 2   | 功能点 → 用例正向追溯                       | ✅ 通过：13 个 FP 均有用例覆盖（映射见 §2.2），0 覆盖缺失                                                                                                                          |
| 3   | 用例 → 功能点反向追溯                       | ✅ 通过：24 条 new 用例全部登记 FP 归属（011→FP-11、017→FP-10、020→FP-12、021~024→FP-13），0 来源不明                                                                              |
| 4   | 数量一致性（逐用例 .md / case_list / 脑图） | ✅ 通过：逐用例 .md 24 份 = case_list 24 条 = 脑图 24 节点（UI 11 / API 8 / DFX 1 / 安全 4）                                                                                       |
| 5   | 等级一致性                                  | ✅ 通过：P0×11 / P1×10 / P2×3，用例 .md、脑图标签、case_list 三方一致，与 §2.1 统计吻合                                                                                            |
| 6   | 编号规范                                    | ✅ 通过：TC-ISSUE205-001~024 连续、无缺号/重号，含 ISSUE 号可追溯                                                                                                                  |
| 7   | 复用合规                                    | ✅ 通过：先检索后新建（§1.6 留痕）；reuse 6 条（易用性 U098/U051/U052/U053/U093/U094）只引用不归档；回归登记 TC-ISSUE136-013 未擅改（规则 02）                                     |
| 8   | 过度发散检查                                | ✅ 通过：0 发散。FP-10 导出列同步为列结构改造直接衍生物（代码走查：导出列由同一 Resp @ExcelProperty 驱动）；FP-11 空态为异常场景回归；FP-12/FP-13 为流程强制横切维度，均有来源依据 |
| 9   | 门禁校验（check_baseline）                  | ✅ 通过（issue_205 范围 0 错误 0 告警）；全仓存量 128 错误/6 告警均来自历史 issue #120/#144/#145 及团队级覆盖率提示，与本 issue 无关                                               |
| 10  | 状态一致性（blocked）                       | ✅ 通过：24 条用例状态全部 blocked（beta 未部署本 issue 前后端实现），与 §1.7/§1.8 一致                                                                                            |

**综合结论**：**通过**——测试设计与需求一致且完整，双向可追溯，无过度发散；安全 6 维度 4 覆盖 + 2 豁免（纵向越权/CSRF，豁免原因见 §1.4，须在评审中确认）。遗留 8 项口径待串讲定稿（§2.3 #1~#8），均为断言方向/映射表微调项，不阻塞设计审核；定稿后仅更新脚本映射表常量与用例备注，不新增/删减用例。

---

## 3. 用例范围与执行状态定稿（v1.3 / v1.4）

> 测试设计脑图由用户在 XMind 中手工维护（Agent 只读，不得 build/覆盖）；生效用例以脑图用例节点为唯一边界，一节点一用例。
> v1.3（2026-10-17）：用户将脑图重写为 GitHub PR门禁看板口径 11 用例节点（代码仓指标汇总表 7 / 代码仓指标明细表 2 / 明细表下钻 workflow 详情 2），逐字生成 TC-ISSUE205-065~~075（01_系统测试/数字化运营，auto_ui，P1×11 暂定，全部 blocked）；脑图外的 001~~024（早期 24 条）与 025~~064（三看板 40 条）按用户决定整批移除、编号作废不回收；上文 §2.1~~§2.4 为移除前设计留痕（已退役，仅作需求背景）。
> v1.4（2026-10-20）：beta 环境核查后执行，详见下表。

| 定稿项                            | 口径                                                                                                                                                                                                                                                                                                                                            | 依据/说明                                                      |
| --------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- |
| 用例编号（最终）                  | **11 条 = TC-ISSUE205-065~075**（01_系统测试/数字化运营，auto_ui，P1×11 暂定待串讲确认），与脑图 11 个节点一一对应；001~064 共 64 条编号作废不回收                                                                                                                                                                                              | case_list.md（11 条）与 执行记录跟踪表.xlsx（11 行）为生效清单 |
| 脑图分支结构                      | 代码仓指标汇总表 7 节点（065 默认不展示PR闭环时长 / 066 默认不展示PR合入时长 / 067 门禁E2E执行时长[平均](min) / 068 [P95](min) / 069 [P90](min) / 070 新增PR总数 / 071 执行状态筛选）；代码仓指标明细表 2 节点（072 默认不展示PR闭环时长(min) / 073 默认不展示PR合入时长(min)）；明细表下钻 workflow 详情 2 节点（074 显示正确 / 075 数据获取） | 测试设计脑图.xmind（用户所有物，Agent 只读）                   |
| beta 部署核查（2026-10-20）       | 已部署：汇总表 PR闭环时长/PR合入时长默认不展示、门禁E2E执行时长[平均]/[P95]默认不展示、[P90]默认展示，列设置可勾选/去勾选/恢复默认，导出包含性校验通过（空态容错：无业务数据时导出断言跳过、表头结构强校验）；未部署：PR总数字段、执行状态筛选、代码仓指标明细表、明细表下钻 workflow 详情                                                      | 页面探索 + pytest 自动化执行验证                               |
| 执行状态（Stage 4/5，2026-10-20） | 065~~069 五条 pytest 自动化执行通过（5/5，通过率 100%，执行凭证 assets/reports/latest/test_report.json）；070~~075 六条因功能未部署保持 blocked，登记具体阻塞原因；测试结论「附条件发布」                                                                                                                                                       | test_report.md；issue 级+版本级 执行记录跟踪表.xlsx 已回填     |
| 缺陷追溯                          | 历史缺陷 #280（门禁E2E执行时长(min)平均值、P90、P95计算错误，已关闭）经 067/068/069 本次回归通过；#281（job未执行但状态标记为失败，已关闭）待 beta 部署明细表下钻功能后随 075 回归                                                                                                                                                              | openlibing-ops 缺陷单                                          |
| 脑图笔误登记                      | 065/066/067/072/073 预期结果「数字段」、069/070「段可见」、068 步骤 3「[P95](min))」多余右括号、072/073 步骤 5 导出对象写「汇总表」（节点归属明细表）——均为脑图原文，用例 .md 逐字保留不改写，勘误仅登记在用例备注与本表                                                                                                                        | 规则：脑图用户所有物，Agent 只读                               |
