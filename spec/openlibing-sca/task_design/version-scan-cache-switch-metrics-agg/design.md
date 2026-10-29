# 版本扫描缓存开关与扫描指标聚合优化 — 技术设计

## 方案概述

以运行时动态开关（`sca.version.scan.cache.switch`，Y/N）统一版本扫描看板的取数模式：Y 旁路 Redis（查库 + 指标实时 Mongo 聚合），N 走原有缓存路径；指标查询由逐 scanId 多次 count 重写为单条 Mongo 聚合管道并零填充空指标；定时预热改走不受开关影响的专用入口；附带 Gitee 文件下载 token/PR 号透传修复与 SBOM API 地址调整。

## 取数链路

```
GET /open/scan/repos
  → isScanCacheBypass()            # 请求入口解析一次，全程下传
  → 取数阶段
      cacheBypass=Y → 直接查库（完全旁路 Redis）
      cacheBypass=N → 结果集缓存命中/回源回填
  → 指标填充阶段
      cacheBypass=Y → fillMetricsFromMongo：单条聚合管道统计一批 scanId 的 9 项指标
      cacheBypass=N → fillMetricsFromRedis：读 PendingCountSchedule 30 分钟刷新的计数器
  → 筛选/排序/分页 → 日志输出 cacheBypass 与总耗时
```

## 关键决策

1. **开关用 `Environment` 实时读取而非 `@Value`**：`@Value` 是启动期注入，Nacos 刷新后不生效；`Environment.getProperty` 依赖 nacos-config 默认开启的动态刷新（刷新时会更新 Environment 的 property source），修改 `sca.version.scan.cache.switch` 无需重启。
2. **开关在请求入口解析一次并作为参数下传**：若取数与指标填充各自读取，动态刷新可能恰好落在两者之间，导致同一请求混用两种模式（例如取数走缓存、指标走 Mongo）。入口解析一次保证请求内模式一致。
3. **指标聚合为单条管道而非循环 count**：原实现每个 scanId 发起约 8 次 count，大社区（上千仓库）下接口超时。改为一条管道 `$match(scanId $in + blockStatus != BLOCK)` → `$group by scanId`，组内以 `$cond` 条件求和一次产出 9 项指标（total、pendingRiskNum、highRiskUnconfirmed、confirmedFileNum、confirmedByRobotNum、confirmedByManualNum、licenseUnconfirmed、copyrightUnconfirmed、licenseAndCopyrightUnconfirmed）。
4. **聚合口径与 Redis 计数器严格对齐**：total 为全部未屏蔽告警数（不看 reviewStatus）；其余按待处理（reviewStatus != 40）、已确认（== 40）、committerType auto/manual、licenseStatus/copyrightStatus FAIL 的组合区分，保证开关 Y/N 两种模式数据口径可比。
5. **无 Mongo 记录显式零填充**：该扫描在 `scan_issue` 无记录时 9 项指标置 0，与缓存路径 `toLong(null)=0` 口径一致，避免前端拿到 null 显示空白。
6. **预热走专用入口 `refreshScanCache`**：预热若复用用户查询入口，开关为 Y 时会"只删缓存不回填"，且每次白跑一次全量 Mongo 聚合。专用入口不受开关影响，始终回源重建并回填结果集缓存；`platform` 传值与用户查询不传 platform 时保持一致以命中同一缓存 key。
7. **聚合走 `getCollection(...).aggregate` 原生管道**：绕开实体映射开销，直接返回 `Document`，按 scanId 建映射后逐条填充。
8. **`RepoFileDto` 字段显式映射**：`majunAccessToken → token`、`pullsNumber → buildNumber` 字段名不一致，`BeanUtils.copyProperties` 静默拷不到——漏 token 下载请求无鉴权（401/403），漏 buildNumber 落 `PR-null` 目录。显式 setter 映射修复，并在下载失败日志中补充 responseCode 便于定位。
9. **gitee v5 status 容错**：gitee 对纯修改文件不填 status（JSON null），`getString` 抛 JSONException 中断整个扫描；改 `optString("status", "updated")` 缺省为 updated。

## 涉及文件

| 文件                                              | 操作      | 说明                                                                                                                |
| ------------------------------------------------- | --------- | ------------------------------------------------------------------------------------------------------------------- |
| `analysis/service/impl/OpenScanServiceImpl.java`  | 修改      | 缓存旁路开关、`fillMetricsFromMongo`/`aggregateScanMetrics` 单条聚合、零填充、`refreshScanCache` 专用入口、耗时日志 |
| `analysis/service/OpenScanService.java`           | 修改      | 新增 `refreshScanCache` 接口方法                                                                                    |
| `analysis/controller/OpenScanController.java`     | 修改      | 查询接口文档补充开关说明（替换原 no-cache 独立端点）                                                                |
| `common/schedule/VersionScanSchedule.java`        | 修改      | 预热改走 `refreshScanCache`（version/community × 全部/gitee/gitcode）                                               |
| `analysis/utils/security/DownLoadFilesUtils.java` | 修改      | token/buildNumber 显式映射、status 容错、失败日志带 responseCode                                                    |
| `common/feign/OpenlibingSbomClient.java`          | 修改      | `/sbom-api/` → `/internal-api/`（3 端点）                                                                           |
| 测试（3 个文件，约 260 行）                       | 新增/修改 | `OpenScanServiceImplTest`、`DownLoadFilesUtilsTest`、`VersionScanScheduleTest`                                      |

## 配置项

| 配置键                          | 默认 | 说明                                                                                                    |
| ------------------------------- | ---- | ------------------------------------------------------------------------------------------------------- |
| `sca.version.scan.cache.switch` | Y    | 版本扫描缓存旁路开关：Y 完全旁路 Redis（查库 + Mongo 实时聚合）；N 走原缓存路径。Nacos 动态刷新即时生效 |

## 风险与缓解

| 风险                                          | 缓解                                                                  |
| --------------------------------------------- | --------------------------------------------------------------------- |
| 旁路模式下大社区实时查库 + Mongo 聚合延迟仍高 | 聚合已收敛为单条管道；日志输出总耗时便于对比 Y/N；可随时切回 N 走缓存 |
| 开关 Y/N 两模式数据口径不一致导致对比失真     | 聚合条件与 `PendingCountSchedule` 计数器口径逐项对齐（见关键决策 4）  |
| 动态刷新时机导致请求内模式混用                | 开关入口解析一次下传，请求内取数与指标填充模式一致                    |
| SBOM 服务端未就绪 `/internal-api/` 路由       | 调用地址变更需与 openlibing-sbom 服务端发布对齐，合入前确认           |
| Mongo 聚合在大集合上全表扫描                  | `$match` 以 `scanId $in` 收敛范围；后续可按 scanId 建索引观察         |

## 跨仓影响

- openlibing-sbom：`OpenlibingSbomClient` 调用地址由 `/sbom-api/` 改为 `/internal-api/`，需服务端路由就绪（无代码改动）。
- 前端：无契约变化（原 no-cache 独立端点被开关替换，响应结构不变）。
- 无其他仓改动。
