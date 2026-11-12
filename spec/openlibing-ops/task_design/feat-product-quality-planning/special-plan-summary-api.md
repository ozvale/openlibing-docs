# 专项策划总结接口文档（前端联调）

> 适用范围：仅包含 `ProductQualitySpecialPlanSummaryController` 的 2 个接口。
>
> 本文以当前代码为最终依据，结合 `V20261104__product_quality_planning.sql` 补充字段含义。示例中的 ID、名称和内容仅用于说明数据结构。

## 1. 接口清单

统一基础路径：`/projects/product-quality/special-plan-summaries`

| 功能 | 请求方式 | 相对路径 | 成功时 `data` 类型 |
|---|---|---|---|
| 查询专项策划总结 | GET | `/detail` | `SpecialPlanSummaryResp`，无记录时为 `null` |
| 保存专项策划总结 | POST | `/update` | `SpecialPlanSummaryResp` |

本地服务端口为 `8098`，`context-path` 为 `/`。其他环境的域名、端口及网关前缀以部署配置为准。

## 2. 通用约定

### 2.1 身份认证与权限

两个接口均要求请求携带有效的 `token` Cookie，服务端从 JWT 中读取用户身份，并通过产品质量策划权限白名单校验读写权限。

- 不接收通过 Query 参数或请求体传递的用户身份。
- 查询接口要求读权限，保存接口要求写权限。
- token 缺失、无效、无法解析用户身份或无相应权限时，请求被拒绝。

### 2.2 公共 Query 参数

两个接口均必须传入以下参数：

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `milestoneId` | Query | Long | 是 | 里程碑 ID，对应 `pq_milestone.id`；前端应传正整数并在发起请求前校验非空和格式 |

请求示例：

```http
GET /projects/product-quality/special-plan-summaries/detail?milestoneId=7
```

### 2.3 统一响应结构

所有业务响应使用 `Result<T>`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | Integer | 业务状态码，成功固定为 `200` |
| `messageCn` | String | 中文消息，成功为 `成功` |
| `messageEn` | String | 英文消息，成功为 `success` |
| `data` | T/null | 业务数据；异常响应通常为 `null` |

前端应根据响应体中的 `code` 判断业务是否成功，不要只依赖 HTTP 状态码。

### 2.4 专项策划总结对象 `SpecialPlanSummaryResp`

| 字段 | 类型 | 是否可能为 null | 说明 |
|---|---|---|---|
| `id` | Long | 否 | 专项策划总结记录主键，对应 `pq_special_plan_summary.id` |
| `projectId` | Integer | 否 | 项目 ID，由里程碑归属生成 |
| `milestoneId` | Long | 否 | 里程碑 ID |
| `milestoneName` | String | 是 | 里程碑名称 |
| `summary` | String | 是 | 专项策划总结内容 |
| `createBy` | String | 否 | 创建人用户 ID |
| `createTime` | String | 否 | 创建时间，格式 `yyyy-MM-dd HH:mm:ss` |
| `updateBy` | String | 是 | 最后修改人用户 ID |
| `updateTime` | String | 是 | 最后修改时间，格式 `yyyy-MM-dd HH:mm:ss` |

### 2.5 通用错误响应

产品质量业务异常与参数校验失败统一返回 `code = 40001`，`messageCn` 为具体场景提示、`messageEn` 为 `params invalid`；参数校验失败时具体原因同时写入 `data`。前端可直接展示 `messageCn`：

| `code` | `messageCn` | 触发场景 |
|---|---|---|
| `40001` | `新增专项策划总结数据失败` | 首次保存时数据落库失败 |
| `40001` | `修改专项策划总结数据失败，记录不存在或已被删除` | 后续保存时记录不存在或已被逻辑删除 |
| `40001` | `保存专项策划总结修改日志失败` | 保存操作日志落库失败 |
| `40001` | `项目 ID 格式不正确，必须为数字` | 里程碑所属项目 ID 不是合法数字 |
| `40001` | 具体校验提示 | 请求参数未通过校验，`messageCn` 与 `data` 均为具体校验原因 |
| `403` | `没有权限` | token Cookie 缺失、无效，或用户无对应读写权限 |
| `500` | `系统异常` | 未被其他处理器捕获的系统异常 |

错误响应示例：

```json
{
  "code": 403,
  "messageCn": "没有权限",
  "messageEn": "no permission",
  "data": null
}
```

## 3. 查询专项策划总结

### 3.1 请求

```http
GET /projects/product-quality/special-plan-summaries/detail?milestoneId=7
```

- 请求参数：仅公共 Query 参数 `milestoneId`。
- 无请求体。
- 查询 `pq_special_plan_summary` 中指定里程碑的 `deleted = 0` 记录，每个里程碑至多一条。
- 未创建过专项策划总结时，成功返回 `data: null`。

### 3.2 成功响应

有记录时：

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
    "summary": "本里程碑专项策划整体按计划推进，关键风险已闭环。",
    "createBy": "user-1",
    "createTime": "2026-11-10 10:00:00",
    "updateBy": "user-1",
    "updateTime": "2026-11-10 10:00:00"
  }
}
```

无记录时：

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": null
}
```

## 4. 保存专项策划总结

### 4.1 请求

```http
POST /projects/product-quality/special-plan-summaries/update?milestoneId=7
Content-Type: application/json
```

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `milestoneId` | Query | Long | 是 | 里程碑 ID |

请求体 `SpecialPlanSummarySaveReq`：

| 字段 | 类型 | 必填 | 校验规则 | 说明 |
|---|---|---|---|---|
| `milestoneName` | String | 否 | 最大 255 字符 | 里程碑名称，由前端传入；修改时允许更新 |
| `summary` | String | 否 | 最大 65,535 字符 | 专项策划总结内容；允许清空 |

请求示例：

```json
{
  "summary": "本里程碑专项策划整体按计划推进，关键风险已闭环。"
}
```

### 4.2 保存逻辑

- 首次保存：服务端校验里程碑存在后，从里程碑获取项目 ID，里程碑名称取自请求体（允许前端修改），创建新记录。创建操作不写独立修改日志。
- 后续保存：保留主键、项目 ID、里程碑 ID、创建人、创建时间不变，更新 `milestoneName`（写入 `milestone_name` 列）、`summary`、更新人和更新时间。更新操作在同一事务内写入 `pq_special_plan_summary_log` 日志表，记录新旧完整 JSON 快照。
- `summary` 允许传 `null` 或空字符串，表示清空内容。
- 业务修改与日志写入处于同一事务，任一步骤失败均回滚。

### 4.3 成功响应

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
    "summary": "本里程碑专项策划整体按计划推进，关键风险已闭环。",
    "createBy": "user-1",
    "createTime": "2026-11-10 10:00:00",
    "updateBy": "user-2",
    "updateTime": "2026-11-10 11:00:00"
  }
}
```

## 5. 独立操作日志

日志表：`pq_special_plan_summary_log`。

| 字段 | 说明 |
|---|---|
| `id` | 日志主键 |
| `special_plan_summary_id` | 专项策划总结记录主键 |
| `old_data` | 修改前完整 JSON，非空 |
| `new_data` | 修改后完整 JSON |
| `update_by` | 操作人用户 ID |
| `update_time` | 操作时间 |

查询和首次保存不写该日志表；后续保存会写入一条新旧快照日志。

## 6. 前端类型参考

```typescript
interface Result<T> {
  code: number;
  messageCn: string;
  messageEn: string;
  data: T | null;
}

interface SpecialPlanSummaryResp {
  id: number;
  projectId: number;
  milestoneId: number;
  milestoneName: string | null;
  summary: string | null;
  createBy: string;
  createTime: string;
  updateBy: string | null;
  updateTime: string | null;
}

interface SpecialPlanSummarySaveReq {
  summary: string | null;
}
```

若前端使用 JavaScript 的 `number` 承载 Long ID，应遵守项目现有的长整型处理约定，避免超出安全整数范围后精度丢失。
