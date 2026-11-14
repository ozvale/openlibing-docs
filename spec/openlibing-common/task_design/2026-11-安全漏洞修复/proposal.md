# 2026-11 安全漏洞修复

## 需求背景

公司团队对 openlibing-common 仓 master 检出多个安全问题，对应 issue 以【安全】命名。本批次在 `fix-current-issues` 分支上完成多轮代码级漏洞修复，均与业务逻辑相关（CI workflow 类 issue #47/#48 单独由组织处理，不在本批次）。

## 功能描述

修复以下安全缺陷（不做/不做什么以每题清单为准）：

| Issue         | 缺陷                                                                                                            | 修复内容                                                                                   |
| ------------- | --------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| #51           | `AESCipher.toXor` 长度不一致静默返回全零数组，根密钥派生降级为可预测值（fail-open）                             | 长度不一致抛 `IllegalArgumentException`；`genRootKey` 增加三段成分长度一致性校验           |
| #46           | `JwtUtils.generateCookie` 未设置 SameSite，存在 CSRF 风险                                                       | Cookie 增加 `SameSite=Lax`                                                                 |
| #52（第2条）  | `ExternalLinkCheckUtils` 硬编码内源 OBS 公网域名                                                                | 改为必配项 `external.default.image.url`（未配置启动失败）                                  |
| #42-F6        | `PBDKF2Util` 口令入参用后未清理                                                                                 | PBEKeySpec 用后 `finally clearPassword()`                                                  |
| #42-F2        | `ParameterExceptionInfoUtils` 异常审计日志将 requestBody 完整 JSON 明文入库                                     | 复用 `OperationLogPayloadSanitizer` 统一脱敏                                               |
| #50           | 搜索路径类 env（PATH/LD_LIBRARY_PATH 等）追加值未校验，可被劫持                                                 | 追加前校验绝对路径/存在/非符号链接/非禁止目录，不受信即拒绝                                |
| #44           | `InternalAuthFilter` URL 编码绕过认证（高危）、`contains` 子串误判、token 未配置 fail-open                      | 判定前 `UriUtils.decode`；段边界匹配；token 未配置 401 fail-closed                         |
| #49（性能项） | `getWorkKey` 每次调用全量重跑 PBKDF2×10000，CPU/GC/内存残留代价                                                 | 增加 Caffeine 内存缓存（key=part1，TTL 1800s），失败不缓存                                 |
| #52（第3条）  | okio 3.4.0 低于 CVE-2023-3635 修复链 3.9.0                                                                      | 升级至 3.18.2                                                                              |
| #52（第4条）  | AESUtil/HmacUtil 密钥以 String/Base64 入参，来源不受控                                                          | 仅 Javadoc 约束提醒（不改代码）：密钥须经 getWorkKey/配置中心/KMS 托管                     |
| #72           | Feign 全局拦截器把内部鉴权 Token 注入所有出站请求，随第三方平台请求外泄（可重放访问全部 `/internal-server/**`） | 仅对内部目标注入 `X-Internal-Token`；外部目标跳过；新增 strict 灰度开关与 allow-hosts 兜底 |

## 验收标准

- [ ] 每处修复均有匹配的单测覆盖（或说明原因）
- [ ] 全量单测通过（当前 430 个）
- [ ] Spotless / CheckStyle / SpotBugs / PMD 全部通过
- [ ] 每个修复独立 commit，均引用对应 issue（`Refs #<n>`）
- [ ] spec 文档（本目录）同步更新最终落地情况
- [ ] #72：外部平台目标的 Feign 请求不再携带 `X-Internal-Token`，内部目标仍正常注入

## 影响范围

- openlibing-common 仓，涉及约 14 个源/测试文件 + pom.xml
- 新增依赖：`com.github.ben-manes.caffeine`（由 Spring Boot BOM 管理，3.2.4）
- 下游服务需关注行为变化：新增必配项 `external.default.image.url`、Cookie 增加 SameSite、搜索路径 env 收紧、InternalAuth token 未配置即 401、密钥派生 fail-closed（详见 design.md 风险小节）
- #72 新增可选配置 `internal.auth.inject.*`（有默认值，不配置即严格模式）；若存在非标准内部域名需补充 `allow-hosts`
- #72 Nacos 变更：**无需新增配置即可生效**；仅当内部目标使用自定义内网域名时补 `internal.auth.inject.allow-hosts`；上线前需核对 `gitcode.api.address`、`gitee.api.address` 及 6 个 `*.direct-url` 的实际取值形态
