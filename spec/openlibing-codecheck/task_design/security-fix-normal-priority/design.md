# Design: codecheck 一般优先级安全问题批次修复

## 1. 方案设计

### 1.1 总体策略

按“先低风险单点、再输入校验、再配置化、再审计日志、最后资源上限”的顺序分 5 批实施。每批独立分支、独立 PR、独立验证，避免一次性大改导致回归定位困难。

| 批次 | 主题       | 核心技术手段                             |
| ---- | ---------- | ---------------------------------------- |
| 1    | 日志与常量 | 输出层转义 + 敏感日志收敛 + 角色常量集中 |
| 2    | 输入校验   | Bean Validation + 分页一致性校验         |
| 3    | 配置化     | `@ConfigurationProperties` + 白名单查表  |
| 4    | 审计日志   | 操作日志 Handler 补齐 + 网关菜单配置     |
| 5    | 资源上限   | 统一分页工具 + 可配置上限                |

### 1.2 各 Issue 方案

#### #386 日志注入

- `log4j2-spring.xml` 的 `MANAGE_LOG_FILE` 输出层由 `%msg%n` 改为 `%enc{%msg}{CRLF}%n`，与普通文件日志一致。
- `ManageLogHelper.writeLog` 对 `operatorIp`、`objectType`、`operationType` 等字符串字段调用 `LogSanitizer.sanitize` 后再写入。
- 选择输出层修复而非逐调用点修复，原因是审计日志可能由 common 的操作日志框架写入，输出层可覆盖全部写入方。

#### #400 调试信息不明确导致敏感信息泄露

- `SuppressionScanServiceImpl.parsePrFilesResponse`：
  - `LOGGER.error("API response code is not 0: {}", responseBody)` 改为只记录状态码与响应体长度，不打印完整响应体；
  - IO/JSON 异常日志**保留异常类型与堆栈**：记录 `e.getClass().getName()` 与前 10 帧 `StackTraceElement` 摘要；**省略异常 message**（可能包含响应体/URL 原文），不再把异常对象直接作为 throwable 传入；
  - `platform` 等上下文参数统一 `LogSanitizer.sanitize`。
- `LogSanitizer` 为既有类（`common/util/LogSanitizer.java`），本次复用；保持既有 `null -> null` 语义不变，新增带最大长度的 `sanitize(String, int)` 重载供可控文本截断使用。
- 不改变解析逻辑与返回值，仅收敛日志内容。

#### #399 带 admin 操作的控制语句

- 与 #215 共用角色常量：`ProjectConstant.Role.ADMIN` / `PLATFORM_OPERATOR` / `COMMUNITY_MANAGER`。
- 在 `AuthUtils` 增加集中判断方法，例如：
  ```java
  public static boolean isSystemAdmin(String role) {
    return ProjectConstant.Role.ADMIN.equals(role)
        || ProjectConstant.Role.PLATFORM_OPERATOR.equals(role);
  }
  ```
- 替换 **5 组位置、共 9 处**角色字面量：
  - `AuthUtils:206`、`AuthUtils:212`、`AuthUtils:374`、`AuthUtils:375`（4 处）
  - `SensitiveDelegateImpl:746`（1 处）
  - `CheckPermissionOperation:40/46`（2 处）
  - `CommonOperation:298/312`（2 处）
- `SensitiveDelegateImpl.checkPermission` 目标形态（保留 null 防御，仅去掉空集合短路，不改变空列表与 platform_operator 结果）：
  ```java
  public boolean checkPermission(String userId) {
    List<UserRoleInfoEntity> roles = userRoleMapper.queryByUserId(userId);
    if (roles == null) {
      return false; // null 安全；空列表走循环自然返回 false
    }
    for (UserRoleInfoEntity role : roles) {
      if (role != null && ProjectConstant.Role.ADMIN.equals(role.getRole())) {
        return true;
      }
    }
    return false;
  }
  ```
  语义边界：`roles == null` 返回 `false`；空列表返回 `false`；含 admin 返回 `true`；platform_operator / 普通角色返回 `false`（与修改前一致）。同时去掉循环内重复调用 `queryByUserId` 的写法。

#### #385 接口参数未校验

- Controller 的 `@RequestBody` 增加 `@Valid`，激活模型上已有的 Jakarta Validation 注解。
- `UpdateRuleModel` 增加：
  - `@NotBlank(message = "taskId不能为空")`
  - `@Min(value = 1, message = "projectId必须大于0")`
  - `@NotBlank(message = "repoName不能为空")`
  - `@NotEmpty(message = "ruleSets不能为空")`
- `ShieldModel` 的 `shieldType`、`reason` 文档未标必填，仅增加 `@Size(max = 512)`，避免行为突变；`IdArray` 无这两个字段，不新增约束。
- delegate 层保留现有 reviewer、occupied、ownership 校验，不重复实现参数非空校验。
- 非法入参由 `GlobalExceptionHandler` 统一返回 `DataResult.code=4010103`（方法参数不合法），不进入 delegate。

#### #373 机机接口分页参数未校验

- `QueryTaskSummaryMachineApiModel`：
  - `@Min(1)` pageNum
  - `@Min(1) @Max(100)` pageSize
  - `@AssertTrue` 校验 pageNum/pageSize 同时为 null 或同时非 null
- 两个入口 Controller 增加 `@Valid`。
- `FullSummaryOperation`：
  - skip 使用 `long` 计算，避免整型溢出；
  - 分页参数非法、`skip < 0` 或 `skip > Integer.MAX_VALUE` 抛 `PageSkipException`；
  - 分页参数缺失时不再进入全量查询，先限制最多返回 1000 条（批次 5 统一收敛到 `PageParams.MAX_UNPAGED_SIZE`）。
- `StaticAlarmServiceImpl.searchRepos`：当前代码已将 `limit` 裁剪到 `[1, 50]`（`Math.max(1, Math.min(limit, 50))`），本次不重复改造，仅补回归测试；当前 Controller 未暴露 `limit` 入参，若后续暴露需同步加 `@Min(1) @Max(50)`。

#### #365 pageSize 无上限

新增 `PageParams` 统一工具：

```java
public final class PageParams {
  public static final int DEFAULT_PAGE_SIZE = 20;
  public static final int MAX_PAGE_SIZE = 100;
  public static final int MAX_UNPAGED_SIZE = 1000;

  public static long resolveSkip(Integer pageNum, Integer pageSize);
  public static int resolveLimit(Integer pageSize);
  public static int resolveUnpagedLimit(Integer requested);
}
```

各链路统一接入（共 **10 个端点**，对应原 Issue 11 条链路中剔除已下线 Webhook 接口后的 10 条）：

| #   | 链路                                                                   | 处理                                                                                                         |
| --- | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 1   | `/machine-api/v1/codecheck/full/task/result/summary`                   | 缺失分页时 `limit(MAX_UNPAGED_SIZE)`，并记录 warn                                                            |
| 2   | `/apig/v1/machine-api/v1/codecheck/full/task/result/summary`           | 同上                                                                                                         |
| 3   | `/machine-api/v1/full-codecheck-record/list`（`queryFullSummaryList`） | 补分页上限；缺失分页时 `limit(MAX_UNPAGED_SIZE)`，并记录 warn                                                |
| 4   | 静态告警汇总                                                           | 缺失分页时同上                                                                                               |
| 5   | FOSS 查询/导出                                                         | `QueryFossScanModel` 加范围约束，skip 用 long；查询缺失分页按上限截断，导出按导出行数上限                    |
| 6   | 敏感词规则                                                             | `QuerySensitiveRuleModel` 加范围约束，Controller 加 `@Valid`；缺失分页按上限截断                             |
| 7   | 规则查询                                                               | `RuleModel` 加范围约束，Controller 加 `@Valid`；缺失分页按上限截断，`getAllRulesBySet` 总数/启用数改用 count |
| 8   | 自定义屏蔽                                                             | `SelfShieldModel` 加范围约束，`getSelfShieldData` 加 `@Valid`                                                |
| 9   | 工作台                                                                 | 缺失分页时使用默认上限                                                                                       |
| 10  | metrics                                                                | total 使用 `mongoTemplate.count`，缺失分页按上限截断，不再置空分页全量加载                                   |

- 分页上限支持配置覆盖：`codecheck.pagination.max-page-size`（默认 100）、`codecheck.pagination.max-unpaged-size`（默认 1000），由 `PaginationProperties` 在启动/刷新时写入 `PageParams`；0 或负数启动校验失败。
- `SensitiveDelegateImpl.querySensitiveRuleSetSettingsById` 不再 `queryRules(criteria, null, null)` 全量加载，启用数改用 `getRuleCount`，`typeCount` 改用按 `type` 聚合计数。
- `CheckboardDelegateImpl.getFullMetrics` / `getIncMetrics` 不再置空分页后全量重查，`total` 改由 `countFullMetricsDetail` / `getIncMetricsCount` 的 `mongoTemplate.count` 提供。
- 自定义屏蔽（`fullShieldDetail` / `incShieldDetail`）未传分页时按 `max-unpaged-size` 截断。

> FOSS 链路的第二个子问题（用户参数拼接正则）当前代码已具备防护：`FossScanOperation` 对 `filePath` / `componentName` 使用 `Pattern.quote(...)` 包裹，并通过 `MAX_REGEX_PARAM_LENGTH` 跳过超长参数。本次不重复改造，只补回归验证（正则元字符按字面量匹配、超长参数跳过过滤）。

> 原 #365 清单中的 `/ci-portal/webhook/codecheck/v1/find/by/mongoDB` 已随废弃接口下线（`bdc9636b` 删除 `WebhookController`），剩余 `WebhookDelegateImpl` / `WebhookOperation` 无调用方，不纳入本次改造。

#### #364 导出/本地文件无大小限制

- 新增配置（已确认）：
  - `codecheck.export.max-rows=200000`
  - `codecheck.export.max-file-bytes=104857600`
  - `codecheck.export.max-merge-parts=50`
- `StaticAlarmServiceImpl.writeExcelInBatches`：累计行数超过 `max-rows` 抛 `IllegalStateException`，由现有异常处理标记导出失败。
- `FileDownloadDelegateImpl.exportDetailToFile`：合并前校验分片数与累计字节数。
- `FileDownloadDelegateImpl.exportFossScanDetail`：查询前设置行数上限，超限拒绝。
- `ExcelReportImpl`：单任务处理前用 count 判断，超限直接失败，不进入全量循环。

#### #215 角色字符串硬编码

- `ProjectConstant.Role` 增加：
  - `PLATFORM_OPERATOR = "platform_operator"`
  - `COMMUNITY_MANAGER = "community_manager"`
- 替换 `AuthUtils` 中 4 处字面量，并同步替换 `SensitiveDelegateImpl`、`CommonOperation`、`CheckPermissionOperation` 中同语义字面量，避免同类告警重复出现。

#### #202 硬编码公网地址/邮箱

新增 `CodePlatformProperties`：

| 配置项                                     | 默认值                      |
| ------------------------------------------ | --------------------------- |
| `codecheck.platform.gitcode-web-base-url`  | `https://gitcode.com/`      |
| `codecheck.platform.gitee-web-base-url`    | `https://gitee.com/`        |
| `codecheck.platform.gitcode-api-base-url`  | `https://api.gitcode.com/`  |
| `codecheck.platform.gitee-api-base-url`    | `https://api.gitee.com/`    |
| `codecheck.platform.github-api-base-url`   | `https://api.github.com/`   |
| `codecheck.notification.mail-from-name`    | `openLiBingCI`              |
| `codecheck.notification.mail-from-address` | `pre-commit@openlibing.com` |

- 替换 `CheckboardDelegateImpl.buildUserUrl`、`ProblemshieldDelegateImpl` 同类方法、`PipelineDelegateImpl` API 地址与默认发件账号。
- `"https://api." + repoType + ".com"` 改为 `Map<String, String>` 白名单查表（gitee/gitcode/github），三个平台 API 地址均来自配置项，不再在 Delegate 内保留字面量。
- **`.mvn/settings.xml` 不修改。**

#### #247 SARIF 解析无界

新增配置（已确认）：

| 配置项                                 | 确认值           |
| -------------------------------------- | ---------------- |
| `codecheck.alarm.sarif.max-urls`       | 50               |
| `codecheck.alarm.sarif.max-file-bytes` | 52428800（50MB） |
| `codecheck.alarm.sarif.max-runs`       | 20               |
| `codecheck.alarm.sarif.max-results`    | 100000           |

- `parseAllUrls` 进入下载前先校验 `obsUrls` 数量：超过 `max-urls` **整批拒绝**，不下载解析任何 URL，并记录错误（携带实际数量与阈值），避免“截断后静默丢 URL”。
- `downloadAndParse` 使用 `LimitedInputStream`（本次新增类），读取超过 `max-file-bytes` 抛 `IOException`，该 URL 独立失败。
- Jackson 3 的解析异常为非受检 `RuntimeException`，`downloadAndParse` 统一转换为 `IOException` 抛出，确保超限/格式异常都按 URL 隔离，不中断整批解析。
- 解析后校验 runs 数量；issue 总数超过 `max-results` 时停止该 URL 并记录错误。
- 单 URL 的 `max-file-bytes` / `max-runs` / `max-results` 超限相互隔离，不影响同批其余 URL 入库。
- 保留 `fileSize` / `bytesRead` 日志，超限时打印阈值。
- 配置校验：`max-urls` / `max-file-bytes` / `max-runs` / `max-results` 均要求 `>= 1`；启动时对 `0` 或负数做配置校验并失败退出，同时打印告警，**不支持 `0 = 不限制`**，防止误配置整体关闭 DoS 防护。

> #249（RabbitMQ 消息无签名）经确认暂不修复，不在本批次实现签名与验签，保留 Issue 打开后续单独评估。

### 1.3 批次 5 已确认参数

| Issue | 确认项                            | 确认值                             |
| ----- | --------------------------------- | ---------------------------------- |
| #365  | 机机接口“不传分页”时的返回上限    | 1000 条                            |
| #365  | 通用 `pageSize` 上限              | 100                                |
| #365  | 是否允许配置覆盖上限              | 允许                               |
| #364  | 单次导出总行数上限                | 200,000 行                         |
| #364  | 单次导出文件大小上限              | 100MB                              |
| #364  | 合并导出分片数上限                | 50 片                              |
| #364  | 超限行为                          | 拒绝导出并标记失败，不截断         |
| #364  | 每 Sheet 50,000 行是否保持        | 保持                               |
| #247  | `obsUrls` 数量上限                | 50 个                              |
| #247  | 单 SARIF 文件大小上限             | 50MB                               |
| #247  | 单文件 runs 数量上限              | 20                                 |
| #247  | 单次解析 results/issue 总数上限   | 100,000                            |
| #247  | `obsUrls` 数量超限行为            | 整批拒绝，不下载解析任何 URL       |
| #247  | 单 URL 文件/runs/results 超限行为 | 该 URL 独立失败，其余 URL 正常入库 |
| #247  | 是否支持 `0 = 不限制` 回退        | 不支持；0/负数启动校验失败并告警   |

#### #363 非查询接口无审计日志

- 现有能力：common 的 `OperationLogAspect` + `RuleSetLogHandler` / `SensitiveLogHandler` / `TestingCenterLogHandler`，由网关 `X-Operation-Log` 头触发；无 Handler 命中时仍写入通用审计记录，仅缺少业务字段补数。
- 覆盖核对（以当前代码为准）：
  - `/attributes/ruleSet/config`：入参 `CreateRuleSetModel`，已由 `RuleSetLogHandler` 覆盖；
  - `/operate/project/ruleSetList`：入参 `RuleSetListParamModel`，`RuleSetLogHandler` 需扩展；
  - `/sensitive/config/ruleSet`：入参 `SensitiveRuleSet`，`SensitiveLogHandler` 需扩展；
  - shield 接口：当前在线 5 个（submit / audit / auditRevoke / referral / revoke），需新增 `ShieldLogHandler`；#363 清单中的 `shield-all-result` 已由 `bdc9636b` 下线，不纳入；
  - `assign-owner`：需新增 `StaticAlarmAssignLogHandler`；
  - `default/template`、`modify/createUser`：散参，需扩展 `RuleSetLogHandler`。
- 新增 `ShieldLogHandler`：
  - `matches`：命中 `ShieldModel` / `IdArray` / `AuditModel`；
  - `before`：按 `detailsId` 回查问题状态分布（数量 + 状态计数）；
  - `after`：填 projectId、resourceId、newData（操作类型、shieldType、auditResult、数量摘要），不记录屏蔽原因与审核意见全文。
- 新增 `StaticAlarmAssignLogHandler`：
  - `matches`：命中 assign-owner 入参 `StaticAlarmAssignOwnerDTO`；
  - `before/after`：按问题 ID 回查旧责任人（最多记录 100 条），记录问题数与责任人变化。
- `RuleSetLogHandler` 扩展：
  - 支持 `ruleSetList` 的 `RuleSetListParamModel`（更新场景按 ruleSetListId 回查旧集合）；
  - 支持 `default/template` 的散参（projectId/templateId/language/userId）；
  - 支持 `modify/createUser` 的散参（projectId/templateId/userId）。
- `SensitiveLogHandler` 扩展：
  - 支持 `sensitive/config/ruleSet` 的 `SensitiveRuleSet`（按 templateId 回查旧规则集）。
- 代码仓不修改网关菜单表；需部署侧在菜单上配置 `write_log=1` 并绑定对应 URL，否则切面不会触发。

**网关菜单 `write_log` 配置清单（部署侧执行）**

| #   | 菜单绑定 URL（含应用前缀）                                                | 方法 | 说明                     |
| --- | ------------------------------------------------------------------------- | ---- | ------------------------ |
| 1   | `/openlibing-codecheck/ci-portal/shield/submit`                           | POST | 提交屏蔽申请             |
| 2   | `/openlibing-codecheck/ci-portal/shield/audit`                            | POST | 屏蔽申请审核             |
| 3   | `/openlibing-codecheck/ci-portal/shield/auditRevoke`                      | POST | 撤销审核通过的问题       |
| 4   | `/openlibing-codecheck/ci-portal/shield/referral`                         | POST | 待审核问题转审           |
| 5   | `/openlibing-codecheck/ci-portal/shield/revoke`                           | POST | 已审核问题撤销           |
| 6   | `/openlibing-codecheck/ci-portal/v2/grant/auth/attributes/ruleSet/config` | POST | 创建/配置规则集          |
| 7   | `/openlibing-codecheck/codecheck/operate/project/ruleSetList`             | POST | 删除/保存/更新规则集集合 |
| 8   | `/openlibing-codecheck/ci-portal/v2/grant/auth/default/template`          | GET  | 设置默认规则集           |
| 9   | `/openlibing-codecheck/ci-portal/v2/grant/auth/modify/createUser`         | GET  | 修改规则集创建人         |
| 10  | `/openlibing-codecheck/ci-portal/ci-sensitive/sensitive/config/ruleSet`   | POST | 配置敏感词集到规则集     |
| 11  | `/openlibing-codecheck/static-alarm/v1/issue/assign-owner`                | POST | 批量指定问题责任人       |

> `shield-all-result` 已随 `bdc9636b` 下线，无对应 URL，不需要配置。

## 2. 实现逻辑设计

### 2.1 批次 1

1. 修改 `log4j2-spring.xml` 的 `MANAGE_LOG_FILE` pattern。
2. `ManageLogHelper.writeLog` 增加字段净化；新增 `LogSanitizer.sanitize(String, int)` 长度截断重载（保持既有 `null -> null` 语义）。
3. `SuppressionScanServiceImpl` 收敛响应体与异常日志（保留异常类型与堆栈）。
4. 新增角色常量与集中判断方法，替换 5 组共 9 处角色字面量。
5. 运行 `ManageLogHelperTest`、`AuthUtilsTest`、`SensitiveDelegateImplTest`，补充新断言（`AuthUtilsTest` 扩展现有文件，覆盖 `isSystemAdmin` 的 admin / platform_operator / community_manager / 普通角色 / null / 空串）。

### 2.2 批次 2

1. 模型层补约束注解。
2. Controller 入参加 `@Valid`。
3. `FullSummaryOperation` 改造 skip 计算与异常抛出。
4. Controller 测试补充非法入参用例，断言 `4010103`（复用 `GlobalExceptionHandler` 现有参数错误码）。

### 2.3 批次 3

1. 新增 `CodePlatformProperties` 并注册。
2. 三个 Delegate 注入配置。
3. 动态主机拼接改白名单 Map。
4. 单测通过配置覆盖验证 URL 与邮箱。

### 2.4 批次 4

1. 核对现有 Handler 与 12 个接口的匹配关系，产出覆盖矩阵。
2. 新增 `ShieldLogHandler` 覆盖 6 个 shield 接口。
3. 新增 `StaticAlarmAssignLogHandler` 覆盖 `assign-owner`。
4. 扩展 `RuleSetLogHandler` 覆盖 `default/template`、`modify/createUser`。
5. 输出网关菜单 `write_log` 配置清单，交部署侧执行。

### 2.5 批次 5

1. 新增 `PageParams` 与 `PaginationProperties`，逐链路替换分页计算（10 个端点，含 `/machine-api/v1/full-codecheck-record/list`），上限可配置。
2. 敏感词配置统计改为 `count` + 按 `type` 聚合；metrics `total` 改为 `mongoTemplate.count`，不再置空分页全量加载。
3. 新增导出上限配置与校验。
4. SARIF 增加 `LimitedInputStream`、数量校验与配置合法性校验（拒绝 0/负数）；Jackson 3 的非受检解析异常统一转为 `IOException`，保证按 URL 隔离失败。
5. 补 FOSS 正则防护与 StaticAlarm `searchRepos` limit 的回归用例。
6. 批次 5 实施前先确认默认值。

## 3. 类设计

### 3.1 新增类

| 类                                            | 职责                                       |
| --------------------------------------------- | ------------------------------------------ |
| `common/utils/PageParams.java`                | 统一分页默认值、上限、skip 计算与负值校验  |
| `common/config/PaginationProperties.java`     | 分页上限配置（可覆盖 `PageParams` 默认值） |
| `common/config/CodePlatformProperties.java`   | 平台域名、API 地址、通知邮箱配置           |
| `common/io/LimitedInputStream.java`           | 限制读取字节数的输入流包装（本次新增）     |
| `common/aop/ShieldLogHandler.java`            | shield 接口操作日志补数                    |
| `common/aop/StaticAlarmAssignLogHandler.java` | assign-owner 操作日志补数                  |

> `LogSanitizer` 为**既有类**（`common/util/LogSanitizer.java`，注意不是 `common/utils`），本次复用并新增长度截断重载（保持既有 `null -> null` 语义），不列入新增类。

### 3.2 修改类

| 类                                                                                                                                                  | 修改点               |
| --------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- |
| `ManageLogHelper`                                                                                                                                   | 日志字段净化         |
| `SuppressionScanServiceImpl`                                                                                                                        | 响应体/异常日志收敛  |
| `AuthUtils` / `SensitiveDelegateImpl` / `CommonOperation` / `CheckPermissionOperation`                                                              | 角色常量与集中判断   |
| `ProblemshieldController` / `RuleController` / `FileDownLoadController` / `SensitiveController`                                                     | `@Valid`             |
| `UpdateRuleModel` / `ShieldModel` / `QueryFossScanModel` / `RuleModel` / `SelfShieldModel` / `WorkbenchModel` / `QuerySensitiveRuleModel`           | 校验注解             |
| `QueryTaskSummaryMachineApiModel`                                                                                                                   | 分页约束与一致性校验 |
| `FullSummaryOperation` / `StaticAlarmSummaryOperation` / `FossScanOperation` / `WorkbenchOperaton` / `IncDetailsOperation` / `FullDetailsOperation` | 分页上限与计数查询   |
| `SensitiveRuleOperation` / `SensitiveDelegateImpl`                                                                                                  | 敏感词统计聚合计数   |
| `ProblemShieldOperation`                                                                                                                            | 自定义屏蔽分页上限   |
| `StaticAlarmServiceImpl` / `FileDownloadDelegateImpl` / `ExcelReportImpl`                                                                           | 导出上限             |
| `SarifParseServiceImpl`                                                                                                                             | SARIF 上限           |
| `CheckboardDelegateImpl` / `ProblemshieldDelegateImpl` / `PipelineDelegateImpl`                                                                     | 配置化地址与邮箱     |
| `RuleSetLogHandler` / `SensitiveLogHandler`                                                                                                         | 扩展审计匹配范围     |

## 4. 数据模型设计

- 数据库 schema 无变更。
- 请求模型仅新增校验注解，不改变 JSON 字段名与结构。
- 新增配置项如下（参数已确认）：

| 配置项                                     | 默认值                      | 状态   |
| ------------------------------------------ | --------------------------- | ------ |
| `codecheck.platform.gitcode-web-base-url`  | `https://gitcode.com/`      | 确定   |
| `codecheck.platform.gitee-web-base-url`    | `https://gitee.com/`        | 确定   |
| `codecheck.platform.gitcode-api-base-url`  | `https://api.gitcode.com/`  | 确定   |
| `codecheck.notification.mail-from-name`    | `openLiBingCI`              | 确定   |
| `codecheck.notification.mail-from-address` | `pre-commit@openlibing.com` | 确定   |
| `codecheck.export.max-rows`                | `200000`                    | 已确认 |
| `codecheck.export.max-file-bytes`          | `104857600`                 | 已确认 |
| `codecheck.export.max-merge-parts`         | `50`                        | 已确认 |
| `codecheck.pagination.max-page-size`       | `100`                       | 已确认 |
| `codecheck.pagination.max-unpaged-size`    | `1000`                      | 已确认 |
| `codecheck.alarm.sarif.max-urls`           | `50`                        | 已确认 |
| `codecheck.alarm.sarif.max-file-bytes`     | `52428800`                  | 已确认 |
| `codecheck.alarm.sarif.max-runs`           | `20`                        | 已确认 |
| `codecheck.alarm.sarif.max-results`        | `100000`                    | 已确认 |

## 5. 性能设计

- 分页链路统一限制 `pageSize <= 100`，避免单次查询放大。
- 机机接口不传分页时最多返回 `MAX_UNPAGED_SIZE` 条，避免全表扫描与全量序列化。
- metrics total 使用 `count` 聚合，避免将全量文档加载到内存。
- 导出采用流式分批写，增加总行数与文件大小上限，防止磁盘/内存耗尽。
- SARIF 解析使用流式 `LimitedInputStream`，超限立即中断，不产生大对象。
- 所有上限均可配置，便于按环境调整。

## 6. API接口设计

- 不新增、不删除、不改名任何接口路径。
- 不改变请求/响应字段结构。
- 行为变化：
  - 非法入参由“静默接受”变为 `DataResult.code=4010103`；
  - 越权/参数非法由业务层返回 403；
  - 导出/SARIF 超限返回明确错误信息；
  - 机机接口分页参数只传一个时返回参数错误。
- 需要同步前端/调用方的点：
  - `shieldSubmit` / `shieldReferral` / `shieldRevoke` 的 `notifyType` 必须传；
  - `updateRule` 的 `taskId`、`projectId`、`repoName`、`ruleSets` 必须合法；
  - `exportBoardByFile` 的 `summaryId` / `tableName` / `defectStatus` / `flag` 必须传；
  - 机机接口分页参数必须成对出现。

## 7. 安全设计

### 7.1 威胁覆盖

| 威胁                         | 覆盖方式                                                    |
| ---------------------------- | ----------------------------------------------------------- |
| 日志伪造（CWE-117）          | 输出层 `%enc{CRLF}` + 字段净化                              |
| 参数绕过（CWE-20）           | `@Valid` + 模型约束 + delegate 业务校验                     |
| 资源耗尽（CWE-400）          | 分页/导出/SARIF 上限 + 流式读取                             |
| 鉴权逻辑不一致（CWE-511）    | 角色常量集中，避免字面量漂移                                |
| 敏感地址/凭证泄露（CWE-798） | 配置化 + 白名单查表                                         |
| 敏感信息泄露（CWE-209）      | 省略响应体/异常 message 原文，保留异常类型/堆栈与脱敏上下文 |
| 操作不可追溯（CWE-778）      | 操作日志 Handler 补齐 + 网关菜单打标                        |

### 7.2 密钥与敏感信息

- 通知邮箱、平台域名均为公开信息，配置化后仍保留默认值。

### 7.3 兼容与回退

- 所有上限配置支持运行时覆盖；极端情况下可调高上限回退。
- #202 配置项均有默认值，未配置时行为不变。

### 7.4 已知边界

- #365 机机接口“不传分页=全量”的既有语义会变为“最多返回上限条数”，参数已确认，上线前需通知调用方。
- #364 / #247 的默认上限值已按建议值确认，避免误伤正常大仓库。
- #247 的 `obsUrls` 数量超限是整批拒绝（不截断、不部分入库）；单 URL 的文件大小/runs/results 超限才是单 URL 隔离失败。`0 = 不限制` 不受支持，0/负数会在启动时校验失败并告警。
- #363 的代码侧 Handler 可在本仓完成，但操作日志切面依赖网关 `X-Operation-Log` 头；菜单 `write_log` 与 URL 绑定需部署侧配置，否则代码改动不会生效。
- #249（RabbitMQ 消息无签名）暂不修复，保留 Issue 打开，本批次不涉及 Producer/Consumer 改动。
