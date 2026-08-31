# proposal: code_metrics_record 新增 6 个总体指标字段

- **业务 Issue**: https://gitcode.com/openlibing/code-metrics-action/issues/4
- **涉及仓库**: code-metrics-action（数据生产侧）、openlibing-coderepo（存储/查询侧）
- **流程模式**: Standard
- **日期**: 2026-08-20

## 1. 需求背景

当前 `code_metrics_record.metrics_data_json` 仅有 5 个总体指标（codeScale / avgFunctionLoc / avgCyclomaticComplexity / totalCodeDuplicationRate / totalFileDuplicationRate），缺少总行数、注释行数、复杂度总量、重复块数量等量化视角，无法支撑"代码规模全貌"与"注释率"等看板维度。

## 2. 新增字段与口径

### 2.1 记录级指标（code_metrics_record.metrics_data_json，6 个）

| # | 字段 | 口径 | 插件端取数逻辑 | 服务端查询侧出口 |
|---|------|------|---------------|-----------------|
| 1 | `codeLineTotal` | 扫描代码总行数 = 代码 + 注释 + 空行的物理总行数 | SlocDetector 解析 scc 汇总输出的 `Lines` 字段（内部名 `rawLines`），现成数据，formatForReport 白名单直接透传 | `BranchMetricsVO.codeLineTotal` |
| 2 | `commentLines` | 注释行数 = 扫描范围内所有文件注释行数总和（**直接取 sloc 的 scc 汇总 commentLines**） | SlocDetector 现成的 `commentLines`（scc 汇总 totalComment），formatForReport 白名单直接透传，不累加明细。每文件 commentLines 明细仍随 fileDetails 落 file_detail 供文件级下钻（见 2.2） | `BranchMetricsVO.commentLines` |
| 3 | `complexityCount` | 函数圈复杂度总和（方法维度总量，与 avgCyclomaticComplexity 同源） | LizardDetector 的 `totalCC`（Σ 所有函数 CCN）——原本已计算但被 formatForReport 白名单丢弃，现在透传 | `BranchMetricsVO.complexityCount` |
| 4 | `cyclomaticComplexityPerFile` | 文件维度圈复杂度 = Σ函数圈复杂度 ÷ **含函数的文件数**（区别于方法维度 avgCyclomaticComplexity） | LizardDetector **新增计算**：`totalCC / fileDetails.length`，`toFixed(2)` 保留 2 位小数；无函数文件/空结果时为 0 | `BranchMetricsVO.cyclomaticComplexityPerFile` |
| 5 | `duplicatedBlocks` | 重复代码块数量 = 重复块**出现位置总数**（同一内容在 3 个文件中出现计 3，与 duplication_block 表行数一致） | DuplicationDetector **新增**：`duplicationOccurrences.length`；getEmptyResult 补 0 | `BranchMetricsVO.duplicatedBlocks` |
| 6 | `duplicatedLines` | 重复代码行数量 = Σ 每文件重复行数（totalCodeDuplicationRate 的分子） | DuplicationDetector 现成的 `duplicatedLines`——原被白名单丢弃，现在透传 | `BranchMetricsVO.duplicatedLines` |

### 2.2 文件级明细（code_metrics_file_detail.metrics_json，1 个）

| 字段 | 口径 | 插件端取数逻辑（SlocDetector 三条路径） | 服务端处理 |
|------|------|--------------------------------------|-----------|
| `commentLines`（每文件） | 单文件注释行数 | ① **scc --by-file 正常路径**：取 scc 每文件 `Comment` 字段（精确口径）<br>② **scc fallback 路径**（--by-file 输出为空重新收集文件）：启发式计数——非空且以 `//` `/*` `*` `#` 开头计为注释行<br>③ **全量 fallback**（scc 二进制不可用）：块注释状态机（`/* */` 跨行追踪 + `//` 单行），按文件累计 | `FileDetailDTO.commentLines` → `buildFileMetricsJson` 写入 metrics_json（null → 0） |

明细合并规则（MetricsCalculator.mergeFileDetails）：sloc 基底文件取明细值；lizard-only / duplication-only 文件补 `commentLines: 0`。

### 口径决策记录（用户确认）

- `complexityCount`：采用 lizard 函数圈复杂度总和（否决 scc Complexity 自有算法口径、函数总数量）
- `cyclomaticComplexityPerFile`：分母为含函数的文件数（否决全部扫描文件数）
- `duplicatedBlocks`：按出现位置总数计（否决重复内容组数）

### 说明

6 个新字段中仅 `commentLines` 有文件级明细语义（故 file_detail 只新增这一个键）；其余 5 个为记录级总量指标，仅存在于 `metrics_data_json`，通过分支查询接口统一返回。

## 3. 验收标准

1. 插件扫描上报后，`code_metrics_record.metrics_data_json` 含全部 6 个新字段，取值符合上表口径
2. `code_metrics_file_detail.metrics_json` 新增每文件 `commentLines`（供文件级下钻）；记录级 `commentLines` 直接取 scc 汇总值，与明细独立
3. `getLatestMetricsByGitUrl` 返回的 `BranchMetricsVO` 含 6 个新字段（MetricItemVO：value + pipelineRunId，支持跨流水线补齐）
4. 历史数据无新字段时查询返回 null（跨 record 补齐语义与其他指标一致）
5. 检测器禁用 / 空结果场景下新字段优雅降级为 0，不报错
6. 跨 record 指标补齐在旧 5 指标齐备后仍能继续补齐新 6 指标（MAX_METRIC_KEYS 同步扩容，有回归测试覆盖）
7. 插件冒烟测试（12 项）与服务端单测（25 项）全部通过

## 4. 非目标

- 不改 action.yml inputs/outputs（新字段仅进入上报 payload 与本地 metrics.json，不作为 action output）
- 不改 openlibing-coderepo 入库主链路协议（metricsData 为 Map 透传，JSON 列自动吸收）
- 前端展示适配不在本次范围（服务端返回字段即视为可消费）
