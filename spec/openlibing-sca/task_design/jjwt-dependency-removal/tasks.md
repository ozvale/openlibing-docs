# 108 jjwt-dependency-removal — 实现任务

## 进度: 3/3 complete

- [x] Task 1: 前置清理 java-jwt 侧 `JwtUtils` 链路（`5852b0d2`，与 #91 共用）
- [x] Task 2: 删除 `TokenUtils` 与 `TokenUtilsTest`，清理 `OpenScanDMServiceImpl` 的 `queryConfiguration` / `getClaims2Token` / `getOperationalData(String)` / `API_TOKEN_FLAG`（`30cc574a`）
- [x] Task 3: 从 `pom.xml` 移除 `io.jsonwebtoken:jjwt:0.9.0` 依赖块，并裁剪相关单测 mock（`30cc574a`）

## 交付记录

分支：`ms_scan`（`openlibing-sca`）

| commit     | 主题                                                               | 关联                                                                  |
| ---------- | ------------------------------------------------------------------ | --------------------------------------------------------------------- |
| `30cc574a` | refactor(dm): remove dead TokenUtils JWT chain and jjwt dependency | 提交 message 未写 `Refs #108`（按 issue 主题回溯关联）                |
| `5852b0d2` | refactor(auth): remove JwtUtils and JWT-based permission logic     | 前置：删除 java-jwt 使用方（详见 `../jwt-decode-without-signature/`） |

关键 diff：

- `pom.xml`：删除 `io.jsonwebtoken:jjwt:0.9.0` 及 `jackson-databind` exclusion。
- `OpenScanDMServiceImpl`：删除 `queryConfiguration`（含 `api_token_flag` 判断）、`getClaims2Token`、`getOperationalData(String token)`；移除 `TokenUtils` 注入、`API_TOKEN_FLAG` 常量、`io.jsonwebtoken.Claims` 与 `ErrorCode` 导入。
- `TokenUtils.java` / `TokenUtilsTest.java`：整文件删除。

验证方式：

- 静态核实：当前 `pom.xml` 无 `jjwt` / `java-jwt` / `auth0` 声明；全仓 grep `io.jsonwebtoken` / `com.auth0.jwt` / `JWT.decode` 无命中。
- 单测：`OpenScanDMServiceImplTest` 已裁剪关联用例；本次回溯未重新执行 `mvn test`，覆盖率未验证。
- 依赖树：未执行 `mvn dependency:tree`，jjwt 是否仍被传递引入未验证。
