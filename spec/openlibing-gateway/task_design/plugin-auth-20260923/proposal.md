# Proposal: 插件登录客户端配置化与 refreshToken 轮换安全增强

## 背景

openlibing-gateway 插件登录链路存在三个问题：

1. **插件客户端白名单硬编码**：`LoginUtil` 中 `ALLOWED_CLIENTS = Set.of("vscode", "idea", "agent_arena")` 写死在代码里，新增客户端必须发版，无法通过配置中心动态调整。
2. **refreshToken 无轮换机制**：通过 refreshToken 换发短效 token 时，旧 refreshToken 原样回传且无失效手段。refreshToken 有效期长达 30 天，一旦泄露，攻击者可在整个有效期内反复换发短效 token，服务端无法撤销。
3. **uniportal 用户同步产生重复记录**（随本批合入）：`checkUniportalUserInfo` 仅按 `accountLogin` 查询，用户更换账号名（accountId 不变、accountLogin 变化）时会插入重复用户记录。

## 需求范围

| #   | 需求                   | 验收标准                                                                                                                             |
| --- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | 插件客户端白名单配置化 | 白名单从配置中心（Apollo）`login.allowed.clients` 读取，逗号分隔；大小写不敏感匹配保持不变；列表为空时拒绝所有插件登录               |
| 2   | refreshToken 轮换      | 换发短效 token 时校验传入 refreshToken 与 Redis 存储值一致；校验通过后生成新 refreshToken 并覆盖存储；旧 refreshToken 因被覆盖而失效 |
| 3   | uniportal 同步修复     | accountLogin 优先、accountId 兜底查询，均未命中才新增；更新语句 WHERE 覆盖 account_id or account_login                               |

## 非目标

- 不实现 refreshToken 黑名单/jti 撤销机制（多客户端并发登录场景另行评估）
- 不改造 Gitee 账号登录、GitCode PAT 登录路径的 refreshToken 存储行为

## 关联交付

- 业务 PR：https://gitcode.com/openlibing/openlibing-gateway/pull/203
- 关联 commit：`ef65431`（需求 1+2）、`b76dd09`（需求 3）、`e8059ae`（bcprov-jdk18on 1.85.2 依赖升级）
