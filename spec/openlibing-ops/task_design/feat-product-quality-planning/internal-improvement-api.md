# 内部改进要求和重点工作接口文档（前端联调）

> 适用范围：`ProductQualityInternalImprovementController` 的新增、分页、详情、修改、单条删除和批量删除接口。
>
> 本文以当前代码和 `V20261104__product_quality_planning.sql` 为依据，示例数据仅用于说明结构。

## 1. 接口清单

统一基础路径：`/projects/product-quality/internal-improvements`

| 功能 | 请求方式 | 相对路径 | 成功时 `data` 类型 |
|---|---|---|---|
| 新增 | POST | `/add` | `InternalImprovementResp` |
| 分页查询 | GET | `/getPage` | `PageResult<InternalImprovementResp>` |
| 单条详情 | GET | `/detail` | `InternalImprovementResp` |
| 修改 | POST | `/update` | `InternalImprovementResp` |
| 单条逻辑删除 | GET | `/delete` | `null` |
| 批量逻辑删除 | POST | `/batch-delete` | `null` |

本地服务端口为 `8098`，`context-path` 为 `/`。其他环境的域名、端口及网关前缀以部署配置为准。

## 2. 通用约定

### 2.1 身份认证与权限

所有接口均要求请求携带有效的 `token` Cookie，服务端从 JWT 中读取用户身份，并通过产品质量策划权限白名单校验读写权限。

- 不接收通过 Query 参数或请求体传递的用户身份。
- 查询接口要求读权限，新增、修改和删除接口要求写权限。
- token 缺失、无效、无法解析用户身份或无相应权限时，请求被拒绝。

### 2.2 公共 Query 参数

所有接口均必须传入：

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

产品质量业务异常与参数校验失败统一返回 `code = 40001`，`messageCn` 为具体场景提示、`messageEn` 为 `params invalid`；参数校验失败时具体原因同时写入 `data`。前端可直接展示 `messageCn`：

| `code` | `messageCn` | 触发场景 |
|---|---|---|
| `40001` | `内部改进数据不存在或已被删除` | 查询、修改或删除时记录不存在或已被逻辑删除 |
| `40001` | `新增内部改进数据失败` | 新增数据落库失败 |
| `40001` | `修改内部改进数据失败，记录不存在或已被删除` | 修改时记录不存在或已被逻辑删除 |
| `40001` | `删除内部改进数据失败，记录不存在或已被删除` | 删除时记录不存在或已被逻辑删除 |
| `40001` | `批量删除失败，部分内部改进数据不存在或已被删除` | 批量删除时存在无效 ID |
| `40001` | `记录内部改进数据操作日志失败` | 修改或删除操作日志落库失败 |
| `40001` | `项目 ID 格式不正确，必须为数字` | 里程碑关联的项目 ID 不是合法数字 |
| `40001` | 具体校验提示 | 请求参数未通过校验，`messageCn` 与 `data` 均为具体校验原因 |
| `403` | `没有权限` | token Cookie 缺失、无效，或用户无对应读写权限 |
| `500` | `系统异常` | 未被其他处理器捕获的系统异常 |

### 2.4 保存请求对象 `InternalImprovementSaveReq`

新增和修改共用以下请求体：

| 字段 | 类型 | 必填 | 校验规则 | 说明 |
|---|---|---|---|---|
| `milestoneName` | String | 否 | 最大 255 字符 | 里程碑名称，由前端传入；修改时允许更新 |
| `category` | String | 否 | 最大 64 字符 | 类别 |
| `name` | String | 否 | 最大 255 字符 | 名称 |
| `improvementTarget` | String | 是 | 非空白，最大 65535 字符 | 本版本改进目标 |
| `implementationMeasure` | String | 是 | 非空白，最大 65535 字符 | 本版本落地措施 |
| `ownerName` | String | 是 | 非空白，最大 128 字符 | 责任人 |
| `plannedFinishTime` | String | 是 | 非空白，最大 20 字符 | 计划完成时间，建议 `yyyy-MM-dd` |
| `status` | String | 否 | 最大 64 字符 | 状态 |
| `progress` | Decimal | 否 | 0～100，最多 2 位小数 | 措施进展百分比 |
| `progressDescription` | String | 否 | 最大 65535 字符 | 进展说明 |

请求体示例：

```json
{
  "category": "内部改进要求",
  "name": "重点工作",
  "improvementTarget": "提升版本需求评审覆盖率",
  "implementationMeasure": "建立评审清单并跟踪闭环",
  "ownerName": "张三",
  "plannedFinishTime": "2026-12-31",
  "status": "进行中",
  "progress": 25.50,
  "progressDescription": "已完成评审清单制定"
}
```

### 2.5 响应对象 `InternalImprovementResp`

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Long | 记录主键 |
| `projectId` | Integer | 项目 ID，由里程碑归属生成 |
| `milestoneId` | Long | 里程碑 ID |
| `milestoneName` | String/null | 里程碑名称 |
| `category` | String/null | 类别 |
| `name` | String/null | 名称 |
| `improvementTarget` | String | 本版本改进目标 |
| `implementationMeasure` | String | 本版本落地措施 |
| `ownerName` | String | 责任人 |
| `plannedFinishTime` | String | 计划完成时间 |
| `status` | String/null | 状态 |
| `progress` | Decimal/null | 措施进展百分比 |
| `progressDescription` | String/null | 进展说明 |
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
    "category": "内部改进要求",
    "name": "重点工作",
    "improvementTarget": "提升版本需求评审覆盖率",
    "implementationMeasure": "建立评审清单并跟踪闭环",
    "ownerName": "张三",
    "plannedFinishTime": "2026-12-31",
    "status": "进行中",
    "progress": 25.50,
    "progressDescription": "已完成评审清单制定",
    "createBy": "user-1",
    "createTime": "2026-11-07 10:00:00",
    "updateBy": "user-1",
    "updateTime": "2026-11-07 10:00:00"
  }
}
```

## 3. 新增

```http
POST /projects/product-quality/internal-improvements/add?milestoneId=7
Content-Type: application/json
```

请求体见 `InternalImprovementSaveReq`。服务端校验里程碑存在后，从里程碑生成 `projectId` 和 `milestoneId`，`milestoneName` 取自请求体（允许前端修改），并写入创建/更新审计字段。新增不写独立操作日志，成功响应见单条响应示例。

## 4. 分页查询

```http
GET /projects/product-quality/internal-improvements/getPage?milestoneId=7&page=1&pageSize=20
```

| 参数 | 位置 | 类型 | 必填 | 默认值 | 说明 |
|---|---|---|---|---|---|
| `page` | Query | Integer | 否 | `1` | 页码，必须大于 0 |
| `pageSize` | Query | Integer | 否 | `20` | 每页条数，1～200 |

仅查询 `deleted=0` 数据，按 `id DESC` 排序，由数据库分页。成功响应：

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": {
    "records": [
      {
        "id": 1,
        "projectId": 100,
        "milestoneId": 7,
        "milestoneName": "TR1",
        "category": "内部改进要求",
        "name": "重点工作",
        "improvementTarget": "提升版本需求评审覆盖率",
        "implementationMeasure": "建立评审清单并跟踪闭环",
        "ownerName": "张三",
        "plannedFinishTime": "2026-12-31",
        "status": "进行中",
        "progress": 25.50,
        "progressDescription": "已完成评审清单制定",
        "createBy": "user-1",
        "createTime": "2026-11-07 10:00:00",
        "updateBy": "user-1",
        "updateTime": "2026-11-07 10:00:00"
      }
    ],
    "total": 1,
    "pageSize": 20,
    "page": 1
  }
}
```

## 5. 单条详情

```http
GET /projects/product-quality/internal-improvements/detail?milestoneId=7&id=1
```

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `id` | Query | Long | 是 | 记录主键，必须为正整数 |

成功响应见单条响应示例。目标不存在、已删除或跨里程碑时返回业务失败提示，不返回 `data:null` 冒充成功。

## 6. 修改

```http
POST /projects/product-quality/internal-improvements/update?milestoneId=7&id=1
Content-Type: application/json
```

Query 参数 `id` 为正整数，请求体见 `InternalImprovementSaveReq`。修改采用全字段保存语义，保留主键、项目/里程碑归属和创建审计字段，更新请求字段（含 `milestoneName`，写入 `milestone_name` 列）、更新人和更新时间。

业务修改与 `pq_internal_improvement_log` 日志写入处于同一事务：日志保存修改前和修改后的完整 JSON 快照；任一步骤失败均回滚。

## 7. 单条逻辑删除

```http
GET /projects/product-quality/internal-improvements/delete?milestoneId=7&id=1
```

将目标记录 `deleted` 置为 `1`，并在同一事务写入操作日志：保存删除前完整 JSON，`new_data=null`。成功响应：

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": null
}
```

## 8. 批量逻辑删除

```http
POST /projects/product-quality/internal-improvements/batch-delete?milestoneId=7
Content-Type: application/json
```

请求体：

| 字段 | 类型 | 必填 | 校验规则 | 说明 |
|---|---|---|---|---|
| `ids` | Long[] | 是 | 非空，最多 200 个，每个 ID 为正整数 | 删除目标；服务端按原顺序去重 |

```json
{
  "ids": [1, 2, 3]
}
```

服务端锁定并校验全部目标。任一目标不存在、已删除或不属于该里程碑时，整批拒绝；删除和逐条日志写入任一步骤失败时，整批回滚。每条日志均保存对应记录删除前完整 JSON，`new_data=null`。成功响应与单条删除相同。

## 9. 独立操作日志

日志表：`pq_internal_improvement_log`。

| 字段 | 说明 |
|---|---|
| `id` | 日志主键 |
| `internal_improvement_id` | 内部改进记录主键 |
| `old_data` | 修改或删除前完整 JSON，非空 |
| `new_data` | 修改后完整 JSON；删除时为 `null` |
| `update_by` | 操作人用户 ID |
| `update_time` | 操作时间 |

新增和查询不写该日志表；修改、单条删除和批量删除会写入。
