# project-rename-adaptation — 实现任务

## 进度: 已完成（PR !382 已合入 release_20261029_iter2）

> 对照业务仓 merge commit `8a0eb268`（`feat/project-rename-adaptation-v6`），共 15 个提交；diff 约 95 files，+3158 / -2577。

### MQ 更名

- [x] Task 1: 新增 `ProjectRenameMessageDTO`、`ProjectRenameService`、`ProjectRenameConsumer`
- [x] Task 2: 新增 `ProjectRenameRabbitConfig`（独立 vhost 连接 + 队列声明 + 监听容器工厂）
- [x] Task 3: `application.yaml` / gama / prod 配置 `spring.rabbitmq.codecheck.project_change_event_queue`
- [x] Task 4: 消费链路 Redisson 锁、二次校验、非法消息与解析失败处理
- [x] Task 5: `applyRenameEvent` 以 `project_info.project_name` 为写入目标；majun 开启时补刷旧平台名 / majun 名 + `inc_` Redis

### actual_project_id

- [x] Task 6: 新增 `ActualProjectIdCollectionRegistry`（**16** 集合映射，见 design.md §4.2）
- [x] Task 7: 新增 `ActualProjectIdWriteEnricher`、`ActualProjectIdSaveListener`，MongoConfig 挂接
- [x] Task 8: `XxlJobHandler.actualProjectIdBackfillJob` + 非法 `projectId` 快速失败
- [x] Task 9: 新增 `ProjectRenameSettings`（`project.rename.match-by-actual-project-id`）

### majun 存量与读路径

- [x] Task 10: 新增 `MajunProjectNameSettings`；`CommonHelper` 双读 Criteria、平台名解析、Job 映射列表
- [x] Task 11: `XxlJobHandler.projectMajunNameMigrationJob`（备份后缀、单项目 / 全量）
- [x] Task 12: 各 Operation / Delegate / Util 改用 `CommonHelper` 查询与写侧平台名（规则集、汇总、屏蔽、邮件等）

### 看板与其它

- [x] Task 13: !382 删除 `CheckboardRepoAccessHelper` / `CheckboardRepoAccessService`，看板逻辑收拢/内联至 `CheckboardDelegateImpl` 等（**代码已合入，鉴权语义见 Task 27**）
- [ ] Task 27: **看板鉴权与 !381 等价**：恢复或内联 §2.4 六类入口的仓可见性 + Feign 读权限（含 `getDetailNum` MR 分支、`assertExportAccessByRecordKey`）；**visibility 统一 §2.3 `isExternallyVisible`（fix-checkboard Task 13）**；迁移 `CheckboardRepoAccessHelperTest` 等价用例至 Delegate/Controller/Excel 单测；网关透传 userId 联调（与 fix-checkboard spec 发布门禁一致）
- [x] Task 14: `RabbitConnectionFactoryConfig` / 生产 Rabbit TLS 行为对齐 amqp-client 5.37.0
- [x] Task 15: 删除或收缩无关测试，新增 `CommonHelperTestMocks`

### 测试

- [x] Task 16: `ProjectRenameServiceTest`（校验、MQ 匹配策略、majun 补刷、Redis 迁移等）
- [x] Task 17: `XxlJobHandlerMajunMigrationParamTest`、`ActualProjectIdWriteEnricherTest`
- [x] Task 18: 各 Operation / Controller 单测 mock `CommonHelper` 适配双读
- [ ] Task 18b: 看板鉴权单测迁移（Task 27）：`getDetailNum` 全量/MR、`getFullTaskTrend`、`getTaskResultDetails`、导出 4001/403 分支；**不得**仅删除 Helper 单测而不补等价覆盖

### 验证与上线

- [x] Task 19: 编译 + 相关单测通过
- [ ] Task 20: 各环境确认 framework 队列投递与消费者 vhost 一致
- [ ] Task 21: 生产发布顺序（design.md 步骤 3–6、**3b/5a**）：回填 Job → **3b 缺 actual_project_id 逐集合 count** → majun 试跑/Job 4/4b/4c → **`match-by=true`（3b 已通过）** → **5a 更名后旧名/majun 残留 count=0** → 关 `majun.project.name.enabled`；误刷 §2.2.1
- [ ] Task 22: prod 导入 RabbitMQ CA/truststore；Nacos `project.rename.rabbit.tls.skip-verify=false`；发布步骤 7 回归更名消费
- [ ] Task 23: **（代码债）** 将 !382 中 `profiles.active=prod` 硬编码 skip-verify 改为 `project.rename.rabbit.tls.skip-verify`（默认 false），禁止 profile 默认跳过校验
- [ ] Task 24: **`migrateIncRedis` 改造**：新键非空时合并去重（或 `inc_{newName}_backup_*` 备份）再写回；单测「新键先有增量 + 旧键有存量 → 不丢数据」
- [ ] Task 25: **（代码债）** `projectMajunNameMigrationJob` 增加入参 `includeSensitive=true`（或独立 Job），支撑 design 步骤 4b（!382 当前无该入参）
- [ ] Task 26: **（代码债）** 生产环境 `backupSuffix` 为空时 Job **拒绝执行**（`handleFail`），与 §2.2.1「生产必填」一致
- [ ] Task 28: **（代码债）** `ProjectRenameService` MQ/Job 刷名：**每集合** INFO `modifiedCount`；刷前 count>0 且 modified=0 → **WARN**（含 projectId、collection、eventId）；单测覆盖 0 行 WARN 分支
