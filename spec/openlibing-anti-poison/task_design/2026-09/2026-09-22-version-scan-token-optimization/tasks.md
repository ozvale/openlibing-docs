# 实现任务：防投毒版本扫描 token 改为各社区项目 token

## 任务清单

### 1. token 获取链路重构

- [x] 1.1 注入 `ProjectInfoMapper`（`@Autowired`）
- [x] 1.2 `getPlatformPassworandUserName` 签名改为 `(String platformName, Integer projectId)`
- [x] 1.3 调用点 `runScan` 传入 `antiEntity.getProjectId()`
- [x] 1.4 `queryProjectCommonAccountInfoById(projectId)` 查询项目公共账号 token
- [x] 1.5 平台密码解密加 try/catch，失败 return null
- [x] 1.6 项目 token 非空时优先使用，经 `decryptTokenQuietly` 解密
- [x] 1.7 项目 token 为空/解密失败时降级平台配置 token（warn 日志）
- [x] 1.8 两者均空时 return null（error 日志含 projectId + platformName）
- [x] 1.9 新增 `decryptTokenQuietly(encryptToken, projectId, platformName)`：trim + 解密 + 失败 return null
- [x] 1.10 platformInfo 校验增加 `StringUtils.isBlank(platformInfo.get(2))`（token 空白校验）

### 2. 扫描容错

- [x] 2.1 扫描前 `Files.createDirectories(Paths.get("/opt/app/openlibing/openlibing-anti-poison" + AntiConstants.SCANRESULTPATH))` 确保报告目录存在
- [x] 2.2 扫描结果为空（`StringUtils.isBlank(result)`）时抛 `IOException("scan result is missing or empty...")`，替代 NPE

### 3. 关联改动

- [x] 3.1 `.gitignore` 追加 `tools/softwareFile/`（扫描引擎运行时产物目录）
- [x] 3.2 `pom.xml` openlibing-common SDK 1.0.20.4 → 1.0.21.0
- [x] 3.3 `PoisonPRController` 清理无用 `@throws ExecutionException` javadoc

### 4. 验证

- [ ] 4.1 编译通过（`mvn compile -q`）
- [ ] 4.2 项目已配置 token 的扫描任务：使用项目 token，扫描正常
- [ ] 4.3 项目未配置 token 的扫描任务：降级平台配置 token，扫描正常（回归）
- [ ] 4.4 项目 token 解密失败：error 日志出现 decrypt failed，降级成功
- [ ] 4.5 密码解密失败：返回 null，调用方报「get platformInfo error」
- [ ] 4.6 新环境无报告目录：扫描前目录自动创建，扫描正常
- [ ] 4.7 扫描结果空文件：抛「scan result is missing or empty」，不 NPE
- [ ] 4.8 grep 确认日志/代码无 token 明文打印

## 提交记录

| Commit                | 说明                                                                            |
| --------------------- | ------------------------------------------------------------------------------- |
| `69f238f`             | feat(scan): 版本扫描token改为优先从项目公共账号表获取                           |
| `0c32246`             | fix(scan): 项目token解密失败不再降级使用平台配置token                           |
| `9552c7a`             | fix(scan): token解密失败降级使用平台配置token并修复下载失败后的NPE              |
| `c915a60` / `6a62534` | fix(scan): 修复报告目录缺失导致扫描失败 / 扫描前确保报告目录存在并修复空结果NPE |
| `8b4cf67`             | build(deps): 升级 openlibing-common SDK 至 1.0.21.0                             |

## 关联 Issue

- [https://gitcode.com/openlibing/openlibing-anti-poison/issues/29](https://gitcode.com/openlibing/openlibing-anti-poison/issues/29)
