# Design: fix-verify-token-allow-expired

## 影响范围

| 文件                                                                   | 变更                                                             |
| ---------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `src/main/java/com/openlibing/gateway/common/utils/JwtHelper.java`     | `verifyTokenAllowExpired` 捕获 `TokenExpiredException` 返回 null |
| `src/test/java/com/openlibing/gateway/common/utils/JwtHelperTest.java` | 新增 4 个真实签名回归用例                                        |

## 技术方案

auth0 java-jwt 的 `JWTVerifier.verify()` 校验顺序为：验签 → 声明断言（含 exp）。
`TokenExpiredException` 仅在验签通过后抛出，因此 catch 该异常返回 null 不引入
安全风险；其他 `JWTVerificationException`（签名非法、格式错误）继续向上抛出，
`AuthFilter.shouldAttemptSilentRefresh` 的 catch 分支据此拒绝触发刷新，
保持"伪造 token 不探测刷新通道"的安全语义。

调用方 `AuthFilter.shouldAttemptSilentRefresh` 无需改动：`decoded == null`
分支（原死代码）恢复生效，正确触发 `trySilentRefresh`。

## 安全评估

- 过期≠签名非法：返回 null 的前提是 HMAC 验签已通过，无认证绕过。
- 签名非法路径行为不变，fail-closed 语义保持。

## 验证方式

- `mvn test -Dtest=JwtHelperTest`（55 例，含 4 例新增）
- `mvn test -Dtest=AuthFilterTest`（95 例回归）
- pre-commit 全门禁（spotless/checkstyle/spotbugs/pmd/gitleaks）
