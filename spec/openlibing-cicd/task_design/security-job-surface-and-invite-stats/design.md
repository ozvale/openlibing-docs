# security-job-surface-and-invite-stats — 技术设计

## 1. 方案设计

**问题定位**：

- **攻击面（暴露入口）**：`XxlJobHandler` 中的 `@XxlJob("refreshWebhookHandler")` handler（原 1274-1316 行）。调度中心注册后，具备调度权限即可触发，经 `parseWebhookRefreshJobParam()` 解析参数后进入 `WebhookRefreshService`，对大量仓库执行 webhook 刷新/迁移操作。该链路共 9 个生产类，体量约 1580 行，属于可以整体收敛的定时任务暴露面。
- **审计与统计（Sink）**：`XxlJobHandler#acceptProjectInvitations`（780-855 行）逐条 `invitationLogMapper.insert` 落库，以及 `acceptProjectInvitationHandler`（736-774 行）的日志输出。改前该链路存在空参静默返回、`description.substring` 无空判、无异常隔离、统计口径不区分成功失败、`expires_at` 缺失时按默认时间落库等问题。

**攻击链 / 问题链**：

```
调度中心 → XxlJobHandler 入口
  ├─ refreshWebhookHandler → parseWebhookRefreshJobParam → WebhookRefreshService（批量 webhook 刷新/迁移）
  └─ acceptProjectInvitationHandler → getGitCodeInvitations → acceptProjectInvitations
       → 调用 GitCode 接受邀请 → invitationLogMapper.insert（无异常隔离、统计失真）
```

**修复策略**：

1. 整体删除 webhook 刷新链路（生产类 + 测试类），从入口层面消除该定时任务。
2. 邀请任务做审计加固：补齐关键分支日志、逐条异常隔离、按接口返回码精确统计、`expires_at` 缺失时跳过落库、日志中不出现任何 token。

**变更性质**：本批次含行为变化，不属于纯等价加固——定时任务下线、配置项失效、部分邀请不再落库，需运维配合（见第 7 章）。

## 2. 实现逻辑设计

### 2.1 删除 webhook 刷新链路

删除 9 个生产类与 2 个测试类：

- 生产类：`WebhookRefreshService`(1071 行)、`WebhookMigrationHelper`(181)、`WebhookRefreshJobParam`(152)、`WebhookRefreshStats`(24)、`WebhookMigrationRule`(17)、`CustomOrgEntry`(27)、`WebhookRefreshProperties`(31)、`WebhookMigrationMode`(36)、`WebhookRefreshScope`(40)。
- 测试类：`WebhookRefreshJobParamTest`(53)、`WebhookRefreshServiceTest`(604)。

### 2.2 XxlJobHandler 移除 handler

改前：存在 `@XxlJob("refreshWebhookHandler")` 方法与 `parseWebhookRefreshJobParam()`（原 1274-1316 行），并通过构造注入持有 `webhookRefreshService`。

改后：上述方法、注入字段及相关 dto import 全部删除。

### 2.3 acceptProjectInvitationHandler（736-774 行）

改前：

- jobParam 为空时静默 `return`，无日志。
- `description.substring` 无空判。

改后：

- jobParam 为空：`log.warn("...skipped, job param is empty")` 后返回。
- 解析成功：打印 projectIds。
- `entity == null`、token 为空：分别补 `log.warn`。
- 私有方法 `getGitCodeInvitations`、`acceptProjectInvitations` 新增 `projectId`、`gitcodeLogin` 入参，用于日志上下文与统计归类。

### 2.4 acceptProjectInvitations（780-855 行）

改前：单循环无异常处理，逐条直接 `invitationLogMapper.insert`。

改后：

- 逐条 `log.info` 记录 sourceType / sourceName / inviterUsername / inviteUrl，**不含任何 token**。
- 接受调用包 `catch (JSONException)` → failCount++ 后 continue，单条失败不影响后续邀请。
- 仅 `"200".equals(resultMsg)` 时 `acceptedBySource.merge(sourceName, 1, Integer::sum)`；否则 failCount++ 并 error 日志。
- 落库分别 `catch (DataAccessException)` 与 `catch (RuntimeException)`。
- 末尾汇总输出 total / accepted / failed / acceptedBySource。

### 2.5 新增 saveInvitationLog（857-885 行）

- `invitation.getInstant("expires_at")` 为 null 时 `log.warn` 并跳过落库，避免用默认时间写入造成审计误判。**已知取舍**：外部已接受的邀请因此没有审计记录，形成可抵赖盲点；改进方向是「缺失时仍落库、`expires_at` 置 NULL 并标记未知」，见 §7 待办。
- `description` 为 null 转空串，之后仍按 100 字符截断。

## 3. 类设计

| 类                                                                                                                                                                                                                              | 变化                                                                                                                                                                    |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `WebhookRefreshService` / `WebhookMigrationHelper` / `WebhookRefreshJobParam` / `WebhookRefreshStats` / `WebhookMigrationRule` / `CustomOrgEntry` / `WebhookRefreshProperties` / `WebhookMigrationMode` / `WebhookRefreshScope` | 整体删除                                                                                                                                                                |
| `WebhookRefreshJobParamTest` / `WebhookRefreshServiceTest`                                                                                                                                                                      | 整体删除                                                                                                                                                                |
| `XxlJobHandler`                                                                                                                                                                                                                 | 删除 `refreshWebhookHandler` 方法与 `parseWebhookRefreshJobParam()`；删除 `webhookRefreshService` 字段及构造注入                                                        |
| `XxlJobHandler`                                                                                                                                                                                                                 | `acceptProjectInvitationHandler` 保持对外 handler 不变，补齐异常分支日志；`getGitCodeInvitations`、`acceptProjectInvitations` 新增 `projectId`、`gitcodeLogin` 两个入参 |
| `XxlJobHandler`                                                                                                                                                                                                                 | `acceptProjectInvitations` 内新增单条异常隔离、精确计数与末尾汇总                                                                                                       |
| `XxlJobHandler`                                                                                                                                                                                                                 | 新增私有方法 `saveInvitationLog`（857-885 行），负责将单条邀请转换为 `InvitationLogEntity` 并落库，含 `expires_at` 空判与 `description` 截断                            |

无新增类；`@XxlJob` 注册的 handler 数量减 1。

## 4. 数据模型设计

无变更。不新增或修改表结构、实体字段与索引，`InvitationLogEntity` 字段集合不变；唯一区别是 `expires_at` 缺失的邀请不再写入该表。

## 5. 性能设计

- 删除体量最大的 webhook 刷新链路后，定时任务侧的 CPU 与 IO 开销归零。
- 邀请任务新增逐条 `log.info` 与异常隔离，单条失败不再中断整批，整体吞吐略有提升。
- 无缓存策略、线程池、超时参数调整；无新增外部调用。
- 落库异常分类捕获不改变原有写库次数。

## 6. API接口设计

无变更。本次改动集中在 xxl-job handler 与内部服务，`openlibing-cicd` 对外 HTTP 接口的路径、入参、出参与返回结构均未变化；无 pom 变更。

## 7. 安全设计

**防护边界**：

- 定时任务入口收敛：`refreshWebhookHandler` 从代码与调度两端下线，具备调度权限者无法再通过该入口触发批量 webhook 刷新/迁移。
- 日志脱敏边界：**本次改造涉及的日志语句**只输出 sourceType / sourceName / inviterUsername / inviteUrl，不含任何 token；该结论不覆盖 `acceptProjectInvitation`（约 887 行）以 `?invitation_token=` 查询串外呼 GitCode 的第三方调用（见残留风险）。

**中间态澄清**：

- `6272dd2e8` 曾输出脱敏后的 `invitation_token` 并引入 `maskToken`；`2363b88d2` 已将相关输出与 `maskToken` 全部删除，最终日志不含任何 token。

**失败语义**：

- 单条邀请接受抛 `JSONException`：failCount++ 后继续，不向上抛出。
- 接受结果非 `"200"`：failCount++ 并打 error，不计入 acceptedBySource。
- 落库异常：`DataAccessException` 与 `RuntimeException` 分别捕获，不中断整批。
- `expires_at` 缺失：跳过落库并 warn，不写入默认时间；代价是该邀请无审计记录（可抵赖盲点），改进见待办。
- handler 级行为变化：jobParam 为空由静默返回改为 warn 后返回。

**残留风险与已知取舍**：

- `acceptProjectInvitation`（887 行起）仍以 `?invitation_token=` 查询串调用 GitCode 第三方接口，本次未覆盖，待后续单独整改。
- `expires_at` 为 null 时整条跳过落库，外部已接受的邀请因此缺少审计记录，形成可抵赖盲点。
- 本轮仅删除测试类，未为邀请任务新逻辑补充 mock 用例（依赖 mapper 与外部 GitCode 调用），新增的异常隔离与统计分支暂无自动化覆盖。
- 调度中心若保留 `refreshWebhookHandler` 任务会持续失败，需在发布前删除；Nacos 配置项 `openlibing.cicd.webhook.refresh-rules` 在发布后清理（顺序见 proposal「发布前置清单」）。
- 第三方接口若调整返回码文案，`"200".equals(resultMsg)` 的判定会导致全部计入失败，属既有接口契约依赖。

**待办（未完成项）**：

- `saveInvitationLog` 改为 `expires_at` 缺失时仍落库（置 NULL 并标记未知），补齐审计记录。
- 补充 3 个 mock 单测：非 `"200"` → failCount++ 且不计入 acceptedBySource；单条 `JSONException` 不中断整批；落库异常不影响后续邀请。
- `acceptProjectInvitation` 的 `?invitation_token=` 查询串迁移到请求头，与 `security-token-header-migration` 同口径。
