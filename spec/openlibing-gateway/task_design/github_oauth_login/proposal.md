# Proposal: Add GitHub OAuth Login Support

## Summary

为 openlibing-gateway 新增 GitHub OAuth2.0 授权登录能力，包括：
- 新增 GitHub 配置类和 OAuth 工具类
- 扩展 `Platform` 枚举支持 `GITHUB`
- 在 `LoginServiceImpl` 中添加 GitHub 相关方法
- 支持 Web 端和 IDE 插件端登录
- 支持用户在个人中心绑定/解绑 GitHub 账号

## Motivation

当前系统已支持 Gitee、Gitcode、Uniportal、Openubmc 四个第三方平台登录，需要扩展 GitHub 平台支持：
1. 为海外用户提供登录入口
2. 支持 IDE 插件通过 GitHub 授权获取 token
3. 完善统一鉴权方案，整合更多第三方平台

## Scope

### 新增文件（2个）

| 文件 | 说明 |
|------|------|
| `common/config/auth/GithubAuthConfig.java` | GitHub OAuth 配置类，读取 Apollo 配置 |
| `common/utils/oauth/GithubOAuthUtil.java` | GitHub OAuth 工具类，实现 token 获取和用户信息查询 |

### 修改文件（2个）

| 文件 | 说明 |
|------|------|
| `common/constants/Platform.java` | 新增 `GITHUB` 枚举值 |
| `business/service/impl/LoginServiceImpl.java` | 新增 `generateGithubAuthUrl()` 等方法 |

### 不在范围内

- 不修改数据库表结构（复用现有 `user_info_github` 表）
- 不新增 Controller 端点（复用统一鉴权入口）

## API Design

### 1. 生成 GitHub 授权 URL

- **方法**: `generateGithubAuthUrl(String state)`
- **入参**: `state` - 防 CSRF 状态参数
- **返回**: GitHub 授权 URL 字符串
- **调用链**: Controller → LoginService → generateGithubAuthUrl

### 2. 获取 GitHub Access Token

- **方法**: `getPlatformAccessToken(String code, "github")`
- **入参**: `code` - 授权码
- **返回**: Access Token 字符串
- **调用链**: Callback → LoginService → getPlatformAccessToken → GithubOAuthUtil.getToken

### 3. 获取 GitHub 用户信息

- **方法**: `getThreePartUserInfoByAccessToken(String accessToken, "github")`
- **入参**: `accessToken` - 访问令牌
- **返回**: HashMap<String, String> 用户信息
- **调用链**: Callback → LoginService → getThreePartUserInfoByAccessToken → GithubOAuthUtil.getThreePartUserInfoByAccessToken

## Authentication Flow

```
Web 端登录:
┌─────────────┐     ┌──────────────────┐     ┌────────────────────┐
│  前端页面   │ ──▶ │ generateGithubAuthUrl │ ──▶ │ 302 重定向到 GitHub │
└─────────────┘     └──────────────────┘     └────────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│  GitHub 回调 /oauth2/callback/github?code=xxx&state=xxx             │
└─────────────────────────────────────────────────────────────────────┘
                                                     │
                                                     ▼
┌─────────────────────────────────────────────────────────────────────┐
│  1. getPlatformAccessToken(code, "github")                          │
│  2. getThreePartUserInfoByAccessToken(accessToken, "github")        │
│  3. platformLoginCallback(threePartUserInfoMap)                     │
│  4. 生成 JWT Token 并返回                                           │
└─────────────────────────────────────────────────────────────────────┘
```

## Risks

- GitHub API 调用限制：需实现请求重试和限流机制
- OAuth 配置泄露：`client_secret` 使用 Jasypt 加密存储
- 三方平台用户名冲突：遵循优先级策略（uniportal > gitcode > gitee > openubmc > github）