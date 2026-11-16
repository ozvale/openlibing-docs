# design: fix-oauth-bind-state-session

## 方案（漏洞报告方案一：state 关联 cookie token hash）

发起绑定时将 `userId|SHA256(token)` 存入 Redis；回调时从回调请求 cookie 取 token 计算摘要，
与 Redis 存储摘要常量时间比对。通过则取 `|` 前的 userId 作为绑定目标，否则 403 拒绝。

回调 URL 与 token cookie 同域（均由网关 8073 提供），第三方 302 回跳时浏览器会携带 token cookie，
方案可行（与报告分析一致）。

## 改动点（LoginController.java）

1. 常量 `BIND_STATE_VALUE_SEPARATOR = "|"`。
2. `buildBindStateValue(userId, tokenValue)`：生成 `userId|sha256(token)`。
3. `sha256Hex(value)`：JDK `MessageDigest` + `HexFormat` 实现摘要（不用 Spring `DigestUtils`，
   因测试 classpath 可能解析到 spring-core 5.3.25，无 SHA-256 方法）。
4. `resolveBindUserId(request, stateValue)`：解析存储值、比对回调 cookie 摘要
   （`MessageDigest.isEqual` 常量时间），通过返回 userId，否则 null（fail-closed：
   无 `|` 分隔、无 token cookie、摘要不一致均拒绝）。
5. 5 处绑定发起（uniportal/openubmc/gitee/gitcode/github）：
   `redisHelper.set(state, userId, 30, MINUTES)` → `redisHelper.set(state, buildBindStateValue(userId, tokenCookie.getValue()), 30, MINUTES)`。
6. 5 处绑定回调 bind 分支：`openLiBingUserId = stateValue` →
   `resolveBindUserId(request, stateValue)`，null 时 403 + warn 日志并终止。
   prManages redirect 分支位于该校验之后，同样受保护。

## 测试（LoginControllerTest.java）

- 新增 `stubCallbackTokenCookie(tokenValue)`、`bindStateValue(userId, tokenValue)` 两个测试 helper。
- 5 个平台 `bindCallback_usesStateValueAsUserId` 适配新格式（stub cookie + `userId|hash`）。
- 每平台新增 `bindCallback_sessionMismatch_rejected`：cookie 为攻击者 token，断言 403 且
  `platformAccountBindCallback` 未被调用。

## 影响范围

- 不改 LoginService/ThreePartyHelper/Mapper；绑定落库链路不变。
- 不影响登录/插件登录 state（`PLATFORM_*_LOGIN`/`PLATFORM_*_PLUGIN` 值格式不变）。
- 兼容性：发布窗口内（≤30min TTL）旧格式 state 的在途绑定会 403 失败，用户重试即可，可接受。
