# 代码重复率详情 - 展示具体重复代码（归档）

> 归档时间：2026-08-12
>
> 关联业务 Issue：[openlibing/openlibing-coderepo#89](https://gitcode.com/openlibing/openlibing-coderepo/issues/89)
>
> 关联业务 PR：[openlibing/openlibing-coderepo!136](https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/136)（`code-metrics-duplication-code-view → release_20260813_iter1`）
>
> 配套文档：[proposal.md](./proposal.md) + [design.md](./design.md) + [requirement-design.md](./requirement-design.md) + [tasks.md](./tasks.md)

## 1. 交付历程

本需求为跨仓 Full 模式，涉及插件、后端 + DB、前端三个仓。整体流程：需求确认 → 后端 DB Schema/Entity/Mapper → 后端上报接口扩展 → 插件改造 → 后端查询接口 → 前端文件代码视图 + 高亮 → 前端 drawer 多页签 + 上下跳转 + 缩放 → 联调验收 → 归档。

关键演进点：

1. **数据模型从"配对对"演进为"出现位置"**：最初设想按 source/target 配对存储，实现中改为"出现位置"表——同一代码内容的所有出现位置归为同一 `group_id`，每个位置一行。干净支撑"一块对多位置（含同文件多位置）"，前端 drawer 多页签直接映射 `occurrence_index`。
2. **代码缓存策略定稿为方案 D**：只存重复块 ±5 行上下文片段快照（非完整文件），存入 `code_metrics_file_detail.snapshot_data`，无 TTL 长期保留；重复块本身存 `code_metrics_duplication_block` 表。快照未命中（旧 record）不走 Git API 降级，避免行号错位误导用户。
3. **前端展示由 lineMapping 演进为 segments**：`file-content` 接口从"拼接展示串 + lineMapping"改为直接返回 `segments`（含 `originalStartLine`/`originalEndLine`/`content` 明文），省略行占位由前端按相邻片段行号差计算，后端不再维护 lineMapping。
4. **`sourceBlockId` 交集定位**：同组各 occurrence 行数可能不同（union-find 分组），以其对应代码块内容为基准，在其他 occurrence 的 block content 中定位匹配子区间（取交集），使前端精确高亮"真正重复"的部分。
5. **recordId 改 String 返回**：避免雪花 ID 在 JS 侧 Number 精度溢出 2^53，`reportMetrics` 返回 `DataResult<String>`。
6. **新增分批上报接口** `POST /metrics/code/duplication-blocks`：插件 `duplicationOccurrences` 超单批 5000 时，首批随主报告上报、后续批次走此接口，控制单请求体量。
7. **幂等加固**：`code_metrics_record` 新增唯一索引 `uk_git_branch_run(git_url, branch_name, pipeline_run_id)`；`code_metrics_duplication_block` 唯一键 `uk_record_group_file_start` 防插件网络重试重复入库。

## 2. 设计偏差与实现说明

> 详细偏差见 [design.md §首部](./design.md) 与 [requirement-design.md §首部](./requirement-design.md) 的"实现偏差说明"。核心偏差：

- `reportMetrics` 返回类型 `DataResult<Long>` → `DataResult<String>`（recordId 用 String，防 JS 精度溢出）。
- 新增独立分批上报接口 `/metrics/code/duplication-blocks`（`DuplicationBlockBatchDTO` + `saveDuplicationBlocksBatch`）。
- `file-content` 改为返回 `segments` 结构（不再返回 `content` + `lineMapping`）。
- `duplication-block/detail` 请求新增 `branchName`/`pipelineRunId`/`sourceBlockId`，`Occurrence` 新增 `contentStartLine`/`contentEndLine`。
- DB：`code_metrics_duplication_block` 无 `git_url`/`branch_name` 列；`code_metrics_file_detail` 新增 `idx_record_file`；`code_metrics_record` 新增唯一索引 `uk_git_branch_run`。
- `repository` 字段仅 DTO/Entity 移除，DB 列保留不 drop（便于回滚）。

## 3. 可复用经验

> 仅沉淀经过验证、未来会复用的通用结论；一次性实现细节不入 ai_memory。

1. **雪花 ID 跨前后端传参用 String**：Snowflake 主键超过 JS Number 安全整数（2^53），后端返回给前端时统一以 String 传输，前端不丢失精度。本需求 `recordId`/`blockId` 均按此处理。
2. **代码内容入库前 Base64 + 出库两阶段回检验证**：入库前编码（防明文进日志/DBA 一眼可见），出库前做 `Base64.isBase64` 快速过滤 + "解码→重编码→比对"回检验证，防止"pass"/"return"等纯字母明文被误判为已编码。工具类在本仓内独立实现，不跨仓依赖（避免服务间耦合）。
3. **重复块按"出现位置"存储而非"配对对"**：一个 N 位置重复块存 N 行（而非 N×(N-1)/2 对），存储更省，且天然支撑"一块对多位置（含同文件多位置）"。
4. **快照未命中不做降级拉取**：历史扫描结果的行号是扫描时点快照，拉取最新代码会导致行号错位、高亮指错位置，"看似能看实则错位"的误导比"提示无快照"更差——宁可提示"该记录无代码快照"。
5. **批量上报新增独立接口而非复用主接口**：超大批量数据分批时，单独 `duplication-blocks` 接口按 `recordId` 累积入库，避免对主 `/report` 接口重复执行幂等删除逻辑。

## 4. 遗留事项

- `openlibing-web` 前端仓的改动在独立分支/PR 交付，本 spec 仅记录契约。
- 插件仓 `code-metrics-scan` 的改动已同步到 `code-metrics-action` 仓（`duplication-rate-view` 分支，commit `472015c`），含"重复率有效代码行口径与 scc 完全一致"修复。
- 后续如需清理历史数据，可按 `code_metrics_record.create_time` 统一清理过期 record 及其关联的 file_detail / duplication_block（本期不做，无 TTL）。
