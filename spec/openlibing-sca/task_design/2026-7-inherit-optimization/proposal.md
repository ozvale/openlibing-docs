# Proposal: SCA 扫描结果继承逻辑优化

## Summary

本次变更对 `openlibing-sca` 的 PR 扫描结果继承链路进行优化，目标是让 PR 重复扫描时能够更精确地从历史审核记录中继承评审结论，同时避免跨 PR 历史污染增量 diff 基线。优化点集中在 `ScanCommonServiceImpl` 的历史匹配算法、`IntegrationApiServiceImpl.processBatchIssues` 的执行顺序、`TblIssue` 实体与 `tbl_issue` 表的 `pr_head_sha` 字段扩展，以及配套的 Liquibase 迁移与单元测试。

关联业务 PR：
- [openlibing/openlibing-sca#214](https://gitcode.com/openlibing/openlibing-sca/merge_requests/214)（合入 `release_20260715`）— 继承逻辑优化主变更
- [openlibing/openlibing-sca#250](https://gitcode.com/openlibing/openlibing-sca/merge_requests/250)（合入 `release_fix_20260723`）— force push 两树直接 diff 修复
- commit `fad72408`（`ms_alert` 分支，待 PR）— copyright-only 告警自动确认

关联业务 Issue：[openlibing/openlibing-sca#54](https://gitcode.com/openlibing/openlibing-sca/issues/54)（[合法合规] 版本批量扫描、继承逻辑和 notice 生成优化）

## Motivation

在 SCA PR 扫描场景下，每次 PR 推送新 commit 都会触发一次扫描。若不继承历史审核结论，已被人工确认或自动确认的问题会反复出现在待审列表中，造成审核人重复劳动；若继承逻辑过宽，则会让本应重新审核的问题被错误继承，留下合规盲区。原有实现存在三类问题：

1. **历史匹配优先级不清晰**：`getTblIssues` 仅按 `repoId + fileHash + scanFile` 分组取最新一条，未区分 `sourceHash` 完全匹配与 `fileHash` 退化匹配，导致同一文件在 sourceHash 变化时仍可能命中过期的历史记录。
2. **增量 diff 基线不可靠**：增量 diff 的 `baseSha` 直接使用上一次审核时的 PR head commit。若该 commit 实际属于另一个 PR（fork 仓分支复用、PR 链中断等场景），compare API 会返回跨 PR 的差异，污染当前 PR 的"修改行范围"判定，进而误判继承。
3. **审核人多评审信息丢失**：`processBatchIssues` 在写 mongo 前未回填 `scanIssue.commitId`，导致下游构建 `TblIssue` 时 `prHeadSha` 缺失，且多评审人信息在批量处理过程中易被覆盖。

本次优化通过引入 `pr_head_sha` 字段记录审核基线、`getPrCommitShas` 校验 baseSha 归属、`backfillPrHeadCommitId` 修正执行顺序、`findMatchingIssue` 三级匹配优先级，系统性地解决上述问题。

### Force Push 场景修复（补充变更，commit `b7f2a8a5`，PR #250）

合入 `release_20260715` 后，生产环境出现继承逻辑在 force push 场景下失效的问题。典型案例：PR `cann/ops-cv#1126` 中 `to_absolute_b_box_tiling_arch35.cpp` 在 commit `865b0843` 审核通过后，`c98e20e3` force push 后扫描未继承审核结论。

根因分析：
1. **三点 diff 落到 merge_base**：force push 后 `baseSha`（旧审核时的 head）不在当前 PR 提交链中，原实现回退到 PR 全量 diff。而 compare API 的 `base...head` 三点语法在 base 不是 head 祖先时会落在 merge_base 上，把整文件判为 `added`。
2. **added 文件被 isInModifiedRange 误判跳过**：`added` 文件的 `modifiedLines` 是全行合集，`isInModifiedRange` 恒为 true，导致 3a 阶段错误跳过继承。

修复方案：
- 在 `resolveFileDiff` 中新增第四优先级：当 baseSha 不在提交链时，改用 `baseSha` 与 `currentHeadSha` 两棵树的**直接 diff**（contents API 逐文件取内容 + jgit `MyersDiff` 本地计算），仅报出真正改动的行。
- `findMatchingIssue` 中 `added` 文件跳过 `isInModifiedRange` 检查，直接进 3b 字段匹配；`added` 文件无 base 侧行号可还原，`adjustedLines` 直接使用当前行号。

### Copyright-Only 告警自动确认（补充变更，commit `fad72408`，`ms_alert` 分支）

版本扫描与 PR 扫描的 `autoSubmitConfirmV2` 自动确认流程中，原有规则仅自动确认 `license=SUCCESS + copyright=SUCCESS` 的问题。在实际运营中发现：大量开源组件的 copyright 被标记为 FAIL（如 `Copyright (c) Huawei Technologies Co., Ltd.`），但这些组件实际是华为自研代码，不需要人工审核，造成了审核人重复劳动。

修复方案：
- 在 `autoSubmitConfirmV2` 中新增一条自动确认分支：`license=SUCCESS + copyright=FAIL` 且远程（开源软件）copyright 全部包含 "huawei" 时，自动确认
- 新增 `isRemoteCopyrightOnlyHuawei` 私有方法：遍历远程 copyright 列表，逐条解析 JSON `name` 字段，全部包含 `huawei`（不区分大小写）时返回 true；任一条解析失败或 name 为空或不含 huawei 则返回 false

## Scope

### 涉及文件

| 文件 | 操作 | 角色 |
|------|------|------|
| `src/main/java/com/openlibing/sca/dm/service/impl/ScanCommonServiceImpl.java` | 修改 | 继承核心逻辑：历史匹配、增量 diff、baseSha 校验、**两树直接 diff（force push 修复）** |
| `src/main/java/com/openlibing/sca/dm/service/impl/IntegrationApiServiceImpl.java` | 修改 | `processBatchIssues` 流程重构与 `backfillPrHeadCommitId` |
| `src/main/java/com/openlibing/sca/analysis/entity/TblIssue.java` | 修改 | 新增 `prHeadSha` 字段及 Builder |
| `src/main/resources/mapper/dm/TblIssueMapper.xml` | 修改 | insert/update/select 加入 `pr_head_sha` |
| `src/main/resources/db/changelog/db.changelog.xml` | 修改 | 注册新 changeset |
| `src/main/resources/db/changelog/mysql/20260715/add-tbl-issue-commit-id.xml` | 新增 | `tbl_issue.pr_head_sha` 列迁移 |
| `src/test/java/com/openlibing/sca/dm/service/impl/ScanCommonServiceImplTest.java` | 修改 | 新增 4 个匹配优先级测试 + **5 个 force push / added 文件测试** |
| `src/main/java/com/openlibing/sca/analysis/service/impl/ConfirmReviewServceImpl.java` | 修改 | `autoSubmitConfirmV2` 新增 copyright-only huawei 自动确认分支 + `isRemoteCopyrightOnlyHuawei` |
| `src/test/java/com/openlibing/sca/analysis/service/impl/ConfirmReviewServceImplTest.java` | 修改 | 新增 3 个自动确认测试（全 huawei / 非 huawei / 混合） |

### 核心方法

- `ScanCommonServiceImpl#getTblIssues` — 历史问题分组与最新记录选取
- `ScanCommonServiceImpl#findMatchingIssue` — 三级匹配：sourceHash+fileHash 完全匹配 → fileHash fallback → 字段全匹配
- `ScanCommonServiceImpl#isValidForInheritance` — 历史记录有效性校验（manual 或 auto+licenseStatus 非空）
- `ScanCommonServiceImpl#getPrCommitShas` — 拉取并缓存当前 PR 全部提交 sha，用于校验 baseSha 归属
- `ScanCommonServiceImpl#getIncrementalPrDiff` / `buildCompareApiUrl` — 调用平台 compare API 获取 `base...head` 增量 diff
- `ScanCommonServiceImpl#prResultInherit` — PR 结果继承主流程
- `IntegrationApiServiceImpl#processBatchIssues` — 批量问题处理流程（重构后拆分为 5 个私有方法）
- `IntegrationApiServiceImpl#backfillPrHeadCommitId` — 新增：写 mongo 前回填 `scanIssue.commitId`

### Force Push 修复新增方法（commit `b7f2a8a5`）

- `ScanCommonServiceImpl#resolveFileDiff` — 重构：原 `resolveEffectiveDiffMap` 改为按单文件解析 diff，新增直接 diff 优先级
- `ScanCommonServiceImpl#getIncrementalDiffMap` — 提取：原内联三点 diff 逻辑独立为方法，带缓存
- `ScanCommonServiceImpl#getDirectFileDiff` — 新增：baseSha 不在提交链时，取两棵树文件内容做直接 diff，结果按 `baseSha|headSha|filePath` 缓存
- `ScanCommonServiceImpl#fetchFileContent` — 新增：通过 contents API 取指定 commit 下文件文本内容（支持 base64 解码）
- `ScanCommonServiceImpl#buildFileContentApiUrl` — 新增：构建 contents API URL（gitee / gitcode 双平台），路径编码处理 `/`
- `ScanCommonServiceImpl#parseOwnerAndRepo` — 新增：从 mergeUrl 解析 owner 与 repo
- `ScanCommonServiceImpl#computeDirectDiff` — 新增：用 jgit `MyersDiff`（`RawTextComparator.DEFAULT`）计算两份文件内容的行级 diff，生成 `PrDiffDto`（status 固定 `modified`）
- `PrInheritContext#directDiffCache` — 新增：`Map<String, PrDiffDto>` 直接 diff 缓存

### Copyright-Only 告警自动确认新增方法（commit `fad72408`）

- `ConfirmReviewServceImpl#autoSubmitConfirmV2` — 新增 `license=SUCCESS + copyright=FAIL + 远程 copyright 全为 huawei` 自动确认分支
- `ConfirmReviewServceImpl#isRemoteCopyrightOnlyHuawei` — 新增：遍历远程 copyright JSON 列表，校验所有条目的 `name` 字段是否全部包含 `huawei`（不区分大小写）

### 不在范围内

- 不修改 `ossinfo_extraction` Python 工具
- 不调整 PR 扫描工作流（`.gitcode/workflows/sca-pr-scan.yml`）的 Job 拆分
- 不变更看板数据回填、OSS 信息抽取集成（这些主题在 PR #214 中独立承载）
- 不引入新的评审人数据模型，复用现有 `TblIssue.userId` + `names` map

## Acceptance Criteria

- [ ] 同一 scanFile 下，`sourceHash + fileHash` 完全匹配的历史记录优先于仅 `fileHash` 匹配的记录被继承
- [ ] `sourceHash` 不一致但 `fileHash` 一致时，可作为 fallback 命中；与完全匹配共存时仅保留完全匹配
- [ ] `fileHash` 完全不匹配的历史记录被过滤，不进入继承结果
- [ ] `baseSha` 不属于当前 PR 提交链时（force push 等），改用两棵树直接 diff 而非回退 PR 全量 diff；直接 diff 取不到时才回退 PR 全量 diff
- [ ] compare API 调用失败时回退到 PR 全量 diff，日志记录 `incremental diff fetch failed`
- [ ] `tbl_issue.pr_head_sha` 字段在 insert / update / select 中均正确持久化与读取
- [ ] `processBatchIssues` 在调用 `resultInherit` 之前完成 `scanIssue.commitId` 回填，保证写 mongo 时 `prHeadSha` 已就绪
- [ ] 历史问题仅当 `committerType=manual` 或 `auto + licenseStatus 非空` 时才参与继承
- [ ] `ScanCommonServiceImplTest` 新增的 **9 个**测试用例全部通过（含 4 个匹配优先级 + 5 个 force push / added 文件）
- [ ] `mvn clean package` 编译通过
- [ ] force push 后 `baseSha` 不在提交链时，改用两棵树直接 diff，不再回退到 PR 全量 diff
- [ ] `added` 文件跳过 `isInModifiedRange` 检查，直接进 3b 字段匹配继承
- [ ] `computeDirectDiff` 仅报出两树之间真正改动的行，未改动片段不被误报
- [ ] contents API 调用失败时 `getDirectFileDiff` 返回空，整链回退到 PR 全量 diff 保留原有降级行为
- [ ] `autoSubmitConfirmV2` 中 `license=SUCCESS + copyright=FAIL` 且远程 copyright 全部包含 `huawei` 的 issue 被自动确认
- [ ] 远程 copyright 不含 `huawei` 或含混合版权时，`license=SUCCESS + copyright=FAIL` 的 issue 保持原状不自动确认
- [ ] `isRemoteCopyrightOnlyHuawei` 对空列表返回 false，对 JSON 解析失败返回 false
- [ ] `ConfirmReviewServceImplTest` 新增的 3 个测试用例全部通过

## 影响范围

- **业务模块**：SCA PR 扫描结果继承链路（`dm` 模块）、自动确认流程（`analysis` 模块）
- **DB schema**：`tbl_issue` 新增 `pr_head_sha VARCHAR(64) NULL`，需在部署前完成 Liquibase 迁移
- **下游依赖**：依赖平台 compare API 与 PR commits API（gitee / gitcode），调用失败时有 fallback 行为
- **跨仓影响**：无；本次改动均在 `openlibing-sca` 业务仓内
