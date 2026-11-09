# 产品质量人员角色查询接口文档（前端联调）

> 适用范围：仅包含 `ProductQualityUserRoleController` 的 1 个接口。
>
> 本文以当前代码为最终依据。接口通过 openlibing-framework 的内部接口 `POST /internal-server/get-user-role` 查询人员角色信息，示例中的 ID、名称和内容仅用于说明数据结构。

## 1. 接口清单

统一基础路径：`/projects/product-quality/user-roles`

| 功能 | 请求方式 | 相对路径 | 成功时 `data` 类型 |
|---|---|---|---|
| 查询人员角色信息 | POST | `/query` | `PageResult<UserRoleResp>` |

本地服务端口为 `8098`，`context-path` 为 `/`。其他环境的域名、端口及网关前缀以部署配置为准。

## 2. 通用约定

### 2.1 身份认证

接口要求请求携带有效的 `token` Cookie，服务端从 JWT 中读取用户身份并校验产品质量策划读权限。

- 不接收通过 Query 参数传递的用户身份。
- 请求体中的 `userId` 仅表示要查询的目标用户，不用于鉴权。
- `userId` 为空或空白时，默认查询当前 token 用户自己的角色。
- token 缺失、无效或无法解析出用户 ID 时，返回业务状态码 `403`。

### 2.2 统一响应结构

所有业务响应使用 `Result<T>`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `code` | Integer | 业务状态码，成功固定为 `200` |
| `messageCn` | String | 中文消息，成功为 `成功` |
| `messageEn` | String | 英文消息，成功为 `success` |
| `data` | T/null | 业务数据；异常响应通常为 `null` |

分页数据使用 `PageResult<T>`：

| 字段 | 类型 | 说明 |
|---|---|---|
| `records` | Array<UserRoleResp> | 当前页人员角色列表 |
| `total` | Integer | 满足条件的记录总数 |
| `pageSize` | Integer | 本次查询每页条数 |
| `page` | Integer | 本次查询页码 |

前端应根据响应体中的 `code` 判断业务是否成功，不要只依赖 HTTP 状态码。

### 2.3 人员角色对象 `UserRoleResp`

| 字段 | 类型 | 是否可能为 null | 说明 |
|---|---|---|---|
| `id` | Integer | 否 | 人员角色记录主键 |
| `userId` | String | 否 | 用户 ID |
| `userName` | String | 是 | 用户名 |
| `userEmail` | String | 是 | 用户邮箱 |
| `role` | String | 是 | 角色标识，如 `admin`、`TEST`、`PM` |
| `productId` | Integer | 是 | 归属产业 ID |
| `projectId` | Integer | 是 | 归属项目 ID |
| `repoId` | Integer | 是 | 归属仓库 ID |
| `permGroupId` | Long | 是 | 权限组 ID，`0` 表示默认权限组 |
| `createTime` | String | 是 | 创建时间 |
| `updateTime` | String | 是 | 更新时间 |
| `syncFlag` | String | 是 | 数据同步标识：`1` 来自 ubmc，`2` 来自 majun，`3` 来自 gitee，`4` 来自 gitcode |

## 3. 查询人员角色信息

### 3.1 请求

```http
POST /projects/product-quality/user-roles/query
Content-Type: application/json
```

请求体 `UserRoleQueryReq`：

| 字段 | 类型 | 必填 | 校验规则 | 说明 |
|---|---|---|---|---|
| `userId` | String | 否 | 最长 32 字符，仅允许字母和数字 | 目标用户 ID；为空时使用当前 token 用户 |
| `productId` | Integer | 否 | 正整数 | 归属产业 ID |
| `projectId` | Integer | 否 | 正整数 | 归属项目 ID |
| `repoId` | Integer | 否 | 正整数 | 归属仓库 ID |
| `userRoles` | Array<String> | 否 | 最多 20 项，每项非空且最长 64 字符 | 角色列表；为空时查询全部角色 |
| `pageNum` | Integer | 否 | 最小 1，默认 `1` | 页码 |
| `pageSize` | Integer | 否 | `10～100`，默认 `20` | 每页条数 |

请求示例：

```json
{
  "userId": "user01",
  "projectId": 100,
  "userRoles": ["admin"],
  "pageNum": 1,
  "pageSize": 20
}
```

仅查询当前登录用户：

```json
{
  "projectId": 100,
  "pageNum": 1,
  "pageSize": 20
}
```

### 3.2 查询逻辑

- 服务端先校验当前请求的产品质量策划读权限，再调用 openlibing-framework 的 `POST /internal-server/get-user-role`。
- 请求参数原样透传 `productId`、`projectId`、`repoId`、`userRoles` 及分页参数。
- `userId` 为空时使用 token 中的当前用户 ID。
- framework 返回的 `data` 与 `total` 转换为统一 `PageResult`。
- framework 返回无数据时，`records` 为空数组、`total` 为 `0`。

### 3.3 成功响应

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": {
    "records": [
      {
        "id": 10,
        "userId": "user01",
        "userName": "张三",
        "userEmail": "zhangsan@example.com",
        "role": "admin",
        "productId": 1,
        "projectId": 100,
        "repoId": null,
        "permGroupId": 0,
        "createTime": "2026-11-09 10:00:00",
        "updateTime": "2026-11-09 10:00:00",
        "syncFlag": "4"
      }
    ],
    "total": 1,
    "pageSize": 20,
    "page": 1
  }
}
```

### 3.4 错误响应

| `code` | `messageCn` | 触发场景 |
|---|---|---|
| `40001` | `请求参数异常` | `userId` 格式非法、分页越界、角色数量或长度超限等参数校验失败 |
| `403` | `没有权限` | token Cookie 缺失、无效或未包含有效用户 ID |
| `50001` | `查询异常` | framework 返回非成功响应 |
| `500` | `系统异常` | framework 不可用或被其他未捕获异常中断 |

错误响应示例：

```json
{
  "code": 403,
  "messageCn": "没有权限",
  "messageEn": "no permission",
  "data": null
}
```

## 4. 前端类型参考

```typescript
interface Result<T> {
  code: number;
  messageCn: string;
  messageEn: string;
  data: T | null;
}

interface PageResult<T> {
  records: T[];
  total: number;
  pageSize: number;
  page: number;
}

interface UserRoleResp {
  id: number;
  userId: string;
  userName: string | null;
  userEmail: string | null;
  role: string | null;
  productId: number | null;
  projectId: number | null;
  repoId: number | null;
  permGroupId: number | null;
  createTime: string | null;
  updateTime: string | null;
  syncFlag: string | null;
}

interface UserRoleQueryReq {
  userId?: string | null;
  productId?: number | null;
  projectId?: number | null;
  repoId?: number | null;
  userRoles?: string[] | null;
  pageNum?: number;
  pageSize?: number;
}
```
