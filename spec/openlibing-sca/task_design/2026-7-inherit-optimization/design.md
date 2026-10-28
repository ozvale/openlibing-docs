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

### 决策 6：force push 场景下用两棵树直接 diff 代替三点 diff（commit `b7f2a8a5`）

**背景**：PR #250 合入前，`baseSha` 不在当前 PR 提交链时（force push 抛弃旧 head），原实现回退到 PR 全量 diff。但 compare API 的 `base...head` 三点语法在 base 不是 head 祖先时会落在 merge_base 上，把整文件判为 `added`，导致 `isInModifiedRange` 恒为 true 错误跳过继承。

**决策**：

- 在 `resolveFileDiff` 中新增第四优先级：baseSha 不在提交链 → 调用 `getDirectFileDiff` 计算两棵树直接 diff
- `getDirectFileDiff` 通过 contents API 分别取 `baseSha` 和 `headSha` 的文件内容，用 jgit `MyersDiff`（`RawTextComparator.DEFAULT`）本地计算行级差异
- 直接 diff 结果的 `PrDiffDto.status` 固定为 `modified`，`modifiedLines` 仅包含真正改动的行
- `findMatchingIssue` 中 `added` 状态文件跳过 `isInModifiedRange` 直接进 3b 字段匹配
- `added` 文件无 base 侧行号可还原，`adjustedLines` 直接使用当前行号

**代价**：引入 jgit 依赖（项目已有）；contents API 增量调用，但经 `directDiffCache` 缓存单次请求内只调一次。

### 决策 7：`resolveFileDiff` 重构为按单文件返回（commit `b7f2a8a5`）

**背景**：原 `resolveEffectiveDiffMap` 按 baseSha 缓存整个增量 diff map，force push 后 baseSha 与 headSha 之间需要逐文件做直接 diff，整 map 缓存不再适用。

**决策**：重构为 `resolveFileDiff`，按单个文件解析 diff：

1. baseSha 为空/等于 head → 返回 `prDiffFileMap.get(filePath)`
2. baseSha 在提交链 → `getIncrementalDiffMap` 取三点 diff，命中返回
3. baseSha 不在提交链 → `getDirectFileDiff` 取两树直接 diff，取到返回
4. 以上均失败 → 返回 `prDiffFileMap.get(filePath)` 降级

提取原内联三点 diff 逻辑为独立方法 `getIncrementalDiffMap`。

### 决策 5：增量 diff、PR commits、直接 diff 三缓存（commit `b7f2a8a5` 补 directDiffCache）

**背景**：同一次扫描可能处理多个 batch，每个 batch 都可能需要相同的 PR commits 集合与同 baseSha 的增量 diff。force push 修复新增 contents API 调用，同样需要缓存。

**决策**：

- `prCommitsCache`：`Map<String, Set<String>>`，key 为 mergeUrl，value 为 PR 全部提交 sha 集合
- `incrementalDiffCache`：`Map<String, Map<String, PrDiffDto>>`，key 为 baseSha，value 为增量 diff 文件映射
- `directDiffCache`：`Map<String, PrDiffDto>`，key 为 `baseSha|headSha|filePath`，value 为单文件直接 diff

缓存生命周期限定在单次扫描请求内，避免跨请求污染。

### 决策 8：`autoSubmitConfirmV2` 新增 huawei copyright-only 自动确认分支（commit `fad72408`）

**背景**：版本扫描与 PR 扫描的 `autoSubmitConfirmV2` 中，现有自动确认规则仅覆盖 `license=SUCCESS + copyright=SUCCESS` 的 issue。大量华为自研开源组件的 remote copyright 被标记为 FAIL（如 `Copyright (c) Huawei Technologies Co., Ltd.`），这些 issue 本不需要人工审核，却在待审列表中堆积。

**决策**：在 `autoSubmitConfirmV2` 的自动确认识别循环中，新增一条分支：`license=SUCCESS + copyright=FAIL` 且所有远程 copyright 条目的 `name` 字段均包含 `huawei`（不区分大小写，通过 `isRemoteCopyrightOnlyHuawei` 判定）。

**`isRemoteCopyrightOnlyHuawei` 判定逻辑**：

- 入参 `copyrights` 为空或 null → 返回 `false`
- 遍历每条 copyright，用 `JSONObject.parseObject` 解析 `name` 字段
- 任一条解析失败 → 返回 `false`（防御性：宁可不确认也不误确认）
- 任一条 `name` 为空或不含 `huawei` → 返回 `false`
- 全部通过 → 返回 `true`

**安全考量**：

- 大小写不敏感匹配（`toLowerCase(Locale.ENGLISH)`），覆盖 `Huawei`、`HUAWEI`、`huawei` 等变体
- JSON 解析异常捕获：copyright 数据格式异常时退回不确认，不抛异常中断流程
- 混合版权（如 huawei + acme）不会误确认，要求**全部**条目均含 huawei

**代价**：无 schema 变更、无新依赖；仅 `ConfirmReviewServceImpl` 内新增 ~30 行代码 + 3 个测试。

## 涉及文件

| 文件                               | 操作 | 关键改动                                                                                                                                                                                                                                                                                                                                                                                                                                                               |
| ---------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `ScanCommonServiceImpl.java`       | 修改 | 新增 `getPrCommitShas` / `buildPrCommitsApiUrl` / `getIncrementalPrDiff` / `buildCompareApiUrl`；`findMatchingIssue` 加入 `isExactHashMatch` 短路；`isInModifiedRange` 加 prDiff null 防护；`getTblIssueInfo` 写入 `prHeadSha(scan.getCommitId())`；**`resolveFileDiff` 重构为按单文件返回，新增两树直接 diff 优先级；`getDirectFileDiff` / `fetchFileContent` / `buildFileContentApiUrl` / `parseOwnerAndRepo` / `computeDirectDiff` 实现 force push 直接 diff 链路** |
| `IntegrationApiServiceImpl.java`   | 修改 | `processBatchIssues` 拆分为 `extractScanFileList` / `backfillPrHeadCommitId` / `buildShieldRoleDto` / `filterAndMarkUnconfirmed` / `executeBatchAnalysisIfNeed`                                                                                                                                                                                                                                                                                                        |
| `TblIssue.java`                    | 修改 | 新增 `prHeadSha` 字段、Builder 方法、`build()` 与 `toBuilder()` 同步                                                                                                                                                                                                                                                                                                                                                                                                   |
| `TblIssueMapper.xml`               | 修改 | insert / update / select 加入 `pr_head_sha` 列与映射                                                                                                                                                                                                                                                                                                                                                                                                                   |
| `db.changelog.xml`                 | 修改 | include 新 changeset `20260715/add-tbl-issue-commit-id.xml`                                                                                                                                                                                                                                                                                                                                                                                                            |
| `add-tbl-issue-commit-id.xml`      | 新增 | `addColumn tableName="tbl_issue"` 加 `pr_head_sha VARCHAR(64)`，含 `preConditions` 与 `rollback`                                                                                                                                                                                                                                                                                                                                                                       |
| `ScanCommonServiceImplTest.java`   | 修改 | 新增 4 个匹配优先级用例 + **5 个 force push / added 文件用例**                                                                                                                                                                                                                                                                                                                                                                                                         |
| `ConfirmReviewServceImpl.java`     | 修改 | `autoSubmitConfirmV2` 新增 `license=SUCCESS + copyright=FAIL + 远程 copyright 全 huawei` 自动确认分支 + `isRemoteCopyrightOnlyHuawei`                                                                                                                                                                                                                                                                                                                                  |
| `ConfirmReviewServceImplTest.java` | 修改 | 新增 3 个自动确认测试（全 huawei 自动确认 / 非 huawei 不确认 / 混合不确认）                                                                                                                                                                                                                                                                                                                                                                                            |

## 关键流程

### resolveFileDiff 四优先级流程（commit `b7f2a8a5` 重构）

```
resolveFileDiff(baseSha, filePath, context, prDiffFileMap)
   │
   ├── 1. baseSha 为空 || baseSha == headSha → 返回 prDiffFileMap.get(filePath)
   │
   ├── 2. getPrCommitShas(mergeUrl) → prCommitShas
   │      ├── prCommitShas.isEmpty() → 放行：API 故障容错，进入步骤 2b
   │      └── prCommitShas.contains(baseSha) → 进入步骤 2b
   │
   ├── 2b. getIncrementalDiffMap(baseSha, context)
   │      ├── 查 incrementalDiffCache，命中返回 → 返回 incrementalMap.get(filePath)
   │      └── 调 compare API (base...head) → 解析 → 缓存 → 返回 incrementalMap.get(filePath)
   │      └── 失败 → 降级到步骤 4
   │
   ├── 3. baseSha 不在提交链（force push）→ getDirectFileDiff(baseSha, headSha, filePath, context)
   │      ├── 查 directDiffCache，命中返回
   │      ├── fetchFileContent(baseSha, filePath) + fetchFileContent(headSha, filePath)
   │      │     └── 任一侧取不到内容（文件在另一侧不存在）→ 缓存 null，返回 empty
   │      ├── computeDirectDiff(baseContent, headContent, filePath)
   │      │     └── jgit MyersDiff + RawTextComparator.DEFAULT → PrDiffDto(status="modified")
   │      └── 写入 directDiffCache，返回
   │      └── 失败 → 降级到步骤 4
   │
   └── 4. 以上均失败 → 返回 prDiffFileMap.get(filePath) 降级（保留原有行为）
```

### 直接 diff 内部流程

```
getDirectFileDiff(baseSha, headSha, filePath, context)
   │
   ├── cacheKey = "baseSha|headSha|filePath"
   ├── 查 directDiffCache，命中跳过
   │
   ├── fetchFileContent(baseSha, filePath)
   │      └── 调 contents API (GET /repos/{o}/{r}/contents/{path}?ref=baseSha)
   │      └── 解析 JSON: {content, encoding} → base64 MIME decode → UTF-8 text
   │
   ├── fetchFileContent(headSha, filePath) 同上
   │
   └── computeDirectDiff(baseText, headText, filePath)
          ├── jgit MyersDiff.diff(RawTextComparator.DEFAULT, baseText, headText)
          ├── EditList 为空 → PrDiffDto(status="modified", modifiedLines=[])
          └── 遍历 Edit[] → 构建 unified diff hunk header + head 侧 modifiedLines（1-indexed）
```

### 历史匹配优先级（含 force push 修复）

```
findMatchingIssue(currentIssue, tblIssues, prDiff)
   │
   ▼ 遍历 tblIssues（已按 modified desc 排序）
   │
   ├── normalizeFilePath 不一致 → 跳过
   ├── !isValidForInheritance → 跳过（manual 或 auto+licenseStatus 非空）
   │
   ├── isExactHashMatch (sourceHash + fileHash 全等)
   │      └── true → 直接返回（最高优先级）
   │
   ├── isAddedFile (prDiff.status == "added")  ← Fix 2：跳过 3a 直接进 3b
   │
   ├── isInModifiedRange(currentIssue.lines, prDiff)
   │      └── true → 跳过该历史（修改行命中范围，不继承）
   │
   └── isAllFieldsMatch (license / copyright / hash / lines / openLines)
          ├── adjustedLines = isAddedFile ? currentIssue.lines : adjustLinesToOriginal(prDiff)
          └── true → 落库新 TblIssue + 返回（fallback 路径）
```

## 风险 & 缓解

| 风险                                          | 影响                    | 缓解                                                                                                  |
| --------------------------------------------- | ----------------------- | ----------------------------------------------------------------------------------------------------- |
| DB 迁移失败导致服务启动受阻                   | 部署阶段                | changeset 加 `preConditions onFail="MARK_RAN"`，已存在则跳过；提供 `rollback` 删列                    |
| compare / PR commits API 限流或故障           | 继承降级                | 双缓存减少调用；API 失败回退 PR 全量 diff，保留原有行为                                               |
| 存量历史 `pr_head_sha` 为 NULL                | 增量 diff 不可用        | baseSha 为空时直接走 PR 全量 diff，不阻塞继承                                                         |
| `prCommitsCache` 跨 batch 失效导致重复调用    | 性能下降                | 缓存 key 为 mergeUrl，单次扫描请求内复用                                                              |
| sourceHash 变化但 fileHash 不变时误继承       | 合规盲区                | fallback 路径仍需通过 `isAllFieldsMatch` 全字段校验，不通过则不继承                                   |
| baseSha 跨 PR 历史污染                        | 错误继承                | `getPrCommitShas` 明确校验归属，不在 PR commits 即回退全量 diff                                       |
| force push 后 contents API 调用失败           | 直接 diff 不可用        | `getDirectFileDiff` 返回 empty → 降级到步骤 4 PR 全量 diff                                            |
| contents API 返回大文件内容消耗带宽           | 性能下降                | `directDiffCache` 按 `baseSha\|headSha\|filePath` 缓存，单次请求同文件只调一次                        |
| `computeDirectDiff` 内存敏感                  | OOM（极大文件）         | jgit `RawText` 逐行处理，MyersDiff 仅计算差异编辑列表不保留全文，与三点 diff 同等内存量级             |
| huawei 版权判定过宽（如 `non-huawei` 误匹配） | 错误自动确认            | 用 `contains("huawei")` 而非精确匹配，`non-huawei` 等词会被匹配——需关注运营数据以确定是否需要收紧规则 |
| copyright JSON 解析失败被静默忽略             | 本应确认的 issue 未确认 | 宁可不确认也不误确认，属保守策略；失败无日志，排查困难时可加 warn 日志                                |

## 跨仓影响

无。本次改动全部在 `openlibing-sca` 业务仓内，不涉及跨仓接口或契约变化。
