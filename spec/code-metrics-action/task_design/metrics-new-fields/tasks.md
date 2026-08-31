# tasks: code_metrics_record 新增 6 个总体指标字段

- **业务 Issue**: https://gitcode.com/openlibing/code-metrics-action/issues/4

## 准备

- [x] 创建业务 Issue（openlibing/code-metrics-action#4）并更新 6 字段口径清单
- [x] 确认 3 个歧义字段口径（complexityCount / cyclomaticComplexityPerFile / duplicatedBlocks）
- [x] code-metrics-action 建分支 `feat-add-codeline-total`（基于 origin/master）
- [x] openlibing-coderepo 建分支 `feat-metrics-codeline-total`（基于主仓 prod/master）

## 插件侧（code-metrics-action）

- [x] SlocDetector：scc --by-file 路径每文件 commentLines（file.Comment）
- [x] SlocDetector：scc fallback 路径每文件 commentLines（注释启发式）
- [x] SlocDetector：fallbackDetect（scc 不可用）每文件 commentLines（块注释状态机）
- [x] LizardDetector：detect 返回 cyclomaticComplexityPerFile（totalCC ÷ 含函数文件数）
- [x] LizardDetector：getEmptyResult 补 cyclomaticComplexityPerFile=0
- [x] DuplicationDetector：detect 返回 duplicatedBlocks（occurrences 总数）
- [x] DuplicationDetector：getEmptyResult 补 duplicatedBlocks=0
- [x] MetricsCalculator：mergeFileDetails 三处合并 commentLines（sloc 基 / lizard-only 补 0 / duplication-only 补 0）
- [x] MetricsCalculator：formatForReport 白名单 +6 字段（commentLines 记录级直接取 scc 汇总）
- [x] dist/index.js bundle 内联副本同步（4 模块全部）
- [x] README 指标口径补充（功能表 + 指标说明 6 条）
- [x] 新增 test/smoke-test.js（12 项断言）+ package.json test 脚本

## 服务端侧（openlibing-coderepo）

- [x] FileDetailDTO 新增 `Integer commentLines`
- [x] buildFileMetricsJson 新增 commentLines（null → 0）
- [x] MAX_METRIC_KEYS 5 → 11
- [x] buildMetricKeyList 增加 6 个 key
- [x] buildMergedMetricsVO builder 增加 6 个字段
- [x] BranchMetricsVO 增加 6 个 MetricItemVO 字段
- [x] 单测扩展：reportMetrics file_detail 明细 commentLines 断言
- [x] 单测扩展：getLatestMetricsByGitUrl 单 record 11 指标透传断言
- [x] 单测扩展：跨 record 新旧指标合并（MAX_METRIC_KEYS 回归覆盖）

## 源码仓同步（code-metrics-scan，分支 feat-add-codeline-total）

- [x] 建分支 `feat-add-codeline-total`（基于 origin/main）
- [x] SlocDetector：与 action 仓基线相同，直接移植每文件 commentLines ×3 路径
- [x] LizardDetector：detect + getEmptyResult 新增 cyclomaticComplexityPerFile
- [x] DuplicationDetector：duplicatedBlocks 架构映射实现（Σ每文件连续重复行区间数）
- [x] DuplicationDetector：新增 countBlocksFromLineSets / countBlocksFromClones 辅助方法 + getEmptyResult 补 0
- [x] MetricsCalculator：mergeFileDetails 三分支 commentLines + formatForReport 白名单 +6 字段（commentLines 取 scc 汇总，与 action 仓同口径）
- [x] README 功能表 +6 指标；package.json 加 test 脚本
- [x] 新增 test/smoke-test.js（15 项断言，含块计数辅助方法 3 项专项单测）
- [x] 说明：scan 仓 dist/index.js 是源码入口而非 ncc bundle（构建打包在发布到 action 仓时进行），无 bundle 双写

## commitId 上报（后续追加；最终口径：插件发送 + 服务端已解析入库）

> 口径修订：最初用户决策「仅插件发送，服务端暂不入库」；后随 coderepo 机机接口需求（openlibing-coderepo#159）落地，服务端已从 OBS 全量文件解析 `commitId` 并持久化到 `code_metrics_record.commit_id` 列（`readMetaField` case "commitId" → `CodeMetricsPayload` → `saveCodeMetricsRecord`），详见 coderepo 仓 spec `openlibing-coderepo/task_design/code-metrics-machine-api-query` §5。

- [x] 口径确认：`commitId = process.env['ATOMGIT_SHA'] || ''`，与 CodeQL（openlibing-upload-sarif）同源
- [x] code-metrics-action：dist/index.js 入口读 ATOMGIT_SHA + 日志 + scan options
- [x] code-metrics-action：dist/index.js 内联 scanner（成功/失败两路径）+ 内联 uploader（fullPayload + /report payload）副本同步
- [x] code-metrics-action：dist/scanner.js 两条上报路径透传 commitId
- [x] code-metrics-action：dist/uploaders/CoderepoUploader.js payload 加 commitId
- [x] code-metrics-scan：dist/index.js（入口 + 内联副本）、dist/scanner.js、dist/uploaders/CoderepoUploader.js 同步双写（旧直传协议，单 payload 加字段）
- [x] 两仓 test/smoke-test.js 各 +2 项 commitId 用例（stub 上传链路）
- [x] 服务端落库（随 openlibing-coderepo#159）：`commit_id` 列（Liquibase 幂等）+ `readMetaField` 解析 OBS JSON 入库，作为 `/latest-by-commit/batch` 三元组关联键

## 验证

- [x] 插件冒烟（action 仓）：`npm test` → 12/12 通过
- [x] bundle 语法与双写一致性校验通过
- [x] 服务端单测：`mvn test -Dtest=CodeMetricsServiceImplTest` → 25/25 通过
- [x] 源码仓冒烟（scan 仓）：`npm test` → 15/15 通过
- [x] 插件冒烟（action 仓，含 commitId）：`node test/smoke-test.js` → 16/16 通过
- [x] 源码仓冒烟（scan 仓，含 commitId）：`node test/smoke-test.js` → 17/17 通过

## 待办（等待用户审查后）

- [ ] 用户审查代码（当前未 commit）
- [ ] 三仓 commit（code-metrics-action + openlibing-coderepo + code-metrics-scan，Conventional Commits 规范）
- [ ] 用户自测
- [ ] 业务 PR（三仓，关联 Issue #4，打 `ai-assisted` 标签）
- [ ] docs PR 归档本 spec 三件套
