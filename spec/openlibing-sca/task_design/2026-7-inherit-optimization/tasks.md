# Tasks: SCA 扫描结果继承逻辑优化

## 进度: 7/7 complete

PR #214 已合入 `release_20260715`，以下任务均已落地。本 tasks 文档作为追溯记录。

- [x] T1: `TblIssue` 实体新增 `prHeadSha` 字段，同步 Builder / `build()` / `toBuilder()`
  - 文件：`src/main/java/com/openlibing/sca/analysis/entity/TblIssue.java`
  - 落地 commit：见 PR #214 提交历史（commit 主题"继承逻辑优化"系列）
- [x] T2: 新增 Liquibase changeset `20260715_add-tbl-issue-commit-id`，为 `tbl_issue` 添加 `pr_head_sha VARCHAR(64) NULL`，含 `preConditions` 与 `rollback`
  - 文件：`src/main/resources/db/changelog/mysql/20260715/add-tbl-issue-commit-id.xml`
  - 注册：`src/main/resources/db/changelog/db.changelog.xml`
- [x] T3: `TblIssueMapper.xml` 在 insert / update / select 三处加入 `pr_head_sha` 列与 `prHeadSha` 参数映射
  - 文件：`src/main/resources/mapper/dm/TblIssueMapper.xml`
- [x] T4: `ScanCommonServiceImpl` 实现增量 diff 基线校验与三级历史匹配
  - 新增 `getPrCommitShas` + `prCommitsCache` 缓存
  - 新增 `buildPrCommitsApiUrl`（gitee / gitcode 双平台）
  - 新增 `getIncrementalPrDiff` + `buildCompareApiUrl`（`base...head` 格式）
  - `findMatchingIssue` 加入 `isExactHashMatch` 完全匹配短路
  - `isInModifiedRange` 加入 `prDiff == null` 防护
  - `getTblIssueInfo` 写入 `.prHeadSha(scan.getCommitId())`
  - 文件：`src/main/java/com/openlibing/sca/dm/service/impl/ScanCommonServiceImpl.java`
- [x] T5: `IntegrationApiServiceImpl.processBatchIssues` 重构为 5 个私有方法，强制回填顺序
  - 新增 `backfillPrHeadCommitId`：在 `resultInherit` 之前回填 `scanIssue.commitId`
  - 抽取 `extractScanFileList` / `buildShieldRoleDto` / `filterAndMarkUnconfirmed` / `executeBatchAnalysisIfNeed`
  - 文件：`src/main/java/com/openlibing/sca/dm/service/impl/IntegrationApiServiceImpl.java`
- [x] T6: `ScanCommonServiceImplTest` 新增 4 个单元测试覆盖匹配优先级
  - `testGetTblIssues_ExactHashMatch_Prioritized`：sourceHash + fileHash 全等优先
  - `testGetTblIssues_FallbackToFileHashOnly`：缺失 sourceHash 完全匹配时回退 fileHash
  - `testGetTblIssues_BothMatchAndFallback_BothMatchWins`：共存时仅保留完全匹配
  - `testGetTblIssues_NoHashMatch_FilteredOut`：fileHash 不一致被过滤
  - 文件：`src/test/java/com/openlibing/sca/dm/service/impl/ScanCommonServiceImplTest.java`
- [x] T7: 验证
  - `mvn test` 单元测试通过
  - `mvn clean package` 编译通过
  - PR #214 CI 流水线 `ci-pipeline-passed`，获 `lgtm` + `approved` 标签，已于 2026-07-15 合入 `release_20260715`

## 后续可选项（不在本次 PR 范围）

- [ ] 增加 `getPrCommitShas` 与 `getIncrementalPrDiff` 的 API 调用成功率指标埋点
- [ ] 为 `prCommitsCache` 与 `incrementalDiffCache` 加容量上限与过期策略（当前依赖请求生命周期回收）
- [ ] 存量 `pr_head_sha` 为 NULL 的历史 TblIssue 数据回填策略（如需启用增量 diff）
