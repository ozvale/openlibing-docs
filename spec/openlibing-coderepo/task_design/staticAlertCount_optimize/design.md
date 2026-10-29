# 方案设计：分支列表 staticAlertCount 落表优化

> 需求来源：[requirement_desc.md](./requirement_desc.md)
> 涉及仓：`openlibing-coderepo`（主）、`openlibing-codecheck`（本期无接口变更）

## 1. 背景与现状

### 1.1 查询链路

分支管理页面查询接口 `/openlibing-coderepo/repo/branch/list`：

```
BranchController#queryProjectBranch
  → RepoServiceImpl#queryProjectBranch
      → repoBranchInfoMapper.countProjectBranch                     -- total
      → [staticAlertCount / metrics 排序时] 全量取回:
          repoBranchInfoMapper.queryProjectBranchByLimit(0, total)   -- 无分页全量
      → fillBranchStaticAlertCounts(allData, projectId)              -- 实时 Feign
      → sortProjectBranchInMemory                                    -- 内存排序
      → paginateProjectBranchList                                    -- 内存分页
      → [非 staticAlertCount 排序时] fillBranchStaticAlertCounts(pageData) -- 实时 Feign
```

`staticAlertCount` 的实时取数在 `RepoServiceImpl#fillBranchStaticAlertCounts`：

1. 按行解析 `repoUrl` 坐标（`RepoUrlParser.parse`，域名无关），组装 `(repoId, repoType, owner, repo, branch)` 批量请求；
2. Feign 调 codecheck 内部接口 `POST /internal/codescan/v1/static-alarm/issue/count/batch`（`OpenlibingCodeCheckClient#batchStaticAlarmCount`）；
3. codecheck 侧 `StaticAlarmServiceImpl#batchIssueCount` 对 Mongo 静态告警集合做聚合（`countIssuesGroupByRepoAndListState`），按 `(repoKey, branch, list_state)` 分组计数，未处理口径 = `OPEN + PENDING_REVIEW`，无记录返回 0；
4. coderepo 按 `(repoId | branch)` 行级回填到 `ProjectBranchInfoVO.staticAlertCount`，取不到的行保持 `null`（前端显示 `--`）。

### 1.2 性能问题

- **每次列表查询都发起一次跨服务 Mongo 聚合**，与页面访问量线性相关；
- **排序路径被迫"全量取回 + 内存排序"**：`staticAlertCount` 不是本地列无法 `ORDER BY`，`isMemorySortField` 命中后取回全量行（`queryProjectBranchByLimit(0, total)`）再内存排序分页，数据量大时查询耗时和内存占用都被放大；
- 同页非告警排序时也要额外发一次 Feign 回填当前页。

### 1.3 现状口径约束（必须保持）

- 统计口径：**未处理告警数**（`OPEN + PENDING_REVIEW`），分支维度；
- 回填**不区分分支是否接入代码检查**（`isCodecheck` 不过滤，有告警数据的未接入分支同样显示数字）；
- `null`（坐标解析失败/无数据）与 `0`（明确无未处理告警）语义不同，前端 `--` vs `0`；
- 排序时 `null` 按 0 参与比较（`sortProjectBranchInMemory` 现行为）。

## 2. 目标与非目标

### 目标（本期）

1. 分支维度的未处理告警数**落表**到 `repo_branch` 表，查询侧直接 SQL 排序 + 分页，消除查询路径上的 Feign 调用与全量取回内存排序；
2. **写时推送**：codecheck 在告警数据变更点（SARIF 解析完成、屏蔽/解除屏蔽、状态流转）实时重算并推送数值，coderepo 秒级落库；
3. 提供历史数据回填与漂移兜底对账能力；
4. 对外接口（请求/响应结构、字段语义、排序语义）**完全不变**，前端无感。

### 非目标（本期不做，二期可选）

1. 仓库管理 tab（repo 维度 `staticAlertCount`，= 该仓所有分支未处理告警之和）仍走现有 Feign 路径；二期可从 `repo_branch` 聚合派生（`SUM`）或同样落表 `repo_info`；
2. 度量类排序字段（`codeScale` 等，存于外部代码度量服务）的落表，另案。

## 3. 方案总览

```
┌─────────────── openlibing-codecheck ────────────────────┐
│ Mongo static_alarm_issue（告警明细，计数数据源）           │
│   变更点：                                                │
│   ① SARIF 解析完成（SarifParseService#parse）            │
│   ② 屏蔽 / 解除屏蔽（shield / batchUnshieldIssues）       │
│   ③ 告警状态流转（人工处理）                               │
│        │ 每个变更点后：对该 (repo, branch)                │
│        │ 重聚合一次 openCount → 发 MQ（带数值）           │
└────────┼─────────────────────────────────────────────────┘
         │ ④ MQ：static_alert_count_refresh 队列
         ▼
┌────────────── openlibing-coderepo ──────────────────────┐
│ StaticAlertCountRefreshConsumer（新增消费者）             │
│   坐标反查 repoId → UPDATE repo_branch.static_alert_count│
│ StaticAlertCountRefreshJob（XXL-Job，兜底对账）           │
│   · 历史数据回填（full 模式，上线手动触发一次）             │
│   · 漂移自愈兜底（incr 模式，低频）                        │
│ 查询侧：queryProjectBranch 移除告警内存排序分支            │
│   ORDER BY IFNULL(b.static_alert_count, 0) 走 SQL        │
└─────────────────────────────────────────────────────────┘
```

三条写入通道（互相独立、幂等）：

| 通道                 | 触发时机                                    | 覆盖范围            | 实时性 |
| -------------------- | ------------------------------------------- | ------------------- | ------ |
| ① 写时推送（主通道） | SARIF 解析完成、屏蔽/解除屏蔽、告警状态流转 | 单个 (repo, branch) | 秒级   |
| ② XXL-Job 兜底对账   | 周期调度（默认 2h，可配）                   | 全量分支行          | 小时级 |
| ③ 历史数据回填       | 上线后手动触发一次 ② 的 full 模式           | 全量分支行          | 一次性 |

核心正确性保证：**推送的是"推送时点对该 (repo, branch) 重聚合出的全量数值"，不是增量 delta**——任何埋点遗漏、消息丢失、乱序都只造成短暂旧值，不会累积误差，由通道 ② 定期收敛。

## 4. 详细设计

### 4.1 表结构变更（coderepo）

```sql
ALTER TABLE repo_branch
    ADD COLUMN static_alert_count INT NULL
        COMMENT '未处理静态告警数（OPEN+PENDING_REVIEW），NULL=未接入或尚未刷新；来源 codecheck 定时刷新',
    ADD COLUMN static_alert_count_synced_at DATETIME NULL
        COMMENT '告警数最近刷新时间';
```

- **不加索引**：排序发生在"项目维度"查询内（`repo_branch b JOIN repo_info r`，`r.project_id` 过滤后行数 = 项目分支数，量级百~千），现有 join + where 结果集内排序代价可忽略；实测量大后再评估 `(project_id, static_alert_count)` 类索引。
- `static_alert_count_synced_at` 用于运维排查（数据新鲜度观测）与后续增量刷新优化（按最久未刷优先），本期仅写入不参与查询。

### 4.2 数据语义

| 值      | 含义                                                                                   | 前端展示 |
| ------- | -------------------------------------------------------------------------------------- | -------- |
| `NULL`  | 分支从未被成功取数：坐标解析失败（非法 URL）、codecheck 长期不可用、新分支尚未轮到刷新 | `--`     |
| `0`     | codecheck 聚合明确返回该 (repo, branch) 无未处理告警                                   | `0`      |
| `N > 0` | 最近一次刷新时的未处理告警数                                                           | `N`      |

- 数值口径与 codecheck `resolveOpenAndIgnoredByListState` 的 open 分量一致（`OPEN + PENDING_REVIEW`），跨域名场景沿用 `RepoUrlParser.parse` 坐标（与现有 `fillBranchStaticAlertCounts` 相同，atomgit/gitcode 双域名已兼容）；
- **刷新范围不按 `isCodecheck` 过滤**，与现查询口径一致（未接入分支若 Mongo 中有该坐标告警数据，同样落表展示）；
- 排序口径 `IFNULL(static_alert_count, 0)`，与现内存排序中 null 按 0 的行为一致。

### 4.3 写入侧

#### 4.3.1 写时推送（主通道，秒级）

codecheck 在每个告警数据变更点完成后，对该 (repo, branch) **重聚合一次 openCount** 并推送 MQ；coderepo 消费落库。

**codecheck 侧发布器**：新增 `BranchAlertCountPushService`（收口组件，所有变更点只调它）：

```
pushFor(repoKey, branch, projectIds):
  1. 对该坐标做一次聚合（复用 countIssuesGroupByRepoAndListState 的过滤与口径，
     缩小 $match 到单 repo + branch），得到 openCount（OPEN + PENDING_REVIEW）；
  2. rabbitTemplate.convertAndSend("static_alert_count_refresh",
     JSON.toJSONString({projectId, repoType, owner, repo, branch, openCount, pushedAt}));
```

埋点位置（变更点完成后调用）：

| #   | 埋点                                                                                             | 变更来源                                     |
| --- | ------------------------------------------------------------------------------------------------ | -------------------------------------------- |
| 1   | `SarifParseServiceImpl#parse` 完成后（`StaticAlarmEventConsumer` 消费链路尾部，upsert 成功即推） | 扫描入库：新告警、SARIF 屏蔽、已消失告警对账 |
| 2   | `StaticAlarmServiceImpl#shield` / 解除屏蔽（`batchUnshieldIssues` 调用处）成功后                 | 屏蔽/恢复，`list_state` 变化                 |
| 3   | 告警状态流转接口（人工处理/恢复）成功后                                                          | `list_state` 变化                            |

- **为什么推"重算全量值"而不是"变更 delta"**：同分支可能并发解析多个 scanRun、屏蔽与解析可能交错，delta 在并发下必然错账；全量值覆盖写天然幂等，消息乱序/重复/丢失的最坏结果只是短暂旧值，由 4.3.2 兜底对账收敛；
- **为什么走 MQ 而非解析主流程内同步 Feign 调 coderepo**：不阻塞/不污染解析主链路（解析成功但推送失败不应把 scanRun 标记失败），削峰（批量扫描时推送消息可堆积），消费端重试自由；codecheck → coderepo 方向依赖有现成先例（`CodeMetricsFeignClient`），但推送走 MQ 进一步解耦，无需 coderepo 新增同步内部接口；
- **埋点遗漏自愈**：即使某变更点漏埋或推送失败，数值只是"旧到下次触发/兜底"，不产生累积误差。

**coderepo 侧消费者**：新增 `StaticAlertCountRefreshConsumer`（`@RabbitListener`，复用 `NotifyConsumer` 重试模式：`MAX_RETRY=3`，backoff `{1s, 5s, 15s}`，超限 ACK 丢弃并错误日志——下轮兜底对账自愈）：

```
consume(payload):
  1. RepoInfoCoordinateResolver 按 (projectId, 坐标) 反查 repo_info → repoId
     （跨域名兼容，resolver 快慢路径已有）；未命中（仓库已删/未录入）→ ACK 丢弃；
  2. UPDATE repo_branch SET static_alert_count = #{openCount},
         static_alert_count_synced_at = NOW()
     WHERE repo_id = #{repoId} AND branch_name = #{branch} AND is_deleted = 0
     （同仓同分支多行/分支重命名导致 0 行 → 丢弃，等兜底对账）；
```

- 消息重复消费幂等（覆盖写）；同分支短窗口多次推送无需去抖，DB 覆盖写代价极低；
- 队列声明沿用两仓现有 RabbitMQ 配置风格（`spring.rabbitmq.*` 配置项），codecheck 发、coderepo 收。

#### 4.3.2 定时兜底对账（XXL-Job）

coderepo 新增 `XxlJobHandler#staticAlertCountRefreshHandler`（跟随现有 `syncRepoInfoHandler` 等的注册方式）：

```
流程：
1. 分页遍历待刷新行：
   SELECT b.branch_id, b.branch_name, b.repo_id, r.project_id, r.repo_url
   FROM repo_branch b JOIN repo_info r ON b.repo_id = r.repo_id
   WHERE b.is_deleted = 0 AND b.has_branch = '1'
     AND (b.branch_type = '0' OR b.branch_type IS NULL)
     [增量模式：AND (b.static_alert_count_synced_at IS NULL
                     OR b.static_alert_count_synced_at < NOW() - INTERVAL ? MINUTE)]
   ORDER BY b.static_alert_count_synced_at IS NULL DESC, b.static_alert_count_synced_at ASC
   LIMIT 1000
2. 每 100 行为一批：
   - RepoUrlParser.parse(repo_url)，解析失败的行跳过（保持 NULL）；
   - (repoId, branchName) 去重后组装 StaticAlarmCountBatchDTO，
     Feign 调 batchStaticAlarmCount（projectId 取行归属项目，跨项目仓库行按 projectId 分组）；
   - 回填：UPDATE repo_branch SET static_alert_count = ?, static_alert_count_synced_at = NOW()
           WHERE branch_id = ?；返回 0（行已删）则忽略。
3. 批间 sleep（如 200ms）限流，避免放大冲击 codecheck。
```

- **两种模式**：`full`（全量刷新，历史回填用）与 `incr`（默认，只刷 `synced_at` 为空或超龄的行，兜底自愈用）；handler 入参切换；
- **幂等**：整链路按 (branchId) 覆盖写，重复执行无副作用；执行中断下轮自愈；
- **调度参数**：频率（默认 2h——写时推送为主后兜底无需高频）与增量超龄阈值（默认同频率）走 XXL-Job 配置；
- **失败处理**：单批 Feign 异常记 warn 日志并跳过该批，任务整体不失败；
- **多实例**：XXL-Job 路由策略配置为单实例（FIRST），无并发写冲突。

> 兜底的存在价值：覆盖埋点遗漏、MQ 消息丢失、codecheck/coderepo 任一方发布窗口期的更新缺口，以及"推送链路整体故障"的极端场景——**定时对账是正确性的最终防线，写时推送只负责实时性**。

#### 4.3.3 历史数据回填

上线后手动在 XXL-Job 控制台以 `full` 模式触发一次 4.3.2 即完成历史回填；此后常态化运行低频 `incr` 模式。

### 4.4 查询侧改造（coderepo）

1. **mapper**（`RepoBranchInfoMapper.xml`）：
   - `queryProjectBranchByLimit` / `projectBranchRowMap`：select 列增加 `b.static_alert_count`；
   - `projectBranchOrderBy`：`<choose>` 增加 `when test="info.sortField == 'static_alert_count'"` 分支 → `IFNULL(b.static_alert_count, 0)`；
2. **常量**（`RepoServiceImpl`）：
   - `PROJECT_BRANCH_SORT_FIELD_MAP` 增加 `"staticAlertCount" → "static_alert_count"`；
   - `PROJECT_BRANCH_MEMORY_SORT_FIELDS` **移除** `"staticAlertCount"`（metrics 五项保留内存排序）；
3. **`queryProjectBranch`**：删除 `sortByStaticAlertCount` 全量取回/排序前回填分支，告警数排序自然落入 SQL 分页路径；删除两处 `fillBranchStaticAlertCounts` 调用（行值改由 SQL 直出）；
4. **VO/实体**：`ProjectBranchRowEntity`、`ProjectBranchInfoVO` 增加 `staticAlertCount` 映射（VO 字段已存在，补 SQL 列映射即可）；
5. **保留不动**：`fillBranchStaticAlertCounts` 方法本身暂不删除——仓库 tab（`fetchStaticAlertCountMap`）本期仍走 Feign；`fillBranchStaticAlertCounts` 在分支查询链路下线后若确认无其他调用方，二期随 repo tab 改造一并清理。

### 4.5 codecheck 侧变更（本期实施）

核心即 4.3.1 的 `BranchAlertCountPushService` + 三处埋点，另需：

- **MQ 队列/交换机声明**：沿用两仓现有 `spring.rabbitmq.*` 配置风格，新增 `static_alert_count_refresh` 队列（codecheck 侧声明发送、coderepo 侧声明消费，参照 `staticalarm_queue` / webhook 通知队列的既有声明方式）；
- **聚合口径复用**：推送前的单坐标重聚合必须与 `batchIssueCount` 完全同源（同一 Mongo 过滤条件 + `resolveOpenAndIgnoredByListState` 口径），建议直接抽取 `StaticAlarmServiceImpl` 内的聚合片段为共用私有方法，避免两处口径漂移；
- **失败语义**：推送失败只记日志，不影响 parse/shield/状态流转的主流程结果（兜底对账自愈）；
- **batch 接口保留**：仓库 tab 与兜底对账仍使用，不下线。

### 4.6 上线步骤

1. 执行 DDL（加列，NULL 默认，无锁风险低）；
2. 发布 codecheck（推送埋点 + 队列声明，先于 coderepo 发布也无妨——消息暂存队列）；
3. 发布 coderepo（查询侧切 SQL + 消费者上线）；
4. XXL-Job 控制台注册 `staticAlertCountRefreshHandler`，手动触发一次 `full` 完成历史回填；
5. 启用常态 `incr` 调度（2h）；
6. 观察项：消费者成功率/积压、`static_alert_count_synced_at` 分布（应持续前移）、列表接口 P95 耗时、codecheck batch 接口调用量（应显著下降）。

## 5. 风险与权衡

| 风险                                   | 影响                     | 对策                                                                                  |
| -------------------------------------- | ------------------------ | ------------------------------------------------------------------------------------- |
| 推送消息乱序/重复/丢失                 | 短暂旧值                 | 推送的是重算全量值（非 delta），覆盖写幂等；兜底对账定期收敛；最坏误差窗口 = 兜底周期 |
| 埋点遗漏（新增长变更路径未接入推送）   | 该路径变更后数值延迟     | 兜底对账自愈；`BranchAlertCountPushService` 收口 + code review 清单提示               |
| 同分支并发推送互覆                     | 最终写者胜，可能短暂回退 | 覆盖写幂等；推送间隔极短场景可接受，兜底收敛                                          |
| MQ 积压（批量扫描风暴）                | 数值延迟上升             | 消费逻辑极轻（一次反查 + 单行 UPDATE）；必要时消费并发调大                            |
| coderepo 不可用期间推送丢失            | 缺更新                   | MQ 暂存 + 消费重试；超限丢弃由兜底对账覆盖                                            |
| 双域名/嵌套群组坐标解析失败行恒为 `--` | 个别分支无数字           | 与现状一致（现查询同样解析失败保持 null）                                             |

**取舍记录**：

- 选择「写时推送重算全量值」而非「变更 delta 增量更新」：同分支并发解析/屏蔽交错下 delta 必然错账且无自愈手段；全量值幂等可乱序，正确性不依赖事件顺序。
- 选择「MQ 异步推送」而非「解析主流程同步 Feign 调 coderepo」：推送失败不应污染解析结果（scanRun 状态），削峰且消费端重试可控；同步调用的唯一优势（零延迟）对本场景非必需。
- 选择「定时兜底对账」作为最终防线而非仅依赖事件链：埋点遗漏、消息丢失、发布窗口缺口均有低成本自愈路径，正确性不依赖枚举完备性。
- 选择「复用 batch 接口（兜底链路）」而非「新增专门回传接口/直接读 Mongo」：不引入跨库依赖，口径收敛在 codecheck 一处。

## 6. 测试要点

1. **推送埋点单测（codecheck）**：parse 完成 / shield / unshield / 状态流转后各触发一次推送，载荷 openCount 为重算值；推送异常不影响主流程返回；
2. **消费者单测（coderepo）**：坐标反查命中/未命中（仓库已删丢弃）、回写 (repoId, branchName)、重复消息幂等、重试 3 次超限丢弃；
3. **兜底任务单测**：full/incr 行筛选（超龄/NULL 优先）、坐标解析失败跳过、(repoId, branch) 去重、Feign 异常批跳过、回写更新 synced_at；
4. **查询侧单测**：`staticAlertCount` 排序走 SQL 分页（不再全量取回）、NULL 按 0 排序、总条数正确、非告警排序路径回归（metrics 内存排序不受影响）；
5. **端到端口径验证**：扫描完成后列表数值秒级更新；屏蔽/解除屏蔽后数值随之减/增；抽样比对列表值与 codecheck 告警列表页聚合值一致（含 `OPEN + PENDING_REVIEW` 边界）；
6. **性能验证**：同一项目大分支量下，优化前后 `/repo/branch/list` 告警排序接口 P95 对比。

## 7. 任务拆分预览

| #   | 任务                                                                                 | 仓        |
| --- | ------------------------------------------------------------------------------------ | --------- |
| 1   | DDL + 实体/VO/RowEntity 字段与 mapper 列映射                                         | coderepo  |
| 2   | `BranchAlertCountPushService` + 三处埋点（parse/shield/unshield/状态流转）+ 队列声明 | codecheck |
| 3   | `StaticAlertCountRefreshConsumer`（反查 repoId + 落库 + 重试）                       | coderepo  |
| 4   | `staticAlertCountRefreshHandler`（full/incr 兜底对账 + 历史回填）                    | coderepo  |
| 5   | 查询侧切换 SQL 排序分页 + 移除查询链路 Feign 回填                                    | coderepo  |
| 6   | 单测补充与全量回归                                                                   | 两仓      |
