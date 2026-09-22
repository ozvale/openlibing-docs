# suppression-review-optimize — 技术设计

## 关联

- 业务 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/63
- proposal：同目录 `proposal.md`
- 跨仓协同：openlibing/openlibing-codecheck

---

## 1. 方案设计

### 1.1 总体方案

本需求分两点推进，但实现上高度耦合：

- **第一点（告警抑制评论优化）**：改造 `openlibing-coderepo` 仓的三方代码检查工具告警抑制注释检视能力，将行级评论改为文件级评论表格汇总，并新增评论编辑能力。同时对 `openlibing-codecheck` 仓进行扩展，使服务间接口返回字段"第一个修改文件"信息。
- **第二点（GitHub 复用）**：在 `openlibing-coderepo` 仓全面补齐 github 平台支持（webhook 入口、token 链路、RepoServiceImpl 各方法分支、MR事件处理器平台适配），同时 `openlibing-codecheck` 仓需新增 github 平台扫描能力。

### 1.2 告警抑制评论优化方案

#### 1.2.1 评论形态变更（行级 → 文件级）

**现状**：POST `/api/v5/repos/:owner/:repo/pulls/:number/comments`，请求体含 `body`/`path`/`start_position`/`position`，每条抑制注释一条评论。

**新方案**：请求体改为 `body`/`path`/`position_type=binary`，不传 `start_position`/`position`。一个文件级评论对应一个文件（PR 第一个修改文件），评论 body 是一个含所有抑制注释的表格。

#### 1.2.2 表格汇总与字数拆分

**表格格式**（需要中英文同时显示）：

```
【openlibing.ci】检测到当前PR中存在代码检查告警抑制 N 处，详情见下表，请Committer检视合理性。

| 文件路径 | 行号 | 代码片段 | 工具 |
|---------|------|---------|------|
| src/Foo.java | [42](url#L42) | `// NOPMD` | PMD |
| src/Bar.java | [88](url#L88) | `@SuppressWarnings("unchecked")` | Checkstyle |
| src/Test.java | [88](url#L88) | `# noqa` | flake8/ruff |
```

- 行号带跳转链接：链接格式 `{repo_web_url}/blob/{commit_sha}/{file_path}#L{line_number}`，commit_sha 取 PR head commit
- 工具：同一注释多工具/分隔（复用现有 `appendToolName` 逻辑）

**字数拆分策略**：

- 单条评论 body 上限 65535 字符
- 表格按行（每条抑制注释一行）拆分：先拼表头 + 说明，再逐行追加，当 body 长度 + 下一行长度 > 65500（留 35 字符余量）时，当前评论截止，剩余行进入下一条评论
- 拆分出的多条评论共享同一 `path`（第一个修改文件），但 comment_seq 递增（1, 2, 3...）
- 每条评论的 body 都以说明文字 + 表头开头（保证每条评论可独立阅读），但说明中的"N 处"改为"本条 M 处 / 共 N 处"

#### 1.2.3 检视结果持久化

CREATE 时 POST 返回的 `id`（GitCode/Gitee/GitHub 评论 id）持久化到 MySQL，供 UPDATE 事件 PATCH 编辑评论使用。

存储方案见"4. 数据模型设计"。

#### 1.2.4 UPDATE 事件编辑更新

**现状**：UPDATE 事件触发 `resolveExpiredComments`（PUT resolve 过期评论），且 `callSuppressionScan` 传 `commitShas` 做增量扫描。

**新方案**：
- UPDATE 事件不再调用 `resolveExpiredComments`（因为新方案评论是文件级，不会因行号变化过期；旧的行级评论仍保留 resolve 逻辑处理历史遗留评论，过渡期保留）
- UPDATE 事件调用 `callSuppressionScan` 时，**不再传 commitShas**，全量扫描当前 PR 所有修改文件（与 CREATE 一致）
- 扫描结果返回后，按 `repo_url + pr_number + file_path` 查询已有的评论记录：
  - 若已有评论记录：逐条调用 PATCH `/pulls/comments/{comment_id}` 编辑，更新表格内容
  - 若评论数量变少：编辑前 N-1 条，删除第 N 条
  - 若评论数量变多：编辑前 N 条，新增第 N+1 条
  - 若无评论记录（如被用户误删或CREATE事件未检测到告警抑制注释）：降级为 POST 创建评论
- `MergeRequestEventHandler.handle` 中的 `eventType` 区分 CREATE/UPDATE，分别走 `postSuppressionComments` / `editSuppressionComments`

#### 1.2.5 "第一个修改文件"获取方式（codecheck 跨仓扩展）

**现状**：`openlibing-codecheck` 仓 `SuppressionScanServiceImpl.fetchPrFiles` 已在 CREATE 事件中获取 PR 所有修改文件（diffs 数组），但返回的结果只含 `filePath/lineNumber/codeSnippet/toolName` 4 个字段，不包含文件列表。

**方案**：扩展 `openlibing-codecheck` 仓的扫描响应，新增字段：

```
{
  "code": 200,
  "result": {
    "suppressionScanList": [ {filePath, lineNumber, codeSnippet, toolName}, ... ],  // 抑制注释列表
    "firstChangedFile": "src/main/Foo.java"  // PR第一个修改文件路径
  }
}
```

coderepo 端解析 `firstChangedFile`，作为文件级评论的 `path`。

**兜底策略**：若 codecheck 未返回 `firstChangedFile`，coderepo 从扫描结果 `result` 列表的第一个元素的 `filePath` 作为兜底（不准确但保证可用）。

**codecheck 仓改动**：
1. `SuppressionScanServiceImpl.scanSuppressionComments` 在 CREATE 分支 `fetchPrFiles` 后，记录 `diffs[0].statistic.new_path` 作为 `firstChangedFile`
2. 响应结构新增 `firstChangedFile` 字段
3. UPDATE 事件也改为全量扫描（不再走 `scanCompareDiff` 增量），与 coderepo 新方案对齐

#### 1.2.6 代码仓管理增加开关控制是否检测告警抑制

在录入/编辑代码仓时增加必选项，是否开启代码仓告警抑制检测（同时入库），后续只对开启的代码仓进行检测。

### 1.3 GitHub 复用方案

#### 1.3.1 GitHub webhook 接入

**新增端点**：`WebHookEventController` 新增 `POST /webhookEvent/hooks/github`，解析 `X-GitHub-Event` 头作为 eventType，`repoType` 设为 `"github"`。

**签名校验**：`MachineInterfaceAuthUtil.webhookMachineInterfacePermissionAuth` 改为按 platform 取签名头：
- gitcode → `X-GitCode-Signature-256`
- gitee → `X-Gitee-Token`
- github → `X-Hub-Signature-256`

签名算法三者都是 HmacSHA256，格式都是 `sha256=<hex>`，`validateSignature` 通用。

**事件路由**：GitHub PR 事件头是 `X-GitHub-Event: pull_request`，与现有 `supportedEventType()="Merge Request Hook"` 不一致。

**方案**：不新增 handler，改造 dispatcher 与 handler 支持多事件类型匹配：
- `WebHookEventHandler` 接口 `supportedEventType()` 改为 `Set<String> supportedEventTypes()`（保留旧方法兼容）
- `MergeRequestEventHandler` 返回 `{"Merge Request Hook", "pull_request"}`
- dispatcher 遍历 handler 时检查 `eventType ∈ supportedEventTypes()`

#### 1.3.2 GitHub token 链路打通

**CommonService 新增 `getGithubToken`**：
```java
String getGithubToken(Integer projectId, boolean isDefault);
```
实现参照 `getGitcodeToken`（`CommonServiceImpl.java:598-611`），从 `project_common_account_info` 表读 `github_token` 解密，未配置时回退到 `${github.common.access_token}`。

**RepoServiceImpl 修正**：
- `getRepoAccessToken`（line 2296-2301）：github 项目级 token 改调 `commonService.getGithubToken`
- `getRepoAccessToken`（line 2306-2307）：公共 token 回退改为 `githubCommonToken`
- `getProjectToken`（line 3835-3846）：增加 github 分支
- `getAccessTokenForWebhook`（line 3898-3933）：回退分支增加 github

#### 1.3.3 GitHub PR 评论接口对接

**关键差异**：GitHub 用 `subject_type=file` 实现文件级评论

| 能力 |  GitHub |
|------|--------|
| 创建文件级评论 | POST `/repos/{o}/{r}/pulls/{n}/comments` + `subject_type=file` |
| 编辑评论 | PATCH `/repos/{o}/{r}/pulls/comments/{id}` |
| 列出评论 | GET `/repos/{o}/{r}/pulls/{n}/comments` |
| 认证头 | `Authorization: Bearer <token>` + `Accept: application/vnd.github+json` |

**MR事件处理器 MergeRequestEventHandler 改造**：
- `buildCommentApiUrl`（line 778-791）：增加 github 分支，URL 用 `githubApiUrl + "/repos/" + owner + "/" + repo + "/pulls/" + prNumber + "/comments"`
- `buildRequestBody`（line 884-898）：增加 `buildGithubRequestBody`，请求体用 `body`/`path`/`subject_type=file`
- `sendCommentRequest`（line 936-943）：header 按 platform 切换，github 用 `Authorization: Bearer <token>` + `Accept: application/vnd.github+json`
- 新增 `sendPatchRequest` 方法（HttpRequestUtil 若无 PATCH 则新增），用于编辑评论

#### 1.3.4 GitHub webhook 能力对比

详见"6.5 GitHub webhook 与 GitCode webhook 对比表"。

**核心结论**：GitHub 与 GitCode webhook 机制相似（都是 HMAC SHA256 签名 + 事件头路由），但 payload 结构、事件名、action 语义差异较大，需要逐方法适配。webhook 设置 API 的 body 格式差异也较大（GitHub 用 `config:{url,content_type,secret}` 嵌套结构）。

#### 1.3.5 codecheck 仓 github 扫描支持

**codecheck 仓改动**：
1. `SuppressionScanServiceImpl.fetchPrFiles`（line 110-120）：增加 github 分支，调 `GET https://api.github.com/repos/{owner}/{repo}/pulls/{pr}/files`，header 用 `Authorization: Bearer <token>`
2. GitHub files 响应格式与 gitcode 不同，GitHub 返回 `[{filename, patch, sha, status}]`，`patch` 是 unified diff 文本。需要新增 `parseGithubPatch` 方法将 patch 解析成内部 `diffs[].content.text[]` 格式（可参考 codecheck UPDATE 事件的 `parsePatch` line 795-825）
3. `CodePlateHelper.getCodePlate`（line 107-121）：增加 github 识别，新增 `GithubHelper`/`GithubPlate` 类
4. 新增常量 `github.api.address=https://api.github.com`

### 1.4 RepoServiceImpl github 能力缺口清单

#### 第一优先级（强阻塞，必须补）

| # | 方法 | 位置 | 当前处理 | 需补内容 |
|---|------|------|---------|---------|
| 1 | `CommonService.getGithubToken` | CommonServiceImpl | 不存在 | 新增方法，参照 `getGitcodeToken` |
| 2 | `getRepoAccessToken` | RepoServiceImpl:2296-2301 | 误用 `getGitcodeToken` | 改调 `commonService.getGithubToken` |
| 3 | `getRepoAccessToken` | RepoServiceImpl:2306-2307 | 回退 `gitcodeCommonToken` | 改为 `githubCommonToken` |
| 4 | `getProjectToken` | RepoServiceImpl:3835-3846 | github 返回空串 | 增加 github 分支 |
| 5 | `getAccessTokenForWebhook` | RepoServiceImpl:3898-3933 | github 返回空串 | 回退分支增加 github |
| 6 | `WebHookEventController` | :56,:96 | 无 github 端点 | 新增 `/hooks/github` |
| 7 | `webhookMachineInterfacePermissionAuth` | MachineInterfaceAuthUtil:62-84 | 硬编码 `X-GitCode-Signature-256` | 按 platform 取签名头 |
| 8 | `MergeRequestEventHandler` 平台分支方法群 | extractAction:210 等 | 无 github 分支 | 全部补 github 适配（payload 结构不同） |
| 9 | `MergeRequestEventHandler.getProjectToken` | :611-622 | github 返回空串 | 增加 github 分支 |
| 10 | `MergeRequestEventHandler.buildCommentApiUrl` | :778-791 | 不支持 github | 增加 github 分支 |
| 11 | `MergeRequestEventHandler.buildRequestBody` | :884-898 | 不支持 github | 新增 `buildGithubRequestBody`（`subject_type=file`） |
| 12 | `MergeRequestEventHandler.sendCommentRequest` | :936-943 | 硬编码 `PRIVATE-TOKEN` | header 按 platform 切换 |
| 13 | `ApplyRepoServiceImpl.repoConfig` | :382-383 | github 早 return | 删除早 return，让 webhook 设置走起来 |
| 14 | RepoServiceImpl webhook 方法群 | getRepoWebhookList 等 | 抛异常/空串 | 增加 github 分支 + 新增 `github.webhook.*.url` 配置 |

#### 第二优先级（影响其他能力但不阻塞告警抑制评论）

| # | 方法 | 影响 |
|---|------|------|
| 15 | `syncAllRepoInfoToProjectRepoInfo`| 全量同步所有仓库信息 |
| 16 | `validateAccessToken`| 录入/更新代码仓时校验accessToken有效性 |
| 17 | `checkRepoAccess`| 录入/更新代码仓时校验项目公共账号信息，获取项目可见性和状态 |
| 18 | `syncRepoBranch`| 同步分支 |
| 19 | `SyncUserServiceImpl.syncRepoUserByJob` | 同步用户 |
| 20 | `syncDesignProject` | design 扫描 |
| 21 | `checkProjectHasCommonAccount`/`isTokenValid`/`processAccessTokenAndUserInfo` | 录入校验与展示 |

**本需求聚焦第一优先级**，第二优先级需要先实现15-18、21的能力，其他暂不实现。

### 1.5 清理历史遗留废弃代码

目前已实现

---

## 2. 实现逻辑设计

### 2.1 CREATE 事件处理流程

```
webhook 收到 PR 创建事件
  → WebHookEventController 接收（gitcode/gitee/github）
  → MachineInterfaceAuthUtil 签名校验（按 platform 取头）
  → WebHookEventService.dispatchEvent 分发事件
  → MergeRequestEventHandler.handle 事件处理
    → extractAction / extractPrInfo（按 platform 解析 payload）
    → getAccessToken（按 platform 取 token）
    → callSuppressionScan（传 owner/repo/prNumber/platform/accessToken/eventType=CREATE）
      ← codecheck 返回 {result:[...], firstChangedFile:"src/Foo.java"}
    → mergeSuppressionResultsByLine（聚合同一行多工具）
    → buildTableBody（拼表格，字数超限拆分多条）
    → for each 拆分后的评论片段:
        → POST /pulls/{n}/comments（gitcode: position_type=binary, github: subject_type=file）
        ← 返回 comment_id
        → 持久化到 pr_suppression_comment 表（comment_seq 递增）
```

### 2.2 UPDATE 事件处理流程

```
webhook 收到 PR 更新事件（gitcode: source update, github: synchronize）
  → MergeRequestEventHandler.handle
    → extractAction / extractPrInfo（按 platform 解析 payload）
    → 校验是有效代码变更（hasActualCodeChange）
    → getAccessToken（按 platform 取 token）
    → callSuppressionScan（eventType=UPDATE，不传 commitShas，全量扫描）
      ← codecheck 返回 {result:[...], firstChangedFile:"src/Foo.java"}
    → mergeSuppressionResultsByLine
    → 按 repo_url + pr_number + file_path=firstChangedFile 查询已有评论记录
    → buildTableBody（拼新表格，拆分多条）
    → if 已有评论记录:
        for i in 0..max(已有记录数, 新评论数):
          if i < 已有记录数 and i < 新评论数:
            → PATCH /pulls/comments/{已有comment_id}（编辑为新评论片段）
            → 更新 pr_suppression_comment 记录（update_time, last_scan_count, last_commit_sha, fingerprint）
          elif i < 已有记录数:  # 新评论更少，多余记录删除
            → DELETE /pulls/comments/{已有comment_id}（可选，或保留）
            → 更新记录 comment_status=deleted
          elif i < 新评论数:  # 新评论更多，新增
            → POST /pulls/{n}/comments
            → 插入新 pr_suppression_comment 记录
      else:
        → 降级为 CREATE 流程（POST）
```

### 2.3 GitHub webhook 接入流程

```
GitHub 仓库配置 webhook（url 指向 coderepo /webhookEvent/hooks/github，secret 由 coderepo 生成）
  → GitHub PR 事件触发
  → POST /webhookEvent/hooks/github
    → 取 X-Hub-Signature-256、X-GitHub-Event、X-GitHub-Delivery 头
    → MachineInterfaceAuthUtil 按 platform=github 校验 X-Hub-Signature-256
    → WebhookEventDTO.repoType="github", eventType=X-GitHub-Event 值（如 "pull_request"）
    → dispatchEvent 匹配 MergeRequestEventHandler（supportedEventTypes 含 "pull_request"）
    → MergeRequestEventHandler.handle
      → extractAction：github 从 body.action 取（opened/synchronize/reopened）
      → extractPrInfo：github 从 body.pull_request.number、body.repository.full_name 取
      → isUpdateAction：github action=synchronize 视为 UPDATE
      → hasActualCodeChange：github 检查 body.pull_request.head.sha 与 before.sha 不同
```

### 2.4 评论 id 持久化与查询流程

```
CREATE:
  POST 评论成功 → 解析响应 id → 插入 pr_suppression_comment (id=雪花, comment_seq=1,2,3...)

UPDATE:
  查询 SELECT * FROM pr_suppression_comment WHERE repo_url=? AND pr_number=? AND file_path=? ORDER BY comment_seq
  → 按 comment_seq 顺序 PATCH 编辑
  → 数量变化时 INSERT 新记录或 UPDATE comment_status=deleted

异常恢复:
  若 PATCH 返回 404（评论被手动删除）→ 降级为 POST 新建，插入新记录，旧记录标记 comment_status=deleted
```

---

## 3. 类设计

### 3.1 新增类（openlibing-coderepo 仓）

#### `PrSuppressionCommentEntity`（新增）

路径：`com.openlibing.coderepo.business.entity.suppression.PrSuppressionCommentEntity`

评论记录表实体类，字段对应数据模型设计的 `pr_suppression_comment` 表。

#### `PrSuppressionCommentMapper`（新增）

路径：`com.openlibing.coderepo.business.mapper.PrSuppressionCommentMapper`

提供 `insert`/`batchInsert`/`updateByCommentId`/`queryByRepoAndPr`/`updateStatus` 方法。

#### `PrSuppressionCommentService` / `PrSuppressionCommentServiceImpl`（新增）

路径：`com.openlibing.coderepo.business.service.PrSuppressionCommentService`

封装评论记录的持久化逻辑：
- `saveComments(List<CommentRecord>)`：批量插入
- `queryComments(repoUrl, prNumber, filePath)`：按 PR + 文件查询
- `editComment(record, newBody)`：更新记录并返回 comment_id
- `markDeleted(commentId)`：标记删除

#### `SuppressionCommentBuilder`（新增）

路径：`com.openlibing.coderepo.business.service.suppression.SuppressionCommentBuilder`

无状态工具类，负责：
- `buildTableBody(List<SuppressionData>, firstChangedFile, repoWebUrl, commitSha)`：拼表格 body
- `splitByCharLimit(body, limit=65535)`：按字数拆分多条
- `buildFileLevelRequest(platform, path, body)`：按平台构造文件级评论请求体

#### `GithubWebhookPayloadParser`（新增）

路径：`com.openlibing.coderepo.business.handler.parser.GithubWebhookPayloadParser`

封装 GitHub webhook payload 解析逻辑，与 GitCode/Gitee 解析逻辑隔离。提供 `extractAction`/`extractPrInfo`/`extractCommitShas`/`hasActualCodeChange` 方法。

### 3.2 修改类（openlibing-coderepo 仓）

| 类 | 修改要点 |
|----|---------|
| `WebHookEventController` | 新增 `/hooks/github` 端点 |
| `WebHookEventHandler` | `supportedEventType()` 改为 `Set<String> supportedEventTypes()`（保留旧方法 `@Deprecated`） |
| `WebHookEventServiceImpl` | dispatchEvent 改为检查 `eventType ∈ supportedEventTypes()` |
| `MergeRequestEventHandler` | (1) `supportedEventTypes` 返回 `{"Merge Request Hook","pull_request"}`；(2) 所有 extract* 方法增加 github 分支或委托 `GithubWebhookPayloadParser`；(3) `buildCommentApiUrl`/`buildRequestBody`/`sendCommentRequest` 增加 github 分支；(4) 新增 `editSuppressionComments` 方法处理 UPDATE；(5) `callSuppressionScan` 解析 `firstChangedFile`；(6) 注入 `PrSuppressionCommentService` |
| `MachineInterfaceAuthUtil` | `webhookMachineInterfacePermissionAuth` 按 platform 路由签名头 |
| `CommonService` / `CommonServiceImpl` | 新增 `getGithubToken(Integer projectId, boolean isDefault)` |
| `RepoServiceImpl` | (1) 新增 `@Value("${github.api.address}")`、`@Value("${github.common.access_token}")`、`@Value("${github.webhook.list.url}")` 等字段；(2) `getRepoAccessToken`/`getProjectToken`/`getAccessTokenForWebhook` 增加 github 分支；(3) webhook 方法群（`getRepoWebhookList`/`createRepoWebhook`/`createCoderepoWebhook`/`deleteRepoWebhook`/`deleteRepoWebhookWithToken`）增加 github 分支 |
| `ApplyRepoServiceImpl` | `repoConfig` 删除 line 382-383 的 github 早 return |
| `OpenlibingCodeCheckClient` | `scanSuppression` 返回值类型保持 `Map<String,Object>`，但消费方解析新增 `firstChangedFile` key |

### 3.3 新增类（openlibing-codecheck 仓，跨仓改动）

| 类 | 修改要点 |
|----|---------|
| `SuppressionScanServiceImpl` | (1) `fetchPrFiles` 增加 github 分支；(2) `scanSuppressionComments` 记录 `firstChangedFile` 并写入响应；(3) UPDATE 事件改为全量扫描 |
| `SuppressionScanResult` | 不改字段（firstChangedFile 放在外层响应） |
| `CodePlateHelper` | `getCodePlate` 增加 github 识别 |
| `GithubHelper` / `GithubPlate`（新增） | GitHub 平台辅助类，参照 `GitCodeHelper`/`GitCodePlate` |
| `SuppressionScanController` | 响应结构外层新增 `firstChangedFile` 字段 |

---

## 4. 数据模型设计

### 4.1 新增表 `pr_suppression_comment`

```sql
CREATE TABLE pr_suppression_comment (
    id                  BIGINT       NOT NULL COMMENT '主键，雪花算法生成',
    repo_url            VARCHAR(512) NOT NULL COMMENT '代码仓链接，如 https://gitcode.com/openlibing/openlibing-coderepo.git',
    pr_number           INT          NOT NULL COMMENT 'PR/Issue 编号',
    file_path           VARCHAR(512) NOT NULL COMMENT '评论挂载的文件路径（PR第一个修改文件）',
    suppression_fingerprint VARCHAR(128) NOT NULL COMMENT '注释指纹，本次表格内容的SHA256，用于幂等判断与审计',
    tool_name           VARCHAR(512) NOT NULL COMMENT '工具名称，多个工具逗号分隔',
    comment_id          BIGINT       NOT NULL COMMENT 'GitCode/Gitee/GitHub 返回的评论id',
    comment_seq         INT          NOT NULL DEFAULT 1 COMMENT '同一PR同一文件的第几条评论（字数超限拆分，从1递增）',
    comment_status      VARCHAR(16)  NOT NULL DEFAULT 'active' COMMENT '评论状态：active/deleted/failed',
    last_scan_count     INT          COMMENT '本次扫描到的抑制注释总数',
    last_commit_sha     VARCHAR(64)  COMMENT '触发本次评论/编辑的最新commit sha',
    create_time         DATETIME     NOT NULL COMMENT '评论创建时间',
    update_time         DATETIME     NOT NULL COMMENT '评论修改时间',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='PR告警抑制文件级评论记录表';
```

### 4.2 字段说明

#### 用户指定字段（9 项）

| 字段 | 来源 | 说明 |
|------|------|------|
| `id` | 用户指定 | 雪花算法主键，分布式唯一 |
| `repo_url` | 用户指定 | 代码仓链接，与 `repo_info.repo_url` 一致，用于反查 token 和关联 |
| `pr_number` | 用户指定 | PR/Issue 编号 |
| `create_time` | 用户指定（"评论创建时间"） | 首次 POST 成功时间 |
| `update_time` | 用户指定（"修改时间"） | 每次 PATCH 编辑更新 |
| `file_path` | 用户指定（"文件路径"） | 评论挂载的 PR 第一个修改文件路径 |
| `suppression_fingerprint` | 用户指定（"注释指纹"） | 本次表格内容的 SHA256，含所有抑制注释的 filePath+lineNumber+toolName+codeSnippet |
| `tool_name` | 用户指定（"工具名称"） | 本次评论涉及的所有工具集合，逗号分隔 |
| `comment_id` | 用户指定（"评论id"） | 平台返回的评论 id，用于 PATCH 编辑 |

#### 建议补充字段（6 项，待用户确认）

| 字段 | 补充理由 |
|------|---------|
| `platform` | repo_url 虽能解析平台但不可靠（私有部署 GitCode 域名多样），显式存 platform 便于按平台查询和路由不同 API |
| `owner` / `repo` | 冗余字段，避免每次从 repo_url 解析；便于按 owner/repo 维度统计与排查 |
| `comment_seq` | 同一 PR 同一文件字数超限拆分多条时区分序号，UPDATE 编辑时按序号匹配 |
| `comment_status` | 追踪评论生命周期（active/edited/deleted/lost），便于异常恢复与清理 |
| `last_scan_count` | 审计字段，记录本次扫描到的抑制注释总数，便于排查"评论为何拆成 N 条" |
| `last_commit_sha` | 审计字段，记录触发本次评论的 commit，便于追溯（虽然不按 sha 取增量，但记录 sha 便于问题定位） |

### 4.3 Liquibase changelog

新增 `db/changelog/changeset_pr_suppression_comment.xml`，包含建表 SQL 和索引。

---

## 5. 性能设计

### 5.1 评论字数拆分策略

- 单条评论 body 上限 65535 字符，预留 35 字符余量，阈值取 65500
- 拆分单位：表格行（每条抑制注释一行）
- 拆分算法：先拼说明 + 表头（约 200 字符），再逐行追加；追加前预估行长度（filePath + lineLink + codeSnippet + toolName + 表格分隔符），若当前 body 长度 + 行长度 > 阈值，则当前评论截止，剩余进入下一条
- 每条拆分评论都带独立说明（"本条 M 处 / 共 N 处"）+ 表头，保证可独立阅读

### 5.2 API 调用次数优化

- CREATE：N 条拆分评论 → N 次 POST（无法避免，平台 API 单次只创建一条）
- UPDATE：
  - 比较所有注释行的 `suppression_fingerprint`，若与上次均相同则跳过 PATCH（减少 API 调用），在 `editSuppressionComments` 入口加 fingerprint 比较
- GitHub API 限流：GitHub REST API 限流 5000 req/h（认证用户），单 PR UPDATE 频率远低于此，无需特殊处理

### 5.3 数据库索引设计（待定，代码实现后再看）

### 5.4 并发与幂等

- 复用现有 `acquireEventLock`（Redis SET NX EX，30 分钟）做事件去重，同一 webhook 事件不会并发处理
- UPDATE 事件若并发到达（如快速 push 多次），由 Redis 锁保证串行；PATCH 编辑按 comment_seq 顺序，无并发冲突
- PATCH 404（评论被手动删除）降级为 POST 新建，插入新记录，旧记录标记 `deleted`

---

## 6. API 接口设计

### 6.1 GitCode/Gitee PR 评论接口（文件级）

#### 创建文件级评论

```
POST {gitcodeApiUrl}/v5/repos/{owner}/{repo}/pulls/{prNumber}/comments
Header: PRIVATE-TOKEN: {accessToken}
Body:
{
  "body": "【openlibing.ci】...表格内容...",
  "path": "src/main/Foo.java",
  "position_type": "binary"
}
Response: { "id": 123456, ... }
```

#### 编辑评论

```
PATCH {gitcodeApiUrl}/v5/repos/{owner}/{repo}/pulls/comments/{commentId}
Header: PRIVATE-TOKEN: {accessToken}
Body:
{
  "body": "【openlibing.ci】...新表格内容..."
}
Response: 200
```

**注意**：现有 `HttpRequestUtil` 无 `sendPatch` 方法，需新增。

### 6.2 GitHub PR 评论接口（文件级）

#### 创建文件级评论（subject_type=file）

```
POST https://api.github.com/repos/{owner}/{repo}/pulls/{prNumber}/comments
Header:
  Authorization: Bearer {accessToken}
  Accept: application/vnd.github+json
Body:
{
  "body": "【openlibing.ci】...表格内容...",
  "path": "src/main/Foo.java",
  "subject_type": "file"
}
Response: { "id": 12345678, ... }
```

**关键**：GitHub 2023 年新增 `subject_type=file`，等价于 GitCode 的 `position_type=binary`，无需传 `line`/`start_line`/`side`。

#### 编辑评论

```
PATCH https://api.github.com/repos/{owner}/{repo}/pulls/comments/{commentId}
Header:
  Authorization: Bearer {accessToken}
  Accept: application/vnd.github+json
Body:
{
  "body": "【openlibing.ci】...新表格内容..."
}
Response: 200
```

#### 列出 PR 评论

```
GET https://api.github.com/repos/{owner}/{repo}/pulls/{prNumber}/comments?per_page=100&page={n}
Header: Authorization: Bearer {accessToken}, Accept: application/vnd.github+json
Response: [ { "id":..., "path":..., "body":..., ... }, ... ]
```

### 6.3 GitHub webhook 设置接口

#### 列出 webhook

```
GET https://api.github.com/repos/{owner}/{repo}/hooks
Header: Authorization: Bearer {accessToken}, Accept: application/vnd.github+json
Response: [ { "id":..., "config":{url,content_type}, "events":[...], ... }, ... ]
```

#### 创建 webhook

```
POST https://api.github.com/repos/{owner}/{repo}/hooks
Header: Authorization: Bearer {accessToken}, Accept: application/vnd.github+json
Body:
{
  "config": {
    "url": "https://coderepo.example.com/webhookEvent/hooks/github",
    "content_type": "json",
    "secret": "{webhook_secret}"
  },
  "events": ["pull_request"]
}
Response: { "id":..., ... }
```

**与 GitCode 差异**：GitHub 用 `config:{url,content_type,secret}` 嵌套结构，GitCode 用 `url`/`content_type`/`secret` 平铺字段。

#### 删除 webhook

```
DELETE https://api.github.com/repos/{owner}/{repo}/hooks/{hookId}
Header: Authorization: Bearer {accessToken}, Accept: application/vnd.github+json
Response: 204
```

### 6.4 GitHub 其他接口（第二优先级，本需求不实现但预留）

| 能力 | 接口 |
|------|------|
| token 校验 | `GET https://api.github.com/user` |
| 列出分支 | `GET /repos/{o}/{r}/branches?per_page=100` |
| 列出 PR 文件 | `GET /repos/{o}/{r}/pulls/{n}/files` |
| 列出 collaborators | `GET /repos/{o}/{r}/collaborators` |
| 查询仓库 |  |

### 6.5 GitHub webhook 与 GitCode webhook 对比表

| 维度 | GitCode | Gitee | GitHub | 一致性 | 适配方式 |
|------|---------|-------|--------|--------|---------|
| webhook 路径 | `/hooks/gitcode` | `/hooks/gitee` | `/hooks/github` | 不一致 | 新增端点 |
| 事件头名 | `X-GitCode-Event` | `X-Gitee-Event` | `X-GitHub-Event` | 不一致 | 按 platform 取头 |
| 事件 id 头 | `X-GitCode-Delivery` | `X-Gitee-Delivery` | `X-GitHub-Delivery` | 不一致 | 同上 |
| 签名头 | `X-GitCode-Signature-256` | `X-Gitee-Token` | `X-Hub-Signature-256` | 不一致 | 按 platform 取头 |
| 签名算法 | HMAC SHA256 | token 明文/MD5 | HMAC SHA256 | GitHub=GitCode | `validateSignature` 通用 |
| 签名格式 | `sha256=<hex>` | — | `sha256=<hex>` | GitHub=GitCode | `sign.substring(7)` 通用 |
| PR 事件名 | `Merge Request Hook` | `Merge Request Hook` | `pull_request` | 不一致 | supportedEventTypes 多值 |
| PR action | `open`/`update` | `open`/`update` | `opened`/`synchronize`/`reopened` | 不一致 | extractAction 适配 |
| update 标识 | `update_reason=source update` | `action_desc=source_branch_changed` | `action=synchronize` | 不一致 | isValidSourceUpdateReason 适配 |
| payload 结构 | `object_attributes.iid` | 顶层 `iid` | `pull_request.number` | 不一致 | extractPrInfo 适配 |
| 仓库信息 | `project.namespace`+`repository.git_http_url` | 同 GitCode | `repository.full_name`+`repository.clone_url` | 不一致 | extractPrInfo 适配 |
| commit 信息 | `object_attributes.last_commit.id`+`oldrev` | `pull_request.head_sha` | `pull_request.head.sha`+`before` | 不一致 | extractPushCommitShas 适配 |
| webhook 创建 body | 平铺 `url`/`events` | 平铺 | 嵌套 `config:{url,content_type,secret}`+`events` | 不一致 | createRepoWebhook 适配 |
| webhook secret | `secret` 字段 | `password` 字段 | `config.secret` 嵌套 | 不一致 | 同上 |

**核心结论**：三者 webhook 机制整体相似（事件头路由 + HMAC 签名），但 payload 结构、事件名、action 语义、webhook 设置 body 格式差异较大，需要逐方法适配。GitHub 与 GitCode 的签名机制完全一致（HmacSHA256 + `sha256=` 前缀），签名校验层可复用。

---

## 7. 安全设计

### 7.1 GitHub webhook 签名校验

- webhook secret 由 coderepo 生成（随机 32 字节 base64）
- 创建 webhook 时将 secret 传给 GitHub（`config.secret`），GitHub 用该 secret 对 payload 做 HMAC SHA256 签名，放入 `X-Hub-Signature-256` 头
- coderepo 接收 webhook 时，用本地 secret 对 payload 重新计算 HMAC，与 `X-Hub-Signature-256` 比对
- `MachineInterfaceAuthUtil.validateSignature` 已实现 HmacSHA256，可直接复用，仅需改签名头名

### 7.2 GitHub token 安全存储与使用

- 仓库级 `access_token` 单字段存储，加密方式与项目级一致
- 日志中 token 一律脱敏（现有 `CommonUtil.java:144` 已对 github token 脱敏）
- GitHub token 必须用 `Authorization: Bearer <token>` 头传输，不得出现在 URL query（GitHub 会记录 URL 日志）
- 配置项 `github.common.access_token` 在 apollo 中应加密存储（与 `gitcode.common.access_token` 一致）

### 7.3 防刷屏与防滥用

- codecheck 扫描结果若异常庞大（如 >1000 条），在 `SuppressionCommentBuilder` 中做截断保护，body 中追加"...（截断，共 N 条，仅展示前 1000 条）"