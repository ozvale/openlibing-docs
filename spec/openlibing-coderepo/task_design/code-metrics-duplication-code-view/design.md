# 代码重复率详情 - 展示具体重复代码（技术设计）

> 配套 [proposal.md](./proposal.md)。本文聚焦"怎么做"。

> **实现偏差说明（实际实现与本文档原始设计不一致点，实施时以实际代码为准）**
>
> 1. **`reportMetrics` 返回类型**：实际由 `DataResult<Long>` 改为 `DataResult<String>`（recordId 用 String，避免雪花 ID 在 JS 侧 Number 精度溢出 2^53）。
> 2. **新增独立分批上报接口** `POST /metrics/code/duplication-blocks`（`DuplicationBlockBatchDTO`：`recordId`(String) + `blocks`），对应 Service 方法 `saveDuplicationBlocksBatch`。插件端 `duplicationOccurrences` 超过单批 5000 时，首批随主报告 `/report` 上报，后续批次走此接口。本文档原始设计仅按"递归分批调 `/report`"描述，实际落地为独立接口。
> 3. **`file-content` 返回结构**：实际 `FileContentViewVO` 不再返回 `content` + `lineMapping`，改为返回 `segments`（List\<CodeSegment\>，含 `originalStartLine`/`originalEndLine`/`content` 明文）。省略行数由前端按相邻片段行号差计算并插入占位，不再有后端 lineMapping。
> 4. **`duplication-block/detail`**：`DuplicationBlockQueryDTO` 实际新增 `branchName`、`pipelineRunId`、`sourceBlockId`（可选）；`DuplicationBlockVO.Occurrence` 实际新增 `contentStartLine`、`contentEndLine`，且 `blockId` 为 String；`content` 优先取自 `file_detail.snapshot_data` 中包含 [startLine,endLine] 的上下文章段，snapshot 不存在时 fallback 为重复块本身代码。`sourceBlockId` 用于 sourceBlockId 交集定位（见 §4.4）。
> 5. **DB 表**：`code_metrics_duplication_block` 实际**没有 `git_url`/`branch_name` 列**；索引为 `idx_record_group`、`idx_record_file`、唯一键 `uk_record_group_file_start`（不再有 `idx_record_id`/`idx_content_hash`）。`code_metrics_file_detail` 实际**新增了 `idx_record_file` 索引**。`code_metrics_record` 实际**新增唯一索引 `uk_git_branch_run`**。
> 6. **`repository` 字段**：实际仅 **DTO/Entity 移除 `repository` 字段**，DB 层 `code_metrics_record.repository` 列**保留不 drop**（便于回滚），liquibase changeset 注释已写明。
> 7. **`FileMetricDetailVO.DuplicationRateItem`**：实际新增 `totalLines`、`duplicationBlockCount`、`hasSnapshot` 三个字段（`duplicatedFiles` 属 metricType=4 的 `FileDuplicationItem`，非 DuplicationRateItem）。

## 1. 方案概述

```
┌─────────────────────┐   上报(含重复块+文件明细含快照, Base64编码)  ┌──────────────────────────┐
│  code-metrics-action│ ───────────────────────────────────────▶ │ openlibing-coderepo      │
│  (插件, jscpd/token)│   POST /metrics/code/report              │                          │
└─────────────────────┘                                          │  ┌────────────────────┐  │
                                                                 │  │ code_metrics_record│  │
                                                                 │  │  (主表, 已有)       │  │
                                                                 │  └─────────┬──────────┘  │
                                                                 │            │ record_id    │
                                                                 │  ┌─────────▼──────────┐  │
                                                                 │  │ code_metrics_       │  │
                                                                 │  │  duplication_block  │  │ ← 新增(长期保留)
                                                                 │  │  (出现位置, B64)    │  │
                                                                 │  └─────────┬──────────┘  │
                                                                 │  ┌─────────▼──────────┐  │
                                                                 │  │ code_metrics_       │  │ ← 已有表, 新增 snapshot_data 字段
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
1. **采集**：插件扫描时，对每个"重复块组"（同一代码内容在多个位置出现）记录所有出现位置（file + startLine + endLine + 代码内容），同组出现位置归为同一 `group_id`，Base64 编码后上报
2. **存储**：后端把每个出现位置存为一行到 `code_metrics_duplication_block`（长期，按 group_id 关联同一组，group_id = content 的 SHA-256）；上下文片段 JSON 存入 `code_metrics_file_detail.snapshot_data` 字段（**长期保留，无 TTL**，不存完整文件，只存重复块 ±5 行上下文）。**不再单独建 `code_metrics_file_snapshot` 表**——快照数据直接挂在 file_detail 上
3. **展示**：前端点击文件路径 → 调 `file-content` 接口拿到上下文片段拼接的展示代码 + `lineMapping` 行号映射 + 该文件所有重复块元信息 → monaco-editor 渲染 + 用 `lineMapping` 转换行号后高亮；点击高亮块 → 用 `block.groupId` 调 `duplication-block/detail` 拿到该组所有出现位置 → drawer 以多页签展示，每个 tab 对应一个出现位置（含同文件其他位置和其他文件位置）

## 2. 架构决策

### 2.1 缓存策略：方案 D（重复块长期 + 文件快照存 file_detail，无 TTL）

详见 [proposal.md §3.3](./proposal.md#33-核心问题决策代码缓存策略)。

补充决策：
- **文件快照仅缓存"有重复的文件"**：无重复的文件 `snapshot_data` 为 NULL，节省空间
- **无 TTL，长期保留（优先保证历史记录完整）**：上下文片段仅存重复块 ±5 行（合并后体积已大幅压缩，大文件省 90%+），DB 膨胀可控，无需 TTL 清理。用户回溯任意一次扫描结果时，上下文片段代码都应可见，不因过期而降级
- **快照未命中即提示"该记录无代码快照"（不做 Git API 降级）**：查询 `file-content` 时，只查 `code_metrics_file_detail.snapshot_data`；为空（旧 record 无快照数据）则返回 `hasSnapshot=false`，前端左侧代码区显示"该记录无代码快照"占位。**不走 Git API 拉取完整文件**——因为重复块行号是扫描时点的，拉最新代码会行号错位、高亮指错位置，"看似能看实则错位"的误导比"提示无快照"更差。但该文件的重复块列表（来自 `code_metrics_duplication_block` 表，长期保留）仍返回，前端展示为可点击列表，用户点击后 drawer 展示该组非来源出现位置的代码片段（含上下文行，重复块部分高亮）
- **快照数据挂在 file_detail 上（不单独建表）**：`code_metrics_file_detail` 新增 `snapshot_data` 字段，与文件明细一对一，直接挂载更简洁；无需 `content_hash` 去重（每个 file_detail 只对应自身一份快照）；少一张表、少一个 Entity/Mapper、少一个 JOIN
- **重复块按"出现位置"存储**：`code_metrics_duplication_block` 每行一个出现位置，同一代码内容的所有出现位置归为同一 group（group_id）。一个 N 位置重复块存 N 行（而非 N×(N-1)/2 对），存储更省，且干净支撑"一块对多位置（含同文件多位置）"场景。前端 drawer 多页签直接映射 occurrence_index（不含来源位置）

### 2.2 编码方案：Base64 + 两阶段回检验证

**复用 codecheck [FragmentCryptoUtil.java](file:///d:/Develop/Java/openlibing-codecheck/src/main/java/com/openlibing/codecheck/common/utils/security/FragmentCryptoUtil.java) 的设计思想**，但在 coderepo 仓内独立实现（不跨仓依赖）：

- 编码：`Base64.encodeBase64String(content.getBytes(UTF_8))`
- 解码两阶段验证：
  1. `Base64.isBase64()` 快速过滤（含空格、特殊字符的源码直接跳过）
  2. 回检验证：解码 → 重新编码 → 比对原始值，不一致则保留原值（防误判"pass"、"return"等纯字母明文）
- 编码失败占位词：`source code encode error`
- 已编码数据跳过二次编码（防重复编码导致数据损坏）

**为什么不是 AES？**
- 当前 codecheck 已用 Base64 并经过安全 review，平台内一致
- Base64 解决的是"明文不出现在日志/DBA 一眼可见"问题，已满足本期安全目标
- 若后续合规要求升级（如等保三级要求加密存储），可在工具类内部平滑替换为 AES-256，密钥从配置中心读取，对上层接口透明

**为什么跨仓独立实现而不复用 codecheck 的工具类？**
- codecheck 与 coderepo 是两个独立微服务，不共享 common 模块的 utility
- 跨仓 jar 依赖会引入版本耦合，不利于独立演进
- 工具类逻辑简单（≈100 行），独立维护成本可接受

### 2.3 上报体量控制

- 单次 HTTP 请求体 ≤ 10MB（与 APIG 网关限制对齐）
- 超过则分批上报：插件端按 `duplicationOccurrences` 数量切片，每批 ≤ 5000 条
- 分批上报的 recordId 一致，后端按 recordId 累积入库
- **快照数据随 `fileDetails` 一起上报**（每个 fileDetail 携带自身的 `snapshotData`），不再单独上报文件快照，避免混批

### 2.4 行号对齐策略

- 重复块的 `startLine / endLine` 来自插件扫描时的源文件实际行号（1-based），存入 `code_metrics_duplication_block`
- 文件快照的 `snapshot_data`（存于 `code_metrics_file_detail` 表）是扫描时点的**上下文片段**（非完整文件），只含重复块 ±5 行上下文，其他部分用 `... N lines omitted ...` 占位，**无 TTL 长期保留**
- 代码视图（快照命中，即 file_detail.snapshot_data 非空）：后端解析 `snapshot_data` JSON → 拼接展示内容（片段 + 占位行）+ 构建 `lineMapping` → 前端 monaco-editor 渲染拼接内容 → 用 `lineMapping` 把原始 `startLine/endLine` 转换为展示行号 → `deltaDecorations` 高亮 `[displayStart-1, displayEnd-1]`
- 代码视图（快照未命中，即旧 record 的 file_detail.snapshot_data 为空）：**不走 Git API 拉取**，左侧代码区显示"该记录无代码快照"占位；重复块列表仍展示（来自 `code_metrics_duplication_block` 表），用户点击列表项 → drawer 展示该组非来源出现位置代码片段。避免拉最新代码导致行号错位、高亮指错位置误导用户
- drawer 内代码片段：每个出现位置的 `content` 是扫描时点提取的代码内容（存于 `code_metrics_duplication_block.content_b64`，长期保留），展示时附带上下文行（重复块 ±5 行），使用源文件原始行号，重复块部分高亮显示，上下文行不高亮。不含来源位置（来源位置已在主视图左侧展示）

## 3. 数据模型设计

### 3.1 新增表 `code_metrics_duplication_block`（出现位置表，长期保留）

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

**字段说明**：
- `group_id`：重复块组ID，同一代码内容的所有出现位置归为同一组。一个组对应一个"重复块"，组内有 N 个出现位置
- `occurrence_index`：组内出现位置序号，按 (filePath, startLine) 排序后从 0 递增。前端 drawer 多页签按此排序
- `file_path`：出现位置文件路径。同一文件可能有多个出现位置（同文件内重复）
- `content_b64`：MEDIUMTEXT 最大 16MB，单块代码（通常 < 1KB）足够
- **实际实现去掉了 `git_url` / `branch_name` 列**（通过 `record_id` 关联主表即可定位仓库/分支，避免冗余）
- 索引：`idx_record_group` 覆盖 `deleteByRecordId`（record_id 最左前缀）和 `selectByGroupId`/`countByRecordAndGroup`；`idx_record_file` 服务文件代码视图查询；唯一键 `uk_record_group_file_start` 保证幂等，防止插件端网络重试导致同一出现位置重复入库

**关键设计变化**：从"source + target 对存储"改为"出现位置"表。优势：
1. 干净支撑"一块对多位置"（含同文件多位置），无需 pair_index 概念
2. 一个 N 位置重复块存 N 行（而非 N×(N-1)/2 对），存储更省
3. 前端多页签直接映射 occurrence_index，无需二次组装

### 3.2 现有表 `code_metrics_file_detail` 新增 `snapshot_data` 字段（长期保留，无 TTL）

**不再单独建 `code_metrics_file_snapshot` 表**。上下文片段快照数据直接存入 `code_metrics_file_detail` 表的新增字段 `snapshot_data`，与文件明细一对一。

```sql
ALTER TABLE code_metrics_file_detail
ADD COLUMN snapshot_data LONGTEXT NULL COMMENT '上下文片段JSON(Base64编码), 仅重复文件有值; 结构:{totalLines,contextLines,segments:[{originalStartLine,originalEndLine,contentB64}]}, 无TTL长期保留';
```

**`snapshot_data` JSON 结构**（Base64 编码后存储）：

```jsonc
{
  "totalLines": 200,           // 文件原始总行数
  "contextLines": 5,           // 上下文行数（重复块上下各取 5 行）
  "segments": [                // 合并后的上下文片段列表（按 originalStartLine 排序）
    {
      "originalStartLine": 1,   // 该片段对应的原始文件起始行号(1-based)
      "originalEndLine": 45,    // 该片段对应的原始文件结束行号(1-based, 包含)
      "contentB64": "Base64..." // 该区间代码内容(Base64编码)
    }
  ]
}
```

**字段说明**：
- `snapshot_data`：LONGTEXT（最大 4GB），nullable。存 Base64 编码的 JSON，JSON 内每个 segment 的 `contentB64` 也是 Base64（防 DBA 解码外层后代码明文可见）。**不存完整文件**，只存重复块 ±5 行上下文的片段，其他部分前端用 `... N lines omitted ...` 占位。无重复的文件该字段为 NULL。**无 TTL，长期保留**——上下文片段体积已大幅压缩，无需 TTL 清理，优先保证用户能看到完整的历史记录

> **不再有 `content_hash` / `line_count` / `context_lines` / `segment_count` / `file_size_bytes` / `created_at` 等独立字段**：这些原属 `code_metrics_file_snapshot` 表的字段不再需要。`content_hash` 去重逻辑取消（每个 file_detail 只对应自身一份快照，无需去重）；`totalLines` / `contextLines` 已内含在 `snapshot_data` JSON 中；监控字段非必要。

**片段合并算法**（插件端执行）：

1. 收集文件所有重复块的 `[startLine, endLine]`
2. 计算上下文区间 `[max(1, startLine - contextLines), min(totalLines, endLine + contextLines)]`（contextLines=5）
3. 按 `contextStartLine` 排序
4. 合并重叠/相邻区间：若下一区间 `startLine` ≤ 上一区间 `endLine + 1`，合并为一个片段
5. 每个合并后的片段提取一次代码内容，Base64 编码

### 3.3 现有表其他变更

- `code_metrics_record`：**DTO/Entity 移除 `repository` 字段**（写死 source-dir 后，工作流所在仓 git_url 即扫描仓，`repository` owner/repo 字段冗余无用）；**DB 层 `repository` 列保留不 drop**（不再使用，便于回滚，liquibase changeset 注释已写明）。同时**新增唯一索引 `uk_git_branch_run (git_url, branch_name, pipeline_run_id)`** 保证幂等，防止并发上报重复 record
- `code_metrics_file_detail`：新增 `snapshot_data` 字段（见 §3.2）+ 新增 `idx_record_file (record_id, file_path(255))` 索引。`metrics_json` 字段继续承载现有指标，结构不变。重复块独立成 `code_metrics_duplication_block` 表的原因：一对多关系不适合塞进 JSON

## 4. 接口设计

### 4.1 上报接口扩展：`POST /metrics/code/report`

**请求体在 [CodeMetricsReportDTO](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/dto/metrics/CodeMetricsReportDTO.java) 基础上变更**：

**返回类型变更**：`reportMetrics` 的返回类型由 `DataResult<Long>` 改为 **`DataResult<String>`**（recordId 用 String 返回，避免雪花 ID 在 JS 侧 Number 精度溢出 2^53）。

**移除字段**：
- `repository`：写死 source-dir 后冗余，**DTO/Entity 移除**（DB 层 `code_metrics_record.repository` 列**保留不 drop**，便于回滚）
- `fileSnapshots`：不再独立上报，快照数据随 `fileDetails` 一起上报

**新增/调整字段**：`duplicationOccurrences`（新增）；`fileDetails` 每项新增 `snapshotData` 子字段；`identicalFileDetails` 每项移除 `filePath`（只保留 `duplicatedFiles` 数组，含组内所有文件）。`DuplicationOccurrenceDTO.contentB64` 与 `FileDetailDTO.snapshotData` 均标注 `@ToString.Exclude`（防日志泄露代码内容）。

```java
public class CodeMetricsReportDTO {
  // 现有字段（gitUrl, branchName, pipelineRunId, runNumber, metricsData,
  // detectionStartedAt, detectionCompletedAt, status, errorMessage）
  // 注意：repository 字段已移除

  /** 文件级指标明细列表（现有，FileDetailDTO 新增 snapshotData 子字段） */
  private List<FileDetailDTO> fileDetails;

  /** 完全一致文件明细列表（现有，IdenticalFileDetailDTO 移除 filePath，只保留 duplicatedFiles） */
  private List<IdenticalFileDetailDTO> identicalFileDetails;

  /** 重复块出现位置列表（新增，每个出现位置一条，同 group_id 关联） */
  private List<DuplicationOccurrenceDTO> duplicationOccurrences;

  public static class FileDetailDTO {
    // ... 现有字段保持不变（filePath, language, loc, functionCount, avgFunctionLoc,
    //     avgCyclomaticComplexity, duplicationRate, duplicationLineCount, functionDetails）...
    private String snapshotData;  // 新增: 上下文片段JSON(Base64编码), 仅重复文件有值, 解码后结构见 §3.2
  }

  public static class IdenticalFileDetailDTO {
    // 移除 filePath 字段：每组完全一致文件只生成一条记录，duplicatedFiles 含组内所有文件
    private List<String> duplicatedFiles;  // 与该文件完全一致的文件路径列表（含组内所有文件）
  }

  /** 重复块出现位置 DTO */
  @Data @Builder @AllArgsConstructor @NoArgsConstructor
  public static class DuplicationOccurrenceDTO {
    private String groupId;             // 重复块组ID（同 content_hash 的所有出现位置归为同一组）
    private String contentHash;         // 重复内容 SHA-256 hex
    private Integer occurrenceIndex;    // 组内出现位置序号(0-based)
    private String filePath;            // 出现位置文件相对路径
    private Integer startLine;          // 1-based
    private Integer endLine;
    private String contentB64;          // 出现位置代码内容(Base64)
  }
}
```

> **不再有 `FileSnapshotDTO` 内部类和 `fileSnapshots` 字段**：快照数据随 `fileDetails` 一起上报（每个 fileDetail 携带自身的 `snapshotData`），由 `saveFileDetails` 统一处理，不再独立入库。

**后端处理（[CodeMetricsServiceImpl.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/CodeMetricsServiceImpl.java)）**：
- `reportMetrics` 增加幂等性检查：相同 `gitUrl + branchName + pipelineRunId` 的旧记录先删除（`codeMetricsFileDetailMapper.deleteByRecordId` + `codeMetricsRecordMapper.deleteById`），防止重复上报导致 file_detail 表产生重复记录；同时 DB 层 `uk_git_branch_run` 唯一索引兜底保证并发下不产生重复 record。**返回 `DataResult<String>`（recordId）**
- `saveCodeMetricsRecord`：移除 `repository` 字段设置（DTO/Entity 已删除，DB 列保留不 drop）
- `saveFileDetails`：现有方法，改造为处理 `fileDetail.snapshotData` 字段（随 file_detail 一起入库，存入 `code_metrics_file_detail.snapshot_data` 列）
- `saveIdenticalFileDetails`：适配新结构（`IdenticalFileDetailDTO` 不再含 `filePath`，每组完全一致文件只生成一条 file_detail 记录，`metrics_json` 中存 `duplicatedFiles` 数组 + `isIdenticalFile=true`）
- `reportMetrics` 新增 `saveDuplicationBlocks(request, recordId)`
- **不再实现 `saveFileSnapshots`**：快照随 `saveFileDetails` 入库，无独立方法
- 批量插入（MyBatis Plus `saveBatch`，每批 500 条）
- 入库前对 `contentB64` **不做二次编码**（插件端已编码），但出库时会走两阶段验证解码
- `buildPipelineLink`：原依赖 `record.getRepository()`，改为从 `record.getGitUrl()` 提取 owner/repo（沿用现有 `extractOwnerRepo` 工具方法）

### 4.1b 新增分批上报接口：`POST /metrics/code/duplication-blocks`

**用途**：插件端 `duplicationOccurrences` 超过单批上限（5000 条）时，首批随主报告 `/metrics/code/report` 上报，**后续批次走此接口**分批入库（主报告接口仍全量入库，批次接口只负责剩余部分）。

**请求体 `DuplicationBlockBatchDTO`**：

```java
public class DuplicationBlockBatchDTO {
  @NotBlank private String recordId;  // 关联主表记录ID（由 /report 接口返回，String 类型，雪花ID 防 JS 精度溢出）
  @NotEmpty @Valid private List<CodeMetricsReportDTO.DuplicationOccurrenceDTO> blocks;  // 本批重复块出现位置
}
```

**响应**：`DataResult<Integer>`（本批实际保存条数）。

**后端处理**：Service 新增 `DataResult<Integer> saveDuplicationBlocksBatch(DuplicationBlockBatchDTO request)`——按 `recordId` 定位 record，`saveBatch` 批量入库（每批 500），单条失败容错；依赖 `uk_record_group_file_start` 唯一索引保证幂等（同一 record 内同组同文件同起点只存一条，防插件网络重试重复入库）。

### 4.2 详情查询接口扩展：`POST /metrics/code/file-detail`

**[FileMetricDetailVO.DuplicationRateItem](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/vo/FileMetricDetailVO.java#L107-L121) 新增字段**：

```java
public static class DuplicationRateItem {
  private String filePath;
  private Object duplicationRate;
  private Integer duplicationLineCount;
  // 新增字段（实际实现）
  private Integer totalLines;            // 代码行总数（文件总行数，便于用户验证 重复率 = 重复行数 / 代码行总数）
  private Integer duplicationBlockCount; // 该文件的重复组数（COUNT(DISTINCT group_id)，含同文件内重复组）
  private Boolean hasSnapshot;           // 是否有上下文片段快照(true=file_detail.snapshot_data 非空, false=旧 record 无快照数据)
}
```

> **说明**：`duplicatedFiles` 属 metricType=4 的 `FileDuplicationItem`（已有结构，每组一条，含组内所有文件），不属于 `DuplicationRateItem`。

后端在 `appendMetricItems` 的 `TOTAL_CODE_DUPLICATION_RATE` 分支中，额外查询 `code_metrics_duplication_block` 表（`COUNT(DISTINCT group_id)` 按组去重）、`code_metrics_file_detail.snapshot_data` 字段是否非空（`hasSnapshot`）以及文件总行数（`totalLines`）。

### 4.3 新增接口 1：`POST /metrics/code/file-content`

**用途**：前端点击文件路径时调用，返回上下文片段拼接的展示代码（`segments` 片段列表）+ 该文件所有重复块元信息。

**请求**：
```java
public class FileContentViewQueryDTO {
  @NotNull private Integer repoId;
  @NotBlank private String branchName;
  @NotBlank private String pipelineRunId;
  @NotBlank private String filePath;
}
```

**响应**（实际实现为 `segments` 结构，**不再返回 `content` + `lineMapping`**）：
```java
public class FileContentViewVO {
  private String gitUrl;
  private String branchName;
  private String pipelineRunId;
  private String filePath;
  private String language;
  private Integer totalOriginalLines;   // 文件原始总行数; hasSnapshot=false 时为 null
  private Boolean hasSnapshot;          // true=file_detail.snapshot_data 非空（可展示上下文片段代码）; false=旧 record 无快照数据（左侧显示"该记录无代码快照"占位）
  private List<CodeSegment> segments;   // 代码片段列表（含原始行号）; hasSnapshot=false 时为 null
  private List<DuplicationBlockRef> duplicationBlocks;  // 该文件所有重复块（按 group 去重）; 无论快照是否命中都返回（来自 duplication_block 表，长期保留）
}

// 代码片段：前端按片段渲染，行号直接用 originalStartLine 递增；片段间省略行数由前端按相邻片段行号差计算并插入 "... N lines omitted ..." 占位
public static class CodeSegment {
  private Integer originalStartLine;  // 原始起始行号（1-based）
  private Integer originalEndLine;    // 原始结束行号（1-based, 包含）
  private String content;             // 片段代码内容（明文，未编码）
}

public static class DuplicationBlockRef {
  private String blockId;              // 该文件此出现位置的 blockId（雪花ID，String 防 JS 精度溢出，用于 drawer 标记"来源"tab）
  private String groupId;              // 重复块组ID（drawer 查询用）
  private Integer startLine;
  private Integer endLine;
  private Integer occurrenceCount;     // 该组出现位置总数（前端判断是否显示多页签）
}
```

**后端逻辑**：
1. 查 `code_metrics_record` 拿 recordId
2. 查 `code_metrics_file_detail` 拿 `snapshot_data`（按 recordId + filePath）
3. 命中（snapshot_data 非空） → Base64 解码 snapshot_data → 解析 JSON 得到 segments → 逐段 Base64 解码 contentB64 → 组装 `List<CodeSegment>`（每段含 `originalStartLine`/`originalEndLine`/`content` 明文）→ `hasSnapshot=true, segments=<片段列表>, totalOriginalLines=<原始总行数>`
4. 未命中（旧 record 的 snapshot_data 为空）→ `hasSnapshot=false, segments=null, totalOriginalLines=null`（**不走 Git API 降级**，避免行号错位误导用户）
5. 查 `code_metrics_duplication_block` 拿该文件所有出现位置（按 group 聚合，不含代码内容）→ 填入 `duplicationBlocks`（无论快照是否命中都返回，前端用于渲染重复块列表/高亮）
6. 返回

> **说明**：前端用 `originalStartLine` 直接渲染行号，不再需要后端 lineMapping；片段之间的省略行数由前端计算（相邻片段差、首段前 `originalStartLine-1`、末段后 `totalOriginalLines-lastEnd`）。

### 4.4 新增接口 2：`POST /metrics/code/duplication-block/detail`

**用途**：前端点击高亮块时调用，按 groupId 返回该组所有出现位置（前端渲染为多页签）。

**请求**（实际实现新增 `branchName`、`pipelineRunId`、`sourceBlockId`）：
```java
public class DuplicationBlockQueryDTO {
  @NotBlank private String groupId;           // 重复块组ID
  @NotNull private Integer repoId;            // 用于鉴权（防越权访问其他仓库的重复块）
  @NotBlank private String branchName;        // 分支名称（定位具体扫描记录）
  @NotBlank private String pipelineRunId;     // 流水线执行记录ID（定位具体扫描记录，避免同 group_id 跨多次扫描混淆）
  private String sourceBlockId;               // 可选：源代码块的 blockId（雪花ID，String），用于交集定位
}
```

**响应**（实际实现 `Occurrence` 新增 `contentStartLine`/`contentEndLine`，`blockId` 为 String）：
```java
public class DuplicationBlockVO {
  private String groupId;
  private String contentHash;
  private Integer totalCount;          // 出现位置总数
  private List<Occurrence> occurrences;

  public static class Occurrence {
    private String blockId;            // 出现位置记录ID（雪花ID，String 防 JS 精度溢出）
    private Integer occurrenceIndex;
    private String filePath;
    private Integer startLine;         // 重复块起始行号（1-based，高亮用）
    private Integer endLine;           // 重复块结束行号（1-based, 包含，高亮用）
    private String content;            // 代码片段内容（含上下文，Base64解码后明文；优先取自 snapshot_data 包含 [startLine,endLine] 的上下文章段，snapshot 不存在时 fallback 为重复块本身代码）
    private Integer contentStartLine;  // content 片段的起始行号（1-based，前端渲染行号用；含上下文时 < startLine，fallback 时 == startLine）
    private Integer contentEndLine;    // content 片段的结束行号（1-based, 包含）
  }
}
```

**`sourceBlockId` 交集定位逻辑**：
- 背景：同一重复组内各 occurrence 的行数可能不同（union-find 分组导致，如文件 B 的 20 行重复块和文件 A 的 10 行重复块归为同组）。
- 传入 `sourceBlockId` 后，以其对应代码块内容为基准，在其他 occurrence 的 block content 中**定位匹配子区间（取交集）**，返回交集部分的行号与 ±5 行上下文，使前端能精确高亮"与源代码块真正重复"的部分，而非整个 occurrence 区间。
- **未传 `sourceBlockId` 时退化为原行为**：直接用各 occurrence 自身的 `startLine`/`endLine`。

**后端逻辑**：
1. 校验 groupId + repoId（鉴权：groupId 必须属于 repoId 对应的仓库）
2. 按 `branchName + pipelineRunId` 定位具体某次扫描的 recordId（避免同 group_id 跨多次扫描混淆）
3. 查 `code_metrics_duplication_block` by (record_id, group_id) → 返回该组所有出现位置，按 occurrence_index 排序
4. 对每个出现位置的 `content_b64` 做 Base64 解码（两阶段验证）；`content` 优先从该文件 `file_detail.snapshot_data` 中取包含 [startLine, endLine] 的上下文章段，snapshot 不存在时 fallback 为重复块本身代码；据此计算 `contentStartLine`/`contentEndLine`
5. 若传入 `sourceBlockId`，则以该块内容为基准在其他 occurrence 的 content 中定位匹配子区间（取交集），返回交集部分行号与 ±5 行上下文
6. 返回

## 5. 插件改造

### 5.1 `DuplicationDetector.js` 改造

**当前问题**：[DuplicationDetector.js](file:///d:/Develop/Java/openlibing-cicd-test-new/.gitcode/actions/code-metrics-action/dist/detectors/DuplicationDetector.js) 主路径 `detectWithTokenLevel` 只产出"文件 → 重复行号集合"，没有显式的"重复块"概念。**原插件只检测跨文件重复**（同文件内重复不算），**本次需求同步修复为同文件重复也算**。需要改造为"重复块"结构。

**改造方案**：

1. **主路径 `detectWithTokenLevel` 后处理**：在拿到 `fileDuplicatedLines: Map<file, Set<line>>` 后，对每个文件的行号集合做"连续区间合并"：
   ```js
   // 连续行号合并为区间：{startLine, endLine}
   mergeConsecutiveLines(lineSet) {
     const sorted = [...lineSet].sort((a, b) => a - b);
     const ranges = [];
     let start = sorted[0], prev = sorted[0];
     for (let i = 1; i < sorted.length; i++) {
       if (sorted[i] === prev + 1) { prev = sorted[i]; }
       else { ranges.push({startLine: start, endLine: prev}); start = sorted[i]; prev = sorted[i]; }
     }
     ranges.push({startLine: start, endLine: prev});
     return ranges;
   }
   ```
   - 合并后每个区间是一个"候选重复块"
   - 过滤掉区间长度 < `minLines`（10）的（与 cmetrics 定义对齐）

2. **配对关系建立**：当前 token-level 算法只标记了行号，没有显式配对。需要扩展 `hashToLocations` 逻辑：
   - 在 `Step 3` 标记行号时，同时记录每个 hash 对应的 `(file, startLine, endLine)` 列表
   - 对每个 hash，2+ 位置出现 → 所有出现位置归为同一 group（group_id = contentHash），每个位置生成一条 `DuplicationOccurrence`
   - 同组出现位置按 (filePath, startLine) 排序，occurrenceIndex 从 0 递增

3. **提取代码内容**：
   ```js
   extractBlockContent(filePath, startLine, endLine, sources) {
     const absPath = resolveAbsolutePath(filePath, sources);
     const content = fs.readFileSync(absPath, 'utf8');
     const lines = content.split('\n');
     return lines.slice(startLine - 1, endLine).join('\n');
   }
   ```

4. **fallback 路径 `detectWithJscpd`**：jscpd 的 `clone.duplicationA / duplicationB` 已有显式 start.line / end.line。改造点：把同一 clone 的两端（或多端）归为同一 group，每个端点生成一条出现位置记录

5. **返回结果新增字段**：
   ```js
   return {
     ...,
     duplicationOccurrences: [
       {
         groupId, contentHash, occurrenceIndex,
         filePath, startLine, endLine, content
       }
     ]
   };
   ```

### 5.2 `CoderepoUploader.js` 改造

[CoderepoUploader.js](file:///d:/Develop/Java/openlibing-cicd-test-new/.gitcode/actions/code-metrics-action/dist/uploaders/CoderepoUploader.js) 改造点：

1. **Base64 编码**：上报前对 `occurrence.content`（出现位置代码）和上下文片段代码做编码
   ```js
   const encodeB64 = (str) => Buffer.from(str, 'utf8').toString('base64');
   ```

2. **payload 调整**：移除独立的 `fileSnapshots` 字段，`snapshotData` 直接挂在每个 `fileDetail` 上随 `fileDetails` 一起上报
   ```js
   const payload = {
     ...,
     // fileDetails 每项已由 buildContextSegments 挂上 snapshotData 字段（Base64 编码的 JSON），直接随 fileDetails 上报
     fileDetails: metricsData.fileDetails || [],
     // 移除 fileSnapshots 字段：快照随 fileDetails 上报，不再独立
     duplicationOccurrences: metricsData.duplicationOccurrences?.map(o => ({
       ...o,
       contentB64: encodeB64(o.content),
       content: undefined  // 不传明文
     })) || []
   };
   ```

3. **分批上报**：单批 `duplicationOccurrences` ≤ 5000 条，超过则递归分批；`fileDetails`（含 `snapshotData`）整体上报不分批（单 record 通常 100-500 条，体量可控）
   ```js
   async uploadInBatches(metricsData, options) {
     const BATCH_SIZE = 5000;
     const occurrences = metricsData.duplicationOccurrences || [];
     if (occurrences.length <= BATCH_SIZE) {
       await this.upload(metricsData, options);
       return;
     }
     for (let i = 0; i < occurrences.length; i += BATCH_SIZE) {
       const batch = occurrences.slice(i, i + BATCH_SIZE);
       // fileDetails 等其他字段每批都全量带；duplicationOccurrences 分批
       await this.upload({...metricsData, duplicationOccurrences: batch}, options);
     }
   }
   ```

### 5.3 `fileCollector` 改造

[fileCollector.js](file:///d:/Develop/Java/openlibing-cicd-test-new/.gitcode/actions/code-metrics-action/dist/utils/fileCollector.js) 需新增"按行号区间读取文件内容"的辅助方法（如 `readLines(filePath, startLine, endLine, sources)`），供上下文片段采集用。采集在 `DuplicationDetector.detect` 末尾，调用 `buildContextSegments` 对 `fileDetails` 中 `duplicationLineCount > 0` 的文件提取每个重复块 ±5 行上下文（合并重叠/相邻区间），生成 `snapshotData` JSON（**不读取完整文件内容**，其他部分前端用 `... N lines omitted ...` 占位）。生成的 `snapshotData` 直接挂到对应 `fileDetail.snapshotData` 字段上，随文件明细一起上报。

## 6. 编码与安全方案

### 6.1 Base64 工具类（coderepo 仓新增）

新建 `openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/utils/security/CodeContentB64Util.java`，设计完全对齐 codecheck [FragmentCryptoUtil](file:///d:/Develop/Java/openlibing-codecheck/src/main/java/com/openlibing/codecheck/common/utils/security/FragmentCryptoUtil.java)：

```java
public final class CodeContentB64Util {
  private static final String ENCODE_ERROR_PLACEHOLDER = "source code encode error";

  private CodeContentB64Util() {}

  /** 编码：明文 → Base64。已编码数据跳过(防二次编码)。 */
  public static String encode(String plain) {
    if (plain == null) return null;
    if (isAlreadyEncoded(plain)) return plain;
    try {
      return Base64.encodeBase64String(plain.getBytes(StandardCharsets.UTF_8));
    } catch (Exception e) {
      return ENCODE_ERROR_PLACEHOLDER;
    }
  }

  /** 解码：两阶段验证(Base64.isBase64 + 回检)，失败保留原值(兼容历史明文) */
  public static String decode(String encoded) {
    if (encoded == null || ENCODE_ERROR_PLACEHOLDER.equals(encoded)) return encoded;
    if (!Base64.isBase64(encoded)) return encoded;
    try {
      String decoded = new String(Base64.decodeBase64(encoded), StandardCharsets.UTF_8);
      String reEncoded = Base64.encodeBase64String(decoded.getBytes(StandardCharsets.UTF_8));
      return encoded.equals(reEncoded) ? decoded : encoded;
    } catch (IllegalArgumentException e) {
      return encoded;
    }
  }

  private static boolean isAlreadyEncoded(String s) {
    if (!Base64.isBase64(s)) return false;
    try {
      String decoded = new String(Base64.decodeBase64(s), StandardCharsets.UTF_8);
      String reEncoded = Base64.encodeBase64String(decoded.getBytes(StandardCharsets.UTF_8));
      return s.equals(reEncoded);
    } catch (Exception e) { return false; }
  }
}
```

**调用点**：
- 入库前：插件端已编码，后端**不二次编码**，直接存
- 出库后：在 service 层调用 `decode` 后返回前端
- **日志脱敏**：service 层禁止 `logger.info` 打印 `content_b64` / `snapshot_data` / `content` 字段值，只打印 `filePath + lineRange + blockId + groupId`

### 6.2 鉴权

- 上报接口：沿用 APIG 签名（已有）
- 查询接口（`file-content`、`duplication-block/detail`）：沿用现有 [CodeMetricsController](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/CodeMetricsController.java) 的鉴权策略（前端调用走网关 token，按 repoId 校验用户对该仓库的访问权限）
- 新增接口需在 controller 层补充 `@Valid` + 业务层校验 `repoId` 对应仓库的可见性

### 6.3 TTL 清理（已移除）

本需求**不再使用 TTL 清理**。上下文片段快照存入 `code_metrics_file_detail.snapshot_data` 字段，随 file_detail 记录长期保留，优先保证用户能看到完整的历史记录。上下文片段仅存重复块 ±5 行（合并后体积已大幅压缩），无需 TTL 清理控制 DB 膨胀。

**不再修改 [XxlJobHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java)**：不新增定时任务。如未来需清理历史数据，可按 `code_metrics_record.create_time` 统一清理过期 record 及其关联的 file_detail / duplication_block（不在本期范围内）。

## 7. 性能方案

### 7.1 数据库索引

- `code_metrics_duplication_block`（实际实现）：
  - `idx_record_group (record_id, group_id)`：drawer 查询主路径，按 group_id 查所有出现位置；同时覆盖 `deleteByRecordId`（record_id 最左前缀）
  - `idx_record_file (record_id, file_path(255))`：文件代码视图查询，按 record + file 查该文件所有出现位置
  - `uk_record_group_file_start (record_id, group_id, file_path(255), start_line)`：**唯一索引，保证幂等**，防止插件网络重试导致同一出现位置重复入库
  - > 实际实现**去掉了 `idx_record_id` / `idx_content_hash`**（`idx_record_group` 已覆盖 deleteByRecordId；group_id 即 content_hash，无需单独索引）
- `code_metrics_file_detail`：
  - `idx_record_file (record_id, file_path(255))`（实际实现**新增**）：文件代码视图查询，按 record + file 查 file_detail（含 `snapshot_data`），避免 N+1 回表过滤
- `code_metrics_record`：
  - `uk_git_branch_run (git_url(255), branch_name, pipeline_run_id(255))`（实际实现**新增唯一索引**）：保证幂等，防止并发上报产生重复 record；创建前先清理历史重复记录

> **不再有 `code_metrics_file_snapshot` 表及其索引**：快照数据存入 `file_detail.snapshot_data`，复用 file_detail 的 `idx_record_file` 索引即可。

### 7.2 批量插入

- `code_metrics_duplication_block`：单次 record 可能 500-5000 条出现位置，用 MyBatis Plus `saveBatch(entities, 500)`
- `code_metrics_file_detail`（含 `snapshot_data`）：单次 record 通常 100-500 条，普通 `saveBatch` 即可；`snapshot_data` 字段随 `metrics_json` 一起写入同一条记录
- 入库失败单条不影响整体（沿用现有 `saveFileDetails` 的 try-catch 容错模式）

### 7.3 查询缓存

- `file-content` 接口：只查 `code_metrics_file_detail` 单表（按 record_id + file_path 索引，取 `snapshot_data` 字段），响应快，无需额外缓存；快照未命中（`snapshot_data` 为空）时直接返回 `hasSnapshot=false`，**不走 Git API、无 Caffeine 缓存**
- `duplication-block/detail` 接口：单次查询（按 record_id + group_id 索引），数据量小，无需缓存
- `file-detail` 接口的 `duplicationBlockCount` 查询：用 `COUNT(DISTINCT group_id)` 子查询，避免 N+1

### 7.4 前端性能

- monaco-editor 懒加载（已有）
- 大文件（> 5000 行）分段渲染（monaco-editor 原生支持）
- 高亮 decoration 用 `deltaDecorations` 增量更新，避免全量重渲染
- drawer 内 monaco-editor 只渲染出现位置代码片段（不加载完整文件），性能可控
- tab 数量过多（> 8）时横向滚动，避免布局挤压

## 8. 前端实现

### 8.1 新增路由

`openlibing-web/apps/web-openlibing/src/router` 新增：
```
/repos/duplication-code-view?repoId=&branchName=&pipelineRunId=&filePath=&runNumber=&pipelineLink=
```

### 8.2 新增页面 `DuplicationCodeView.vue`

路径：`openlibing-web/apps/web-openlibing/src/views/Repos/dialog/DuplicationCodeView.vue`

**布局（初始状态 — 右侧 50% 侧边页，无 drawer）**：
```
┌──────────────────────────────────────────────────────────────────────────┐
│  ← 返回列表   代码仓: xxx  分支: xxx  流水线: #xxx                         │
├──────────────────────────────────────────────────────────────────────────┤
│  ⚠ 该记录无代码快照                 (仅 hasSnapshot=false 时显示)      │
├──────────────────────────────────────────────────────────────────────────┤
│  hasSnapshot=true 时:                                                    │
│  monaco-editor (上下文片段拼接代码 + ...占位)                             │
│  [高亮块 1 ▶N] ← 点击高亮块或指示器                                        │
│  [高亮块 2 ▶N]                                                           │
│  ↑ 上一个  ↓ 下一个  ⤢ 放大                                              │
│                                                                          │
│  hasSnapshot=false 时:                                                   │
│  重复块列表 (点击→全屏+drawer)                                            │
│  · Foo:10-40 (3 个位置)                                                  │
│  · Foo:80-110 (3 个位置)                                                 │
└──────────────────────────────────────────────────────────────────────────┘
```

**布局（点击代码块后 — 全屏 + drawer）**：
```
┌──────────────────────────────────────────┬───────────────────────────────┐
│  源文件                                  │  重复代码块 (N-1 个位置)        │
│  ↑ 上一个  ↓ 下一个  ⤈ 缩小             │  ┌──────────┬──────────────┐  │
│                                          │  │Foo:80-95 │Bar:5-22      │  │
│  monaco-editor (上下文片段拼接代码)       │  │ [同文件] │ 当前*        │  │
│  [高亮块 1]                              │  └──────────┴──────────────┘  │
│  [高亮块 2 ◀── 当前选中]                 │  monaco-editor               │
│                                          │  (当前 tab 代码片段+上下文)    │
│                                          │                               │
│                                          │  ← 上一个  1/(N-1)  下一个 → │
└──────────────────────────────────────────┴───────────────────────────────┘
```

**核心逻辑**：
1. `onMounted` → 调 `file-content` 接口 → 拿到 `content` + `duplicationBlocks`（含 groupId）+ `hasSnapshot` + `lineMapping`
2. 初始状态：源文件以右侧 50% 侧边页打开，drawer 关闭
3. `hasSnapshot=true` → monaco-editor `onMount` → 用 `lineMapping` 把每个 block 的原始 `startLine/endLine` 转换为展示行号 → `deltaDecorations` 高亮 `[displayStart-1, displayEnd-1]` 行范围（淡黄底）→ 每个重复块起始行添加可点击指示器 `▶ N 个位置`
4. `hasSnapshot=false` → 左侧隐藏 monaco-editor，展示"该记录无代码快照"占位 + 重复块列表（`duplicationBlocks` 渲染为可点击行）；用户点击列表项 → 同 step 5 进入全屏+drawer
5. 点击高亮块或指示器（hasSnapshot=true）→ 页面展开为全屏 + 打开 drawer → 记录 `currentBlockId` → 用 `block.groupId` 调 `duplication-block/detail` → drawer 展示多页签（不含来源 tab）
6. drawer 内 tab 切换 → 切换 `activeTabIndex` → monaco-editor 重新渲染对应出现位置代码片段（含上下文行，重复块部分高亮）
7. drawer 内"上一个/下一个" → 切换当前 blockIndex →（hasSnapshot=true 时）用 `lineMapping` 转换 `block.startLine` 为展示行号 → monaco-editor `revealLineInCenter(displayLine)` + drawer 用新 groupId 重新调 `duplication-block/detail`
8. 放大/缩小与 drawer 联动：
   - 点击"缩小"按钮 → 恢复为右侧 50% 侧边页 + 关闭 drawer
   - 点击"放大"按钮 → 展开为全屏 + 重新打开 drawer（展示当前选中块的重复位置）

**高亮样式**：
- 普通重复块：`background: rgba(255, 235, 59, 0.15)`（淡黄底）
- 当前选中块：`background: rgba(255, 152, 0, 0.30)`（深橙底）+ `border-left: 3px solid #ff9800`
- 重复块指示器：`▶ N 个位置`（淡橙色背景，点击触发 selectBlock）

### 8.3 新增组件 `DuplicationBlockDrawer.vue`（多页签）

路径：`openlibing-web/apps/web-openlibing/src/views/Repos/dialog/DuplicationBlockDrawer.vue`

**props**：`groupId`, `visible`, `currentBlockId`（用于过滤来源 tab）
**emit**：`close`, `prev`, `next`, `resize`

内部状态：
- `detail`：从 `duplication-block/detail` 接口拿到的 `DuplicationBlockVO`
- `activeTabIndex`：默认选中第一个（即第一个非来源位置）
- `nonSourceOccurrences`：过滤掉 `currentBlockId` 对应的出现位置后的列表

布局：
```
┌─────────────────────────────────────────────────┐
│  重复代码块 (N-1 个位置)                         │
│  ┌──────────────┬──────────────┐                │
│  │Foo:80-95     │Bar:5-22      │  ← tabs        │
│  │ [同文件]     │ 当前*        │                │
│  └──────────────┴──────────────┘                │
│  ─────────────────────────────────────────────  │
│  monaco-editor (当前 tab 代码片段+上下文, 只读)   │
│  ─────────────────────────────────────────────  │
│  ← 上一个  下一个 →                              │
└─────────────────────────────────────────────────┘
```

- tab 标签：`basename(filePath) + ':' + startLine + '-' + endLine`
- **不展示来源 tab**：当前点击位置（`currentBlockId` 匹配的 occurrence）不出现在 tab 列表中，因为主视图左侧已展示
- **同文件其他位置**的 tab 额外显示"同文件"蓝色 badge（如 `Foo:80-95 [同文件]`），便于区分同文件内重复和跨文件重复
- 当前展示位置（`activeTabIndex`）标记"当前"橙色 badge
- tab 数量 > 8 时横向滚动
- 点击 tab → 切换 `activeTabIndex` → monaco-editor 重新渲染对应 occurrence 的 content（含上下文行，重复块部分高亮）
- drawer 标题显示位置数 = 非来源位置数

### 8.4 `MetricsDetailDialog.vue` 改造

[MetricsDetailDialog.vue:91-95](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/views/Repos/dialog/MetricsDetailDialog.vue#L91-L95) 的 metricType=3 列配置改为：
```js
'3': [
  filePathColumn,  // 改为可点击：点击跳转到 DuplicationCodeView
  { prop: 'duplicationRate', label: '重复率', ... },
  { prop: 'duplicationLineCount', label: '重复行数', ... },
  { prop: 'duplicationBlockCount', label: '重复块数', ... },  // 新增列，值=重复组数（COUNT(DISTINCT group_id)，含同文件内重复组）
],
```

`filePath` 列 cell 渲染改为 `<a @click="goToCodeView(row)">{{ row.filePath }}</a>`，`goToCodeView` 用 `router.push` 跳转。

### 8.5 API 新增

`openlibing-web/apps/web-openlibing/src/api/Repos/url.ts` 新增：
```ts
export const FILE_CONTENT = CODE_REPO + '/metrics/code/file-content';
export const DUPLICATION_BLOCK_DETAIL = CODE_REPO + '/metrics/code/duplication-block/detail';
```

`api.ts` 新增：
```ts
export const fileContent: RequestFunc = (a, s) => apiClient.post(urls.FILE_CONTENT, a, s);
export const duplicationBlockDetail: RequestFunc = (a, s) => apiClient.post(urls.DUPLICATION_BLOCK_DETAIL, a, s);
```

## 9. 风险与缓解

| 风险 | 影响 | 缓解 |
|------|------|------|
| 上报体量过大导致 APIG 网关 413 | 插件扫描失败 | 分批上报（每批 ≤ 5000 出现位置 / ≤ 10MB）；上下文片段体积小（仅重复块±5行），不再以文件大小跳过 |
| DB 膨胀（重复块 + 上下文片段长期保留） | 查询变慢、存储成本上升 | 上下文片段仅存重复块±5行（大文件省 90%+）；重复块表加合理索引；监控表大小告警；如需清理可按 `code_metrics_record.create_time` 统一清理过期 record 及其关联表 |
| 旧 record 无 `snapshot_data`（本需求上线前已扫描的数据） | 用户查看历史扫描结果时上下文片段代码不可看 | **不走 Git API 降级**（避免行号错位误导）；左侧提示"该记录无代码快照" + 重复块列表；重复块代码片段（duplication_block 表，长期保留）仍可在 drawer 查看 |
| Base64 不是真正加密，DBA 可解码 | 源代码泄露给 DBA | 当前与 codecheck 一致，已 review 通过；上下文片段仅含重复块±5行，即使解码也无法还原完整文件；若合规升级，工具类内部可换 AES，上层透明 |
| 同一重复块在 N 个位置出现导致重复块表数据膨胀 | 数据冗余 | "出现位置"表设计，N 个位置存 N 行（而非 N×(N-1)/2 对），存储更省；可接受 |
| 旧插件上报的数据无 `duplicationOccurrences` | 前端展示不一致 | 详情接口返回 `duplicationBlockCount=0` + `hasSnapshot=false`，前端隐藏"查看代码"入口 |
| monaco-editor 大文件渲染卡顿 | 前端体验差 | 限制单文件 ≤ 5000 行渲染；超过则提示"文件过大，建议本地查看" |
| drawer 多页签数量过多（> 8） | 前端布局挤压 | tab 横向滚动；tab 标签用 basename + 行号区间，简短可读 |

## 10. 跨仓影响

| 仓 | 接口/契约变化 | 兼容性 |
|----|------|------|
| `openlibing-cicd-test-new` | 插件输出新增字段 | 旧版后端忽略新字段，兼容 |
| `openlibing-coderepo-fork` | 上报接口接收新字段、详情接口新增字段、新增 2 个查询接口 + 1 个分批上报接口 | 旧插件不传新字段时降级展示，兼容 |
| `openlibing-web` | 新增页面 + 路由 + API | 旧后端不返回 `duplicationBlockCount` 时，前端列展示 '--'，兼容 |

## 11. 实施分阶段

详见 [tasks.md](./tasks.md)。建议按"插件 → 后端 DB → 后端接口 → 前端"顺序，每阶段独立可验证：
- 阶段 1：后端 DB schema + Entity/Mapper（可独立测试入库）
- 阶段 2：后端上报接口扩展（用 Postman 模拟插件上报，验证入库）
- 阶段 3：插件改造（本地跑插件，验证上报到测试环境）
- 阶段 4：后端查询接口（含 Base64 解码）
- 阶段 5：前端文件代码视图 + 高亮
- 阶段 6：前端 drawer + 上下跳转 + 缩放
- 阶段 7：联调 + 验收

## 12. 关键文件清单（实施时涉及）

### 12.1 `openlibing-cicd-test-new`
- [code-metrics-action/dist/detectors/DuplicationDetector.js](file:///d:/Develop/Java/openlibing-cicd-test-new/.gitcode/actions/code-metrics-action/dist/detectors/DuplicationDetector.js) - 改造算法提取重复块
- [code-metrics-action/dist/uploaders/CoderepoUploader.js](file:///d:/Develop/Java/openlibing-cicd-test-new/.gitcode/actions/code-metrics-action/dist/uploaders/CoderepoUploader.js) - Base64 编码 + 分批上报
- `code-metrics-action/dist/utils/fileCollector.js` - 新增文件内容读取辅助

### 12.2 `openlibing-coderepo-fork`
- 新增 `src/main/resources/db/changelog/v1.0.0/code-metrics-duplication-code-view.xml` - 一张新表（`code_metrics_duplication_block`，无 git_url/branch_name 列，含 `idx_record_group`/`idx_record_file`/`uk_record_group_file_start`）+ `code_metrics_file_detail` 新增 `snapshot_data` 字段 + 新增 `idx_record_file` 索引 + `code_metrics_record` 新增 `uk_git_branch_run` 唯一索引（**repository 列保留不 drop**，仅 DTO/Entity 移除）
- 新增 `entity/metrics/CodeMetricsDuplicationBlockEntity.java`
- 改 [CodeMetricsFileDetailEntity.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/metrics/CodeMetricsFileDetailEntity.java) - 新增 `snapshotData` 字段
- 改 [CodeMetricsRecordEntity.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/metrics/CodeMetricsRecordEntity.java) - 移除 `repository` 字段（DB 列保留不 drop）
- 改 [CodeMetricsRecordMapper.xml](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/resources/mapper/CodeMetricsRecordMapper.xml) - resultMap 和 SELECT 移除 `repository` 列
- 新增 `mapper/CodeMetricsDuplicationBlockMapper.java` + xml
- 新增 `common/utils/security/CodeContentB64Util.java`
- 新增 `dto/metrics/DuplicationBlockQueryDTO.java`（groupId/repoId/branchName/pipelineRunId/sourceBlockId）、`DuplicationBlockBatchDTO.java`（recordId/blocks）、`FileContentViewQueryDTO.java`
- 新增 `vo/DuplicationBlockVO.java`（Occurrence 含 blockId(String)/contentStartLine/contentEndLine）、`FileContentViewVO.java`（segments 结构）
- 改 [CodeMetricsReportDTO.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/dto/metrics/CodeMetricsReportDTO.java) - 新增 `DuplicationOccurrenceDTO` + `duplicationOccurrences` 字段；`FileDetailDTO` 新增 `snapshotData`；**移除 `repository` 字段**；`IdenticalFileDetailDTO` **移除 `filePath`**（只保留 `duplicatedFiles`）；**移除 `FileSnapshotDTO` 和 `fileSnapshots`**
- 改 [FileMetricDetailVO.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/vo/FileMetricDetailVO.java) - `DuplicationRateItem` 新增 `totalLines`、`duplicationBlockCount`、`hasSnapshot`
- 改 [CodeMetricsServiceImpl.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/CodeMetricsServiceImpl.java) - 新增 `saveDuplicationBlocks` / `saveDuplicationBlocksBatch` / `getFileContent` / `getDuplicationBlockDetail`（含 sourceBlockId 交集定位）；**不再实现 `saveFileSnapshots`**（快照随 `saveFileDetails` 入库）；`reportMetrics` 返回 String；`saveCodeMetricsRecord` 移除 `repository` 设置；`buildPipelineLink` 改为从 `gitUrl` 提取 owner/repo；`saveIdenticalFileDetails` 适配无 `filePath`；`appendFileDuplicationItems` 适配新结构
- 改 [CodeMetricsController.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/CodeMetricsController.java) - 新增 2 个查询接口 endpoint（file-content、duplication-block/detail）+ 1 个分批上报接口 endpoint（duplication-blocks）
- **不修改 [XxlJobHandler.java](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java)** - 本需求移除 TTL 清理逻辑，不新增定时任务

### 12.3 `openlibing-web`
- 新增 `src/views/Repos/dialog/DuplicationCodeView.vue`
- 新增 `src/views/Repos/dialog/DuplicationBlockDrawer.vue`
- 改 [src/api/Repos/url.ts](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/api/Repos/url.ts) - 新增 2 个 URL
- 改 `src/api/Repos/api.ts` - 新增 2 个 api 函数
- 改 [src/views/Repos/dialog/MetricsDetailDialog.vue](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/views/Repos/dialog/MetricsDetailDialog.vue) - metricType=3 文件路径列改为可点击 + 新增"重复块数"列
- 改 `src/router` - 新增路由
