# Archive: 插件登录客户端配置化与 refreshToken 轮换

## 交付结论

| 项          | 值                                                                                 |
| ----------- | ---------------------------------------------------------------------------------- |
| 业务仓      | openlibing/openlibing-gateway                                                      |
| 发布分支    | release_20260923                                                                   |
| 业务 PR     | https://gitcode.com/openlibing/openlibing-gateway/pull/203（`ai-assisted` 已打标） |
| 关联 Issue  | 暂不关联（PR 被打 `needs-issue`，CI 标签未动）                                     |
| 关联 commit | `ef65431` / `b76dd09` / `e8059ae`                                                  |
| 变更规模    | 9 files, +211/-67                                                                  |
| 测试        | 全量 1473+ 单测通过；CheckStyle/SpotBugs/PMD/Spotless 通过                         |

## 实际交付内容

1. **插件客户端白名单配置化**：`LoginUtil.checkPluginLogin` 从硬编码改为接收 `LoginController` 注入的 Apollo 配置 `login.allowed.clients`（`List<String>`），大小写不敏感，空列表拒绝所有。
2. **refreshToken 轮换**：刷新路径先 Redis 比对（`PLUGIN_LOGIN_REFRESH-{accountId}-{accountName}`，AES 解密后比对），通过后生成新短效 JWT + 新 refreshToken，新 refreshToken 覆盖存储使旧 token 即刻失效。
3. **uniportal 同步修复**：accountLogin 优先、accountId 兜底查询，修复换账号名产生重复记录；更新 WHERE 扩展为 `account_id or account_login`。
4. **依赖升级**：bcprov-jdk18on 1.85.2。

## 过程中的方案演进（重要决策记录）

| 轮次 | 方案                                                | 结论                                                                                |
| ---- | --------------------------------------------------- | ----------------------------------------------------------------------------------- |
| v1   | 新 refreshToken 不落 Redis，仅返回客户端            | 缺乏服务端撤销能力，废弃                                                            |
| v2   | 新 refreshToken 覆盖存储 + 校验比对                 | **本批采纳**：旧 token 失效即时确定                                                 |
| v3   | 黑名单模式（SHA-256 摘要入 `*-revoked-*` 废弃缓存） | 已在 develop 分支原型验证，支持多客户端并存；发布分支未纳入，后续多客户端需求时启用 |

v2 的已知局限：同一用户多客户端登录时后登录者会踢掉先登录者的 refreshToken。v3 黑名单方案是现成的演进路径。

## 部署依赖（运维必读）

1. Apollo 需**先行发布** `login.allowed.clients`（如 `vscode,idea,agent_arena`），否则启动失败。
2. 升级瞬间存量 refreshToken 不在 Redis，首次刷新被拒，用户需重新登录（一次性影响）。

## 经验沉淀

- 纯 Mockito 测试类（`@ExtendWith(MockitoExtension.class)`）中 `@Value` 不生效，需 `ReflectionTestUtils.setField` 手动注入——新增 `@Value` 字段时同步排查所有测试类。
- AES-GCM 随机 IV 非确定性加密，密文不能直接做缓存 key 或等值比对依据，需先取 SHA-256 摘要。
- 本仓 refreshToken JWT 无 `jti` claim，做黑名单/审计需以 token 摘要为唯一标识。
- pre-commit 的 gitleaks 钩子需从 go.dev 下载 Go 工具链，网络受限环境会阻塞提交（临时 `SKIP=gitleaks`，勿长期跳过）。
- `mvn-spotless` 钩子格式化整个项目：远端合并引入的格式漂移会阻塞无关提交，合并后应第一时间提交一次全量格式化。
