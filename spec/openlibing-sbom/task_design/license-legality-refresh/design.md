# License 合规性数据自动刷新（license-legality-refresh）设计文档

> 需求背景：页面「OSI/FSF 认证 license / 非 OSI/FSF 认证 license」筛选读取 `license.is_legal`，该值目前只在 SBOM 解析时判定一次，貂蝉平台结论变化后无法同步，数据持续失真。本设计在批处理兜底新建 license 时接入貂蝉权威判定（主链路保持现状不接貂蝉），并以 xxl-job 每周全量校正存量数据。前端无改动、无表结构变化、无对外接口契约变化。

## 1. 方案设计

### 1.1 整体思路

在 openlibing-sbom 单仓内完成改造，围绕「貂蝉 /check 合规查询」新增一条独立的数据链路：批处理主链路保持现状，仅兜底新建 license 时查貂蝉落库，存量与失真值统一由 xxl-job 每周校正：

| 场景                                         | 现状口径                                                                    | 新口径                                                                                                                  |
| -------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 批处理主链路（ExtractLicensesProcessor）     | `!illegalLicenseList.contains(lic)`（compliance3/repo_meta 黑名单布尔判断） | **保持现状**，不接入貂蝉；主链路覆盖写入的失真值由 xxl-job 每周校正收敛                                                 |
| 批处理兜底（FillUpLicenseStep 新建 license） | 硬编码 `setIsLegal(true)`                                                   | 貂蝉从严口径：仅 ALLOW→true，其余（NOT_ALLOW/UNKNOW/调用异常）→新建且 is_legal=false（批处理唯一貂蝉触点）              |
| 存量数据校正（新增）                         | 无                                                                          | xxl-job 每周六 06:00 全量刷新；UNKNOW 跳过保留现值；支持管理台手动强制刷新                                              |
| 统计冗余同步（新增）                         | 无                                                                          | 刷新后重算受影响包的 `package_statistics.is_legal_license` 与受影响产品的 `product_statistics` 合法/非法 license 包计数 |

### 1.2 职责划分与涉及范围

- **前端（openlibing-web）**：不涉及。
- **后端（openlibing-sbom）**：
  - `interface` 模块：新增貂蝉客户端接口与结果枚举；
  - `clients` 模块：新增貂蝉 HTTP 客户端实现（WebClient，对齐 LicenseClientImpl 风格）；
  - `cache` 模块：新增貂蝉合规结果 Caffeine 缓存（12h TTL，清空缓存由刷新 service 注入 CacheManager 实现）；
  - `batch` 模块：兜底新建路径（FillUpLicenseStep）接入貂蝉；主链路（ExtractLicensesProcessor）保持现状不改动；
  - `sbom-web` 模块：新增 xxl-job handler 与刷新 service（含受影响统计冗余字段重算，见 2.6）。

### 1.3 验收标准

1. 手动/定时触发调度任务后，貂蝉已收录 license 的 `is_legal` 与貂蝉结论一致；UNKNOW 记录保持原值；调度日志完整输出查询总数、合规总数、不合规总数、未知总数。
2. 批处理兜底新建 license 时，貂蝉已收录的按貂蝉结论落库（未收录/调用异常→false）；主链路判定与覆盖行为保持现状不变。
3. 貂蝉服务不可用时：批处理不中断（兜底新建从严置 false，主链路不涉及貂蝉），调度任务单条失败不中断整体，均输出告警日志。
4. 刷新完成后，软件包列表「合规性」筛选结果与列表行内 license 红绿点一致（统计冗余字段已同步重算，见 2.6）。

## 2. 实现逻辑设计

### 2.1 貂蝉 /check 接口契约（实测确认）

- 请求：`GET {diaochan.api.url}?license=<spdxLicenseId>`；`diaochan.api.url` 配置为**完整 endpoint**（含 `/check`，如 `https://compliance.openeuler.org/check`），客户端仅在其后拼接 `?license=`，**不再追加任何路径**（杜绝 `/check/check` 二次拼接）；
- 响应：HTTP 200，body 为 JSON 字符串文本（带双引号），三值：
  - `"ALLOW"`：OSI/FSF 认证（合规）；
  - `"NOT_ALLOW"`：明确不合规；
  - `"UNKNOW"`：貂蝉未收录；
- 大小写不敏感；缺失 `license` 参数返回 400；响应出现未知取值时按 UNKNOW 处理并 warn（协议前向兼容）。

### 2.2 调度任务核心流程（refreshLicenseLegalityHandler）

```text
1. 清空 licenseCompliance 缓存（service 注入 CacheManager 实现，保证手动触发也是真实全量刷新）
2. licenseRepository.findAll() 加载全量 license（量级：千级）
3. 逐条 license：
   a. 调 LicenseComplianceCache.getLicenseCompliance(spdxId)（缓存已清，真实调用貂蝉）
   b. ALLOW  → 目标值 true；与现值不一致才 save
   c. NOT_ALLOW → 目标值 false；与现值不一致才 save
   d. UNKNOW → unknown++，跳过（保留现值）
   e. 调用异常 → failed++，error 日志，继续下一条（单条失败不中断）
   f. 连续失败 ≥ 20 条 → 熔断：提前 handleFail 退出（防止貂蝉持续不可用时
      重试放大拖垮任务、xxl 超时被杀，见 2.5/5）
4. 统计冗余同步（对账式自愈，不依赖本次值变化集合）：一条对账查询找出
   package_statistics.is_legal_license 与其关联 license 实际聚合值
   （allMatch，含无关联 license → null 边界）不一致的 package 集合，
   对该集合重算 package_statistics 并联动受影响 product_statistics
   的合法/非法 license 包计数（见 2.6）——任务中途被杀后，下一轮
   运行的对账会自动覆盖此前遗漏的重算（自愈）
5. 结果判定与汇总：
   - 正常：XxlJobHelper.handleSuccess 输出查询总数 / 合规总数 / 不合规
     总数 / 未知总数 / 更新数 / 失败数
   - handleFail（+ error 告警）条件：needRequest()==false（URL 未配置）、
     触发连续失败熔断、全量失败、unknown 占比 > 80%（防貂蝉协议/网关
     变化导致全量 UNKNOW 时静默成功、数据陈旧无告警）
```

- cron `0 0 6 ? * SAT`（每周六 06:00）在 xxl 管理台配置（代码不写 cron，对齐 pendingVulCleanHandler 注释模式）；路由策略单实例、阻塞策略丢弃后续。
- 任务可重入：值相同的 license 重跑时跳过 save；统计重算为对账式、与值变化集合解耦，任务中途被杀（xxl 超时/executor 重启）后下一轮运行自动修复遗漏的统计重算。

### 2.3 批处理主链路口径（ExtractLicensesProcessor，保持现状）

主链路不接入貂蝉，判定与覆盖落库行为完全保持现状：

```text
保持不变：getLicenseCache(lic, getLicenseLegality(illegalLicenseList, lic))

fallback = !illegalLicenseList.contains(lic)   // 现有黑名单口径原样保留
```

- openEuler 产品的 illegalList 来自 repo_meta 缓存，其他产品来自 compliance3 `/lic`，降级链路不变；
- `LicenseObjectCache.getLicenseCache` 本身不改动，覆盖落库行为维持现状。

**主链路缓存逻辑背景（评审确认，固化结论）**：

- **为什么有这层缓存**：一次批处理会解析大量 SBOM，同一 license 会跨包/跨 SBOM 反复出现，为避免对同一 license 重复「查库 + 写库」，`getLicenseCache` 设计了进程内 `@Cacheable` 缓存（LICENSE_OBJECT：key = `spdxId + '_' + legality`、容量 1000、写后 1h 过期、cacheNullValue=true）。key 携带 legality 是因为不同包的黑名单口径可能不同：(spdxId, legality) 组合各自独立缓存，同口径请求直接复用缓存实体、跨口径请求各自触发落库。
- **现状行为链**：缓存命中 → 跳过方法体、不碰 DB；缓存未命中 → `findBySpdxLicenseId` 查库，**无论 license 是否已存在都执行 `setIsLegal(传入值)` + `save()`**（存在 = 覆盖更新、不存在 = 新建）。即主链路并非「库里有就跳过不更新」。
- **由此产生的失真背景**：is_legal 最终值取决于最后一次批处理的判定口径（后写覆盖先写），且缓存仅本进程实例有效（重启 / 多实例部署不共享，重新落库）——这正是需要引入貂蝉实时判定的动机。
- **本方案下的定位**：不改动该类与缓存配置。主链路仍按黑名单口径写入、可能写回失真值（现状行为保留，接受由调度兜底校正）；批处理中貂蝉权威值的唯一入口是兜底新建（见 2.4）；主链路写入与调度刷新的交叉收敛依赖每周全量校正（见 2.2）与对账式统计重算（见 2.6），不引入跨链路锁。

### 2.4 批处理兜底口径（FillUpLicenseStep.toLicense）

- 仅对 `existLicenses` 中不存在而新建的 license 生效（已有 license 直接返回，不触发貂蝉调用）；
- 新建时 `setIsLegal(resolveLicenseLegalityStrict(spdxId))`（独立从严语义方法），从严控制：**仅 ALLOW→true；NOT_ALLOW / UNKNOW（貂蝉未收录视同非 OSI/FSF 认证）/ 调用异常（无法确认合规）一律 false**，正常新建 license 且默认不合规；该路径为批处理中唯一触发貂蝉查询的入口；
- 新建的 license 随 `licenseRepository.saveAll(existLicenses.values())` 统一落库，落库方式不变。

### 2.5 异常与边界处理

| 场景                        | 处理                                                                                                                                                                                                                    |
| --------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 貂蝉超时 / 5xx / 网络不可达 | WebClient 配置 connect/response 超时 + `Retry.backoff(3, 1s)`，耗尽后抛异常；@Cacheable 异常不缓存；兜底新建从严置 false、调度任务跳过该条（主链路不涉及貂蝉）                                                          |
| 貂蝉持续不可用（调度任务）  | 连续失败 ≥ 20 条熔断提前 handleFail 退出：最坏耗时上界 ≈ 20 × (单次超时 + 7s 退避) ≈ 10 分钟量级，远低于 60 分钟 xxl 超时，避免任务被杀留下统计不同步                                                                   |
| 响应文本非三态              | 按 UNKNOW 处理 + warn 日志（保留协议演进空间）                                                                                                                                                                          |
| 响应带引号 / 纯文本         | 按 JSON 字符串解析，解析失败 fallback 去引号 trim 比对                                                                                                                                                                  |
| `diaochan.api.url` 未配置   | 客户端 `needRequest()=false`：批处理兜底新建按从严口径置 false；调度任务 handleFail 告警退出                                                                                                                            |
| 调度任务与批处理并发        | 缓存层仅引发回源重查；DB 逐行 update 无锁冲突。**已知窗口（设计接受）**：主链路保持现状按黑名单口径写入，可能覆盖调度刚刷新的权威值；收敛机制——每周调度全量校正（见 2.2）+ 对账式统计重算自愈（见 2.6），不引入跨链路锁 |
| 结果判定阈值                | handleFail 条件：needRequest==false、连续失败熔断、全量失败、unknown 占比 > 80%（防协议/网关变化致全量 UNKNOW 时静默成功、数据陈旧无告警）；其余 handleSuccess 汇总输出                                                 |

### 2.6 页面筛选数据来源分析与统计冗余同步（评审新增）

软件包列表 license 表头筛选面板三组选项的来源与本次改造的影响（已核实前端 openlibing-web 与后端查询实现）：

| 筛选项                                            | 选项/过滤数据来源                                                                                                                                                                     | 是否需调度后刷新                                                                                                |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| License 名称标签（可搜索多选，如 MIT/Apache-2.0） | 前端每次进页面调 `queryProductStatistics` 接口**现查**，数据源为 `product_statistics.licenseDistribution`（JSONB Map&lt;spdxId, 包数&gt;，由批处理 CollectStatisticsStep 写入）       | 否：键值只含 license 名称→包数，与 is_legal 无关，名称集合不因刷新变化                                          |
| License 数量（无/单/多）                          | 前端写死常量；后端按 `package_statistics.license_count` 过滤                                                                                                                          | 否：与 is_legal 无关                                                                                            |
| License 合规性（OSI/FSF 认证/非认证）             | 前端写死常量（LEGAL/ILLEGAL）；后端过滤条件为 **`package_statistics.is_legal_license = TRUE/FALSE`**（批处理时经 `allMatch(pkg_license_relp → license.is_legal)` 聚合写入的冗余字段） | **是：`license.is_legal` 刷新后该冗余字段不会自动更新，必须同步重算，否则合规性筛选结果与列表行内红绿点不一致** |
| 列表行内 license 红绿点                           | 查询时实时经 `pkg_license_relp → license.is_legal` 组装（`LicenseVo.fromLicense`）                                                                                                    | 无需动作，实时反映刷新结果                                                                                      |

受影响冗余字段与同步策略（在刷新 service 差异化落库后执行）：

1. **package_statistics.is_legal_license**（对账式自愈）：一条对账查询找出统计字段与其关联 license 实际聚合值不一致的 package 集合（聚合口径 `allMatch(license.isLegal)`，包无关联 license 时为 null，与 `CollectStatisticsStep.collectPackageLicenseStatistics` 一致）→ 对不一致集合重算并批量保存；**不依赖本次值变化集合**——任务中断后下一轮运行的对账自动覆盖遗漏重算；
2. **product_statistics.packageWithLegalLicenseCount / packageWithIllegalLicenseCount**：对对账出的不一致 package 所属 sbom（产品）重算合法/非法 license 包计数，语义对齐 CollectStatisticsStep 现有聚合；
3. `license_distribution`、`license_count`、`licenses` 数组不涉及合法性，不做改动。

## 3. 类设计

### 3.1 新增类

| 类                              | 模块                                                                                  | 职责与关键签名                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| ------------------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DiaochanClient`                | interface（`org.opensourceway.sbom.api.license`）                                     | 貂蝉合规查询接口：`DiaochanCheckResult checkLicense(String spdxLicenseId)`、`boolean needRequest()`                                                                                                                                                                                                                                                                                                                                                                                                                                            |
| `DiaochanCheckResult`           | interface（同包枚举）                                                                 | 三态：`ALLOW` / `NOT_ALLOW` / `UNKNOW`                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                         |
| `DiaochanClientImpl`            | clients（`org.opensourceway.sbom.clients.license`）                                   | WebClient GET `{diaochan.api.url}?license=<spdxId>`（配置值为完整 endpoint 含 `/check`，不再追加路径）；`@Value("${diaochan.api.url:}")`；响应解析三态；connect/response 超时 + `Retry.backoff(3, 1s)`；风格对齐 LicenseClientImpl（复用 WebClientUtil.connector、`spring.codec.max-in-memory-size`）                                                                                                                                                                                                                                          |
| `LicenseComplianceCache`        | cache（`org.opensourceway.sbom.cache`）                                               | 对齐 LicenseObjectCache 结构（`@Configuration` + `@Bean CacheProperties` + `@Cacheable`），**不注入 CacheManager**（CacheManager 构造需收集 List&lt;CacheProperties&gt;，若缓存类反向注入 CacheManager 会形成循环依赖）：① `@Bean CacheProperties licenseComplianceCacheProperties()`：cacheName=`licenseCompliance`、maximumSize=5000、expireAfterWrite=12h（43200s）、cacheNullValue=false；② `@Cacheable` 方法 `DiaochanCheckResult getLicenseCompliance(String spdxLicenseId)`（内部委托 DiaochanClient）；清缓存职责放 service 侧（见下） |
| `LicenseLegalityRefreshService` | sbom-web（`org.opensourceway.sbom.service.license`，风格对齐 PendingVulCleanService） | `RefreshSummary refreshAllLicenses()`：注入 CacheManager 清 licenseCompliance 缓存 → 全量查询 → 差异化落库 → 对账式统计冗余重算（见 2.6）→ 结果判定（unknown 占比 >80% / 连续失败 ≥20 条 / 全量失败 → 抛出由 handler handleFail）→ 返回统计；内部记录 total/legal/illegal/unknown/updated/failed、连续失败计数                                                                                                                                                                                                                                 |
| `LicenseXxlJobHandler`          | sbom-web（`org.opensourceway.sbom.handler`，与 VulXxlJobHandler 同级）                | `@XxlJob("refreshLicenseLegalityHandler")`：调用刷新 service，`XxlJobHelper.handleSuccess/handleFail` 汇总日志                                                                                                                                                                                                                                                                                                                                                                                                                                 |
| `RefreshSummary`                | sbom-web（service 内部 POJO 或嵌套类）                                                | 刷新统计结果载体                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                               |

### 3.2 修改类

| 类                                                                                                      | 模块  | 改动点                                                                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CacheConstants`                                                                                        | cache | 新增 `LICENSE_COMPLIANCE_CACHE_NAME = "licenseCompliance"` 与对应 key 常量（`#spdxLicenseId`）                                                                                                                                                                              |
| `FillUpLicenseStep`                                                                                     | batch | 注入 `LicenseComplianceCache`；`toLicense` 新建分支 `setIsLegal` 改为独立从严方法 `resolveLicenseLegalityStrict(spdxId)`（仅 ALLOW→true，UNKNOW/调用异常→false，批处理唯一貂蝉触点）                                                                                        |
| 相关 Repository（PkgLicenseRelpRepository / PackageStatisticsRepository / ProductStatisticsRepository） | dao   | 新增对账查询：聚合 pkg_license_relp + license 实际 is_legal（allMatch，含无关联 → null）与 package_statistics.is_legal_license 比对，返回不一致的 package 集合；加载不一致 PackageStatistics（含 relps）并批量保存；按不一致 package 所属 sbom 聚合合法/非法 license 包计数 |

类间关系：`LicenseXxlJobHandler → LicenseLegalityRefreshService → LicenseComplianceCache → DiaochanClient`；`FillUpLicenseStep → LicenseComplianceCache`（批处理仅兜底新建接入）；清空缓存由 `LicenseLegalityRefreshService` 注入 `CacheManager` 实现，`LicenseComplianceCache` 不反向持有 `CacheManager`（避免与 CaffeineCacheConfig 收集缓存配置产生循环依赖，对齐 LicenseObjectCache 结构）。

## 4. 数据模型设计

不涉及。本次仅改变 `license` 表既有 `is_legal` 字段（boolean）值的刷新机制与判定来源，无表结构、索引、迁移变化；不新增表。

## 5. 性能设计

- **批处理（高频、重复度高）**：主链路零貂蝉调用（保持现状性能特征）；仅兜底新建 license 时查貂蝉，同 chunk 与跨 chunk 重复 license 命中 Caffeine 缓存（5000 条 / 12h）仅 cache miss 时发起 HTTP；貂蝉单次查询为轻量 GET（实测百毫秒级），新建频次低，增量可忽略。
- **调度任务（每周一次）**：入口清缓存后全量真实调用，串行执行。按千级 license × 百毫秒级单次耗时估算，整体分钟级，远小于 xxl 超时上限；仅对值变化的记录 save，DB 写量小。一期保持串行（简单可靠），若 license 规模增长到万级再引入受控并发。
- **服务退化场景耗时上界（Retry 放大效应）**：貂蝉持续不可用且每次调用耗尽重试（Retry.backoff(3, 1s)，3 次重试 + 退避约 7s + 超时）时，连续失败 ≥ 20 条即熔断退出，最坏耗时上界 ≈ 20 × (单次超时 + 重试退避) ≈ 10 分钟量级，仍远低于 60 分钟 xxl 超时上限，任务不会被杀（见 2.5）。
- **内存**：`findAll()` 全量加载 License 实体（千级、字段少）无内存风险；Caffeine maximumSize 上限防膨胀。
- **慢查询**：无新增复杂 SQL，主键/唯一键点查点写。
- **统计冗余同步**：对账式重算（不依赖值变化集合），对账查询以关联聚合一次找出不一致 package 集合（每轮调度执行一次，走关联查询非全表逐行比对，见 2.6）；重算仅对不一致集合执行，走唯一键/主键批量读写，不产生全表扫描。首轮全量校正后对账差异通常为 0 或极小，稳态成本可忽略。

## 6. API 接口设计

- **对外 HTTP 接口**：不涉及（无新增/变更，前端无感知）。
- **新增外部依赖调用**：貂蝉 `GET https://compliance.openeuler.org/check?license=<spdxId>`，入参 `license`（SPDX ID），出参 JSON 字符串 `ALLOW | NOT_ALLOW | UNKNOW`，无鉴权，400=缺参，5xx/超时按失败处理。
- **xxl-job 管理台**：executor=`openlibing-sbom-executor` 注册新任务 handler `refreshLicenseLegalityHandler`；cron `0 0 6 ? * SAT`（每周六 06:00）；路由单实例、阻塞丢弃、超时上限建议 60 分钟。
- **配置项**（Nacos + 各 profile properties）：`diaochan.api.url` 配置为**完整 endpoint**（含 `/check`，gamma/beta/prod 同值 `https://compliance.openeuler.org/check`），客户端直接拼 `?license=<spdxId>`，不再追加任何路径；留空即整体关闭貂蝉链路，自动降级。

## 7. 安全设计

- **鉴权与权限**：貂蝉为公开合规查询服务，无凭证要求；本服务不新增对外暴露端点；xxl-job 沿用现有 accessToken（SecurityUtil.decrypt）机制。
- **输入校验**：spdxLicenseId 来源于本服务 license 词典表（写入时已经过 SPDX 标准映射与解析校验），作为 query 参数由 WebClient uriBuilder 自动 URL 编码，无注入面；不向貂蝉发送任何业务数据或用户数据。
- **敏感信息**：新增配置仅含公网 URL，入 Nacos 管理，不硬编码、不含凭证；日志输出 license ID 与统计数，无敏感信息。
- **注入风险**：响应按白名单三态解析，任意非预期响应文本不进入存储或执行路径。

## 8. 测试设计（要点）

- `DiaochanClientImplTest`：mock WebClient 响应 — ALLOW/NOT_ALLOW/UNKNOW/带引号文本/未知值/4xx/5xx 重试耗尽/URL 未配置/URL 为完整 endpoint 时仅拼 `?license=` 不二次拼接/connect 与 response 超时配置生效（超时后触发重试）；
- `LicenseLegalityRefreshServiceTest`：mock client 与 repository — 值变化才 save、UNKNOW 保留现值、单条异常不中断、连续失败 ≥ 20 条熔断提前退出、unknown 占比 > 80% 触发 handleFail、清缓存先于查询（验证 CacheManager 清缓存被调用）、统计数正确；
- `FillUpLicenseStepTest`（既有测试补充）：兜底从严口径走 `resolveLicenseLegalityStrict`（仅 ALLOW→true，UNKNOW/异常→false）；
- 统计冗余同步测试（对账式）：对账查询返回不一致 package 集合时重算正确（含无关联 license → null 边界）、产品级合法/非法包计数重算正确、对账无差异时不触发重算、任务中断后残留的不一致在下一轮对账中被修复（自愈）；
- 本地验证：`mvn compile` + 上述单测；gamma 部署后 xxl 管理台手动触发任务，核对 license 表 is_legal 与调度日志统计。
