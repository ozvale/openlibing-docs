# 版本扫描缓存开关与扫描指标聚合优化（OpenScanService）

## 需求背景

版本扫描看板查询 `/open/scan/repos` 此前只有两种取数模式：走 Redis 缓存（结果集缓存 + 每 30 分钟刷新的指标计数器），或绕过缓存的独立 no-cache 端点。存在三个问题：

- **指标查询性能**：看板指标（告警总数、待处理数、高低风险等）按 scanId 逐条发起约 8 次 Mongo count，大社区（上千仓库）下接口超时。
- **模式切换僵硬**：缓存与实时查询之间没有运行时开关，切换取数模式需要改代码/重启，无法在 gamma 快速对比两种模式的数据正确性与性能。
- **null 指标**：扫描在 Mongo `scan_issue` 集合无记录时指标为 null，前端显示空白。

同分支还携带两个 pr-scan 下载链路缺陷修复（Gitee 文件下载漏传 token 导致 401/403、漏传 PR 号落错目录）与 SBOM API 接口地址调整。

## 功能描述

- **动态缓存旁路开关**：新增配置 `sca.version.scan.cache.switch`（Y/N，缺省 Y）。
  - Y（旁路）：扫描记录直接查库，指标实时从 Mongo 聚合统计，完全旁路 Redis。
  - N：走原有缓存路径（结果集缓存 + 定时刷新的指标计数器）。
  - 经 `Environment` 实时读取（依赖 nacos-config 动态刷新），Nacos 修改后无需重启生效；请求入口解析一次后全程下传，避免动态刷新落在取数与指标填充之间导致两种模式混用。
  - 查询日志标注 `cacheBypass` 状态与接口总耗时，便于对比 Y/N 性能差异。
- **扫描指标单条 Mongo 聚合**：重写为一条聚合管道（`$match: scanId $in + blockStatus != BLOCK` → `$group by scanId`，组内 `$cond` 条件求和），一次统计一批 scanId 的全部 9 项指标；无 Mongo 记录的扫描指标显式零填充（与缓存路径 `toLong(null)=0` 口径一致，避免前端拿到 null）。
- **预热专用入口**：`OpenScanService` 新增 `refreshScanCache(community, repositoryType, platform)`，`VersionScanSchedule` 定时预热改走该入口——不受旁路开关影响，始终回源重建并回填结果集缓存，避免开关为 Y 时预热退化为"只删不写"。
- **Gitee 文件下载修复**：`RepoFileDto` 显式映射 `token`（源 `majunAccessToken`）与 `buildNumber`（源 `pullsNumber`）——字段名不一致 `BeanUtils.copyProperties` 拷不到，漏 token 下载请求无鉴权（401/403），漏 buildNumber 落 `PR-null` 目录；gitee v5 对纯修改文件不填 `status`（JSON null），`getString` 抛 JSONException 导致扫描失败，改 `optString("status", "updated")`；下载失败日志补充 responseCode。
- **SBOM API 地址调整**：`OpenlibingSbomClient` 三个端点由 `/sbom-api/` 前缀改为 `/internal-api/`（`queryProductConfig`、`queryProduct`、`exportSbom`）。
- 新增 `OpenScanServiceImplTest`、`DownLoadFilesUtilsTest`，更新 `VersionScanScheduleTest`。

## 验收标准

- [ ] 开关 Y（缺省）：查询不走 Redis，指标实时 Mongo 聚合，无 Mongo 记录时指标为 0 而非 null。
- [ ] 开关 N：行为与原缓存路径一致（结果集缓存 + 计数器指标）。
- [ ] Nacos 修改 `sca.version.scan.cache.switch` 无需重启即生效；同一请求内取数与指标填充使用同一模式。
- [ ] `VersionScanSchedule` 预热在开关 Y/N 两种模式下都能正常回填结果集缓存。
- [ ] 单条聚合的各指标口径与 `PendingCountSchedule` 刷新 Redis 计数器的查询条件一致（total 不看 reviewStatus，其余按 pending `!=40` / confirmed `==40` / committerType auto/manual / license/copyright FAIL 组合区分）。
- [ ] Gitee 纯修改文件（status 为 null）不再导致扫描失败；下载请求携带 token、文件落盘目录 PR 号正确。
- [ ] SBOM 三个接口调用新 `/internal-api/` 地址正常。
- [ ] 单元测试通过（`OpenScanServiceImplTest`、`DownLoadFilesUtilsTest`）。

## 影响范围

- 仅 `openlibing-sca` 仓：9 文件 +545/−195（测试约 260 行）。
- **行为变化**：`/open/scan/repos` 缺省（开关 Y）从缓存读改为实时查库 + Mongo 聚合；原 no-cache 独立端点被开关替换。
- **内部接口变化**：`OpenScanService` 新增 `refreshScanCache`。
- **外部依赖**：`OpenlibingSbomClient` 调用地址变更，需确认 openlibing-sbom 服务端 `/internal-api/` 路由已就绪。
- 无 DB schema 变化、无部署链路变化；新增 Nacos 配置项一项。

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-sca/pull/349（`ms_version` → `release_20261029`，+545/−195，9 files，进行中）
