# 260610-access-control-blacklist-whitelist — Tasks

## Phase 1: 数据模型与基础设施

- [x] 1.1 创建 Liquibase changelog：`workspace_access_whitelist` 表
- [x] 1.2 创建 Liquibase changelog：`workspace_access_blacklist` 表
- [x] 1.3 创建实体类：`AccessWhitelist`、`AccessBlacklist`
- [x] 1.4 创建 Mapper：`AccessWhitelistMapper`、`AccessBlacklistMapper` 及 XML

## Phase 2: 核心服务

- [x] 2.1 实现 `IpPatternMatcher`：精确 IP / CIDR / `*` 通配符匹配
- [x] 2.2 实现 `AccessControlService.check(userId, clientIp)`：白名单 → 账号黑名单 → IP 黑名单
- [x] 2.3 实现 `AccessControlService.checkAccess(userId, clientIp)`：返回结构化结果（不抛异常）
- [x] 2.4 实现 `AccessControlResult` / `AccessControlException`：差异化错误类型
- [x] 2.5 实现缓存层：Redis 缓存黑白名单，TTL 60s，增删时主动失效
- [x] 2.6 修复 Redis 反序列化类型丢失：`List<LinkedHashMap>` → `List<AccessWhitelist>`（`ObjectMapper.convertValue`）；`Set<String>` 缓存读回为 `ArrayList`（改用 `instanceof Collection` 兼容）
- [x] 2.7 修复 Redis `LocalDateTime` 序列化：`RedisConfig` 注册 `JavaTimeModule`

## Phase 3: 拦截器改造

- [x] 3.1 移除 `OpenlibingAuthInterceptor` 中 `lingshu.test.whitelist` 相关逻辑
- [x] 3.2 移除 `isJwtEnabled` 配置项及 `handleLocalDev()` 分支
- [x] 3.3 无 Token 请求直接返回 401（原设计遗漏：之前是放行 + warn 日志）
- [x] 3.4 改造 `getClientIp()` fallback：安全场景使用 `RemoteAddr` 而非 `X-Forwarded-For`（方案 C）
- [x] 3.5 `OpenlibingAuthInterceptor`：用户信息解析后调用 `AccessControlService.check()`（对 `/access/check` 路径跳过）
- [x] 3.6 `MaasAuthInterceptor`：API Key 验证后调用 `AccessControlService.check()`
- [x] 3.7 userName 回填逻辑从 `OpenlibingAuthInterceptor` 移至 `UserInfoSyncService.updateUserNameInBusinessTables()`，在用户信息同步时顺带更新黑白名单和管理员表

## Phase 4: 错误处理

- [x] 4.1 `GlobalExceptionHandler` 新增 `AccessControlException` 处理分支
- [x] 4.2 管理接口错误格式：`{code, msg}`
- [x] 4.3 MaaS 接口错误格式：复用 `writeMaasFormatError()` 输出 OpenAI/Anthropic 格式

## Phase 5: 前端管理接口

- [x] 5.1 `AccessControlController`：白名单查询（GET `/api/admin/access/whitelist`）、添加（POST）、更新（POST `/{id}/update`）、删除（POST `/{id}/delete`）
- [x] 5.2 `AccessControlController`：黑名单查询（GET `/api/admin/access/blacklist`）、添加（POST）、更新（POST `/{id}/update`）、删除（POST `/{id}/delete`）
- [x] 5.3 校验接口：`GET /api/admin/access/check`（从 UserContext 解析身份，不需要管理员权限；拦截器对此路径跳过 check() 调用）
- ~~5.4 MaaS 校验接口~~：不需要单独暴露，校验已嵌入 `MaasAuthInterceptor`
- [x] 5.5 管理接口（CRUD）添加 `@RequireAdmin` 注解；`/check` 接口不需要管理员权限
- [x] 5.6 删除接口改用 `@PostMapping` + `/{id}/delete` 路径（网关拦截 PUT/DELETE）

## Phase 6: 用户搜索接口（后续实现）

- [ ] 6.1 `GET /api/admin/access/user-search?keyword=xxx`：从 `workspace_user_info` 表搜索用户

## Phase 7: 三方账号信息统一（合并自 260727-access-list-thirdparty-account）

- [x] 7.1 `access-control-tables.xml` 追加 changeSet：whitelist/blacklist 加 account_platform/account_login
- [x] 7.2 `AccessWhitelist` / `AccessBlacklist` 实体加 accountPlatform/accountLogin 字段
- [x] 7.3 新建 `AccountUserResolverService`：封装解析三方账号 + syncOnAddMember 逻辑
- [x] 7.4 `AccessControlController` 注入 `AccountUserResolverService`，addWhitelist/addBlacklist(ACCOUNT) 改用
- [x] 7.5 `WhitelistRequest` / `BlacklistRequest` record 调整（ACCOUNT 类型用 accountPlatform + accountLogin，IP 类型保持 targetId）
- [x] 7.6 更新 `AccessControlControllerTest`：mock AccountUserResolverService，适配新请求体

## Phase 8: PR review 反馈修复（742cf64）

- [x] 8.1 `IpPatternMatcher.matchesCidr` 增加 prefixLength 0-32 范围校验
- [x] 8.2 补充 `invalidPrefixLengthWithMatchingNetworkAddress` 回归测试
- [x] 8.3 `OpenlibingAuthInterceptor.resolveTrustedClientIp` 增加 X-Real-IP 解析（与 MaasAuthInterceptor 一致，不用 X-Forwarded-For）
- [x] 8.4 `AccessControlResultTest` 删除私有 assertFalse 包装，改用静态导入

## 验证

- [x] V1 白名单为空时允许所有请求
- [x] V2 白名单精确 IP 匹配
- [x] V3 白名单 CIDR 网段匹配
- [x] V4 白名单 `*` 通配符匹配
- [x] V5 黑名单账号封禁（精确）
- [x] V6 黑名单 IP 封禁（精确）
- [x] V7 黑名单过期自动失效
- [x] V8 先白名单后黑名单，黑名单优先
- [x] V9 MaaS 接口联合校验（账号-IP 绑定）
- [x] V10 无 Token 请求返回 401
- [x] V11 管理接口非管理员返回 403
- [x] V12 校验接口从 Token 解析身份（不需要管理员权限）
- [x] V13 白名单添加传 accountPlatform + accountLogin + ipPattern 成功
- [x] V14 黑名单 ACCOUNT 添加传 accountPlatform + accountLogin 成功；IP 类型保持 targetId
- [x] V15 三方账号解析失败返回 400
- [x] V16 CIDR 无效前缀（/33、/-1、/64）被拒绝
- [x] V17 resolveTrustedClientIp 优先使用 X-Real-IP
- [x] V18 AccessControlResultTest 使用标准 assertFalse 静态导入
