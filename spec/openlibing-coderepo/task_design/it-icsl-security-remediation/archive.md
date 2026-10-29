# Archive：【openLiBing】ICSL安全送检排查及整改（openlibing-coderepo 侧）

- **FE 需求名称**：【openLiBing】ICSL安全送检排查及整改
- **FE 需求 Issue**：openlibing/openlibing-codecheck#372（<https://gitcode.com/openlibing/openlibing-codecheck/issues/372>）
- **整改仓**：openlibing/openlibing-coderepo（问题台账：`20261012091116_issues_export.xlsx`）
- **交付规模**：26 项已合并（25 个 PR）+ 1 项在途 + 5 项登记接受
- **合入分支**：Batch 1 → `release_20261019_iter1`（#223 入 `release_20261020`）；Batch 2 → `release_20261029_iter2`
- **归档时间**：2026-10-29

## 一、已合并问题与 PR 汇总（26 项 / 25 个 PR）

| issue | 主题                          | PR                                                                            | 分支                                 | 修复要点                                                                       |
| ----- | ----------------------------- | ----------------------------------------------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------------ |
| #163  | SENINFO 公网地址入仓          | [!209](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/209) | config-ize-api-domains               | 三方 API 域名配置化；清理 `@Value` 内联默认值；webhook URL 去域名改路径拼接    |
| #164  | Gitee accessToken 走 URL 参数 | [!211](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/211) | fix-gitee-token-to-header            | 令牌改请求头；失败日志剥离凭证                                                 |
| #165  | PR 同步明文令牌入 MQ          | [!231](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/231) | feat/repo-token-api                  | MQS 去 `access_token`，改传引用；令牌经内部接口密文下发                        |
| #169  | Webhook 无时间戳/重放防护     | [!217](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/217) | security-webhook-replay-hardening    | 投递 ID 入口层（分钟级）+ 消费层（小时级）两层幂等；失败释放占位               |
| #172  | OBS 中转无大小限制            | [!220](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/220) | security-obs-transfer-hardening      | 元数据预检 + 计数流兜底 + 流式解析（上限 500MB 可配）                          |
| #173  | 文件明细接口缺失授权          | [!221](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/221) | fix-ut-coverage-file-detail-auth     | 补仓库维度归属校验（IDOR）                                                     |
| #176  | 去重锁 Redis 异常 fail-open   | [!223](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/223) | fix-webhook-dedup-redis-fallback     | 降级 `LocalDedupLock`（有界 + compute 原子 + 多实例窗口声明）                  |
| #177  | 端点缺失归属校验              | [!224](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/224) | fix-repo-owner-permission-check      | 分支列表/平台所有者查询补归属校验                                              |
| #179  | 写操作复用读菜单鉴权          | [!225](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/225) | fix-sync-repo-permission-anchor      | 切换为写菜单 URL 锚点（菜单已登记，无需平台数据变更）                          |
| #180  | CRLF 日志注入                 | [!226](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/226) | fix-crlf-log-injection-180           | 入口校验 + logback 输出层收口 + 逐点净化补充                                   |
| #181  | HMAC 非常量时间比较           | [!217](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/217) | security-webhook-replay-hardening    | `MessageDigest.isEqual`                                                        |
| #182  | API URL 拼接未编码            | [!227](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/227) | fix-api-client-url-encoding          | builder 分段编码，保持对外产出逐字等价                                         |
| #184  | 逐请求新建 OkHttpClient       | [!262](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/262) | fix-http-client-reuse-cleanup        | 复用静态 `CLIENT`；清理无调用方 RestTemplateConfig                             |
| #185  | MQ 消费者日志整包输出         | [!252](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/252) | fix-mq-consumer-log-security         | 脱敏器改"包含关键字"匹配，前缀式头名（X-Gitee-Token 等）同被遮盖               |
| #187  | Redis 键 hashCode 碰撞        | [!261](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/261) | fix_redis_token_cache_key_sha256     | `TokenDigestUtil.sha256Hex` 单一来源；旧键 TTL 过期                            |
| #194  | Token 变更日志含 token        | [!263](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/263) | fix-token-change-log-no-body         | 安全异常替代原始异常栈；截断报文遮盖；DTO 注释修正                             |
| #210  | pageSize 无上限/全量加载      | [!256](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/256) | fix-pagination-resource-abuse        | 5 链路收口；`JSON_TABLE`/`JSON_EXTRACT` 下推；键集分批                         |
| #211  | 大字段长度无校验              | [!266](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/266) | fix-issue211-text-length-guard       | `PayloadSizeConstants` 字节预算；Jackson 上限对齐                              |
| #223  | limit 拼接逻辑反向            | [!254](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/254) | fix-repo-query-limit-page-size       | LIMIT 条件改 `pageSize >= 1`，消除 pageSize=1 全表查询                         |
| #224  | 异常信息泄露                  | [!251](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/251) | fix-exception-message-leak           | 固定文案映射；原始异常仅落服务端日志                                           |
| #226  | 分页乘法 int 溢出             | [!255](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/255) | fix-pagination-int-overflow-226      | `PaginationUtil` long 偏移 + 夹取；DTO 补上限                                  |
| #239  | SSRF 白名单可绕过             | [!268](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/268) | fix-repo-address-whitelist-239       | `contains` → `protocol://host` 精确匹配                                        |
| #242  | Excel 公式注入                | [!267](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/267) | fix-issue242-excel-formula-injection | 33 列单元格敏感前缀前置 `'`                                                    |
| #245  | webhook 凭据头入 MQ           | [!269](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/269) | fix-webhook-header-credential-leak   | headerMap 剔除 4 个签名/令牌头，保留投递 ID                                    |
| #246  | XFF 可伪造操作者 IP           | [!271](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/271) | fix-issue246-remove-get-user-ip      | 删除死代码 `getUserIpAddress`；IP 采信移交 common `OperationLogClientIp`       |
| #263  | Webhook URL 路径段注入        | [!274](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/274) | fix_263_webhook_url_path_injection   | `WebhookUrlUtil` 统一构造 + 段级白名单 + 录入入口收紧（存量 1185 条 0 不合规） |

## 二、验证证据（汇总）

| 项       | 说明                                                                                                                                 |
| -------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 单元测试 | 各 PR 单测通过（!252 脱敏 24/24、!255 分页 339、!256 全量 1359、!266 相关 75、!274 定向 298、!262 受影响模块回归等）                 |
| 静态检查 | 各 PR pre-commit 全钩子通过（gitleaks / spotless / checkstyle / spotbugs / pmd）                                                     |
| 专项验证 | !253 中继 STARTTLS 实测（587 可协商 TLSv1.3）；!256 新增 SQL 测试库只读验证；!274 存量 repo_url 只读扫描；!242 转义单测覆盖 7 类前缀 |
| 测试结论 | 已合并问题逐项在 issue 评论区留有"修改方案"；#173/#177/#179 等附 BETA 验证结论（区分实测通过/未做独立测试）                          |
| 追溯性   | 26 项 issue 的 PR 描述均引用 FE 需求 openlibing-codecheck#372                                                                        |

## 三、暂不修复（登记接受，5 项）

| issue | 主题                                  | 处置                                     |
| ----- | ------------------------------------- | ---------------------------------------- |
| #174  | MQ 消费者重试耗尽死信不可达           | 需 MQ 平台侧死信能力配套，登记接受并跟踪 |
| #175  | pre-commit CI 检出 fork PR 不可信代码 | 属 CI 仓范围，转 CI 侧整改               |
| #178  | Docker 构建 JRE 动态下载未固定        | 属构建链路，转构建侧确认                 |
| #225  | swagger 生产暴露                      | 端点经网关、菜单受限，登记为加固项       |
| #252  | Mongo 主机名校验 / 非 prod MQ 明文    | 待环境侧 TLS 能力确认后另行评估          |

## 四、遗留事项

1. **#192（!253）在途**：需合入 `release_20261029_iter2` 并完成发信验证；上线前与运维确认各环境 SMTP 中继支持 STARTTLS。
2. **同源拷贝工具类**：codecheck `EmailUtil`、cicd `EmailHelper` 与 coderepo `EmailHelper` 为同一拷贝（#192 波及三仓），其余两仓需各自修复跟踪。
3. **网关侧协同**：安全响应头注入、转发头（XFF）清洗策略、机机接口登记与限流由 APIG 承担，不在本仓范围（对应 #237/#246 相关结论）。
4. **openlibing-common 侧**：操作日志 IP 采信逻辑（`OperationLogClientIp`）如需收紧应转 common 仓立项（#246 结论）。
5. **送检材料**：本 spec 目录与威胁分析报告、复扫结论一并作为 IT-ICSL 送检底稿提交。
