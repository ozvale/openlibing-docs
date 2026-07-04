# Tasks: codecheck 安全审计漏洞修复

## 进度: 0/14 complete

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

### F-004 InternalController 鉴权

- [ ] 10. 新增 `common/security/InternalSecurityFilter.java`
  - 拦截 `/internal/**`
  - 校验 `X-Internal-Token` Header（`@Value("${internal.service.token:}")`）
  - `MessageDigest.isEqual` 常时比较
  - `fail-closed`（未配置 token → 全部 401）

- [ ] 11. 修改 `application.yml`（或 `application-*.yml`）
  - 新增 `internal.service.token: ${INTERNAL_SERVICE_TOKEN:}` 配置

- [ ] 12. 新增 `InternalSecurityFilterTest.java` — 鉴权场景测试
  - 无 Header → 401
  - 错误 Header → 401
  - 正确 Header → 200
  - 未配置 token → 全部 401
  - 路径不在 `/internal/**` → 不影响

### 验证

- [ ] 13. 编译验证
  - `mvn -DskipTests clean compile` 通过
  - 修改文件的现有单测全部通过：
    - `WebhookControllerTest` / `WebhookDelegateImplTest` / `WebhookOperationTest`
    - `InternalControllerTest` / `PipelineDelegateImplTest`
    - `XxlJobHandlerTest`

- [ ] 14. 提交
  - 一轮 AI 编码交付 = 一次 commit
  - 格式遵循 `gitcode-dev-workflow` skill 中的 Commit 规范
  - commit message 包含 `Refs #<issue>` 关联业务 Issue
