# go-purl-ssrf-hardening — 实现任务

## 进度: 4/4 complete

- [x] Task 1（c3f88357）：`BasePackageUrlResolver#httpGet` 接入 `SsrfsafeUrlUtil.validateUrl`，
      改 `Redirect.NEVER` 并实现手动逐跳跟随（`MAX_QUERY_REDIRECT_HOPS=5`），抽出 `sendQueryGet` /
      `isRedirectStatus`
- [x] Task 2（c3f88357）：`GoPackageUrlResolver#queryGoImportSourceRepo` 增加 module host 结构预检
      （新增 `IPV4_HOST_PATTERN`、`extractModuleHost`）
- [x] Task 3（c3f88357）：`GoPackageUrlResolverTest` 新增 6 个回归用例
- [x] Task 4（c3f88357）：交付 commit

## 交付记录

| 项         | 内容                                                                                                                                                                                                                                                                                                                                                                                               |
| ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| commit     | `c3f8835785dab75b3d137f211af58921e13f1d35`（`fix(dm): block SSRF in versionless go purl go-import fallback`）                                                                                                                                                                                                                                                                                      |
| 分支       | `ms_scan`                                                                                                                                                                                                                                                                                                                                                                                          |
| 变更规模   | 3 文件，+192 / -7                                                                                                                                                                                                                                                                                                                                                                                  |
| 关联 issue | commit message 仅 `Refs #133`；#97 未显式引用（映射出入，见下）                                                                                                                                                                                                                                                                                                                                    |
| 验证方式   | `git show c3f88357` 核实 diff；静态核对当前代码中 `httpGet` / `queryGoImportSourceRepo` 最终形态                                                                                                                                                                                                                                                                                                   |
| 单测       | 新增 6 个：`resolve_versionlessPurl_ipModuleHost_rejectedWithZeroGoImportOutbound`、`resolve_versionlessPurl_singleLabelHost_rejectedWithZeroGoImportOutbound`、`toOfficialUrl_versionlessIpHostPurl_keepsPurlWithoutGoImportOutbound`、`httpGetText_linkLocalMetadataIp_rejectedBeforeOutbound`、`httpGetText_siteLocalIp_rejectedBeforeOutbound`、`httpGetText_localhost_rejectedBeforeOutbound` |
| 测试结果   | 本轮回溯未执行 `mvn test`（需私仓凭据），结果未验证                                                                                                                                                                                                                                                                                                                                                |

## 映射说明

- 提交 message 只写 `Refs #133`，但代码改动中的 `BasePackageUrlResolver#httpGet` SSRF 校验正是
  issue #97 指向的 sink，故 #97 由同一提交覆盖。
- 当前分支外的拆分提交 `9d3ae997`（`fix(dm): block blind SSRF in versionless go purl resolution`）
  message 同时包含 `Refs #133 #97`，但该提交不是 `ms_scan` 的祖先，不作为本批交付证据。
