# 质量管理-质量策划模块需求提案

## 1.5 本轮内部改进要求和重点工作增量基线（2026-11-07，优先于后文）

本轮采用 Standard 模式，交付 Step1 策划导入-质量策划导入-内部改进要求和重点工作的完整表格后端接口，关联 Issue #328。

1. 以 `V20261104__product_quality_planning.sql` 当前 `pq_internal_improvement` DDL 为准，记录归属里程碑，项目 ID 和里程碑名称由服务端根据里程碑生成。
2. 基础路径为 `/projects/product-quality/internal-improvements`，提供新增、分页查询、单条详情、修改、单条逻辑删除和批量逻辑删除接口；业务参数沿用 Query 参数风格，不引入 `planId`。
3. 新增 `pq_internal_improvement_log`，字段参照 `pq_version_summary_log`：`id/internal_improvement_id/old_data/new_data/update_by/update_time`。修改保存旧、新完整 JSON 快照，删除保存旧快照且新数据为 `NULL`，创建不写独立日志。
4. 修改、单条删除和批量删除均在事务内完成业务写入及日志写入；任一日志写入失败或批量记录归属校验失败必须回滚整次操作。
5. 读写权限复用 `ProductQualityPermissionService.canRead/canWrite` 白名单和 token-only 用户身份。改进目标、落地措施、责任人和计划完成时间必填，措施进展范围为 0～100。
6. 分页默认 `page=1`、`pageSize=20`，单页最大 200；批量 ID 去重后数量为 1～200，任一记录不存在、已删除或不属于当前里程碑时整批拒绝。
7. 本轮完成后使用中文提交信息提交代码和文档，并推送两个仓库的当前远程分支；不创建 PR，不进入 Phase 5 归档。

### 本轮验收标准

- [x] 六类接口均使用强类型请求/响应和统一 `Result` 返回，分页使用 `PageResult`。
- [x] 查询仅返回当前里程碑的未删除数据，修改和删除不能跨里程碑操作。
- [x] 新增从里程碑补齐项目 ID 和名称，修改保留主键、归属及创建审计字段。
- [x] 修改和删除日志快照正确，批量删除逐条记录旧快照，日志失败可回滚。
- [x] 字段校验、分页边界、批量去重及归属校验有测试覆盖，productquality 回归通过。
- [ ] API 联调文档与实际代码一致，代码和文档以中文提交并推送。

## 1. 需求来源

- 业务仓库：`openlibing/openlibing-ops`
- 业务 Issue：[#328 【蓝区】开源社区质量管理IT建设-质量策划](https://gitcode.com/openlibing/openlibing-ops/issues/328)
- 流程模式：Full
- 需求名称：`feat-product-quality-planning`
- 当前开发分支：`yanhongbing_fork_01`

## 1.1 本轮里程碑增量基线（2026-11-05，优先于后文）

本轮只交付项目里程碑 CRUD 及独立修改日志，不交付后文所述策划初始化、目录和其他策划业务表接口。经用户确认，本轮规则如下：

1. 以 `V20261104__product_quality_planning.sql` 当前 `pq_milestone` DDL 为准：`project_id` 为 `VARCHAR(64)`，包含 `project_name`，没有 `deleted` 字段；实体中的项目 ID 使用 `String`。
2. 里程碑字段为项目名称、里程碑名称、计划时间、实际时间及审计字段。同一项目内里程碑名称唯一，通过服务校验和 `(project_id, milestone_name)` 唯一索引共同保证。
3. 删除为**物理删除**，不依赖 `pq_quality_plan`，也不存在“已初始化策划不可删除”的本轮约束。后文涉及里程碑逻辑删除、策划初始化状态和项目成员角色矩阵的内容属于旧总体方案，不作为本轮验收依据。
4. 新增 `pq_milestone_log`：主键 ID、里程碑 ID、旧数据 JSON、新数据 JSON、修改人、修改时间。修改保存旧/新完整快照；删除保存旧快照且新数据为 `NULL`；创建不写该表。
5. 修改/删除与日志插入处于同一本地事务，日志插入失败必须回滚业务操作。保留公共 `@LogApi` 操作日志，但不以 best-effort AOP 代替事务日志表。
6. 权限复用当前 `ProductQualityPermissionService.canRead/canWrite` 全局白名单和 token-only 用户身份，不在本轮实现旧方案的项目成员/项目质量负责人角色矩阵。
7. 本轮全程不提交代码、不推送、不创建 PR；后续其他策划模块仍按原需求另行实施和验收。

## 1.2 本轮目录查询增量基线（2026-11-05，优先于后文）

本轮在既有里程碑代码基础上，只增加基础目录和里程碑目录的只读查询，不交付策划初始化、目录写入或其他策划业务表接口：

1. 以 `V20261104__product_quality_planning.sql` 中 `pq_basic_catalog` 和 `pq_milestone_catalog` 当前 DDL 为准。前者 `catalog_level=0` 的记录构成左侧目录；后者按 `milestone_id` 隔离，`catalog_id` 是当前节点自身的目录 ID 而非左侧树目录 ID，保存从 1 级开始的右侧目录，不保存左侧 0 级节点。
2. 新增 `GET /projects/product-quality/catalogs/basic`，无需业务查询参数，返回全部左侧目录树。
3. 新增 `GET /projects/product-quality/catalogs/milestone?milestoneId=`，`milestoneId` 为必填正整数，返回所选里程碑的全部右侧目录树。
4. 两个接口均返回 `Result<List<CatalogResp>>`。每个节点包含目录标识、父节点、名称、层级、排序号、可选标记和非空 `children` 数组；右侧节点还返回 `milestoneId/catalogId`。
5. 同级按 `sort_no ASC, id ASC` 稳定排序。数据库中没有记录时返回空数组；不根据目录名称推测或补造节点。
6. 查询权限复用当前 `ProductQualityPermissionService.canRead` 全局白名单，GET 不写业务变更日志；本轮不增加项目归属或项目成员角色校验。
7. 全程不提交代码、不推送、不创建 PR；完成后保留本地变更供用户自测。

### 本轮验收标准

- [ ] 左侧接口仅返回 `pq_basic_catalog` 的 0 级根节点及其下级节点，响应数组中每个节点都有 `children`。
- [ ] 右侧接口严格按 `milestoneId` 查询该里程碑的全部目录，不使用 `catalogId` 过滤，不混入其他里程碑的数据。
- [ ] 右侧按 `id/parent_id` 父子层级返回 1～3 级目录树，根节点为当前范围内 `parent_id IS NULL` 的记录，顺序稳定，叶子节点 `children=[]`。
- [ ] 两个接口均执行白名单读权限校验；无效参数不调用业务服务；空结果返回成功空数组。
- [ ] Mapper SQL、应用服务组树和 Controller 契约测试通过，既有 productquality 测试无本轮回归。
- [ ] 所有代码和文档修改仅保留在工作区，未 commit、push 或创建 PR。

## 1.4 本轮质量策划思路增量基线（2026-11-07，优先于后文）

本轮只交付 Step1 策划导入的质量策划思路查询和保存，不交付其他 Step1 业务模块、删除或日志查询接口。经用户确认，本轮规则如下：

1. 以 `V20261104__product_quality_planning.sql` 当前 `pq_quality_roadmap` DDL 为准：按 `milestone_id` 每个里程碑保存一条有效 JSON 文档，`project_id` 为 `INT`，并包含 `milestone_name`、审计字段和 `deleted`。
2. 新增 `GET /projects/product-quality/roadmap/detail?milestoneId=` 和 `POST /projects/product-quality/roadmap/update?milestoneId=`。请求体仅包含 `roadmapJson`，项目 ID 和里程碑名称由服务端根据里程碑生成。
3. 查询无记录返回 `data=null`；首次保存自动创建且不写独立修改日志；后续保存全量更新 JSON 并记录修改日志。
4. 新增 `pq_quality_roadmap_log`，字段参照 `pq_version_summary_log`：`id/roadmap_id/old_data/new_data/update_by/update_time`。更新保存旧、新完整 JSON 快照，业务更新与日志插入在同一事务。
5. 读写权限复用当前 `ProductQualityPermissionService.canRead/canWrite` 全局白名单和 token-only 用户身份。
6. `roadmapJson` 为 JSON 格式字符串，最大 200,000 字符，允许清空。
7. 在 `api/controller/` 下新建 `productquality` 包，将 `ProductQualityCatalogController`、`ProductQualityMilestoneController`、`ProductQualityVersionSummaryController` 迁移到该包，与 `external` 包平级。
8. 本轮完成后提交代码并推送至远程仓库。

### 本轮验收标准

- [ ] 查询严格按 `milestoneId + deleted=0` 返回单条质量策划思路，无记录返回成功空数据。
- [ ] 首次保存从里程碑补齐项目 ID 和里程碑名称，后续保存不覆盖主键及创建审计字段。
- [ ] 后续更新写入正确的新旧完整 JSON 快照，日志失败可回滚业务更新；创建不写独立日志。
- [ ] 无效里程碑、超长 JSON、无权限请求按既有异常语义处理。
- [ ] 产品质量相关 Controller 迁移到 `api.controller.productquality` 包，原有接口路径不变。
- [ ] SQL/Mapper、Domain、App、Controller 契约测试及 productquality 回归通过。
- [ ] 代码提交并推送至远程仓库。

## 1.3 本轮版本摘要增量基线（2026-11-07，优先于后文）

1. 以 `V20261104__product_quality_planning.sql` 当前 `pq_version_summary` DDL 为准：按 `milestone_id` 每个里程碑保存一条有效富文本，`project_id` 为 `INT`，并包含 `milestone_name`、审计字段和 `deleted`。
2. 新增 `GET /projects/product-quality/version-summary/detail?milestoneId=` 和 `POST /projects/product-quality/version-summary/update?milestoneId=`。请求体仅包含 `summaryHtml`，项目 ID 和里程碑名称由服务端根据里程碑生成。
3. 查询无记录返回 `data=null`；首次保存自动创建且不写独立修改日志；后续保存全量更新富文本并记录修改日志。
4. 新增 `pq_version_summary_log`，字段参照 `pq_milestone_log`：`id/version_summary_id/old_data/new_data/update_by/update_time`。更新保存旧、新完整 JSON 快照，业务更新与日志插入在同一事务。
5. 读写权限复用当前 `ProductQualityPermissionService.canRead/canWrite` 全局白名单和 token-only 用户身份。
6. 富文本允许清空，最大 100,000 字符；保存前使用白名单清理危险 HTML。
7. 全程不提交代码、不推送、不创建 PR，完成后保留本地变更供用户自测。

### 本轮验收标准

- [ ] 查询严格按 `milestoneId + deleted=0` 返回单条摘要，无记录返回成功空数据。
- [ ] 首次保存从里程碑补齐项目 ID 和里程碑名称，后续保存不覆盖主键及创建审计字段。
- [ ] 后续更新写入正确的新旧完整 JSON 快照，日志失败可回滚业务更新；创建不写独立日志。
- [ ] 无效里程碑、超长或危险富文本、无权限请求按既有异常语义处理。
- [ ] SQL/Mapper、Domain、App、Controller 契约测试及 productquality 回归通过。
- [ ] 所有代码和文档修改仅保留在工作区，未 commit、push 或创建 PR。

## 2. 背景与问题

OPS 当前没有项目里程碑主数据，也没有按项目、里程碑维护质量策划数据的能力。Issue #328 要求增加质量管理入口，首先交付质量策划后端能力：维护里程碑，为一个里程碑初始化一份质量策划，提供三级策划目录、权限控制和各策划子模块的增删改查、批量删除及操作日志。

本需求在 `openlibing-ops` 既有四层架构内增加 `productquality` 子包，不在 `com.openlibing.ops` 下新增非标准顶层包。用户、项目权限、操作日志与业务模型之间通过适配器隔离，为后续迁移到其他项目保留清晰边界；本期不拆分 Maven 子模块。

## 3. 目标

1. 在 OPS 的 MySQL 数据源中建立独立的质量管理策划数据模型，表名统一使用 `pq_` 前缀。
2. 支持项目下里程碑的创建、查询、修改和受限删除，并记录计划时间、实际时间及操作日志。
3. 里程碑创建后由用户显式触发质量策划初始化；同一里程碑仅有一份策划，重复初始化幂等返回同一策划。
4. 初始化时从 Java 固定模板生成最多三级的策划目录，包含全部必需及可选策划目录。
5. 对 Issue 已给出字段的 17 类业务数据提供强类型 CRUD；表格数据支持批量删除。
6. 所有接口按项目隔离数据：项目成员只读，项目管理员或项目质量负责人可写，只有项目管理员可维护质量负责人。
7. 所有写操作记录操作者、项目、资源、动作及变更前后快照。
8. 提供数据库脚本、单元测试和集成验证，满足仓库构建与静态检查要求。

## 4. 本期范围

### 4.1 里程碑与策划

- 项目里程碑维护：里程碑名称、计划时间、实际时间。
- 显式、幂等初始化质量策划。
- 一个里程碑对应一份质量策划，业务数据通过 `plan_id` 归属策划。
- 明细行可关联同一项目下的其他里程碑；后端必须校验归属，不能引用跨项目里程碑。
- 返回三级策划目录及当前用户权限，供后续前端渲染。

### 4.2 版本级公共策划

| Issue 模块 | 本期交付 |
|---|---|
| Step1 / 版本摘要 | 单条富文本内容查询、保存 |
| Step1 / 质量策划思路 | 单条思维导图 JSON 内容查询、保存 |
| Step1 / 内部改进要求（重点工作） | 固定字段表格 CRUD、批量删除 |
| Step1 / 历史经验导入 | 固定字段表格 CRUD、批量删除 |
| Step1 / 价值特性 | 固定字段表格 CRUD、批量删除 |
| Step1 / 策划输入分析 | 固定字段表格 CRUD、批量删除 |
| Step2 / 目标差距分析及分解 | 固定字段表格 CRUD、批量删除 |
| Step2 / 风险策划 | 固定字段表格 CRUD、批量删除 |
| Step3 / 质量要求策划 / 版本级要求 | 仅目录，Issue 未给字段，不建业务表 |
| Step3 / 交付件策划 / 版本级文档 | 仅目录，Issue 未给字段，不建业务表 |
| Step3 / 交付件策划 / 研发内部设计文档 | 仅目录，Issue 未给字段，不建业务表 |
| Step3 / 交付件策划 / 营销资料以及生态发展相关发布件 | 仅目录，Issue 未给字段，不建业务表 |
| Step3 / 度量指标策划 | 固定字段表格 CRUD、批量删除 |
| Step3 / 转测试评估和版本出口评估 | 固定字段表格 CRUD、批量删除 |
| Step4 / 会议运作制度（可选） | 固定字段表格 CRUD、批量删除 |
| Step4 / 状态报告制度（可选） | 固定字段表格 CRUD、批量删除 |
| Step4 / 知识输入（可选） | 固定字段表格 CRUD、批量删除 |
| Step4 / 知识输出（可选） | 固定字段表格 CRUD、批量删除 |

### 4.3 特性级、领域专项及其他专项

| Issue 模块 | 本期交付 |
|---|---|
| 特性级策划 / 专项策划（可选） | 固定字段表格 CRUD、批量删除 |
| 领域专项策划 / 工程能力专项 / 阶段规划表（可选） | 固定字段表格 CRUD、批量删除 |
| 领域专项策划 / 工程能力专项 / 领域检查项表（可选） | 固定字段表格 CRUD、批量删除 |
| 其他专项策划 / 专项策划（可选） | 仅目录，Issue 未给字段，不建业务表 |

### 4.4 权限与日志

- 项目成员：读取里程碑、目录、权限、自身项目内策划数据。
- 项目质量负责人：在项目成员只读权限基础上，拥有里程碑、策划及业务数据写权限。
- 项目管理员：拥有全部读写权限，并维护本项目质量负责人。
- 全局管理员按 OPS 现有管理角色语义放行。
- 所有写接口记录操作日志；查询接口不记录业务变更日志，越权拒绝保留安全审计信息。

## 5. 非本期范围

- 前端导航栏、页面、页签、表格和交互实现。
- 质量评估业务模块；本期仅在目录模型中预留后续扩展能力，不创建质量评估业务表或接口。
- 导入、导出、列设置。
- 质量目标、风险等级、指标实际值等自动计算或自动评估。
- 与外部作业平台、majun 平台、PI、QCC 等系统的自动集成；Issue 中相应字段仅作为策划数据保存。
- 文件上传、附件管理和在线富文本/思维导图编辑器。
- 独立 Maven 子模块、独立微服务或跨仓代码修改。
- 对 Issue 未给出字段的目录臆造表结构或枚举字典。

## 6. 关键业务规则

1. **目录层级**：目录最多三级。Issue 中“知识管理计划”作为知识管理策划下的展示分组，不额外形成第四级可导航节点；知识输入、知识输出直接作为第三级叶子。
2. **策划初始化**：创建里程碑只返回“待初始化”状态，不自动创建策划；显式初始化接口在事务内创建策划和目录。数据库唯一约束兜底，重复请求返回已有策划。
3. **数据隔离**：所有接口路径包含 `projectId`；策划接口还包含 `planId`。每次读写均校验 `projectId → planId → recordId` 的归属链。
4. **跨里程碑引用**：明细行的 `milestoneId` 是策划执行关联，不改变记录的 `planId` 归属；只允许选择同项目里程碑。
5. **批量删除**：ID 列表非空、去重、限制批量大小；任一 ID 不存在、已删除或不属于当前 `planId`，整批拒绝并回滚。
6. **字段语义**：Issue 标记 `*` 的字段由 Bean Validation 和业务层双重必填校验；措施进展为 0–100；未定义字典的类型、状态、角色、来源等字段使用字符串，不虚构枚举。
7. **逻辑删除**：业务数据统一逻辑删除，查询默认仅返回未删除数据。里程碑已有策划时不允许删除，避免隐式级联删除策划数据。
8. **审计**：创建人、创建时间、更新人、更新时间和逻辑删除标记是所有表的公共字段。

## 7. 验收标准

### 7.1 里程碑与初始化

- [ ] 项目成员可查询本项目里程碑，不能查询其他项目里程碑。
- [ ] 有写权限用户可创建和修改里程碑，名称、计划时间按规则校验，实际时间可为空。
- [ ] 未初始化策划的里程碑可逻辑删除；已初始化的里程碑删除被拒绝。
- [ ] 创建里程碑后响应明确返回待初始化状态。
- [ ] 显式初始化后生成一份策划及完整目录；并发或重复初始化不会产生重复策划或目录。

### 7.2 目录与权限

- [ ] 目录包含 Issue 指定的全部必需和可选节点，最大层级为 3，顺序稳定。
- [ ] 版本级要求、三类交付件、其他专项标记为“仅目录”，不存在伪造的 CRUD 接口。
- [ ] 项目成员读接口成功、写接口返回 403。
- [ ] 项目质量负责人可写但不能维护质量负责人。
- [ ] 项目管理员可维护质量负责人；非项目成员不能被设置为质量负责人。
- [ ] 修改路径中的项目、策划或记录 ID 为其他项目资源时返回 403 或资源不存在，不泄露数据内容。

### 7.3 业务数据

- [ ] 17 类已定义业务数据均有强类型请求/响应和对应持久化表。
- [ ] 15 类表格数据均支持分页查询、单条详情、新增、修改、单条删除和批量删除。
- [ ] 版本摘要和质量策划思路支持单条查询及保存，重复保存不产生多条有效记录。
- [ ] 所有 `*` 字段缺失时返回参数错误；进展小于 0 或大于 100 时返回参数错误。
- [ ] 明细行可关联同项目其他里程碑，关联其他项目里程碑时整次写入失败。
- [ ] 批量删除包含一个越权或不属于当前策划的 ID 时，所有记录均保持不变。

### 7.4 日志与质量

- [ ] 新增、修改、删除、批量删除、初始化及质量负责人变更均记录操作日志和前后快照。
- [ ] 日志不记录 token、Cookie 等认证凭证；失败操作不伪造成功的新数据快照。
- [ ] 相关单元测试、控制器权限测试、MyBatis 映射测试通过。
- [ ] `mvn spotless:apply`、`mvn checkstyle:check`、`mvn spotbugs:check`、`mvn pmd:check`、`mvn test` 通过。
- [ ] 数据库脚本可在全新 MySQL 8.0  schema 执行，重复升级路径有明确说明。

## 8. 交付物

- `openlibing-ops`：质量管理后端代码、MyBatis XML、MySQL 建表脚本和测试。
- `openlibing-docs`：本提案、`design.md`、`tasks.md`，以及独立的安全威胁模型和安全设计。
- 业务 PR 必须关联 Issue #328；用户自测明确确认后才创建业务 PR。
