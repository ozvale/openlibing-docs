# 静态告警问题责任人指定 - 技术设计

## 1. 方案设计

在静态告警问题管理中增加**责任人（assignee）**功能，允许对问题指定一个或多个处理责任人，支持两种指定方式：

- **精确指定**：前端勾选一条或多条问题，统一指定责任人
- **条件批量指定**：前端配置筛选条件（仓库、分支、工具、级别、状态等），对满足条件的问题批量指定责任人

方案核心思路：在 `static_alarm_issue` 主表新增 `assignees` 字段（`List<String>`），通过两个指定接口 + 一个搜索接口完成端到端操作，同时写入审计记录表保证操作可追溯。不引入新的工作流状态，责任人信息作为问题的附加属性存在，不影响现有的 OPEN/SHIELDED/RESOLVED 状态流转。

责任人来源：前端选择责任人时，通过搜索接口查询 `repo_user_role_info` 表（MySQL），按仓库 ID 集合 + 账号关键字 + 平台筛选，返回该仓库下具备角色的用户作为候选责任人。

```
┌──────────────────────────────────────────────────────────────────────┐
│  前端                                                                 │
│  ┌────────────────────┐  ┌────────────────────────┐  ┌────────────┐  │
│  │ 搜索责任人候选       │  │ 精确模式：勾选问题列表  │  │ 条件批量    │  │
│  │ GET /assignee/search│  │ POST /issue/assign     │  │ POST /issue│  │
│  │        │            │  │                        │  │ /assign-by-│  │
│  │        ▼            │  │                        │  │ filter     │  │
│  │ ┌────────────────┐  │  │                        │  │            │  │
│  │ │ repo_user_role │  │  │                        │  │            │  │
│  │ │ _info (MySQL)  │  │  │                        │  │            │  │
│  │ └────────────────┘  │  │                        │  │            │  │
│  └─────────┬──────────┘  └──────────┬─────────────┘  └──────┬─────┘  │
│            │                        │                        │         │
└────────────┼────────────────────────┼────────────────────────┼─────────┘
             │                        │                        │
             ▼                        ▼                        ▼
┌──────────────────────────────────────────────────────────────────────┐
│  StaticAlarmController (新增 3 个端点)                                 │
│  StaticAlarmService.searchAssignees() / assign() / assignByFilter()   │
│  ┌────────────────────────────────────────────────────────────────┐  │
│  │ [搜索] 查 repo_user_role_info (MyBatis → MySQL)                │  │
│  │ [指定] 1.参数校验 → 2.权限校验 → 3.批量更新 MongoDB             │  │
│  │         4.批量写审计记录 → 5.返回成功/失败明细                  │  │
│  └────────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────────┘
```

---

## 2. 实现逻辑

### 2.1 精确指定流程 (`/issue/assign`)

```
输入: issueIds (List<String>), assignees (List<String>), userId (String)
  │
  ├─ 1. 校验 issueIds 非空 & assignees 非空
  │
  ├─ 2. 批量查询 issueIds 对应的 issue 记录
  │     提取 repoType + owner + repo 去重集合
  │
  ├─ 3. 权限校验：对每个 (repoType, owner, repo) 组合
  │     验证 userId 是否为该仓库管理员
  │     (复用现有 Shield 的权限校验逻辑)
  │
  ├─ 4. 批量更新 MongoDB：
  │     db.static_alarm_issue.updateMany(
  │       { _id: { $in: issueIds } },
  │       { $set: { assignees: [...], updatedAt: now } }
  │     )
  │
  ├─ 5. 批量写入审计记录到 static_alarm_assign_audit：
  │     每条 issue 写入一条审计记录
  │     { issueId, operation: ASSIGN, oldAssignees, newAssignees, operator, operatedAt }
  │
  └─ 6. 返回 StaticAlarmAssignResultVO
        { successCount, failCount, details: [{ issueId, success, errorMsg }] }
```

### 2.2 条件批量指定流程 (`/issue/assign-by-filter`)

```
输入: filterConditions (条件对象), assignees (List<String>), userId (String)
  │
  ├─ 1. 校验：至少一个筛选维度非空（repoType+owner+repo / branch / tool / severity / status）
  │     校验 assignees 非空
  │
  ├─ 2. 权限校验：对筛选条件涉及的 (repoType, owner, repo) 组合
  │     验证 userId 是否为仓库管理员
  │     (若筛选条件未指定具体仓库，需要额外的项目级权限校验)
  │
  ├─ 3. 构造 MongoDB 查询条件：
  │     基于 filterConditions 构造 criteria（复用 StaticAlarmOperation.buildIssueCriteria 逻辑）
  │
  ├─ 4. 先查询匹配的 issueIds（分页拉取，避免一次更新过多）：
  │     db.static_alarm_issue.find(criteria, { _id: 1 })
  │     单次上限 5000 条，超出返回错误提示缩小筛选范围
  │
  ├─ 5. 批量更新：
  │     db.static_alarm_issue.updateMany(
  │       { _id: { $in: matchedIds } },
  │       { $set: { assignees: [...], updatedAt: now } }
  │     )
  │
  ├─ 6. 批量写入审计记录
  │
  └─ 7. 返回 StaticAlarmAssignResultVO
        { successCount, matchedCount, details }
```

### 2.3 责任人来源搜索流程 (`/assignee/search`)

```
输入: repoIds (List<String>), accountLogin (String, 可选), accountPlatform (String, 可选)
  │
  ├─ 1. 校验 repoIds 非空
  │
  ├─ 2. 查询 repo_user_role_info 表（MySQL，MyBatis）：
  │     SELECT DISTINCT account_id, account_login, account_name, account_platform
  │     FROM repo_user_role_info
  │     WHERE repo_id IN (#{repoIds})
  │       [AND account_login LIKE CONCAT('%', #{accountLogin}, '%')]
  │       [AND account_platform = #{accountPlatform}]
  │     LIMIT #{limit}
  │
  ├─ 3. 返回 StaticAlarmAssigneeVO 列表
  │     { accountId, accountLogin, accountName, accountPlatform }
  │
  └─ 注：此接口无需仓库管理员权限，仅用于提供候选列表
```

### 2.4 列表查询与筛选扩展

- 列表 VO (`StaticAlarmIssueListVO`) 增加 `assignees` 字段
- 详情 VO (`StaticAlarmIssueDetailVO`) 增加 `assignees` 字段
- 查询 DTO (`StaticAlarmQueryDTO`) 增加 `assignees` 多选筛选字段
- 筛选项接口返回结果增加 `assignees` 候选列表（从现有 issue 中提取已存在的 assignee 值）

---

## 3. 类设计

### 3.1 DTO

#### StaticAlarmAssignDTO（精确指定入参）

```java
package com.openlibing.codecheck.business.entity.dto.alarm;

@Data
public class StaticAlarmAssignDTO {
    @NotEmpty(message = "问题 ID 列表不能为空")
    private List<String> issueIds;

    @NotEmpty(message = "责任人列表不能为空")
    private List<String> assignees;
}
```

#### StaticAlarmAssignByFilterDTO（条件批量指定入参）

```java
package com.openlibing.codecheck.business.entity.dto.alarm;

@Data
public class StaticAlarmAssignByFilterDTO {
    // --- 筛选条件（所有字段可选，但至少一个非空）---
    private String repoType;
    private String owner;
    private String repo;
    private String branch;
    private String tool;
    private List<String> severities;
    private List<String> statuses;
    private List<String> ruleIds;
    private List<String> languages;
    // 兼容项目级多仓坐标
    private List<RepoCoordinate> repoCoordinates;

    @NotEmpty(message = "责任人列表不能为空")
    private List<String> assignees;

    @Data
    @AllArgsConstructor
    @NoArgsConstructor
    public static class RepoCoordinate {
        private String repoType;
        private String owner;
        private String repo;
    }
}
```

#### StaticAlarmAssigneeSearchDTO（责任人搜索入参）

```java
package com.openlibing.codecheck.business.entity.dto.alarm;

@Data
public class StaticAlarmAssigneeSearchDTO {
    @NotEmpty(message = "仓库 ID 列表不能为空")
    private List<String> repoIds;

    /** 账号关键字（模糊匹配），可选 */
    private String accountLogin;

    /** 账号平台，可选 */
    private String accountPlatform;

    /** 返回条数上限，默认 20 */
    private Integer limit;
}
```

### 3.2 VO

#### StaticAlarmAssigneeVO（责任人候选）

```java
package com.openlibing.codecheck.business.vo.alarm;

@Data
public class StaticAlarmAssigneeVO {
    private String accountId;
    private String accountLogin;
    private String accountName;
    private String accountPlatform;
}
```

#### StaticAlarmAssignResultVO（指定结果）

```java
package com.openlibing.codecheck.business.vo.alarm;

@Data
public class StaticAlarmAssignResultVO {
    /** 成功更新条数 */
    private int successCount;
    /** 失败条数 */
    private int failCount;
    /** 条件模式下匹配到的总条数 */
    private Integer matchedCount;
    /** 明细（失败时给出原因） */
    private List<AssignDetail> details;

    @Data
    @AllArgsConstructor
    @NoArgsConstructor
    public static class AssignDetail {
        private String issueId;
        private boolean success;
        private String errorMsg;
    }
}
```

### 3.3 Entity

#### StaticAlarmAssignAuditEntity（审计记录）

```java
package com.openlibing.codecheck.business.entity.alarm;

@Data
@Document(collection = "static_alarm_assign_audit")
public class StaticAlarmAssignAuditEntity {
    @Id
    private String id;
    /** 关联的问题 ID */
    private String issueId;
    /** 操作类型：ASSIGN */
    private String operation;
    /** 操作前的责任人列表 */
    private List<String> oldAssignees;
    /** 操作后的责任人列表 */
    private List<String> newAssignees;
    /** 操作人 userId */
    private String operator;
    /** 操作来源：BY_IDS / BY_FILTER */
    private String source;
    /** 操作时间 */
    private Date operatedAt;
}
```

### 3.4 现有类修改

| 类 | 修改内容 |
|---|---|
| `StaticAlarmIssueEntity` | 新增字段 `private List<String> assignees;` |
| `StaticAlarmIssueListVO` | 新增字段 `private List<String> assignees;` |
| `StaticAlarmIssueDetailVO` | 新增字段 `private List<String> assignees;` |
| `StaticAlarmQueryDTO` | 新增字段 `private List<String> assignees;`（多选筛选） |
| `StaticAlarmFilterOptionsQueryDTO` | 无需修改，筛选项根据实际数据动态返回 |
| `StaticAlarmController` | 新增 3 个端点：`GET /assignee/search`、`POST /issue/assign`、`POST /issue/assign-by-filter` |
| `StaticAlarmService` (接口) | 新增 3 个方法签名 |
| `StaticAlarmServiceImpl` | 新增 3 个方法实现，注入 MyBatis Mapper 查询 `repo_user_role_info` |
| `StaticAlarmOperation` | 新增 `batchUpdateAssignees()`、`findIssueIdsByFilter()` 方法 |
| `UserRoleMapper` (MyBatis) | 新增 `searchRepoUsers()` 查询方法，参数 repoIds + accountLogin + accountPlatform |
| `CodeCheckCollectionName` | 新增 `STATIC_ALARM_ASSIGN_AUDIT` 常量 |

---

## 4. 数据模型设计

### 4.1 `static_alarm_issue` 新增字段

| 字段 | 类型 | 说明 |
|------|------|------|
| assignees | List\<String\> | 责任人列表（用户 ID），可为空 |

### 4.2 新增集合 `static_alarm_assign_audit`（审计表）

| 字段 | 类型 | 说明 |
|------|------|------|
| id | String | 主键 |
| issueId | String | 关联的问题 ID |
| operation | String | 操作类型：ASSIGN |
| oldAssignees | List\<String\> | 操作前的责任人列表 |
| newAssignees | List\<String\> | 操作后的责任人列表 |
| operator | String | 操作人 userId |
| source | String | 操作来源：BY_IDS / BY_FILTER |
| operatedAt | Date | 操作时间 |

索引设计：

| 索引名 | 字段 | 类型 | 用途 |
|--------|------|------|------|
| idx_assign_audit_issue | issueId, operatedAt(-1) | 普通 | 按问题查指定历史 |

---

## 5. API 接口设计

### 5.1 精确指定责任人

| 项目 | 内容 |
|------|------|
| 方法 | POST |
| 路径 | `/static-alarm/v1/issue/assign` |
| 描述 | 对指定 ID 列表的问题批量指定责任人 |
| 鉴权 | 需登录态，需仓库管理员权限 |

**请求参数**：

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| userId | Query | String | 是 | 操作人 ID |
| StaticAlarmAssignDTO | Body | JSON | 是 | issueIds + assignees |

**请求示例**：

```json
{
  "issueIds": ["abc123", "def456", "ghi789"],
  "assignees": ["zhangsan", "lisi"]
}
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "successCount": 2,
    "failCount": 1,
    "details": [
      { "issueId": "abc123", "success": true },
      { "issueId": "def456", "success": true },
      { "issueId": "ghi789", "success": false, "errorMsg": "问题不存在或已删除" }
    ]
  }
}
```

### 5.2 条件批量指定责任人

| 项目 | 内容 |
|------|------|
| 方法 | POST |
| 路径 | `/static-alarm/v1/issue/assign-by-filter` |
| 描述 | 对满足筛选条件的问题批量指定责任人 |
| 鉴权 | 需登录态，需仓库管理员权限 |

**请求参数**：

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| userId | Query | String | 是 | 操作人 ID |
| StaticAlarmAssignByFilterDTO | Body | JSON | 是 | 筛选条件 + assignees |

**请求示例**：

```json
{
  "repoType": "gitcode",
  "owner": "openlibing",
  "repo": "openlibing-codecheck",
  "statuses": ["OPEN"],
  "severities": ["ERROR"],
  "assignees": ["zhangsan", "lisi"]
}
```

**响应**：

```json
{
  "code": 0,
  "data": {
    "successCount": 150,
    "failCount": 0,
    "matchedCount": 150
  }
}
```

**约束**：
- 至少提供一个筛选维度（`repoType+owner+repo`、`branch`、`tool`、`severities`、`statuses` 等任意组合）
- 匹配数量超过 5000 条时返回错误：`"匹配问题过多（{count}），请缩小筛选范围"`

### 5.3 现有接口改动

#### GET `/static-alarm/v1/list` — 列表返回增加 assignees

响应 `StaticAlarmIssueListVO` 中新增 `assignees` 字段。

#### GET `/static-alarm/v1/issue/detail` — 详情返回增加 assignees

响应 `StaticAlarmIssueDetailVO` 中新增 `assignees` 字段。

#### GET `/static-alarm/v1/list` — 查询入参增加 assignees 筛选

请求参数 `StaticAlarmQueryDTO` 中新增 `assignees` 多选参数，支持按责任人筛选问题。

#### GET `/static-alarm/v1/issue/filter-options` — 筛选项增加 assignees

响应中新增可选的 `assignees` 列表，返回当前筛选上下文中已存在的责任人候选值。

### 5.4 责任人来源搜索

| 项目 | 内容 |
|------|------|
| 方法 | GET |
| 路径 | `/static-alarm/v1/assignee/search` |
| 描述 | 按仓库 ID 集合搜索具备角色的用户，作为责任人候选列表（自动补全） |
| 鉴权 | 需登录态，无需仓库管理员权限（仅读取候选列表） |

**请求参数**：

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| repoIds | Query | String[] | 是 | 仓库 ID 列表 |
| accountLogin | Query | String | 否 | 账号关键字，模糊匹配（LIKE %xxx%） |
| accountPlatform | Query | String | 否 | 账号平台 |
| limit | Query | Integer | 否 | 返回条数上限，默认 20 |

**数据源**：`repo_user_role_info` 表（MySQL），通过 MyBatis 查询。

**请求示例**：

```
GET /static-alarm/v1/assignee/search?repoIds=123&repoIds=456&accountLogin=zhang&accountPlatform=gitcode&limit=20
```

**响应**：

```json
{
  "code": 0,
  "data": [
    {
      "accountId": "u001",
      "accountLogin": "zhangsan",
      "accountName": "张三",
      "accountPlatform": "gitcode"
    },
    {
      "accountId": "u002",
      "accountLogin": "zhangwei",
      "accountName": "张伟",
      "accountPlatform": "gitcode"
    }
  ]
}
```

---

## 6. 安全设计

### 6.1 权限控制

- 责任人指定操作需要**仓库管理员权限**，复用现有的 shield/unshield 权限校验逻辑
- 条件批量指定时，若筛选条件涉及多个仓库，需要对每个仓库逐一校验管理员权限
- 若筛选条件未限定具体仓库（如仅按 tool 或 severity 筛选），需增加**项目级管理员**或**系统管理员**权限校验
- 权限校验失败返回 403，并记录审计日志（即使操作未执行）

### 6.2 输入校验

| 校验项 | 规则 |
|--------|------|
| issueIds | 非空，单次不超过 200 条 |
| assignees | 非空，每个元素为有效 userId 格式（字母、数字、下划线、中划线），单次不超过 20 个 |
| 筛选条件 | 至少一个维度非空，防止全表更新 |
| 匹配上限 | 条件批量模式匹配超过 5000 条时拒绝执行，要求缩小范围 |
| userId | 非空，与当前登录态一致 |

### 6.3 审计追溯

- 每次指定操作写入 `static_alarm_assign_audit`，记录操作前后的 assignees 快照
- 审计记录包含：issueId、操作人、操作时间、操作来源（BY_IDS / BY_FILTER）、变更前后值
- 审计记录不可删除，保留完整的责任人变更历史

### 6.4 其他安全考量

- 不做责任人通知（发消息/邮件等），避免信息泄露风险，通知由上游业务系统自行处理
- assignees 存储的是用户 ID，前端展示时由调用方自行查用户名做脱敏映射
- 不在 SARIF 解析流程中自动设置 assignees，仅通过人工操作指定
- MongoDB 更新使用 `updateMany` + 精确条件，避免注入风险（使用 MongoTemplate 参数化查询）
