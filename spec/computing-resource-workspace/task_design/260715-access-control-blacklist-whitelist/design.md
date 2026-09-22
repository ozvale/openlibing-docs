# 260610-access-control-blacklist-whitelist — 设计文档

## 1. 需求概述

在现有鉴权拦截器（`OpenlibingAuthInterceptor` + `MaasAuthInterceptor`）基础上，增加黑白名单机制，实现：

- **白名单**：允许访问的账号-IP 组合，不在白名单则拒绝
- **黑名单**：禁止访问的账号或 IP，在黑名单则拒绝
- **MaaS 联合校验**：apikey 对应的账号 + 请求 IP 的联合合法性（账号-IP 绑定判断）
- **前端管理**：黑白名单的增删改查，前端展示用户名而非 userId
- **校验接口**：供前端和内部调用的合法性校验接口
- **差异化错误提示**：不同拦截原因返回不同错误信息

## 2. 现状分析

### 2.1 现有鉴权拦截器

| 拦截器 | 路径 | 用户信息来源 | IP 来源 |
|--------|------|------------|---------|
| `OpenlibingAuthInterceptor` | `/api/maas/**`, `/api/project/**`, `/api/monitor/**`（排除 `/api/maas/v1/**`） | JWT → `OpenlibingUserInfo(userId, userName, ...)` | 远程 get-user-info API 返回的 `currentLoginIp`（可信），fallback 为 `X-Forwarded-For` → `RemoteAddr` |
| `MaasAuthInterceptor` | `/api/maas/v1/**` | API Key → `ApiKeyVo(userId, userName, projectId, ...)` | `X-Real-IP` → `RemoteAddr`（经 APIG，可信） |

### 2.2 现有白名单机制（需移除）

当前 `OpenlibingAuthInterceptor` 有一个基于配置的白名单（`lingshu.test.whitelist`），用于：
- 本地开发模式下识别用户
- 生产环境无 Token 时的 fallback

**本次改造需移除此白名单机制**。原因：
1. 访问控制白名单将由数据库表管理，不再使用配置文件
2. 无 Token 请求应直接拒绝（返回 401），不再 fallback 放行
3. 本地开发时也会携带 Token，不需要特殊处理

移除范围：
- `lingshu.test.whitelist` 配置项
- `isJwtEnabled` 配置项及 `handleLocalDev()` 整个分支
- `isWhitelistedUser()` 方法
- `cachedWhitelist` / `whitelistCacheTime` 缓存字段
- `handleProduction()` 中无 Token 时白名单放行逻辑

### 2.3 IP 获取方式

两个拦截器的 IP 来源不同，但都是可信的：

| 拦截器 | IP 来源 | 可信原因 |
|--------|--------|---------|
| `OpenlibingAuthInterceptor` | get-user-info 远程 API 返回的 `currentLoginIp` | 来自认证系统，非客户端伪造 |
| `MaasAuthInterceptor` | `X-Real-IP` → `RemoteAddr` | 经 APIG 网关，APIG 覆写为真实来源 IP |

**注意**：`OpenlibingAuthInterceptor` 的 `getClientIp()` 方法使用 `X-Forwarded-For` 最后一个 IP，这个在安全场景下不可信（可伪造）。但实际使用中，`resolveUserInfo()` 会优先从远程 API 获取 `currentLoginIp`，`getClientIp()` 仅作为 fallback。对于访问控制校验，应使用 `OpenlibingUserInfo.clientIp()` 字段（优先来自远程 API），而非直接调用 `getClientIp(request)`。

### 2.4 用户信息缓存与访问控制的关系

`OpenlibingAuthInterceptor` 的 `resolveUserInfo()` 流程中存在 Redis 缓存：

```
请求 → JWT 解析 → resolveUserInfo()
  ├── 1. 查 Redis 缓存（key: user:info:{userId}，TTL 300s）
  │     ├── 命中 → 使用缓存的 userInfo（含 clientIp）
  │     └── 未命中 → 调用远程 get-user-info API
  │           ├── 成功 → 写入缓存 + 使用返回的 userInfo（含 currentLoginIp）
  │           └── 失败 → fallback 使用 JWT 基本信息 + getClientIp(request)
  └── 2. ensureClientIp()：如果 clientIp 为空，用 getClientIp(request) 补充
```

**缓存内容**：userId, userName, accountId, accountName, accountPlatform, accountLogin, clientIp

**对访问控制的影响**：

| 场景 | 影响 | 处理方式 |
|------|------|---------|
| 缓存命中 | clientIp 来自缓存，可能是 300s 前的登录 IP | 可接受：IP 黑白名单校验允许短暂延迟 |
| 缓存未命中 + 远程成功 | clientIp 来自远程 API 的 currentLoginIp | 最准确 |
| 缓存未命中 + 远程失败 | clientIp 来自 `X-Forwarded-For`（不可信） | **风险**：不可信 IP 参与安全决策 |

**风险处理**：当远程 API 不可用且缓存未命中时，`clientIp` fallback 为 `X-Forwarded-For`，此 IP 不可信。访问控制校验应考虑此场景：
- 方案 A：IP 黑白名单校验仍使用 fallback IP，接受风险（简单，但可能被伪造 IP 绕过）
- 方案 B：远程 API 不可用时跳过 IP 相关校验，仅做账号黑白名单校验（安全，但降低了防护）
- 方案 C：远程 API 不可用时，仅使用 `RemoteAddr`（TCP 连接 IP，可信但可能是代理 IP）

**采用方案 C（已实现）**：`resolveTrustedClientIp()` 的 fallback 逻辑为 `X-Real-IP` -> `RemoteAddr`。经 spec `260602-maas-clientip-recording` 测试验证（commit `0d3f261b`），APIG 部署下 `X-Real-IP` 由 APIG 覆写为真实来源 IP（可信），`RemoteAddr` 与 `X-Real-IP` 一致（可信），`X-Forwarded-For` 原样透传可伪造（不可信，不参与安全决策）。loopback 地址归一为 `127.0.0.1`。

**已确认**：远程 API 不可用时的 IP fallback 策略采用方案 C（`X-Real-IP` -> `RemoteAddr`）。实际场景中远程 API 基本不会不可用，此策略仅作为兜底。

## 3. 整体架构

### 3.1 核心流程

```
请求进入
  │
  ├── /api/maas/v1/** ──→ MaasAuthInterceptor
  │     │
  │     ├── 1. 提取 API Key，验证有效性（现有逻辑）
  │     ├── 2. 获取 clientIp（X-Real-IP → RemoteAddr，可信）
  │     ├── 3. 从 ApiKeyVo 获取 userId / userName
  │     ├── 4. 【新增】调用 AccessControlService.check(userId, clientIp)
  │     │     ├── 白名单检查：账号-IP 组合是否在白名单内
  │     │     │   ├── 不在白名单 → 抛出 AccessControlException(NOT_IN_WHITELIST)
  │     │     │   └── 在白名单 → 继续
  │     │     ├── 账号黑名单检查 → 在黑名单 → 抛出 AccessControlException(ACCOUNT_BLACKLISTED)
  │     │     ├── IP 黑名单检查 → 在黑名单 → 抛出 AccessControlException(IP_BLACKLISTED)
  │     │     └── 通过 → 继续
  │     └── 5. 设置 MaasAuthContext（现有逻辑）
  │
  └── 非 /api/maas/v1/** ──→ OpenlibingAuthInterceptor
        │
        ├── 1. JWT 解析（移除白名单 fallback，无 Token 直接 401）
        ├── 2. 获取 userId / clientIp（clientIp 优先来自远程 API 的 currentLoginIp）
        ├── 3. 触发 UserInfoSyncService.syncOnRequest()（异步同步用户信息，userName 变更时顺带回填黑白名单和管理员表）
        ├── 4. 【新增】调用 AccessControlService.check(userId, clientIp)
        │     ├── 跳过 `/access/check` 路径（该接口需返回结构化结果，不抛异常）
        │     ├── 白名单检查：账号-IP 组合是否在白名单内
        │     │   ├── 不在白名单 → 抛出 AccessControlException(NOT_IN_WHITELIST)
        │     │   └── 在白名单 → 继续
        │     ├── 账号黑名单检查 → 在黑名单 → 抛出 AccessControlException(ACCOUNT_BLACKLISTED)
        │     ├── IP 黑名单检查 → 在黑名单 → 抛出 AccessControlException(IP_BLACKLISTED)
        │     └── 通过 → 继续
        └── 5. 设置 UserContext（现有逻辑）
```

### 3.2 判断优先级

```
1. 白名单检查 → 不在白名单 → 拒绝（NOT_IN_WHITELIST）
2. 账号黑名单检查 → 在黑名单 → 拒绝（ACCOUNT_BLACKLISTED）
3. IP 黑名单检查 → 在黑名单 → 拒绝（IP_BLACKLISTED）
4. 通过
```

**设计决策**：白名单和黑名单不互斥，两者独立检查。先判断白名单，再判断黑名单。一个用户可以同时在白名单和黑名单中，但黑名单优先级高于白名单——即"在白名单但也在黑名单"的情况，应被拦截。

### 3.3 MaaS 联合校验（账号-IP 绑定）

对于 `/api/maas/v1/**` 接口，白名单的语义是**账号-IP 绑定判断**：

- 白名单中一条记录 = 一个「账号 + IP」组合
- 请求过来时，从 API Key 解析出 userId，从请求头获取 IP
- 判断「userId + IP」这个组合是否在白名单中
- 如果不在白名单，说明这个组合不合法（可能是其他人盗用了 API Key，或从不允许的 IP 发起请求）

这意味着：
- 同一个用户可以从多个 IP 访问，只要每个「用户-IP」组合都在白名单中
- 白名单中 IP 字段支持 `*`（所有 IP）和 CIDR（网段）
- 黑名单仍然是独立的：账号黑名单和 IP 黑名单分别判断

### 3.4 白名单为空时的行为

当白名单表为空（没有任何记录）时，**允许所有请求通过**。

理由：
1. 系统初始部署时白名单为空，拒绝所有会导致无法配置
2. 白名单是"允许层"，空则不限制；黑名单是"拒绝层"，两者配合使用
3. 后续可考虑增加配置开关切换为"默认拒绝"模式（需超级管理员机制配合）

## 4. 数据模型

### 4.1 核心概念：userId、账号、三方账号

| 概念 | 说明 | 前端可见性 | 存储字段 |
|------|------|-----------|---------|
| userId | openLiBing 统一用户 ID（如 `u-20250601xxxx`） | 不可见，前端不使用 | `user_id` |
| 账号（userName） | openLiBing 用户名（如"张三"） | 可见，前端主要展示 | `user_name` |
| 三方账号（accountLogin） | 三方平台登录名（如 GitCode 的 `zhangsan`） | 可见，添加用户时搜索用 | 不在黑白名单表中，通过搜索接口查询 |

**关键设计**：
- 黑白名单表使用 `user_id` 和 `user_name` 字段，与现有表（如 `workspace_user_info`）命名风格一致
- 前端所有操作使用 `user_name`（用户名）展示和搜索，后端负责 userName → userId 的转换
- 添加用户时，前端通过搜索接口输入关键字，后端从 `workspace_user_info` 表查询匹配的用户，返回 userId + userName + accountLogin 供选择

### 4.2 表设计

#### 4.2.1 `workspace_access_whitelist`（白名单表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT AUTO_INCREMENT | 主键 |
| `user_id` | VARCHAR(128) | userId |
| `user_name` | VARCHAR(128) | 用户名（展示用） |
| `account_platform` | VARCHAR(64) | 三方平台（添加时快照，NULL） |
| `account_login` | VARCHAR(128) | 三方登录名（添加时快照，NULL） |
| `ip_pattern` | VARCHAR(256) | IP 匹配模式：具体 IP / `*` / CIDR 网段 |
| `created_by` | VARCHAR(64) | 操作人 userName |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

**索引**：
- `uk_whitelist_user_ip` UNIQUE (`user_id`, `ip_pattern`) — 同用户同 IP 模式唯一
- `idx_whitelist_user_id` (`user_id`)

**ip_pattern 说明**：

| ip_pattern 值 | 含义 | 匹配逻辑 |
|---------------|------|---------|
| `*` | 该用户所有 IP 都允许 | 任何 IP 都匹配 |
| `10.0.0.0/24` | 10.0.0.0/24 CIDR 网段 | CIDR 匹配 |
| `192.168.1.100` | 具体 IP | 精确匹配 |

**匹配优先级**：精确 IP > CIDR 网段 > 通配符 `*`。同一用户有多条匹配时，取最精确的。

**不支持简单通配符**（如 `10.0.0.*`），CIDR 已能覆盖网段场景。

#### 4.2.2 `workspace_access_blacklist`（黑名单表）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | BIGINT AUTO_INCREMENT | 主键 |
| `target_type` | VARCHAR(16) | 目标类型：`ACCOUNT` / `IP` |
| `target_id` | VARCHAR(128) | userId（ACCOUNT 类型）或 IP 地址（IP 类型） |
| `target_name` | VARCHAR(128) | 用户名（ACCOUNT 类型）或 IP 备注（IP 类型） |
| `account_platform` | VARCHAR(64) | 三方平台（ACCOUNT 类型添加时快照，NULL） |
| `account_login` | VARCHAR(128) | 三方登录名（ACCOUNT 类型添加时快照，NULL） |
| `reason` | VARCHAR(512) | 封禁原因 |
| `expires_at` | DATETIME NULL | 过期时间，NULL 表示永久 |
| `created_by` | VARCHAR(64) | 操作人 userName |
| `created_at` | DATETIME | 创建时间 |
| `updated_at` | DATETIME | 更新时间 |

**索引**：
- `uk_blacklist_target` UNIQUE (`target_type`, `target_id`) — 同类型同目标唯一
- `idx_blacklist_expires` (`expires_at`) — 用于清理过期记录

**说明**：
- 黑名单的 `target_type` 有 `ACCOUNT` 和 `IP` 两种
- 黑名单的 IP 是精确 IP，不支持通配符和 CIDR（封禁场景需要精确控制影响范围）
- 黑名单支持过期时间，过期后自动失效
- 黑名单的 `target_type` 区分两种类型，因为 ACCOUNT 类型存储 userId/user_name，IP 类型存储 IP 地址/备注，字段语义不同

**过期记录清理**（后续实现，当前版本查询时过滤即可）：
- 查询时过滤 `expires_at IS NULL OR expires_at > NOW()`
- 后续可增加定时任务清理过期记录

### 4.3 缓存设计

黑白名单数据量预期较小（百级别），但查询频率高（每个请求），需要缓存。

**缓存策略**：
- Redis 缓存，TTL 60s
- Key 格式：
  - `access:whitelist` → `List<WhitelistEntry>` （全量缓存，数据量小）
  - `access:blacklist:ACCOUNT` → `Set<userId>`
  - `access:blacklist:IP` → `Set<ip>`
- 增删改时主动失效缓存

**白名单匹配逻辑**：
- 从缓存获取全量白名单
- 按 `user_id` 过滤出当前用户的记录
- 遍历该用户的所有 `ip_pattern`，按优先级匹配当前 IP
- 无匹配 → 不在白名单

**降级**：Redis 不可用时，直接查库（带本地内存缓存 30s），不阻断请求。

## 5. 核心类设计

### 5.1 AccessControlService

```java
@Service
public class AccessControlService {

    /**
     * 校验访问合法性
     *
     * @param userId 用户ID
     * @param clientIp 客户端IP
     * @throws AccessControlException 如果校验不通过
     */
    public void check(String userId, String clientIp) {
        // 1. 白名单检查（账号-IP 绑定）
        if (!isWhitelistEmpty() && !isInWhitelist(userId, clientIp)) {
            throw AccessControlException.notInWhitelist(userId, clientIp);
        }
        // 2. 账号黑名单检查
        if (userId != null && isInAccountBlacklist(userId)) {
            throw AccessControlException.accountBlacklisted(userId);
        }
        // 3. IP 黑名单检查
        if (clientIp != null && isInIpBlacklist(clientIp)) {
            throw AccessControlException.ipBlacklisted(clientIp);
        }
    }

    /**
     * 查询访问合法性（不抛异常，返回结果）
     * 供校验接口使用
     */
    public AccessControlResult checkAccess(String userId, String clientIp) {
        // 返回结构化结果而非抛异常
    }

    /**
     * 白名单匹配
     * 账号-IP 绑定判断：查找该用户的所有白名单记录，匹配 IP
     */
    private boolean isInWhitelist(String userId, String clientIp) {
        List<WhitelistEntry> entries = getWhitelistEntriesForUser(userId);
        if (entries.isEmpty()) {
            return false;
        }
        return entries.stream().anyMatch(e -> IpPatternMatcher.matches(clientIp, e.getIpPattern()));
    }
}
```

### 5.2 IpPatternMatcher（IP 模式匹配）

```java
public class IpPatternMatcher {

    /**
     * 判断 IP 是否匹配 ip_pattern
     *
     * @param ip 具体 IP 地址
     * @param pattern IP 模式：* / CIDR / 具体 IP
     * @return 是否匹配
     */
    public static boolean matches(String ip, String pattern) {
        if ("*".equals(pattern)) {
            return true;
        }
        if (pattern.contains("/")) {
            return matchesCidr(ip, pattern);
        }
        return ip.equals(pattern);
    }

    private static boolean matchesCidr(String ip, String cidr) {
        // CIDR 匹配逻辑，含 prefixLength 0-32 范围校验
        // 无效前缀（如 /33、/-1、/64）返回 false
    }
}
```

### 5.3 AccessControlResult

```java
public record AccessControlResult(
    boolean allowed,
    AccessControlDenyReason denyReason,
    String denyMessage,
    String denyTarget
) {
    public enum AccessControlDenyReason {
        NOT_IN_WHITELIST,       // 账号-IP 组合不在白名单
        ACCOUNT_BLACKLISTED,    // 账号在黑名单
        IP_BLACKLISTED          // IP 在黑名单
    }
}
```

### 5.4 AccessControlException

```java
public class AccessControlException extends RuntimeException {
    private final AccessControlResult.AccessControlDenyReason reason;

    // 工厂方法
    public static AccessControlException notInWhitelist(String userId, String ip) { ... }
    public static AccessControlException accountBlacklisted(String userId) { ... }
    public static AccessControlException ipBlacklisted(String ip) { ... }
}
```

### 5.5 拦截器改造

**OpenlibingAuthInterceptor**：
1. 移除 `lingshu.test.whitelist` 相关逻辑
2. 移除 `isJwtEnabled` 配置项及 `handleLocalDev()` 分支（本地开发也携带 Token）
3. 无 Token 请求直接返回 401
4. 在用户信息解析完成后，增加 `AccessControlService.check()` 调用

**MaasAuthInterceptor**：
1. 在 API Key 验证通过后、设置 `MaasAuthContext` 前，增加 `AccessControlService.check()` 调用

**关键决策**：黑白名单校验应在鉴权成功之后执行，因为需要先获取到 userId 和 IP 才能判断。校验失败直接抛出 `AccessControlException`。

### 5.6 拦截器注册顺序

当前顺序不变：`MaasAuthInterceptor` → `OpenlibingAuthInterceptor` → `AuthInterceptor` → 限流

黑白名单校验嵌入各拦截器内部，不改变注册顺序。

## 6. 错误处理

### 6.1 错误码与消息

| 场景 | HTTP 状态码 | 错误码 | 错误消息 | MaaS error_type |
|------|-----------|--------|---------|----------------|
| 不在白名单 | 403 | `ACCESS_DENIED_NOT_IN_WHITELIST` | "您的账号或IP不在访问白名单内，请联系管理员" | `permission_error` |
| 账号黑名单 | 403 | `ACCESS_DENIED_ACCOUNT_BLACKLISTED` | "您的账号已被封禁，如有疑问请联系管理员" | `permission_error` |
| IP 黑名单 | 403 | `ACCESS_DENIED_IP_BLACKLISTED` | "您的IP已被封禁，如有疑问请联系管理员" | `permission_error` |
| 无 Token | 401 | `UNAUTHORIZED` | "未登录，请先登录" | `authentication_error` |

### 6.2 不同接口的错误格式

**管理接口**（非 `/api/maas/v1/**`）：

```json
{
  "code": 403,
  "msg": "您的账号已被封禁，如有疑问请联系管理员"
}
```

**MaaS 接口**（`/api/maas/v1/**`）：

OpenAI 格式：
```json
{
  "error": {
    "message": "您的账号已被封禁，如有疑问请联系管理员",
    "type": "permission_error",
    "code": 403
  }
}
```

Anthropic 格式：
```json
{
  "type": "error",
  "error": {
    "type": "permission_error",
    "message": "您的账号已被封禁，如有疑问请联系管理员"
  }
}
```

**实现方式**：`AccessControlException` 为独立异常类，在 `GlobalExceptionHandler` 中新增处理分支，复用 `writeMaasFormatError()` 的格式化逻辑。

### 6.3 Coding Agent 错误格式

Coding Agent 通过 MaaS API 调用，错误格式与普通 MaaS 接口一致（OpenAI/Anthropic 格式），不需要额外处理。

## 7. 校验接口设计

### 7.1 管理接口校验

```
GET /api/admin/access/check
```

**请求参数**：无（从当前请求的 Token/Cookie 解析 userId，从远程 API 获取 IP）

**权限要求**：已登录用户即可访问（不需要管理员权限）

**说明**：此接口不受 `OpenlibingAuthInterceptor` 中访问控制检查的影响（拦截器对 `/access/check` 路径跳过 `check()` 调用），因此即使当前用户被黑名单拦截，此接口仍能正常返回结构化结果，而非 403 错误。

**响应**：

```json
{
  "code": 200,
  "data": {
    "isAllowed": true,
    "denyReason": null,
    "denyMessage": null,
    "denyTarget": null
  }
}
```

或拒绝时：

```json
{
  "code": 200,
  "data": {
    "isAllowed": false,
    "denyReason": "ACCOUNT_BLACKLISTED",
    "denyMessage": "您的账号已被封禁，如有疑问请联系管理员",
    "denyTarget": "u-20250601xxxx"
  }
}
```

**说明**：前端调用此接口时携带自己的 Token/Cookie，后端通过鉴权拦截器解析出 userId 和 IP，然后执行访问控制校验并返回结果。前端无需传入 userId 或 IP 参数。此接口不需要管理员权限，因为前端在应用初始化时需要判断当前用户是否被拦截，普通用户也需要调用。

### 7.2 MaaS 接口校验

不单独提供接口。MaaS 接口的访问控制校验已嵌入 `MaasAuthInterceptor` 中，每次请求自动执行。无需额外暴露校验接口，因为不存在外部调用方需要主动查询的场景。

## 8. 前端管理接口

> 所有接口仅使用 GET 和 POST 方法（网关会拦截 PUT/DELETE 请求），与现有接口风格一致。
> 管理接口路径前缀为 `/api/admin/access/`，由 `AdminAuthInterceptor` 校验 `@RequireAdmin` 权限。
> 校验接口路径为 `/api/admin/access/check`，不需要管理员权限。

### 8.1 白名单管理

| 操作 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 查询列表 | GET | `/api/admin/access/whitelist` | 返回全部记录，按创建时间倒序 |
| 添加 | POST | `/api/admin/access/whitelist` | |
| 更新 | POST | `/api/admin/access/whitelist/{id}/update` | 更新 IP 规则或用户名 |
| 删除 | POST | `/api/admin/access/whitelist/{id}/delete` | |

> **设计变更说明**：原设计含"分页查询"接口，实际实现中简化：
> - 数据量预期百级别，暂不需要分页，直接返回全量列表

**查询响应**：

```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "userId": "u-20250601xxxx",
      "userName": "张三",
      "ipPattern": "*",
      "createdBy": "u-admin",
      "createdAt": "2026-06-10T10:00:00",
      "updatedAt": "2026-06-10T10:00:00"
    }
  ]
}
```

**添加请求体**（统一使用三方账号信息，与 addMembers 一致；由 `AccountUserResolverService` 解析 userId）：

```json
{
  "accountPlatform": "gitcode",
  "accountLogin": "zhangsan",
  "userName": "张三",
  "ipPattern": "*"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| accountPlatform | 是 | 三方平台 |
| accountLogin | 是 | 三方登录名 |
| userName | 否 | 用户名（展示用，不填时后端从用户表抓取） |
| ipPattern | 是 | IP 规则 |

> **设计变更（合并自 260727）**：原设计前端传 userId，改为传 accountPlatform + accountLogin，后端通过 `AccountUserResolverService` 调用 `FrameworkUserQueryService` 解析 userId 并同步 user_info。

**更新请求体**：

```json
{
  "userName": "张三",
  "ipPattern": "10.0.0.0/24"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| userName | 否 | 用户名（传空或不传则不修改） |
| ipPattern | 否 | IP 规则（传空或不传则不修改；修改时校验同用户下是否重复） |

### 8.2 黑名单管理

| 操作 | 方法 | 路径 | 说明 |
|------|------|------|------|
| 查询列表 | GET | `/api/admin/access/blacklist` | 返回全部记录，按创建时间倒序 |
| 添加 | POST | `/api/admin/access/blacklist` | |
| 更新 | POST | `/api/admin/access/blacklist/{id}/update` | 更新封禁原因、过期时间等 |
| 删除 | POST | `/api/admin/access/blacklist/{id}/delete` | |

> **设计变更说明**：同白名单，简化了分页接口。

**查询响应**：

```json
{
  "code": 200,
  "data": [
    {
      "id": 1,
      "targetType": "ACCOUNT",
      "targetId": "u-20250601xxxx",
      "targetName": "张三",
      "reason": "违规使用",
      "expiresAt": "2026-12-31T23:59:59",
      "createdBy": "u-admin",
      "createdAt": "2026-06-10T10:00:00",
      "updatedAt": "2026-06-10T10:00:00"
    },
    {
      "id": 2,
      "targetType": "IP",
      "targetId": "192.168.1.100",
      "targetName": null,
      "reason": "异常访问",
      "expiresAt": null,
      "createdBy": "u-admin",
      "createdAt": "2026-06-10T10:00:00",
      "updatedAt": "2026-06-10T10:00:00"
    }
  ]
}
```

**添加请求体**（ACCOUNT 类型用 accountPlatform + accountLogin，IP 类型保持 targetId）：

```json
{
  "targetType": "ACCOUNT",
  "accountPlatform": "gitcode",
  "accountLogin": "zhangsan",
  "targetName": "张三",
  "reason": "违规使用",
  "expiresAt": "2026-12-31T23:59:59"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| targetType | 是 | `ACCOUNT` 或 `IP` |
| targetId | 否 | IP 类型时为 IP 地址（仅精确 IP）；ACCOUNT 类型不传 |
| accountPlatform | ACCOUNT 必填 | 三方平台（ACCOUNT 类型） |
| accountLogin | ACCOUNT 必填 | 三方登录名（ACCOUNT 类型） |
| targetName | 否 | ACCOUNT 时不填则后端从用户表抓取；IP 类型忽略此字段 |
| reason | 否 | 封禁原因 |
| expiresAt | 否 | 过期时间（ISO 8601），不填表示永久 |

> **设计变更（合并自 260727）**：ACCOUNT 类型原设计传 targetId(userId)，改为传 accountPlatform + accountLogin，后端通过 `AccountUserResolverService` 解析 userId 作为 targetId 存储。IP 类型保持原 targetId 逻辑不变。

**删除**：`POST /api/admin/access/blacklist/{id}/delete`

**更新请求体**：

```json
{
  "targetName": "张三",
  "reason": "违规使用，延长封禁",
  "expiresAt": "2027-06-30T23:59:59"
}
```

| 字段 | 必填 | 说明 |
|------|------|------|
| targetName | 否 | 目标名称（传空或不传则不修改） |
| reason | 否 | 封禁原因（传空或不传则不修改） |
| expiresAt | 否 | 过期时间（传空或不传则不修改；传 null 表示永久封禁） |

### 8.3 用户搜索接口（后续实现，当前仅设计）

前端添加账号白名单/黑名单时，通过此接口搜索用户。前端输入关键字，后端从 `workspace_user_info` 表查询匹配的用户。

```
GET /api/admin/access/user-search?keyword=张三
```

**响应**：

```json
{
  "code": 200,
  "data": [
    {
      "userId": "u-20250601xxxx",
      "userName": "张三",
      "accountLogin": "zhangsan"
    }
  ]
}
```

**搜索范围**：userName（模糊匹配）+ accountLogin（模糊匹配），支持三方平台账号搜索。

**限制**：最多返回 20 条结果，避免大量数据返回。

## 9. 拦截器改造细节

### 9.1 OpenlibingAuthInterceptor 改造

**移除内容**：
- `whitelistConfig` 配置项（`lingshu.test.whitelist`）
- `isJwtEnabled` 配置项及 `handleLocalDev()` 整个分支
- `cachedWhitelist` / `whitelistCacheTime` 缓存字段
- `isWhitelistedUser()` 方法
- `handleProduction()` 中无 Token 时白名单放行逻辑

**新增内容**：
- 注入 `AccessControlService`
- 无 Token → 返回 401（不再放行）
- 用户信息解析完成后，增加访问控制检查

```java
// 现有逻辑：解析用户信息
UserContext.OpenlibingUserInfo userInfo = resolveUserInfo(basicInfo, request);

// 【新增】访问控制检查
accessControlService.check(userInfo.userId(), userInfo.clientIp());

// 现有逻辑：设置上下文
UserContext.setOpenlibingUser(userInfo);
UserContext.setJwtResolved(true);
```

**clientIp 来源**：`userInfo.clientIp()` 优先来自远程 API 的 `currentLoginIp`，fallback 为 `resolveTrustedClientIp(request)`（`X-Real-IP` -> `RemoteAddr`，可信）。访问控制使用 `userInfo.clientIp()` 即可。

### 9.2 MaasAuthInterceptor 改造

在 API Key 验证通过后、设置 `MaasAuthContext` 之前，插入访问控制检查：

```java
// 现有逻辑：验证 API Key
DataResult<ApiKeyVo> result = apiKeyService.verifyApiKey(keySha256);
// ... 验证失败处理
ApiKeyVo apiKeyVo = result.getData();
String clientIp = resolveClientIp(request);

// 【新增】访问控制检查
accessControlService.check(apiKeyVo.getUserId(), clientIp);

// 现有逻辑：设置上下文
MaasAuthContext.set(apiKeyVo, apiKeyVo.getUserName(), clientIp);
```

**clientIp 来源**：`X-Real-IP` → `RemoteAddr`（经 APIG，可信）。

## 10. 涉及文件清单

### 10.1 新增文件

| 文件 | 说明 |
|------|------|
| `db/changelog/v1.0.0/workspace-access-control.xml` | Liquibase 建表 |
| `entity/AccessWhitelist.java` | 白名单实体 |
| `entity/AccessBlacklist.java` | 黑名单实体 |
| `mapper/AccessWhitelistMapper.java` | 白名单 Mapper |
| `mapper/AccessBlacklistMapper.java` | 黑名单 Mapper |
| `mapper/xml/AccessWhitelistMapper.xml` | 白名单 Mapper XML |
| `mapper/xml/AccessBlacklistMapper.xml` | 黑名单 Mapper XML |
| `service/AccessControlService.java` | 访问控制核心服务 |
| `service/user/AccountUserResolverService.java` | 三方账号解析公共服务（与系统管理员共用，合并自 260727） |
| `service/AccessWhitelistService.java` | 白名单管理服务（CRUD） |
| `service/AccessBlacklistService.java` | 黑名单管理服务（CRUD） |
| `controller/AccessControlController.java` | 访问控制管理接口（CRUD + 校验） |
| `exception/AccessControlException.java` | 访问控制异常 |
| `dto/AccessControlResult.java` | 校验结果 DTO |
| `dto/AccessWhitelistRequest.java` | 白名单操作请求 |
| `dto/AccessBlacklistRequest.java` | 黑名单操作请求 |
| `dto/AccessControlPageQuery.java` | 分页查询请求 |
| `utils/IpPatternMatcher.java` | IP 模式匹配工具（精确 / CIDR / 通配符） |

### 10.2 修改文件

| 文件 | 改动说明 |
|------|---------|
| `OpenlibingAuthInterceptor.java` | 移除 `lingshu.test.whitelist` 和 `handleLocalDev()` 相关逻辑；无 Token 返回 401；注入 AccessControlService 增加访问控制检查 |
| `MaasAuthInterceptor.java` | 注入 AccessControlService，在 API Key 验证后增加访问控制检查 |
| `GlobalExceptionHandler.java` | 新增 AccessControlException 处理，复用 MaaS 格式化逻辑 |
| `WebConfig.java` | 可能需要调整拦截器路径（校验接口的鉴权排除） |
| `db/changelog/db.changelog-master.yaml` | 引入新的 changelog 文件 |

## 11. 风险与待确认问题汇总

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| 1 | 前端管理接口的权限控制：谁可以管理黑白名单？ | 安全性 | 需要系统管理员权限，见独立设计文档 `260610-system-admin` |
| 2 | 管理接口（`/api/access/**`）本身是否需要排除访问控制检查？ | 管理员被封禁后无法解封 | 不做额外处理，实际存在多个管理员，一个被封禁不影响其他管理员操作 |
| 3 | 黑名单过期记录的清理策略 | 性能 | 当前版本查询时过滤 `expires_at`，后续可增加定时任务清理（非必要，延后实现） |
| 4 | 白名单未来是否可能需要纯 IP 白名单（不绑定账号）？ | 数据模型扩展性 | 当前只支持账号-IP 绑定，预留 `target_type` 字段 |

## 12. 与鉴权设计文档待改造项的关系

鉴权设计文档（`鉴权设计文档.md` 第 5 节）列出的待改造项中，以下与本次需求相关：

| 待改造项 | 本次处理 |
|---------|---------|
| 无 Token 时的行为：放行但 UserContext 为空 → 应拒绝请求 | ✅ 本次改造：移除白名单 fallback 和 localDev 分支，无 Token 返回 401 |
| 一站式作业白名单移除 | ❌ 不在本次范围（`AuthInterceptor` 的白名单） |
| 三套 UserContext 统一 | ❌ 不在本次范围 |

本次改造完成后，需同步更新鉴权设计文档。

## 13. 设计不完备补充（开发过程中发现）

以下问题在原始设计中未考虑，开发过程中暴露并修复：

### 13.1 Redis 缓存序列化/反序列化类型丢失

**问题**：`RedisConfig` 使用 `Jackson2JsonRedisSerializer<>(Object.class)` 序列化，写入 JSON 时不含 Java 类型信息。反序列化时 Jackson 默认将 JSON 对象还原为 `LinkedHashMap`、JSON 数组还原为 `ArrayList`，导致：
- `List<AccessWhitelist>` 缓存读回实际为 `List<LinkedHashMap>`，遍历时触发 `ClassCastException`
- `Set<String>` 缓存读回实际为 `ArrayList<String>`，`instanceof Set` 判断为 false，每次都查库

**修复**：
1. `RedisConfig` 注册 `JavaTimeModule`，支持 `LocalDateTime` 序列化（之前缓存对象不含时间类型，未暴露此问题）
2. `AccessControlService` 使用 `ObjectMapper.convertValue()` 将 `List<LinkedHashMap>` 转回 `List<AccessWhitelist>`
3. `AccessControlService.toStringSet()` 统一处理 `Collection` → `Set<String>` 转换，兼容 `List`/`Set` 两种反序列化结果
4. `SystemAdminService.getAdminUserIds()` 同样改用 `instanceof Collection` + 逐项转换

**设计教训**：使用 `Jackson2JsonRedisSerializer<>(Object.class)` 时，所有缓存读取方必须处理反序列化类型丢失问题。要么在 RedisConfig 层面启用 default typing（影响全局），要么在每个读取方做 `convertValue`（局部安全）。

### 13.2 无 Token 请求应返回 401 而非放行

**问题**：原 `OpenlibingAuthInterceptor.handleProduction()` 在无 Token 时仅打印 warn 日志并 `return true`（放行），JWT 解析失败时同样放行。这导致未认证请求可以到达业务逻辑，`UserContext` 为空。

**修复**：
1. 无 Token → 写 401 响应 + `return false`
2. JWT 解析失败 → 同样 401
3. JWT 解出 userId 为空 → 401（防御性校验）
4. 统一响应格式：`{"code":401,"message":"...","data":""}`

**设计教训**：鉴权拦截器的核心职责是"未认证则拒绝"，不应存在放行未认证请求的逻辑。本地开发环境也应携带 Token，不需要特殊处理。

### 13.3 /check 接口不需要管理员权限

**问题**：原设计中 `/check` 接口被标记为需要管理员权限（`@RequireAdmin`），但此接口的用途是前端判断当前用户是否被访问控制拦截，普通用户也需要调用。

**修复**：移除 `@RequireAdmin` 注解，从 `UserContext` 获取当前用户的 userId 和 clientIp，不需要请求体参数。

### 13.4 MaaS 校验接口不需要单独暴露

**问题**：原设计中有 `GET /api/maas/v1/access/check` 接口，但不存在外部调用方需要主动查询此接口的场景。MaaS 接口的访问控制校验已嵌入 `MaasAuthInterceptor` 中，每次请求自动执行。

**修复**：不实现此接口，从设计中移除。

### 13.5 CIDR 前缀长度校验缺失（PR review 修复，742cf64）

**问题**：`IpPatternMatcher.matchesCidr()` 未校验 `prefixLength` 范围。当 `prefixLength >= 32`（如 `/33`）时，`fullBytes = 4` 等于 `ipBytes.length`，剩余位检查被跳过，导致 IP 与网络地址完全相同时无效 CIDR 被错误放行。

**修复**：解析 `prefixLength` 后增加 `if (prefixLength < 0 || prefixLength > 32) { return false; }`，并补充 `invalidPrefixLengthWithMatchingNetworkAddress` 回归测试（覆盖 `/33`、`/-1`、`/64`）。

### 13.6 客户端 IP fallback 未解析可信 Header（PR review 修复，742cf64）

**问题**：`resolveTrustedClientIp()` 直接使用 `request.getRemoteAddr()`，未解析 `X-Real-IP`。虽然 spec `260602` 已测试 APIG 部署下 `RemoteAddr` 与 `X-Real-IP` 一致，但与 `MaasAuthInterceptor` 的 IP 提取逻辑不一致。

**修复**：增加 `X-Real-IP` 解析作为 `getRemoteAddr` 的优先来源，与 `MaasAuthInterceptor.resolveClientIp()` 一致。**未采用** review 建议的 `X-Forwarded-For`（spec `260602` 已测试其为不可信，客户端可伪造）。

### 13.7 AccessControlResultTest 断言风格不一致（PR review 修复，742cf64）

**问题**：`AccessControlResultTest` 中 `assertTrue` 已静态导入，但 `assertFalse` 用私有包装方法委托 `Assertions.assertFalse`，风格不一致。

**修复**：删除私有 `assertFalse` 方法，改为 `import static org.junit.jupiter.api.Assertions.assertFalse`。
