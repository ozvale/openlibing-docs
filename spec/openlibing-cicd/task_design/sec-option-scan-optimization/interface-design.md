# 安全编译选项扫描能力优化 接口设计文档

> 面向前端开发的接口契约文档。与《requirement-design.md》配套，聚焦安全编译选项扫描能力优化涉及的 HTTP 接口：字段定义、筛选能力、排序能力、分页约定与鉴权说明。前端联调以此文档为准。

## 1. 通用约定

### 1.1 基础信息

| 项           | 说明                                                                                                                                                                                                                                                                                         |
| ------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 服务         | openlibing-cicd（后端仓库 `openlibing-cicd-fork`）                                                                                                                                                                                                                                           |
| 路由前缀     | 所有接口统一挂载在 `BuildArtifactController`，`@RequestMapping("/build-artifact")`                                                                                                                                                                                                           |
| 网关前缀     | 经网关访问时完整路径形如 `https://<domain>/openlibing-cicd/build-artifact/sec-option/...`，前端请求相对路径用 `/build-artifact/sec-option/...` 即可，网关遮罩由部署层处理                                                                                                                    |
| Content-Type | 均为 `application/json`，POST + body                                                                                                                                                                                                                                                         |
| 鉴权         | 登录态通过 Cookie `token`（JWT）传递；gateway 解析 JWT 后把登录 `userId`/`userName` 以 query param（`userId`/`userName`）注入到服务端请求，controller 通过 `@RequestParam` 接收（服务侧不直接解析 Cookie）；服务侧仅做项目级横向鉴权（项目成员校验），纵向角色鉴权由 gateway 完成（见 §1.4） |

### 1.2 统一响应结构

所有接口返回 `DataResult<T>`，JSON 形如：

```json
{
  "code": "000000",
  "msg": "success",
  "data": { ... },
  "exMessage": ""
}
```

- `code == 0`（或平台约定的成功码）表示成功，`data` 为业务数据；非成功码时 `msg`/`exMessage` 携带错误说明。
- 备案写接口鉴权失败时，HTTP 状态码为 `403`，`code` 为权限相关错误码。

### 1.3 分页约定

| 字段       | 类型    | 说明                    |
| ---------- | ------- | ----------------------- |
| `pageNum`  | Integer | 页码，从 1 开始，默认 1 |
| `pageSize` | Integer | 每页条数，默认 20       |
| `total`    | Long    | 命中总记录数（出参）    |
| `records`  | Array   | 当前页记录（出参）      |

页面筛选项除 `projectId` 外均可不传，不传即不过滤；字符串类筛选默认为**模糊匹配**（`LIKE %value%`），枚举类筛选为**精确匹配**，时间范围为**闭区间**。

### 1.4 角色鉴权（备案写操作）

| 项              | 说明                                                                                                                                                                                                                               |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 角色码          | `security_compilation_options_filing_approver`                                                                                                                                                                                     |
| 作用写接口      | `/sec-option/filing/save`、`/sec-option/filing/cancel`                                                                                                                                                                             |
| 鉴权方式        | 纵向角色鉴权由网关完成（校验当前登录 `userId` 持有该角色或为 `admin`，不足则 403）；服务侧仅做项目级横向鉴权——校验当前登录 `userId` 为 `projectId` 对应项目的成员，否则返回 403                                                    |
| 业务例外        | 只读接口（`overview`、`file-detail`、`record-list`、`filing/list`）不要求专用角色，仅需项目成员校验；`save` 与 `cancel` 均为备案写操作，都需要审批人角色（权限一致），`cancel` 另校验备案记录 `projectId` 与请求一致，防止伪造越权 |
| 备案人/备案时间 | 备案人 ID/姓名由后端取 gateway 注入的 `userId`/`userName` 写入 `sec_option_filing` 表，前端无需也不应传备案人字段；备案时间后端取当前时间写入                                                                                      |

---

## 2. 接口总览

| 接口         | 方法 + 路径                                          | 用途                                                        | 变更类型 |
| ------------ | ---------------------------------------------------- | ----------------------------------------------------------- | -------- |
| 概览列表     | `POST /build-artifact/sec-option/overview`           | 一级概览页（产物包维度分页列表）                            | 增强     |
| 文件详情     | `POST /build-artifact/sec-option/file-detail`        | 二/三级页的包内文件逐项检测结果                             | 增强     |
| 保存备案     | `POST /build-artifact/sec-option/filing/save`        | 创建/更新例外备案（支持批量，items 一次携带多条）           | 新增     |
| 取消备案     | `POST /build-artifact/sec-option/filing/cancel`      | 取消（删除）例外备案（查询时实时关联，无回填）              | 新增     |
| 待备案项列表 | `POST /build-artifact/sec-option/filing/list`        | 某产物包扫描记录下文件×扫描项扁平行列表（SQL 分页）         | 新增     |
| 备案人名单   | `POST /build-artifact/sec-option/filing/filer-list`  | 备案人精确筛选下拉名单（含每人备案条数，按产物包/项目维度） | 新增     |
| 备案记录列表 | `POST /build-artifact/sec-option/filing/record-list` | 独立备案记录页（跨包）                                      | 新增     |
| 扫描结果上报 | `POST /build-artifact/sec-option/report`             | 插件调用，前端不涉及                                        | 不变     |

---

## 3. 概览列表接口

`POST /build-artifact/sec-option/overview`

一级概览页：每行一个产物包扫描记录，只展示基础信息（代码仓、流水线、产物包、扫描时间、状态、扫描项数、总文件数），**不展示每个扫描项覆盖率数字**。

### 3.1 请求体 `SecOptionOverviewQueryDTO`

| 字段           | 类型             | 必填 | 筛选/排序能力    | 说明                                                                                                    |
| -------------- | ---------------- | ---- | ---------------- | ------------------------------------------------------------------------------------------------------- |
| `projectId`    | String           | 是   | 精确（项目隔离） | 项目 ID，只查询该项目下代码仓的产物                                                                     |
| `repoUrl`      | String           | 否   | 模糊             | 代码仓链接（如 `gitcode.com/owner/repo`），后端对完整 gitUrl 做 LIKE                                    |
| `pipelineName` | String           | 否   | 模糊             | 流水线名称（ATOMGIT_WORKFLOW 环境变量值）                                                               |
| `runNumber`    | String           | 否   | 模糊             | 流水线运行编号（对应插件上报的 runNumber，支持输入任意数字片段）                                        |
| `packageName`  | String           | 否   | 模糊             | 构建产物包名（插件取 `artifact-path` 对应的文件名 basename，如 `DrivingSDK_v2.7.1_3.9_aarch64.tar.gz`） |
| `startTime`    | String           | 否   | 区间下界         | 检测完成时间起始，ISO 8601 或 `yyyy-MM-dd HH:mm:ss`                                                     |
| `endTime`      | String           | 否   | 区间上界         | 检测完成时间截止                                                                                        |
| `statuses`     | Array\<Integer\> | 否   | 多选             | 扫描状态多选筛选，0-失败，1-成功，2-部分成功，如 `[0,1]`；不传时不按状态过滤（返回所有状态）            |
| `sort`         | String           | 否   | 排序方向         | `asc`/`desc`，默认 `asc`                                                                                |
| `sortByField`  | String           | 否   | 排序字段         | `detectionCompletedAt` 或 `指标名.子字段`（如 `bindNow.rate`、`nx.totalFiles`、`pie.yesCount`）         |
| `pageNum`      | Integer          | 否   | 分页             | 默认 1                                                                                                  |
| `pageSize`     | Integer          | 否   | 分页             | 默认 20                                                                                                 |

> 说明：本接口分页与排序已下推数据库（SQL LIMIT/OFFSET + COUNT），不再内存分页。`sortByField` 为数值指标（`xxx.rate`/`xxx.totalFiles`/`xxx.yesCount`）时，若当前记录未扫描该指标，排序兜底按 `detectionCompletedAt` 处理；前端默认不传 `sortByField`，后端按 `detectionCompletedAt` 倒序。

### 3.2 响应体 `SecOptionOverviewVO`

```json
{
  "total": 100,
  "pageNum": 1,
  "pageSize": 20,
  "records": [
    {
      "id": "1234567890",
      "repoUrl": "gitcode.com/DrivingSDK/core",
      "pipelineName": "nightly-build",
      "runNumber": "512",
      "pipelineLink": "https://gitcode.com/DrivingSDK/core/actions/runs/xxx",
      "packageName": "DrivingSDK_v2.1.0_3.8_aarch64.tar.gz",
      "status": 0,
      "optionCount": 8,
      "scanOptions": "bindNow,fortify,fstackCheck,...",
      "totalScannedFiles": 80,
      "filingCoverage": "64.29%",
      "downloadUrl": "https://...",
      "downloadAccessible": true,
      "detectionCompletedAt": "2026-09-02 15:20:00",
      "overviewData": [
        {
          "key": "bindNow",
          "scanned": true,
          "totalFiles": 80,
          "applicableFiles": 79,
          "yesCount": 68,
          "rate": "86.08%",
          "confirmedFiles": 5,
          "confirmationCoverage": "87.34%"
        },
        {
          "key": "nx",
          "scanned": false,
          "totalFiles": 0,
          "applicableFiles": 0,
          "yesCount": 0,
          "rate": "N/A",
          "confirmedFiles": 0,
          "confirmationCoverage": "N/A"
        },
        "..."
      ]
    }
  ]
}
```

`SecOptionRecordItem` 字段：

| 字段                   | 类型                    | 说明                                                                      |
| ---------------------- | ----------------------- | ------------------------------------------------------------------------- |
| `id`                   | String                  | 记录 ID（字符串传递，避免 64 位 Long 失真后按 id 查询失败）               |
| `repoUrl`              | String                  | 代码仓链接（`gitcode.com/owner/repo`）                                    |
| `pipelineName`         | String                  | 流水线名称                                                                |
| `runNumber`            | String                  | 流水线运行编号                                                            |
| `pipelineLink`         | String                  | 流水线链接                                                                |
| `packageName`          | String                  | 产物包名                                                                  |
| `status`               | Integer                 | 扫描状态：0-失败，1-成功，2-部分成功（见下方状态说明）                    |
| `optionCount`          | Integer                 | 扫描项数（`scanOptions` 逗号分隔项的个数）                                |
| `scanOptions`          | String                  | 实际扫描项 key，逗号分隔                                                  |
| `totalScannedFiles`    | Integer                 | 实际扫描 ELF 文件总数（新增）                                             |
| `filingCoverage`       | String                  | 确认结果覆盖率（备案后满足数/实际参与数，新增，格式如 `64.29%` 或 `N/A`） |
| `downloadUrl`          | String                  | 产物下载链接                                                              |
| `downloadAccessible`   | Boolean                 | 下载是否可访问                                                            |
| `detectionCompletedAt` | String                  | 检测完成时间（`yyyy-MM-dd HH:mm:ss`）                                     |
| `overviewData`         | Array\<OverviewOption\> | 逐扫描项数据数组，按固定 14 项顺序排列，见下                              |

#### 扫描状态说明

`status` 由扫描插件（security-compilation-options-action）依据扫描结果上报，含义如下：

| 值  | 含义     | 触发场景                                                                                                                                                             |
| --- | -------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0   | 失败     | **全部文件扫描失败**（每个 ELF 文件解析均抛异常，`successCount=0` 且 `failedCount>0`），或脚本级异常（源目录不存在、扫描脚本报错），仍上传附带 `errorMessage` 的报告 |
| 1   | 成功     | 全部文件扫描成功（`failedCount=0`），或扫描目录下无任何文件（空结果也视为成功）                                                                                      |
| 2   | 部分成功 | 存在成功文件**且**存在失败文件（`failedCount>0` 且 `totalScannedFiles>0`），部分 ELF 文件解析失败但整体仍产出结果                                                    |

> 失败文件判定：文件为 ELF 但解析/分析抛异常（如 `ELF parse error`、`Open file failed`）。非 ELF 文件、包解压失败的文件按跳过处理，不计为失败、不拉低状态。
>
> 插件将失败文件相对路径写入 `summary.failedFiles`、数量写入 `summary.failedCount`，Node 端据此计算最终 `status`。

`overviewData` 数组元素 `OverviewOption`（固定 14 项顺序，前端据此渲染避免对象键序不一致）：

- **已扫描项**：`{ "key": "bindNow", "scanned": true, "totalFiles": int, "applicableFiles": int, "yesCount": int, "rate": "86.08%", "confirmedFiles": int, "confirmationCoverage": "87.34%" }`
- **未扫描项**：`{ "key": "fstackCheck", "scanned": false, "totalFiles": 0, "applicableFiles": 0, "yesCount": 0, "rate": "N/A", "confirmedFiles": 0, "confirmationCoverage": "N/A" }`，前端应隐藏该扫描项。

`OverviewOption` 字段说明：

| 字段                   | 类型    | 说明                                                                    |
| ---------------------- | ------- | ----------------------------------------------------------------------- |
| `key`                  | String  | 扫描项 key（如 `bindNow`、`nx`），前端据此映射展示                      |
| `scanned`              | Boolean | 是否扫描                                                                |
| `totalFiles`           | Integer | 总文件数                                                                |
| `applicableFiles`      | Integer | 实际参与数（排除 N/A 的文件数）                                         |
| `yesCount`             | Integer | 满足数（检测结果为 YES 的文件数）                                       |
| `rate`                 | String  | 检测结果覆盖率（字符串百分比，如 `"86.08%"`；已扫描但不适用为 `"N/A"`） |
| `confirmedFiles`       | Integer | 已确认文件数（该扫描项有备案记录的文件数）                              |
| `confirmationCoverage` | String  | 确认结果覆盖率（备案后满足数/实际参与数，如 `"87.34%"` 或 `"N/A"`）     |

---

## 4. 文件详情接口

`POST /build-artifact/sec-option/file-detail`

二/三级页：按 `projectId + recordId` 定位一条扫描记录，返回包内所有文件的逐项检测结果（分页）。以 `recordId`（雪花 ID）作为定位键，而非 `repoUrl + runNumber + packageName`：产物包名以 basename 记录后，同一构建可能产出多个目录下的同名包，三元组无法唯一区分。

### 4.1 请求体 `SecOptionFileDetailQueryDTO`

| 字段            | 类型                         | 必填 | 筛选能力         | 说明                                                 |
| --------------- | ---------------------------- | ---- | ---------------- | ---------------------------------------------------- |
| `projectId`     | String                       | 是   | 精确（项目隔离） | 项目 ID，仅允许查询本项目下的扫描记录                |
| `recordId`      | String                       | 是   | 精确             | 扫描记录 ID（雪花 ID，从 overview 行的 `id` 取）     |
| `fileName`      | String                       | 否   | 模糊             | 文件名模糊搜索（对 `file_name` 做 LIKE `%value%`）   |
| `filePath`      | String                       | 否   | 模糊             | 文件路径模糊搜索（对 `file_path` 做 LIKE `%value%`） |
| `optionFilters` | Array\<SecOptionFileFilter\> | 否   | 每扫描项独立多选 | 扫描项+扫描值筛选，结构见下                          |
| `pageNum`       | Integer                      | 否   | 分页             | 默认 1                                               |
| `pageSize`      | Integer                      | 否   | 分页             | 默认 20                                              |

> **项目隔离说明**：即使以 `recordId` 定位，后端仍校验该记录所属代码仓（`git_url`）是否属于 `projectId` 对应项目（git 仓名大小写不敏感比较），不属于则返回"未找到对应的扫描记录"，防止越权访问其他项目。

> `SecOptionFileFilter`：`{ "optionKey": string, "scanValues": string[] }`，一个对象记录**一个扫描项**及其可匹配的扫描值集合；多个扫描项之间为**复合（AND）关系**（该行需同时满足所有传的扫描项），同一扫描项的多个扫描值之间为 **IN** 关系；特别地，若某文件未扫描某扫描项，`JSON_EXTRACT` 返回 NULL、`IN` 不命中即该行落选；任一元素的扫描值集合为空则忽略该条件，`optionFilters` 整体不传表示不按扫描项过滤。
>
> 文件详情页默认按 `filePath` 升序返回。**`fileName`/`filePath` 与 `optionFilters` 均在服务端 SQL 完成、与分页一起下推**：路径类对 `file_name`/`file_path` 做 LIKE `%value%`；`optionFilters` 内每个扫描项作为独立的 AND 谓词对 `raw_options` JSON 做 IN 筛选（值域 `YES`/`NO`/`N/A`，按原始扫描值过滤，与备案值无关），仍为 SQL 侧 LIMIT/OFFSET + COUNT 分页，非内存分页。分页命中的文件再由 Service 层加载该产物所有备案（按 `projectId + gitUrl + packageName` 一次性查 `sec_option_filing`）后在内存组装 `options`（生效值）与 `rawOptions`（已备案项的原值），故分页 100 行内 JOIN 等价为内存 map 命中，性能无显著影响。

### 4.2 响应体 `SecOptionFileDetailVO`

```json
{
  "repoUrl": "gitcode.com/DrivingSDK/core",
  "pipelineName": "nightly-build",
  "runNumber": "512",
  "pipelineLink": "https://gitcode.com/DriverSDK/core/actions/runs/xxx",
  "packageName": "DrivingSDK_v2.1.0_3.8_aarch64.tar.gz",
  "total": 80,
  "pageNum": 1,
  "pageSize": 20,
  "fileDetails": [
    {
      "filePath": "mx_driving/lib/libperception.so",
      "fileName": "libperception.so",
      "options": {
        "bindNow": "YES",
        "nx": "NO",
        "fortify": "YES",
        "...": "..."
      },
      "rawOptions": { "fortify": "NO" }
    }
  ]
}
```

`FileSecOptionItem` 字段：

| 字段         | 类型   | 说明                                                                                                  |
| ------------ | ------ | ----------------------------------------------------------------------------------------------------- |
| `filePath`   | String | 包内相对路径（插件已相对化，`/` 分隔）                                                                |
| `fileName`   | String | 文件名                                                                                                |
| `options`    | Map    | 逐扫描项**生效值**（备案后值），key 固定 14 项；已扫描为 `YES`/`NO`/`N/A`，未扫描项值为 `"UNSCANNED"` |
| `rawOptions` | Map    | 已备案项 → 原始扫描值（新增，如 `{ "fortify": "NO" }`），用于展示"备案值 + 划线原值"；无备案为空 `{}` |

> 前端判断展示：`options[key] == "UNSCANNED"` 则隐藏；`rawOptions` 存在该 key 时，以 `options[key]` 为备案生效值、`rawOptions[key]` 为划线原值。

---

## 5. 保存备案接口

`POST /build-artifact/sec-option/filing/save`

创建/更新例外备案（upsert，**支持批量**）。**需「安全编译选项例外备案审批人」角色（角色码 `security_compilation_options_filing_approver`，纵向鉴权由网关完成）**。

前端执行批量备案时，一次请求通过 `items` 携带多个（文件×扫描项）备案项，由后端逐项 upsert（按自然键 `projectId + gitUrl + packageName + filePath + optionKey`），无需循环多次调用。**备案写入 `sec_option_filing` 表后不再回填 `sec_option_scan_file_detail.filed_options`**，所有查询接口（file-detail / filing-list / overview）均在查询时实时 `LEFT JOIN sec_option_filing` 按自然键关联出当前最新备案状态——因此对同一产物同一文件同一扫描项备案后，该产物的**历史和未来所有扫描记录**都能看到该备案结果。整个批量写入在同一事务内（失败整体回滚）。

### 5.1 请求体 `SecOptionFilingDTO`

| 字段          | 类型                              | 必填 | 说明                                                         |
| ------------- | --------------------------------- | ---- | ------------------------------------------------------------ |
| `projectId`   | String                            | 是   | 项目 ID（一次批量备案的公共维度）                            |
| `gitUrl`      | String                            | 是   | 代码仓完整链接（如 `https://gitcode.com/owner/repo.git`）    |
| `packageName` | String                            | 是   | 产物包名                                                     |
| `filingValue` | String                            | 是   | 备案值，仅 `YES`（批量统一备案为 YES，确认该安全选项已启用） |
| `reason`      | String                            | 否   | 备案理由（批量统一理由）                                     |
| `items`       | Array\<`SecOptionFilingItemDTO`\> | 是   | 待备案项列表，至少一项（空会拒绝并返回失败）                 |

### 5.1.1 备案项 `SecOptionFilingItemDTO`

| 字段        | 类型   | 必填 | 说明                                                  |
| ----------- | ------ | ---- | ----------------------------------------------------- |
| `filePath`  | String | 是   | 文件相对路径（与 file-detail 返回的 `filePath` 一致） |
| `optionKey` | String | 是   | 扫描项 key（如 `fortify`）                            |

每个备案项的唯一键：`projectId + gitUrl + packageName + filePath + optionKey`。

请求示例（批量备案 2 条）：

```json
{
  "projectId": "p1",
  "gitUrl": "https://gitcode.com/owner/repo.git",
  "packageName": "foo.tar.gz",
  "filingValue": "YES",
  "reason": "统一理由",
  "items": [
    { "filePath": "bin/a", "optionKey": "bindNow" },
    { "filePath": "bin/b", "optionKey": "fortify" }
  ]
}
```

### 5.2 响应体

```json
{ "code": 0, "msg": "success", "data": ["1234567890", "1234567891"] }
```

`data` 为备案记录 ID 列表（Array\<String\>），顺序与请求 `items` 一一对应；前端可用其调用取消备案/二次保存，字符串传递避免 64 位 Long 失真。

---

## 6. 取消备案接口

`POST /build-artifact/sec-option/filing/cancel`

取消（删除）例外备案（按 `id` 批量删除 `sec_option_filing` 表记录）。**与 `save` 一样需审批人角色（角色码 `security_compilation_options_filing_approver`，纵向鉴权由网关完成）**；服务侧校验当前用户为 `projectId` 对应项目成员，且备案记录 `projectId` 与请求一致。**取消后无需重算**：查询接口实时 `LEFT JOIN sec_option_filing`，删除后所有历史和未来扫描记录中该备案自然消失。

### 6.1 请求体 `SecOptionFilingCancelDTO`（独立 DTO，与 save 不共用）

| 字段        | 类型   | 必填 | 说明                                                  |
| ----------- | ------ | ---- | ----------------------------------------------------- |
| `id`        | String | 是   | 备案记录 ID（字符串传递，避免 64 位 Long 失真）       |
| `projectId` | String | 是   | 项目 ID（用于项目隔离校验，须与备案记录所属项目一致） |

### 6.2 响应体

```json
{ "code": 0, "msg": "success", "data": null }
```

---

## 7. 待备案项列表接口

`POST /build-artifact/sec-option/filing/list`

三级「待备案项列表」页：把某条扫描记录下的**文件×扫描项**降维为扁平行列表，每行 = 一个"文件×扫描项"组合（已扫描且适用，扫描值 YES/NO），服务端 SQL 分页下推（**非内存分页**）。**每行自动区分备案状态**：未备案行 `id` 为空（可勾选批量备案），已备案行带备案记录 `id`（可取消备案）。数据来源为 `sec_option_scan_file_detail` 与 14 个扫描项 key 笛卡尔展开后 **`LEFT JOIN sec_option_filing`** 按自然键（`git_url + package_name + file_path + option_key + project_id`）关联当前备案，因此**该产物包历史和未来所有扫描记录都会展示同一份最新备案**（不再依赖 `filed_options` 快照回填）。**只读，需项目成员校验 + 记录归属校验**。

### 7.1 请求体 `SecOptionFilingRowQueryDTO`

| 字段              | 类型            | 必填 | 筛选能力         | 说明                                                                                                                         |
| ----------------- | --------------- | ---- | ---------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| `projectId`       | String          | 是   | 精确（项目隔离） | 项目 ID                                                                                                                      |
| `recordId`        | String          | 是   | 精确             | 扫描记录 ID（定位该记录下的文件×扫描项行），字符串传递，避免 64 位 Long 失真                                                 |
| `filePath`        | String          | 否   | 模糊             | 文件路径，对 `file_path` 做 LIKE `%value%`                                                                                   |
| `optionKeys`      | Array\<String\> | 否   | **多选**         | 扫描项 key 多选，对 `option_key` 做 IN；空则不按扫描项过滤                                                                   |
| `scanValues`      | Array\<String\> | 否   | **多选**         | 扫描值多选，仅允许 `YES`/`NO`，对 `raw_value` 做 IN；空默认只查 `[NO]`（只看不满足项）                                       |
| `filedStatus`     | String          | 否   | 精确             | 备案状态筛：`FILED` 有备案 / `UNFILED` 未备案 / `ALL` 全部；空默认 `ALL`                                                     |
| `filerName`       | String          | 否   | **精确**         | 备案人账号名精确筛选，对已备案行 `filer_name` 做等值匹配（未备案行为空不匹配）；供由 `/filing/filer-list` 返回的名单下拉使用 |
| `filingStartTime` | String          | 否   | 区间下界         | 备案时间起始（`yyyy-MM-dd HH:mm:ss`，闭区间），对已备案行 `filing_time` 过滤                                                 |
| `filingEndTime`   | String          | 否   | 区间上界         | 备案时间截止（`yyyy-MM-dd HH:mm:ss`，闭区间）                                                                                |
| `pageNum`         | Integer         | 否   | 分页             | 默认 1                                                                                                                       |
| `pageSize`        | Integer         | 否   | 分页             | 默认 20                                                                                                                      |

> 每条扁平行对应一次"文件×扫描项"，跨页/n 条总数为 SQL `COUNT` 下推结果，前端直接以 `total` 展示，跨页勾选可基于 `id` 集合维护。

### 7.2 响应体 `SecOptionFilingRowVO`

`records` 中每行 `SecOptionFilingRow`（未备案行 `id`/`filingValue`/备案人字段为 null）：

```json
{
  "total": 48,
  "pageNum": 1,
  "pageSize": 20,
  "records": [
    {
      "id": null,
      "filePath": "mx_driving/lib/libperception.so",
      "optionKey": "fortify",
      "rawValue": "NO",
      "filingValue": null,
      "filerId": null,
      "filerName": null,
      "filingTime": null,
      "reason": null
    },
    {
      "id": "10000001",
      "filePath": "mx_driving/lib/libperception.so",
      "optionKey": "nx",
      "rawValue": "NO",
      "filingValue": "YES",
      "filerId": "10086",
      "filerName": "zhangsan",
      "filingTime": "2026-09-02 15:20:00",
      "reason": "已核对源码，可豁免"
    }
  ]
}
```

`SecOptionFilingRow` 字段：

| 字段          | 类型   | 说明                                                                     |
| ------------- | ------ | ------------------------------------------------------------------------ |
| `id`          | String | 备案记录 ID（字符串传递；未备案行为 null；已备案行作为取消备案接口入参） |
| `filePath`    | String | 文件相对路径                                                             |
| `optionKey`   | String | 扫描项 key                                                               |
| `rawValue`    | String | 原始扫描值（上报检测值，`YES`/`NO`）                                     |
| `filingValue` | String | 备案值（已备案行为 `YES`/`NO`，未备案行为 null）                         |
| `filerId`     | String | 备案人 ID（未备案行为 null）                                             |
| `filerName`   | String | 备案人账号名（未备案行为 null）                                          |
| `filingTime`  | String | 备案时间（未备案行为 null，`yyyy-MM-dd HH:mm:ss`）                       |
| `reason`      | String | 备案理由（未备案行为 null）                                              |

> 前端展示约定：`id == null` 为可勾选批量备案行；`id != null` 为已备案行，展示 `rawValue → filingValue` 划线原值并提供"取消备案"。

---

## 8. 备案记录列表接口

`POST /build-artifact/sec-option/filing/record-list`

独立「安全编译选项备案记录」页：跨产物包总览所有备案记录（含备案人、备案时间）。**只读，无需专用角色**（但需登录进入项目）。

### 8.1 请求体 `SecOptionFilingRecordQueryDTO`

| 字段              | 类型    | 必填 | 筛选/排序能力    | 说明                                                                                               |
| ----------------- | ------- | ---- | ---------------- | -------------------------------------------------------------------------------------------------- |
| `projectId`       | String  | 是   | 精确（项目隔离） | 项目 ID                                                                                            |
| `repoUrl`         | String  | 否   | 模糊             | 代码仓链接，对 `git_url` 做 LIKE                                                                   |
| `packageName`     | String  | 否   | 模糊             | 产物包名                                                                                           |
| `optionKey`       | String  | 否   | 精确             | 扫描项 key（如 `fortify`）                                                                         |
| `filerName`       | String  | 否   | **精确**         | 备案人账号名精确筛选（对 `filer_name` 做等值匹配）；可配合 `/filing/filer-list` 返回的名单下拉使用 |
| `filingStartTime` | String  | 否   | 区间下界         | 备案时间起始（`yyyy-MM-dd HH:mm:ss`）                                                              |
| `filingEndTime`   | String  | 否   | 区间上界         | 备案时间截止                                                                                       |
| `sortByField`     | String  | 否   | 排序字段         | 白名单：`filingTime`（默认）、`packageName`、`optionKey`、`filerName`                              |
| `sort`            | String  | 否   | 排序方向         | `asc`/`desc`，默认 `desc`                                                                          |
| `pageNum`         | Integer | 否   | 分页             | 默认 1                                                                                             |
| `pageSize`        | Integer | 否   | 分页             | 默认 20                                                                                            |

### 8.2 响应体 `SecOptionFilingRecordVO`

```json
{
  "total": 30,
  "pageNum": 1,
  "pageSize": 20,
  "records": [
    {
      "id": "1000001",
      "repoUrl": "gitcode.com/DrivingSDK/core",
      "packageName": "DrivingSDK_v2.1.0_3.8_aarch64.tar.gz",
      "filePath": "mx_driving/lib/libperception.so",
      "optionKey": "fortify",
      "filingValue": "YES",
      "reason": "已核对源码，可豁免",
      "filerName": "zhangsan",
      "filingTime": "2026-09-02 15:20:00"
    }
  ]
}
```

`SecOptionFilingRecordItem` 字段：

| 字段          | 类型   | 说明                                                        |
| ------------- | ------ | ----------------------------------------------------------- |
| `id`          | String | 备案记录 ID（删除操作使用，字符串传递避免 64 位 Long 失真） |
| `repoUrl`     | String | 代码仓链接（`gitcode.com/owner/repo`）                      |
| `packageName` | String | 产物包名                                                    |
| `filePath`    | String | 文件相对路径                                                |
| `optionKey`   | String | 扫描项 key                                                  |
| `filingValue` | String | 备案值（`YES`/`NO`）                                        |
| `reason`      | String | 备案理由                                                    |
| `filerName`   | String | 备案人账号名                                                |
| `filingTime`  | String | 备案时间（`yyyy-MM-dd HH:mm:ss`）                           |

### 8.3 备案人名单接口

`POST /build-artifact/sec-option/filing/filer-list`

供「待备案项列表」与「备案记录列表」的**备案人账号名精确筛选**下拉使用。返回备案人名单（含每人备案的数据项数量）。**只读，需项目成员校验**。

#### 8.3.1 请求体 `SecOptionFilerQueryDTO`

| 字段          | 类型   | 必填 | 说明                                                                                  |
| ------------- | ------ | ---- | ------------------------------------------------------------------------------------- |
| `projectId`   | String | 是   | 项目 ID（项目隔离）                                                                   |
| `packageName` | String | 否   | 产物包名。**传入则只返回该产物包下的备案人；未传则返回项目（projectId）下全部备案人** |

#### 8.3.2 响应体 `SecOptionFilerVO`

```json
{
  "filers": [
    { "filerId": "10086", "filerName": "zhangsan", "filingCount": 12 },
    { "filerId": "10087", "filerName": "lisi", "filingCount": 3 }
  ]
}
```

`filers` 数组元素 `FilerItem`（按备案数据项数量降序）：

| 字段          | 类型   | 说明                                 |
| ------------- | ------ | ------------------------------------ |
| `filerId`     | String | 备案人 ID                            |
| `filerName`   | String | 备案人账号名                         |
| `filingCount` | Long   | 该备案人在当前范围内的备案数据项数量 |

---

## 9. 扫描项枚举（14 项）

前端筛选下拉、矩阵列、未扫描项隐藏均以此固定 key 集为准：

```
bindNow, nx, pic, pie, relro, rpath, sp, strip,
fortify, fvisibility, ftrapv, stackClash, fstackCheck, aslr
```

备案值 `filingValue` 仅为 `YES` 或 `NO`；文件/扫描项检测值除 `YES`/`NO`/`N/A` 外，未扫描时为 `"UNSCANNED"`（file-detail）或 `{"scanned": false}`（overview）。

---

## 10. 覆盖率口径（前端公式展示用）

- 实际参与数 = 满足数 + 不满足数（`N/A` 不参与分母）。
- 检测结果覆盖率 = 满足数 / 实际参与数 × 100%。
- 确认结果覆盖率 = 备案后满足数 / 实际参与数 × 100%（备案值 `YES` 的文件改判满足，`NO` 改判不满足；未做任何备案时，确认覆盖率 == 检测覆盖率）。
- overview 行级 `filingCoverage` 即确认结果覆盖率。
