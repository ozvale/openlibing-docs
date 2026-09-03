# repo-sync（黄蓝协同代码同步）技术方案

## 架构概览

```
GitCode / Gitee / GitHub（蓝区入口）
  │ Merge Request Hook / Note Hook / Push Hook、pull_request / issue_comment / push
  ▼
WebHookEventController（存量）→ RabbitMQ webhook_event_queue → WebhookEventConsumer（存量）
  ▼
WebHookEventServiceImpl.dispatchEvent（存量，按 supportedEventTypes() 多 handler 分发）
  ├─ MergeRequestEventHandler（存量：告警抑制检视）── 抽取 ── PrAccessTokenService ★
  ├─ PushEventHandler（存量：本地分支同步）
  ├─ PrSyncEventHandler ★          PR 事件：动作映射 → 锁去重 → 预插 → 发送
  ├─ PrSyncCommentEventHandler ★   评论事件：note 校验 / UNAUTHORIZED / 去重 / CI 检查 / 发送
  └─ PrSyncPushEventHandler ★      push 事件：过滤 → 5 字段最小消息发送
        │
        ▼
  MqsMessageSender ★（HTTP POST + SEND_OK 校验，头 X-HW-ID / X-HW-APPKEY / MsgTopic）
        │ MQS 消息（字段与 cicd 完全一致）
        ▼
  MQS 服务 ──────────► 黄区消费：跨区代码同步 / 流水线触发（本仓不做）
        │
        ▼
  共享 MySQL（与 cicd 同一库，无 DDL 变更）
  ├─ yellow_region_pipeline  预插 / 中断 / 改失败（PrPipelineRecordService）
  ├─ gitee_pr_info            PR 信息，join 定位流水线（只写不读）
  └─ gitee_commit_type        编译触发词表（只读）
```

蓝区侧配套能力：PrLabelService（三平台打 / 删标签）、PrCommentReplyService（三平台评论回复）。

## 事件处理流程

### PR 事件（PrSyncEventHandler）

1. 解析三平台载荷（prId / title / source/targetBranch / org / repo / user / 仓库 URL），并按平台提取请求类型：
   - gitcode / gitee：`create → open`、`merge → merge`、`close → close`；`update + source update(sync)` → 删标签后按 open 处理；`update label` 忽略
   - github：`opened → open`、`closed+merged → merge`、`closed → close`、`synchronize` → 删标签后按 open 处理；其余（edited / labeled 等）忽略
2. Redis 锁去重（同一 PR 相同动作 30 分钟内不重复），Redis 异常放行
3. `ensurePrInfo`：`gitee_pr_info` 无记录时插入（流水线记录 join 依赖）
4. 预插 START 记录：`status=start`、`pipelineStatus=WAIT_START`、taskUrl、execUser、startTime
5. 发送 MQS（含仓库 access_token 明文）；失败 → 记录改 `failure` + `MQS 发送失败`
6. 全程 try-catch 记日志不抛异常

### 评论事件（PrSyncCommentEventHandler）

1. 解析评论载荷（note / prId / prKey / taskUrl / org / repo / labels / user）
2. note 校验：等于 `pre-build` 或存在于 `gitee_commit_type` 才处理，否则忽略
3. note 为 `无权限，请联系管理员` → 最新记录标记 FAILURE（UNAUTHORIZED）+ 删标签后返回
4. Redis 去重：同 PR 评论 3 分钟内重复 → 回复 `代码同步中，请勿频繁操作！`
5. CI 检查：org=ascend 且仓库在 MindIE 仓库列表时，无 `ci-pipeline-passed` 标签 → 回复 `CI流水线未通过，禁止触发前冒烟测试！`
6. reqType 解析：`pre-build → compile`，其余取 `gitee_commit_type.type`
7. reqType=compile → 中断运行中记录（FAILURE + `主动停止导致中断`）并预插新 START 记录
8. 发送 MQS；成功 → 打 `SC-START` 标签；失败 → 预插记录改 FAILURE（`MQS 发送失败`）
9. github `issue_comment` 载荷缺 MR 信息，先按 issue number 调平台 API 补齐 PR 信息

### push 事件（PrSyncPushEventHandler）

1. 支持事件类型 `Push Hook`（gitcode / gitee）与 `push`（github）
2. 过滤：非 `refs/heads/` 分支 ref（tag 等）、分支删除（gitee / github 的 `deleted` 字段或 `after` 全 0）、仓库未在本地注册（候选 URL 反查 `repo_info` 失败）
3. 通过过滤后构建 `req_type=push` 的最小消息（repoType / owner / repo / brName / reqType，**不带 access_token**）发送 MQS
4. 与存量 PushEventHandler（本地分支同步）并存互不影响

## MQS 消息体（MqsReqMessageVO）

| 字段                                 | 说明                                                           |
| ------------------------------------ | -------------------------------------------------------------- |
| repo_type / org_name / repo_name     | 平台类型（gitee / gitcode / github）与仓库标识                 |
| pr_id                                | PR 编号（iid / number），push 流程为空                         |
| br_name / tgt_branch                 | 目标分支（base）/ 源分支（head），push 流程 br_name 为推送分支 |
| req_type                             | open / merge / close / compile / push                          |
| title / description                  | PR 标题 / 描述（push 流程为空）                                |
| gitee_account / gitee_name 等 6 字段 | 按平台填充触发人账号 / 昵称                                    |
| access_token                         | 仓库 token（明文），PR / 评论流程携带，push 流程为 null        |
| timestamp / params                   | 时间戳毫秒字符串 / 预留空 map                                  |

- 字段名即 JSON 键名（snake_case），与 cicd 完全一致，黄区消费端免改造
- 请求头：`X-HW-ID`（mqs.hw.app_id）、`X-HW-APPKEY`（mqs.hw.app_key 解密 part1）、`MsgTopic`（mqs.msg_topic）
- 发送成功判定：响应 `sendStatus == SEND_OK`

## 共享库表（复用 cicd，无 DDL 变更）

| 表                     | 用途                                             | 操作                                                        |
| ---------------------- | ------------------------------------------------ | ----------------------------------------------------------- |
| yellow_region_pipeline | 黄区流水线记录：预插 START / 中断 / 改失败       | 只写（YelloRegionPipelineMapper 按 prId 查最新记录 + 更新） |
| gitee_pr_info          | PR 信息，黄蓝协同查询经 pipeline.pr_id join 定位 | 只写（ensurePrInfo 插入缺失记录）                           |
| gitee_commit_type      | 编译触发词 → 类型映射                            | 只读（exists / getType）                                    |

## 常量（与 cicd 对齐）

- 动作 `CooperateAction`：open / merge / close / compile / comment / push
- 评论 `CooperateComment`：`pre-build`、`无权限，请联系管理员`、`代码同步中，请勿频繁操作！`、`CI流水线未通过，禁止触发前冒烟测试！`
- 标签 `CooperateLabel`：`SC-START`；待删列表 `SC-START,SC-RUNNING,SC-FAIL,SC-SUCC`；CI 通过标签 `ci-pipeline-passed`
- 状态 `PipelineStatus`：start / failure / success；失败原因 `CrossRegionFailReason`：UNAUTHORIZED / INTERRUPT / MQS_SEND_FAIL
- 去重前缀：`giteePr:` / `gitecodePr:`（历史拼写保留）/ `githubPr:`；TTL：评论 3 分钟、PR 事件 30 分钟

## 错误处理与幂等

| 场景                     | 处理                                                                 |
| ------------------------ | -------------------------------------------------------------------- |
| MQS 发送失败             | 预插记录改 FAILURE + `MQS 发送失败`；error 日志，不抛异常            |
| 预插 / 中断 DB 异常      | catch + warn 日志，发送优先，不阻塞 MQS                              |
| Redis 不可用             | 去重放行（保证可用性）                                               |
| access_token 缺失 / 无效 | error 日志（告警），跳过发送                                         |
| 平台标签 / 评论 API 失败 | catch + error 日志，不阻塞主流程；gitee / github 删标签 404 视为成功 |

## 关键设计决策

1. **沿用 WebHookEventHandler 多 handler 分发**：不引入 cicd 的 PlatformAdapter / PlatformDispatcher 架构，dispatcher 按 `supportedEventTypes()` 已支持多 handler 订阅同一事件，新增 handler 零侵入接入。
2. **MQS 消息与 cicd 逐字段对齐**：字段名 / 请求头 / SEND_OK 判定一致，黄区消费端免改动。
3. **共享 cicd 数据库表**：coderepo 与 cicd 同库，yellow_region_pipeline / gitee_pr_info / gitee_commit_type 直接复用，不重复建表。
4. **push 最小消息不带 token**：push 流程仅需仓库与分支信息，避免明文 token 进入跨区链路。
5. **access_token 逻辑抽取为公共 Service**：仓库私有 token → 项目级 token 回退 + 解密 + API 有效性校验，PR 同步与抑制检视共用，消除重复实现。
6. **平台 API 地址补默认值**：gitee / gitcode `@Value` 增加默认值，规避配置缺失导致启动失败。

## 影响范围

- **openlibing-coderepo**：
  - 新增 handler：PrSyncEventHandler / PrSyncCommentEventHandler / PrSyncPushEventHandler
  - 新增 service：MqsMessageSender / PrPipelineRecordService / PrLabelService / PrCommentReplyService / PrAccessTokenService（+ impl）
  - 新增 dto（mqs）/ entity / mapper（cross_region）、常量包 `common/constants/cooperate`
  - 修改：RepoServiceImpl（webhook 订阅扩展）、MergeRequestEventHandler（仅 @Value 默认值）、GitCode / Gitee（仅 @Value 默认值）
- **openlibing-cicd**：无代码变更，仅依赖既有 MQS 消息协议与共享表（黄区消费端为消息接收方）
- **配置**：部署侧（Apollo）按环境补充 `mqs.url`、`mqs.hw.app_id`、`mqs.hw.app_key`、`mqs.msg_topic`
