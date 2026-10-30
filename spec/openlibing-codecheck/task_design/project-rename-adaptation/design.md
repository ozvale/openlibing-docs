# project-rename-adaptation — 技术设计

## 1. 方案设计

codecheck 侧以 **MQ 异步刷数 + xxl-job 存量治理 + 读路径双读过渡** 落地项目更名与 majun 名下线：

```
framework（项目更名后投 MQ）
  → 队列 spring.rabbitmq.codecheck.project_change_event_queue（独立 rabbitmq.vhost）
    → ProjectRenameConsumer（Redisson 锁 codecheck:project_rename:lock:{projectId}）
        → ProjectRenameService.applyRenameEvent
            → 以 project_info.project_name 为写入目标
            → Mongo：ActualProjectIdCollectionRegistry 各集合 updateMulti
            → Redis：migrateIncRedis(旧名, 新名)
            → majun.enabled 时可选补刷（旧平台名 / majun 社区名）

运维 / 存量
  → actualProjectIdBackfillJob：补齐 actual_project_id
  → projectMajunNameMigrationJob：majun 社区名 → 平台名（Mongo 可备份 + inc_ Redis）
  → Nacos：project.rename.match-by-actual-project-id、majun.project.name.enabled
```

写路径新增 **save 前 enrich**：对注册集合文档按项目名反查 `project_info` 写入 `actual_project_id`，降低 MQ 按 id 刷数时的漏匹配。

## 2. 实现逻辑设计

### 2.1 MQ 消费

| 步骤     | 行为                                                                                                                |
| -------- | ------------------------------------------------------------------------------------------------------------------- |
| 反序列化 | `ProjectRenameMessageDTO`，`@JsonIgnoreProperties(ignoreUnknown = true)` 容忍未知字段                               |
| 校验     | `projectId`、old/new 项目名非空且不等；`project_info` 存在且 `project_name` 非空                                    |
| 加锁     | `tryLock(3s, lease=-1)`，失败抛 `IllegalStateException` 触发重投                                                    |
| 二次校验 | 持锁后再 `validate`，避免并发下状态变化                                                                             |
| 执行     | `applyRenameEvent`：写入目标 **始终** 取库内 `project_info.project_name`（消息 `newProjectName` 与库不一致仅 warn） |

非法 JSON、校验失败：**记 ERROR 后 return**（不重投）；中断/未拿到锁：**抛异常** 重投。

### 2.2 Mongo 刷名条件

| 场景                                                                 | 查询条件                                                          | 更新内容                                     |
| -------------------------------------------------------------------- | ----------------------------------------------------------------- | -------------------------------------------- |
| MQ 主路径（`match-by-actual-project-id=true` 或 legacy 首轮后按 id） | `actual_project_id == projectId`                                  | 项目名字段 → 平台名 + 写 `actual_project_id` |
| MQ legacy（`match-by-actual-project-id=false`）首轮                  | 项目名字段 == 消息 `oldProjectName`                               | 同上                                         |
| majun Job / MQ majun 补刷                                            | 项目名字段 == majun 社区名（`mongoLegacyNameScope`）              | 同上                                         |
| majun Job 备份                                                       | update 前 `find` 命中文档 insert 到 `{collection}_{backupSuffix}` | 原样含 `_id`                                 |

敏感词集合：`SENSITIVE_CHECK_RULE_SET`、`SENSITIVE_TASK_RULE_SET` 参与 **MQ 更名**；**majun Job** 默认 `includeSensitive=false` 跳过。

### 2.3 Redis

- 键模式：`inc_{社区名}`（List 结构，经 `RedisHelper.get/setList/del`）。
- 迁移：新键已有内容时仍用旧键 payload 覆盖写入，再删旧键。

### 2.4 读路径（CommonHelper）

- `resolvePlatformProjectName(anyName, projectId)`：有 `projectId` 优先查库；否则 majun 反查平台名。
- `projectNamesForMongoRead(platformName)`：`majun.project.name.enabled=false` 仅平台名；`true` 时 `[平台名, majun名]` 去重。
- `criteriaForMongoProjectNameField` / `criteriaForMongoProjectNameFieldResolved`：单名 `is`，双名 `in`。
- `getAdaptMajunProjectName`：受 `majun.project.name.enabled` 控制；Job 列举映射用 `listMajunMigrationMappingsForJob`（不受 enabled 影响）。

### 2.5 Rabbit 连接

`ProjectRenameRabbitConfig` 使用 `framework.rabbitmq.*` 凭证 + `rabbitmq.vhost`（与 framework 更名事件 vhost 一致），**独立** `CachingConnectionFactory` 与 `projectRenameRabbitListenerContainerFactory`；启动时用 `RabbitAdmin` 在 **该 vhost** 幂等声明 durable 队列（避免主 vhost 的 `RabbitAdmin` 误声明）。

生产环境（`spring.profiles.active=prod`）连接 Rabbit 使用 `useTlsWithNoVerification()`（待 RabbitMQ CA 配置后可恢复校验）。

## 3. 类设计

| 类                                  | 职责                                                                                         |
| ----------------------------------- | -------------------------------------------------------------------------------------------- |
| `ProjectRenameMessageDTO`           | MQ 消息体：eventType、eventId、projectId、old/newProjectName、publishedAt（ISO-8601 字符串） |
| `ProjectRenameConsumer`             | `@RabbitListener`，锁 + 调用 Service                                                         |
| `ProjectRenameService`              | validate、applyRenameEvent、backfillActualProjectIds、migrateMajunNames、Mongo/Redis 底层    |
| `ActualProjectIdCollectionRegistry` | 15 集合 → 项目名字段名映射                                                                   |
| `ActualProjectIdWriteEnricher`      | save 前补 `actual_project_id`                                                                |
| `ActualProjectIdSaveListener`       | 挂接 Mongo 保存链路                                                                          |
| `ProjectRenameSettings`             | `project.rename.match-by-actual-project-id`                                                  |
| `MajunProjectNameSettings`          | `majun.project.name.enabled`                                                                 |
| `ProjectRenameRabbitConfig`         | 更名专用 Rabbit 连接与队列声明                                                               |
| `CommonHelper`                      | 双读 Criteria、平台名解析、majun 映射查询                                                    |
| `XxlJobHandler`                     | `actualProjectIdBackfillJob`、`projectMajunNameMigrationJob`                                 |

## 4. 数据模型设计

### 4.1 Mongo 新增字段

| 字段                | 类型    | 说明                                                                |
| ------------------- | ------- | ------------------------------------------------------------------- |
| `actual_project_id` | Integer | 与 `project_info.project_id` 一致；MQ 按 id 刷名、回填 Job 目标字段 |

### 4.2 更名涉及集合（注册表）

| 集合                        | 项目名字段     |
| --------------------------- | -------------- |
| `codecheck_rule_set`        | `account`      |
| `codecheck_rule_set_pro`    | `project_name` |
| `rule_set_list_info`        | `project_name` |
| `sig_rule_set`              | `project_name` |
| `sin_info`                  | `project_name` |
| `branch_repo`               | `project_name` |
| `project_domain`            | `project_name` |
| `task_inc_result_summary`   | `projectName`  |
| `task_result_summary`       | `projectName`  |
| `code_check_task`           | `projectName`  |
| `task_inc`                  | `projectName`  |
| `codecheck_task_inc_error`  | `projectName`  |
| `codecheck_task_full_error` | `projectName`  |
| `task_alarm_email_log`      | `projectName`  |
| `sensitive_check_rule_set`  | `project_name` |
| `sensitive_task_rule_set`   | `project_name` |

### 4.3 MQ 消息体（消费侧）

| 字段           | 类型    | 必填 | 说明                                    |
| -------------- | ------- | ---- | --------------------------------------- |
| eventType      | String  | 否   | 与 framework 约定（如项目更名），日志用 |
| eventId        | String  | 否   | 幂等排查                                |
| projectId      | Integer | 是   | 平台项目 id                             |
| oldProjectName | String  | 是   | 刷数匹配旧冗名                          |
| newProjectName | String  | 是   | 消息侧新名（执行仍以库内当前名为准）    |
| publishedAt    | String  | 否   | ISO-8601 带时区                         |

### 4.4 MySQL

`ProjectInfoEntity` / `ProjectInfoMapper` 沿用 `project_id`、`project_name`；刷数与 enrich 均以其为权威。

## 5. 性能设计

- Mongo 刷名与回填均使用 **`updateMulti` + 索引友好条件**（按 `actual_project_id` 或项目名字段），避免按文档逐条 find 反查 MySQL。
- 回填 Job 以 `project_info` 全表（或单 projectId）驱动，对每个集合批量更新缺失 id 的文档。
- MQ 消费 `concurrency = 1-4`，同项目 Redisson 锁串行，避免并发写同一项目 Mongo。
- majun 全量 Job 对映射表顺序执行，按 `projectId` 去重，防止重复刷同一项目。

## 6. API 接口设计

本需求 **不新增、不修改** 对外 HTTP API 路径与契约。与外部协作的接口形态为：

| 类型    | 名称                                                   | 说明                                                                           |
| ------- | ------------------------------------------------------ | ------------------------------------------------------------------------------ |
| MQ 消费 | `spring.rabbitmq.codecheck.project_change_event_queue` | 入参：上表 JSON 字符串；出参：无（副作用写 Mongo/Redis）                       |
| xxl-job | `actualProjectIdBackfillJob`                           | 入参：`projectId=123`（可选）；出参：调度中心 success/fail 文案含 updated 计数 |
| xxl-job | `projectMajunNameMigrationJob`                         | 入参：`projectId=`、`backupSuffix=`（均可选）；出参：success/fail 文案         |

## 7. 安全设计

鉴权：继承原有鉴权逻辑

敏感信息：不打印日志，不明文存储数据库，不可下载

硬编码：appkey，token，cookie不写在代码中

审计日志：操作记录可追溯

---

## 配置项

| 配置键                                                 | 默认                                                              | 说明                                                          |
| ------------------------------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------- |
| `spring.rabbitmq.codecheck.project_change_event_queue` | 各环境 `project_change_event_codecheck_queue_{beta\|gamma\|prod}` | 监听队列名                                                    |
| `rabbitmq.vhost`                                       | Nacos                                                             | framework 更名事件 vhost，与 `ProjectRenameRabbitConfig` 一致 |
| `framework.rabbitmq.username/password/ip/port`         | Nacos 密文                                                        | 更名专用连接                                                  |
| `project.rename.match-by-actual-project-id`            | `false`                                                           | 回填完成后改为 `true`                                         |
| `majun.project.name.enabled`                           | `true`                                                            | 关闭后读路径与 MQ majun 补刷停用                              |
| `majun.project.name`                                   | JSON 对象                                                         | 平台名 → majun 名；Job 刷数仍读取                             |

## 发布与运维顺序（建议）

1. 部署含 `ProjectRenameRabbitConfig` 的版本，确认目标 vhost 下队列已声明、消费者在线。
2. 注册并试跑 `actualProjectIdBackfillJob`（可先单 `projectId`），确认 `actual_project_id` 覆盖率。
3. 注册 `projectMajunNameMigrationJob`，生产建议带 `backupSuffix`，全量或分批 `projectId`。
4. Nacos 将 `project.rename.match-by-actual-project-id` 置为 `true`。
5. majun 存量刷净后，将 `majun.project.name.enabled` 置为 `false`，并计划移除 `majun.project.name` 配置（代码仍兼容空配置）。

## 风险与缓解

| 风险                                                 | 缓解                                                                    |
| ---------------------------------------------------- | ----------------------------------------------------------------------- |
| 校验失败 / 坏消息被 ack 跳过                         | 结构化 ERROR 日志含 eventId、projectId；同步逻辑可对照 framework 重放   |
| 未回填 `actual_project_id` 时 MQ 按 id 匹配更新 0 行 | 默认 `match-by-actual-project-id=false` 过渡；Job 回填后再开 true       |
| majun Job 误刷                                       | 单项目模式校验 projectId；全量按配置 key 严格匹配平台名；Mongo 备份集合 |
| Redis `inc_` 迁移冲突                                | 日志记录 oldKey/newKey；新键覆盖策略明确，运维可手工核对 List 内容      |
| 生产 Rabbit TLS 无证书校验                           | 临时 `useTlsWithNoVerification`；CA 就绪后改回严格校验                  |

## 跨仓影响

- **依赖 framework** 在项目更名后向约定队列投递 JSON（字段与 SCA `ProjectChangeListener` 同类约定）。
- coderepo / cicd 更名能力不在本 PR 范围；codecheck 仅消费本服务队列并治理本仓 Mongo/Redis。
