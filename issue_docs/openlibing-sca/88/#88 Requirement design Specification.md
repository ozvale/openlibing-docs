# #349 版本扫描缓存开关与扫描指标聚合优化需求分析说明书

## 1. 基础信息

- **需求链接**: https://gitcode.com/openlibing/openlibing-sca/pull/349
- **需求名称**: 版本扫描缓存开关与扫描指标聚合优化（Version Scan Cache Switch & Metrics Aggregation）
- **开发责任人**: qq_39751731

---

## 2. 需求场景说明

> 描述"在什么情况下，为了解决什么问题，用户需要做什么"。

版本扫描看板查询 `/open/scan/repos` 是运营/社区用户查看扫描记录与告警指标的核心入口。当前实现存在三类问题：

**痛点一：指标查询性能瓶颈。** 看板指标（告警总数、待处理数、高低风险数、license/copyright 未确认数等）按 scanId 逐条发起约 8 次 Mongo count，大社区（上千仓库）下接口超时。

**痛点二：取数模式切换僵硬。** 看板只有"走 Redis 缓存（结果集缓存 + 每 30 分钟刷新的指标计数器）"一种路径，没有运行时开关在缓存模式与实时模式间切换，无法在 gamma 环境快速对比两种模式的数据正确性与性能差异，排查"缓存数据不准"类问题只能改代码重启。

**痛点三：null 指标。** 扫描在 Mongo `scan_issue` 集合中无记录时，各指标字段为 null，前端显示空白。

**附带缺陷**（同分支携带的 pr-scan 修复）：Gitee 文件下载漏传 token（下载请求无鉴权返回 401/403）、漏传 PR 号（文件落 `PR-null` 目录）；gitee v5 files 接口对纯修改文件不填 `status`（JSON null），`getString` 抛 JSONException 中断整个扫描。

**解决方案**：引入动态缓存旁路开关 `sca.version.scan.cache.switch`（Y/N），Y 旁路 Redis（查库 + 指标实时 Mongo 聚合），N 走原有缓存路径；指标查询重写为单条 Mongo 聚合管道并零填充空指标；定时预热改走不受开关影响的专用入口；同步修复 Gitee 下载缺陷并调整 SBOM API 调用地址。

## 3 需求验收标准

> 明确需求完成的标志，必须是可量化、可测试的。

- [x] 开关 Y（缺省）：`/open/scan/repos` 完全旁路 Redis——扫描记录直接查库，指标实时从 Mongo 聚合，无 Mongo 记录的扫描各指标显式为 0（非 null）
- [x] 开关 N：行为与原缓存路径一致（结果集缓存 + PendingCountSchedule 30 分钟刷新的计数器指标）
- [x] `sca.version.scan.cache.switch` 经 Nacos 修改后无需重启即生效；同一请求内取数与指标填充使用同一模式
- [x] 单条聚合管道各指标口径与 `PendingCountSchedule` 刷新 Redis 计数器的查询条件一一对应（total 不看 reviewStatus，其余按 pending `!=40` / confirmed `==40` / committerType auto/manual / license/copyright FAIL 组合区分）
- [x] `VersionScanSchedule` 定时预热在开关 Y/N 两种模式下均能正常回源重建并回填结果集缓存
- [x] Gitee 纯修改文件（status 为 null）不再导致扫描失败；下载请求携带 token、文件落盘目录 PR 号正确
- [ ] gamma 环境验证：开关 Y/N 两种模式下扫描指标查询正确性与性能对比
- [ ] 确认 openlibing-sbom 服务端 `/internal-api/` 路由已就绪

> 注：PR #349 已于 2026-10-29 合入 `release_20261029`（标签：ai-assisted / ci-pipeline-passed / approved / lgtm）。前六项为已实现并有单元测试覆盖的代码级验收项；最后两项为 gamma 环境验证项与 SBOM 服务端路由确认项，随合入后验证推进。

---

## 4 需求设计与分解

> 说明：基于初步方案，将需求拆解为可实施的原子 Task。

### 4.1 核心逻辑方案

#### 数据流向

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     看板查询链路（/open/scan/repos）                       │
│                                                                         │
│  前端                                                                    │
│    │ GET /open/scan/repos                                                │
│    ▼                                                                     │
│  OpenScanController.getScanByCommunity                                   │
│    │                                                                     │
│    ▼                                                                     │
│  OpenScanServiceImpl.getScanByCommunity                                  │
│    │                                                                     │
│    ├─ ① 开关解析（请求入口一次，全程下传）                                  │
│    │    isScanCacheBypass()                                              │
│    │    └─ Environment 实时读 sca.version.scan.cache.switch（缺省 Y）      │
│    │                                                                     │
│    ├─ ② 取数阶段（按 cacheBypass 分流）                                    │
│    │    Y → 直接查库（完全旁路 Redis）                                     │
│    │    N → 结果集缓存命中 / 未命中回源后回填                               │
│    │                                                                     │
│    ├─ ③ 指标填充阶段（与取数同模式）                                       │
│    │    Y → fillMetricsFromMongo：单条聚合管道统计一批 scanId 的 9 项指标   │
│    │       └─ 无 Mongo 记录的扫描 → 9 项指标显式置 0                        │
│    │    N → fillMetricsFromRedis：读 PendingCountSchedule 30 分钟刷新计数器│
│    │                                                                     │
│    └─ ④ 筛选 / 排序 / 分页                                                │
│         └─ 日志输出 cacheBypass 状态 + 接口总耗时（对比 Y/N 性能）           │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     指标聚合管道（cacheBypass=Y）                          │
│                                                                         │
│  scanIds（本次结果集去重后的扫描 ID 列表）                                 │
│    │                                                                     │
│    ▼                                                                     │
│  $match: { scanId: { $in: scanIds }, blockStatus: { $ne: BLOCK } }       │
│    ▼                                                                     │
│  $group: { _id: "$scanId",                                               │
│            total:                { $sum: 1 },                            │
│            pendingRiskNum:       $cond(reviewStatus != 40),              │
│            highRiskUnconfirmed:  $cond(pending && type == snippet),      │
│            confirmedFileNum:     $cond(reviewStatus == 40),              │
│            confirmedByRobotNum:  $cond(confirmed && committerType auto), │
│            confirmedByManualNum: $cond(confirmed && committerType manual)│
│            licenseUnconfirmed:   $cond(pending && lic FAIL && © != FAIL),│
│            copyrightUnconfirmed: $cond(pending && © FAIL && lic != FAIL),│
│            licAndCopyrightUnconf:$cond(pending && lic FAIL && © FAIL) }  │
│    ▼                                                                     │
│  Map<scanId, metrics> → 逐条填充 ScanInfoVO；无记录 scanId 零填充          │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     定时预热链路（VersionScanSchedule）                    │
│                                                                         │
│  定时任务 → 遍历社区 × repositoryType × platform                          │
│    │  删除旧缓存 key（community-version-platform-getScanByCommunity）     │
│    ▼                                                                     │
│  OpenScanService.refreshScanCache(community, type, platform)  ★ 新增     │
│    └─ 不受旁路开关影响，始终回源重建并回填结果集缓存                        │
│            （platform=null 须与用户查询不传 platform 时取值一致，           │
│              才能命中同一缓存 key）                                        │
└─────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────┐
│                     pr-scan 下载修复链路（DownLoadFilesUtils）             │
│                                                                         │
│  gitee files 接口 → DownloadFutureDto                                    │
│    ├─ status: getString → optString("status","updated")（null 容错）      │
│    ▼                                                                     │
│  createRepoFileDto：BeanUtils.copyProperties 之外显式映射                 │
│    ├─ majunAccessToken → token（漏拷 → 下载 401/403）                     │
│    └─ pullsNumber   → buildNumber（漏拷 → 落 PR-null 目录）               │
│    ▼                                                                     │
│  downloadFile：失败日志补充 responseCode                                  │
└─────────────────────────────────────────────────────────────────────────┘
```

#### 核心设计决策

1. **开关用 `Environment` 实时读取而非 `@Value`**：`@Value` 为启动期注入，Nacos 刷新后不生效；`Environment.getProperty` 依赖 nacos-config 动态刷新（刷新时更新 property source），修改开关无需重启。
2. **开关在请求入口解析一次并作为参数下传**：若取数与指标填充各自读取，动态刷新可能恰好落在两者之间，导致同一请求混用两种模式。入口解析一次保证请求内模式一致。
3. **指标聚合为单条管道而非循环 count**：原实现每个 scanId 约 8 次 count，大社区超时。改为一条管道 `$match(scanId $in + blockStatus != BLOCK)` → `$group by scanId`，组内 `$cond` 条件求和一次产出 9 项指标。
4. **聚合口径与 Redis 计数器严格对齐**：total 为全部未屏蔽告警数（不看 reviewStatus）；其余按待处理（reviewStatus != 40）、已确认（== 40）、committerType auto/manual、licenseStatus/copyrightStatus FAIL 的组合区分，保证 Y/N 两模式数据口径可比。
5. **无 Mongo 记录显式零填充**：与缓存路径 `toLong(null)=0` 口径一致，避免前端拿到 null 显示空白。
6. **预热走专用入口 `refreshScanCache`**：预热若复用用户查询入口，开关为 Y 时会"只删缓存不回填"，且每次白跑全量聚合。专用入口不受开关影响，始终回源重建并回填。
7. **聚合走 `getCollection(...).aggregate` 原生管道**：绕开实体映射开销，直接返回 `Document`，按 scanId 建映射后逐条填充。
8. **`RepoFileDto` 字段显式映射**：`majunAccessToken → token`、`pullsNumber → buildNumber` 字段名不一致，`BeanUtils.copyProperties` 静默拷不到，显式 setter 映射修复。
9. **gitee v5 status 容错**：纯修改文件 status 为 JSON null，`getString` 抛 JSONException 中断扫描；改 `optString("status", "updated")` 缺省 updated。

### 4.2 数据库设计

**无 MySQL schema 变更。**

MongoDB 侧使用既有 `scan_issue` 集合（`ScanIssueVO` 映射），本需求新增一条聚合查询，不写入数据：

| 项目     | 说明                                                                                                             |
| -------- | ---------------------------------------------------------------------------------------------------------------- |
| 集合     | `scan_issue`                                                                                                     |
| 查询形态 | `$match(scanId $in + blockStatus != BLOCK)` → `$group by scanId`（9 个 `$cond` 条件求和）                        |
| 匹配字段 | `scanId`（$in 批量）、`blockStatus`、`reviewStatus`、`type`、`committerType`、`licenseStatus`、`copyrightStatus` |
| 索引建议 | 若大集合上聚合执行计划为全表扫描，建议按 `scanId` 建索引并观察（列为后续可选项）                                 |

### 4.3 接口设计

##### 4.3.1 版本扫描看板查询接口（行为变化）

- **URL**: `/open/scan/repos`
- **方法**: POST
- **行为变化**: 取数路径受 `sca.version.scan.cache.switch` 控制（Y=查库+Mongo 实时聚合，N=缓存+计数器）；原 no-cache 独立端点被开关替换。请求/响应结构不变。
- **返回**: `JSONObject` - 扫描记录 + 指标（无记录指标为 0 非 null）

##### 4.3.2 缓存刷新入口（新增，内部）

- **方法**: `OpenScanService.refreshScanCache(community, repositoryType, platform)`
- **说明**: 预热专用，不受旁路开关影响，始终回源重建并回填结果集缓存；非对外 HTTP 端点。

##### 4.3.3 SBOM 服务调用地址变更（OpenlibingSbomClient）

| 端点               | 旧地址                         | 新地址                             |
| ------------------ | ------------------------------ | ---------------------------------- |
| queryProductConfig | `/sbom-api/queryProductConfig` | `/internal-api/queryProductConfig` |
| queryProduct       | `/sbom-api/queryProduct`       | `/internal-api/queryProduct`       |
| exportSbom         | `/sbom-api/exportSbom`         | `/internal-api/exportSbom`         |

> 需与 openlibing-sbom 服务端发布对齐，合入前确认新路由就绪。

##### 4.3.4 Gitee 文件下载（内部修复）

- gitee files 接口返回 `status=null` 时按 `"updated"` 处理（不再抛 JSONException）。
- 下载请求携带 token（显式映射 `majunAccessToken`），落盘目录携带 PR 号（显式映射 `pullsNumber`）。

### 4.4 配置清单

| 配置项                        | 说明                                                                                                       | 默认值 |
| ----------------------------- | ---------------------------------------------------------------------------------------------------------- | ------ |
| sca.version.scan.cache.switch | 版本扫描缓存旁路开关：Y 完全旁路 Redis（查库 + Mongo 实时聚合）；N 走原缓存路径。经 Nacos 动态刷新即时生效 | Y      |

### 4.5 任务清单

| 任务 ID   | 任务描述 (Task Description)                                                           | 预期产出 (Deliverables)                                                        | 涉及文件                                                                       |
| --------- | ------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------ |
| **task1** | 实现缓存旁路开关 `isScanCacheBypass`，请求入口解析一次下传，取数按开关分流            | 开关读取 + 取数分流逻辑                                                        | `OpenScanServiceImpl.java`                                                     |
| **task2** | 实现单条 Mongo 聚合 `aggregateScanMetrics` + `fillMetricsFromMongo`（含零填充）       | 聚合管道 + 指标填充 + 与 Redis 计数器口径对齐                                  | `OpenScanServiceImpl.java`                                                     |
| **task3** | 保留 Redis 指标路径 `fillMetricsFromRedis`（开关 N 模式）                             | 原计数器指标逻辑按开关接入                                                     | `OpenScanServiceImpl.java`                                                     |
| **task4** | 新增预热专用入口 `refreshScanCache` 并改造 `VersionScanSchedule`                      | 接口方法 + 预热改造（不受开关影响）                                            | `OpenScanService.java`、`OpenScanServiceImpl.java`、`VersionScanSchedule.java` |
| **task5** | 查询接口文档补充开关说明，替换原 no-cache 独立端点                                    | Controller javadoc 更新                                                        | `OpenScanController.java`                                                      |
| **task6** | Gitee 下载修复：token/buildNumber 显式映射、status null 容错、失败日志带 responseCode | 下载链路修复                                                                   | `DownLoadFilesUtils.java`                                                      |
| **task7** | SBOM API 调用地址 `/sbom-api/` → `/internal-api/`（3 端点）                           | Feign client 地址调整                                                          | `OpenlibingSbomClient.java`                                                    |
| **task8** | 单元测试：开关两模式、聚合零填充、下载修复                                            | `OpenScanServiceImplTest`、`DownLoadFilesUtilsTest`、`VersionScanScheduleTest` | test 目录 3 文件                                                               |

---

## 5 需求相关性分析

> **操作说明**：根据上述拆解出的 Task，识别其变更行为。任何一项勾选为"是"：打上对应issue标签，必须执行对应的流程门禁。全部未勾选：该需求自动判定为轻量化特性，打上need_light标签。

### A. 安全相关性分析

> *若涉及以下任一项，打标 `need_security`标签，PR 必须关联特性issue的架构设计文档（含安全设计部分）**如勾选需要给出原因**。

- [ ] **边界变更**：新增公网端口、修改防火墙规则、变更网关配置。
- [ ] **凭证处理**：涉及密钥（Secret/Key）、Token、证书的存储或分发。
- [ ] **权限调整**：修改权限模型、服务账号（SA）权限或鉴权逻辑。
- [ ] **供应链**：引入新的第三方二进制文件、SDK 或重大版本依赖升级。
- [ ] **隐私风险评估**：涉及用户个人数据（Email、手机号、IP、邮箱 等）的处理。
- [ ] **AI使用**：涉及AIGC能力应用，并提供服务。

### B. 架构设计相关性分析

> *若涉及以下任一项，打标 `need_design`标签，PR 必须关联特性issue的架构设计文档。 **如勾选需要给出原因**。

- [ ] A环节判定需要完成安全设计
- [ ] 改变了现有系统的物理/逻辑拓扑
- [x] 新增或大幅修改对外暴露的 API/CLI 接口 **[勾选必填]** _原因：`/open/scan/repos` 缺省取数路径由缓存改为实时查库 + Mongo 聚合，原 no-cache 独立端点被开关替换（端点级变化）；`OpenlibingSbomClient` 三个调用地址由 `/sbom-api/` 变更为 `/internal-api/`，依赖 openlibing-sbom 服务端路由同步就绪。_
- [ ] 引入了新的中间件、数据库或三方核心组件

### C. 系统集成测试相关性分析

> *若涉及以下任一项，打标 `need_itest`标签，PR必须关联特性issue的测试策略和测试报告文档。 **如勾选需要给出原因**。

- [ ] 上述环节判定需要执行安全设计或架构设计。
- [ ] **跨组件影响**：变更会触发下游服务或关联系统的连锁反应（级联效应）。 _原因：SBOM 调用地址变更依赖 openlibing-sbom 服务端 `/internal-api/` 路由；看板缺省切到实时查库 + Mongo 聚合后，Mongo/DB 压力与接口耗时需在 gamma 与缓存模式对比验证。_
- [ ] **核心组件管控**：含项目定级为 Core 的核心逻辑变更。
- [ ] **环境强依赖**：功能高度依赖内核参数、网络拓扑或特定的物理挂载。
- [ ] **端到端流程**：涉及从用户输入到持久化存储的全链路逻辑（前端→Controller→MongoDB+MySQL 双写→扫描继承→前端展示）。

### D. 用户体验相关性分析

> *若涉及以下任一项，打标 `need_ux`标签，PR必须关联特性issue的用户体验设计文档。 **如勾选需要给出原因**。

- [ ] **交互逻辑变更**：涉及 Web 门户、控制台（Dashboard）或命令行工具（CLI）的交互流程调整。
- [ ] **感知性能变动**：变更可能显著影响页面的加载时间、同步请求的响应时延或异步任务的进度反馈。 _原因：看板查询在开关 Y/N 两种模式下耗时特征不同（实时聚合 vs 缓存），需通过 gamma 性能对比确认用户可感知的响应时延无回退；无 Mongo 记录的指标由 null 变为 0，属展示层修正。_
- [ ] **文档与辅助能力**：涉及报错提示语、帮助中心链接、FAQ 或新功能的 Runbook 说明。
- [ ] **无障碍与多语种**：涉及国际化（i18n）支持、辅助功能或不同终端（移动端/桌面端）的适配。

### 5.1 需求相关性分析汇总结果

- [ ] need_security (需架构设计（含安全威胁分析和安全设计）)
- [ ] need_design (需架构设计)
- [ ] need_itest (需执行测试策略设计和全链路集成测试)
- [ ] need_ux (需架构设计（含UX设计）)
- [ ] need_light (上述均未勾选，走快速合入通道)
