# Tasks: codecheck 安全审计漏洞修复

## 进度: 9/12 complete（11/14 调整为 9/12：F-004 透档）

### F-001 Webhook MongoDB NoSQL 注入

- [ ] 1. 新增 `common/security/WebhookInputValidator.java`
  - 集合名白名单（与 `CodeCheckCollectionName` 对齐的最小集）
  - 字段名白名单（按需收紧）
  - `validateTableName(String)` / `validateFieldName(String)` / `validateValue(Object)` 静态方法
  - 拒绝以 `$` 开头的字段名（NoSQL 操作符）
  - 拒绝 `Map` / `List` / 嵌套对象类型的 value

- [ ] 2. 修改 `WebhookController.java`
  - `insertData` / `insertEvent` / `readMongoDB` / `readMongoDBFindOne` 4 个端点统一调用 `WebhookInputValidator` 校验
  - 非法输入返回 `MultiResponse().code(403).message("Invalid request")`

- [ ] 3. 修改 `WebhookDelegateImpl.java`
  - `getCriteria` 字段名校验（白名单）
  - 移除 `getCriteria` 中 `sort` / `orderBy` 接受任意字符串的逻辑（改为白名单字段）

- [ ] 4. 修改 `WebhookOperation.java`
  - `queryData` / `insertData` 对 `queryData` / `mongoData` 的 key/value 同样过白名单

- [ ] 5. 新增 `WebhookInputValidatorTest.java` — 白名单覆盖测试

### F-002 Pipeline 命令注入

- [ ] 6. 新增 `common/security/CommandArgSanitizer.java`
  - `sanitizeRepoUrl(String)` — 正则 `^https?://[a-zA-Z0-9._/-]+\\.git$`
  - `sanitizeBranchName(String)` — 正则 `^[a-zA-Z0-9._/-]+$`
  - 不通过抛 `IllegalArgumentException`

- [ ] 7. 修改 `PipelineDelegateImpl.java`
  - `preMergeAndFix` 将 `String.format` + `ProcessBuilder("bash", "-c", cmd)` 改为 `ProcessBuilder(commandList)`
  - 注入 `targetRepo` / `sourceRepo` / `sourceBranch` / `targetBranch` 经过 `CommandArgSanitizer`
  - 工作目录限制（如适用）

- [ ] 8. 修改 `InternalController.java`
  - `preCommitCheck` 入口轻量校验 `repoUrl` 格式，避免无效请求占用线程

### F-003 XxlJob 参数校验

- [ ] 9. 修改 `XxlJobHandler.java`
  - `lintRunnerChecksHandler` 校验 `^[a-zA-Z0-9_\\-, ]*$`，不通过拒绝并打 ERROR 日志
  - `getTaskTimeout` 增加 `Math.max(1, Math.min(..., 1440))` 边界
  - 显式 `null` 兜底

### F-004 InternalController 鉴权 — **透档**

- [x] **10. F-004 透档为遗留项**
  - 不在本次 PR 修复 F-004（`/internal/**` 鉴权）
  - 相关代码（`InternalSecurityFilter.java` / `InternalSecurityFilterTest.java` / `application.yaml` 中 `internal.service.token` 配置）已从 commit 中移除
  - 后续方案候选（待 F-004 独立工单评估）：
    - K8s NetworkPolicy / Service Mesh AuthorizationPolicy
    - 源 IP / CIDR 白名单
    - Feign `RequestInterceptor` 自动注入 Token
    - 维持现状（接受风险）
  - **验收**：审计报告 F-004 保持"未修复 / 已知风险"状态，由独立工单跟进

### 验证

- [x] 11. 编译验证
  - `mvn -DskipTests clean compile` 通过
  - 修改文件的现有单测全部通过：
    - `WebhookDelegateImplTest` / `WebhookOperationTest` / `InternalControllerTest`
    - `CommandArgSanitizerTest`
  - 41 cases 全部通过

- [x] 12. 提交
  - 一轮 AI 编码交付 = 一次 commit（`bd2dcf53`）
  - 格式遵循 `gitcode-dev-workflow` skill 中的 Commit 规范
  - commit message 包含 `Refs #131` 关联业务 Issue
  - 业务 PR：openlibing/openlibing-codecheck#234
  - Spec PR：openlibing/openlibing-docs#518
