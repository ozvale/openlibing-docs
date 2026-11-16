# 质量管理-质量策划模块技术设计

## 1.4 本轮内部改进要求和重点工作增量设计（2026-11-07，优先于后文）

### 数据模型与接口

采用独立强类型表格资源，沿用 `Controller → App Service → Domain Service → Mapper/MySQL`，不引入通用 Map CRUD，也不依赖旧规划的 `planId`。

- `PqInternalImprovement` 继承 `PqBaseModel`，字段为 `projectId/milestoneId/milestoneName/category/name/improvementTarget/implementationMeasure/ownerName/plannedFinishTime/status/progress/progressDescription`；`projectId` 为 `Integer`，`progress` 为 `BigDecimal`，计划完成时间按当前 DDL 使用字符串。
- 新增 `pq_internal_improvement_log`：`id/internal_improvement_id/old_data/new_data/update_by/update_time`，索引 `(internal_improvement_id, update_time)`。业务表与日志表均使用 `openlibing_quality` 库名前缀，Mapper SQL 显式声明且仅使用参数绑定。
- `InternalImprovementSaveReq` 仅接收业务字段；`InternalImprovementResp` 返回完整业务字段和审计字段；`BatchDeleteReq` 接收非空、最多 200 项的 ID 列表。

| 方法 | 相对路径        | Query 参数                  | 成功响应                                      |
| ---- | --------------- | --------------------------- | --------------------------------------------- |
| POST | `/add`          | `milestoneId`               | `Result<InternalImprovementResp>`             |
| GET  | `/getPage`      | `milestoneId/page/pageSize` | `Result<PageResult<InternalImprovementResp>>` |
| GET  | `/detail`       | `milestoneId/id`            | `Result<InternalImprovementResp>`             |
| POST | `/update`       | `milestoneId/id`            | `Result<InternalImprovementResp>`             |
| GET  | `/delete`       | `milestoneId/id`            | `Result<Void>`                                |
| POST | `/batch-delete` | `milestoneId`               | `Result<Void>`，body 为 ID 列表               |

统一基础路径为 `/projects/product-quality/internal-improvements`。分页默认 `1/20`，`pageSize<=200`，列表固定 `id DESC`。新增时校验里程碑存在并生成项目归属；详情、修改和删除均固定 `milestone_id + id + deleted=0` 条件。修改为全量覆盖可编辑字段，保留归属和创建审计字段。

### 事务与日志

App Service 负责权限、token 用户、DTO、事务和公共审计快照；Domain Service 负责持久化、归属校验、批量完整性和独立日志。修改先查询旧实体，再更新并插入旧/新 JSON；单条删除按里程碑读取目标后逻辑删除并插入旧 JSON，批量删除先锁定当前里程碑的全部目标记录，数量不一致即拒绝，再逐条更新 `deleted=1` 并插入旧 JSON、`new_data=NULL`。所有写操作影响行数必须为 1，日志异常向外传播以回滚事务。

### 测试与交付约束

按 Standard 模式采用 RED → GREEN → REFACTOR，覆盖 SQL/Mapper 契约、Domain CRUD 和日志、App 权限/归属/DTO/事务、Controller 路由和参数校验。运行定向测试、`ProductQuality*Test` 回归、格式化、checkstyle、SpotBugs、PMD 和全量测试；无真实 MySQL 时明确未执行数据库事务集成验证。最终使用中文提交并推送当前分支，不创建 PR。

## 1. 设计依据与现状约束

- 需求：Issue [#328](https://gitcode.com/openlibing/openlibing-ops/issues/328)。
- 技术栈：Java 21、Spring Boot、MyBatis-Plus、MySQL 8.0，统一返回 `Result<T>` / `PageResult<T>`。
- 持久化模型遵循当前代码，放在 `domain/model`，不使用 `infrastructure/entity` 代替业务模型。
- 复用 `ResourcePermissionService` 的项目归属查询、`user_role_info` / `role_type_info` 权限数据、MyBatis 审计时间填充和 `openlibing-common` 操作日志链路。
- 当前权限库没有里程碑主数据，本需求新增；不修改其他项目已有表。
- 当前 `ResourcePermissionMapper` 只证明项目归属，不能直接表达“项目质量负责人”，需新增模块内权限查询。
- 当前权限设计文档将 `role_type_info.type = 'project'` 且 `project_id` 匹配描述为项目管理员。本设计沿用该语义；通过 product/repo 归属获得访问权的用户按普通成员只读处理，不虚构新的角色名称。
- 当前 `UserUtil.currentUserId` 存在 query 参数兜底。质量管理模块写权限不能依赖可伪造的外部参数，因此新增 token-only 的用户身份入口供本模块使用，保留原方法避免影响存量接口。

需求与代码冲突时以当前代码为准。上述权限和身份差异是适配器必须显式处理的边界，不能只在 Controller 上加注解后默认安全。

### 1.1 本轮里程碑实施基线（2026-11-05，优先于后文）

本轮仅实现里程碑 CRUD 和独立修改日志，后文策划初始化、目录、项目成员权限矩阵及其他业务表接口不属于本轮交付。冲突处以本节和当前 SQL 为准。

#### 数据模型

- `pq_milestone`：`id BIGINT UNSIGNED`、`project_id VARCHAR(64)`、`project_name VARCHAR(255)`、`milestone_name VARCHAR(255)`、`planned_time DATETIME`、`actual_time DATETIME NULL` 和创建/更新审计字段；没有 `deleted`。Java `projectId` 使用 `String`，实体不继承含 `@TableLogic deleted` 的 `PqBaseModel`。
- 将普通索引 `idx_pq_milestone_project(project_id, milestone_name)` 调整为唯一索引 `uk_pq_milestone_project_name(project_id, milestone_name)`；服务层在新增/修改前检查名称，数据库唯一键兜底并发冲突。
- 新增 `pq_milestone_log`：`id BIGINT UNSIGNED AUTO_INCREMENT`、`milestone_id BIGINT UNSIGNED NOT NULL`、`old_data JSON NOT NULL`、`new_data JSON NULL`、`update_by VARCHAR(64) NOT NULL`、`update_time DATETIME NOT NULL`，主键 `id`，索引 `idx_pq_milestone_log_milestone(milestone_id, update_time)`。
- 日志模型不继承公共逻辑删除模型；JSON 列在 Java 中使用字符串承载，插入内容仅来自里程碑实体的完整快照。
- 当前 SQL 不含 `pq_quality_plan` / `pq_plan_catalog`，本轮删除不查询或依赖这两张表，采用物理删除。

#### API 接口契约

里程碑接口契约已独立维护，详见同目录 `milestone-api.md`，本节不再重复描述请求路径、参数、响应字段和错误语义。

#### 事务与日志

- App Service 负责权限、身份、DTO 转换、事务及公共 AOP 快照；Domain Service 负责持久化、名称唯一校验和日志记录；Mapper/XML 负责带项目归属条件的 SQL。两个里程碑 Mapper 不继承 `BaseMapper`，包括 `insert` 在内的 SQL 均在 XML 中显式声明，便于直接检索和审查。所有里程碑 SQL 的表名均显式使用 `openlibing_quality` 库名前缀（如 `openlibing_quality.pq_milestone`），不依赖当前默认数据库。
- 修改：先查询旧实体，在同一事务内更新并插入 `old_data=旧完整 JSON`、`new_data=新完整 JSON` 的日志。
- 删除：先查询旧实体，在同一事务内物理删除并插入 `old_data=旧完整 JSON`、`new_data=NULL` 的日志。
- 创建不写 `pq_milestone_log`。查询不写业务日志。任何更新/删除影响行数不等于 1、日志插入失败或序列化失败均抛出异常，由 `@Transactional` 回滚。
- POST/PUT/DELETE 保留 `@LogApi`，并继续通过 `ProductQualityAuditSupport` 提供公共日志快照；该链路是补充审计，不替代上述强一致日志表。

#### 测试与交付约束

采用 RED → GREEN → REFACTOR：先更新 SQL/Mapper 契约测试并观察失败，再实现模型和 DDL；先写 Domain/App/Controller 失败测试，再实现对应代码。覆盖 CRUD、归属隔离、名称唯一、字段校验、白名单权限、修改/删除日志快照、日志失败异常传播和事务注解。运行定向测试、`ProductQuality*Test` 回归及编译/静态检查；本机没有 MySQL 时明确标注未做真实数据库事务验证。全程不 commit、不 push、不创建 PR。

## 1.2 本轮目录查询增量设计（2026-11-05，优先于后文）

### 数据与查询边界

- `pq_basic_catalog` 字段为 `id/parent_id/catalog_en_name/catalog_cn_name/catalog_level/sort_no/optional_flag` 及审计字段，无 `deleted`。左接口一次查询 `catalog_level=0` 的全部记录，应用层按 `parent_id` 组树。
- `pq_milestone_catalog` 在相同目录字段外增加 `milestone_id INT` 和 `catalog_id BIGINT UNSIGNED`，无 `deleted`。`catalog_id` 是当前节点自身的目录 ID，不作为左侧树查询条件。右接口一次查询指定 `milestone_id` 的全部 1～3 级记录，应用层按 `id/parent_id` 组树，根条件为 `parent_id IS NULL`。
- 两张表均使用 `openlibing_quality` 库名前缀。Mapper 使用 MyBatis 参数绑定，排序固定 `ORDER BY sort_no ASC, id ASC`；不采用逐节点查询的 N+1，也不引入递归 CTE。
- 新增独立 `PqBasicCatalog`、`PqMilestoneCatalog` 及对应 Mapper/XML，不复用旧 `PqPlanCatalog` 或 `pq_plan_catalog`。模型不继承包含逻辑删除字段的 `PqBaseModel`。

### API 与分层

| 方法 | 路径                                           | 参数                     | 响应                        |
| ---- | ---------------------------------------------- | ------------------------ | --------------------------- |
| GET  | `/projects/product-quality/catalogs/basic`     | 无                       | `Result<List<CatalogResp>>` |
| GET  | `/projects/product-quality/catalogs/milestone` | 必填正整数 `milestoneId` | `Result<List<CatalogResp>>` |

- `CatalogResp` 包含 `id/milestoneId/catalogId/parentId/catalogEnName/catalogCnName/catalogLevel/sortNo/optionalFlag/children`；基础目录的 `milestoneId/catalogId` 为 `null`，所有节点的 `children` 初始化为空数组。
- `ProductQualityCatalogController` 仅负责参数校验和统一响应；`ProductQualityCatalogService` 负责 `canRead`、DTO 转换和内存组树；`ProductQualityCatalogDomainService` 委托两个 Mapper 查询。
- 组树以 ID 建索引、以 `parentId` 建子节点关系，形成完整父子层级，仅返回当前里程碑查询范围内的根节点。若子记录先于父记录出现仍能正确挂载；空查询返回空列表；叶节点保持空 `children`。
- 两个 GET 均不加 `@LogApi`，不引入写事务、项目 ID 参数或项目归属校验。

### 测试与交付约束

先新增 Mapper XML 契约、Domain、App 和 standalone MockMvc 失败测试并观察 RED，再写最小实现观察 GREEN。覆盖固定查询条件、参数绑定、排序、权限拒绝、跨里程碑隔离、三级乱序父子节点、空结果、非空 `children` 和参数校验。随后运行目录定向测试、`ProductQualityCoreMapperXmlTest`、`ProductQuality*Test` 回归、格式化后重测、checkstyle/compile 与 `git diff --check`。无真实 MySQL 时明确不声称数据库集成验证通过；全程不 commit、不 push、不创建 PR。

## 1.3 本轮版本摘要增量设计（2026-11-07，优先于后文）

### 方案与数据模型

采用独立版本摘要资源，沿用 `Controller → App Service → Domain Service → Mapper/MySQL`，不提前抽象通用单条内容框架，也不复用里程碑日志表。

- `PqVersionSummary` 继承 `PqBaseModel`，业务字段为 `Integer projectId`、`Long milestoneId`、`String milestoneName`、`String summaryHtml`。当前里程碑模型的项目 ID 为字符串，而摘要 DDL 为 `INT`；首次创建时将里程碑的数字字符串项目 ID 安全转换为 `Integer`，非数字按参数异常拒绝。
- 新增 `pq_version_summary_log`：`id BIGINT UNSIGNED AUTO_INCREMENT`、`version_summary_id BIGINT UNSIGNED NOT NULL`、`old_data JSON NOT NULL`、`new_data JSON DEFAULT NULL`、`update_by VARCHAR(64) NOT NULL`、`update_time DATETIME NOT NULL`，索引 `idx_pq_version_summary_log_summary(version_summary_id, update_time)`。
- 摘要和日志 Mapper 不继承 `BaseMapper`，所有 SQL 在 XML 显式声明，表名使用 `openlibing_quality` 前缀；有效摘要查询固定 `milestone_id=#{milestoneId} AND deleted=0`。

### API 与保存流程

| 方法 | 路径                                               | 参数                                              | 响应                                               |
| ---- | -------------------------------------------------- | ------------------------------------------------- | -------------------------------------------------- |
| GET  | `/projects/product-quality/version-summary/detail` | 必填正整数 `milestoneId`                          | `Result<VersionSummaryResp>`，无记录时 `data=null` |
| POST | `/projects/product-quality/version-summary/update` | Query `milestoneId`；body `VersionSummarySaveReq` | `Result<VersionSummaryResp>`                       |

`VersionSummarySaveReq` 仅包含可空的 `summaryHtml`，最大 100,000 字符。响应包含摘要主键、项目 ID、里程碑 ID/名称、富文本和完整审计字段。

- 查询：`canRead` 后按里程碑查询有效摘要，不伪造空实体。
- 首次保存：`canWrite` 后校验里程碑存在，从里程碑取得项目 ID 和名称，插入有效摘要；创建不写 `pq_version_summary_log`。
- 后续保存：保留主键、项目、里程碑和创建审计字段，仅更新清理后的 `summaryHtml`、更新人和更新时间；更新影响行数必须为 1，并在同一事务插入旧、新完整 JSON 快照。日志插入异常向外传播以回滚业务更新。
- App Service 继续使用 `ProductQualityAuditSupport` 冻结公共审计快照；独立日志表是强一致修改记录，不由 best-effort AOP 替代。
- 使用 OWASP Java HTML Sanitizer 固定版本依赖和白名单策略，保留基本排版、列表、表格及安全链接，移除脚本、事件属性和危险 URL。

### 测试与交付约束

按 RED → GREEN → REFACTOR 依次更新 SQL/Mapper 契约、Domain、App 和 standalone MockMvc 测试。覆盖空查询、首次创建、后续更新、归属数据生成、审计字段保留、HTML 清理、新旧日志快照、影响行数异常、日志失败传播、白名单权限和参数校验。运行定向测试、`ProductQuality*Test` 回归、格式化、checkstyle 和编译；无真实 MySQL 时不声称数据库事务集成验证通过。全程不 commit、不 push、不创建 PR。

## 2. 方案选择

采用**全固定表模型**：每类 Issue 已定义字段的业务数据使用独立表、独立实体和强类型请求/响应；目录使用统一模板和实例表；权限、归属校验、批量删除和日志快照使用公共支撑组件。

不采用以下方案：

1. **单表 JSON 存全部内容**：表少但字段校验、查询、迁移和权限审计弱，不符合本次明确选择的固定表方案。
2. **立即拆 Maven 子模块或微服务**：会扩大构建和部署范围；本期先在各标准层使用 `productquality` 子包，并隔离外部适配器，后续再按边界迁移。
3. **通用 Map/JsonNode CRUD**：虽然减少类数量，但无法提供稳定契约和字段级校验，不采用。

## 3. 包与组件设计

```text
com.openlibing.ops
├── api
│   ├── controller/productquality/
│   ├── request/productquality/
│   └── response/productquality/
├── app/service/productquality/
├── domain
│   ├── mapper/productquality/
│   ├── model/productquality/
│   └── service/productquality/
└── infrastructure
    ├── aop/productquality/              # 仅日志等 OPS 适配器
    └── util/UserUtil.java               # 增加 token-only 身份入口，不改变原方法

src/main/resources
├── mapper/productquality/
└── sql/V20261104__product_quality_planning.sql
```

调用链固定为：

```text
Controller
  → App Service（身份、权限、事务、DTO 转换、日志快照）
  → Domain Service（归属链、字段规则、CRUD）
  → Mapper / XML（project_id + plan_id + deleted 条件）
  → MySQL
```

### 3.1 Controller 分组

| 类                                    | 职责                                           |
| ------------------------------------- | ---------------------------------------------- |
| `ProductQualityMilestoneController`   | 里程碑 CRUD、按里程碑查询策划                  |
| `ProductQualityPlanController`        | 幂等初始化、目录、当前用户权限、质量负责人维护 |
| `ProductQualityStepOneController`     | 版本摘要、思维导图及 Step1 四个表格            |
| `ProductQualityStepTwoController`     | 目标策划、风险策划                             |
| `ProductQualityStepThreeController`   | 度量指标、评估策划                             |
| `ProductQualityStepFourController`    | 会议、状态报告、知识输入、知识输出             |
| `ProductQualitySpecialPlanController` | 特性专项、工程能力阶段表和检查项表             |

每个叶子资源使用独立 `XxxSaveReq` / `XxxResp`，不暴露持久化实体。批量删除共用 `BatchDeleteReq`，分页参数使用统一 `PageQueryReq` 或等价校验对象。

### 3.2 App Service

- `ProductQualityMilestoneService`：里程碑维护及待初始化状态。
- `ProductQualityPlanService`：初始化事务、目录实例化、策划查询。
- `ProductQualityPermissionService`：读、写、质量负责人管理三类权限决策。
- `ProductQualityStepOneService` 等分组服务：强类型 DTO 转换并调用领域服务。
- `ProductQualityUserAdapter`：从 token Cookie 获取当前用户，不接受 query 参数身份。
- `ProductQualityLogSnapshot`：请求范围内冻结变更前后快照，交由日志 Handler 消费。

### 3.3 Domain Service 公共约束

`ProductQualityPlanItemServiceSupport` 仅承载重复技术逻辑，不取代各业务的强类型校验：

1. 根据 `projectId + planId` 查询有效策划，不存在即拒绝。
2. 查询、修改、删除时同时限定 `project_id + plan_id + id + deleted = 0`。
3. 新增时由服务端写入 `project_id / plan_id / create_by / update_by`，忽略请求体中的归属和审计字段。
4. 修改时保持 `project_id / plan_id / create_by / create_time` 不变。
5. 有 `milestoneId` 的记录校验该里程碑属于当前项目；允许与策划所属里程碑不同。
6. 批量删除在同一事务中先锁定并核对全部记录，再统一逻辑删除；数量不一致则抛业务异常并回滚。
7. 所有列表默认 `id DESC`，仅支持数据库侧分页，禁止客户端传表名、列名或 SQL 片段。

## 4. 数据模型

### 4.1 公共约定

- 21 张表均位于 OPS MySQL schema，统一 `pq_` 前缀，字符集 `utf8mb4`。
- 主键统一 `id BIGINT UNSIGNED AUTO_INCREMENT`。
- 项目 ID 使用 `project_id INT NOT NULL`，与当前权限库 `project_info.project_id` 类型一致。
- 策划业务表同时保存 `project_id` 和 `plan_id`；两者均由服务端根据路径和策划归属写入，不能由请求体指定。
- 审计字段统一为 `create_by VARCHAR(64)`、`create_time DATETIME`、`update_by VARCHAR(64)`、`update_time DATETIME`、`deleted TINYINT NOT NULL DEFAULT 0`。
- `create_time / update_time` 复用 MyBatis-Plus 自动填充；用户字段由 App Service 填充。
- 所有查询显式带 `deleted = 0`。逻辑删除不物理清除内容。
- 普通名称/编码/人员/状态字段使用 `VARCHAR(64~255)`；说明、措施和分析使用 `TEXT`；富文本使用 `MEDIUMTEXT`；思维导图使用 `JSON`；时间使用 `DATETIME`；进展使用 `DECIMAL(5,2)`。
- 目标值、实际值、指标算法等按 Issue 原义保存为字符串或文本，不擅自转换为数值或派生枚举。
- 除下文明确的策划唯一约束外，不通过外键代替业务校验。迁移时只依赖本模块表及已有权限表，降低耦合。

### 4.2 核心表（4 张）

| 表                         | 关键字段与约束                                                                                                                                                                                        | 说明                                                             |
| -------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `pq_milestone`             | `project_id`、`milestone_name VARCHAR(255)`、`planned_time DATETIME`、`actual_time DATETIME NULL`；索引 `(project_id, deleted, id)`                                                                   | 项目里程碑主数据；名称必填，实际时间可空                         |
| `pq_quality_plan`          | `project_id`、`milestone_id`；唯一键 `(milestone_id, deleted)`，索引 `(project_id, deleted)`                                                                                                          | 一个里程碑一份有效策划；不提供策划删除接口                       |
| `pq_plan_catalog`          | `project_id`、`plan_id`、`parent_id NULL`、`template_code`、`catalog_name`、`catalog_level`、`sort_no`、`content_type`、`table_key NULL`、`optional_flag`；唯一键 `(plan_id, template_code, deleted)` | 初始化时复制 Java 固定目录模板；`catalog_level <= 3`             |
| `pq_project_quality_owner` | `project_id`、`user_id VARCHAR(64)`、`user_name VARCHAR(128) NULL`；唯一键 `(project_id, user_id, deleted)`                                                                                           | 项目级质量负责人；重新添加已删除用户时恢复原记录，避免唯一键冲突 |

`content_type` 只使用系统固定值：`DIRECTORY`、`RICH_TEXT`、`MINDMAP`、`TABLE`。它是技术渲染类型，不是 Issue 未定义的业务字典。

### 4.3 Step1 业务表（6 张）

公共字段不在下表重复。除两个单条内容表外，其余均包含 `project_id + plan_id`，索引 `(project_id, plan_id, deleted, id)`。

#### `pq_version_summary`

| Issue 字段 | 列                        | 规则                                         |
| ---------- | ------------------------- | -------------------------------------------- |
| 版本摘要   | `summary_html MEDIUMTEXT` | 单条富文本；服务端白名单清理，防止存储型 XSS |

约束：`(plan_id, deleted)` 唯一；保存采用“存在则更新、不存在则新增”。

#### `pq_quality_mindmap`

| Issue 字段   | 列                  | 规则                                                        |
| ------------ | ------------------- | ----------------------------------------------------------- |
| 质量策划思路 | `mindmap_json JSON` | 单条思维导图文档；合法 JSON、大小受限、结构只读为数据不执行 |

约束：`(plan_id, deleted)` 唯一。

#### `pq_internal_improvement`

| Issue 字段      | 列                             | 规则                     |
| --------------- | ------------------------------ | ------------------------ |
| 类别            | `category`                     | 字符串                   |
| 名称            | `name`                         | 字符串                   |
| *本版本改进目标 | `improvement_target TEXT`      | 必填                     |
| *本版本落地措施 | `implementation_measure TEXT`  | 必填                     |
| *责任人         | `owner_name`                   | 必填                     |
| *计划完成时间   | `planned_finish_time DATETIME` | 必填                     |
| 里程碑          | `milestone_id BIGINT`          | 可空；非空时须属于同项目 |
| 状态            | `status`                       | 字符串                   |
| 措施进展(%)     | `progress DECIMAL(5,2)`        | 0–100，可空              |
| 进展说明        | `progress_description TEXT`    | 可空                     |

#### `pq_historical_experience`

| Issue 字段      | 列                               | 规则       |
| --------------- | -------------------------------- | ---------- |
| 经验名称        | `experience_name`                | 字符串     |
| 摘要            | `summary TEXT`                   | 可空       |
| 问题发生时间    | `problem_occurred_time DATETIME` | 可空       |
| *本版本落地措施 | `implementation_measure TEXT`    | 必填       |
| *责任人         | `owner_name`                     | 必填       |
| *计划完成时间   | `planned_finish_time DATETIME`   | 必填       |
| 里程碑          | `milestone_id BIGINT`            | 同项目校验 |
| 状态            | `status`                         | 字符串     |
| 措施进展(%)     | `progress DECIMAL(5,2)`          | 0–100      |
| 进展说明        | `progress_description TEXT`      | 可空       |

#### `pq_value_feature`

| Issue 字段   | 列                           | 规则                       |
| ------------ | ---------------------------- | -------------------------- |
| *名称        | `name`                       | 必填                       |
| *输入描述    | `input_description TEXT`     | 必填                       |
| 类型         | `feature_type`               | 字符串                     |
| 编码         | `feature_code`               | 字符串                     |
| 是否策划     | `planned_flag TINYINT`       | 可空布尔                   |
| 来源         | `source`                     | 字符串                     |
| 里程碑       | `milestone_id BIGINT`        | 同项目校验                 |
| 是否价值特性 | `value_feature_flag TINYINT` | 可空布尔                   |
| PI           | `pi`                         | 字符串，不调用外部 PI 系统 |

#### `pq_input_analysis`

| Issue 字段                           | 列                                  | 规则       |
| ------------------------------------ | ----------------------------------- | ---------- |
| *视角分类                            | `perspective_category`              | 必填字符串 |
| *小类                                | `sub_category`                      | 必填字符串 |
| *输入描述                            | `input_description TEXT`            | 必填       |
| 机会/优势（strengths/opportunities） | `strengths_opportunities TEXT`      | 可空       |
| 危险/劣势（weaknesses/threats）      | `weaknesses_threats TEXT`           | 可空       |
| *本版本质量策略                      | `quality_strategy TEXT`             | 必填       |
| 里程碑                               | `milestone_id BIGINT`               | 同项目校验 |
| 是否分解质量目标                     | `objective_decomposed_flag TINYINT` | 可空布尔   |

### 4.4 Step2 业务表（2 张）

#### `pq_quality_objective`

| Issue 字段        | 列                              |
| ----------------- | ------------------------------- |
| 视角分类          | `perspective_category`          |
| 小类              | `sub_category`                  |
| 一级分类(QFD展开) | `qfd_primary_category`          |
| 二级分类(QFD展开) | `qfd_secondary_category`        |
| *本版本质量策略   | `quality_strategy TEXT`         |
| 策划类别          | `planning_category`             |
| 策划项子模块      | `planning_submodule`            |
| 责任角色          | `owner_role`                    |
| 子模块责任人      | `submodule_owner`               |
| 策划完成时间      | `planning_finish_time DATETIME` |
| *质量目标         | `quality_objective TEXT`        |
| *差距&风险分析    | `gap_risk_analysis TEXT`        |
| 策划要点          | `planning_key_points TEXT`      |
| *关键措施         | `key_measure TEXT`              |
| *措施实施责任人   | `measure_owner`                 |
| *计划完成时间     | `planned_finish_time DATETIME`  |
| 措施进展说明      | `progress_description TEXT`     |
| 措施进展（%）     | `progress DECIMAL(5,2)`         |
| 措施完成状态      | `completion_status`             |
| 验收标准          | `acceptance_criteria TEXT`      |
| 度量指标          | `metric_name`                   |
| 里程碑            | `milestone_id BIGINT`           |
| 目标值            | `target_value`                  |
| 实际值            | `actual_value`                  |
| 目标达成结果      | `achievement_result`            |
| 目标达成情况说明  | `achievement_description TEXT`  |

`*` 字段必填，进展 0–100，里程碑同项目；目标达成结果由用户填写，本期不自动计算。

#### `pq_quality_risk`

| Issue 字段                                             | 列                              | 规则               |
| ------------------------------------------------------ | ------------------------------- | ------------------ |
| *WHY（目标）                                           | `why_objective TEXT`            | 必填               |
| *WHO（谁参与实现目标）                                 | `who_participants TEXT`         | 必填               |
| *HOW（为了实现目标，需要做什么事情/活动？）            | `how_activity TEXT`             | 必填               |
| *WHAT（做的过程有什么问题/风险？依此制定质量保障措施） | `what_risk TEXT`                | 必填               |
| 发生概率                                               | `occurrence_probability`        | 字符串，不虚构等级 |
| 影响程度                                               | `impact_degree`                 | 字符串             |
| 风险等级                                               | `risk_level`                    | 字符串，不自动计算 |
| *应对措施                                              | `response_measure TEXT`         | 必填               |
| 责任人                                                 | `owner_name`                    | 字符串             |
| 提出人                                                 | `proposer_name`                 | 字符串             |
| 计划解决时间                                           | `planned_resolve_time DATETIME` | 可空               |
| 状态                                                   | `status`                        | 字符串             |
| 措施进展(%)                                            | `progress DECIMAL(5,2)`         | 0–100              |
| 进展                                                   | `progress_description TEXT`     | 可空               |
| 是否QCC备选主题                                        | `qcc_candidate_flag TINYINT`    | 可空布尔           |

### 4.5 Step3 业务表（2 张）

版本级要求、版本级文档、研发内部设计文档、营销资料以及生态发展相关发布件只有 `pq_plan_catalog` 目录，无业务表。

#### `pq_metric_plan`

| Issue 字段   | 列                       | 规则             |
| ------------ | ------------------------ | ---------------- |
| 指标名称     | `metric_name`            | 字符串           |
| 指标评估项   | `evaluation_item`        | 字符串           |
| 指标定义     | `metric_definition TEXT` | 可空             |
| 指标属性     | `metric_attribute`       | 字符串           |
| 指标算法     | `metric_algorithm TEXT`  | 可空，不执行公式 |
| 里程碑       | `milestone_id BIGINT`    | 同项目校验       |
| 责任人       | `owner_name`             | 字符串           |
| 版本级目标值 | `version_target_value`   | 字符串           |
| IT实际值     | `it_actual_value`        | 字符串           |
| 实际值       | `actual_value`           | 字符串           |
| 状态         | `status`                 | 字符串           |

#### `pq_evaluation_plan`

| Issue 字段             | 列                             | 规则                     |
| ---------------------- | ------------------------------ | ------------------------ |
| *质量评估点            | `quality_evaluation_point`     | 必填                     |
| *最新计划时间          | `latest_planned_time DATETIME` | 必填                     |
| *SUB子领域             | `sub_domain`                   | 必填                     |
| *评审组织              | `review_organization`          | 必填                     |
| *评估要点              | `evaluation_key_points TEXT`   | 必填                     |
| *领域代表              | `domain_representative`        | 必填                     |
| *SUB结论承载的作业平台 | `conclusion_platform`          | 必填字符串，不做外部调用 |
| 评估结论               | `evaluation_conclusion TEXT`   | 可空                     |
| 评估意见               | `evaluation_opinion TEXT`      | 可空                     |
| 实际时间               | `actual_time DATETIME`         | 可空                     |

### 4.6 Step4 业务表（4 张）

#### `pq_meeting_operation`

| Issue 字段 | 列                    |
| ---------- | --------------------- |
| 会议       | `meeting_name`        |
| 责任人     | `owner_name`          |
| 类别       | `category`            |
| 频度       | `frequency`           |
| 参加人     | `participants TEXT`   |
| 议题       | `topics TEXT`         |
| 里程碑     | `milestone_id BIGINT` |
| 责任角色   | `owner_role`          |

#### `pq_status_report`

| Issue 字段 | 列                        |
| ---------- | ------------------------- |
| 报告       | `report_name`             |
| 频度       | `frequency`               |
| 发送人     | `sender_name`             |
| 主送人员   | `primary_recipients TEXT` |
| 抄送人员   | `cc_recipients TEXT`      |
| 里程碑     | `milestone_id BIGINT`     |
| 责任角色   | `owner_role`              |

#### `pq_knowledge_input`

| Issue 字段                        | 列                              | 规则                                        |
| --------------------------------- | ------------------------------- | ------------------------------------------- |
| *关键知识领域                     | `knowledge_domain`              | 必填                                        |
| 短板/痛点分析                     | `pain_point_analysis TEXT`      | 可空                                        |
| *我们缺哪些知识？（要回答的问题） | `missing_knowledge TEXT`        | 必填                                        |
| *谁需要获取知识（赋能对象）       | `empowerment_target TEXT`       | 必填                                        |
| *获取知识采用行动（赋能方式）     | `acquisition_action TEXT`       | 必填                                        |
| *知识资源在哪里？                 | `knowledge_resource TEXT`       | 必填                                        |
| *谁负责采取行动（姓名+工号）      | `action_owner TEXT`             | 必填，不拆分未验证的人员字段                |
| 开展阶段                          | `execution_stage`               | 字符串                                      |
| *需要完成行动日期                 | `required_finish_time DATETIME` | 必填                                        |
| 优先级                            | `priority`                      | 字符串                                      |
| 状态                              | `status`                        | 字符串                                      |
| 赋能效果验收方式                  | `acceptance_method TEXT`        | 可空                                        |
| 链接                              | `resource_link TEXT`            | 仅允许 http/https，避免 javascript 等伪协议 |

#### `pq_knowledge_output`

| Issue 字段                   | 列                             | 规则   |
| ---------------------------- | ------------------------------ | ------ |
| *阶段点                      | `stage_point`                  | 必填   |
| *时间点                      | `time_point DATETIME`          | 必填   |
| *捕获哪些知识                | `captured_knowledge TEXT`      | 必填   |
| *捕获知识采取的行动          | `capture_action TEXT`          | 必填   |
| 输出交付件                   | `output_deliverable TEXT`      | 可空   |
| 存放或分享的位置             | `storage_location TEXT`        | 可空   |
| *谁负责采取行动（姓名+工号） | `action_owner`                 | 必填   |
| *计划完成时间                | `planned_finish_time DATETIME` | 必填   |
| 状态                         | `status`                       | 字符串 |
| 优先级                       | `priority`                     | 字符串 |

### 4.7 可选专项业务表（3 张）

#### `pq_feature_plan`

| Issue 字段 | 列                             |
| ---------- | ------------------------------ |
| 类别       | `category`                     |
| 需求描述   | `requirement_description TEXT` |
| 需求       | `requirement_name TEXT`        |
| 需求来源   | `requirement_source`           |
| 规划指标   | `planned_metric TEXT`          |
| 达成指标   | `achieved_metric TEXT`         |
| 落地情况   | `implementation_status TEXT`   |

#### `pq_engineering_stage`

| Issue 字段 | 列                         |
| ---------- | -------------------------- |
| 阶段       | `stage_name`               |
| 版本子阶段 | `version_substage`         |
| 基础设施   | `infrastructure TEXT`      |
| 工具       | `tool_name TEXT`           |
| 质量要求   | `quality_requirement TEXT` |
| 问题点     | `problem_points TEXT`      |
| 涉及SIG    | `involved_sig`             |
| IT化进展   | `it_progress TEXT`         |

#### `pq_engineering_check`

| Issue 字段                        | 列                           |
| --------------------------------- | ---------------------------- |
| 领域                              | `domain_name`                |
| 检查项                            | `check_item TEXT`            |
| 责任团队                          | `responsible_team`           |
| β（全部新特转测第一个版本）       | `beta_value TEXT`            |
| Final                             | `final_value TEXT`           |
| 落地majun平台情况（最终发布版本） | `majun_platform_status TEXT` |

其他专项只有目录，无业务表。`majun` 保留 Issue 原始命名，不在本期更名或集成。

## 5. 固定目录模板

初始化由 `ProductQualityCatalogTemplate` 生成以下节点。`sort_no` 按表中顺序递增，`template_code` 是稳定英文标识；后续模板新增节点可做增量初始化，但不允许改变历史节点含义。

| 一级                         | 二级                 | 三级                           | 内容类型 / `table_key`           |
| ---------------------------- | -------------------- | ------------------------------ | -------------------------------- |
| Step1 策划导入               | 版本摘要             | —                              | `RICH_TEXT / version-summary`    |
| Step1 策划导入               | 质量策划思路         | —                              | `MINDMAP / quality-mindmap`      |
| Step1 策划导入               | 质量策划导入         | 内部改进要求/重点工作          | `TABLE / internal-improvements`  |
| 同上                         | 同上                 | 历史经验导入                   | `TABLE / historical-experiences` |
| 同上                         | 同上                 | 价值特性                       | `TABLE / value-features`         |
| 同上                         | 同上                 | 策划输入分析                   | `TABLE / input-analyses`         |
| Step2 目标与风险策划         | 目标策划             | 目标差距分析及分解             | `TABLE / quality-objectives`     |
| 同上                         | 风险策划             | —                              | `TABLE / quality-risks`          |
| Step3 过程与控制策划         | 质量要求策划         | 版本级要求                     | `DIRECTORY`                      |
| 同上                         | 交付件策划           | 版本级文档                     | `DIRECTORY`                      |
| 同上                         | 同上                 | 研发内部设计文档               | `DIRECTORY`                      |
| 同上                         | 同上                 | 营销资料以及生态发展相关发布件 | `DIRECTORY`                      |
| 同上                         | 度量指标策划         | —                              | `TABLE / metric-plans`           |
| 同上                         | 评估策划             | 转测试评估和版本出口评估       | `TABLE / evaluation-plans`       |
| Step4 项目运作与人力资源策划 | 组织运作策划（可选） | 会议运作制度                   | `TABLE / meeting-operations`     |
| 同上                         | 同上                 | 状态报告制度                   | `TABLE / status-reports`         |
| 同上                         | 知识管理策划（可选） | 知识输入                       | `TABLE / knowledge-inputs`       |
| 同上                         | 同上                 | 知识输出                       | `TABLE / knowledge-outputs`      |
| 特性级策划（可选）           | 专项策划             | —                              | `TABLE / feature-plans`          |
| 领域专项策划（可选）         | 工程能力专项         | 阶段规划                       | `TABLE / engineering-stages`     |
| 同上                         | 同上                 | 领域检查项                     | `TABLE / engineering-checks`     |
| 其他专项策划（可选）         | 专项策划             | —                              | `DIRECTORY`                      |

“知识管理计划”不再单独占一层，以保证整个目录最大层级不超过三级。该调整只影响导航映射，不减少知识输入/输出功能。

## 6. 后续 API 规划（非本轮已交付接口）

本节描述后续策划业务的规划契约，不代表当前已经实现的接口。前端本轮开发里程碑功能时只使用同目录 `milestone-api.md` 的接口契约，不要使用本节的历史里程碑路由、权限或响应字段。

统一基础路径：

```text
/projects/{projectId}/product-quality
```

所有响应使用 `Result<T>`，分页使用 `PageResult<T>`。`projectId`、`planId`、`milestoneId`、`id` 为正整数；请求体不接收 `projectId`、`planId`、审计字段或逻辑删除字段。

### 6.1 策划和权限（后续规划）

当前已实现的里程碑接口见 `milestone-api.md`；以下仅为后续策划与权限接口规划：

| 方法 | 路径                      | 权限       | 说明                                            |
| ---- | ------------------------- | ---------- | ----------------------------------------------- |
| POST | `/plans/initialize`       | 写权限     | body 为 `milestoneId`；显式、幂等创建策划及目录 |
| GET  | `/plans/{planId}/catalog` | 项目成员   | 返回树形目录，最多三级                          |
| GET  | `/permissions`            | 项目成员   | 返回 `canRead/canWrite/canManageOwners`         |
| GET  | `/quality-owners`         | 项目成员   | 查询本项目质量负责人                            |
| PUT  | `/quality-owners`         | 项目管理员 | 整体替换质量负责人列表；事务内校验、增删和恢复  |

质量负责人整体替换使用用户 ID 列表，服务端去重并逐个验证其项目成员资格。任何用户不合法则整次不修改。项目管理员身份不能通过该接口由质量负责人自我提升。

### 6.2 单条内容资源

| 资源路径                          | 方法      | 说明                   |
| --------------------------------- | --------- | ---------------------- |
| `/plans/{planId}/version-summary` | GET / PUT | 查询或保存版本摘要     |
| `/plans/{planId}/quality-mindmap` | GET / PUT | 查询或保存质量策划思路 |

空内容从未保存时，GET 返回 `data = null`，不伪造空记录。PUT 幂等保存并返回最新内容。

### 6.3 表格资源

以下 15 个 `resource` 均提供独立强类型端点：

| `resource`               | 业务模块                 |
| ------------------------ | ------------------------ |
| `internal-improvements`  | 内部改进要求/重点工作    |
| `historical-experiences` | 历史经验导入             |
| `value-features`         | 价值特性                 |
| `input-analyses`         | 策划输入分析             |
| `quality-objectives`     | 目标差距分析及分解       |
| `quality-risks`          | 风险策划                 |
| `metric-plans`           | 度量指标策划             |
| `evaluation-plans`       | 转测试评估和版本出口评估 |
| `meeting-operations`     | 会议运作制度             |
| `status-reports`         | 状态报告制度             |
| `knowledge-inputs`       | 知识输入                 |
| `knowledge-outputs`      | 知识输出                 |
| `feature-plans`          | 特性级专项策划           |
| `engineering-stages`     | 工程能力阶段规划表       |
| `engineering-checks`     | 工程能力领域检查项表     |

每个资源的路径模板如下；实现时映射到对应强类型 Controller 方法，而不是运行时接收任意 `resource` 字符串：

| 方法   | 路径模板                                                  | 说明                                                 |
| ------ | --------------------------------------------------------- | ---------------------------------------------------- |
| GET    | `/plans/{planId}/{resource}?page=&pageSize=&milestoneId=` | 分页列表；`milestoneId` 可选，用于筛选执行关联里程碑 |
| POST   | `/plans/{planId}/{resource}`                              | 新增，返回保存后的强类型响应                         |
| GET    | `/plans/{planId}/{resource}/{id}`                         | 单条详情                                             |
| PUT    | `/plans/{planId}/{resource}/{id}`                         | 修改，返回保存后的强类型响应                         |
| DELETE | `/plans/{planId}/{resource}/{id}`                         | 单条逻辑删除                                         |
| POST   | `/plans/{planId}/{resource}/batch-delete`                 | body 为去重前非空的 ID 列表，整批原子删除            |

分页默认 `page=1`、`pageSize=20`，`pageSize <= 200`；批量 ID 数量 `1..200`。列表不开放任意排序字段。目录中 `DIRECTORY` 类型节点没有对应 CRUD 路由。

### 6.4 错误语义

| 场景                                                          | 处理                                                               |
| ------------------------------------------------------------- | ------------------------------------------------------------------ |
| 未认证、非项目成员、只读成员写数据、质量负责人维护负责人      | 现有权限异常，返回 403，不泄露目标资源内容                         |
| 必填字段缺失、进展越界、分页或批量大小非法、URL 非 http/https | 参数异常，返回 400                                                 |
| 策划、里程碑或记录不属于路径项目，记录不存在或已删除          | 按现有业务异常语义返回资源不存在或无权限；查询条件始终包含归属字段 |
| 已初始化里程碑被删除                                          | 业务冲突，提示先保留策划数据，不做级联删除                         |
| 重复初始化                                                    | 返回已有策划，不报错、不复制目录                                   |
| 批量删除任一 ID 校验失败                                      | 整批回滚，任何记录都不删除                                         |
| 数据库唯一键冲突发生在并发初始化                              | 事务内重新查询已有策划并返回；其他唯一键异常不得一律当作幂等成功   |

## 7. 权限与身份设计

### 7.1 决策矩阵

| 用户类型         |   读 | 里程碑/策划/业务写 | 维护质量负责人 |
| ---------------- | ---: | -----------------: | -------------: |
| 无有效身份       | 拒绝 |               拒绝 |           拒绝 |
| 非项目成员       | 拒绝 |               拒绝 |           拒绝 |
| 项目普通成员     | 允许 |               拒绝 |           拒绝 |
| 项目质量负责人   | 允许 |               允许 |           拒绝 |
| 项目管理员       | 允许 |               允许 |           允许 |
| OPS 全局管理角色 | 允许 |               允许 |           允许 |

判定顺序固定为：有效 token 身份 → 项目归属 → 是否管理员 → 是否质量负责人。任何查询异常或空结果都按拒绝处理。

### 7.2 当前角色映射

- 项目归属复用 `ResourcePermissionService.check(userId, PROJECT, [projectId])`。
- 全局管理角色沿用当前 SQL：`super_admin`、`admin`、`platform_operater`、`数字化运营看板管理员`。
- 项目管理员沿用当前权限设计：`role_type_info.type = 'project'` 且 `user_role_info.project_id = projectId`。
- 通过 product/repo 归属获得项目访问权的用户只读；质量负责人记录在 `pq_project_quality_owner`，只在同项目内生效。
- 管理员/负责人判定集中在新 Mapper，不复制到各 Controller。后续角色模型变化只修改适配器及测试。

### 7.3 身份来源

为 `UserUtil` 增加只读取 token Cookie 的公开方法，内部复用当前私有 JWT 解析逻辑；`ProductQualityUserAdapter` 只调用该新方法。原 `currentUserId` 保持不变，避免本需求改变其他模块行为。新模块任何接口都不使用 query 参数中的 `userId` 作为身份。

## 8. 操作日志与审计

新增 `ProductQualityLogHandler extends AbstractLogHandler` 和请求级快照支撑，复用现有 Recorder 的公共字段、菜单标识、IP、起止时间及写入链路。

1. 所有 POST/PUT/DELETE 写接口标注仓库要求的日志注解，并由 Handler 精确匹配质量管理路径。
2. App Service 在修改前冻结旧实体/DTO 快照并存入请求级上下文：批量删除保存旧记录列表，初始化保存空策划快照，质量负责人变更保存旧负责人集合。这样不依赖 AOP `before` 阶段再次路由全部业务表。
3. 业务保存成功后立即冻结新实体/DTO 快照；Handler 在 `after` 阶段一次性消费请求级旧/新快照，避免并发请求回查混入其他数据。失败操作不填成功的新快照。
4. 快照字段来自白名单业务实体，不序列化 `HttpServletRequest`、Cookie、token、JWT 或完整 HTTP 报文。
5. 日志资源标识：里程碑使用 `milestoneId`，策划使用 `planId`，明细使用 `id`，批量操作使用有序 ID 列表，质量负责人使用 `projectId`。
6. 富文本清理后的内容和思维导图 JSON 可进入业务快照，但接口设置大小上限，避免超大日志；数据库和日志后端均需验证上限兼容性。
7. 日志补数异常遵循现有框架策略，不在业务响应中暴露日志系统内部地址、堆栈或凭证。

## 9. 输入、输出与数据安全

- Controller 使用 `@Validated`，Domain Service 再校验跨字段和资源归属规则。
- 字符串执行 trim 和长度限制；`TEXT` 字段默认最大 20,000 字符，富文本最大 100,000 字符，思维导图最大 200,000 字符；数据库字段和请求约束保持一致。
- 版本摘要使用 OWASP Java HTML Sanitizer 白名单，仅保留基本排版、标题、列表、表格和安全链接；移除 script、style、iframe、事件属性、危险 URL。新增依赖需固定版本并通过依赖漏洞及许可证检查。
- 思维导图只接受 JSON 数据，限制总大小、节点数和嵌套深度，不执行其中脚本、模板或表达式。
- `resource_link` 仅允许 `http/https`，输出为 JSON 字符串；后端不主动请求该 URL，避免 SSRF。
- 所有 SQL 使用 MyBatis 参数绑定；列表排序和过滤字段固定，禁止字符串拼接客户端 SQL。
- 业务数据按内部数据保护；本模块不保存密码、token、密钥或个人敏感认证信息。人员字段只保存 Issue 要求的姓名/工号文本。
- 复用现有 HTTPS、数据库连接和部署配置，不在代码或 SQL 中写入环境地址、账号和密码。

详细威胁模型与八维度安全设计见 `system_design/feat-product-quality-planning/`。

## 10. 事务、幂等与并发

### 10.1 初始化

1. 校验写权限及 `projectId + milestoneId` 归属。
2. 查询有效策划，存在则直接返回。
3. 在单个 MySQL 事务中插入 `pq_quality_plan` 和全部 `pq_plan_catalog`。
4. 并发插入时由 `(milestone_id, deleted)` 唯一约束防止双策划；捕获该特定冲突后重新查询并返回已有策划。
5. 目录任一插入失败则整事务回滚，不留下半份策划。

### 10.2 质量负责人替换

在同一事务内读取当前有效负责人、验证目标集合、逻辑删除移除项、新增或恢复新增项并写入日志快照。目标用户不是项目成员或任一数据库操作失败时整体回滚。

### 10.3 批量删除

使用事务和带归属条件的行查询；需要时通过 `SELECT ... FOR UPDATE` 防止校验后并发修改。删除 SQL 同时带 `project_id + plan_id + id + deleted = 0`，影响行数不等于预期即回滚。

## 11. 数据库脚本与部署

新增 `src/main/resources/sql/V20261104__product_quality_planning.sql`，包含 21 张表的 `CREATE TABLE`、索引、注释和初始化前置说明。

- 当前仓库 SQL 由 DBA 手动执行，本设计不引入 Flyway 自动启动迁移。
- 上线顺序：备份/评审脚本 → beta MySQL 执行 → 发布后端 → 接口验证 → 生产执行与发布。
- 脚本针对全新模块建表；重跑前必须检查表是否存在，不通过无条件 `DROP TABLE` 实现可重跑。
- 回滚应用代码不自动删除表；数据表保留。确需回滚 schema 时由 DBA 单独评估，禁止应用启动时删表。
- 不新增运行时配置项、外部服务地址或凭证。

## 12. 测试策略

Full 模式按行为先补测试，再实现，覆盖以下最小集合：

### 12.1 单元测试

- 目录模板：所有必需/可选节点存在、最大层级为 3、代码和顺序稳定、目录-only 节点无 `table_key`。
- 权限矩阵：匿名、非成员、普通成员、质量负责人、项目管理员、全局管理员。
- 字段校验：全部 `*` 字段、进展 0/100 边界及越界、URL 白名单、富文本 XSS、思维导图大小/深度。
- 归属校验：跨项目策划、记录、执行里程碑均拒绝。
- 初始化：首次成功、重复返回、目录失败回滚、唯一键并发冲突重查。
- 批量删除：全部成功、空列表、重复 ID、跨策划 ID、部分不存在、影响行数不一致均符合原子性。
- 里程碑删除：未初始化允许，已初始化拒绝。
- 质量负责人：非管理员拒绝、非成员不能加入、移除后重加不冲突。

### 12.2 Mapper / Controller 测试

- MyBatis XML 字段映射、逻辑删除条件、项目/策划过滤和分页。
- Controller 验证强类型 JSON 契约、统一响应、400/403 语义和所有资源路由。
- 日志 Handler 验证新增/修改/删除/批量/初始化前后快照，且不包含 token、Cookie。

### 12.3 集成验证

- 在 MySQL 8.0 全新 schema 执行脚本，验证 21 张表、唯一键和索引。
- 使用两个项目、两个里程碑和多个角色执行跨项目读写、跨里程碑引用和批量删除回归。
- 执行仓库完整质量门禁：`spotless`、Checkstyle、SpotBugs、PMD、全量测试。
- 编码完成后按安全设计清单执行代码级安全复核，确认没有凭证、注入、XSS、越权和危险依赖。

## 13. 预计修改范围

1. 新增 `productquality` 各层子包、强类型 DTO、实体、Mapper、Service 和 Controller。
2. 新增 `resources/mapper/productquality/` XML 和模块建表 SQL。
3. 新增模块权限与日志适配器及测试。
4. 对 `UserUtil` 仅新增 token-only 方法，不改变既有 query 兜底方法的行为。
5. `pom.xml` 仅增加富文本白名单清理所必需的 OWASP Sanitizer 固定版本依赖。
6. 不修改其他业务模块、部署文件、外部接口或 `openlibing-docs` 以外的仓库。

## 14. 后续迁移边界

迁移时业务表、固定目录、领域服务和强类型契约整体移动；目标项目只需重新实现三类适配器：

- 用户身份适配器：提供当前用户 ID。
- 项目权限适配器：提供成员、管理员判定。
- 操作日志适配器：消费统一的变更元数据和前后快照。

在 OPS 内暂不为了“可能迁移”引入额外插件框架、SPI、消息协议或独立服务。
