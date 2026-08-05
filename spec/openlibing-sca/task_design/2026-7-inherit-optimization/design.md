# Design: SCA 扫描结果继承逻辑优化

## 方案概述

围绕 `ScanCommonServiceImpl` 的继承匹配算法与 `IntegrationApiServiceImpl.processBatchIssues` 的执行顺序，引入三级历史匹配优先级、`pr_head_sha` 基线字段、`getPrCommitShas` 归属校验三层机制，确保 PR 重复扫描时继承结论既精确又不被跨 PR 历史污染。增量 diff 基线由"上次审核时的 PR head commit"提供，并通过 PR commits API 校验其归属，再调用 compare API 拉取增量 diff；任一环节失败均回退到 PR 全量 diff，保留原有行为。

## 架构决策

### 决策 1：以 `pr_head_sha` 作为增量 diff 基线，而非 `commitId`

**背景**：原实现 `baseSha` 来源不稳定，跨 PR 场景下 compare API 会返回跨 PR 的差异。

**决策**：在 `tbl_issue` 新增 `pr_head_sha` 字段，专门记录"审核通过时的 PR head commit sha"。继承时以此作为 `baseSha`，语义清晰、来源单一。

**代价**：新增一列，需 Liquibase 迁移；存量历史记录的 `pr_head_sha` 为 NULL，继承时按"无基线"处理（回退到 PR 全量 diff）。

### 决策 2：baseSha 校验失败时回退到全量 diff，而非拒绝继承

**背景**：`getPrCommitShas` 可能因 API 失败返回空集，或 baseSha 真的不属于当前 PR。

**决策**：
- `prCommitShas.isEmpty()` → 视为"无法校验"，放行到 compare API（保留原有行为，避免 API 故障导致继承全部失效）
- `!prCommitShas.isEmpty() && !prCommitShas.contains(baseSha)` → 明确不属于当前 PR，回退到 PR 全量 diff，日志告警

**理由**：兼容性优先，宁可降级到全量 diff 也不阻塞继承流程。

### 决策 3：历史匹配采用三级优先级，同 key 仅保留最优

**背景**：原 `getTblIssues` 仅按 `repoId + fileHash + scanFile` 分组取最新，未区分 sourceHash 是否一致。

**决策**：`findMatchingIssue` 内部按以下顺序匹配：
1. **完全匹配**：`sourceHash + fileHash` 均一致 → 直接继承（`isExactHashMatch`）
2. **fallback 匹配**：`fileHash` 一致但 `sourceHash` 不一致 → 进入 `isAllFieldsMatch` 校验 license / copyright / lines / openLines 等字段
3. **字段全匹配**：上述字段全部一致 → 继承并落库新 TblIssue

同 key 下完全匹配优先，fallback 被抑制；`fileHash` 完全不匹配的记录在 `getTblIssues` 阶段即被分组过滤。

### 决策 4：`processBatchIssues` 拆分为 5 个私有方法，强制回填顺序

**背景**：原方法长达百行，且 `scanIssue.commitId` 在写 mongo 时未就绪。

**决策**：重构为：
```
processBatchIssues:
  1. extractScanFileList
  2. backfillPrHeadCommitId      ← 新增：回填 scanIssue.commitId
  3. scanCommonService.resultInherit
  4. buildShieldRoleDto + doShieldRole
  5. saveScanResult               ← 写 mongo（commitId 已就绪）
  6. filterAndMarkUnconfirmed
  7. executeBatchAnalysisIfNeed
```

每个私有方法职责单一，便于测试与维护。

### 决策 5：增量 diff 与 PR commits 双缓存

**背景**：同一次扫描可能处理多个 batch，每个 batch 都可能需要相同的 PR commits 集合与同 baseSha 的增量 diff。

**决策**：
- `prCommitsCache`：`Map<String, Set<String>>`，key 为 mergeUrl，value 为 PR 全部提交 sha 集合
- `incrementalDiffCache`：`Map<String, Map<String, PrDiffDto>>`，key 为 baseSha，value 为增量 diff 文件映射

缓存生命周期限定在单次扫描请求内，避免跨请求污染。

## 涉及文件

| 文件 | 操作 | 关键改动 |
|------|------|---------|
| `ScanCommonServiceImpl.java` | 修改 | 新增 `getPrCommitShas` / `buildPrCommitsApiUrl` / `getIncrementalPrDiff` / `buildCompareApiUrl`；`findMatchingIssue` 加入 `isExactHashMatch` 短路；`isInModifiedRange` 加 prDiff null 防护；`getTblIssueInfo` 写入 `prHeadSha(scan.getCommitId())` |
| `IntegrationApiServiceImpl.java` | 修改 | `processBatchIssues` 拆分为 `extractScanFileList` / `backfillPrHeadCommitId` / `buildShieldRoleDto` / `filterAndMarkUnconfirmed` / `executeBatchAnalysisIfNeed` |
| `TblIssue.java` | 修改 | 新增 `prHeadSha` 字段、Builder 方法、`build()` 与 `toBuilder()` 同步 |
| `TblIssueMapper.xml` | 修改 | insert / update / select 加入 `pr_head_sha` 列与映射 |
| `db.changelog.xml` | 修改 | include 新 changeset `20260715/add-tbl-issue-commit-id.xml` |
| `add-tbl-issue-commit-id.xml` | 新增 | `addColumn tableName="tbl_issue"` 加 `pr_head_sha VARCHAR(64)`，含 `preConditions` 与 `rollback` |
| `ScanCommonServiceImplTest.java` | 修改 | 新增 `testGetTblIssues_FallbackToFileHashOnly` / `testGetTblIssues_BothMatchAndFallback_BothMatchWins` / `testGetTblIssues_NoHashMatch_FilteredOut` / `testGetTblIssues_ExactHashMatch_Prioritized` 4 个用例 |

## 关键流程

### 增量 diff 获取流程

```
prResultInherit
   │
   ▼
getPrDiffFileMap(mergeUrl, projectId, platform, baseSha, currentHeadSha)
   │
   ├── 1. 查 incrementalDiffCache，命中直接返回
   │
   ├── 2. getPrCommitShas(mergeUrl, projectId, platform, prCommitsCache)
   │      ├── 命中缓存 → 返回 sha 集合
   │      └── 调用 PR commits API → 解析 → 缓存 → 返回
   │
   ├── 3. 校验 baseSha
   │      ├── prCommitShas.isEmpty() → 放行到 compare API（API 故障容错）
   │      └── !contains(baseSha) → 日志告警 + 回退 PR 全量 diff
   │
   ├── 4. getIncrementalPrDiff(baseSha, currentHeadSha, ...)
   │      ├── 调用 compare API (base...head) → 解析为 PrDiffDto map
   │      └── 失败 → 回退 PR 全量 diff
   │
   └── 5. 写入 incrementalDiffCache，返回
```

### 历史匹配优先级

```
findMatchingIssue(currentIssue, tblIssues, prDiffFileMap)
   │
   ▼ 遍历 tblIssues（已按 modified desc 排序）
   │
   ├── normalizeFilePath 不一致 → 跳过
   ├── !isValidForInheritance → 跳过（manual 或 auto+licenseStatus 非空）
   │
   ├── isExactHashMatch (sourceHash + fileHash 全等)
   │      └── true → 直接返回（最高优先级）
   │
   ├── isInModifiedRange(currentIssue.lines, prDiff)
   │      └── true → 跳过该历史（修改行命中范围，不继承）
   │
   └── isAllFieldsMatch (license / copyright / hash / lines / openLines)
          └── true → 落库新 TblIssue + 返回（fallback 路径）
```

## 风险 & 缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| DB 迁移失败导致服务启动受阻 | 部署阶段 | changeset 加 `preConditions onFail="MARK_RAN"`，已存在则跳过；提供 `rollback` 删列 |
| compare / PR commits API 限流或故障 | 继承降级 | 双缓存减少调用；API 失败回退 PR 全量 diff，保留原有行为 |
| 存量历史 `pr_head_sha` 为 NULL | 增量 diff 不可用 | baseSha 为空时直接走 PR 全量 diff，不阻塞继承 |
| `prCommitsCache` 跨 batch 失效导致重复调用 | 性能下降 | 缓存 key 为 mergeUrl，单次扫描请求内复用 |
| sourceHash 变化但 fileHash 不变时误继承 | 合规盲区 | fallback 路径仍需通过 `isAllFieldsMatch` 全字段校验，不通过则不继承 |
| baseSha 跨 PR 历史污染 | 错误继承 | `getPrCommitShas` 明确校验归属，不在 PR commits 即回退全量 diff |

## 跨仓影响

无。本次改动全部在 `openlibing-sca` 业务仓内，不涉及跨仓接口或契约变化。
