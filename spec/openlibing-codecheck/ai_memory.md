# openlibing-codecheck — AI 记忆（可复用规则）

本文件沉淀经过验证且会复用的规则，供后续 AI 任务直接引用，避免重复踩坑。

## 横向鉴权（checkPermission）模式

- 接口补 `@RequestParam(value = "userId", required = true) String userId`（网关注入可信身份，客户端不可伪造）。
- `projectId <= 0` → 403「projectId is invalid」，防止 projectId=0 绕过权限校验。
- `!authUtils.checkPermission("/openlibing-codecheck" + 真实HTTP路径, projectId, userId)` → 403「no permission」；URL 约定 `/openlibing-codecheck` 前缀，`menu_url_info` 表精确匹配。
- MultiResponse 返回型 `.code(403).message(...)`；DataResult 返回型 `DataResult.build(403, msg, null)`。
- Controller 测试：`@Mock AuthUtils` 默认不 stub（等价拒绝），仅在正常路径用例中 `lenient().when(authUtils.checkPermission(anyString(), any(), anyString())).thenReturn(true)`；每个受保护接口至少保留一条 `checkPermission=false → 403「no permission」` 与 `projectId<=0 → 403「projectId is invalid」` 断言，防止鉴权调用被删除或写反而单测仍全绿；model 测试数据 `setProjectId(>0)`。
- 资源归属校验（撤销/审核）：操作人须为申请人（revision.userId）或审核人（reviewerId/reviewers.userId 命中），否则 403；空列表 50001。

## apigateway SDK（java-sdk-core）URL 行为

- `Request.setUrl()` 解析 query 后重建时**对已编码序列原样保留**（不把 `%26` 二次编码为 `%2526`），仅把 `+` 规范化为 `%20`。
- 结论：参数注入修复可在 URL 构建层对 key/value 直接 `URLEncoder.encode(value, UTF_8)`，合法值（含空格/特殊字符）语义不变，无双重编码回归（实测验证，勿凭记忆改回裸拼接）。
- 跨仓引用：GitCode 平台内置动作（checkout/setup-jdk/setup-go）无仓库路径，无法/无需 SHA 固定；其余跨仓/第三方 action 必须固定 40 位 commit SHA，禁止 tag/branch 引用（#290 的豁免仅限平台内置动作）。

## Nacos / CSE

- `spring-cloud-alibaba`（2025.1.0.0）`NacosConfigProperties` **没有** `secure` 字段，`spring.cloud.nacos.config.secure` 无效；`secure` 仅存在于 `NacosDiscoveryProperties`（服务实例注册为 HTTPS，与配置拉取传输加密无关）。
- 客户端→Nacos 传输加密需 nacos-client TLS（`tls.enable` 系统属性 + 证书信任）+ 服务端开通 TLS，属部署级变更。

## 安全整改（ICSL）模式

- 日志脱敏统一走 `LogSanitizer`：外部可控对象/响应体用 `sanitizeAndMask()`（先 CRLF 净化再掩码），敏感字段清单集中在 `maskSensitiveFields()` 且字段名匹配不区分大小写；清单须覆盖 query/body 形态（token/accessToken/refresh_token/password/secret/private_key/access_key/secret_key/AK/SK）与 header 形态（authorization/PRIVATE-TOKEN/Cookie/Set-Cookie/api-key/x-auth-token），新增接入点须同步补清单，禁止各调用点自写正则。
- 用户输入作 Mongo `$regex` 模式必须 `Pattern.quote()`；邮件/HTML 拼接外部字段必须 `HtmlUtils.htmlEscape()`；异常详情只记服务端日志，客户端返回固定文案。
- 凭证传递三原则：不进 argv（列表参数即 argv，仅承载命令与非敏感参数，凭证一律走环境变量 / GIT_ASKPASS / `PRIVATE-TOKEN` header）、不进 URL 查询串、不落盘（GIT_ASKPASS 临时脚本 + cleanup 清理）。
- 免认证接口不能只靠业务主键（summaryId/taskId/uuid），必须叠加资源归属/仓库可见性校验：`userId` 为空仅放行公开仓只读，非空调用框架校验仓库读权限（`CheckboardRepoAccessHelper` 模式）；`userId` 必须从 Query 由网关注入，禁止从 body 取。
- SMTP TLS 由平台统一改造，本服务禁止单独加 STARTTLS（#392）；Nacos TLS / RabbitMQ SSL 同属平台/部署级变更，代码侧不改。
- SARIF 下载解析不设硬截断（50 URL/50MB 会误伤合法大报告），用 `CountingInputStream` 统计 obsUrlCount/fileSize/runs 并记录日志；必须补可配置软上限（fileSize/obsUrlCount），超限拒绝该 URL 并告警，默认阈值待定（#247）。
- 依赖漏洞只升级本仓直接依赖；common 包引入组件（jackson/httpclient5/nacos-client 等）由 openlibing-common 跟踪，不在本仓强行 override。

## GitCode CLI / Windows

- Issue `state_event` 仅接受 open/closed/reopen/close，**无法设置自定义状态**（如"修复中"）→ 告知用户在网页手动切换。
- 中文远端写操作必须 `--body-file` + `[System.IO.File]::WriteAllText(..., UTF8)` 写盘；PowerShell 5 不支持 `&&`。
- 跨仓 PR 必须 `--head fork-owner:branch`；PR 标签只追加不删（含 `ci` 的标签禁止修改、`needs-issue` 禁止删除）。
- 分支命名语义化（禁 batchX）；业务仓分支禁 `/`；docs 仓分支 `spec/<repo>/<change>`。

## 报告建议技术可行性核实

- 报告给出的属性/参数是否存在 → `javap` 反编译依赖 jar 验证（实例：NacosConfigProperties 无 secure 字段）。
- SDK/框架行为 → 写最小 Java 探针程序实测（实例：apigateway setUrl 不二次编码）。
- 外部平台能力（CSE Nacos TLS 等）无法在代码仓验证 → 标注部署级变更，不盲改，报告建议无效时向用户确认豁免并留痕。
