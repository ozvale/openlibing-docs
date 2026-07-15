# Proposal: SCA 扫描结果继承逻辑优化

## Summary

本次变更对 `openlibing-sca` 的 PR 扫描结果继承链路进行优化，目标是让 PR 重复扫描时能够更精确地从历史审核记录中继承评审结论，同时避免跨 PR 历史污染增量 diff 基线。优化点集中在 `ScanCommonServiceImpl` 的历史匹配算法、`IntegrationApiServiceImpl.processBatchIssues` 的执行顺序、`TblIssue` 实体与 `tbl_issue` 表的 `pr_head_sha` 字段扩展，以及配套的 Liquibase 迁移与单元测试。

关联业务 PR：[openlibing/openlibing-sca#214](https://gitcode.com/openlibing/openlibing-sca/merge_requests/214)（合入 `release_20260715`）
关联业务 Issue：[openlibing/openlibing-sca#54](https://gitcode.com/openlibing/openlibing-sca/issues/54)（[合法合规] 版本批量扫描、继承逻辑和 notice 生成优化）

## Motivation

在 SCA PR 扫描场景下，每次 PR 推送新 commit 都会触发一次扫描。若不继承历史审核结论，已被人工确认或自动确认的问题会反复出现在待审列表中，造成审核人重复劳动；若继承逻辑过宽，则会让本应重新审核的问题被错误继承，留下合规盲区。原有实现存在三类问题：

1. **历史匹配优先级不清晰**：`getTblIssues` 仅按 `repoId + fileHash + scanFile` 分组取最新一条，未区分 `sourceHash` 完全匹配与 `fileHash` 退化匹配，导致同一文件在 sourceHash 变化时仍可能命中过期的历史记录。
2. **增量 diff 基线不可靠**：增量 diff 的 `baseSha` 直接使用上一次审核时的 PR head commit。若该 commit 实际属于另一个 PR（fork 仓分支复用、PR 链中断等场景），compare API 会返回跨 PR 的差异，污染当前 PR 的"修改行范围"判定，进而误判继承。
3. **审核人多评审信息丢失**：`processBatchIssues` 在写 mongo 前未回填 `scanIssue.commitId`，导致下游构建 `TblIssue` 时 `prHeadSha` 缺失，且多评审人信息在批量处理过程中易被覆盖。

本次优化通过引入 `pr_head_sha` 字段记录审核基线、`getPrCommitShas` 校验 baseSha 归属、`backfillPrHeadCommitId` 修正执行顺序、`findMatchingIssue` 三级匹配优先级，系统性地解决上述问题。

## Scope

### 涉及文件

| 文件 | 操作 | 角色 |
|------|------|------|
| `src/main/java/com/openlibing/sca/dm/service/impl/ScanCommonServiceImpl.java` | 修改 | 继承核心逻辑：历史匹配、增量 diff、baseSha 校验 |
| `src/main/java/com/openlibing/sca/dm/service/impl/IntegrationApiServiceImpl.java` | 修改 | `processBatchIssues` 流程重构与 `backfillPrHeadCommitId` |
| `src/main/java/com/openlibing/sca/analysis/entity/TblIssue.java` | 修改 | 新增 `prHeadSha` 字段及 Builder |
| `src/main/resources/mapper/dm/TblIssueMapper.xml` | 修改 | insert/update/select 加入 `pr_head_sha` |
| `src/main/resources/db/changelog/db.changelog.xml` | 修改 | 注册新 changeset |
| `src/main/resources/db/changelog/mysql/20260715/add-tbl-issue-commit-id.xml` | 新增 | `tbl_issue.pr_head_sha` 列迁移 |
| `src/test/java/com/openlibing/sca/dm/service/impl/ScanCommonServiceImplTest.java` | 修改 | 新增 4 个 fallback / 优先级测试用例 |

### 核心方法

- `ScanCommonServiceImpl#getTblIssues` — 历史问题分组与最新记录选取
- `ScanCommonServiceImpl#findMatchingIssue` — 三级匹配：sourceHash+fileHash 完全匹配 → fileHash fallback → 字段全匹配
- `ScanCommonServiceImpl#isValidForInheritance` — 历史记录有效性校验（manual 或 auto+licenseStatus 非空）
- `ScanCommonServiceImpl#getPrCommitShas` — 拉取并缓存当前 PR 全部提交 sha，用于校验 baseSha 归属
- `ScanCommonServiceImpl#getIncrementalPrDiff` / `buildCompareApiUrl` — 调用平台 compare API 获取 `base...head` 增量 diff
- `ScanCommonServiceImpl#prResultInherit` — PR 结果继承主流程
- `IntegrationApiServiceImpl#processBatchIssues` — 批量问题处理流程（重构后拆分为 5 个私有方法）
- `IntegrationApiServiceImpl#backfillPrHeadCommitId` — 新增：写 mongo 前回填 `scanIssue.commitId`

### 不在范围内

- 不修改 `ossinfo_extraction` Python 工具
- 不调整 PR 扫描工作流（`.gitcode/workflows/sca-pr-scan.yml`）的 Job 拆分
- 不变更看板数据回填、OSS 信息抽取集成（这些主题在 PR #214 中独立承载）
- 不引入新的评审人数据模型，复用现有 `TblIssue.userId` + `names` map

## Acceptance Criteria

- [ ] 同一 scanFile 下，`sourceHash + fileHash` 完全匹配的历史记录优先于仅 `fileHash` 匹配的记录被继承
- [ ] `sourceHash` 不一致但 `fileHash` 一致时，可作为 fallback 命中；与完全匹配共存时仅保留完全匹配
- [ ] `fileHash` 完全不匹配的历史记录被过滤，不进入继承结果
- [ ] `baseSha` 不属于当前 PR 提交链时，回退到 PR 全量 diff，并在日志中记录 `baseSha not in current PR commits`
- [ ] compare API 调用失败时回退到 PR 全量 diff，日志记录 `incremental diff fetch failed`
- [ ] `tbl_issue.pr_head_sha` 字段在 insert / update / select 中均正确持久化与读取
- [ ] `processBatchIssues` 在调用 `resultInherit` 之前完成 `scanIssue.commitId` 回填，保证写 mongo 时 `prHeadSha` 已就绪
- [ ] 历史问题仅当 `committerType=manual` 或 `auto + licenseStatus 非空` 时才参与继承
- [ ] `ScanCommonServiceImplTest` 新增的 4 个测试用例全部通过
- [ ] `mvn clean package` 编译通过

## 影响范围

- **业务模块**：SCA PR 扫描结果继承链路（`dm` 模块）
- **DB schema**：`tbl_issue` 新增 `pr_head_sha VARCHAR(64) NULL`，需在部署前完成 Liquibase 迁移
- **下游依赖**：依赖平台 compare API 与 PR commits API（gitee / gitcode），调用失败时有 fallback 行为
- **跨仓影响**：无；本次改动均在 `openlibing-sca` 业务仓内
