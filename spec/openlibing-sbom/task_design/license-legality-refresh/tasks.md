# License 合规性数据自动刷新 — 实现任务

## 进度: 0/15 complete

### openlibing-sbom（分支 feat-license-legality-refresh）

#### 貂蝉客户端与缓存

- [ ] `interface`（`org.opensourceway.sbom.api.license`）新增 `DiaochanClient`（`checkLicense(String spdxLicenseId)` / `needRequest()`）与 `DiaochanCheckResult` 三态枚举（ALLOW / NOT_ALLOW / UNKNOW）
- [ ] `clients`（`org.opensourceway.sbom.clients.license`）新增 `DiaochanClientImpl`：WebClient GET `/check`、三态解析（带引号/纯文本兼容、未知值按 UNKNOW + warn）、`Retry.backoff(3, 1s)`、`@Value("${diaochan.api.url:}")` + `needRequest()` 判断，风格对齐 LicenseClientImpl（WebClientUtil.connector、`spring.codec.max-in-memory-size`）
- [ ] `cache` 新增 `LicenseComplianceCache`：`@Bean CacheProperties`（cacheName=licenseCompliance、maximumSize=5000、expireAfterWrite=12h、cacheNullValue=false）+ `@Cacheable getLicenseCompliance` + `clearCache()`（CacheManager 取 CaffeineCache 清空）
- [ ] `CacheConstants` 新增 `LICENSE_COMPLIANCE_CACHE_NAME` 与 key 常量（`#spdxLicenseId`）

#### 批处理双路径接入

- [ ] `ExtractLicensesProcessor`：注入 `LicenseComplianceCache`；新增私有方法 `resolveLicenseLegality(lic, illegalLicenseList)`（貂蝉 ALLOW→true / NOT_ALLOW→false / UNKNOW 与异常→降级黑名单）；`setLicenseAndPkgInfo` legality 计算切换；`getLicenseLegality` 保留为降级口径
- [ ] `FillUpLicenseStep`：注入 `LicenseComplianceCache`；`toLicense` 新建分支 `setIsLegal` 改为从严口径（仅 ALLOW→true，NOT_ALLOW / UNKNOW / 调用异常→false）

#### 调度刷新与统计冗余同步

- [ ] dao 相关 Repository 新增统计冗余重算查询：按变化 license_id 集合经 `pkg_license_relp` 反查受影响 pkg_id；加载受影响 PackageStatistics（含 relps）并批量保存；按受影响 sbom 聚合合法/非法 license 包计数
- [ ] 新增 `LicenseLegalityRefreshService.refreshAllLicenses()`（sbom-web，风格对齐 PendingVulCleanService）：清缓存 → findAll 全量逐条查询 → 值变化才 save（UNKNOW 跳过保留现值、单条异常不中断）→ 统计冗余同步重算（口径对齐 CollectStatisticsStep）→ 返回 `RefreshSummary`（total/legal/illegal/unknown/updated/failed）
- [ ] 新增 `LicenseXxlJobHandler`（sbom-web，与 VulXxlJobHandler 同级）：`@XxlJob("refreshLicenseLegalityHandler")`、handleSuccess 输出汇总 / needRequest=false 或全量失败 handleFail + error 告警（cron `0 0 6 ? * SAT` 在 xxl 管理台配置，代码不写 cron）
- [ ] 配置：Nacos + gamma/beta/prod profile properties 增加 `diaochan.api.url=https://compliance.openeuler.org/check`

#### 测试

- [ ] `DiaochanClientImplTest`：ALLOW / NOT_ALLOW / UNKNOW / 带引号文本 / 未知值 / 4xx / 5xx 重试耗尽 / URL 未配置
- [ ] `LicenseLegalityRefreshServiceTest`：值变化才 save、UNKNOW 保留现值、单条异常不中断、统计数正确、清缓存先于查询
- [ ] `ExtractLicensesProcessorTest` / `FillUpLicenseStepTest`（既有测试补充）：貂蝉三态覆盖降级逻辑、client 异常降级、兜底从严口径
- [ ] 统计冗余同步测试：受影响包 `is_legal_license` 重算正确（含无关联 license → null 边界）、产品级合法/非法包计数重算正确、值无变化不触发重算
- [ ] `mvn compile` + 相关单测全部通过

### 收尾

- [ ] pre-commit 全部改动文件通过

## 关联

- 业务 Issue：openlibing/openlibing-sbom#187（https://gitcode.com/openlibing/openlibing-sbom/issues/187）
- docs PR：https://gitcode.com/openlibing/openlibing-docs/merge_requests/1405（分支 spec-openlibing-sbom-license-legality-refresh）
