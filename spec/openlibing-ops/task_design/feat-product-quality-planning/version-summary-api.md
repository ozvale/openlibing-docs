# 产品质量版本摘要接口文档（前端联调）

> 适用范围：仅包含 `ProductQualityVersionSummaryController` 的 2 个接口。
>
> 本文以当前代码为最终依据，结合 `V20261104__product_quality_planning.sql` 补充字段含义。示例中的 ID、名称和内容仅用于说明数据结构。

## 1. 接口清单

统一基础路径：`/projects/product-quality/version-summary`

| 功能 | 请求方式 | 相对路径 | 成功时 `data` 类型 |
|---|---|---|---|
| 查询版本摘要 | GET | `/detail` | `VersionSummaryResp`，无记录时为 `null` |
| 保存版本摘要 | POST | `/update` | `VersionSummaryResp` |

本地服务端口为 `8098`，`context-path` 为 `/`。其他环境的域名、端口及网关前缀以部署配置为准。

## 2. 通用约定

### 2.1 身份认证与权限

两个接口均要求请求携带有效的 `token` Cookie，服务端从 JWT 中读取用户身份。

- 不接收通过 Query 参数传递的用户身份。
- 查询接口要求读权限（`canRead`），保存接口要求写权限（`canWrite`）。
- token 缺失、无效或无法解析出用户 ID 时，返回业务状态码 `403`。

### 2.2 公共 Query 参数

两个接口均必须传入以下参数：

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `milestoneId` | Query | Long | 是 | 里程碑 ID，对应 `pq_milestone.id`；必须为大于 0 的整数，前端应在发起请求前校验非空和格式 |

请求示例：

```http
GET /projects/product-quality/version-summary/detail?milestoneId=7
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

### 2.4 版本摘要对象 `VersionSummaryResp`

| 字段 | 类型 | 是否可能为 null | 说明 |
|---|---|---|---|
| `id` | Long | 否 | 版本摘要记录主键，对应 `pq_version_summary.id` |
| `projectId` | Integer | 否 | 项目 ID，首次保存时由服务端根据里程碑生成 |
| `milestoneId` | Long | 否 | 里程碑 ID |
| `milestoneName` | String | 是 | 里程碑名称，首次保存时由服务端根据里程碑生成 |
| `summaryHtml` | String | 是 | 版本摘要富文本（HTML 片段），已在服务端按白名单清理 |
| `createBy` | String | 否 | 创建人用户 ID |
| `createTime` | String | 否 | 创建时间，格式 `yyyy-MM-dd HH:mm:ss` |
| `updateBy` | String | 是 | 最后修改人用户 ID |
| `updateTime` | String | 是 | 最后修改时间，格式 `yyyy-MM-dd HH:mm:ss` |

所有时间字段统一返回 `yyyy-MM-dd HH:mm:ss` 格式字符串，不返回 ISO 8601 的 `T` 分隔格式，也不返回时间戳。

### 2.5 通用错误响应

| `code` | `messageCn` | 触发场景 |
|---|---|---|
| `40001` | `请求参数异常` | `milestoneId` 校验失败、里程碑不存在、里程碑项目 ID 非数字 |
| `403` | `没有权限` | token Cookie 缺失、无效或未包含有效用户 ID |
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

## 3. 查询版本摘要

### 3.1 请求

```http
GET /projects/product-quality/version-summary/detail?milestoneId=7
```

- 请求参数：仅公共 Query 参数 `milestoneId`。
- 无请求体。
- 查询 `pq_version_summary` 中指定里程碑的 `deleted = 0` 记录。
- 未创建过版本摘要时，成功返回 `data: null`。

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
    "summaryHtml": "<h2>版本摘要</h2><p>本版本聚焦质量目标收敛。</p>",
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

## 4. 保存版本摘要

### 4.1 请求

```http
POST /projects/product-quality/version-summary/update?milestoneId=7
Content-Type: application/json
```

| 参数 | 位置 | 类型 | 必填 | 说明 |
|---|---|---|---|---|
| `milestoneId` | Query | Long | 是 | 里程碑 ID，必须为大于 0 的整数 |

请求体 `VersionSummarySaveReq`：

| 字段 | 类型 | 必填 | 校验规则 | 说明 |
|---|---|---|---|---|
| `summaryHtml` | String | 否 | 最大 100,000 字符 | 版本摘要富文本；允许传 `null` 或空字符串表示清空内容 |

请求示例：

```json
{
  "summaryHtml": "<h2>版本摘要</h2><p>本版本聚焦质量目标收敛。</p>"
}
```

### 4.2 保存逻辑

- 首次保存：服务端校验里程碑存在后，从里程碑获取项目 ID 和里程碑名称，创建新记录。创建操作不写独立修改日志。
  - 里程碑 ID 为字符串，服务端会将其转换为 `Integer` 写入 `project_id`；非数字时返回 `40001`。
- 后续保存：保留主键、项目 ID、里程碑 ID/名称、创建人、创建时间不变，仅更新 `summaryHtml`、更新人和更新时间。更新操作在同一事务内写入 `pq_version_summary_log` 日志表，记录新旧完整 JSON 快照。
- `summaryHtml` 会经过服务端 OWASP HTML 白名单清理后再落库：保留常见块级与行内排版元素，以及 `table`、`thead`、`tbody`、`tfoot`、`tr`、`th`、`td`、`caption`、`hr`、`a`；`a` 仅保留 `href`，`th`/`td` 仅保留 `colspan`、`rowspan`；链接仅允许 `http`、`https` 协议并自动追加 `rel="nofollow"`。`script`、`style`、`iframe`、事件属性及危险协议会被移除。
- 清理后长度仍受请求校验上限约束，前端应在提交前自行限制富文本长度。
- 同一里程碑同时只存在一条有效记录（`milestone_id + deleted` 唯一约束）。

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
    "summaryHtml": "<h2>版本摘要</h2><p>本版本聚焦质量目标收敛。</p>",
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

interface VersionSummaryResp {
  id: number;
  projectId: number;
  milestoneId: number;
  milestoneName: string | null;
  summaryHtml: string | null;
  createBy: string;
  createTime: string;
  updateBy: string | null;
  updateTime: string | null;
}

interface VersionSummarySaveReq {
  summaryHtml: string | null;
}
```

若前端使用 JavaScript 的 `number` 承载 Long ID，应遵守项目现有的长整型处理约定，避免超出安全整数范围后精度丢失。
