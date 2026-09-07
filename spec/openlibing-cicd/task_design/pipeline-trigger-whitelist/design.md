# 流水线白名单支持按人员维度配置 — 工程设计

## 需求背景

流水线管理员需要对关键流水线做精细化触发管控：仅允许指定人员执行手动运行和重试，降低误触发风险。当前系统的权限控制只到"角色 × 接口"粒度（项目管理员/CIE 可执行全部流水线的运行操作），无法对单条流水线限制到指定人员。本次改造在现有「流水线白名单管理」能力上扩展人员维度配置。

# 1. 方案设计

## 1.1 现有权限判定逻辑（改造基线）

页面运行/重试请求到达后端后，依次经过两道校验：

**门1 · 角色权限校验**（`AuthInterceptor` 拦截 `@CheckPermission` 注解，现有逻辑，本次不改动）：

- 请求未携带 `userId`（匿名访问）：走 `checkAnonymousAccess`——流水线关联仓库全部公开（或无代码源）则放行；任一仓库私有则拦截（需登录）
- 请求携带 `userId`（登录访问）：先判仓库公开性（`isGitUrlPublic`，结果缓存在 Redis）——**公开仓直接放行，不查角色表**；私有仓再按请求 URI 对应的权限点查角色（`userRoleMapper.hasPermission`），未命中拦截

**门2 · 触发人员名单校验**（本次新增，Service 层）：

- 名单为空 → 放行；名单非空 → `userId` 必须在名单内才放行

由此得出的关键结论：**公开仓的门1 对任何访问（含匿名）恒放行，名单是公开仓流水线唯一的触发防线**。这意味着"公开仓 + 配名单"是合理且会被使用的场景（管理员将一条全员可见的公开仓流水线收紧到少数人），名单校验必须对公开仓同样生效。

## 1.2 本次设计的场景矩阵

以 仓库可见性 × 登录态/角色 × 名单配置 三个维度穷举页面触发场景（BETA 数据库抽样公开仓占比约 68%，公开仓不是边缘场景）：

| #   | 仓库 | 登录态 / 角色        | 名单         | 门1      | 门2      | 最终结果 |
| --- | ---- | -------------------- | ------------ | -------- | -------- | -------- |
| 1   | 私有 | 匿名                 | 任意         | 拦截     | —        | 拦截     |
| 2   | 私有 | 登录 · 无触发角色    | 任意         | 拦截     | —        | 拦截     |
| 3   | 私有 | 登录 · 有触发角色    | 未配置       | 放行     | 放行     | 放行     |
| 4   | 私有 | 登录 · 有触发角色    | 在名单内     | 放行     | 放行     | 放行     |
| 5   | 私有 | 登录 · 有触发角色    | 不在名单内   | 放行     | 拦截     | 拦截     |
| 6   | 公开 | 匿名                 | 未配置       | 放行     | 放行     | 放行     |
| 7   | 公开 | 匿名                 | 已配置       | 放行     | 拦截     | 拦截     |
| 8   | 公开 | 登录 · 无触发角色    | 未配置       | 放行     | 放行     | 放行     |
| 9   | 公开 | 登录 · 无触发角色    | 在名单内     | 放行     | 放行     | 放行     |
| 10  | 公开 | 登录 · 无触发角色    | 不在名单内   | 放行     | 拦截     | 拦截     |
| 11  | 公开 | 登录 · 有触发角色    | 未配置 / 在名单内 / 不在名单内 | 放行 | 同 #3-#5 | 同 #3-#5 |

注：`pipeline_run`（执行）与 `pipeline_retry`（重试）是两个独立权限点，角色集不同（retry 额外放行 `project_member`），"有无触发角色"按具体动作分别判定。

## 1.3 方案内容

在流水线配置（`pipeline_info.config_json`）中新增 `triggerWhiteList` 触发人员名单字段（存储 openlibing 平台用户ID/UUID），提供名单的查询与全量保存接口；页面运行/重试链路在现有角色权限校验之后叠加名单校验（AND 关系），PR 评论等事件触发链路完全跳过名单校验。

前端按钮置灰与提示文案的判定采用**后端权威结论下发**：新增统一评估函数将门1 + 门2 的判定收口为一处实现，运行/重试链路调用它做实际拦截，flags 查询接口调用它做结果投影（只取结论，不拦截），返回 `canTrigger` + `denyReason`（拦截原因枚举），前端只做原因 → 文案映射，不在前端复现任何判定逻辑。

**否决的备选方案——门2 独立投影**（flags 只算名单、不查角色与仓库公开性）：实现最简，但 `canTrigger=true` 仅代表"名单不拦"，无法覆盖门1 结论，前端被迫在"与既有 hasAuth 叠加（公开仓误杀，场景 #9 复现 B5）"与"覆盖 hasAuth（场景 #2/#4 类配置下按钮亮起但点击 403）"之间二选一，两种接法各带一个内生缺陷，故否决。

采用该方案的原因：

- 名单是流水线自身的管控配置，与 `config_json` 中已有的 `commentWhiteList`（评论触发白名单）性质相同，复用同一存储模式，无 DDL 变更，存量数据天然兼容
- 校验关系为 AND 叠加收紧：名单只能收缩现有权限集合，不能放大，不破坏现有权限体系
- **判定逻辑单点收口**：门1 + 门2 只在一个函数里计算，实际拦截与前端展示使用同一段代码的结论，结构性消除"两处实现不同步漂移"这一类缺陷（公开仓豁免规则曾因 flags 未复刻而漏判，即此类）
- **denyReason 直给结论**：前端不做布尔组合推导拦截原因，后端规则演进（如角色配置调整、公开仓策略变化）前端零改动，仅需文案映射
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
  → 保存接口（全量覆盖，提交 userId 列表）→ 校验：@CheckPermission 框架鉴权（菜单/角色映射，平台侧可配置）→ 白名单已开启 → UUID 格式/去重/上限 → 写入 config_json.triggerWhiteList → 记录操作日志
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

统一文案：`该流水线已限制触发人员，请在「流水线白名单管理」中查看可触发人员`

## 权限标记下发

流水线列表接口响应为华为云 SDK 类型（`ListPipelinesResponse`），无法在既有列表/详情响应上直接新增字段。改为提供独立的批量标记接口 `POST /project/pipeline/trigger-users/flags`：入参项目 ID（可选流水线 ID 列表）+ 用户 ID，返回**稀疏 Map**——仅包含配置了名单的流水线，未配置名单的流水线不出现在映射中（前端视为不限制、维持既有表现）。

每个条目的值通过统一评估函数计算：

```java
TriggerDecision evaluate(userId, pipeline, action) {
  boolean hasRole = checkRole(userId, pipeline, action);       // 复用门1 角色查询
  boolean publicExempt = hasRole ? false : isGitUrlPublic(pipeline); // 仅无角色时才查公开性
  boolean gate1Pass = hasRole || publicExempt;
  boolean inWhitelist = whitelist.isEmpty() || containsIgnoreCase(whitelist, userId);
  return new TriggerDecision(gate1Pass && inWhitelist,
      reasonOf(hasRole, publicExempt, inWhitelist));           // denyReason 枚举
}
```

返回结构为 `{canTrigger, denyReason}`：`canTrigger` 为两道门 AND 结论（"点了真的会成功"），`denyReason` 为拦截原因（`NONE` / `NO_ROLE` / `NOT_IN_WHITELIST` / `NO_ROLE_AND_NOT_IN_WHITELIST`），前端据此选择提示文案（缺角色走统一角色申请体系，不在名单联系项目管理员加名单，两者皆缺给并行指引）。

**公开性查询剪枝**：评估函数仅在"名单非空 且 用户无触发角色"时才调用 `isGitUrlPublic`——有角色时门1 必过、公开性不影响结论；未配名单时门2 必过。公开性判定复用门1 已有的 Redis 缓存（key：`projectId+pipelineId`），缓存未命中才回源查询。实际拦截链路（runPipeline/retryPipeline）仍由 AuthInterceptor 先行处理门1，Service 层名单校验保持现有纯名单判断，评估函数用于 flags 投影，二者结论一致（同一套门1 规则 + 同一套名单规则）。

**公开性判断的归属（依赖设计）**：`isGitUrlPublic` 实现收编进 `PipelineServiceImpl` 并通过 `PipelineService` 接口暴露，形成零新增依赖边的结构——`AuthInterceptor → PipelineService`（既有边，委托调用）、`getTriggerFlags → this.isGitUrlPublic`（自调用）。否决了两个备选：① 业务层直接调用 AuthInterceptor 的 public 方法（形成 `PipelineServiceImpl → AuthInterceptor → PipelineService` 循环依赖，且 MVC 拦截器承担业务查询职责，分层倒挂）；② 独立 `GitVisibilityService` 中间层（该服务需注入 `PipelineService` 查流水线详情，与 `PipelineServiceImpl` 的依赖形成 bean cycle，Spring 6.x 默认拒绝启动）。

# 3. 类设计

| 类名                                                                                                                                                               | 职责                  | 主要修改内容                                                                                                                                                                   |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `PipelineInfoEntity`                                                                                                                                               | 流水线配置实体        | 内部类 `ConfigJson` 新增 `triggerWhiteList` 字段（List\<String\> 平台用户ID，空 = 不限制）                                                                                     |
| `PipelineControllerV2`                                                                                                                                             | 流水线接口            | 新增名单查询、保存、权限标记批量查询三个端点                                                                                                                                   |
| `PipelineService` / `PipelineServiceImpl`                                                                                                                          | 流水线业务逻辑        | 新增名单查询/保存/标记查询方法；`runPipeline`、`retryPipeline` 叠加名单校验；新增 `retryPipelineByEvent`（事件链路专用，跳过名单校验）；新增统一评估方法（门1 + 门2 收口，flags 投影调用）；新增成员 VO 转换与项目成员查询辅助方法；**收编公开性判断**：`isGitUrlPublic` / `checkGitUrlPublicFromHwCloud`（含 Redis 缓存与异步刷新）由 `AuthInterceptor` 迁入并作为接口方法暴露，`getTriggerFlags` 自调用，`AuthInterceptor` 经既有依赖委托调用 |
| `AuthInterceptor`                                                                                                                                                  | 访问权限校验拦截器    | 公开性判断调用点改为 `pipelineService.isGitUrlPublic(...)`（既有依赖，无新增边），删除原私有实现；匿名链路 `checkAnonymousAccess` 与角色校验主链路不变 |
| `TriggerDenyReasonEnum`                                                                                                                                            | 拦截原因枚举          | 新增：`NONE` / `NO_ROLE` / `NOT_IN_WHITELIST` / `NO_ROLE_AND_NOT_IN_WHITELIST`，flags 接口下发，前端据此映射提示文案 |
| `TriggerWhiteListQueryDTO` / `TriggerWhiteListSaveDTO` / `TriggerWhiteListRespDTO` / `TriggerFlagsQueryDTO` / `PipelineTriggerFlagVO` / `TriggerWhiteListMemberVO` | 名单接口契约          | 新增，请求/响应载体；`TriggerWhiteListMemberVO` 含 userId + userName；`PipelineTriggerFlagVO` 含 canTrigger + denyReason |
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

flags 接口的成本控制（统一评估函数带来的公开性查询）：

- **剪枝**：仅在"名单非空 且 当前用户无触发角色"的流水线上触发公开性查询。多数用户要么有角色（跳过）、要么项目内配名单的流水线很少（单项目通常个位数），实际回源查询量远小于流水线总数
- **缓存复用**：公开性判定复用门1 已有的 Redis 缓存（key：`projectId+pipelineId`），命中为 O(1)；缓存未命中才查库/华为云，并沿用既有异步刷新机制
- **失败降级**：公开性查询异常时按私有仓处理（denyReason 走 NO_ROLE 路径），不阻塞 flags 接口整体返回

新增接口满足 3 秒性能要求。

# 6. API 接口设计

新增接口均挂载在 `PipelineControllerV2`（`/project/pipeline` 前缀）。`trigger-users/query` 与 `trigger-users/save` 挂 `@CheckPermission` 走框架鉴权（与 `/whitelist` 族接口一致），依赖平台侧的菜单-角色权限映射，**须在发版前完成权限点配置**（见第 7 节"权限点配置"）。`trigger-users/flags` 不挂注解：列表页所有用户（含普通成员）加载时均需调用，仅返回当前用户自身的权限布尔，无敏感信息。

## 查询触发人员名单

- URL：`POST /project/pipeline/trigger-users/query`
- 请求：`{ projectId, pipelineId }`，query param `userId`
- 响应：`DataResult<TriggerWhiteListRespDTO>`，含 `pipelineId`、`triggerWhiteList: List<TriggerWhiteListMemberVO>`（每个元素含 `userId` 与 `userName`）、`selectableMembers: List<TriggerWhiteListMemberVO>`（当前项目全部成员，作为下拉数据源）、`canEdit: boolean`（恒为 true——能通过 `@CheckPermission` 即具备编辑权）
- 校验：`@CheckPermission` 框架鉴权；目标流水线白名单已开启
- 失败兜底：当名单中某 userId 在 `user_basic_info` 查不到时，`userName` 回退为 userId 本身，不影响查询成功

## 保存触发人员名单

- URL：`POST /project/pipeline/trigger-users/save`
- 请求：`{ projectId, pipelineId, triggerWhiteList: List<String>（平台用户ID/UUID） }`，query param `userId`，全量覆盖语义，空数组 = 清除限制
- 校验：`@CheckPermission` 框架鉴权；目标流水线白名单已开启、UUID 格式 `^[0-9a-fA-F]{32}$`、去重（忽略大小写）、上限 100
- 并发控制：Redis 锁（`pipeline:trigger-whitelist:{projectId}:{pipelineId}`，5 秒）
- 操作日志：`@LogApi` 记录到 `log_pipeline`，操作类型"更新流水线触发人员名单"

## 批量查询触发权限标记

- URL：`POST /project/pipeline/trigger-users/flags`（不挂 `@CheckPermission`）
- 请求：`{ projectId, pipelineIds? }`，query param `userId`（可选，匿名/缺省时 canTrigger 为 false、denyReason 为 `NO_ROLE`，前端统一提示登录）
- 响应：`DataResult<Map<pipelineId, {canTrigger, denyReason}>>`，**稀疏 Map**——仅包含配置了名单的流水线，未配名单的流水线不出现（前端视为不限制）
- denyReason 取值：`NONE`（可触发）/ `NO_ROLE`（私有仓未命中触发角色）/ `NOT_IN_WHITELIST`（门1 通过但不在名单）/ `NO_ROLE_AND_NOT_IN_WHITELIST`（两条件均不满足，前端给并行指引）
- 响应示例：

```json
{
  "code": 200,
  "data": {
    "9a1f...": { "canTrigger": true,  "denyReason": "NONE" },
    "b2c3...": { "canTrigger": false, "denyReason": "NOT_IN_WHITELIST" },
    "d4e5...": { "canTrigger": false, "denyReason": "NO_ROLE_AND_NOT_IN_WHITELIST" }
  }
}
```

## 既有接口扩展（兼容性）

无改动。运行/重试接口在 Service 层叠加名单校验，接口签名不变，旧前端无感知。

# 7. 安全设计

## 鉴权

`trigger-users/query` 与 `trigger-users/save` 挂 `@CheckPermission` 走框架鉴权（AuthInterceptor 按接口自身 URL 查菜单-角色映射），与同 Controller 的 `/whitelist` 族接口同构；Service 层不再重复做角色校验。`trigger-users/flags` 不挂注解（全员可调，仅返回当前用户自身权限布尔）。名单校验与现有角色权限为 AND 叠加，`runPipeline` / `retryPipeline` Service 层强制校验兜底，防止绕过前端直接调用。

## 权限点配置（发版前置，平台管理中心操作）

框架鉴权依赖 `menu_url_info` → `role_permission_manager` → `role_type_info` 三表映射，新 URL 无配置记录时挂注解接口会被全员 403，故**必须先配置、后发版**（配置先行对旧代码无影响）。

**第 1 步·菜单管理**：新增菜单节点并绑定接口 URL（URL 绑定是鉴权生效的关键，只建菜单不绑 URL 则配置无效）：

| 菜单名 | 绑定 URL | Method |
| ------ | -------- | ------ |
| 查询流水线触发人员名单 | `/openlibing-cicd/project/pipeline/trigger-users/query` | POST |
| 保存流水线触发人员名单 | `/openlibing-cicd/project/pipeline/trigger-users/save` | POST |

**第 2 步·角色管理**：新菜单节点出现后为以下角色勾选（与现有「流水线黑白名单」权限对齐）：

| 角色标识 | 角色名称（勾选时的中文显示） |
| -------- | --------------------------- |
| `project_manager` | 项目管理员 |
| `project_cie` | 流水线工程师 |
| `admin` | 系统管理员 |

`pipeline_executor`（流水线执行者）**不勾选**——名单管理是管控配置动作，与黑白名单开关一致仅管理角色可操作。相比早期 Service 层复用 run 权限的实现（含 executor），executor 编辑名单的能力被收窄，属预期行为变化。

**发版后验证矩阵**：

| 账号 | 预期 |
| ---- | ---- |
| 有管理角色的账号 | query/save 正常；在名单内可触发 |
| 无管理角色的普通成员 | query/save 被 403（第一道门）；flags 正常返回 |
| 有管理角色但不在名单 | query/save 正常，执行被名单拦截（第二道门） |

## 校验覆盖范围（调用链核查结论）

- 页面手动运行：`PipelineControllerV2.runPipeline` → Service 校验 ✅
- 页面手动重试：`PipelineControllerV2.retryPipeline` → Service 校验 ✅
- PR 评论触发重试：`PipelineRetryEventHandler`（MQ）改调 `retryPipelineByEvent`，**完全跳过名单校验**，维持原有 webhook 开关 + commentWhiteList 管控。理由：该链路 userName 为 GitCode 用户名，与平台 UUID 不同域，纳入校验必然全拦；PR 触发者多为非 openlibing 成员的外部开发者，本就不是本需求的管控对象
- 二分定位（bisect）等其他内部链路不经过 `runPipeline` / `retryPipeline` 入口，不在管控范围（nightly 范畴，需求明确排除）

## 名单标识域与项目隔离

- 名单存 openlibing 平台用户ID（32 位 UUID），与第一道门 `hasPermission` 使用的标识同域，校验为纯字符串比对
- UUID 全局唯一不区分项目，项目隔离由两处保证：第一道门 `hasPermission` 按 projectId 查角色；名单本身存储在各流水线独立的 `config_json` 中（`project_id + source_pipeline_id` 定位）
- 全局 admin 在第一道门全项目通行（`or role = 'admin'`），但第二道门**不豁免**：名单非空时 admin 同样需在名单内才可触发（严格语义，admin 与普通用户一视同仁）；admin 始终具备名单编辑权限，不存在锁死风险

## 已知安全披露 · userId 参数伪造（历史遗留，本次书面升级）

run/retry 接口的 `userId` 为 `@RequestParam` 传参，后端未与真实会话身份核验，属于历史遗留认证缺口（非本次引入）。**白名单功能上线后该缺口的风险等级上升**：在"公开仓 + 配名单"场景下（公开仓门1 恒放行），一个不在名单内的用户将请求中的 `userId` 改写为名单内任意用户的 UUID，即可绕过门2 触发本应受限的关键流水线——名单功能对公开仓（约 68% 仓库）的防误触发承诺因此不成立。

处置决策：

- 本 PR **不在认证体系上做修复**（改动面属平台级会话改造，超出本需求范围），以本节书面披露为准，避免评审通过后成为无人知晓的隐性缺陷
- 同步向安全团队提交正式工单，标注"因白名单功能上线，此漏洞利用价值从无提升为可绕过访问控制"，推动平台级修复（run/retry 从真实会话取身份）
- flags 查询链路不受影响：展示用途，用户无动机伪造自己的 userId 去看错误的按钮状态

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
