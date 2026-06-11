# mongodb-cpu-fix — 归档

## 关联
- 业务 PR: https://gitcode.com/openlibing/openlibing-codecheck/pulls/207

## 交付历程
- commit `b673208`: 增加诊断日志（[MONGODB-CPU] 前缀），覆盖 RuleSetScheduleTask / ScheduleDelegateImpl / RuleSetOperation / SigRuleSetOperation
- commit `490a9822`: 新增 codecheck_rule_account 复合索引（Liquibase changelog），清理诊断日志，保留 SLOW 告警（500ms 阈值），恢复 cron 和 shouldExecuteTask

## 问题定位过程

### 现象
生产环境 MongoDB CPU 在凌晨 2:00-5:30 接近 100%，gamma 环境趋势相同但峰值仅 30%+。

### 排查步骤
1. 在 `mongodb-cpu-yym` 分支添加大量诊断日志，部署到 gamma 环境
2. 将凌晨 2 点的定时任务调整到白天执行，复现问题
3. gamma CPU 飙至 90%+，成功复现
4. 搜索 `[MONGODB-CPU] SLOW` 日志，发现 2 万+ 条 `batchUpdateRuleAccountEntities SLOW` 告警
5. 每条 update 耗时 100-130ms，查询条件为 `{rule_id, user_name, domain_name, region, project_id}`
6. 确认 `codecheck_rule_account` 表缺少该组合的复合索引

### 根因
`codecheck_rule_account` 表（39 万行）缺少 `{rule_id, user_name, domain_name, region, project_id}` 复合索引，导致 `batchUpdateRuleAccountEntities` 逐条 update 时每次都进行全表扫描。凌晨 2 点多个定时任务并发执行，大量慢写操作叠加造成 CPU 飙高。

### 验证
- 加索引前：gamma CPU 90%+，2 万+ 条 SLOW 告警
- 加索引后：gamma CPU 降至 40%，SLOW 告警基本消失

### 之前排查过的方向（均排除）
- 索引缺失导致全表扫描（之前只确认了 select 走了 IXSCAN，未关注 update/delete 的查询条件）
- codecheck_rule_account 重复数据
- 多 Pod 并发执行同一任务
- getAllAccountRule 异常写入

## 用户自测反馈
- Liquibase changelog 文件未被打包进 JAR 导致启动失败 → 临时去掉 changelog 引用，手动在 gamma MongoDB 创建索引，后续修复文件打包问题
- SSL 配置改动（MongoConfig/RedisConfig）仅用于 gamma 环境，不纳入 PR

## 最终验证
- 编译通过：`mvn compile` 成功
- gamma 环境验证：加索引后 CPU 从 90%+ 降至 40%

## 设计偏差与取舍
- 5 字段复合索引 vs 2 字段索引：选择 5 字段全覆盖索引，因为 batchUpdate/batchDelete 的查询条件包含全部 5 个字段，全覆盖索引可直接定位无需回表
- queryRules 的查询条件（4 字段，无 rule_id）无法复用此索引的前缀，如后续 queryRules 也变慢需单独加 `{user_name, domain_name, region, project_id}` 索引
- SLOW 告警阈值从 100ms 提高到 500ms，减少正常操作的日志噪音

## 可复用经验
- MongoDB CPU 飙高时，不仅要看 select 是否走索引，还要看 update/delete 的查询条件是否有对应索引
- 逐条 update/delete 是伪批量操作，数据量大时性能问题严重，应考虑 BulkOperations
- Liquibase changelog 新增文件需确认被打包进 JAR，否则会导致启动失败

## 归档日期
2026-06-11
