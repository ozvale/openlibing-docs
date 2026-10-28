# Tasks: 插件登录客户端配置化与 refreshToken 轮换

## 需求 1：插件客户端白名单配置化

- [x] `LoginUtil` 删除 `ALLOWED_CLIENTS` 硬编码常量，`checkPluginLogin` 增加 `List<String> allowedClients` 参数
- [x] 大小写不ensitive 匹配：配置项与入参统一小写化比较
- [x] 空列表/null 拒绝所有（安全失败）
- [x] `LoginController` 新增 `@Value("${login.allowed.clients}")` 字段，5 处调用统一传参
- [x] `LoginUtilTest` 适配新签名 + 新增空列表/大小写用例
- [x] `LoginControllerTest.setUp` 通过 `ReflectionTestUtils.setField` 注入 `allowedClients`（纯 Mockito 无 Spring 容器，`@Value` 不生效）

## 需求 2：refreshToken 轮换

- [x] 刷新路径增加 Redis 比对校验（`PLUGIN_LOGIN_REFRESH-{accountId}-{accountName}`，解密后与传入值比对）
- [x] 校验失败返回 `Invalid refreshToken`，日志仅打 key 不打 token 明文
- [x] 生成新短效 JWT（30 分钟）与新 refreshToken（30 天）
- [x] 新 refreshToken 加密后覆盖存储到同一 key，旧 token 即刻失效
- [x] `LoginServiceImplTest` 新增校验拒绝/放行用例

## 需求 3：uniportal 用户同步修复

- [x] `checkUniportalUserInfo` 改为 accountLogin 优先、accountId 兜底，均未命中才新增
- [x] `updateThreePartyUserInfo` uniportal 分支 WHERE 扩展为 `account_id or account_login`
- [x] 邮箱绑定逻辑抽取为 `bindUniportalUserEmail`（G.MET.01）
- [x] `LoginServiceImplTest` 新增重复账号场景用例

## 需求 4：依赖升级

- [x] bcprov-jdk18on 升级 1.85.2（`pom.xml`）

## 验证

- [x] 全量单测通过（1473+ 用例，0 失败）
- [x] CheckStyle / SpotBugs / PMD / Spotless 通过
- [x] 业务 PR #203 创建并补打 `ai-assisted` 标签
- [ ] 用户手动自测：Apollo 配置调整生效 / 旧 refreshToken 被拒 / uniportal 换账号名不产生重复记录
