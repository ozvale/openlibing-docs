# 开源通告扫描包下载解析增强与安全加固 — 实现任务

## 进度: 6/6 complete

- [x] 新增 `CargoPackageUrlResolver`（static.crates.io 确定性直链 + rsproxy 镜像候选回落 + 无版本号 purl 经 API 取 max_version）与 `NugetPackageUrlResolver`（最新 stable + 无扩展名补 `.nupkg`）；修复 npm scoped purl `@` 双重编码
- [x] `manual_download_url` 分离：Liquibase 加列（幂等 + rollback）、`getEffectiveDownloadUrl` 生效地址口径统一（下载/缓存/文档/查询）、继承匹配键升级为 `(software_name, version, download_url)`、旧数据兼容回落
- [x] 下载执行器加固：SSRF sink 校验、手动逐跳重定向（≤5 跳逐跳校验、相对 Location 按当前跳解析）、`.part` 临时文件落盘、生态白名单补归档扩展名
- [x] 安全修复：startScan 调用方鉴权（#99）、NOTICE 合并内容注入中和 + content 长度上限（#100）、supplement 受理期 SSRF 预检（#105、#118）
- [x] 配套能力：`GET /display/config` 白名单端点（fail-closed、Nacos 实时读取）、`exportBatch` 返回 `skippedProductNames`（防御性拷贝）
- [x] PR #353（`ms_notice` → `release_20261029`）CI 通过（`ci-pipeline-passed`）、lgtm/approved 后已合入；新增/补充 8 个测试文件约 1200 行

## 后续（可选）

- [ ] issue #103（CmdInjection.runCmd 无超时）改动已从本 PR revert，需单独建 PR 交付
- [ ] Nacos 下发 `sca.notice.community.display.whitelist` 生产白名单，验证 NOTICE 入口展示控制
- [ ] beta 环境实测 pkg:cargo / pkg:nuget 扫描全链路（含 rsproxy 镜像回落与 .nupkg 解压）

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-sca/pull/353
- 业务 Issue: Fixes #99、#100、#105、#118（#103 未随本 PR 交付）
- 分支: `ms_notice` → `release_20261029`（已合入）
