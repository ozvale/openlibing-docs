# staticAlertCount 数据链路梳理

> 回答三个问题：这个指标**从哪来**、**存在哪**、**什么时候写**。
> 结论先行：`staticAlertCount` **没有独立存储**——它是查询时对 codecheck Mongo 告警集合的**实时聚合结果**；告警明细本身在静态扫描流水线完成后异步入库。落表优化方案见 [design.md](./design.md)。

## 1. 数据源头与存储位置

| 存储位置                                          | 内容                                                                                                                                                         | 角色                                                      |
| ------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------- |
| codecheck **Mongo** `static_alarm_issue`          | 告警明细：`repo_type/owner/repo`、`branch`、`list_state`、`status`、`severity`、`rule_id`、`fingerprint_key`、`project_ids`、`first_seen_at/last_seen_at` 等 | **staticAlertCount 的唯一数据源**（聚合即出自此集合）     |
| codecheck **Mongo** `static_alarm_scan_run`       | 扫描记录：OBS 上 SARIF 文件地址、`branch`、`commit_id`、`project_ids`、解析状态                                                                              | 解析链路的调度载体（一次扫描一行）                        |
| codecheck **Mongo** `static_alarm_issue_instance` | 同一告警（fingerprint）跨扫描的实例历史                                                                                                                      | 下钻溯源用，不参与计数                                    |
| coderepo MySQL `repo_branch`                      | 分支行（**当前不含告警数列**）                                                                                                                               | 展示行载体；`staticAlertCount` 目前查询时实时回填，未落库 |

集合名定义于 codecheck `CodeCheckCollectionName`（`STATIC_ALARM_ISSUE = "static_alarm_issue"` 等）。

## 2. 写入触发链路（告警明细什么时候进 Mongo）

### 2.1 主链路：静态扫描流水线完成后自动上报

```
cicd（流水线事件）                      codecheck                             Mongo
────────────────────                  ──────────────────────                ─────────────
PipelineEventConsumer
  (MQ 消费流水线结束事件,
   拉取构建产物)
        │ 静态检查任务完成,
        │ 从产物解析出 SARIF 的 OBS downloadUrl
        ▼
CodeCheckClient#receiveStaticAlarmResult
  = Feign POST /internal/codescan/v1/result/receive ──► StaticAlarmReceiveServiceImpl#receive
                                                          │ 1. 解析 repoUrl 坐标
                                                          │    (RepoInfoCoordinateResolver,
                                                          │     反查归属项目 projectIds)
                                                          │ 2. scanRunOperation.insert
                                                          ├──────────────────────────► static_alarm_scan_run
                                                          │ 3. eventProducer.sendScanParseEvent(scanRunId)
                                                          ▼    (发 MQ, 消息体=scanRunId)
                                                   StaticAlarmEventConsumer
                                                     (@RabbitListener "staticalarm_queue",
                                                      并发 1-3)
                                                          │
                                                          ▼
                                                   SarifParseServiceImpl#parse
                                                          │ 4. 下载 OBS SARIF → 识别工具
                                                          │    → 按规则/文件解析 issues
                                                          │    → fingerprintKey 指纹
                                                          ▼
                                                   upsertIssues
                                                     ├ 新告警 → list_state=OPEN
                                                     ├ SARIF suppression 标记
                                                     │   → SUPPRESSED_BY_COMMENT
                                                     ├ 本次未出现的指纹 → 对账标记消失/RESOLVED
                                                     └ 其余 → upsert 更新 last_seen_at
                                                          ├──────────────────────────► static_alarm_issue  ◄─ 计数源
                                                          └ 更新 scanRun 解析状态 ────► static_alarm_scan_run
```

- **触发起点**：静态检查流水线跑完（cicd `PipelineEventConsumer` 消费流水线事件，无需人工）；
- **保存时机**：`receive` 同步落 scanRun（快），SARIF 解析**异步**（MQ 削峰），解析完成才真正写 `static_alarm_issue`——秒级到分钟级取决于 SARIF 体量；
- 幂等性：按 `fingerprint_key`（tool+ruleId+filePath+locationHash 等）upsert，重复扫描不产生重复计数。

### 2.2 人工操作链路（同样直接改 Mongo 计数源）

| 操作                      | 入口                                                                          | 对 `static_alarm_issue` 的影响               |
| ------------------------- | ----------------------------------------------------------------------------- | -------------------------------------------- |
| 处理/流转告警             | codecheck 告警列表的状态变更接口                                              | `list_state` 变化（如 OPEN → 已处理）        |
| 屏蔽/恢复告警（含审批流） | `StaticAlarmOperation` 中 list_state 置换（`SUPPRESSED_BY_COMMENT` ↔ `OPEN`） | `list_state` 变化                            |
| 项目归属对账修复          | codecheck XXL-Job（`staticAlarmProjectIdsReconcileHandler` 等）               | 批量修正 `project_ids`，影响项目维度聚合命中 |

## 3. 读取链路（分支列表的 staticAlertCount 怎么算出来）

```
前端分支管理页 (按 staticAlertCount 排序/展示)
        │ GET /openlibing-coderepo/repo/branch/list
        ▼
coderepo BranchController#queryProjectBranch
        │ RepoServiceImpl#queryProjectBranch
        │   ├ 告警数排序时: 全量取回分支行 (queryProjectBranchByLimit(0, total))
        │   ├ fillBranchStaticAlertCounts  ────── 每次查询都实时调 ↓
        ▼
OpenlibingCodeCheckClient#batchStaticAlarmCount
  = Feign POST /internal/codescan/v1/static-alarm/issue/count/batch
        │ 入参: projectId + [(repoId, repoType, owner, repo, branch)...]
        │       (repoUrl 经 RepoUrlParser.parse, 域名无关)
        ▼
codecheck StaticAlarmServiceImpl#batchIssueCount
        │ StaticAlarmOperation#countIssuesGroupByRepoAndListState
        │ Mongo 聚合: $match(project_ids + repo) → $group(repo, branch, list_state)
        ▼
    static_alarm_issue 集合 ──► open = OPEN + PENDING_REVIEW   ◄─ "未处理"口径
        │ 返回 [(repoId, openCount, branch)...]
        ▼
coderepo 按 (repoId | branch) 行级回填 VO.staticAlertCount
        │ null = 解析失败/无数据(前端显示 --), 与 0 语义不同
        ▼
内存排序/分页 → 响应
```

要点：

- **每次列表查询都发起一次实时 Mongo 聚合**——`staticAlertCount` 数值永远"现算"，无缓存无落库，这是它"保存时机"的答案：**没有保存时机，读时计算**；
- 也正因数值只在查询时存在，排序无法走 MySQL `ORDER BY`，被迫全量取回 + 内存排序；
- 仓库管理 tab（repo 维度，= 该仓所有分支未处理之和）走同一 batch 接口的整仓模式，链路同理。

## 4. 保存时机汇总

| 数据                      | 存哪                                   | 什么时候写                                                                              |
| ------------------------- | -------------------------------------- | --------------------------------------------------------------------------------------- |
| 扫描记录                  | Mongo `static_alarm_scan_run`          | cicd 上报时同步写入（receive）                                                          |
| 告警明细                  | Mongo `static_alarm_issue`             | receive 后 MQ 异步解析完成时 upsert；人工处理/屏蔽实时改 `list_state`                   |
| **staticAlertCount 数值** | **无存储**                             | 每次查询 `/repo/branch/list` 时对 `static_alarm_issue` 实时聚合                         |
| （规划中）落表值          | MySQL `repo_branch.static_alert_count` | 落表方案上线后：XXL-Job 定时刷新 + 分支新增/接入时即时刷新，见 [design.md](./design.md) |

## 5. 一句话总结

**告警明细在扫描流水线完成后由 cicd 推送、codecheck 异步解析进 Mongo（`static_alarm_issue`），人工处理/屏蔽实时改状态；而分支列表上的 `staticAlertCount` 不落任何表，是每次查询时对这个 Mongo 集合按 (项目, 仓库, 分支) 实时聚合出的 `OPEN + PENDING_REVIEW` 计数。**
