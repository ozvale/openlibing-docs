# 版本级别（nightly）流水线支持开源代码检测工具结果可视 - 归档

## 归档信息

| 项目 | 内容 |
|------|------|
| FE 需求名称 | 版本级别（nightly）流水线支持开源代码检测工具结果可视，并能采集数据支撑运营 |
| 业务 PR | openlibing-codecheck #189, openlibing-cicd #351 |
| 开发分支 | nightly-yym |
| 归档日期 | 2026-06-11 |

## 实现总结

### 功能概述

本功能实现了 Nightly 版本级别流水线中 CodeQL 等开源代码检测工具扫描结果的可视化展示与数据运营支撑。核心能力包括：

1. **自动触发**：cicd 仓库在构建产物分析完成后，自动检测 SARIF 文件并触发 codecheck 侧的异步解析
2. **SARIF 解析**：codecheck 仓库接收 SARIF 文件，通过 RabbitMQ 异步解析入库，支持 CodeQL 格式（可扩展）
3. **问题管理**：基于指纹去重的问题生命周期管理（OPEN → RESOLVED → SHIELDED）
4. **可视化查询**：提供列表查询、详情查看、状态统计、级联筛选、仓库搜索等 API
5. **问题屏蔽**：支持批量屏蔽问题，记录屏蔽原因和操作人

### 跨仓协作

```
cicd (PipelineEventConsumer)
  → 检测 .sarif 文件
  → 构建 StaticAlarmReceiveDTO
  → Feign 调用 codecheck /internal/codescan/v1/result/receive

codecheck (StaticAlarmReceiveController)
  → 写入 ScanRun (PARSING)
  → 发 MQ 消息 (scanRunId)
  → 返回 scanRunId

codecheck (StaticAlarmEventConsumer)
  → 消费 MQ 消息
  → 下载 SARIF → 解析 → upsert 问题 → 处理消失问题
  → 更新 ScanRun (SUCCESS/FAILED)

codecheck (StaticAlarmController)
  → 提供查询/屏蔽 API
```

### 关键技术决策

| 决策 | 原因 |
|------|------|
| 异步解析（RabbitMQ） | SARIF 文件可能较大，避免阻塞接口响应 |
| SHA-256 指纹去重 | tool\|ruleId\|filePath\|locationHashRaw 组合唯一标识问题 |
| 消失问题自动 RESOLVED | 每次扫描时，未出现的问题自动标记为已解决 |
| 解析器工厂模式 | SarifParserFactory 便于扩展其他 SARIF 工具 |
| cicd 侧容错 | 触发失败不影响主流程，只记录日志 |
| repoUrl 反查 | 通过 URL 解析 repoType/owner/repo，不依赖外部项目 ID |
| 死信队列 + 2h TTL | 防止消息积压，超时转入死信 |

### 数据模型

- **static_alarm_scan_run**：扫描记录，每次触发解析一条，记录解析状态和统计
- **static_alarm_issue**：静态告警问题，按指纹去重，支持状态流转和屏蔽

### 变更文件清单

#### openlibing-codecheck（新增约 30 个文件）

| 类别 | 文件 |
|------|------|
| Controller | StaticAlarmController, StaticAlarmInternalController, StaticAlarmReceiveController |
| Entity | StaticAlarmIssueEntity, StaticAlarmScanRunEntity |
| DTO | StaticAlarmReceiveDTO, StaticAlarmQueryDTO, StaticAlarmFilterOptionsQueryDTO, StaticAlarmShieldDTO |
| Model | ParsedIssue, ParsedSarifMeta |
| Operation | StaticAlarmOperation, StaticAlarmScanRunOperation |
| Service | StaticAlarmReceiveService/Impl, StaticAlarmService/Impl, SarifParseService/Impl |
| Parser | ISarifParser, SarifParserFactory, CodeQlSarifParser |
| MQ | StaticAlarmRabbitConfig, StaticAlarmEventProducer, StaticAlarmEventConsumer |
| VO | StaticAlarmIssueListVO, StaticAlarmIssueDetailVO, StaticAlarmIssueCountVO, StaticAlarmFilterOptionsVO, StaticAlarmRepoSearchVO, StaticAlarmShieldResultVO, PageInfoInVO, PageInfoOutVO |
| Enum | StaticAlarmSeverityEnum, StaticAlarmStatusEnum |
| Util | RepoUrlParser, MongoCriteriaBuilder |
| Config | application.yaml, application-gama.yaml, application-prod.yaml |
| DB | static_alarm_index.xml (MongoDB changelog) |

#### openlibing-cicd（修改 3 个文件）

| 文件 | 变更 |
|------|------|
| StaticAlarmReceiveDTO | 新增 DTO 类 |
| PipelineEventConsumer | 新增 SARIF 检测与触发逻辑 |
| CodeCheckClient | 新增 receiveStaticAlarmResult Feign 接口 |

## 经验沉淀

1. **SARIF 解析的健壮性**：SARIF 文件格式可能因工具版本不同而有差异，解析器需做好防御性编程，对缺失字段做容错处理
2. **指纹设计**：初始使用 MD5，后改为 SHA-256 以降低碰撞风险；locationHashRaw 的计算需考虑行号+列号+消息的组合
3. **MQ 消息设计**：消息体只传 scanRunId，消费者查库获取完整信息，避免消息体过大和序列化问题
4. **消失问题处理**：需注意"本次扫描无问题"与"扫描失败"的区别，前者应将所有 OPEN 问题标记为 RESOLVED
5. **repoUrl 解析**：不同代码托管平台 URL 格式不同（gitcode vs gitee），需统一解析逻辑
