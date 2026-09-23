# Design: 插件登录客户端配置化与 refreshToken 轮换

## 1. 插件客户端白名单配置化

### 改造前

```java
// LoginUtil.java（硬编码）
private static final Set<String> ALLOWED_CLIENTS = Set.of("vscode", "idea", "agent_arena");
```

### 改造后

```
Apollo (login.allowed.clients = vscode,idea,agent_arena)
    ↓ @Value("${login.allowed.clients}") List<String>
LoginController.allowedClients
    ↓ 方法参数传入
LoginUtil.checkPluginLogin(clientId, redirectUri, state, allowedClients)
```

| 组件                         | 变更                                                                                                                                                       |
| ---------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `LoginController`            | 新增 `@Value("${login.allowed.clients}") private List<String> allowedClients` 字段，5 处 `checkPluginLogin` 调用统一传入                                   |
| `LoginUtil.checkPluginLogin` | 删除 `ALLOWED_CLIENTS` 常量，新增 `List<String> allowedClients` 参数（沿用本文件 `checkIpTrust` 的既有传参模式）；配置项小写化后匹配，兼容配置中心返回大写 |
| 空值语义                     | 列表为空/null 时返回 false（拒绝所有），安全失败                                                                                                           |

### 配置项

| 配置                    | 格式           | 默认                 | 说明                                                                                                     |
| ----------------------- | -------------- | -------------------- | -------------------------------------------------------------------------------------------------------- |
| `login.allowed.clients` | 逗号分隔字符串 | 无（缺失时启动失败） | Spring Boot 自动绑定到 `List<String>`；如需允许缺失可写 `${login.allowed.clients:}`（空列表 = 拒绝所有） |

## 2. refreshToken 轮换

### 流程

```
客户端 ──refreshToken──▶ generatePluginAuthByRefreshToken
                            │
                            ├─ ① JWT 签名校验（verifyrefreshToken）
                            ├─ ② Redis 比对：PLUGIN_LOGIN_REFRESH-{accountId}-{accountName}
                            │      解密存储值 == 传入 refreshToken？不等 → 拒绝
                            ├─ ③ 生成新短效 JWT token（30min，FIELD_TOKEN_TYPE key）
                            ├─ ④ 生成新 refreshToken（30 天）
                            └─ ⑤ 新 refreshToken 覆盖存储到 ② 的 key（30 天 TTL）
                                   → 旧 refreshToken 立即失效
```

### Redis key 设计

| Key                                              | 值                | TTL     | 写入方                          | 读取方           |
| ------------------------------------------------ | ----------------- | ------- | ------------------------------- | ---------------- |
| `FIELD_TOKEN_TYPE-{accountId}-{accountName}`     | 加密短效 JWT      | 30 分钟 | 登录/刷新路径                   | AuthFilter       |
| `PLUGIN_LOGIN_REFRESH-{accountId}-{accountName}` | 加密 refreshToken | 30 天   | 登录路径颁发 + 刷新路径轮换覆盖 | 刷新路径校验比对 |

### 设计权衡

- **为什么用"单 key 覆盖"而非黑名单**：实现简单，旧 token 失效即时且确定。
- **已知局限**：单 key 意味着同一用户多客户端登录时，后登录客户端轮换会使先登录客户端的 refreshToken 失效（互踢）。若未来需要多客户端并存，应改为黑名单模式（轮换时将被替换 token 的 SHA-256 摘要写入 `*-revoked-<sha256>` 废弃缓存，校验时查黑名单）。该方案已在 develop 分支原型验证，未纳入本批发布。
- JWT 本身无 `jti` claim，AES-GCM 加密为随机 IV 非确定性，故不能以加密结果作 key，黑名单方案需先取摘要。

## 3. uniportal 用户同步修复

### 查询策略（checkUniportalUserInfo）

```
accountLogin 查询 → 命中 → 走更新
       ↓ 未命中
accountId 查询 → 命中 → 走更新（修复点：原先直接新增，产生重复记录）
       ↓ 未命中
新增入库
```

### Mapper 变更（ThreePartyUserInfoMapper.xml）

`updateThreePartyUserInfo` uniportal 分支 WHERE 从 `account_login = #{...}` 扩展为 `(account_id = #{...} or account_login = #{...})`。

### 方法拆分

邮箱自动绑定逻辑抽取为 `bindUniportalUserEmail` 独立方法（G.MET.01：方法不超过 50 行），行为不变。

## 4. 影响范围

| 文件                           | 变更类型                                     |
| ------------------------------ | -------------------------------------------- |
| `LoginController.java`         | 新增配置字段 + 传参                          |
| `LoginUtil.java`               | 方法签名变更                                 |
| `LoginServiceImpl.java`        | 刷新路径校验 + 轮换；uniportal 查询/更新逻辑 |
| `UserInfoConstants.java`       | 新增 `PLUGIN_LOGIN_REFRESH` 常量             |
| `ThreePartyUserInfoMapper.xml` | uniportal 更新 WHERE 扩展                    |
| `pom.xml`                      | bcprov-jdk18on 1.85.2                        |
| 对应 3 个测试类                | 用例适配 + 新增覆盖                          |

## 5. 风险与部署依赖

1. **Apollo 必须先行发布** `login.allowed.clients`（如 `vscode,idea,agent_arena`），否则应用启动失败。
2. 刷新校验依赖 Redis 中 `PLUGIN_LOGIN_REFRESH` key，颁发 refreshToken 的所有登录入口必须写入该 key——本批已覆盖插件登录路径。
3. 升级部署瞬间，存量 refreshToken 不在 Redis 中（旧版本未写），首次刷新会被拒绝，用户需重新登录。属一次性影响。
