# 代码重复率详情 - 展示具体重复代码（需求设计文档）

> 跨仓 Full 模式需求设计文档。涉及 `openlibing-cicd-test-new`（采集插件）、`openlibing-coderepo-fork`（后端 + DB）、`openlibing-web`（前端）三个仓。
>
> 配套文档：[proposal.md](./proposal.md)（需求背景与验收标准）、[design.md](./design.md)（技术设计）、[tasks.md](./tasks.md)（实现任务清单）。
>
> 本文按"方案设计 → 实现逻辑设计 → 类设计 → 数据模型设计 → 性能设计 → API 接口设计 → 安全设计"七节组织，作为评审与实施依据。

> **实现偏差说明（实际实现与本文档原始设计不一致点，实施时以实际代码为准）**
>
> 1. **上报接口返回类型**：`reportMetrics` 实际由 `DataResult<Long>` 改为 `DataResult<String>`（recordId 用 String，防雪花 ID 在 JS 侧 Number 精度溢出 2^53）。
> 2. **新增独立分批上报接口** `POST /metrics/code/duplication-blocks`（`DuplicationBlockBatchDTO`：`recordId`(String)+`blocks`），Service 方法 `saveDuplicationBlocksBatch`。插件端 `duplicationOccurrences` 超过单批 5000 时，首批随 `/report` 上报，后续批次走此接口。
> 3. **`file-content` 返回结构**：实际 `FileContentViewVO` 改为返回 `segments`（List\<CodeSegment\>，含 `originalStartLine`/`originalEndLine`/`content` 明文），**不再返回 `content` + `lineMapping`**；省略行数由前端按相邻片段行号差计算。
> 4. **`duplication-block/detail`**：`DuplicationBlockQueryDTO` 实际新增 `branchName`、`pipelineRunId`、`sourceBlockId`（可选）；`DuplicationBlockVO.Occurrence` 实际新增 `contentStartLine`、`contentEndLine`，`blockId` 为 String；`content` 优先取自 `file_detail.snapshot_data` 上下文章段，snapshot 不存在时 fallback 为重复块本身代码。`sourceBlockId` 用于交集定位（见 §6.4）。
> 5. **DB 表**：`code_metrics_duplication_block` 实际**没有 `git_url`/`branch_name` 列**；索引为 `idx_record_group`/`idx_record_file`/唯一键 `uk_record_group_file_start`。`code_metrics_file_detail` 实际**新增 `idx_record_file` 索引**；`code_metrics_record` 实际**新增唯一索引 `uk_git_branch_run`**。
> 6. **`repository` 字段**：实际仅 **DTO/Entity 移除 `repository` 字段**，DB 层 `code_metrics_record.repository` 列**保留不 drop**（便于回滚）。
> 7. **`FileMetricDetailVO.DuplicationRateItem`**：实际新增 `totalLines`、`duplicationBlockCount`、`hasSnapshot` 三个字段（`duplicatedFiles` 属 metricType=4 的 `FileDuplicationItem`）。

## 1. 方案设计

### 1.1 问题域

代码重复率指标当前只能下钻到「文件粒度」（文件路径 + 重复率 + 重复行数），用户无法看到：

- 重复代码在源文件中的具体行号区间
- 与之重复的配对文件路径与行号区间
- 重复代码的具体内容

用户必须 clone 仓库、人工查重，体验割裂。本次需求把"具体重复代码"直接展示在平台上。

**关键复杂性**：一个代码块可能与**包括自己在内的多个文件中的多个代码块**重复。例如 `Foo.java:10-40` 的代码块可能同时与 `Foo.java:80-110`（同文件其他位置）和 `Bar.java:5-35`（其他文件）重复。展示时需要让用户在所有重复位置间切换查看。

### 1.2 候选方案对比

代码缓存策略是本需求最关键的架构决策。围绕"用户代码是否缓存到数据库、缓存多少"，给出 4 个候选方案：

| 方案                                                      | 完整文件来源                                                    | 重复块存储   | 优点                                                                                                          | 缺点                                                                                        |
| --------------------------------------------------------- | --------------------------------------------------------------- | ------------ | ------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- |
| **A. 实时拉取 + 不存代码**                                | Git 平台 API 实时拉取                                           | 只存行号区间 | DB 零增长、代码永远最新                                                                                       | 慢、依赖 Git 平台可用性、API 限流、历史扫描时点代码无法复现、行号会因代码变更而错位         |
| **B. 全量缓存**                                           | 编码入库（全文件）                                              | 编码入库     | 完整可追溯、行号严格对齐                                                                                      | DB 膨胀严重、隐私风险大、上报体量大、同一文件未变更时多次冗余存储                           |
| **C. 只存重复块 + 完整文件实时拉取**                      | Git 平台 API 拉取（带短缓存）                                   | 编码入库     | DB 体积可控、隐私风险低                                                                                       | 完整文件查看仍依赖 Git 平台、历史代码可能错位（用户看 N 天前扫描结果，代码已变更）          |
| **D. 只存重复块 + 上下文片段快照（无 TTL，长期保留）** ✅ | 编码入库（仅重复块±5行上下文，长期保留），其他部分以 `...` 占位 | 编码入库     | 可追溯、行号严格对齐（通过 lineMapping 映射）、DB 体积大幅压缩（大文件省 90%+）、隐私风险低、历史记录完整可查 | 实现复杂度增加（需拼接展示代码 + 行号映射）、DB 有一定膨胀（用上下文 ±5 行 + 片段合并控制） |

### 1.3 推荐方案：D

**理由**：

1. **重复块必须入库**：详情展示的核心数据，必须可追溯。用户看的是历史 `pipelineRunId` 的扫描结果，无法重新计算。
2. **上下文片段快照（非完整文件）**：保证用户看到的代码与扫描时点一致，行号严格对齐。若用方案 C，用户看 7 天前扫描结果时，代码已变更，重复块行号会指向错误位置。但**不必缓存完整文件**——用户关注的是重复块本身及其紧邻上下文，完整文件中远离重复块的代码对定位重复问题价值很低。因此快照仅存"重复块 ±5 行上下文片段"（合并重叠/相邻区间），其他部分前端用 `... N lines omitted ...` 占位。后端解析片段 JSON 拼接展示代码时同步构建 `lineMapping`（展示行号 ↔ 原始行号），前端高亮和跳转用 lineMapping 转换行号，保证行号严格对齐。相比全量缓存：大文件存储节省 90%+，DBA 解码后只能看片段无法还原完整文件，隐私风险更低。
3. **无 TTL，长期保留（优先保证历史记录完整）**：上下文片段仅存重复块 ±5 行（合并后体积已大幅压缩，大文件省 90%+），DB 膨胀可控，无需 TTL 清理。**优先保证用户能看到完整的历史记录**——用户回溯任意一次扫描结果时，上下文片段代码都应可见，不因过期而降级。**快照未命中（旧 record 无 `snapshot_data`）不走 Git API 降级拉取完整文件**——重复块行号是扫描时点的，拉最新代码会行号错位、高亮指错位置，"看似能看实则错位"的误导比"提示无快照"更差；改为直接提示"该记录无代码快照"。但重复块代码片段（`code_metrics_duplication_block` 表，长期保留）仍可查看，drawer 内片段行号从 1 重新编号，不存在错位问题。
4. **编码**：Base64（参考 codecheck 的 [FragmentCryptoUtil.java](file:///d:/Develop/Java/openlibing-codecheck/src/main/java/com/openlibing/codecheck/common/utils/security/FragmentCryptoUtil.java)），防止"明文出现在日志和 DBA 一眼可见"。若后续合规升级，可平滑替换为 AES-256，工具类对上层透明。
5. **hash 算法选用 SHA-256**：重复块内容 hash 用于"同一代码内容的出现位置归为同一组"的分组键（`code_metrics_duplication_block.group_id`）。虽本场景 hash 非安全用途（不做完整性校验/签名），但 MD5 已被标记为不安全算法，review 中易引发争议；SHA-256（hex 编码，64 字符）消除该争议，`content_hash VARCHAR(64)` 字段长度刚好适配，无额外存储成本。

### 1.4 整体架构

```
┌─────────────────────┐   上报(含重复块+文件明细含快照, Base64编码)  ┌──────────────────────────┐
│  code-metrics-action│ ───────────────────────────────────────▶ │ openlibing-coderepo      │
│  (插件, jscpd/token)│   POST /metrics/code/report              │                          │
└─────────────────────┘                                          │  ┌────────────────────┐  │
                                                                 │  │ code_metrics_record│  │  (主表, 已有)
                                                                 │  └─────────┬──────────┘  │
                                                                 │            │ record_id
                                                                 │  ┌─────────▼──────────┐  │
                                                                 │  │ code_metrics_       │  │  ← 新增(长期保留)
                                                                 │  │  duplication_block  │  │  (出现位置, B64)
                                                                 │  └─────────┬──────────┘  │
                                                                 │  ┌─────────▼──────────┐  │
                                                                 │  │ code_metrics_       │  │  ← 已有表, 新增 snapshot_data 字段
                                                                 │  │  file_detail        │  │  (上下文片段, B64)
                                                                 │  └────────────────────┘  │
                                                                 └────────────┬─────────────┘
                                                                              │
┌─────────────────────┐   POST /metrics/code/file-content         ┌──────────▼────────────┐
│  openlibing-web     │ ◀──────────────────────────────────────── │  查询接口             │
│  (monaco-editor +   │   POST /metrics/code/duplication-block/   │  (Base64解码后返回)   │
│   drawer 多页签)    │   detail                                  │                       │
└─────────────────────┘                                          └───────────────────────┘
```

核心流程：

1. **采集**：插件扫描时，对每个"重复块组"（同一代码内容在多个位置出现）记录所有出现位置（file + startLine + endLine + 代码内容），Base64 编码后上报；同时对有重复的文件提取"重复块 ±5 行上下文片段"（合并重叠区间），Base64 编码为 JSON，**随该文件的 `fileDetail` 一起上报**（存入 `fileDetail.snapshotData` 字段）。
2. **存储**：后端把每个出现位置存为一行到 `code_metrics_duplication_block`（长期，按 group_id 关联同一组，group_id = content 的 SHA-256）；上下文片段 JSON 存入 `code_metrics_file_detail.snapshot_data` 字段（长期保留，不存完整文件）。**不再单独建 `code_metrics_file_snapshot` 表**——快照数据直接挂在 file_detail 上，一对一关系更简洁，且无需 `content_hash` 去重（每个 file_detail 只对应自身一份快照）。
3. **展示**：前端点击文件路径 → 调 `file-content` 接口拿到上下文片段拼接的展示代码 + lineMapping 行号映射 + 该文件所有重复块元信息 → monaco-editor 渲染 + 用 lineMapping 转换行号后高亮；点击高亮块 → 调 `duplication-block/detail`（按 groupId）拿到该组所有出现位置 → drawer 以多页签展示，每个 tab 对应一个出现位置。

### 1.5 关键决策汇总

| 决策点            | 选择                                                                                                                                                                                                                                                                   | 理由                                                                                                                                         |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| 缓存策略          | 方案 D（重复块长期 + 文件快照存 file_detail，无 TTL）                                                                                                                                                                                                                  | 上下文片段 ±5 行已大幅压缩体积，无需 TTL；优先保证用户能看到完整的历史记录                                                                   |
| 编码方式          | Base64 + 两阶段回检验证                                                                                                                                                                                                                                                | 与 codecheck 平台一致，防日志明文泄露                                                                                                        |
| hash 算法         | SHA-256（hex 编码，64 字符）                                                                                                                                                                                                                                           | 用于 `code_metrics_duplication_block.group_id` 分组（非安全用途），SHA-256 消除"已知不安全算法"的 review 争议，字段长度 VARCHAR(64) 刚好适配 |
| 快照范围          | 仅缓存"有重复文件"的**上下文片段**（重复块 ±5 行，其他部分 `...` 占位）                                                                                                                                                                                                | 节省存储（大文件节省 90%+）；安全提升（DBA 解码后只能看片段，无法还原完整文件）；前端通过 lineMapping 转换行号实现高亮和跳转                 |
| 快照存储位置      | `code_metrics_file_detail.snapshot_data` 字段（不单独建表）                                                                                                                                                                                                            | 快照与文件明细一对一，直接挂载更简洁；无需 `content_hash` 去重；减少一张表和 JOIN 开销                                                       |
| 重复块存储模型    | "出现位置"表 `code_metrics_duplication_block`，按 group_id 关联                                                                                                                                                                                                        | 干净支撑"一块对多位置"（含同文件多位置），前端多页签直接映射                                                                                 |
| 上报分批          | 单批 ≤ 5000 块 / ≤ 10MB，**实际实现为独立接口 `/metrics/code/duplication-blocks`**（超过单批时首批随 `/report` 上报，后续批次走该接口）                                                                                                                                | 与 APIG 网关限制对齐；独立接口避免重复解析主报告体                                                                                           |
| 降级策略          | 快照未命中（旧 record 无 snapshot_data）即提示"该记录无代码快照"（不做 Git API 降级）                                                                                                                                                                                  | 避免行号错位误导用户；重复块代码片段（长期保留）仍可在 drawer 查看                                                                           |
| 文件代码视图      | **实际实现返回 `segments` 片段列表**（前端用 `originalStartLine` 直接渲染行号，省略行数由前端按相邻片段差计算），**不再返回 content + lineMapping**                                                                                                                    | 结构更简单，行号天然对齐，前端控制省略占位                                                                                                   |
| 重复块详情定位    | `DuplicationBlockQueryDTO` **实际新增 `branchName`、`pipelineRunId`、`sourceBlockId`**；`sourceBlockId` 用于**交集定位**（同组各 occurrence 行数可能不同，以其代码块内容为基准在其他 occurrence 中取交集匹配子区间，返回交集行号 ±5 行上下文，精确高亮"真正重复"部分） | 避免同 group_id 跨多次扫描混淆；解决 union-find 分组导致的行数不一致，精确高亮                                                               |
| drawer 交互       | 多页签 tabs（每个 tab 一个出现位置）                                                                                                                                                                                                                                   | 用户在所有重复位置间切换查看                                                                                                                 |
| `repository` 字段 | **DTO/Entity 移除 `repository` 字段，DB 层 `code_metrics_record.repository` 列保留不 drop（便于回滚）**                                                                                                                                                                | 写死 source-dir 后插件只能扫描工作流所在仓，git_url 即扫描仓，`repository`（owner/repo）字段冗余无用；DB 列保留以降低回滚成本                |
| 上报返回值        | `reportMetrics` **返回 `String` 类型的 recordId**（实际实现）                                                                                                                                                                                                          | 雪花 ID 超过 JS Number 安全整数范围（2^53-1），用 String 避免前端/插件精度溢出                                                               |

## 2. 实现逻辑设计

### 2.1 采集端逻辑（插件）

#### 2.1.1 主路径 token-level 检测改造

现状：[DuplicationDetector.js](file:///d:/Develop/Java/openlibing-cicd-test-new/.gitcode/actions/code-metrics-action/dist/detectors/DuplicationDetector.js) 的 `detectWithTokenLevel` 只产出"文件 → 重复行号集合"，没有显式的"重复块"概念。**原插件只检测跨文件重复**（同一 hash 在 2+ 个不同文件出现才计入，同文件内重复不算），**本次需求同步修复该逻辑，改为同文件中发现重复代码块也算**（`if (locations.length < 2) continue`，2+ 个出现位置即计为重复，含同文件内重复）。

改造后流程：

```
detectWithTokenLevel(files):
  Step 1: 分词 + 滑动窗口哈希（不变）
  Step 2: hashToLocations 记录 (file, startIdx, endIdx)
  Step 3: 重复块匹配 → 对每个 hash 有 2+ 个出现位置即计为重复（含同文件内重复）:
          - 所有出现位置归为同一 group（group_id = contentHash）
          - 每个出现位置生成一条 DuplicationOccurrence
          - 记录 (groupId, contentHash, filePath, startLine, endLine, content, occurrenceIndex)
          注意：同文件内多次出现同一 hash 的位置也归入同一 group，同文件内重复同样计入该文件的"重复块数"
  Step 4: 行号集合合并为连续区间（mergeConsecutiveLines）
          - 过滤区间长度 < minLines(10) 的（与 cmetrics 定义对齐）
  Step 5: 对每个出现位置提取代码内容（extractBlockContent）
  Step 6: 同组出现位置按 (filePath, startLine) 排序，occurrenceIndex 从 0 递增
```

**关键变化**：不再以"source + target 对"存储，而是以"出现位置"为单位存储。同一代码内容的所有出现位置归为同一 group，每个位置一条记录。这干净地支撑了"一块对多位置（含同文件多位置）"的场景。**同文件内重复同样计入**——例如文件内部多个相同 catch 块属于需要消除的重复代码。

**"重复块数"定义**：文件的"重复块数"= 该文件参与的重复组数（`COUNT(DISTINCT group_id) WHERE file_path = ?`）。一个 group 在同一代码内容出现 2+ 次时成立（含同文件内重复），因此"重复块数"包含同文件内重复的组。它衡量的是"该文件有多少段代码在其他位置（同文件或其他文件）重复出现"。

#### 2.1.2 fallback 路径 jscpd 检测改造

jscpd 的 `clone.duplicationA / duplicationB` 已有显式 `start.line / end.line`。改造点：把同一 clone 的两端（或多端）归为同一 group，每个端点生成一条出现位置记录。**保留同文件内 clone**（原逻辑过滤了同文件 clone，本次需求同文件内重复也算）。

#### 2.1.3 上下文片段快照采集

在 `detect` 末尾，对 `fileDetails` 中 `duplicationLineCount > 0` 的文件，调用 `buildContextSegments(fileDetails, sources, contextLines=5)`：提取该文件每个重复块 ±5 行上下文，合并重叠/相邻区间，生成 `snapshotData`（JSON 结构：`{totalLines, contextLines, segments:[{originalStartLine, originalEndLine, contentB64}]}`，每个 segment 的 contentB64 内部再次 Base64 编码）。**不读取/上报完整文件内容**，其他部分代码由前端用 `... N lines omitted ...` 占位。因仅存片段，不再以文件大小作为跳过条件。生成的 `snapshotData` 直接挂到对应 `fileDetail.snapshotData` 字段上，随文件明细一起上报。

#### 2.1.4 上报逻辑

[CoderepoUploader.js](file:///d:/Develop/Java/openlibing-cicd-test-new/.gitcode/actions/code-metrics-action/dist/uploaders/CoderepoUploader.js) 改造：

- 上报前对出现位置代码内容 / 快照内容做 Base64 编码
- 单批 `duplicationOccurrences` ≤ 5000 条，超过递归分批
- **快照数据随 `fileDetails` 一起上报**（每个 fileDetail 携带自身的 `snapshotData`），不再单独上报文件快照，避免混批

### 2.2 后端实现逻辑

#### 2.2.1 上报处理流程

```
reportMetrics(request):
  0. 幂等检查：相同 gitUrl + branchName + pipelineRunId 的旧记录先删除
     - 查询 code_metrics_record 是否存在同 pipelineRunId 记录
     - 存在 → 先删除旧记录的 file_detail（deleteByRecordId），再删除旧 record
     - 防止重复上报导致 file_detail 表产生重复记录；DB 层 uk_git_branch_run 唯一索引兜底防并发重复
  1. 校验请求（APIG 签名 + 必填字段）
  2. 序列化 metricsData → saveCodeMetricsRecord（已有，不变；DTO/Entity 移除 repository 字段，DB 列保留不 drop）
  3. saveFileDetails（已有，改造：fileDetail 含 snapshotData 字段，随 metrics_json 一起存入或单独存 snapshot_data 列）
  4. saveIdenticalFileDetails（已有，不变；identicalFileDetails 每项只含 duplicatedFiles 数组，不含 filePath）
  5. saveDuplicationBlocks(request, recordId)   ← 新增
       - 批量 saveBatch，每批 500
       - 单条失败容错（try-catch，不影响整体）
       - 入库前不二次编码（插件端已编码）
  6. 返回 recordId（String 类型，DataResult<String>）
```

> **注意**：不再有独立的 `saveFileSnapshots` 步骤——快照数据 `snapshotData` 随 `fileDetails` 一起入库（存入 `code_metrics_file_detail.snapshot_data` 字段），由 `saveFileDetails` 统一处理。
>
> **分批上报**：插件端 `duplicationOccurrences` 超过单批 5000 时，首批随 `/report` 上报并拿到 `recordId`（String），后续批次调新增接口 `POST /metrics/code/duplication-blocks`（`DuplicationBlockBatchDTO`：`recordId` + `blocks`）由 `saveDuplicationBlocksBatch` 分批入库，依赖 `uk_record_group_file_start` 唯一索引保证幂等。

#### 2.2.2 文件代码视图查询流程

```
getFileContent(query):
  1. 校验 repoId → 查 repo_info 拿 gitUrl
  2. 查 code_metrics_record 拿 recordId（按 gitUrl + branchName + pipelineRunId）
  3. 查 code_metrics_file_detail (recordId, filePath):
     - snapshot_data 字段非空 → Base64 解码 snapshot_data → 解析 JSON 得到 segments
       → 逐段 Base64 解码 contentB64 → 组装 List<CodeSegment>（每段含 originalStartLine/originalEndLine/content 明文）
       → hasSnapshot=true, segments=<片段列表>, totalOriginalLines=<原始总行数>
       （前端用 originalStartLine 直接渲染行号，省略行数由前端按相邻片段差计算，不再需要 lineMapping）
     - snapshot_data 字段为空（旧 record 无快照数据）→ hasSnapshot=false, segments=null, totalOriginalLines=null
       （不走 Git API 降级，避免行号错位误导用户）
  4. 查 code_metrics_duplication_block (recordId, file_path=filePath):
     - 取该文件所有出现位置（不含代码内容）
     - 按 start_line 排序
     - 同 group_id 的位置聚合，得到该文件的重复块列表
     （无论快照是否命中都返回，前端用于渲染高亮或重复块列表）
  5. 组装 FileContentViewVO 返回
```

#### 2.2.3 重复块详情查询流程（按 group_id）

```
getDuplicationBlockDetail(query):
  1. 校验 groupId + repoId（鉴权：groupId 必须属于 repoId 对应的仓库）
  2. 按 branchName + pipelineRunId 定位具体某次扫描的 recordId（避免同 group_id 跨多次扫描混淆）
  3. 查 code_metrics_duplication_block by (record_id, group_id):
     - 返回该组所有出现位置
     - 按 occurrence_index 排序
  4. 对每个出现位置的 content_b64 做 Base64 解码（两阶段验证）
     - content 优先从该文件 file_detail.snapshot_data 中取包含 [startLine,endLine] 的上下文章段，snapshot 不存在时 fallback 为重复块本身代码
     - 据此计算 contentStartLine / contentEndLine
  5. （可选）若传入 sourceBlockId：以该块内容为基准，在其他 occurrence 的 content 中定位匹配子区间（取交集），返回交集部分行号与 ±5 行上下文
  6. 组装 DuplicationBlockVO 返回:
     - groupId, contentHash
     - occurrences: List<Occurrence>（每个含 blockId(String), filePath, startLine, endLine, content, contentStartLine, contentEndLine, occurrenceIndex）
     - totalCount: occurrences.size()
```

**关键变化**：查询入参从 `blockId` 改为 `groupId`，返回该组所有出现位置（前端渲染为多页签）；并新增 `branchName`/`pipelineRunId` 定位扫描记录、`sourceBlockId` 交集定位（见 §6.4）。

#### 2.2.4 TTL 清理流程（已移除）

本需求**不再使用 TTL 清理**。上下文片段快照存入 `code_metrics_file_detail.snapshot_data` 字段，随 file_detail 记录长期保留，优先保证用户能看到完整的历史记录。上下文片段仅存重复块 ±5 行（合并后体积已大幅压缩），无需 TTL 清理控制 DB 膨胀。如未来需清理历史数据，可按 `code_metrics_record.create_time` 统一清理过期 record 及其关联的 file_detail / duplication_block（不在本期范围内）。

### 2.3 前端实现逻辑

#### 2.3.1 文件列表点击跳转

[MetricsDetailDialog.vue](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/views/Repos/dialog/MetricsDetailDialog.vue) metricType=3 的 `filePath` 列改为可点击 `<a>`，点击 `router.push` 到 `DuplicationCodeView`，query 携带 `repoId / branchName / pipelineRunId / filePath / runNumber / pipelineLink`。

#### 2.3.2 代码视图渲染

```
DuplicationCodeView.vue onMounted:
  1. 解析 query 参数
  2. 调 file-content 接口 → 拿 content + duplicationBlocks + hasSnapshot + lineMapping
  3. 初始状态：源文件以右侧 50% 侧边页形式打开，drawer 关闭
  4a. hasSnapshot=true:
      - monaco-editor.create → model.setValue(content)  // content 是拼接后的展示代码（含 ... 占位行）
      - 遍历 duplicationBlocks，用 lineMapping 把 block.startLine/endLine（原始行号）转换为展示行号
      - deltaDecorations 高亮转换后的 [displayStart-1, displayEnd-1] 行范围（淡黄底）
      - 每个重复块起始行添加可点击指示器 "▶ N 个位置"（N = 该组非当前来源的出现位置数，含同文件其他位置）
  4b. hasSnapshot=false:
      - 隐藏 monaco-editor，左侧展示"该记录无代码快照"占位
      - 渲染 duplicationBlocks 为可点击的重复块列表（basename + 行号区间 + occurrenceCount）

点击高亮块或点击指示器（hasSnapshot=true）或点击重复块列表项（hasSnapshot=false）:
  1. （hasSnapshot=true）onMouseDown → 判断位置是否在某个 block 的展示行范围内
  2. 切换当前 block：高亮改为深橙底
  3. （hasSnapshot=true）用 lineMapping 把 block.startLine 转换为展示行号 → monaco-editor.revealLineInCenter(displayLine)
  4. 页面展开为全屏 + 打开 drawer（与初始 50% 侧边页不同，点击代码块后自动全屏+drawer）
  5. 用 block.groupId 调 duplication-block/detail
     + 记录 currentBlockId（用于确定哪些是"非来源"tab）

放大/缩小与 drawer 联动:
  - 点击"缩小"按钮 → 恢复为右侧 50% 侧边页 + 关闭 drawer
  - 点击"放大"按钮 → 展开为全屏 + 重新打开 drawer（展示当前选中块的重复位置）
```

**行号映射转换工具函数**（前端）：

```typescript
// originalLine → displayLine，用 lineMapping 查找所属 segment
function toDisplayLine(
  originalLine: number,
  lineMapping: LineMapping[],
): number | null {
  for (const seg of lineMapping) {
    if (
      originalLine >= seg.originalStartLine &&
      originalLine <= seg.originalEndLine
    ) {
      return seg.displayStartLine + (originalLine - seg.originalStartLine);
    }
  }
  return null; // 该行不在任何片段内（被省略）
}
```

#### 2.3.3 drawer 多页签交互

```
DuplicationBlockDrawer.vue:
  props: groupId, visible, currentBlockId（当前点击的出现位置 blockId）
  state: detail, activeTabIndex
  lifecycle:
    watch(groupId) → fetchBlockDetail(groupId)
                     → 拿到 occurrences 列表
                     → 过滤掉 currentBlockId 对应的出现位置（来源位置不作为 tab）
                     → activeTabIndex 默认选中第一个（即第一个非来源位置）
  methods:
    fetchBlockDetail(groupId): 调 duplication-block/detail API
    renderOccurrence(occurrence): monaco-editor 只读渲染 occurrence.content（含上下文行）
                                   高亮重复块行范围，上下文行不高亮
    onTabClick(index): 切换 activeTabIndex → 重新渲染对应 occurrence
    onPrev/onNext: emit prev/next（父组件切换源文件相邻重复块）
    onResize: emit resize
```

**多页签设计要点**：

- 一个重复块组有 N 个出现位置 → drawer 只展示 N-1 个 tab（排除来源位置，因为主视图已展示）
- 每个 tab 标签：`basename(filePath) + ':' + startLine + '-' + endLine`（如 `Foo.java:80-95`）
- **同文件其他位置**的 tab 额外显示"同文件"蓝色 badge（如 `Foo:80-95 [同文件]`），便于用户区分同文件内重复和跨文件重复
- 默认选中第一个 tab（第一个非来源位置）
- tab 切换时，drawer 内 monaco-editor 重新渲染对应出现位置的代码片段（含上下文），并高亮重复块部分
- tab 数量过多（> 8）时横向滚动
- drawer 标题显示位置数 = 非来源位置数（如 "重复代码块 (2 个位置)"）

### 2.4 行号对齐策略

- 重复块的 `startLine / endLine` 来自插件扫描时的源文件实际行号（1-based），存入 `code_metrics_duplication_block`
- 文件快照的 `snapshot_data`（存于 `code_metrics_file_detail` 表）是扫描时点的**上下文片段**（非完整文件），只含重复块 ±5 行上下文，其他部分用 `... N lines omitted ...` 占位
- 代码视图（快照命中，即 file_detail.snapshot_data 非空）：
  - 后端解析 snapshot_data JSON → 拼接展示内容（片段 + 占位行）+ 构建 `lineMapping`（`displayStartLine/displayEndLine ↔ originalStartLine/originalEndLine`）
  - 前端 monaco-editor 渲染拼接后的展示内容
  - 高亮时用 `lineMapping` 把 block 的原始 `startLine/endLine` 转换为展示行号，`deltaDecorations` 高亮 `[displayStart-1, displayEnd-1]`
  - `revealLineInCenter` 跳转也用转换后的展示行号
- 代码视图（快照未命中，即旧 record 的 file_detail.snapshot_data 为空）：**不走 Git API 拉取**，左侧显示"该记录无代码快照"占位 + 重复块列表；避免拉最新代码导致行号错位、高亮指错位置误导用户
- drawer 内 tab 展示的是出现位置代码片段（来自 `code_metrics_duplication_block` 表，长期保留，非完整文件），展示时附带上下文行（重复块 ±5 行），使用源文件原始行号，重复块部分高亮，上下文行不高亮；不含来源位置（来源位置已在主视图左侧展示）

### 2.5 前端交互示例图

#### 图 1：文件列表（MetricsDetailDialog metricType=3）

```
┌──────────────────────────────────────────────────────────────────┐
│  总代码重复率详情                                                  │
├──────────────────────────────────────────────────────────────────┤
│  代码仓: openlibing-coderepo   分支: master   流水线: #123         │
├────────────────────────────┬──────────┬──────────┬───────────────┤
│  文件名称                   │ 重复率    │ 重复行数  │ 重复块数       │
├────────────────────────────┼──────────┼──────────┼───────────────┤
│  src/main/Foo.java      🔗 │ 35.5%    │ 120      │ 2             │
│  src/main/Bar.java      🔗 │ 28.2%    │ 85       │ 2             │
│  src/main/Baz.java      🔗 │ 15.0%    │ 40       │ 1             │
└────────────────────────────┴──────────┴──────────┴───────────────┘

  点击文件路径（🔗）→ 源文件以右侧 50% 侧边页形式打开（初始状态，无 drawer）
```

#### 图 2：初始状态 — 右侧 50% 侧边页（快照命中，无 drawer）

```
┌──────────────────────────────┬────────────────────────────────────────┐
│  总代码重复率详情（文件列表）    │  源文件 src/main/Foo.java                │
│  ...                         │  ↑ 上一个  ↓ 下一个  ⤢ 放大               │
│                              │ ───────────────────────────────────────── │
│                              │   3    ...                               │
│                              │  ┌────────────────────────────────────┐  │
│                              │  │10  public void methodA() {         │  │
│                              │  │11    System.out.println("hello");  │  │
│                              │  │12  }                               │  │
│                              │  └────────────────────────────────────┘  │
│                              │   13    ...                              │
│                              │  ┌────────────────────────────────────┐  │
│                              │  │58  public ScanResult scan() {  ▶2  │  │ ← 指示器
│                              │  │59      ...                         │  │
│                              │  │70  }                               │  │
│                              │  └────────────────────────────────────┘  │
│                              │   71    ...                              │
│                              │  ┌────────────────────────────────────┐  │
│                              │  │80  public ScanResult scan() {      │  │ ← 同文件重复
│                              │  │81      ...                         │  │
│                              │  │95  }                               │  │
│                              │  └────────────────────────────────────┘  │
│                              │   96    ...                              │
│                              │  ┌────────────────────────────────────┐  │
│                              │  │105 public Report generateReport()▶1│  │ ← 指示器
│                              │  │106     ...                         │  │
│                              │  │116 }                               │  │
│                              │  └────────────────────────────────────┘  │
│                              │  117    ...                              │
└──────────────────────────────┴────────────────────────────────────────┘

  - 初始状态：右侧 50% 侧边页，无 drawer
  - 淡黄底: 重复块高亮
  - ▶N: 可点击指示器，N = 该组非来源出现位置数（含同文件其他位置）
  - 点击高亮块或指示器 → 展开全屏 + 打开 drawer
```

#### 图 3：点击代码块后 — 全屏 + drawer（多页签，不含来源 tab）

```
┌────────────────────────────────────────────────┬─────────────────────────────────────────┐
│  源文件 src/main/Foo.java                      │  重复代码块 (2 个位置)                    │
│  ↑ 上一个  ↓ 下一个  ⤈ 缩小                     │ ┌──────────────┬──────────────┐         │
├────────────────────────────────────────────────│ │Foo:80-95     │Bar:5-22      │         │
│   3    ...                                     │ │ [同文件]     │ 当前*        │         │
│  ┌─────────────────────────────────────────┐   │ └──────────────┴──────────────┘         │
│  │10  public void methodA() {              │   │ ─────────────────────────────────────── │
│  │11    System.out.println("hello");       │   │ 当前 tab 代码片段 (Bar.java 第 5-22 行): │
│  │12  }                                    │   │  5  import java.util.List;              │
│  └─────────────────────────────────────────┘   │  6  /**                                 │
│   13    ...                                    │ ┌────────────────────────────────────┐   │
│  ┌─────────────────────────────────────────┐   │ │ 11  public ScanResult scan() {    │   │ ← 高亮
│  │58  public ScanResult scan() { ▶2        │   │ │ 12      List<String> paths = ...  │   │
│  │59    ...                                │   │ │ 22  }                             │   │
│  │70  }                                    │   │ └────────────────────────────────────┘   │
│  └─────────────────────────────────────────┘   │  23                                     │
│   71    ...                                    │ ─────────────────────────────────────── │
│  ┌─────────────────────────────────────────┐   │  ← 上一个  1/2  下一个 →                │
│  │80  public ScanResult scan() { ◀── 当前选中│   │                                         │
│  │81    System.out.println("hello");       │   │                                         │
│  │95  }                                    │   │                                         │
│  └─────────────────────────────────────────┘   │                                         │
│   96    ...                                    │                                         │
│  ┌─────────────────────────────────────────┐   │                                         │
│  │105 public Report generateReport() ▶1    │   │                                         │
│  │116 }                                    │   │                                         │
│  └─────────────────────────────────────────┘   │                                         │
└────────────────────────────────────────────────┴─────────────────────────────────────────┘

  点击代码块后的状态变化:
  - 面板自动从 50% 展开为全屏
  - 右侧 drawer 自动打开
  - 当前选中块高亮改为深橙底

  drawer tab 设计:
  - 不展示来源 tab（源文件已展示在左侧，无需重复）
  - 同文件其他位置 tab 标注 [同文件] 蓝色 badge
  - 当前选中 tab 标注 "当前*" 橙色 badge
  - drawer 内代码片段含上下文行，重复块部分高亮

  缩小按钮:
  - 恢复为右侧 50% 侧边页 + 关闭 drawer
  放大按钮:
  - 展开为全屏 + 重新打开 drawer
```

## 3. 类设计

### 3.1 后端类设计（openlibing-coderepo-fork）

#### 3.1.1 新增 Entity

```java
/** 代码重复块出现位置实体（每个出现位置一行，同 group_id 关联） */
@Data @Builder @AllArgsConstructor @NoArgsConstructor
@TableName("code_metrics_duplication_block")
public class CodeMetricsDuplicationBlockEntity implements Serializable {
  @TableId(value = "id", type = IdType.INPUT) private Long id;
  @TableField("record_id") private Long recordId;
  @TableField("git_url") private String gitUrl;
  @TableField("branch_name") private String branchName;
  @TableField("group_id") private String groupId;          // 重复块组ID（同 content_hash 的所有出现位置归为同一组）
  @TableField("content_hash") private String contentHash;  // 重复内容 hash（SHA-256 hex, 64字符），用于块分组
  @TableField("occurrence_index") private Integer occurrenceIndex;  // 组内出现位置序号(0-based)
  @TableField("file_path") private String filePath;        // 出现位置文件路径
  @TableField("start_line") private Integer startLine;     // 出现位置起始行(1-based)
  @TableField("end_line") private Integer endLine;         // 出现位置结束行(1-based, 包含)
  @TableField("content_b64") private String contentB64;    // 出现位置代码内容(Base64编码)
  @TableField("created_at") private Date createdAt;
}
```

> **不再新增 `CodeMetricsFileSnapshotEntity`**：上下文片段快照数据直接存入 `code_metrics_file_detail` 表的新增字段 `snapshot_data`，与文件明细一对一，无需独立 Entity 和独立表。

#### 3.1.1b 现有 Entity 扩展：CodeMetricsFileDetailEntity

[CodeMetricsFileDetailEntity](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/metrics/CodeMetricsFileDetailEntity.java) 新增字段：

```java
/** 上下文片段快照JSON(Base64编码), 仅重复文件有值; 结构:{totalLines,contextLines,segments:[{originalStartLine,originalEndLine,contentB64}]} */
@TableField("snapshot_data")
private String snapshotData;
```

#### 3.1.2 新增 Mapper

```java
public interface CodeMetricsDuplicationBlockMapper extends BaseMapper<CodeMetricsDuplicationBlockEntity> {
  int saveBatch(@Param("list") List<CodeMetricsDuplicationBlockEntity> list);
  /** 查询某文件在某 record 内的所有出现位置（不含代码内容，列表展示用） */
  List<CodeMetricsDuplicationBlockEntity> selectByRecordAndFile(@Param("recordId") Long recordId, @Param("filePath") String filePath);
  /** 查询某 group 的所有出现位置（含代码内容，drawer 多页签用） */
  List<CodeMetricsDuplicationBlockEntity> selectByGroupId(@Param("recordId") Long recordId, @Param("groupId") String groupId);
  /** 查询某文件在某 record 内的重复块数量（按 group 去重） */
  int countGroupsByRecordAndFile(@Param("recordId") Long recordId, @Param("filePath") String filePath);
  int deleteByRecordId(@Param("recordId") Long recordId);
}
```

> **不再新增 `CodeMetricsFileSnapshotMapper`**：快照数据存入 `code_metrics_file_detail`，由现有 [CodeMetricsFileDetailMapper](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/mapper/CodeMetricsFileDetailMapper.java) 处理。`selectByRecordAndFile` 查询时顺带返回 `snapshot_data` 字段即可。

#### 3.1.3 新增工具类

```java
/** 代码内容 Base64 编解码工具类（对齐 codecheck FragmentCryptoUtil 设计） */
public final class CodeContentB64Util {
  private static final String ENCODE_ERROR_PLACEHOLDER = "source code encode error";

  private CodeContentB64Util() {}

  /** 编码：明文 → Base64。已编码数据跳过（防二次编码）。 */
  public static String encode(String plain);

  /** 解码：两阶段验证（Base64.isBase64 + 回检），失败保留原值（兼容历史明文）。 */
  public static String decode(String encoded);

  private static boolean isAlreadyEncoded(String s);
}
```

#### 3.1.4 新增 DTO

```java
/** 文件代码视图查询请求 */
@Data @Builder @AllArgsConstructor @NoArgsConstructor
public class FileContentViewQueryDTO {
  @NotNull(message = "仓库ID不能为空") private Integer repoId;
  @NotBlank(message = "分支名称不能为空") private String branchName;
  @NotBlank(message = "流水线执行记录ID不能为空") private String pipelineRunId;
  @NotBlank(message = "文件路径不能为空") private String filePath;
}

/** 重复块详情查询请求（按 group_id 查所有出现位置） */
@Data @Builder @AllArgsConstructor @NoArgsConstructor
public class DuplicationBlockQueryDTO {
  @NotBlank(message = "重复块组ID不能为空") private String groupId;
  @NotNull(message = "仓库ID不能为空") private Integer repoId;  // 用于鉴权
}
```

#### 3.1.5 新增 VO

```java
/** 文件代码视图响应 */
@Data @Builder @AllArgsConstructor @NoArgsConstructor
public class FileContentViewVO {
  private String gitUrl;
  private String branchName;
  private String pipelineRunId;
  private String filePath;
  private String language;
  private String content;              // 拼接后的展示代码（含 "... N lines omitted ..." 占位行）; hasSnapshot=false 时为 null
  private Integer totalOriginalLines;  // 文件原始总行数; hasSnapshot=false 时为 null
  private Boolean hasSnapshot;         // true=file_detail.snapshot_data 非空（可展示上下文片段代码）; false=旧 record 无快照数据（左侧显示"该记录无代码快照"占位）
  private List<LineMapping> lineMapping;  // 行号映射表（展示行号 ↔ 原始行号）; hasSnapshot=false 时为 null
  private List<DuplicationBlockRef> duplicationBlocks;  // 该文件所有重复块; 无论快照是否命中都返回（来自 duplication_block 表，长期保留）

  @Data @Builder @AllArgsConstructor @NoArgsConstructor
  public static class DuplicationBlockRef {
    private Long blockId;              // 该文件此出现位置的 blockId（用于标记"来源"）
    private String groupId;            // 重复块组ID（drawer 查询用）
    private Integer startLine;         // 原始起始行号（1-based）
    private Integer endLine;           // 原始结束行号（1-based, 包含）
    private Integer occurrenceCount;   // 该组出现位置总数（前端判断是否显示多页签）
  }

  /** 行号映射：展示行号（拼接后内容中的行号） ↔ 原始行号（扫描时点文件中的行号） */
  @Data @Builder @AllArgsConstructor @NoArgsConstructor
  public static class LineMapping {
    private Integer displayStartLine;  // 展示起始行号（1-based）
    private Integer displayEndLine;    // 展示结束行号（1-based, 包含）
    private Integer originalStartLine; // 原始起始行号（1-based）
    private Integer originalEndLine;   // 原始结束行号（1-based, 包含）
  }
}

/** 重复块详情响应（含所有出现位置，前端渲染为多页签） */
@Data @Builder @AllArgsConstructor @NoArgsConstructor
public class DuplicationBlockVO {
  private String groupId;
  private String contentHash;
  private Integer totalCount;          // 出现位置总数
  private List<Occurrence> occurrences;

  @Data @Builder @AllArgsConstructor @NoArgsConstructor
  public static class Occurrence {
    private Long blockId;
    private Integer occurrenceIndex;
    private String filePath;
    private Integer startLine;
    private Integer endLine;
    private String content;            // 该出现位置代码内容（Base64解码后明文）
  }
}
```

#### 3.1.6 现有类扩展

| 类                                                                                                                                                                             | 改动                                                                                                                                                                                                                                                                                                                                                                                            |
| ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| [CodeMetricsReportDTO](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/dto/metrics/CodeMetricsReportDTO.java)                  | 新增 `DuplicationOccurrenceDTO` 内部类 + `duplicationOccurrences` 字段；**移除 `repository` 字段**（写死 source-dir 后冗余）；`FileDetailDTO` 新增 `snapshotData` 字段（随文件明细上报上下文片段）；`IdenticalFileDetailDTO` **移除 `filePath` 字段**（每组只保留 `duplicatedFiles` 数组，含组内所有文件）；**移除 `FileSnapshotDTO` 内部类和 `fileSnapshots` 字段**（快照随 fileDetails 上报） |
| [CodeMetricsFileDetailEntity](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/metrics/CodeMetricsFileDetailEntity.java) | 新增 `snapshotData` 字段（`@TableField("snapshot_data")`），存储上下文片段 JSON                                                                                                                                                                                                                                                                                                                 |
| [CodeMetricsRecordEntity](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/metrics/CodeMetricsRecordEntity.java)         | **移除 `repository` 字段**                                                                                                                                                                                                                                                                                                                                                                      |
| [CodeMetricsRecordMapper.xml](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/resources/mapper/CodeMetricsRecordMapper.xml)                                          | resultMap 和 SELECT 语句移除 `repository` 列                                                                                                                                                                                                                                                                                                                                                    |
| [FileMetricDetailVO.DuplicationRateItem](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/vo/FileMetricDetailVO.java#L107-L121) | 新增 `duplicationBlockCount`、`hasSnapshot` 字段                                                                                                                                                                                                                                                                                                                                                |
| [CodeMetricsService](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/CodeMetricsService.java)                          | 新增 `getFileContent(query)`、`getDuplicationBlockDetail(query)` 方法                                                                                                                                                                                                                                                                                                                           |
| [CodeMetricsServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/CodeMetricsServiceImpl.java)             | 实现新方法 + `saveDuplicationBlocks`；**不再实现 `saveFileSnapshots`**（快照随 `saveFileDetails` 入库）；`appendMetricItems` TOTAL_CODE_DUPLICATION_RATE 分支补充查询；`saveIdenticalFileDetails` 适配新结构（无 filePath）                                                                                                                                                                     |
| [CodeMetricsController](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/CodeMetricsController.java)                 | 新增 `POST /metrics/code/file-content`、`POST /metrics/code/duplication-block/detail`                                                                                                                                                                                                                                                                                                           |

> **不再修改 [XxlJobHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java)**：本需求移除 TTL 清理逻辑，不新增定时任务。

### 3.2 前端类设计（openlibing-web）

#### 3.2.1 新增页面组件

```typescript
// DuplicationCodeView.vue
props: { repoId, branchName, pipelineRunId, filePath, runNumber, pipelineLink }
state: { content, duplicationBlocks, hasSnapshot, lineMapping, totalOriginalLines, currentBlockIndex, drawerVisible, drawerWidth, currentBlockId }
lifecycle:
  onMounted → fetchFileContent():
    - hasSnapshot=true → renderMonaco() + highlightAllBlocks()
    - hasSnapshot=false → renderExpiredPlaceholder() + renderBlockList()
methods:
  fetchFileContent(): 调 fileContent API
  renderMonaco(): monaco-editor.create + model.setValue（hasSnapshot=true 时）
  highlightAllBlocks(): 遍历 duplicationBlocks，用 lineMapping 转换原始行号→展示行号，deltaDecorations 淡黄底
  renderExpiredPlaceholder(): 展示"数据已过期，请重新扫描"占位（hasSnapshot=false 时）
  renderBlockList(): 渲染 duplicationBlocks 为可点击列表（hasSnapshot=false 时）
  toDisplayLine(originalLine): 用 lineMapping 查找所属 segment，返回展示行号
  onBlockClick(blockIndex): 切换深橙底高亮 +（hasSnapshot=true）toDisplayLine + revealLineInCenter + 打开 drawer
                           + 记录 currentBlockId（用于 drawer 标记"来源"）
  onDrawerPrev/onDrawerNext: 切换 currentBlockIndex + 重新调 detail
  onDrawerResize(width): 切换 drawerWidth
```

#### 3.2.2 新增 drawer 组件（多页签）

```typescript
// DuplicationBlockDrawer.vue
props: { groupId, visible, width, currentBlockId }
emits: { close, prev, next, resize }
state: { detail, activeTabIndex }
lifecycle:
  watch(groupId) → fetchBlockDetail(groupId)
                   → 拿到 occurrences 列表
                   → activeTabIndex 默认选中"非 currentBlockId 的第一个"
methods:
  fetchBlockDetail(groupId): 调 duplicationBlockDetail API
  renderOccurrence(occurrence): monaco-editor 只读渲染 occurrence.content
                                高亮 [0, endLine-startLine] 行范围
  onTabClick(index): 切换 activeTabIndex → renderOccurrence(occurrences[index])
  onPrev/onNext: emit prev/next
  onResize: emit resize
```

**多页签渲染要点**：

- tab 列表来自 `detail.occurrences`
- tab 标签：`basename(filePath) + ':' + startLine + '-' + endLine`
- 当前点击位置（`currentBlockId` 匹配的 occurrence）标记"来源"图标
- 当前展示位置（`activeTabIndex`）标记"当前"样式
- tab 数量 > 8 时横向滚动（CSS `overflow-x: auto`）

#### 3.2.3 API 层扩展

```typescript
// url.ts 新增
export const FILE_CONTENT = CODE_REPO + "/metrics/code/file-content";
export const DUPLICATION_BLOCK_DETAIL =
  CODE_REPO + "/metrics/code/duplication-block/detail";

// api.ts 新增
export const fileContent: RequestFunc = (a, s) =>
  apiClient.post(urls.FILE_CONTENT, a, s);
export const duplicationBlockDetail: RequestFunc = (a, s) =>
  apiClient.post(urls.DUPLICATION_BLOCK_DETAIL, a, s);
```

### 3.3 插件端类设计（openlibing-cicd-test-new）

[DuplicationDetector.js](file:///d:/Develop/Java/openlibing-cicd-test-new/.gitcode/actions/code-metrics-action/dist/detectors/DuplicationDetector.js) 新增方法：

```javascript
class DuplicationDetector extends BaseDetector {
  // 新增方法
  mergeConsecutiveLines(lineSet)           // 连续行号合并为区间
  extractBlockContent(filePath, startLine, endLine, sources)  // 提取代码片段
  buildDuplicationOccurrences(hashToLocations, fileTokens, sources) // 按组构建出现位置列表
  buildContextSegments(fileDetails, sources, contextLines=5) // 构建上下文片段快照（重复块±5行，合并重叠区间），挂到 fileDetail.snapshotData
}

class CoderepoUploader {
  // 新增方法
  encodeB64(str)                  // Base64 编码
  async uploadInBatches(metricsData, options)  // 分批上报
}
```

## 4. 数据模型设计

### 4.1 新增表 `code_metrics_duplication_block`（长期保留）

```sql
CREATE TABLE code_metrics_duplication_block (
    id BIGINT UNSIGNED PRIMARY KEY COMMENT '主键ID，雪花算法生成',
    record_id BIGINT UNSIGNED NOT NULL COMMENT '关联 code_metrics_record.id',
    group_id VARCHAR(64) NOT NULL COMMENT '重复块组ID(同content_hash的所有出现位置归为同一组)',
    content_hash VARCHAR(64) NOT NULL COMMENT '重复内容hash(SHA-256 hex, 64字符), 用于块分组',
    occurrence_index INT NOT NULL DEFAULT 0 COMMENT '组内出现位置序号(0-based, 按 filePath+startLine 排序)',
    file_path VARCHAR(512) NOT NULL COMMENT '出现位置文件相对路径',
    start_line INT NOT NULL COMMENT '出现位置起始行(1-based)',
    end_line INT NOT NULL COMMENT '出现位置结束行(1-based, 包含)',
    content_b64 MEDIUMTEXT NOT NULL COMMENT '出现位置代码内容(Base64编码)',
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    INDEX idx_record_group (record_id, group_id),
    INDEX idx_record_file (record_id, file_path(255)),
    UNIQUE KEY uk_record_group_file_start (record_id, group_id, file_path(255), start_line)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='代码重复块出现位置表';
```

> **实现说明**：实际实现**去掉了 `git_url` / `branch_name` 列**（通过 `record_id` 关联主表即可定位仓库/分支，避免冗余）；索引为 `idx_record_group`、`idx_record_file` + 唯一键 `uk_record_group_file_start`（**不再有 `idx_record_id` / `idx_content_hash`**）。

**字段设计说明**：

| 字段               | 设计考量                                                                                                                                                                                                                         |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `id`               | 雪花算法生成，避免自增主键在分批插入时的锁竞争                                                                                                                                                                                   |
| `record_id`        | 关联主表，用于按扫描批次查询/删除                                                                                                                                                                                                |
| `group_id`         | 重复块组ID，同一代码内容的所有出现位置归为同一组。一个组对应一个"重复块"，组内有 N 个出现位置                                                                                                                                    |
| `content_hash`     | SHA-256（hex 编码，64 字符），与 group_id 一一对应（本期 group_id 即取 content_hash）。选 SHA-256 而非 MD5：虽本场景 hash 仅用于分组（非安全用途），但 SHA-256 消除"已知不安全算法"的 review 争议，字段长度 VARCHAR(64) 刚好适配 |
| `occurrence_index` | 组内出现位置序号，按 (filePath, startLine) 排序后从 0 递增。前端 drawer 多页签按此排序                                                                                                                                           |
| `file_path`        | 出现位置文件路径。同一文件可能有多个出现位置（同文件内重复）                                                                                                                                                                     |
| `content_b64`      | MEDIUMTEXT（最大 16MB），单块代码通常 < 1KB，足够                                                                                                                                                                                |

**索引设计说明**：

- `idx_record_group`：drawer 查询主路径，按 group_id 查所有出现位置；同时覆盖 `deleteByRecordId`（record_id 最左前缀）
- `idx_record_file`：文件代码视图查询，按 record + file 查该文件所有出现位置
- `uk_record_group_file_start`：**唯一索引，保证幂等**，防止插件端网络重试导致同一出现位置（同 record 内同组同文件同起点）重复入库

**关键设计变化**：从"source + target 对存储"改为"出现位置"表。优势：

1. 干净支撑"一块对多位置"（含同文件多位置），无需 pair_index 概念
2. 一个 N 位置重复块存 N 行（而非 N×(N-1)/2 对），存储更省
3. 前端多页签直接映射 occurrence_index，无需二次组装

### 4.2 现有表 `code_metrics_file_detail` 新增 `snapshot_data` 字段（长期保留，无 TTL）

**不再单独建 `code_metrics_file_snapshot` 表**。上下文片段快照数据直接存入 `code_metrics_file_detail` 表的新增字段 `snapshot_data`，与文件明细一对一。

```sql
ALTER TABLE code_metrics_file_detail
ADD COLUMN snapshot_data LONGTEXT NULL COMMENT '上下文片段JSON(Base64编码), 仅重复文件有值; 结构:{totalLines,contextLines,segments:[{originalStartLine,originalEndLine,contentB64}]}, 无TTL长期保留';
```

**`snapshot_data` JSON 结构**（Base64 编码后存储）：

```jsonc
{
  "totalLines": 200, // 文件原始总行数
  "contextLines": 5, // 上下文行数（重复块上下各取 5 行）
  "segments": [
    // 合并后的上下文片段列表（按 originalStartLine 排序）
    {
      "originalStartLine": 1, // 该片段对应的原始文件起始行号(1-based)
      "originalEndLine": 45, // 该片段对应的原始文件结束行号(1-based, 包含)
      "contentB64": "Base64...", // 该区间代码内容(Base64编码)
    },
    {
      "originalStartLine": 65,
      "originalEndLine": 115,
      "contentB64": "Base64...",
    },
  ],
}
```

**字段设计说明**：

| 字段            | 设计考量                                                                                                                                                                                                                                                           |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `snapshot_data` | LONGTEXT（最大 4GB）， nullable。存 Base64 编码的 JSON，JSON 内每个 segment 的 `contentB64` 也是 Base64（防 DBA 解码外层后代码明文可见）。**不存完整文件**，只存重复块上下文 ±5 行的片段，其他部分前端用 `... N lines omitted ...` 占位。无重复的文件该字段为 NULL |

> **不再有 `content_hash` / `line_count` / `context_lines` / `segment_count` / `file_size_bytes` / `created_at` 等独立字段**：这些原属 `code_metrics_file_snapshot` 表的字段不再需要。`content_hash` 去重逻辑取消（每个 file_detail 只对应自身一份快照，无需去重）；`totalLines` / `contextLines` 已内含在 `snapshot_data` JSON 中；监控字段非必要。

**片段合并算法**（插件端执行）：

1. 收集文件所有重复块的 `[startLine, endLine]`
2. 计算上下文区间 `[max(1, startLine - contextLines), min(totalLines, endLine + contextLines)]`（contextLines=5）
3. 按 `contextStartLine` 排序
4. 合并重叠/相邻区间：若下一区间 `startLine` ≤ 上一区间 `endLine + 1`，合并为一个片段
5. 每个合并后的片段提取一次代码内容，Base64 编码

**收益**：

- **存储节省**：2000 行文件只有 3 个块（各 30 行）时，存 `3 × (30+10) = 120` 行而非 2000 行，节省 94%
- **安全提升**：DBA 解码后只能看到重复块附近的片段，无法还原完整文件
- **架构简化**：少一张表、少一个 Entity/Mapper、少一个 JOIN，快照与文件明细同生命周期

### 4.3 现有表其他变更

- `code_metrics_record`：**DTO/Entity 移除 `repository` 字段**（写死 source-dir 后，工作流所在仓 git_url 即扫描仓，`repository` owner/repo 字段冗余无用）；**DB 层 `repository` 列保留不 drop**（便于回滚）。同时**新增唯一索引 `uk_git_branch_run (git_url, branch_name, pipeline_run_id)`** 保证幂等，防止并发上报重复 record
- `code_metrics_file_detail`：新增 `snapshot_data` 字段（见 §4.2）+ **新增 `idx_record_file (record_id, file_path(255))` 索引**（覆盖文件代码视图查询，避免 N+1 回表过滤）。`metrics_json` 字段继续承载现有指标，结构不变。重复块独立成 `code_metrics_duplication_block` 表的原因：一对多关系不适合塞进 JSON

### 4.4 数据量预估

假设一个 10 万行代码仓（5000 文件，平均 200 行/文件）：

| 维度                                                   | 估算                                                                                                              |
| ------------------------------------------------------ | ----------------------------------------------------------------------------------------------------------------- |
| 出现位置                                               | 5% 文件有重复 × 每文件 2 块 × 平均 2.5 个位置/块 × 30 行 ≈ 3.75 万行 ≈ 1.5 MB 原文 / 2 MB Base64                  |
| 文件快照（上下文片段，存于 file_detail.snapshot_data） | 250 文件 × 平均 1.5 个合并片段 × (30 行块 + 10 行上下文) ≈ 1.5 万行 ≈ 0.6 MB 原文 / 0.8 MB Base64（含 JSON 开销） |
| 单仓单次扫描                                           | ≈ 2.8 MB 入库                                                                                                     |
| 100 仓 × 每周扫描 × 长期保留（无 TTL）                 | ≈ 14.5 GB / 年（可接受；如需清理可按 record.create_time 统一清理过期 record）                                     |

比存完整文件（~700 MB / 单次）节省约 99.6%；大文件场景节省更显著（2000 行文件只存 ~120 行，节省 94%）。无 TTL 意味着数据长期累积，但单次扫描仅 ~2.8 MB，年增量可控。

### 4.5 ER 关系

```
code_metrics_record (1) ──── (N) code_metrics_file_detail      (已有, 新增 snapshot_data 字段)
                       ──── (N) code_metrics_duplication_block  (新增, 出现位置表)

code_metrics_duplication_block.record_id  → code_metrics_record.id
code_metrics_file_detail.record_id        → code_metrics_record.id
code_metrics_file_detail.snapshot_data    → 上下文片段 JSON（一对一, 仅重复文件有值）

同一 group_id 的 N 行 code_metrics_duplication_block 构成一个"重复块组"
```

## 5. 性能设计

### 5.1 数据库性能

#### 5.1.1 索引策略

| 表                               | 索引                                                                                              | 服务场景                                                                                 |
| -------------------------------- | ------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `code_metrics_duplication_block` | `idx_record_group (record_id, group_id)`                                                          | drawer 查询：按 group_id 查所有出现位置；同时覆盖 deleteByRecordId（record_id 最左前缀） |
|                                  | `idx_record_file (record_id, file_path(255))`                                                     | 文件代码视图：按 record + file 查该文件所有出现位置                                      |
|                                  | `uk_record_group_file_start (record_id, group_id, file_path(255), start_line)`                    | 唯一索引，保证幂等，防插件网络重试重复入库                                               |
| `code_metrics_file_detail`       | `idx_record_file (record_id, file_path(255))`（实际实现**新增**）                                 | 文件代码视图：按 record + file 查 file_detail（含 snapshot_data），避免 N+1 回表过滤     |
| `code_metrics_record`            | `uk_git_branch_run (git_url(255), branch_name, pipeline_run_id(255))`（实际实现**新增唯一索引**） | 保证幂等，防并发上报重复 record；创建前先清理历史重复记录                                |

> **不再有 `code_metrics_file_snapshot` 表及其索引**：快照数据存入 file_detail.snapshot_data，复用 file_detail 的 `idx_record_file` 索引即可。
>
> **实现说明**：实际实现 `code_metrics_duplication_block` 表**不再有 `idx_record_id` / `idx_content_hash`**（`idx_record_group` 已覆盖 deleteByRecordId；group_id 即 content_hash，无需单独索引）。

#### 5.1.2 批量插入

- `code_metrics_duplication_block`：单次 record 可能 500-5000 条出现位置，用 MyBatis Plus `saveBatch(entities, 500)`，每批 500 条
- `code_metrics_file_detail`：单次 record 通常 100-500 条（含 snapshot_data），普通 `saveBatch` 即可；snapshot_data 字段随 metrics_json 一起写入
- 入库失败单条不影响整体（沿用现有 `saveFileDetails` 的 try-catch 容错模式）

#### 5.1.3 查询优化

- `file-detail` 接口的 `duplicationBlockCount` 查询：用 `COUNT(DISTINCT group_id)` 子查询，避免 N+1
- `file-content` 接口：单次查询 `code_metrics_file_detail`（按 record + file，取 snapshot_data）+ 单次查询 `code_metrics_duplication_block`（按 record + file），2 次 SQL
- `duplication-block/detail` 接口：单次查询 `code_metrics_duplication_block`（按 record + group_id），1 次 SQL

### 5.2 缓存设计

#### 5.2.1 无 Git API 拉取缓存（设计决策）

- **快照未命中即提示"该记录无代码快照"，不做 Git API 降级**：上下文片段代码只查 `code_metrics_file_detail.snapshot_data` 字段；为空（旧 record 无快照数据）直接返回 `hasSnapshot=false`，前端展示"该记录无代码快照"占位
- **不引入 Caffeine 缓存**：快照查询走 `(record_id, file_path)` 索引，响应已足够快（< 500ms）；Git API 降级路径已去除，无需 5 分钟缓存
- **设计理由**：重复块行号是扫描时点的，走 Git API 拉最新代码会行号错位、高亮指错位置，"看似能看实则错位"的误导比"提示无快照"更差

#### 5.2.2 不缓存的部分

- `file-content` 接口：单表查询，响应快，无需缓存
- `duplication-block/detail` 接口：单次查询，数据量小，无需缓存
- `file-detail` 接口：已有分页逻辑，重复查询概率低

### 5.3 上报体量控制

| 维度                        | 限制                        | 超限处理                                                              |
| --------------------------- | --------------------------- | --------------------------------------------------------------------- |
| 单次 HTTP 请求体            | ≤ 10MB（与 APIG 网关对齐）  | 分批上报                                                              |
| 单批 duplicationOccurrences | ≤ 5000 条                   | 递归分批                                                              |
| 单文件 snapshotData         | ≤ 1MB（编码前）             | 跳过该文件快照 + warn 日志，前端 hasSnapshot=false 降级展示重复块列表 |
| 单块代码                    | 无硬限制（MEDIUMTEXT 16MB） | 实际 < 1KB，无需限制                                                  |

### 5.4 前端性能

| 维度                    | 策略                                               |
| ----------------------- | -------------------------------------------------- |
| monaco-editor 加载      | 懒加载（已有）                                     |
| 大文件渲染              | > 5000 行提示"文件过大，建议本地查看"              |
| 高亮更新                | `deltaDecorations` 增量更新，避免全量重渲染        |
| drawer 内 monaco-editor | 只渲染出现位置代码片段（不加载完整文件），性能可控 |
| tab 数量过多            | > 8 个 tab 横向滚动，避免布局挤压                  |
| 路由切换                | keep-alive 缓存列表页，避免重复请求                |

### 5.5 性能验收指标

| 指标                               | 目标                                 |
| ---------------------------------- | ------------------------------------ |
| 单文件代码视图接口响应（快照命中） | < 500ms                              |
| 单重复块详情接口响应               | < 200ms                              |
| 插件单次上报体量                   | < 10MB（超过分批）                   |
| 前端代码视图首屏渲染               | < 1s（含 monaco-editor 加载）        |
| drawer 多页签切换响应              | < 100ms（本地 monaco-editor 重渲染） |

## 6. API 接口设计

### 6.1 上报接口扩展：`POST /metrics/code/report`

**位置**：[CodeMetricsController.reportMetrics](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/CodeMetricsController.java#L39-L48)

**请求体**在现有 [CodeMetricsReportDTO](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/dto/metrics/CodeMetricsReportDTO.java) 基础上变更：

**返回类型**：`DataResult<String>`（recordId 用 String 返回，避免雪花 ID 在 JS 侧 Number 精度溢出 2^53）。

**移除字段**：

- `repository`：写死 source-dir 后冗余，**DTO/Entity 移除**（DB 层 `code_metrics_record.repository` 列**保留不 drop**，便于回滚）
- `fileSnapshots`：不再独立上报，快照数据随 `fileDetails` 一起上报

**新增字段**：`duplicationOccurrences`；`fileDetails` 每项新增 `snapshotData` 子字段（`DuplicationOccurrenceDTO.contentB64` 与 `FileDetailDTO.snapshotData` 均 `@ToString.Exclude` 防日志泄露）

```jsonc
{
  // 现有字段（gitUrl, branchName, pipelineRunId, runNumber, metricsData, detectionStartedAt, detectionCompletedAt, status, errorMessage）
  // 注意：repository 字段已移除
  "fileDetails": [                 // 现有字段, 每项新增 snapshotData 子字段
    {
      "filePath": "src/main/Foo.java",
      "language": "java",
      "loc": 200,
      "functionCount": 8,
      "avgFunctionLoc": 25.0,
      "avgCyclomaticComplexity": 3.5,
      "duplicationRate": 35.5,
      "duplicationLineCount": 120,
      "functionDetails": [...],
      "snapshotData": "eyJ0b3RhbExpbmVzIjoyMDAsImNvbnRleHRMaW5lcyI6NSxzZWdtZW50cyI6W119..."  // 新增, 可选: 上下文片段JSON(Base64编码), 仅重复文件有值, 解码后结构见 §4.2
    }
  ],
  "identicalFileDetails": [        // 现有字段, 结构变更: 每项只含 duplicatedFiles 数组(含组内所有文件), 不再含 filePath
    {
      "duplicatedFiles": ["src/main/A.java", "src/main/B.java", "src/main/C.java"]  // 一组完全一致的所有文件
    }
  ],
  "duplicationOccurrences": [      // 新增, 可选
    {
      "groupId": "a1b2c3d4e5f6",
      "contentHash": "a1b2c3d4e5f6",
      "occurrenceIndex": 0,
      "filePath": "src/main/Foo.java",
      "startLine": 10,
      "endLine": 40,
      "contentB64": "cHVibGljIGNsYXNz..."
    },
    {
      "groupId": "a1b2c3d4e5f6",   // 同 group, 另一个出现位置（同文件其他位置）
      "contentHash": "a1b2c3d4e5f6",
      "occurrenceIndex": 1,
      "filePath": "src/main/Foo.java",
      "startLine": 80,
      "endLine": 110,
      "contentB64": "cHVibGljIGNsYXNz..."
    },
    {
      "groupId": "a1b2c3d4e5f6",   // 同 group, 第三个出现位置（其他文件）
      "contentHash": "a1b2c3d4e5f6",
      "occurrenceIndex": 2,
      "filePath": "src/main/Bar.java",
      "startLine": 5,
      "endLine": 35,
      "contentB64": "cHVibGljIGNsYXNz..."
    }
  ]
}
```

**响应**（`recordId` 为 String 类型）：

```jsonc
{ "code": 200, "msg": "success", "data": "1234567890123456789" } // recordId（String，雪花ID，防 JS 精度溢出）
```

**兼容性**：旧插件不传 `duplicationOccurrences` / `snapshotData` 时，后端正常处理其他字段，不报错（`hasSnapshot` 返回 false）。

### 6.1b 新增分批上报接口：`POST /metrics/code/duplication-blocks`

**用途**：插件端 `duplicationOccurrences` 超过单批上限（5000 条）时，首批随主报告 `/metrics/code/report` 上报并拿到 `recordId`，后续批次走此接口分批入库。

**请求体 `DuplicationBlockBatchDTO`**：

```jsonc
{
  "recordId": "1234567890123456789", // 主报告接口返回的 recordId（String）
  "blocks": [
    // 本批重复块出现位置（结构同 duplicationOccurrences）
    {
      "groupId": "a1b2c3d4e5f6",
      "contentHash": "a1b2c3d4e5f6",
      "occurrenceIndex": 0,
      "filePath": "src/main/Foo.java",
      "startLine": 10,
      "endLine": 40,
      "contentB64": "cHVibGljIGNsYXNz...",
    },
  ],
}
```

**响应**：`DataResult<Integer>`（本批实际保存条数）。

**幂等**：依赖 `code_metrics_duplication_block.uk_record_group_file_start` 唯一索引，同一 record 内同组同文件同起点只存一条，防插件网络重试重复入库。

### 6.2 详情查询接口扩展：`POST /metrics/code/file-detail`

**位置**：[CodeMetricsController.getFileMetricDetail](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/CodeMetricsController.java#L56-L66)

**请求体**（不变）：

```jsonc
{
  "repoId": 1,
  "branchName": "master",
  "pipelineRunId": "12345",
  "metricType": "3",
  "pageNum": 1,
  "pageSize": 20,
}
```

**响应** metricType=3 时 `DuplicationRateItem` 新增字段：

```jsonc
{
  "fileDetails": [
    {
      "filePath": "src/main/Foo.java",
      "totalLines": 200, // 新增：文件代码行总数（便于用户验证 重复率 = 重复行数 / 代码行总数）
      "duplicationRate": 35.5,
      "duplicationLineCount": 120,
      "duplicationBlockCount": 2, // 新增：该文件的重复块数量（含同文件内重复组，按 group_id 去重）
      "hasSnapshot": true, // 新增：是否有上下文片段快照（file_detail.snapshot_data 是否非空）
    },
  ],
}
```

> **说明**：`duplicatedFiles` 属 metricType=4 的 `FileDuplicationItem`（每组一条，含组内所有文件），不属于 `DuplicationRateItem`。

### 6.3 新增接口 1：`POST /metrics/code/file-content`

**用途**：前端点击文件路径时调用，返回上下文片段拼接的展示代码（`segments` 片段列表）+ 该文件所有重复块元信息。

**请求**：

```jsonc
{
  "repoId": 1,
  "branchName": "master",
  "pipelineRunId": "12345",
  "filePath": "src/main/Foo.java",
}
```

**响应（快照命中，hasSnapshot=true）**（实际实现为 `segments` 结构，**不再返回 `content` + `lineMapping`**）：

```jsonc
{
  "code": 200,
  "data": {
    "gitUrl": "https://gitcode.com/owner/repo.git",
    "branchName": "master",
    "pipelineRunId": "12345",
    "filePath": "src/main/Foo.java",
    "language": "java",
    "totalOriginalLines": 200,
    "hasSnapshot": true,
    "segments": [
      {
        "originalStartLine": 1,
        "originalEndLine": 50,
        "content": "package com.example;\npublic class Foo {\n  ...",
      },
      {
        "originalStartLine": 70,
        "originalEndLine": 120,
        "content": "  void methodB() {\n  ...",
      },
    ],
    "duplicationBlocks": [
      {
        "blockId": "1001",
        "groupId": "a1b2c3d4e5f6",
        "startLine": 10,
        "endLine": 40,
        "occurrenceCount": 3,
      },
      {
        "blockId": "1002",
        "groupId": "b2c3d4e5f6a1",
        "startLine": 80,
        "endLine": 110,
        "occurrenceCount": 3,
      },
    ],
  },
}
```

前端按 `segments` 片段渲染，行号直接用 `originalStartLine` 递增；片段间省略行数由前端按相邻片段行号差计算并插入 `... N lines omitted ...` 占位（不再需要后端 lineMapping）。

**响应（快照未命中，hasSnapshot=false）**：

```jsonc
{
  "code": 200,
  "data": {
    "gitUrl": "https://gitcode.com/owner/repo.git",
    "branchName": "master",
    "pipelineRunId": "12345",
    "filePath": "src/main/Foo.java",
    "language": "java",
    "totalOriginalLines": null,
    "hasSnapshot": false,
    "segments": null,
    "duplicationBlocks": [
      {
        "blockId": "1001",
        "groupId": "a1b2c3d4e5f6",
        "startLine": 10,
        "endLine": 40,
        "occurrenceCount": 3,
      },
      {
        "blockId": "1002",
        "groupId": "b2c3d4e5f6a1",
        "startLine": 80,
        "endLine": 110,
        "occurrenceCount": 3,
      },
    ],
  },
}
```

快照未命中时（旧 record 无 `snapshot_data`），前端左侧展示"该记录无代码快照"占位 + 重复块列表（`duplicationBlocks` 仍返回，用户可点击列表项打开 drawer 查看代码片段）。

**说明**：`duplicationBlocks` 列出该文件作为出现位置的所有重复块（每个块对应一个 group）。`blockId` 是该文件此出现位置的 blockId（String，前端用于标记"来源"tab）。`occurrenceCount` 是该组出现位置总数（前端判断是否显示多页签）。`duplicationBlocks` 无论快照是否命中都返回（来自 `code_metrics_duplication_block` 表，长期保留）。

**错误响应**：

```jsonc
{ "code": 500, "msg": "未找到对应的仓库信息，repoId: {id}" }
{ "code": 500, "msg": "未找到对应的指标记录" }
{ "code": 500, "msg": "参数错误：{detail}" }
```

### 6.4 新增接口 2：`POST /metrics/code/duplication-block/detail`

**用途**：前端点击高亮块时调用，按 groupId 返回该组所有出现位置（前端渲染为多页签）。

**请求**：

```jsonc
{ "groupId": "a1b2c3d4e5f6", "repoId": 1 }
```

**响应**（3 个出现位置的示例）：

```jsonc
{
  "code": 200,
  "data": {
    "groupId": "a1b2c3d4e5f6",
    "contentHash": "a1b2c3d4e5f6",
    "totalCount": 3,
    "occurrences": [
      {
        "blockId": 1001,
        "occurrenceIndex": 0,
        "filePath": "src/main/Foo.java",
        "startLine": 10,
        "endLine": 40,
        "content": "public void methodA() {\n  System.out.println(\"hello\");\n  ...",
      },
      {
        "blockId": 1002,
        "occurrenceIndex": 1,
        "filePath": "src/main/Foo.java",
        "startLine": 80,
        "endLine": 110,
        "content": "public void methodB() {\n  System.out.println(\"hello\");\n  ...",
      },
      {
        "blockId": 1005,
        "occurrenceIndex": 2,
        "filePath": "src/main/Bar.java",
        "startLine": 5,
        "endLine": 35,
        "content": "public class Bar {\n  public void methodA() {\n  ...",
      },
    ],
  },
}
```

**前端渲染**：每个 occurrence 对应一个 tab，tab 标签为 `basename(filePath):startLine-endLine`。点击任意 tab 切换展示对应出现位置的代码片段。

### 6.5 接口契约汇总

| 接口         | 方法 | 路径                                     | 鉴权                     | 请求体                           | 响应体                           |
| ------------ | ---- | ---------------------------------------- | ------------------------ | -------------------------------- | -------------------------------- |
| 上报         | POST | `/metrics/code/report`                   | APIG 签名                | CodeMetricsReportDTO（含新字段） | `DataResult<Long>`               |
| 文件详情     | POST | `/metrics/code/file-detail`              | 网关 token + repoId 校验 | FileMetricDetailQueryDTO         | `DataResult<FileMetricDetailVO>` |
| 文件代码视图 | POST | `/metrics/code/file-content`             | 网关 token + repoId 校验 | FileContentViewQueryDTO          | `DataResult<FileContentViewVO>`  |
| 重复块详情   | POST | `/metrics/code/duplication-block/detail` | 网关 token + repoId 校验 | DuplicationBlockQueryDTO         | `DataResult<DuplicationBlockVO>` |

### 6.6 错误码约定

| code | msg                                 | 场景                 |
| ---- | ----------------------------------- | -------------------- |
| 200  | success                             | 成功                 |
| 500  | 未找到对应的仓库信息，repoId: {id}  | repoId 无效          |
| 500  | 未找到对应的指标记录                | pipelineRunId 不存在 |
| 500  | 未找到对应的重复块组，groupId: {id} | groupId 无效         |
| 500  | 参数错误：{detail}                  | 校验失败             |

> **说明**：快照未命中（旧 record 无 `snapshot_data`）**不是错误**，返回 `code=200` + `hasSnapshot=false`，前端展示"该记录无代码快照"占位。前端仍展示该文件的重复块列表（来自 `code_metrics_duplication_block` 表，长期保留），不报错。

## 7. 安全设计

### 7.1 代码内容编码

- **方式**：Base64 + 两阶段回检验证（对齐 codecheck [FragmentCryptoUtil.java](file:///d:/Develop/Java/openlibing-codecheck/src/main/java/com/openlibing/codecheck/common/utils/security/FragmentCryptoUtil.java)）
- **编码**：`Base64.encodeBase64String(content.getBytes(UTF_8))`
- **解码两阶段验证**：
  1. `Base64.isBase64()` 快速过滤（含空格、特殊字符的源码直接跳过）
  2. 回检验证：解码 → 重新编码 → 比对原始值，不一致则保留原值（防误判 "pass"、"return" 等纯字母明文）
- **编码失败占位词**：`source code encode error`
- **已编码数据跳过二次编码**（防重复编码导致数据损坏）

### 7.2 日志脱敏

#### 7.2.1 禁止打印的字段

service 层禁止 `logger.info` / `logger.debug` 打印以下字段值：

- `content_b64`（出现位置代码内容，Base64 编码后的字符串）
- `snapshot_data`（文件上下文片段 JSON，Base64 编码后的字符串）
- `content`（解码后的明文）

#### 7.2.2 允许打印的字段

只打印 `filePath + lineRange + blockId + groupId + recordId` 等元信息：

```java
// ✅ 正确
logger.info("Query file content, repoId: {}, filePath: {}, blockCount: {}", repoId, filePath, blocks.size());
logger.info("Query duplication block detail, groupId: {}, occurrenceCount: {}", groupId, occurrences.size());

// ❌ 错误
logger.info("File content: {}", content);  // 禁止
logger.info("Block content b64: {}", block.getContentB64());  // 禁止
```

### 7.3 鉴权

#### 7.3.1 上报接口

沿用 APIG 签名（SDK-HMAC-SHA256）+ HTTPS，不退化。详见 [CoderepoUploader.js](file:///d:/Develop/Java/openlibing-cicd-test-new/.gitcode/actions/code-metrics-action/dist/uploaders/CoderepoUploader.js) 的 `ApigSigner`。

#### 7.3.2 查询接口

- `file-content` / `duplication-block/detail` 走网关 token 鉴权
- `duplication-block/detail` 入参加 `repoId`，业务层校验用户对该 repoId 的访问权限（防止用户通过 groupId 越权访问其他仓库的重复块）
- controller 层补充 `@Valid` + 业务层校验 `repoId` 对应仓库的可见性
- 用户无权限访问某仓库时，返回 403

### 7.4 输入校验

- 所有查询接口入参用 `@Valid` + JSR-303 注解校验（`@NotNull` / `@NotBlank` / `@Min`）
- `filePath` 入参需校验路径遍历攻击（如 `../`）：业务层过滤 `filePath.contains("..")` 时拒绝
- `groupId` 入参校验为合法的 SHA-256 格式（64 位十六进制）

### 7.5 上报接口防滥用

- APIG 签名保证只有持 AK/SK 的插件能上报
- 单次上报体量 ≤ 10MB，超过则分批
- 未来可加 rate limit：单 gitUrl 每小时上报次数上限

### 7.6 Git 平台 token 安全

- **本需求不调用 Git API 拉取完整文件**：快照未命中即提示"该记录无代码快照"，不做 Git API 降级，因此代码视图查询链路不涉及 Git 平台 token 的使用
- [RepoServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java) 中已有的 GitCode/Gitee/GitHub 工具类仍用于其他场景（仓库同步、分支同步等），但本需求的 `file-content` / `duplication-block/detail` 接口不依赖它
- 收益：减少凭证使用面（不为查看完整文件而调 Git 平台 API），降低 token 泄露风险

### 7.7 数据长期保留的安全考量（无 TTL）

- 上下文片段快照（`file_detail.snapshot_data`）和重复块（`code_metrics_duplication_block`）均**长期保留**，无 TTL 清理，优先保证用户能看到完整的历史记录
- 虽数据长期保留，但 `snapshot_data` 只存重复块 ±5 行上下文片段（非完整文件），且为 Base64 编码的 JSON；即使 DBA 解码也只能看到片段，无法还原完整文件
- 重复块表（`code_metrics_duplication_block`）长期保留，但仅含代码片段（非完整文件），且为 Base64 编码
- 若未来合规要求"代码不长期留存"，可按 `code_metrics_record.create_time` 统一清理过期 record 及其关联的 file_detail / duplication_block（不在本期范围内）

### 7.8 安全验收清单

- [ ] DBA 直接查表确认 `content_b64` 和 `snapshot_data` 字段均为 Base64 字符串
- [ ] 后端日志 grep "File content" / "Block content" 无代码内容泄露
- [ ] 上报接口未持 AK/SK 的请求被 APIG 拒绝（401）
- [ ] 查询接口未持网关 token 的请求被拒绝（401）
- [ ] 用户无权限访问某仓库时返回 403
- [ ] 用户通过 groupId 越权访问其他仓库重复块时返回 403（鉴权校验 repoId 与 groupId 归属）
- [ ] `filePath` 含 `../` 时被拒绝
- [ ] `groupId` 非法格式时被拒绝
- [ ] Git 平台 token 不出现在任何日志中
- [ ] 单元测试覆盖：编码 → 入库 → 查询 → 解码 全链路
