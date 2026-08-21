# 代码仓管理与需求解耦 + SIG 组一键批量录入（需求设计文档）

> 跨仓 Full 模式需求设计文档。涉及 `openlibing-coderepo-fork`（后端 + DB）、`openlibing-web`（前端）两个仓，并参考 `openlibing-framework` 的 `GitCode.getYaml` 实现模式。
>
> **影响面说明**：本需求对 `repo_info` 表 `project_id` 采取「暂时保留 + 分阶段改造」策略——首批改造 `coderepo`/`codecheck`/`cicd`/`sbom` 四仓切换为从 `repo_project_ref` 取 `project_id`；`framework`/`anti-poison`/`sca`/`gateway`/`vulnerability` 暂不修改，仍从 `repo_info.project_id` 读取（见 §1.2 分阶段改造范围）。
>
> 配套文档：[feature-spec.md](./feature-spec.md)（特性规格设计：业务背景 / 版本变化点 / 页面原型 / 业务逻辑 / 权限设计）。
>
> 本文按"方案设计 → 实现逻辑设计 → 类设计 → 数据模型设计 → 性能设计 → API 接口设计 → 安全设计"七节组织，作为评审与实施依据。

## 1. 方案设计

### 1.1 问题域

当前 [repo_info](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/space/RepoInfoEntity.java) 表把「代码仓信息」与「项目归属」耦合在同一张表：`repo_id`、`repo_url`、`project_id` 三字段同表，导致同一 `repo_url` 可在不同 `project_id` 下各存一条记录，且各条记录的配置（用途、开源类型、接管 PR、自动触发、规则集等）可不一致。由此产生三类问题：

1. **配置漂移**：同一代码仓在 A 项目配置「代码风格自动修复=是」，在 B 项目配置「代码风格自动修复=否」，平台行为以哪条为准无法收敛。
2. **重复录入成本**：每个项目都要重复填一遍同一代码仓的全部配置，无复用机制。
3. **缺少批量录入**：当前用户只能逐个手工录入代码仓，无法一键导入。

本次需求做三件事：

- **解耦**：拆 `repo_info`（全局仓库信息，`repo_url` 全局唯一 → 单一 `repo_id`）与 `repo_project_ref`（仓库 ↔ 项目关联表），确保同一代码仓在平台内全局唯一、配置单一来源。
- **双录入通道**：保留手动录入（输入链接自动检测是否已录入其他项目，命中则自动同步其配置到表单、支持选择性删除之前项目关联），新增「SIG 组一键批量录入」（从项目级全局配置中按平台读取 sig-info.yaml 位置，下拉多选**尚未录入当前项目**的仓库后在表格中核对/编辑/删除再批量录入，位置可为 community / community-private 等任意配置的仓路径，**每平台仅一个**）。SIG 录入不会覆盖已有配置。
- **项目级全局配置**：在代码仓管理页「导出仓库」右侧新增「全局配置」按钮，按 GitCode / Gitee / GitHub 三个平台页签统一维护项目公共账号（可直接配置）、代码仓录入配置（sig-info.yaml 位置）与 GitCode 角色映射；改造 `project_gitcode_role_mapping` 表为通用配置表 `project_global_config`，各配置项以 JSON 存储，便于后续扩展新配置项而不需改表。

### 1.2 解耦方案

`repo_url` 全局唯一 → 单一 `repo_id`；新建 `repo_project_ref` 作为仓库↔项目多对多关联表；`repo_info.project_id` **暂时保留**（回填该 repo 在 `repo_project_ref` 中最早关联记录的 `project_id`，作为过渡期冗余字段），后续再择期移除。

1. **全局唯一是核心目标**：需求明确「每个 `repo_url` 全局唯一对应一个 `repo_id`」。**先不在 DB 层对 `repo_url` 加唯一约束**（避免上线窗口并发录入触发唯一键冲突、且存量重复数据未清理会阻塞加唯一索引），先在**在代码层保证新录入仓库不重复**（`addRepoInfo` / `sigImport` 在事务内按归一化 `repo_url_normalized` 查重 + 锁，见 §5.3），同一仓库不再允许按项目重复存入多条 `repo_info`。
2. **配置单一来源**：同一 `repo_id` 只有一份配置（用途/开源类型/接管 PR/规则集等），从根上消除配置漂移。多个项目关联同一仓库时共享这份配置。
3. **关联表表达多对多**：`repo_project_ref` 干净支撑「一个 repo 关联 N 个 project」「一个 project 关联 N 个 repo」的多对多语义，且可在关联上记录「该关联是手动建立还是 SIG 建立」（`source` 字段），支撑 SIG 优先级判定。
4. **过渡期双轨兼容**：`repo_info.project_id` 不立即删除，回填为最早关联记录的 `project_id`，保证未改造仓继续按旧方式读取不中断；`repo_url` 全局唯一目标**在上线后统一执行数据变更清理达成**（存量不同项目下的重复仓库按 `repo_url` 归并），清理完成前由代码层保证新录入不重复。
5. **分阶段改造（影响面收敛）**：本需求先只让 `coderepo`、`codecheck`、`cicd`三个仓全面切换为从 `repo_project_ref` 取 `project_id`；其余仓（`framework`、`anti-poison`、`sca`、`gateway`、`vulnerability`）暂不统一修改，仍从 `repo_info.project_id` 读取，后续版本再逐个切换（见 §2.5 迁移策略与 §4.4 过渡期策略）。

**分阶段改造范围与影响仓**（基于全量代码检索 `repo_info` 表 `repo_id ↔ project_id` 互查使用情况）：

| 阶段 | 仓 | 改造方式 |
|------|-----|---------|
| 第一批（本需求） | `coderepo` / `codecheck` / `cicd` / `sbom` | 全面切换：`project_id` 从 `repo_project_ref` 取（查询 JOIN 关联表，写入同时维护两表） |
| 暂不修改 | `framework` / `anti-poison` / `sca` / `gateway` / `vulnerability` | 仍从 `repo_info.project_id` 读取（过渡期冗余字段，值为最晚关联 `project_id`） |
| 后续版本 | 上述暂不修改仓 | 逐个切换为从 `repo_project_ref` 取 `project_id`，全部切换完成后择期 `DROP COLUMN project_id` |

> **过渡期语义说明**：`repo_info.project_id` 仅能冗余单个 `project_id`（最晚关联），故未改造仓在「一个 repo 关联多个 project」场景下只能读到最早的那个 project 归属；这对当前各仓存量逻辑（基本按单 project 读仓库列表）可接受，待其逐个切换后补齐多对多语义。

### 1.3 整体架构

```
┌──────────────────────────────────┐         ┌──────────────────────────────────────┐
│  openlibing-web                  │         │  openlibing-coderepo-fork            │
│  Repos/index.vue                 │         │                                      │
│  ┌────────────────────────────┐  │  HTTP   │  RepoController (/project-repo)     │
│  │ 录入仓库（手动 / SIG 二选一）│  │ ──────▶ │   ├─ add-repo       (手动录入+检测) │
│  │ 同步仓库 / 编辑 / 删除      │  │         │   ├─ update-repo    (直接编辑)      │
│  └────────────────────────────┘  │         │   ├─ sig/config     (sig-info链接配置)│
│         │                        │ ◀────── │   ├─ sig/repos       (实时解析YAML)  │
│         │                        │  resp   │   └─ sig/import      (默认参数录入) │
│         ▼                        │         │              │                       │
│  配置自动同步 / 选择性删除提示    │         │              │                       │
└──────────────────────────────────┘         │              ▼                       │
┌──────────────────────────────────┐         │  ┌──────────────────────────────┐   │
│  SIG 仓 (gitcode)               │         │  │ repo_info (全局唯一)          │   │
│  sig-info.yaml (固定格式)        │ ◀────── │  │  repo_url UNIQUE, source,    │   │
│  repositories:                   │  实时读  │  │  sig_config_file, ...        │   │
│   - repo:                        │  YAML   │  └──────────────┬───────────────┘   │
│     - openlibing/xxx            │         │                 │ repo_id            │
│     - openlibing/yyy            │         │  ┌──────────────▼───────────────┐   │
│   - repo:                        │         │  │ repo_project_ref (新增)       │   │
│     - openlibing/zzz            │         │  │  (repo_id, project_id,        │   │
└──────────────────────────────────┘         │  │   source, sig_config_file)   │   │
                                              │  └──────────────┬───────────────┘   │
┌──────────────────────────────────┐         │                 │                   │
│  project_global_config (改造)    │         │  ┌──────────────▼───────────────┐   │
│  项目级全局配置 config_json      │◀─────── │  │ (按 project_id+平台 查位置)   │   │
│  gitcode/gitee/github 各平台     │  读取    │  └─────────────────────────────┘   │
│  (sigInfoLocation + roleMapping)│         └──────────────────────────────────────┘
└──────────────────────────────────┘
```

核心流程：
1. **手动录入**：用户输入 `repo_url`（blur 时调检测接口）→ 后端查 `repo_info` by `repo_url`：未命中则新建 `repo_info` + 新建 `repo_project_ref(source=manual)`；命中则**自动将已有配置同步到表单**（可修改），展示已关联项目列表供**选择性删除**（仅取消所选项目的关联），提交时新建当前项目关联、可选删除所选项目关联并按表单更新全局配置。
2. **SIG 一键录入**：用户在代码仓管理「全局配置」弹窗按平台（gitcode/gitee/github）配置 sig-info.yaml 所在位置（**每平台唯一一个**仓路径）→ 录入弹窗「SIG 组一键录入」下拉多选**尚未录入当前项目**的 SIG 仓库（已录入的不展示，避免覆盖已有配置）→ 选出后在表格中展示所选仓库（默认配置，可单条/批量编辑或删除）→ 后端按所选仓库（默认参数或用户编辑配置）录入，每个仓库 upsert `repo_info`（source=sig，已全局存在则复用其配置不覆盖）+ upsert `repo_project_ref(source=sig)`。
3. **编辑**：仓库配置全局唯一一份，编辑直接更新 `repo_info` 即可（SIG 来源仓库同样允许手动编辑）；不再做「多项目影响提示」与「SIG 来源编辑拦截」。
4. **历史存量迁移**：对相同 `repo_url` 的多条旧 `repo_info`，保留最早一条的配置作为唯一 `repo_info`，其余记录的 `project_id` 迁移到 `repo_project_ref`，多余记录删除。

### 1.5 关键决策汇总

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 表结构 | 新建 `repo_project_ref`（多对多）；`repo_info.project_id` **暂不删除**，作为过渡期冗余回填为最早关联记录的 `project_id`，后续择期移除 | 全局唯一 + 多对多关联，先确保四仓切换，其余仓仍从 `repo_info.project_id` 读取，过渡期双轨兼容 |
| `repo_url` 唯一性 | **暂不加 DB 唯一约束**；应用层 normalize（`.git` 后缀、大小写、末尾斜杠归一）+ 代码层事务内查重保证新录入不重复 | 避免上线窗口并发录入触发唯一键冲突、存量未清理导致加唯一索引失败；存量不同项目下重复仓库上线后统一清理，清理完成后择期加唯一索引 |
| source 字段 | `repo_info.source`（manual/sig）+ `repo_project_ref.source`（manual/sig） | repo 级标记「当前配置来源」+ 关联级标记「该关联建立方式」，双粒度支撑优先级判定 |
| SIG 优先级 | sig 与 manual 录入**互不覆盖**：SIG 录入只针对**尚未录入当前项目**的仓库，已录入的不展示、不覆盖；手动录入命中已存在仓库时自动同步其配置，支持选择性删除之前项目关联 | 避免配置被覆盖/漂移；SIG 仓库配置允许后续手动编辑（不做来源拦截） |
| 配置文件读取 | 复用 framework `GitCode.getYaml` 模式（coderepo 服务内独立实现 `SigInfoClient`），**接口实时调 gitcode 读取并解析** | coderepo 与 framework 是独立微服务，不跨仓引 jar；逻辑简单（≈120 行）独立维护 |
| 配置文件位置 | 项目级配置：用户在代码仓管理「全局配置」弹窗按平台（gitcode/gitee/github）配置**一个** sig-info.yaml **链接**（`https://{host}/{owner}/{repo}/blob/{branch}/{path}`，每平台唯一，后端解析出 owner/repo/branch/path），存 `project_global_config.config_json` | 每平台仅一个位置、可跨多平台（gitcode/gitee/github）扩展，用户填写完整链接即可，无需拆字段 |
| 全局配置入口 | 代码仓管理页「导出仓库」右侧新增「全局配置」按钮，三页签（GitCode/Gitee/GitHub）分别维护项目公共账号 / 代码仓录入配置 / 角色映射 | 项目级公共配置集中管理，对所有代码仓生效；公共账号仍存 `project_common_account_info`（新增直接写入接口），角色映射与 sig-info 链接存 `project_global_config.config_json` |
| 项目公共账号 | 仍存现有 `project_common_account_info` 表（登录名 + 加密令牌），全局配置弹窗提供「保存公共账号」接口直接配置（不再只读跳转） | 令牌加密存储现状不变，避免迁移与多服务读取改造；仅新增写入入口，读取沿用现有 `get-project-common-account` |
| 配置同步机制 | **去除 webhook**：不再推送解析入库；一键录入接口**实时调对应平台 API 读取指定位置 sig-info.yaml 并直接解析返回** | 简化链路、去掉缓存一致性与事件丢失问题；sig-info.yaml 内容以对应平台实时文件为准 |
| 配置读取 | `sig/repos` / `sig/import` 均实时调对应平台（gitcode/gitee/github）API 读取指定位置 sig-info.yaml（走配置位置白名单，见 §7.2） | 保证读到最新配置；平台 API 失败时返回明确错误并提示稍后重试 |
| 冲突检测时机 | 手动录入时 `repoUrl` blur 调 check 接口预查，命中即自动同步配置；后端在 add 时二次校验防并发 | 前端 blur 触发自动同步；后端 add 时按归一化 `repo_url` 查重兜底 |
| 历史迁移 | 一次性迁移脚本 + 灰度开关（按 `repo_url` 归并，保留最早配置） | 存量数据收敛到新模型，迁移期间双写保护（见 §2.5） |
| YAML 解析安全 | SnakeYAML `SafeConstructor`（拒绝实例化任意类） | 防 YAML 反序列化攻击 |
| accessToken 传递 | 调 gitcode API 时 `Authorization: Bearer <token>` header（不复用 framework 的 URL param 方式） | 遵循项目硬约束「第三方 API 调用 accessToken 必须在 header」 |

## 2. 实现逻辑设计

### 2.1 手动录入逻辑（含跨项目检测与选择性删除）

> **核心变化**：输入仓库链接后 blur 即向后端发起检测请求，命中已录入其他项目的仓库时**自动将已有配置同步进表单**（无需「一键同步」按钮），用户可修改配置；「是否删除之前项目中的代码仓」支持**选择性删除**（仅取消所选项目与该代码仓的关联，非一次删除所有）；若未删除之前项目中的代码仓，修改配置会**同步修改之前项目中的代码仓配置**（代码仓配置全局唯一），前端需提示用户。

#### 2.1.1 录入主流程

```
addRepoInfo(userId, userName, projectId, RepoDTO, deleteProjectIds):
  1. normalize repoUrl：去末尾斜杠、去 .git 后缀、统一 https 协议头
  2. 查 repo_info by repo_url（命中=已全局存在）
  3a. 未命中（首次录入）:
      - insert repo_info (source=manual, sig_config_file=null, 配置取 RepoDTO)
      - insert repo_project_ref (repo_id, project_id, source=manual)
      - 同步仓库信息（调 GitCodeUtil 拉平台元数据回填，沿用现有 syncRepoInfo 逻辑）
      - 配置 webhook（沿用现有 autoSetWebHook 逻辑）
  3b. 命中（已存在）:
      - 前端 blur 时已触发检测、表单已自动同步现有配置，用户已勾选
        「是否删除之前项目中的代码仓」（deleteProjectIds 为勾选的项目 ID 列表）
      - 若 deleteProjectIds 非空 → 逐个删除 repo_project_ref (repo_id, deleteProjectId)
        （仅取消所选项目与该代码仓的关联，repo_info 保留，其余项目不受影响）
      - 若未勾选任何删除项 → 按表单更新 repo_info 配置（同步影响所有仍关联项目），
        前端已提示「修改会同步修改之前项目中的代码仓配置」
      - upsert repo_project_ref (repo_id, project_id, source=manual)
  4. 返回 repoId
```

#### 2.1.2 检测接口（前端 blur 触发）

```
checkRepoUrl(userId, projectId, repoUrl):
  1. normalize repoUrl
  2. 查 repo_info by repo_url
  3. 未命中 → { exists: false }（表单不填充，正常录入）
  4. 命中 → {
       exists: true,
       repoId,
       currentConfig: { repoName, repoOwner, purpose, openSource, assumePr,
                        defaultBranchName, isAutoFormat, isSuppressionEnabled, ... },
       associatedProjects: [            // 该 repo 已关联的项目列表
         { projectId, projectName }
       ]
     }
  5. 前端把 currentConfig 自动同步到表单（可修改），并展示「是否删除之前项目中的代码仓」多选
```

#### 2.1.3 前端交互（自动同步 + 选择性删除）

- `repoUrl` blur → 调 `checkRepoUrl`（防抖 300ms）
- `exists=false` → 表单正常录入
- `exists=true` →
  - 顶部蓝色提示条：「检测到该代码仓已在 项目A、项目B 录入，已将已有配置自动同步到下方表单，可直接修改后提交。」（**无「一键同步」按钮**，配置自动同步）
  - 「是否删除之前项目中的代码仓？」多选框列出所有关联项目，**可多选**，仅取消所选项目与该代码仓的关联（**非一次删除所有**；不勾选则不删除该项目下的该代码仓）
  - 若未勾选任何删除项 → 黄色警告条：「您未删除之前项目中的代码仓，修改下方配置将**同步修改项目A、项目B中的该代码仓配置**（代码仓配置全局唯一）。」
  - 表单字段全部可编辑；提交时携带 `deleteProjectIds`（勾选的项目）与表单配置

### 2.2 SIG 组一键录入逻辑

> **配置来源**：用户在代码仓管理「全局配置」弹窗按平台（gitcode/gitee/github）配置 sig-info.yaml 所在位置（**每个平台唯一一个链接**，形如 `https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private/sig-info.yaml`），存 `project_global_config.config_json`（§4.2.1）。sig-info.yaml 为固定格式（§2.2.0b），一键录入各接口**实时调对应平台 API 读取指定位置文件并直接解析返回**，**去除 webhook 推送 / 定时兜底 / 入库缓存** 逻辑。

#### 2.2.0 sig-info.yaml 位置配置（新增，位于「全局配置」弹窗，每平台唯一）

> **核心变化**：用户无需拆分填写 仓/分支/文件路径 三个字段，只需填写**一个完整的链接**——在代码托管平台对应代码仓、对应分支中找到 sig-info.yaml 文件，复制此时的完整链接即可（表单提供示例链接）。后端保存时解析链接为 `owner/repo/branch/path` 后实时校验可用性。

```
saveSigConfig(userId, projectId, platform, location):
  - platform: gitcode / gitee / github（位置所属平台）
  - location: { url, remark? }   // 该平台唯一 sig-info.yaml 链接（null 表示清空）
  1. 校验 platform 合法；校验链接格式：解析出 owner/repo/branch/path（
     https://{host}/{owner}/{repo}/blob/{branch}/{path}，path 为 sig-info.yaml 或 .yaml/.yml 且文件名含 sig-info）
  2. 读取 project_global_config.config_json，将该平台 sigInfoLocation 更新为入参链接（其余平台配置保持不变）
  3. 实时校验：按解析出的 owner/repo/branch/path 调对应平台 getFileContent 验证文件存在且 YAML 可解析；
     不可用位置在响应中标记（不阻断保存，便于用户排查）
  4. 返回保存结果 + 位置可用性（可读 / 文件不存在 / 解析失败）

listSigConfig(userId, projectId, platform):
  1. 从 project_global_config.config_json 取该平台配置的 sig-info.yaml 链接
     → { url, remark? }（未配置为 null）
```

#### 2.2.0b sig-info.yaml 文件格式（固定）

sig-info.yaml 格式固定，仅声明「SIG 组管理的代码仓清单」，**不含任何录入参数**（录入参数全部使用默认值，见 §2.2.3）：

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

解析规则：
- 顶层键 `repositories` 必填，为列表；列表项为 `- repo:`，其值为该组下的代码仓清单（`owner/repo` 字符串列表，可多行）。
- 每个 `owner/repo` 按位置所属平台组装完整 repoUrl：`https://gitcode.com/{owner}/{repo}.git`（gitcode）/ `https://gitee.com/{owner}/{repo}.git`（gitee）/ `https://github.com/{owner}/{repo}.git`（github）。
- 对重复的 `owner/repo` 跨分组去重，只保留一条。
- 解析失败（缺 `repositories` / 结构不符）返回明确错误，不阻断其他平台与其他功能。

#### 2.2.1 读取配置文件内仓库清单（实时解析，仅展示未录入当前项目的仓库）

> **核心变化**：`listSigReposInConfig` 只返回**尚未录入当前项目**的 SIG 仓库（已录入当前项目的仓库被过滤、不展示），因此 SIG 录入**不会覆盖**已有配置，**录入状态（NEW/OVERRIDE/SYNCED）不再需要**。位置为每平台唯一的链接，SIG 录入弹窗**不单独展示配置文件**（仅选择平台，见 §2.6.2）。

```
listSigReposInConfig(userId, projectId, platform):
  1. 从 project_global_config.config_json 取该平台位置（校验属于该项目且平台一致）
  2. 实时调对应平台 getFileContent 读取 sig-info.yaml → 解析 repositories → List<{owner, repo}>
  3. 过滤：查 repo_project_ref where project_id=? → 得到当前项目已录入的 repo_url 集合
     - 仅保留**未录入当前项目**的仓库（已录入的不展示，避免覆盖已有配置）
  4. 按平台组装完整 repoUrl + 默认别名（repo 名，见 §2.2.3 别名规则）
     + 默认配置（默认分支/仓库责任人/开源类型/代码风格自动修复/告警抑制自动检视 等，见 §2.2.3 默认参数表）
  5. 返回 [{ owner, repo, repoUrl, platform, defaultConfig: { alias, defaultBranchName,
           repoOwner, openSource, isAutoFormat, isSuppressionEnabled, ... } }]
```

#### 2.2.3 一键录入（默认参数 + 别名规则，可单条/批量编辑配置）

**录入默认参数**（sig-info.yaml 中不配置，直接使用默认值；用户可在表格中**单条/批量编辑**，或**不修改、直接使用默认值**）：

| 字段 | 默认值 | 说明 |
|------|--------|------|
| 代码仓别名 | 先用 repo 名；当前项目已存在同名别名 → 用 `repo名-平台名`（如 `openlibing-cicd-web` → `openlibing-cicd-web-gitcode`） | 别名在**当前项目**内查重，冲突按 §「别名冲突」处理 |
| 默认分支 | 平台仓库默认分支（master / main，调平台仓库详情接口获取） | 实时获取，可编辑 |
| 仓库责任人 | gitcode 上该代码仓的**建仓人账号名**（调 gitcode 仓库详情接口获取） | 实时获取，非配置写死，可编辑 |
| 开源类型 | 主导开源 | 固定默认，可编辑 |
| 用途 | 自研源码 | 固定默认，可编辑 |
| 语言 | 不选 | 固定默认，可编辑 |
| 公共账号令牌 | 不填 | 沿用项目公共账号 |
| 接管 PR 管理 | 否 | 固定默认，可编辑 |
| 自动触发门禁流水线 | 否 | 固定默认，可编辑 |
| 自动触发接口扫描 | 否 | 固定默认，可编辑 |
| 代码风格自动修复 | 否 | 固定默认，可编辑 |
| 告警抑制自动检视 | 否 | 固定默认，可编辑 |
| 仓库规则集配置 | 不配置 | 固定默认 |

```
sigImport(userId, userName, projectId, platform, repoConfigs):
  - repoConfigs: [{ repoUrl, config: { alias, defaultBranchName, repoOwner, purpose,
                  openSource, isAutoFormat, isSuppressionEnabled, ... } }]  // 用户编辑后或默认值
  1. 从 project_global_config.config_json 取位置 → 实时调对应平台读取 sig-info.yaml → 解析 repositories
     → 校验每个 repoUrl 都在本次解析结果中（防止前端伪造 / 过期数据）
  2. 事务内对每个 repoConfigs（owner/repo）:
     a. 查 repo_info by repo_url（理论上均为未录入当前项目的仓库，见 §2.2.1 过滤）
     b. 未命中 → insert repo_info (source=sig, sig_config_file=<location path>, 配置取 config)
     c. 命中（全局已存在但当前项目未关联）→ **不覆盖已有配置**（复用现有 repo_info），
        仅 upsert repo_project_ref (repo_id, project_id, source=sig, sig_config_file=location path)
     d. upsert repo_project_ref (repo_id, project_id, source=sig, sig_config_file=location path)
  3. 对每个新入库的 repo：异步同步平台元数据 + 配置 webhook（沿用现有逻辑，不阻塞录入）
  4. 返回 { imported: N, failed: [...] }
```

> **别名冲突**：同一项目内若多个仓库按默认别名生成后仍冲突（如两个仓 repo 名相同），按 `repo名-平台名`、`repo名-平台名2`... 递增直至唯一。

> **前端编辑/删除**：表格中每个仓库行提供「编辑配置」（单条）/ 顶部「批量编辑配置」按钮（作用于所有勾选仓库），复用与手动录入一致的配置表单，默认值见上表，可修改后保存或「恢复默认」；「删除」/「批量删除」用于移除选错、不想录入的仓库（仅从本次待录入列表移除，不影响已入库数据）。

> **SIG 同步已去除**：不再提供「SIG 同步」按钮与 `sig/sync-one` / `sig/sync-all` 接口——SIG 仓库配置全局唯一一份，需要调整配置时直接手动编辑即可（SIG 来源仓库同样允许编辑，见 §2.3）；已录入仓库若要重新从配置文件批量更新，可删除关联后重新执行 SIG 一键录入。

### 2.3 编辑逻辑（直接编辑）

> **核心变化**：不再做「多项目影响提示」与「SIG 来源编辑拦截」——SIG 来源仓库同样允许手动编辑；仓库配置全局唯一一份，编辑直接更新 `repo_info` 即可，自动影响所有关联项目。

```
updateRepoInfo(userId, userName, projectId, RepoDTO):
  1. normalize repoUrl → 按 repo_id 查 repo_info（编辑定位）
  2. update repo_info（全局唯一一份配置，同步影响所有关联项目）
  3. 同步平台元数据 + webhook 配置（沿用现有逻辑）
```

> **说明**：手动录入命中已存在仓库时，前端在录入表单内提示「修改会同步修改之前项目中的代码仓配置」（见 §2.1.3）；编辑已录入仓库时**不做**多项目影响提示。

### 2.4 删除逻辑

```
deleteRepoInfo(userId, userName, repoId, projectId):
  1. 查 repo_project_ref where repo_id=? and is_deleted=0 → 关联项目数 N
  2. N > 1 → 仅删除当前 project 的 ref（repo_info 保留，其他项目仍可用）
  3. N == 1 → 删除 ref + 逻辑删除 repo_info（is_deleted=1）+ 清理 webhook（沿用现有逻辑）
  4. 删除前沿用现有「删除代码平台仓库」审批流程（reviewerId）
```

> **注意**：现有 `deleteProjectRepo` 接口按 `id`（repo_id）删除，不传 `projectId`。改造后需增加 `projectId` 入参以判断是删 ref 还是删 repo_info。前端 `handleDeleteRepo` 调用处需补传 `project.value?.projectId`。

### 2.5 历史存量数据迁移策略

```
migrateRepoProjectRef():
  1. 扫描 repo_info 全表，按 normalize(repo_url) 分组
  2. 对每组（同一 repo_url 的多条记录）:
     a. 选最早 create_at 的记录作为「基准 repo_info」（保留其配置）
     b. 其余记录的 project_id 逐个 insert 到 repo_project_ref（source=manual）
        - 若 (基准 repo_id, project_id) 已存在则跳过
     c. 其余记录逻辑删除（is_deleted=1）
  3. 基准 repo_info 设置 source=manual, sig_config_file=null
  4. repo_project_ref 对基准 repo_id 的所有关联补齐
  5. 回填 repo_info.project_id（过渡期冗余字段）：取 repo_project_ref 中该 repo_id 最早（id 最小 / create_at 最早）关联记录的
     project_id，写入 repo_info.project_id —— 保证未改造仓（framework/anti-poison/sca/gateway/vulnerability）
     继续按旧方式读到 project_id 不中断
  6. 校验：SELECT repo_url_normalized, COUNT(*) FROM repo_info WHERE is_deleted=0
     GROUP BY repo_url_normalized HAVING COUNT(*)>1 → 期望 0 行（全局唯一）
  7. 存量重复清理完成、校验通过后，再择期 ALTER TABLE repo_info
     ADD UNIQUE INDEX uk_repo_url_normalized (repo_url_normalized) 作为兜底（不阻断上线，可放到后续版本）
```

**清理时机（上线后统一执行，不在上线前）**：
- 迁移/清理脚本在**服务上线后统一执行**，上线期间**不在 DB 层加 `repo_url` 唯一约束**，靠**代码层事务内查重 + 锁**保证新录入仓库不重复（见 §5.3 并发控制），规避「上线窗口并发录入触发唯一键冲突」「存量未清理导致加唯一索引直接失败」两个风险。
- 存量不同项目下的重复仓库由该脚本按 `repo_url` 归并（保留最早配置，其余 `project_id` 迁入 `repo_project_ref` 并逻辑删除），执行完成且 `GROUP BY` 校验返回 0 行后再择期加唯一索引。

**灰度开关**：迁移脚本独立执行，不与代码上线耦合。迁移完成后进入双轨期——四仓从 `repo_project_ref` 取 `project_id`，未改造仓仍读 `repo_info.project_id`（详见 §4.4）。

### 2.6 前端实现逻辑

#### 2.6.1 全局配置按钮与弹窗（新增，[Repos/index.vue](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/views/Repos/index.vue)）

- 工具栏在「导出仓库」右侧新增「全局配置」按钮，点击打开全局配置弹窗；原「gitcode 角色映射」「项目公共账号」两个按钮从工具栏移除（能力并入全局配置弹窗）
- 弹窗顶部三个页签：`GitCode` / `Gitee` / `GitHub`，各页签配置项如下：

| 页签 | 项目公共账号 | 代码仓录入配置（sig-info.yaml 位置） | 角色映射 |
|------|-------------|-----------------------------------|---------|
| GitCode | ✅ 直接配置 | ✅ | ✅（gitcode 角色 ↔ openLiBing 角色） |
| Gitee   | ✅ 直接配置 | ✅ | — |
| GitHub  | ✅ 直接配置 | ✅ | — |

- **项目公共账号**：不再只读跳转，直接编辑登录名与令牌。读取调现有 `get-project-common-account`（令牌掩码 `*`，空 token 表示不修改），保存调新增 `update-project-common-account`（令牌加密入库，令牌留空则不覆盖原值），仅需修改某平台时逐平台保存
- **代码仓录入配置**：维护该平台**唯一一个** sig-info.yaml **链接**（表单提供示例链接，用户在对应代码仓、对应分支中找到 sig-info.yaml 后复制完整链接填入），保存时按平台实时校验文件可用性（OK / FILE_NOT_FOUND / PARSE_ERROR），存 `project_global_config.config_json[platform].sigInfoLocation`（存链接字符串）
- **角色映射**：仅 GitCode 页签展示，gitcode 角色 ↔ openLiBing 角色行式编辑（沿用现有 roleMappingDialog 交互），存 `project_global_config.config_json.gitcode.roleMapping`
- 底部「保存」统一提交：公共账号走新增接口、sig-info 位置与角色映射走 `update-global-config`

#### 2.6.2 录入对话框改造（[Repos/index.vue](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/views/Repos/index.vue) 的 `el-dialog`）

- 对话框顶部新增「录入方式」单选切换：`手动录入` / `SIG 组一键录入`
- `手动录入` 模式：沿用现有表单，新增 `repoUrl` blur 时调检测接口（`checkRepoUrl`），命中时按 §2.1.3 自动同步配置 + 选择性删除 + 修改同步提示（**无「一键同步」按钮**）
- `SIG 组一键录入` 模式：
  - 隐藏现有表单字段
  - 顶部提示条：「SIG 组录入默认使用默认配置（别名=仓库名、责任人=建仓人、开源类型=主导开源、各开关=否）；下拉仅展示尚未录入当前项目的 SIG 仓库，已录入的不展示，不会覆盖已有配置；sig-info.yaml 链接在「全局配置」中维护」
  - 新增「平台」下拉（gitcode/gitee/github），**不单独展示配置文件**（每平台位置唯一，在「全局配置」中维护）
  - **「选择仓库」下拉多选框**（调 `listSigReposInConfig`）：仅展示**尚未录入当前项目**的仓库（已录入的不展示），多选后**表格才展示所选仓库列表**
  - 表格列：`选择`、`代码仓`、`代码仓别名`、`平台`、`默认分支`、`仓库责任人`、`开源类型`、`用途`、`代码风格自动修复`、`告警抑制自动检视`、`操作`（`编辑配置` / `删除`）——**无「录入状态」列**
  - 顶部批量操作条：「批量编辑配置」（作用于勾选仓库）/「批量删除」；单条行内「编辑配置」「删除」
  - 底部「一键录入 (N)」按钮 → 调 `sigImport`（N 为表格内仓库数）

#### 2.6.3 列表页改造

- 工具栏新增「全局配置」按钮（§2.6.1）；**无**「SIG 同步」按钮（SIG 同步功能已去除，见 §2.2.3 说明）
- 列表新增列「来源」（手动/SIG），通过 `repo_project_ref.source` 返回
- 编辑按钮：**不做** SIG 来源编辑拦截（SIG 仓库同样可编辑）；删除按钮沿用现有交互

#### 2.6.4 编辑对话框

- **不再做**「多项目影响提示」与「SIG 来源编辑拦截」（已移除，见 §2.3），编辑对话框保持现有表单即可

### 2.7 交互流程示例图

#### 图 0：全局配置弹窗（三页签）

```
┌──────────────────────────────────────────────────────────┐
│  全局配置（对项目下所有代码仓生效）                ✕       │
│  ┌─────────┬────────┬─────────┐                           │
│  │ GitCode │ Gitee  │ GitHub  │                           │
│  └─────────┴────────┴─────────┘                           │
├──────────────────────────────────────────────────────────┤
│  项目公共账号（gitcode）                                   │
│  登录名: [ openlibing-gitcode          ]                  │
│  令牌:   [ ••••••••••••  ] (留空不修改)                   │
├──────────────────────────────────────────────────────────┤
│  代码仓录入配置（sig-info.yaml 链接）  （每平台唯一）     │
│  sig-info.yaml 链接: [ https://gitcode.com/.../sig-info.yaml ]│
│  校验:  可用            (FILE_NOT_FOUND / PARSE_ERROR 标红) │
├──────────────────────────────────────────────────────────┤
│  角色映射（gitcode 角色 ↔ openLiBing 角色）                │
│  gitcode角色  openLiBing角色                               │
│  owner        [ 项目管理员 ▾ ]  ＋  －                    │
│  master       [ 仓库管理员 ▾ ]  ＋  －                    │
│  developer    [ 开发者     ▾ ]  ＋  －                    │
├──────────────────────────────────────────────────────────┤
│                              [保存]  [取消]               │
└──────────────────────────────────────────────────────────┘
```

#### 图 1：手动录入（自动同步配置 + 选择性删除）

```
┌──────────────────────────────────────────────────────────┐
│  录入代码仓                                       ✕       │
│  ◉ 手动录入   ○ SIG 组一键录入                            │
├──────────────────────────────────────────────────────────┤
│  仓库链接: https://gitcode.com/org/repo.git   (blur 检测) │
│                                                          │
│  ℹ 检测到该代码仓已在 项目A、项目B 录入，已将已有配置      │
│    自动同步到下方表单，可直接修改后提交。（无一键同步按钮） │
│                                                          │
│  □ 是否删除之前项目中的代码仓？（可多选，仅取消所选项目    │
│    关联）  ☑ 项目A   ☐ 项目B                              │
│  ⚠ 您未删除之前项目中的代码仓，修改下方配置将同步修改      │
│    项目A、项目B中的该代码仓配置（代码仓配置全局唯一）。    │
├──────────────────────────────────────────────────────────┤
│  托管平台: gitcode     代码仓别名: repo   (可编辑)        │
│  仓库责任人: sig-owner (可编辑)   用途: 自研源码           │
│  ...                                                      │
└──────────────────────────────────────────────────────────┘
```

#### 图 2：SIG 组一键录入（多选未录入仓库 → 表格核对/编辑/删除）

```
┌──────────────────────────────────────────────────────────┐
│  录入代码仓                                       ✕       │
│  ○ 手动录入   ◉ SIG 组一键录入                            │
├──────────────────────────────────────────────────────────┤
│  ℹ 下拉仅展示尚未录入当前项目的 SIG 仓库，已录入的不展示， │
│    不会覆盖已有配置；默认使用默认配置，可编辑或直接使用    │
│  平台: [ gitcode ▾ ]                                      │
│  选择仓库: [ ☑ repo-a ☑ repo-b ☑ repo-d ▾ ](多选，选后表格展示)│
├──────────────────────────────────────────────────────────┤
│  已选 3 个   [批量编辑配置] [批量删除]                     │
│  ☑│ 代码仓      │ 别名   │ 默认分支│ 责任人 │ 开源类型│ 代码风格修复│ 告警抑制 │ 操作            │
│ ──┼────────────┼────────┼─────────┼────────┼────────┼──────────┼─────────┼─────────────────│
│  ☑│ org/repo-a  │ repo-a │ master  │ u-a    │ 主导开源│ 否       │ 否      │ 编辑配置 删除   │
│  ☑│ org/repo-b  │ repo-b │ master  │ u-b    │ 主导开源│ 否       │ 否      │ 编辑配置 删除   │
│  ☑│ org/repo-d  │ repo-d │ main    │ u-d    │ 主导开源│ 是       │ 否      │ 编辑配置 删除   │
├──────────────────────────────────────────────────────────┤
│                          [一键录入 (3)]                   │
└──────────────────────────────────────────────────────────┘
```

## 3. 类设计

### 3.1 后端类设计（openlibing-coderepo-fork）

#### 3.1.1 新增 Entity

```java
/** 仓库-项目关联实体（多对多） */
@Data @Builder @AllArgsConstructor @NoArgsConstructor
@TableName("repo_project_ref")
public class RepoProjectRefEntity implements Serializable {
  @TableId(value = "id", type = IdType.INPUT) private Long id;
  @TableField("repo_id") private Integer repoId;
  @TableField("project_id") private Integer projectId;
  /** 关联建立来源: manual-手动录入, sig-SIG一键录入 */
  @TableField("source") private String source;
  /** SIG 关联时记录的配置文件路径（source=sig 时必填） */
  @TableField("sig_config_file") private String sigConfigFile;
  @TableField("create_at") private Date createAt;
  @TableField("create_by") private String createBy;
  @TableField("update_at") private Date updateAt;
  @TableField("update_by") private String updateBy;
  @TableField("is_deleted") private Boolean isDeleted;
}

/** 项目级全局配置实体（原 project_gitcode_role_mapping 泛化） */
@Data @Builder @AllArgsConstructor @NoArgsConstructor
@TableName("project_global_config")
public class ProjectGlobalConfigEntity implements Serializable {
  @TableId(value = "id", type = IdType.INPUT) private Long id;
  @TableField("project_id") private Integer projectId;
  /** 全局配置 JSON：gitcode.roleMapping + 各平台 sigInfoLocation 等，按平台分键（见 §4.2.1） */
  @TableField("config_json") private String configJson;
  @TableField("create_at") private Date createAt;
  @TableField("create_by") private String createBy;
  @TableField("update_at") private Date updateAt;
  @TableField("update_by") private String updateBy;
  @TableField("is_deleted") private Boolean isDeleted;
}
```

> **原 `GitCodeRoleMappingEntity`（表 `project_gitcode_role_mapping`）作废**：泛化为 `ProjectGlobalConfigEntity`（表 `project_global_config`），`roleMapping` 字段迁移至 `config_json.gitcode.roleMapping`。旧表相关 Mapper/Service（`GitcodeRoleMappingMapper`、`GitcodeRoleMappingService`）改造为基于新表的读写。

#### 3.1.2 现有 Entity 改造

[RepoInfoEntity](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/space/RepoInfoEntity.java) 改动：

| 改动 | 字段 | 说明 |
|------|------|------|
| 保留（过渡期冗余） | `projectId` | **暂不删除**；值回填为 `repo_project_ref` 中该 repo 最早关联记录的 `project_id`，保证未改造仓继续按旧方式读取。四仓改造后不再依赖该字段，后续择期删除 |
| 新增 | `source` | `manual` / `sig`，标记当前仓库配置来源 |
| 新增 | `sigConfigFile` | SIG 来源时记录配置文件链接 |

#### 3.1.3 新增 Mapper

```java
public interface RepoProjectRefMapper extends BaseMapper<RepoProjectRefEntity> {
  /** 查询某 repo 关联的所有项目（含项目名） */
  List<RepoProjectRefEntity> selectByRepoId(@Param("repoId") Integer repoId);
  /** 查询某 project 下的所有 repo 关联 */
  List<RepoProjectRefEntity> selectByProjectId(@Param("projectId") Integer projectId);
  /** upsert 关联（repo_id + project_id 唯一） */
  int upsert(@Param("entity") RepoProjectRefEntity entity);
  /** 统计某 repo 关联的项目数（未删除） */
  int countByRepoId(@Param("repoId") Integer repoId);
  /** 删除某 repo 在某 project 下的关联（逻辑删除） */
  int deleteByRepoAndProject(@Param("repoId") Integer repoId, @Param("projectId") Integer projectId);
}
```

[RepoInfoMapper](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/resources/mapper/RepoInfoMapper.xml) 改造：
- `selectByRepoUrl`：新增，按 normalize 后的 repo_url 查询（用于冲突检测）
- `queryRepoInfo`：现有按 `project_id` 查询改为 JOIN `repo_project_ref`（四仓切换后）
- `addRepoInfo`：保留 `project_id` 列写入（首次录入即最早关联），同时新增 `repo_project_ref` 写入
- `updateRepoInfo`：不变（已按 `repo_id`）

#### 3.1.4 新增 Service

```java
public interface RepoProjectRefService {
  List<RepoProjectRefEntity> listByRepoId(Integer repoId);
  List<RepoProjectRefEntity> listByProjectId(Integer projectId);
  int countByRepoId(Integer repoId);
  void upsert(Integer repoId, Integer projectId, String source, String sigConfigFile,
              String operator);
  void deleteByRepoAndProject(Integer repoId, Integer projectId, String operator);
}

public interface SigRepoImportService {
  /** 保存 sig-info.yaml 位置配置（每平台唯一链接，按平台存 config_json，见 §2.2.0） */
  SigConfigSaveVO saveConfig(String userId, String userName, Integer projectId,
                             String platform, SigLocationDTO location);
  /** 查询该项目某平台配置的 sig-info.yaml 链接（未配置为 null） */
  SigLocationVO listConfig(String userId, Integer projectId, String platform);
  /** 读取某平台 sig-info.yaml 内仓库清单（实时解析，仅返回尚未录入当前项目的仓库 + 默认配置，见 §2.2.1） */
  SigRepoConfigVO listReposInConfig(String userId, Integer projectId, String platform);
  /** 一键录入（默认参数或用户编辑后的配置，见 §2.2.3） */
  SigImportResultVO importRepos(String userId, String userName, Integer projectId,
                                String platform, List<SigRepoConfigItemDTO> repoConfigs);
}

/** 项目级全局配置读写（project_global_config.config_json） */
public interface ProjectGlobalConfigService {
  /** 读取某项目完整全局配置（弹窗回显） */
  GlobalConfigVO getGlobalConfig(String userId, Integer projectId);
  /** 更新某项目全局配置（sig-info 位置 + 角色映射，按平台合并更新 config_json） */
  GlobalConfigVO updateGlobalConfig(String userId, String userName, Integer projectId,
                                    GlobalConfigUpdateDTO dto);
  /** 更新项目公共账号（令牌加密入库，留空不覆盖，见 §6.6） */
  void updateProjectCommonAccount(String userId, String userName, Integer projectId,
                                  ProjectCommonAccountUpdateDTO dto);
}
```

#### 3.1.5 新增工具类 / 处理器

```java
/** sig-info.yaml 读取客户端（接口实时调用，参考 framework GitCode.getYaml 模式独立实现） */
@Component
public class SigInfoClient {
  /** 读取并解析指定位置 sig-info.yaml（owner/repo/branch/path）→ List<{owner, repo}> */
  public List<SigRepoDTO> readYaml(String owner, String repo, String branch, String path);
  /** 校验文件存在且 YAML 可解析（位置保存时实时校验用） */
  public boolean validate(String owner, String repo, String branch, String path);
  /** 获取 gitcode 仓库建仓人账号名（调仓库详情接口） */
  public String getRepoCreator(String owner, String repo);
}

/** SIG 默认录入参数构造器（sig-info.yaml 不含录入参数，全部走默认值） */
@Component
public class SigDefaultParamBuilder {
  /** 生成代码仓别名：先 repo 名；当前项目已存在同名 → repo名-平台名、repo名-平台名2... 递增 */
  public String buildAlias(Integer projectId, String repoName);
  /** 构造 RepoDTO 默认参数（用途=自研源码/语言=不选/开源类型=主导开源/令牌=不填/各开关=否/规则集=不配置） */
  public RepoDTO buildDefault(Integer projectId, String owner, String repo, String creator);
}

/** repo_url 归一化工具 */
public final class RepoUrlNormalizer {
  /** 去末尾斜杠、去 .git 后缀、统一 https、owner/repo 小写 */
  public static String normalize(String repoUrl);
  /** 生成归一化 key（用于应用层查重 / 存量归并，暂不依赖 DB 唯一索引） */
  public static String normalizeKey(String repoUrl);
}
```

> **说明**：`SigInfoClient` 供 `listReposInConfig` / `sigImport` 实时调对应平台读取指定位置 sig-info.yaml；`SigDefaultParamBuilder` 统一构造默认录入参数（别名、建仓人、各开关默认值）。**不再使用 webhook / 定时任务同步 SIG 配置**（去除了原 `SigConfigWebhookHandler` 与 `syncRepoInfoHandler` 中的 SIG 配置同步步骤）；**不再提供 SIG 单个/一键同步**（已去除，见 §2.2.3 说明）。

#### 3.1.6 新增 DTO / VO

```java
/** 跨项目检测请求（手动录入 blur 触发） */
@Data
public class RepoUrlCheckQueryDTO {
  @NotNull private Integer projectId;
  @NotBlank private String repoUrl;
}

/** 跨项目检测结果 */
@Data @Builder
public class RepoUrlCheckVO {
  private Boolean exists;
  private Integer repoId;
  private RepoInfoEntity currentConfig;     // 命中时返回现有配置（前端自动同步到表单）
  private List<AssociatedProjectVO> associatedProjects;  // 该 repo 已关联的项目列表（供选择性删除）
}

/** SIG 仓库（sig-info.yaml 中 owner/repo） */
@Data @Builder
public class SigRepoDTO {
  private String owner;
  private String repo;
}

/** sig-info.yaml 位置配置（保存入参：填写完整链接，后端解析出 owner/repo/branch/path） */
@Data
public class SigLocationDTO {
  @NotBlank private String url;     // 完整链接，如 https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private/sig-info.yaml
  private String remark;            // 备注，可选
}

/** sig-info.yaml 位置配置（查询返回，每个平台至多一个链接） */
@Data @Builder
public class SigLocationVO {
  private String url;               // 完整链接（未配置为 null）
  private String remark;
}

/** 全局配置更新入参（update-global-config，按平台合并更新 config_json） */
@Data
public class GlobalConfigUpdateDTO {
  @NotNull private Integer projectId;
  @NotBlank private String platform;                    // gitcode / gitee / github
  /** 该平台 sig-info.yaml 位置（唯一；传 null 表示清空该平台位置） */
  private SigLocationDTO sigInfoLocation;
  /** 仅 gitcode 页签使用：gitcode 角色 ↔ openLiBing 角色映射（替换原 roleMapping） */
  private List<RoleMappingItemDTO> roleMapping;
}

/** 角色映射项 */
@Data
public class RoleMappingItemDTO {
  @NotBlank private String gitcodeRole;     // owner / master / developer ...
  @NotBlank private String openlibingRole;  // project_admin / repo_admin / developer ...
}

/** 全局配置查询返回（get-global-config，弹窗回显） */
@Data @Builder
public class GlobalConfigVO {
  private Integer projectId;
  /** 各平台配置（与 config_json 结构一致，见 §4.2.1） */
  private GlobalPlatformConfigVO gitcode;
  private GlobalPlatformConfigVO gitee;
  private GlobalPlatformConfigVO github;
  /** 各平台项目公共账号（登录名 + 掩码令牌，令牌已脱敏） */
  private CommonAccountVO commonAccount;
}

/** 单平台全局配置 */
@Data @Builder
public class GlobalPlatformConfigVO {
  private List<RoleMappingItemDTO> roleMapping;   // 仅 gitcode 有值
  private SigLocationVO sigInfoLocation;          // 该平台唯一 sig-info.yaml 链接（未配置为 null）
}

/** 项目公共账号（令牌脱敏返回） */
@Data @Builder
public class CommonAccountVO {
  private String gitcodeLogin;
  private String gitcodeTokenMasked;   // 掩码如 ******（存在则有值）
  private String giteeLogin;
  private String giteeTokenMasked;
  private String githubLogin;
  private String githubTokenMasked;
}

/** 项目公共账号更新入参（update-project-common-account，留空不覆盖） */
@Data
public class ProjectCommonAccountUpdateDTO {
  @NotNull private Integer projectId;
  @NotBlank private String platform;            // gitcode / gitee / github
  private String login;                         // 登录名（非空则更新）
  private String token;                         // 令牌（留空则不改原值，避免空覆盖）
}

/** sig-info.yaml 位置保存结果（含可用性校验） */
@Data @Builder
public class SigConfigSaveVO {
  private SigLocationHealthVO location;  // 保存后该平台唯一位置的可用性（未配置为 null）
}

/** 位置可用性（保存时实时校验） */
@Data @Builder
public class SigLocationHealthVO {
  private String url;      // 该平台唯一链接（未配置为 null）
  private String status;   // OK / FILE_NOT_FOUND / PARSE_ERROR
  private String error;    // 失败原因（不暴露 token）
}

/** SIG 配置内仓库清单 */
@Data @Builder
public class SigRepoConfigVO {
  private String platform;
  private String owner;
  private String repo;
  private String branch;
  private String path;
  private List<SigRepoItemVO> repos;
}

@Data @Builder
public class SigRepoItemVO {
  private String owner;
  private String repo;
  private String repoUrl;
  private String platform;
  /** 默认配置（sig-info.yaml 不含录入参数，默认值见 §2.2.3 默认参数表，可编辑） */
  private SigRepoConfigItemDTO defaultConfig;
}

/** SIG 录入配置项（单条仓库的录入参数，用于下拉回显默认值与 sig/import 入参） */
@Data
public class SigRepoConfigItemDTO {
  @NotBlank private String repoUrl;              // owner/repo 组装后的完整链接
  private String alias;                          // 默认别名（repo 名 / repo名-平台名）
  private String defaultBranchName;              // 默认分支（平台仓库默认分支）
  private String repoOwner;                      // 仓库责任人（建仓人账号名）
  private String purpose;                        // 用途（默认自研源码）
  private String openSource;                     // 开源类型（默认主导开源）
  private String repoLanguage;                   // 语言（默认不选）
  private Boolean isAutoFormat;                  // 代码风格自动修复（默认否）
  private Boolean isSuppressionEnabled;          // 告警抑制自动检视（默认否）
  // ... 其余录入参数与手动录入表单一致
}

/** SIG 一键录入结果 */
@Data @Builder
public class SigImportResultVO {
  private Integer imported;   // 新增数（含新建 repo_info 与新建当前项目关联）
  private List<String> failedRepoUrls;
}

/** 关联项目信息（编辑/删除时提示用） */
@Data @Builder
public class RepoAssociationVO {
  private Integer projectCount;
  private List<AssociatedProjectVO> projects;
}
```

#### 3.1.7 现有类扩展

| 类 | 改动 |
|------|------|
| [RepoController](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/RepoController.java) | 新增 `check-repo-url`、`global-config`（get/update）、`update-project-common-account`、`sig/config`（保存/查询位置配置，带 platform）、`sig/repos`、`sig/import`；`delete-repo` 入参加 `projectId`（`get-repo-association` 仅在删除场景按需保留） |
| [RepoDTO](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/dto/space/RepoDTO.java) | 新增 `deleteProjectIds`（List\<Integer\>，手动录入命中已存在仓库时，勾选要删除关联的「之前项目」ID 列表；不传表示不删除，修改配置同步影响所有仍关联项目） |
| [RepoService](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/RepoService.java) | `addRepoInfo` 增加「命中已存在」分支（自动同步 + 选择性删除 `deleteProjectIds`）；`updateRepoInfo` 直接编辑（**无** sig 拦截、**无**多项目确认）；`deleteRepoInfo` 增加 `projectId` 入参；新增 `checkRepoUrl` |
| [RepoServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java) | 实现上述改造；`queryRepoInfo` SQL 改 JOIN `repo_project_ref`；SIG 相关委托 `SigRepoImportService` |
| [RepoInfoMapper.xml](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/resources/mapper/RepoInfoMapper.xml) | `queryRepoInfo` 改 JOIN；新增 `selectByRepoUrl`；`addRepoInfo` 保留 `project_id` 列写入（首次录入即最早关联） |
| 新增 [ProjectGlobalConfigServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/) | 实现 `ProjectGlobalConfigService`：`config_json` 读写（Jackson 序列化/反序列化，按平台合并）、公共账号更新（复用现有加密逻辑） |
| 改造 [GitcodeRoleMappingMapper.xml](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/resources/mapper/GitcodeRoleMappingMapper.xml) | 原 `project_gitcode_role_mapping` 读写改为 `project_global_config.config_json.gitcode.roleMapping` 读写 |
| 改造 [ProjectCommonAccountServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/) | 新增 `updateProjectCommonAccount`（登录名 + 令牌按平台更新，令牌加密入库、留空不覆盖） |

### 3.2 前端类设计（openlibing-web）

#### 3.2.1 [Repos/index.vue](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/views/Repos/index.vue) 改造

```typescript
// 录入对话框新增状态
const importMode = ref<'manual' | 'sig'>('manual');
const repoUrlCheck = ref<RepoUrlCheckVO | null>(null);   // check-repo-url 检测结果
const deleteProjectIds = ref<number[]>([]);             // 选择性删除：勾选的「之前项目」ID
const sigLocation = ref<SigLocationVO | null>(null);      // 当前平台 sig-info.yaml 位置（唯一）
const selectedSigPlatform = ref<'gitcode' | 'gitee' | 'github'>('gitcode');
const sigCandidateRepos = ref<SigRepoItemVO[]>([]);       // 尚未录入当前项目的候选仓库（下拉多选）
const sigSelectedRepos = ref<SigRepoItemVO[]>([]);        // 选出后表格展示的仓库（含可编辑配置）
const sigCheckedUrls = ref<string[]>([]);                 // 表格勾选（用于批量编辑/批量删除）

// 全局配置弹窗新增状态（三页签：gitcode / gitee / github）
const globalConfigDialogVisible = ref(false);
const activeGlobalTab = ref<'gitcode' | 'gitee' | 'github'>('gitcode');
const globalConfig = ref<GlobalConfigVO | null>(null);   // get-global-config 回显
const platformConfig = computed(() => globalConfig.value?.[activeGlobalTab.value]);
const commonAccountForm = ref<CommonAccountVO | null>(null);

// 方法
function onRepoUrlBlur() {
  // 调 checkRepoUrl（防抖 300ms）→ exists=true 时：
  //   自动把 currentConfig 同步到表单（可修改）；
  //   展示「是否删除之前项目中的代码仓」多选（deleteProjectIds）；
  //   未勾选删除项时提示「修改会同步修改之前项目中的代码仓配置」
}
function openGlobalConfigDialog() {
  // 打开「全局配置」弹窗 → 调 getGlobalConfig 回显三个页签 + 公共账号
}
function switchGlobalTab(tab: 'gitcode' | 'gitee' | 'github') {
  // 切换页签；回显该平台唯一 sig-info 位置（实时校验可用性）
}
function saveCommonAccount(platform: string, form: { login?: string; token?: string }) {
  // 调 updateProjectCommonAccount（token 留空不覆盖原值），逐平台保存
}
function saveSigConfig(platform: string, location: SigLocationDTO | null) {
  // 调 updateGlobalConfig（携带 platform + sigInfoLocation + roleMapping）
  // → 展示位置可用性（OK/文件不存在/解析失败）；null 表示清空该平台位置
}
function saveRoleMapping(items: RoleMappingItemDTO[]) {
  // 调 updateGlobalConfig（platform=gitcode + roleMapping）
}
function loadSigConfigFiles() {
  // 调 listSigConfigFiles（实时读取当前平台唯一位置 sig-info.yaml 并统计仓库数；未配置标记 NOT_CONFIGURED）
}
function onSigPlatformChange(platform: 'gitcode' | 'gitee' | 'github') {
  // 切换平台 → 调 listSigReposInConfig（实时解析，仅返回尚未录入当前项目的仓库 + 默认配置）
}
function onSigReposSelected(selected: SigRepoItemVO[]) {
  // 下拉多选确认后 → sigSelectedRepos=selected，表格展示所选仓库（默认配置）
}
function editSigRepoConfig(row) { /* 单条「编辑配置」，复用手动录入配置表单，可恢复默认 */ }
function batchEditSigRepoConfig() { /* 「批量编辑配置」作用于所有勾选仓库 */ }
function removeSigRepo(row) { /* 单条「删除」：从本次待录入列表移除 */ }
function batchRemoveSigRepo() { /* 「批量删除」：移除所有勾选仓库 */ }
function sigImport() {
  // 调 sigImport，入参 = sigSelectedRepos 映射为 repoConfigs（含用户编辑后的配置或默认值）
}
function openEditDialog(row) { /* 直接打开编辑表单（无多项目提示、无 SIG 拦截） */ }
```

> **全局配置弹窗**：工具栏「导出仓库」右侧新增「全局配置」按钮；弹窗三页签。各页签「项目公共账号」直接编辑（参考 [Project/projectAddEditForm.vue](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/views/Project/projectAddEditForm.vue) 的公共账号配置项），「代码仓录入配置」维护该平台**唯一** sig-info.yaml 位置，「角色映射」仅 gitcode 页签（沿用 [Repos/roleMappingDialog.vue](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/views/Repos/roleMappingDialog.vue) 交互）。保存按平台分别调 `update-project-common-account` 与 `update-global-config`。

#### 3.2.2 API 层扩展

```typescript
// api.ts 新增
export const checkRepoUrl = (cfg) => apiClient.post(urls.CHECK_REPO_URL, cfg.data, cfg);
export const getRepoAssociation = (cfg) => apiClient.get(urls.GET_REPO_ASSOCIATION, cfg);
export const getGlobalConfig = (cfg) => apiClient.get(urls.GLOBAL_CONFIG, cfg);
export const updateGlobalConfig = (cfg) => apiClient.post(urls.GLOBAL_CONFIG, cfg.data);
export const updateProjectCommonAccount = (cfg) => apiClient.post(urls.UPDATE_PROJECT_COMMON_ACCOUNT, cfg.data);
export const saveSigConfig = (cfg) => apiClient.post(urls.SIG_CONFIG, cfg.data);
export const listSigConfig = (cfg) => apiClient.get(urls.SIG_CONFIG, cfg);
export const listSigReposInConfig = (cfg) => apiClient.post(urls.SIG_REPOS, cfg.data);
export const sigImport = (cfg) => apiClient.post(urls.SIG_IMPORT, cfg.data);

// url.ts 新增
export const CHECK_REPO_URL = CODE_REPO + '/project-repo/check-repo-url';
export const GET_REPO_ASSOCIATION = CODE_REPO + '/project-repo/get-repo-association';
export const GLOBAL_CONFIG = CODE_REPO + '/project-repo/global-config';
export const UPDATE_PROJECT_COMMON_ACCOUNT = CODE_REPO + '/project-repo/update-project-common-account';
export const SIG_CONFIG = CODE_REPO + '/project-repo/sig/config';
export const SIG_REPOS = CODE_REPO + '/project-repo/sig/repos';
export const SIG_IMPORT = CODE_REPO + '/project-repo/sig/import';
```

## 4. 数据模型设计

### 4.1 新增表 `repo_project_ref`

```sql
CREATE TABLE repo_project_ref (
    id BIGINT UNSIGNED PRIMARY KEY COMMENT '主键ID，雪花算法生成',
    repo_id INT NOT NULL COMMENT '关联 repo_info.repo_id',
    project_id INT NOT NULL COMMENT '关联项目ID',
    source VARCHAR(16) NOT NULL DEFAULT 'manual' COMMENT '关联建立来源: manual-手动, sig-SIG一键录入',
    sig_config_file VARCHAR(512) NULL COMMENT 'SIG关联时记录的配置文件路径(source=sig时必填)',
    create_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    create_by VARCHAR(64) NOT NULL COMMENT '创建人',
    update_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    update_by VARCHAR(64) NULL COMMENT '更新人',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '是否删除: 0-否, 1-是',
    UNIQUE INDEX uk_repo_project (repo_id, project_id, is_deleted),
    INDEX idx_project_id (project_id),
    INDEX idx_repo_id (repo_id),
    INDEX idx_source (source)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='仓库-项目关联表(多对多)';
```

**字段设计说明**：

| 字段 | 设计考量 |
|------|---------|
| `id` | 雪花算法生成，避免自增主键锁竞争 |
| `repo_id` | 关联 `repo_info.repo_id`，一个 repo 可关联多 project |
| `project_id` | 关联项目，一个 project 可关联多 repo |
| `source` | 关联建立方式。手动录入建立的关联=manual，SIG 录入建立的关联=sig。用于标记关联建立来源（支撑 SIG 录入仅展示未录入当前项目的仓库、列表按来源筛选统计） |
| `sig_config_file` | SIG 关联时记录的配置文件链接（source=sig 时记录，用于定位来源位置） |
| `uk_repo_project` | 联合唯一约束（含 `is_deleted` 软删除标记），防止同一 repo 同一 project 重复关联 |
| `idx_project_id` | 列表页按项目查询主路径 |
| `idx_repo_id` | 编辑/删除时查关联项目数 |

### 4.2 现有表 `repo_info` 改造

```sql
-- 1. 新增字段
ALTER TABLE repo_info ADD COLUMN source VARCHAR(16) NOT NULL DEFAULT 'manual'
  COMMENT '仓库配置来源: manual-手动录入, sig-SIG一键录入' AFTER default_branch_name;
ALTER TABLE repo_info ADD COLUMN sig_config_file VARCHAR(512) NULL
  COMMENT 'SIG来源时记录的配置文件链接' AFTER source;

-- 2. 数据迁移（见 §2.5）中，对 repo_url 归一化（暂不加唯一索引）
ALTER TABLE repo_info ADD COLUMN repo_url_normalized VARCHAR(512) NULL
  COMMENT '归一化后的repo_url(去.git/末尾斜杠/统一小写owner-repo)';
-- 应用层回填 repo_url_normalized，加普通索引用于冲突检测/查重
ALTER TABLE repo_info ADD INDEX idx_repo_url_normalized (repo_url_normalized);
-- 唯一索引暂不添加：待存量重复仓库上线后统一清理、GROUP BY 校验 0 行后，再择期升级为唯一索引兜底
-- ALTER TABLE repo_info ADD UNIQUE INDEX uk_repo_url_normalized (repo_url_normalized);

-- 3. project_id 暂不删除（过渡期冗余）：迁移时回填为 repo_project_ref 中该 repo 最早关联记录的 project_id，
--    保证未改造仓（framework/anti-poison/sca/gateway/vulnerability）继续按旧方式读取不中断。
--    待四仓（coderepo/codecheck/cicd/sbom）全面切换为从 repo_project_ref 取 project_id、且其余仓完成切换后再择期删除：
-- ALTER TABLE repo_info DROP COLUMN project_id;
```

**repo_url 归一化规则**（应用层 [RepoUrlNormalizer](#316-新增工具类)）：
- 去末尾斜杠
- 去 `.git` 后缀
- 统一 `https://` 协议头（`http://` → `https://`，`git@host:` SSH 形式 → `https://host/`）
- owner/repo 部分小写（GitCode/Gitee/GitHub 的 owner/repo 大小写不敏感）

归一化后存入 `repo_url_normalized`（先加普通索引用于冲突检测/查重；暂不加唯一索引，存量清理完成后择期升级），`repo_url` 原值保留用于展示与跳转。

#### 4.2.1 改造表 `project_global_config`（原 `project_gitcode_role_mapping` 泛化）

**改造思路**：将原 `project_gitcode_role_mapping`（仅存 GitCode 角色映射）泛化为项目级通用配置表 `project_global_config`。所有项目级配置项（GitCode 角色映射、各平台 sig-info.yaml 位置等）**统一以 JSON 存入 `config_json`**，后续新增配置项只需在 JSON 中扩展、无需再改表结构。

**SIG 配置内容不落库**：sig-info.yaml 由各接口实时调对应平台读取解析，本表只保存位置元数据（含在 `config_json` 中）。

```sql
-- 1. 原 project_gitcode_role_mapping 表重命名 + 增加 config_json 字段
RENAME TABLE project_gitcode_role_mapping TO project_global_config;

ALTER TABLE project_global_config
    ADD COLUMN config_json JSON NULL COMMENT '项目级全局配置(JSON)：含各平台 sig-info.yaml 位置、gitcode 角色映射等，按平台分键存储，便于后续扩展新配置项' AFTER project_id;

-- 2. 数据迁移：将原 role_mapping 文本（gitcode 角色映射 JSON 数组字符串）迁移到
--    config_json 的 gitcode.roleMapping 键，然后删除旧字段（见 §2.5）
-- ALTER TABLE project_global_config DROP COLUMN role_mapping;
```

**改造后表结构**：

```sql
CREATE TABLE project_global_config (
    id BIGINT UNSIGNED PRIMARY KEY COMMENT '主键ID，雪花算法生成',
    project_id INT NOT NULL COMMENT '所属项目ID',
    config_json JSON NULL COMMENT '项目级全局配置(JSON)：gitcode.roleMapping + 各平台 sigInfoLocation 等，按平台分键，可扩展',
    create_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    create_by VARCHAR(64) NOT NULL COMMENT '创建人',
    update_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    update_by VARCHAR(64) NULL COMMENT '更新人',
    is_deleted TINYINT NOT NULL DEFAULT 0 COMMENT '是否删除: 0-否, 1-是',
    UNIQUE INDEX uk_project (project_id, is_deleted)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_0900_ai_ci COMMENT='项目级全局配置表(通用，各配置项以 JSON 存储)';
```

**`config_json` 数据结构（约定，按平台分键）**：

```jsonc
{
  "gitcode": {
    "roleMapping": [                       // GitCode 角色映射（原 role_mapping 内容迁移至此）
      { "gitcodeRole": "owner",     "openlibingRole": "project_admin" },
      { "gitcodeRole": "master",    "openlibingRole": "repo_admin" },
      { "gitcodeRole": "developer", "openlibingRole": "developer" }
    ],
    "sigInfoLocation": {                   // 该平台 sig-info.yaml 位置（唯一，可为 null 表示未配置）
      "owner": "openlibing", "repo": "community-private",
      "branch": "master", "path": "openLiBing-private/sigs/openLiBing-private/sig-info.yaml",
      "remark": "openLiBing SIG 组"
    }
  },
  "gitee": {
    "sigInfoLocation": {
      "owner": "openlibing", "repo": "gitee-sig",
      "branch": "master", "path": "sig-info.yaml", "remark": ""
    }
  },
  "github": {
    "sigInfoLocation": {
      "owner": "openlibing", "repo": "github-sig",
      "branch": "main", "path": "sig-info.yaml", "remark": ""
    }
  }
}
```

> **项目公共账号不存本表**：仍存 `project_common_account_info`（登录名 + 加密令牌），被 gitcode/gitee/github API 调用等多服务读取，保持现状避免迁移；全局配置弹窗仅新增直接写入接口（§6.6）。后续如需将公共账号也纳入 JSON，可平滑扩展（本期不做）。

**设计说明**：

| 维度 | 说明 |
|------|------|
| 粒度 | 每个项目一条记录，`config_json` 内按平台（gitcode/gitee/github）分键存储各类配置项 |
| 写入方 | `update-global-config`（§2.6.1）在代码仓管理「全局配置」弹窗保存：sig-info 位置 + 角色映射；公共账号另走 `update-project-common-account`（§6.6） |
| 读取方 | 角色映射：现有成员同步/鉴权逻辑；sig-info 位置：`listSigConfig` / `listSigReposInConfig` / `sigImport` 读位置元数据后，再实时调对应平台读取 sig-info.yaml |
| 实时性 | sig-info.yaml 内容以对应平台实时文件为准，**不缓存、不落库**；SIG 组改文件即生效，位置变更只需改 `config_json` |
| 安全性 | 读取位置受本表 `config_json` 约束（白名单），防止任意文件读取（见 §7.2） |
| 可扩展性 | 各配置项以 JSON 存储，后续新增配置项（如默认参数、更多平台）只需扩展 JSON 键，无需加字段 |

> **去除了原「`project_repo_info` 表新增 json 字段（sig_config_json / sig_config_file / sig_config_sha / repo_key）」的方案**：不再 webhook 入库缓存，`project_repo_info` 保持现状不变。

### 4.3 sig-info.yaml 配置文件结构（固定格式）

配置文件位于用户配置的仓路径下（§2.2.0b），例如 `https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private/sig-info.yaml`。

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

**格式说明**：
- 顶层 `repositories` 为列表，列表项为 `- repo:`，其值为该组下的代码仓清单（`owner/repo` 字符串列表，可多行）。
- **不含任何录入参数**：别名、责任人、用途、语言、开源类型、令牌、接管 PR、各自动触发开关、规则集 均不在此文件中声明，录入时全部使用默认值（见 §2.2.3）。
- 每个 `owner/repo` 按位置所属平台组装完整 repoUrl：`https://gitcode.com/{owner}/{repo}.git`（gitcode）/ `https://gitee.com/{owner}/{repo}.git`（gitee）/ `https://github.com/{owner}/{repo}.git`（github）。
- **支持多平台**：同一项目可在 gitcode / gitee / github 三个平台分别配置位置（`config_json[platform].sigInfoLocation`），各平台各自的 sig-info.yaml 格式一致，位置所属平台即仓库所属平台。

### 4.4 双写过渡期策略

过渡期 `repo_info.project_id` **保留不删**，迁移时回填为 `repo_project_ref` 中该 repo 最早关联记录的 `project_id`，双轨兼容：

- **四仓（coderepo/codecheck/cicd/sbom）**：全面切换为从 `repo_project_ref` 取 `project_id`（查询 JOIN 关联表，写入同时维护两表），不再依赖 `repo_info.project_id`
- **其余仓（framework/anti-poison/sca/gateway/vulnerability）**：暂不修改，仍从 `repo_info.project_id` 读取（值为最早关联 project_id，过渡期单项目语义可接受，见 §1.2 说明）
- `addRepoInfo`：写 `repo_info`（保留 `project_id` 写入，首次录入即最早关联）+ 写 `repo_project_ref`
- `queryRepoInfo`（四仓）：JOIN `repo_project_ref` 取 `project_id`
- **后续版本**：其余仓逐个切换为从 `repo_project_ref` 取 `project_id`，全部切换完成后，灰度开关 `coderepo.repo-decouple.enabled=true` 仅走新模型，最后 `DROP COLUMN project_id`

### 4.5 ER 关系

```
project (1) ──── (N) repo_project_ref (N) ──── (1) repo_info
                     │                            │
                     │ source: manual/sig         │ repo_url_normalized
                     │ sig_config_file            │ source: manual/sig
                     │                            │ sig_config_file
                     │
                     └─ uk(repo_id, project_id)

project (1) ──── (1) project_global_config ──实时读取──▶ SIG 仓 sig-info.yaml (gitcode/gitee/github)
                      config_json[平台].sigInfoLocation          │ 解析 repositories
                                          + roleMapping           ▼
                                        repo_info (source=sig) + repo_project_ref (source=sig)
```

### 4.6 数据量预估

| 维度 | 估算 |
|------|------|
| repo_info | 现有规模不变（去重后略减），单表 < 10 万行 |
| repo_project_ref | repo 数 × 平均关联项目数（1.2），约 12 万行 |
| 单项目仓库数 | 平均 50-200，列表查询走 `idx_project_id`，毫秒级 |
| SIG 位置配置 | 每项目每平台最多 1 个 sig-info.yaml 链接（gitcode/gitee/github 共 ≤3 个，存 config_json）；sig-info.yaml 内容不落库，仓库数实时读取 |

## 5. 性能设计

### 5.1 数据库性能

#### 5.1.1 索引策略

| 表 | 索引 | 服务场景 |
|------|------|---------|
| `repo_info` | `idx_repo_url_normalized (repo_url_normalized)`（普通索引，暂不唯一） | 冲突检测 / 新录入查重；存量清理完成后可升级为唯一索引 |
| `repo_project_ref` | `uk_repo_project (repo_id, project_id, is_deleted)` | 防重复关联 + upsert |
| | `idx_project_id (project_id)` | 列表页按项目查询 |
| | `idx_repo_id (repo_id)` | 编辑/删除时查关联项目数 |
| | `idx_source (source)` | 按 sig 关联筛选 / 列表按来源统计 |
| `project_global_config` | `uk_project (project_id, is_deleted)` | 每项目一条，按项目查全局配置（sig-info 位置 + 角色映射） |

#### 5.1.2 查询优化

- `queryRepoInfo`：`repo_project_ref` JOIN `repo_info` ON `repo_id` WHERE `project_id=?`，走 `idx_project_id`，单次查询 < 50ms
- `checkRepoUrlConflict`：按 `repo_url_normalized` 索引查询，< 10ms
- `getRepoAssociation`：按 `repo_id` 查 `repo_project_ref`，< 10ms

#### 5.1.3 批量插入

- SIG 一键录入：单次最多 100 个仓库，事务内循环 upsert，单事务 < 2s
- upsert 用 `INSERT ... ON DUPLICATE KEY UPDATE`，避免先查后写的并发问题

### 5.2 配置读取设计（实时调对应平台）

> 去除 webhook / 入库缓存：sig-info.yaml 由各接口**实时调对应平台（gitcode/gitee/github）读取并解析**（§2.2），保证读到最新配置，无缓存一致性与事件丢失问题。

#### 5.2.1 配置读取路径

- **位置元数据**：`listSigConfig` 读 `project_global_config.config_json`（按项目唯一，走 `uk_project`），毫秒级
- **实时读取**：`listSigReposInConfig` / `sigImport` 对该平台唯一位置调**对应平台**（gitcode/gitee/github）`getFileContent` 读取 sig-info.yaml → `SigInfoClient` 解析 repositories（§4.3）
- **超时与降级**：平台调用设置超时（如 3s），单个平台位置失败不影响其他平台（标记 UNREACHABLE）；全部失败返回明确错误提示稍后重试
- **并发读取优化**：不同平台的唯一位置独立读取（互不阻塞）；单平台仅一个位置，无需并行放大

#### 5.2.2 不引入缓存的部分

- `repo_info` 查询：走索引足够快，不引入缓存避免一致性问题
- `checkRepoUrlConflict`：每次录入必查最新，不缓存
- sig-info.yaml：内容以 gitcode 实时文件为准，不缓存（保证 SIG 组改文件即生效）；若后续调用量增大，可评估按 `(owner/repo/branch/path, sha)` 短时缓存，本期不做

### 5.3 并发控制

- **录入并发**：同一 `repo_url` 两个项目同时首次录入 → 应用层在事务内按 `repo_url_normalized` 查重（`SELECT ... FOR UPDATE` 锁行 / 分布式锁串行化），后到者查到已存在走「命中」分支（前端已自动同步配置，提交时按表单更新配置 + 可选选择性删除之前项目关联，见 §2.1）；**不依赖 DB 唯一索引兜底**（存量清理完成前不加唯一约束，见 §2.5 清理时机）
- **SIG 录入并发**：同一 project 同时两次 SIG 录入 → `uk_repo_project` 兜底，upsert 幂等
- **编辑并发**：沿用现有乐观锁（`update_at` 版本号，如有）

### 5.4 前端性能

| 维度 | 策略 |
|------|------|
| 冲突预查 | `repoUrl` blur 时防抖 300ms 后调 `checkRepoUrlConflict` |
| SIG 仓库清单 | 平台切换时实时加载，loading 态；表格虚拟滚动（>100 行） |
| 一键录入 | loading 态 + 禁用按钮，防重复提交 |
| 列表页 | 沿用现有分页（10/20/40/50） |

### 5.5 性能验收指标

| 指标 | 目标 |
|------|------|
| `checkRepoUrlConflict` 响应 | < 100ms |
| `queryRepoInfo` 响应（含 JOIN） | < 100ms（与改造前持平） |
| `sigImport`（50 个仓库） | < 3s（含一次 sig-info.yaml 实时读取 + 建仓人查询） |
| `listSigReposInConfig`（实时读取单位置） | < 500ms |
| 历史迁移脚本（10 万行 repo_info） | < 10 分钟 |

## 6. API 接口设计

### 6.1 现有接口改造：`POST /project-repo/add-repo`

**位置**：[RepoController.addRepoInfo](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/RepoController.java#L167-L178)

**请求体**在 [RepoDTO](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/dto/space/RepoDTO.java) 基础上新增字段：

```jsonc
{
  // ... 现有字段不变（含表单配置） ...
  "deleteProjectIds": [3]   // 新增, 可选: 手动录入命中已存在仓库时，勾选「是否删除之前项目中的代码仓」的项目 ID 列表；
                            // 空数组/不传表示不删除，修改配置同步影响所有仍关联项目（前端已提示）
}
```

**响应**（不变）：`DataResult<Integer>`（repoId）

**业务变化**：见 §2.1。`repo_url` 命中已存在仓库时**自动同步其配置到表单**（前端 blur 时已调 check-repo-url），提交时按表单更新配置（未删除之前项目时同步影响所有仍关联项目）、可选按 `deleteProjectIds` **选择性删除**所选项目关联（仅取消关联，repo_info 保留）。后端按归一化 `repo_url` 二次查重防并发。

### 6.2 现有接口改造：`POST /project-repo/update-repo`

**请求体**：沿用现有字段（配置按表单提交）

**业务变化**：
- 直接更新 `repo_info`（全局唯一一份配置，同步影响所有关联项目）
- **不再**做 SIG 来源拦截（`source=sig` 的仓库同样允许编辑）
- **不再**做多项目关联二次确认（`confirm` 字段移除）

### 6.3 现有接口改造：`POST /project-repo/delete-repo`

**入参**新增 `projectId`：

```
POST /project-repo/delete-repo?userId=xxx&userName=xxx&id={repoId}&projectId={projectId}
```

**业务变化**：见 §2.4，按 `projectId` 判定删 ref 还是删 repo_info。

### 6.4 新增接口 1：`POST /project-repo/check-repo-url`

**用途**：手动录入时 `repoUrl` blur 触发，检测 repo_url 全局是否已存在；命中时返回现有配置（前端**自动同步到表单**）与已关联项目列表（供**选择性删除**）。

**请求**：
```jsonc
{ "userId": "xxx", "projectId": 1, "repoUrl": "https://gitcode.com/org/repo.git" }
```

**响应（未存在）**：
```jsonc
{ "code": 200, "data": { "exists": false } }
```

**响应（已存在）**：
```jsonc
{
  "code": 200,
  "data": {
    "exists": true,
    "repoId": 1001,
    "currentConfig": {
      "repoName": "repo", "repoOwner": "sig-owner", "purpose": "自研源码",
      "openSource": "lead", "assumePr": "1", "autoTrigger": "1",
      "autoTriggerDesignScan": "0", "isAutoFormat": false,
      "isSuppressionEnabled": true, "disallowSelfMerge": 1,
      "disallowUnresolvedDiscussionsMerge": 0, "repoLanguage": "java"
    },
    "associatedProjects": [
      { "projectId": 2, "projectName": "项目A" },
      { "projectId": 3, "projectName": "项目B" }
    ]
  }
}
```

前端据 `exists=true`：将 `currentConfig` 自动同步到表单（可修改）；展示「是否删除之前项目中的代码仓」多选（`associatedProjects`）；未勾选删除项时提示「修改会同步修改之前项目中的代码仓配置」。

### 6.5 新增接口 2：`GET /project-repo/get-repo-association`

**用途**：删除前查询仓库关联的项目列表（判定仅解除当前项目关联还是删除仓库）。

**请求**：`GET /project-repo/get-repo-association?userId=xxx&repoId=1001`

**响应**：
```jsonc
{
  "code": 200,
  "data": {
    "projectCount": 3,
    "projects": [
      { "projectId": 1, "projectName": "当前项目", "source": "manual" },
      { "projectId": 2, "projectName": "项目A", "source": "manual" },
      { "projectId": 3, "projectName": "项目B", "source": "sig" }
    ]
  }
}
```

### 6.6 新增接口 3：`GET /project-repo/global-config`（查询全局配置）

**用途**：打开「全局配置」弹窗时回显三个页签数据（gitcode/gitee/github 各平台的代码仓录入配置 + 角色映射 + 项目公共账号）。

**数据来源**：读 `project_global_config.config_json`（按平台分键，§4.2.1）+ `project_common_account_info`（登录名 + 掩码令牌）。

**请求**：`GET /project-repo/global-config?userId=xxx&projectId=1`

**响应**：
```jsonc
{
  "code": 200,
  "data": {
    "projectId": 1,
    "gitcode": {
      "roleMapping": [
        { "gitcodeRole": "owner", "openlibingRole": "project_admin" },
        { "gitcodeRole": "master", "openlibingRole": "repo_admin" },
        { "gitcodeRole": "developer", "openlibingRole": "developer" }
      ],
      "sigInfoLocation": {
        "owner": "openlibing", "repo": "community-private",
        "branch": "master", "path": "openLiBing-private/sigs/openLiBing-private/sig-info.yaml",
        "remark": "openLiBing SIG 组"
      }
    },
    "gitee":  { "sigInfoLocation": null },   // 未配置
    "github": { "sigInfoLocation": null },   // 未配置
    "commonAccount": {
      "gitcodeLogin": "openlibing-gitcode", "gitcodeTokenMasked": "******",
      "giteeLogin": "", "giteeTokenMasked": null,
      "githubLogin": "", "githubTokenMasked": null
    }
  }
}
```

### 6.7 新增接口 4：`POST /project-repo/global-config`（更新全局配置）

**用途**：全局配置弹窗保存某平台配置（代码仓录入配置 + gitcode 角色映射），按平台合并更新 `config_json`。

**请求**：
```jsonc
{
  "userId": "xxx", "userName": "xxx",
  "projectId": 1,
  "platform": "gitcode",        // gitcode / gitee / github
  "sigInfoLocation": {
    "owner": "openlibing", "repo": "community-private",
    "branch": "master",
    "path": "openLiBing-private/sigs/openLiBing-private/sig-info.yaml",
    "remark": "openLiBing SIG 组"
  },
  "roleMapping": [               // 仅 gitcode 页签携带
    { "gitcodeRole": "owner", "openlibingRole": "project_admin" }
  ]
}
```

**响应**：`DataResult<GlobalConfigVO>`（保存后最新全局配置）

**业务变化**：
- 按 `platform` 将该平台 `sigInfoLocation` / `roleMapping` 合并写入 `config_json`（其余平台配置保持不变）；`gitee` / `github` 忽略 `roleMapping`
- 保存时对每个位置**实时调对应平台** `getFileContent` 校验文件存在且 YAML 可解析，不可用位置在 `sigInfoLocation` 中标记状态（OK / FILE_NOT_FOUND / PARSE_ERROR），不阻断保存，便于用户排查（§2.2.0）
- 校验 `platform` 合法（gitcode/gitee/github）、位置格式安全（§7.2.2）

### 6.8 新增接口 5：`POST /project-repo/update-project-common-account`（更新项目公共账号）

**用途**：全局配置弹窗直接配置某平台项目公共账号（登录名 + 令牌），替代原只读跳转。令牌加密入库，**令牌留空表示不覆盖原值**（避免空覆盖）。

**请求**：
```jsonc
{
  "userId": "xxx", "userName": "xxx",
  "projectId": 1,
  "platform": "gitcode",     // gitcode / gitee / github
  "login": "openlibing-gitcode",
  "token": ""                // 留空则不修改原令牌
}
```

**响应**：`DataResult<Void>`

**业务变化**：更新 `project_common_account_info` 对应平台列的 `login` / 加密 `token`；token 非空时加密后入库，空时保留原值。令牌字段不出日志、不返回明文（§7.4）。

### 6.9 新增接口 6：`POST /project-repo/sig/config`（保存位置配置）

**用途**：在代码仓管理页保存/更新某平台的 sig-info.yaml 所在位置（**每平台唯一**）。**推荐走 §6.7 `update-global-config`（并入全局配置弹窗保存）**，本接口作为按平台独立保存位置的兼容入口保留。

**请求**：
```jsonc
{
  "userId": "xxx", "userName": "xxx",
  "projectId": 1,
  "platform": "gitcode",     // gitcode / gitee / github
  "location": {
    "url": "https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private/sig-info.yaml",
    "remark": "openLiBing SIG 组"
  }
}
```

**响应**：
```jsonc
{
  "code": 200,
  "data": {
    "location": {
      "url": "https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private/sig-info.yaml",
      "status": "OK", "error": null
    }
  }
}
```

**业务变化**：保存时解析链接为 `owner/repo/branch/path`（`https://{host}/{owner}/{repo}/blob/{branch}/{path}`），实时调**对应平台** `getFileContent` 校验文件存在且 YAML 可解析（`status`=OK / FILE_NOT_FOUND / PARSE_ERROR），不可用位置不阻断保存，便于用户排查；链接写入 `project_global_config.config_json[platform].sigInfoLocation`（§4.2.1，替代原表内逐行 upsert；传 null 清空该平台位置）。

### 6.10 新增接口 7：`GET /project-repo/sig/config`

**用途**：查询该项目某平台配置的 sig-info.yaml 链接（编辑配置时回显）。

**请求**：`GET /project-repo/sig/config?userId=xxx&projectId=1&platform=gitcode`

**响应**：
```jsonc
{
  "code": 200,
  "data": {
    "url": "https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private/sig-info.yaml",
    "remark": "openLiBing SIG 组"
  }
}
```

### 6.11 新增接口 8：`POST /project-repo/sig/repos`（仓库清单，实时解析，仅未录入当前项目的仓库）

**用途**：SIG 一键录入「选择仓库」下拉多选框数据源——实时解析该平台 sig-info.yaml，**仅返回尚未录入当前项目的仓库**（已录入的不展示，避免覆盖），并附带默认配置（默认分支/责任人/开源类型/代码风格修复/告警抑制检视 等，供表格展示与编辑）。

**请求**：
```jsonc
{ "userId": "xxx", "projectId": 1, "platform": "gitcode" }
```

**响应**：
```jsonc
{
  "code": 200,
  "data": {
    "platform": "gitcode", "owner": "openlibing", "repo": "community-private",
    "branch": "master", "path": "openLiBing-private/sigs/openLiBing-private/sig-info.yaml",
    "repos": [
      {
        "owner": "openlibing", "repo": "repo-a", "platform": "gitcode",
        "repoUrl": "https://gitcode.com/openlibing/repo-a.git",
        "defaultConfig": {
          "alias": "repo-a", "defaultBranchName": "master", "repoOwner": "u-a",
          "openSource": "主导开源", "purpose": "自研源码",
          "isAutoFormat": false, "isSuppressionEnabled": false
        }
      },
      {
        "owner": "openlibing", "repo": "repo-b", "platform": "gitcode",
        "repoUrl": "https://gitcode.com/openlibing/repo-b.git",
        "defaultConfig": {
          "alias": "repo-b", "defaultBranchName": "master", "repoOwner": "u-b",
          "openSource": "主导开源", "purpose": "自研源码",
          "isAutoFormat": false, "isSuppressionEnabled": false
        }
      }
    ]
  }
}
```

> **说明**：无「录入状态」字段（录入状态已移除，见 §2.2.1）；`repo-c` 等已录入当前项目的仓库被过滤不返回。`defaultConfig` 为默认参数（见 §2.2.3 默认参数表），前端选中后在表格展示，可单条/批量编辑或直接使用默认值。

### 6.13 新增接口 10：`POST /project-repo/sig/import`（一键录入，默认参数或用户编辑配置）

**用途**：一键录入勾选的仓库。参数为默认值（§2.2.3）或用户**单条/批量编辑后**的配置；sig-info.yaml 中不配置录入参数。

**请求**：
```jsonc
{
  "userId": "xxx", "userName": "xxx",
  "projectId": 1,
  "platform": "gitcode",
  "repoConfigs": [
    {
      "repoUrl": "https://gitcode.com/openlibing/repo-a.git",
      "config": { "alias": "repo-a", "defaultBranchName": "master", "repoOwner": "u-a",
                  "openSource": "主导开源", "purpose": "自研源码",
                  "isAutoFormat": false, "isSuppressionEnabled": false }
    },
    {
      "repoUrl": "https://gitcode.com/openlibing/repo-b.git",
      "config": { "alias": "repo-b", "defaultBranchName": "master", "repoOwner": "u-b",
                  "openSource": "主导开源", "purpose": "自研源码",
                  "isAutoFormat": true, "isSuppressionEnabled": false }
    }
  ]
}
```

**响应**：
```jsonc
{
  "code": 200,
  "data": {
    "imported": 2,      // 新增（repo-a, repo-b，含新建 repo_info + 当前项目关联）
    "failedRepoUrls": []
  }
}
```

**业务变化**：后端校验 `platform` 属于该项目且该项目已配置该平台位置（`project_global_config.config_json` 白名单，§7.2），实时调对应平台读取该位置 sig-info.yaml 解析 repositories，校验每个 `repoConfigs[].repoUrl` 均在解析结果中（防伪造/过期数据）且**尚未录入当前项目**，然后事务内逐个 upsert `repo_info`（未命中才新建，命中复用不覆盖）+ upsert `repo_project_ref(source=sig)`（§2.2.3）。

### 6.14 接口契约汇总

| 接口 | 方法 | 路径 | 鉴权 | 请求体 | 响应体 |
|------|------|------|------|--------|--------|
| 录入仓库（改造） | POST | `/project-repo/add-repo` | 网关 token | RepoDTO（含 deleteProjectIds） | `DataResult<Integer>` |
| 修改仓库（改造） | POST | `/project-repo/update-repo` | 网关 token | RepoDTO | `DataResult<Integer>` |
| 删除仓库（改造） | POST | `/project-repo/delete-repo` | 网关 token | repoId + projectId | `DataResult<Void>` |
| 冲突检测 | POST | `/project-repo/check-repo-url` | 网关 token | RepoUrlCheckQueryDTO | `DataResult<RepoUrlCheckVO>` |
| 关联查询 | GET | `/project-repo/get-repo-association` | 网关 token | repoId | `DataResult<RepoAssociationVO>` |
| 查询全局配置（新增） | GET | `/project-repo/global-config` | 网关 token | projectId | `DataResult<GlobalConfigVO>` |
| 更新全局配置（新增） | POST | `/project-repo/global-config` | 网关 token | GlobalConfigUpdateDTO | `DataResult<GlobalConfigVO>` |
| 更新项目公共账号（新增） | POST | `/project-repo/update-project-common-account` | 网关 token | ProjectCommonAccountUpdateDTO | `DataResult<Void>` |
| 保存 SIG 位置配置 | POST | `/project-repo/sig/config` | 网关 token | SigConfigSaveDTO（platform + location） | `DataResult<SigConfigSaveVO>` |
| 查询 SIG 位置配置 | GET | `/project-repo/sig/config` | 网关 token | projectId + platform | `DataResult<SigLocationVO>` |
| SIG 配置内仓库清单（实时读） | POST | `/project-repo/sig/repos` | 网关 token | { projectId, platform } | `DataResult<SigRepoConfigVO>` |
| SIG 一键录入 | POST | `/project-repo/sig/import` | 网关 token | { projectId, platform, repoConfigs } | `DataResult<SigImportResultVO>` |

### 6.15 错误码约定

| code | msg | 场景 |
|------|------|------|
| 200 | success | 成功 |
| 403 | SIG 位置不存在或不属于该项目 | sig 接口传了该项目未配置的 platform |
| 403 | 平台不合法 | global-config 传了非 gitcode/gitee/github 的 platform |
| 404 | sig-info.yaml 文件不存在 | 实时读取指定位置文件失败（FILE_NOT_FOUND） |
| 500 | sig-info.yaml 格式错误或解析失败 | 实时解析 YAML 失败（PARSE_ERROR） |
| 500 | 所选仓库不在该配置文件中 | sig/import 传了不在解析结果中的 repoUrl |
| 500 | 配置文件读取失败，请稍后重试 | 平台 API 调用失败（网络/超时） |
| 500 | 仓库链接不合法 | repoUrl 校验失败 |
| 500 | 参数错误：{detail} | 其他校验失败 |

## 7. 安全设计

### 7.1 鉴权

#### 7.1.1 现有接口鉴权不变

- `/project-repo/add-repo`、`/update-repo`、`/delete-repo`、`/query-repo`：网关 token + 角色校验（见 [feature-spec.md](./feature-spec.md) 权限矩阵）
- 沿用 `userId` / `userName` 入参 + 网关透传

#### 7.1.2 新增 SIG 接口鉴权

- `/global-config`（查询）、`/sig/config`（查询）、`/sig/repos`：读权限，沿用 `query-repo` 的角色集合
- `/global-config`（更新）、`/update-project-common-account`、`/sig/config`（保存）、`/sig/import`：写权限，沿用 `add-repo` 的角色集合（产业管理者、项目审批人员、流水线工程师、项目管理员）
- 所有 SIG 与全局配置接口均校验 `userId` 对 `projectId` 的访问权限（防止跨项目越权）

### 7.2 SIG 仓（sig-info.yaml 位置）访问安全

#### 7.2.1 token 传递

- 调用平台（gitcode/gitee/github）API 实时读取指定位置 sig-info.yaml 时，`accessToken` 通过 `Authorization: Bearer <token>` header 传递（遵循项目硬约束「第三方 API 调用 accessToken 必须在 header」）
- token 从对应平台公共账号获取（`commonService.getGitcodeToken(projectId, true)` / gitee / github 同理），解密后使用，**不入日志、不入 URL 参数**
- **与 framework [GitCode.getYaml](file:///d:/Develop/Java/openlibing-framework/src/main/java/com/openlibing/framework/common/utils/GitCode.java#L106-L128) 的差异**：framework 现有实现把 `access_token` 拼在 URL query 参数中，本需求在 coderepo 服务内独立实现（`SigInfoClient`）时改为 header 方式，避免 token 出现在网关访问日志中

#### 7.2.2 sig-info.yaml 位置白名单（防任意文件读取）

- 所有 SIG 读取接口**不接受前端任意传仓路径/文件路径**：`sig/repos`、`sig/import` 均以 `platform` 入参，后端先从 `project_global_config.config_json[platform].sigInfoLocation` 取出 `(owner/repo/branch/path)`，**仅允许读取该项目已配置的位置**，杜绝通过入参读取任意仓内文件
- `updateGlobalConfig` / `saveSigConfig` 保存位置时校验：
  - `owner`/`repo`/`branch` 非空且为安全字符（`[a-zA-Z0-9\-_.]`）
  - `path` 后缀必须为 `sig-info.yaml`（或 `.yaml`/`.yml` 且文件名含 `sig-info`），不含 `..` 路径穿越，长度 ≤ 512
  - 实时调对应平台 `getFileContent` 校验文件存在且 YAML 可解析，失败仅标记该位置状态，不阻断保存
- 读取位置时对平台返回的 `owner/repo/path` 做二次拼接校验，防止越权读取其他项目配置的位置

#### 7.2.3 YAML 解析安全

- 使用 SnakeYAML `SafeConstructor`（`new Yaml(new SafeConstructor())`），拒绝 `!!java/object` 等实例化标签，防 YAML 反序列化攻击
- 解析失败时返回明确错误，不暴露堆栈

### 7.3 输入校验

- 所有新增接口入参用 `@Valid` + JSR-303 注解校验
- `repoUrl` 校验：沿用前端 `validateSafeUrl` 后端镜像校验（协议头白名单、域名信任、无 `..`）
- SIG 位置入参（`owner/repo/branch/path`）校验：见 §7.2.2
- `platform` 校验：必须为 `gitcode` / `gitee` / `github` 之一，且该平台位置必须已在当前 `projectId` 的 `config_json` 中配置（global-config / sig 接口共用，§7.2.2，防跨项目越权）
- `update-project-common-account` 校验：`token` 不打印、不返回明文；`login`/`token` 均留空时拒绝（无任何更新）
- `selectedRepoUrls`：单次最多 100 个，防批量滥用；且每个必须在所选位置实时解析结果内
- `repoUrl` 长度限制 512，`repoName` 限制 50（沿用 [RepoDTO](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/dto/space/RepoDTO.java) 现有约束）

### 7.4 日志脱敏

#### 7.4.1 禁止打印的字段

- `accessToken`（仓库账号令牌 / 项目公共账号令牌）
- `currentConfig.accessToken`（冲突检测返回的现有配置中的令牌）
- YAML 配置文件内的 `accessToken` 字段
- `project_global_config.config_json` 整对象（一旦后续扩展纳入令牌类字段将泄露；打印时仅打平台键与位置 owner/repo/path）

#### 7.4.2 允许打印的字段

```java
// ✅ 正确
logger.info("Check repo url conflict, projectId: {}, repoUrl: {}, exists: {}", projectId, repoUrl, exists);
logger.info("Sig import, projectId: {}, platform: {}, selectedCount: {}, imported: {}", projectId, platform, selectedRepoUrls.size(), result.getImported());
logger.info("Read sig-info.yaml, platform: {}, owner: {}, repo: {}, branch: {}, path: {}", platform, owner, repo, branch, path);
logger.info("Update global config, projectId: {}, platform: {}", projectId, platform);

// ❌ 错误
logger.info("Repo config: {}", repoInfoEntity);  // 含 accessToken，禁止
logger.info("Yaml content: {}", yamlRawString);  // 可能含 accessToken，禁止
logger.info("Global config: {}", globalConfigVO);  // 含 commonAccount 令牌掩码信息，禁止整对象打印
```

冲突检测返回的 `currentConfig` 中，`accessToken` 字段在序列化前必须置空（前端不需要该字段做表单填充，令牌编辑单独走现有 `isEditAccessToken` 流程）；`get-global-config` 返回的公共账号令牌一律掩码（`******`），`update-project-common-account` 入参中的明文令牌不出日志、不返回。

### 7.5 SIG 录入与手动录入互不覆盖

- **SIG 录入不覆盖已有配置**：`sig/repos` 只返回**尚未录入当前项目**的仓库（已录入的不展示）；`sig/import` 校验每个 repoUrl 尚未录入当前项目，且对全局已存在但当前项目未关联的仓库**复用其现有配置、不覆盖**（仅 upsert 当前项目关联）
- **SIG 来源仓库允许手动编辑**：`repo_info.source=sig` 的仓库同样走 `update-repo` 编辑（**不做来源拦截**），仓库配置全局唯一一份，编辑自动影响所有关联项目
- **手动录入命中已存在仓库**：不视为冲突错误，前端 blur 自动同步现有配置到表单，支持选择性删除之前项目关联（详见 §2.1）
- 以上约束在 `SigRepoImportService` / `RepoServiceImpl` 中实现，不依赖角色或配置开关

### 7.6 数据库安全

- `repo_info.repo_url_normalized` 普通索引 + 应用层事务内查重保证新录入 `repo_url` 全局唯一（存量清理完成前**不加 DB 唯一约束**；清理完成后择期升级唯一索引作兜底，见 §2.5 清理时机）
- `repo_project_ref.uk_repo_project` 防重复关联
- 软删除（`is_deleted`）保留历史可追溯，删除操作不物理删除
- DBA 查表可见 `accessToken` 字段（明文存储现状），本需求不改变该现状；后续可独立立项做令牌加密存储

### 7.7 平台 token 安全

- 沿用现有 `GitCodeUtil` / `GiteeUtil` / `GithubUtil` 的 token 使用方式，本需求不新增 Git 平台 token 使用面
- `SigInfoClient` 复用 `commonService.getGitcodeToken`，不引入新凭证

### 7.8 迁移脚本安全

- `project_global_config` 迁移：将 `project_gitcode_role_mapping.role_mapping`（gitcode 角色映射 JSON 文本）写入 `config_json.gitcode.roleMapping`，批量 upsert，失败可重跑（幂等：按 `(project_id, is_deleted)` 先查后写）
- repo 迁移脚本在事务内执行，每批 1000 行提交，失败可重跑（幂等：先查 ref 是否存在再 insert）
- 迁移/清理脚本**在上线后统一执行**，不阻塞服务上线；执行期间新录入重复由代码层事务内查重保证（见 §2.5 清理时机）
- 迁移前全量备份 `repo_info` 表
- 迁移后校验：存量重复清理完成（`repo_url` 全局唯一）、`repo_project_ref` 关联数 = 原 `repo_info` 行数
- 灰度开关 `coderepo.repo-decouple.enabled` 控制新旧逻辑切换，可快速回滚

### 7.9 安全验收清单

- [ ] `accessToken` 不出现在任何后端日志中（grep 验证）
- [ ] `accessToken` 不出现在 URL 参数中（网关访问日志验证）
- [ ] 调平台 API 的请求 header 中含 `Authorization: Bearer`，URL 中无 `access_token`
- [ ] SIG 读取接口传本项目未配置的 `platform` 返回 403
- [ ] `updateGlobalConfig` / `saveSigConfig` 保存位置时 `path` 含 `..` 被拒绝、后缀非 `sig-info.yaml` 被拒绝
- [ ] 不存在的位置（未在 `project_global_config.config_json` 配置）无法通过任意接口读取其文件
- [ ] `update-project-common-account` 入参令牌不出日志、不返回明文；`get-global-config` 返回令牌为掩码 `******`
- [ ] global-config 传非 gitcode/gitee/github 的 `platform` 返回 403
- [ ] YAML 含 `!!java/object` 等危险标签时解析被拒绝
- [ ] 跨项目访问 SIG / 全局配置接口返回 403（无该 project 权限）
- [ ] 上线后存量重复仓库统一清理完成：`SELECT repo_url_normalized, COUNT(*) FROM repo_info WHERE is_deleted=0 GROUP BY repo_url_normalized HAVING COUNT(*)>1` 返回 0 行
- [ ] 新录入重复仓库被代码层查重拦截：`add-repo` / `sig/import` 并发重复 `repo_url` 不产生第二条 `repo_info`（并发用例）
- [ ] 单元测试覆盖：手动录入冲突（自动同步配置 + 选择性删除）、SIG 录入仅未录入仓库 + 不覆盖已有配置、SIG 来源仓库手动编辑、全局配置 config_json 读写（含 roleMapping 迁移）、迁移幂等、sig-info.yaml 解析与位置白名单
