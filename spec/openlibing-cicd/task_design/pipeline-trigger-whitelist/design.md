# 流水线白名单支持按人员维度配置 — 工程设计

## 需求背景

流水线管理员需要对关键流水线做精细化触发管控：仅允许指定人员执行手动运行和重试，降低误触发风险。当前系统的权限控制只到"角色 × 接口"粒度（项目管理员/CIE 可执行全部流水线的运行操作），无法对单条流水线限制到指定人员。本次改造在现有「流水线白名单管理」能力上扩展人员维度配置。

# 1. 方案设计

在流水线配置（`pipeline_info.config_json`）中新增 `triggerWhiteList` 触发人员名单字段（存储 openlibing 平台用户ID/UUID），提供名单的查询与全量保存接口；页面运行/重试链路在现有角色权限校验之后叠加名单校验（AND 关系），PR 评论等事件触发链路完全跳过名单校验。

采用该方案的原因：

- 名单是流水线自身的管控配置，与 `config_json` 中已有的 `commentWhiteList`（评论触发白名单）性质相同，复用同一存储模式，无 DDL 变更，存量数据天然兼容
- 校验关系为 AND 叠加收紧：名单只能收缩现有权限集合，不能放大，不破坏现有权限体系
- 前后端契约收口为两个派生布尔字段（`triggerRestricted` / `canTrigger`），前端不实现校验逻辑，后端规则演进前端零改动
- 名单标识与现有权限体系同域：openlibing 平台内部以 32 位 UUID（`user_basic_info.user_id`）识别用户，页面链路 `userId` 参数、`user_role_info` 角色表、`hasPermission` 鉴权全程使用 UUID，名单存 UUID 可直接字符串比对、免疫改名；GitCode 用户名仅存在于 PR webhook 等外部链路，不作为名单标识
- 名单仅管控页面手动触发：PR 评论触发者多为外部开发者（非 openlibing 项目成员，本就不在角色权限体系内），且其用户名与平台账号不同域，纳入名单校验必然全拦，故事件链路（`retryPipelineByEvent`）不做名单校验，维持原有 webhook/commentWhiteList 管控

涉及模块：

- 流水线白名单管理（名单配置入口）
- 流水线运行/重试（校验叠加）
- 流水线列表/详情查询（权限标记下发）
- 操作日志（名单变更审计）

# 2. 实现逻辑设计

## 配置链路

```text
白名单管理页 → 查询接口（返回现有名单[userId+userName]、项目可选成员列表、canEdit）
  → 编辑弹窗（人员选择器，从项目可选成员中增减）
  → 保存接口（全量覆盖，提交 userId 列表）→ 校验：编辑权限（具备流水线运行权限，动态查询）→ 白名单已开启 → UUID 格式/去重/上限 → 写入 config_json.triggerWhiteList → 记录操作日志
```

下拉数据源为**当前项目全部成员**（`user_role_info` 按 projectId 查询 join `user_basic_info` 取 userName，按 userId 去重），而非"当前具备执行权限的人"——名单多配无权限者无害（第一道门会拦），按权限快照筛选反而会在角色变更后与实际脱节。项目隔离天然成立：A 项目流水线配置时仅返回 A 项目成员。

## 校验链路

```text
页面运行/重试请求（userId = 平台 UUID）
  → AuthInterceptor @CheckPermission（现有角色权限校验，不改动）
  → Service 层名单校验（新增，仅 Controller 入口的 runPipeline/retryPipeline）：
      查 pipeline_info（projectId + sourcePipelineId）
      → 行不存在 或 triggerWhiteList 为空 → 放行（未配置 = 不限制）
      → 名单非空且 userId 不在内（忽略大小写）→ 拦截，返回统一文案
```

统一文案：`该流水线已限制触发人员，需同时具备流水线执行权限并在触发人员名单内`

## 权限标记下发

流水线列表接口响应为华为云 SDK 类型（`ListPipelinesResponse`），无法在既有列表/详情响应上直接新增字段。改为提供独立的批量标记接口 `POST /project/pipeline/trigger-users/flags`：入参项目 ID（可选流水线 ID 列表）+ 用户 ID，返回 `Map<pipelineId, {triggerRestricted, canTrigger}>`。前端加载列表/详情页时调用一次，映射中不存在的流水线视为不限制。

# 3. 类设计

| 类名                                                                                                                                                               | 职责                  | 主要修改内容                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `PipelineInfoEntity`                                                                                                                                               | 流水线配置实体        | 内部类 `ConfigJson` 新增 `triggerWhiteList` 字段（List\<String\> 平台用户ID，空 = 不限制）                                                                                     |
| `PipelineControllerV2`                                                                                                                                             | 流水线接口            | 新增名单查询、保存、权限标记批量查询三个端点                                                                                                                                   |
| `PipelineService` / `PipelineServiceImpl`                                                                                                                          | 流水线业务逻辑        | 新增名单查询/保存/标记查询方法；`runPipeline`、`retryPipeline` 叠加名单校验；新增 `retryPipelineByEvent`（事件链路专用，跳过名单校验）；新增成员 VO 转换与项目成员查询辅助方法 |
| `TriggerWhiteListQueryDTO` / `TriggerWhiteListSaveDTO` / `TriggerWhiteListRespDTO` / `TriggerFlagsQueryDTO` / `PipelineTriggerFlagVO` / `TriggerWhiteListMemberVO` | 名单接口契约          | 新增，请求/响应载体；`TriggerWhiteListMemberVO` 含 userId + userName                                                                                                           |
| `PipelineRetryEventHandler`                                                                                                                                        | PR 评论重试事件处理器 | 改调 `retryPipelineByEvent`，名单校验对其无感                                                                                                                                  |
| `LogOperationAndModule`                                                                                                                                            | 操作常量              | 新增"更新触发人员名单"操作常量                                                                                                                                                 |
| `PipelineWhiteListLogHandler`                                                                                                                                      | 白名单操作日志处理器  | 支持名单变更的日志记录                                                                                                                                                         |

# 4. 数据模型设计

数据库表：不涉及（`config_json` 为 json 列，字段级扩展无需 DDL，无 liquibase changeSet）。

Entity：`PipelineInfoEntity.ConfigJson` 新增：

```java
/** 触发人员白名单：存储 openlibing 平台用户ID（32 位 UUID）；null 或空 = 不限制 */
private List<String> triggerWhiteList;
```

DTO/VO：新增名单接口的 DTO/VO（见类设计）；`TriggerWhiteListRespDTO.triggerWhiteList` 返回 `List<TriggerWhiteListMemberVO>`（含 userId 与 userName），便于前端展示；`selectableMembers` 字段提供项目可选成员列表作为下拉数据源。

# 5. 性能设计

名单校验为运行/重试请求新增一次 `pipeline_info` 单行查询（`project_id + source_pipeline_id` 条件），该表数据量为个位到百行级，无性能影响。

当前场景无高频访问需求，无需新增缓存。新增接口满足 3 秒性能要求。

# 6. API 接口设计

新增接口均挂载在 `PipelineControllerV2`（`/project/pipeline` 前缀）。因 `menu_url_info` 权限表无本仓 liquibase 管理先例，新接口不挂 `@CheckPermission` 注解，改在 Service 层复用运行接口的菜单 URL（`/openlibing-cicd/project/pipeline/run`）做角色校验，权限语义与"可运行流水线"完全一致。可编辑角色由 `user_role_mapper.hasPermission` 基于菜单 URL 动态查询，不硬编码角色清单（BETA 当前快照：admin / project_manager / project_cie / pipeline_executor，可随权限配置调整）。

## 查询触发人员名单

- URL：`POST /project/pipeline/trigger-users/query`
- 请求：`{ projectId, pipelineId }`，query param `userId`
- 响应：`DataResult<TriggerWhiteListRespDTO>`，含 `pipelineId`、`triggerWhiteList: List<TriggerWhiteListMemberVO>`（每个元素含 `userId` 与 `userName`）、`selectableMembers: List<TriggerWhiteListMemberVO>`（当前项目全部成员，作为下拉数据源）、`canEdit: boolean`
- 校验：目标流水线白名单已开启；当前用户具备运行权限
- 失败兜底：当名单中某 userId 在 `user_basic_info` 查不到时，`userName` 回退为 userId 本身，不影响查询成功

## 保存触发人员名单

- URL：`POST /project/pipeline/trigger-users/save`
- 请求：`{ projectId, pipelineId, triggerWhiteList: List<String>（平台用户ID/UUID） }`，query param `userId`，全量覆盖语义，空数组 = 清除限制
- 校验：编辑权限（具备运行权限）、目标流水线白名单已开启、UUID 格式 `^[0-9a-fA-F]{32}$`、去重（忽略大小写）、上限 100
- 并发控制：Redis 锁（`pipeline:trigger-whitelist:{projectId}:{pipelineId}`，5 秒）
- 操作日志：`@LogApi` 记录到 `log_pipeline`，操作类型"更新流水线触发人员名单"

## 批量查询触发权限标记

- URL：`POST /project/pipeline/trigger-users/flags`
- 请求：`{ projectId, pipelineIds? }`，query param `userId`（可选，缺省时 canTrigger 为 false）
- 响应：`DataResult<Map<pipelineId, {triggerRestricted, canTrigger}>>`

## 既有接口扩展（兼容性）

无改动。运行/重试接口在 Service 层叠加名单校验，接口签名不变，旧前端无感知。

# 7. 安全设计

## 鉴权

新增接口不挂 `@CheckPermission`（`menu_url_info` 权限表无本仓 liquibase 管理先例，挂注解会导致全员 403），名单查询/保存在 Service 层复用运行接口的菜单 URL 做角色校验，编辑权限 = 运行权限（动态查询菜单绑定角色，不硬编码）。名单校验与现有角色权限为 AND 叠加，`runPipeline` / `retryPipeline` Service 层强制校验兜底，防止绕过前端直接调用。

## 校验覆盖范围（调用链核查结论）

- 页面手动运行：`PipelineControllerV2.runPipeline` → Service 校验 ✅
- 页面手动重试：`PipelineControllerV2.retryPipeline` → Service 校验 ✅
- PR 评论触发重试：`PipelineRetryEventHandler`（MQ）改调 `retryPipelineByEvent`，**完全跳过名单校验**，维持原有 webhook 开关 + commentWhiteList 管控。理由：该链路 userName 为 GitCode 用户名，与平台 UUID 不同域，纳入校验必然全拦；PR 触发者多为非 openlibing 成员的外部开发者，本就不是本需求的管控对象
- 二分定位（bisect）等其他内部链路不经过 `runPipeline` / `retryPipeline` 入口，不在管控范围（nightly 范畴，需求明确排除）

## 名单标识域与项目隔离

- 名单存 openlibing 平台用户ID（32 位 UUID），与第一道门 `hasPermission` 使用的标识同域，校验为纯字符串比对
- UUID 全局唯一不区分项目，项目隔离由两处保证：第一道门 `hasPermission` 按 projectId 查角色；名单本身存储在各流水线独立的 `config_json` 中（`project_id + source_pipeline_id` 定位）
- 全局 admin 在第一道门全项目通行（`or role = 'admin'`），但第二道门**不豁免**：名单非空时 admin 同样需在名单内才可触发（严格语义，admin 与普通用户一视同仁）；admin 始终具备名单编辑权限，不存在锁死风险

## 敏感信息

名单内容为平台用户ID 数组，非敏感信息，无特殊处理。

## 硬编码

无新增硬编码凭证；UUID 格式正则与上限值定义为常量。

## 审计日志

名单新增/修改/清空操作通过 `@LogApi` 记录到 `log_pipeline`（复用现有流水线白名单日志处理器），可追溯操作人与变更前后名单。

# 附录

## 二期升级独立表的触发条件（满足其一）

1. 需要跨流水线批量配置（独立表单条 SQL 可完成批量增量，json 需逐条读改写）
2. 出现"按人反查可触发流水线"需求
3. 单条流水线名单规模超过 100 人

满足前，名单存储保持在 `config_json` 内。

## 前端参考

前端期望表现与交互细节见同目录 `frontend-guide.md`（前端由 openlibing-cicd-web 仓独立实现）。
