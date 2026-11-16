# token-exposure-hardening — 实现任务

## 进度: 3/4 complete

- [x] Task 1: `ScanossFileDto.token` 加 `@ToString.Exclude`，`toString()` 不再输出 token（commit `2e309ec5`）
- [x] Task 2: gitee 文件检查鉴权改造 —— `getPrFileSize` 取 headerToken、`buildFileCheckUrl` 去 token 拼接、剥离存量 `access_token=` 片段、修正注释（commit `d5d284ed`）
- [x] Task 3: 单测更新 —— `testGetPrFileSize_Gitee_UsesHeaderToken`（新增）、`testBuildFileCheckUrl_Gitee`（改为否定断言）、`testBuildFileCheckUrl_Gitee_StripsLegacyAccessTokenFromConfig`（新增）（commit `d5d284ed`）
- [ ] Task 4: 单测实际执行 + 真实 gitee 环境回归（文件数检查正常、Bearer 被平台接受）（本轮未执行）

## 交付记录

| 项         | 内容                                                                                                                                        |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| commit 1   | `2e309ec5` fix(security): exclude token from ScanossFileDto toString（2026-11-03，1 文件 +2 / -1，Refs #140）                               |
| commit 2   | `d5d284ed` fix(security): move gitee file check token from URL to Authorization header（2026-11-03，2 文件 +59 / -9，Fixes #140、Refs #85） |
| 分支       | `ms_scan`（两 commit 均为 HEAD 祖先，`git merge-base --is-ancestor` 核实）                                                                  |
| 关联 Issue | #140（d5d284ed 为 Fixes，2e309ec5 为 Refs）；关联 #85 的 gitee Bearer 整改                                                                  |
| 验证方式   | 本轮只读核对代码最终形态（L508-570、`HttpClientUtil` L225-268、`ScanossFileDto` L30）与测试用例存在性；未执行 mvn test，未做真实环境回归    |

## 遗留（未在本次提交覆盖）

- `IntegrationApiServiceImpl.checkFileNum` 的 Javadoc（L606）仍描述"gitee 为 null，token 已拼入 URL"，与现状不符，建议后续清理。
- 未新增 `ScanossFileDto.toString()` 不含 token 的断言。
- 配置中心 `gitee.file.url` 模板中的 `access_token=` 需运维侧清理，代码仅做兼容剥离。

## 关联

- 对应 Issue：https://gitcode.com/openlibing/openlibing-sca/issues/140
- 同链路既有整改：本仓 spec 目录 `gitee-token-bearer-header`
