# 里程碑 CRUD 与事务修改日志实施计划

> 执行要求：按任务顺序使用 TDD；本轮用户明确要求全程不提交代码，因此不执行 commit、push、PR 或归档操作。

**目标：** 依据当前 `pq_milestone` DDL 交付字符串项目 ID 的里程碑增删改查接口，并以独立日志表强一致记录修改和删除快照。

**架构：** 沿用 `Controller → App Service → Domain Service → Mapper/MySQL`。App Service 负责白名单权限、token 用户、DTO、事务和公共 AOP 快照；Domain Service 负责持久化、唯一性和事务日志；独立 `pq_milestone_log` 不依赖 best-effort AOP。

**技术栈：** Java 21、Spring Boot、MyBatis-Plus、MySQL 8.0、JUnit 5、Mockito、AssertJ、standalone MockMvc。

---

## 0. 实施约束

- [x] 用户已确认设计，目标仓为 `openlibing-ops`，当前分支为 `yanhongbing_fork_01`。
- [x] 当前 SQL 是里程碑结构权威来源：无 `deleted`，有 `project_name`，`project_id` 为字符串。
- [x] 本轮不实现策划初始化、目录、其他策划表接口或旧项目成员角色矩阵。
- [ ] 不切换分支，不修改其他业务仓，不把 spec 文件加入业务仓。
- [ ] 全程不 commit、不 push、不创建 PR；每轮反馈后也只保留本地变更。
- [ ] 每个实现步骤先观察对应测试失败，再写最小实现并观察同一测试通过。

### Task 1：修正 DDL、里程碑模型与 Mapper 契约

**文件：**

- Modify: `openlibing-ops/src/main/resources/sql/V20261104__product_quality_planning.sql`
- Modify: `openlibing-ops/src/main/java/com/openlibing/ops/domain/model/productquality/PqMilestone.java`
- Create: `openlibing-ops/src/main/java/com/openlibing/ops/domain/model/productquality/PqMilestoneLog.java`
- Modify: `openlibing-ops/src/main/java/com/openlibing/ops/domain/mapper/productquality/PqMilestoneMapper.java`
- Create: `openlibing-ops/src/main/java/com/openlibing/ops/domain/mapper/productquality/PqMilestoneLogMapper.java`
- Modify: `openlibing-ops/src/main/resources/mapper/productquality/PqMilestoneMapper.xml`
- Modify: `openlibing-ops/src/test/java/com/openlibing/ops/infrastructure/sql/ProductQualityPlanningSqlTest.java`
- Modify: `openlibing-ops/src/test/java/com/openlibing/ops/domain/mapper/productquality/ProductQualityCoreMapperXmlTest.java`

**步骤：**

- [ ] RED：更新 SQL 契约测试，使表集合对应当前 DDL 加 `pq_milestone_log`；断言里程碑无 `deleted`、有 `project_name`，项目内名称唯一索引存在。
- [ ] RED：断言日志表严格包含 `id/milestone_id/old_data/new_data/update_by/update_time`，JSON 仅用于思维导图和日志新旧快照；删除旧 `pq_quality_plan` 唯一键假设。
- [ ] RED：更新 Mapper 契约，断言 `projectId` 为 `String`、里程碑包含 `projectName` 和自身审计字段、不使用 `@TableLogic`；断言查询/修改/删除带 `id + project_id` 且无 `deleted` 条件。
- [ ] 运行 `mvn "-Dtest=ProductQualityPlanningSqlTest,ProductQualityCoreMapperXmlTest" test`，确认新断言因实现未更新而失败。
- [ ] GREEN：修改 `pq_milestone` 唯一索引并新增日志表 DDL；不得 DROP 或重建已有业务表。
- [ ] GREEN：将 `PqMilestone` 改为匹配 DDL 的独立实体；新增日志实体和 MySQL Mapper，不继承 `BaseMapper`，在 XML 中显式实现 `insert` 等 SQL。
- [ ] GREEN：实现按项目查询、分页、按归属修改/物理删除及名称计数 SQL，全部参数绑定，所有表名添加 `openlibing_quality` 库名前缀，排序固定 `id DESC`。
- [ ] 重跑同一定向测试并确认通过。

### Task 2：实现 Domain Service 唯一性和事务日志持久化

**文件：**

- Create: `openlibing-ops/src/main/java/com/openlibing/ops/domain/service/productquality/ProductQualityMilestoneDomainService.java`
- Create: `openlibing-ops/src/test/java/com/openlibing/ops/domain/service/productquality/ProductQualityMilestoneDomainServiceTest.java`

**步骤：**

- [ ] RED：覆盖创建/详情/分页委托；跨项目或不存在记录按当前业务异常语义拒绝。
- [ ] RED：覆盖新增和修改为重复名称时拒绝，数据库并发唯一键冲突转换为业务参数异常。
- [ ] RED：覆盖修改日志的旧/新完整 JSON、删除日志旧 JSON 和 `newData=null`、创建不插日志、操作者和操作时间。
- [ ] RED：覆盖更新/删除影响行数不为 1 时不写日志，日志插入异常继续向外抛出以触发上层事务回滚。
- [ ] 运行 `mvn "-Dtest=ProductQualityMilestoneDomainServiceTest" test`，确认失败原因是领域服务尚不存在。
- [ ] GREEN：实现最小领域服务；修改/删除接收已按项目查询的旧实体，业务 SQL 和日志插入不捕获并吞掉异常。
- [ ] 重跑领域测试并确认通过。

### Task 3：实现 App Service 权限、事务、DTO 和公共审计快照

**文件：**

- Create: `openlibing-ops/src/main/java/com/openlibing/ops/api/request/productquality/MilestoneSaveReq.java`
- Create: `openlibing-ops/src/main/java/com/openlibing/ops/api/response/productquality/MilestoneResp.java`
- Create: `openlibing-ops/src/main/java/com/openlibing/ops/app/service/productquality/ProductQualityMilestoneService.java`
- Create: `openlibing-ops/src/test/java/com/openlibing/ops/app/service/productquality/ProductQualityMilestoneServiceTest.java`

**步骤：**

- [ ] RED：覆盖 `canRead/canWrite` 拒绝、token 用户写入审计人、请求体不能覆盖项目/主键/创建审计字段。
- [ ] RED：覆盖创建、详情、分页和修改响应完整映射；创建不写独立日志由 Domain Service 契约保证。
- [ ] RED：覆盖修改/删除先捕获旧公共快照、成功后捕获新快照；删除公共新快照为空。
- [ ] RED：反射断言创建/修改/删除具有 `@Transactional`，日志或持久化异常不被 App Service 吞掉。
- [ ] 运行 `mvn "-Dtest=ProductQualityMilestoneServiceTest" test`，确认失败。
- [ ] GREEN：实现强类型请求/响应和应用服务；写方法使用事务，权限复用现有服务，不增加项目角色逻辑。
- [ ] 重跑应用服务测试及 `ProductQualityPermissionServiceTest`，确认通过且无权限回归。

### Task 4：提供前端可调用的 Controller 接口

**文件：**

- Create: `openlibing-ops/src/main/java/com/openlibing/ops/api/controller/ProductQualityMilestoneController.java`
- Create: `openlibing-ops/src/test/java/com/openlibing/ops/api/controller/ProductQualityMilestoneControllerTest.java`

**步骤：**

- [ ] RED：用 standalone MockMvc 覆盖五个路由、统一 `Result/PageResult`、`@RequestParam` 参数传递和 JSON 时间字段，并断言不使用 `@PathVariable`。
- [ ] RED：覆盖项目名称、里程碑名称、计划时间必填，长度、正整数 ID、页码和页大小边界；无效请求不调用 Service。
- [ ] RED：反射确认 POST/PUT/DELETE 带公共 `@LogApi`，GET 不带写操作日志。
- [ ] 运行 `mvn "-Dtest=ProductQualityMilestoneControllerTest" test`，确认失败。
- [ ] GREEN：实现 `/projects/product-quality/milestones` 下 POST、GET 分页、GET `/detail`、PUT `/update`、DELETE `/delete`，`projectId` 和 `id` 均使用 `@RequestParam`。
- [ ] 重跑 Controller 测试并确认通过。

### Task 5：回归验证与交付

**文件：**

- Modify: 仅修复回归发现的本轮缺陷及对应测试，不做无关重构。

**步骤：**

- [ ] 运行 `mvn "-Dtest=ProductQualityMilestoneDomainServiceTest,ProductQualityMilestoneServiceTest,ProductQualityMilestoneControllerTest,ProductQualityPlanningSqlTest,ProductQualityCoreMapperXmlTest" test`，全部通过。
- [ ] 运行 `mvn "-Dtest=ProductQuality*Test" test`，完成 productquality 回归；若旧总体方案测试与当前 SQL 冲突，仅修正已确认过期契约，不扩展业务范围。
- [ ] 运行 `mvn spotless:apply`，再重跑上述定向测试，避免格式化后未验证。
- [ ] 运行 `mvn checkstyle:check` 和 `mvn -DskipTests compile`；记录实际结果，失败则修复本轮问题后重跑。
- [ ] 执行 `git diff --check` 和 `git status --short`，核对仅有本轮业务文件及三份 docs spec；确认没有凭证、无关格式化或 spec 混入业务仓。
- [ ] 如本机无可用 MySQL 8.0，明确记录未执行真实 DDL 和事务回滚集成验证，不声称数据库集成通过。
- [ ] 最终仅报告变更文件、测试证据、未验证项和“未提交代码”，进入用户自测，不自动进入 Phase 4/5。

## 完成定义

- [ ] 五个里程碑接口可用，项目归属、字段校验、白名单权限和服务端审计人正确。
- [ ] 同项目名称唯一；里程碑模型、Mapper 与当前 DDL 一致，无逻辑删除假设。
- [ ] 修改和删除分别写入正确新旧快照，日志失败可回滚；创建不写独立日志。
- [ ] 定向及 productquality 回归有实际执行证据，未执行项如实说明。
- [ ] 工作区保留全部本地修改，未产生 commit、push 或 PR。
