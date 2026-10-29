# 消费 framework 项目重命名事件同步 community 数据（ProjectChangeListener）

## 需求背景

framework 平台侧支持项目重命名，但 openlibing-sca 侧以项目名作为 `community` / `community_name` 维度存储扫描数据。项目重命名后，SCA 侧数据仍挂在旧项目名下，导致 SCA 数据与 framework 不一致：按新项目名查询不到历史扫描数据，旧项目名下残留脏数据。

framework 在项目重命名事务提交后会向 RabbitMQ 队列 `project_change_event_sca_queue_<环境后缀>` 投递项目变更事件，SCA 侧需要新增消费者，将 community 维度数据同步到新项目名。

## 功能描述

- 新增 `ProjectChangeListener`（`common/config/rabbitmq`）：监听 `spring.rabbitmq.project-change.queue` 配置的队列（`queuesToDeclare` 自动声明持久化队列，与 framework 生产端参数保持一致），消费项目重命名事件。
- 消息体为 JSON：`eventType`、`eventId`、`projectId`、`oldProjectName`、`newProjectName`、`publishedAt`；仅处理 `eventType=PROJECT_RENAME` 的事件。
- 新增 `ProjectChangeEventService` + `ProjectChangeEventServiceImpl`：在单个事务内将 7 张表的 community 维度数据从旧项目名更新为新项目名（SQL 统一维护在 `ProjectChangeEventMapper.xml`，`#{}` 参数绑定）。
- 更新成功（数据库事务已提交）后失效相关 Redis 缓存：按 community 维度的 PR 扫描列表缓存（TTL 1 天，新旧两个 key）、全量社区仓库列表缓存（TTL 10 分钟）。
- `ProjectConstant` 新增两个缓存 key 常量；`PRScanSchedule`、`OpenPersonScanServiceImpl` 改用常量引用，消除散落的魔法字符串（顺带修复 `PRScanSchedule` 中 LOGGER 声明为错误类 `PendingCountSchedule` 的问题）。
- `application*.yaml` 新增 `spring.rabbitmq.project-change.queue` 配置：本地与 beta 环境为 `project_change_event_sca_queue_beta`，gama 为 `_gamma` 后缀，prod 为 `_prod` 后缀（与 framework 生产端 queue-suffix 一致）。
- 新增 `ProjectChangeListenerTest`（6 个用例）、`ProjectChangeEventServiceImplTest` 单元测试。

## 验收标准

- [x] `eventType` 不支持时记日志并 ack 跳过，不调用同步逻辑。
- [x] 新旧项目名为空时 `basicReject(false)` 丢弃并记 ERROR，避免毒消息无限重投。
- [x] 新旧项目名相同时 ack 跳过。
- [x] 同步逻辑覆盖 7 张表：`tbl_export_data`、`tbl_measure`、`tbl_person_scan`、`tbl_repo`（`community` 列）+ `tbl_scan_result_log`、`tbl_scanoss_shield`、`tbl_shield_role`（`community_name` 列）。
- [x] 任一表更新失败整体事务回滚，消息 reject 丢弃并记 ERROR。
- [x] 更新条件为 `WHERE community(_name) = 旧项目名`，天然幂等，消息重放无副作用。
- [x] 同步成功后失效新旧 community 的扫描列表缓存与全量社区仓库列表缓存；缓存删除失败仅记 ERROR，不影响 ack。
- [x] 单元测试通过（`ProjectChangeListenerTest`、`ProjectChangeEventServiceImplTest`）。
- [x] CI 流水线通过（PR 标签 `ci-pipeline-passed`），PR 已合入。

## 影响范围

- 仅 `openlibing-sca` 仓：新增 listener/service/mapper/XML/单测，修改 `ProjectConstant`、`PRScanSchedule`、`OpenPersonScanServiceImpl`、3 个环境 `application*.yaml`。
- 新增 RabbitMQ 队列（自动声明，持久化），环境间队列名按后缀隔离。
- 无 DB schema 变化（仅数据行 UPDATE）、无对外 HTTP 接口变化。
- 行为变化：SCA 开始消费 project change 队列；项目重命名后 SCA 侧 community 数据自动同步。

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-sca/pull/351（`ms_project` → `release_20261029`，+642/−7，13 files，已合入）
