# License 合规性数据自动刷新 — license-legality-refresh

## 业务 Issue

- openlibing/openlibing-sbom#187（https://gitcode.com/openlibing/openlibing-sbom/issues/187）
- docs PR：https://gitcode.com/openlibing/openlibing-docs/merge_requests/1405

## 需求背景

软件包列表页「License 合规性」筛选（OSI/FSF 认证 / 非 OSI/FSF 认证）读取 `license.is_legal`，该值目前只在 SBOM 批处理解析时按本地黑名单口径（compliance3 `/lic` / repo_meta illegalList）判定一次，判定来源权威性不足；且批处理主链路「后写覆盖先写」（`getLicenseCache` 未命中即无条件覆盖落库）导致同 license 的 is_legal 最终值取决于最后一次批处理的口径，数据持续失真。

引入貂蝉平台（compliance.openeuler.org `/check?license=<spdxId>`，返回 `"ALLOW"` / `"NOT_ALLOW"` / `"UNKNOW"`）作为 OSI/FSF 认证判定的权威来源，通过两条刷新途径保证 `license.is_legal` 与貂蝉结论一致：

1. **批处理兜底新建即查**：仅当 license 不存在需要新建入库时，实时调用貂蝉判定并随新建落库；批处理主链路保持现状不接貂蝉；
2. **xxl-job 每周全量校正**：每周六 06:00 全量刷新存量 license（含主链路后续覆盖写入的失真值），支持管理台手动触发。

前端无改动、无表结构变化、无对外接口契约变化。

## 功能描述

### 口径定义（现状 → 新口径）

| 场景                                         | 现状口径                                              | 新口径                                                                                                                  |
| -------------------------------------------- | ----------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 批处理主链路（ExtractLicensesProcessor）     | `!illegalLicenseList.contains(lic)`（黑名单布尔判断） | **保持现状**，不接入貂蝉；主链路覆盖写入的失真值由 xxl-job 每周校正收敛                                                 |
| 批处理兜底（FillUpLicenseStep 新建 license） | 硬编码 `setIsLegal(true)`                             | 从严口径：仅 ALLOW→true，其余（NOT_ALLOW/UNKNOW/调用异常）→新建且 is_legal=false                                        |
| 存量数据校正（新增）                         | 无                                                    | xxl-job 每周六 06:00 全量刷新；UNKNOW 跳过保留现值；支持管理台手动强制刷新                                              |
| 统计冗余同步（新增）                         | 无                                                    | 刷新后重算受影响包的 `package_statistics.is_legal_license` 与受影响产品的 `product_statistics` 合法/非法 license 包计数 |

### 核心实现

1. `DiaochanClient`（interface）+ `DiaochanClientImpl`（clients）：WebClient GET 貂蝉 `/check`（URL 配置为完整 endpoint），三态解析（未知值按 UNKNOW + warn，协议前向兼容），`Retry.backoff(3, 1s)`，URL 未配置时 `needRequest()=false` 整体降级；
2. `LicenseComplianceCache`（cache）：Caffeine 缓存（maximumSize=5000、expireAfterWrite=12h、cacheNullValue=false），`@Cacheable` 查询（清空缓存由刷新 service 注入 CacheManager 实现）；
3. 批处理兜底新建接入（batch）：主链路 `ExtractLicensesProcessor` 保持现状不改动；仅兜底新建（`FillUpLicenseStep`）查貂蝉从严（仅 ALLOW→true，其余→false）；
4. `LicenseLegalityRefreshService` + `LicenseXxlJobHandler`（sbom-web）：清缓存 → 全量真实查询 → 值变化才 save → 统计冗余同步重算 → 汇总日志（查询总数/合规/不合规/未知/更新数/失败数）；
5. 统计冗余同步（§2.6 分析）：合规性筛选取自 `package_statistics.is_legal_license`（批处理冗余聚合字段），license.is_legal 刷新后必须同步重算，否则筛选结果与行内红绿点不一致；`licenseDistribution` / `license_count` / 名称选项与 is_legal 无关，不受影响；
6. 配置：Nacos + 各 profile `diaochan.api.url=https://compliance.openeuler.org/check`（留空即整体关闭貂蝉链路自动降级）；xxl 管理台配置 cron `0 0 6 ? * SAT`、单实例路由、阻塞丢弃。

## 不做

- 不改动批处理主链路 `ExtractLicensesProcessor` 与 `LicenseObjectCache.getLicenseCache`（主链路保持现状黑名单口径与覆盖落库行为，失真值依靠调度任务每周校正收敛）；
- 不改 `license_distribution`、`license_count`、`licenses` 数组等与合法性无关的统计字段；
- 不做貂蝉查询并发优化（一期串行，license 千级整体分钟级，规模到万级再引入受控并发）；
- 前端 openlibing-web 无任何改动。

## 验收标准

- [ ] 手动/定时触发调度任务后，貂蝉已收录 license 的 `is_legal` 与貂蝉结论一致；UNKNOW 记录保持原值
- [ ] 调度日志完整输出查询总数、合规总数、不合规总数、未知总数、更新数、失败数
- [ ] 批处理兜底新建 license 时，貂蝉已收录的按貂蝉结论落库（未收录/调用异常→false）；主链路判定与覆盖行为保持现状不变
- [ ] 貂蝉服务不可用时：批处理不中断（兜底新建从严置 false，主链路不涉及貂蝉），调度任务单条失败不中断整体，均输出告警日志
- [ ] 刷新完成后，软件包列表「合规性」筛选结果与列表行内 license 红绿点一致（package_statistics.is_legal_license 与 product_statistics 合法/非法包计数已同步重算）
- [ ] `diaochan.api.url` 未配置时整体降级：批处理兜底新建按从严口径置 false，调度任务 handleFail 告警退出

## 影响范围

| 文件                                                                          | 操作      | 说明                                        |
| ----------------------------------------------------------------------------- | --------- | ------------------------------------------- |
| `interface/.../api/license/DiaochanClient.java`                               | 新增      | 貂蝉合规查询接口                            |
| `interface/.../api/license/DiaochanCheckResult.java`                          | 新增      | 三态枚举                                    |
| `clients/.../license/DiaochanClientImpl.java`                                 | 新增      | WebClient 实现（Retry + 三态解析）          |
| `cache/.../LicenseComplianceCache.java`                                       | 新增      | 合规结果 Caffeine 缓存（清空在 service 侧） |
| `cache/.../CacheConstants.java`                                               | 修改      | 新增缓存名与 key 常量                       |
| `batch/.../FillUpLicenseStep.java`                                            | 修改      | 兜底新建查貂蝉从严口径                      |
| `sbom-web/.../service/license/LicenseLegalityRefreshService.java`             | 新增      | 刷新 service（含统计冗余同步）              |
| `sbom-web/.../handler/LicenseXxlJobHandler.java`                              | 新增      | xxl-job handler                             |
| dao 相关 Repository（PkgLicenseRelp / PackageStatistics / ProductStatistics） | 修改      | 统计冗余重算查询                            |
| 测试类若干                                                                    | 新增/修改 | 单元测试                                    |

- 业务仓：`openlibing-sbom`（单仓）
- 数据模型：不涉及表结构变更（仅刷新既有 `license.is_legal` boolean 值的判定来源）
- 所属分支：`feat-license-legality-refresh`

## 流程模式

Full 模式：单仓但新增外部服务集成 + 调度链路 + 统计冗余同步，改动超 300 行（含测试），有配置/部署影响（Nacos 新配置项 + xxl-job 任务注册）→ proposal + design + tasks + 完整单测。
