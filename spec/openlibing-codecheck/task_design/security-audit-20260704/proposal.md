# Proposal: codecheck 安全审计漏洞修复（F-001~F-003，F-004 透档）

## 需求背景

`deep-audit-report.md`（2026-07-04）对 `openlibing-codecheck` 进行了注入类（D1）+ 命令执行类（D4）漏洞深度审计，定位到 4 个待修复漏洞：

| 编号 | 漏洞 | 严重度 | 文件 |
|------|------|--------|------|
| F-001 | Webhook MongoDB NoSQL 注入（CWE-943） | **Critical** | `WebhookController.java`, `WebhookDelegateImpl.java`, `WebhookOperation.java` |
| F-002 | Pipeline 预提交命令注入（CWE-78） | **Critical** | `InternalController.java`, `PipelineDelegateImpl.java` |
| F-003 | XxlJob 任务参数无类型校验（CWE-20） | **High** | `XxlJobHandler.java` |
| F-004 | InternalController 微服务间接口无鉴权 | **High** | `InternalController.java` |

### 核心风险

- **F-001**：4 个 `/ci-portal/webhook/codecheck/v1/...` 端点接受任意 JSON 字符串直接作为 MongoDB 查询条件，攻击者可绕过认证、跨集合窃取数据、注入 `$ne`/`$regex`/`$where` 等 MongoDB 操作符。
- **F-002**：`/internal/pre-commit` 接收 `requestBody`（含 `git_http_url`、`source_branch`、`target_branch`），通过 `String.format` 拼接到 `bash -c` 命令，攻击者控制输入即可在宿主机执行任意命令（CVSS 9.9）。
- **F-003**：`lintRunnerChecksHandler` 接收 xxl-job `jobParam` 后**未做校验**即写入静态变量，被 F-002 的命令构造链路直接使用，构成 F-002 的"第二利用路径"。
- **F-004**：`/internal/**` 三个端点（`getRepoAccessToken`、`pre-commit`、`recompute-used`）当前无任何鉴权机制，依赖部署层网络隔离；缺乏纵深防御。

## 功能描述

### 做什么

1. **F-001 修复**：在 `WebhookController` 4 个端点（`insertData` / `insertEvent` / `readMongoDB` / `readMongoDBFindOne`）以及 `WebhookDelegateImpl.getCriteria` / `WebhookOperation.queryData` 增加 **MongoDB 集合名白名单 + 字段名白名单 + 值类型校验**；禁止 NoSQL 操作符（`$ne`/`$regex`/`$gt` 等）。
2. **F-002 修复**：
   - 将 `PipelineDelegateImpl.preMergeAndFix` 中 `ProcessBuilder("bash", "-c", cmd)` 改造为**列表形式**（不经过 shell 解析）。
   - 新增 `sanitizeRepoUrl` / `sanitizeBranchName` 严格校验 `repoUrl`、`source_branch`、`target_branch` 格式（白名单正则）。
3. **F-003 修复**：在 `XxlJobHandler.lintRunnerChecksHandler` 增加 `^[a-zA-Z0-9_\\-, ]*$` 校验；其他 `jobParam` 解析（`syncIncCheckTasksHandler` / `syncDailyCheckTasksHandler` / `rollbackTimeoutTasks`）也补强类型与边界校验。
4. ~~**F-004 修复**：新增 `InternalSecurityFilter`（基于 `OncePerRequestFilter`），对 `/internal/**` 路径校验 `X-Internal-Token` Header（值来自配置 `internal.service.token`），缺失/错误则 401 拒绝。~~  **本次 PR 透档为遗留项**。原因：F-004 当前推荐方案（`X-Internal-Token` + `INTERNAL_SERVICE_TOKEN`）需要 openlibing-coderepo / openlibing-cicd / openlibing-framework 三个上游服务同步改造 + 部署侧协调，协调成本较高。F-004 将由独立工单跟进，可选方案见设计文档 `design.md` 的"后续方案候选"小节。

### 不做什么

- **不**修改 `auto-fix.sh`（脚本层加固由运维/部署侧处理，超出本次仓内范围）。
- **不**启用 Spring Security 全栈方案（最小化改动，避免引入新依赖与全局 Filter 顺序问题；Header 校验 Filter 即可满足 F-004 修复要求）。
- **不**改 `MongoDB 服务端配置`（mongod.conf 加固属于部署侧）。
- **不**触碰 webhook 之外的其它公开 Controller 鉴权（不在审计范围内）。

## 验收标准

- [ ] F-001：调用 `readMongoDB?str={"tableName":"forbidden_collection","x":1}` 返回 403，拒绝跨集合访问
- [ ] F-001：调用 `readMongoDB?str={"tableName":"user_role_info","username":{"$ne":""}}` 返回 403，拒绝 MongoDB 操作符
- [ ] F-001：合法调用（白名单集合 + 合法字段 + 字符串值）行为不变
- [ ] F-002：`preCommitCheck` 调用时不再走 `bash -c`，命令通过列表形式传给 `ProcessBuilder`
- [ ] F-002：`preCommitCheck` 收到 `repoUrl="https://x.com/y.git; touch /tmp/pwned; #"` 时直接抛 IllegalArgumentException
- [ ] F-002：合法仓库 URL 与分支名继续正常工作
- [ ] F-003：xxl-job `lintRunnerChecksHandler` 收到 `"foo; rm -rf /"` 时拒绝更新并打 ERROR 日志
- [ ] F-003：`fullTaskTimeout` / `incTaskTimeout` 接收非整数或负数时使用默认值
- [ ] **F-004 透档为遗留项**：本次 PR 不实现鉴权，audit report 仍标记为"未修复 / 已知风险"，由独立工单跟进
- [ ] 现有单元测试（`WebhookControllerTest` / `WebhookDelegateImplTest` / `WebhookOperationTest` / `InternalControllerTest` / `PipelineDelegateImplTest` / `XxlJobHandlerTest`）全部通过
- [ ] 编译 `mvn -DskipTests clean compile` 通过

## 影响范围

- **修改文件**（预估 5 个）：
  - `WebhookController.java`
  - `WebhookDelegateImpl.java`
  - `WebhookOperation.java`
  - `InternalController.java`
  - `PipelineDelegateImpl.java`
  - `XxlJobHandler.java`
  - （`application.yml` / `application-*.yml` **不**再修改 — F-004 配置已透档）
- **新增文件**（预估 2 个）：
  - `common/security/WebhookInputValidator.java`（白名单常量集中管理）
  - `common/security/CommandArgSanitizer.java`（仓库 URL/分支名 sanitizer）
  - ~~`common/security/InternalSecurityFilter.java`~~（F-004 已透档，不新增）
- **接口/契约变化**：无（仅收紧输入校验，行为对外不变）
- **数据库/Schema**：无
- **依赖**：无新增
- **测试**：补充针对白名单/校验/鉴权的单元测试

## 关联

- 业务 Issue: openlibing/openlibing-codecheck#131
- 业务 PR: <待创建>
- 审计报告: `d:\code\openlibing\deep-audit-report.md`
