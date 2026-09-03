# repo-sync（黄蓝协同代码同步）实现任务

## openlibing-coderepo

### 常量（common/constants/cooperate，与 cicd 对齐）

- [x] CooperateAction：open / merge / close / compile / comment / push（PUSH 为本功能新增）
- [x] CooperateComment：PRE_BUILD / UNAUTHORIZED / NO_REPEATED / CI_FAIL
- [x] CooperateLabel：START=`SC-START`、CI_PASSED、PR_LABELS（待删标签清单）
- [x] PipelineStatus：start / failure / success
- [x] CrossRegionFailReason：UNAUTHORIZED / INTERRUPT / MQS_SEND_FAIL
- [x] RepoType：gitee / gitcode / github
- [x] PrSyncWebhookConstants：去重前缀（giteePr / gitecodePr / githubPr）与 TTL、ASCEND_ORG、MIND_IE_REPOS、WAIT_START_STATUS、SEND_OK

### 共享表实体与 Mapper（复用 cicd 库表）

- [x] YellowRegionPipelineEntity：映射 yellow_region_pipeline，覆盖 prId / taskUrl / status / startTime / execUser / failReason / pipelineStatus 等列
- [x] GiteePrInfoEntity + GiteePrInfoMapper：映射 gitee_pr_info，ensurePrInfo 缺失插入
- [x] GiteeCommitTypeEntity + GiteeCommitTypeMapper：映射 gitee_commit_type（只读），exists(content) / getType(content)
- [x] YelloRegionPipelineMapper：BaseMapper，最新记录查询在服务层用 LambdaQueryWrapper（按 prId 倒序取最新）

### MQS 消息 DTO

- [x] MqsReqMessageVO：snake_case 字段与 cicd 完全一致（req_type / repo_type / org_name / repo_name / pr_id / br_name / tgt_branch / 平台账号昵称 / access_token / timestamp / params）
- [x] MqsResponseDTO：msgId / sendStatus
- [x] PrSyncMessageContext：handler 解析后的消息构建上下文

### 服务层

- [x] MqsMessageSender（+Impl）：构建消息 + HTTP POST（X-HW-ID / X-HW-APPKEY 解密 / MsgTopic）+ sendStatus==SEND_OK 校验；按 repoType 填充平台账号昵称
- [x] PrAccessTokenService（+Impl）：仓库 URL → 仓库私有 token / 项目级 token（isDefault=false）→ 解密 → API 有效性校验，首个有效即返回（从 MergeRequestEventHandler 抽取，共用）
- [x] PrPipelineRecordService（+Impl）：insertStartRecord 预插 START（WAIT_START）/ interruptAndCreateRecord 中断运行中再预插 / markMqsSendFail / markUnauthorized
- [x] PrLabelService（+Impl）：三平台 updateStartLabel（先删 PR_LABELS 旧标签再打 SC-START）、deleteLabels（gitee / github 404 视为成功）
- [x] PrCommentReplyService（+Impl）：三平台 PR 评论回复

### 事件处理器（WebHookEventHandler 扩展）

- [x] PrSyncEventHandler：三平台 PR 载荷解析与动作映射（open / merge / close / source-update 删标签重发 / update-label 忽略）、Redis 锁去重（30 分钟）、ensurePrInfo、预插 START、发送、失败改 FAILURE
- [x] PrSyncCommentEventHandler：note 校验（pre-build / gitee_commit_type）、UNAUTHORIZED 特判、Redis 去重（3 分钟）+ 重复回复、ascend MindIE CI 检查回复、COMPILE 中断 + 预插、发送、失败改 FAILURE；github issue_comment 按 issue number 调 API 补 PR 信息
- [x] PrSyncPushEventHandler：Push Hook / push 事件过滤（tag / 删分支 / 未注册仓库），通过后构建 req_type=push 的 5 字段消息发送（不含 access_token），与存量 PushEventHandler 并存

### 存量文件修改

- [x] RepoServiceImpl：github webhook events 增加 issue_comment（创建与更新 body 均保留该订阅）；gitee / gitcode webhook 开启 note_events（compile 评论触发入口）；gitee / gitcode API 地址 @Value 补默认值
- [x] MergeRequestEventHandler：gitee / gitcode API 地址 @Value 补默认值（无逻辑变更）
- [x] GitCode / Gitee 工具类：gitcode / gitee API 地址 @Value 补默认值
