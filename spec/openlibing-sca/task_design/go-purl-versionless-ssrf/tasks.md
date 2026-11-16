# go-purl-versionless-ssrf — 实现任务

## 进度: 4/4 complete

- [x] Task 1（c3f88357）：`GoPackageUrlResolver#queryGoImportSourceRepo` 增加 module host 结构预检，
      新增 `extractModuleHost` 与 `IPV4_HOST_PATTERN`
- [x] Task 2（c3f88357）：`BasePackageUrlResolver#httpGet` 接入 `SsrfsafeUrlUtil.validateUrl`，
      `Redirect.ALWAYS` → `Redirect.NEVER` + 逐跳校验手动跟随（≤5 跳）
- [x] Task 3（c3f88357）：`GoPackageUrlResolverTest` 新增 6 个 SSRF 回归用例
      （IP / 单标签零出站、toOfficialUrl 链路、link-local / site-local / localhost 拒绝）
- [x] Task 4（c3f88357）：交付 commit

## 交付记录

| 项         | 内容                                                                                                           |
| ---------- | -------------------------------------------------------------------------------------------------------------- |
| commit     | `c3f8835785dab75b3d137f211af58921e13f1d35`（`fix(dm): block SSRF in versionless go purl go-import fallback`）  |
| 分支       | `ms_scan`                                                                                                      |
| 变更规模   | 3 文件，+192 / -7                                                                                              |
| 关联 issue | `Refs #133`                                                                                                    |
| 验证方式   | `git show c3f88357` 核实 diff；静态核对当前 `queryGoImportSourceRepo`、`extractModuleHost`、`httpGet` 最终形态 |
| 单测       | 新增 6 个用例（名称见 `go-purl-ssrf-hardening/tasks.md` 交付记录）                                             |
| 测试结果   | 本轮回溯未执行 `mvn test`（需私仓凭据），结果未验证                                                            |

## 与 issue 建议的偏差

- 建议 1（`validateUrl` + 手动逐跳）：已落地。
- 建议 2（module host 白名单仅 github.com / golang.org / gitlab.com）：未按原样实现，
  改为拒绝纯 IPv4 与单标签 host，其余域名交由 `httpGet` 的 SSRF 校验兜底。
- 建议 3（回归测试）：IP / 单标签零出站与 httpGet 拒绝已覆盖；github 正常解析由既有用例继续覆盖，
  未新增专门用例。
- issue 中引用的 `GoPackageUrlResolver.java:380`、`BasePackageUrlResolver.java:209-213`
  为报告时点行号，当前代码分别位于 L390/L400 与 L209-L253（行号漂移，方法一致）。
