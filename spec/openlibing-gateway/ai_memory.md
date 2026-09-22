# openlibing-gateway AI Memory

## Redis 使用规则

### INCR 与 TTL 交互
- Redis `INCR`/`INCRBY` 命令**不会保留 key 的 TTL**，执行后 key 的 TTL 会被清除为 -1（永不过期）
- 正确模式：首次用 `set(key, "1", ttl)` 原子设置值和 TTL；后续仅 `INCR` 递增，不重设 TTL
- 反模式：`set(key, "0", ttl)` + `increase(key, 1)` — INCR 会清除 set 设置的 TTL
- 如果业务要求"计数窗口从首次操作开始计时，后续操作不刷新 TTL"，必须走 get 判空 + 首次 set / 后续 increase 的分支逻辑

### get + increase 竞态条件
- `get(key)` + `increase(key)` 组合存在竞态：key 可能在 `get` 返回值后、`increase` 执行前过期
- 此时 `INCR` 在 key 不存在时创建新 key 且 TTL=-1
- 兜底方案：`increase` 后检查 `getExpire(key) == -1`，若为 -1 则补设 `expire(key, ttl)`
- 严格方案：使用 Redis Lua 脚本原子执行条件 INCR + 设置 TTL（适用于高并发场景）
