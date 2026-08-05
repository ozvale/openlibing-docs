# License 文件兼容性分析继承逻辑 — 实现任务清单

## 数据层

- [x] 新建 Liquibase changelog `create-tbl-license-manual-analysis.xml`，建表 `tbl_license_manual_analysis` + 索引 `idx_lma_file_hash`
- [x] 新建 MyBatis Mapper 接口 `LicenseManualAnalysisMapper`（insert / update / selectByFileHash）
- [x] 新建 Mapper XML `LicenseManualAnalysisMapper.xml`（含 resultMap、三条 SQL）
- [x] 新建实体 `LicenseManualAnalysis`（手写 Builder + 防御性 Date 拷贝，修复 EI_EXPOSE_REP2）

## 枚举与 VO

- [x] 新建枚举 `ManualRiskLevel`（NO_RISK="0", HAS_RISK="1" + getDescriptionByCode）
- [x] 新建入参 VO `LicenseAnalysisVO`（objectId / fileHash / file / manualRiskLevel / manualDescription）

## MongoDB 实体扩展

- [x] `LicenseIssue` 新增字段：fileHash、manualRiskLevel、manualDescription

## 扫描引擎（读路径 — 继承）

- [x] `IntegrationApiServiceImpl.computeFileMd5Hashes`：workspace 删除前预计算所有文件 MD5
- [x] `IntegrationApiServiceImpl.md5Hex`：单文件 MD5 计算（8KB buffer + MessageDigest）
- [x] `IntegrationApiServiceImpl.processFileLicenses`：为每个 LicenseIssue 设置 fileHash
- [x] `IntegrationApiServiceImpl.inheritManualAnalysis`：按 fileHash 查 MySQL → 继承 riskLevel / description → 覆盖 compatible
- [x] `compatibleVersion` 方法签名新增 `Map<String, String> fileHashes` 参数

## License 服务（写路径 — 保存）

- [x] `LicenseServiceImpl.batchManualAnalysis`：批量遍历 + 异常兜底
- [x] `LicenseServiceImpl.updateLicenseIssueManualAnalysis`：更新 MongoDB（_id + fileHash 定位）+ 联动 compatible
- [x] `LicenseServiceImpl.upsertManualAnalysis`：MySQL 存在则 update，不存在则 insert

## Controller 接口

- [x] `LicenseController` 新增 `POST /license/manualAnalysis/batch`（入参 List + userName）
- [x] `LicenseController` 新增 `POST /license/cache/refresh`（异步刷新社区缓存）

## 查询展示适配

- [x] `getLicenseIssue` 返回时将 manualRiskLevel 编码转中文描述

## 单元测试

- [x] `IntegrationApiServiceImplTest`：inheritManualAnalysis 正常继承 / 无记录 / 异常容错
- [x] `LicenseServiceImplTest`：batchManualAnalysis 正常 / 空列表 / 数据库异常

## 验证

- [x] 本地单元测试全部通过
- [x] Liquibase changelog 在 MySQL 8.0 正常执行
- [ ] 集成环境手动验证：人工标注 → 重新扫描 → 确认继承生效
