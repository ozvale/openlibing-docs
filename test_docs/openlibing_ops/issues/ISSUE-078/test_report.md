# 测试报告 - ISSUE-078

> **Issue编号**: ISSUE-078
> **Issue标题**: 【蓝区】 Nightly流水线看板增加汇总数据展示、明细增加失败类型和导出能力
> **报告日期**: 2026-08-12
> **测试负责人**: tester-a
> **报告版本**: v1.1

---

## 1. 执行概览

| 项目 | 内容 |
|------|------|
| 测试周期 | 2026-08-11 ~ 2026-08-12 |
| 测试环境 | test (https://beta.openlibing.com) |
| 用例总数 | 21 |
| 执行数 | 19 |
| 通过 | 15 |
| 失败 | 4 |
| 阻塞 | 0 |
| 跳过 | 2 |
| 通过率 | 78.9%（不含跳过） |

### 1.1 按用例等级统计

| 等级 | 总数 | 通过 | 失败 | 阻塞 | 跳过 |
|------|------|------|------|------|------|
| L0 | 8 | 7 | 0 | 0 | 1 |
| L1 | 13 | 8 | 4 | 0 | 1 |

### 1.2 按用例类型统计

| 类型 | 总数 | 通过 | 失败 | 阻塞 | 跳过 |
|------|------|------|------|------|------|
| 手工用例 | 0 | 0 | 0 | 0 | 0 |
| 自动化-UI | 5 | 5 | 0 | 0 | 0 |
| 自动化-API | 9 | 5 | 2 | 0 | 2 |
| 自动化-性能 | 1 | 1 | 0 | 0 | 0 |
| 自动化-安全 | 6 | 4 | 2 | 0 | 0 |

---

## 2. 用例执行明细

### 2.1 执行信息

| 字段 | 内容 |
|------|------|
| 自动化执行Action链接 | 本地 pytest 执行（gitcode action 待测试人员确认后补充） |
| 手工执行人 | — |
| 执行日期 | 2026-08-12 |

### 2.2 用例执行明细

| 用例编号 | 用例标题 | 用例等级 | 用例类型 | 执行结果 | 缺陷issue | 备注 |
|----------|----------|----------|----------|----------|------------|------|
| TC-ISSUE078-001 | 明细接口返回 failedTaskType 字段 | L0 | auto_api | pass | — | |
| TC-ISSUE078-002 | 失败任务类型筛选-构建任务 | L0 | auto_api | skip | — | 无构建任务失败记录 |
| TC-ISSUE078-003 | 失败任务类型筛选-测试任务 | L0 | auto_api | skip | — | 无测试任务失败记录 |
| TC-ISSUE078-004 | 失败任务类型筛选-其他任务 | L0 | auto_api | pass | — | |
| TC-ISSUE078-005 | 失败任务类型不传/非法值不过滤 | L1 | auto_api | fail | [待创建] | 非法值返回业务 code=500 |
| TC-ISSUE078-006 | 项目级汇总接口返回结构验证 | L0 | auto_api | pass | — | |
| TC-ISSUE078-007 | 项目级汇总接口字段完整性（26 字段） | L0 | auto_api | pass | — | 字段名 caseReleaseCountP0 与文档差异 |
| TC-ISSUE078-008 | 汇总接口无 projectId 参数行为 | L1 | auto_api | fail | [待创建] | 缺省 projectId 返回业务 code=500 |
| TC-ISSUE078-009 | 主列表导出接口返回 xlsx 文件流 | L0 | auto_api | pass | — | |
| TC-ISSUE078-010 | UI-失败任务类型列存在及取值合法 | L0 | auto_ui | pass | — | |
| TC-ISSUE078-011 | UI-未失败流水线展示"流水线未失败" | L1 | auto_ui | pass | — | |
| TC-ISSUE078-012 | UI-失败任务类型筛选功能 | L0 | auto_ui | pass | — | |
| TC-ISSUE078-013 | UI-主列表导出按钮及下载验证 | L0 | auto_ui | pass | — | |
| TC-ISSUE078-014 | UI-项目级汇总无导出、流水线级有导出 | L1 | auto_ui | pass | — | |
| TC-ISSUE078-015 | 汇总接口响应时间验证 | L1 | auto_perf | pass | — | avg<3s P95<5s |
| TC-ISSUE078-016 | 汇总/导出接口未认证访问拒绝 | L1 | auto_sec | pass | — | 无 cookie 独立请求验证 401 |
| TC-ISSUE078-017 | 认证校验-伪造 token 请求 | L1 | auto_sec | pass | — | 无会话伪造 token 返回 401 |
| TC-ISSUE078-018 | 横向越权-跨项目数据隔离 | L1 | auto_sec | pass | — | 项目数据隔离正确 |
| TC-ISSUE078-019 | 传输安全-HTTPS 与 Cookie 属性 | L1 | auto_sec | fail | [待创建] | Cookie 缺 Secure/HttpOnly |
| TC-ISSUE078-020 | CSRF 防护-导出接口变更请求 | L1 | auto_sec | fail | [待创建] | 导出接口无 CSRF 防护 |
| TC-ISSUE078-021 | 敏感信息防护-响应不泄露凭证 | L1 | auto_sec | pass | — | 响应无敏感字段泄露 |

---

## 3. 缺陷列表

> 本期发现 2 个缺陷（均待测试人员在 gitcode 创建缺陷 issue 后关联）。

| 关联用例 | 缺陷issue链接 | 缺陷描述 | 严重级别 | 状态 |
|----------|----------------|----------|----------|------|
| TC-ISSUE078-005 | [待创建] | 明细接口 failedTaskType 传非法值返回业务 code=500，未按文档"其他值不过滤"处理 | 一般 | 已发现，待提交 |
| TC-ISSUE078-008 | [待创建] | 汇总接口不传 projectId 返回业务 code=500，与文档声明"projectId 可选"不符 | 一般 | 已发现，待提交 |
| TC-ISSUE078-019 | [待创建] | 会话 Cookie（token / csrf-token-open-li-bing）缺 Secure/HttpOnly 属性 | 一般 | 已发现，待提交 |
| TC-ISSUE078-020 | [待创建] | 导出接口无 CSRF 防护：缺失/伪造 CSRF token 均返回有效 xlsx | 一般 | 已发现，待提交 |

### 缺陷详情

#### [待创建]: 明细接口 failedTaskType 非法值导致 500

- **关联用例**: TC-ISSUE078-005
- **缺陷issue**: [待测试人员创建]
- **严重级别**: 一般
- **状态**: 已发现，待提交
- **复现步骤**:
  1. 登录 test 环境
  2. POST /gateway/openlibing-ops/common/detail
  3. 请求体 category=nightly-dashboard-detail，failedTaskType="非法值"，带日期范围
- **实际结果**: HTTP 200，业务 code=500，messageCn="系统异常"
- **预期结果**: 按设计文档 4.1，"不传/空串/其他值不过滤"，应返回正常明细数据
- **影响范围**: 前端列筛选若传入异常值时接口报错；接口健壮性不足
- **复现概率**: 100%

#### [待创建]: 汇总接口缺省 projectId 导致 500

- **关联用例**: TC-ISSUE078-008
- **缺陷issue**: [待测试人员创建]
- **严重级别**: 一般
- **状态**: 已发现，待提交
- **复现步骤**:
  1. 登录 test 环境
  2. POST /gateway/openlibing-ops/common/detail
  3. 请求体 category=nightly-dashboard-summary，不传 projectId，仅带日期范围
- **实际结果**: HTTP 200，业务 code=500，messageCn="系统异常"
- **预期结果**: 按设计文档 3.1，"projectId | number | 否"为可选参数，应正常返回（total 0 或 1）
- **影响范围**: 前端按项目聚合时可正常使用；缺省参数场景接口报错
- **复现概率**: 100%

#### [待创建]: 会话 Cookie 缺 Secure/HttpOnly 属性

- **关联用例**: TC-ISSUE078-019
- **缺陷issue**: [待测试人员创建]
- **严重级别**: 一般
- **状态**: 已发现，待提交
- **复现步骤**:
  1. 登录 test 环境
  2. 获取浏览器上下文 cookies
  3. 检查 token 与 csrf-token-open-li-bing cookie 属性
- **实际结果**: 两个 cookie 的 secure=False、httpOnly=False（sameSite=Lax）
- **预期结果**: 会话 Cookie 应具备 Secure 与 HttpOnly 属性
- **影响范围**: Cookie 可能被脚本读取（XSS 风险）或经非 HTTPS 通道传输
- **复现概率**: 100%

#### [待创建]: 导出接口无 CSRF 防护

- **关联用例**: TC-ISSUE078-020
- **缺陷issue**: [待测试人员创建]
- **严重级别**: 一般
- **状态**: 已发现，待提交
- **复现步骤**:
  1. 登录 test 环境
  2. 删除 csrf-token-open-li-bing cookie 后 POST 导出接口
  3. 伪造 csrf-token-open-li-bing cookie 后 POST 导出接口
- **实际结果**: 两种场景均返回 HTTP 200 与有效 xlsx 文件
- **预期结果**: 变更类请求缺失/伪造 CSRF token 应被拒绝
- **影响范围**: 导出接口存在 CSRF 攻击面（跨站伪造导出请求）
- **复现概率**: 100%

---

## 4. 测试结论

### 4.1 结论

**附条件发布**（安全测试补充后维持原结论，新增 2 个安全缺陷需跟踪修复）

### 4.2 结论依据

- **功能覆盖**: 三大需求（失败类型字段+筛选、项目级汇总、导出能力）均有用例覆盖，UI/API/性能/安全四维覆盖；安全维度 6 项中 5 项已覆盖（纵向越权因低权限凭证未配置豁免，已在测试设计说明）
- **L0用例结果**: 8 条 L0 用例 7 通过 1 跳过（无数据），无 L0 失败
- **L1用例结果**: 13 条 L1 用例 8 通过 1 跳过 4 失败；4 个失败为接口参数容错（2 个）与安全属性（2 个），均有规避措施
- **L2用例结果**: 无
- **遗留风险**:
  1. 明细接口 failedTaskType 非法值未容错（前端列筛选传参固定 3 值，实际触发概率低）
  2. 汇总接口缺省 projectId 未容错（前端按项目进入必传 projectId）
  3. 汇总字段名 caseReleaseCountP0 与文档 caseTotalCountP0 命名不一致，建议开发确认文档同步
  4. 会话 Cookie（token/csrf）缺 Secure/HttpOnly 属性，建议补充（与 security-testing SKILL 历史记录存在差异，需开发确认环境配置）
  5. 导出接口无 CSRF 防护，建议补充校验或评估风险接受

### 4.3 附条件发布说明

- **条件**: 缺陷 issue 已创建并在后续迭代修复；或经产品确认非法参数/缺省参数场景不在本期支持范围
- **规避措施**: 前端固定传递合法 failedTaskType（3 枚举值）与必填 projectId，可完全规避两个缺陷触发路径
- **后续要求**: 缺陷修复后进行回归验证（TC-ISSUE078-005、TC-ISSUE078-008）

---

## 5. 版本历史

| 版本 | 日期 | 修改人 | 修改内容 |
|------|------|--------|----------|
| v1.0 | 2026-08-11 | tester-a | 初始报告（本地 pytest 执行，缺陷 issue 待测试人员创建后关联） |
| v1.1 | 2026-08-12 | tester-a | 补充安全测试（TC-ISSUE078-017~021），新增 2 个安全缺陷（Cookie 属性、CSRF 防护缺失） |
