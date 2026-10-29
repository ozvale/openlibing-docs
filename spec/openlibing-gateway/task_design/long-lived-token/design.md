# long-lived-token — 技术设计

## 方案概述

Web 端复用既有插件端 refresh token 基础设施（30 天 JWT + Redis 加密存储 + 轮换校验），在正式用户会话确立时签发 `refresh_token` Cookie，`AuthFilter` 在 access 会话失效时静默换发，实现关浏览器后 30 天内免登录。

## 现状关键事实（编码依据）

| 事实                                                                                                                                                                    | 位置                                                                                                        |
| ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| access JWT：`generateUserJwtToken` 24h 有效（原 8h，`ca96ba7` 调整）；`generateJwtToken`（OAuth 过渡）30min                                                             | `JwtHelper.java`                                                                                            |
| token Cookie maxAge 30min，AuthFilter 每请求滑动续期                                                                                                                    | `AuthFilter.performAuthenticationChecks` / `JwtHelper.generateCookie`                                       |
| Redis token key：`token-{accountId}-{accountName}`，TTL 30min 滑动（拨测侧接口与 Web 共享此 key，单会话模型）                                                           | `AuthFilter.isValidToken`                                                                                   |
| Redis csrf key：`csrfToken{accountId}`，TTL 30min 滑动；csrf JWT 8h；客户端经 `Csrf-Token-Open-Li-Bing` 响应头获取并持久化                                              | `UserServiceImpl.generateAndSaveCsrfToken`                                                                  |
| 插件端 refresh token：30 天 JWT（refreshJwtSecret 签名，含全部用户 claims），加密存 Redis `pluginLoginRefresh-{accountId}-{accountName}`，换发时轮换 + Redis 比对防重放 | `LoginServiceImpl.generatePluginAuthByRefreshToken`                                                         |
| Web 会话确立点（签发 8h user JWT + token Cookie 的位置）                                                                                                                | `UserController.generateAndSetJwtToken`（check-account-bind 等）、`check-verification-code`、`modify-email` |
| CSRF 校验在 token 有效性校验**之前**，对过期 token 提取 claim 抛异常 → 误判为 CSRF → 401                                                                                | `AuthFilter.checkCsrfAttack`                                                                                |

## 架构决策

### D1：refresh token 与插件端共用签发/校验逻辑，但 Redis key 隔离

- 签发复用 `JwtHelper.getRefreshToken`（refreshJwtSecret 签名，claims 含 accountId/accountName/accountLogin/accountPlatform/加密三方 token/userId/userName/isSignPrivacyPolicy）。
- Redis key 使用新前缀 `webLoginRefresh-{accountId}-{accountName}`（`UserInfoConstants` 新增常量）。
- 原因：若与插件端共用 `pluginLoginRefresh-*`，任一端刷新轮换后另一端 Cookie 立即失配被踢下线；隔离后双端独立轮换互不影响。

### D2：静默刷新复用 `generatePluginAuthByRefreshToken` 的换发逻辑

- 该方法已实现：refresh JWT 验签/验期 → DB 查询最新用户数据（防 claims 陈旧）→ Redis 轮换比对防重放 → 签发新 user JWT + 轮换新 refresh token → 更新 Redis。
- 复用方式：将其中"校验 + 换发"核心提取为可复用方法（或直接调用原方法取返回 HashMap 中的 token/refreshedToken），Redis 存储的 refresh key 前缀按调用渠道区分。
- AuthFilter 拿到新 token 后：设置 `token` Cookie + 轮换后的 `refresh_token` Cookie + 调 `userService.generateAndSaveCsrfToken` 重建 CSRF 状态并写入响应头。

### D3：刷新触发条件与安全边界

触发条件（仅 Web Cookie 路径，插件 `plugin-token` header 路径不触发）：

1. `token` Cookie 缺失（浏览器 30min 已删）；
2. access JWT 过期（`TokenExpiredException`）；
3. JWT 有效但 Redis token key 过期（`isValidToken` 失败分支）；
4. JWT 有效但需 CSRF 校验的请求未携带任何 csrf 凭证（浏览器重启后 csrf Session Cookie 丢失；`4ec5994` 补充。csrf 信任列表内路径豁免，避免高频接口白白轮换 refresh token）。

不触发：JWT **签名非法**（防伪造 token 探测刷新通道，直接走既有 401；csrf 缺失判定位于验签之后，不影响该语义）。

### D4：触发刷新的请求跳过 CSRF token 校验、保留 referer host 校验

- 浏览器重启后 Redis csrf key（30min）已过期、客户端 csrf JWT（8h）可能已过期，静默刷新同时重建两者。
- 刷新请求本身不执行业务动作（仅轮换凭证到受害者自己的浏览器），攻击者无收益；跳过 csrf token 校验但**保留 referer host 精准匹配校验**，后续请求恢复完整 CSRF 校验。
- 实现上需将 AuthFilter 主流程中"CSRF → 有效性"的判定顺序调整为：先判定 token 状态（有效/过期/缺失/非法），过期或缺失先尝试刷新，再走 CSRF 与后续校验。

### D5：Cookie 细节

- `refresh_token` Cookie：HttpOnly、Secure、Path=/、domain 同 token Cookie、maxAge 30 天。
- `JwtHelper.generateCookie` 增加带 cookie name 参数的重载（现硬编码 `"token"`）。
- access `token` Cookie 保持 30min 滑动不变。

### D6：登出吊销

- `LoginController` 登出：删除 Redis `webLoginRefresh-*` key（轮换比对失配即吊销）+ 下发 maxAge=0 的 `refresh_token` Cookie 清除浏览器侧。
- 无 token Cookie 的极端场景（超 30min 后点登出）：至少清除 refresh Cookie；Redis key 待其自然过期或下次刷新失配。

### D7：轮换 60 秒宽限期（实现期新增，`a6e9360`）

- **问题**：SPA 首屏并发请求同时携带同一旧 refresh token，第一个轮换成功后其余请求 Redis 比对失配 → 401 洪流 → 前端 401 处理器触发 logout 连锁清除凭证 → 跳登录页。
- **方案**：轮换时旧 token 转入 `webLoginRefreshGrace-{accountId}-{accountName}` key（60 秒 TTL）；宽限期内旧 token 可换发新 access token + 重建 CSRF，但**不再轮换**，`refresh_token` Cookie 统一下发当前主凭证——并发请求全部成功且收敛到同一凭证。
- **安全权衡**：盗取 token 在轮换后 60 秒内仍可用一次（Auth0 等平台同款折衷）；宽限期外旧 token 依旧直接拒绝，防重放语义不变。宽限期内换发跳过 CSRF 校验，同时消除了 `clearCacheCredentials` 的连锁会话破坏。

### D8：refresh token 固定 30 天（实现期新增，`c1281e2`）

- 轮换获取新 access 时只换值、**不重置 TTL**：写回沿用主 key 剩余寿命（`getExpire` 取剩余 TTL，缺失时兜底满额 30 天避免轮换瞬间立即失效）。
- `refresh_token` Cookie maxAge 同步对齐 Redis 剩余寿命，服务端过期后浏览器无僵尸 Cookie。
- 语义：30 天内活跃完全无感，但第 30 天到期后必须重新登录——会话最长寿命有硬上限，凭证被窃取的利用窗口从"无限"收敛为"登录后 30 天"。

### D9：会话确立点全量覆盖（实现期新增，`71b5757`）

- 初版仅覆盖 `UserController` 三个会话确立点；实测发现主登录入口 **OAuth gitcode 回调**（`LoginServiceImpl.responseLoginInfo`）未签发 refresh token，导致重启浏览器后无凭证可换发。
- 修复：`responseLoginInfo` 成功路径新增 `establishWebLoginSession`——签发 30 天 refresh token（加密写 Redis + 持久化 Cookie）+ 重建 CSRF 状态（Redis + 响应头 `Csrf-Token-Open-Li-Bing`）。
- 未绑定开放平台账号的临时用户（无 userId）跳过签发，账号绑定时由既有接口补发。

### D10：access JWT 本体 8h → 24h（实现期新增，`ca96ba7`）

- `generateUserJwtToken` JWT exp 8h → 24h，减少"JWT 本体过期靠 refresh 兜底"的触发场景；静默刷新频率不变（仍由 30 分钟 Cookie 驱动）。csrf token（同 8h）不受影响。

## 涉及文件

| 文件                                          | 操作 | 说明                                                                                                                |
| --------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------- |
| `common/constants/UserInfoConstants.java`     | 修改 | 新增 `WEB_LOGIN_REFRESH`/`WEB_LOGIN_REFRESH_GRACE` key 前缀常量、`REFRESH_TOKEN` cookie 名常量                      |
| `common/utils/JwtHelper.java`                 | 修改 | `generateCookie` 增加带 cookie 名的重载；`verifyTokenAllowExpired` 区分过期/非法；`generateUserJwtToken` exp 8h→24h |
| `business/controller/UserController.java`     | 修改 | 会话确立点（generateAndSetJwtToken / check-verification-code / modify-email）签发 refresh token，新增私有 helper    |
| `business/filter/AuthFilter.java`             | 修改 | 静默刷新分支（缺失/JWT 过期/Redis 过期/csrf 缺失四触发 + 宽限期换发 + Cookie/CSRF 重建）+ 登出/轮换联动             |
| `business/controller/LoginController.java`    | 修改 | 登出清理 refresh 凭证                                                                                               |
| `business/service/impl/LoginServiceImpl.java` | 修改 | OAuth 回调 `responseLoginInfo` 新增 `establishWebLoginSession`（正式用户签发，临时用户跳过）                        |
| `src/test/java/...`（对应测试类）             | 修改 | 新增刷新成功/过期/重放/宽限期/非法签名/登出清理/Cookie 签发等用例                                                   |

## 风险 & 缓解

| 风险                                                                                       | 缓解                                                                                                                                                                           |
| ------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 前端未持久化静默刷新返回的新 CSRF header → 后续请求 401                                    | 实测闭环成立：落地页为首页，既有 `Content.vue` 逻辑已捕获响应头写入 Cookie；深链直达场景每个请求多一次刷新往返（功能可用、低效），列为后续优化项（ApiClient 响应链路统一捕获） |
| refresh token 泄露窗口 30 天                                                               | HttpOnly + Secure + Redis 轮换比对（旧 token 重放即失配，60 秒宽限期内除外）+ 登出即吊销 + 固定 30 天硬上限                                                                    |
| 触发刷新的请求跳过 csrf token 校验                                                         | 保留 referer host 精准校验；刷新无业务副作用；后续请求完整校验                                                                                                                 |
| AuthFilter 注入 LoginService/UserService 引入新依赖                                        | 与既有 AuthFilter 注入 Mapper/Helper 模式一致，构造器/字段注入遵循现状                                                                                                         |
| 同账号拨测 + Web 同时活跃：Web 静默换发轮换共享 `token-*` 会话 key → 拨测旧 token 失配 401 | 单账号单会话模型的固有语义（任何重新登录都会覆盖该 key）；拨测使用独立账号规避，或 401 后重新调拨测登录接口                                                                    |

## 跨仓影响

- 无业务跨仓代码改动。前端仓零改动闭环（深链捕获优化列为后续项）。
