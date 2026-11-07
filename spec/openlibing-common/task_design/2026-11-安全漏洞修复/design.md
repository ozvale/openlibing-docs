# 2026-11 安全漏洞修复 — 技术设计

## 方案概述

6 处独立的安全缺陷修复，均遵循"fail-closed 优先、最小行为变化、复用已有安全组件"原则，逐项独立 commit。

## 架构决策

### 决策 1：toXor 长度不一致 fail-closed（#51）

- **决策**：`toXor` 长度不一致时抛 `IllegalArgumentException`，`genRootKey` 派生前显式校验三段成分（part1/part2/part3）等长。
- **原因**：原实现静默返回全零数组，密钥组件误配时根密钥降级为可预测值（CWE-754 fail-open）。
- **影响**：正常配置（三段等长）不受影响；配置错误时密钥派生立即失败，属于期望的 fail-closed。
- **测试**：`AESCipherTest` 更新"长度不同返回零数组"断言为"抛异常"，新增三段一致性校验用例。

### 决策 2：JWT Cookie SameSite=Lax（#46）

- **决策**：`generateCookie` 增加 `.sameSite("Lax")`，不引入 Strict。
- **原因**：修复 CSRF（跨站 POST 不带 cookie）；Lax 保留顶级导航 GET，兼容登录回跳。HMAC 密钥与签名算法保持不变（issue 明确暂不迁移 RS256/KMS）。
- **影响**：跨站 POST/submit 不再携带认证 cookie，需下游回归登录回跳场景。
- **测试**：`JwtUtilsTest` 断言 cookie `getSameSite() == "Lax"`。

### 决策 3：OBS 默认图 URL 必配化（#52 第2条）

- **决策**：`ExternalLinkCheckUtils` 硬编码域名改为 `@Value("${external.default.image.url}")` 必配项。
- **原因**：移除字节码中的内源公网域名（红线 A2-05）。与既有 `external.white.links` 注入机制风格一致。
- **影响**：未配置 `external.default.image.url` 的项目启动失败（fail-fast）——**下游行为破坏性**，需全部下游补配 yaml。
- **测试**：`ExternalLinkCheckUtilsTest` setUp 注入字段；新增空配置用例。

### 决策 4：PBEKeySpec 口令清理（#42-F6）

- **决策**：`PBDKF2Util.getPBKDF2Bytes` 将 `PBEKeySpec` 生命周期包在 try-finally，`finally` 调 `clearPassword()`。
- **原因**：派生后口令字符仍滞留 `PBEKeySpec`，用后即清可回收（"用完即清"的真场景）。
- **影响**：无运行时行为变化。
- **测试**：`PBDKF2UtilTest` 既有用例全覆盖。

### 决策 5：异常审计日志 requestBody 脱敏（#42-F2）

- **决策**：`ParameterExceptionInfoUtils` 序列化入参前复用 `OperationLogPayloadSanitizer`（由 package-private 改 public），与 operation-log 主链路共用同一套脱敏规则。
- **原因**：原实现 requestBody 完整 JSON 明文入库（含 password/token）。共用规则避免两套黑名单漂移。
- **影响**：仅影响参数校验异常日志内容，无行为破坏。
- **测试**：新增 `ParameterExceptionInfoUtilsTest` 行为用例（password/token 打码、username 保留）。

### 决策 6：搜索路径 env 追加校验（#50）

- **决策**：`SecureCmdExecutor.applyEnvAndDir` 对 MULTI_VALUE_ENV_KEYS 追加前逐段校验：绝对路径、真实存在、非符号链接、不在 `BLOCKED_DIRS`，任一段不受信抛 `CmdValidatorException`。
- **原因**：拦截调用方把外部可控字符串拼入 PATH/LD_LIBRARY_PATH 等造成子进程命中攻击者目录（CWE-427）。保留追加语义以保证合法构建/扫描链路（直接加 BLOCKED 会断业务，与组件设计意图相悖）。
- **影响**：相对路径/不存在的绝对路径/符号链接/系统目录的追加值将被拒绝——**行为收紧**，需下游排查是否传过此类值。
- **测试**：更新追加用例用绝对路径；新增"相对路径被拒""不存在绝对路径被拒"用例。

## 明确不做的项（团队裁定）

| 项                               | 裁定来源                                                             |
| -------------------------------- | -------------------------------------------------------------------- |
| #42-F5 JWT 密钥内存常驻（KMS）   | 团队 11-02 拒绝：密钥每次运算都要用，无法解密后删除；根治为 KMS 专项 |
| #45 salt 固定值                  | 已关闭：三段式+PBKDF2+随机IV 符合业界推荐方式                        |
| #44 InternalAuthFilter fail-open | 待用户/同事确认后再定，行为破坏性改动                                |
| #47/#48 CI workflow              | 组织层面处理（权限已补，事件/执行机待同步）                          |
| #49 密钥生命周期                 | 团队裁定轮换/删除不成立（k8s 兜底）；保留 getWorkKey 缓存性能项      |

## 涉及文件

| 文件                                                                                      | 操作 | 说明                                        |
| ----------------------------------------------------------------------------------------- | ---- | ------------------------------------------- |
| src/main/java/com/openlibing/common/security/cipher/AESCipher.java                        | 修改 | #51 toXor fail-closed + genRootKey 长度校验 |
| src/test/java/com/openlibing/common/security/cipher/AESCipherTest.java                    | 修改 | #51 断言更新 + 新增                         |
| src/main/java/com/openlibing/common/utils/JwtUtils.java                                   | 修改 | #46 SameSite=Lax                            |
| src/test/java/com/openlibing/common/utils/JwtUtilsTest.java                               | 修改 | #46 断言                                    |
| src/main/java/com/openlibing/common/utils/ExternalLinkCheckUtils.java                     | 修改 | #52-2 OBS URL 必配化                        |
| src/test/java/com/openlibing/common/utils/ExternalLinkCheckUtilsTest.java                 | 修改 | #52-2 注入 + 空配置用例                     |
| src/main/java/com/openlibing/common/security/security/PBDKF2Util.java                     | 修改 | #42-F6 clearPassword                        |
| src/main/java/com/openlibing/common/aspect/operationlog/OperationLogPayloadSanitizer.java | 修改 | #42-F2 改 public                            |
| src/main/java/com/openlibing/common/utils/ParameterExceptionInfoUtils.java                | 修改 | #42-F2 复用脱敏                             |
| src/test/java/com/openlibing/common/utils/ParameterExceptionInfoUtilsTest.java            | 修改 | #42-F2 行为用例                             |
| src/main/java/com/openlibing/common/security/SecureCmdExecutor.java                       | 修改 | #50 env 路径校验                            |
| src/test/java/com/openlibing/common/security/SecureCmdExecutorTest.java                   | 修改 | #50 更新+新增用例                           |

## 风险 & 缓解

1. **下游行为破坏**（必配项/SameSite/env 收紧）：在 PR 描述与 release 通知中显式列出 3 项行为变化，要求下游扫描配置。
2. **脱敏规则变更影响旧日志分析**：`ParameterExceptionInfoUtils` 输出从完整明文变为打码，长字段被截断到 500,需审计平台侧确认兼容。
3. **Windows 路径校验**：`checkParams` 的 REGEX 拦截 `\`，Windows 绝对路径需以 `/` 形式传入（测试已处理），文档需说明。

## 跨仓影响

- 无接口变更。行为变化通过 release note 传导给 openlibing-common 全部下游服务。
