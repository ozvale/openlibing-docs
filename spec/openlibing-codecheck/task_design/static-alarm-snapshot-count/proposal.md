# static-alarm-snapshot-count

## 基本信息

| 项          | 值                                     |
| ----------- | -------------------------------------- |
| FE 需求名称 | 静态告警入湖快照字段                   |
| 目标仓      | openlibing-codecheck                   |
| 业务分支    | add-count-yym（base: master 460b4025） |
| 业务 PR     | openlibing/openlibing-codecheck#314    |
| 流程模式    | Standard                               |

## 需求背景

静态告警每次扫描结束后会写 scanRun 记录（MongoDB），下游数据入湖消费该记录。原实体上仅有 `issue_count` / `new_issue_count` / `resolved_issue_count` 三个增量口径字段，存在两个问题：

1. **入湖需要的不是增量而是存量快照**：下游消费方需要本次扫描结束时各状态（未解决/已解决/已忽略）、各级别（致命/严重/一般/提示）的存量计数，原字段口径不匹配。
2. **原增量字段为死字段**：`new_issue_count` / `resolved_issue_count` 从未真正写入有效数据，`issue_count` 语义含混（SARIF 解析总数 ≠ 存量）。

本需求将死字段替换为 7 个存量快照字段 + 1 个计算成功标记，扫描结束（SUCCESS / PARTIAL_SUCCESS）时通过 MongoDB 聚合一次性写入。

## 验收标准

1. `StaticAlarmScanRunEntity` 删除 `new_issue_count` / `resolved_issue_count` 死字段，新增 `issue_snapshot` / `solve_snapshot` / `ignore_snapshot` / `critical_count_snapshot` / `major_count_snapshot` / `minor_count_snapshot` / `suggestion_count_snapshot` 7 个快照字段及 `snapshot_computed` 标记。
2. 扫描成功与部分成功两条路径均写入快照字段（SARIF 解析总数 `issue_count` 保留）。
3. 聚合管道命中既有 `idx_issue_branch_status` 索引（覆盖索引扫描，无 FETCH）。
4. 聚合失败不阻塞 scanRun 正常入库：状态照常更新为 SUCCESS / PARTIAL_SUCCESS，快照字段为 null，`snapshot_computed=false`，下游按标记区分。
5. 聚合成功路径下，未命中的 0 计数字段写 0 而非 null（与失败路径的 null 语义区分清晰）。
6. 聚合耗时超过 500ms 输出慢日志告警。
