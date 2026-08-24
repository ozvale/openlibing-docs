# 代码仓管理与需求解耦 + SIG 组一键批量录入（需求设计文档）

> 配套：[feature-spec.md](./feature-spec.md)（特性规格：版本变化点 / 页面原型 / 权限 / 验收）；[demo.html](./demo.html)（页面原型）。
>
> **核心结论（本文档唯一基线）**：经与 SCA 确认，其扫描按 `(project_id, repo_url)` 反查 `repo_info`、查不到即报错；且同一代码仓被多项目扫描是真实场景（存量 53 个共享仓）。因此 **`repo_info` 保持「一项目一行、多行并存」的现状模型，本期不拆分、不归并**。配置单一来源通过「**主仓配置同步**」实现（主仓行配置为准，变更同步覆盖同 `repo_url` 组内其他行），使下游 7 仓（codecheck/cicd/framework/anti-poison/sca/gateway/vulnerability）**零改动**。真正「全局唯一单行 + 关联表」留作 Phase 2 远期目标，待下游仓可控后再引入（见 §2.6）。

## 1. 方案设计

### 1.1 问题域

> 痛点明细（配置漂移 / 重复录入 / 缺批量录入 / 跨项目不可见）见 [feature-spec.md](./feature-spec.md) §1.2，本文不重复。核心矛盾：同一代码仓被多项目各自录入维护导致配置漂移；且 SCA 等下游按 `(project_id, repo_url)` 反查 `repo_info`，要求每项目必须存在独立行。

### 1.2 核心方案（保留多行 + 主仓配置同步）

**模型不拆分，配置靠同步收敛**：

1. **repo_info 保持一项目一行**：同一 `repo_url` 可跨项目多行并存（现状模型不动）。7 个下游仓按 `(project_id, repo_url)` 反查每行都命中，**零改动**。
2. **新增主仓标记**：`repo_info.is_main_repo`，同一 `repo_url` 组内**有且仅有一个主仓行**（默认=最早录入行，可迁移）。主仓行 = 该组配置的**权威来源**（配置单一来源）+ 后续归并时的保留行。
3. **配置同步（单一来源）**：主仓行配置变更 → **同步覆盖同组所有行**（副仓行）。任一项目编辑/录入该组仓库，最终全组配置一致，消除漂移。
4. **新录入不产生重复漂移**：仓库已在其他项目存在（组内有主仓行）→ 当前项目**新建一行**并**复制主仓配置**（而非重新手填），前端提示「该仓库主仓在项目 X，配置已同步」。
5. **查重约束**：`(repo_url, project_id)` 唯一（一项目一行），不做 `repo_url` 全局唯一。

> **为什么不做 repo_info 单行化（对比原方案）**：原方案把项目关联拆到 `repo_project_ref`、repo_info 全局唯一单行，副仓项目无行 → SCA 等下游按 `(project_id, repo_url)` 反查不到即报错，且用户无法感知需要指定新主仓；「同一仓库被多项目扫描」也无法支撑。方案 A 让每个项目都有可扫描的行，彻底规避该冲突，且下游 7 仓完全零改动。

### 1.3 改造边界（重要）

- 本次改造**仅涉及 `repo_info` 表**（新增 `source` / `is_participate_operation` / `is_main_repo` 等字段）与 `project_repo_global_config`（全局配置表泛化）。
- 代码仓相关配置表还包括 `codecheck` 下的 Mongo 表（如 `sig_rule_set` 规则集表），**本次不改动**——仍允许不同项目对同一代码仓存在不同配置（规则集、告警抑制等项仍按各项目在 codecheck 侧各自配置，不在本期收敛范围内）。
- **不新建 `repo_project_ref` 表**；不归并存量多行；不删 `project_id`（每行 `project_id` 语义=该行所属项目，与现状一致）。

### 1.4 关键决策汇总

| 决策点 | 选择 | 理由 |
|--------|------|------|
| repo_info 数据模型 | **保持一项目一行、多行并存**；每行 `project_id`=该行所属项目，语义与现状一致 | SCA 等 7 仓按 `(project_id, repo_url)` 反查每行命中、零改动；多项目扫描共享仓为真实场景 |
| 配置单一来源 | 通过**主仓配置同步**实现：`is_main_repo` 标记主仓行，主仓配置变更同步覆盖同 `repo_url` 组所有行 | 不删行、不迁移子表，7 仓零改动的前提下收敛配置漂移 |
| 主仓标记 | `repo_info.is_main_repo`（TINYINT，组内恰一行=1）；首录行即主仓，可迁移 | 每行自身携带归属标记，无需新增关联表 |
| 主仓语义 | 主仓行=组内配置权威源 + Phase 2 归并保留行；**所有项目行均参与下游扫描/检查**（无「副仓不可见」概念） | 与 SCA 反查方式兼容；迁移主仓即切换配置基准与归并保留行 |
| 查重 | `(repo_url, project_id)` 唯一（一项目一行）；不做 repo_url 全局唯一 | 保证同项目不重复录入；不同项目各自建行以支撑各自扫描 |
| 组 key | 直接用 `repo_url`（录入已保证协议/https/平台/`.git` 结尾格式统一，无需额外归一化字段）；repo_url 加普通索引用于组查询 | 用于「同 repo_url 组」判定（主仓同步、录入检测、列表去重） |
| source | `repo_info.source`（manual/sig）标记配置来源；**来源链接不冗余到行级**，SIG 仓库按项目从 `config_json[platform].sigInfoLocation` 实时读取 | SIG 与手动互不覆盖、无优先级判定场景，无需额外表/字段记录来源 |
| 跨项目录入 | 仓库已在其他项目存在 → 当前项目**新建一行**并复制主仓配置；不删除其他项目行 | SCA 兼容 + 避免重复手填；配置靠同步保持全组一致 |
| 选择性删除 | 手动录入/编辑时可勾选「删除之前项目的关联」=删除其他项目对应行 | 支持用户回收误关联；删除主仓行需先迁移主仓（§2.4） |
| 下游仓改造 | **7 仓零改动**（framework 亦无需副仓拦截改造） | 多行模型下每项目都有行，权限/归属按行内 project_id 语义与现状一致 |
| 全局配置 | `project_gitcode_role_mapping` 泛化为 `project_repo_global_config`（config_json 按平台分键） | 集中管理公共账号 / sig-info 位置 / 角色映射，见 §4.2 |
| SIG 配置读取 | 实时调对应平台读取指定位置 sig-info.yaml 并解析；**去除 webhook / 入库缓存** | 保证读到最新配置，简化链路 |
| 历史迁移 | **Phase 1**：清洗同项目重复行（按 repo_url）+ 标记主仓 + 加 `(repo_url, project_id)` 唯一索引；**Phase 2**（远期，7 仓可控后）：再评估全局唯一单行 + 关联表 | 本期不归并、不删行，7 仓零影响；远期归并依赖下游仓配合 |
| 改造边界 | 仅 repo_info + project_repo_global_config；codecheck Mongo（sig_rule_set）等不改 | 规则集等按各项目在 codecheck 侧各自配置，不在本期收敛范围 |
| YAML 解析安全 | SnakeYAML `SafeConstructor` | 防 YAML 反序列化攻击 |
| accessToken 传递 | 调平台 API 时 `Authorization: Bearer <token>` header | 遵循项目硬约束「第三方 API 调用 accessToken 必须在 header」 |

## 2. 实现逻辑设计

### 2.1 手动录入逻辑

> **核心变化**：输入 `repo_url` blur 即调检测接口；命中其他项目已录入（同组多行）时自动复制**主仓配置**进表单（可修改），展示「主仓设置」与「选择性删除其他项目行」；提交时当前项目**新建/更新本行**，并可选删除其他项目行。

```
addRepoInfo(userId, userName, projectId, RepoDTO, deleteProjectIds):
  1. 组 key = repo_url（原样，录入已保证格式统一）
  2. 查该组现有行（repo_info where repo_url=? and is_deleted=0）
  3. 未命中（全局首次录入）：
     - insert repo_info（source=manual, is_main_repo=1, 配置取 RepoDTO）  // 首录行即主仓
     - 同步平台元数据 + 配置 webhook（沿用现有 syncRepoInfo / autoSetWebHook）
  4. 命中（该 repo_url 已在其他项目存在）：
     - 前端 blur 已调 checkRepoUrl：返回 mainRepoProjectId（当前主仓）与 associatedProjects
     - 前端默认把主仓配置同步进表单（可修改），展示「主仓设置」与「删除其他项目行」多选
     - 当前项目已存在本行 → update 本行配置（以表单为准，主仓行变更将同步全组）
     - 当前项目无本行 → insert 本行（is_main_repo=0，配置=主仓配置副本 / 用户修改后的表单值）
     - 可选「设为本项目为主仓」：is_main_repo 迁移到本行，并以本行配置为基准同步全组（§2.5）
  5. deleteProjectIds 非空 → 逐个删除其他项目对应行（§2.4；含主仓行时需先迁移主仓）
  6. 同步全组配置：若本行是主仓（is_main_repo=1）→ 以其配置为基准 update 组内其余行（§2.5）
  7. 返回 repoId
```

> **过渡期存量 53 个共享仓**（同 repo_url 多行、各项目配置可能不同）：检测返回各关联项目及其配置；编辑/录入按 §2.3/§2.5 以主仓配置为基准同步全组，逐步收敛存量漂移（不删行、不归并）。

### 2.2 SIG 组一键录入逻辑

#### 2.2.1 sig-info.yaml 位置配置（全局配置弹窗，每平台唯一链接）

- 用户在「全局配置」弹窗按平台（gitcode/gitee/github）维护**一个** sig-info.yaml **完整链接**（形如 `https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private/sig-info.yaml`），存 `project_repo_global_config.config_json[platform].sigInfoLocation`。
- 保存时解析链接为 owner/repo/branch/path 并实时校验文件可用性（OK / FILE_NOT_FOUND / PARSE_ERROR，不阻断保存）。

#### 2.2.2 sig-info.yaml 文件格式（固定）

```yaml
# sig-info.yaml —— SIG 组代码仓清单（固定格式）
repositories:
  - repo:            # 可存在多个不同的 repo 分组
      - openlibing/community
      - openlibing/openlibing-web
  - repo:
      - openlibing/anti-poison
      - openlibing/coderepo
```

解析规则：顶层 `repositories` 必填（列表）；列表项 `- repo:` 值为该组代码仓清单（`owner/repo` 字符串列表）。**不含任何录入参数**（录入参数全部用默认值或用户编辑）。每个 `owner/repo` 按位置所属平台组装完整 repoUrl。重复项跨分组去重。

#### 2.2.3 仓库清单（实时解析，仅未录入当前项目的仓库）

```
listSigReposInConfig(userId, projectId, platform):
  1. 从 config_json 取该平台位置（校验属于该项目且平台一致）
  2. 实时调对应平台 getFileContent 读 sig-info.yaml → 解析 repositories → List<{owner, repo}>
  3. 过滤：仅保留 (repo_url, projectId) 尚无行的仓库（已录入当前项目的不展示，避免覆盖）
  4. 组装完整 repoUrl + 默认参数（别名/默认分支/责任人/开源类型/是否参与运营/各开关，见 §2.2.4）
  5. 返回 [{ owner, repo, repoUrl, platform, defaultConfig }]
```

#### 2.2.4 一键录入（默认参数或用户编辑配置）

**默认参数**（sig-info.yaml 不配置，全部用默认值，用户可在表格单条/批量编辑）：

| 字段 | 默认值 | 说明 |
|------|--------|------|
| 代码仓别名 | 先用 repo 名；当前项目已存在同名 → `repo名-平台名` 递增 | 当前项目内查重 |
| 默认分支 | 平台仓库默认分支（调仓库详情接口实时获取） | 可编辑 |
| 仓库责任人 | 该代码仓建仓人账号名（实时获取） | 可编辑 |
| 开源类型 / 用途 | 主导开源 / 自研源码 | 可编辑 |
| 是否参与运营 | 是 | 可编辑 |
| 接管 PR / 自动触发门禁 / 接口扫描 / 代码风格修复 / 告警抑制 | 否 | 可编辑 |
| 公共账号令牌 | 不填 | 沿用项目公共账号 |
| 仓库规则集配置 | 不配置 | — |

```
sigImport(userId, userName, projectId, platform, repoConfigs):
  1. 取该平台位置 → 实时读 sig-info.yaml → 解析 repositories
     → 校验每个 repoConfigs[].repoUrl 均在解析结果中（防伪造/过期数据）且当前项目无该行
  2. 事务内对每个仓库：
     a. 查该组现有行（repo_url）
     b. 未命中（全局首次）→ insert 本行（source=sig, is_main_repo=1, 配置取 config）
     c. 命中（其他项目已存在，主仓行在别处）→ insert 本行（source=sig, is_main_repo=0,
        配置=主仓配置副本——复用现有配置不覆盖，保持全组一致）
     d. 若本行为主仓 → 以本行配置同步全组（§2.5）
  3. 异步同步平台元数据 + 配置 webhook（不阻塞录入）
  4. 返回 { imported: N, failed: [...] }
```

> **SIG 同步已去除**：不再提供「SIG 同步」按钮与 sync 接口——配置以主仓为准、变更自动同步全组，需要调整配置直接编辑即可（SIG 来源仓库同样允许编辑）。

### 2.3 编辑逻辑（主仓设置 + 同步全组）

> **核心变化**：不做 SIG 来源编辑拦截（SIG 来源仓库同样允许手动编辑）；不做多项目影响 confirm（现状模型每行独立，天然无需确认）。编辑保存时若本行是主仓 → 以本行配置为基准**同步全组**；若本行是副仓且用户勾选「设为本项目为主仓」→ 主仓迁移到本行后同步全组。

```
updateRepoInfo(userId, userName, projectId, repoId, RepoDTO, setMainRepo?):
  1. 查本行（repo_id）→ 组 key = repo_url
  2. update 本行配置
  3. 若 setMainRepo=true → is_main_repo 置 1（原主仓行置 0），以本行配置为基准同步全组
  4. 若本行已是主仓 → 以本行配置为基准 update 组内其余行（副仓行，保持全组一致）
  5. 同步平台元数据 + webhook（沿用现有逻辑）
```

> **前端提示**：打开编辑时若该 repo_url 已在多个项目录入（组内多行、配置可能不同），展示蓝色提示条：「该代码仓已在多个项目录入，配置以主仓（项目 X）为准，保存后将以主仓配置同步各项目，保证一致。」并提供「设为本项目为主仓」操作（迁移主仓，前端强提示：迁移后配置以本项目为基准同步全组）。

### 2.4 删除逻辑（按行删除 + 主仓迁移）

> **现状说明**：删除接口为 `deleteRepoInfo` / `batchDeleteRepoInfo`（`POST /project-repo/delete-repo` / `batch-delete-repo`），按 `id`（repo_id）物理删除，并清理 `repo_branch` / `user_role` / `field_and_repo` / Mongo `sig_rule_set`、通知 codecheck 重算 is_used；不清理 webhook。本期**保持物理删除与子表清理现状**，仅增加 `projectId` 入参并处理主仓行。

```
deleteRepoInfo(userId, userName, repoId, projectId):
  1. 校验请求 projectId == 本行 project_id（越权沿用现有 verifyPermissionsByProduct）
  2. 若本行 is_main_repo=1 且组内还有其他行 → 拒绝或要求先迁移主仓（提示：请先指定新主仓，
     可调用 set-main-repo 迁移后再删除；或勾选连带删除全组）
  3. 删除本行（物理删除）+ 保留现有子表清理链路（repo_branch/user_role/field_and_repo/sig_rule_set
     + 通知 codecheck 重算 is_used；webhook 现状不清理）
  4. 其他项目行不受影响（各项目行独立）
```

```
batchDeleteRepoInfo(userId, userName, repoIds, projectId):
  - 复用单删语义；批量删除前先校验其中主仓行：存在主仓行且组内非仅剩本行时，要求先迁移主仓
  - 前端批量删除调用处补传当前项目 id
```

> **删除主仓行规则**：主仓行删除 = 该组删除。若组内仅剩本行 → 直接删（组消失）；若组内还有其他项目行 → 必须先迁移主仓到另一行（或连坐删除全组，需二次确认）。

### 2.5 主仓管理与配置同步（核心机制）

- **主仓标记**：`repo_info.is_main_repo`，组内（`repo_url` 相同）有且仅有一个主仓行。
- **首录即主仓**：新仓库首个录入项目的行 `is_main_repo=1`。
- **迁移主仓**：`POST /project-repo/set-main-repo`（§6.5）将 `is_main_repo` 从当前主仓行迁移到指定行，并以新主仓配置为基准**同步全组**（update 组内所有行的配置字段）。
- **配置同步**：任何使主仓行配置变更的操作（主仓行编辑、迁移主仓、主仓行经手动录入/SIG 更新），事务内以主仓行配置为基准 update 组内其余行，保证各项目读到一致配置。
- **副作用提示**：迁移主仓仅改变配置基准与归并保留行，**不改变各项目行的扫描结果归属**（每项目扫自己的行、结果归自己的项目，与现状一致）。

### 2.6 历史存量迁移策略（Phase 1 回填标记，归并推迟）

> **背景**：存量体检发现 53 个共享仓（同 repo_url 多项目多行、配置可能不同）。归并需重映射各仓子表 FK（sca `tbl_scan.repo_id` 等），而这些仓不归属本项目、不可控 → **归并推迟到 Phase 2**。

**Phase 1（本期上线时执行，幂等可重跑，不阻塞上线）**：

```
migrateRepoInfoPhase1():
  1. 清洗同项目重复行：对 (repo_url, project_id) 多行的脏数据，保留最早 create_at 行，
     其余行迁移子表 FK 后删除（或提示人工处理，数量应极少）
  2. 标记主仓：对每个 repo_url 组，默认 is_main_repo=1 给最早 create_at 行；组内仅此一行
  3. ALTER TABLE repo_info ADD UNIQUE INDEX uk_repo_project (repo_url, project_id)
  4. 校验：无同项目重复行；每组合法主仓数 = 1
```

- **效果**：7 个下游仓零影响（每行 project_id 语义不变）；新录入一项目一行由唯一索引兜底；配置收敛靠主仓同步逻辑。
- **Phase 1 明确不做**：不归并 53 个共享仓多行、不删存量行、不建 `repo_project_ref`、不删 `project_id`。

**Phase 2（远期，7 仓逐个可控后评估）**：
- 若仍需「全局唯一单行」，届时新建 `repo_project_ref` 关联表、推动 7 仓将反查改为查关联表，再按主仓行为基准归并 53 个共享仓（重映射子表 FK 后删副仓行），最后 `DROP COLUMN project_id` + 加 `repo_url` 唯一索引。
- 本期**不实施**，仅保留该远期目标说明。

### 2.7 前端实现逻辑

#### 2.7.1 全局配置弹窗（新增，[Repos/index.vue](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/views/Repos/index.vue)）

- 工具栏「导出仓库」右侧新增「全局配置」按钮；原「gitcode 角色映射」「项目公共账号」按钮并入。
- 三页签 GitCode / Gitee / GitHub，各页签：
  - **项目公共账号**：直接编辑登录名 + 令牌（留空不修改），调 `update-project-common-account`
  - **代码仓录入配置**：维护该平台唯一 sig-info.yaml 链接，调 `update-global-config`，保存实时校验可用性
  - **角色映射**：仅 GitCode 页签（gitcode 角色 ↔ openLiBing 角色），存 `config_json.gitcode.roleMapping`

#### 2.7.2 录入对话框改造

- 顶部「录入方式」单选：`手动录入` / `SIG 组一键录入`
- 手动录入：`repoUrl` blur 调 `checkRepoUrl`（防抖 300ms）→ 命中展示主仓提示（「该仓库主仓在项目 X，配置已同步到表单」）+ 「设为本项目为主仓」+ 「删除其他项目行」多选
- SIG 一键录入：平台下拉 → 「选择仓库」多选（仅未录入当前项目的仓库）→ 表格展示（默认参数，可单条/批量编辑/删除）→ 「一键录入 (N)」

#### 2.7.3 列表页与编辑对话框

- 列表新增「来源」（manual/sig，读 `repo_info.source`）、「关联项目数」（同 `repo_url` 组内行数，可选）列
- 编辑对话框：不做 SIG 来源拦截；组内多行时展示主仓提示 + 「设为本项目为主仓」（§2.3）

### 2.8 交互流程示例图

```
【手动录入（命中多行）】
┌────────────────────────────────────────────────┐
│ 录入代码仓                              ✕       │
│ ◉ 手动录入   ○ SIG 组一键录入                   │
│ 仓库链接: https://gitcode.com/org/repo.git     │
│ ℹ 该仓库已在 项目A(主仓)、项目B 录入，配置已按主仓│
│   同步到表单，可直接修改后提交。                │
│ 主仓设置: ◉ 以项目A为主仓同步   ○ 设为本项目为主仓│
│ □ 删除其他项目中的该仓库: ☑项目B               │
├────────────────────────────────────────────────┤
│ 托管平台: gitcode  别名: repo  责任人: sig-owner │
│ ...（其余表单字段）                             │
└────────────────────────────────────────────────┘
```

## 3. 类设计

### 3.1 后端类设计（openlibing-coderepo-fork）

#### 3.1.1 Entity 改造

- [RepoInfoEntity](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/space/RepoInfoEntity.java) 新增字段：

| 字段 | 说明 |
|------|------|
| `source` | `manual` / `sig`，仓库配置来源（SIG 来源链接按项目从 `config_json` 读，不冗余存储） |
| `isMainRepo` | 该 repo_url 组内是否主仓（0/1） |
| `isParticipateOperation` | 是否参与运营（默认是，已存在） |

- 新增 [ProjectRepoGlobalConfigEntity](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/space/)（表 `project_repo_global_config`，config_json 按平台分键）。原 `GitCodeRoleMappingEntity`（表 `project_gitcode_role_mapping`）作废，roleMapping 迁至 `config_json.gitcode.roleMapping`。
- **不新增** `RepoProjectRefEntity`。

#### 3.1.2 Mapper 改造

- [RepoInfoMapper.xml](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/resources/mapper/RepoInfoMapper.xml)：
  - 新增 `selectByRepoUrl`：按 repo_url 查同组所有行（供主仓同步 / 录入检测 / 关联项目数）
  - 新增 `updateConfigByGroup`：以主仓配置为基准更新同组其余行（配置同步）
  - 新增 `markMainRepo` / `clearMainRepo`：主仓标记迁移
  - 现有按 `project_id` / `repo_id` 的查询**不变**（多行模型语义与现状一致）
- 删除计划中的 `RepoProjectRefMapper`（不再需要）。

#### 3.1.3 Service

- [RepoService](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/RepoService.java) / [RepoServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java)：
  - `addRepoInfo`：新增「命中多行」分支（复制主仓配置 + deleteProjectIds + 可选设为主仓，见 §2.1）
  - `updateRepoInfo`：主仓行变更后同步全组；可选迁移主仓（§2.3）
  - `deleteRepoInfo` / `batchDeleteRepoInfo`：增加 `projectId` 入参 + 主仓行删除校验（§2.4）
  - 新增 `checkRepoUrl`、`setMainRepo`、`getRepoAssociation`
- 新增 [MainRepoSyncService](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/)（或并入 RepoServiceImpl）：`syncGroupConfig(repoUrl, baseRow)` 以主仓行为基准同步同组配置；`migrateMainRepo(repoId, newMainRepoId)` 迁移主仓标记并同步全组。
- 新增 [SigRepoImportService](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/)：`saveConfig` / `listConfig` / `listReposInConfig` / `importRepos`（§2.2）。
- 新增 [ProjectRepoGlobalConfigService](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/)：`getGlobalConfig` / `updateGlobalConfig` / `updateProjectCommonAccount`。

#### 3.1.4 工具类 / DTO

- 新增 `SigInfoClient`（实时读 sig-info.yaml，参考 framework GitCode.getYaml 但 accessToken 走 header）、`SigDefaultParamBuilder`（默认参数/别名规则）。
- 新增 DTO/VO：`RepoUrlCheckQueryDTO` / `RepoUrlCheckVO`（exists、repoId、mainRepoProjectId、currentConfig、associatedProjects）、`SetMainRepoDTO`、`RepoAssociationVO`、`GlobalConfigVO`、`SigLocationDTO/VO`、`SigRepoItemVO`、`SigImportResultVO` 等（与 SIG 相关 VO 沿用 §2.2 描述）。
- 删除计划中的 `RepoProjectRef` 相关 DTO/Entity/Mapper/Service。

#### 3.1.5 现有业务读取点（`repoInfo.getProjectId()` 多项目语义）

> **结论：全部无需改造。** 多行模型下每行 `project_id`=该行所属项目，`repoInfo.getProjectId()` 语义与现状完全一致（平台 token、越权校验、列表查询、删除/编辑、成员/角色、上报/日志、事件归属）。本期**不做**任何读取点改造（对比原方案 ~40 处改读 ref 的清单全部取消）。
> 定时任务（syncRepoInfoHandler / codeMetricsObsImportHandler / refreshWebhookHandler / FrameworkJobs.refreshProjectIdCache）均按 `project_id` 逐项目处理，语义不变，零改动。

### 3.2 前端类设计（openlibing-web）

- [Repos/index.vue](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/views/Repos/index.vue)：录入对话框新增「录入方式」切换、手动录入 blur 检测（主仓提示 + 设为主仓 + 选择性删除）、SIG 录入表单；工具栏新增「全局配置」按钮与三页签弹窗；编辑对话框增加主仓提示与「设为本项目为主仓」。
- api/url 层新增：`checkRepoUrl` / `setMainRepo` / `getRepoAssociation` / `getGlobalConfig` / `updateGlobalConfig` / `updateProjectCommonAccount` / `saveSigConfig` / `listSigConfig` / `listSigReposInConfig` / `sigImport`。

## 4. 数据模型设计

### 4.1 现有表 `repo_info` 改造

```sql
-- 1. 新增字段
ALTER TABLE repo_info ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'manual'
  COMMENT '仓库配置来源: manual-手动录入, sig-SIG一键录入' AFTER default_branch_name;
ALTER TABLE repo_info ADD COLUMN is_participate_operation TINYINT(1) NOT NULL DEFAULT 1
  COMMENT '是否参与运营（默认是）' AFTER source;
ALTER TABLE repo_info ADD COLUMN is_main_repo TINYINT(1) NOT NULL DEFAULT 0
  COMMENT '同repo_url组内是否主仓(0-否,1-是)，组内恰一行=1' AFTER repo_url;

-- 2. 确保 repo_url 有普通索引用于组查询（若原表无则新增）：
-- ALTER TABLE repo_info ADD INDEX idx_repo_url (repo_url);
-- 3. 清洗 + 主仓标记 + 唯一索引（见 §2.6 Phase 1 迁移）
-- ALTER TABLE repo_info ADD UNIQUE INDEX uk_repo_project (repo_url, project_id);
```

- **`project_id` 不删除**：每行 `project_id`=该行所属项目，语义与现状一致，7 个下游仓继续按旧方式读取，零改动。
- **不做 `repo_url` 全局唯一**：跨项目多行并存，`uk_repo_project (repo_url, project_id)` 保证一项目一行。

### 4.2 改造表 `project_repo_global_config`（原 `project_gitcode_role_mapping` 泛化）

```sql
-- 1. 原 project_gitcode_role_mapping 重命名 + 增加 config_json 字段
RENAME TABLE project_gitcode_role_mapping TO project_repo_global_config;
ALTER TABLE project_repo_global_config
    ADD COLUMN config_json JSON NULL COMMENT '项目级全局配置(JSON)：各平台sig-info位置、gitcode角色映射等，按平台分键，可扩展' AFTER project_id;

-- 2. 数据迁移：role_mapping 文本迁入 config_json.gitcode.roleMapping，再删旧字段
-- ALTER TABLE project_repo_global_config DROP COLUMN role_mapping;
```

**config_json 结构（约定）**：

```jsonc
{
  "gitcode": {
    "roleMapping": [
      { "gitcodeRole": "owner",     "openlibingRole": "project_admin" },
      { "gitcodeRole": "master",    "openlibingRole": "repo_admin" },
      { "gitcodeRole": "developer", "openlibingRole": "developer" }
    ],
    "sigInfoLocation": { "owner": "openlibing", "repo": "community-private",
                         "branch": "master",
                         "path": "openLiBing-private/sigs/openLiBing-private/sig-info.yaml",
                         "remark": "openLiBing SIG 组" }
  },
  "gitee":  { "sigInfoLocation": null },
  "github": { "sigInfoLocation": null }
}
```

> 项目公共账号仍存 `project_common_account_info`（登录名 + 加密令牌），全局配置弹窗仅新增直接写入接口；不迁移。

### 4.3 sig-info.yaml 配置文件结构（固定格式）

见 §2.2.2。文件位于用户配置的仓路径下，仅声明 SIG 组代码仓清单，不含录入参数。

### 4.4 ER 关系

```
project (1) ──── (N) repo_info (每行=该项目下的一条代码仓；同 repo_url 跨项目多行)
                     ├─ project_id       = 该行所属项目（7 仓反查键）
                     ├─ repo_url         = 组 key（同 repo_url 为一组，主仓同步按此分组）
                     ├─ is_main_repo     = 组内主仓标记（恰一行=1）
                     └─ source / is_participate_operation

project (1) ──── (1) project_repo_global_config ──实时读取──▶ SIG 仓 sig-info.yaml
                      config_json[平台].sigInfoLocation                 │ 解析 repositories
                                  + roleMapping                          ▼
                                                          repo_info（source=sig / 主仓同步）
```

### 4.5 数据量预估

| 维度 | 估算 |
|------|------|
| repo_info | 现状规模不变（< 10 万行），一项目一行；同 repo_url 多行并存（53 个共享仓） |
| 单项目仓库数 | 平均 50-200，列表按 project_id 走索引，毫秒级 |
| SIG 位置配置 | 每项目每平台最多 1 个 sig-info.yaml 链接（存 config_json），内容不落库 |

## 5. 性能设计

### 5.1 数据库性能

| 表 | 索引 | 服务场景 |
|------|------|---------|
| `repo_info` | `uk_repo_project (repo_url, project_id)` | 一项目一行唯一；同组查询走前缀 |
| | `idx_project_id (project_id)` | 列表页按项目查询（现有，保留） |
| | `idx_repo_url (repo_url)` | 组查询（主仓同步/检测） |
| `project_repo_global_config` | `uk_project (project_id, is_deleted)` | 每项目一条全局配置 |

- 主仓同步：按 `repo_url` 一次 UPDATE 同组行，组内行数少（1~N），单次 < 50ms。
- SIG 一键录入：单次最多 100 个仓库，事务内循环，单事务 < 2s。

### 5.2 配置读取设计（实时调对应平台）

- sig-info.yaml 由各接口**实时调对应平台读取并解析**，不缓存、不落库（去除 webhook / 定时兜底）。
- 位置元数据读 `config_json`（毫秒级）；平台调用设超时（如 3s），单平台失败不影响其他平台；全部失败返回明确错误提示稍后重试。

### 5.3 并发控制

- **录入并发**：同一项目同 repo_url 并发首次录入 → `uk_repo_project` 唯一索引兜底（INSERT 冲突即报错/幂等）。不同项目同 repo_url 各自建行，互不冲突。
- **主仓同步并发**：主仓行配置更新 + 同步同组在事务内完成（行锁），避免并发读到中间态；迁移主仓用乐观锁（`update_at`）防并发覆盖。
- **SIG 录入并发**：同一项目同仓库重复导入 → 唯一索引 + 前置过滤兜底。

### 5.4 前端性能

| 维度 | 策略 |
|------|------|
| 冲突预查 | `repoUrl` blur 防抖 300ms 调 `checkRepoUrl` |
| SIG 仓库清单 | 平台切换实时加载 + loading；表格虚拟滚动（>100 行） |
| 一键录入 | loading + 禁用按钮防重复提交 |
| 列表页 | 沿用现有分页 |

### 5.5 性能验收指标

| 指标 | 目标 |
|------|------|
| `checkRepoUrl` 响应 | < 100ms |
| `queryRepoInfo` 响应 | < 100ms（与现状持平） |
| `sigImport`（50 个仓库） | < 3s（含一次 sig-info.yaml 实时读取） |
| `listSigReposInConfig` | < 500ms |
| Phase 1 迁移脚本（10 万行） | < 10 分钟 |

## 6. API 接口设计

### 6.1 现有接口改造：`POST /project-repo/add-repo`

请求体在 [RepoDTO](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/dto/space/RepoDTO.java) 基础上新增：

```jsonc
{
  // ... 现有字段不变（含表单配置） ...
  "isParticipateOperation": true,   // 新增, 可选: 是否参与运营（默认是）
  "setMainRepo": false,             // 新增, 可选: 命中多行时是否设为本项目为主仓（默认 false）
  "deleteProjectIds": [3]           // 新增, 可选: 命中多行时，勾选「删除其他项目中的该仓库」的项目ID列表
}
```

业务变化见 §2.1：命中多行 → 当前项目新建/更新本行（复制主仓配置）、可选设为主仓并同步全组、可选删除其他项目行。

### 6.2 现有接口改造：`POST /project-repo/update-repo`

请求体新增 `setMainRepo`（Boolean，可选）。业务变化见 §2.3：不做 SIG 来源拦截；主仓行变更后以本行配置同步全组；`setMainRepo=true` 时迁移主仓并以本行配置同步全组。

### 6.3 现有接口改造：`POST /project-repo/delete-repo` / `POST /project-repo/batch-delete-repo`

入参新增 `projectId`：

```
POST /project-repo/delete-repo?userId=xxx&userName=xxx&id={repoId}&projectId={projectId}
```

业务变化见 §2.4：删当前项目本行 + 子表清理；主仓行且组内还有其他行时拒绝（需先迁移主仓）。

### 6.4 新增接口 1：`POST /project-repo/check-repo-url`

**用途**：手动录入 blur 触发，检测 repo_url 是否已在其他项目录入（同组多行）；命中返回当前主仓与已关联项目列表。

请求：`{ "projectId": 1, "repoUrl": "https://gitcode.com/org/repo.git" }`

响应（已存在）：

```jsonc
{
  "code": 200,
  "data": {
    "exists": true,
    "repoId": 1001,                    // 当前项目本行 repo_id（未录入为 null）
    "mainRepoProjectId": 2,            // 当前主仓项目（is_main_repo=1 的行所属项目）
    "currentConfig": {                 // 主仓行配置（默认同步基准）
      "repoName": "repo", "repoOwner": "sig-owner", "purpose": "自研源码",
      "openSource": "lead", "assumePr": "1", "isAutoFormat": false,
      "isSuppressionEnabled": true, "isParticipateOperation": true, ...
    },
    "associatedProjects": [            // 已关联项目列表（含本组各行所属项目）
      { "projectId": 2, "projectName": "项目A", "isMainRepo": true },
      { "projectId": 3, "projectName": "项目B", "isMainRepo": false }
    ]
  }
}
```

前端据 `exists=true`：自动同步主仓配置到表单；展示「该仓库主仓在项目 X，配置已同步」+「设为本项目为主仓」+「删除其他项目中的该仓库」多选。

### 6.5 新增接口 2：`POST /project-repo/set-main-repo`（迁移主仓）

**用途**：将指定 repo 的主仓迁移到本行（或指定行），并以新主仓配置为基准同步全组。

```jsonc
{ "userId": "xxx", "userName": "xxx", "projectId": 1, "repoId": 1001 }
```

响应：`DataResult<Void>`。业务：校验本行属于该项目 → `is_main_repo` 迁移 → 同步全组（§2.5）。前端需强提示：迁移后配置以本项目为基准同步各项目。

### 6.6 新增接口 3：`GET /project-repo/get-repo-association`

**用途**：编辑/删除前查该 repo 关联的项目列表（判定删除语义 + 主仓提示）。

请求：`GET /project-repo/get-repo-association?userId=xxx&repoId=1001`

响应：

```jsonc
{ "code": 200, "data": {
    "projectCount": 3,
    "projects": [
      { "projectId": 1, "projectName": "当前项目", "isMainRepo": false },
      { "projectId": 2, "projectName": "项目A", "isMainRepo": true }
    ] } }
```

### 6.7 新增接口 4/5：`GET|POST /project-repo/global-config`

- `GET /project-repo/global-config?userId=xxx&projectId=1`：回显三页签（各平台 sigInfoLocation + gitcode roleMapping + 公共账号掩码）。
- `POST /project-repo/global-config`：按 `platform` 合并更新 `config_json`（sigInfoLocation + 仅 gitcode 的 roleMapping），保存时实时校验位置可用性。

### 6.8 新增接口 6：`POST /project-repo/update-project-common-account`

按平台更新项目公共账号登录名 + 令牌（令牌加密入库、留空不覆盖），替代原只读跳转。

### 6.9 新增接口 7/8：`POST|GET /project-repo/sig/config`

- `POST`：保存该平台唯一 sig-info.yaml 链接（解析 owner/repo/branch/path + 实时校验可用性），推荐走 §6.7 `update-global-config`，本接口作为独立保存入口保留。
- `GET /project-repo/sig/config?userId=xxx&projectId=1&platform=gitcode`：查询该平台位置链接。

### 6.10 新增接口 9：`POST /project-repo/sig/repos`

SIG「选择仓库」下拉数据源：实时解析该平台 sig-info.yaml，仅返回**尚未录入当前项目**的仓库 + 默认参数（§2.2.3）。

### 6.11 新增接口 10：`POST /project-repo/sig/import`

一键录入勾选仓库（默认参数或用户编辑配置）。校验每个 repoUrl 在实时解析结果内且当前项目未录入；未命中建主仓行、命中建副仓行（复制主仓配置），见 §2.2.4。

### 6.12 接口契约汇总

| 接口 | 方法 | 路径 | 请求体 | 响应体 |
|------|------|------|--------|--------|
| 录入仓库（改造） | POST | `/project-repo/add-repo` | RepoDTO（+setMainRepo/deleteProjectIds） | `DataResult<Integer>` |
| 修改仓库（改造） | POST | `/project-repo/update-repo` | RepoDTO（+setMainRepo） | `DataResult<Integer>` |
| 删除仓库（改造） | POST | `/project-repo/delete-repo` | repoId + projectId | `DataResult<Void>` |
| 批量删除（改造） | POST | `/project-repo/batch-delete-repo` | repoIds + projectId | `DataResult<Void>` |
| 冲突检测（新增） | POST | `/project-repo/check-repo-url` | RepoUrlCheckQueryDTO | `DataResult<RepoUrlCheckVO>` |
| 迁移主仓（新增） | POST | `/project-repo/set-main-repo` | {projectId, repoId} | `DataResult<Void>` |
| 关联查询（新增） | GET | `/project-repo/get-repo-association` | repoId | `DataResult<RepoAssociationVO>` |
| 查询全局配置（新增） | GET | `/project-repo/global-config` | projectId | `DataResult<GlobalConfigVO>` |
| 更新全局配置（新增） | POST | `/project-repo/global-config` | GlobalConfigUpdateDTO | `DataResult<GlobalConfigVO>` |
| 更新项目公共账号（新增） | POST | `/project-repo/update-project-common-account` | ProjectCommonAccountUpdateDTO | `DataResult<Void>` |
| 保存 SIG 位置（新增） | POST | `/project-repo/sig/config` | {projectId, platform, location} | `DataResult<SigConfigSaveVO>` |
| 查询 SIG 位置（新增） | GET | `/project-repo/sig/config` | projectId + platform | `DataResult<SigLocationVO>` |
| SIG 仓库清单（新增） | POST | `/project-repo/sig/repos` | {projectId, platform} | `DataResult<SigRepoConfigVO>` |
| SIG 一键录入（新增） | POST | `/project-repo/sig/import` | {projectId, platform, repoConfigs} | `DataResult<SigImportResultVO>` |

### 6.13 错误码约定

| code | msg | 场景 |
|------|------|------|
| 200 | success | 成功 |
| 400 | 主仓行删除需先迁移主仓 | delete-repo 删除组内主仓行且组内还有其他行 |
| 403 | SIG 位置不存在或不属于该项目 | sig 接口传了未配置的 platform |
| 403 | 平台不合法 | global-config 传了非 gitcode/gitee/github 的 platform |
| 404 | sig-info.yaml 文件不存在 | 实时读取指定位置失败 |
| 500 | sig-info.yaml 格式错误或解析失败 | 实时解析失败 |
| 500 | 所选仓库不在该配置文件中 | sig/import 传了不在解析结果中的 repoUrl |
| 500 | 配置文件读取失败，请稍后重试 | 平台 API 调用失败 |
| 500 | 仓库链接不合法 | repoUrl 校验失败 |
| 500 | 该仓库已录入当前项目 | 违反 uk_repo_project 唯一约束（并发兜底） |

### 6.14 内部 API 契约

- [InternalProjectRepoController](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/InternalProjectRepoController.java) `POST /project-repo/internal/query-repo`：语义与 `query-repo` 一致、不要求 `userId`；响应 `data.list` 为精简视图（repoId/projectId/repoName/repoUrl/repoOwner/platform/status），不返回敏感字段。**多行模型下按行返回，语义与现状一致，下游仓零改动**。
- 删除仓库后通知 openlibing-codecheck 重算 `is_used` 的调用契约不变（走 `OpenlibingCodeCheckClient`）。

## 7. 安全设计

### 7.1 鉴权

- 现有接口（add/update/delete/query-repo）鉴权不变（网关 token + 角色校验）。
- 新增接口：
  - 读权限（check-repo-url / get-repo-association / global-config GET / sig/config GET / sig/repos）：沿用 `query-repo` 角色集合
  - 写权限（set-main-repo / global-config POST / update-project-common-account / sig/config POST / sig/import）：沿用 `add-repo` 角色集合
- 所有接口校验 `userId` 对 `projectId` 的访问权限（防跨项目越权）；越权校验沿用现有 `verifyPermissionsByProduct`（多行模型下 `repo_info.getProjectId()`=该行所属项目，语义与现状一致，**无需 ref 集合改造**）。

### 7.2 SIG 仓（sig-info.yaml 位置）访问安全

- **token 传递**：调平台 API 用 `Authorization: Bearer <token>` header（遵循项目硬约束），token 从项目公共账号获取、解密后使用，不入日志、不入 URL 参数。
- **位置白名单**：所有 SIG 读取接口不接受前端任意传仓路径，仅允许读取 `config_json[platform].sigInfoLocation` 配置的位置；保存时校验 `owner/repo/branch` 安全字符、`path` 后缀必须为 `sig-info.yaml`（或含 `sig-info` 的 `.yaml/.yml`）、不含 `..`，实时校验文件存在且可解析。
- **YAML 解析安全**：SnakeYAML `SafeConstructor`，拒绝实例化标签，失败返回明确错误不暴露堆栈。

### 7.3 输入校验

- 新增接口 `@Valid` + JSR-303 校验；`repoUrl` 沿用现有 `validateSafeUrl` 镜像校验（协议头白名单、域名信任、无 `..`）；`repoUrl` ≤512、`repoName` ≤50；`selectedRepoUrls` 单次 ≤100 且必须在实时解析结果内；`platform` 必须合法且该项目已配置。

### 7.4 日志脱敏

- 禁止打印：accessToken（仓库/项目公共账号令牌）、`currentConfig.accessToken`、YAML 内 accessToken、`config_json` 整对象。
- 允许打印：projectId / repoUrl / platform / owner/repo/branch/path / 计数等。
- 冲突检测返回的 `currentConfig` 中 accessToken 序列化前置空；`get-global-config` 公共账号令牌掩码 `******`；`update-project-common-account` 明文令牌不出日志、不返回。

### 7.5 SIG 录入与手动录入互不覆盖

- SIG 录入只针对尚未录入当前项目的仓库（已录入不展示、不覆盖）；全局已存在仓库 SIG 录入时**复制主仓配置、不覆盖**（新行是副仓行，配置与主仓一致）。
- SIG 来源仓库允许手动编辑（不做来源拦截）。
- 手动录入命中多行不视为错误：自动同步主仓配置、可选删除其他项目行（见 §2.1）。

### 7.6 数据库安全

- `uk_repo_project (repo_url, project_id)` 防同项目重复录入；不做 repo_url 全局唯一。
- 软删除现状保留（is_deleted）；删除链路本期保持物理删除（与现状一致，7 仓零变化）。
- accessToken 明文存储现状不改（可后续独立立项加密）。

### 7.7 平台 token 安全

沿用现有 `GitCodeUtil`/`GiteeUtil`/`GithubUtil` token 使用方式；`SigInfoClient` 复用 `commonService.getGitcodeToken`，不引入新凭证。

### 7.8 迁移脚本安全

- `project_repo_global_config` 迁移：role_mapping 迁入 `config_json.gitcode.roleMapping`，批量 upsert 幂等可重跑。
- **Phase 1** repo 迁移（清洗同项目重复行 + 标主仓 + 加唯一索引）：事务分批（每批 1000 行）提交、可重跑；只动 repo_info 本身，不触碰 7 仓数据。
- 迁移在上线后统一执行、不阻塞上线；迁移前备份 repo_info。
- 灰度开关 `coderepo.repo-decouple.enabled`（仅控制主仓同步新逻辑开关，可快速回滚）。

### 7.9 安全验收清单

- [ ] accessToken 不出现在任何日志与 URL 参数中（grep + 网关日志验证）；调平台 API 走 `Authorization: Bearer` header
- [ ] SIG 读取接口传本项目未配置的 platform 返回 403；位置保存时 `path` 含 `..`/后缀不符被拒绝
- [ ] 未在 config_json 配置的位置无法通过任意接口读取
- [ ] `update-project-common-account` 令牌不出日志、不返回明文；`get-global-config` 令牌掩码
- [ ] YAML 含 `!!java/object` 等危险标签时解析被拒绝
- [ ] 跨项目访问返回 403
- [ ] **Phase 1** 迁移后：`uk_repo_project` 生效（同项目同 repo_url 无法重复插入）；每个 `repo_url` 组合法主仓数=1；7 个下游仓按 `(project_id, repo_url)` 反查全部命中（SCA 联调用例）
- [ ] 主仓配置同步：编辑主仓行 → 同组其余行配置一致；迁移主仓 → 新主仓配置同步全组、旧主仓降为副仓（单测 + DB 校验）
- [ ] 删除主仓行且组内还有其他行 → 被拒绝并提示先迁移主仓
- [ ] 单元测试覆盖：手动录入命中多行（复制主仓配置/设为主仓/选择性删除）、SIG 录入仅未录入仓库 + 不覆盖已有配置、主仓同步/迁移、全局配置 config_json 读写（含 roleMapping 迁移）、迁移幂等、sig-info.yaml 解析与位置白名单
