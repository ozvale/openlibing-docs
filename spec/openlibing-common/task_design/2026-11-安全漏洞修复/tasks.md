# 2026-11 安全漏洞修复 — 实现任务

## 进度: 6/6 complete

### Issue #51 AESCipher.toXor fail-open → fail-closed

- [x] `toXor` 长度不一致抛 `IllegalArgumentException`，不再静默返回全零
- [x] `genRootKey` 增加三段成分（part1/part2/part3）长度一致性校验
- [x] `AESCipherTest` 更新"长度不同返回零数组"断言为"抛异常"，补齐一致性用例

### Issue #46 JWT Cookie SameSite

- [x] `generateCookie` 增加 `.sameSite("Lax")`
- [x] `JwtUtilsTest` 断言 `cookie.getSameSite() == "Lax"`

### Issue #52（第2条）OBS 默认图 URL 必配化

- [x] `ExternalLinkCheckUtils` 去除硬编码域名，改为 `@Value("${external.default.image.url}")`
- [x] `ExternalLinkCheckUtilsTest` setUp 注入字段；新增空配置替换用例

### Issue #42-F6 PBEKeySpec 口令清理

- [x] `PBDKF2Util.getPBKDF2Bytes` try-finally 中 `keySpec.clearPassword()`
- [x] 既有 `PBDKF2UtilTest` 全覆盖，无行为变化

### Issue #42-F2 异常审计日志 requestBody 脱敏

- [x] `OperationLogPayloadSanitizer` 由 package-private 改 public（跨包复用）
- [x] `ParameterExceptionInfoUtils` 序列化前复用脱敏（含 requestBody）
- [x] 新增行为用例：password/token 打码、username 保留

### Issue #50 搜索路径 env 追加校验

- [x] `SecureCmdExecutor` 对 MULTI_VALUE_ENV_KEYS 追加前逐段校验（绝对路径/存在/非符号链接/非禁止目录）
- [x] 更新追加用例为绝对路径；新增相对路径与不存在绝对路径被拒用例

## 验证记录

- [x] 全量测试 418 个全部通过
- [x] Spotless / CheckStyle / SpotBugs / PMD 全部通过（pre-commit 逐 commit 验证）
- [x] 6 个独立 commit，均含 `Refs #<n>` + AI attribution footer
