# 黄蓝协同 stop 接口修复 — 技术方案

## 方案概述

在 `BlueYellowPipelineServiceImpl#checkDuplicateAndTimeout` 中引入 `actionType` 参数，区分 start/stop/retry 三种操作路径；新增 `resetForStop` mapper 方法，仅重置 stop 关心的字段，保留黄区定位字段；DTO/VO/MQS payload 透传 `yellowRecordId`，使黄区可精确定位需停止的执行记录。

## 状态机与分支判定

```
checkDuplicateAndTimeout(recordId, taskId, actionType):
  exist = queryByBlueRecord(recordId, taskId)
  ┌─ exist == null ─────────────────────────────────────────────┐
  │  if actionType == "stop":                                    │
  │     return FAILURE("Cannot stop: no existing record ...")    │
  │  else:                                                       │
  │     return SUCCESS("new", false)  // 首次 start              │
  └──────────────────────────────────────────────────────────────┘
  ┌─ exist != null ──────────────────────────────────────────────┐
  │  if actionType == "stop":                                    │
  │     return SUCCESS("stop", true)   // 复用已有 task          │
  │  elif status == MQS_SEND_FAILURE:                            │
  │     return SUCCESS("retry", true)                            │
  │  elif (status == MQS_SEND_SUCCESS or blank) and > 5min:      │
  │     return SUCCESS("retry", true)  // 超时重试                │
  │  else:                                                       │
  │     return FAILURE("Task already exists ...")                │
  └──────────────────────────────────────────────────────────────┘
```

## 落库策略

`saveOrResetRecord(request, mqsSendTime, isRetry)` 根据 `actionType` 与 `isRetry` 分三路：

| actionType | isRetry | 路径 | 行为 |
|------------|---------|------|------|
| stop | (任意) | `resetForStop` | UPDATE status/mqs_send_time/fail_message/action_type，**保留** yellow_record_id / start_time / end_time / yellow_pipeline_url |
| (非 stop) | true | `resetForRetry` | UPDATE status/mqs_send_time，**清空** yellow_record_id / start_time / end_time / yellow_pipeline_url |
| (非 stop) | false | `insert` | 全量插入新记录 |

`resetForStop` 与 `resetForRetry` 的关键区别：stop 必须保留 `yellow_record_id` 供黄区定位"要停止哪条执行记录"；retry 是重新发起，旧的黄区记录失效，需清空。

## MQS payload 字段

`buildMqsPayload` 新增透传字段：

```java
mqsPayload.put("actionType", request.getActionType());
mqsPayload.put("yellowRecordId", request.getYellowRecordId());
```

黄区消费时：
- `actionType == "stop"`：执行停止流程，根据 `yellowRecordId` 定位需停止的黄区执行记录。
- `actionType != "stop"`：执行 start/retry 流程。

## Mapper 层改动

### `BlueYellowPipelineMapper.java`

新增方法：

```java
int resetForStop(@Param("blueRecordId") String blueRecordId,
                 @Param("blueRecordTaskId") String blueRecordTaskId,
                 @Param("mqsSendTime") String mqsSendTime,
                 @Param("actionType") String actionType);
```

### `BlueYellowPipelineMapper.xml`

- `queryByBlueRecord`：result map 增加 `yellow_record_id` 字段映射。
- `resetForStop`：新增 UPDATE SQL，仅重置 4 个字段。

```xml
<update id="resetForStop">
    UPDATE blue_yellow_pipeline
    SET status = 'MQS_SEND_SUCCESS',
        mqs_send_time = #{mqsSendTime},
        fail_message = NULL,
        action_type = #{actionType}
    WHERE blue_record_id = #{blueRecordId}
      AND blue_record_task_id = #{blueRecordTaskId}
</update>
```

## DTO/VO 改动

### `CrossRegionStartReqDTO`

新增字段：

```java
private String yellowRecordId;
private String actionType;
```

### `CrossRegionQueryVO`

新增字段，使用 builder 模式：

```java
.yellowRecordId(record.getYellowRecordId())
```

## 影响范围分析

| 维度 | 影响 |
|------|------|
| 接口契约 | stop 接口新增 `yellowRecordId` 入参，查询接口新增 `yellowRecordId` 返回字段（向后兼容） |
| 数据库 schema | 无变更，`yellow_record_id` 列已存在 |
| 鉴权 | 无影响 |
| 依赖 | 无新增依赖 |
| 部署 | 无特殊配置 |
| 兼容性 | start/retry 路径完全不受影响，仅 stop 路径增强 |

## 风险与缓解

| 风险 | 缓解 |
|------|------|
| stop 对不存在记录的旧调用方误判已成功 | `exist == null` 时直接返回 `failureMessage`，调用方收到明确错误 |
| `resetForStop` 与 `resetForRetry` SQL 易混淆 | 方法名显式区分，javadoc 说明保留字段差异 |
| MQS payload 新增字段对黄区消费端兼容性 | 黄区按字段名取值，缺失字段不影响既有逻辑 |

## 测试策略

- **单元测试**（Standard 模式）：
  - `checkDuplicateAndTimeout`：覆盖 exist==null + stop（返回失败）、exist==null + 非 stop（返回 new）、exist!=null + stop（返回 stop, true）、exist!=null + retry 各分支。
  - `saveOrResetRecord`：验证 stop 调用 `resetForStop`、retry 调用 `resetForRetry`、首次调用 `insert`。
  - `buildMqsPayload`：验证 `yellowRecordId` 透传。
- **回归验证**：
  - stop 后再发起 start，仍能正常创建新记录。
  - retry 路径未受影响，`resetForRetry` 仍清空 `yellow_record_id`。

## 关联

- 业务 Issue: openlibing/openlibing-cicd#137
- 业务 PR: openlibing/openlibing-cicd!413 (merged)
