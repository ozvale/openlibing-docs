# 安全问题整改修复 — 实现任务

## 进度: 两部分均已完成（遗留/豁免项见 archive.md）

### A 批（#280 #281 #282 #287 #295 #352）

- [x] RuleController / FulltaskController / ProblemshieldController 等 18+ 接口补 userId 必填 + checkPermission + projectId 非 0 校验（commit `1b3566df` 批次1+2、`d3f41187` 批次3）
- [x] openlibing-web 前端调用补 projectId（commit `f773864b` / `333678ec`）
- [x] 补充/更新 Controller 与 Delegate 测试，全量 1483 测试通过

### B 批（#284 #288 #289 #292）

- [x] exportDebugFile 补 userId + projectId 校验 + checkPermission（#284）
- [x] ShieldAll PASS_REVOKE 候选条件归属约束（#288）
- [x] shieldRevoke / shieldPassRevoke 归属校验 checkRevokeOwnership（#289）
- [x] 或签抢占/回滚绑定操作人，回滚操作人显式传参（#292）
- [x] 补充测试（403 越权用例 + 归属断言），全量 1469 测试通过（commit `f1d46781`）

### C 批（#278 #279 #286 #254 #382 #384）

- [x] listCriterions / listCriterionFilters 参数 URL 编码（#278 #279）
- [x] obsUrl 协议/主机白名单 + 超时 + 禁重定向（#286 #245）
- [x] OBS 对象 key 白名单校验（#254）
- [x] suppression 接口 owner/repo/prNumber 白名单/正则校验（#382）
- [x] getLoginEmailByToken 的 repoType 平台白名单（#384）
- [x] 补充测试（编码断言 + 白名单/302/超时用例，端到端改本地 HttpServer），全量 1470 测试通过（commit `ea6af6f2`；补充修复 `fd152406`）

### D 批（#290 #291）

- [x] #290 按 SIG 结论豁免（维持 tag 引用），评论记录
- [x] #291 技术核实后豁免（secure 属性不存在），评论记录并建议部署层跟踪

### B2 凭证与加密（#220 #221 #222 #305）

- [x] auto-fix token 改环境变量 `FIX_TARGET_TOKEN`/`FIX_SOURCE_TOKEN` 传入，移出 argv（#220）
- [x] git 凭证改 GIT_ASKPASS 临时脚本，token 不落盘 `.git/config`，用后清理（#221）
- [x] GitCodeHelper/GiteeHelper token 改 `PRIVATE-TOKEN` header，HttpRequestUtil 增加 header 重载（#222）
- [x] 外部 auto-fix.sh 执行固定路径 + 参数白名单 + 敏感 token 移出 argv（#305）
- [x] GiteeHelperTest 通过，pre-commit 通过（commit `2cee975a` → `5faa765d`，PR !369）

### B3 传输与配置（#301 #303）

- [x] ProblemshieldDelegateImpl 内部服务调用 http→https（#301）
- [x] EmailUtil 增加 STARTTLS 与 buildMailProperties（#303，commit `90e5dfd6` → `0ad25e48`，PR !370）
- [x] 因 SMTP TLS 需平台统一改造，回退 STARTTLS 改动，保留 host/auth（commit `2de976fd`，PR !383，跟踪 #392）
- [x] EmailUtilTest 通过

### B4 依赖升级（#161 #226 #228）

- [x] log4j2 2.24.3 → 2.26.1（CVE-2026-49844，commit `3b48aef0`）
- [x] jsoup 1.15.3 → 1.23.2、kotlin-stdlib 1.9.25 → 2.4.20、amqp-client 5.37.0（commit `3e527937` → `edc97945`）
- [x] `mvn test-compile` 通过，依赖树版本核对通过（PR !376）

### B5 日志与审计（#214 #241 #256 #297）

- [x] LogSanitizer 新增 maskSensitiveFields / sanitizeAndMask（#256）
- [x] Controller / Operation / Delegate / webhook 入口 / RestCodeCheckUtil 响应体日志统一脱敏（#214 #241 #297）
- [x] 补齐检视指出的日志脱敏遗漏（commit `ee17aa49`）
- [x] LogSanitizerTest 23 项通过，pre-commit 通过（PR !377）

### 输入校验与资源限制（#357 #242 #374 #366 #247）

- [x] 正则参数 `Pattern.quote` 转义（#357）
- [x] 告警邮件 HTML 实体转义（#242）
- [x] 异常详情不回显客户端，改固定文案（#374）
- [x] ReDoS 与扫描量限长/限量（#366）
- [x] SARIF 移除 50 URL/50MB 硬限制，改记录 obsUrlCount/fileSize/runs（#247）
- [x] 相关 64 个用例通过，pre-commit 通过（PR !378）

### 免认证接口越权（#389）

- [x] 新增 CheckboardRepoAccessService/Helper，看板/文件下载/Excel 导出统一仓可见性校验（PR !381）
- [x] Excel 导出 userId 改 Query 参数，DTO 移除 userId；补充 CheckboardRepoAccessHelperTest 等（PR !384）
