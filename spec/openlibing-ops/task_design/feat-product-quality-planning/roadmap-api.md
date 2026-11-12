# 产品质量策划思路接口文档（前端联调）

> 适用范围：仅包含 `ProductQualityRoadmapController` 的 2 个接口。
>
> 本文以当前代码为最终依据，结合 `V20261104__product_quality_planning.sql` 补充字段含义。示例中的 ID、名称和内容仅用于说明数据结构。

## 1. 接口清单

统一基础路径：`/projects/product-quality/roadmap`

| 功能 | 请求方式 | 相对路径 | 成功时 `data` 类型 |
|---|---|---|---|
| 查询质量策划思路 | GET | `/detail` | `RoadmapResp`，无记录时为 `null` |
| 保存质量策划思路 | POST | `/update` | `RoadmapResp` |

本地服务端口为 `8098`，`context-path` 为 `/`。其他环境的域名、端口及网关前缀以部署配置为准。

## 2. 通用约定

### 2.1 身份认证

两个接口均要求请求携带有效的 `token` Cookie，服务端从 JWT 中读取用户身份。

- 不接收通过 Query 参数传递的用户身份。
- token 缺失、无效或无法解析出用户 ID 时，返回业务状态码 `403`。
- 跨域请求由前端按现有工程认证方式携带 Cookie。

### 2.2 公共 Query 参数

两个接口均必须传入以下参数：

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `milestoneId` | Query | Long | 是 | 里程碑 ID，对应 `pq_milestone.id`；前端应传正整数并在发起请求前校验非空和格式 |

请求示例：

```http
GET /projects/product-quality/roadmap/detail?milestoneId=7
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

### 2.4 质量策划思路对象 `RoadmapResp`

| 字段 | 类型 | 是否可能为 null | 说明 |
|---|---|---|---|
| `id` | Long | 否 | 质量策划思路记录主键，对应 `pq_quality_roadmap.id` |
| `projectId` | Integer | 否 | 项目 ID |
| `milestoneId` | Long | 否 | 里程碑 ID |
| `milestoneName` | String | 是 | 里程碑名称 |
| `roadmapJson` | String | 是 | 质量策划思路文档，JSON 格式字符串 |
| `createBy` | String | 否 | 创建人用户 ID |
| `createTime` | String | 否 | 创建时间，格式 `yyyy-MM-dd HH:mm:ss` |
| `updateBy` | String | 是 | 最后修改人用户 ID |
| `updateTime` | String | 是 | 最后修改时间，格式 `yyyy-MM-dd HH:mm:ss` |

### 2.5 通用错误响应

产品质量业务异常统一返回 `code = 500`，`messageCn` 为场景化中文提示、`messageEn` 为 `null`；参数校验失败返回 `code = 40001`，具体校验原因见 `data`。前端可直接展示 `messageCn`：

| `code` | `messageCn` | 触发场景 |
|---|---|---|
| `500` | `新增质量策划思路失败` | 新增数据落库失败 |
| `500` | `修改质量策划思路失败，记录不存在或已被删除` | 修改时记录不存在或已被逻辑删除 |
| `500` | `记录质量策划思路操作日志失败` | 修改操作日志落库失败 |
| `500` | `项目 ID 格式不正确，必须为数字` | 里程碑关联的项目 ID 不是合法数字 |
| `40001` | `请求参数异常` | 请求参数未通过校验，具体原因见 `data` |
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

## 3. 查询质量策划思路

### 3.1 请求

```http
GET /projects/product-quality/roadmap/detail?milestoneId=7
```

- 请求参数：仅公共 Query 参数 `milestoneId`。
- 无请求体。
- 查询 `pq_quality_roadmap` 中指定里程碑的 `deleted = 0` 记录。
- 未创建过质量策划思路时，成功返回 `data: null`。

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
    "roadmapJson": "{\"nodes\":[...]}",
    "createBy": "user-1",
    "createTime": "2026-11-07 10:00:00",
    "updateBy": "user-1",
    "updateTime": "2026-11-07 10:00:00"
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

## 4. 保存质量策划思路

### 4.1 请求

```http
POST /projects/product-quality/roadmap/update?milestoneId=7
Content-Type: application/json
```

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `milestoneId` | Query | Long | 是 | 里程碑 ID |

请求体 `RoadmapSaveReq`：

| 字段 | 类型 | 必填 | 校验规则 | 说明 |
|---|---|---|---|---|
| `milestoneName` | String | 否 | 最大 255 字符 | 里程碑名称，由前端传入；修改时允许更新 |
| `roadmapJson` | String | 否 | 最大 200,000 字符 | 质量策划思路文档，JSON 格式字符串；允许清空 |

请求示例：

```json
{
  "roadmapJson": "{\"nodes\":[{\"id\":\"1\",\"text\":\"质量目标\"}]}"
}
```

### 4.2 保存逻辑

- 首次保存：服务端校验里程碑存在后，从里程碑获取项目 ID，里程碑名称取自请求体（允许前端修改），创建新记录。创建操作不写独立修改日志。
- 后续保存：保留主键、项目 ID、里程碑 ID、创建人、创建时间不变，更新 `milestoneName`、`roadmapJson`、更新人和更新时间。更新操作在同一事务内写入 `pq_quality_roadmap_log` 日志表，记录新旧完整 JSON 快照。
- `roadmapJson` 允许传 `null` 或空字符串，表示清空内容。

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
    "roadmapJson": "{\"nodes\":[{\"id\":\"1\",\"text\":\"质量目标\"}]}",
    "createBy": "user-1",
    "createTime": "2026-11-07 10:00:00",
    "updateBy": "user-2",
    "updateTime": "2026-11-07 11:00:00"
  }
}
```

## 5. 前端类型参考

```typescript
interface Result<T> {
  code: number;
  messageCn: string;
  messageEn: string;
  data: T | null;
}

interface RoadmapResp {
  id: number;
  projectId: number;
  milestoneId: number;
  milestoneName: string | null;
  roadmapJson: string | null;
  createBy: string;
  createTime: string;
  updateBy: string | null;
  updateTime: string | null;
}

interface RoadmapSaveReq {
  roadmapJson: string | null;
}
```

若前端使用 JavaScript 的 `number` 承载 Long ID，应遵守项目现有的长整型处理约定，避免超出安全整数范围后精度丢失。
