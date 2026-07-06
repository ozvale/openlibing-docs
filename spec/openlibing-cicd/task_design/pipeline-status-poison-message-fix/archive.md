# pipeline-status-poison-message-fix — 归档

## 关联

| 类型 | 链接 |
|---|---|
| 业务 Issue | https://gitcode.com/openlibing/openlibing-cicd/issues/169 |
| 业务 Issue 标题 | pipeline_status_queue 积压 60 条毒消息不消费 |
| 业务 PR | https://gitcode.com/openlibing/openlibing-cicd/merge_requests/449 |
| 业务 PR 标题 | fix(cicd): 修复 pipeline_status_queue 毒消息卡死 60 条 + 消息体敏感字段脱敏 |
| 业务 PR 分支 | fix-pipeline-status-poison-message → release_20260706 |
| docs PR | (本 PR) |
| docs PR 分支 | spec-openlibing-cicd-pipeline-status-poison-message-fix → master |

## 交付历程

| commit | 说明 |
|---|---|
| `180fc080` | fix(pipeline-status): unblock pipeline_status_queue from ClassCastException poison message（业务代码兜底 + 框架 retry interceptor） |
| `d9e41aea` | fix(pipeline-status): log fallback path when parsing PR labels response（用户反馈加 WARN 日志） |
| `54bb6f47` | fix(security): mask sensitive fields (accessToken/token/etc) in pipeline status update logs（用户反馈加日志脱敏） |

## 用户自测反馈

- 用户明确确认自测通过：broker 端 60 条 unacked 降为 0，重投毒消息 3 次重试后入 DLQ，日志中 `accessToken` 显示为 `******`
- 用户明确确认：业务 PR 提到 `release_20260706`
- 用户明确触发 Phase 5 归档

## 最终验证

| 项 | 结果 |
|---|---|
| 业务代码修改 | ✅ 3 个 commit 已 push 到 fork |
| 单元测试 | ✅ 206/206 通过 |
| 业务 PR | ✅ PR #449 已创建并打 `ai-assisted` 标签 |
| 业务 PR CI | ✅ `ci_state_passed: true` |
| 业务 PR 合入 | ⏳ 待用户/评审合入 |
| 用户 dev 自测 | ✅ 通过 |
| docs PR | ⏳ 本次提交（target=master） |

## 设计偏差与取舍

| 取舍 | 原因 |
|---|---|
| 业务代码兜底 vs 修 GitCode API 客户端 schema | GitCode API 行为是上游约束，业务侧兜底最稳 |
| `setDefaultRequeueRejected(false)` 必须配套 `RejectAndDontRequeueRecoverer` | 否则瞬时异常直接入 DLQ，丢失重试机会 |
| retry 次数定 3 + 退避 1s/2s/5s | 业务可容忍 ~8s 延迟；超过 8s 视为毒消息 |
| 脱敏用正则而非 JSON 解析 | 热路径避免 Gson parse 开销；正则覆盖 7 个常见敏感字段 |
| 仅修 `pipelineStatusListenerContainerFactory` | 其他 7 个 listener catch 后不重抛，行为不同，不在本次范围 |
| `bisectQueue` DLX 死循环 bug 不在本次范围 | 涉及独立故障路径，单独工单跟进 |

## 可复用经验

1. **fastjson2 泛型擦除陷阱**：`JSON.parseArray(json, XxxDTO.class)` 当 JSON 实际为字符串数组时，泛型擦除后实际构造出 `List<String>`，编译期 `List<XxxDTO>` 不报错，运行期 `.map(XxxDTO::getXxx)` 才炸。**通用防御模板**：
   ```java
   List<XxxDTO> labels = new ArrayList<>();
   try {
       List<XxxDTO> parsed = JSON.parseArray(body, XxxDTO.class);
       if (parsed != null && !parsed.isEmpty()) return parsed;
   } catch (JSONException ignore) {
       // 尝试字符串数组兜底
   }
   List<String> strs = JSON.parseArray(body, String.class);
   // ...
   ```
2. **Spring AMQP `setDefaultRequeueRejected(true)` ≠ 自动重试**：它只是让异常消息回队首，**没有重试次数限制**。要实现有限重试必须挂 `RetryInterceptorBuilder` + `MessageRecoverer`，否则注释里写的"3 次后入 DLQ"是骗人的。
3. **DLQ 路由仅在 `requeue=false` 时触发**：业务侧如果期望"异常 → 重试 → DLQ"，三件事必须配套：`setDefaultRequeueRejected(false)` + `RetryInterceptor` + `RejectAndDontRequeueRecoverer`。
4. **MQ 消息体必含敏感字段时日志必须脱敏**：常见模式是在 `String` 类型 listener 入参处用静态工具方法做字段替换；正则覆盖 `accessToken` / `access_token` / `token` / `password` / `secret` / `privateKey` / `private_key` 七个字段。
5. **fastjson2 `parseArray` 返回值不可信**：`List<XxxDTO>` 实际元素类型可能是 `String` / `LinkedHashMap` / `null`，流式操作前**必须**做元素类型校验或异常隔离。

## 归档日期

2026-07-06
