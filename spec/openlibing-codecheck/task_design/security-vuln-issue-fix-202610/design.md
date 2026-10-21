# 安全漏洞 Issue 批次修复 — 设计

## 1. 方案设计

分 A/B/C 三批独立分支与 PR 交付，每批聚焦一个主题，互不依赖；D 批（#290 #291）技术核实后豁免。整体采用分层防护：

- **身份层**：网关注入可信 userId（客户端不可伪造），A 批前端接口全覆盖；
- **授权层**：`authUtils.checkPermission("/openlibing-codecheck"+真实路径, projectId, userId)` 菜单 URL 精确校验 + `projectId<=0` 一律拦截（防绕过）；
- **资源归属层**：撤销/审核类接口校验操作人须为申请人（revision.userId）或审核人（reviewerId/reviewers.userId 命中）；
- **注入类**：URL 构建层统一 `URLEncoder.encode`（UTF-8），一处修复覆盖所有调用方；
- **SSRF 类**：协议白名单（仅 http/https）+ 主机白名单（精确匹配）+ 超时 + 禁重定向；
- **并发类**：抢占/回滚查询条件绑定操作人，回滚操作人由调用处显式传入。

## 2. 实现逻辑设计

- **A 批（#280 #281 #282 #287）**：各 Controller 接口补 `@RequestParam("userId", required=true)`，`projectId<=0` → 403「projectId is invalid」；`!checkPermission(...)` → 403「no permission」；前端调用从 `app.projectInfo.projectId` 携带 projectId。
- **B 批**：
  - #284 `FileDownLoadController.exportDebugFile`：补 userId 必填 + projectId 非 0 校验 + checkPermission；
  - #288 `ShieldAllQueryOperation.buildHardCriteria` PASS_REVOKE：`revision.reviewerStatus=2` 且归属约束（申请人 or 审核人）；
  - #289 `ProblemshieldDelegateImpl`：新增 `checkRevokeOwnership`，shieldRevoke/shieldPassRevoke 在 occupied 检查后调用；
  - #292 `ProblemShieldOperation`：claimPendingAudits 增加 reviewerCriteria；rollbackClaimedAudits 改 3 参并限定 `revision.reviewerId=操作人`；Delegate 回滚显式传 userId（修复 shieldAllAudit 未设 auditModel.userId 隐患）。
- **C 批**：
  - #278/#279 `RestCodeCheckUtil.listCriterions/listCriterionFilters`：参数 key/value 均 `urlEncode()`；
  - #286 `SarifParseServiceImpl.downloadAndParse`：`validateObsUrl`（scheme 仅 http/https + 主机白名单）+ HttpURLConnection（connect 5s/read 30s + `setInstanceFollowRedirects(false)`）+ `URI.create` 异常转 IOException。

## 3. 类设计

- `FileDownLoadController`：exportDebugFile 增加鉴权前置逻辑。
- `ShieldAllQueryOperation`：PASS_REVOKE 候选条件增加归属约束，新增 `reviewerCriteria`。
- `ProblemshieldDelegateImpl`：新增 `checkRevokeOwnership(List<DefectVo>, String userId)`；`rollbackClaimedAudits(AuditModel, List<DefectVo>, String userId)` 3 参。
- `ProblemShieldOperation`：`claimPendingAudits`/`rollbackClaimedAudits` 绑定 reviewerId，新增 `reviewerCriteria`。
- `RestCodeCheckUtil`：新增 `urlEncode(String)` helper（URLEncoder + UTF-8）。
- `SarifParseServiceImpl`：新增 `validateObsUrl(URI)`/`isHostAllowed(String)`，`obsHostWhitelist` 实例字段默认项目 OBS 桶。

## 4. 数据模型设计

不涉及（无 schema / 数据结构 / 迁移变化）。

## 5. 性能设计

- SSRF 下载增加 connect 5s / read 30s 超时，避免请求挂起；单个 URL 失败仅记录错误，不阻塞其他 URL 解析。
- 归属条件基于已有索引字段（revision.userId / reviewerId / reviewers.userId），查询开销可忽略。
- 或签抢占 `updateMulti` 原子条件绑定操作人，减少无效抢占与回滚，避免重复处理。

## 6. API接口设计

- 变化：`GET /ci-portal/excel/v1/download/log`（exportDebugFile）新增必填 `userId` 参数（网关注入的可信身份）。
- 变化：A 批 18+ 前端调用接口需携带 projectId（前端从 `app.projectInfo.projectId` 获取，由网关补全/校验）。
- 无新增接口，无响应体结构变化；DataResult 返回型接口的 403 响应为 `DataResult.build(403, "no permission", null)`。

## 7. 安全设计

### 鉴权

- 身份层：网关注入可信 userId，客户端不可伪造（A 批全覆盖）；未登录/缺 userId → 必填参数校验 400。
- 授权层：`checkPermission` 按 menu_url_info 表精确匹配；`projectId<=0` 一律 403，防止 projectId=0 绕过。
- 资源归属：撤销/审核/抢占类接口操作人须为申请人或审核人，否则 403；空列表 50001。

### 敏感信息

不涉及新增敏感字段；沿用既有日志脱敏约定（MessageMaskUtils）掩码 token/password/secret 等。

### 硬编码

SSRF 主机白名单默认值为项目固定 OBS 公共读桶域名（实例字段逗号分隔可扩展），非凭证硬编码；无新增密钥/令牌。

### 审计日志

审批/撤销/抢占操作人字段以网关可信身份为准，客户端改写 userId 无法把操作记到被冒充者名下；撤销与回滚均限定本人记录。
