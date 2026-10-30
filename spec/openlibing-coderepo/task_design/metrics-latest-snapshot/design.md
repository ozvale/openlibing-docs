# design: 代码度量分支表快照列（metrics-latest-snapshot）

## 1. 方案设计

将页面展示的 5 个度量指标（代码规模 / 平均代码行数 / 平均圈复杂度 / 总代码重复率 / 总文件重复率）落为 `repo_branch` 分支表冗余值列，对齐 UT 行覆盖率先例：

- **查询**：分支列表 SQL 直接带出值列，零拼接；度量排序下推 SQL `ORDER BY`，删除全量拉取 + 内存排序路径；
- **写入**：`reportMetrics` 主记录入库后同步刷列（最新成功快照），失败仅告警不阻断主链路；
- **刷数**：常驻 XxlJob 存量刷数，全量/定向两种模式，幂等可反复刷；刷数走**存量清洗补齐语义**（从新到旧先到先得），与写入侧"只看最新一条"职责分离；
- **保留**：`code_metrics_record` 与 `metrics_data_json` 原文不动（详情页、codecheck 机机接口继续使用）；
- **跳转**：不落来源 runId 列——度量详情接口 `locateMetricsRecord` 已支持"不传 `pipelineRunId` → 兜底取该分支最新一次成功记录"，与快照定义天然同源，前端传空 runId 行为已兼容（前端零改动）；重复块下钻与文件代码视图两个子下钻接口（`getDuplicationBlockDetail` / `getFileContent`）保持 `pipelineRunId` 必传不改动——master 前端 MetricsDetailDialog 已实现 file-detail 响应回填 runId 后再调子下钻接口，不会出现空 runId 请求（20261022 前端 master 代码核实）；
- **上线刷数**（建议项，非强约束）：补齐清洗语义下任何时刻刷数均为当时最新正确值，不存在数据丢失，择机触发即可；建议部署后尽快全量刷数缩短存量列漏显窗口（漏显，非错值），页面验证前先刷数可避免空列误判；新上报分支由写入链路自动自愈。

职责边界（写入/刷数分离）：**写入** = 本次快照，恒等于最新一次成功扫描（`status=0`，按 `detection_completed_at` 最新），不跨记录补齐，缺键写空、留待后续扫描自愈；**刷数** = 存量清洗，从新到旧遍历历史记录先到先得补齐缺键，与改造前页面展示语义完全等价。

## 2. 实现逻辑设计

### 2.1 写入（refreshBranchMetricsSnapshot）

`persistMetrics` 四遍解析完成、recordId 生成后：

1. `selectLatestByGitAndBranch(gitUrl, branchName)` 取最新一条 `status=0`（含刚插入的本条）；
2. 解析其 `metrics_data_json` 的 5 个指标值（变体键 `average*` 双键 fallback 兼容读取，仅此读取点做兼容；解析失败按缺键处理并 warn）；
3. `gitUrl → repoId`（repo_info 按 repo_url 反查，核对 URL 规范化口径）；
4. `UPDATE repo_branch SET 5 值列 WHERE repo_id=? AND branch_name=? AND branch_type='0'`；
5. 无匹配行（分支未录入）跳过；全程 try-catch，失败仅 warn 不阻断上报主链路。

失败记录（status=1）/部分成功（status=2）不刷列，保持上次成功快照。

### 2.2 查询

- **单仓** `queryRepoBranchInfo`：`queryByLimit` 实体直接带出 5 列 → 新增 `buildBranchMetricsVo(entity)`（照 `buildBranchUtCoverage` 模式），`MetricItemVO.value` 取列值、`pipelineRunId` 为 null；删除 `getLatestMetricsByGitUrl` 调用；
- **跨仓** `queryProjectBranch`：`queryProjectBranchByLimit` select 列增加 `b.code_scale` 等 5 列（既有 join，`ProjectBranchRowEntity` 加 5 字段）→ `buildProjectBranchInfoList` 从行实体构建；删除 `getLatestMetricsByGitUrls` 调用与 repoUrl 收集；
- **排序下推**：sortField（5 个度量字段）→ 白名单枚举映射分支表列名 → 注入 `projectBranchOrderBy`；删除 `isMetricSortField` 全量拉取、`sortProjectBranchByMetric`、`extractMetricSortValue`、`paginateProjectBranchList` 内存路径；
- **删除清单**：`selectLatestByGitUrls`（SQL+Mapper）、`getLatestMetricsByGitUrl(s)`（接口+实现）、`buildBranchMetricsMap` / `buildMergedMetricsVO` / `resolveMetricsFromRecord` / `MAX_METRIC_KEYS`；
- **保留**：`locateMetricsRecord`（详情兜底，已存在）、`selectByPipelineRunId`、`getLatestMetricsByCommitBatch`（codecheck 机机）、快照查询。

### 2.3 刷数任务（BranchMetricsSyncJob，XxlJob）

| jobParam            | 模式                                                                  |
| ------------------- | --------------------------------------------------------------------- |
| 空串                | 全量：遍历 `repo_branch`（branch_type='0'）join repo_info 取 repo_url |
| 仅 gitUrl           | 定向-整仓                                                             |
| gitUrl + branchName | 定向-单分支                                                           |

单分支处理 `backfillBranchMetricsHistory(gitUrl, branchName)`（存量清洗补齐语义）：倒序取该分支全部成功记录（`selectSuccessHistoryByGitAndBranch`，`detection_completed_at DESC`）→ 空则跳过 → 从新到旧遍历解析 5 值（与写入点同一份解析代码 + 变体键 fallback），先到先得、5 键集齐提前收敛，单条 JSON 解析失败 warn 跳过继续向上 → 全历史均缺键的列写 NULL → UPDATE 分支表 5 值列（多项目 repoIds IN 批量）。与写入侧差异：写入只看最新一条（O(1)），刷数负责存量清洗收敛，缺键向上补齐历史值。幂等：同值 UPDATE 影响行数 0，成功记录集合不变则结果不变；并发安全（按 repo_id+branch_name 精确 UPDATE）；updated/no-change 计数汇总日志。

## 3. 类设计

| 类                                                                  | 变更                                                                                                                                                                                     |
| ------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `RepoBranchInfoEntity` / `ProjectBranchRowEntity`                   | +5 指标值字段                                                                                                                                                                            |
| `RepoBranchInfoMapper.xml`                                          | 查询 select 列补齐；+`updateMetricsSnapshot`；排序注入                                                                                                                                   |
| `CodeMetricsRecordMapper`（接口+XML）                               | +`selectLatestByGitAndBranch`（写入点，最新一条）+`selectSuccessHistoryByGitAndBranch`（刷数，倒序全历史）；-`selectLatestByGitUrls`                                                     |
| `CodeMetricsServiceImpl`                                            | +`refreshBranchMetricsSnapshot`（写入点）+`backfillBranchMetricsHistory`（刷数补齐，共用 `syncBranchSnapshotColumns`）+ 5 指标解析公共方法；`persistMetrics` 接入；删除度量查询/拼接链路 |
| `CodeMetricsService`（接口）                                        | -`getLatestMetricsByGitUrl(s)`                                                                                                                                                           |
| `RepoServiceImpl`                                                   | 两查询改读分支表列；删内存排序路径与 repoUrl 收集                                                                                                                                        |
| `BranchMetricsSyncJob`（新增，实际命名 `branchMetricsSyncHandler`） | XxlJob handler：入参解析 / 分支遍历 / 调 `backfillBranchMetricsHistory` / 汇总日志                                                                                                       |
| `BranchMetricsVO` / `MetricItemVO`                                  | 结构不变；value 值源改分支表列，pipelineRunId 恒 null                                                                                                                                    |

## 4. 数据模型设计

```sql
ALTER TABLE repo_branch
  ADD COLUMN code_scale BIGINT DEFAULT NULL COMMENT '代码规模快照（最新成功扫描）',
  ADD COLUMN avg_function_loc DECIMAL(10,2) DEFAULT NULL COMMENT '平均代码行数快照',
  ADD COLUMN avg_cyclomatic_complexity DECIMAL(10,2) DEFAULT NULL COMMENT '平均圈复杂度快照',
  ADD COLUMN total_code_duplication_rate DECIMAL(10,2) DEFAULT NULL COMMENT '总代码重复率快照',
  ADD COLUMN total_file_duplication_rate DECIMAL(10,2) DEFAULT NULL COMMENT '总文件重复率快照';
```

Liquibase changeset 含对称回滚；不落来源 runId/时间列（详情兜底可反查，无不可替代消费点）；无需新增索引（排序 filesort 行数量级可控，实测超阈值再评估组合索引）；`code_metrics_record` 结构与内容零变更。

## 5. 性能设计

- 非排序列表：单次分页 SQL，度量列随行带出，零额外查询（现状：全历史拉取 + 内存拼接）；
- 度量排序：SQL ORDER BY（现状：全量分支 + 全历史度量内存排序分页）；
- 单仓/Tag 列表：零额外查询（现状：每页一次全历史拉取，Tag 纯浪费）；
- 写入：+1 次 repo_url 反查 + 1 次按主键维度 UPDATE；刷数：每分支 1 次倒序全历史查询（既有 `idx_git_url_branch` 命中）+ 逐条 JSON 解析（5 键集齐提前收敛，通常命中最新 1 条）+ 至多 1 次 UPDATE。

## 6. API 接口设计

- 对外 HTTP 接口（`/repo/branch/list`、`/project-repo/query-repo-branch`、`/repo/branch/filter-meta`）路径/入参/出参结构零变化；
- 出参语义变化：`metrics[key].value` 值源为分支表快照列——写入语义为"最新成功快照值"，经刷数存量补齐后与改造前"跨记录补齐值"完全等价；`metrics[key].pipelineRunId` 恒为 null（跳转走详情接口兜底）；
- 度量详情 `/metrics/file-detail` 零改动；机机接口 `/metrics/code/latest-by-commit/batch` 零影响；
- XxlJob 新增刷数任务注册。

## 7. 安全设计

- 查询链路横向越权校验不变；刷数任务无用户上下文、不暴露 HTTP 入口；
- 排序字段白名单枚举映射（非字符串拼接）；新增 SQL 全部 MyBatis 参数化；jobParam 校验格式；
- 新增列均为度量数值，无敏感泄露面；
- 写列失败/解析失败降级不阻断上报主链路；刷数遍历中单条 JSON 解析失败 warn 跳过继续向上；刷数任务异常跳过该分支继续。
