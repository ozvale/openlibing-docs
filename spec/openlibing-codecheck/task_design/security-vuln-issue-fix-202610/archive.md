# 安全问题整改修复 — 归档

## 一、漏洞挖掘批次（A/B/C）

### 关联

- 业务 Issue（已修复 16 个）：
  - #280 规则控制器用户ID参数未验证导致认证绕过（CWE-287，严重）
  - #281 全量检查任务管理接口缺少身份认证机制（CWE-306，严重）
  - #282 问题屏蔽审核接口缺失认证导致未授权访问（CWE-306，严重）
  - #287 屏蔽审批/撤销接口操作者身份可伪造（CWE-287，高危）
  - #284 任务日志下载接口缺少权限校验导致越权访问（CWE-639，高危）
  - #288 屏蔽审核通过后撤销全部缺少服务端归属校验（CWE-639，高危）
  - #289 屏蔽撤销与已审撤销接口缺少资源归属校验（CWE-639，高危）
  - #292 问题屏蔽或签抢占与回滚未按操作人隔离（CWE-362，中危）
  - #278 规则查询接口参数未编码导致 HTTP 参数注入（高危）
  - #279 规则过滤器接口参数未编码拼接 URL 导致参数注入（高危）
  - #286 静态告警接收接口 obsUrl 未校验导致 SSRF 与本地文件读取（CWE-918，高危）
  - #295 门户接口身份取自请求参数服务端不可验证（高危）
  - #352 40 个接口未校验资源归属（高危）
  - #254 OBS 对象 key 无白名单可越权覆盖（中危）
  - #382 suppression 扫描接口 URL 拼接未校验存在 SSRF/路径注入风险（中危）
  - #384 webhook 可控 repoType 拼接主机名存在主机注入/SSRF 与 token 泄露风险（中危）
- 业务 Issue（豁免 2 个）：
  - #290 CI 工作流 action 引用未固定 commit SHA（CWE-829，中危）→ SIG 组结论维持 tag 引用
  - #291 Nacos 配置中心明文 HTTP 拉取（CWE-319，中危）→ `config.secure` 属性不存在，需平台开 TLS + 部署层变更
- 业务 PR：!366（分支 A：#280 #281 #282 #287 #295 #352）、!367（分支 B：#284 #288 #289 #292）、!368（分支 C：#278 #279 #286 #254 #382 #384）
- docs PR：本文档

### 交付历程

| 批次 | 分支                         | 修复内容                                                                                                                                                                                                                                                                                    | commit                                                                                 |
| ---- | ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------- |
| A    | `fix-auth-trusted-identity`  | 前端接口补可信身份 + checkPermission 横向鉴权（RuleController/FulltaskController/ProblemshieldController/CheckboardController/FileDownLoadController/SelectionController/SensitiveController/IgnoretreeController/StaticAlarmController 等 18+ 接口）；前端 openlibing-web 同步补 projectId | `1b3566df`（批次1+2，18 文件）、`d3f41187`（批次3，5 文件）；web `f773864b`/`333678ec` |
| B    | `fix-auth-revoke-permission` | 撤销接口越权/并发：exportDebugFile 补 userId+checkPermission（#284）；ShieldAll PASS_REVOKE 候选归属约束（#288）；shieldRevoke/shieldPassRevoke 归属校验（#289）；或签抢占/回滚绑定操作人（#292）                                                                                           | `f1d46781`（8 文件）                                                                   |
| C    | `fix-param-injection-ssrf`   | listCriterions/listCriterionFilters 参数 URL 编码（#278/#279）；downloadAndParse 协议/主机白名单 + 超时 + 禁重定向（#286）；OBS key 白名单（#254）；suppression URL 路径校验（#382）；repoType 主机白名单（#384）                                                                           | `ea6af6f2`（4 文件）、`fd152406`（5 文件）                                             |

### 用户自测反馈（第一部分）

- 每批次均由用户自测确认完成后才创建 PR，无遗留问题反馈。
- 编码阶段自检发现：分支 B 撤销/审核测试数据缺 userId 归属导致 6 例失败 → 补归属数据修复；shieldAllAudit 未设 auditModel.userId 导致回滚条件为 null 的生产隐患 → rollbackClaimedAudits 改为调用处显式传参。

## 二、ICSL 安全送检整改批次（#372）

### 关联

- 总需求：https://gitcode.com/openlibing/openlibing-codecheck/issues/372 【openLiBing】ICSL安全送检排查及整改
- 业务 PR（2026-10-28 ~ 10-29 合入 release_20261029_iter2）：
  - !369 B2 凭证与加密：#220 #221 #222 #305
  - !370 B3 传输与配置：#301 #303 → !383 回退 #303（#392）
  - !376 B4 依赖漏洞升级：#161 #226 #228
  - !377 B5 日志与审计：#214 #241 #256 #297
  - !378 输入校验与资源限制：#357 #242 #374 #366 #247
  - !381 / !384 免认证接口仓可见性越权校验：#389

### 交付历程

| 批次 | 分支                                    | 修复内容                                                                                                                                                                                | PR / commit                                     |
| ---- | --------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------- |
| B2   | `fix-security-credential-crypto`        | token 移出子进程 argv（环境变量 `FIX_TARGET_TOKEN`/`FIX_SOURCE_TOKEN`）；git 凭证改 GIT_ASKPASS 临时脚本；代码平台 token 改 `PRIVATE-TOKEN` header；外部 auto-fix.sh 敏感信息暴露面收敛 | !369，`2cee975a` → `5faa765d`                   |
| B3   | `fix-security-transport-config`         | 内部服务调用 http→https（#301）；SMTP STARTTLS 加固（#303）后因平台统一 TLS 回退，仅保留 host/auth（#392）                                                                              | !370，`90e5dfd6` → `0ad25e48`；!383，`2de976fd` |
| B4   | `fix-security-deps`                     | log4j2 2.24.3→2.26.1（CVE-2026-49844）、jsoup 1.15.3→1.23.2、kotlin-stdlib 1.9.25→2.4.20、amqp-client 显式 5.37.0                                                                       | !376，`3e527937` → `3b48aef0` → `edc97945`      |
| B5   | `fix-security-log-sanitize`             | LogSanitizer 新增 `maskSensitiveFields`/`sanitizeAndMask`；Controller/Operation/Delegate/webhook/RestCodeCheckUtil 统一 CRLF 净化 + 敏感字段掩码                                        | !377，`83270256` → `0ce76e80` → `ee17aa49`      |
| 输入 | `fix-security-input-validation`         | `Pattern.quote` 正则转义（#357）、`HtmlUtils.htmlEscape` 邮件 HTML 转义（#242）、异常详情不回显（#374）、ReDoS/扫描量限长限量（#366）、SARIF 移除硬截断仅记录规模（#247）               | !378，`66db0d72` → `2cf79136`                   |
| 越权 | `fix-checkboard-repo-visibility-auth-2` | CheckboardRepoAccessService/Helper 统一仓可见性校验；Excel 导出 userId 改 Query、DTO 移除 userId（#389）                                                                                | !381，`59b5cc40`；!384                          |

### 最终验证

- 第一部分：分支 A 全量 1483 测试 0 失败；分支 B 1469 测试 0 失败；分支 C 1470 测试 0 失败；编译通过。
- 第二部分：B2 GiteeHelperTest 通过；B3 EmailUtilTest 通过；B4 `mvn test-compile` 通过且依赖树版本核对通过；B5 LogSanitizerTest 23 项通过；输入校验相关 64 个用例通过；越权校验新增/更新 CheckboardRepoAccessHelperTest 等通过。
- 全部 PR 均带 `ai-assisted` 与 `ci-pipeline-passed` 标签，CI 通过。
- 合并入 `develop_202610_iter2` 后全量 1571 单元测试通过，pre-commit（gitleaks/spotless/checkstyle/spotbugs/pmd）通过。

## 三、设计偏差、豁免与遗留

### 用户确认的豁免

1. **#278/#279「RuleModel 增加输入校验」豁免**：URL 编码已彻底闭合参数注入；自由文本搜索字段（ruleName）白名单会误伤合法输入、枚举校验与华为云外部接口契约耦合。已记入 commit `ea6af6f2` body 留痕。
2. **#290 豁免**：SIG 组结论建议使用 tag 引用，不固定 commit SHA；已评论记录，未来引入第三方 action 时再评估。
3. **#291 豁免**：`spring-cloud-alibaba 2025.1.0.0` 的 `NacosConfigProperties` 无 `secure` 字段（javap 验证），`config.secure` 会被静默忽略；真实传输加密需 CSE Nacos 平台开通 TLS + nacos-client `tls.enable` 系统属性 + 证书信任（cacerts），属部署级变更，单独跟踪。
4. **#303 SMTP STARTTLS 回退**：SMTP AUTH 阶段返回 EOF，且 SMTP TLS 需平台统一改造；本服务回退为仅配置 `mail.smtp.host`/`mail.smtp.auth`，由 #392 跟踪平台统一处理。
5. **#247 SARIF 资源限制**：移除 50 URL/50MB 硬限制（会误截断合法大报告），改为记录 obsUrlCount/fileSize/runs；合理限制值待后续确定，Issue 保持 open。

### 遗留与后续跟踪

- 平台/部署级：#291（Nacos TLS）、#302（RabbitMQ SSL）、#306/#307（废弃 KMS/token 字段明文配置）。
- 依赖类（common 包引入）：#227（httpclient5）、#229（jackson-databind）、#230（jackson-core）、#231（spring-data-jpa 等），由 openlibing-common 处理。
- 未纳入本批次、保持 open：#249（RabbitMQ 消息无签名）、#250（非生产环境明文传输）、#251（恶意 prUrl 消耗配额）、#252（XXL-Job accessToken 明文）、#300（硬编码发件邮箱）、#363（非查询接口审计日志）、#364/#365（文件/分页大小无上限）、#373（分页参数未校验，相关提交 `f309e93e` 已 revert）、#375（pycache 入库）、#376（swagger 生产默认开启）、#385（接口参数未校验）、#386（日志注入 TOP 问题）、#389（免认证接口越权，PR !381/!384 已合入待验证关闭）。
- #161（jsoup CVE）与 #372（总需求）在 Issue 侧仍为 open，待验证关闭。

## 四、可复用经验（已同步 ai_memory.md）

1. **checkPermission 横向鉴权模式**：接口补 `userId` 必填 + `projectId<=0` 拦截（403「projectId is invalid」）+ `authUtils.checkPermission("/openlibing-codecheck"+路径, projectId, userId)`（403「no permission」）；URL 约定 `/openlibing-codecheck` 前缀。
2. **apigateway SDK `setUrl` 对已编码序列原样保留**（不二次编码，仅规范化 `+`→`%20`）：URL 编码类修复可直接在 URL 构建层 `URLEncoder.encode`，合法值语义不变。
3. **GitCode issue `state_event` 仅接受 open/closed/reopen/close**：CLI 无法设置自定义状态（如"修复中"），需网页手动切换。
4. **报告建议需技术可行性核实**：`javap` 反编译依赖 jar 验证属性是否存在；SDK/框架行为写最小探针程序实测，不凭记忆推断；平台能力无法在代码仓验证时标注为部署级变更。
5. **日志脱敏统一入口**：外部可控对象/响应体一律 `LogSanitizer.sanitizeAndMask()`（先 CRLF 净化再掩码），敏感字段清单集中在 `LogSanitizer.maskSensitiveFields`，避免各调用点自写正则。
6. **用户输入作 Mongo 正则必须 `Pattern.quote`**；邮件/富文本拼接外部字段必须 `HtmlUtils.htmlEscape`；异常详情只进服务端日志，客户端返回固定文案。
7. **凭证传递三原则**：不进 argv（环境变量/列表参数）、不进 URL 查询串（header）、不落盘（GIT_ASKPASS 临时脚本 + cleanup）。
8. **免认证接口不能只靠业务主键**：必须叠加资源归属/仓库可见性校验；userId 为空仅放行公开资源。

## 归档日期

- 第一部分：2026-10-21
- 第二部分：2026-10-30
