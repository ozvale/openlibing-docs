# project-rename-adaptation

## 需求背景

平台 `project_info.project_name` 变更后，codecheck 侧 Mongo / Redis 仍大量冗余存储 `project_name`、`projectName`、`account` 等社区名；与母表不一致时，规则集、看板、增量汇总、屏蔽等功能会出现查不到数据或写到错误项目名下的问题。

历史上 codecheck 通过 Nacos 配置 `majun.project.name`（JSON：平台名 → majun 社区名）在读写路径做名称映射。本 PR 在保留可配置开关的前提下，补齐三件事：

1. **消费 framework 项目更名 MQ**，按 `project_info` 当前名刷 Mongo 冗名字段并迁移 `inc_{社区名}` Redis；
2. **引入 `actual_project_id`**，写入时补全、Job 回填，MQ 刷数优先按 id 定位文档；
3. **读路径统一经 `CommonHelper` 解析平台名 + majun 双读**，写路径逐步以平台项目名为准；提供 xxl-job 做 majun 存量刷名与 id 回填。

## 功能描述

1. **MQ 消费**：`ProjectRenameConsumer` 监听 `spring.rabbitmq.codecheck.project_change_event_queue`，解析 `ProjectRenameMessageDTO`，Redisson 按 `projectId` 加锁后调用 `ProjectRenameService.applyRenameEvent`。
2. **更名刷数**：在 `ActualProjectIdCollectionRegistry` 注册的 15 个 Mongo 集合上 `updateMulti` 更新项目名字段与 `actual_project_id`；同步 `migrateIncRedis`（`inc_旧名` → `inc_新名`）。
3. **匹配策略（Nacos 可刷新）**：
   - `project.rename.match-by-actual-project-id=false`（默认）：MQ 首轮按消息 `oldProjectName` 匹配项目名字段（回填 Job 完成前）；
   - `true`：Mongo 更新条件仅 `actual_project_id == projectId`。
4. **majun 开关 `majun.project.name.enabled`**：`false` 时读路径不再双读、MQ 不走 majun 补刷；`true` 且存量未刷净时，MQ 在首轮刷写后按消息旧平台名 / majun 社区名追加 Mongo 刷写并迁移 majun 对应 `inc_` 键。
5. **xxl-job**：
   - `actualProjectIdBackfillJob`：按 `project_info` 驱动，为注册集合缺失 `actual_project_id` 的文档补 id（入参 `projectId=` 可选）；
   - `projectMajunNameMigrationJob`：按 `majun.project.name` 配置将 Mongo（默认不含敏感词两集合）与 Redis 从 majun 名刷成平台名，刷前可选备份到 `{集合名}_{yyyyMMdd}`（入参 `projectId=`、`backupSuffix=` 可选）。
6. **写入补全**：`ActualProjectIdSaveListener` + `ActualProjectIdWriteEnricher` 在 Mongo save/insert 前按项目名反查 `project_info` 写入 `actual_project_id`。
7. **读路径改造**：各 Operation / Delegate 通过 `CommonHelper.criteriaForMongoProjectNameField*`、`projectNamesForMongoRead`、`resolvePlatformProjectName` 等统一查询；`majun.project.name.enabled=true` 时对同一平台名使用 `IN (平台名, majun名)` 双读。
8. **看板鉴权收敛**：删除 `CheckboardRepoAccessHelper` / `CheckboardRepoAccessService`，看板相关逻辑收拢到 `CheckboardDelegateImpl` 等既有路径（与更名无直接 HTTP 契约变化）。

## 不做什么

- 本仓 **不新增** 对外 REST 接口；不实现 framework 侧重命名编排或 Feign 回调入口（更名触发由 framework 投 MQ）。
- **不修改** `sensitive_check_rule_set` / `sensitive_task_rule_set` 的 majun Job 刷名范围（MQ 更名仍包含敏感词集合；majun 存量 Job 默认跳过这两集合）。
- 不追溯历史 PR 评论、外链中的旧项目名。

## 验收标准

- [x] framework 投递更名消息后，codecheck 消费成功：Mongo 注册集合项目名对齐 `project_info.project_name`，`actual_project_id` 写入正确，`inc_` Redis 完成迁移
- [x] `actualProjectIdBackfillJob` / `projectMajunNameMigrationJob` 支持 `projectId` 非法时快速失败（`handleFail`）
- [x] `ProjectRenameConsumer` 解析失败、校验失败记 ERROR 并跳过；拿不到锁抛异常便于 MQ 重投
- [x] `majun.project.name.enabled=false` 时 `getAdaptMajunProjectName` 返回原平台名，Mongo 读条件不再双读
- [x] `ProjectRenameServiceTest`、`CommonHelperTest`、`XxlJobHandlerMajunMigrationParamTest` 等单测覆盖主路径
- [x] 编译通过，相关单测通过
- [ ] 生产按发布清单执行：独立 vhost 队列声明、Job 注册、Nacos 开关切换顺序（见 design.md 发布说明）

## 影响范围

### 业务仓 `openlibing-codecheck`（PR !382，95 files，约 +3158 / -2577）

| 类别              | 代表文件                                                             | 操作    | 说明                                                   |
| ----------------- | -------------------------------------------------------------------- | ------- | ------------------------------------------------------ |
| 更名核心          | `business/projectrename/ProjectRenameService.java` 等                | 新增    | MQ 刷数、Redis 迁移、Job 刷 majun / 回填 id            |
| MQ 配置           | `common/config/rabbitmq/ProjectRenameRabbitConfig.java`              | 新增    | 独立连接工厂 + vhost 下声明更名队列                    |
| actual_project_id | `common/mongo/actualprojectid/*`                                     | 新增    | 注册表、写入 enricher、save 监听                       |
| 配置开关          | `MajunProjectNameSettings.java`、`ProjectRenameSettings.java`        | 新增    | Nacos `@RefreshScope`                                  |
| 读写在途          | `CommonHelper.java`、各 `*Operation.java`、部分 `*DelegateImpl.java` | 修改    | 双读、平台名解析、写侧平台名                           |
| 定时任务          | `common/job/XxlJobHandler.java`                                      | 修改    | 两个新 Job                                             |
| 看板              | `CheckboardDelegateImpl.java`；删除 `CheckboardRepoAccessHelper*`    | 修改/删 | 鉴权与查询路径调整                                     |
| 配置              | `application.yaml` / gama / prod                                     | 修改    | `spring.rabbitmq.codecheck.project_change_event_queue` |
| 测试              | `ProjectRenameServiceTest.java` 等                                   | 新增/改 | 单测与 mock 支撑                                       |

### docs 仓 `openlibing-docs`

| 文件                                                                          | 操作 |
| ----------------------------------------------------------------------------- | ---- |
| `spec/openlibing-codecheck/task_design/project-rename-adaptation/proposal.md` | 新增 |
| `spec/openlibing-codecheck/task_design/project-rename-adaptation/design.md`   | 新增 |
| `spec/openlibing-codecheck/task_design/project-rename-adaptation/tasks.md`    | 新增 |

## 关联 PR

- https://gitcode.com/openlibing/openlibing-codecheck/pull/382（分支 `feat/project-rename-adaptation-v6` → `release_20261029_iter2`，已合入）
