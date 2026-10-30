# 安全问题整改修复 — 设计

## 1. 方案设计

分两轮交付：第一部分漏洞挖掘按 A/B/C 三批独立分支与 PR；第二部分 ICSL 整改按主题分 B2~B5 与专项批次，每批一个分支一个 PR。整体采用分层防护：

- **身份层**：网关注入可信 userId（客户端不可伪造），前端接口全覆盖；
- **授权层**：`authUtils.checkPermission("/openlibing-codecheck"+真实路径, projectId, userId)` 菜单 URL 精确校验 + `projectId<=0` 一律拦截（防绕过）；
- **资源归属层**：撤销/审核类接口校验操作人须为申请人（revision.userId）或审核人（reviewerId/reviewers.userId 命中）；看板/导出类接口校验仓库可见性；
- **注入类**：URL 构建层统一 `URLEncoder.encode`（UTF-8）；Mongo 正则参数 `Pattern.quote`；邮件 HTML `HtmlUtils.htmlEscape`；
- **SSRF 类**：协议白名单（仅 http/https）+ 主机白名单（精确匹配）+ 超时 + 禁重定向；
- **并发类**：抢占/回滚查询条件绑定操作人，回滚操作人由调用处显式传入；
- **凭证类**：token 通过环境变量 / GIT_ASKPASS / 请求头传递，不进 argv、URL 查询串与 `.git/config`；
- **日志类**：CRLF 净化 + 敏感字段掩码统一走 `LogSanitizer`；
- **依赖类**：直接依赖漏洞版本升级，common 包引入组件由 openlibing-common 跟踪。

## 2. 实现逻辑设计

### 2.1 第一部分（漏洞挖掘 A/B/C）

- **A 批（#280 #281 #282 #287 #295 #352）**：各 Controller 接口补 `@RequestParam("userId", required=true)`，`projectId<=0` → 403「projectId is invalid」；`!checkPermission(...)` → 403「no permission」；前端调用从 `app.projectInfo.projectId` 携带 projectId。
- **B 批**：
  - #284 `FileDownLoadController.exportDebugFile`：补 userId 必填 + projectId 非 0 校验 + checkPermission；
  - #288 `ShieldAllQueryOperation.buildHardCriteria` PASS_REVOKE：`revision.reviewerStatus=2` 且归属约束（申请人 or 审核人）；
  - #289 `ProblemshieldDelegateImpl`：新增 `checkRevokeOwnership`，shieldRevoke/shieldPassRevoke 在 occupied 检查后调用；
  - #292 `ProblemShieldOperation`：claimPendingAudits 增加 reviewerCriteria；rollbackClaimedAudits 改 3 参并限定 `revision.reviewerId=操作人`；Delegate 回滚显式传 userId（修复 shieldAllAudit 未设 auditModel.userId 隐患）。
- **C 批**：
  - #278/#279 `RestCodeCheckUtil.listCriterions/listCriterionFilters`：参数 key/value 均 `urlEncode()`；
  - #286 `SarifParseServiceImpl.downloadAndParse`：`validateObsUrl`（scheme 仅 http/https + 主机白名单）+ HttpURLConnection（connect 5s/read 30s + `setInstanceFollowRedirects(false)`）+ `URI.create` 异常转 IOException；
  - #254 `ObsBucketServiceImpl.uploadFile` 增加 object key 白名单校验，拒绝路径穿越/绝对路径/非法字符；
  - #382 `SuppressionScanServiceImpl.buildPrFilesApiUrl`：owner/repo 仅允许字母数字 `_.-`，prNumber 必须为正整数，阻断路径注入/受限 SSRF；
  - #384 `PipelineDelegateImpl.getLoginEmailByToken`：repoType 仅允许 `gitee/gitcode/github` 白名单，拒绝后回落默认系统账号。

### 2.2 第二部分（ICSL 整改 B2~B5 与专项）

- **B2 凭证与加密（#220 #221 #222 #305）**：
  - auto-fix token 改 `ProcessBuilder.environment()`（`FIX_TARGET_TOKEN` / `FIX_SOURCE_TOKEN`）传入，不再作为脚本参数；
  - git clone/fetch/push 改用 `GIT_ASKPASS` 临时脚本（脚本仅 `echo` 变量名，不含 token 明文），token 不落盘 `.git/config`，`cleanup()` 删除临时脚本；
  - `GitCodeHelper` / `GiteeHelper` token 从 URL 查询参数改为 `PRIVATE-TOKEN` header，`HttpRequestUtil` 新增带 header 的 `httpsPostResponse` 重载；
  - #305 外部脚本固定路径 + `CommandArgSanitizer` 白名单 + `ProcessBuilder` 列表传参，敏感 token 移出 argv。
- **B3 传输与配置（#301 #303）**：
  - #301 `ProblemshieldDelegateImpl` 内部服务调用 `http://openlibing-framework` → `https://`；
  - #303 EmailUtil 曾强制 STARTTLS（`mail.smtp.starttls.enable` / `required`），因 SMTP AUTH 阶段 EOF 且 SMTP TLS 需平台统一改造，PR !383 回退为仅配置 `mail.smtp.host` / `mail.smtp.auth`，平台跟踪见 #392；
  - #291 Nacos TLS、#302 RabbitMQ SSL 属平台/部署级变更，代码侧不做单点修改。
- **B4 依赖升级（#161 #226 #228）**：`pom.xml` 中 log4j2 2.24.3 → 2.26.1（含 CVE-2026-49844）、jsoup 1.15.3 → 1.23.2、kotlin-stdlib 1.9.25 → 2.4.20、amqp-client 显式 5.37.0，并补齐 log4j-api 显式声明统一版本。
- **B5 日志与审计（#214 #241 #256 #297）**：
  - `LogSanitizer` 新增 `maskSensitiveFields`（字段名不区分大小写，覆盖 token/accessToken/refresh_token/password/secret/private_key/access_key/secret_key/AK/SK 等 body/query 字段与 authorization/x-auth-token 等 header 字段，命中值掩码为 `***`）与 `sanitizeAndMask`（先 CRLF 净化再掩码）；接入含 PRIVATE-TOKEN/Cookie/Set-Cookie/api-key 等 header 的日志前须先补清单；
  - 接入点：HwApigController 4 处、InternalCodeFullController / InternalCodeIncController / MachineApiCheckboardController 各 1 处、RuleSetOperation 2 处、ProblemshieldDelegateImpl 1 处、webhook 入口 9 处 params、PipelineDelegateImpl:302、RestCodeCheckUtil 11 处响应体日志。
- **输入校验与资源限制（#357 #242 #374 #366 #247）**：
  - #357 `RuleSetOperation` templateName、`SensitiveDelegateImpl` sensitiveId 3 处改用 `Pattern.quote()` 字面量转义；
  - #242 `SaveIncTaskResult.buildEmailContent` 5 处外部字段改 `HtmlUtils.htmlEscape()`；
  - #374 `SuppressionScanController` 与 `WebhookDelegateImpl` 4 处 catch 回显改固定文案，异常详情仅记服务端日志；
  - #366 FossScan filePath/componentName 改 `Pattern.quote()` + 限长 100；ruleTag/ruleName 限长 100；suppression 单次 500 文件、单文件 20000 行；
  - #247 移除 50 URL / 50MB 硬限制，改用 `CountingInputStream` 统计字节，记录 obsUrlCount / fileSize / runs，不截断解析；遗留约束：须补可配置软上限（建议 `codescan.sarif.max-file-size` / `codescan.sarif.max-obs-url-count`，默认阈值由 #247 评估确定），超限拒绝该 URL 并告警。
- **免认证接口越权（#389）**：
  - 新增 `CheckboardRepoAccessService` / `CheckboardRepoAccessHelper`：userId 为空仅公开仓只读放行；userId 非空调用框架校验用户对仓库的读权限；
  - `CheckboardDelegateImpl` 概览/趋势/详情统一走 Helper，替代原内联鉴权；
  - `FileDownLoadController` / `ExcelReportImpl`：提交导出前 `assertExportAccess`，状态查询 `assertExportAccessByRecordKey`，`summary/detail/export` 的 userId 改 Query `@RequestParam(required=false)`，DTO 移除 userId 字段。

## 3. 类设计

- `FileDownLoadController`：exportDebugFile 鉴权前置；导出接口 userId 改 Query 参数。
- `ShieldAllQueryOperation`：PASS_REVOKE 候选条件增加归属约束，新增 `reviewerCriteria`。
- `ProblemshieldDelegateImpl`：新增 `checkRevokeOwnership`；`rollbackClaimedAudits` 改 3 参；内部调用 https。
- `ProblemShieldOperation`：`claimPendingAudits`/`rollbackClaimedAudits` 绑定 reviewerId，新增 `reviewerCriteria`。
- `RestCodeCheckUtil`：新增 `urlEncode(String)` helper（URLEncoder + UTF-8）；响应体日志脱敏。
- `SarifParseServiceImpl`：新增 `validateObsUrl`/`isHostAllowed`、超时与禁重定向、资源规模统计。
- `LogSanitizer`：新增 `maskSensitiveFields` / `sanitizeAndMask`。
- `CheckboardRepoAccessService` / `CheckboardRepoAccessHelper`：仓库可见性校验统一入口。
- `PipelineDelegateImpl` / `scripts/auto-fix.sh`：token 环境变量传递 + GIT_ASKPASS。
- `GitCodeHelper` / `GiteeHelper` / `HttpRequestUtil`：token header 化与 header 请求重载。

## 4. 数据模型设计

不涉及（无 schema / 数据结构 / 迁移变化）。

## 5. 性能设计

- SSRF 下载增加 connect 5s / read 30s 超时，避免请求挂起；单个 URL 失败仅记录错误，不阻塞其他 URL 解析。
- 归属条件基于已有索引字段（revision.userId / reviewerId / reviewers.userId），查询开销可忽略。
- 或签抢占 `updateMulti` 原子条件绑定操作人，减少无效抢占与回滚，避免重复处理。
- SARIF 解析不再硬截断，`CountingInputStream` 仅计数不缓存；规模写入日志用于后续确定合理限制值。**遗留约束**：当前仅记录规模、未设阈值，后续须补可配置软上限（建议 `codescan.sarif.max-file-size` / `codescan.sarif.max-obs-url-count`），超限拒绝该 URL 并告警（#247）。
- Suppression 扫描限制单次 500 文件 / 单文件 20000 行，防止超大 PR 逐行匹配耗尽 CPU。
- 仓可见性校验为每请求一次框架权限查询，与既有菜单鉴权开销一致。

## 6. API接口设计

- 变化：`GET /ci-portal/excel/v1/download/log`（exportDebugFile）新增必填 `userId` 参数（网关注入的可信身份）。
- 变化：A 批 18+ 前端调用接口需携带 projectId（前端从 `app.projectInfo.projectId` 获取，由网关补全/校验）。
- 变化：`GET /ci-portal/excel/v1/summary/detail/export` 的 `userId` 由 body 改为 Query（`required=false`，网关注入；公开仓可匿名只读）；`ExportDetailRequestDTO` 移除 userId 字段。
- 变化：看板/导出类接口 `userId` 可选——为空时仅允许访问公开仓，非空时按用户仓库读权限校验。
- 无新增接口，无响应体结构变化；DataResult 返回型接口的 403 响应为 `DataResult.build(403, "no permission", null)`。

## 7. 安全设计

### 鉴权

- 身份层：网关注入可信 userId，客户端不可伪造；A 批接口 userId 必填，未登录/缺 userId → 400；免认证/看板/导出接口 userId 为 `required=false`，为空时仅允许公开仓只读访问，非空时按用户仓库读权限校验。
- 授权层：`checkPermission` 按 menu_url_info 表精确匹配；`projectId<=0` 一律 403，防止 projectId=0 绕过。
- 资源归属：撤销/审核/抢占类接口操作人须为申请人或审核人，否则 403；空列表 50001。
- 仓库可见性：看板/导出接口按仓库公开性 + 用户读权限校验，私有仓无 userId 一律拒绝。

### 敏感信息

- 凭证：token 不进 argv、URL 查询串、`.git/config`；GIT_ASKPASS 临时脚本用后清理。
- 日志：`LogSanitizer.sanitizeAndMask` 统一 CRLF 净化 + token/password/secret/private_key/AK/SK 掩码。
- SMTP 口令：本服务不做 STARTTLS，待平台统一 TLS 改造（#392）。

### 硬编码

- SSRF 主机白名单默认值为项目固定 OBS 公共读桶域名（实例字段逗号分隔可扩展），非凭证硬编码；无新增密钥/令牌。

### 审计日志

- 审批/撤销/抢占操作人字段以网关可信身份为准，客户端改写 userId 无法把操作记到被冒充者名下；撤销与回滚均限定本人记录。
- 非查询类接口审计日志（#363）未纳入本批次，后续跟踪。

### 依赖与供应链

- 直接依赖升级至修复版本（log4j2 2.26.1 / jsoup 1.23.2 / kotlin-stdlib 2.4.20 / amqp-client 5.37.0）。
- common 包引入组件由 openlibing-common 跟踪（#227 #229 #230 #231）。
