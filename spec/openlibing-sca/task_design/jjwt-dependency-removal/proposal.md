# 108 jjwt-dependency-removal — 移除 jjwt 0.9.0 与死 TokenUtils 链路

## 需求背景

Issue：https://gitcode.com/openlibing/openlibing-sca/issues/108
（【安全】【ICSL安全缺陷】jjwt 0.9.0 已停止维护存在已知 CVE-2018-1000613，且与 java-jwt 3.19.1 双库并存，建议统一并升级）

`pom.xml` 直接依赖 `io.jsonwebtoken:jjwt:0.9.0`（仅排除 `jackson-databind` 传递依赖，CVE 本体在于 jjwt 自身的 base64/JAXB 反序列化路径，排除传递依赖无法规避）。该库在仓内的唯一使用链为：

`OpenScanDMService#getOperationalData(String token)` → `OpenScanDMServiceImpl#queryConfiguration` → `#getClaims2Token` → `TokenUtils#getClaimsFromToken`

归类：CVE-2018-1000613 / CWE-1104（Use of Unmaintained Third Party Components）。风险：解析不受信 JWT 的反序列化暴露面；双 JWT 库并存导致密钥与校验逻辑分散、维护成本与攻击面增加。

## 功能描述

**做什么**：

1. 删除 `pom.xml` 中 `io.jsonwebtoken:jjwt:0.9.0` 依赖块（含 `com.fasterxml.jackson.core:jackson-databind` exclusion）。
2. 删除 `TokenUtils`（`src/main/java/com/openlibing/sca/analysis/utils/TokenUtils.java`，103 行）与 `TokenUtilsTest`（237 行）。
3. 删除上述死链路：`OpenScanDMService#getOperationalData(String token)` 声明、`OpenScanDMServiceImpl#queryConfiguration` / `#getClaims2Token` / `getOperationalData(String)` 实现，以及 `API_TOKEN_FLAG` 常量、`TokenUtils` 字段注入、`io.jsonwebtoken.Claims` 与 `ErrorCode` 导入。
4. 裁剪 `OpenScanDMServiceImplTest` 中 `TokenUtils`、`queryConfiguration`、`getClaims2Token`、`getOperationalData` 相关 mock 与用例（-161 行）。

**不做什么**（与 issue 建议的差异）：

- 未"升级到当前受维护版本"（java-jwt 4.x 或 jjwt 0.12.x）：唯一使用链已删除，没有需要升级的调用点；
- 未处理 `com.auth0:java-jwt`：`pom.xml` 中并无该依赖的直接声明（`JwtUtils` 通过传递依赖使用），`JwtUtils` 已在 `5852b0d2` 删除，代码不再引用 `com.auth0.jwt`；该库是否仍留在解析后的依赖树中未验证；
- 未做依赖树/SBOM 复核，也未做第三方依赖扫描复跑。

## 验收标准

- [x] `jjwt 0.9.0` 从 `pom.xml` 移除（当前 `pom.xml` 中 grep `jjwt|java-jwt|auth0` 无命中）
- [x] 代码中无 `io.jsonwebtoken` 引用（全仓 grep 无命中）
- [x] 依赖该库的死链路删除，且无生产调用方（`getOperationalData(String)` / `queryConfiguration` / `getClaims2Token` 全仓无引用）
- [ ] 升级到受维护版本（本轮未覆盖：改为删除唯一使用点）
- [ ] 鉴权相关单测回归（`JwtUtilsTest` 已在 #91 删除，本轮无 JWT 单测可回归）
- [ ] java-jwt 是否仍在依赖树、是否需要显式收敛或排除（未验证）

## 影响范围

- 仓库：`openlibing-sca`（根 `pom.xml` + `dm` 模块）。
- 接口：无路由变化；`getOperationalData(String token)` 为无调用方的接口方法（当前保留的无参 `getOperationalData()` 同样全仓无调用方），删除不影响调用方。
- 依赖：移除一个直接依赖（jjwt 0.9.0）。
- 配置 / schema / 部署：无。
