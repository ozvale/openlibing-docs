# 技术设计：防投毒版本扫描 token 改为各社区项目 token

## 1. 总体方案

本需求分三块改造，全部集中在 `AntiServiceImpl.java`，另有 3 个关联小改动：

1. **token 获取链路重构**：`getPlatformPassworandUserName` 签名增加 `projectId`，按「项目公共账号 token → 平台配置 token」优先级取值，并新增 `decryptTokenQuietly` 统一解密容错。
2. **扫描容错**：扫描前 `Files.createDirectories` 确保目录存在；扫描结果为空时抛 `IOException` 替代 NPE。
3. **关联改动**：`.gitignore` 忽略运行时产物、SDK 升级、`PoisonPRController` 清理无用 javadoc。

## 2. token 获取链路设计

### 2.1 调用点改造

`runScan`（版本级扫描）中 token 获取从：

```java
List<String> platformInfo = this.getPlatformPassworandUserName(platform);
```

改为：

```java
List<String> platformInfo = this.getPlatformPassworandUserName(platform, antiEntity.getProjectId());
```

`antiEntity.getProjectId()` 是扫描任务关联的项目 ID，按项目维度取 token。

### 2.2 返回值校验增强

`platformInfo` 合法性判断新增第 3 个元素（token）的空白校验：

```java
if (platformInfo == null
    || platformInfo.size() != 3
    || StringUtils.isBlank(platformInfo.get(1))   // password
    || StringUtils.isBlank(platformInfo.get(2))) { // token 新增校验
  LOGGER.error("get platformInfo error");
  return MultiResponse.error(StatusCode.ERROR_50001, "get platformInfo error");
}
```

**理由**：此前 token 解密失败可能返回空字符串而不报错，导致后续 API 调用带空 token；显式校验空 token 提前失败，错误语义更清晰。

### 2.3 getPlatformPassworandUserName 重构

```text
getPlatformPassworandUserName(platformName, projectId)
  │
  ├─ 1. 按 projectId 查项目公共账号：projectInfoMapper.queryProjectCommonAccountInfoById(projectId)
  │
  ├─ 2. 平台密码解密（try/catch，失败 → return null）
  │      pass = "gitee" ? decrypt(giteeUserPassword.trim(), part1)
  │                     : decrypt(gitcodeUserPassword.trim(), part1)
  │
  ├─ 3. 项目 token 优先：
  │      若 projectCommonAccountInfoVO 非空 →
  │        token = "gitee" ? vo.getGiteeToken() : vo.getGitcodeToken()
  │        token = decryptTokenQuietly(token, projectId, platformName)   // 解密失败返回 null
  │
  ├─ 4. 降级平台配置 token：
  │      若 token 为空（项目未配置/解密失败）→
  │        log.warn("project common account token not found or decrypt failed ... fallback to platform config token")
  │        token = decryptTokenQuietly("gitee" ? giteeAccessToken : gitcodeAccessToken, ...)
  │
  ├─ 5. token 仍为空 → log.error(...) → return null
  │
  └─ 6. return [userName, pass, token]
```

### 2.4 decryptTokenQuietly 设计

```java
private String decryptTokenQuietly(String encryptToken, Integer projectId, String platformName) {
  if (StringUtils.isBlank(encryptToken)) {
    return null;
  }
  try {
    String token = SecurityUtil.decrypt(encryptToken.trim(), part1);
    return StringUtils.isNotBlank(token) ? token.trim() : null;
  } catch (Exception e) {
    LOGGER.error(
        "decrypt project common account token failed, projectId: {}, platform: {}, fallback to platform config token",
        projectId, platformName, e);
    return null;
  }
}
```

**要点**：

- `trim()` 去除加密串首尾空白（Apollo/DB 中可能携带空格，此前已出现过「配置有空格的」问题）
- 解密失败记 error 日志后返回 null，由上层决定降级，不把异常抛到业务链路
- **不打印 token 明文**，日志仅含 projectId + platformName

### 2.5 优先级与兼容性

| 场景                | 项目公共账号 token | 平台配置 token | 行为                                             |
| ------------------- | ------------------ | -------------- | ------------------------------------------------ |
| 新项目已配置        | ✅ 使用            | 不触达         | 项目 token                                       |
| 老项目未配置        | 空                 | ✅ 降级        | 配置中心 token（与升级前一致）                   |
| 项目 token 解密失败 | 解密失败 → null    | ✅ 降级        | 配置中心 token + error 日志                      |
| 两者都不可用        | 空                 | 空/解密失败    | return null → 调用方报「get platformInfo error」 |

## 3. 扫描容错设计

### 3.1 目录自动创建

扫描执行前：

```java
// 确保扫描结果目录存在（目录为运行时产物，不随镜像打包）
Files.createDirectories(
    Paths.get("/opt/app/openlibing/openlibing-anti-poison" + AntiConstants.SCANRESULTPATH));
```

**背景**：此前镜像不打包 `tools/softwareFile/report/` 目录，新部署环境目录缺失导致扫描工具写结果失败。扫描前显式创建，避免依赖人工建目录。

### 3.2 空结果 NPE 修复

```java
String result = ...; // 读取扫描结果文件内容
if (StringUtils.isBlank(result)) {
  throw new IOException(
      "scan result is missing or empty, please check scan tool logs: " + antiEntity.getRepoName());
}
List<ResultEntity> results = JSONArray.parseArray(result, ResultEntity.class);
```

**背景**：扫描结果文件存在但内容为空时，`parseArray` 返回空列表本不致 NPE，但空内容说明扫描工具异常；此前路径在空结果时可能继续处理导致 NPE。现在显式抛异常，语义为「扫描产物异常，需查扫描工具日志」。

## 4. 涉及文件清单

| 文件                      | 类型 | 说明                                                                                         |
| ------------------------- | ---- | -------------------------------------------------------------------------------------------- |
| `AntiServiceImpl.java`    | M    | token 获取重构（getPlatformPassworandUserName + decryptTokenQuietly）+ 目录创建 + 空结果校验 |
| `.gitignore`              | M    | 忽略 `tools/softwareFile/`（扫描引擎运行时产物目录）                                         |
| `pom.xml`                 | M    | openlibing-common SDK 1.0.20.4 → 1.0.21.0                                                    |
| `PoisonPRController.java` | M    | 清理无用 `@throws ExecutionException` javadoc                                                |

## 5. 风险与回滚

| 风险                                           | 应对                                                                                |
| ---------------------------------------------- | ----------------------------------------------------------------------------------- |
| 项目公共账号表无该 projectId 记录              | `queryProjectCommonAccountInfoById` 返回 null，直接降级平台配置 token，不影响扫描   |
| 项目 token 权限不足（比配置中心 token 权限小） | 扫描失败时 error 日志含 projectId，便于定位；可回退为在项目公共账号表补配正确 token |
| 解密失败误伤                                   | 解密失败仅降级不抛错，最大程度保证扫描可用性；error 日志辅助排查                    |
| 老项目行为变化                                 | 无变化：项目未配置 token 时与升级前走同一平台配置 token 路径                        |

## 6. 验证计划

| 场景                | 验证点                                                     |
| ------------------- | ---------------------------------------------------------- |
| 项目已配置 token    | 扫描时使用项目 token（日志/抓包确认无配置中心 token 调用） |
| 项目未配置 token    | 降级平台配置 token，扫描正常（老项目回归）                 |
| 项目 token 解密失败 | 降级平台配置 token，error 日志出现 decrypt failed          |
| 密码解密失败        | return null，调用方报「get platformInfo error」            |
| 新环境无报告目录    | 扫描前自动创建目录，扫描正常                               |
| 扫描结果为空文件    | 抛「scan result is missing or empty」，不 NPE              |
