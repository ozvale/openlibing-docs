# Design: codecheck 安全审计漏洞修复

## 技术方案

### F-001 — Webhook MongoDB NoSQL 注入

#### 方案：白名单 + 类型校验（推荐）

新增 `WebhookInputValidator` 工具类集中管理白名单常量与校验逻辑：

```java
public final class WebhookInputValidator {
    // 允许的集合名（与 CodeCheckCollectionName 一致；白名单最小集）
    private static final Set<String> ALLOWED_TABLES = Set.of(
        "code_check_task", "code_check_task_inc", "user_role_info",
        "menu_info", "role_info", "role_permission", "project_info",
        "repo_info", "repo_branch_info", "task_result_details",
        "task_inc_result_details", "full_shield_detail", "inc_shield_detail"
        // 其它业务实际使用的集合，按需补齐
    );

    // 允许的字段名（按需收紧；F-001 PoC 用的 "username"/"password" 等不在内）
    private static final Set<String> ALLOWED_QUERY_FIELDS = Set.of(
        "uuid", "taskId", "userId", "projectId", "repoId", "status",
        "processing", "isProcessing", "isUsed", "type", "category"
    );

    // NoSQL 操作符前缀
    private static final Pattern MONGO_OPERATOR = Pattern.compile("^\\$");

    public static void validateTableName(String tableName) { ... }
    public static void validateFieldName(String field) { ... }
    public static void validateValue(Object value) { ... }   // 拒绝 Map/List/嵌套对象
}
```

**改造点**：
1. `WebhookController.insertData` / `insertEvent` / `readMongoDB` / `readMongoDBFindOne`：进入 Delegate 前调用 `WebhookInputValidator` 校验。
2. `WebhookDelegateImpl.getCriteria`：除白名单字段名外抛 `IllegalArgumentException`；值为 `Map`/`List`/非 `String/Number/Boolean` 视为非法。
3. `WebhookDelegateImpl.readMongoDB/readMongoDBFindOne`：`tableName` 不在白名单 → 返回 403。
4. `WebhookOperation.queryData` / `insertData`：对 `queryData` / `mongoData` 的 key/value 同样过白名单（这是 `insertData` 端点被利用的辅助 Sink）。

**返回码**：非法输入统一返回 `MultiResponse().code(403).message("Invalid request: ...")`。

#### 兼容性

- 合法调用（白名单集合 + 字符串/数字值）行为不变。
- 跨集合/操作符利用被拦截。

### F-002 — Pipeline 命令注入

#### 方案：ProcessBuilder 列表形式 + Sanitizer

**关键改造**（`PipelineDelegateImpl.preMergeAndFix`）：

```java
private Process preMergeAndFix(PrStartPipelineVo vo, Inspection ins) throws IOException {
    // 1. 解析 + sanitizer
    String targetRepo = CommandArgSanitizer.sanitizeRepoUrl(vo.getRepoUrl());
    String[] source = getRepoBranch(vo.getEvent().getRequestBody());
    String sourceRepo = CommandArgSanitizer.sanitizeRepoUrl(source[0]);
    String sourceBranch = CommandArgSanitizer.sanitizeBranchName(source[1]);
    String targetBranch = CommandArgSanitizer.sanitizeBranchName(source[2]);
    // ... token/email 同原

    // 2. 列表形式（不走 shell）
    List<String> command = Arrays.asList(
        "timeout", "--foreground", "60",
        "/opt/app/openlibing/auto-fix.sh",
        "-a", targetRepo,
        "-b", targetBranch,
        "-c", String.valueOf(vo.getPrId()),
        "-d", targetToken,
        "-e", targetUser.getLogin(),
        "-j", sourceRepo,
        "-k", sourceBranch,
        "-l", sourceToken,
        "-m", sourceUser.getLogin(),
        "-n", sourceUser.getEmail(),
        "-t", lintRunnerChecks
    );
    ProcessBuilder processBuilder = new ProcessBuilder(command);
    processBuilder.redirectErrorStream(true);
    return processBuilder.start();
}
```

**新增 `CommandArgSanitizer`**：

```java
public final class CommandArgSanitizer {
    private static final Pattern REPO_URL = Pattern.compile("^https?://[a-zA-Z0-9._/-]+\\.git$");
    private static final Pattern BRANCH_NAME = Pattern.compile("^[a-zA-Z0-9._/-]+$");

    public static String sanitizeRepoUrl(String url) {
        if (url == null || !REPO_URL.matcher(url).matches()) {
            throw new IllegalArgumentException("Invalid repo URL");
        }
        return url;
    }

    public static String sanitizeBranchName(String branch) {
        if (branch == null || !BRANCH_NAME.matcher(branch).matches()) {
            throw new IllegalArgumentException("Invalid branch name");
        }
        return branch;
    }
}
```

**调用方**：`preCommitCheck` 已经把异常 catch 住并打 ERROR 日志，所以 sanitizer 失败会安全地走错误分支而不会让 500 漏到调用方。

**PrStartPipelineVo.repoUrl 校验**：在 Controller 层调 `preCommitCheck` 前也做一次轻量校验（避免无效请求占用线程）。

### F-003 — XxlJob 参数校验

**改造点**：

1. `lintRunnerChecksHandler`：
   ```java
   private static final Pattern LINT_CHECK_PATTERN = Pattern.compile("^[a-zA-Z0-9_\\-, ]*$");
   @XxlJob("lintRunnerChecksHandler")
   public void lintRunnerChecksHandler() {
       String jobParam = Strings.nullToEmpty(XxlJobContext.getXxlJobContext().getJobParam());
       if (!LINT_CHECK_PATTERN.matcher(jobParam).matches()) {
           logger.error("Invalid lintRunnerChecks, ignored: {}", jobParam);
           return;  // 静默拒绝，保持旧值
       }
       String oldChecks = PipelineDelegateImpl.getLintRunnerChecks();
       if (!jobParam.equals(oldChecks)) {
           PipelineDelegateImpl.setLintRunnerChecks(jobParam);
           logger.info("Lint runner newChecks changed: {} -> {}", oldChecks, jobParam);
       }
   }
   ```

2. `getTaskTimeout` 边界：
   ```java
   int fullTaskTimeout = Math.max(1, Math.min(params.getInteger("fullTaskTimeout", 20), 1440));
   int incTaskTimeout = Math.max(1, Math.min(params.getInteger("incTaskTimeout", 5), 1440));
   ```

3. `getCheckTaskIncEntityList` / `getDailyCheckTasks`：保留 `try/catch` 行为，但补一次**显式** `null` 检查（如果 `getProcessingTasks` 接收 null）。

### F-004 — InternalController 微服务间鉴权

#### 方案：Header-based Token Filter（最小化改动）

**新增 `InternalSecurityFilter`**：

```java
@Component
@Order(Ordered.HIGHEST_PRECEDENCE)
public class InternalSecurityFilter extends OncePerRequestFilter {

    private static final String INTERNAL_TOKEN_HEADER = "X-Internal-Token";
    private static final AntPathMatcher PATH_MATCHER = new AntPathMatcher();

    @Value("${internal.service.token:}")
    private String expectedToken;

    @Override
    protected void doFilterInternal(HttpServletRequest req, HttpServletResponse res, FilterChain chain)
            throws ServletException, IOException {
        String uri = req.getRequestURI();
        if (uri != null && uri.startsWith("/internal/")) {
            // 配置未设置 → 拒绝（fail-closed）
            if (StringUtils.isBlank(expectedToken)) {
                writeUnauthorized(res, "internal service token not configured");
                return;
            }
            String provided = req.getHeader(INTERNAL_TOKEN_HEADER);
            if (!constantTimeEquals(expectedToken, provided)) {
                writeUnauthorized(res, "invalid internal token");
                return;
            }
        }
        chain.doFilter(req, res);
    }

    private boolean constantTimeEquals(String a, String b) {
        if (a == null || b == null) return false;
        return MessageDigest.isEqual(a.getBytes(StandardCharsets.UTF_8), b.getBytes(StandardCharsets.UTF_8));
    }

    private void writeUnauthorized(HttpServletResponse res, String message) throws IOException {
        res.setStatus(HttpServletResponse.SC_UNAUTHORIZED);
        res.setContentType("application/json");
        res.getWriter().write("{\"code\":401,\"message\":\"" + message + "\"}");
    }
}
```

**配置**（`application.yml` / `application-prod.yml`）：

```yaml
internal:
  service:
    token: ${INTERNAL_SERVICE_TOKEN:}  # 从环境变量注入
```

**`fail-closed` 策略**：未配置 `internal.service.token` → 全部 `/internal/**` 拒绝（避免遗漏配置导致对外开放）。

**常时比较**：`MessageDigest.isEqual` 避免时序攻击。

**安全**：
- 不在错误响应中泄露预期 token 长度/内容。
- 不记录预期 token。
- 仅对 `/internal/**` 路径生效（其它路径不受影响）。

## 关键决策

| 决策 | 选择 | 理由 |
|------|------|------|
| F-001 防护策略 | 白名单 + 类型校验 | 最小化改动，对调用方透明；MongoDB 操作符无法用 Map 传递 |
| F-002 防护策略 | ProcessBuilder 列表形式 + sanitizer | 完全避免 shell 解析；sanitizer 防止非法 URL/分支名进入 |
| F-003 防护策略 | 静默拒绝 + 保留旧值 | 不影响正在运行的 pre-commit 流程；可观测性靠 ERROR 日志 |
| F-004 鉴权方式 | Header-based Token Filter | 最小化改动；不引入 Spring Security 依赖；与现有代码风格一致 |
| F-004 失败策略 | fail-closed | 避免配置缺失导致对外开放 |
| 集合白名单范围 | 12 个核心集合 | 覆盖现有 webhoook 调用场景；后续新增集合需显式加白名单 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| F-001 白名单遗漏导致合法调用被拒 | 集合名常量与 `CodeCheckCollectionName` 对齐；如发生回归可通过错误码定位 |
| F-002 sanitizer 误杀合法 URL | 正则允许 `https?://` + 路径字符 + `.git`；不限制端口以外的合法字符 |
| F-003 lint runner checks 中含特殊字符 | 校验正则已允许 `[a-zA-Z0-9_\\-, ]`，覆盖原用法；如需中文/特殊字符可后续扩展 |
| F-004 配置 token 泄露 | 从环境变量 `INTERNAL_SERVICE_TOKEN` 注入；不写入代码；可定期轮换 |
| F-004 调用方未带 token 导致集成失败 | 同步通知调用方（openlibing-coderepo 等）补充 Header；回归测试覆盖 |

## 跨仓影响

| 仓 | 集成点 | 风险 |
|----|--------|------|
| openlibing-coderepo | 调用 `/internal/rule-set/recompute-used` | 调用方需带 `X-Internal-Token` Header；需配套部署协调 |
| openlibing-cicd | 调用 `/internal/pre-commit` | 同上 |
| openlibing-framework | 调用 `/internal/repo/getRepoAccessToken` | 同上 |

**协调方式**：在 PR 描述中明确列出调用方仓与所需 Header 变更；建议在 Phase 4 PR 创建时同步在 `#openlibing-dev` 通知。

## 文件清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `WebhookController.java` | 修改 | Controller 层白名单校验 |
| `WebhookDelegateImpl.java` | 修改 | `getCriteria` 字段名白名单 |
| `WebhookOperation.java` | 修改 | `queryData` / `insertData` 字段白名单 |
| `InternalController.java` | 修改 | 入口轻量校验（防御性） |
| `PipelineDelegateImpl.java` | 修改 | ProcessBuilder 列表形式 + sanitizer 调用 |
| `XxlJobHandler.java` | 修改 | lintRunnerChecks 校验 + timeout 边界 |
| `common/security/WebhookInputValidator.java` | 新增 | F-001 白名单集中管理 |
| `common/security/CommandArgSanitizer.java` | 新增 | F-002 sanitizer |
| `common/security/InternalSecurityFilter.java` | 新增 | F-004 鉴权 Filter |
| `application.yml` | 修改 | 新增 `internal.service.token` 配置项 |
| `WebhookDelegateImplTest.java` | 修改 | 新增非法输入 → 拒绝用例 |
| `PipelineDelegateImplTest.java` | 修改 | 新增非法 repoUrl → 拒绝用例 |
| `XxlJobHandlerTest.java` | 修改 | 新增非法 lintRunnerChecks → 拒绝用例 |
| `InternalSecurityFilterTest.java` | 新增 | F-004 鉴权用例 |
| `WebhookInputValidatorTest.java` | 新增 | F-001 白名单覆盖 |
