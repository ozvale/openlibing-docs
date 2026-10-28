# Design: Fix PostgreSql Health Check URL Not Decrypted

## Context

`MiddlewareHealthServiceImpl` 负责对各中间件做健康检查，配置项（url/user/password）统一以加密形态存放在 Apollo/Nacos 配置中心，运行时由 `SecurityUtil.decrypt(cipher, part1)` 解密后使用。

PostgreSql 健康检查方法 `checkPostgresHealth()` 漏掉对 URL 的解密，导致 JDBC 连接失败。

## Bug Analysis

### 调用链路

```
MiddlewareHealthController
    ↓
MiddlewareHealthServiceImpl.checkHealth(MiddlewareType.POSTGRES)
    ↓
checkPostgresHealth()
    ↓
SecurityUtil.decrypt(postgrePassword, part1)   ← 只解密密码
    ↓
DriverManager.getConnection(postgreUrl, ...)   ← URL 未解密，连接失败
```

### 配置加密约定

| 配置项             | 存储形态 | 期望运行时处理                           |
| ------------------ | -------- | ---------------------------------------- |
| `postgre.url`      | 密文     | 解密后传给 `DriverManager.getConnection` |
| `postgre.user`     | 明文     | 直接使用                                 |
| `postgre.password` | 密文     | 解密后传给 `DriverManager.getConnection` |

修复前 URL 列错位为"明文直接使用"。

## Fix Design

### 方案选型

| 方案                                                  | 描述           | 优点               | 缺点                              |
| ----------------------------------------------------- | -------------- | ------------------ | --------------------------------- |
| A: 补一次 `SecurityUtil.decrypt(postgreUrl, part1)`   | 与密码解密对齐 | 最小改动、风格一致 | 无                                |
| B: 抽出 `decryptConfig(url, user, password)` 工具方法 | 统一配置解密   | 复用性好           | 超出本 bug 修复范围，引入无关重构 |

**选择方案 A**：最小改动，与本方法内密码解密写法完全对齐，符合 Light 模式修复原则。

### 修复后逻辑

```
1. Class.forName("org.postgresql.Driver")
2. decryptPassword = SecurityUtil.decrypt(postgrePassword, part1)
3. decryptUrl = SecurityUtil.decrypt(postgreUrl, part1)        ← 新增
4. DriverManager.getConnection(decryptUrl, postgreUser, decryptPassword)
5. statement.execute("select 1")
6. 返回"PostgreSql连接正常" / "PostgreSql连接失败"
```

## Exception Handling

保持原有异常处理逻辑不变：

- `ClassNotFoundException` → 返回"PostgreSql连接异常"
- `SQLException` → 返回"PostgreSql连接失败"
- `SecurityUtil.decrypt` 解密异常由外层 `catch (SQLException)` 兜底（解密失败时 `DriverManager.getConnection` 收到非法 URL 自然抛 `SQLException`）

## Verification

### 验证场景

| #   | 场景               | 操作                                       | 预期结果                 |
| --- | ------------------ | ------------------------------------------ | ------------------------ |
| 1   | 正常连接           | 配置正确加密的 `postgre.url`，触发健康检查 | 返回"PostgreSql连接正常" |
| 2   | URL 密文错误       | 配置错误密文，触发健康检查                 | 返回"PostgreSql连接失败" |
| 3   | 数据库不可达       | 配置正确但 PostgreSql 服务停止             | 返回"PostgreSql连接失败" |
| 4   | 其他中间件不受影响 | 触发 Redis / RabbitMQ / Doris 健康检查     | 行为不变                 |

## References

- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/184
