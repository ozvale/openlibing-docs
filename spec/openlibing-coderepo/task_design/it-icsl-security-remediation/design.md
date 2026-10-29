# Design：【openLiBing】ICSL安全送检排查及整改（openlibing-coderepo 侧）

## 1. 方案设计

### 1.1 总体思路：分层治理 + 批次收敛 + 可复检

按"问题发生的链路位置"分六层收口，同一层内的问题合并处置，避免逐条打补丁造成口径漂移：

| 层                | 治理目标                                                              | 覆盖 issue                                           |
| ----------------- | --------------------------------------------------------------------- | ---------------------------------------------------- |
| L1 暴露面收敛     | 不需要对外可见的能力关闭/出仓                                         | #163（域名配置化）                                   |
| L2 入口校验       | 不可信输入在 DTO/入口层拦截                                           | #180、#239、#242、#263、#226、#210、#211             |
| L3 鉴权收口       | 资源类入参回查归属；写操作独立权限锚点                                | #173、#177、#179                                     |
| L4 数据安全       | 凭据全链路最小化：只走 Header、跨服务只传引用、日志/MQ/异常三出口脱敏 | #164、#165、#182、#185、#187、#192、#194、#224、#245 |
| L5 容量与拒绝服务 | 上限 + 流式 + 资源复用                                                | #172、#210、#211、#226、#184                         |
| L6 健壮性基线     | 外部失败不改写状态、失败终态可自愈、事件幂等可重放防护                | #169、#176、#181                                     |

### 1.2 关键设计决策

| 决策                          | 内容                                                                                                                                             | 依据                                                                              |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| 确定性错误码按平台实测        | 仅平台明确 `401` 判凭据失效；`403`（已认证未授权）、限流、5xx、无响应一律按取数失败保留原状态                                                    | #243 修复过程实测：403 语义含限流/风控/scope/角色不足，据此判失效会把瞬时故障固化 |
| 脱敏分层防线                  | 入口 `@Pattern` 拒绝控制字符 + 日志输出层 `%maskMsg` 统一替换为主防线；应用层逐点 `sanitize` 仅作补充                                            | #180/#185/#194：逐点包裹必然漏点（`X-Gitee-Token` 不在精确白名单内即漏）          |
| 路径统一分段编码 + 段级白名单 | 出站 URL 一律 `ApiUrlUtil`/`WebhookUrlUtil` 分段编码；org/repo/hookId 先过 `isLegalSegment` 字符白名单；禁止 `String.format` 拼路径              | #182、#263：`contains` 子串匹配与裸拼接均可被构造输入绕过                         |
| 凭据只传引用                  | MQ 消息体不携带明文令牌（改传 repoId 按需获取）；webhook 事件 headerMap 剔除签名/令牌头（仅保留投递 ID）                                         | #165、#245：下游消费点只用投递 ID，凭据驻留 MQ 属不必要暴露                       |
| 降级方向按语义选择            | 一次性语义（防重放 nonce）fail-closed；幂等去重语义（webhook 重复投递）可降级本地内存锁（有容量上界 + 原子更新 + 下游幂等兜底 + 声明多实例窗口） | #176：Redis 异常时一律 fail-open 会重复触发扫描评论与携带 token 的 MQS 消息       |
| 两层 TTL 职责分离             | 入口层去重分钟级（拦重试风暴，不影响人工重发恢复）；消费层幂等小时级（不重复执行业务）                                                           | #169/#176                                                                         |
| 状态与派生字段同写            | 状态置无效/不可用时，过期时间、权限范围同写占位符；失败终态仍在复核范围内（可自愈）                                                              | #243：避免"状态无效但过期时间有效"矛盾数据与永久误判                              |

### 1.3 交付批次

- **Batch 1（合入 `release_20261019_iter1`，11 个 PR）**：!209 / !211 / !217 / !220 / !221 / !223（iter2）/ !224 / !225 / !226 / !227 / !231；
- **Batch 2（合入 `release_20261029_iter2`，14 个 PR）**：!251 / !252 / !254 / !255 / !256 / !261 / !262 / !263 / !266 / !267 / !268 / !269 / !271 / !274；
- **在途（1 个 PR）**：!253（#192 SMTP STARTTLS）。

## 2. 实现逻辑设计

### 2.1 凭据与敏感数据传输/存储/展示全链路（L4）

- **#163（!209）**：三方 API 域名（gitee/gitcode/github）从代码提取到配置中心，清理 `@Value` 内联默认值；webhook URL 常量去域名改路径后缀，运行期与配置基址拼接。
- **#164（!211）**：Gitee 出站 `access_token` 由 URL 查询参数改为请求头传递；失败路径日志记录 URL 前先剥离凭证。
- **#165（!231）**：MQS 消息体移除明文仓库 `access_token`，改由消费方按需通过内部接口获取（令牌经时间戳窗口 + 一次性 nonce + 签名验签，ECDH 协商后密文下发）。
- **#182（!227）**：三平台 API 客户端 URL 用 builder 的路径段/查询参数 API 编码；替换手工编码保持对外产出逐字等价（`addEncodedPathSegment`）。
- **#185（!252）**：`SensitiveDataConverter` 由精确 key 白名单改为包含关键字匹配（`token`/`password`/`secret`/`privatekey`，前后缀有界 64 字符防回溯），使 `X-Gitee-Token`、`X-GitCode-Token` 等前缀式头名同样被 `****` 打码；固化误打码边界用例（`tokenCount`）。
- **#187（!261）**：令牌校验 Redis 缓存键由 `accessToken.hashCode()` 改为 SHA-256 派生（新增 `TokenDigestUtil` 单一来源），旧键按 10 分钟 TTL 自然过期。
- **#194（!263）**：Token 变更消息解析失败时，异常栈改为"固定文案 + 原始堆栈"的安全异常（fastjson2 异常 message 会拼接完整报文）；脱敏正则去掉闭合引号 lookahead，截断报文同样遮盖；修正 DTO 中 token 字段"明文"的错误注释（实际为密文）。
- **#224（!251）**：`DataResult.failureMessage(e.getMessage())` 各处改为固定文案映射，原始异常作为 cause 仅落服务端日志；补"不泄露临时文件绝对路径"单测。
- **#245（!269）**：Webhook 入口 headerMap 移除 `X-Gitee-Token`、`X-GitCode-Token`、`X-Gitee-Timestamp`、`X-Hub-Signature-256`，保留投递 ID 等非敏感头；鉴权仍在入口由 `WebhookAuthUtil` 直接读 `HttpServletRequest`。
- **#192（!253，在途）**：`EmailHelper` 增加 `mail.smtp.starttls.enable=true` + `mail.smtp.starttls.required=true`（强制 STARTTLS，避免静默降级明文）；已实测中继 `smtp.exmail.qq.com` 587 支持 STARTTLS。

### 2.2 鉴权与越权（L3）

- **#173（!221）**：`POST /ut/coverage/file-detail` 补齐仓库维度对象级授权校验（网关注入 userId + repoId → projectId 回查 + 横向权限校验），消除 IDOR 与存在性探测。
- **#177（!224）**：`/project-repo/query-repo-branchList`、`/project-repo/query-platform-owner` 补归属校验，消除"鉴权参数存在但未生效"的假象。
- **#179（!225）**：`sync-repo` / `sync-repo-branch` 写型操作由复用读菜单 URL（`REPO_QUERY`）切换为各自已登记的写菜单 URL 锚点，无需新增菜单数据。

### 2.3 注入与输入校验（L2）

- **#180（!226）**：CRLF 日志注入分层防线落地——入参控制字符校验 + logback 输出层 `%replace(%maskMsg)` 收口 + 应用层 `LogSanitizer` 覆盖已知点（与 SpotBugs 12 处告警同批，!212）。
- **#239（!268）**：`checkRepoAddress` 由"配置值 contains 待校验值"子串匹配改为 `protocol://host` 忽略大小写精确匹配；保留 gitcode 平台对 `gitcode.com`/`atomgit.com` 的 host 精确放行。
- **#242（!267）**：Excel 导出 `setCellValue` 写入前统一 `escapeFormulaInjection`（覆盖 33 列），对以 `=`、`+`、`-`、`@`、制表符、回车、换行开头的值前置英文单引号；内部占位符 `--` 不转义。
- **#263（!274）**：新增 `WebhookUrlUtil` 统一仓库级平台 API 出站 URL 构造（org/repo/hookId 先过 `isLegalSegment` 白名单再分段编码，非法拒绝并记 SECURITY 告警）；webhook list/create/delete/update 全部替换 `String.format` 拼接；`checkRepoAddress` 增加 `isLegalRepoUrlPath`（拒绝 query/fragment/userInfo、双点/单点段、百分号编码）；存量 `repo_info.repo_url` 只读扫描 1185 条 0 不合规，无需清洗。

### 2.4 拒绝服务与资源上限（L5）

- **#172（!220）**：OBS 下载增加双重防护——元数据 `contentLength` 预检 + 计数复制兜底（实际流量超限中止并清理临时文件），上限 `obs.download.max-size-mb`（默认 500MB，`@RefreshScope` 动态生效）；UT 覆盖率上报改两遍 Jackson 流式解析，不再全量读内存。
- **#210（!256）**：5 条链路全部收口——`pageSize` 限制 1~200；文件/函数级明细过滤排序分页下推 MySQL（`JSON_EXTRACT`/`JSON_TABLE`），LONGTEXT 不再整段载入；`staticAlertCount` 排序改键集分批 + 有界 top-N；filter-meta 改 SQL `DISTINCT + LIMIT`；分支列表改键集分批取数。
- **#211（!266）**：写入上限集中定义在 `PayloadSizeConstants`（按列类型与 `max_allowed_packet` 预算推导）：`error_message` 超 4000 字符截断；`snapshot_data`/`coverage_file_detail_json` 超 48MB 丢弃或拒绝上报；重复块按累计 32MB 切批；`content_b64` 单块超 16MB 跳过。
- **#226（!255）**：新增 `PaginationUtil`（long 计算偏移 + 边界夹取，页码越界返回空列表），替换 4 处 int 乘法内存分页；4 个分页 DTO 补 `@Max(100000)` / `@Range(1,200)`。
- **#184（!262）**：`HttpRequestUtil` 5 处逐请求 `new OkHttpClient()` 改复用静态共享 `CLIENT`（主体改动 master `8eec114c`）；清理无调用方的 `RestTemplateConfig`。

### 2.5 Webhook 安全基线与幂等（L6）

- **#169 / #181（!217）**：HMAC 比较改常量时间（`MessageDigest.isEqual`）；按平台投递 ID（`X-GitCode-Delivery` / `X-GitHub-Delivery`）做入口层 SET NX EX 幂等去重（分钟级）+ 消费层幂等标记（小时级）；鉴权通过后才占用去重键；投递失败释放占位保证平台重试可入队。
- **#176（!223）**：去重锁 Redis 异常由 fail-open 改为降级 `LocalDedupLock`（容量上界 10000、`compute` 原子更新、超限清过期/重置、多实例窗口在类注释显式声明），事件不丢弃、单实例内重复投递仍被拦截。

## 3. 类设计

| 模块      | 类                                                 | 动作                                                      |
| --------- | -------------------------------------------------- | --------------------------------------------------------- |
| 常量/配置 | `WebhookDeliveryConstants`                         | 去重/消费两层 TTL 与 key 前缀                             |
|           | `PayloadSizeConstants`（新增）                     | 大字段写入上限单一来源                                    |
| 工具类    | `HttpRequestUtil`                                  | 客户端复用、CRLF 净化、URL 构造                           |
|           | `ApiUrlUtil` / `WebhookUrlUtil`（新增）            | 出站 URL 分段编码与段级白名单                             |
|           | `LocalDedupLock`（新增）                           | 本地内存降级去重锁                                        |
|           | `PaginationUtil`（新增）                           | 分页偏移 long 计算与夹取                                  |
|           | `TokenDigestUtil`（新增）                          | 令牌相关 Redis 键 SHA-256 派生                            |
|           | `SensitiveDataConverter`                           | 关键字包含匹配 + 截断报文遮盖                             |
|           | `LogSanitizer`                                     | 逐点净化（补充防线）                                      |
| 鉴权      | `RepoTokenAuthFilter`                              | 内部接口验签、解码后路径匹配                              |
| Service   | `RepoServiceImpl`                                  | 归属校验、权限锚点、白名单精确匹配、固定文案、webhook URL |
|           | `UtCoverageServiceImpl` / `CodeMetricsServiceImpl` | 流式解析、分页下推、上限校验、固定文案                    |
|           | `ObsBucketServiceImpl`                             | 下载大小上限与计数流兜底                                  |
|           | `EmailHelper`                                      | STARTTLS 强制（在途）                                     |
| Webhook   | `WebHookEventController` / `WebhookEventConsumer`  | headerMap 去凭据头、投递 ID 幂等                          |
|           | `MergeRequestEventHandler` / `PrSyncEventHandler`  | 缓存键强哈希、降级本地锁                                  |
| 导出      | `RepoExportDelegateImpl`                           | 公式注入转义                                              |

## 4. 数据模型设计

无新增表、无 Schema 变更。涉及：

| 项                        | 变更                                                                              | 备注                                          |
| ------------------------- | --------------------------------------------------------------------------------- | --------------------------------------------- |
| Redis 令牌校验缓存键      | 由 `hashCode()` 派生改为 SHA-256 派生                                             | 旧键按 10 分钟 TTL 自然过期，无需迁移（#187） |
| Redis webhook 去重键      | 新增入口层 `webhook:delivery:dedup:` 与消费层 `webhook:delivery:consumed:` 两类键 | 分钟级 / 小时级两层 TTL（#169）               |
| 存量 `repo_info.repo_url` | 无需清洗                                                                          | 只读扫描 1185 条，0 条不合规（#263）          |

## 5. 性能设计

- **客户端复用**（#184）：消除逐请求 `new OkHttpClient()`，复用 OkHttp 默认连接池，降低 PR 事件高频调用下的握手与线程开销。
- **分页下推**（#210/#226）：文件/函数级明细与 UT 明细的过滤、排序、分页下推 MySQL（`JSON_TABLE`/`JSON_EXTRACT`），大字段不再整段载入；键集分批 + 有界 top-N 替代全量加载。
- **流式与上限**（#172/#211）：OBS 下载流式落盘 + 计数流兜底；上报解析两遍流式；字段级字节预算避免 `max_allowed_packet` 超限。
- **降级结构有界**（#176）：本地去重锁容量上界 10000，超限先清过期再整体重置。
- **脱敏输出层收口**（#185/#194）：`%maskMsg` 单点正则替换，有界量词限制回溯开销。

## 6. API接口设计

无新增对外接口；本次整改涉及的契约变化（供前端/调用方核对）：

| 接口/入口                                                                                                                 | 变化                                                                             | 适配方                   | 状态                |
| ------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------ | ------------------- |
| `/ut/coverage/file-detail`                                                                                                | 新增网关注入 `userId` 并真正参与归属校验                                         | 前端无感                 | 已合并（!221）      |
| `/project-repo/query-platform-owner`                                                                                      | 补齐 `userId` 归属校验                                                           | 前端无感                 | 已合并（!224）      |
| `/project-repo/query-repo-branchList`                                                                                     | `userId` 校验真正生效                                                            | 确认前端传本人 userId    | 已合并（!224）      |
| `/project-repo/sync-repo`、`/sync-repo-branch`                                                                            | 鉴权锚点切换为写菜单 URL                                                         | 权限配置侧已登记菜单     | 已合并（!225）      |
| 分页类接口（`/metrics/code/file-detail`、`/ut/coverage/file-detail`、`/project-repo/query-repo`、`/repo/branch/list` 等） | `pageSize` 限制 1~200、`pageNum` 上限 100000，超限返回参数校验失败；响应结构不变 | 前端校验提示按既有口径   | 已合并（!255/!256） |
| 仓库录入（页面新增 / `external/add-repo`）                                                                                | `repoUrl` 拒绝 query/fragment/userInfo、双点/单点段、空格与百分号编码路径        | 录入方（含外部对接）需知 | 已合并（!274）      |
| 异常返回文案                                                                                                              | `e.getMessage()` 改为固定文案（如"获取资源信息失败，请联系运维人员处理"）        | 前端若有文案依赖需确认   | 已合并（!251）      |
| 导出文件                                                                                                                  | 敏感前缀单元格前置 `'`（内容形态微调）                                           | 无                       | 已合并（!267）      |

## 7. 安全设计

整改后形成的安全基线：

1. **鉴权**：资源类入参一律"回查归属 + 横向校验"；写操作独立权限锚点并已登记菜单；网关注入 `userId` 为唯一身份来源；内部/机机接口应用层验签 + 时间窗 + 一次性 nonce（fail-closed）+ 按解码后路径匹配。
2. **凭据流转**：只走请求头；MQ 只传引用（webhook 事件剔除签名/令牌头，仅保留投递 ID）；凭证加密下发不回显；缓存键强哈希（SHA-256）。
3. **输出安全**：日志分层防线（入口拒绝 + 输出层替换）；异常消息固定文案；富文本按渲染容器转义；出站 URL 分段编码 + 路径段白名单 + host 精确匹配。
4. **传输安全**：SMTP 强制 STARTTLS（#192 在途）；非 prod MQ / Mongo 主机名校验等待环境侧确认后另行评估（#252 登记接受）。
5. **容量与降级**：分页/文本/批量/文件四类上限明确，超限明确报错；降级方向按语义（一次性 fail-closed / 幂等可降级本地锁并声明多实例窗口）；外部失败不改写确定性状态、失败终态可自愈。
6. **Webhook 基线**：常量时间比较 + 投递 ID 两层幂等（入口分钟级 / 消费小时级）+ 去重占位晚于鉴权 + 失败路径释放占位。
7. **暴露面**：三方地址配置化、公网地址出仓；swagger 暴露与 Mongo/MQ 加密套件登记为接受项跟踪。
