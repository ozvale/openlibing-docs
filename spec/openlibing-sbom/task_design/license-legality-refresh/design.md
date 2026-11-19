# License 合规性数据自动刷新（license-legality-refresh）设计文档

> 需求背景：页面「OSI/FSF 认证 license / 非 OSI/FSF 认证 license」筛选读取 `license.is_legal`，该值目前只在 SBOM 解析时判定一次，貂蝉平台结论变化后无法同步，数据持续失真。本设计引入「批处理解析即查貂蝉 + xxl-job 每周全量校正」两条刷新途径。前端无改动、无表结构变化、无对外接口契约变化。

## 1. 方案设计

### 1.1 整体思路

在 openlibing-sbom 单仓内完成改造，围绕「貂蝉 /check 合规查询」新增一条独立的数据链路，替换/增强现有 is_legal 的判定来源：

| 场景                                         | 现状口径                                                                    | 新口径                                                                                                                  |
| -------------------------------------------- | --------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 批处理主链路（ExtractLicensesProcessor）     | `!illegalLicenseList.contains(lic)`（compliance3/repo_meta 黑名单布尔判断） | 貂蝉优先：ALLOW→true，NOT_ALLOW→false，UNKNOW/查询失败→降级现有黑名单口径                                               |
| 批处理兜底（FillUpLicenseStep 新建 license） | 硬编码 `setIsLegal(true)`                                                   | 貂蝉从严口径：仅 ALLOW→true，其余（NOT_ALLOW/UNKNOW/调用异常）→新建且 is_legal=false                                    |
| 存量数据校正（新增）                         | 无                                                                          | xxl-job 每周六 06:00 全量刷新；UNKNOW 跳过保留现值；支持管理台手动强制刷新                                              |
| 统计冗余同步（新增）                         | 无                                                                          | 刷新后重算受影响包的 `package_statistics.is_legal_license` 与受影响产品的 `product_statistics` 合法/非法 license 包计数 |

### 1.2 职责划分与涉及范围

- **前端（openlibing-web）**：不涉及。
- **后端（openlibing-sbom）**：
  - `interface` 模块：新增貂蝉客户端接口与结果枚举；
  - `clients` 模块：新增貂蝉 HTTP 客户端实现（WebClient，对齐 LicenseClientImpl 风格）；
  - `cache` 模块：新增貂蝉合规结果 Caffeine 缓存（12h TTL，支持整体清空）；
  - `batch` 模块：两条 license 写入路径的口径调整；
  - `sbom-web` 模块：新增 xxl-job handler 与刷新 service（含受影响统计冗余字段重算，见 2.6）。

### 1.3 验收标准

1. 手动/定时触发调度任务后，貂蝉已收录 license 的 `is_legal` 与貂蝉结论一致；UNKNOW 记录保持原值；调度日志完整输出查询总数、合规总数、不合规总数、未知总数。
2. 新导入 SBOM 解析落库后，貂蝉已收录 license 的 `is_legal` 即与貂蝉一致；未收录 license 走降级口径。
3. 貂蝉服务不可用时：批处理不中断（主链路降级黑名单、兜底新建从严置 false），调度任务单条失败不中断整体，均输出告警日志。
4. 刷新完成后，软件包列表「合规性」筛选结果与列表行内 license 红绿点一致（统计冗余字段已同步重算，见 2.6）。

## 2. 实现逻辑设计

### 2.1 貂蝉 /check 接口契约（实测确认）

- 请求：`GET {diaochan.api.url}?license=<spdxLicenseId>`，`diaochan.api.url` 配置为 `https://compliance.openeuler.org/check`；
- 响应：HTTP 200，body 为 JSON 字符串文本（带双引号），三值：
  - `"ALLOW"`：OSI/FSF 认证（合规）；
  - `"NOT_ALLOW"`：明确不合规；
  - `"UNKNOW"`：貂蝉未收录；
- 大小写不敏感；缺失 `license` 参数返回 400；响应出现未知取值时按 UNKNOW 处理并 warn（协议前向兼容）。

### 2.2 调度任务核心流程（refreshLicenseLegalityHandler）

```text
1. 清空 LicenseComplianceCache（保证手动触发也是真实全量刷新）
2. licenseRepository.findAll() 加载全量 license（量级：千级）
3. 逐条 license：
   a. 调 LicenseComplianceCache.getLicenseCompliance(spdxId)（缓存已清，真实调用貂蝉）
   b. ALLOW  → 目标值 true；与现值不一致才 save
   c. NOT_ALLOW → 目标值 false；与现值不一致才 save
   d. UNKNOW → unknown++，跳过（保留现值）
   e. 调用异常 → failed++，error 日志，继续下一条（单条失败不中断）
4. 统计冗余同步：对 is_legal 值发生变化的 license 集合，经 pkg_license_relp
   反查受影响 package，重算 package_statistics.is_legal_license 与受影响
   product_statistics 的合法/非法 license 包计数（见 2.6）
5. XxlJobHelper.handleSuccess 输出汇总：
   查询总数 / 合规总数 / 不合规总数 / 未知总数 / 更新数 / 失败数
6. needRequest()==false（URL 未配置）或全量失败 → handleFail + error 告警
```

- cron `0 0 6 ? * SAT`（每周六 06:00）在 xxl 管理台配置（代码不写 cron，对齐 pendingVulCleanHandler 注释模式）；路由策略单实例、阻塞策略丢弃后续。
- 任务幂等：重复执行仅重复查询比对，无副作用累积。

### 2.3 批处理主链路口径（ExtractLicensesProcessor）

```text
原：getLicenseCache(lic, getLicenseLegality(illegalLicenseList, lic))
新：getLicenseCache(lic, resolveLicenseLegality(lic, illegalLicenseList))

resolveLicenseLegality(lic, illegalLicenseList):
  try
    ALLOW     -> true
    NOT_ALLOW -> false
    UNKNOW    -> fallback
  catch (查询异常)
    fallback
  fallback = !illegalLicenseList.contains(lic)   // 现有黑名单口径原样保留
```

- openEuler 产品的 illegalList 来自 repo_meta 缓存，其他产品来自 compliance3 `/lic`，降级链路不变；
- `LicenseObjectCache.getLicenseCache` 本身不改动（其缓存 key 含 legality，传入值即新口径结果），覆盖落库行为维持现状。

**主链路缓存逻辑背景（评审确认，固化结论）**：

- **为什么有这层缓存**：一次批处理会解析大量 SBOM，同一 license 会跨包/跨 SBOM 反复出现，为避免对同一 license 重复「查库 + 写库」，`getLicenseCache` 设计了进程内 `@Cacheable` 缓存（LICENSE_OBJECT：key = `spdxId + '_' + legality`、容量 1000、写后 1h 过期、cacheNullValue=true）。key 携带 legality 是因为不同包的黑名单口径可能不同：(spdxId, legality) 组合各自独立缓存，同口径请求直接复用缓存实体、跨口径请求各自触发落库。
- **现状行为链**：缓存命中 → 跳过方法体、不碰 DB；缓存未命中 → `findBySpdxLicenseId` 查库，**无论 license 是否已存在都执行 `setIsLegal(传入值)` + `save()`**（存在 = 覆盖更新、不存在 = 新建）。即主链路并非「库里有就跳过不更新」。
- **由此产生的失真背景**：is_legal 最终值取决于最后一次批处理的判定口径（后写覆盖先写），且缓存仅本进程实例有效（重启 / 多实例部署不共享，重新落库）——这正是需要引入貂蝉实时判定的动机。
- **新方案下的影响**：不改动该类与缓存配置。貂蝉优先的 legality 作为第二参传入后，缓存 key 随口径自然分离——貂蝉结论变化 → 新 key → 必然未命中 → 覆盖写库（新口径即时生效）；结论不变 → 同一次运行内被缓存挡住、不重复写库。缓存 1h 过期相对每周调度周期可忽略（跨周运行时缓存必已过期）；UNKNOW 降级得到的黑名单口径值同样参与 key，与貂蝉口径条目互不干扰。

### 2.4 批处理兜底口径（FillUpLicenseStep.toLicense）

- 仅对 `existLicenses` 中不存在而新建的 license 生效（已有 license 直接返回，不触发貂蝉调用）；
- 新建时 `setIsLegal(resolveLicenseLegality(spdxId))`，从严控制：**仅 ALLOW→true；NOT_ALLOW / UNKNOW（貂蝉未收录视同非 OSI/FSF 认证）/ 调用异常（无法确认合规）一律 false**，正常新建 license 且默认不合规；
- 新建的 license 随 `licenseRepository.saveAll(existLicenses.values())` 统一落库，落库方式不变。

### 2.5 异常与边界处理

| 场景                        | 处理                                                                                                                           |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| 貂蝉超时 / 5xx / 网络不可达 | WebClient `Retry.backoff(3, 1s)` 耗尽后抛异常；@Cacheable 异常不缓存；主链路降级黑名单、兜底新建从严置 false、调度任务跳过该条 |
| 响应文本非三态              | 按 UNKNOW 处理 + warn 日志（保留协议演进空间）                                                                                 |
| 响应带引号 / 纯文本         | 按 JSON 字符串解析，解析失败 fallback 去引号 trim 比对                                                                         |
| `diaochan.api.url` 未配置   | 客户端 `needRequest()=false`：批处理直接走降级口径；调度任务 handleFail 告警退出                                               |
| 调度任务与批处理并发        | 共享缓存仅引发回源重查，无正确性影响；DB 层为逐行 update，无锁冲突                                                             |
| 全部 license 查询失败       | 调度任务 handleFail（updated/failed 比例判断），不误报成功                                                                     |

### 2.6 页面筛选数据来源分析与统计冗余同步（评审新增）

软件包列表 license 表头筛选面板三组选项的来源与本次改造的影响（已核实前端 openlibing-web 与后端查询实现）：

| 筛选项                                            | 选项/过滤数据来源                                                                                                                                                                     | 是否需调度后刷新                                                                                                |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- |
| License 名称标签（可搜索多选，如 MIT/Apache-2.0） | 前端每次进页面调 `queryProductStatistics` 接口**现查**，数据源为 `product_statistics.licenseDistribution`（JSONB Map&lt;spdxId, 包数&gt;，由批处理 CollectStatisticsStep 写入）       | 否：键值只含 license 名称→包数，与 is_legal 无关，名称集合不因刷新变化                                          |
| License 数量（无/单/多）                          | 前端写死常量；后端按 `package_statistics.license_count` 过滤                                                                                                                          | 否：与 is_legal 无关                                                                                            |
| License 合规性（OSI/FSF 认证/非认证）             | 前端写死常量（LEGAL/ILLEGAL）；后端过滤条件为 **`package_statistics.is_legal_license = TRUE/FALSE`**（批处理时经 `allMatch(pkg_license_relp → license.is_legal)` 聚合写入的冗余字段） | **是：`license.is_legal` 刷新后该冗余字段不会自动更新，必须同步重算，否则合规性筛选结果与列表行内红绿点不一致** |
| 列表行内 license 红绿点                           | 查询时实时经 `pkg_license_relp → license.is_legal` 组装（`LicenseVo.fromLicense`）                                                                                                    | 无需动作，实时反映刷新结果                                                                                      |

受影响冗余字段与同步策略（在刷新 service 差异化落库后执行）：

1. **package_statistics.is_legal_license**：收集本次 is_legal 值发生变化的 license 集合 → 经 `pkg_license_relp` 反查受影响 package 集合 → 按现行聚合口径重算（`allMatch(license.isLegal)`，包无关联 license 时为 null），逻辑与 `CollectStatisticsStep.collectPackageLicenseStatistics` 保持一致；
2. **product_statistics.packageWithLegalLicenseCount / packageWithIllegalLicenseCount**：对受影响 package 所属 sbom（产品）重算合法/非法 license 包计数，语义对齐 CollectStatisticsStep 现有聚合；
3. `license_distribution`、`license_count`、`licenses` 数组不涉及合法性，不做改动。

## 3. 类设计

### 3.1 新增类

| 类                              | 模块                                                                                  | 职责与关键签名                                                                                                                                                                                                                                                                                                                                                                     |
| ------------------------------- | ------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `DiaochanClient`                | interface（`org.opensourceway.sbom.api.license`）                                     | 貂蝉合规查询接口：`DiaochanCheckResult checkLicense(String spdxLicenseId)`、`boolean needRequest()`                                                                                                                                                                                                                                                                                |
| `DiaochanCheckResult`           | interface（同包枚举）                                                                 | 三态：`ALLOW` / `NOT_ALLOW` / `UNKNOW`                                                                                                                                                                                                                                                                                                                                             |
| `DiaochanClientImpl`            | clients（`org.opensourceway.sbom.clients.license`）                                   | WebClient GET `/check`；`@Value("${diaochan.api.url:}")`；响应解析三态；`Retry.backoff(3, 1s)`；风格对齐 LicenseClientImpl（复用 WebClientUtil.connector、`spring.codec.max-in-memory-size`）                                                                                                                                                                                      |
| `LicenseComplianceCache`        | cache（`org.opensourceway.sbom.cache`）                                               | ① `@Bean CacheProperties licenseComplianceCacheProperties()`：cacheName=`licenseCompliance`、maximumSize=5000、expireAfterWrite=12h（43200s）、cacheNullValue=false；② `@Cacheable` 方法 `DiaochanCheckResult getLicenseCompliance(String spdxLicenseId)`（内部委托 DiaochanClient）；③ `void clearCache()`（注入 CacheManager 取对应 CaffeineCache 调 clear，供调度任务入口调用） |
| `LicenseLegalityRefreshService` | sbom-web（`org.opensourceway.sbom.service.license`，风格对齐 PendingVulCleanService） | `RefreshSummary refreshAllLicenses()`：清缓存→全量查询→差异化落库→统计冗余同步重算（见 2.6）→返回统计；内部记录 total/legal/illegal/unknown/updated/failed                                                                                                                                                                                                                         |
| `LicenseXxlJobHandler`          | sbom-web（`org.opensourceway.sbom.handler`，与 VulXxlJobHandler 同级）                | `@XxlJob("refreshLicenseLegalityHandler")`：调用刷新 service，`XxlJobHelper.handleSuccess/handleFail` 汇总日志                                                                                                                                                                                                                                                                     |
| `RefreshSummary`                | sbom-web（service 内部 POJO 或嵌套类）                                                | 刷新统计结果载体                                                                                                                                                                                                                                                                                                                                                                   |

### 3.2 修改类

| 类                                                                                                      | 模块  | 改动点                                                                                                                                                                                                                      |
| ------------------------------------------------------------------------------------------------------- | ----- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `CacheConstants`                                                                                        | cache | 新增 `LICENSE_COMPLIANCE_CACHE_NAME = "licenseCompliance"` 与对应 key 常量（`#spdxLicenseId`）                                                                                                                              |
| `ExtractLicensesProcessor`                                                                              | batch | 注入 `LicenseComplianceCache`；`setLicenseAndPkgInfo` 中 legality 计算改为 `resolveLicenseLegality(lic, illegalLicenseList)`（貂蝉优先+降级）；新增私有方法 `resolveLicenseLegality`；`getLicenseLegality` 保留作为降级口径 |
| `FillUpLicenseStep`                                                                                     | batch | 注入 `LicenseComplianceCache`；`toLicense` 新建分支 `setIsLegal` 改为貂蝉从严口径（仅 ALLOW→true，UNKNOW/调用异常→false）                                                                                                   |
| 相关 Repository（PkgLicenseRelpRepository / PackageStatisticsRepository / ProductStatisticsRepository） | dao   | 新增统计冗余重算所需查询：按变化 license_id 集合反查受影响 pkg_id；加载受影响 PackageStatistics（含 relps）并批量保存；按受影响 sbom 聚合合法/非法 license 包计数                                                           |

类间关系：`LicenseXxlJobHandler → LicenseLegalityRefreshService → LicenseComplianceCache → DiaochanClient`；`ExtractLicensesProcessor / FillUpLicenseStep → LicenseComplianceCache`；`LicenseComplianceCache` 同时持有 `CacheManager` 引用用于清空。

## 4. 数据模型设计

不涉及。本次仅改变 `license` 表既有 `is_legal` 字段（boolean）值的刷新机制与判定来源，无表结构、索引、迁移变化；不新增表。

## 5. 性能设计

- **批处理（高频、重复度高）**：同 chunk 与跨 chunk 的重复 license 命中 Caffeine 缓存（5000 条 / 12h），仅 cache miss 时发起 HTTP；貂蝉单次查询为轻量 GET（实测百毫秒级），兜底路径仅对新建 license 触发，增量小。
- **调度任务（每周一次）**：入口清缓存后全量真实调用，串行执行。按千级 license × 百毫秒级单次耗时估算，整体分钟级，远小于 xxl 超时上限；仅对值变化的记录 save，DB 写量小。一期保持串行（简单可靠），若 license 规模增长到万级再引入受控并发。
- **内存**：`findAll()` 全量加载 License 实体（千级、字段少）无内存风险；Caffeine maximumSize 上限防膨胀。
- **慢查询**：无新增复杂 SQL，主键/唯一键点查点写。
- **统计冗余同步**：仅对 is_legal 值发生变化的 license 关联包做重算（首轮全量校正后，逐周增量通常为 0 或极小）；重算走唯一键/主键批量读写，不产生全表扫描。

## 6. API 接口设计

- **对外 HTTP 接口**：不涉及（无新增/变更，前端无感知）。
- **新增外部依赖调用**：貂蝉 `GET https://compliance.openeuler.org/check?license=<spdxId>`，入参 `license`（SPDX ID），出参 JSON 字符串 `ALLOW | NOT_ALLOW | UNKNOW`，无鉴权，400=缺参，5xx/超时按失败处理。
- **xxl-job 管理台**：executor=`openlibing-sbom-executor` 注册新任务 handler `refreshLicenseLegalityHandler`；cron `0 0 6 ? * SAT`（每周六 06:00）；路由单实例、阻塞丢弃、超时上限建议 60 分钟。
- **配置项**（Nacos + 各 profile properties）：`diaochan.api.url`（gamma/beta/prod 同值 `https://compliance.openeuler.org/check`；留空即整体关闭貂蝉链路，自动降级）。

## 7. 安全设计

- **鉴权与权限**：貂蝉为公开合规查询服务，无凭证要求；本服务不新增对外暴露端点；xxl-job 沿用现有 accessToken（SecurityUtil.decrypt）机制。
- **输入校验**：spdxLicenseId 来源于本服务 license 词典表（写入时已经过 SPDX 标准映射与解析校验），作为 query 参数由 WebClient uriBuilder 自动 URL 编码，无注入面；不向貂蝉发送任何业务数据或用户数据。
- **敏感信息**：新增配置仅含公网 URL，入 Nacos 管理，不硬编码、不含凭证；日志输出 license ID 与统计数，无敏感信息。
- **注入风险**：响应按白名单三态解析，任意非预期响应文本不进入存储或执行路径。

## 8. 测试设计（要点）

- `DiaochanClientImplTest`：mock WebClient 响应 — ALLOW/NOT_ALLOW/UNKNOW/带引号文本/未知值/4xx/5xx 重试耗尽/URL 未配置；
- `LicenseLegalityRefreshServiceTest`：mock client 与 repository — 值变化才 save、UNKNOW 保留现值、单条异常不中断、统计数正确、清缓存先于查询；
- `ExtractLicensesProcessorTest` / `FillUpLicenseStepTest`（既有测试补充）：貂蝉三态覆盖降级逻辑、client 异常降级、兜底从严口径（仅 ALLOW→true，UNKNOW/异常→false）；
- 统计冗余同步测试：license 值变化后受影响包 `is_legal_license` 重算正确（含无关联 license → null 边界）、产品级合法/非法包计数重算正确、值无变化时不触发重算；
- 本地验证：`mvn compile` + 上述单测；gamma 部署后 xxl 管理台手动触发任务，核对 license 表 is_legal 与调度日志统计。
