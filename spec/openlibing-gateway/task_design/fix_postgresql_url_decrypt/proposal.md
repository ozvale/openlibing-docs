# Proposal: Fix PostgreSql Health Check URL Not Decrypted

## Summary

修复 `MiddlewareHealthServiceImpl.checkPostgresHealth()` 中 PostgreSql 连接 URL 未走解密流程的 bug。配置中的 `postgre.url` 与 `postgre.password` 一样以加密形态存储，但健康检查只解密了密码，直接用明文 URL 连接导致健康检查失败。

## Motivation

### Bug 现象

PostgreSql 健康检查接口返回"PostgreSql连接异常"，但实际数据库服务正常、密码解密也正常。

### 根因分析

`checkPostgresHealth()` 中只对密码调用 `SecurityUtil.decrypt`：

```java
String decryptPassword = SecurityUtil.decrypt(postgrePassword, part1);
// ❌ postgreUrl 未解密，直接传入 DriverManager
try (Connection connection =
        DriverManager.getConnection(postgreUrl, postgreUser, decryptPassword);
    ...
```

实际配置中 `postgre.url` 也是密文（与 `postgre.password` 同样的加密约定），未解密直接用会导致 JDBC URL 非法，连接失败。

### 业务影响

- 中间件健康检查面板 PostgreSql 项始终报异常，误导运维
- 实际数据库可用性无法被正确监控

## Scope

### 修改文件（1 个）

| 文件                                                                                          | 说明                                                                                                             |
| --------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------- |
| `src/main/java/com/openlibing/gateway/business/service/impl/MiddlewareHealthServiceImpl.java` | `checkPostgresHealth()` 中对 `postgreUrl` 调用 `SecurityUtil.decrypt` 解密后再传入 `DriverManager.getConnection` |

### 不在范围内

- 不修改 `postgre.url` / `postgre.password` 配置加密方式
- 不修改 `SecurityUtil.decrypt` 实现
- 不修改其他中间件（Redis / RabbitMQ / Doris）健康检查逻辑
- 不调整 `part1` 密钥来源

## Fix Design

### 修复前

```java
String decryptPassword = SecurityUtil.decrypt(postgrePassword, part1);
try (Connection connection =
        DriverManager.getConnection(postgreUrl, postgreUser, decryptPassword);
    ...
```

### 修复后

```java
String decryptPassword = SecurityUtil.decrypt(postgrePassword, part1);
String decryptUrl = SecurityUtil.decrypt(postgreUrl, part1);
try (Connection connection =
        DriverManager.getConnection(decryptUrl, postgreUser, decryptPassword);
    ...
```

### 关键约束

- `part1` 密钥与密码解密共用，无新增密钥
- 解密失败时 `SecurityUtil.decrypt` 行为与密码解密一致（抛异常由外层 `catch (SQLException)` 兜底，返回"PostgreSql连接失败"）

## Risks

- 风险极低：仅对单条 URL 调用补一次解密，行为与同方法内密码解密完全对齐
- 仅影响 PostgreSql 健康检查路径，无外部接口契约变化

## References

- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/184
- 业务仓分支: `release_20260831_nacos`（fork: `codechentao/openlibing-gateway`）
- 注：本次 PR 按用户决定未关联业务 Issue
