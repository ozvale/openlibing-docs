# 109 — 实现任务

## 进度: 4/4 complete

- [x] Task 1: `SsrfsafeUrlUtil` 新增 `resolveAndValidate` 返回核准地址集合；`doDownload` 改 OkHttp pinned DNS 并逐跳重新核准/重新 pin；`doGitDownload` 通过 `GIT_CONFIG_*` 注入 `http.curloptResolve`（`eb7cb58d`）
- [x] Task 2: SSRF 黑名单补齐 CGNAT 与特殊用途 IPv4 网段，IPv4-mapped IPv6 归一化（`3980eb33`）
- [x] Task 3: git clone 注入 `http.followRedirects=false` 重定向 fail-closed；IPv6 核准地址方括号形式（`b18855ba`）
- [x] Task 4: 单测补充（`SsrfsafeUrlUtilTest`、`ProjectNoticeScanExecutorTest`、`ProjectNoticeScanServiceImplTest`）+ 交付 commit

## 交付记录

| commit     | 日期       | 标题                                                                               | 关联                             |
| ---------- | ---------- | ---------------------------------------------------------------------------------- | -------------------------------- |
| `eb7cb58d` | 2026-11-06 | fix(notice-scan): pin connections to SSRF-approved addresses to stop DNS rebinding | Refs #143（同链路 DNS pin 子项） |
| `3980eb33` | 2026-11-06 | fix(analysis): block CGNAT and special-purpose IPv4 ranges in SSRF guard           | Fixes #142（同链路网段子项）     |
| `b18855ba` | 2026-11-11 | fix(notice-scan): reject git clone redirects to close SSRF gap                     | Refs #109                        |

- 分支：`ms_scan`（`openlibing-sca`）
- 本 issue 无单独 `Fixes #109` trailer；三个 commit 分别通过 Fixes #142 / Refs #143 / Refs #109 关联，按 BRIEF 映射归入本目录
- 验证方式：
  - 自动化：`ProjectNoticeScanExecutorTest` 新增 pinned 建连与重定向重 pin 用例（本地 `HttpServer` + `*.invalid` 主机名，只有pin 生效时才连到本地回环服务）；`SsrfsafeUrlUtilTest` 覆盖拒绝与返回集合
  - 手工：`b18855ba` 记录按批次 1 用例集 A8 验证「非重定向公网 clone 正常、重定向 clone 被拒绝」
  - 本轮为回溯补写文档，未重新执行 `mvn test`（测试通过性未验证）
- 已知残留：`HttpClientUtil` / `HttpUtil` / `BasePackageUrlResolver` 等出网路径仍只做 `validateUrl` 校验，未绑定核准地址（见 design「明确不在范围」）
