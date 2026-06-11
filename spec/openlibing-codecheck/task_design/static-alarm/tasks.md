# 版本级别（nightly）流水线支持开源代码检测工具结果可视 - 实现任务

## openlibing-codecheck 仓库

### 数据模型层

- [x] 创建 `StaticAlarmScanRunEntity` 扫描记录实体类
- [x] 创建 `StaticAlarmIssueEntity` 静态告警问题实体类
- [x] 创建 `StaticAlarmReceiveDTO` 接收扫描结果入参
- [x] 创建 `StaticAlarmQueryDTO` 查询问题列表入参
- [x] 创建 `StaticAlarmFilterOptionsQueryDTO` 筛选项查询入参
- [x] 创建 `StaticAlarmShieldDTO` 批量屏蔽入参
- [x] 创建 `ParsedIssue` / `ParsedSarifMeta` 解析中间模型
- [x] 创建 `StaticAlarmIssueListVO` / `StaticAlarmIssueDetailVO` / `StaticAlarmIssueCountVO` 等 VO
- [x] 创建 `StaticAlarmFilterOptionsVO` / `StaticAlarmRepoSearchVO` / `StaticAlarmShieldResultVO` 等 VO
- [x] 创建 `PageInfoInVO` / `PageInfoOutVO` 通用分页 VO
- [x] 创建 `StaticAlarmSeverityEnum` / `StaticAlarmStatusEnum` 枚举

### 数据库操作层

- [x] 创建 `StaticAlarmOperation` 问题表 CRUD 操作类（含 upsert、resolveDisappearedIssues）
- [x] 创建 `StaticAlarmScanRunOperation` 扫描记录表 CRUD 操作类（含状态流转）
- [x] 创建 MongoDB 索引 changelog（static_alarm_index.xml）
- [x] 创建 `MongoCriteriaBuilder` 通用查询条件构建工具

### SARIF 解析层

- [x] 创建 `ISarifParser` 解析器接口
- [x] 创建 `SarifParserFactory` 解析器工厂（根据工具名选择解析器）
- [x] 创建 `CodeQlSarifParser` CodeQL SARIF 解析器实现
- [x] 创建 `SarifParseService` / `SarifParseServiceImpl` 解析服务

### 消息队列层

- [x] 创建 `StaticAlarmRabbitConfig` RabbitMQ 配置（Exchange/Queue/Binding/死信）
- [x] 创建 `StaticAlarmEventProducer` 消息生产者
- [x] 创建 `StaticAlarmEventConsumer` 消息消费者

### 业务服务层

- [x] 创建 `StaticAlarmReceiveService` / `StaticAlarmReceiveServiceImpl` 接收服务
- [x] 创建 `StaticAlarmService` / `StaticAlarmServiceImpl` 查询与屏蔽服务

### 控制器层

- [x] 创建 `StaticAlarmReceiveController` 内部接收接口
- [x] 创建 `StaticAlarmInternalController` 内部查询接口
- [x] 创建 `StaticAlarmController` 外部查询与屏蔽接口

### 工具类

- [x] 创建 `RepoUrlParser` 仓库 URL 解析工具
- [x] 创建 `RepoUrlParserTest` 单元测试

### 配置

- [x] application.yaml 添加 staticalarm_exchange/queue/key 配置
- [x] application-gama.yaml / application-prod.yaml 环境配置补充

## openlibing-cicd 仓库

### 触发层

- [x] 创建 `StaticAlarmReceiveDTO` 传递给 codecheck 的 DTO
- [x] 修改 `PipelineEventConsumer` 添加 SARIF 文件检测与触发逻辑
- [x] 修改 `CodeCheckClient` 添加 `receiveStaticAlarmResult` Feign 接口
- [x] 注入 `PipelineInfoMapper` 和 `CodeCheckClient` 依赖
- [x] 实现 `triggerStaticAlarmIfSarif` 方法（检测 SARIF 文件并触发）
- [x] 实现 `buildStaticAlarmDTO` 方法（构建 DTO）
- [x] 实现 `fillPipelineInfo` 方法（填充流水线配置信息）
- [x] 实现 `sendToStaticAlarm` 方法（调用 codecheck 接口，容错处理）
