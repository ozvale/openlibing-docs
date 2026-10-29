# static-alarm-snapshot-count 实现步骤

## 实体与模型

- [x] StaticAlarmScanRunEntity：删除 issue_count/new_issue_count/resolved_issue_count 三个增量字段中的两个死字段，调整 issue_count 注释语义
- [x] StaticAlarmScanRunEntity：新增 7 个快照字段 + snapshot_computed 标记
- [x] 新增 StaticAlarmSnapshotCount model（含 failed() 静态工厂）

## 聚合实现

- [x] StaticAlarmOperation.aggregateSnapshot：$match（仓库维度）+ $project（status/severity）+ $group（status × severity 计数）
- [x] 客户端按状态维度、级别维度分别累加推导 7 个快照值
- [x] 聚合成功路径未命中字段统一填 0（修复 0 计数字段为 null 的问题）
- [x] 聚合异常 catch 返回 failed()，不阻塞 scanRun 入库
- [x] 耗时 > 500ms 慢日志告警

## 写入路径

- [x] updateScanRunSuccess 调用聚合并写入 8 个字段
- [x] updateScanRunPartialSuccess 调用聚合并写入 8 个字段
- [x] 两条路径聚合失败时输出 warn 日志（snapshot_computed=false）

## 验证

- [x] 业务 PR CI 通过（ci-pipeline-passed 标签）
- [ ] 业务 PR #314 合入 release_20260831_iter2
