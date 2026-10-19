# 代码检查仓库展示分支配置 API

> Tag: `代码检查运营看板`
> 分支: `enhance_dashboard_codecheck`
> 关联 PR: https://gitcode.com/openlibing/openlibing-ops/merge_requests/139

## 概述

代码检查详情接口走配置分支筛选（详见 [design-final.md](./2026-07-28_代码检查运营看板/design-final.md)）。本批次新增 2 个 RESTful 接口（配置 add/list），并复用 `/common/detail` 端点扩展 1 个分支明细分类（`code-check-branch-detail`），合计对外 4 个能力。

存储表：`sdi_rd_efc_codecheck_branch_config`（Doris UNIQUE 表，详见 `dm_rd_efc_repo_code_metric_day` DDL 段）。
接口列表：

| 路径                                                    | 方法 | 用途                                                          |
| ------------------------------------------------------- | ---- | ------------------------------------------------------------- |
| `/code-check-dashboard/branch-config/add`               | POST | **批量**新增仓库展示分支配置（一次请求可写入多个仓）          |
| `/code-check-dashboard/branch-config/list`              | POST | **分页 + 仓库 id 多选**列出项目下仓库及其展示分支配置         |
| `/common/detail`（category=`code-check-repo-detail`）   | POST | 仓库明细（详情表），走配置分支筛选                            |
| `/common/detail`（category=`code-check-branch-detail`） | POST | 分支明细（新增），从 `dwi_rd_efc_repo_branch_detail_day` 取数 |

通用响应体：

```json
{
  "code": 200,
  "messageCn": "操作成功",
  "messageEn": "Success",
  "data": <T>
}
```

---

## 1. 批量新增展示分支配置

**POST** `/code-check-dashboard/branch-config/add`

### 请求体

请求体直接为 `CodeCheckBranchConfigReq` 数组（**不包装外层对象**）；数组至少 1 条 `@Valid` 通过。

单条字段：

| 字段     | 类型    | 必填 | 说明                      | 示例     |
| -------- | ------- | ---- | ------------------------- | -------- |
| `repoId` | Integer | ✅   | 仓库 id                   | `1001`   |
| `branch` | String  | ✅   | 展示分支名（trim 后非空） | `master` |

请求示例：

```json
[
  { "repoId": 1001, "branch": "master" },
  { "repoId": 1002, "branch": "release-2026-Q3" },
  { "repoId": 1003, "branch": "develop" }
]
```

### 响应

`data = null`（仅返回成功码）。

### 业务说明

- 写入表 `sdi_rd_efc_codecheck_branch_config`，影响详情接口"每仓展示一行"的分支选择。
- 单接口内一次性写入多条；Service 用 `@Transactional` 包裹，循环调用 `SdiRdEfcCodecheckBranchConfigServiceImpl.insert`（MyBatis-Plus `IService.insert`），任一异常整体回滚。
- 若同 `(repoId, branch)` 已存在，由数据库唯一约束决定行为（重复插入可能抛异常）。
- 不做删除接口：详情接口有"未配置走默认分支（`sdi_repo_branch_info.default_branch`）"的兜底语义，配置错误可被覆盖写入新值。

---

## 2. 列出项目下仓库展示分支配置（分页 + repoIds 过滤）

**POST** `/code-check-dashboard/branch-config/list`

### 请求体

| 字段        | 类型            | 必填 | 默认   | 说明                                                 | 示例           |
| ----------- | --------------- | ---- | ------ | ---------------------------------------------------- | -------------- |
| `projectId` | Integer         | ✅   | —      | 项目 id                                              | `12345`        |
| `page`      | Integer         | ❌   | `1`    | 当前页（1 ≤ page ≤ 10000）                           | `1`            |
| `pageSize`  | Integer         | ❌   | `20`   | 每页大小（1 ≤ pageSize ≤ 100）                       | `20`           |
| `repoIds`   | List\<Integer\> | ❌   | `null` | 按仓库 id 多选过滤；**空/null = 不过滤**（项目全量） | `[1001, 1002]` |

请求示例：

```json
{
  "projectId": 12345,
  "page": 1,
  "pageSize": 20,
  "repoIds": [1001, 1002]
}
```

### 响应 data

`PageResult<CodeCheckBranchConfigResp>`，按 `repoName` 升序。

单条字段：

| 字段       | 类型    | 说明                                                                    |
| ---------- | ------- | ----------------------------------------------------------------------- |
| `repoId`   | Integer | 仓库 id                                                                 |
| `repoName` | String  | 仓库名称                                                                |
| `branch`   | String  | 已配置的展示分支；**`null`** 表示该仓未配置（前端应走默认分支回退口径） |

`PageResult` 通用字段：`page` / `pageSize` / `total` / `records`。

响应示例：

```json
{
  "code": 200,
  "messageCn": "操作成功",
  "messageEn": "Success",
  "data": {
    "page": 1,
    "pageSize": 20,
    "total": 3,
    "records": [
      { "repoId": 1001, "repoName": "payment-core", "branch": "master" },
      { "repoId": 1002, "repoName": "settlement-core", "branch": null },
      {
        "repoId": 1003,
        "repoName": "user-center-core",
        "branch": "release-2026-Q3"
      }
    ]
  }
}
```

### 业务说明

- 项目下**指定仓库（`repoIds`）或全量**返回，**未配置的仓 `branch = null`**（数据源：`sdi_repo_info` 过滤 + `sdi_rd_efc_codecheck_branch_config` 命中）。
- 一仓一行；前端拿到 `branch=null` 时，详情接口会走 `sdi_repo_branch_info.default_branch = true` 的分支兜底。
- 排序：`ORDER BY repo_name ASC`，保证前端展示稳定。
- 分页：在 Java 端 `PageResult.pageConvert(page, pageSize, rows)` 截断；`total` = 过滤后仓库总数。

---

## 错误码

沿用项目统一 `ResponseCodeEnum`：

| code | 含义                                                                |
| ---- | ------------------------------------------------------------------- |
| 200  | 成功                                                                |
| 4xx  | 请求参数校验失败（如 `repoId / branch / projectId` 缺失；数组为空） |
| 5xx  | 系统异常                                                            |

---

## 3. 仓库分支明细（`/common/detail` category=`code-check-branch-detail`）

**POST** `/common/detail`

### 请求体

```json
{
  "category": "code-check-branch-detail",
  "repoId": 1001,
  "branch": "master",
  "createDate": "2026-07-22",
  "page": 1,
  "pageSize": 10,
  "startTime": "2026-07-22 00:00:00",
  "endTime": "2026-07-22 23:59:59"
}
```

字段说明（继承 `DetailReq` / `TimeReq`，仅列关键项）：

| 字段                | 类型      | 必填 | 说明                                         |
| ------------------- | --------- | ---- | -------------------------------------------- |
| `category`          | String    | ✅   | 固定 `code-check-branch-detail`              |
| `repoId`            | Integer   | ✅   | 仓库 id（前端直接传 `repoId`，无需解析 URL） |
| `branch`            | String    | ✅   | 分支名                                       |
| `createDate`        | LocalDate | ✅   | 数据创建日期                                 |
| `page` / `pageSize` | Integer   | ❌   | 分页（默认 1 / 10）                          |

### 响应 data

`PageResult<CodeCheckBranchDetailResp>`。

单条字段：

| 字段         | 类型      | 说明         |
| ------------ | --------- | ------------ |
| `repoUrl`    | String    | 仓库 URL     |
| `branch`     | String    | 分支名       |
| `createDate` | LocalDate | 数据创建日期 |

### 业务说明

- **不新增独立端点**，复用已有 `/common/detail` 归一化端点 + `CommonHandleFactory<T>` 路由。
- `DetailReq` 多态注册新增 `@JsonSubTypes(name = "code-check-branch-detail") -> CodeCheckBranchDetailReq`。
- **关键流程**：
  1. Service 通过 `SdiRepoInfoService.getOne(LambdaQueryWrapper.eq(repoId), false)` 按 `repoId` 从 `sdi_repo_info` 查到 `repoUrl`。
  2. 若仓不存在，记录 warn 日志并返回空分页（**不抛错**，让前端优雅兜底）。
  3. 用 `(repoUrl, branch, createDate)` 在 `dwi_rd_efc_repo_branch_detail_day` 中查所有行，按需分页。
- 数据源：`dwi_rd_efc_repo_branch_detail_day`（Doris UNIQUE KEY `(repo_url, branch, create_date)`）。
- 与 `/code-check-dashboard/branch-config/list` 的关系：列表只给"已配置展示分支"，明细按 `branch + createDate` 查实际行数 / 检出明细。

### 命名规范

枚举 / JSON `category` / `@JsonTypeName` **统一全小写连字符 (kebab-case)**，与现有 `ops-repo-detail` / `github-pr-detail` / `code-scan-language` 等保持一致。

| 枚举                       | category 字符串            | 备注                 |
| -------------------------- | -------------------------- | -------------------- |
| `CODE_CHECK_REPO_DETAIL`   | `code-check-repo-detail`   | 仓库明细             |
| `CODE_CHECK_BRANCH_DETAIL` | `code-check-branch-detail` | 分支明细（本批新增） |

---

## 内部实现要点

- `CodeCheckBranchConfigService` 走 MyBatis-Plus `IService` 自带方法，无自定义 SQL：
  - `addBatch(List<CodeCheckBranchConfigReq>)`：`@Transactional` + 循环调用 `configService.insert(entity)`；入参校验由 `@Valid @NotEmpty` 在 Controller 层完成。
  - `list(CodeCheckBranchConfigListReq)`：先 `repoInfoMapper.selectList(LambdaQueryWrapper<SdiRepoInfo>.eq(projectId).in(repoIds, ?).select(...))`，再 `configMapper.selectList(IN(repoIds))` 命中，Java 端 `HashMap` 拼装 + `PageResult.pageConvert(page, pageSize, rows)` 截断。
- `OpsCodeCheckBranchDetailService`：
  - 注入 `DwiRdEfcRepoBranchDetailDayMapper`（`BaseMapper<DwiRdEfcRepoBranchDetailDay>`）和 `SdiRepoInfoService`（`IService<SdiRepoInfo>`）。
  - `queryDetail` 先做 `repoId -> repoUrl` 解析（不存在返空分页），再按 `(repoUrl, branch, createDate)` 三字段精确匹配。
- Mapper：`SdiRdEfcCodecheckBranchConfigMapper extends BaseMapper<SdiRdEfcCodecheckBranchConfig>`；`DwiRdEfcRepoBranchDetailDayMapper extends BaseMapper<DwiRdEfcRepoBranchDetailDay>`（均无 XML）。
- 实体：`SdiRdEfcCodecheckBranchConfig`（无 `id` 字段，直接以 `(repo_id, branch)` 业务主键标识）；`DwiRdEfcRepoBranchDetailDay`（Doris UNIQUE KEY `(repo_url, branch, create_date)`）。
