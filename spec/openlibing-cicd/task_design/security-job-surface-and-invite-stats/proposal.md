# security-job-surface-and-invite-stats: 下线 webhook 刷新定时任务并修复邀请接受任务的审计与统计口径

## 需求背景

对应安全扫描问题 openlibing-cicd#332，包含两个整改点：

1. **xxl-job 攻击面收敛**：`refreshWebhookHandler` handler 承载 webhook 刷新与迁移逻辑，整条链路由 9 个生产类组成（`WebhookRefreshService` 1071 行等），任务在调度中心注册后即可被具备调度权限者触发，对大量仓库执行 webhook 刷新/迁移操作，暴露面大且维护成本高。
2. **邀请接受任务的审计与统计缺陷**：`acceptProjectInvitationHandler` 在 jobParam 为空时静默 `return`，无任何日志；`description` 直接 `substring` 无空判；逐条接受邀请时无异常隔离，单条失败会中断整批；统计不区分接受成功与失败；`expires_at` 缺失时仍按默认时间落库，造成审计数据误判。

## 功能描述

- 删除 `refreshWebhookHandler` handler 及整条 `WebhookRefresh*` 链路（9 个生产类），同步删除 2 个对应测试类。
- `XxlJobHandler` 移除 `webhookRefreshService` 构造注入字段、相关 dto import 与 `parseWebhookRefreshJobParam()`。
- `acceptProjectInvitationHandler` 补齐空参、实体为空、token 为空等异常分支的 `log.warn`，解析成功后打印 projectIds；`getGitCodeInvitations`、`acceptProjectInvitations` 新增 `projectId`、`gitcodeLogin` 入参。
- `acceptProjectInvitations` 增加逐条 `log.info`（sourceType/sourceName/inviterUsername/inviteUrl，不含任何 token）、`catch (JSONException)` 单条隔离、仅 `"200".equals(resultMsg)` 计入 acceptedBySource、落库异常分类捕获，末尾汇总 total/accepted/failed/acceptedBySource。
- 新增私有方法 `saveInvitationLog`，`expires_at` 为 null 时 warn 并跳过落库，`description` 为 null 转空串后仍截断 100 字符。

## 验收标准

- [x] 12 个文件变更，124 insertions / 2312 deletions
- [x] 代码仓内不再存在 `refreshWebhookHandler` handler、`parseWebhookRefreshJobParam()` 与 `WebhookRefresh*` 相关类
- [x] `XxlJobHandler` 不再注入 `webhookRefreshService`
- [x] 邀请接受任务本次改造涉及的日志语句均不含任何 token（`6272dd2e8` 引入的 `maskToken` 已在 `2363b88d2` 全部删除）；`acceptProjectInvitation`（约 887 行）以 `?invitation_token=` 查询串外呼 GitCode 的链路未覆盖，见残留风险
- [x] 单条邀请接受抛 `JSONException` 时 failCount++ 并继续处理后续邀请，不中断整批
- [x] 仅 `"200".equals(resultMsg)` 时执行 `acceptedBySource.merge(sourceName, 1, Integer::sum)`
- [x] 落库分别以 `catch (DataAccessException)`、`catch (RuntimeException)` 处理
- [x] `expires_at` 缺失的邀请不写入 `InvitationLogEntity`（避免默认时间造成审计误判；代价是外部已接受的邀请缺少审计记录，属已知取舍）
- [ ] 本轮未补自动化测试：删除的是整条下线链路；邀请任务新逻辑依赖 mapper 与外部 GitCode 调用，`catch (JSONException)` 隔离、`"200".equals(resultMsg)` 精确计数、落库异常分类捕获、`expires_at` 空判均为未自动化验证的行为变更
- [x] 对外 HTTP 接口无出入参变化，无 pom 变更

## 影响范围

| 文件                                                                                      | 操作 | 说明                                                                                                                  |
| ----------------------------------------------------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/cicd/business/service/impl/WebhookRefreshService.java`      | 删除 | 1071 行，webhook 刷新主逻辑                                                                                           |
| `src/main/java/com/openlibing/cicd/business/service/impl/WebhookMigrationHelper.java`     | 删除 | 181 行                                                                                                                |
| `src/main/java/com/openlibing/cicd/business/dto/webhooks/WebhookRefreshJobParam.java`     | 删除 | 152 行                                                                                                                |
| `src/main/java/com/openlibing/cicd/business/dto/webhooks/WebhookRefreshStats.java`        | 删除 | 24 行                                                                                                                 |
| `src/main/java/com/openlibing/cicd/business/dto/webhooks/WebhookMigrationRule.java`       | 删除 | 17 行                                                                                                                 |
| `src/main/java/com/openlibing/cicd/business/dto/webhooks/CustomOrgEntry.java`             | 删除 | 27 行                                                                                                                 |
| `src/main/java/com/openlibing/cicd/business/config/WebhookRefreshProperties.java`         | 删除 | 31 行，`@ConfigurationProperties(prefix="openlibing.cicd.webhook")`                                                   |
| `src/main/java/com/openlibing/cicd/common/enums/WebhookMigrationMode.java`                | 删除 | 36 行，枚举                                                                                                           |
| `src/main/java/com/openlibing/cicd/common/enums/WebhookRefreshScope.java`                 | 删除 | 40 行                                                                                                                 |
| `src/test/java/com/openlibing/cicd/business/dto/webhooks/WebhookRefreshJobParamTest.java` | 删除 | 53 行                                                                                                                 |
| `src/test/java/com/openlibing/cicd/business/service/impl/WebhookRefreshServiceTest.java`  | 删除 | 604 行                                                                                                                |
| `src/main/java/com/openlibing/cicd/common/job/XxlJobHandler.java`                         | 修改 | 删除 handler 与解析方法；加固 `acceptProjectInvitationHandler` / `acceptProjectInvitations`；新增 `saveInvitationLog` |

## 发布前置清单（严格按序执行）

1. **发布前**：在调度中心停用并删除 `refreshWebhookHandler` 任务。必须先于代码发布完成，否则新版本上线后该任务持续失败告警。
2. **发布代码**。
3. **发布后**：清理 Nacos 配置项 `openlibing.cicd.webhook.refresh-rules`（`WebhookRefreshProperties` 已整体删除，配置项失效）。

能力替代说明：`refreshWebhookHandler` 下线后，系统不再提供批量 webhook 地址刷新/迁移能力，webhook 地址变更需在代码仓侧手工重新配置；如后续确有批量迁移需求，须单独发起需求评审，不在本次范围内重开该 handler。

## 关联 Issue

- openlibing-cicd#332 — https://gitcode.com/openlibing/openlibing-cicd/issues/332

## 关联 PR 与提交

- PR：!632 《fix(security): 收敛 xxl-job 定时任务攻击面，下线 webhook 刷新任务》，分支 `fix/security-vuln-332-xxljob-invite-log`，base `release_20261029_iter2`，状态 merged
- 提交：
  - `6272dd2e8` 收敛 xxl-job 攻击面，下线 webhook 刷新任务
  - `2363b88d2` 修复邀请接受任务的审计日志缺陷
- diff 规模：12 个文件，124 insertions / 2312 deletions
