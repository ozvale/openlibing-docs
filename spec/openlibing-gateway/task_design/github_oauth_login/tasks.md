# Tasks: Add GitHub OAuth Login Support

## Task 1: Create GithubAuthConfig Class ✅

**文件**: `src/main/java/com/openlibing/gateway/common/config/auth/GithubAuthConfig.java`

- [x] 创建配置类，标注 `@Component`
- [x] 使用 `@Value` 注入配置项
- [x] 字段: clientId, clientSecret, redirectUri, scope, authorizeUrl, accessTokenUrl, userInfoUrl, responseType, grantType, part1
- [x] `getClientSecret()` 方法使用 `SecurityUtil.decrypt()` 解密
- [x] 提供 getter/setter 方法

## Task 2: Create GithubOAuthUtil Class ✅

**文件**: `src/main/java/com/openlibing/gateway/common/utils/oauth/GithubOAuthUtil.java`

- [x] 创建工具类，使用静态方法
- [x] `getToken(String code, GithubAuthConfig config)`: 调用 GitHub API 获取 access_token
- [x] `getThreePartUserInfoByAccessToken(String accessToken, GithubAuthConfig config)`: 获取用户信息
- [x] 数字类型转换为正常字符串（避免科学计数法）
- [x] 使用 OkHttp 进行 HTTP 调用
- [x] 添加日志记录

## Task 3: Extend Platform Enum ✅

**文件**: `src/main/java/com/openlibing/gateway/common/constants/Platform.java`

- [x] 在枚举中添加 `GITHUB` 值
- [x] 枚举顺序: GITEE, GITCODE, UNIPORTAL, OPENUBMC, GITHUB
- [x] `isValid()` 方法自动支持新值

## Task 4: Update LoginServiceImpl ✅

**文件**: `src/main/java/com/openlibing/gateway/business/service/impl/LoginServiceImpl.java`

- [x] 注入 `GithubAuthConfig`
- [x] 新增 `generateGithubAuthUrl(String state)` 方法
- [x] 在 `getPlatformAccessToken()` 中添加 `GITHUB` 分支
- [x] 在 `getThreePartUserInfoByAccessToken()` 中添加 `GITHUB` 分支
- [x] 在 `queryAllPlatformUserInfos()` 中添加 GitHub 平台查询

## Task 5: Add Apollo Configuration ✅

**配置路径**: Apollo → openlibing-gateway → github.oauth

- [x] `github.oauth.client-id`
- [x] `github.oauth.client-secret` (加密存储)
- [x] `github.oauth.redirect-uri`
- [x] `github.oauth.scope`
- [x] `github.oauth.authorize-url`
- [x] `github.oauth.access-token-url`
- [x] `github.oauth.user-info-url`
- [x] `github.oauth.response-type`
- [x] `github.oauth.grant-type`
- [x] `security.part1` (加密密钥)

## Task 6: Testing ✅

- [x] 单元测试: 测试 `GithubOAuthUtil` 方法
- [x] 集成测试: 测试 GitHub 登录流程
- [x] 安全测试: 验证 client_secret 不泄露
- [x] 边界测试: 测试 GitHub API 调用失败场景

## Task 7: Documentation ✅

- [x] 更新 API 文档
- [x] 更新配置文档
- [x] 更新安全文档