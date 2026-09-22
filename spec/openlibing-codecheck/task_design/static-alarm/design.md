# 版本级别（nightly）流水线支持开源代码检测工具结果可视 - 技术设计

## 1. 系统架构

本功能涉及两个微服务的协作：

```
┌─────────────────────────────────────────────────────────────────────┐
│  openlibing-cicd                                                    │
│  PipelineEventConsumer                                              │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │ 1. 流水线完成事件触发                                         │  │
│  │ 2. 分析构建产物，检测 .sarif 文件                              │  │
│  │ 3. 解析流水线配置获取 repoUrl/branch/pipelineName             │  │
│  │ 4. 构建 StaticAlarmReceiveDTO                                │  │
│  │ 5. 通过 Feign 调用 codecheck 接口                             │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                          │ HTTP (Feign)                             │
│                          ▼                                          │
└─────────────────────────────────────────────────────────────────────┘
┌─────────────────────────────────────────────────────────────────────┐
│  openlibing-codecheck                                               │
│  ┌──────────────────────┐    ┌──────────────────────────────────┐  │
│  │ StaticAlarmReceive   │    │ StaticAlarmEventProducer         │  │
│  │ Controller/Service   │───▶│ (RabbitMQ Producer)              │  │
│  │ 接收 → 写 ScanRun    │    │ 发送 scanRunId 到 MQ            │  │
│  └──────────────────────┘    └──────────┬───────────────────────┘  │
│                                         │                           │
│                                         ▼                           │
│                              ┌──────────────────────────────────┐  │
│                              │ StaticAlarmEventConsumer         │  │
│                              │ (RabbitMQ Consumer, 1-3并发)     │  │
│                              │ 收到 scanRunId → 触发解析        │  │
│                              └──────────┬───────────────────────┘  │
│                                         │                           │
│                                         ▼                           │
│                              ┌──────────────────────────────────┐  │
│                              │ SarifParseService                │  │
│                              │ 1. 从 OBS 下载 SARIF 文件        │  │
│                              │ 2. SarifParserFactory 选择解析器 │  │
│                              │ 3. CodeQlSarifParser 解析        │  │
│                              │ 4. 指纹去重 + upsert 问题        │  │
│                              │ 5. 处理消失问题(OPEN→RESOLVED)   │  │
│                              │ 6. 更新 ScanRun 统计             │  │
│                              └──────────────────────────────────┘  │
│                                                                      │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │ StaticAlarmController / StaticAlarmService                   │   │
│  │ 查询 API：列表/详情/数量/筛选项/仓库搜索/屏蔽                  │   │
│  └──────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────┘
```

## 2. 数据模型

### 2.1 static_alarm_scan_run（扫描记录表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String | 主键 |
| repoType | String | 代码托管平台：gitcode / gitee |
| owner | String | 仓库所属空间 |
| repo | String | 仓库名 |
| repoUrl | String | 代码仓链接 |
| pipelineId | String | 流水线 ID |
| pipelineName | String | 流水线名称 |
| pipelineRunId | String | 流水线运行 ID |
| obsUrl | String | SARIF 文件的 OBS 下载地址 |
| tool | String | 扫描工具（解析后写入） |
| toolVersion | String | 工具版本 |
| language | List\<String\> | 扫描语言列表 |
| branch | String | 扫描分支 |
| commitId | String | commit ID |
| scanStartAt | Date | 扫描开始时间 |
| scanEndAt | Date | 扫描结束时间 |
| status | String | 解析状态：PARSING / SUCCESS / FAILED |
| issueCount | Integer | 当前未解决问题总数 |
| newIssueCount | Integer | 本次新增问题数 |
| resolvedIssueCount | Integer | 本次修复问题数 |
| errorMsg | String | 解析失败时的错误信息 |
| createdAt | Date | 记录创建时间 |
| updatedAt | Date | 记录更新时间 |

### 2.2 static_alarm_issue（静态告警问题表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String | 主键 |
| fingerprintKey | String | 问题指纹（SHA-256，唯一索引） |
| repoType | String | 代码托管平台 |
| owner | String | 仓库所属空间 |
| repo | String | 仓库名 |
| repoUrl | String | 代码仓链接 |
| branch | String | 分支 |
| pipelineId | String | 关联流水线 ID |
| pipelineRunId | String | 关联流水线运行 ID |
| tool | String | 扫描工具 |
| ruleId | String | 规则 ID |
| ruleName | String | 规则名称 |
| severity | String | 严重级别：note / warning / error |
| filePath | String | 文件路径 |
| startLine | Integer | 起始行号 |
| startColumn | Integer | 起始列号 |
| endLine | Integer | 结束行号 |
| endColumn | Integer | 结束列号 |
| message | String | 问题描述 |
| snippet | String | 代码片段 |
| contextSnippet | String | 上下文代码片段 |
| codeFlows | String | 代码流（JSON） |
| language | String | 编程语言（根据文件后缀推断） |
| status | String | 问题状态：OPEN / RESOLVED / SHIELDED |
| shieldType | String | 屏蔽类型 |
| shieldReason | String | 屏蔽原因 |
| shieldedBy | String | 屏蔽操作人 |
| shieldedAt | Date | 屏蔽时间 |
| firstSeenAt | Date | 首次发现时间 |
| lastSeenAt | Date | 最近出现时间 |
| createdAt | Date | 记录创建时间 |
| updatedAt | Date | 记录更新时间 |

## 3. 核心流程

### 3.1 触发流程（cicd 侧）

1. `PipelineEventConsumer` 监听流水线完成事件
2. 分析构建产物，检测文件名以 `.sarif` 结尾的产物
3. 解析流水线配置（configJson），获取 repoUrl、branch、pipelineName
4. 构建 `StaticAlarmReceiveDTO`（obsUrl、repoUrl、pipelineId、pipelineName、pipelineRunId、branch、commitId）
5. 通过 `CodeCheckClient`（Feign）调用 codecheck 的 `/internal/codescan/v1/result/receive` 接口
6. 调用失败只记录日志，不影响主流程

### 3.2 接收与解析流程（codecheck 侧）

1. `StaticAlarmReceiveController` 接收请求
2. `StaticAlarmReceiveServiceImpl.receive()`:
   - 从 repoUrl 解析出 repoType、owner、repo
   - 创建 `StaticAlarmScanRunEntity`，状态为 PARSING
   - 插入 MongoDB
   - 通过 `StaticAlarmEventProducer` 发送 scanRunId 到 RabbitMQ
   - 返回 scanRunId
3. `StaticAlarmEventConsumer` 消费消息:
   - 根据 scanRunId 查询 ScanRun
   - 调用 `SarifParseService.parse()`
4. `SarifParseServiceImpl.parse()`:
   - 从 OBS 下载 SARIF 文件
   - `SarifParserFactory` 根据 SARIF 内容选择解析器
   - `CodeQlSarifParser` 解析 SARIF，提取 meta 和 issues
   - 对每个 issue 计算 fingerprintKey（SHA-256: tool|ruleId|filePath|locationHashRaw）
   - upsert 问题：已存在则更新 lastSeenAt，不存在则新建
   - 处理消失问题：本次扫描未出现的问题状态变为 RESOLVED
   - 更新 ScanRun 为 SUCCESS 状态
   - 异常时更新 ScanRun 为 FAILED 状态

### 3.3 问题指纹机制

fingerprintKey = SHA-256(tool + "|" + ruleId + "|" + filePath + "|" + locationHashRaw)

- 任一组成字段为空时跳过该问题并记录错误日志
- fingerprintKey 在 MongoDB 中建立唯一索引，保证同一问题不重复创建
- upsert 逻辑：fingerprintKey 已存在 → 更新 lastSeenAt、status=OPEN；不存在 → 新建

### 3.4 问题状态流转

```
首次出现 → OPEN
再次出现 → 更新 lastSeenAt，保持 OPEN
消失（本次扫描未出现）→ RESOLVED
屏蔽 → SHIELDED
```

## 4. API 接口

### 4.1 内部接口（cicd 调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/internal/codescan/v1/result/receive` | 接收 SARIF 扫描结果，触发异步解析 |

### 4.2 外部接口（前端调用）

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/codescan/v1/issue/list` | 分页查询静态告警问题列表 |
| GET | `/codescan/v1/issue/count` | 查询各状态问题数量 |
| GET | `/codescan/v1/issue/detail` | 查询单条问题完整详情 |
| GET | `/codescan/v1/issue/filter-options` | 获取筛选项（支持级联） |
| GET | `/codescan/v1/issue/repo/search` | 仓库自动补全搜索 |
| GET | `/codescan/v1/issue/repo/candidates` | 获取来源/组织下拉候选 |
| POST | `/codescan/v1/issue/shield` | 批量屏蔽问题 |

## 5. MongoDB 索引设计

### static_alarm_issue

| 索引名 | 字段 | 类型 | 用途 |
|--------|------|------|------|
| idx_issue_fingerprint | fingerprintKey | 唯一 | 指纹去重 |
| idx_issue_list | repo_type, owner, repo, status, last_seen_at(-1) | 普通 | 列表主查询 |
| idx_issue_branch_status | repo_type, owner, repo, branch, status, severity | 普通 | 详情/数量/筛选 |
| idx_issue_rule | repo_type, owner, repo, rule_id | 普通 | 规则维度筛选 |

### static_alarm_scan_run

| 索引名 | 字段 | 类型 | 用途 |
|--------|------|------|------|
| idx_scanrun_repo_branch | repo_type, owner, repo, branch, status | 普通 | 按仓库+分支查扫描记录 |
| idx_scanrun_pipeline_run_id | pipeline_run_id | 普通 | 按流水线运行 ID 查扫描记录 |

## 6. RabbitMQ 配置

| 配置项 | 值 | 说明 |
|--------|-----|------|
| Exchange | static_alarm_exchange | Direct 类型，持久化 |
| Queue | static_alarm_queue | 持久化，绑定死信 |
| Routing Key | static_alarm_key | - |
| TTL | 7200000 (2h) | 超时转入死信队列 |
| 死信 Exchange | dead_exchange | 复用已有死信交换机 |
| 死信 Routing Key | dead_key | 复用已有死信路由键 |
| 消费并发 | 1-3 | @RabbitListener concurrency |
| 消息持久化 | PERSISTENT | MessageDeliveryMode.PERSISTENT |

## 7. 枚举定义

### StaticAlarmSeverityEnum

| 枚举值 | 说明 |
|--------|------|
| NOTE | 提示 |
| WARNING | 警告 |
| ERROR | 错误 |

### StaticAlarmStatusEnum

| 枚举值 | 说明 |
|--------|------|
| OPEN | 未解决 |
| RESOLVED | 已解决（消失） |
| SHIELDED | 已屏蔽 |

## 8. 关键设计决策

1. **异步解析**：SARIF 文件可能较大，采用 RabbitMQ 异步解析避免阻塞接口响应
2. **指纹去重**：使用 SHA-256(tool|ruleId|filePath|locationHashRaw) 作为问题唯一标识，避免重复入库
3. **消失问题自动流转**：每次扫描时，本次未出现的问题自动标记为 RESOLVED，实现问题的生命周期管理
4. **解析器工厂模式**：通过 SarifParserFactory 根据工具名选择解析器，便于后续扩展其他 SARIF 工具（如 Semgrep、SonarQube 等）
5. **cicd 侧容错**：触发 codecheck 解析失败不影响主流程，只记录日志
6. **repoUrl 反查项目信息**：通过 repoUrl 解析出 repoType/owner/repo，避免依赖外部项目 ID
