# 度量指标策划接口文档（前端联调）

> 适用范围：`ProductQualityMetricPlanController` 的新增、分页、详情、修改、单条删除和批量删除接口。
>
> 本文以当前代码和 `V20261104__product_quality_planning.sql` 为依据，示例数据仅用于说明结构。

## 1. 接口清单

统一基础路径：`/projects/product-quality/metric-plans`

| 功能 | 请求方式 | 相对路径 | 成功时 `data` 类型 |
|---|---|---|---|
| 新增 | POST | `/add` | `MetricPlanResp` |
| 分页查询 | GET | `/getPage` | `PageResult<MetricPlanResp>` |
| 单条详情 | GET | `/detail` | `MetricPlanResp` |
| 修改 | POST | `/update` | `MetricPlanResp` |
| 单条逻辑删除 | GET | `/delete` | `null` |
| 批量逻辑删除 | POST | `/batch-delete` | `null` |

## 2. 通用约定

### 2.1 身份认证与权限

所有接口均要求请求携带有效的 `token` Cookie，服务端从 JWT 中读取用户身份，并通过产品质量策划权限白名单校验读写权限。查询接口要求读权限，新增、修改和删除接口要求写权限。

### 2.2 公共 Query 参数

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `milestoneId` | Query | Long | 是 | 里程碑 ID，对应 `pq_milestone.id`，必须为正整数 |

数据查询、修改和删除均限定在该里程碑内；记录不存在、已删除或不属于该里程碑时，返回参数异常。

### 2.3 统一响应结构

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | Integer | 业务状态码，成功固定为 `200` |
| `messageCn` | String | 中文消息，成功为 `成功` |
| `messageEn` | String | 英文消息，成功为 `success` |
| `data` | T/null | 业务数据；删除成功或异常时通常为 `null` |

### 2.4 保存请求对象 `MetricPlanSaveReq`

| 字段 | 类型 | 必填 | 校验规则 | 说明 |
|---|---|---|---|---|
| `metricName` | String | 否 | 最大 255 字符 | 指标名称 |
| `evaluationItem` | String | 否 | 最大 255 字符 | 指标评估项 |
| `metricDefinition` | String | 否 | 最大 65535 字符 | 指标定义 |
| `metricAttribute` | String | 否 | 最大 128 字符 | 指标属性 |
| `metricAlgorithm` | String | 否 | 最大 65535 字符 | 指标算法文本 |
| `ownerName` | String | 否 | 最大 128 字符 | 责任人 |
| `versionTargetValue` | String | 否 | 最大 255 字符 | 版本级目标值 |
| `itActualValue` | String | 否 | 最大 255 字符 | IT实际值 |
| `actualValue` | String | 否 | 最大 255 字符 | 实际值 |
| `status` | String | 否 | 最大 64 字符 | 状态 |

### 2.5 响应对象 `MetricPlanResp`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Long | 记录主键 |
| `projectId` | Integer | 项目 ID，由里程碑归属生成 |
| `milestoneId` | Long | 里程碑 ID |
| `milestoneName` | String/null | 里程碑名称 |
| `metricName` | String/null | 指标名称 |
| `evaluationItem` | String/null | 指标评估项 |
| `metricDefinition` | String/null | 指标定义 |
| `metricAttribute` | String/null | 指标属性 |
| `metricAlgorithm` | String/null | 指标算法文本 |
| `ownerName` | String/null | 责任人 |
| `versionTargetValue` | String/null | 版本级目标值 |
| `itActualValue` | String/null | IT实际值 |
| `actualValue` | String/null | 实际值 |
| `status` | String/null | 状态 |
| `createBy` | String | 创建人用户 ID |
| `createTime` | String | 创建时间，格式 `yyyy-MM-dd HH:mm:ss` |
| `updateBy` | String/null | 最后修改人用户 ID |
| `updateTime` | String/null | 最后修改时间，格式 `yyyy-MM-dd HH:mm:ss` |

单条成功响应示例：

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": {
    "id": 1,
    "projectId": 100,
    "milestoneId": 7,
    "milestoneName": "TR1",
    "metricName": "示例",
    "evaluationItem": "示例",
    "metricDefinition": "示例",
    "metricAttribute": "示例",
    "metricAlgorithm": "示例",
    "ownerName": "示例",
    "versionTargetValue": "示例",
    "itActualValue": "示例",
    "actualValue": "示例",
    "status": "示例",
    "createBy": "user-1",
    "createTime": "2026-11-09 10:00:00",
    "updateBy": "user-1",
    "updateTime": "2026-11-09 10:00:00"
  }
}
```

## 3. 新增

```http
POST /projects/product-quality/metric-plans/add?milestoneId=7
Content-Type: application/json
```

服务端校验里程碑存在后，从里程碑生成 `projectId`、`milestoneId` 和 `milestoneName`，并写入创建/更新审计字段。新增不写独立操作日志。

## 4. 分页查询

```http
GET /projects/product-quality/metric-plans/getPage?milestoneId=7&page=1&pageSize=20
```

| 参数 | 位置 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|---|
| `page` | Query | Integer | 否 | `1` | 页码，必须大于 0 |
| `pageSize` | Query | Integer | 否 | `20` | 每页条数，1～200 |

仅查询 `deleted=0` 数据，按 `id DESC` 排序，由数据库分页。

## 5. 单条详情

```http
GET /projects/product-quality/metric-plans/detail?milestoneId=7&id=1
```

目标不存在、已删除或跨里程碑时返回参数异常。

## 6. 修改

```http
POST /projects/product-quality/metric-plans/update?milestoneId=7&id=1
Content-Type: application/json
```

修改采用全字段保存语义，保留主键、项目/里程碑归属和创建审计字段，更新请求字段、更新人和更新时间。

业务修改与 `pq_metric_plan_log` 日志写入处于同一事务：日志保存修改前和修改后的完整 JSON 快照；任一步骤失败均回滚。

## 7. 单条逻辑删除

```http
GET /projects/product-quality/metric-plans/delete?milestoneId=7&id=1
```

将目标记录 `deleted` 置为 `1`，并在同一事务写入操作日志：保存删除前完整 JSON，`new_data=null`。成功时 `data` 为 `null`。

## 8. 批量逻辑删除

```http
POST /projects/product-quality/metric-plans/batch-delete?milestoneId=7
Content-Type: application/json
```

```json
{
  "ids": [1, 2, 3]
}
```

`ids` 非空、最多 200 个、每个 ID 为正整数，服务端按原顺序去重。任一目标不存在、已删除或不属于该里程碑时整批拒绝；删除和逐条日志写入任一步骤失败时整批回滚。每条日志均保存对应记录删除前完整 JSON，`new_data=null`。

## 9. 独立操作日志

日志表：`pq_metric_plan_log`。

| 字段 | 说明 |
|---|---|
| `id` | 日志主键 |
| `metric_plan_id` | 业务记录主键 |
| `old_data` | 修改或删除前完整 JSON，非空 |
| `new_data` | 修改后完整 JSON；删除时为 `null` |
| `update_by` | 操作人用户 ID |
| `update_time` | 操作时间 |

新增和查询不写该日志表；修改、单条删除和批量删除会写入。
