# 测试用例 - ISSUE-093

> **Issue编号**: ISSUE-093
> **Issue标题**: 【蓝区】【运营看板】GitHub workflow中job数据采集&workflow排队数据计算
> **创建日期**: 2026-08-29
> **用例总数**: 1
> **手工用例**: 0
> **自动化用例**: 1
> **复用旧用例**: 0
> **新设计用例**: 1

### 执行信息

> **自动化用例**的执行凭证由 **AI 基于真实执行输出**回填（规则 03 v2.1）；**手工用例**的执行人由**测试人员**填写。Action 链接在此**统一填写一个**，无需每条用例重复填写。

| 字段                 | 内容                                                                                                                                                                                                                                 |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 自动化执行Action链接 | 本地执行（pytest --env=test，最新 2026-08-31 17:46，40.92s，透出接口口径修正后复跑）；执行凭证：`execution_evidence/pytest_junit_20260831_local_v3.xml`（历史执行：v2=17:32 泛化关键词口径、v1=16:57 首次，均 1 passed / 2 xfailed） |
| 手工执行人           | —                                                                                                                                                                                                                                    |
| 执行日期             | 2026-08-31                                                                                                                                                                                                                           |

---

## 用例列表

| 用例编号        | 用例标题                      | 所属功能点        | 用例类型 | 用例来源 | 用例等级 | 脚本位置                                                                                              | 状态   |
| --------------- | ----------------------------- | ----------------- | -------- | -------- | -------- | ----------------------------------------------------------------------------------------------------- | ------ |
| TC-ISSUE093-005 | 运营看板 API 排队字段透出验证 | FP-05 看板API透出 | auto_api | new      | L2       | src/tests/openlibing/openlibing_ops/api/beta/operation_dashboard/test_api_ops_dashboard_fields_005.py | active |

> **用例来源说明**：
>
> - `reuse`：复用已有用例，引用已有用例编号（在详情中"引用已有用例"字段标注），不重新归档
> - `new`：新设计用例，必须按规则 5.3 归档到模块用例文件与 case_list.md

---

## 执行结果记录

> **自动化用例**执行结果由 AI 基于真实执行输出回填（规则 03 v2.1，禁止凭推测填写）；**手工用例**由测试人员填写。执行结果未填写完整前，AI 不得生成测试报告（见规则 03 第4节）。
> **2026-08-31 17:46 本地复跑**（透出接口口径修正后：改查 category=github-pr-workflow-main；pytest --env=test，40.92s，3 tests）：**3 passed / 0 failed / 0 xfailed**，JUnit 汇总 `errors=0, failures=0, skipped=0`，凭证：`execution_evidence/pytest_junit_20260831_local_v3.xml`。
>
> - `test_tc005_github_workflow_detail_structure`：passed（接口可达、业务码 200、records 非空且 repoId 匹配请求，38.26s 含登录 fixture）
> - `test_tc005_github_workflow_queue_fields`：passed（8 个目标字段 queueP50/queueP90/queueP95、execP50/execP90/execP95、prMergeDuration、e2ePassRate 全部透出，1.07s）
> - `test_tc005_github_workflow_field_semantics`：passed（分位单调 P50≤P90≤P95、存在非空排队数据、prMergeDuration/e2ePassRate 非空且取值合法，1.50s）
> - **口径修正依据**：测试人员提供调用实例（POST common/detail，category=github-pr-workflow-main，repoIds=[402051]），归档 `exploration_assets/github_pr_workflow_main_example_20260831.json`。此前按 category=project / nightly-dashboard-* 探查未命中系透出位置判断偏差（此前判定 block 的问题"FP-05 是否属本期范围"就此关闭：字段已透出且取值正常）
> - 历史执行：v2（17:32，泛化关键词+错误接口口径）1 passed / 2 xfailed，凭证 `pytest_junit_20260831_local_v2.xml`；v1（16:57 首次）1 passed / 2 xfailed，凭证 `pytest_junit_20260831_local.xml`；2026-08-29 端到端预验证结论与数据层发现项详见 `test_design.md` 与 `execution_evidence/e2e_verification_20260829.json`

| 用例编号        | 用例类型 | 执行结果 | 缺陷issue | 备注                                                                                                                                                                                                                                                                                                              |
| --------------- | -------- | -------- | --------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TC-ISSUE093-005 | auto_api | pass     | —         | 3/3 断言通过：github-pr-workflow-main 明细接口 8 个排队/合入字段全部透出且取值语义合法（分位单调、存在非空排队数据、仓级字段取值合法）；口径修正依据测试人员调用实例（归档 `exploration_assets/github_pr_workflow_main_example_20260831.json`）；执行凭证 `execution_evidence/pytest_junit_20260831_local_v3.xml` |

---

## 自动化用例详情

### TC-ISSUE093-005: 运营看板 API 排队字段透出验证

- **所属功能点**: FP-05 看板 API 字段透出
- **测试设计方法**: 场景法
- **用例类型**: 自动化-API (auto_api)
- **用例来源**: new
- **引用已有用例**: —
- **脚本位置**: `src/tests/openlibing/openlibing_ops/api/beta/operation_dashboard/test_api_ops_dashboard_fields_005.py`
- **用例等级**: L2
- **前置条件**: test 环境已登录（api_client fixture 可用）
- **测试步骤**:
  1. POST `/gateway/openlibing-ops/common/detail`（category=github-pr-workflow-main，repoIds=[402051]，近 30 天窗口）获取 GitHub PR workflow 级明细数据
  2. 检查响应 records 的字段集合中是否透出 8 个目标字段：queueP50/queueP90/queueP95（排队时间）、execP50/execP90/execP95（合入时间）、prMergeDuration（PR合入时长）、e2ePassRate（E2E达标率）
  3. 校验字段取值语义：分位单调（P50≤P90≤P95）、存在非空排队数据、仓级字段（prMergeDuration/e2ePassRate）非空且取值合法
- **预期结果**: 8 个字段全部透出且取值语义合法；**实测（2026-08-31 口径修正后复跑 3/3 passed）：通过**
- **透出接口口径修正（2026-08-31）**: 依据测试人员提供的调用实例，排队/合入字段透出位置为 `common/detail`（category=github-pr-workflow-main，workflow 级明细，repoIds 过滤）；此前按 category=project（项目级汇总）与 nightly-dashboard-*（Nightly 看板）探查未命中，系透出位置判断偏差而非字段缺失。调用实例归档 `exploration_assets/github_pr_workflow_main_example_20260831.json`
- **字段取值观察（2026-08-31 调用实例, repo=vllm-ascend）**: prE2eDuration/ciE2eTime/prMergeDuration/e2ePassRate 为仓级指标按行冗余；workflowE2eP50/P90 与 execP50/P90 取值一致（同源）；定时触发类 workflow（如 _nightly_image_build）queueP50/90/95 为 null（无 PR 触发排队样本，合理空值）
- **预验证发现（2026-08-29，已被 2026-08-31 透出口径修正取代）**: 项目级汇总接口仅透出 avgAccessDuration/avgBuildDuration/avgDtDuration 等执行时长字段；仓库下钻接口 `manage/repo/base/dashboard` 当时返回 503

---

## 用例汇总

| 类型        | 数量  | 通过  | 失败  | 阻塞  | 跳过  |
| ----------- | ----- | ----- | ----- | ----- | ----- |
| 手工用例    | 0     | 0     | 0     | 0     | 0     |
| 自动化-UI   | 0     | 0     | 0     | 0     | 0     |
| 自动化-API  | 1     | 1     | 0     | 0     | 0     |
| 自动化-性能 | 0     | 0     | 0     | 0     | 0     |
| 自动化-安全 | 0     | 0     | 0     | 0     | 0     |
| **合计**    | **1** | **1** | **0** | **0** | **0** |

| 用例来源            | 数量 |
| ------------------- | ---- |
| reuse（复用旧用例） | 0    |
| new（新设计用例）   | 1    |

---

## 版本历史

| 版本 | 日期       | 修改人   | 修改内容                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                  |
| ---- | ---------- | -------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.0 | 2026-08-29 | tester-a | 初始版本：5 条新建用例（draft，待设计评审定稿）                                                                                                                                                                                                                                                                                                                                                                                                                                                           |
| v1.1 | 2026-08-29 | tester-a | 端到端验证完成：正式脚本落地（数据层 4 + API 层 1，含 doris_client 工具）；TC-001 新鲜度断言修正为 DWI 层（raw 层为日批暂存语义）；TC-003 改用直连 JOIN 口径并加 5s 取整容差；证据归档 execution_evidence/e2e_verification_20260829.json                                                                                                                                                                                                                                                                  |
| v1.2 | 2026-08-31 | tester-a | 按测试人员决策删除涉及数据库（Doris 直连）的用例 TC-ISSUE093-001~004 及对应脚本；保留 TC-ISSUE093-005（API 层用例）；doris_client 工具类与 Doris 配置保留供后续数据层用例复用                                                                                                                                                                                                                                                                                                                             |
| v1.3 | 2026-08-31 | AI Agent | TC-ISSUE093-005 本地正式执行（pytest --env=test，51.16s）并按规则 03 v2.1 回填结果：结构断言 passed、排队字段断言 xfail，整体判定 block；执行凭证 `execution_evidence/pytest_junit_20260831_local.xml`；用例状态 draft → active                                                                                                                                                                                                                                                                           |
| v1.4 | 2026-08-31 | AI Agent | 按测试人员提供的看板真实字段名修正 TC-ISSUE093-005 验证口径：脚本 QUEUE_KEYWORDS 由泛化关键词（queue/pending/wait 子串匹配）改为精确字段名（queueP50/queueP90/queueP95 排队时间、execP50/execP90/execP95 合入时间、prMergeDuration PR合入时长、e2ePassRate E2E达标率，精确匹配）；清理临时探针脚本；复跑回填（1 passed / 2 xfailed，35.96s），凭证 `execution_evidence/pytest_junit_20260831_local_v2.xml`                                                                                                |
| v1.5 | 2026-08-31 | AI Agent | 依据测试人员提供的调用实例修正透出接口口径：改查 `common/detail`（category=github-pr-workflow-main，repoIds=[402051]，workflow 级明细）——8 个排队/合入字段全部透出；脚本由 xfail 改为 3 个硬断言（结构/字段透出/取值语义：分位单调、排队数据非空、仓级字段合法）；复跑 3/3 passed（40.92s），执行结果 **block → pass**，"FP-05 是否属本期范围"待确认项关闭；调用实例归档 `exploration_assets/github_pr_workflow_main_example_20260831.json`，凭证 `execution_evidence/pytest_junit_20260831_local_v3.xml` |
