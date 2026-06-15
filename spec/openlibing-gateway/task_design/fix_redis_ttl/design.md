# Design: Fix Redis Key TTL=-1 in setVerificationCodeFailureCount

## Bug Analysis

### 调用链路

```
LoginServiceImpl.verifyVerificationCode()
    ↓
UserServiceImpl.setVerificationCodeFailureCount(accountId, accountPlatform, type)
    ↓
RedisHelper.set(key, "0", 60min)     ← 设置带 TTL 的初始值
    ↓
RedisHelper.increase(key, 1)          ← INCR 清除 TTL → key 永不过期
```

### Redis INCR 与 TTL 交互机制

| 操作 | key 不存在时 | key 存在时 | 对 TTL 的影响 |
|------|-------------|-----------|--------------|
| `SET key value EX 3600` | 创建 key，TTL=3600s | 覆盖值，重设 TTL=3600s | 设置 TTL |
| `INCR key` | 创建 key=1，**TTL=-1** | 值+1，**TTL 不变** | 新 key 无 TTL；已有 key 保留 TTL |
| `SET key 0 EX 3600` → `INCR key` | — | 值=1，**TTL=-1** | INCR 清除 SET 设置的 TTL |

**关键发现**：Redis `INCR` 命令在 key 已存在时保留 TTL，但 `SET` + `INCR` 组合操作中，`INCR` 内部实现会重写 key 值，导致 `SET` 设置的 TTL 被清除。

### 根因确认

```java
// RedisHelper.increase() 实现
public Long increase(String key, long delta) {
    return stringRedisTemplate.opsForValue().increment(key, delta);
}
```

`increment()` 底层执行 Redis `INCRBY` 命令，该命令**不会保留/设置 TTL**。

## Fix Design

### 方案选型

| 方案 | 描述 | 优点 | 缺点 |
|------|------|------|------|
| A: set("1") + increase | 首次直接 set("1", ttl)，后续仅 increase | 简单、原子 | 无 |
| B: increase + expire | 先 increase，再 expire | 每次都刷新 TTL | 违反"不刷新过期时间"约束 |
| C: Lua 脚本 | 原子执行 INCR + 条件设置 TTL | 最严谨 | 过度设计，单方法不需要 |

**选择方案 A**：符合业务约束（60 分钟窗口不刷新），实现最简单。

### 竞态条件修复（v2 增强）

方案 A 的 v1 实现存在竞态条件：`get(key)` 返回值后，key 可能在进入 `else` 分支前过期，此时 `INCR` 会创建无 TTL 的新 key。

v2 增加竞态兜底：

```java
redisHelper.increase(key, 1);
// 防竞态：若key在get与increase之间过期，INCR会创建无TTL的key，需补设过期时间
if (redisHelper.getExpire(key) == -1L) {
    redisHelper.expire(key, ttl);
}
```

**为什么不用 Lua 脚本**：虽然 Lua 脚本可以原子解决，但需要新增 Redis 脚本管理，对单方法修复来说过度设计。`getExpire == -1` 的检查足够覆盖竞态场景，且性能影响可忽略（多一次 TTL 查询）。

### 修复后逻辑

```
首次失败 (key 不存在):
  redisHelper.set(key, "1", 60min)    ← 原子设置值和 TTL
  return true

后续失败 (key 已存在):
  redisHelper.increase(key, 1)         ← 仅递增，保留原有 TTL
  if getExpire(key) == -1:             ← 竞态兜底：key 在 get 与 increase 间过期
      redisHelper.expire(key, 60min)   ← 补设过期时间
  return true
```

### 时序图

```
时间轴:  0min        10min       30min       60min
         │           │           │           │
首次失败  set("1",60) │           │           │ key 过期清零
         TTL=60min   │           │           │
         │           │           │           │
第2次失败 │  increase→2           │           │
         │  TTL=50min(不刷新)    │           │
         │           │           │           │
第3次失败 │           │  increase→3           │
         │           │  TTL=30min(不刷新)    │
         │           │           │           │
         │           │           │    key 过期，计数归零
```

## Exception Handling

保持原有异常处理逻辑不变：

```java
catch (NumberFormatException | RedisConnectionFailureException e) {
    LOGGER.error("An error occurred while setting the number of verification code failures");
    return false;
}
```

## Verification

### 验证场景

| # | 场景 | 操作 | 预期结果 |
|---|------|------|---------|
| 1 | 首次失败 | 触发验证码校验失败 | key 值=1，TTL=60min |
| 2 | 后续失败 | 再次触发失败 | key 值=2，TTL 不刷新（<60min） |
| 3 | 过期清零 | 等待 60 分钟 | key 自动删除，重新计数从 1 开始 |
| 4 | Redis 异常 | 模拟 Redis 连接失败 | 返回 false，不抛异常 |
| 5 | 竞态条件 | `get` 返回值后 key 过期，`increase` 创建新 key | `getExpire == -1` 触发补设 TTL |

## References

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/104
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/143
