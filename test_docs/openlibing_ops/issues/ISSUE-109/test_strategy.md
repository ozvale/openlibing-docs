# 测试策略 - 【蓝区】【运营看板】资源运营看板建设

> **模板版本**: v1.0
> **对应规则**: ai-rules/01-requirement-driven-test-design.md
> **生成阶段**: Stage 3（测试策略）

---

## 1. Issue 信息

| 字段 | 内容 |
|------|------|
| Issue编号 | ISSUE-109 |
| Issue标题 | 【蓝区】【运营看板】资源运营看板建设 |
| 关联需求 | https://gitcode.com/openlibing/openlibing-ops/issues/109 |
| 所属微服务 | openlibing-ops |
| 所属模块 | resource_dashboard（页面路由 nRDashboard） |
| 负责人 | 测试人员（mth） |
| 创建日期 | 2026-08-31 |
| 状态 | 进行中 |

## 2. 需求摘要

> 从 Issue 原文与页面探索提炼，**禁止超出文档范围**。

- **业务目标**（Issue 原文唯一有效信息）：蓝区资源紧张，资源利用率需要有可视化看板进行运营
- **实现形态**（页面探索确认）：前端看板页面 `/apps/nRDashboard`（权限码 `npu_resource`）+ 后端 5 个 API（`/gateway/openlibing-ops/resource-operation/*`）
- **功能基线**：因 Issue 设计文档信息不足（模板字段全部为空），功能基线以 Stage 2 页面探索（`page_exploration.md`）实测的页面结构、API 清单、请求/响应结构、数据分布为准，并经端到端验证（`verification_report.md`，18 检查点）确认

## 3. 测试目标

1. 验证资源运营看板 8 个功能点（`requirement_analysis.md` FP-1 ~ FP-8）在 beta 环境的正确性与稳定性
2. 验证后端 5 个 API 的功能正确性、参数校验完备性、错误码规范性
3. 验证看板权限模型（`npu_resource`）在前端守卫与后端 API 两层的一致性（**已知 DEF-01 越权缺陷未修复，#114 open**）
4. 已知缺陷基线回归：DEF-01（#114）、DEF-02（#115）修复后验证关闭
5. 输出明确的发布结论（允许发布 / 附条件发布 / 暂不允许发布）

## 4. 测试范围

| 测试类型 | 是否覆盖 | 说明 |
|----------|----------|------|
| UI功能测试 | 是 | 覆盖看板页面渲染、时间选择交互、维度切换、热力图悬浮/抽屉、项目下钻（FP-1/2/3/4/5/6 的 UI 层）。**注意**：测试账号 `p_tianyan` 的 `npu_resource` 权限为 false，UI 用例依赖平台侧开通权限后方可执行，未开通时标记 block |
| API接口测试 | 是 | 覆盖 5 个 API 的正常功能、项目过滤、维度切换、边界时间窗口、非法参数校验（FP-2 ~ FP-7）。已知 DEF-02（#115）影响 4 个接口的时间校验错误码，用例按预期失败基线设计 |
| 性能测试 | 否 | Issue 无性能约束（模板字段为空）；运营看板为低频查询场景（运营人员日常查看），无 TPS/RT 指标要求。如后续提出性能需求，另立 Issue 补充 |
| 安全测试 | 是 | 覆盖纵向越权（无 `npu_resource` 权限账号直连 5 个 API 应被拒绝，当前实际放行 = DEF-01 #114 发布阻塞项）与敏感信息防护（响应体不泄露超出运营范围的数据）。传输安全（HTTPS/Cookie 属性）已在仓库既有基线覆盖，不重复设计 |

## 5. 测试策略

### 5.1 手工测试

覆盖 UI 层交互与图表正确性（自动化不适合的视觉/交互验证）：

- 看板页面控件与图表渲染完整性（KPI 卡片、趋势图、热力图、折线图）
- 时间范围选择器交互（7 天限制提示、起止日期联动）
- 趋势图 pool/gen 维度切换
- 热力图机器悬浮任务详情、抽屉交互
- 项目下钻折线图联动
- 无权限账号访问看板页面的拦截提示（noPermission 页）

手工用例归档位置: `assets/docs/openlibing/openlibing_ops/resource_dashboard/manual_test_cases.md`

### 5.2 自动化测试

覆盖 API 层功能与校验 + 安全越权（可稳定断言的部分）：

- summary：7 天窗口 KPI 数据结构与数值、projectId 过滤、cloud/lab 分组
- trend：pool/gen 双维度分组、labels 逐小时连续、缺失小时补 0、alloc 百分比截断
- heatmap：服务器骨架完整性、projectId/resourcePoolId 过滤、空数据窗口补 0
- run-analysis：runId+projectId 必填校验（40001）、有效 runId 状态机、无效 runId 空数据
- project-alloc-trend：逐小时申请次数与排队时长曲线
- 时间参数校验（跨 FP-7）：超 7 天跨度、时间倒置、缺日期、非法格式（预期 40001，当前 500 = DEF-02 #115）
- 安全越权（FP-8 权限模型 + DEF-01 #114）：无权限账号直连 5 个 API，断言应被拒绝（预期 fail 基线：当前返回 200+数据）

自动化用例归档位置: `assets/docs/openlibing/openlibing_ops/resource_dashboard/auto_test_cases.md`
自动化脚本位置: `src/tests/openlibing/openlibing_ops/{api,security}/beta/resource_dashboard/`

### 5.3 覆盖矩阵

| 功能点 | UI | API | 性能 | 安全 | 说明 |
|--------|----|----|------|------|------|
| FP-1 页面路由与权限守卫 | ✓ | - | - | ✓ | UI: noPermission 拦截；安全: 后端越权（DEF-01） |
| FP-2 KPI 汇总 summary | ✓ | ✓ | - | - | |
| FP-3 NPU 趋势 trend | ✓ | ✓ | - | - | |
| FP-4 服务器热力图 heatmap | ✓ | ✓ | - | - | |
| FP-5 运行分析 run-analysis | ✓ | ✓ | - | - | |
| FP-6 项目下钻 project-alloc-trend | ✓ | ✓ | - | - | |
| FP-7 时间范围校验 | ✓ | ✓ | - | - | API 层 5 种非法参数；UI 层选择器交互 |
| FP-8 数据管道与数据正确性 | - | ✓ | - | - | API 数据与 Doris 宽表一致性抽查 |

### 5.4 优先级分级

| 级别 | 范围 | 说明 |
|------|------|------|
| P0（冒烟） | summary 正常窗口、trend 正常窗口、越权拒绝（5 API） | 核心数据正确性 + 发布阻塞安全项 |
| P1（核心） | heatmap/run-analysis/project-alloc-trend 功能、时间参数校验、projectId 过滤、权限守卫拦截 | 单点功能与校验完备性 |
| P2（补充） | UI 图表渲染细节、维度切换交互、抽屉/悬浮交互、无权限提示文案 | 体验性验证 |

## 6. 风险与约束

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| DEF-01（#114 open）越权未修复 | 越权用例按预期失败基线执行，发布结论受其影响（安全阻塞项） | 用例断言"应被拒绝"方向，失败即确认缺陷仍存在，形成修复验证闭环；报告结论按"暂不允许发布"口径 |
| DEF-02（#115 open）错误码未修复 | 4 个 API 时间校验用例失败 | 同上，按已知缺陷基线设计预期 40001 |
| 测试账号无 `npu_resource` 权限 | UI 手工用例全部 block（无法进入页面） | 依赖平台侧开通权限；未开通时报告明确标注 block 与原因，API 层用例补偿覆盖功能面 |
| beta 数据管道曾停更（08-23） | 数据类断言可能因数据缺失误报 | 复测已确认回填恢复；用例对数据断言采用"结构+非空"弱断言，数值精确断言仅在样本数据稳定时启用 |
| Issue 设计文档信息不足 | 功能基线依赖页面探索，存在范围遗漏风险 | 已经源码走读 + API 实测补全（requirement_analysis.md 第 3 节声明）；测试设计不覆盖探索中不存在的功能 |
| 数据敏感（服务器 IP/池名/任务名） | 响应内容包含基础设施信息 | 敏感信息防护维度检查响应是否超出运营数据范围；越权缺陷修复前数据泄露风险已知（#114） |

## 7. 依赖与前置条件

- 环境：beta（test）https://beta.openlibing.com（安全用例仅允许 test 环境，prod 强制跳过）
- 测试账号：`p_tianyan`（admin 系统角色，`npu_resource` 权限 false）；低权限对照账号 `pub_LIBING`（安全用例双身份模型）
- 凭证：`.env`（`SECURITY_HIGH_PRIV_*` / `SECURITY_LOW_PRIV_*`，不硬编码）
- projectId：300036（项目过滤用例）
- 样本数据：heatmap 有数据窗口（如 2026-08-22 ~ 2026-08-23）、有效 runId（e1dcd94695414ab6a2aad29bff37ad3c）
- UI 手工用例前置：平台侧为 `p_tianyan` 开通 `npu_resource` 权限（当前 false）
- 执行环境：Windows + pytest + Playwright；安全用例 `SECURITY_ENABLED=true` 且仅 test 环境

## 8. 版本历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0 | 2026-08-31 | mth | 初始版本（基于页面探索 + 端到端验证基线生成） |
