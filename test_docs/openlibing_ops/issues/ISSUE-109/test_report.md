# 测试报告 - ISSUE-109

> **模板版本**: v1.0
> **对应规则**: ai-rules/03-test-execution-and-report.md
> **生成门槛**: 必须在 test_cases.md 执行结果完整填写后方可生成（见规则 03 第4节）

---

> **Issue编号**: ISSUE-109
> **Issue标题**: 【蓝区】【运营看板】资源运营看板建设
> **报告日期**: 2026-08-31
> **测试负责人**: mth
> **报告版本**: v1.0

---

## 1. 执行概览

| 项目 | 内容 |
|------|------|
| 测试周期 | 2026-08-29 ~ 2026-08-31（08-29 端到端验证，08-31 正式测试流程执行） |
| 测试环境 | test (https://beta.openlibing.com) |
| 用例总数 | 20 |
| 执行数 | 20 |
| 通过 | 18 |
| 失败 | 2 |
| 阻塞 | 0 |
| 跳过 | 0 |
| 通过率 | 90% |

### 1.1 按用例等级统计

| 等级 | 总数 | 通过 | 失败 | 阻塞 | 跳过 |
|------|------|------|------|------|------|
| L0 | 5 | 4 | 1 | 0 | 0 |
| L1 | 13 | 12 | 1 | 0 | 0 |
| L2 | 2 | 2 | 0 | 0 | 0 |

### 1.2 按用例类型统计

| 类型 | 总数 | 通过 | 失败 | 阻塞 | 跳过 |
|------|------|------|------|------|------|
| 手工用例 | 4 | 4 | 0 | 0 | 0 |
| 自动化-UI | 0 | 0 | 0 | 0 | 0 |
| 自动化-API | 13 | 12 | 1 | 0 | 0 |
| 自动化-性能 | 0 | 0 | 0 | 0 | 0 |
| 自动化-安全 | 3 | 2 | 1 | 0 | 0 |

---

## 2. 用例执行明细

> 数据来源：test_cases.md 的执行结果记录。所有执行数据必须可追溯。

### 2.1 执行信息

| 字段 | 内容 |
|------|------|
| 自动化执行Action链接 | 本地 beta 执行（TEST_ENV=test + SECURITY_ENABLED=true，串行分 3 批；无 GitCode Action 流水线） |
| 手工执行人 | mth |
| 执行日期 | 2026-08-31 |

### 2.2 用例执行明细

| 用例编号 | 用例标题 | 用例等级 | 用例类型 | 执行结果 | 缺陷issue | 备注 |
|----------|----------|----------|----------|----------|------------|------|
| TC-ISSUE109-001 | summary 接口 7 天窗口 KPI 数据结构与分组验证 | L0 | auto_api | pass | — | KPI 四字段结构完整、cloud/lab 分组正确、npuNum 非负 |
| TC-ISSUE109-002 | summary 接口 projectId 过滤验证 | L1 | auto_api | pass | — | 过滤后 cloud:1/lab:1 ≤ 全量 cloud:3/lab:10 |
| TC-ISSUE109-003 | trend 接口 pool 维度分组与逐小时曲线验证 | L0 | auto_api | pass | — | pool 分组曲线完整、labels 逐小时连续、数值 ∈ [0,100] |
| TC-ISSUE109-004 | trend 接口 gen 维度分组验证 | L1 | auto_api | pass | — | gen 维度分组正常（A2/A3/310P） |
| TC-ISSUE109-005 | heatmap 接口服务器骨架与分配数据验证 | L0 | auto_api | pass | — | servers 骨架完整、抽样存在非零分配值 |
| TC-ISSUE109-006 | heatmap 接口空数据窗口补零验证 | L1 | auto_api | pass | — | 空窗口 HTTP 200 不报错、骨架完整、补 0 |
| TC-ISSUE109-007 | run-analysis 有效 runId 状态机验证 | L1 | auto_api | pass | — | 状态机完整，states ⊆ {QUEUING, RUNNING, NONE} |
| TC-ISSUE109-008 | run-analysis 无效 runId 空数据验证 | L2 | auto_api | pass | — | 随机 runId 返回空结构不报错 |
| TC-ISSUE109-009 | project-alloc-trend 接口曲线数据验证 | L1 | auto_api | pass | — | 逐小时申请次数与排队时长曲线结构正确 |
| TC-ISSUE109-010 | 时间参数校验决策表验证（4 接口 × 5 非法场景） | L1 | auto_api | fail | [#115](https://gitcode.com/openlibing/openlibing-ops/issues/115) | 20/20 非法时间场景返回 500 而非 40001；对照组合法请求均 200 正常 |
| TC-ISSUE109-011 | 时间窗口边界值验证（6 天/7 天整） | L1 | auto_api | pass | — | 边界内跨度均正常返回 200+数据 |
| TC-ISSUE109-012 | run-analysis 必填参数校验验证 | L1 | auto_api | pass | — | 缺 runId/projectId 均返回 40001（防回归基线保持） |
| TC-ISSUE109-013 | 数据管道新鲜度弱断言验证 | L1 | auto_api | pass | — | 当日数据管道有产出 |
| TC-ISSUE109-014 | 看板页面渲染与图表完整性验证 | L0 | manual | pass | — | 四类图表完整渲染，抽样数值与 API 层一致 |
| TC-ISSUE109-015 | 时间选择器与维度切换交互验证 | L1 | manual | pass | — | 时间联动刷新正常、维度切换正确、超 7 天拦截提示友好 |
| TC-ISSUE109-016 | 热力图悬浮与抽屉交互验证 | L1 | manual | pass | — | 悬浮浮层与详情抽屉交互均正常 |
| TC-ISSUE109-017 | 无权限访问拦截验证 | L1 | manual | pass | — | 重定向 noPermission 页，守卫生效正常 |
| TC-ISSUE109-018 | 低权限账号纵向越权验证（5 接口） | L0 | auto_sec | fail | [#114](https://gitcode.com/openlibing/openlibing-ops/issues/114) | p_tianyan（npu_resource=false）浏览器 fetch 5/5 接口越权成功返回全量数据（heatmap 泄露 88 台服务器） |
| TC-ISSUE109-019 | 匿名与伪造 token 调用看板接口认证校验 | L1 | auto_sec | pass | — | 匿名与伪造 token 均被 401 拒绝 |
| TC-ISSUE109-020 | 看板接口响应体敏感信息防护验证 | L2 | auto_sec | pass | — | 响应体/响应头未泄露凭证类敏感字段 |

> 执行证据说明：原 `execution_results/` 下 junit 结果（junit_api_batch1.xml、junit_api_batch2.xml、junit_security_batch3.xml、junit_security_019_020.xml、tc018_final.log）与失败截图（screenshots/failure_test_tc010_*.png、failure_test_tc018_*.png）因 2026-08-31 本地存储层异常丢失且未入库，无法恢复；逐条执行结果以本表与 test_cases.md「执行结果记录」为准（结果回填自执行时实测输出）。

---

## 3. 缺陷列表

> 仅列出 fail 用例对应的缺陷，缺陷信息来源于 test_cases.md 中填写的缺陷 issue。

| 关联用例 | 缺陷issue链接 | 缺陷描述 | 严重级别 | 状态 |
|----------|----------------|----------|----------|------|
| TC-ISSUE109-018 | [#114](https://gitcode.com/openlibing/openlibing-ops/issues/114) | 资源运营看板后端 API 未做权限校验，登录用户可越权获取数据 | 严重（发布阻塞项） | 已提交 |
| TC-ISSUE109-010 | [#115](https://gitcode.com/openlibing/openlibing-ops/issues/115) | 时间参数校验错误返回 500 系统异常而非 40001 参数异常 | 一般 | 已提交 |

### 缺陷详情

#### #114: 资源运营看板后端 API 未做权限校验，登录用户可越权获取数据

- **关联用例**: TC-ISSUE109-018
- **缺陷issue**: https://gitcode.com/openlibing/openlibing-ops/issues/114
- **严重级别**: 严重（数据泄露，发布阻塞项）
- **状态**: 已提交（open）
- **复现步骤**:
  1. 使用 p_tianyan（admin 系统角色、npu_resource=false）登录 beta
  2. 打开浏览器控制台（F12），fetch 调用 `/gateway/openlibing-ops/resource-operation/heatmap`（credentials include，合法时间参数）
  3. 其余 4 个接口（summary/trend/run-analysis/project-alloc-trend）同方式调用
- **实际结果**: 5/5 接口返回 HTTP 200 + code=200 + 全量数据（heatmap 返回 88 台服务器，含服务器 IP、池名、代际、逐小时分配/使用率、任务名）
- **预期结果**: 后端应校验 `npu_resource` 权限，未授权用户返回 403/401（与前端路由守卫行为一致）
- **影响范围**: 任意已登录用户可获取全部资源池/服务器利用率运营数据，存在数据泄露风险
- **复现概率**: 100%（2026-08-29 端到端发现，2026-08-31 正式流程 TC-018 闭环确认）
- **补充说明**: pub_LIBING（纯低权限）浏览器 fetch 被 401 拒绝，属网关基础权限层拦截；`npu_resource` 业务权限校验在全部 5 个接口缺失

#### #115: 时间参数校验错误返回 500 系统异常而非 40001 参数异常

- **关联用例**: TC-ISSUE109-010
- **缺陷issue**: https://gitcode.com/openlibing/openlibing-ops/issues/115
- **严重级别**: 一般
- **状态**: 已提交（open）
- **复现步骤**:
  1. 对 summary/trend/heatmap/project-alloc-trend 4 个接口分别传入非法时间参数：跨度 8 天（超限）、跨度 30 天、时间倒置、缺 endDate、非法格式（yyyy/MM/dd）
- **实际结果**: 20/20 组合全部返回 code=500 "系统异常"（对照组 4 个合法 7 天窗口请求均 200 正常，排除服务故障）
- **预期结果**: 返回 code=40001 参数异常并携带具体原因
- **影响范围**: 用户通过非常规时间参数操作时收到误导性"系统异常"报错，无法定位输入问题；接口异常处理规范缺失
- **复现概率**: 100%

---

## 4. 测试结论

### 4.1 结论

> 取值：允许发布 / 附条件发布 / 暂不允许发布（见规则 03 第5.2节）

**暂不允许发布**

### 4.2 结论依据

- **功能覆盖**: 8 个功能点（FP-1~FP-8）全部覆盖，UI/API/安全三维度（性能维度经策略说明不覆盖）；20 条用例全部执行，通过率 90%
- **L0用例结果**: 存在失败 —— TC-ISSUE109-018 fail（缺陷 #114：后端 API 未做 `npu_resource` 权限校验，任意登录用户可越权获取全量资源运营数据，含 88 台服务器 IP/池名/任务名）
- **L1用例结果**: 存在失败，无规避措施 —— TC-ISSUE109-010 fail（缺陷 #115：5 种非法时间场景统一返回 500 系统异常而非 40001 参数异常，误导性报错）
- **L2用例结果**: 全部通过（TC-008 无效 runId 空数据、TC-020 敏感信息防护）
- **遗留风险**: ① 缺陷 #114 为数据越权泄露，属发布阻塞项，须后端补充 `@PreAuthorize` 类权限校验或网关层拦截后方可发布；② 缺陷 #115 参数校验异常处理缺失，影响错误提示体验；③ run-analysis 的 usageServers 曾观测 pool/gen 为 null（页面探索记录），建议开发排查数据管道字段填充完整性

### 4.3 附条件发布说明

不适用（结论为"暂不允许发布"）。

**修复后回归要求**: 缺陷 #114 修复后重跑 TC-ISSUE109-018（预期转 pass：越权请求被 401/403 或业务拒绝拦截）；缺陷 #115 修复后重跑 TC-ISSUE109-010（预期转 pass：非法时间参数返回 40001）。两用例均为缺陷修复验证闭环用例，复测通过后方可重新评估发布结论。

---

## 5. 版本历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0 | 2026-08-31 | mth | 初始报告（20 条用例全部执行：18 pass + 2 fail，通过率 90%；结论：暂不允许发布） |
