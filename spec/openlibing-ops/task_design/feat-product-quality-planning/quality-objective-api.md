# 质量目标差距分析及分解接口文档（前端联调）

> 适用范围：`ProductQualityObjectiveController` 的新增、分页、详情、修改、单条删除和批量删除接口。
>
> 本文以当前代码和 `V20261104__product_quality_planning.sql` 为依据，示例数据仅用于说明结构。

## 1. 接口清单

统一基础路径：`/projects/product-quality/quality-objectives`

| 功能 | 请求方式 | 相对路径 | 成功时 `data` 类型 |
|---|---|---|---|
| 新增 | POST | `/add` | `QualityObjectiveResp` |
| 分页查询 | GET | `/getPage` | `PageResult<QualityObjectiveResp>` |
| 单条详情 | GET | `/detail` | `QualityObjectiveResp` |
| 修改 | POST | `/update` | `QualityObjectiveResp` |
| 单条逻辑删除 | GET | `/delete` | `null` |
| 批量逻辑删除 | POST | `/batch-delete` | `null` |

## 2. 通用约定

### 2.1 身份认证与权限

所有接口均要求请求携带有效的 `token` Cookie，服务端从 JWT 中读取用户身份，并通过产品质量策划权限白名单校验读写权限。查询接口要求读权限，新增、修改和删除接口要求写权限。

### 2.2 公共 Query 参数

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `milestoneId` | Query | Long | 是 | 里程碑 ID，对应 `pq_milestone.id`，必须为正整数 |

数据查询、修改和删除均限定在该里程碑内；记录不存在、已删除或不属于该里程碑时，返回业务失败提示。

### 2.3 统一响应结构

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | Integer | 业务状态码，成功固定为 `200` |
| `messageCn` | String | 中文消息，成功为 `成功` |
| `messageEn` | String | 英文消息，成功为 `success` |
| `data` | T/null | 业务数据；删除成功或异常时通常为 `null` |

产品质量业务异常统一返回 `code = 500`，`messageCn` 为场景化中文提示、`messageEn` 为 `null`；参数校验失败返回 `code = 40001`，具体校验原因见 `data`。前端可直接展示 `messageCn`：

| `code` | `messageCn` | 触发场景 |
|---|---|---|
| `500` | `质量目标差距分析及分解数据不存在或已被删除` | 查询、修改或删除时记录不存在或已被逻辑删除 |
| `500` | `新增质量目标差距分析及分解数据失败` | 新增数据落库失败 |
| `500` | `修改质量目标差距分析及分解数据失败，记录不存在或已被删除` | 修改时记录不存在或已被逻辑删除 |
| `500` | `删除质量目标差距分析及分解数据失败，记录不存在或已被删除` | 删除时记录不存在或已被逻辑删除 |
| `500` | `批量删除失败，部分质量目标差距分析及分解数据不存在或已被删除` | 批量删除时存在无效 ID |
| `500` | `记录质量目标差距分析及分解数据操作日志失败` | 修改或删除操作日志落库失败 |
| `500` | `项目 ID 格式不正确，必须为数字` | 里程碑关联的项目 ID 不是合法数字 |
| `40001` | `请求参数异常` | 请求参数未通过校验，具体原因见 `data` |
| `403` | `没有权限` | token Cookie 缺失、无效，或用户无对应读写权限 |
| `500` | `系统异常` | 未被其他处理器捕获的系统异常 |

### 2.4 保存请求对象 `QualityObjectiveSaveReq`

| 字段 | 类型 | 必填 | 校验规则 | 说明 |
|---|---|---|---|---|
| `milestoneName` | String | 否 | 最大 255 字符 | 里程碑名称，由前端传入；修改时允许更新 |
| `perspectiveCategory` | String | 否 | 最大 128 字符 | 视角分类 |
| `subCategory` | String | 否 | 最大 128 字符 | 小类 |
| `qfdPrimaryCategory` | String | 否 | 最大 255 字符 | 一级分类QFD展开 |
| `qfdSecondaryCategory` | String | 否 | 最大 255 字符 | 二级分类QFD展开 |
| `qualityStrategy` | String | 是 | 非空白，最大 65535 字符 | 本版本质量策略 |
| `planningCategory` | String | 否 | 最大 64 字符 | 策划类别 |
| `planningSubmodule` | String | 否 | 最大 255 字符 | 策划项子模块 |
| `ownerRole` | String | 否 | 最大 128 字符 | 责任角色 |
| `submoduleOwner` | String | 否 | 最大 128 字符 | 子模块责任人 |
| `planningFinishTime` | String | 否 | 最大 20 字符 | 策划完成时间 |
| `qualityObjective` | String | 是 | 非空白，最大 65535 字符 | 质量目标 |
| `gapRiskAnalysis` | String | 是 | 非空白，最大 65535 字符 | 差距和风险分析 |
| `planningKeyPoints` | String | 否 | 最大 65535 字符 | 策划要点 |
| `keyMeasure` | String | 是 | 非空白，最大 65535 字符 | 关键措施 |
| `measureOwner` | String | 是 | 非空白，最大 128 字符 | 措施实施责任人 |
| `plannedFinishTime` | String | 是 | 非空白，最大 20 字符 | 计划完成时间 |
| `progressDescription` | String | 否 | 最大 65535 字符 | 措施进展说明 |
| `progress` | Decimal | 否 | 0～100，最多 2 位小数 | 措施进展百分比 |
| `completionStatus` | String | 否 | 最大 64 字符 | 措施完成状态 |
| `acceptanceCriteria` | String | 否 | 最大 65535 字符 | 验收标准 |
| `metricName` | String | 否 | 最大 255 字符 | 度量指标 |
| `targetValue` | String | 否 | 最大 255 字符 | 目标值 |
| `actualValue` | String | 否 | 最大 255 字符 | 实际值 |
| `achievementResult` | String | 否 | 最大 255 字符 | 目标达成结果 |
| `achievementDescription` | String | 否 | 最大 65535 字符 | 目标达成情况说明 |

### 2.5 响应对象 `QualityObjectiveResp`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Long | 记录主键 |
| `projectId` | Integer | 项目 ID，由里程碑归属生成 |
| `milestoneId` | Long | 里程碑 ID |
| `milestoneName` | String/null | 里程碑名称 |
| `perspectiveCategory` | String/null | 视角分类 |
| `subCategory` | String/null | 小类 |
| `qfdPrimaryCategory` | String/null | 一级分类QFD展开 |
| `qfdSecondaryCategory` | String/null | 二级分类QFD展开 |
| `qualityStrategy` | String | 本版本质量策略 |
| `planningCategory` | String/null | 策划类别 |
| `planningSubmodule` | String/null | 策划项子模块 |
| `ownerRole` | String/null | 责任角色 |
| `submoduleOwner` | String/null | 子模块责任人 |
| `planningFinishTime` | String/null | 策划完成时间 |
| `qualityObjective` | String | 质量目标 |
| `gapRiskAnalysis` | String | 差距和风险分析 |
| `planningKeyPoints` | String/null | 策划要点 |
| `keyMeasure` | String | 关键措施 |
| `measureOwner` | String | 措施实施责任人 |
| `plannedFinishTime` | String | 计划完成时间 |
| `progressDescription` | String/null | 措施进展说明 |
| `progress` | Decimal/null | 措施进展百分比 |
| `completionStatus` | String/null | 措施完成状态 |
| `acceptanceCriteria` | String/null | 验收标准 |
| `metricName` | String/null | 度量指标 |
| `targetValue` | String/null | 目标值 |
| `actualValue` | String/null | 实际值 |
| `achievementResult` | String/null | 目标达成结果 |
| `achievementDescription` | String/null | 目标达成情况说明 |
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
    "perspectiveCategory": "示例",
    "subCategory": "示例",
    "qfdPrimaryCategory": "示例",
    "qfdSecondaryCategory": "示例",
    "qualityStrategy": "示例",
    "planningCategory": "示例",
    "planningSubmodule": "示例",
    "ownerRole": "示例",
    "submoduleOwner": "示例",
    "planningFinishTime": "示例",
    "qualityObjective": "示例",
    "gapRiskAnalysis": "示例",
    "planningKeyPoints": "示例",
    "keyMeasure": "示例",
    "measureOwner": "示例",
    "plannedFinishTime": "示例",
    "progressDescription": "示例",
    "progress": 25.50,
    "completionStatus": "示例",
    "acceptanceCriteria": "示例",
    "metricName": "示例",
    "targetValue": "示例",
    "actualValue": "示例",
    "achievementResult": "示例",
    "achievementDescription": "示例",
    "createBy": "user-1",
    "createTime": "2026-11-09 10:00:00",
    "updateBy": "user-1",
    "updateTime": "2026-11-09 10:00:00"
  }
}
```

## 3. 新增

```http
POST /projects/product-quality/quality-objectives/add?milestoneId=7
Content-Type: application/json
```

服务端校验里程碑存在后，从里程碑生成 `projectId` 和 `milestoneId`，`milestoneName` 取自请求体（允许前端修改），并写入创建/更新审计字段。新增不写独立操作日志。

## 4. 分页查询

```http
GET /projects/product-quality/quality-objectives/getPage?milestoneId=7&page=1&pageSize=20
```

| 参数 | 位置 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|---|
| `page` | Query | Integer | 否 | `1` | 页码，必须大于 0 |
| `pageSize` | Query | Integer | 否 | `20` | 每页条数，1～200 |

仅查询 `deleted=0` 数据，按 `id DESC` 排序，由数据库分页。

## 5. 单条详情

```http
GET /projects/product-quality/quality-objectives/detail?milestoneId=7&id=1
```

目标不存在、已删除或跨里程碑时返回业务失败提示。

## 6. 修改

```http
POST /projects/product-quality/quality-objectives/update?milestoneId=7&id=1
Content-Type: application/json
```

修改采用全字段保存语义，保留主键、项目/里程碑归属和创建审计字段，更新请求字段（含 `milestoneName`）、更新人和更新时间。

业务修改与 `pq_quality_objective_log` 日志写入处于同一事务：日志保存修改前和修改后的完整 JSON 快照；任一步骤失败均回滚。

## 7. 单条逻辑删除

```http
GET /projects/product-quality/quality-objectives/delete?milestoneId=7&id=1
```

将目标记录 `deleted` 置为 `1`，并在同一事务写入操作日志：保存删除前完整 JSON，`new_data=null`。成功时 `data` 为 `null`。

## 8. 批量逻辑删除

```http
POST /projects/product-quality/quality-objectives/batch-delete?milestoneId=7
Content-Type: application/json
```

```json
{
  "ids": [1, 2, 3]
}
```

`ids` 非空、最多 200 个、每个 ID 为正整数，服务端按原顺序去重。任一目标不存在、已删除或不属于该里程碑时整批拒绝；删除和逐条日志写入任一步骤失败时整批回滚。每条日志均保存对应记录删除前完整 JSON，`new_data=null`。

## 9. 独立操作日志

日志表：`pq_quality_objective_log`。

| 字段 | 说明 |
|---|---|
| `id` | 日志主键 |
| `quality_objective_id` | 业务记录主键 |
| `old_data` | 修改或删除前完整 JSON，非空 |
| `new_data` | 修改后完整 JSON；删除时为 `null` |
| `update_by` | 操作人用户 ID |
| `update_time` | 操作时间 |

新增和查询不写该日志表；修改、单条删除和批量删除会写入。
