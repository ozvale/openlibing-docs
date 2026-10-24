# 接口层采集设计文档（raw → sdi）

> 用途：面向「链路A 接口拉取」的 5 个指标任务，梳理 **GitCode 接口字段 / 获取逻辑 / raw 落表 / sdi 清洗**，与既有任务 `[job][raw][GitCode]获取gitcode pr评论信息` 保持同一实现范式。
> 覆盖指标：3 分支保护、2 代码评审、14 发布签名、17 贡献者多样性、19 Webhook 安全。
> 目标平台：仅 GitCode（github/gitee 本期不做）。
> 文档中的接口字段、响应结构均来自 GitCode 官方 API 文档（docs.gitcode.com）实测抓取，非臆造。

---

## 0. 全局约束（先读）

- **仓库遍历清单**：`openlibing.sdi_rd_efc_repo_operate_conf` 取 **`is_operate = 1`**（⚠️ 实际列名是 `is_operate`，不是任务清单里写的 `is_operated`）。
- **凭证**：gitcode token 取自 `sdi_project_common_account_info.gitcode_token`，经项目级 `project_id` 关联；SeaTunnel 侧先 `Decrypt` 解密，禁止硬编码、禁止明文落库。
- **落表范式**：与 `[job][raw][GitCode]get_pr_comment` 一致 —— 接口原始 JSON **全量**存 `json_data`（原文保留），另存业务主键字段便于定位。
- **分层**：先落 raw（原文全量），再清洗 sdi（去重 / 布尔标准化 / 机器人识别 / 补 repo_id）。
- 所有新建 raw / sdi 表均带 `repo_id`（关联仓库）与 `etl_time`（采集时间），下游按仓 join。
- 若目标 raw 表已存在，**复用不重建**（如 `raw_pr_comment_gitcode` 已在用，T2 直接复用）。
- 预留指标（7/10/11/15）不产生任何接口采集任务。

---

## 1. 任务总览（本文档范围）

| 任务 | 指标            | GitCode 接口                                                                          | 落 raw 表                          | 清洗 sdi 表                           | 分页            |
| ---- | --------------- | ------------------------------------------------------------------------------------- | ---------------------------------- | ------------------------------------- | --------------- |
| T1a  | 3 分支保护      | `GET /api/v5/repos/{owner}/{repo}/protect_branches`                                   | `raw_repo_branch_protection`(新建) | `sdi_rd_efc_branch_protection`(新建)  | 单次(数组)      |
| T1b  | 3 分支保护      | `GET /api/v5/repos/{owner}/{repo}/pull_request_settings`                              | `raw_repo_pr_setting`(新建)        | `sdi_rd_efc_pr_setting`(新建)         | 单次(对象)      |
| T2   | 2 代码评审      | PR 评论/评审（复用已有采集）                                                          | `raw_pr_comment_gitcode`(复用)     | `sdi_rd_efc_pr_review_reviewer`(新建) | 已含分页        |
| T3   | 14 发布签名     | `GET /api/v5/repos/{owner}/{repo}/releases`                                           | `raw_release`(新建)                | `sdi_rd_efc_release`(新建)            | page 分页       |
| T4   | 17 贡献者多样性 | `GET /api/v5/repos/{owner}/{repo}/contributors` + `GET /api/v5/users/{username}/orgs` | `raw_contrib`(新建)                | `sdi_rd_efc_repo_contributor`(新建)   | 单次(数组)+按人 |
| T5   | 19 Webhook 安全 | `GET /api/v5/repos/{owner}/{repo}/hooks`                                              | `raw_repo_webhook`(新建)           | `sdi_rd_efc_repo_webhook`(新建)       | page 分页       |

---

## 2. 统一源（遍历 SQL，5 个任务共用）

仓库清单以 `sdi_rd_efc_repo_operate_conf(is_operate=1)` 为驱动，join 出 `repo_id / owner / repo / token`：

```sql
SELECT
  cf.repo_id,
  SUBSTRING_INDEX(SUBSTRING_INDEX(cf.repo_url, '/', 4), '/', -1) AS owner,
  SUBSTRING_INDEX(SUBSTRING_INDEX(cf.repo_url, '/', -1), '.', 1) AS repo,
  cf.repo_url,
  acc.gitcode_token AS access_token
FROM sdi_rd_efc_repo_operate_conf cf
JOIN sdi_repo_info info ON info.repo_id = cf.repo_id
JOIN sdi_project_common_account_info acc ON acc.project_id = info.project_id
WHERE cf.is_operate = 1
  AND info.platform = 'gitcode'
```

- 并行分片：为每行生成伪自增 id（`ROW_NUMBER() OVER (ORDER BY cf.repo_id)`），作为 JDBC source `partition_column`；`split.size=500`、`fetch.size=10` 小批量限流，避免下游 HTTP 处理不过来（复刻 `get_pr_comment.conf` 既有设置）。
- 同时带出 `info.project_id`（T1b 的 project_id、T5 的 result 关联用，按需补列）。

---

## 3. 各任务：接口字段 + 获取逻辑 + raw/sdi 设计

> 统一获取范式（SeaTunnel transform 链）：
> `JDBC source(遍历列表) → Decrypt(access_token) → Http(调用 GitCode API，Bearer 鉴权) → JDBC sink(raw 表)`
> Http 配置要点：`method=GET, format=json, headers.Authorization="Bearer ${access_token}"`，`retry=3, connect_timeout_ms=12000, socket_timeout_ms=60000`，`error_handling.strategy="continue"`（仓库失败不影响本批其他仓库）。

---

### 3.1 T1a 分支保护（指标3）

**接口**：`GET https://api.gitcode.com/api/v5/repos/{owner}/{repo}/protect_branches`

- Path 参数：`owner`、`repo`
- 支持鉴权：`access_token`（query）或 `Authorization: Bearer`
- **返回：数组**（该仓库全部保护分支），无独立分页参数（保护分支通常很少，单次拉取）。

**响应 schema（实测）**：数组元素——

```json
{
  "name": "main",
  "updated_at": "2024-09-18T10:15:48.471+08:00",
  "push_users": [],
  "merge_users": [],
  "merged": false,
  "developers_can_push": false,
  "developers_can_merge": false,
  "committer_can_push": false,
  "committer_can_merge": false,
  "master_can_push": true,
  "master_can_merge": true,
  "maintainer_can_push": true,
  "maintainer_can_merge": true,
  "owner_can_push": true,
  "owner_can_merge": true,
  "no_one_can_push": false,
  "no_one_can_merge": false
}
```

**字段与 Excel 规则对照（以评分表为准）**：

| Excel 目标                                              | 接口判定字段                        | 说明                                                                                                                                |
| ------------------------------------------------------- | ----------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------- |
| T₁「阻止删除+强制推送」                                 | `no_one_can_push`                   | ✅ 接口有，**直接取**。Excel 明确：查看默认分支是否保护分支，且 `no_one_can_push==true` 即满足；**不派生 force_push/deletion 字段** |
| (本接口只解决 T₁) T₂/T₃/T₄ 的合并模式/状态检查/审查人数 | 在 T1b `pull_request_settings` 接口 | 拆到 `raw_repo_pr_setting`                                                                                                          |

> 注：实测 schema 里的各角色 `*_can_push/*_can_merge` 属于原始全量，按 `json_data` 原样落库即可，**不作为判级依据（Excel 未引用）**。Excel 对"阻止删除+强制推送"统一用 `no_one_can_push` 判定。

**raw 表 `raw_repo_branch_protection`（新建）**

```sql
CREATE TABLE raw_repo_branch_protection (
  repo_id     INT            COMMENT '仓库ID',
  owner       VARCHAR(36)    COMMENT '仓库所属空间path',
  repo        VARCHAR(36)    COMMENT '仓库路径',
  branch_name VARCHAR(128)   COMMENT '保护分支名',
  json_data   JSON           COMMENT '该保护分支原始JSON全量',
  etl_time    DATETIME       COMMENT '采集时间'
) UNIQUE KEY (repo_id, branch_name) DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

> 落库：对数组逐元素一行：`branch_name = $.name`，`json_data = 该元素`。

**sdi 清洗 `sdi_rd_efc_branch_protection`（新建）**——一仓默认分支一行

```sql
CREATE TABLE sdi_rd_efc_branch_protection (
  repo_id            INT      COMMENT '仓库ID',
  branch_name        VARCHAR(128) COMMENT '默认分支名(来自默认分支口径,见下)',
  is_protected       TINYINT  COMMENT '1=默认分支在保护列表中存在 0=否',
  no_one_can_push    TINYINT  COMMENT '1=阻止删除+强制推送(T₁判据,布尔标准化) 0=否',
  etl_time           DATETIME COMMENT '采集时间'
) UNIQUE KEY (repo_id, branch_name, etl_time) DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

- **默认分支口径**：取 `sdi_repo_branch_info.default_branch`（与指标1 commit 同口径）；若无可回退取 name ∈ `('master','main','trunk')`。
- `is_protected` = 默认分支名是否出现在 protect_branches 数组。
- `no_one_can_push` = 该默认分支对象上的 `no_one_can_push` 布尔标准化。
- 布尔标准化：接口返回 `false/true`，清洗为 `0/1`。

---

### 3.2 T1b PR 设置/合并设置（指标3）

**接口**：`GET https://api.gitcode.com/api/v5/repos/{owner}/{repo}/pull_request_settings`

- **返回：单对象**（非数组，**无分页**）——注意与列表类接口的 transform 差异。
- 顶层直接含判级所需 3 个字段，另嵌套 `merge_request_setting`。

**响应 schema（实测）**：

```json
{
  "merge_request_setting": {
    "id": 1431,
    "project_id": 2745002,
    "can_force_merge": false,
    "disable_squash_merge": true,
    "approval_required_reviewers": 0,
    "approval_required_approvers": 0,
    "approval_required_testers": 0,
    "codeowner_merge_count": true,
    "disable_merge_by_self": false,
    "only_allow_merge_if_all_discussions_are_resolved": false // 注:嵌套关系以顶层为准
  },
  "only_allow_merge_if_all_discussions_are_resolved": false,
  "only_allow_merge_if_pipeline_succeeds": false,
  "merge_method": "merge"
}
```

**判级所需字段（全部直接可得）**：`merge_method`、`only_allow_merge_if_pipeline_succeeds`、`only_allow_merge_if_all_discussions_are_resolved`、`approval_required_approvers`、`approval_required_reviewers`、`codeowner_merge_count`。

**raw 表 `raw_repo_pr_setting`（新建）**

```sql
CREATE TABLE raw_repo_pr_setting (
  repo_id   INT          COMMENT '仓库ID',
  owner     VARCHAR(36)  COMMENT '仓库所属空间path',
  repo      VARCHAR(36)  COMMENT '仓库路径',
  json_data JSON         COMMENT 'pull_request_settings 原始JSON全量',
  etl_time  DATETIME     COMMENT '采集时间'
) UNIQUE KEY (repo_id) DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

**sdi 清洗 `sdi_rd_efc_pr_setting`（新建）**——一仓一行，**只留 Excel 判据字段**（其余按 raw 全量 `json_data` 兜底）

```sql
CREATE TABLE sdi_rd_efc_pr_setting (
  repo_id   INT      COMMENT '仓库ID',
  merge_method VARCHAR(16) COMMENT '合并模式 merge/squash/rebase等(Excel:非merge即满足合并方式)',
  only_allow_merge_if_pipeline_succeeds TINYINT COMMENT '状态检查:流水线通过(T₃判据,布尔标准化)',
  approval_required_approvers INT COMMENT '要求最小审批人数(Excel:>2即≥2审查者,T₄判据)',
  etl_time   DATETIME COMMENT '采集时间'
) UNIQUE KEY (repo_id, etl_time) DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

**指标3 分级判据（Excel G4/H4 原文）**：

| 层级                         | Excel 判据                                                                                                                  | 取自                    |
| ---------------------------- | --------------------------------------------------------------------------------------------------------------------------- | ----------------------- |
| T₁=3 阻止删除+强制推送       | 默认分支是保护分支且 `no_one_can_push==true`                                                                                | `protect_branches`(T1a) |
| T₂=3 PR审查+状态检查前置     | `merge_method != 'merge'`（要求 merge commit/半线性）；"要求最近推送审批"GitCode 默认支持，**Excel 注明 2026-09-10 不扫描** | `pull_request_settings` |
| T₃=2 状态检查通过            | `only_allow_merge_if_pipeline_succeeds=1`                                                                                   | `pull_request_settings` |
| T₄=1 ≥2审查者+CODEOWNERS     | `approval_required_approvers > 2`                                                                                           | `pull_request_settings` |
| T₅=1 取消过期审查+管理员约束 | Excel 未给接口字段                                                                                                          | 本期暂空                |

> ⚠️ 每层需**全部满足**才得该层分，未满足则该层及后续层均 0 分（Excel 明确）。
> ⚠️ Excel 未给出 CODEOWNERS 判定的独立接口字段；接口 `codeowner_merge_count` 是否等价"要求 CODEOWNERS 审查"待规则方确认（不属于采集阻断项）。

---

### 3.3 T2 PR 评审记录（指标2）

**采集来源**：复用既有任务 `[job][raw][GitCode]get_pr_comment` 产出的 **`raw_pr_comment_gitcode`**（本任务不新建接口采集，只做 sdi 清洗）。

**既有表结构（实测，已存在）**：

```
owner(varchar36) | repo(varchar36) | number(int) | comment_id(bigint) | json_data(json) | create_time | update_time
```

- 无 `repo_id`、无 `etl_time`、无作者字段（作者在 `json_data` 内）。清洗时需用 `owner+repo` 关联 `sdi_repo_info` 反查 `repo_id`、用 `create_time` 当采集时间。

**sdi 清洗 `sdi_rd_efc_pr_review_reviewer`（新建）**

```sql
CREATE TABLE sdi_rd_efc_pr_review_reviewer (
  repo_id       INT          COMMENT '仓库ID(由owner+repo反查sdi_repo_info)',
  pr_number     INT          COMMENT 'PR编号(raw_pr_comment_gitcode.number)',
  reviewer_login VARCHAR(128) COMMENT '评论人login(来自json_data.user.login)',
  reviewer_user_id VARCHAR(64) COMMENT '评论人user_id(若有)',
  review_type   VARCHAR(32)  COMMENT '评审命令:/lgtm|/approve|其他(来自json_data.body文本)',
  is_bot        TINYINT      COMMENT '1=名称含bot/robot/[bot] 0=人',
  is_effective_review TINYINT COMMENT '1=非机器人且命令为/lgtm或/approve',
  comment_time  DATETIME     COMMENT '评论时间(json_data.created_at)',
  etl_time      DATETIME     COMMENT '清洗写入时间'
) UNIQUE KEY (repo_id, pr_number, reviewer_login, review_type)
DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

**清洗规则**：

1. **机器人识别**（Excel 明确）：评论人名称含 `bot`（不区分大小写），扩展名单 `robot`、`[bot]` → `is_bot=1`。
2. **有效人工评审**：`is_bot=0` 且 `review_type` ∈ (`/lgtm`,`/approve`) → `is_effective_review=1`。
3. 去重：同一 PR 同一评论人同一命令只保留最早一条（`UNIQUE KEY`）。
4. **产出**：指标2 SQL 侧对每个 PR，存在 `is_effective_review=1` 且 `reviewer_login != PR创建人` 的评审 → 判定「已人工评审」；`PR创建人` 来自 `dwi_rd_efc_pr_info_sum.creator`（最近30次已合入、剔除机器人作者）。
5. `review_type` 解析：`json_data.body` 以 `/` 开头提取命令；大小写归一。

---

### 3.4 T3 Release（指标14）

**接口**：`GET https://api.gitcode.com/api/v5/repos/{owner}/{repo}/releases`

- Query：`page`、`per_page`(≤100 默认20)、`direction`(**必须传 `desc`**，否则默认为升序=旧在前)。
- **返回：数组，支持分页**（实测单仓可 >100 条，需 page 循环）。

**响应 schema（实测）**：

```json
{
  "tag_name": "v1.0.217",
  "target_commitish": "930401b0...",
  "prerelease": false,
  "name": "release1 名称",
  "body": "release1 描述",
  "author": {
    "id": "26593",
    "login": "fenglonghui",
    "name": "龙辉",
    "avatar_url": "...",
    "type": "User"
  },
  "created_at": "2025-01-16T19:58:07+08:00",
  "assets": [
    {
      "browser_download_url": "https://gitcode.com/rust-learning/serde/-/archive/v1.0.217/serde-v1.0.217.tar.gz",
      "name": "serde-v1.0.217.tar.gz"
    }
  ]
}
```

**字段与 Excel 规则对照（差异！）**：

| 清单期望                                   | 接口实际                | 处理                                                |
| ------------------------------------------ | ----------------------- | --------------------------------------------------- |
| `published_at`                             | ❌ 用 `created_at`      | 映射为 published_at                                 |
| `draft`                                    | ❌ 公开列表不含 draft   | 统一视为非 draft（draft 不在 `/releases` 默认结果） |
| `prerelease`                               | ✅ 有 `prerelease(int)` | 标准化 bool                                         |
| `has_sha256_asset` / `has_signature_asset` | ❌ 无该字段             | 由 `assets[].name` 派生（见下）                     |
| `assets_json`                              | ✅ 有 `assets`          | 存原文                                              |

**派生规则**：

- `has_sha256_asset` = 任一 asset 名匹配 `(?i)(\.sha256(\.md5)?|\.sha256sum|\.sha256\.asc)$`。
- `has_signature_asset` = 任一 asset 名匹配 `(?i)(\.signature|\.sig|\.asc|\.pgp|\.gpg|\.minisig|\.pem|\.crt|\.cer)$`。
- **指标14 判级（Excel G14 原文）**：仓库**存在 release** → 判定该（批）release 是否含 sha256 与签名文件；**不存在 release → 不进行分数计算（NA）**。sdi 对每条 release 落 `has_sha256_asset / has_signature_asset` 供计算层聚合；H 列建议记录**最近 5 次 release 版本号**及其满足情况（Excel H14）。
- 说明：采集时保留 `release_status`/`created_at` 便于排序取"最新"，但判级不附加"最新正式发布才算"的口径（那是 Excel 之外的解释）。

**raw 表 `raw_release`（新建）**

```sql
CREATE TABLE raw_release (
  repo_id   INT          COMMENT '仓库ID',
  owner     VARCHAR(36)  COMMENT '仓库所属空间path',
  repo      VARCHAR(36)  COMMENT '仓库路径',
  release_tag VARCHAR(128) COMMENT 'release tag(定位键)',
  json_data JSON         COMMENT '单个release原始JSON全量',
  etl_time  DATETIME     COMMENT '采集时间'
) UNIQUE KEY (repo_id, release_tag) DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

**sdi 清洗 `sdi_rd_efc_release`（新建）**——一仓按 release 多行，原 tag 唯一：

```sql
CREATE TABLE sdi_rd_efc_release (
  repo_id       INT          COMMENT '仓库ID',
  release_tag   VARCHAR(128) COMMENT 'tag_name',
  release_name  VARCHAR(255) COMMENT 'release名称',
  published_at  DATETIME     COMMENT '发布时间(取created_at)',
  prerelease    TINYINT      COMMENT '1=预发布 0=正式发布',
  target_commitish VARCHAR(64) COMMENT '发布对应commit',
  author_login  VARCHAR(128) COMMENT '发布人login',
  assets_json   JSON         COMMENT '资产明细[{name,browser_download_url}]原文',
  has_sha256_asset    TINYINT COMMENT '1=含sha256校验资产(按名派生)',
  has_signature_asset TINYINT COMMENT '1=含签名资产(按名派生)',
  etl_time      DATETIME     COMMENT '清洗写入时间'
) UNIQUE KEY (repo_id, release_tag, etl_time) DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

**✅ 实时实测结论（2026-09-14，token + 20 仓扫描核验）**

| #   | 实测发现                                                                                                                                                             | 设计落地                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------- |
| 1   | **默认排序=升序（旧在前）**；显式传 `direction=desc` 才按新→旧返回                                                                                                   | HTTP params 必须带 `direction=desc`；sdi 仍按 `created_at` 取最新兜底（顺序无关）                         |
| 2   | **分页真实存在**：某仓 page1 满 100，page2 仍有数据                                                                                                                  | 保留 `page=1..N + per_page=100` 循环，until 空页终止                                                      |
| 3   | `prerelease` 对 rc/beta tag 返回 **`False`**（不标记预发布）                                                                                                         | 采集全量 release，不做「非 prerelease」二次过滤（`/releases` 列表本身不含 draft）                         |
| 4   | sha256 真实命名为 **`xxx.tar.gz.sha256sum`**，正则 `.sha256sum` 可命中                                                                                               | `has_sha256_asset` 正则保留                                                                               |
| 5   | 20 仓中**无一含签名资产**（`.asc/.sig/.pem/...`），多数仓无 release，个别仓返回 **404**（private/更名）                                                              | 404 → 该仓记录空/NULL，**continue 跳过不失败本批**；签名判定会致大部分仓 0/NA，属规则覆盖面问题需业务确认 |
| 6   | 返回字段实测含 `tag_name / name / body / author / prererlease / created_at / target_commitish / assets[{name,browser_download_url}]`，**无 draft / 无 published_at** | 映射一致                                                                                                  |

---

### 3.5 T4 贡献者（指标17）

**接口①**：`GET https://api.gitcode.com/api/v5/repos/{owner}/{repo}/contributors`

- Query 可选 `type`（committers/authors）。返回数组，无独立分页参数（单次拉全量）。
- **响应 schema（实测）：仅 `name / contributions / email`** —— ⚠️ **无 user_id、无 org/company 字段**。

```json
[{ "name": "dengmengmian", "contributions": 3, "email": "my@dengmengmian.com" }]
```

**接口②**：`GET https://api.gitcode.com/api/v5/users/{username}/orgs`（取每个贡献者所属组织）

- `username` 取接口①的 `name`（实测 `name` 即登录名）。
- **响应 schema（实测）**：数组，元素含 `id / login / path / name / description / avatar_url`。一个用户可属多个组织（wordplace 实测 LJPeng 属 TTFHVV、openlibing 两个组织）。

```json
[
  {
    "id": 12952309,
    "login": "TTFHVV",
    "path": "TTFHVV",
    "name": "TTFHW",
    "description": "",
    "avatar_url": "..."
  }
]
```

**获取逻辑（两跳）**：

1. 遍历仓库列表 → 调 contributors 取贡献者姓名列表。
2. 对每个贡献者 `name` → 调 `/users/{name}/orgs`，把其所属组织并入本仓该贡献者的组织集合。

> ⚠️ 复杂度提示：贡献者×org 是「仓库→人→组织」两段 HTTP，调用量=仓库数×贡献者数。需评估限流/缓存；可将同一用户多次出现的 org 结果先按 login 缓存一次全仓再展开。

**raw 表 `raw_contrib`（新建）**

```sql
CREATE TABLE raw_contrib (
  repo_id    INT          COMMENT '仓库ID',
  owner      VARCHAR(36)  COMMENT '仓库所属空间path',
  repo       VARCHAR(36)  COMMENT '仓库路径',
  user_login VARCHAR(128) COMMENT '贡献者login(=contributors.name)',
  json_data  JSON         COMMENT '贡献者行JSON(或组织原始JSON,按采集粒度定)',
  etl_time   DATETIME     COMMENT '采集时间'
) UNIQUE KEY (repo_id, user_login) DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

**sdi 清洗 `sdi_rd_efc_repo_contributor`（新建）**——(人×组织) 多行：

```sql
CREATE TABLE sdi_rd_efc_repo_contributor (
  repo_id            INT          COMMENT '仓库ID',
  user_login         VARCHAR(128) COMMENT '贡献者login',
  user_email         VARCHAR(255) COMMENT '贡献者email(若有)',
  contributions_count INT         COMMENT '贡献次数',
  org_login          VARCHAR(128) COMMENT '所属组织login(来自users/orgs),非组织成员可空',
  org_name           VARCHAR(255) COMMENT '所属组织名称',
  etl_time           DATETIME     COMMENT '清洗写入时间'
) UNIQUE KEY (repo_id, user_login, org_login) DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

**指标17 判级**：Excel G17 仅要求"扫描仓库贡献者所属的组织等"，**未给打分阈值**。本设计暂按任务清单口径：该仓贡献者所属**组织集合去重后数量 ≥3 → 10 分**（组织键 `org_login`，`org_login=NULL` 不计入多样性）。⚠️ 阈值"≥3→10"为清单补充，**需规则方确认是否与 Excel 后续版本一致**。

---

### 3.6 T5 Webhook（指标19）

**接口**：`GET https://api.gitcode.com/api/v5/repos/{owner}/{repo}/hooks`

- Query：`page`、`per_page`(≤100 默认20)。返回数组，分页。
- **响应 schema（实测）**：

```json
{
  "id": 78043,
  "url": "https://www.openlibing.com/repo",
  "password": "132",
  "result": null,
  "project_id": 9357123,
  "result_code": 0,
  "push_events": true,
  "tag_push_events": false,
  "issues_events": true,
  "note_events": false,
  "merge_requests_events": true,
  "created_at": "2026-09-14T11:45:34+08:00",
  "active": true
}
```

**字段与 Excel 规则对照（实测，wordplace 实锤 ✅）**：

| 清单期望                              | 接口实际                      | 处理                                                      |
| ------------------------------------- | ----------------------------- | --------------------------------------------------------- |
| `active`(激活状态)                    | ✅ **有 `active` 布尔字段**   | **直接取**（无需派生，之前误判）                          |
| `config_password`                     | ✅ 有 `password` **明文**返回 | 用于 `password_is_null` 判定，**落库前必须脱敏/不落明文** |
| `config_url`                          | ✅ 有 `url`                   | 取                                                        |
| `config_events`                       | ✅ 各 `*_events` 布尔         | 存事件位集合                                              |
| `active==true 且 password 非空才安全` | —                             | `active` 直接取，`password` 脱敏为 `password_is_null`     |

**实测结论**：Wordplace 上真实 hook 对象含 `active` 布尔，直接决定活跃态；`result_code` 记录最近投递结果供复核（非活跃判定依据）。

**raw 表 `raw_repo_webhook`（新建）**（⚠️ `password` 明文不落库）

```sql
CREATE TABLE raw_repo_webhook (
  repo_id    INT          COMMENT '仓库ID',
  owner      VARCHAR(36)  COMMENT '仓库所属空间path',
  repo       VARCHAR(36)  COMMENT '仓库路径',
  webhook_id INT          COMMENT 'webhook id(定位键)',
  password_is_null TINYINT COMMENT '1=password为空/未配置secret 0=非空(勿落明文password)',
  json_data  JSON         COMMENT '除password外的webhook原始JSON全量(脱敏)',
  etl_time   DATETIME     COMMENT '采集时间'
) UNIQUE KEY (repo_id, webhook_id) DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

**sdi 清洗 `sdi_rd_efc_repo_webhook`（新建）**——一钩一行：

```sql
CREATE TABLE sdi_rd_efc_repo_webhook (
  repo_id    INT          COMMENT '仓库ID',
  webhook_id INT          COMMENT 'webhook id',
  webhook_url VARCHAR(512) COMMENT '回调url',
  is_active  TINYINT      COMMENT '1=活跃(接口直接返回 active)',
  password_is_null TINYINT COMMENT '1=password为空/未配置secret(0=非空)',
  event_flags_json JSON   COMMENT '事件位集合{push_events,issues_events,...}',
  result_code INT         COMMENT '最近投递结果码(复核用)',
  created_at DATETIME     COMMENT '创建时间',
  etl_time   DATETIME     COMMENT '清洗写入时间'
) UNIQUE KEY (repo_id, webhook_id, etl_time) DISTRIBUTED BY HASH(repo_id) BUCKETS 8;
```

**指标19 判级**：以 **激活状态（`active=true`）的 webhook** 为对象，判断其 **`password` 是否为空/`""`**（Excel G19 唯一判据）。采集侧产出 `is_active + password_is_null`；打分层级（无活跃→NA、均有 secret→10、部分缺 secret→按占比扣减）为清单补充口径，供计算层使用。

---

## 4. 一次性链路接入注意点（SeaTunnel）

| 端点                  | 响应形态   | 分页 | data_json 落法                                  |
| --------------------- | ---------- | ---- | ----------------------------------------------- |
| protect_branches      | 数组       | 无   | 逐元素一行，json_data=元素                      |
| pull_request_settings | **单对象** | 无   | 一仓一行，json_data=整个对象                    |
| releases              | 数组       | page | 逐元素一行，json_data=元素                      |
| contributors          | 数组       | 无   | 逐人一行，json_data=元素（组织另任务/二次调用） |
| hooks                 | 数组       | page | 逐钩一行，json_data=脱敏后元素                  |

- **单对象端点**（pull_request_settings）不能套用数组分页的 `page_type=PageNumber`，需单独配置为「一次调用取整体」，json_data 映射根对象。
- 参考任务把 `json_data="$"` 存成整页数组——若题库要求逐行，改为 `${[].name}` 展开；本文档按「逐业务键一行」设计，与参考任务精神一致且便于 sdi 清洗。
- 所有列表类端点复用 `per_page=100` + `PageNumber` 分页 + `error_handling.continue`（仓库级失败跳过，不影响本批）。

---

## 5. DolphinScheduler 编排（新增任务节点）

```
security_check_scoring
├─ 01 接口拉取层(每日)
│   ├ task_repo_branch_protection → raw_repo_branch_protection
│   ├ task_repo_pr_setting        → raw_repo_pr_setting
│   ├ task_repo_contributors      → raw_contrib
│   ├ task_repo_release           → raw_release
│   └ task_repo_webhook           → raw_repo_webhook
└─ 02 清洗 sdi(依赖01)
    ├ sdi_rd_efc_pr_review_reviewer      (raw_pr_comment_gitcode→评审人/机器人)
    ├ sdi_rd_efc_branch_protection / sdi_rd_efc_pr_setting
    ├ sdi_rd_efc_release / sdi_rd_efc_repo_contributor / sdi_rd_efc_repo_webhook
```

> 复用既有 `raw_pr_comment_gitcode`、`[job][raw][GitCode]get_pr_comment`，不重建。
> 幂等：所有 raw/sdi 以 `repo_id + 业务键(+ etl_time)` 唯一，按批次覆盖本批，多批次历史保留（sdi 层保留历史批次）。

---

## 6. 待确认 / 风险项（实现前需澄清）

| #   | 项                                                       | 说明                                                                                                                                                                                          | 责任方     |
| --- | -------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------- |
| R1  | 仓库清单列名                                             | 任务清单写 `is_operated`，库表实测为 **`is_operate`** → 用 `is_operate=1`                                                                                                                     | ——         |
| R2  | 分支保护分级字段                                         | ✅ 已改齐：Excel 判据只用 `no_one_can_push`(T₁)+`merge_method`(T₂)+`only_allow_merge_if_pipeline_succeeds`(T₃)+`approval_required_approvers>2`(T₄)，清理此前臆断的 `force_push/deletion` 字段 | lihongfeng |
| R3  | `codeowner_merge_count` 是否等价「要求 CODEOWNERS 审查」 | 只能取到该布尔，无法区分审查者是否含 CODEOWNERS 成员                                                                                                                                          | lihongfeng |
| R4  | ~~webhook `active` 派生口径~~                            | ✅ 已解决：wordplace 实测 hooks 返回 `active` **布尔字段，直接取**，无需派生                                                                                                                  | ——         |
| R5  | webhook `password` 明文                                  | 接口回明文 password，**落库必须脱敏为 password_is_null 布尔**，勿存明文                                                                                                                       | ——         |
| R6  | contributors 无 org 字段                                 | 需二次调 `/users/{name}/orgs`，且 `name` 即 login 的假设需验证；调用量=人×仓，需限流缓存                                                                                                      | ——         |
| R7  | releases 无 draft 字段                                   | ✅ 已实测确认无 draft；sha256 正则 `.sha256sum` 已对真实命名验证命中；**签名资产判定需业务确认**（20 仓实测无签名资产，将致该指标大多 0/NA）                                                  | 业务方     |
| R8  | raw_pr_comment_gitcode 无 repo_id/etl_time               | 清洗时用 owner+repo 反查 `sdi_repo_info` 补 repo_id                                                                                                                                           | ——         |

---

## 7. 验收要点

1. 5 个接口任务均按 `is_operate=1` 清单遍历，raw → sdi 落表成功。
2. `sdi_rd_efc_pr_review_reviewer` 按「名称含 bot」标记机器人，得到「已人工评审」PR 集合，与最近30次已合入PR口径一致。
3. `sdi_rd_efc_pr_setting` 能输出 `merge_method / only_allow_merge_if_pipeline_succeeds / approval_required_approvers`，供指标3 五层阶梯。
4. `sdi_rd_efc_release` 对每条 release 落 `has_sha256_asset / has_signature_asset`（无 release → 指标14 判 NA）。
5. `sdi_rd_efc_repo_webhook` 不落 password 明文，能区分活跃 webhook 与 secret 配置。
6. `sdi_rd_efc_repo_contributor` 组织去重数正确，指标17 判定 ≥3（阈值待规则方确认）。
7. 接口任务失败不影响预留指标（7/10/11/15）；重跑幂等、多批次历史保留。

---

## 8. 接口字段对账表（Excel/清单字段 ↔ 接口真实字段，实测核验）

> 结论：字段差异的根因是 **Excel/清单的 raw 列混入了"重命名字段"和"派生计算字段"**，接口原始返回并不含这些。下表逐个给出判定。

### 8.1 核验状态说明

| 接口                         | 实测方式                                   | 核验状态                                                       |
| ---------------------------- | ------------------------------------------ | -------------------------------------------------------------- |
| `releases`                   | 真实 token + 多仓 dump 全量 JSON           | ✅ 200，字段实锤                                               |
| `pull_request_settings`      | 真实 token + `cann/asnumpy` dump 全量 JSON | ✅ 200，字段实锤                                               |
| `hooks` / `protect_branches` | 真实 token + `LJPeng/wordplace`(admin)     | ✅ 200 + 实数据实锤（wordplace 配了 webhook + 保护 main 分支） |
| 全部 5 端点的路径            | wordplace 确认 admin 可访问（200）         | ✅ endpoint 正确；此前操作仓 403 = token 无 admin，非接口错    |

### 8.2 逐字段对账

**releases（指标14）—— ✅ 实测一致**

| Excel/清单字段                             | 接口真实字段                               | 判定                                                         |
| ------------------------------------------ | ------------------------------------------ | ------------------------------------------------------------ |
| `release_tag`                              | `tag_name`                                 | ✅ 改名直接取                                                |
| `release_name`                             | `name`                                     | ✅ 直接取                                                    |
| `published_at`                             | `created_at`                               | ⚠️ 接口无 `published_at`，**映射到 `created_at`**            |
| `draft`                                    | 无                                         | ❌ 公开 `/releases` 列表不含 draft，默认非 draft             |
| `prerelease`                               | `prerelease`                               | ✅ 直接取（但实测 rc/beta 也返回 False，别依赖它筛正式发布） |
| `assets_json`                              | `assets[{name,browser_download_url,type}]` | ✅ 直接取（含 `type=source/binary`）                         |
| `has_sha256_asset` / `has_signature_asset` | 无                                         | ❌ **派生**：按 `assets[].name` 正则                         |
| 新增                                       | `release_status:"latest"`                  | 可选：辅助定位最新发布                                       |

**pull_request_settings（指标3）—— ✅ 实测一致（Excel 判据字段全命中）**

| Excel 判据字段                                 | 接口真实字段                                                                                 | 判定                                                             |
| ---------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------- |
| `merge_method`（非 merge 即满足合并方式）      | `merge_method`（实例如 `rebase_merge`/`merge`）                                              | ✅ 直接取                                                        |
| `only_allow_merge_if_pipeline_succeeds`        | `only_allow_merge_if_pipeline_succeeds`                                                      | ✅ 直接取                                                        |
| `approval_required_approvers`（>2 = ≥2审查者） | `merge_request_setting.approval_required_approvers`                                          | ✅ 直接取（嵌套）                                                |
| ~~清单补充字段~~                               | `can_force_merge`/`codeowner_merge_count`/`only_allow_merge_if_all_discussions_are_resolved` | 原始 schema 字段，raw 全量保留，**不作判级依据（Excel 未引用）** |

**protect_branches（指标3）—— ✅ 实测一致（wordplace 保护 main）**

| Excel 判据           | 接口真实字段                                                           | 判定                                       |
| -------------------- | ---------------------------------------------------------------------- | ------------------------------------------ |
| T₁ 阻止删除+强制推送 | `no_one_can_push`                                                      | ✅ 直接取，**单字段判定**（Excel 明确）    |
| ~~原始全量~~         | `name/updated_at/*_can_push/*_can_merge/push_users/merge_users/merged` | raw `json_data` 全量保留，**不作判级依据** |

**hooks（指标19）—— ✅ 实测一致（wordplace 配了 webhook）**

| Excel 判据             | 接口真实字段                                               | 判定                                      |
| ---------------------- | ---------------------------------------------------------- | ----------------------------------------- |
| 激活状态               | `active` 布尔（`"active":true`）                           | ✅ **直接取**（此前误判需派生）           |
| password 是否为空/`""` | `password`（明文返回）                                     | ⚠️ **脱敏，只落 `password_is_null` 布尔** |
| ~~原始全量~~           | `url/id/result/result_code/project_id/*_events/created_at` | raw `json_data` 全量保留，供复核          |

### 8.3 遗留待确认

- **指标3 分级口径**：T 层分级按 Excel G4/H4；"要求最近推送审批"已按 Excel 注明**不扫描**（2026-09-10）。CODEOWNERS 无独立接口字段，是否用 `codeowner_merge_count` 判定待规则方确认（不阻断采集）。
- **指标17 组织去重≥3→10 阈值**：非 Excel 原文，需规则方确认。
- **指标14 签名资产判定**：20+ 仓实测无签名资产，规则覆盖面上大概率全员 0/NA，需业务确认（GitCode 是否有 release 签名机制）。
- **指标19 打分层级（NA/扣减占比）**：为清单补充口径，Excel 仅给定"激活+password 判空"，供计算层落地。
