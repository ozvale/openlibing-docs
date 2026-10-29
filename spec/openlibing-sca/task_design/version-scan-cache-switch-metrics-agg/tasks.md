# 版本扫描缓存开关与扫描指标聚合优化 — 实现任务

## 进度: 5/5 complete

- [x] 缓存旁路开关：`sca.version.scan.cache.switch`（Y/N，缺省 Y）经 `Environment` 实时读取，请求入口解析一次下传；取数与指标填充按开关分流（查库/缓存 × Mongo 聚合/Redis 计数器），替换原 no-cache 独立端点
- [x] 指标聚合改造：重写为单条 Mongo 聚合管道（`$match scanId $in + blockStatus != BLOCK` → `$group by scanId` + `$cond` 条件求和），口径与 `PendingCountSchedule` 计数器对齐；无 Mongo 记录时 9 项指标零填充
- [x] 预热专用入口：`OpenScanService.refreshScanCache` 不受开关影响始终回源回填，`VersionScanSchedule` 改走该入口
- [x] pr-scan 修复：`RepoFileDto` 显式映射 token/buildNumber（401/403 与 PR-null 目录问题）、gitee status null 容错、下载失败日志带 responseCode；`OpenlibingSbomClient` 三个端点改 `/internal-api/`
- [x] 补充 `OpenScanServiceImplTest`、`DownLoadFilesUtilsTest`，更新 `VersionScanScheduleTest`；创建 PR #349（`ms_version` → `release_20261029`），补打 `ai-assisted` 标签

## 后续（可选）

- [ ] PR #349 CI 流水线完成并合入（当前进行中）
- [ ] gamma 环境验证开关 Y/N 两种模式下扫描指标查询正确性与性能对比
- [ ] 确认 openlibing-sbom 服务端 `/internal-api/` 路由已就绪
- [ ] 观察 Mongo `scan_issue` 集合按 scanId 查询计划，评估是否需要索引

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-sca/pull/349
- 分支: `ms_version` → `release_20261029`（进行中）
