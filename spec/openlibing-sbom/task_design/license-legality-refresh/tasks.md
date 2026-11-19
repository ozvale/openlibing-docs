# License 合规性数据自动刷新 — 实现任务

## 进度: 0/16 complete

### openlibing-sbom（分支 feat-license-legality-refresh）

#### 貂蝉客户端与缓存

- [ ] `interface`（`org.opensourceway.sbom.api.license`）新增 `DiaochanClient`（`checkLicense(String spdxLicenseId)` / `needRequest()`）与 `DiaochanCheckResult` 三态枚举（ALLOW / NOT_ALLOW / UNKNOW）
- [ ] `clients`（`org.opensourceway.sbom.clients.license`）新增 `DiaochanClientImpl`：`diaochan.api.url` 配置为完整 endpoint（含 `/check`），客户端仅拼 `?license=<spdxId>` 不追加路径、connect/response 超时配置、三态解析（带引号/纯文本兼容、未知值按 UNKNOW + warn）、`Retry.backoff(3, 1s)`、`@Value("${diaochan.api.url:}")` + `needRequest()` 判断，风格对齐 LicenseClientImpl（WebClientUtil.connector、`spring.codec.max-in-memory-size`）
- [ ] `cache` 新增 `LicenseComplianceCache`：`@Bean CacheProperties`（cacheName=licenseCompliance、maximumSize=5000、expireAfterWrite=12h、cacheNullValue=false）+ `@Cacheable getLicenseCompliance`；结构对齐 LicenseObjectCache，**不注入 CacheManager**（避免与 CaffeineCacheConfig 循环依赖），清空缓存由 service 注入 CacheManager 实现
- [ ] `CacheConstants` 新增 `LICENSE_COMPLIANCE_CACHE_NAME` 与 key 常量（`#spdxLicenseId`）

#### 批处理双路径接入

- [ ] `ExtractLicensesProcessor`：注入 `LicenseComplianceCache`；新增私有方法 `resolveLicenseLegality(lic, illegalLicenseList)`（貂蝉 ALLOW→true / NOT_ALLOW→false / UNKNOW 与异常→降级黑名单，**仅用于主链路**）；`setLicenseAndPkgInfo` legality 计算切换；`getLicenseLegality` 保留为降级口径
- [ ] `FillUpLicenseStep`：注入 `LicenseComplianceCache`；`toLicense` 新建分支 `setIsLegal` 改为独立从严方法 `resolveLicenseLegalityStrict(spdxId)`（仅 ALLOW→true，NOT_ALLOW / UNKNOW / 调用异常→false，不复用主链路带黑名单降级的方法）

#### 调度刷新与统计冗余同步

- [ ] dao 相关 Repository 新增对账查询：聚合 `pkg_license_relp` + license 实际 is_legal（allMatch，含无关联 → null）与 `package_statistics.is_legal_license` 比对，返回不一致的 package 集合；加载不一致 PackageStatistics（含 relps）并批量保存；按不一致 package 所属 sbom 聚合合法/非法 license 包计数
- [ ] 新增 `LicenseLegalityRefreshService.refreshAllLicenses()`（sbom-web，风格对齐 PendingVulCleanService）：注入 `CacheManager` 清空缓存（保证手动触发也是真实全量刷新）→ findAll 全量逐条查询 → 值变化才 save（UNKNOW 跳过保留现值、单条异常不中断、连续失败 ≥ 20 条熔断提前退出）→ 统计冗余对账式重算（不依赖值变化集合，口径对齐 CollectStatisticsStep，任务中断后下一轮对账自愈）→ 返回 `RefreshSummary`（total/legal/illegal/unknown/updated/failed）
- [ ] 新增 `LicenseXxlJobHandler`（sbom-web，与 VulXxlJobHandler 同级）：`@XxlJob("refreshLicenseLegalityHandler")`、handleSuccess 输出汇总 / handleFail + error 告警条件：needRequest=false（URL 未配置）、触发连续失败熔断、全量失败、unknown 占比 > 80%（cron `0 0 6 ? * SAT` 在 xxl 管理台配置，代码不写 cron）
- [ ] 配置：Nacos + gamma/beta/prod profile properties 增加 `diaochan.api.url=https://compliance.openeuler.org/check`（完整 endpoint 含 `/check`，客户端直接拼 `?license=` 不再追加路径）

#### 测试

- [ ] `DiaochanClientImplTest`：ALLOW / NOT_ALLOW / UNKNOW / 带引号文本 / 未知值 / 4xx / 5xx 重试耗尽 / URL 未配置 / URL 为完整 endpoint 时仅拼 `?license=` 不二次拼接 / connect 与 response 超时配置生效
- [ ] `LicenseLegalityRefreshServiceTest`：值变化才 save、UNKNOW 保留现值、单条异常不中断、连续失败 ≥ 20 条熔断提前退出、unknown 占比 > 80% 触发 handleFail、统计数正确、清缓存先于查询（验证 CacheManager 清缓存被调用）
- [ ] `ExtractLicensesProcessorTest` / `FillUpLicenseStepTest`（既有测试补充）：主链路貂蝉三态覆盖降级逻辑、client 异常降级、兜底从严口径走 `resolveLicenseLegalityStrict`
- [ ] 统计冗余同步测试（对账式）：对账查询返回不一致集合时 `is_legal_license` 重算正确（含无关联 license → null 边界）、产品级合法/非法包计数重算正确、对账无差异不触发重算、任务中断后残留不一致下一轮对账自愈
- [ ] `mvn compile` + 相关单测全部通过

### 收尾

- [ ] pre-commit 全部改动文件通过

## 关联

- 业务 Issue：openlibing/openlibing-sbom#187（https://gitcode.com/openlibing/openlibing-sbom/issues/187）
- docs PR：https://gitcode.com/openlibing/openlibing-docs/merge_requests/1405（分支 spec-openlibing-sbom-license-legality-refresh）
