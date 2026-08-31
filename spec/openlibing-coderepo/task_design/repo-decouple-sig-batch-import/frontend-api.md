# 代码仓管理优化 + SIG 仓一键同步 · 前端接口文档

> 配套文档：[requirement-design.md](./requirement-design.md)（需求设计：方案唯一基线）、[feature-spec.md](./feature-spec.md)（特性规格）、[demo.html](./demo.html)（页面原型）。
>
> 本文档面向前端开发，仅覆盖本期**新增/改造**接口与前端需要感知的行为变化；未列出的接口均保持现状。

## 1. 通用约定

### 1.1 基础信息

| 项           | 约定                                                                                                      |
| ------------ | --------------------------------------------------------------------------------------------------------- |
| 服务         | openlibing-coderepo                                                                                       |
| 路径前缀     | `/project-repo`（仓库相关，RepoController）、`/project-config`（全局配置相关，ProjectConfigController）   |
| 鉴权         | 沿用现有网关 token + 角色校验；新增接口读权限沿用 `query-repo` 角色集合、写权限沿用 `add-repo` 角色集合   |
| 传参风格     | 现有 `/project-repo` 接口沿用 `userId` / `userName` 走 query、复杂对象走 JSON 请求体；本期新增 `/project-config` 接口的参数位置以各节定义为准：`global-config` 走 query（`userId`/`userName`/`projectId`），`validate-sig-path` / `sig-sync` 的 `userId`/`userName`/`projectId` 统一放 JSON 请求体（与需求设计基线 §6.5/§6.6 一致），`sig-sync/status` 走 query |
| Content-Type | `application/json`（有请求体时）                                                                          |

### 1.2 统一响应结构

```jsonc
{
  "code": 200,          // 200 成功；非 200 见 §4 错误码
  "msg": "success",
  "data": { ... }       // 各接口业务数据，见各节定义
}
```

### 1.3 核心行为变化摘要（前端必读）

| 变化点         | 说明                                                                                                                                                    |
| -------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 录入自动检测   | `repoUrl` blur 调 `check-repo-url`；命中其他项目已录入 → 表单**直接使用**同步过来的上次录入配置（可修改）；编辑对话框**不预填**其他项目数据，仅回显本行 |
| 配置不一致提示 | 录入提交前 / 编辑保存前，传 `formConfig`（编辑时另传 `repoId`）调 `check-repo-url` 比对；`configDiff` 非空 → 弹确认弹窗，用户确认后**仅保存当前项目行** |
| 默认分支只读   | 直接从代码托管平台实时获取，表单只读展示，**不提交该字段**                                                                                              |
| 是否参与运营   | `add-repo` / `update-repo` 新增 `isParticipateOperation` 参数                                                                                           |
| 开关 OR 聚合   | 同一仓库被多项目录入时，开关类配置「任一项目开启即生效」——前端仅需在提示文案中说明，无接口调用变化                                                      |
| SIG 仓一键同步 | 全局配置弹窗内的「一键同步」按钮（异步 + 任务状态在弹窗内展示）                                                                                         |
| 废弃接口       | `GET /project-repo/get-repo-association`、`POST /project-config/update-gitcode-role-mapping` 废弃（能力并入 `check-repo-url` / `global-config`）        |

## 2. 接口总览

| 序号 | 接口                | 方法 | 路径                                | 状态     | 使用场景                           |
| ---- | ------------------- | ---- | ----------------------------------- | -------- | ---------------------------------- |
| 1    | 录入/编辑冲突检测   | POST | `/project-repo/check-repo-url`      | **新增** | 录入 blur 检测、编辑保存前差异检测 |
| 2    | 录入仓库            | POST | `/project-repo/add-repo`            | 改造     | 录入对话框提交                     |
| 3    | 修改仓库            | POST | `/project-repo/update-repo`         | 改造     | 编辑对话框提交                     |
| 4    | 查询全局配置        | GET  | `/project-config/global-config`     | **新增** | 全局配置弹窗打开时回显             |
| 5    | 更新全局配置        | POST | `/project-config/global-config`     | **新增** | 全局配置弹窗保存                   |
| 6    | sig-info 路径校验   | POST | `/project-config/validate-sig-path` | **新增** | 路径输入 blur/防抖即时校验         |
| 7    | 触发 SIG 仓一键同步 | POST | `/project-config/sig-sync`          | **新增** | 全局配置弹窗「一键同步」按钮       |
| 8    | 查询同步任务状态    | GET  | `/project-config/sig-sync/status`   | **新增** | 轮询任务状态（全局配置弹窗内展示） |

## 3. 接口详情

### 3.1 录入/编辑冲突检测 `POST /project-repo/check-repo-url`（新增）

**用途**：同一接口支持两类调用：

- **录入 blur 检测**（只传 `projectId` + `repoUrl`）：检测 `repoUrl` 是否已在其他项目录入（同 repo_url 多行）；命中时返回**上次录入配置副本** `lastConfig`（录入表单预填用）与已关联项目列表。
- **保存前一致性比对**（额外传 `formConfig`，编辑时再传 `repoId`）：将用户当前表单配置与同 repo_url 其他项目行比对，返回差异字段 `configDiff`。录入提交前 / 编辑保存前均调本接口；写接口 `add-repo` / `update-repo` **不做比对**，保持纯写入语义。

**请求**

- Query 参数：

| 参数   | 类型   | 必填 | 说明                  |
| ------ | ------ | ---- | --------------------- |
| userId | String | 是   | 操作人 id（权限校验） |

- 请求体：

| 参数       | 类型    | 必填 | 说明                                                                                                                                                                                                                                                                                    |
| ---------- | ------- | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| projectId  | Integer | 是   | 当前项目 id                                                                                                                                                                                                                                                                             |
| repoUrl    | String  | 是   | 仓库链接（如 `https://gitcode.com/org/repo.git`）                                                                                                                                                                                                                                       |
| repoId     | Integer | 否   | 当前项目本行 repo_id；**保存前比对时若当前项目已有本行（录入场景 blur 返回的 repoId 非 null、编辑场景）必须传**，比对时排除本行                                                                                                                                                         |
| formConfig | Object  | 否   | 用户当前表单配置（**保存前比对时传**；字段同 add-repo 表单配置：repoName / repoOwner / purpose / openSource / repoLanguage / assumePr / autoTrigger / autoTriggerDesignScan / isAutoFormat / isSuppressionEnabled / isParticipateOperation / accessToken 等；默认分支不传、不参与比对） |

```jsonc
// 录入 blur 检测
{
  "projectId": 1,
  "repoUrl": "https://gitcode.com/openlibing/openlibing-coderepo.git"
}

// 保存前一致性比对（编辑场景示例；录入场景不传 repoId 或传 blur 返回的 repoId）
{
  "projectId": 1,
  "repoUrl": "https://gitcode.com/openlibing/openlibing-coderepo.git",
  "repoId": 1001,
  "formConfig": {
    "repoName": "openlibing-coderepo",
    "repoOwner": "sig-owner",
    "purpose": "自研源码",
    "openSource": "lead",
    "repoLanguage": "java",
    "assumePr": "1",
    "autoTrigger": "1",
    "autoTriggerDesignScan": "0",
    "isAutoFormat": false,
    "isSuppressionEnabled": true,
    "isParticipateOperation": true
  }
}
```

**响应**

```jsonc
{
  "code": 200,
  "msg": "success",
  "data": {
    "exists": true, // 该 repo_url 是否已在任一项目录入
    "repoId": 1001, // 当前项目本行 repo_id（当前项目未录入为 null）
    "lastConfig": {
      // 上次录入该代码仓的配置副本（仅录入场景预填用；accessToken 已脱敏为空；不含 remark——备注为项目特定信息，不跨项目复制）
      "repoName": "openlibing-coderepo",
      "repoOwner": "sig-owner",
      "purpose": "自研源码",
      "openSource": "lead",
      "repoLanguage": "java",
      "assumePr": "1",
      "autoTrigger": "1",
      "autoTriggerDesignScan": "0",
      "isAutoFormat": false,
      "isSuppressionEnabled": true,
      "isParticipateOperation": true,
    },
    "associatedProjects": [
      // 已关联项目列表（不含当前项目，供提示文案展示）
      { "projectId": 2, "projectName": "项目A" },
      { "projectId": 3, "projectName": "项目B" },
    ],
    "configDiff": [
      // 配置差异字段（仅当请求传 formConfig 时返回；本表单配置 与 同组其他行比对；无差异或无同组行为空数组）
      {
        "field": "assumePr",
        "fieldLabel": "接管PR管理",
        "currentValue": "1",
        "otherValues": [
          { "projectId": 2, "projectName": "项目A", "value": "0" },
        ],
      },
    ],
  },
}
```

> 默认分支不在本接口返回：录入表单的默认分支只读展示沿用现有录入流程的仓库信息获取逻辑，编辑对话框回显本行数据（默认分支均从代码托管平台实时获取）。

**前端处理要点**

- **录入**：blur 调用（只传基础参数）→ `exists=true` 时将 `lastConfig` 预填进表单（**直接使用同步过来的数据**，可修改）；显示提示条「检测到该代码仓已在 项目A、项目B 录入，表单已按上次录入配置自动同步」。提交前传 `formConfig`（blur 返回的 repoId 非 null 时一并传）再调本接口 → `configDiff` 非空则弹「配置不一致提示」确认弹窗（列出差异字段），用户确认后调 `add-repo`。
- **编辑**：打开对话框回显本行当前配置（**不预填其他项目数据、不覆盖**）；保存前传 `repoId` + `formConfig` 调本接口 → `configDiff` 非空则弹提示性告警，用户确认后调 `update-repo`（仅更新本行）。
- `exists=false`：正常录入流程，无需保存前比对（无同组其他行，`configDiff` 必为空）。

### 3.2 录入仓库 `POST /project-repo/add-repo`（改造）

**变化**：请求体新增 `isParticipateOperation`；默认分支**不入参**（后端从代码托管平台实时获取）。

**请求**

- Query 参数：`userId`（必填）、`userName`（必填）
- 请求体（在现有 RepoDTO 基础上，仅列关键/变化字段）：

| 参数                            | 类型             | 必填 | 说明                                                                                                                                              |
| ------------------------------- | ---------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------- |
| repoName                        | String           | 是   | 代码仓别名，≤50 字符                                                                                                                              |
| repoUrl                         | String           | 是   | 仓库地址                                                                                                                                          |
| repoOwner                       | String           | 是   | 仓库责任人                                                                                                                                        |
| platform                        | String           | 是   | `gitee` / `gitcode` / `github`                                                                                                                    |
| projectId                       | Integer          | 是   | 归属项目 id                                                                                                                                       |
| purpose                         | String           | 是   | 用途（枚举：工程&配置文件 / 文档 / 构建 / 测试 / 自研工具（不参与构建）/ 自研工具（参与构建）/ 自研源码 / 运维部署 / 预研&技术）                  |
| openSource                      | String           | 是   | 开源类型：`lead` 主导开源 / `participate` 参与开源                                                                                                |
| assumePr                        | String           | 是   | 接管 PR 管理：`"0"` / `"1"`                                                                                                                       |
| autoTrigger                     | String           | 是   | 自动触发门禁流水线：`"0"` / `"1"`                                                                                                                 |
| autoTriggerDesignScan           | String           | 是   | 自动触发接口扫描：`"0"` / `"1"`                                                                                                                   |
| isAutoFormat                    | Boolean          | 是   | 代码风格自动修复                                                                                                                                  |
| isSuppressionEnabled            | Boolean          | 是   | 告警抑制自动检视                                                                                                                                  |
| **isParticipateOperation**      | Boolean          | 否   | **新增**：是否参与运营（默认 `true`）                                                                                                             |
| repoLanguage                    | String           | 否   | 语言（java、go 等）                                                                                                                               |
| accessToken / isEditAccessToken | String / Boolean | 否   | 仓库令牌及是否编辑标记（沿用现状）                                                                                                                |
| 其他字段                        | —                | 否   | projectName、realProjectName、disallowSelfMerge、disallowUnresolvedDiscussionsMerge、reviewerId、remark、codecheckRuleSet、antiRuleSet 等沿用现状 |

```jsonc
{
  "repoName": "openlibing-coderepo",
  "repoUrl": "https://gitcode.com/openlibing/openlibing-coderepo.git",
  "repoOwner": "sig-owner",
  "platform": "gitcode",
  "projectId": 1,
  "purpose": "自研源码",
  "openSource": "lead",
  "repoLanguage": "java",
  "assumePr": "1",
  "autoTrigger": "1",
  "autoTriggerDesignScan": "0",
  "isAutoFormat": false,
  "isSuppressionEnabled": true,
  "isParticipateOperation": true,
}
```

**响应**：`DataResult<Integer>`（data 为新录入行的 repo_id）

**业务行为**（命中同组多行时）：当前项目已有本行 → 更新本行；无本行 → 新建本行（配置=用户提交的表单值）。**不覆盖其他项目行**。

### 3.3 修改仓库 `POST /project-repo/update-repo`（改造）

**变化**：请求体新增 `isParticipateOperation`；默认分支**不入参**（后端从平台实时获取，编辑时也不可改）。

**请求**

- Query 参数：`userId`（必填）、`userName`（必填）
- 请求体：RepoDTO（`repoId` **必填**，其余同 §3.2；新增 `isParticipateOperation`）

**响应**：`DataResult<Integer>`

**业务行为**：无跨项目行或配置一致 → 直接更新本行；存在跨项目行且配置不一致 → 前端保存前弹「配置不一致提示」告警（数据来自 §3.1 的 `configDiff`），用户确认后**仅更新本行，不覆盖其他项目行**。

### 3.4 查询全局配置 `GET /project-config/global-config`（新增）

**用途**：全局配置弹窗打开时回显全部配置（sig-info 路径列表 + GitCode 角色映射 + 各平台项目公共账号掩码）。

**请求**

- Query 参数：

| 参数      | 类型    | 必填 | 说明      |
| --------- | ------- | ---- | --------- |
| userId    | String  | 是   | 操作人 id |
| projectId | Integer | 是   | 项目 id   |

**响应**

```jsonc
{
  "code": 200,
  "msg": "success",
  "data": {
    // sig-info.yaml 路径（按平台分组，平台 key：gitcode / gitee / github——后端根据 URL 域名解析归类）
    "sigInfoLocations": {
      "gitcode": [
        {
          "url": "https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private",
          "owner": "openlibing",
          "repo": "community-private",
          "branch": "master",
          "path": "openLiBing-private/sigs/openLiBing-private",
        },
      ],
      "gitee": [],
      "github": [],
    },
    // 角色映射（仅 gitcode 平台有）
    "roleMapping": {
      "gitcode": [
        { "platformRole": "owner", "openlibingRole": "project_admin" },
        { "platformRole": "master", "openlibingRole": "repo_admin" },
        { "platformRole": "developer", "openlibingRole": "developer" },
      ],
    },
    // 各平台项目公共账号（令牌掩码回显）
    "commonAccounts": {
      "gitcode": { "accountName": "openlibing-gitcode", "token": "******" },
      "gitee": { "accountName": "", "token": "" },
      "github": { "accountName": "", "token": "" },
    },
  },
}
```

> 回显按平台分组（`sigInfoLocations.gitcode` / `.gitee` / `.github`），平台 key 即分组标识；`url` 为后端根据存储的 owner/repo/branch/path 拼接的完整路径，前端直接用于输入框回显。

### 3.5 更新全局配置 `POST /project-config/global-config`（新增）

**用途**：全局配置弹窗保存（**唯一写入口**）：一次提交 sig-info 路径列表 + GitCode 角色映射 + 各平台项目公共账号。现有 `/project-config/update-gitcode-role-mapping` 废弃，前端改调本接口。

**请求**

- Query 参数：`userId`（必填）、`userName`（必填）
- 请求体：

| 参数             | 类型     | 必填 | 说明                                                                                                                                                                                                        |
| ---------------- | -------- | ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| projectId        | Integer  | 是  | 项目 id                                                                                                                                                                                                     |
| sigInfoLocations | Object   | 否   | sig-info.yaml 路径 URL，**按平台分键 Map** 提交（`{ "gitcode": [...], "gitee": [...], "github": [...] }`，**合计 ≤20 个**；后端保存时校验每条 URL 域名与其所属平台键一致；回显同结构）                    |
| roleMapping      | Object   | 否   | 仅 `gitcode` 键：`[{ "platformRole": "...", "openlibingRole": "..." }]`                                                                                                                                     |
| commonAccounts   | Object   | 否   | 各平台公共账号：`{ gitcode: { accountName, token }, gitee: {...}, github: {...} }`；**token 留空/`******` 表示不修改原令牌**                                                                                |

```jsonc
{
  "projectId": 1,
  "sigInfoLocations": {
    "gitcode": [
      "https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private",
      "https://gitcode.com/openlibing/community/blob/master/sigs/sig-infra",
    ],
    "gitee": [],
    "github": [],
  },
  "roleMapping": {
    "gitcode": [
      { "platformRole": "owner", "openlibingRole": "project_admin" },
      { "platformRole": "master", "openlibingRole": "repo_admin" },
      { "platformRole": "developer", "openlibingRole": "developer" },
    ],
  },
  "commonAccounts": {
    "gitcode": { "accountName": "openlibing-gitcode", "token": "" },
  },
}
```

**响应**：`DataResult<GlobalConfigVO>`（结构同 §3.4 响应，保存后回显）

**注意**

- 保存时**不再重复校验路径**（路径可用性校验已前移至输入时的 `validate-sig-path`，见 §3.6）。
- 后端对 `projectId` 加分布式锁防并发丢更新，前端无需处理（提交失败按普通错误提示重试即可）。
- 角色映射取值沿用现有角色映射编辑器的可选值。

### 3.6 sig-info 路径校验 `POST /project-config/validate-sig-path`（新增）

**用途**：全局配置弹窗中用户输入/修改 sig-info 路径后（blur / 防抖 300ms）**批量**校验：每条路径（owner/repo/branch/path）是否可访问、其下是否存在 sig-info.yaml 文件。**单条失败不阻断其余路径**；校验结果就地逐条展示，不阻断保存。

**请求**（参数统一放 JSON 请求体，与需求设计基线一致）

| 参数      | 类型     | 必填 | 说明                                                                    |
| --------- | -------- | ---- | ----------------------------------------------------------------------- |
| userId    | String   | 是   | 操作人 id（权限校验）                                                   |
| projectId | Integer  | 是   | 项目 id                                                                 |
| paths     | String[] | 是   | 路径 URL 数组（每条指向 sig-info.yaml 所在**目录**，**≤20 个**）        |

```jsonc
{
  "userId": "10001",
  "projectId": 1,
  "paths": [
    "https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private",
    "https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/sig2",
  ],
}
```

**响应**：`DataResult<List<SigPathValidateVO>>`（逐条对应入参 `paths`，顺序一致）

```jsonc
{
  "code": 200,
  "msg": "success",
  "data": [
    {
      "path": "https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private", // 对应该条入参路径
      "valid": true, // 路径存在且其下存在 sig-info.yaml 文件
      "platform": "gitcode", // 后端根据 URL 域名解析的平台（gitcode / gitee / github）
      "errorCode": null, // 失败时：REPO_NOT_FOUND / BRANCH_NOT_FOUND / FILE_NOT_FOUND / API_ERROR
      "message": "校验通过", // 失败原因描述（如「路径不存在」「目录下未找到 sig-info.yaml 文件」）
    },
  ],
}
```

**前端展示建议**（对响应列表中每条路径逐条展示）

| 校验结果                                        | 展示                                        |
| ----------------------------------------------- | ------------------------------------------- |
| `valid=true`                                    | `● 可用`（绿色）                            |
| `errorCode=REPO_NOT_FOUND` / `BRANCH_NOT_FOUND` | `● 路径不存在`（红色）                      |
| `errorCode=FILE_NOT_FOUND`                      | `● 目录下未找到 sig-info.yaml 文件`（红色） |
| `errorCode=API_ERROR`                           | `● 校验失败，请稍后重试`（红色）            |

> 校验仅在就地标红，不阻断保存；单条失败不阻断其余路径；超过 20 条整批拒绝。

### 3.7 触发 SIG 仓一键同步 `POST /project-config/sig-sync`（新增）

**用途**：全局配置弹窗「SIG 仓一键同步」按钮触发异步同步任务（后端异步执行 + 分布式锁 `sig_sync:{projectId}`，防同一项目并发重复触发）。

**同步规则**（前端提示文案可用）：

- 从全部配置路径拉取 sig-info.yaml 并合并去重；
- 仅同步**尚未录入当前项目**的仓库（已录入的不覆盖）；
- 已存在于其他项目的仓库自动复制**上次录入配置**；全局首次录入的仓库按默认参数填充：别名=repoUrl 中的 repo 名（项目内同名冲突依次尝试「repo名-平台名」、加数字递增）、责任人=代码托管平台创建人账号名、用途=自研源码、开源类型=主导开源、默认分支=从平台实时获取（不可修改）、公共账号令牌=项目级公共账号令牌；所有开关除「是否参与运营=是」外均默认为否。

**请求**（参数统一放 JSON 请求体，与需求设计基线一致）

| 参数      | 类型    | 必填 | 说明       |
| --------- | ------- | ---- | ---------- |
| userId    | String  | 是   | 操作人 id  |
| userName  | String  | 是   | 操作人名称 |
| projectId | Integer | 是   | 项目 id    |

```jsonc
{
  "userId": "10001",
  "userName": "张三",
  "projectId": 1,
}
```

**响应**（立即返回任务 ID，异步执行）

```jsonc
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "sig-sync-123456",
    "status": "RUNNING",
    "message": "SIG同步任务已触发，请稍后查询结果",
  },
}
```

> 若已有任务在执行（分布式锁获取失败），返回已有任务的 `taskId` + `status=RUNNING`，不重复触发；前端按钮在任务 RUNNING 期间置灰防重复提交。

### 3.8 查询同步任务状态 `GET /project-config/sig-sync/status`（新增）

**用途**：轮询一键同步任务状态。**任务状态直接在全局配置弹窗内展示**（代码仓录入配置区域下方的任务状态卡片）。

**请求**

- Query 参数：

| 参数      | 类型    | 必填 | 说明                                              |
| --------- | ------- | ---- | ------------------------------------------------- |
| userId    | String  | 是   | 操作人 id                                         |
| projectId | Integer | 是   | 项目 id                                           |
| taskId    | String  | 否   | 任务 id（触发接口返回值；不传则返回最近一次任务） |

**响应**

```jsonc
{
  "code": 200,
  "msg": "success",
  "data": {
    "taskId": "sig-sync-123456",
    "status": "PARTIAL", // RUNNING / SUCCESS / FAILED / PARTIAL
    "imported": 45, // 已成功同步仓库数
    "failed": 3, // 失败仓库数
    "failedRepos": [
      // 失败仓库列表（含失败原因）
      {
        "repoUrl": "https://gitcode.com/openlibing/openlibing-legacy.git",
        "reason": "平台API超时",
      },
    ],
    "message": "同步完成：成功 45 个，失败 3 个",
  },
}
```

**状态说明**

| status  | 含义     | 前端展示                                      |
| ------- | -------- | --------------------------------------------- |
| RUNNING | 执行中   | 黄色标签 + 已同步/失败计数，继续轮询          |
| SUCCESS | 全部成功 | 绿色标签 + imported 计数                      |
| FAILED  | 全部失败 | 红色标签 + 失败原因                           |
| PARTIAL | 部分成功 | 橙色标签 + imported/failed 计数与失败原因列表 |

**轮询建议**：每 3s 轮询一次，超时 10 分钟停止；任务完成后停止轮询。

## 4. 错误码

| code | msg                              | 场景                                           |
| ---- | -------------------------------- | ---------------------------------------------- |
| 200  | success                          | 成功                                           |
| 403  | SIG 路径不存在或不属于该项目     | sig-sync 接口未配置任何 sigInfoLocations       |
| 403  | 平台不合法                       | 路径 URL 域名非 gitcode/gitee/github           |
| 403  | 跨项目访问被拒绝                 | userId 对 projectId 无访问权限                 |
| 404  | sig-info.yaml 文件不存在         | 实时读取指定路径失败（目录下无 sig-info.yaml） |
| 500  | sig-info.yaml 格式错误或解析失败 | 实时解析失败                                   |
| 500  | 配置文件读取失败，请稍后重试     | 平台 API 调用失败                              |
| 500  | 仓库链接不合法                   | repoUrl 校验失败                               |
| 500  | 该仓库已录入当前项目             | 违反唯一约束（并发兜底）                       |

## 5. 前端交互要点汇总

| 场景           | 交互流程                                                                                                                                                                                                                                                                                                                                                                                                             |
| -------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 录入对话框     | ① `repoUrl` blur（防抖 300ms）调 `check-repo-url`（只传基础参数）；② `exists=true` → 表单**直接使用** `lastConfig` 同步数据（可修改）+ 提示条列出已关联项目；③ 提交前传 `formConfig`（blur 返回的 repoId 非 null 时一并传）再调 `check-repo-url`，`configDiff` 非空 → 弹「配置不一致提示」确认弹窗（文案：仅影响当前项目行，不修改其他项目配置）；④ 确认后调 `add-repo`（含 `isParticipateOperation`，不含默认分支） |
| 编辑对话框     | ① 打开时回显本行配置（不预填其他项目数据）；② 保存前传 `repoId` + `formConfig` 调 `check-repo-url`，`configDiff` 非空 → 弹「配置不一致提示」告警（文案含开关 OR 聚合规则说明）；③ 确认后调 `update-repo`（含 `isParticipateOperation`，不含默认分支）；默认分支只读展示                                                                                                                                              |
| 全局配置弹窗   | ① 打开时 GET `global-config` 回显（`sigInfoLocations` 按平台分组返回，路径输入框用 `url` 回显、公共账号令牌显示掩码）；② 路径输入 blur（防抖 300ms）调 `validate-sig-path`，结果就地展示（不阻断保存）；③ 保存时 POST `global-config`（`sigInfoLocations` 按平台分键 Map 提交 `{gitcode:[...],gitee:[...],github:[...]}`；公共账号令牌留空表示不修改）                                                                                                          |
| SIG 仓一键同步 | ① 点击「一键同步」→ POST `sig-sync` 返回 `taskId`，按钮置灰；② 轮询 GET `sig-sync/status`（每 3s，超时 10 分钟）；③ 任务状态卡片展示在全局配置弹窗内（RUNNING/SUCCESS/FAILED/PARTIAL + imported/failed 计数与失败原因）；④ 完成后恢复按钮                                                                                                                                                                            |
