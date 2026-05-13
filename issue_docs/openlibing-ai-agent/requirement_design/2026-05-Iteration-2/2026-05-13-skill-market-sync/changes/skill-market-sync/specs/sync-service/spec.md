# Spec: Sync Service

**Change ID**: skill-market-sync
**Feature**: Skill 市场数据同步更新

## Scenario 1: 定时同步触发

**GIVEN** APScheduler 配置为每天凌晨 1 点触发同步任务

**WHEN** 定时任务触发

**THEN** 系统尝试获取分布式锁，成功后开始同步所有有 `source_url` 的 Skill

## Scenario 2: 同步 Skill 内容更新

**GIVEN** 数据库中存在一个 Skill，其 `source_url` 指向 GitHub 仓库中的 SKILL.md

**WHEN** 同步服务通过 Raw API 拉取最新 SKILL.md 内容，发现内容与数据库不同

**THEN** 更新数据库中该 Skill 的 `content_md`、`file_tree`、`updated_at` 字段

## Scenario 3: 同步文件树更新

**GIVEN** 数据库中存在一个 Skill，其外部仓库目录结构发生了变化（新增/删除了文件）

**WHEN** 同步服务通过 Contents API 获取最新目录结构

**THEN** 更新数据库中该 Skill 的 `file_tree` 字段

## Scenario 4: 同步 README.md 更新

**GIVEN** 数据库中存在一个 Skill，其外部仓库中的 README.md 内容发生了变化

**WHEN** 同步服务拉取最新 README.md 内容

**THEN** 更新数据库中该 Skill 的 `content_md` 字段（合并 SKILL.md + README.md）

## Scenario 5: 外部 Skill 已被删除（404）

**GIVEN** 数据库中存在一个 Skill，其 `source_url` 指向的文件在外部仓库中已不存在（返回 404）

**WHEN** 同步服务尝试拉取内容

**THEN** 不删除数据库中的 Skill 记录，将该 Skill 标记为"过时"并在同步结果中记录

## Scenario 6: 多实例分布式锁

**GIVEN** 服务部署了多个实例，APScheduler 在每个实例上同时触发同步任务

**WHEN** 两个实例同时尝试获取同步锁

**THEN** 只有成功 INSERT `sync_task` 记录（`status='running'`）的实例执行同步；另一个实例因唯一索引冲突 INSERT 失败，跳过同步

## Scenario 6a: 多实例竞态条件

**GIVEN** 两个实例几乎同时 SELECT 发现无 `running` 记录

**WHEN** 两个实例同时 INSERT `sync_task`

**THEN** 数据库唯一索引保证只有一个 INSERT 成功，另一个抛出 `IntegrityError`，失败实例捕获异常后跳过同步

## Scenario 7: 死锁兜底

**GIVEN** sync_task 表中存在一条 `status='running'` 的记录，且 `started_at` 超过 2 小时前（实例可能已崩溃）

**WHEN** 新实例尝试获取同步锁

**THEN** 新实例将旧记录标记为 `failed`，然后创建新的 `running` 记录并执行同步

## Scenario 7a: 同步过程幂等性

**GIVEN** 上一次同步因实例崩溃而中断，部分 Skill 已更新，部分未同步

**WHEN** 新实例接管后重新执行同步

**THEN** 已更新的 Skill 因内容无变化被跳过，未同步的 Skill 正常拉取更新，结果一致无副作用

## Scenario 8: 同步结果邮件通知

**GIVEN** 同步任务完成

**WHEN** 有同步结果（更新成功、过时等）

**THEN** 通过 SMTP 发送邮件给所有管理员，包含同步统计和详情

## Scenario 9: SMTP 不可用

**GIVEN** SMTP 服务不可用

**WHEN** 同步任务完成后尝试发送邮件失败

**THEN** 记录错误日志，不阻塞同步流程，sync_task 状态仍更新为 `completed`

## Scenario 10: Skill 无变化

**GIVEN** 数据库中存在一个 Skill，其外部内容未发生变化

**WHEN** 同步服务拉取并对比内容

**THEN** 不更新数据库，在同步结果中标记为"无变化"

## Scenario 11: 同步历史清理

**GIVEN** sync_task 表中存在超过 30 天的记录

**WHEN** 同步任务执行前

**THEN** 自动清理超过 30 天的 sync_task 记录

## Scenario 12: API 超时指数退避重试

**GIVEN** 同步服务调用 GitHub/GitCode API 时发生超时

**WHEN** 请求超时（TimeoutException）

**THEN** 按指数退避 + 随机抖动策略重试（10s → 30s → 60s，±25% 抖动），最多重试 3 次；若仍失败则标记该 Skill 为"更新失败"

## Scenario 13: API 限流指数退避重试

**GIVEN** 同步服务调用 GitHub/GitCode API 时收到 429 限流响应

**WHEN** 响应状态码为 429

**THEN** 优先使用 `Retry-After` header 指定的等待时间，否则按指数退避 + 随机抖动重试（30s → 90s → 120s，±25% 抖动），最多重试 3 次；若仍被限流则标记该 Skill 为"更新失败"

## Scenario 14: API 服务端错误指数退避重试

**GIVEN** 同步服务调用 GitHub/GitCode API 时收到 5xx 服务端错误

**WHEN** 响应状态码为 500/502/503 等

**THEN** 按指数退避 + 随机抖动策略重试（10s → 30s → 60s，±25% 抖动），最多重试 3 次；若仍失败则标记该 Skill 为"更新失败"
