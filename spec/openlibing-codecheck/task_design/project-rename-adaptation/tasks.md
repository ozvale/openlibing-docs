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

- [x] Task 6: 新增 `ActualProjectIdCollectionRegistry`（15 集合映射）
- [x] Task 7: 新增 `ActualProjectIdWriteEnricher`、`ActualProjectIdSaveListener`，MongoConfig 挂接
- [x] Task 8: `XxlJobHandler.actualProjectIdBackfillJob` + 非法 `projectId` 快速失败
- [x] Task 9: 新增 `ProjectRenameSettings`（`project.rename.match-by-actual-project-id`）

### majun 存量与读路径

- [x] Task 10: 新增 `MajunProjectNameSettings`；`CommonHelper` 双读 Criteria、平台名解析、Job 映射列表
- [x] Task 11: `XxlJobHandler.projectMajunNameMigrationJob`（备份后缀、单项目 / 全量）
- [x] Task 12: 各 Operation / Delegate / Util 改用 `CommonHelper` 查询与写侧平台名（规则集、汇总、屏蔽、邮件等）

### 看板与其它

- [x] Task 13: 删除 `CheckboardRepoAccessHelper` / `CheckboardRepoAccessService`，`CheckboardDelegateImpl` 等适配
- [x] Task 14: `RabbitConnectionFactoryConfig` / 生产 Rabbit TLS 行为对齐 amqp-client 5.37.0
- [x] Task 15: 删除或收缩无关测试，新增 `CommonHelperTestMocks`

### 测试

- [x] Task 16: `ProjectRenameServiceTest`（校验、MQ 匹配策略、majun 补刷、Redis 迁移等）
- [x] Task 17: `XxlJobHandlerMajunMigrationParamTest`、`ActualProjectIdWriteEnricherTest`
- [x] Task 18: 各 Operation / Controller 单测 mock `CommonHelper` 适配双读

### 验证与上线

- [x] Task 19: 编译 + 相关单测通过
- [ ] Task 20: 各环境确认 framework 队列投递与消费者 vhost 一致
- [ ] Task 21: 生产执行回填 Job → 打开 `match-by-actual-project-id` → majun Job → 关闭 `majun.project.name.enabled`
