# Product Quality Planning Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 在 openlibing-ops 中交付 Issue #328 的质量策划后端，包括项目里程碑、幂等策划初始化、三级目录、项目权限、17 类固定业务数据、批量删除和操作日志。

**Architecture:** 在既有 `api → app → domain → MyBatis/MySQL` 四层中增加 `productquality` 子包。采用 4 张核心表和 17 张固定业务表，以 App Service 统一身份、权限、事务和审计快照，以 Domain Service 统一资源归属和批量删除约束；不拆 Maven 子模块。

**Tech Stack:** Java 21、Spring Boot 3.4.5、MyBatis-Plus、MySQL 8.0、JUnit/Mockito、OWASP Java HTML Sanitizer。

---

## 0. 实施约束与输入

开始编码前必须再次确认：

- [ ] 用户已批准 `proposal.md`、`design.md`、`threat-model.md`、`security-design.md` 和本计划。
- [ ] 业务仓为 `openlibing-ops`，当前分支为 `yanhongbing_main_01`，工作区无与本需求冲突的未提交修改。
- [ ] 不切换分支、不创建顶层 `com.openlibing.ops.productquality` 包、不把 spec 文件放入业务仓。
- [ ] 每轮编码完成立即提交一次；每个 commit 新增+删除不超过 1000 行，超出则停止并报告，不能强行提交。
- [ ] 不自动 `git push`，不创建业务 PR；用户自测明确确认后才进入 Phase 4。
- [ ] 每轮遵循 TDD：先写失败测试并观察失败，再写最小实现，再运行同一测试确认通过。

设计基线：

- 字段、表名、目录和 API：`task_design/feat-product-quality-planning/design.md`。
- 验收范围：`task_design/feat-product-quality-planning/proposal.md`。
- SEC-1～SEC-10：`system_design/feat-product-quality-planning/security-design.md`。

### 通用验证与提交步骤

每个 Task 的“提交”都包含以下动作，不省略：

1. 运行 `mvn spotless:apply`，然后重新检查并暂存格式化后的文件。
2. 运行本 Task 指定的定向测试，预期全部 PASS。
3. 运行 `git diff --check`，预期无输出。
4. 只暂存本 Task 文件，使用以下 PowerShell 统计暂存行数：

```powershell
$lines = git diff --cached --numstat
$add = 0; $del = 0
foreach ($line in $lines) {
  $parts = $line -split "`t"
  $add += [int]$parts[0]; $del += [int]$parts[1]
}
"Staged lines: $($add + $del) (+$add -$del)"
```

5. 总行数大于 1000 时停止，中文报告并拆分；不超过 1000 才提交。
6. commit body 关联 `Refs #328`，并带以下 trailer：

```text
Co-authored-by: Trae <noreply@trae.ai>
Generated-by: kimi-k3.1-pro
```

7. 每轮结束展示 commit hash、测试结果、变更行数和尚未实现的范围。

---

### Task 1: 建立 21 张表的数据库脚本

**Files:**
- Create: `src/main/resources/sql/V20261104__product_quality_planning.sql`
- Test: `src/test/java/com/openlibing/ops/infrastructure/sql/ProductQualityPlanningSqlTest.java`

**Steps:**

- [ ] 编写失败测试：读取 SQL 资源，断言 4 张核心表和 17 张业务表全部存在，且表集合精确等于 design.md，不多不少。
- [ ] 断言所有表都有 `id/create_by/create_time/update_by/update_time/deleted`；所有策划业务表都有 `project_id/plan_id`；断言 `pq_quality_plan` 有 `(milestone_id, deleted)` 唯一键。
- [ ] 运行 `mvn "-Dtest=ProductQualityPlanningSqlTest" test`，预期因 SQL 资源不存在而 FAIL。
- [ ] 按 design.md 第 4 节逐列编写完整 DDL，不使用 JSON 列替代固定业务字段；只有 `pq_quality_mindmap.mindmap_json` 使用 JSON。
- [ ] 为所有外查路径建立 `(project_id, plan_id, deleted, id)` 或对应核心表索引，添加表和列注释，不写 `DROP TABLE`、真实账号或环境地址。
- [ ] 重跑测试，预期 21 张表、公共字段和唯一键检查全部 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add quality planning database schema`。

---

### Task 2: 实现 token-only 身份和权限决策（SEC-1、SEC-2）

**Files:**
- Modify: `src/main/java/com/openlibing/ops/infrastructure/util/UserUtil.java`
- Create: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityUserAdapter.java`
- Create: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityPermissionService.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqProjectQualityOwner.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqProjectQualityOwnerMapper.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/ProductQualityPermissionMapper.java`
- Create: `src/main/resources/mapper/productquality/ProductQualityPermissionMapper.xml`
- Test: `src/test/java/com/openlibing/ops/infrastructure/util/UserUtilTest.java`
- Test: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityPermissionServiceTest.java`
- Test: `src/test/java/com/openlibing/ops/domain/mapper/productquality/ProductQualityPermissionMapperXmlTest.java`

**Steps:**

- [ ] 写身份失败测试：无 Cookie、无效 token、空 userId 均拒绝；只有 query `userId` 时仍拒绝；有效 token 返回其用户 ID；原 `currentUserId` 行为不变。
- [ ] 写权限矩阵失败测试，逐项覆盖匿名、非成员、普通成员、质量负责人、项目管理员、全局管理员，以及权限 Mapper 抛异常时默认拒绝。
- [ ] 运行 `mvn "-Dtest=UserUtilTest,ProductQualityPermissionServiceTest,ProductQualityPermissionMapperXmlTest" test`，预期相关测试 FAIL。
- [ ] 将当前私有 JWT Cookie 解析逻辑复用到新的公开 token-only 方法，不复制 JWT 算法，不修改原方法签名和行为。
- [ ] 权限服务按“身份 → 项目归属 → 管理员 → 质量负责人”判定；读复用 `ResourcePermissionService`，写和管理分别提供独立 public 方法。
- [ ] XML 全局角色与现有权限 SQL 一致，项目管理员使用 project 类型及 project_id 匹配；所有值参数绑定，owner 查询只读 `deleted = 0`。
- [ ] 重跑定向测试，预期全部 PASS，尤其 query 身份不能获得任何权限。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add identity and permission guards`。

---

### Task 3: 建立核心模型、Mapper 和三级目录模板

**Files:**
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqBaseModel.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqMilestone.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqQualityPlan.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqPlanCatalog.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqMilestoneMapper.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqQualityPlanMapper.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqPlanCatalogMapper.java`
- Create: `src/main/resources/mapper/productquality/PqMilestoneMapper.xml`
- Create: `src/main/resources/mapper/productquality/PqQualityPlanMapper.xml`
- Create: `src/main/resources/mapper/productquality/PqPlanCatalogMapper.xml`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/ProductQualityCatalogTemplate.java`
- Test: `src/test/java/com/openlibing/ops/domain/service/productquality/ProductQualityCatalogTemplateTest.java`
- Test: `src/test/java/com/openlibing/ops/domain/mapper/productquality/ProductQualityCoreMapperXmlTest.java`

**Steps:**

- [ ] 编写目录失败测试：模板覆盖 design.md 第 5 节全部叶子和可选节点，`templateCode` 唯一、同级 `sortNo` 连续、所有节点层级为 1～3。
- [ ] 断言版本级要求、三类交付件和其他专项为 `DIRECTORY` 且 `tableKey = null`；15 个表格叶子有精确 `tableKey`；知识输入/输出为第三级。
- [ ] 运行 `mvn "-Dtest=ProductQualityCatalogTemplateTest,ProductQualityCoreMapperXmlTest" test`，预期 FAIL。
- [ ] 实现公共审计模型、核心实体和 Mapper；所有查询带 `deleted = 0`，策划查询同时支持 `id + project_id` 和 `milestone_id + project_id`。
- [ ] 用不可变 Java 模板定义目录，初始化时复制为 `PqPlanCatalog`，不把模板做成数据库可变配置。
- [ ] 重跑定向测试，预期全部 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add core models and catalog template`。

---

### Task 4: 实现通用写操作审计快照（SEC-7）

**Files:**
- Create: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityAuditPayload.java`
- Create: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityAuditSupport.java`
- Create: `src/main/java/com/openlibing/ops/infrastructure/aop/productquality/ProductQualityLogSnapshot.java`
- Create: `src/main/java/com/openlibing/ops/infrastructure/aop/productquality/ProductQualityLogHandler.java`
- Test: `src/test/java/com/openlibing/ops/infrastructure/aop/productquality/ProductQualityLogHandlerTest.java`
- Test: `src/test/java/com/openlibing/ops/infrastructure/aop/productquality/ProductQualityLogSnapshotTest.java`

**Steps:**

- [ ] 写失败测试：新增时 old 为空/new 为实体；修改保留 old/new；删除 new 为空；批量保存旧列表；失败操作不伪造成功 new；请求结束后快照被清理。
- [ ] 写敏感信息测试：快照序列化不包含 token、Cookie、HttpServletRequest、数据库配置和完整 HTTP 报文。
- [ ] 运行 `mvn "-Dtest=ProductQualityLogHandlerTest,ProductQualityLogSnapshotTest" test`，预期 FAIL。
- [ ] 实现请求级白名单 payload，App Service 在修改前冻结 old、成功后冻结 new；Handler `after` 一次性消费并调用 `OperationLogHandlerSupport.applySnapshot` 或等价现有能力。
- [ ] Handler 只匹配质量管理写请求，不能影响 `DashboardCommonLogHandler`；日志异常按现有框架策略处理且不暴露内部细节。
- [ ] 重跑审计测试及 `DashboardCommonLogHandlerTest`，预期全部 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add operation audit snapshots`。

---

### Task 5: 交付里程碑 CRUD 和删除约束

**Files:**
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/MilestoneSaveReq.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/MilestoneResp.java`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/ProductQualityMilestoneDomainService.java`
- Create: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityMilestoneService.java`
- Create: `src/main/java/com/openlibing/ops/api/controller/productquality/ProductQualityMilestoneController.java`
- Test: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityMilestoneServiceTest.java`
- Test: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualityMilestoneControllerTest.java`

**Steps:**

- [ ] 写失败测试：成员可读、普通成员写 403；名称/计划时间必填；创建返回 `planInitialized=false` 和 `initializationRequired=true`。
- [ ] 写归属与删除测试：跨项目读写拒绝；未初始化可逻辑删除；已有策划拒绝删除；每次成功写操作有正确 old/new 快照。
- [ ] 运行 `mvn "-Dtest=ProductQualityMilestoneServiceTest,ProductQualityMilestoneControllerTest" test`，预期 FAIL。
- [ ] 实现 design.md 第 6.1 节里程碑路由；服务端写审计人，所有 Mapper 条件带项目 ID，不提供策划级联删除。
- [ ] 重跑测试，预期 PASS；再跑 Task 2/4 权限与日志测试，预期无回归。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add project milestone APIs`。

---

### Task 6: 交付显式幂等策划初始化与目录查询（SEC-4）

**Files:**
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/QualityPlanInitializeReq.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/QualityPlanResp.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/ProductQualityCatalogResp.java`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/ProductQualityPlanDomainService.java`
- Create: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityPlanService.java`
- Create: `src/main/java/com/openlibing/ops/api/controller/productquality/ProductQualityPlanController.java`
- Test: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityPlanServiceTest.java`
- Test: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualityPlanControllerTest.java`

**Steps:**

- [ ] 写初始化失败测试：首次创建一份策划和完整目录；重复调用返回相同 planId 且目录数量不变；跨项目里程碑拒绝。
- [ ] 写事务测试：任一目录插入失败全部回滚；并发唯一键冲突只对该特定冲突重查并返回，其他数据库异常不能伪装为幂等成功。
- [ ] 写目录树测试：响应最大三级、排序稳定、目录-only 节点没有业务路由。
- [ ] 运行 `mvn "-Dtest=ProductQualityPlanServiceTest,ProductQualityPlanControllerTest" test`，预期 FAIL。
- [ ] 实现 `POST /plans/initialize`、`GET /milestones/{milestoneId}/plan`、`GET /plans/{planId}/catalog`，初始化不在里程碑创建方法中自动触发。
- [ ] 重跑测试，预期 PASS，并验证初始化日志 old/new 快照。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add idempotent plan initialization`。

---

### Task 7: 交付权限查询和质量负责人维护

**Files:**
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/QualityOwnerUpdateReq.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/ProductQualityPermissionResp.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/QualityOwnerResp.java`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/ProductQualityOwnerDomainService.java`
- Create: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityOwnerService.java`
- Modify: `src/main/java/com/openlibing/ops/api/controller/productquality/ProductQualityPlanController.java`
- Test: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityOwnerServiceTest.java`
- Modify: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualityPlanControllerTest.java`

**Steps:**

- [ ] 写失败测试：成员可查看自身 `canRead/canWrite/canManageOwners`；负责人可写但 `canManageOwners=false`。
- [ ] 写维护测试：普通成员和质量负责人维护均 403；非项目成员不能加入；目标列表去重；移除、增加、已删除后恢复在一个事务完成。
- [ ] 写回滚测试：任一目标用户不合法或数据库失败，原负责人集合保持不变；日志保存旧/新集合。
- [ ] 运行 `mvn "-Dtest=ProductQualityOwnerServiceTest,ProductQualityPlanControllerTest" test`，预期 FAIL。
- [ ] 实现 `GET /permissions`、`GET /quality-owners`、`PUT /quality-owners`，禁止通过请求体指定 projectId 或自我提权。
- [ ] 重跑测试和 Task 2 权限矩阵，预期 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): manage project quality owners`。

---

### Task 8: 建立策划明细公共归属、分页和批量删除支撑（SEC-3、SEC-4、SEC-6）

**Files:**
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqPlanItemModel.java`
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/PageQueryReq.java`
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/BatchDeleteReq.java`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/ProductQualityPlanItemServiceSupport.java`
- Test: `src/test/java/com/openlibing/ops/domain/service/productquality/ProductQualityPlanItemServiceSupportTest.java`

**Steps:**

- [ ] 写失败测试：跨项目 plan、跨项目执行 milestone、跨 plan 记录均拒绝；修改不能改变 projectId/planId/createBy/createTime。
- [ ] 写分页/批量参数测试：页码、页大小、空 ID、超过 200、重复 ID 的规则明确；重复 ID 去重后执行。
- [ ] 写原子删除测试：任一 ID 不存在、已删除、跨策划或影响行数不足时整体回滚；成功时只逻辑删除当前策划记录。
- [ ] 运行 `mvn "-Dtest=ProductQualityPlanItemServiceSupportTest" test`，预期 FAIL。
- [ ] 实现公共支撑；Mapper 更新/删除必须同时带 `project_id + plan_id + id + deleted = 0`，需要锁定的批量查询使用 `FOR UPDATE`。
- [ ] 重跑测试，预期 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add scoped plan item operations`。

---

### Task 9: 交付版本摘要与质量策划思路（SEC-5、SEC-8）

**Files:**
- Modify: `pom.xml`
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/VersionSummarySaveReq.java`
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/QualityMindmapSaveReq.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/VersionSummaryResp.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/QualityMindmapResp.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqVersionSummary.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqQualityMindmap.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqVersionSummaryMapper.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqQualityMindmapMapper.java`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/ProductQualityContentDomainService.java`
- Create: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityContentService.java`
- Create: `src/main/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepOneController.java`
- Create: `src/main/resources/mapper/productquality/PqVersionSummaryMapper.xml`
- Create: `src/main/resources/mapper/productquality/PqQualityMindmapMapper.xml`
- Test: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityContentServiceTest.java`
- Test: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepOneControllerTest.java`

**Steps:**

- [ ] 写失败测试：未保存 GET 返回 null；PUT 幂等更新同一有效记录；普通成员写 403；跨项目 plan 拒绝。
- [ ] 写 XSS 测试覆盖 script、事件属性、iframe、javascript URL 和安全表格/链接保留；写 JSON 非法、超大、超深测试。
- [ ] 运行 `mvn "-Dtest=ProductQualityContentServiceTest,ProductQualityStepOneControllerTest" test`，预期 FAIL。
- [ ] 在 pom 固定 OWASP Sanitizer 版本，检查依赖树和许可证；实现白名单清理，禁止退回原样存储 HTML。
- [ ] 实现两个单条资源 GET/PUT，清理后的摘要才入库和进入审计快照；思维导图仅作为 JSON 数据处理。
- [ ] 重跑测试，预期 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add summary and mindmap planning`。

---

### Task 10: 交付内部改进和历史经验表格

**Files:**
- Create: `api/request/productquality/InternalImprovementSaveReq.java`、`HistoricalExperienceSaveReq.java`（完整路径前缀均为 `src/main/java/com/openlibing/ops/`）
- Create: `api/response/productquality/InternalImprovementResp.java`、`HistoricalExperienceResp.java`
- Create: `domain/model/productquality/PqInternalImprovement.java`、`PqHistoricalExperience.java`
- Create: `domain/mapper/productquality/PqInternalImprovementMapper.java`、`PqHistoricalExperienceMapper.java`
- Create: `domain/service/productquality/PqInternalImprovementService.java`、`PqHistoricalExperienceService.java`
- Create: `resources/mapper/productquality/PqInternalImprovementMapper.xml`、`PqHistoricalExperienceMapper.xml`（前缀为 `src/main/`）
- Modify: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityStepOneService.java`（不存在则创建）
- Modify: `src/main/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepOneController.java`
- Test: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityStepOneServiceTest.java`
- Modify: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepOneControllerTest.java`

**Steps:**

- [ ] 为两类资源分别写 CRUD 失败测试，覆盖 design.md 所有字段、必填、进展 0/100 与越界、同项目其他 milestone 允许、跨项目 milestone 拒绝。
- [ ] 写六种表格端点契约测试：分页列表、新增、详情、修改、单删、批量删除；批量含一个跨 plan ID 时全部不变。
- [ ] 运行 `mvn "-Dtest=ProductQualityStepOneServiceTest,ProductQualityStepOneControllerTest" test`，预期 FAIL。
- [ ] 按 design.md 字段表实现两个垂直切片，复用 Task 8 支撑，不使用 Map/JsonNode 代替 DTO，所有写操作接入审计快照。
- [ ] 重跑测试，预期 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add step one improvement planning`。

---

### Task 11: 交付价值特性和策划输入分析表格

**Files:**
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/ValueFeatureSaveReq.java`、`InputAnalysisSaveReq.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/ValueFeatureResp.java`、`InputAnalysisResp.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqValueFeature.java`、`PqInputAnalysis.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqValueFeatureMapper.java`、`PqInputAnalysisMapper.java`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/PqValueFeatureService.java`、`PqInputAnalysisService.java`
- Create: `src/main/resources/mapper/productquality/PqValueFeatureMapper.xml`、`PqInputAnalysisMapper.xml`
- Modify: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityStepOneService.java`
- Modify: `src/main/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepOneController.java`
- Modify: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityStepOneServiceTest.java`
- Modify: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepOneControllerTest.java`

**Steps:**

- [ ] 按 Task 10 的测试矩阵为两类资源写失败测试，额外覆盖布尔字段可空、名称/输入描述/视角/小类/质量策略必填。
- [ ] 运行同一定向测试，预期 FAIL。
- [ ] 实现两个垂直切片和六种端点，未定义类型/来源/视角字典一律使用字符串。
- [ ] 重跑 Step1 全部测试，预期四个表格和两个单条内容资源全部 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add feature and input planning`。

---

### Task 12: 交付目标差距分析及分解

**Files:**
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/QualityObjectiveSaveReq.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/QualityObjectiveResp.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqQualityObjective.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqQualityObjectiveMapper.java`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/PqQualityObjectiveService.java`
- Create: `src/main/resources/mapper/productquality/PqQualityObjectiveMapper.xml`
- Create: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityStepTwoService.java`
- Create: `src/main/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepTwoController.java`
- Test: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityStepTwoServiceTest.java`
- Test: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepTwoControllerTest.java`

**Steps:**

- [ ] 写覆盖全部 26 个 Issue 字段的 DTO/持久化映射失败测试，防止漏列和 snake/camel 错配。
- [ ] 写必填、进展、执行里程碑、六种端点、批量原子性和日志快照失败测试；目标达成结果不由后端自动计算。
- [ ] 运行 `mvn "-Dtest=ProductQualityStepTwoServiceTest,ProductQualityStepTwoControllerTest" test`，预期 FAIL。
- [ ] 实现目标策划垂直切片，目标值/实际值保持字符串，不虚构达成状态枚举。
- [ ] 重跑测试，预期 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add quality objective planning`。

---

### Task 13: 交付风险策划

**Files:**
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/QualityRiskSaveReq.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/QualityRiskResp.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqQualityRisk.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqQualityRiskMapper.java`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/PqQualityRiskService.java`
- Create: `src/main/resources/mapper/productquality/PqQualityRiskMapper.xml`
- Modify: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityStepTwoService.java`
- Modify: `src/main/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepTwoController.java`
- Modify: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityStepTwoServiceTest.java`
- Modify: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepTwoControllerTest.java`

**Steps:**

- [ ] 写 WHY/WHO/HOW/WHAT/应对措施必填、全部字段映射、六种端点及批量回滚失败测试。
- [ ] 验证发生概率、影响程度、风险等级原样保存，不自动推导；QCC 仅保存布尔值。
- [ ] 运行 Step2 定向测试，预期 FAIL。
- [ ] 实现风险策划垂直切片并接入公共权限、归属和日志。
- [ ] 重跑 Step2 全部测试，预期 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add quality risk planning`。

---

### Task 14: 交付度量指标和评估策划

**Files:**
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/MetricPlanSaveReq.java`、`EvaluationPlanSaveReq.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/MetricPlanResp.java`、`EvaluationPlanResp.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqMetricPlan.java`、`PqEvaluationPlan.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqMetricPlanMapper.java`、`PqEvaluationPlanMapper.java`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/PqMetricPlanService.java`、`PqEvaluationPlanService.java`
- Create: `src/main/resources/mapper/productquality/PqMetricPlanMapper.xml`、`PqEvaluationPlanMapper.xml`
- Create: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityStepThreeService.java`
- Create: `src/main/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepThreeController.java`
- Test: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityStepThreeServiceTest.java`
- Test: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepThreeControllerTest.java`

**Steps:**

- [ ] 为两类资源写字段映射、六种端点、归属、批量和日志失败测试；评估策划七个 `*` 字段逐一验证。
- [ ] 验证指标算法只保存不执行，目标/实际值不自动计算，作业平台字段不触发外部请求。
- [ ] 运行 `mvn "-Dtest=ProductQualityStepThreeServiceTest,ProductQualityStepThreeControllerTest" test`，预期 FAIL。
- [ ] 实现两个垂直切片；版本级要求和三类交付件不得出现伪造 CRUD 路由。
- [ ] 重跑测试，预期 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add metric and evaluation planning`。

---

### Task 15: 交付会议运作和状态报告制度

**Files:**
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/MeetingOperationSaveReq.java`、`StatusReportSaveReq.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/MeetingOperationResp.java`、`StatusReportResp.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqMeetingOperation.java`、`PqStatusReport.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqMeetingOperationMapper.java`、`PqStatusReportMapper.java`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/PqMeetingOperationService.java`、`PqStatusReportService.java`
- Create: `src/main/resources/mapper/productquality/PqMeetingOperationMapper.xml`、`PqStatusReportMapper.xml`
- Create: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityStepFourService.java`
- Create: `src/main/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepFourController.java`
- Test: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityStepFourServiceTest.java`
- Test: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepFourControllerTest.java`

**Steps:**

- [ ] 为两类资源写完整字段映射、六种端点、执行里程碑、批量原子性和日志失败测试。
- [ ] 运行 `mvn "-Dtest=ProductQualityStepFourServiceTest,ProductQualityStepFourControllerTest" test`，预期 FAIL。
- [ ] 实现两个垂直切片，人员列表按文本保存，不新增未要求的人员系统集成。
- [ ] 重跑测试，预期 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add organization operation planning`。

---

### Task 16: 交付知识输入和知识输出

**Files:**
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/KnowledgeInputSaveReq.java`、`KnowledgeOutputSaveReq.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/KnowledgeInputResp.java`、`KnowledgeOutputResp.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqKnowledgeInput.java`、`PqKnowledgeOutput.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqKnowledgeInputMapper.java`、`PqKnowledgeOutputMapper.java`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/PqKnowledgeInputService.java`、`PqKnowledgeOutputService.java`
- Create: `src/main/resources/mapper/productquality/PqKnowledgeInputMapper.xml`、`PqKnowledgeOutputMapper.xml`
- Modify: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityStepFourService.java`
- Modify: `src/main/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepFourController.java`
- Modify: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityStepFourServiceTest.java`
- Modify: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualityStepFourControllerTest.java`

**Steps:**

- [ ] 写全部 `*` 字段、六种端点、归属、批量和日志失败测试。
- [ ] 写 `resource_link` 的 http/https 允许及 javascript/file/ftp 等拒绝测试；Mock 验证后端从不请求该链接。
- [ ] 运行 Step4 定向测试，预期 FAIL。
- [ ] 实现两个垂直切片，姓名+工号保持 Issue 原始文本，不拆成未定义字段。
- [ ] 重跑 Step4 全部测试，预期 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add knowledge management planning`。

---

### Task 17: 交付特性专项和工程能力专项

**Files:**
- Create: `src/main/java/com/openlibing/ops/api/request/productquality/FeaturePlanSaveReq.java`、`EngineeringStageSaveReq.java`、`EngineeringCheckSaveReq.java`
- Create: `src/main/java/com/openlibing/ops/api/response/productquality/FeaturePlanResp.java`、`EngineeringStageResp.java`、`EngineeringCheckResp.java`
- Create: `src/main/java/com/openlibing/ops/domain/model/productquality/PqFeaturePlan.java`、`PqEngineeringStage.java`、`PqEngineeringCheck.java`
- Create: `src/main/java/com/openlibing/ops/domain/mapper/productquality/PqFeaturePlanMapper.java`、`PqEngineeringStageMapper.java`、`PqEngineeringCheckMapper.java`
- Create: `src/main/java/com/openlibing/ops/domain/service/productquality/PqFeaturePlanService.java`、`PqEngineeringStageService.java`、`PqEngineeringCheckService.java`
- Create: `src/main/resources/mapper/productquality/PqFeaturePlanMapper.xml`、`PqEngineeringStageMapper.xml`、`PqEngineeringCheckMapper.xml`
- Create: `src/main/java/com/openlibing/ops/app/service/productquality/ProductQualitySpecialPlanService.java`
- Create: `src/main/java/com/openlibing/ops/api/controller/productquality/ProductQualitySpecialPlanController.java`
- Test: `src/test/java/com/openlibing/ops/app/service/productquality/ProductQualitySpecialPlanServiceTest.java`
- Test: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualitySpecialPlanControllerTest.java`

**Steps:**

- [ ] 为三类资源写完整字段映射、六种端点、归属、批量和日志失败测试。
- [ ] 验证需求来源、SIG、β/Final、majun 状态均为数据字段，不增加外部调用；其他专项只有目录，没有 CRUD。
- [ ] 运行 `mvn "-Dtest=ProductQualitySpecialPlanServiceTest,ProductQualitySpecialPlanControllerTest" test`，预期 FAIL。
- [ ] 实现三个垂直切片；若暂存行数预计超过 1000，先将特性专项单独提交，再提交两个工程能力表格，不能超限。
- [ ] 重跑测试，预期 PASS。
- [ ] 执行通用验证与提交，建议主题：`feat(productquality): add optional special planning`。

---

### Task 18: 全量契约、安全和质量回归

**Files:**
- Create: `src/test/java/com/openlibing/ops/domain/mapper/productquality/ProductQualityMapperXmlContractTest.java`
- Create: `src/test/java/com/openlibing/ops/api/controller/productquality/ProductQualityApiContractTest.java`
- Modify: 仅修改回归发现的本模块缺陷及对应测试，不做无关重构。

**Steps:**

- [ ] 增加契约测试：15 个表格资源各有六种端点，2 个单条资源各有 GET/PUT；目录-only 节点无业务表和路由；17 个实体与 17 张业务表一一对应。
- [ ] 用两个项目、两个里程碑完成成员/负责人/管理员、跨项目 IDOR、跨里程碑引用、初始化和批量删除集成回归。
- [ ] 在可用 MySQL 8.0 测试 schema 手动执行 SQL，验证 21 张表、字段、索引、唯一键和 utf8mb4；若本机无 MySQL，明确记录未执行项，不能声称集成验证通过。
- [ ] 运行 `mvn "-Dtest=ProductQuality*Test" test`，预期全部 PASS。
- [ ] 依次运行以下完整门禁，任何失败先修复再重跑，不能跳过：

```powershell
mvn spotless:apply
mvn checkstyle:check
mvn spotbugs:check
mvn pmd:check
mvn test
```

- [ ] 按 SEC-1～SEC-10 做代码安全复核，检查依赖漏洞/许可证、日志无凭证、SQL 参数化、XSS、越权和失败回滚；SEC-9 部署项单独记录 beta/生产待验证证据。
- [ ] 检查 `git diff --check`、工作区状态和业务仓文件清单，确认没有 spec 文档、真实配置、凭证或无关格式化进入业务仓。
- [ ] 若本 Task 有代码修改，执行通用验证与提交，建议主题：`test(productquality): add full planning contract coverage`；若无修改，不创建空提交。
- [ ] 交付最终本地验证报告和 commit 清单，进入用户自测/反馈循环；不得自动 push 或创建 PR。

---

## 完成定义

只有同时满足以下条件才可向用户声明“编码完成，待自测”：

- [ ] proposal.md 中所有本期验收项均有实现和对应测试证据。
- [ ] 21 张表、完整目录、15 个表格资源、2 个单条内容资源和权限/日志全部交付。
- [ ] 全量 Maven 测试和静态检查实际执行并 PASS；未执行的 MySQL/部署验证明确标注，不能伪造。
- [ ] 每个 commit 不超过 1000 行，所有 commit 有规范关联和 AI trailer。
- [ ] 用户尚未自测前，不创建业务 PR，不宣称验收完成。
