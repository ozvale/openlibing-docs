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
  → projectMajunNameMigrationJob：majun 社区名 → 平台名（**生产强制 Mongo 备份** + inc_ Redis；Redis !382 无自动备份）
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

| 场景                                                                 | 查询条件                                                                                       | 更新内容                                     |
| -------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------- | -------------------------------------------- |
| MQ 主路径（`match-by-actual-project-id=true` 或 legacy 首轮后按 id） | `actual_project_id == projectId`                                                               | 项目名字段 → 平台名 + 写 `actual_project_id` |
| MQ legacy（`match-by-actual-project-id=false`）首轮                  | 项目名字段 == 消息 `oldProjectName`                                                            | 同上                                         |
| majun Job / MQ majun 补刷                                            | 项目名字段 == majun 社区名（`mongoLegacyNameScope`）                                           | 同上                                         |
| majun Job 备份                                                       | **生产必传** `backupSuffix`；update 前 `find` 命中文档 insert 到 `{collection}_{backupSuffix}` | 原样含 `_id`；未传后缀则无备份、误刷难回滚   |

**静默漏刷**：`updateMulti` 匹配 0 行时 **不抛错、不 fail 消费**；Job/MQ 仍可能 overall success。`match-by-actual-project-id=true` 后，凡 **`actual_project_id` 缺失或与 `projectId` 不一致** 的文档不会被主路径更新；legacy 首轮若消息 `oldProjectName` 与库内冗名不一致（大小写、历史 majun 名、未双读到的别名），同样 **0 行**。见 §2.2.2、发布步骤 3b/5a。

敏感词集合：`SENSITIVE_CHECK_RULE_SET`、`SENSITIVE_TASK_RULE_SET` 参与 **MQ 更名**；**majun Job** 默认 `includeSensitive=false` **跳过**（!382 `projectMajunNameMigrationJob` 固定走该路径，无 Job 入参可改）。

**关闭 `majun.project.name.enabled` 的前置条件（与步骤 6 绑定）**

| 项                       | 要求                                                                                                                                                                                                                          |
| ------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 默认 majun Job（步骤 4） | 刷 **14** 个非敏感集合 + `inc_` Redis（注册表 16 − 敏感词 2）                                                                                                                                                                 |
| 敏感词两集合（步骤 4b）  | **须额外**以 `includeSensitive=true` 执行刷名（!382 需扩展 Job 入参如 `includeSensitive=true`，或等价一次性脚本/MQ 补刷）；**禁止**在未刷这两集合前关双读                                                                     |
| 「刷净」判据             | 对 `majun.project.name` 各映射项目，在 **注册表全部 16 集合**（与 §4.2 表格行数一致，**含** sensitive）抽样或 count：项目名字段等于 majun 社区名且 `actual_project_id` 归属该项目的文档数为 **0**（或工单认可的例外清单为空） |
| 失败后果                 | 仅执行默认 Job 即关 `majun.project.name.enabled` → 敏感词规则/任务规则仍存 majun 名 → 读路径只查平台名 → **规则集「丢失」/不生效**，Job 仍可能 success                                                                        |

### 2.2.1 majun Job：配置核对、试跑、备份与回滚

**配置风险**：`majun.project.name` 为 Nacos JSON（人工维护）。错映射、多写平台 key 或 majun 名写错时，Job 按「项目名字段 == majun 社区名」批量 `updateMulti`，会把**非本项目**文档刷成错误平台名；`migrateIncRedis` 可能覆盖/迁错 `inc_` 键。**无 Mongo 备份时几乎只能人工重建。**

| 阶段       | 运维要求                                                                                                                                                                                                                                                                        |
| ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 刷前核对   | 导出 JSON，逐条对照 `project_info`：平台名 key 存在、`project_id` 与业务确认一致；删除测试/过期映射；变更走工单并留档                                                                                                                                                           |
| 试跑       | 先 **`projectId={单项目}` + `backupSuffix=yyyyMMdd`** 执行步骤 4（及 4b）；执行前在各相关集合 **count**「项目名字段 == 该 majun 名」；执行后对照 Job/应用日志中的更新条数与 count **同量级**，并抽检文档 `actual_project_id`、平台名是否正确；通过后再去掉 `projectId` 分批全量 |
| 生产备份   | 步骤 **4 与 4b 均须** 同一 `backupSuffix`（如 `20261030_majun`）；**禁止**生产全量在未传 `backupSuffix` 时执行（!382 代码仍允许空后缀 → 见 Task 26 代码债）                                                                                                                     |
| Mongo 回滚 | 1）暂停后续 majun Job / 勿关双读；2）对每个 `{collection}_{backupSuffix}`：按 `_id` 将备份文档 **replaceOne/upsert** 写回主集合（恢复刷前快照）；3）按集合核对 count 与业务抽检；4）修正 Nacos 映射后 **新后缀** 再试跑                                                         |
| Redis 回滚 | !382 **无** Job 级 `inc_` 备份：误刷须依运维侧 **执行前 RDB/AOF 快照** 或已知键名手工 `GET`/`DEL`/`setList` 恢复；合入 Task 24 备份/合并策略后，Redis 回滚与 Mongo 同批次对齐                                                                                                   |

**代码现状（!382）**：`backupSuffix` 为空则跳过备份 insert，仍执行 `updateMulti` 与 `migrateIncRedis`。

### 2.2.2 更名刷数可观测性与残留校验

**问题**：发布清单若只验「消费者在线」「`actual_project_id` 覆盖率」，**无法**证明 MQ/Job 已对 **16 注册集合**逐集刷名成功；漏刷仅在业务侧表现为按**新**项目名查不到规则集/看板/汇总。

| 项                                   | 约定                                                                                                                                                                                                                                                                                              |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **目标日志（Task 28）**              | 每次 `applyRenameEvent` / majun `applyRename` 对 **每个参与集合** 输出：`projectId`、`eventId`（或 Job 批次）、`collection`、`modifiedCount`；若刷前运维/预检 count（旧平台名 / majun 名 / 消息 `oldProjectName`）**> 0** 而 `modifiedCount==0` → **WARN**（含匹配条件摘要），便于告警与排障      |
| **!382 现状**                        | 仅 `project rename apply finished, mongoModifiedApprox={total}` 汇总 INFO，**无分集合计数、无 0 行 WARN**                                                                                                                                                                                         |
| **发布后校验（步骤 5a，强制）**      | 对已完成更名的 `projectId`（或试跑更名项目），在 §4.2 **16 集合逐表**执行 count：项目名字段仍为 **旧平台名 / majun 社区名 / 消息 oldName**（按当前开关与历史映射分别统计）且文档仍属该项目的条数 **= 0**；与消费日志分集合 `modifiedCount` 交叉核对。非 0 **禁止**关 majun 双读或宣称该次更名闭环 |
| **开 `match-by=true` 前（步骤 3b）** | 对目标项目（或全量抽检）逐集合 count：`actual_project_id` 为空/缺失且项目名字段可关联到 `project_info` 的文档；非 0 须补跑回填或排查 bypass enrich 的写入（`updateMulti`、批量导入、其它服务直连 Mongo），**通过后再步骤 5**                                                                      |

**legacy 匹配提示**：步骤 5a 须覆盖「仅 id 匹配未命中、但冗名仍为旧值」的文档；不能只看 `actual_project_id` 覆盖率。

### 2.3 Redis（`migrateIncRedis`）

- 键模式：`inc_{社区名}`（List 语义，经 `RedisHelper.get` / `setList` / `del`）。
- 调用时机：`applyRename` 在 Mongo 刷名后执行 `migrateIncRedis(oldName, newName)`（MQ 更名与 majun Job 均会走到）。

**目标行为（运维与后续改造依据）**

| 步骤          | 约定                                                                                                                                                 |
| ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- |
| 读旧键        | `GET inc_{oldName}`，空则 `DEL` 旧键并返回                                                                                                           |
| 新键已存在    | **不得**用旧 payload 整表覆盖；须 **合并去重**（旧 List ∪ 新 List，按业务元素去重规则）或迁移前将新键备份为 `inc_{newName}_backup_{yyyyMMdd}` 再写回 |
| 写回          | 合并结果 `setList(inc_{newName})`，再 `DEL inc_{oldName}`                                                                                            |
| 与 Mongo 对齐 | Mongo majun Job 有 `{collection}_{backupSuffix}` 备份；Redis 侧应对等具备可恢复手段，避免「Mongo 有备份、Redis 破坏性覆盖」策略相反                  |

**PR !382 代码现状（缺陷）**：`migrateIncRedis` 在旧键非空时直接 `setList(newKey, oldPayload)`，**覆盖**新键已有 List，再删旧键；无合并、无备份。

**失败模式（改名窗口竞态）**

1. framework 更新 `project_info.project_name` → 新名生效，写路径开始向 `inc_{新名}` 写入增量数据。
2. MQ 更名消息稍后到达，执行迁移：用**旧键** payload **覆盖** `inc_{新名}`。
3. 步骤 1 已写入的增量条目丢失；旧键删除后无副本 → Redis 与 Mongo 不一致，规则集/增量汇总读 Redis 缺数据。
4. 仅「运维手工核对 List」**无法恢复**已覆盖数据，只能事后发现。

**验收/改造**：合入合并或备份逻辑后，单测覆盖「新键先有数据 + 旧键有数据 → 合并后两者元素均保留」。

### 2.4 看板仓可见性 / 读权限（与 PR !381 对齐）

**背景**：同迭代 `release_20261029_iter2` 中 !381 引入 `CheckboardRepoAccessHelper` / `CheckboardRepoAccessService` 统一免登录看板链路的仓校验；!382 **删除上述类**并将部分逻辑留在 `CheckboardDelegateImpl` 旧方法（如 `fullIsOpenSourceRepo` / `incIsOpenSourceRepo` / `fullDetailAuth`）或其它入口。**文档约定**：无论类是否删除，网关免登录白名单不变时，下列入口的 **4001 / 403 / 50001** 分支必须与 [fix-checkboard-repo-visibility-auth](../fix-checkboard-repo-visibility-auth/design.md) §2 入口表一致（匿名仅对外可见仓；**visibility 判定须 §2.3 单一 `isExternallyVisible`，禁止全量/MR 分叉**；已登录走 Feign 仓读）。

| 类别     | HTTP / 调用链                                             | !381 校验点                      | 必测分支                                     |
| -------- | --------------------------------------------------------- | -------------------------------- | -------------------------------------------- |
| 统计     | `GET …/getDetailNum`（`type=harmony_full`，summaryId）    | `assertFullSummaryAccess`        | 匿名 + 私有 → 4001；有 userId 无读权限 → 403 |
| 统计     | `GET …/getDetailNum`（`type=harmony_inc`，uuid + taskId） | `assertIncAccess`                | MR uuid 路径同上（**易漏**）                 |
| 趋势     | `GET …/getFullTaskTrend`                                  | `assertFullTaskAccess`           | 匿名私有 task → 4001                         |
| 任务详情 | `getTaskResultDetails`                                    | 查询前 `assertFullSummaryAccess` | 私有 summary 未授权 → 4001/403               |
| 导出     | `FileDownLoadController` 提交 Excel 任务                  | `assertExportAccess`             | checkType=mr 走 uuid 分支，非 mr 走 summary  |
| 导出     | `getExcelStatus` / `exportDetailToFile`                   | `assertExportAccessByRecordKey`  | 先解析 ExportRecord 再分流                   |

**单测迁移要求（Task 27）**

| 原 !381 资产                                                                            | 迁移目标                                                                       |
| --------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------ |
| `CheckboardRepoAccessHelperTest`（全量/MR/导出分流、recordKey、repo 缺失 fail-open 等） | 收拢后实现类上的等价单测（Delegate 私有方法可经入口方法或 package 可见性覆盖） |
| `CheckboardDelegateImplTest` 中对 Helper 的 mock/verify                                 | 改为断言 **4001/403** 或对内联校验逻辑的 mock                                  |
| `FileDownLoadControllerTest` / `ExcelReportImplTest` 导出前校验                         | 删除 Service 后仍须 verify 校验在 Controller/Impl 层执行                       |

**PR !382 代码现状（鉴权缺口，发布前须闭合 Task 27）**

对照 !381 合入态，!382 至少存在：**`getDetailNum` 未再调用 summary/MR 仓校验且 Controller 去掉 query `userId`**；**`getFullTaskTrend` 无 task 维度校验**；**`getTaskResultDetails` 未在查询前 assert 全量 summary**；**导出链路移除 `CheckboardRepoAccessService`，`getExcelStatus` / 异步导出提交未再 assert**；**`fullIsOpenSourceRepo` / `incIsOpenSourceRepo` 仍保留 §2.3（fix-checkboard）字面量 vs 常量分叉**。网关白名单不变时，上述缺口会导致 **私有仓看板/导出对匿名重新开放**。Task 13 仅表示「删类 + 合流改动已合入」，**不等于**安全验收通过。

### 2.5 读路径（CommonHelper）

- `resolvePlatformProjectName(anyName, projectId)`：有 `projectId` 优先查库；否则 majun 反查平台名。
- `projectNamesForMongoRead(platformName)`：`majun.project.name.enabled=false` 仅平台名；`true` 时 `[平台名, majun名]` 去重。
- `criteriaForMongoProjectNameField` / `criteriaForMongoProjectNameFieldResolved`：单名 `is`，双名 `in`。
- `getAdaptMajunProjectName`：受 `majun.project.name.enabled` 控制；Job 列举映射用 `listMajunMigrationMappingsForJob`（不受 enabled 影响）。

### 2.6 Rabbit 连接与 TLS

`ProjectRenameRabbitConfig` 使用 `framework.rabbitmq.*` 凭证 + `rabbitmq.vhost`（与 framework 更名事件 vhost 一致），**独立** `CachingConnectionFactory` 与 `projectRenameRabbitListenerContainerFactory`；启动时用 `RabbitAdmin` 在 **该 vhost** 幂等声明 durable 队列（避免主 vhost 的 `RabbitAdmin` 误声明）。

**目标行为（上线与运维依据）**

| 项   | 约定                                                                                                                |
| ---- | ------------------------------------------------------------------------------------------------------------------- |
| 默认 | TLS **开启服务端证书校验**（信任 RabbitMQ 平台 CA / truststore）                                                    |
| 例外 | 仅当 Nacos 显式打开 **`project.rename.rabbit.tls.skip-verify=true`** 时，才允许 `useTlsWithNoVerification()` 类行为 |
| 禁止 | 不得将「prod profile 即跳过校验」作为长期默认；该开关 **默认 false**，且须登记到期关闭                              |

**PR !382 代码现状（技术债）**：`ProjectRenameRabbitConfig` 在 `spring.profiles.active=prod` 时**硬编码** `useTlsWithNoVerification()`，无上述 Nacos 开关。文档以开关模型为**应达成配置**；合入后须排期改为可配置且默认严格校验，并在 CA 落地后关闭 skip 开关。

**跳过校验时的失败模式**：TLS 仍加密信道，但不验证 broker 身份 → 同网段 ARP/DNS 劫持或指向伪装 broker 时，中间人可**读取或篡改**更名 JSON（含 projectId、old/new 项目名），Consumer 按消息刷 Mongo/Redis → **项目名被污染**，非单纯泄露。

## 3. 类设计

| 类                                  | 职责                                                                                         |
| ----------------------------------- | -------------------------------------------------------------------------------------------- |
| `ProjectRenameMessageDTO`           | MQ 消息体：eventType、eventId、projectId、old/newProjectName、publishedAt（ISO-8601 字符串） |
| `ProjectRenameConsumer`             | `@RabbitListener`，锁 + 调用 Service                                                         |
| `ProjectRenameService`              | validate、applyRenameEvent、backfillActualProjectIds、migrateMajunNames、Mongo/Redis 底层    |
| `ActualProjectIdCollectionRegistry` | **16** 集合 → 项目名字段名映射（与 !382 源码 `collectionToNameField()` 条目数一致）          |
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

**计数口径（与业务仓 `ActualProjectIdCollectionRegistry` 一致）**

| 口径                                       | 数量   | 说明                                                                                                         |
| ------------------------------------------ | ------ | ------------------------------------------------------------------------------------------------------------ |
| 注册表总行数                               | **16** | 下表每一行对应一条 `map.put`；MQ 更名、`actualProjectIdBackfillJob`、save enrich **均遍历全部 16 集合**      |
| majun Job 默认（`includeSensitive=false`） | **14** | 跳过 `sensitive_check_rule_set`、`sensitive_task_rule_set`；步骤 4b 须 `includeSensitive=true` 补刷该 2 集合 |
| Redis `inc_*`                              | 非集合 | 不在本表计数；更名/MQ/majun Job 另走 `migrateIncRedis`                                                       |

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

| 类型    | 名称                                                   | 说明                                                                                                |
| ------- | ------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| MQ 消费 | `spring.rabbitmq.codecheck.project_change_event_queue` | 入参：上表 JSON 字符串；出参：无（副作用写 Mongo/Redis）                                            |
| xxl-job | `actualProjectIdBackfillJob`                           | 入参：`projectId=123`（可选）；出参：调度中心 success/fail 文案含 updated 计数                      |
| xxl-job | `projectMajunNameMigrationJob`                         | 入参：`projectId=`（试跑可选）、**`backupSuffix=`（生产必填，见 §2.2.1）**；出参：success/fail 文案 |

## 7. 安全设计

鉴权：继承原有鉴权逻辑

敏感信息：不打印日志，不明文存储数据库，不可下载

硬编码：appkey，token，cookie不写在代码中

审计日志：操作记录可追溯

---

## 配置项

| 配置键                                                 | 默认                                                              | 说明                                                                                 |
| ------------------------------------------------------ | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------ |
| `spring.rabbitmq.codecheck.project_change_event_queue` | 各环境 `project_change_event_codecheck_queue_{beta\|gamma\|prod}` | 监听队列名                                                                           |
| `rabbitmq.vhost`                                       | Nacos                                                             | framework 更名事件 vhost，与 `ProjectRenameRabbitConfig` 一致                        |
| `framework.rabbitmq.username/password/ip/port`         | Nacos 密文                                                        | 更名专用连接                                                                         |
| `project.rename.match-by-actual-project-id`            | `false`                                                           | 回填完成后改为 `true`                                                                |
| `majun.project.name.enabled`                           | `true`                                                            | 关闭后读路径与 MQ majun 补刷停用                                                     |
| `majun.project.name`                                   | JSON 对象                                                         | 平台名 → majun 名；Job 刷数仍读取                                                    |
| `project.rename.rabbit.tls.skip-verify`                | **`false`（强制默认）**                                           | 仅 CA/truststore 未就绪的短期例外置 `true`；CA 落地后必须改回 `false` 并重启/Refresh |

## 发布与运维顺序（建议）

1. 部署含 `ProjectRenameRabbitConfig` 的版本，确认目标 vhost 下队列已声明、消费者在线。
2. **RabbitMQ CA / truststore**：在 prod 执行机或镜像内导入平台 CA；确认更名专用连接 factory **未**开启 skip-verify（`project.rename.rabbit.tls.skip-verify=false`）。若 !382 仍为 prod 硬编码 skip，须先合入「开关 + 默认 false」再视为本步骤完成。
3. 注册并试跑 `actualProjectIdBackfillJob`（可先单 `projectId`），确认 `actual_project_id` 覆盖率。
   3b. **（步骤 5 前必过）** 对将开 `match-by-actual-project-id` 的项目（或抽检项目），在 **16 注册集合**逐表 count 仍缺 `actual_project_id` 且冗名可关联 `project_info` 的文档（§2.2.2）；非 0 → 补回填 / 查 bypass enrich 写入源，**不得**仅因 Job success 进入步骤 5。
4. **刷前**：核对 `majun.project.name`（§2.2.1）→ 单项目试跑 + 命中 count 核对 → 注册并执行 `projectMajunNameMigrationJob`，**必传** `backupSuffix=yyyyMMdd`（步骤 4/4b 共用同一后缀），全量或分批 `projectId` — **默认仅非敏感集合 + Redis**。
   4b. **（关闭 majun 双读前必做）** 对 `sensitive_check_rule_set`、`sensitive_task_rule_set` 以 **`includeSensitive=true`** 再跑一轮 majun 刷名（**同样必传 `backupSuffix`**；须 Job 支持该入参或等价运维手段；!382 无此入参则先合入再执行）。
   4c. **刷净校验**：按 §2.2 判据确认 16 集合无 majun 社区名残留（留存则不得进入步骤 6）。
5. Nacos 将 `project.rename.match-by-actual-project-id` 置为 `true`（**须 3b 已通过**）。
   5a. **更名闭环校验**：framework 试跑或生产更名完成后，对受影响 `projectId` 在 **16 集合**按 §2.2.2 统计旧平台名 / majun 名 / 消息 `oldProjectName` **残留 = 0**；核对 MQ/Job 日志分集合 `modifiedCount`（合入 Task 28 后）；有残留或「预检 count>0 但 modified=0」的 WARN → 暂停后续步骤、排查漏刷。
6. **仅当 4c 与（若已发生更名）5a 通过**：将 `majun.project.name.enabled` 置为 `false`，并计划移除 `majun.project.name` 配置（代码仍兼容空配置）。
7. **（强制收尾）** CA 就绪后：Nacos 设 `project.rename.rabbit.tls.skip-verify=false` → 滚动重启 codecheck → 回归：更名 MQ 消费正常、连接日志无 certificate 错误、**步骤 5a 对试跑 projectId 通过**（不得仅「抽检一条」而无分集合残留 count）。

## 风险与缓解

| 风险                                                      | 缓解                                                                                                                        |
| --------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| 校验失败 / 坏消息被 ack 跳过                              | 结构化 ERROR 日志含 eventId、projectId；同步逻辑可对照 framework 重放                                                       |
| 未回填 `actual_project_id` 时 MQ 按 id 匹配更新 0 行      | 步骤 **3b** 逐集合缺 id count；默认 `match-by=false` 过渡；Task 28 分集合 WARN                                              |
| `updateMulti` 0 行静默漏刷（id/legacy 名不匹配）          | 步骤 **5a** 逐集合旧名/majun 残留 count；Task 28 预检 count>0 且 modified=0 → WARN                                          |
| majun Job 误刷                                            | 刷前 §2.2.1 配置核对 + 单项目试跑；**生产强制 `backupSuffix`**；Mongo 按备份集合 `_id` 回滚                                 |
| 未传 `backupSuffix` 仍全量刷                              | 清单禁止；Task 26 代码债：prod 空后缀 `handleFail`                                                                          |
| 默认 majun Job 后关 `majun.enabled` 未刷 sensitive 两集合 | 步骤 4b + 4c 强制；Job 增加 `includeSensitive=true` 入参（代码债）                                                          |
| Redis `inc_` 迁移覆盖新键                                 | !382 用旧 payload 覆盖 `inc_{新名}`，改名窗口内增量丢失；**目标**：合并去重或迁移前备份新键；单测 + 回归更名窗口            |
| Rabbit TLS 跳过服务端证书校验（skip-verify）              | **默认禁止**；仅短期例外 + 工单/发布单跟踪；CA 导入后步骤 7 强制关闭并回归；中间人可篡改更名消息导致 Mongo/Redis 项目名污染 |
| !382 prod 硬编码 skip-verify                              | 排期改为 `project.rename.rabbit.tls.skip-verify` 控制，默认 false                                                           |
| 删 Helper 后看板/导出漏校验                               | §2.4 入口表 + Task 27 单测/联调；闭合前不得宣称 !381 安全修复生效                                                           |

## 跨仓影响

- **依赖 framework** 在项目更名后向约定队列投递 JSON（字段与 SCA `ProjectChangeListener` 同类约定）。
- **同 release !381**：看板鉴权 spec `fix-checkboard-repo-visibility-auth`；!382 删 Helper 后须 **行为不退化**（§2.4）。
- coderepo / cicd 更名能力不在本 PR 范围；codecheck 仅消费本服务队列并治理本仓 Mongo/Redis。
