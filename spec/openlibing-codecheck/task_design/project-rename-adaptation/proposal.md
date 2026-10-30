# project-rename-adaptation

## 需求背景

平台 `project_info.project_name` 变更后，codecheck 侧 Mongo / Redis 仍大量冗余存储 `project_name`、`projectName`、`account` 等社区名；与母表不一致时，规则集、看板、增量汇总、屏蔽等功能会出现查不到数据或写到错误项目名下的问题。

历史上 codecheck 通过 Nacos 配置 `majun.project.name`（JSON：平台名 → majun 社区名）在读写路径做名称映射。本 PR 在保留可配置开关的前提下，补齐三件事：

1. **消费 framework 项目更名 MQ**，按 `project_info` 当前名刷 Mongo 冗名字段并迁移 `inc_{社区名}` Redis；
2. **引入 `actual_project_id`**，写入时补全、Job 回填，MQ 刷数优先按 id 定位文档；
3. **读路径统一经 `CommonHelper` 解析平台名 + majun 双读**，写路径逐步以平台项目名为准；提供 xxl-job 做 majun 存量刷名与 id 回填。

## 功能描述

1. **MQ 消费**：`ProjectRenameConsumer` 监听 `spring.rabbitmq.codecheck.project_change_event_queue`，解析 `ProjectRenameMessageDTO`，Redisson 按 `projectId` 加锁后调用 `ProjectRenameService.applyRenameEvent`。
2. **更名刷数**：在 `ActualProjectIdCollectionRegistry` 注册的 **16** 个 Mongo 集合（见 design.md §4.2，**含**敏感词两集合）上，MQ `updateMulti` 更新项目名字段与 `actual_project_id`；同步 `migrateIncRedis`（`inc_旧名` → `inc_新名`，**目标**为合并去重或备份后迁移，见 design.md §2.3；!382 实现为覆盖写，属已知缺陷）。**majun 存量 Job 默认跳过敏感词 2 集合，仅刷 14 个非敏感集合**（计数口径见 §4.2 说明）。
3. **匹配策略（Nacos 可刷新）**：
   - `project.rename.match-by-actual-project-id=false`（默认）：MQ 首轮按消息 `oldProjectName` 匹配项目名字段（回填 Job 完成前）；
   - `true`：Mongo 更新条件仅 `actual_project_id == projectId`。
4. **majun 开关 `majun.project.name.enabled`**：`false` 时读路径不再双读、MQ 不走 majun 补刷；`true` 且存量未刷净时，MQ 在首轮刷写后按消息旧平台名 / majun 社区名追加 Mongo 刷写并迁移 majun 对应 `inc_` 键。
5. **xxl-job**：
   - `actualProjectIdBackfillJob`：按 `project_info` 驱动，为注册集合缺失 `actual_project_id` 的文档补 id（入参 `projectId=` 可选）；
   - `projectMajunNameMigrationJob`：按 `majun.project.name` 配置将 Mongo 与 Redis 从 majun 名刷成平台名；**默认 `includeSensitive=false`，不刷** `sensitive_check_rule_set` / `sensitive_task_rule_set`（见 design.md §2.2、发布步骤 4b）。**生产执行须带 `backupSuffix=yyyyMMdd`**（与步骤 4/4b 同后缀），Job 在 `updateMulti` 前将命中文档写入 `{集合名}_{backupSuffix}`；`projectId=` 可选（试跑单项目）。备份、试跑、回滚见 design.md §2.2.1。
6. **写入补全**：`ActualProjectIdSaveListener` + `ActualProjectIdWriteEnricher` 在 Mongo save/insert 前按项目名反查 `project_info` 写入 `actual_project_id`。
7. **读路径改造**：各 Operation / Delegate 通过 `CommonHelper.criteriaForMongoProjectNameField*`、`projectNamesForMongoRead`、`resolvePlatformProjectName` 等统一查询；`majun.project.name.enabled=true` 时对同一平台名使用 `IN (平台名, majun名)` 双读。
8. **看板鉴权结构调整（同 release 与 !381 叠加）**：删除 `CheckboardRepoAccessHelper` / `CheckboardRepoAccessService`，将仓可见性 + Feign 读权限校验收拢到 `CheckboardDelegateImpl` 等调用链。**HTTP 路径与 query 形态不因更名而变，但对外安全语义必须与 [fix-checkboard-repo-visibility-auth](../fix-checkboard-repo-visibility-auth/proposal.md)（!381）一致**——删除集中类不等于取消校验；见 design.md §2.4、Task 27。

## 不做什么

- 本仓 **不新增** 对外 REST 接口；不实现 framework 侧重命名编排或 Feign 回调入口（更名触发由 framework 投 MQ）。
- **不修改** `sensitive_check_rule_set` / `sensitive_task_rule_set` 的 majun Job 刷名范围（MQ 更名仍包含敏感词集合；majun 存量 Job 默认跳过这两集合）。
- 不追溯历史 PR 评论、外链中的旧项目名。
- **不削弱** !381 已落地的看板/导出仓可见性与仓读权限校验（见 §2.4；!382 若漏入口须补全后再发布）。

## 验收标准

- [x] framework 投递更名消息后，codecheck 消费成功：Mongo 注册集合项目名对齐 `project_info.project_name`，`actual_project_id` 写入正确
- [ ] **`migrateIncRedis`**：新键已有数据时与旧键 **合并去重**（或备份后迁移），不得覆盖丢失改名窗口内已写入 `inc_{新名}` 的增量；!382 覆盖行为须改造后勾选
- [x] `actualProjectIdBackfillJob` / `projectMajunNameMigrationJob` 支持 `projectId` 非法时快速失败（`handleFail`）
- [x] `ProjectRenameConsumer` 解析失败、校验失败记 ERROR 并跳过；拿不到锁抛异常便于 MQ 重投
- [x] `majun.project.name.enabled=false` 时 `getAdaptMajunProjectName` 返回原平台名，Mongo 读条件不再双读
- [x] `ProjectRenameServiceTest`、`CommonHelperTest`、`XxlJobHandlerMajunMigrationParamTest` 等单测覆盖主路径
- [ ] **看板鉴权（!381 等价）**：删除 Helper/Service 后，下列入口行为与 `fix-checkboard-repo-visibility-auth` 一致——匿名 + 私有仓 → **4001**；网关注入 `userId` 无仓读权限 → **403**；公开/开源仓匿名可访问（见 design.md §2.4 入口表）
- [ ] **看板鉴权单测**：`CheckboardRepoAccessHelperTest` 等价场景已迁移至 `CheckboardDelegateImplTest` / Controller / 导出单测（含 `getDetailNum` 全量/MR 分支、`getFullTaskTrend`、`getTaskResultDetails`、`assertExportAccess` / `assertExportAccessByRecordKey` 的 4001/403）
- [x] 编译通过，相关单测通过
- [ ] 生产 majun 刷名（步骤 4/4b）：**已传 `backupSuffix` 且备份集合可核对**；单项目试跑命中条数与预期一致后再全量；误刷可按 design.md §2.2.1 回滚 Mongo
- [ ] **更名可观测性（Task 28）**：MQ/Job 分集合 `modifiedCount` 日志；预检 count>0 且 modified=0 时 WARN
- [ ] 生产按发布清单执行（见 design.md 发布顺序）；**步骤 3b / 5a** 逐 **16** 注册集合校验通过；**关闭 `majun.project.name.enabled` 前**须完成敏感词两集合刷名 + 「刷净」校验（步骤 4b、6 前置）
- [ ] **Rabbit TLS**：prod truststore/CA 已配置；`project.rename.rabbit.tls.skip-verify=false`（或等效严格校验）；完成 design.md 发布步骤 7 回归
- [ ] **（若 !382 仍为 prod 硬编码 skip）** 合入可配置开关并去掉 profile 硬编码后，再勾选上一项

## 影响范围

### 业务仓 `openlibing-codecheck`（PR !382，95 files，约 +3158 / -2577）

| 类别              | 代表文件                                                             | 操作    | 说明                                                                                    |
| ----------------- | -------------------------------------------------------------------- | ------- | --------------------------------------------------------------------------------------- |
| 更名核心          | `business/projectrename/ProjectRenameService.java` 等                | 新增    | MQ 刷数、Redis 迁移、Job 刷 majun / 回填 id                                             |
| MQ 配置           | `common/config/rabbitmq/ProjectRenameRabbitConfig.java`              | 新增    | 独立连接工厂 + vhost 队列；!382 prod 硬编码 TLS skip（须改为 Nacos 开关，默认严格校验） |
| actual_project_id | `common/mongo/actualprojectid/*`                                     | 新增    | 注册表、写入 enricher、save 监听                                                        |
| 配置开关          | `MajunProjectNameSettings.java`、`ProjectRenameSettings.java`        | 新增    | Nacos `@RefreshScope`                                                                   |
| 读写在途          | `CommonHelper.java`、各 `*Operation.java`、部分 `*DelegateImpl.java` | 修改    | 双读、平台名解析、写侧平台名                                                            |
| 定时任务          | `common/job/XxlJobHandler.java`                                      | 修改    | 两个新 Job                                                                              |
| 看板              | `CheckboardDelegateImpl.java` 等；删除 `CheckboardRepoAccessHelper*` | 修改/删 | 结构收敛；**须保持 !381 鉴权语义**（§2.4）；!382 存在已知漏校验                         |
| 配置              | `application.yaml` / gama / prod                                     | 修改    | `spring.rabbitmq.codecheck.project_change_event_queue`                                  |
| 测试              | `ProjectRenameServiceTest.java` 等                                   | 新增/改 | 单测与 mock 支撑                                                                        |

### docs 仓 `openlibing-docs`

| 文件                                                                          | 操作 |
| ----------------------------------------------------------------------------- | ---- |
| `spec/openlibing-codecheck/task_design/project-rename-adaptation/proposal.md` | 新增 |
| `spec/openlibing-codecheck/task_design/project-rename-adaptation/design.md`   | 新增 |
| `spec/openlibing-codecheck/task_design/project-rename-adaptation/tasks.md`    | 新增 |

## 关联 PR

- https://gitcode.com/openlibing/openlibing-codecheck/pull/382（分支 `feat/project-rename-adaptation-v6` → `release_20261029_iter2`，已合入）
- **同 release 前置**：https://gitcode.com/openlibing/openlibing-codecheck/pull/381（看板仓可见性；spec `fix-checkboard-repo-visibility-auth`）
