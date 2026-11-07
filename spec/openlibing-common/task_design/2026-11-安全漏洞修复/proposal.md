# 2026-11 安全漏洞修复

## 需求背景

公司团队对 openlibing-common 仓 master 检出多个安全问题，对应 issue 以【安全】命名。本批次在 `fix-current-issues` 分支上完成 6 处代码级漏洞修复，均与业务逻辑相关（CI workflow 类 issue #47/#48 单独由组织处理，不在本批次）。

## 功能描述

修复以下 6 处安全缺陷（不做/不做什么以每题清单为准）：

| Issue        | 缺陷                                                                                | 修复内容                                                                         |
| ------------ | ----------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| #51          | `AESCipher.toXor` 长度不一致静默返回全零数组，根密钥派生降级为可预测值（fail-open） | 长度不一致抛 `IllegalArgumentException`；`genRootKey` 增加三段成分长度一致性校验 |
| #46          | `JwtUtils.generateCookie` 未设置 SameSite，存在 CSRF 风险                           | Cookie 增加 `SameSite=Lax`                                                       |
| #52（第2条） | `ExternalLinkCheckUtils` 硬编码内源 OBS 公网域名                                    | 改为必配项 `external.default.image.url`（未配置启动失败）                        |
| #42-F6       | `PBDKF2Util` 口令入参用后未清理                                                     | PBEKeySpec 用后 `finally clearPassword()`                                        |
| #42-F2       | `ParameterExceptionInfoUtils` 异常审计日志将 requestBody 完整 JSON 明文入库         | 复用 `OperationLogPayloadSanitizer` 统一脱敏                                     |
| #50          | 搜索路径类 env（PATH/LD_LIBRARY_PATH 等）追加值未校验，可被劫持                     | 追加前校验绝对路径/存在/非符号链接/非禁止目录，不受信即拒绝                      |

## 验收标准

- [ ] 6 处修复均有匹配的单测覆盖（或说明原因）
- [ ] 全量单测通过（当前 418 个）
- [ ] Spotless / CheckStyle / SpotBugs / PMD 全部通过
- [ ] 每个修复独立 commit，均引用对应 issue（`Refs #<n>`）

## 影响范围

- openlibing-common 仓，共 6 个文件 + 5 个测试文件
- 下游服务需关注行为变化：新增必配项 `external.default.image.url`、Cookie 增加 SameSite、搜索路径 env 收紧、密钥派生 fail-closed（详见 design.md 风险小节）
