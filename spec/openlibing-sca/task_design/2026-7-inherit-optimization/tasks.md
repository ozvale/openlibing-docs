# Tasks: SCA 扫描结果继承逻辑优化

## 进度: 9/9 complete

PR #214（主变更）已合入 `release_20260715`，PR #250（force push 修复）已合入 `release_fix_20260723`，commit `fad72408`（copyright-only 自动确认）位于 `ms_alert` 分支待发起 PR。以下任务均已落地，本 tasks 文档作为追溯记录。

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
- [x] T8: force push 场景直接 diff 修复（commit `b7f2a8a5`，PR #250）
  - 重构 `resolveEffectiveDiffMap` 为 `resolveFileDiff`，按单文件四优先级解析 diff
  - 提取 `getIncrementalDiffMap` 独立方法（原内联三点 diff 逻辑）
  - 新增 `getDirectFileDiff`：baseSha 不在提交链时取两棵树文件内容做直接 diff
  - 新增 `fetchFileContent`：通过 contents API 取指定 commit 下文件文本内容，支持 base64 解码
  - 新增 `buildFileContentApiUrl`：构建 contents API URL，路径编码保留 `/`
  - 新增 `parseOwnerAndRepo`：从 mergeUrl 解析 owner/repo
  - 新增 `computeDirectDiff`：jgit `MyersDiff` + `RawTextComparator.DEFAULT` 计算行级差异
  - `PrInheritContext` 新增 `directDiffCache`（`Map<String, PrDiffDto>`，key 为 `baseSha|headSha|filePath`）
  - `findMatchingIssue` 中 `added` 状态文件跳过 `isInModifiedRange` 直接进 3b，`adjustedLines` 用当前行号
  - 新增 5 个单元测试：`testComputeDirectDiff_NoChange` / `testComputeDirectDiff_SnippetUnchangedAcrossForcePush` / `testParseOwnerAndRepo_NormalUrl` / `testBuildFileContentApiUrl_GitCode` / `testPrResultInherit_AddedFileNotSkipped`
  - `mvn clean package` 编译通过，已于 2026-07-23 合入 `release_fix_20260723`
  - 文件：`src/main/java/com/openlibing/sca/dm/service/impl/ScanCommonServiceImpl.java` | `src/test/java/.../ScanCommonServiceImplTest.java`

- [x] T9: `autoSubmitConfirmV2` 新增 huawei copyright-only 自动确认（commit `fad72408`，`ms_alert` 分支）
  - 在 `autoSubmitConfirmV2` 中新增自动确认分支：`license=SUCCESS + copyright=FAIL` 且所有远程 copyright 的 `name` 字段均包含 `huawei`（不区分大小写）时自动确认
  - 新增 `isRemoteCopyrightOnlyHuawei` 私有方法：遍历 copyright JSON 列表，解析 `name` 字段，全部包含 `huawei` 返回 true；空列表、解析失败、name 为空或不含 huawei 均返回 false
  - 新增 3 个单元测试：`testAutoSubmitConfirmV2_OnlyCopyrightFail_Huawei_AutoConfirm` / `testAutoSubmitConfirmV2_OnlyCopyrightFail_NonHuawei_NoAutoConfirm` / `testAutoSubmitConfirmV2_OnlyCopyrightFail_Mixed_NoAutoConfirm`
  - `mvn clean package` 编译通过
  - 文件：`src/main/java/com/openlibing/sca/analysis/service/impl/ConfirmReviewServceImpl.java` | `src/test/java/.../ConfirmReviewServceImplTest.java`

## 后续可选项（不在本次 PR 范围）

- [ ] 增加 `getPrCommitShas`、`getIncrementalPrDiff`、`fetchFileContent` 的 API 调用成功率指标埋点
- [ ] 为 `prCommitsCache` 与 `incrementalDiffCache` 加容量上限与过期策略（当前依赖请求生命周期回收）
- [ ] 存量 `pr_head_sha` 为 NULL 的历史 TblIssue 数据回填策略（如需启用增量 diff）
