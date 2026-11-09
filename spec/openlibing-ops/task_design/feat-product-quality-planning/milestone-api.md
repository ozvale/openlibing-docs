# 产品质量项目里程碑接口文档（前端联调）

> 适用范围：仅包含 `ProductQualityMilestoneController` 的 4 个接口。
>
> 本文以当前代码为最终依据。示例中的 ID、名称和时间仅用于说明数据结构。

## 1. 接口清单

统一基础路径：`/projects/product-quality/milestones`

| 功能 | 请求方式 | 相对路径 | 成功时 `data` 类型 |
|---|---|---|---|
| 创建里程碑 | POST | `/add` | `MilestoneResp` |
| 查询项目里程碑列表 | GET | `/detail` | `List<MilestoneResp>` |
| 修改里程碑 | POST | `/update` | `MilestoneResp` |
| 删除里程碑 | GET | `/delete` | `null` |

本地服务端口为 `8098`，`context-path` 为 `/`。其他环境的域名、端口及网关前缀以部署配置为准。

## 2. 通用约定

### 2.1 身份认证与权限

四个接口均要求请求携带有效的 `token` Cookie，服务端从 JWT 中读取用户身份。

- 不接收通过 Query 参数传递的用户身份。
- 查询接口要求读权限（`canRead`），创建、修改、删除接口要求写权限（`canWrite`）。
- token 缺失、无效、无法解析出用户 ID 或用户不在产品质量策划白名单时，返回业务状态码 `403`。

### 2.2 公共 Query 参数

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `projectId` | Query | String | 是 | 项目 ID，最长 64 字符，不可为空白 |
| `id` | Query | Long | 视接口 | 里程碑 ID，正整数；修改、删除接口必填 |

### 2.3 统一响应结构

所有业务响应使用 `Result<T>`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | Integer | 业务状态码，成功固定为 `200` |
| `messageCn` | String | 中文消息，成功为 `成功` |
| `messageEn` | String | 英文消息，成功为 `success` |
| `data` | T/null | 业务数据；删除成功时为 `null` |

前端应根据响应体中的 `code` 判断业务是否成功，不要只依赖 HTTP 状态码。

### 2.4 里程碑对象 `MilestoneResp`

| 字段 | 类型 | 是否可能为 null | 说明 |
|---|---|---|---|
| `id` | Long | 否 | 里程碑 ID，对应 `pq_milestone.id` |
| `projectId` | String | 否 | 项目 ID |
| `projectName` | String | 是 | 项目名称 |
| `milestoneName` | String | 否 | 里程碑名称，同一项目内唯一 |
| `plannedTime` | String | 否 | 计划时间，格式 `yyyy-MM-dd HH:mm:ss` |
| `actualTime` | String | 是 | 实际时间，格式 `yyyy-MM-dd HH:mm:ss`；未发生时为空 |
| `createBy` | String | 否 | 创建人用户 ID |
| `createTime` | String | 否 | 创建时间，格式 `yyyy-MM-dd HH:mm:ss` |
| `updateBy` | String | 是 | 最后修改人用户 ID |
| `updateTime` | String | 是 | 最后修改时间，格式 `yyyy-MM-dd HH:mm:ss` |

所有时间字段统一返回 `yyyy-MM-dd HH:mm:ss` 格式字符串，不返回 ISO 8601 的 `T` 分隔格式，也不返回时间戳。

### 2.5 通用错误响应

| `code` | `messageCn` | 触发场景 |
|---|---|---|
| `40001` | `请求参数异常` | 参数校验失败、里程碑不存在、跨项目访问、同项目里程碑名称重复 |
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

## 3. 创建里程碑

### 3.1 请求

```http
POST /projects/product-quality/milestones/add?projectId=project-1
Content-Type: application/json
```

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `projectId` | Query | String | 是 | 项目 ID |

请求体 `MilestoneSaveReq`：

| 字段 | 类型 | 必填 | 校验规则 | 说明 |
|---|---|---|---|---|
| `projectName` | String | 否 | 最长 255 字符 | 项目名称；服务端最终以 `project_info` 中的项目名称为准 |
| `milestoneName` | String | 是 | 非空白，最长 255 字符 | 里程碑名称，同一项目内唯一 |
| `plannedTime` | String | 是 | `yyyy-MM-dd HH:mm:ss` | 计划时间 |
| `actualTime` | String | 否 | `yyyy-MM-dd HH:mm:ss` | 实际时间；未发生时可不传或传 `null` |

请求示例：

```json
{
  "projectName": "测试项目",
  "milestoneName": "需求冻结",
  "plannedTime": "2026-11-10 10:00:00",
  "actualTime": null
}
```

创建逻辑：

- 服务端校验写权限、同项目里程碑名称唯一性和项目存在性。
- 创建人、创建时间、更新人、更新时间由服务端生成，时间格式为 `yyyy-MM-dd HH:mm:ss`。
- 创建操作不写独立里程碑修改日志。

### 3.2 成功响应

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": {
    "id": 1,
    "projectId": "project-1",
    "projectName": "测试项目",
    "milestoneName": "需求冻结",
    "plannedTime": "2026-11-10 10:00:00",
    "actualTime": null,
    "createBy": "user-1",
    "createTime": "2026-11-09 17:06:52",
    "updateBy": "user-1",
    "updateTime": "2026-11-09 17:06:52"
  }
}
```

同一项目下里程碑名称重复时返回 `code = 40001`。

## 4. 查询项目里程碑列表

### 4.1 请求

```http
GET /projects/product-quality/milestones/detail?projectId=project-1
```

- 请求参数：仅公共 Query 参数 `projectId`。
- 无请求体。
- 返回该项目下全部里程碑，按 `id DESC` 排序，不做分页。

### 4.2 成功响应

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": [
    {
      "id": 1,
      "projectId": "project-1",
      "projectName": "测试项目",
      "milestoneName": "需求冻结",
      "plannedTime": "2026-11-10 10:00:00",
      "actualTime": null,
      "createBy": "user-1",
      "createTime": "2026-11-09 17:06:52",
      "updateBy": "user-1",
      "updateTime": "2026-11-09 17:06:52"
    }
  ]
}
```

无记录时 `data` 为空数组。

## 5. 修改里程碑

### 5.1 请求

```http
POST /projects/product-quality/milestones/update?projectId=project-1&id=1
Content-Type: application/json
```

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `projectId` | Query | String | 是 | 项目 ID |
| `id` | Query | Long | 是 | 里程碑 ID |

请求体 `MilestoneSaveReq` 与创建接口一致：

```json
{
  "projectName": "测试项目",
  "milestoneName": "代码冻结",
  "plannedTime": "2026-11-20 10:00:00",
  "actualTime": "2026-11-20 09:30:00"
}
```

修改逻辑：

- 全量覆盖 `projectName`、`milestoneName`、`plannedTime`、`actualTime`。
- 创建人、创建时间保持不变；更新人和更新时间由服务端生成，时间格式为 `yyyy-MM-dd HH:mm:ss`。
- 在同一事务内写入 `pq_milestone_log` 日志表，记录新旧完整 JSON 快照。
- 记录不存在、跨项目修改或修改后名称与当前项目其他里程碑重复时返回 `code = 40001`。

### 5.2 成功响应

成功时 `data` 返回修改后的完整 `MilestoneResp`，字段与创建成功响应一致。

## 6. 删除里程碑

### 6.1 请求

```http
GET /projects/product-quality/milestones/delete?projectId=project-1&id=1
```

- 请求参数：`projectId`、`id`。
- 无请求体。
- 当前实现按 `id + projectId` **物理删除**，并在同一事务内写入 `old_data` 快照、`new_data = null` 的日志记录。

### 6.2 成功响应

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": null
}
```

记录不存在或不属于该 `projectId` 时返回 `code = 40001`。前端删除成功后应移除本地记录或重新查询列表。

## 7. 前端类型参考

```typescript
interface Result<T> {
  code: number;
  messageCn: string;
  messageEn: string;
  data: T | null;
}

interface MilestoneResp {
  id: number;
  projectId: string;
  projectName: string | null;
  milestoneName: string;
  plannedTime: string;
  actualTime: string | null;
  createBy: string;
  createTime: string;
  updateBy: string | null;
  updateTime: string | null;
}

interface MilestoneSaveReq {
  projectName?: string | null;
  milestoneName: string;
  plannedTime: string;
  actualTime?: string | null;
}
```

若前端使用 JavaScript 的 `number` 承载 Long ID，应遵守项目现有的长整型处理约定，避免超出安全整数范围后精度丢失。
