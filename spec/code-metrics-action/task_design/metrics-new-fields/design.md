# design: code_metrics_record 新增 6 个总体指标字段

- **业务 Issue**: https://gitcode.com/openlibing/code-metrics-action/issues/4
- **分支**: code-metrics-action `feat-add-codeline-total` / openlibing-coderepo `feat-metrics-codeline-total`（均基于主仓 master）

## 1. 数据流与改动点

```
SlocDetector ──(新增每文件 commentLines ×3 路径；rawLines 现成)──┐
LizardDetector ──(新增 cyclomaticComplexityPerFile；totalCC 现成)──┤
DuplicationDetector ──(新增 duplicatedBlocks；duplicatedLines 现成)─┤
                                                                   ▼
MetricsCalculator.mergeFileDetails（合并每文件 commentLines，lizard-only/duplication-only 补 0）
MetricsCalculator.formatForReport（白名单 5 → 11 个总体指标；commentLines 记录级直接取 scc 汇总）
                                                                   ▼
CoderepoUploader（无需改动：metricsData Map 透传）→ APIG → /metrics/code/report
                                                                   ▼
openlibing-coderepo 入库（metrics_data_json JSON 列自动吸收；file_detail 明细新增 commentLines）
                                                                   ▼
查询侧 getLatestMetricsByGitUrl → buildMergedMetricsVO → BranchMetricsVO（+6 MetricItemVO）
```

### 1.1 关键设计决策

1. **记录级 commentLines 直接取 scc 汇总**：SlocDetector 现成返回 `commentLines`（scc 语言级汇总 totalComment），formatForReport 直接透传，不累加明细。每文件 commentLines 明细仍随 fileDetails 落 file_detail 供下钻；scc --by-file 正常路径下汇总与 Σ 明细同源一致，fallback 路径下以 scc 汇总为准。
2. **MAX_METRIC_KEYS 5 → 11**：跨 record 指标补齐循环在 `resolvedPrimaryKeys.size() >= MAX_METRIC_KEYS` 时提前 break。主键从 5 扩到 11，若不同步扩容，旧 5 指标齐备后新指标永远不会被补齐（有专项回归测试）。
3. **duplicatedBlocks = duplicationOccurrences.length**：与 `code_metrics_duplication_block` 表行数一致，前端下钻数据可直接对账。
4. **每文件 commentLines 双写进 file_detail**：FileDetailDTO + buildFileMetricsJson 新增字段，历史数据无该键时序列化为 0（null → 0 与既有字段风格一致）。

## 2. 字段取数逻辑对照表

> 口径定义详见 proposal.md 第 2 节；本节为技术实现视角的字段全链路对照。

### 2.1 记录级指标（code_metrics_record.metrics_data_json，6 个）

| #   | 字段                          | 插件端取数逻辑                                                                                      | 检测器              | 服务端查询侧出口                              |
| --- | ----------------------------- | --------------------------------------------------------------------------------------------------- | ------------------- | --------------------------------------------- |
| 1   | `codeLineTotal`               | scc 汇总输出 `Lines` 字段（内部名 `rawLines`），现成数据，formatForReport 白名单直接透传            | SlocDetector        | `BranchMetricsVO.codeLineTotal`               |
| 2   | `commentLines`                | formatForReport 直接透传 SlocDetector 现成的 `commentLines`（scc 汇总 totalComment），不累加明细    | SlocDetector        | `BranchMetricsVO.commentLines`                |
| 3   | `complexityCount`             | `totalCC`（Σ 所有函数 CCN），原已计算但被白名单丢弃，现透传                                         | LizardDetector      | `BranchMetricsVO.complexityCount`             |
| 4   | `cyclomaticComplexityPerFile` | **新增计算**：`totalCC / fileDetails.length`（含函数的文件数），`toFixed(2)`；无函数文件/空结果为 0 | LizardDetector      | `BranchMetricsVO.cyclomaticComplexityPerFile` |
| 5   | `duplicatedBlocks`            | **新增**：`duplicationOccurrences.length`（出现位置总数）；getEmptyResult 补 0                      | DuplicationDetector | `BranchMetricsVO.duplicatedBlocks`            |
| 6   | `duplicatedLines`             | 现成 `duplicatedLines`（Σ 每文件重复行数），原被白名单丢弃，现透传                                  | DuplicationDetector | `BranchMetricsVO.duplicatedLines`             |

### 2.2 文件级明细（code_metrics_file_detail.metrics_json，1 个）

| 字段                     | 插件端取数逻辑（SlocDetector 三条路径）                                                                                                                                                                                                                  | 服务端处理                                                                          |
| ------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `commentLines`（每文件） | ① scc --by-file 正常路径：取每文件 `Comment`（精确口径）<br>② scc fallback（--by-file 输出为空重新收集）：启发式——非空且以 `//` `/*` `*` `#` 开头计注释行<br>③ 全量 fallback（scc 二进制不可用）：块注释状态机（`/* */` 跨行追踪 + `//` 单行）按文件累计 | `FileDetailDTO.commentLines` → `buildFileMetricsJson` 写入 metrics_json（null → 0） |

明细合并（mergeFileDetails）：sloc 基底文件取明细值；lizard-only / duplication-only 文件补 0。

### 2.3 查询侧配套改动（记录级指标统一出口）

| 改动点                 | 位置（feat-metrics-codeline-total 分支） | 内容                                                                                              |
| ---------------------- | ---------------------------------------- | ------------------------------------------------------------------------------------------------- |
| `MAX_METRIC_KEYS`      | `CodeMetricsServiceImpl.java:72`         | 5 → 11（跨 record 指标补齐上限；不同步扩容则旧 5 指标齐备后新指标永远不会被补齐，有专项回归测试） |
| `buildMetricKeyList`   | `CodeMetricsServiceImpl.java:1188-1193`  | 新增 6 个 key，用于跨 record 补齐匹配                                                             |
| `buildMergedMetricsVO` | `CodeMetricsServiceImpl.java:1151-1156`  | builder 新增 6 个字段取值                                                                         |
| `BranchMetricsVO`      | `BranchMetricsVO.java:25-41`             | +6 个 `MetricItemVO`（value + pipelineRunId + 检测时间，与其他指标同构）                          |

**对外暴露链路**：`queryRepoBranchInfo`（POST 分支查询接口）→ `getLatestMetricsByGitUrl(repoUrl)` → `buildMergedMetricsVO` → `RepoBranchInfoVO.metrics`（按 branchName 匹配，无数据返回空结构体）。

### 2.4 字段层级说明

6 个新字段中仅 `commentLines` 有文件级明细语义（file_detail 只新增这一个键）；其余 5 个为记录级总量指标，仅存在于 `metrics_data_json`，通过分支查询接口统一返回——文件级明细查询（`/file-detail`）不涉及这 5 个字段属设计预期，并非遗漏。

## 3. 影响范围

### code-metrics-action（6 文件）

| 文件                                                | 改动                                                                                                        |
| --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `dist/detectors/SlocDetector.js`                    | 每文件 commentLines ×3 路径（--by-file 取 scc Comment；fallback 两条路径按各自注释启发式计数）              |
| `dist/detectors/LizardDetector.js`                  | detect 返回值 + getEmptyResult 新增 cyclomaticComplexityPerFile                                             |
| `dist/detectors/DuplicationDetector.js`             | detect 返回值 + getEmptyResult 新增 duplicatedBlocks                                                        |
| `dist/calculators/MetricsCalculator.js`             | mergeFileDetails 合并 commentLines（3 处）；formatForReport 白名单 +6 字段                                  |
| `dist/index.js`                                     | **bundle 内联副本同步**（运行时实际加载 dist/index.js，独立源码文件运行时为死代码；仓库既有"双写同步"惯例） |
| `README.md` / `package.json` / `test/smoke-test.js` | 指标口径文档、`npm test` 脚本、12 项冒烟断言                                                                |

### code-metrics-scan（源码仓同步，分支 feat-add-codeline-total）

插件源码仓（`.gitcode/actions/code-metrics-scan/`，纯源码形态——`dist/index.js` 是源码入口而非 ncc bundle，构建打包发生在发布到 action 仓时，故无 bundle 双写）：

| 文件                                                | 改动                                                                                                                                                                                                                                                                                                                                    |
| --------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `dist/detectors/SlocDetector.js`                    | 与 action 仓完全一致（基线相同，直接移植：每文件 commentLines ×3 路径）                                                                                                                                                                                                                                                                 |
| `dist/detectors/LizardDetector.js`                  | detect 返回值 + getEmptyResult 新增 cyclomaticComplexityPerFile（totalCC ÷ fileDetails.length，scan 的 fileDetails 仅含函数文件）                                                                                                                                                                                                       |
| `dist/detectors/DuplicationDetector.js`             | **架构映射实现**：scan 仓为 token 级滑动窗口 + jscpd fallback（无 occurrence 结构），duplicatedBlocks 改为 **Σ每文件连续重复行区间数**（出现位置总数口径的等价映射；区间内隔 1 行不拆分）。新增 `countBlocksFromLineSets`（token 主路径，从标记行集合分段）与 `countBlocksFromClones`（jscpd fallback，clone 两端区间合并）两个辅助方法 |
| `dist/calculators/MetricsCalculator.js`             | mergeFileDetails 三分支合并 commentLines；formatForReport 白名单 +6 字段（commentLines 取 scc 汇总，与 action 仓同口径）                                                                                                                                                                                                                |
| `README.md` / `package.json` / `test/smoke-test.js` | 功能表 +6 指标、`npm test` 脚本、15 项冒烟断言（含块计数辅助方法 3 项专项单测）                                                                                                                                                                                                                                                         |

### openlibing-coderepo（4 文件）

| 文件                              | 改动                                                                                                                                  |
| --------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| `CodeMetricsServiceImpl.java`     | `MAX_METRIC_KEYS` 11；`buildMetricKeyList` +6 key；`buildMergedMetricsVO` builder +6；`buildFileMetricsJson` +commentLines            |
| `CodeMetricsReportDTO.java`       | FileDetailDTO + `Integer commentLines`                                                                                                |
| `BranchMetricsVO.java`            | +6 个 `MetricItemVO` 字段（value + pipelineRunId，跨流水线补齐同构）                                                                  |
| `CodeMetricsServiceImplTest.java` | 3 处扩展：file_detail 明细 commentLines 断言（ArgumentCaptor）、单 record 11 指标透传、跨 record 新旧指标合并（MAX_METRIC_KEYS 回归） |

### 兼容性

- **存储**：`metrics_data_json` / `metrics_json` 均为 JSON 列，新字段自动吸收，无 schema 变更、无迁移
- **历史数据**：旧 record 无新字段 → 查询返回 null；旧 file_detail 无 commentLines 键 → 不影响
- **上报协议**：服务端 metricsData 为 `Map<String, Object>` 透传，旧版插件上报无新字段时入库行为不变；新版插件对旧版服务端上报，新字段被忽略（fastjson2 反序列化容错）
- **风险**：插件 dist v1.0.6 三段式上传需服务端 ≥ develop_202608_iter1（本改动不改变该既有约束）

## 4. 验证

- 插件：`npm test`（12 项冒烟断言：11 指标齐全 / commentLines Σ 口径 / lizard-only 补 0 / 禁用降级 0 / validate 原有必填仍生效）
- 服务端：`mvn test -Dtest=CodeMetricsServiceImplTest`（25 项，含 3 项新增/扩展断言）
- bundle 同步：grep 双写字段计数 + `node` 语法校验通过

## 5. commitId 上报元数据（后续追加）

### 5.1 口径定义

`commitId = process.env['ATOMGIT_SHA'] || ''`——GitCode/AtomGit Runner 注入的"触发工作流的提交 SHA"，**与 CodeQL 侧（openlibing-upload-sarif）的 commitId 完全同源**（同一环境变量、同一取值方式）。三种触发场景（push / workflow_dispatch / schedule）下该变量均存在，值分别为触发 commit / 所选分支 HEAD / 默认分支 HEAD；缺失时为空串，不阻断上报。

### 5.2 数据流

```
index.js 入口（读 ATOMGIT_SHA → core.info 日志 → scan options.commitId）
                                                                   ▼
scanner.js scan()（成功 / 失败两条上报路径均透传 options.commitId）
                                                                   ▼
CoderepoUploader.upload() payload 新增 commitId（与 pipelineRunId / runNumber 同级元数据）
  - action 仓：OBS 全量文件 fullPayload + /report 请求体两处都带
  - scan 仓：直传 /report payload（旧协议单 payload）
                                                                   ▼
openlibing-coderepo：暂不解析入库（用户决策"仅插件发送"），
fastjson2 反序列化忽略未知字段；后续要入库时从 OBS 文件 buildPayload 读取 commitId 即可，插件无需再发版
```

### 5.3 改动文件

| 仓库                | 文件                                                                                               | 改动                                                                                                                             |
| ------------------- | -------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------- |
| code-metrics-action | `dist/index.js`                                                                                    | 入口读 `ATOMGIT_SHA` + 日志 + scan options；内联 scanner（2 处上报路径）/ 内联 uploader（fullPayload + /report payload）副本同步 |
| code-metrics-action | `dist/scanner.js`                                                                                  | 成功 / 失败两条 uploader.upload 调用透传 `commitId: options.commitId`                                                            |
| code-metrics-action | `dist/uploaders/CoderepoUploader.js`                                                               | fullPayload（OBS 全量文件）与 /report 请求体各加 `commitId`                                                                      |
| code-metrics-scan   | `.gitcode/actions/code-metrics-scan/dist/{index,scanner}.js`、`dist/uploaders/CoderepoUploader.js` | 同步双写（scan 仓为旧版直传协议，仅 /report payload 一处加字段，按各自现有结构，不重构）                                         |
| 两仓                | `test/smoke-test.js`                                                                               | 各 +2 项 commitId 用例（stub 上传链路验证 payload 携带；缺失时优雅降级）                                                         |

### 5.4 兼容性

- 服务端 `CodeMetricsReportDTO` 未声明 commitId，fastjson2 忽略未知字段，旧版服务端行为不变
- OBS 全量文件多出的 commitId 键对保底定时任务补导入路径同样无影响（buildPayload 未读取）
- 后续服务端要持久化时：`CodeMetricsPayload` + `buildPayload()` 读取 `payload.getString("commitId")` → `CodeMetricsRecordEntity` 加 `commit_id` 列即可，数据源已在 OBS 文件中就绪
