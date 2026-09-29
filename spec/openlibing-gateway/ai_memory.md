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

## 测试与加解密规则

### 纯 Mockito 测试类中的 @Value 注入

- 纯 Mockito 测试类（`@ExtendWith(MockitoExtension.class)` + `@InjectMocks`）没有 Spring 容器，被测类新增 `@Value` 字段后测试中该字段为 null，相关分支静默走默认路径
- 必须在 `setUp()` 中用 `ReflectionTestUtils.setField(被测实例, "字段名", 值)` 手动注入；为被测类新增 `@Value` 字段时应同步排查所有测试类

### AES-GCM 密文不可作等值比对依据

- `SecurityHelper` 底层 AES-GCM 使用随机 IV，同一明文每次加密结果不同（非确定性加密）
- 密文不能直接作为 Redis key 或等值比对依据；需要以密文定位/比对时，先对明文取 SHA-256 摘要（hutool `DigestUtil.sha256Hex`）
- 本仓 refreshToken JWT 无 `jti` claim，黑名单/审计场景以 token 明文摘要作为唯一标识

## 工程环境踩坑

### pre-commit 钩子

- `gitleaks` 为 Go 语言钩子，首次安装需从 go.dev 下载 Go 工具链，网络受限环境会阻塞所有提交；临时绕过用 `SKIP=gitleaks`，不应长期跳过
- `mvn-spotless` 钩子对整个项目执行格式化：远端合并引入的格式漂移（无关文件）会阻塞本次提交，合并远端后应第一时间单独提交一次全量格式化，避免阻塞后续提交
