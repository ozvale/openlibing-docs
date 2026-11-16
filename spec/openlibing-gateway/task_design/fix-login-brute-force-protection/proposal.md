# fix-login-brute-force-protection

## 背景

漏洞报告 openlibinggateway-20261103105553 L-0011 (argus-006)：`/login/gitee/account`
与 `/login/gitcode/token` 两个登录端点仅有非空校验与白名单准入，无失败次数限制，
可对白名单内账号无限次尝试密码/PAT 枚举。

## 修复方案

复用 UserServiceImpl 验证码失败计数的既有模式（get 阈值比对 / 首次 set+TTL /
后续 increase 不刷新窗口 / INCR 无 TTL 竞态补设），在 LoginServiceImpl 新增：

- `checkLoginFailureCount` / `setLoginFailureCount` / `clearLoginFailureCount`，
  Redis key `loginFailureCount_<platform>_<identity>`，窗口默认 60 分钟
- 配置项（带默认值，可配置中心覆盖）：`login.fail.count.limiter.number`（默认 5）、
  `login.fail.count.limiter.time`（默认 3600 秒）
- gitee 账密登录：**账号维度**计数，入口检查、认证失败/token 签发失败计数、
  成功清零
- gitcode PAT 登录：PAT 枚举发生在凭证校验前无法获知账号，**退化为平台级窗口**
  （解密失败/API 失败/白名单拒绝均计数，达到阈值暂停该平台 PAT 登录入口，
  窗口过期自动恢复）；成功清零

## 已知取舍

- PAT 平台级窗口存在 DoS 面：攻击者刷满失败次数可让白名单用户 PAT 登录暂停
  至窗口过期。接受原因：PAT 登录本身白名单 fail-closed 且低频，窗口自动恢复，
  不造成持久影响

## 验收标准

1. 失败次数达到阈值后，后续登录尝试直接拒绝且不再触发上游认证/解密
2. 认证失败计数落 Redis 并带窗口 TTL
3. 既有 LoginServiceImplTest 适配后全量通过
