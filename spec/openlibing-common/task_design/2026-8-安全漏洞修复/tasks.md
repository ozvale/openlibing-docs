# 安全漏洞修复 — 实现任务

## 进度: 0/6 complete

### 漏洞 1：ObsUtil.uploadObject 路径遍历风险

- [ ] 修改 `ObsUtil.uploadObject` 方法，添加路径规范化校验
- [ ] 补充测试用例（路径遍历、符号链接、目录、不可读文件）
- [ ] 运行测试验证

### 漏洞 2：CsvValidator 缺少制表符/换行符检测

- [ ] 在 `CsvValidator.validate` 方法中增加 `\t`/`\n`/`\r` 全字符串检测
- [ ] 补充测试用例（制表符注入、换行符注入、中间位置注入）
- [ ] 运行测试验证

### 漏洞 3：SecurityRandom 使用 SecureRandom.getInstanceStrong() 导致阻塞风险

- [ ] 修改静态初始化块，使用 `new SecureRandom()` 替代 `SecureRandom.getInstanceStrong()`
- [ ] 修改 `getInstanceStrong()` 方法，使用 `new SecureRandom()` 替代 `SecureRandom.getInstance(random.getAlgorithm())`
- [ ] 更新 Javadoc 说明不再使用阻塞算法
- [ ] 补充测试用例（验证非阻塞行为）
- [ ] 运行测试验证

### 漏洞 4：ExternalLinkCheckUtils 白名单绕过风险

- [ ] 新增 `isAllowedDomain` 私有方法，使用 URL 解析校验 hostname
- [ ] 修改 `replaceMarkdownExternalImageLink` 中的 filter 逻辑
- [ ] 补充测试用例（子域名欺骗、userinfo 注入、格式错误 URL）
- [ ] 运行测试验证

### 漏洞 5：LoggerAspect 中 SMN projectId 硬编码默认值

- [ ] 移除 `@Value("${ci.smn.projectId:2800e241e44a4d2d82861556acc1312f}")` 中的默认值
- [ ] 确认各环境配置文件已正确配置 `ci.smn.projectId`
- [ ] 运行测试验证启动行为

### 漏洞 6：JwtUtils.getClaimByName 未验证 JWT 签名

- [ ] 修改 `JwtUtils.getClaimByName`，内部调用 `verifyToken()` 验证签名
- [ ] 验证失败时抛 `JWTVerificationException`（RuntimeException，调用方无需强制捕获）
- [ ] 给 `AbstractLogHandler.encapsulatingInfoFromRequest` 加 try-catch 保护业务接口
- [ ] 补充测试用例（伪造 token、过期 token、合法 token）
- [ ] 运行测试验证
