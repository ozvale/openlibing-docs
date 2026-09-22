# Design: Add GitHub OAuth Login Support

## Architecture

遵循项目现有的第三方平台认证架构：

```
Controller → LoginService → GithubOAuthUtil → GitHub API
            ↓
      ThreePartyUserInfoMapper → MySQL
            ↓
      Redis → 会话管理
```

## Data Model

### ThreePartyUserInfoEntity

复用现有实体，`accountPlatform` 字段值为 `"GITHUB"`：

| 字段 | Java类型 | DB类型 | 说明 |
|------|---------|--------|------|
| id | Long | BIGINT (AI, PK) | 主键 |
| userId | String | VARCHAR(64) | openLiBing 用户 ID |
| accountId | String | VARCHAR(64) | GitHub 用户 ID |
| accountName | String | VARCHAR(128) | GitHub 用户名 |
| accountLogin | String | VARCHAR(64) | GitHub 登录名 |
| accountPlatform | String | VARCHAR(32) | 平台标识 = "GITHUB" |
| accessToken | String | VARCHAR(512) | GitHub Access Token（加密） |
| createdAt | Date | DATETIME | 创建时间 |
| updatedAt | Date | DATETIME | 更新时间 |

## Component Design

### GithubAuthConfig

配置类，读取 Apollo 配置：

| 字段 | 类型 | 说明 |
|------|------|------|
| clientId | String | GitHub OAuth 客户端 ID |
| clientSecret | String | GitHub OAuth 客户端密钥（加密存储） |
| redirectUri | String | 重定向 URI |
| scope | String | 授权范围 |
| authorizeUrl | String | 授权 URL |
| accessTokenUrl | String | Access Token 获取 URL |
| userInfoUrl | String | 用户信息获取 URL |
| responseType | String | 响应类型（固定为 "code"） |
| grantType | String | 授权类型（固定为 "authorization_code"） |
| part1 | String | 加密密钥片段 |

**加密处理**：`getClientSecret()` 方法返回解密后的值

### GithubOAuthUtil

工具类，提供 GitHub OAuth 操作：

| 方法 | 说明 | 参数 | 返回值 |
|------|------|------|--------|
| `getToken()` | 根据授权码获取 Access Token | `code`, `config` | String |
| `getThreePartUserInfoByAccessToken()` | 根据 Access Token 获取用户信息 | `accessToken`, `config` | HashMap<String, String> |

### Platform Enum

扩展现有枚举：

```java
public enum Platform {
    GITEE, GITCODE, UNIPORTAL, OPENUBMC, GITHUB;  // 新增 GITHUB
}
```

### LoginServiceImpl 扩展

在现有服务中新增方法：

| 方法 | 说明 |
|------|------|
| `generateGithubAuthUrl(String state)` | 生成 GitHub 授权 URL |
| `getPlatformAccessToken(String code, "github")` | 获取 GitHub Access Token（复用） |
| `getThreePartUserInfoByAccessToken(String token, "github")` | 获取 GitHub 用户信息（复用） |

## Key Design Decisions

### 1. 加密方案

`GithubAuthConfig.getClientSecret()` 使用 `SecurityUtil.decrypt()` 解密存储在 Apollo 中的加密配置：

```java
public String getClientSecret() {
    return SecurityUtil.decrypt(clientSecret, part1);
}
```

### 2. 数字类型处理

在 `GithubOAuthUtil.getThreePartUserInfoByAccessToken()` 中，数字类型统一转换为正常数字字符串，避免科学计数法：

```java
if (value instanceof Number) {
    userInfo.put(key, new BigDecimal(value.toString()).toPlainString());
} else {
    userInfo.put(key, value.toString());
}
```

### 3. 平台优先级策略

在多平台用户名冲突时，遵循以下优先级：
1. UNIPORTAL（最高）
2. GITCODE
3. GITEE
4. OPENUBMC
5. GITHUB（最低）

### 4. HTTP 客户端选择

使用 OkHttp 进行 HTTP 调用，与其他第三方平台保持一致：

```java
OkHttpClient client = new OkHttpClient().newBuilder().build();
```

## Dependency Injection

### GithubOAuthUtil

无需依赖注入，所有方法为静态方法。

### LoginServiceImpl 新增注入

```java
@Autowired
private GithubAuthConfig githubAuthConfig;
```

### 调用链路

```
1. Controller 收到回调请求
    ↓
2. LoginServiceImpl.platformLoginCallback()
    ↓
3. getPlatformAccessToken(code, "github")
    ↓
4. GithubOAuthUtil.getToken(code, githubAuthConfig)
    ↓
5. getThreePartUserInfoByAccessToken(accessToken, "github")
    ↓
6. GithubOAuthUtil.getThreePartUserInfoByAccessToken(accessToken, githubAuthConfig)
    ↓
7. 验证用户并生成 JWT Token
```