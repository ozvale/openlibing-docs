# openlibing-sca CodeQL 静态扫描安全问题修复 — 设计文档

## 1. 背景与目标

openlibing-sca 通过 CodeQL 静态扫描发现 81 处安全 / 代码质量问题。本分支（`codeql-fix`）围绕 **SSRF 防护、日志注入防御、日志质量、正则构造、JWT 解析、接口语义** 六类问题做系统性修复。

修复原则：

- **统一收敛**：SSRF 校验收敛为单一工具类 `SsrfsafeUrlUtil`，日志注入防御收敛为 `LogSanitizer`，避免同类逻辑散落。
- **行为兼容**：SSRF 拒绝与 IO 异常走同一降级路径（warn 日志 / 返回空结果 / 抛出既有业务异常），不改变既有调用方的异常契约。
- **可验证**：每类行为变化均配套单测调整或新增。

## 2. 修复分类与技术方案

### 2.1 SSRF 防护（CodeQL: `ssrf`）

**新增 `SsrfsafeUrlUtil.validateUrl(String url)`**（`com.openlibing.sca.analysis.utils`）：

| 校验维度 | 规则 |
|---------|------|
| 协议白名单 | 仅允许 `http` / `https`，否则抛 `IllegalArgumentException` |
| 主机名黑名单 | `localhost` / `127.0.0.1` / `0.0.0.0` 直接拒绝 |
| DNS 解析校验 | `InetAddress.getAllByName(host)` 逐地址检查：site-local / loopback / link-local 拒绝；解析失败（IOException）抛 `IllegalArgumentException` |
| 私网段校验 | 手写 IPv4 判定：`10.x` / `172.16-31.x` / `192.168.x` / `169.254.x`（链路本地）拒绝 |

接入点（4 种 HTTP 客户端全部覆盖）：

| 客户端 | 接入位置 | 行为 |
|-------|---------|------|
| OkHttp | `HttpClientUtil.sendPost` / `get` / `getResponse` | `sendPost` 捕获 `IllegalArgumentException` → warn 日志返回 null；`get`/`getResponse` 抛 IO 风格异常由调用方处理 |
| Apache HttpClient | `HttpUtil.doGet` | 捕获 `IllegalArgumentException` → error 日志返回空 body |
| RestTemplate | `OpenScanServiceImpl.showFileHash`（OSS 文件读取） | 先对 `fileHash` 做非法字符净化（`[\\/:*?"<>|\x00-\x1F\x7F]` → `_`），再 `validateUrl`，防止路径拼接注入 |
| URLConnection / Apache | `IntegrationApiServiceImpl`：`getRemoteBranch` / `checkoutBranch` / `checkRepoSizeAndSendToMq` / 其余 URL 请求 | 捕获 `IllegalArgumentException` → warn/error 日志，抛既有 `ScaException(500, ...)` 或返回既有降级值 |

**配套容错**（`GitCodeUtil.getUbmcToken` / `getUbmcUserInfo`）：`sendPost` 返回 null 时不再 NPE，warn 日志后返回空 `HashMap`。

### 2.2 日志注入防御（CodeQL: `log-injection`）

**新增 `LogSanitizer.sanitizeForLog(String)`**（`com.openlibing.sca.common.utils`）：

- 转义策略：`\` → `\\`，`\r` → `\r`（字面），`\n` → `\n`（字面），null 输入返回 null。
- 适用：业务日志中需要**保留原信息**的用户可控字段（repoUrl、prUrl、flag 等）。

**`DefaultExceptionHandler` 改造**：

- 新增 `UNSAFE_LOG_CHARS = [\r\n\t\f\u0000-\u001F\u007F]` 正则，私有方法 `sanitizeForLog` 将控制字符替换为 `_`（剥离式，用于异常日志）。
- 新增 `logHandledException(request, errorCode, errorMsg)`：参数化日志，携带请求上下文 —— `errorCode / errorMsg / uri / method / clientIp / userAgent / referer`，其中用户可控字段（URI / UA / Referer / IP）统一净化。
- 新增 `getClientIp(request)`：代理友好取 IP（`X-Forwarded-For` → `X-Real-IP` → `getRemoteAddr`，逗号截断）。
- 全部 `LOGGER.error(append.toString())` 替换为 `logHandledException(...)`；`request == null` 时记录无上下文日志，**避免原实现的递归 / NPE**（`bc3cbf67` 修复 null 分支无限递归）。
- `systemException` 分支使用不含请求上下文的参数化日志（异常自带 errorCode/errorMsg）。

**业务日志净化点**：`IntegrationApiServiceImpl`（prUrl、repoUrl）、`OpenScanServiceImpl`（flag 文件名分支）。

### 2.3 日志质量（CodeQL: `format-string` 等）

- 替换 25 处 `append.toString()` 字符串拼接日志为参数化日志（commit `5bd46778`）。
- `OpenPersonScanServiceImpl`：修复 `refreshVersionData` 日志缺失参数（补 `repoName`）；`refreshPersonData` 日志 `e.getMessage()` 改为参数化占位符。

### 2.4 正则构造修复（CodeQL: 逻辑告警）

`OpenScanDMServiceImpl.wildCard2RegEx` 与 `ShieldRoleServiceImpl.wildCard2RegEx` 对齐为**逐字符处理**：

```java
// 原实现：多轮 replace 链式替换，'.'与'\\' 存在顺序依赖，产生双重转义
String pattern = role;
pattern = pattern.replace('.', '#');
pattern = pattern.replaceAll("#", "\\\\.");
...

// 新实现：单遍扫描
StringBuilder sb = new StringBuilder();
for (int i = 0; i < role.length(); i++) {
  char c = role.charAt(i);
  if (c == '*')       sb.append(".*");
  else if (c == '?')  sb.append(".?");
  else if ("\\.[]{}()+^$|".indexOf(c) >= 0) sb.append('\\').append(c);
  else                sb.append(c);
}
return "^" + sb + "$";
```

### 2.5 JWT 解析修复

- `JwtUtils.getAccessToken`：新增 `sub = getClaimByName(token, "sub")`，写入返回 map。
- `OpenScanDMServiceImpl.scanPathConfirmParseV2`：`new HashMap<>()` 改为 `JwtUtils.getAccessToken(httpRequest)`，使 `"gitee".equals(mapToken.get("sub"))` 判定生效：gitee 用户不加前缀，gitcode 用户保留 `gitcode-` 前缀。

### 2.6 接口语义调整（GET → POST，共 9 个接口）

避免敏感参数出现在 URL / 访问日志，且 GET 不应产生副作用：

| Controller | 接口路径 | 调整 |
|-----------|---------|------|
| `BinaryLicenseController` | `/export/notice`、`/export/license/check` | GET → POST |
| `LicenseController` | `/export/community` | GET → POST |
| `OpenPersonScanController` | `/refreshVersionData`、`/refreshPersonData` | GET → POST |
| `OpenScanController` | `/putExportXLS`、`/export/community/count`、`/versionSchedule` | GET → POST |
| `TblScancodeInfoController` | `/getScanCodeInfo` | GET → POST |
| `OpenScanDMController` | `/refresh/confirmNum`、`/refresh/repoid-community-repo` | GET → POST |

### 2.7 工程配置

- 新增 `.gitignore`：排除 `target/`、`.trae/` 及 CodeQL 修复脚本产物。
- `.pre-commit-config.yaml`：各 hook 增加 `exclude: '^target/'`，避免 target 产物与测试 fixture 干扰检查。

## 3. 涉及文件清单

| 文件 | 改动 |
|------|------|
| `analysis/utils/SsrfsafeUrlUtil.java` | **新增**：SSRF 校验工具 |
| `common/utils/LogSanitizer.java` | **新增**：日志注入转义工具 |
| `common/exception/DefaultExceptionHandler.java` | 异常日志参数化 + 请求上下文 + 日志净化 + null 分支修复 |
| `analysis/utils/HttpClientUtil.java` | sendPost / get / getResponse 接入 SSRF 校验 |
| `analysis/utils/HttpUtil.java` | doGet 接入 SSRF 校验 |
| `analysis/utils/GitCodeUtil.java` | sendPost null 容错 |
| `analysis/utils/JwtUtils.java` | 返回 map 增加 sub claim |
| `analysis/service/impl/OpenScanServiceImpl.java` | showFileHash 净化 + SSRF 校验；flag 日志净化 |
| `analysis/service/impl/OpenPersonScanServiceImpl.java` | 日志参数补齐 + 参数化 |
| `analysis/service/impl/ShieldRoleServiceImpl.java` | wildCard2RegEx 重写 |
| `dm/service/impl/IntegrationApiServiceImpl.java` | SSRF 接入 + 异常兜底 + 日志净化 |
| `dm/service/impl/OpenScanDMServiceImpl.java` | wildCard2RegEx 对齐 + scanPathConfirmParseV2 取 sub |
| `analysis/controller/BinaryLicenseController.java` | 2 个接口 GET→POST |
| `analysis/controller/LicenseController.java` | 1 个接口 GET→POST |
| `analysis/controller/OpenPersonScanController.java` | 2 个接口 GET→POST |
| `analysis/controller/OpenScanController.java` | 3 个接口 GET→POST |
| `analysis/controller/TblScancodeInfoController.java` | 1 个接口 GET→POST |
| `dm/controller/OpenScanDMController.java` | 2 个接口 GET→POST |
| `test/.../JwtUtilsTest.java` | sub claim 断言 |
| `test/.../DefaultExceptionHandlerTest.java` | 移除 append.toString() mock |
| `test/.../OpenScanDMServiceImplTest.java` | mockStatic JwtUtils + sub 断言 |
| `.gitignore` | **新增**：排除 target 等产物 |
| `.pre-commit-config.yaml` | hook exclude target |

## 4. 设计决策

| 决策 | 理由 |
|------|------|
| SSRF 校验收敛为独立工具类 | 4 种 HTTP 客户端复用同一套校验规则，避免各自实现不一致 |
| 私网段判定用手写 IPv4 解析而非 `InetAddress.isSiteLocalAddress` 单独判断 | 两者结合：`isSiteLocalAddress` 覆盖 A/B/C 类私网与链路本地，手写规则补充明确拒绝 `169.254.x` 并便于测试 |
| SSRF 拒绝抛 `IllegalArgumentException` 而非 checked exception | 与既有 `HttpClientUtil.sendPost` 吞 IOException 的降级风格一致，调用方按 `IOException` 同路径处理即可 |
| 日志净化双策略（转义 / 剥离） | 业务日志保留可读信息用转义（`LogSanitizer`），异常日志强调安全性用剥离（`DefaultExceptionHandler` 内联） |
| `wildCard2RegEx` 逐字符单遍扫描 | 消除 replace 链的顺序依赖，`\`、`.` 等元字符显式转义，行为确定 |
| GET→POST 一次性调整 9 个接口 | 均为导出 / 刷新 / 触发类接口，不承载查询语义，调整后副作用语义清晰 |
| `.gitignore` 排除 `.trae/` 与修复脚本产物 | CodeQL 修复过程生成 `findings.json` / `fix_results.json` 等临时文件，不应入库 |

## 5. 风险与注意事项

- **SSRF 校验可能误伤合法内网调用**：若既有业务存在访问内网地址（如内部 OSS / 网关）的需求，`validateUrl` 会拒绝；需评估现有 URL 全部为公网地址后才合并（本分支已覆盖全部出站入口）。
- **`getRemoteBranch` / `checkoutBranch` 的降级**：SSRF 拒绝后抛出 `ScaException(500, ...)`，若前端对错误文案有断言需同步确认。
- **GET→POST 接口的调用方**：openlibing-web 前端及外部脚本需同步调整请求方法，否则 404/405。
- **`wildCard2RegEx` 行为等价性**：`ShieldRoleServiceImpl` 与 `OpenScanDMServiceImpl` 双处实现需保持一致，后续若再有修改应两处同步。
- **DNS 解析耗时**：`validateUrl` 内 `InetAddress.getAllByName` 触发 DNS 查询，高并发出站请求有轻微性能开销（可接受，未做缓存）。
