# 108 jjwt-dependency-removal — 技术设计

## 方案概述

`30cc574a` 一次性删除 `TokenUtils` 及其整条死调用链，同时移除 `pom.xml` 中的 `jjwt 0.9.0` 依赖。由于该库在仓内只服务这一条无人调用的链路，删除后不再有 JWT 解析代码，CVE-2018-1000613 的暴露面随使用点消失，而不是通过升级版本消除。

## 架构决策

| 决策                           | 证据 / 理由                                                                                                                                                                                                                                                       |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 删除依赖而非升级            | `TokenUtils#getClaimsFromToken` 只被 `OpenScanDMServiceImpl#getClaims2Token` 调用，后者只被 `queryConfiguration` 调用，再加一层 `getOperationalData(String token)`；该链路无生产调用方（提交说明 `only tests referenced them`），升级会保留无用代码与密钥配置负担 |
| D2 与 #91 顺序耦合             | `5852b0d2` 先删除 `JwtUtils`（java-jwt 侧）后，`OpenScanDMServiceImpl` 中的 `io.jsonwebtoken.Claims` / `TokenUtils` 成为孤立导入；`30cc574a` 再清理 jjwt 侧，两个提交分别对应两个库                                                                               |
| D3 连带删除 API token 校验开关 | `queryConfiguration` 读取 `tbl_category` 的 `api_token_flag` 决定是否校验动态 token；该方法无调用方，删除后不再存在"开关打开才校验"的分支，避免留下可被误用的半成品鉴权                                                                                           |
| D4 只删直接依赖                | `pom.xml` 中 `jjwt` 是唯一显式声明；`java-jwt` 并非直接声明，故本轮只移除 `jjwt` 一个依赖块，避免误改其他依赖版本                                                                                                                                                 |
| D5 测试随被测代码删除          | `TokenUtilsTest` 整文件删除（237 行）；`OpenScanDMServiceImplTest` 精简 161 行 mock/用例，不重写替代用例（无业务行为可测）                                                                                                                                        |

## 涉及文件

| 文件                                                                              | 操作 | 说明                                                                                                                                                     |
| --------------------------------------------------------------------------------- | ---- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `pom.xml`                                                                         | 修改 | 删除 `io.jsonwebtoken:jjwt:0.9.0` 依赖块及其 `jackson-databind` exclusion（-11 行）                                                                      |
| `src/main/java/com/openlibing/sca/analysis/utils/TokenUtils.java`                 | 删除 | JWT 解析组件（103 行）                                                                                                                                   |
| `src/main/java/com/openlibing/sca/analysis/utils/TokenUtilsTest.java`             | 删除 | -237 行                                                                                                                                                  |
| `src/main/java/com/openlibing/sca/dm/service/OpenScanDMService.java`              | 修改 | 删除 `getOperationalData(String token)` 声明                                                                                                             |
| `src/main/java/com/openlibing/sca/dm/service/impl/OpenScanDMServiceImpl.java`     | 修改 | 删除 `queryConfiguration`、`getClaims2Token`、`getOperationalData(String)`、`API_TOKEN_FLAG`、`TokenUtils` 注入、`io.jsonwebtoken.Claims` 导入（-64 行） |
| `src/test/java/com/openlibing/sca/dm/service/impl/OpenScanDMServiceImplTest.java` | 修改 | 删除相关 mock 与用例（-161 行）                                                                                                                          |

合计 6 个文件、-584 行。

## 风险 & 缓解

| 风险                                                    | 缓解                                                                                                                  |
| ------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| 误判"无调用方"                                          | 提交说明列出完整链路口径；当前全仓 grep `queryConfiguration` / `getClaims2Token` / `getOperationalData(String` 无命中 |
| 依赖树中仍有 jjwt（其他依赖传递引入）                   | 未验证；如需确认应执行 `mvn dependency:tree`（本次回溯未执行）                                                        |
| java-jwt 仍作为传递依赖存在，JWT 库"双库并存"未彻底消除 | 代码已无 `com.auth0.jwt` 引用；是否显式排除该传递依赖未验证，建议后续依赖治理单独跟踪                                 |
| 删除 API token 开关后，若有外部调用方依赖该鉴权语义     | `getOperationalData(String)` 无调用方（接口与实现均已删除），当前保留的无参 `getOperationalData()` 亦无调用方         |
| 测试覆盖下降                                            | 删除的是死代码测试，不降低有效覆盖率；本次未执行覆盖率统计                                                            |

## 跨仓影响

无。依赖变更仅影响本服务构建产物；spec 文档归档 `openlibing-docs` 仓。
