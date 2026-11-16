# 产品质量目录接口文档（前端联调）

> 适用范围：仅包含 `ProductQualityCatalogController` 的 3 个接口。
>
> 本文以当前代码为最终依据，结合 `V20261104__product_quality_planning.sql` 补充字段含义。示例中的 ID、目录名称和数量仅用于说明数据结构。

## 1. 接口清单

统一基础路径：`/projects/product-quality/catalogs`

| 功能               | 请求方式 | 相对路径     | 成功时 `data` 类型          |
| ------------------ | -------- | ------------ | --------------------------- |
| 查询左侧根目录列表 | GET      | `/basic`     | `CatalogResp[]`             |
| 查询右侧目录树     | GET      | `/milestone` | `CatalogResp[]`             |
| 初始化里程碑目录   | POST     | `/init`      | `Integer`，实际新增目录数量 |

本地服务端口为 `8098`，`context-path` 为 `/`。其他环境的域名、端口及网关前缀以部署配置为准。

## 2. 通用约定

### 2.1 身份认证

三个接口均要求请求携带有效的 `token` Cookie，服务端从 JWT 中读取用户身份。

- 不接收通过 Query 参数传递的用户身份。
- token 缺失、无效或无法解析出用户 ID 时，返回业务状态码 `403`。
- 跨域请求由前端按现有工程认证方式携带 Cookie。

### 2.2 公共 Query 参数

三个接口均必须传入以下参数，均无请求体：

| 参数          | 位置  | 类型 | 必填 | 说明                                                                        |
| ------------- | ----- | ---- | ---- | --------------------------------------------------------------------------- |
| `milestoneId` | Query | Long | 是   | 里程碑 ID，对应 `pq_milestone.id`；前端应传整数并在发起请求前校验非空和格式 |

请求示例：

```http
GET /projects/product-quality/catalogs/basic?milestoneId=7
```

### 2.3 统一响应结构

所有业务响应使用产品质量模块专用 `Result<T>`，与通用 `Result` 字段结构一致：

| 字段        | 类型    | 说明                            |
| ----------- | ------- | ------------------------------- |
| `code`      | Integer | 业务状态码，成功固定为 `200`    |
| `messageCn` | String  | 中文消息，成功为 `成功`         |
| `messageEn` | String  | 英文消息，成功为 `success`      |
| `data`      | T/null  | 业务数据；异常响应通常为 `null` |

前端应根据响应体中的 `code` 判断业务是否成功，不要只依赖 HTTP 状态码。

### 2.4 目录对象 `CatalogResp`

| 字段            | 类型            | 是否可能为 null | 说明                                                           |
| --------------- | --------------- | --------------- | -------------------------------------------------------------- |
| `id`            | Long            | 否              | 里程碑目录记录主键，对应 `pq_milestone_catalog.id`             |
| `milestoneId`   | Long            | 否              | 当前节点所属里程碑 ID                                          |
| `catalogId`     | Long            | 否              | 目录 ID；初始化时复制自基础目录 `pq_basic_catalog.id`          |
| `parentId`      | Long/null       | 是              | 父目录 ID，指向父节点的 `catalogId`，不是父节点的记录主键 `id` |
| `catalogEnName` | String          | 否              | 目录英文名称，数据库最大长度 64                                |
| `catalogCnName` | String          | 否              | 目录中文名称，数据库最大长度 255                               |
| `catalogLevel`  | Integer         | 否              | 目录层级：`0` 为左侧根目录；右侧目录为 `1`～`3`                |
| `sortNo`        | Integer         | 否              | 同级排序号，由基础目录复制                                     |
| `optionalFlag`  | Integer         | 否              | 是否可选目录：`0` 否，`1` 是                                   |
| `createBy`      | String          | 是              | 创建人用户 ID                                                  |
| `createTime`    | String          | 是              | 创建时间，格式 `yyyy-MM-dd HH:mm:ss`                           |
| `updateBy`      | String          | 是              | 最后修改人用户 ID                                              |
| `updateTime`    | String          | 是              | 最后修改时间，格式 `yyyy-MM-dd HH:mm:ss`                       |
| `children`      | `CatalogResp[]` | 否              | 子目录数组；无子目录时为 `[]`，不会返回 `null`                 |

前端组树或处理节点关系时，应使用 `catalogId` 与 `parentId`，不要使用 `id` 与 `parentId` 配对。

当前 SQL 查询按记录主键 `id ASC` 返回，`sortNo` 仅作为排序字段随节点返回；前端如要求按同级排序号展示，应在同级节点内按 `sortNo` 排序。

### 2.5 通用错误响应

业务失败统一返回 `code = 40001`，`messageCn` 为具体场景提示、`messageEn` 为 `params invalid`；参数校验失败时具体原因同时写入 `data`。前端可直接展示 `messageCn`：

| `code`  | `messageCn`                              | 触发场景                                                   |
| ------- | ---------------------------------------- | ---------------------------------------------------------- |
| `40001` | `里程碑不存在或已被删除，无法初始化目录` | 初始化目录时里程碑不存在                                   |
| `40001` | 具体校验提示                             | 请求参数未通过校验，`messageCn` 与 `data` 均为具体校验原因 |
| `403`   | `没有权限`                               | token Cookie 缺失、无效，或用户无对应读写权限              |
| `500`   | `系统异常`                               | 未被其他处理器捕获的系统异常                               |

`milestoneId` 缺失或格式非法时不会进入目录业务逻辑；右侧目录树接口新增的 `catalogId` 同样必填。前端必须将各接口的必填参数作为整数处理，不应依赖错误响应补救。

错误响应示例：

```json
{
  "code": 403,
  "messageCn": "没有权限",
  "messageEn": "no permission",
  "data": null
}
```

## 3. 查询左侧根目录列表

### 3.1 请求

```http
GET /projects/product-quality/catalogs/basic?milestoneId=7
```

- 请求参数：仅公共 Query 参数 `milestoneId`。
- 无请求体。
- 查询 `pq_milestone_catalog` 中指定里程碑的 `catalog_level = 0` 记录。
- 用于页面左侧根目录展示，返回平铺数组，不组装子树，节点的 `children` 固定为空数组。
- 未初始化目录或指定里程碑没有根目录时，成功返回空数组 `data: []`。

### 3.2 成功响应

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": [
    {
      "id": 1001,
      "milestoneId": 7,
      "catalogId": 1,
      "parentId": null,
      "catalogEnName": "root-catalog",
      "catalogCnName": "根目录",
      "catalogLevel": 0,
      "sortNo": 10,
      "optionalFlag": 0,
      "children": []
    }
  ]
}
```

空数据响应：

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": []
}
```

## 4. 查询右侧目录树

### 4.1 请求

```http
GET /projects/product-quality/catalogs/milestone?milestoneId=7&catalogId=1
```

| 参数          | 位置  | 类型 | 必填 | 说明                                                                     |
| ------------- | ----- | ---- | ---- | ------------------------------------------------------------------------ |
| `milestoneId` | Query | Long | 是   | 公共参数，里程碑 ID                                                      |
| `catalogId`   | Query | Long | 是   | 左侧根目录的目录 ID，取左侧接口返回节点的 `catalogId`，不是记录主键 `id` |

- 无请求体。
- 查询指定里程碑的 `catalog_level > 0` 记录，即 1～3 级目录，在服务端组装为树后，仅返回属于 `catalogId` 指定左侧根目录的右侧子树。
- 不包含 `catalog_level = 0` 的左侧根目录。
- 返回值为所选左侧根目录下的顶层节点数组，可能包含多个顶层节点，前端不应假设只有一个根节点。
- 右侧顶层节点的 `parentId` 等于请求参数 `catalogId`，其指向的 0 级左侧根目录不包含在当前 `data` 中。
- 未初始化目录、指定里程碑没有非根目录，或所选左侧根目录下没有右侧目录时，成功返回 `data: []`。

### 4.2 成功响应

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": [
    {
      "id": 1002,
      "milestoneId": 7,
      "catalogId": 2,
      "parentId": 1,
      "catalogEnName": "first-level-catalog",
      "catalogCnName": "一级目录",
      "catalogLevel": 1,
      "sortNo": 10,
      "optionalFlag": 0,
      "children": [
        {
          "id": 1003,
          "milestoneId": 7,
          "catalogId": 3,
          "parentId": 2,
          "catalogEnName": "second-level-catalog",
          "catalogCnName": "二级目录",
          "catalogLevel": 2,
          "sortNo": 10,
          "optionalFlag": 1,
          "children": []
        }
      ]
    }
  ]
}
```

上述示例中，请求参数 `catalogId = 1` 对应左侧根目录的 `catalogId = 1`，因此顶层节点的 `parentId = 1`；子节点的 `parentId = 2` 对应其父节点的 `catalogId = 2`。其他左侧根目录下的目录不会出现在该响应中。

## 5. 初始化里程碑目录

### 5.1 请求

```http
POST /projects/product-quality/catalogs/init?milestoneId=7
```

- 请求参数：仅公共 Query 参数 `milestoneId`。
- 无请求体，不需要构造 JSON Body。
- 服务端校验里程碑存在后，将 `pq_basic_catalog` 的全部基础目录复制到 `pq_milestone_catalog`。
- 复制内容包括目录 ID、父目录 ID、中英文名称、层级、排序号和可选标记；创建人与更新人由服务端根据 token 用户生成，创建时间与更新时间由服务端按 `yyyy-MM-dd HH:mm:ss` 生成。
- 初始化在事务中执行。

### 5.2 幂等与返回值

`data` 为本次实际插入的目录记录数量，不是里程碑 ID，也不是目录对象。

| 场景                         | 结果                               |
| ---------------------------- | ---------------------------------- |
| 首次初始化且基础目录非空     | 返回实际新增目录数量，例如 `42`    |
| 指定里程碑已存在任意目录记录 | 跳过初始化，返回 `0`               |
| 基础目录表为空               | 不插入数据，返回 `0`               |
| 里程碑不存在                 | 返回业务失败提示（`code = 40001`） |

因此，`data = 0` 不一定表示失败，前端应结合 `code = 200` 判断请求成功，并按需重新查询左右侧目录。

### 5.3 成功响应

首次初始化新增 42 条目录记录：

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": 42
}
```

重复初始化或基础目录为空：

```json
{
  "code": 200,
  "messageCn": "成功",
  "messageEn": "success",
  "data": 0
}
```

里程碑不存在：

```json
{
  "code": 40001,
  "messageCn": "里程碑不存在或已被删除，无法初始化目录",
  "messageEn": "params invalid",
  "data": null
}
```

## 6. 前端类型参考

```typescript
interface Result<T> {
  code: number;
  messageCn: string;
  messageEn: string;
  data: T | null;
}

interface CatalogResp {
  id: number;
  milestoneId: number;
  catalogId: number;
  parentId: number | null;
  catalogEnName: string;
  catalogCnName: string;
  catalogLevel: 0 | 1 | 2 | 3;
  sortNo: number;
  optionalFlag: 0 | 1;
  createBy: string | null;
  createTime: string | null;
  updateBy: string | null;
  updateTime: string | null;
  children: CatalogResp[];
}
```

若前端使用 JavaScript 的 `number` 承载 Long ID，应遵守项目现有的长整型处理约定，避免超出安全整数范围后精度丢失。
