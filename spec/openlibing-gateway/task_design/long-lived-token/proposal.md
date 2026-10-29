# long-lived-token（登录认证优化：支持长令牌免频繁登录）

## 需求背景

当前 Web 端会话由 `token` Cookie（maxAge 30 分钟）+ 8h 有效期 access JWT 构成，随请求滑动续期，但存在两个掉线场景：

1. 浏览器关闭超过 30 分钟后 Cookie 被删除，重新打开必须重新登录；
2. 距上次登录超过 8 小时后 access JWT 本体过期，即使会话活跃也必须重新登录。

参考 Gitee 平台体验：关闭浏览器后，只要长效令牌仍在有效期内，再次访问无需重新登录。

## 功能描述

**做什么**：

- Web 登录建立正式用户会话时，同步签发 30 天长效 refresh token：
  - 加密存储到 Redis（独立 key 前缀 `webLoginRefresh-*`，与插件端 `pluginLoginRefresh-*` 隔离，避免双端轮换互踢）；
  - 以 `refresh_token` Cookie 下发（HttpOnly、Secure、Path=/、30 天 maxAge）。
- `AuthFilter` 支持静默刷新：access 会话失效（token Cookie 缺失 / JWT 过期 / Redis token key 过期 / 需 CSRF 校验的请求未携带 csrf 凭证）时，用 refresh token 自动换发新会话，用户无感。
- refresh token 固定 30 天：从登录时刻起算，轮换获取新 access 时只换值、不重置 TTL，持续活跃也无法超过 30 天，到期必须重新登录。
- 首屏并发竞态容忍：轮换后旧 refresh token 进入 60 秒宽限期，宽限期内可换发新 access 但不再轮换，SPA 首屏并发请求全部收敛到同一凭证。
- 登出时吊销：删除 Redis web refresh key + 清除 `refresh_token` Cookie。

**不做什么**：

- 不改插件端刷新逻辑（`generatePluginAuthByRefreshToken` 对外行为不变，仅被复用）；
- 不做"记住我"勾选框（登录即发，Gitee 同款默认行为）；
- 不改前端仓代码（实测后端闭环成立：落地页为首页，既有 Content.vue 逻辑已捕获刷新响应的 CSRF header；深链直达场景为已知低效边界，每个请求会多一次刷新往返，列为后续优化项）；
- OAuth 回调（`responseLoginInfo`）对正式用户同步签发 refresh token（主登录入口必须覆盖）；未绑定开放平台账号的临时用户不签发，账号绑定时由既有接口补发。

## 验收标准

- [x] 登录后存在 `refresh_token` Cookie（HttpOnly、Secure、30 天）与 Redis `webLoginRefresh-{accountId}-{accountName}` key（OAuth 回调、账号绑定、验证码校验、邮箱变更四个会话确立点全覆盖）
- [x] 关闭浏览器静置超过 30 分钟（token Cookie 已删、Redis token key 已过期）后访问，自动换发新会话，无需登录
- [x] access JWT 超过 24h 过期后访问，自动换发，无需登录
- [x] 需 CSRF 校验的请求未携带 csrf 凭证时触发换发（浏览器重启后 csrf Session Cookie 丢失场景）
- [x] 首屏并发请求携带同一旧 refresh token 时，宽限期内全部换发成功且收敛到同一新凭证，无 401 洪流
- [x] 每次换发后 refresh token 轮换，旧 refresh token 重放被拒绝（Redis 比对失配；宽限期 60 秒内除外）
- [x] 轮换沿用主 key 剩余 TTL，不重置 30 天（固定时长语义，持续活跃也无法超过登录起算 30 天）
- [x] 签名非法的 token 不触发刷新，直接 401
- [x] 登出后 refresh token 立即失效（Redis key 删除 + Cookie 清除）
- [x] 插件端 token header 路径不触发 Web 静默刷新
- [x] 拨测侧接口（gitee 账密 / gitcode PAT 登录）契约零变化，其 `token-*-refresh` Redis 体系与 Web `webLoginRefresh-*` 完全隔离
- [x] 相关单元测试全绿，既有测试无回归（全量 1567+ 用例 0 失败）

## 影响范围

- 业务仓：`openlibing-gateway`（auth 链路单模块，无外部接口契约变化、无数据模型变化、无跨仓代码改动）
- 前端仓：零改动闭环。已知低效边界：非首页落地/深链刷新时刷新响应头无人捕获，每个请求多一次刷新往返（功能可用），后续可在 ApiClient 响应链路统一捕获 CSRF header 优化

## 交付提交（develop_202610_iter2 分支）

| commit    | 内容                                       |
| --------- | ------------------------------------------ |
| `bd10a31` | 会话确立点签发 refresh token + 登出吊销    |
| `4ec5994` | csrf 凭证缺失触发静默刷新                  |
| `71b5757` | OAuth 回调主登录入口纳入会话确立           |
| `a6e9360` | 轮换 60 秒宽限期解决首屏并发竞态           |
| `c1281e2` | refresh token 固定 30 天（轮换不重置 TTL） |
| `ca96ba7` | access token JWT 本体有效期 8h → 24h       |
