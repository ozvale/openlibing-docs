# 安全漏洞修复

## 需求背景

安全平台扫描出 openlibing-common 代码仓的多个安全漏洞，需要逐一修复。

## 功能描述

修复 6 个安全漏洞，涉及路径遍历、输入校验、DoS、白名单绕过、配置管理、JWT 签名验证等问题。

## 验收标准

- [ ] 所有漏洞修复完成
- [ ] 相关测试补充/更新
- [ ] 代码质量检查通过（Checkstyle/SpotBugs/PMD/Spotless）

## 影响范围

- openlibing-common 仓
- 预计涉及多个工具类

## 漏洞清单

### 漏洞 1：ObsUtil.uploadObject 路径遍历风险

**问题**：`ObsUtil.uploadObject` 方法直接使用 `new File(filePath)` 创建文件对象，没有进行路径验证。如果调用者没有对路径进行安全检查，攻击者可能通过路径遍历访问或上传任意文件。

**修复方案**：使用 Path API 进行防御性校验

```java
Path path = Paths.get(filePath).toAbsolutePath().normalize();
Path canonical = path.toRealPath();  // 解析 symlink + 校验存在
if (!canonical.equals(path)) {
    throw new IllegalArgumentException("Symbolic link not allowed: " + filePath);
}
if (!Files.isRegularFile(canonical)) {
    throw new IllegalArgumentException("Not a regular file: " + filePath);
}
if (!Files.isReadable(canonical)) {
    throw new IllegalArgumentException("File not readable: " + filePath);
}
request.setFile(canonical.toFile());
```

**防御层**：

1. `normalize()` — 消除 `../` 遍历
2. `toRealPath()` — 解析符号链接并校验文件存在
3. `isRegularFile` — 排除目录
4. `isReadable` — 排除不可读文件
5. `setFile(canonical.toFile())` — 使用校验后的规范化路径

**不做的**：

- 白名单目录校验（改动太大，暂不实施）

### 漏洞 2：CsvValidator 缺少制表符/换行符检测

**问题**：`CsvValidator.java:19` 的正则 `^[=+\\-&\\\\@\"].{0,}` 只检测首字符是否为公式注入危险字符，未检测制表符 `\t`、换行符 `\n`、回车符 `\r`。攻击者可用这些字符破坏 CSV 文件结构（注入额外列/行）或绕过首字符检测注入恶意公式。

**修复方案**：在全角转换和 null 字节清理之后、正则匹配之前，增加全字符串范围的制表符/换行符/回车符检测

```java
if (convert.indexOf('\t') >= 0 || convert.indexOf('\n') >= 0 || convert.indexOf('\r') >= 0) {
    return true;
}
```

**选择全字符串检测而非仅首字符的原因**：

- `\t` 在任意位置都能拆出额外 CSV 列
- `\n`/`\r` 在任意位置都能拆出额外 CSV 行
- CSV 单元格内容本身不应包含这些字符
- 作为安全校验工具，严格比宽松更安全

### 漏洞 3：SecurityRandom 使用 SecureRandom.getInstanceStrong() 导致阻塞风险

**问题**：`SecurityRandom.java` 在静态初始化块和 `getInstanceStrong()` 方法中使用 `SecureRandom.getInstanceStrong()`，该方法在 Linux 上默认使用 `NativePRNGBlocking` 算法，读取 `/dev/random`。当系统熵池耗尽时会阻塞线程，攻击者可通过大量消耗熵池导致依赖此组件的服务阻塞，造成拒绝服务（DoS）。

**代码位置**：

1. 第 28 行静态初始化块：`random = SecureRandom.getInstanceStrong();`
2. 第 64-65 行 `getInstanceStrong()` 方法：`SecureRandom.getInstance(random.getAlgorithm())` + `random.generateSeed(20)`

**修复方案**：统一使用 `new SecureRandom()`

```java
static {
    random = new SecureRandom();  // 非阻塞，使用 /dev/urandom
}

public static SecureRandom getInstanceStrong() {
    SecureRandom newInstance = new SecureRandom();  // 非阻塞
    byte[] bytes = random.generateSeed(20);
    newInstance.setSeed(bytes);
    return newInstance;
}
```

**选择 `new SecureRandom()` 的理由**：

- Linux 上使用 `/dev/urandom`，不会阻塞
- 密码学安全性等同（业界共识：CSPRNG + 足够初始熵 = 安全）
- Google、AWS、Azure、GCP 等大厂统一推荐
- Linux 5.6（2020）起 `/dev/random` 和 `/dev/urandom` 行为已统一
- `SecureRandom.getInstanceStrong()` 在生产环境被视为反模式

**兼容性**：

- 方法名 `getInstanceStrong()` 保留不变，避免破坏调用方兼容性
- 更新 Javadoc 说明不再使用阻塞算法

### 漏洞 4：ExternalLinkCheckUtils 白名单绕过风险

**问题**：`ExternalLinkCheckUtils.java:48-49` 使用字符串前缀匹配 `imageUrl::startsWith` 检查 URL 是否在白名单域名中，而不是解析 URL 的 hostname。攻击者可以构造特殊 URL 绕过白名单检查，导致恶意图片链接被保留在 markdown 中，在用户浏览器中渲染，存在内容安全绕过风险（钓鱼、用户信息泄露等）。

**绕过示例**（假设白名单包含 `https://openlibing.obs.myhuaweicloud.com`）：

| 攻击 URL                                                   | `startsWith` 结果 | 实际访问                    |
| ---------------------------------------------------------- | ----------------- | --------------------------- |
| `https://openlibing.obs.myhuaweicloud.com.evil.com/xx.png` | ✓ 通过            | `evil.com`（子域名欺骗）    |
| `https://openlibing.obs.myhuaweicloud.com@evil.com/xx.png` | ✓ 通过            | `evil.com`（userinfo 注入） |

**修复方案**：解析 URL 并校验 hostname，不改变方法签名和调用方

```java
// 修改 filter 逻辑
.filter(domain -> isAllowedDomain(imageUrl, domain))

// 新增私有方法
private boolean isAllowedDomain(String imageUrl, String whiteDomain) {
    try {
        URL url = new URL(imageUrl);
        URL domainUrl = new URL(whiteDomain);
        String host = url.getHost();
        String whiteHost = domainUrl.getHost();
        return host.equals(whiteHost) || host.endsWith("." + whiteHost);
    } catch (MalformedURLException e) {
        return false;
    }
}
```

**防御层**：

1. `new URL()` 解析 — 正确提取 URL 结构
2. `getHost()` — 获取真实主机名，不受 userinfo/路径欺骗
3. 精确匹配 + 子域名匹配 — 防止 `evil.com` 冒充 `openlibing.com`
4. 异常处理 — URL 格式错误直接拒绝

**兼容性**：

- 方法签名不变
- 调用方使用方式不变
- 只改内部实现逻辑

### 漏洞 5：LoggerAspect 中 SMN projectId 硬编码默认值

**问题**：`LoggerAspect.java:63` 使用 `@Value("${ci.smn.projectId:2800e241e44a4d2d82861556acc1312f}")` 硬编码了华为云 SMN 项目的 projectId 默认值。虽然 projectId 本身不是密钥（单独无法攻击 SMN），但存在配置管理风险：

1. 不同环境（dev/test/prod）应使用不同 projectId，默认值可能导致环境误用
2. 硬编码在代码中，变更需重新发版
3. 违反 fail-fast 原则，配置缺失时静默使用错误值

**修复方案**：移除默认值，强制从配置文件读取

```java
@Value("${ci.smn.projectId}")
private String projectId;
```

**效果**：

- 配置缺失时启动失败，而非静默使用错误 projectId
- 强制各环境显式配置，避免环境误用
- 改动极小（仅删除 `:2800e241e44a4d2d82861556acc1312f`）

### 漏洞 6：JwtUtils.getClaimByName 未验证 JWT 签名

**问题**：`JwtUtils.getClaimByName` 方法仅使用 `JWT.decode()` 解码 token，不验证签名。攻击者可以伪造 JWT token（修改 payload 中的 userId、userName、accountId 等 claims），绕过认证机制。

**攻击路径**：

1. 攻击者构造伪造 token（修改 payload 中的用户信息，签名随意填写）
2. 调用使用 `getClaimByName` 的接口
3. `getClaimByName` 只解码不验证，直接返回伪造的 claims
4. 攻击者以任意用户身份执行操作

**修复方案**：在 `getClaimByName` 内部先验证签名再读取 claims

```java
public static Claim getClaimByName(String token, String name) {
    assertInitialized();
    DecodedJWT jwt = verifyToken(token);
    if (jwt == null) {
        log.warn("Token verification failed for claim: {}", name);
        throw new JWTVerificationException("Token verification failed");
    }
    return jwt.getClaim(name);
}
```

**调用方影响评估**：

| 调用位置                                                    | 异常处理            | 影响                                       |
| ----------------------------------------------------------- | ------------------- | ------------------------------------------ |
| `AbstractLogHandler:294-306`（openlibing-common）           | 无 try-catch        | **高风险**：审计切面异常会导致业务接口失败 |
| `ParameterExceptionInfoUtils:85-88`（openlibing-common）    | 无 try-catch        | 异常信息提取失败                           |
| `MultiRateLimitAspect:227`（openlibing-framework）          | 有 catch(Exception) | **无影响**                                 |
| `PrivacyProfileController:66,96`（openlibing-framework）    | 无 try-catch        | 正确行为：伪造 token 应被拒绝              |
| `PrivacyProfileServiceImpl:177,180`（openlibing-framework） | 无 try-catch        | 正确行为：伪造 token 应被拒绝              |

**额外修改**：

- `AbstractLogHandler.encapsulatingInfoFromRequest` 需要加 try-catch 保护，防止审计切面异常导致业务接口失败
