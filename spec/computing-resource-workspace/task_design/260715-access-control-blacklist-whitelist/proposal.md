# 260610-access-control-blacklist-whitelist - Proposal

## 需求背景

当前 computing-resource-workspace 没有访问控制机制，所有通过鉴权的用户都能访问所有接口。存在以下问题：
- 无法限制特定用户或 IP 的访问
- MaaS 接口缺乏账号-IP 绑定校验，API Key 被盗用后无法从 IP 层面拦截
- 现有的 `lingshu.test.whitelist` 配置式白名单不够灵活，无法动态管理

## 功能描述

增加黑白名单访问控制机制：

1. **白名单**：允许访问的账号-IP 组合，不在白名单则拒绝。支持精确 IP、CIDR 网段、通配符 `*`
2. **黑名单**：禁止访问的账号或 IP，在黑名单则拒绝。仅支持精确封禁，支持过期时间
3. **判断优先级**：先白名单后黑名单，黑名单优先级高于白名单
4. **MaaS 联合校验**：API Key 解析的账号 + 请求 IP 必须在白名单内且不在黑名单内
5. **前端管理**：黑白名单的增删改查，管理员权限控制
6. **校验接口**：供前端查询当前用户访问状态
7. **差异化错误提示**：不同拦截原因返回不同错误信息，MaaS 接口使用 OpenAI/Anthropic 格式
8. **三方账号统一传递**：白名单/黑名单添加接口统一使用 accountPlatform + accountLogin（与 addMembers 一致），后端通过 AccountUserResolverService 解析 userId
9. **CIDR 前缀校验**：IpPatternMatcher 对 IPv4 CIDR 校验 prefixLength 0-32，拒绝 /33 等无效前缀

## 验收标准

- [x] 移除现有 `lingshu.test.whitelist` 白名单机制和 `isJwtEnabled` 本地开发分支
- [x] 无 Token 请求直接返回 401
- [x] 白名单为空时允许所有请求通过
- [x] 白名单支持精确 IP、CIDR 网段、`*` 通配符匹配
- [x] 黑名单仅支持精确 IP/账号封禁，支持过期时间
- [x] 先白名单后黑名单，黑名单优先
- [x] OpenlibingAuthInterceptor 和 MaasAuthInterceptor 均接入访问控制
- [x] IP fallback 策略：远程 API 不可用时使用 X-Real-IP -> RemoteAddr（可信来源，X-Forwarded-For 不可信）
- [x] 前端管理接口使用 GET/POST + /add/update/delete 后缀
- [x] 校验接口从 Token/Cookie 解析身份，前端无需传参
- [x] MaaS 接口错误使用 OpenAI/Anthropic 格式
- [x] 管理接口需要系统管理员权限（`@RequireAdmin`）
- [x] 白名单/黑名单添加接口改用 accountPlatform + accountLogin（复用 AccountUserResolverService）
- [x] IpPatternMatcher 校验 CIDR prefixLength 0-32，拒绝无效前缀
- [x] AccessControlResultTest 使用 JUnit 标准 assertFalse 静态导入

## 影响范围

- **核心改动**：`OpenlibingAuthInterceptor`、`MaasAuthInterceptor`、`AccessControlController`
- **新增模块**：AccessControlService、IpPatternMatcher、AccessControlException、AccountUserResolverService（与系统管理员共用）
- **新增数据表**：`workspace_access_whitelist`、`workspace_access_blacklist`（均含 account_platform/account_login 列）
- **前端影响**：新增黑白名单管理页面、校验接口调用
