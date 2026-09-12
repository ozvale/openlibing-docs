# repo-sync: 黄蓝协同代码同步（三平台 PR / 评论 / push 事件 MQS 同步）

## 需求背景

- **PR 事件 MQS 同步**：coderepo（蓝区）接收 gitcode / gitee / github 三平台 PR 事件（Merge Request Hook / pull_request），按动作（open / merge / close）构建与 cicd 完全一致的 MQS 消息 HTTP 发送到 MQS 服务，由黄区消费触发跨区流水线。
- **评论事件 MQS 同步**：三平台评论事件（Note Hook / issue_comment）命中编译触发词（`pre-build` 或 `gitee_commit_type` 表内容）时按 COMPILE 发送，并预插 / 中断 `yellow_region_pipeline` 流水线记录；无权限评论（`无权限，请联系管理员`）将流水线标记为 UNAUTHORIZED 失败并删除标签。
- **push 事件 MQS 同步**：三平台 push 事件过滤 tag / 删分支 / 未注册仓库后，构建 `req_type=push` 的 5 字段最小消息（不含 access_token）发送 MQS，供黄区按仓库配置筛选后增量同步代码分支。
- **流水线记录与幂等**：发送前预插 START 记录（`status=start`、`pipelineStatus=WAIT_START`），MQS 发送失败将记录标记为 FAILURE（`MQS 发送失败`），避免记录永久挂起；Redis 去重防重复触发（评论 3 分钟 / PR 事件 30 分钟 TTL）。
- **标签与评论回复**：三平台发送 COMPILE 成功后打 `SC-START` 标签（先删除 `SC-START,SC-RUNNING,SC-FAIL,SC-SUCC` 旧状态标签），同步提供去重提示、CI 未通过提示等评论回复能力。
- **webhook 订阅扩展**：仓库 webhook 创建 / 更新时，github 增加 `issue_comment` 订阅、gitcode / gitee 开启 note 事件，作为 compile 评论触发的入口。
- **access_token 获取逻辑复用**：将 MergeRequestEventHandler 中"按仓库 URL 反查仓库私有 token / 项目级 token + 解密 + 有效性校验"逻辑抽取为 PrAccessTokenService，PR 同步与抑制检视共用。
- **平台 API 地址默认值**：gitee / gitcode API 地址 `@Value` 增加默认值（`https://api.gitee.com` / `https://api.gitcode.com`），缺失配置时不再启动失败。

**不做：** 不做 MQS 消费（消息只发不收，消费在黄区）；不引入 cicd 的 PlatformAdapter / PlatformDispatcher 架构（沿用 coderepo 现有 WebHookEventHandler 分发机制）；不修改存量 MergeRequestEventHandler（告警抑制）、PushEventHandler（本地分支同步）的处理行为。

## 验收标准

- [ ] gitcode / gitee / github 三平台 PR open / merge / close 事件均能映射为对应动作并发 MQS，消息字段与 cicd 对齐
- [ ] PR 事件 `update + source update`（github `synchronize`）先删旧标签再按 open 处理；`update label` 等无业务含义动作忽略
- [ ] `pre-build` 及 `gitee_commit_type` 表内的评论能触发 COMPILE MQS，并完成运行中流水线中断 + 新 START 记录预插
- [ ] 无权限评论将最新流水线记录标记为 FAILURE（UNAUTHORIZED）并删除标签
- [ ] 同 PR 评论 3 分钟内去重并回复提示；ascend 组织 MindIE 仓库在无 CI 通过标签时回复拒绝提示
- [ ] push 事件：分支 push 发送 5 字段消息（req_type=push、无 access_token）；tag / 删分支 / 未注册仓库不发送
- [ ] MQS 发送失败时预插记录改为 FAILURE（MQS 发送失败），异常不抛出、不阻塞 webhook 主流程
- [ ] 流水线记录写入前确保 `gitee_pr_info` 记录存在（黄蓝协同查询 join 依赖）
- [ ] 仓库 webhook 创建 / 更新后已订阅 github `issue_comment` 与 gitee / gitcode note 事件
- [ ] 平台 API 地址配置缺失时应用可正常启动（使用默认值）

## 关联 Issue

- openlibing/openlibing-coderepo#112
