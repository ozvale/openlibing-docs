# 代码仓管理与需求解耦 + SIG 组一键批量录入（需求设计文档）

> 跨仓 Full 模式需求设计文档。涉及 `openlibing-coderepo-fork`（后端 + DB）、`openlibing-web`（前端）两个仓，并参考 `openlibing-framework` 的 `GitCode.getYaml` 实现模式。
>
> **影响面说明**：下游 `codecheck`/`cicd`/`framework`/`anti-poison`/`sca`/`gateway`/`vulnerability` **7 个仓均不归属本项目，无法控制其改造进度**（`sbom` 仓为独立 SBOM 工具、持有自有 schema，**不涉及 `repo_info` 表，不在影响面内**）；存量体检（`GROUP BY repo_url HAVING COUNT(DISTINCT project_id)>1`）发现 **53 个共享仓**（同一 `repo_url` 已录入多个项目）。因此对 `repo_info.project_id` 采取「**暂时保留 + 归并推迟**」策略——Phase 1（本需求）**仅 `coderepo` 改造**：新建 `repo_project_ref`、新录入仓库全局唯一（代码层查重）、coderepo 自身读写切换；**7 个下游仓零改动**，仍从 `repo_info.project_id` 读取；53 个共享仓**保留现状多行不归并**（归并需重映射其下游子表 FK，推迟到 7 仓逐个可控后统一执行，见 §1.2 分阶段方案与 §2.5 迁移策略）。
>
> **改造边界（重要）**：本次改造**仅涉及 `repo_info` 表**（及新增 `repo_project_ref` 关联表）；代码仓相关配置表还包括 `codecheck` 下的 Mongo 表（如 `sig_rule_set` 规则集表），**本次不改动**——即仍允许不同项目对同一代码仓存在不同配置的情况（规则集、告警抑制等项仍按各项目在 codecheck 侧各自配置，不在本次收敛范围内）。
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
- **项目级全局配置**：在代码仓管理页「导出仓库」右侧新增「全局配置」按钮，按 GitCode / Gitee / GitHub 三个平台页签统一维护项目公共账号（可直接配置）、代码仓录入配置（sig-info.yaml 位置）与 GitCode 角色映射；改造 `project_gitcode_role_mapping` 表为通用配置表 `project_repo_global_config`，各配置项以 JSON 存储，便于后续扩展新配置项而不需改表。

**两阶段目标**（受下游 7 仓不可控约束，解耦与归并分两步落地）：

| 阶段 | 范围 | 交付 |
|------|------|------|
| **Phase 1（本需求）** | `coderepo`（本项目可控）+ `framework`（必要例外） | 新建 `repo_project_ref` 表达仓库↔项目多对多；**新录入仓库全局唯一**（同一 `repo_url` 不再产生第二行，代码层查重）；coderepo 自身读写切新模型；framework 做**副仓拦截改造**（§7.1.4）；**其余 6 仓零改动**，仍读 `repo_info.project_id`（值=该行所属项目；53 个共享仓多行保留、各自项目照常可见）；归并与唯一索引**推迟** |
| **Phase 2（7 仓逐个可控后）** | 7 个下游仓 | 逐个切换为从 `repo_project_ref` 取 `project_id` → 按 `repo_url` 归并 53 个共享仓（保留最早行为基准，其余行删除前重映射其子表 FK，如 sca `tbl_scan.repo_id`）→ 全部完成后 `DROP COLUMN project_id` + 加 `repo_url` 唯一索引 |

### 1.2 解耦方案

`repo_url` 全局唯一 → 单一 `repo_id`；新建 `repo_project_ref` 作为仓库↔项目多对多关联表；`repo_info.project_id` **暂时保留**（该 repo 的**主仓项目**的 `project_id`，作为过渡期冗余字段，也是 7 个下游仓唯一能读到的项目归属），后续择期移除。

1. **新录入全局唯一是核心目标**：需求明确「每个 `repo_url` 全局唯一对应一个 `repo_id`」。**先不在 DB 层对 `repo_url` 加唯一约束**（存量 53 个共享仓多行未清理会阻塞加唯一索引、上线窗口并发录入会触发唯一键冲突），先在**代码层保证新录入仓库不重复**（`addRepoInfo` / `sigImport` 在事务内按归一化 `repo_url_normalized` 查重 + 锁，见 §5.3），同一仓库不再新增第二行；**存量 53 个共享仓多行保留（遗留现状，不阻塞新录入），列入待归并清单，Phase 2 统一归并**。
2. **配置单一来源（仅限 `repo_info` 表字段）**：新模型下同一 `repo_id` 只有一份配置（用途/开源类型/接管 PR/自动触发等 `repo_info` 自身字段），从根上消除新产生配置漂移，多个项目关联同一仓库时共享这份配置；**存量 53 个共享仓在归并前暂按各自行维护配置（与现状一致，不强制收敛），归并后自然达成单一来源**。**边界**：此「单一来源」仅针对 `repo_info` 表自身配置字段；`codecheck` 下的 Mongo 表（如 `sig_rule_set` 规则集）**不在本次改造范围，仍允许不同项目对同一代码仓配置不同**（见文首「改造边界」）。
3. **关联表表达多对多**：`repo_project_ref` 干净支撑「一个 repo 关联 N 个 project」「一个 project 关联 N 个 repo」的多对多语义。**不再在关联表记录 `source`**——SIG 与手动录入互不覆盖、无优先级判定场景，关联来源信息（手动/SIG）由 `repo_info.source`（当前配置来源）承担。
4. **过渡期双轨兼容**：`repo_info.project_id` 不立即删除（该行所属项目），保证 7 个未改造仓继续按旧方式读取不中断；**Phase 1 不做存量归并**——仅新增 `repo_project_ref` 并为存量行做 1:1 回填（无副作用），归并整体推迟到 Phase 2。
5. **分阶段改造（影响面收敛，Phase 1 仅 coderepo + framework 必要例外）**：本项目只可控 `coderepo`，Phase 1 让 coderepo 全面切换为从 `repo_project_ref` 取 `project_id`；`framework` 因主仓/副仓模型下存在「副仓用户被静默登记为主仓项目成员」的污染风险，需同步做**副仓拦截改造**（见 §7.1.4）；其余 `codecheck`/`cicd`/`anti-poison`/`sca`/`gateway`/`vulnerability` **6 仓本需求一律不动**，仍从 `repo_info.project_id` 读取，后续逐个可控后再切换（见 §2.5 迁移策略与 §4.4 过渡期策略）。
6. **主仓/副仓语义（Phase 1 关键决策）**：`repo_info.project_id` = 用户选择的**主仓项目**（唯一参与下游 7 仓扫描/检查/权限/漏洞的项目，默认=首个录入项目，可迁移）；其他项目对同一仓库的关联为**副仓**——仅在 coderepo 侧 `repo_project_ref` 记录（管理/展示用），**不参与任何下游任务**，下游 7 仓对副仓不可见。该语义保证 Phase 1 `repo_info.project_id` 始终是「真实单归属」，消除「新多项目关联在下游静默丢失」的风险（决策细节见 §1.5，录入流程见 §2.1）。

**分阶段改造范围与影响仓**（基于全量代码检索 `repo_info` 表 `repo_id ↔ project_id` 互查使用情况 + 存量体检 53 个共享仓）：

| 阶段 | 仓 | 改造方式 |
|------|-----|---------|
| **Phase 1（本需求）** | `coderepo`（本项目可控） | 新建 `repo_project_ref` + 存量 1:1 回填；新录入全局唯一（代码层查重）；coderepo 自身读写切关联表；`repo_info.project_id` 保留 |
| **Phase 1 必要例外（需改造）** | `framework` | 主仓/副仓模型下，framework 仓库级/git 成员权限路径不校验访问者项目，副仓用户会被静默登记为主仓项目成员 → 需同步做**副仓拦截改造**（`checkRepoUserNamePermission`/`saveRepoUserInfo`/`verifyPermissions`/`getSpaceId`/`getBySca`，见 §7.1.4）；`repo_info.project_id` 读取语义不变 |
| **暂不修改（其余 6 仓零改动）** | `codecheck` / `cicd` / `anti-poison` / `sca` / `gateway` / `vulnerability` | 仍从 `repo_info.project_id` 读取（该行所属项目；53 个共享仓多行保留、各自项目照常可见），Phase 1 不做任何修改 |
| **Phase 2（7 仓逐个可控后）** | 上述 7 仓 | 逐个切换为从 `repo_project_ref` 取 `project_id`；全部切换完成后按 `repo_url` 归并 53 个共享仓（保留最早行为基准、其余行删除前重映射其子表 FK）、`DROP COLUMN project_id`、加 `repo_url` 唯一索引 |

> **过渡期语义说明（主仓/副仓模型）**：`repo_info.project_id` 仅能冗余单个 `project_id` = 该仓库的**主仓项目**。存量 53 个共享仓多行保留，每行 `project_id`=该行所属项目（与现状一致，7 仓读取零变化）；**新模型下同一仓库被多个项目关联时，仅「主仓」参与 7 个下游仓的扫描/检查/权限/漏洞，其余项目为「副仓」——副仓仅在 coderepo 侧有 `repo_project_ref` 记录，下游 7 仓对副仓不可见**（决策见 §1.5）。代码审计确认（sca/anti-poison/framework/gateway/vulnerability 四仓逐一核查）：
> - sca：扫描结果 `tbl_scan`/`tbl_person_scan` **按 `repo_id` 存储、无 project_id**；展示/触发经 `repo_info.project_id JOIN project_info` 现算——副仓触发扫描在入口抛 41003 干净失败，**不会「在副仓扫、结果串到主仓」**；
> - anti-poison：按 `(project_id, repo_url)` 反查 `repo_info`，副仓查不到 → 返回 400 错误，不崩溃、不串结果；
> - framework：**项目级**权限判定（`checkRepoUserNamePermission` 项目管理员/内部开源仓分支）按 `repo_info.getProjectId()`=主仓 → 副仓项目角色对该仓**无权限**（符合副仓不参与预期）；但**仓库级成员判定（`repoId.equals(entity.getRepoId())`）与 git 平台成员校验（`queryRepoUser` / git API）不校验访问者项目**，副仓用户一旦通过该路径会被 `saveRepoUserInfo` 静默登记为主仓项目 `REPO_DEVELOPER` 并补插 `PROJECT_MEMBER`（污染主仓成员数据）→ 需做**副仓拦截改造**（见 §7.1.4）；`deleteByProjectId` 项目删除级联会**连坐删除副仓引用的 repo_info**（隐患，处理见 §1.5/§2.4）；
> - gateway：`getRepoIdByRepoUrl` 为**死代码**（无调用方），无影响；
> - vulnerability：CVE 漏洞看板按「项目名」分桶（Mongo `<org>_cve_details`）、漏洞管理按各自 project_id 存取 → 主链路不受影响、**不串项目**；仅昇腾链路 `queryRepoInfoByUrl` 按 `(project_name, repo_url)` join `repo_info` → 副仓项目查不到即跳过（昇腾看板为空，不报错、不串项目），**接受该行为并在方案说明**（昇腾项目一般无副仓场景；若出现需改造该查询支持 `repo_project_ref`，见 §4.4）。
>
> **归并（含子表 FK 重映射，如 sca `tbl_scan.repo_id`、anti-poison 相关表）必须等对应仓可控后执行**，Phase 1 不归并。

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
│  SIG 仓 (gitcode)               │         │  │ repo_info (新录入全局唯一)          │   │
│  sig-info.yaml (固定格式)        │ ◀────── │  │  repo_url 唯一(代码层), source,    │   │
│  repositories:                   │  实时读  │  │  sig_config_file, ...        │   │
│   - repo:                        │  YAML   │  └──────────────┬───────────────┘   │
│     - openlibing/xxx            │         │                 │ repo_id            │
│     - openlibing/yyy            │         │  ┌──────────────▼───────────────┐   │
│   - repo:                        │         │  │ repo_project_ref (新增)       │   │
│     - openlibing/zzz            │         │  │  (repo_id, project_id)       │   │
└──────────────────────────────────┘         │  └──────────────┬───────────────┘   │
                                              │  └──────────────┬───────────────┘   │
┌──────────────────────────────────┐         │                 │                   │
│  project_repo_global_config (改造)    │         │  ┌──────────────▼───────────────┐   │
│  项目级全局配置 config_json      │◀─────── │  │ (按 project_id+平台 查位置)   │   │
│  gitcode/gitee/github 各平台     │  读取    │  └─────────────────────────────┘   │
│  (sigInfoLocation + roleMapping)│         └──────────────────────────────────────┘
└──────────────────────────────────┘
```

核心流程：
1. **手动录入**：用户输入 `repo_url`（blur 时调检测接口）→ 后端查 `repo_info` by `repo_url`：未命中则新建 `repo_info` + 新建 `repo_project_ref`；命中则**自动将已有配置同步到表单**（可修改），展示已关联项目列表供**选择性删除**（仅取消所选项目的关联），提交时新建当前项目关联、可选删除所选项目关联并按表单更新全局配置。
2. **SIG 一键录入**：用户在代码仓管理「全局配置」弹窗按平台（gitcode/gitee/github）配置 sig-info.yaml 所在位置（**每平台唯一一个**仓路径）→ 录入弹窗「SIG 组一键录入」下拉多选**尚未录入当前项目**的 SIG 仓库（已录入的不展示，避免覆盖已有配置）→ 选出后在表格中展示所选仓库（默认配置，可单条/批量编辑或删除）→ 后端按所选仓库（默认参数或用户编辑配置）录入，每个仓库 upsert `repo_info`（source=sig，已全局存在则复用其配置不覆盖）+ upsert `repo_project_ref`。
3. **编辑**：仓库配置全局唯一一份，编辑直接更新 `repo_info` 即可（SIG 来源仓库同样允许手动编辑）；不再做「多项目影响提示」与「SIG 来源编辑拦截」。
4. **历史存量迁移（分两阶段）**：Phase 1 为存量全部 `repo_info` 行做 **1:1 回填 `repo_project_ref`**（repo_id ↔ 该行所属项目），**53 个共享仓多行保留、不归并**；Phase 2 待 7 仓逐个可控后按 `repo_url` 归并 53 个共享仓（保留最早行为基准，其余行删除前重映射其子表 FK），见 §2.5。

### 1.5 关键决策汇总

| 决策点 | 选择 | 理由 |
|--------|------|------|
| 表结构 | 新建 `repo_project_ref`（多对多）；`repo_info.project_id` **暂不删除**，作为过渡期冗余（值=该 repo 的**主仓项目**的 `project_id`；新录入仓库默认主仓=首个录入项目，可迁移，见「多项目归属（主仓/副仓）」决策），后续择期移除 | 全局唯一 + 多对多关联；Phase 1 仅 coderepo 切换，7 个下游仓零改动仍从 `repo_info.project_id` 读取，过渡期双轨兼容 |
| `repo_url` 唯一性 | **暂不加 DB 唯一约束**；应用层 normalize（`.git` 后缀、大小写、末尾斜杠归一）+ 代码层事务内查重保证**新录入**不重复；存量 53 个共享仓多行保留、Phase 2 归并完成后择期加唯一索引 | 避免上线窗口并发录入触发唯一键冲突、存量 53 个共享仓多行未清理导致加唯一索引失败；新录入不新增多行，存量归并推迟 |
| `repo_name`（代码仓别名）唯一性范围 | **项目内唯一，不做全局唯一**：`repo_url` 才是全局唯一维度；`repo_name` 用于当前项目内列表展示 / 成员与角色映射 / 别名冲突判定（同名不同仓按 `repo名-平台名`、`repo名-平台名2`… 递增区分，见 §2.2.3）。别名沿用 `repo_info.repo_name`（配置单一来源决定别名全局单一：同一仓在多个项目共享同一别名），**本期不支撑「不同项目对同一仓起不同别名」**；若 Phase 2 有该诉求再迁 `repo_project_ref` 扩展字段 | 避免把 `repo_name` 误当作全局唯一键导致跨项目撞名拒绝录入；与「repo_url 全局唯一 + 配置单一来源」目标一致 |
| 多项目归属（主仓/副仓） | Phase 1 同一仓库仅一个**主仓**参与下游扫描/检查/权限/漏洞（`repo_info.project_id`=主仓项目 id，用户可选择/迁移）；其他项目关联为**副仓**，仅作 coderepo 侧 `repo_project_ref` 记录，**不参与 sca/anti-poison/cicd-fork/framework/vulnerability 等任何下游任务** | 下游仓全部按 `repo_info.project_id` 单值读取（代码审计逐一确认：sca 结果按 repo_id 存储、展示/触发按 project_id 现算；anti-poison 按 `(project_id, repo_url)` 反查副仓干净报错；framework 项目级判定按 project_id 但**仓库级/git 成员路径不校验访问者项目 → 需副仓拦截改造（§7.1.4）**；vulnerability 按项目名分桶主链路不受影响、仅昇腾链路副仓静默缺失；gateway 无调用）。主仓/副仓模型保证副仓在这些服务中**不可见或干净报错**，杜绝「结果串项目」与「副仓静默丢失扫描」 |
| 副仓边界与前端提示 | 副仓在 **coderepo** 内可见（管理/记录），在 **sca/anti-poison 等下游仓不可见、不可扫**；录入/编辑时前端明确提示「该项目为副仓，仅作记录，不参与 SCA 扫描/防投毒/漏洞等检测」 | 避免副仓用户「录入了却看不到扫描结果」的困惑；与「Phase 1 下游 7 仓零改动」完全一致 |
| 迁移归属副作用 | 把主仓从 A 迁移到 B（`repo_info.project_id` A→B）会使该仓**全部历史扫描/检查/漏洞结果整体从 A 项目消失、出现在 B 项目**（结果按 repo_id 存储、归属经 project_id 现算），framework 权限同步切到 B；前端迁移前需强提示 | 代码审计确认 sca 展示经 `repo_info.project_id` 现算，改主仓即整体「搬家」；避免用户误操作后以为数据丢失 |
| 主仓项目删除对副仓 | 删除主仓项目时若该仓被其他项目关联（副仓存在），**禁止直接级联删 `repo_info`**（framework `ProjectServiceImpl.deleteProject` → `queryByProjectId` + `deleteByProjectId` + `deleteByRepoIds` 会连坐删除副仓引用的 repo_info，[证据 L424-433](file:///d:/Develop/Java/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/ProjectServiceImpl.java#L418-L443)）；应先**迁移主仓给任一副仓**，或先删除该仓全部 ref 再删 repo_info | 防止副仓 `repo_project_ref` 悬空；该规则同时写进 coderepo 自身删除链路（§2.4）与 framework 后续切换时的改造点（§2.5） |
| framework 副仓拦截（Phase 1 必要例外） | framework 随本需求同步改造：`checkRepoUserNamePermission`/`saveRepoUserInfo`/`verifyPermissions`/`getSpaceId`/`getBySca` 等按 repoId 直入的权限/成员路径，先校验访问者项目 ∈ 该 repo 的 `repo_project_ref` 关联集合，副仓访问**拒绝且禁止写入主仓成员表**（`saveRepoUserInfo` 对副仓用户跳过、不补插 PROJECT_MEMBER） | 防止副仓用户被静默登记为主仓 `REPO_DEVELOPER`/`PROJECT_MEMBER`，污染主仓成员数据（代码审计确认 [InternalServerImpl.java](file:///d:/Develop/Java/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/InternalServerImpl.java#L138-L189) L153/L177/L185/L231-277）；是「下游仓零改动」的唯一必要例外，其余 6 仓副仓场景干净报错/不可见 |
| source 字段 | `repo_info.source`（manual/sig） | 仅 repo 级标记「当前配置来源」（列表「来源」列展示用）；**`repo_project_ref` 不再保留 `source`/`sig_config_file`**——SIG 与手动录入互不覆盖、无优先级判定场景，关联建立方式无需落库，SIG 配置来源路径由 `repo_info.sig_config_file` 记录 |
| SIG 优先级 | sig 与 manual 录入**互不覆盖**：SIG 录入只针对**尚未录入当前项目**的仓库，已录入的不展示、不覆盖；手动录入命中已存在仓库时自动同步其配置，支持选择性删除之前项目关联 | 避免配置被覆盖/漂移；SIG 仓库配置允许后续手动编辑（不做来源拦截） |
| 配置文件读取 | 复用 framework `GitCode.getYaml` 模式（coderepo 服务内独立实现 `SigInfoClient`），**接口实时调 gitcode 读取并解析** | coderepo 与 framework 是独立微服务，不跨仓引 jar；逻辑简单（≈120 行）独立维护 |
| 配置文件位置 | 项目级配置：用户在代码仓管理「全局配置」弹窗按平台（gitcode/gitee/github）配置**一个** sig-info.yaml **链接**（`https://{host}/{owner}/{repo}/blob/{branch}/{path}`，每平台唯一，后端解析出 owner/repo/branch/path），存 `project_repo_global_config.config_json` | 每平台仅一个位置、可跨多平台（gitcode/gitee/github）扩展，用户填写完整链接即可，无需拆字段 |
| 全局配置入口 | 代码仓管理页「导出仓库」右侧新增「全局配置」按钮，三页签（GitCode/Gitee/GitHub）分别维护项目公共账号 / 代码仓录入配置 / 角色映射 | 项目级公共配置集中管理，对所有代码仓生效；公共账号仍存 `project_common_account_info`（新增直接写入接口），角色映射与 sig-info 链接存 `project_repo_global_config.config_json` |
| 项目公共账号 | 仍存现有 `project_common_account_info` 表（登录名 + 加密令牌），全局配置弹窗提供「保存公共账号」接口直接配置（不再只读跳转） | 令牌加密存储现状不变，避免迁移与多服务读取改造；仅新增写入入口，读取沿用现有 `get-project-common-account` |
| 配置同步机制 | **去除 webhook**：不再推送解析入库；一键录入接口**实时调对应平台 API 读取指定位置 sig-info.yaml 并直接解析返回** | 简化链路、去掉缓存一致性与事件丢失问题；sig-info.yaml 内容以对应平台实时文件为准 |
| 配置读取 | `sig/repos` / `sig/import` 均实时调对应平台（gitcode/gitee/github）API 读取指定位置 sig-info.yaml（走配置位置白名单，见 §7.2） | 保证读到最新配置；平台 API 失败时返回明确错误并提示稍后重试 |
| 冲突检测时机 | 手动录入时 `repoUrl` blur 调 check 接口预查，命中即自动同步配置；后端在 add 时二次校验防并发 | 前端 blur 触发自动同步；后端 add 时按归一化 `repo_url` 查重兜底 |
| 历史迁移 | 分两阶段（见 §2.5）：**Phase 1** 仅 1:1 回填 `repo_project_ref`（不归并、不加唯一索引）；**Phase 2** 7 仓逐个可控后按 `repo_url` 归并 53 个共享仓（保留最早配置、重映射子表 FK）→ 全部切换后 `DROP COLUMN project_id` + 加唯一索引；灰度开关 `coderepo.repo-decouple.enabled` | 7 个下游仓不可控，归并需其子表 FK 重映射配合；Phase 1 零副作用交付新模型，归并推迟到可控时统一执行 |
| YAML 解析安全 | SnakeYAML `SafeConstructor`（拒绝实例化任意类） | 防 YAML 反序列化攻击 |
| accessToken 传递 | 调 gitcode API 时 `Authorization: Bearer <token>` header（不复用 framework 的 URL param 方式） | 遵循项目硬约束「第三方 API 调用 accessToken 必须在 header」 |

## 2. 实现逻辑设计

### 2.1 手动录入逻辑（含跨项目检测与选择性删除）

> **核心变化**：输入仓库链接后 blur 即向后端发起检测请求，命中已录入其他项目的仓库时**自动将已有配置同步进表单**（无需「一键同步」按钮），用户可修改配置；**历史存量暂未归并，同一代码仓可能在多个项目（如 项目A、项目B）各有独立行且配置不同，前端先展示「主仓设置」让用户选择以哪个项目为主仓，配置按所选主仓自动同步（默认当前主仓）**；「是否删除之前项目中的代码仓」支持**选择性删除**（仅取消所选项目与该代码仓的关联，非一次删除所有）；若未删除之前项目中的代码仓，修改配置会**同步修改之前项目中的代码仓配置**（代码仓配置全局唯一），前端需提示用户。

#### 2.1.1 录入主流程

```
addRepoInfo(userId, userName, projectId, RepoDTO, deleteProjectIds):
  1. normalize repoUrl：去末尾斜杠、去 .git 后缀、统一 https 协议头
  2. 查 repo_info by repo_url（命中=已全局存在；存量 53 个共享仓可能命中多行，见下方分流说明）
  3a. 未命中（首次录入，走新模型全局唯一）:
      - insert repo_info (source=manual, sig_config_file=null, 配置取 RepoDTO)
      - insert repo_project_ref (repo_id, project_id)
      - 同步仓库信息（调 GitCodeUtil 拉平台元数据回填，沿用现有 syncRepoInfo 逻辑）
      - 配置 webhook（沿用现有 autoSetWebHook 逻辑）
  3b. 命中（已存在；历史存量暂未归并，同一 repo_url 可能在多个项目存在独立行且配置不同）:
      - 前端 blur 时已触发检测；checkRepoUrl 返回当前主仓 + 各关联项目配置（见 §2.1.2）。
      - 前端展示「主仓设置」单选（列出所有关联项目，标记当前主仓，默认选中当前主仓）：
        · 用户选定主仓（如 项目A / 项目B）→ 表单配置立即按所选主仓对应行的配置**自动同步**
          （可继续手动修改）；提示「历史数据暂未归并，各项目配置可能不同，配置以主仓为准」。
        · 用户也可将当前项目设为主仓（见下方「设为本项目为主仓」）。
      - 随后确认当前项目归属（沿用二选一）：
        · **设为本项目为主仓（迁移归属）** → 将该 repo 主仓从原项目迁移到当前项目
          （repo_info.project_id 改为当前项目，配置以当前项目表单为准）。前端强提示：「该仓库
          全部历史扫描/检查/漏洞结果将整体迁移到本项目（结果按仓库存储、归属随主仓项目变化），
          原主仓项目的相关结果将不再展示」；原主仓降为普通关联（或按 deleteProjectIds 删除）。
        · **作为副仓关联（仅记录）** → 仅新建 repo_project_ref (repo_id, project_id)，
          不修改 repo_info.project_id、不参与任何下游任务。前端提示：「该项目为副仓，仅作记录，
          不参与 SCA 扫描/防投毒/漏洞等检测，相关结果请在主仓项目查看」。
      - 若 deleteProjectIds 非空（删除之前项目关联）→ 逐个删除所选项目关联：
        · 删「非主仓」项目关联 → 删除 repo_project_ref (repo_id, deleteProjectId)
          （仅取消所选项目与该代码仓的关联，repo_info 保留，其余项目不受影响）
        · 删「主仓」项目关联 → 必须同时指定**新主仓**（迁移给另一关联项目）或允许该仓进入
          「无主仓」状态（repo_info.project_id 置空，仅剩副仓 ref；下游 7 仓将看不到该仓，需提示）
      - 若未勾选任何删除项且未设当前项目为主仓 → 按表单更新 repo_info 配置（以所选主仓配置为基准，
        同步影响所有仍关联项目），前端已提示「修改会同步修改之前项目中的代码仓配置」
      - upsert repo_project_ref (repo_id, project_id)
  4. 返回 repoId
```

> **过渡期 53 个共享仓分流（Phase 1）**：存量 53 个共享仓（同一 `repo_url` 在 `repo_info` 存在多行未删除记录，迁移时列入待归并清单）在归并前**退化为现状行级语义**——
> - 每个项目操作**各自的行**（新增/编辑/删除按行，7 仓按 `repo_info.project_id` 照常读到），该 repo_url **不参与新模型全局唯一去重**（多行是既定事实，归并前无法唯一）；
> - `checkRepoUrl` 命中多行时返回**每行所属项目的配置**（`projectConfigs`）与**当前主仓**（`mainRepoProjectId`，默认=最早 `create_at` 行所属项目），`associatedProjects` 合并所有行所属项目（去重）；前端「主仓设置」默认选中当前主仓，用户改选主仓后按所选主仓对应行的配置**重新同步**（见 §2.1.2/§2.1.3）；
> - 前端交互与需求一致（主仓设置 + 按主仓自动同步配置 + 选择性删除提示），提交时携带 `mainRepoProjectId`（主仓选择）与 `deleteProjectIds`（对其他项目删除其**行**，而非仅 ref），当前项目未关联则按现状新建当前项目行；
> - Phase 2 归并后这些 repo_url 收敛为唯一行 + `repo_project_ref` 多对多，届时走新模型标准流程。

#### 2.1.2 检测接口（前端 blur 触发）

```
checkRepoUrl(userId, projectId, repoUrl):
  1. normalize repoUrl
  2. 查 repo_info by repo_url（过渡期 53 个共享仓可能命中多行，见下方分流说明）
  3. 未命中 → { exists: false }（表单不填充，正常录入）
  4. 命中 → {
       exists: true,
       repoId,
       mainRepoProjectId,             // 当前主仓项目 id（repo_info.project_id；历史多行默认=最早 create_at 行所属项目）
       currentConfig: {               // 当前主仓对应配置（默认同步基准，用户改选主仓后可覆盖）
         repoName, repoOwner, purpose, openSource, assumePr,
         defaultBranchName, isAutoFormat, isSuppressionEnabled,
         isParticipateOperation, ...
       },
       projectConfigs: [              // 各关联项目各自的配置（历史多行配置可能不同，供「主仓设置」切换）
         { projectId, projectName, config: { /* 同 currentConfig 字段 */ } }
       ],
       associatedProjects: [          // 该 repo 已关联的项目列表
         { projectId, projectName }
       ]
     }
  5. 前端默认把 currentConfig（当前主仓配置）同步到表单（可修改）；展示「主仓设置」单选
     （列出 associatedProjects，标记当前主仓）与「是否删除之前项目中的代码仓」多选；
     用户改选主仓后，按 projectConfigs[projectId].config 重新同步表单
```

#### 2.1.3 前端交互（自动同步 + 选择性删除）

- `repoUrl` blur → 调 `checkRepoUrl`（防抖 300ms）
- `exists=false` → 表单正常录入
- `exists=true` →
  - 顶部蓝色提示条：「检测到该代码仓已在 项目A、项目B 录入。历史数据暂未归并，各项目中的配置可能不同，请先选择**主仓**，下方表单将按主仓配置自动同步，可直接修改后提交。」（**无「一键同步」按钮**，配置自动同步）
  - **「主仓设置」单选**：列出所有关联项目（`associatedProjects`），默认选中当前主仓（`mainRepoProjectId`，标记「当前主仓」）。用户改选主仓 → 表单配置立即按 `projectConfigs[projectId].config` 重新同步（可继续手动修改）；提示「切换主仓后该仓库全部历史检测结果归属也随之迁移到新主仓项目」。
  - 「是否删除之前项目中的代码仓？」多选框列出所有关联项目，**可多选**，仅取消所选项目与该代码仓的关联（**非一次删除所有**；不勾选则不删除该项目下的该代码仓）
  - 若未勾选任何删除项 → 黄色警告条：「您未删除之前项目中的代码仓，修改下方配置将**同步修改项目A、项目B中的该代码仓配置**（代码仓配置全局唯一）。」
  - 表单字段全部可编辑；提交时携带 `mainRepoProjectId`（所选主仓）、`deleteProjectIds`（勾选的项目）与表单配置

### 2.2 SIG 组一键录入逻辑

> **配置来源**：用户在代码仓管理「全局配置」弹窗按平台（gitcode/gitee/github）配置 sig-info.yaml 所在位置（**每个平台唯一一个链接**，形如 `https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private/sig-info.yaml`），存 `project_repo_global_config.config_json`（§4.2.1）。sig-info.yaml 为固定格式（§2.2.0b），一键录入各接口**实时调对应平台 API 读取指定位置文件并直接解析返回**，**去除 webhook 推送 / 定时兜底 / 入库缓存** 逻辑。

#### 2.2.0 sig-info.yaml 位置配置（新增，位于「全局配置」弹窗，每平台唯一）

> **核心变化**：用户无需拆分填写 仓/分支/文件路径 三个字段，只需填写**一个完整的链接**——在代码托管平台对应代码仓、对应分支中找到 sig-info.yaml 文件，复制此时的完整链接即可（表单提供示例链接）。后端保存时解析链接为 `owner/repo/branch/path` 后实时校验可用性。

```
saveSigConfig(userId, projectId, platform, location):
  - platform: gitcode / gitee / github（位置所属平台）
  - location: { url, remark? }   // 该平台唯一 sig-info.yaml 链接（null 表示清空）
  1. 校验 platform 合法；校验链接格式：解析出 owner/repo/branch/path（
     https://{host}/{owner}/{repo}/blob/{branch}/{path}，path 为 sig-info.yaml 或 .yaml/.yml 且文件名含 sig-info）
  2. 读取 project_repo_global_config.config_json，将该平台 sigInfoLocation 更新为入参链接（其余平台配置保持不变）
  3. 实时校验：按解析出的 owner/repo/branch/path 调对应平台 getFileContent 验证文件存在且 YAML 可解析；
     不可用位置在响应中标记（不阻断保存，便于用户排查）
  4. 返回保存结果 + 位置可用性（可读 / 文件不存在 / 解析失败）

listSigConfig(userId, projectId, platform):
  1. 从 project_repo_global_config.config_json 取该平台配置的 sig-info.yaml 链接
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
  1. 从 project_repo_global_config.config_json 取该平台位置（校验属于该项目且平台一致）
  2. 实时调对应平台 getFileContent 读取 sig-info.yaml → 解析 repositories → List<{owner, repo}>
  3. 过滤：查 repo_project_ref where project_id=? → 得到当前项目已录入的 repo_url 集合
     - 仅保留**未录入当前项目**的仓库（已录入的不展示，避免覆盖已有配置）
  4. 按平台组装完整 repoUrl + 默认别名（repo 名，见 §2.2.3 别名规则）
     + 默认配置（默认分支/仓库责任人/开源类型/代码风格自动修复/告警抑制自动检视/是否参与运营 等，见 §2.2.3 默认参数表）
  5. 返回 [{ owner, repo, repoUrl, platform, defaultConfig: { alias, defaultBranchName,
           repoOwner, openSource, isAutoFormat, isSuppressionEnabled, isParticipateOperation, ... } }]
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
| 是否参与运营 | 是 | 固定默认，可编辑 |
| 仓库规则集配置 | 不配置 | 固定默认 |

```
sigImport(userId, userName, projectId, platform, repoConfigs):
  - repoConfigs: [{ repoUrl, config: { alias, defaultBranchName, repoOwner, purpose,
                  openSource, isAutoFormat, isSuppressionEnabled, isParticipateOperation, ... } }]  // 用户编辑后或默认值
  1. 从 project_repo_global_config.config_json 取位置 → 实时调对应平台读取 sig-info.yaml → 解析 repositories
     → 校验每个 repoUrl 都在本次解析结果中（防止前端伪造 / 过期数据）
  2. 事务内对每个 repoConfigs（owner/repo）:
     a. 查 repo_info by repo_url（理论上均为未录入当前项目的仓库，见 §2.2.1 过滤）
     b. 未命中 → insert repo_info (source=sig, sig_config_file=<location path>, 配置取 config)
     c. 命中（全局已存在但当前项目未关联）→ **不覆盖已有配置**（复用现有 repo_info），
        仅 upsert repo_project_ref (repo_id, project_id)
     d. upsert repo_project_ref (repo_id, project_id)
  3. 对每个新入库的 repo：异步同步平台元数据 + 配置 webhook（沿用现有逻辑，不阻塞录入）
  4. 返回 { imported: N, failed: [...] }
```

> **别名冲突**：同一项目内若多个仓库按默认别名生成后仍冲突（如两个仓 repo 名相同），按 `repo名-平台名`、`repo名-平台名2`... 递增直至唯一。

> **前端编辑/删除**：表格中每个仓库行提供「编辑配置」（单条）/ 顶部「批量编辑配置」按钮（作用于所有勾选仓库），复用与手动录入一致的配置表单，默认值见上表，可修改后保存或「恢复默认」；「删除」/「批量删除」用于移除选错、不想录入的仓库（仅从本次待录入列表移除，不影响已入库数据）。

> **SIG 同步已去除**：不再提供「SIG 同步」按钮与 `sig/sync-one` / `sig/sync-all` 接口——SIG 仓库配置全局唯一一份，需要调整配置时直接手动编辑即可（SIG 来源仓库同样允许编辑，见 §2.3）；已录入仓库若要重新从配置文件批量更新，可删除关联后重新执行 SIG 一键录入。

### 2.3 编辑逻辑（直接编辑 + 多项目主仓设置）

> **核心变化**：不再做「多项目影响提示」与「SIG 来源编辑拦截」——SIG 来源仓库同样允许手动编辑；新模型仓库配置全局唯一一份，编辑直接更新 `repo_info` 即可，自动影响所有关联项目。**存量 53 个共享仓（同一 repo_url 在 `repo_info` 存在多行、各项目配置不同）编辑时，先展示「主仓设置」让用户确认以哪个项目为主仓**，保存后以主仓配置为基准**覆盖其余项目（副仓）的配置**，兼容跨项目重复代码仓历史数据。

```
updateRepoInfo(userId, userName, projectId, RepoDTO, mainRepoProjectId, deleteProjectIds):
  1. normalize repoUrl → 按 repo_id 查 repo_info（编辑定位；同一 repo_url 多行时定位到当前项目行）
  2. 若该 repo_url 在 repo_info 存在多行未删除记录（存量 53 个共享仓）:
     - 前端先展示「主仓设置」单选（列出所有关联项目，默认选中当前主仓 mainRepoProjectId）
     - 用户选定主仓 → 表单按所选主仓对应行的配置自动同步（可修改）
  3. 保存：
     - 单行（新模型全局唯一）→ 直接 update repo_info 配置（同步影响所有关联项目）
     - 多行（存量共享仓）→ 以所选主仓配置为基准，更新该 repo_url 下所有未删除行的配置
       （覆盖主仓与副仓，保证各项目读到一致配置）
  4. 若 deleteProjectIds 非空 → 删除对应项目与该仓的关联（repo_project_ref；多行场景连同其行）
  5. 同步平台元数据 + webhook 配置（沿用现有逻辑）
```

> **说明**：手动录入命中已存在仓库时，前端在录入表单内提示「修改会同步修改之前项目中的代码仓配置」（见 §2.1.3）；编辑已录入仓库时，若该 repo_url 已在多个项目录入过（存量多行、配置可能不同），前端展示「主仓设置」蓝色提示条：「该代码仓已在多个项目录入且配置可能不同，请选择**主仓**，保存后将以主仓配置覆盖各项目（副仓）的配置。」保存后各项目配置统一为主仓配置（兼容 `repo_info` 跨项目重复历史数据）。

### 2.4 删除逻辑（含单删/批量删、子表清理与多项目语义）

> **现状说明（代码审计确认）**：现有删除接口为 [deleteRepoInfo](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/RepoController.java#L247-L261)（`POST /project-repo/delete-repo`）与 `batchDeleteRepoInfo`（`POST /project-repo/batch-delete-repo`），均只传 `id`（repo_id）、**不传 projectId**；删除为**物理删除**（XML `deleteById` / BaseMapper `delete`），并清理 `repo_branch`、`user_role`、`field_and_repo`、Mongo `sig_rule_set`，通知 codecheck 重算 is_used；**不清理 webhook**。**不存在「删除代码平台仓库」审批流**——`RepoDTO.reviewerId` 为未使用字段，删除链路无审批。若产品要求删除审批（feature-spec SOD 规则组 1/3），需作为**新能力**建设（见 §7.1.3），不能按「沿用现有」实现。

```
deleteRepoInfo(userId, userName, repoId, projectId):
  1. 查 repo_project_ref where repo_id=? and is_deleted=0 → 关联项目数 N
  2. N > 1 → 仅逻辑删除当前 project 的 ref（repo_info 保留，其他项目仍可用，子表数据不动）
  3. N == 1 → 删除 ref + 逻辑删除 repo_info（is_deleted=1）
     + 保留现有子表清理链路：删 repo_branch / user_role / field_and_repo / Mongo sig_rule_set
       + 通知 codecheck 重算 is_used（webhook 现状不清理，本期保持一致）
  4. 删除前沿用现有越权校验 verifyPermissionsByProduct（多项目语义见 §7.1.3）
```

```
batchDeleteRepoInfo(userId, userName, repoIds, projectId):
  - 复用单删语义：对每个 repoId 按 repo_project_ref 关联项目数 N 判定「删 ref」还是「删 repo_info + 子表」
  - 现状只传 repoIds，改造后需新增 projectId 入参，前端批量删除调用处补传当前项目 id
```

> **注意**：现有删除接口为 `deleteRepoInfo` / `batchDeleteRepoInfo`（**非** `deleteProjectRepo`），按 `id`（repo_id）删除。改造后两接口均需增加 `projectId` 入参以判断删 ref 还是删 repo_info。前端 `handleDeleteRepo` 调用处需补传 `project.value?.projectId`。

> **逻辑删除 vs 物理删除（对 7 仓的影响）**：现状为物理删除（删除后 7 仓按 `repo_info.project_id` 读取不到该行）。若改为逻辑删除（`is_deleted=1`），7 个未改造仓若不按 `is_deleted` 过滤，可能读到已删行。Phase 1 **默认建议保持物理删除**（与现状一致、对 7 仓零变化），仅「多项目时删 ref 不删 repo_info」这一语义走新模型；如需启用逻辑删除，必须先核对 7 仓查询是否带 `is_deleted=0` 过滤（见 §7.9 验收清单）。

### 2.5 历史存量数据迁移策略（分两阶段：Phase 1 只建关联，归并推迟）

> **背景**：存量体检发现 **53 个共享仓**（同一 `repo_url` 已在多个项目录入，`GROUP BY repo_url_normalized HAVING COUNT(DISTINCT project_id)>1`）。归并需将其他仓子表的 `repo_id` 重映射到基准行（如 sca `tbl_scan.repo_id`、anti-poison 相关表），而这些仓不归属本项目、不可控 → **归并推迟到 Phase 2**，Phase 1 只做无副作用的 **1:1 关联回填**。

#### Phase 1（本需求上线时执行）：1:1 回填 repo_project_ref，不归并

```
migrateRepoProjectRefPhase1():
  1. 扫描 repo_info 全表未删除记录（is_deleted=0），对每条记录 (repo_id, project_id)：
     - upsert repo_project_ref (repo_id, project_id)
     - 幂等：先查 (repo_id, project_id) 是否已存在，存在则跳过
  2. 统计 53 个共享仓待归并清单：
     - SELECT repo_url_normalized FROM repo_info WHERE is_deleted=0
         GROUP BY repo_url_normalized HAVING COUNT(DISTINCT project_id)>1
     - 对每个命中 repo_url：记录涉及 project_id 列表、基准 repo_id（最早 create_at 行），
       写入待归并清单（migration_queue 表或配置，供 Phase 2 使用）
  3. 回填 repo_info.project_id：对新录入仓库（唯一行）取 repo_project_ref 中该 repo 最早关联记录的
     project_id 写入（过渡期冗余）；存量多行 repo_url 每行保持自身 project_id 不变
  4. 校验：repo_project_ref 未删除记录数 = repo_info 未删除记录数（1:1 完整性）
```

- **效果**：新增一张关联表并 1:1 回填，对 7 个下游仓零影响；53 个共享仓多行原样保留（各自项目照常可见）；新录入不再新增多行（代码层查重，见 §5.3）。
- **Phase 1 明确不做**：不合并 `repo_info` 多行、不删除任何存量行、不改存量 `project_id`、不加唯一索引。

#### Phase 2（7 仓逐个可控后执行）：按 repo_url 归并 53 个共享仓

```
migrateRepoProjectRefPhase2():
  1. 按待归并清单逐个 repo_url_normalized 处理：
     a. 选唯一 repo_info 基准行：优先取**用户通过「主仓设置」指定的主仓项目对应行**（过渡期已录入/编辑时记录）；
        未指定主仓时默认取最早 create_at 行（保留其配置、source、sig_config_file）
     b. 其余行的 project_id 合并到 repo_project_ref：
        - 在 (基准 repo_id, 其余行 project_id) 上 upsert 关联
        - 先将各子表（sca tbl_scan / anti-poison 相关表等，需对应仓配合数据脚本）中
          repo_id=其余行 repo_id 的记录重映射到基准 repo_id，再删除其余行
     c. 删除其余 repo_info 行（逻辑删除 is_deleted=1）
  2. 全部归并完成后校验：SELECT repo_url_normalized, COUNT(*) FROM repo_info WHERE is_deleted=0
     GROUP BY repo_url_normalized HAVING COUNT(*)>1 → 期望 0 行
  3. 校验通过后 ALTER TABLE repo_info ADD UNIQUE INDEX uk_repo_url_normalized (repo_url_normalized)
  4. 7 仓全部切换为从 repo_project_ref 取 project_id 后，再择期 ALTER TABLE repo_info DROP COLUMN project_id
```

**清理时机与灰度**：
- **Phase 1 迁移脚本在服务上线后统一执行（不阻塞上线）**，执行期间新录入重复由代码层事务内查重 + 锁保证（见 §5.3 并发控制），规避「上线窗口并发录入触发唯一键冲突」「存量未清理导致加唯一索引直接失败」两个风险。
- **Phase 2 归并与 7 仓切换解耦**：归并脚本独立执行、可回滚，由灰度开关 `coderepo.repo-decouple.enabled` 控制 coderepo 新旧逻辑切换；每切换一个可控仓再归并一批 53 个共享仓，全部完成后再加唯一索引、再删 `project_id`。**归并不在 Phase 1 执行，也不在 7 仓可控前执行**。

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
- **代码仓录入配置**：维护该平台**唯一一个** sig-info.yaml **链接**（表单提供示例链接，用户在对应代码仓、对应分支中找到 sig-info.yaml 后复制完整链接填入），保存时按平台实时校验文件可用性（OK / FILE_NOT_FOUND / PARSE_ERROR），存 `project_repo_global_config.config_json[platform].sigInfoLocation`（存链接字符串）
- **角色映射**：仅 GitCode 页签展示，gitcode 角色 ↔ openLiBing 角色行式编辑（沿用现有 roleMappingDialog 交互），存 `project_repo_global_config.config_json.gitcode.roleMapping`
- 底部「保存」统一提交：公共账号走新增接口、sig-info 位置与角色映射走 `update-global-config`

#### 2.6.2 录入对话框改造（[Repos/index.vue](file:///d:/Develop/Java/openlibing-web/apps/web-openlibing/src/views/Repos/index.vue) 的 `el-dialog`）

- 对话框顶部新增「录入方式」单选切换：`手动录入` / `SIG 组一键录入`
- `手动录入` 模式：沿用现有表单，新增 `repoUrl` blur 时调检测接口（`checkRepoUrl`），命中时按 §2.1.3 展示「主仓设置」（默认当前主仓，改选主仓后按所选主仓配置重新同步）+ 自动同步配置 + 选择性删除 + 修改同步提示（**无「一键同步」按钮**）
- `SIG 组一键录入` 模式：
  - 隐藏现有表单字段
  - 顶部提示条：「SIG 组录入默认使用默认配置（别名=仓库名、责任人=建仓人、开源类型=主导开源、是否参与运营=是、其余各开关=否）；下拉仅展示尚未录入当前项目的 SIG 仓库，已录入的不展示，不会覆盖已有配置；sig-info.yaml 链接在「全局配置」中维护」
  - 新增「平台」下拉（gitcode/gitee/github），**不单独展示配置文件**（每平台位置唯一，在「全局配置」中维护）
  - **「选择仓库」下拉多选框**（调 `listSigReposInConfig`）：仅展示**尚未录入当前项目**的仓库（已录入的不展示），多选后**表格才展示所选仓库列表**
  - 表格列：`选择`、`代码仓`、`代码仓别名`、`平台`、`默认分支`、`仓库责任人`、`开源类型`、`用途`、`代码风格自动修复`、`告警抑制自动检视`、`是否参与运营`、`操作`（`编辑配置` / `删除`）——**无「录入状态」列**
  - 顶部批量操作条：「批量编辑配置」（作用于勾选仓库）/「批量删除」；单条行内「编辑配置」「删除」
  - 底部「一键录入 (N)」按钮 → 调 `sigImport`（N 为表格内仓库数）

#### 2.6.3 列表页改造

- 工具栏新增「全局配置」按钮（§2.6.1）；**无**「SIG 同步」按钮（SIG 同步功能已去除，见 §2.2.3 说明）
- 列表新增列「来源」（手动/SIG），通过 `repo_info.source` 返回
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

#### 图 1：手动录入（主仓设置 → 按主仓自动同步配置 + 选择性删除）

```
┌──────────────────────────────────────────────────────────┐
│  录入代码仓                                       ✕       │
│  ◉ 手动录入   ○ SIG 组一键录入                            │
├──────────────────────────────────────────────────────────┤
│  仓库链接: https://gitcode.com/org/repo.git   (blur 检测) │
│                                                          │
│  ℹ 检测到该代码仓已在 项目A、项目B 录入。历史数据暂未归并，│
│    各项目配置可能不同，请先选择主仓，表单将按主仓配置自动   │
│    同步，可直接修改后提交。（无一键同步按钮）              │
│  主仓设置（配置以主仓为准自动同步；主仓参与检测，副仓仅记录）│
│    ◉ 项目A（当前主仓）   ○ 项目B                          │
│    （切换主仓后表单按新主仓重新同步，检测结果归属随之迁移） │
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
│  ☑│ 代码仓      │ 别名   │ 默认分支│ 责任人 │ 开源类型│ 代码风格修复│ 告警抑制 │ 是否运营 │ 操作            │
│ ──┼────────────┼────────┼─────────┼────────┼────────┼──────────┼─────────┼─────────┼─────────────────│
│  ☑│ org/repo-a  │ repo-a │ master  │ u-a    │ 主导开源│ 否       │ 否      │ 是      │ 编辑配置 删除   │
│  ☑│ org/repo-b  │ repo-b │ master  │ u-b    │ 主导开源│ 否       │ 否      │ 是      │ 编辑配置 删除   │
│  ☑│ org/repo-d  │ repo-d │ main    │ u-d    │ 主导开源│ 是       │ 否      │ 是      │ 编辑配置 删除   │
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
  @TableField("create_at") private Date createAt;
  @TableField("create_by") private String createBy;
  @TableField("update_at") private Date updateAt;
  @TableField("update_by") private String updateBy;
  @TableField("is_deleted") private Boolean isDeleted;
}

/** 项目级全局配置实体（原 project_gitcode_role_mapping 泛化） */
@Data @Builder @AllArgsConstructor @NoArgsConstructor
@TableName("project_repo_global_config")
public class ProjectRepoGlobalConfigEntity implements Serializable {
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

> **原 `GitCodeRoleMappingEntity`（表 `project_gitcode_role_mapping`）作废**：泛化为 `ProjectRepoGlobalConfigEntity`（表 `project_repo_global_config`），`roleMapping` 字段迁移至 `config_json.gitcode.roleMapping`。旧表相关 Mapper/Service（`GitcodeRoleMappingMapper`、`GitcodeRoleMappingService`）改造为基于新表的读写。

#### 3.1.2 现有 Entity 改造

[RepoInfoEntity](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/entity/space/RepoInfoEntity.java) 改动：

| 改动 | 字段 | 说明 |
|------|------|------|
| 保留（过渡期冗余） | `projectId` | **暂不删除**；值=该行所属项目（新录入仓库回填为 `repo_project_ref` 中该 repo 最早关联记录的 `project_id`），保证 7 个下游仓继续按旧方式读取。7 仓全部切换后不再依赖该字段，后续择期删除 |
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

[RepoInfoMapper](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/resources/mapper/RepoInfoMapper.xml) 改造（**全量按 `project_id` 过滤点清单**，均为 coderepo 侧需切换为 `repo_project_ref` 的查询）：
- `selectByRepoUrl`：新增，按 normalize 后的 repo_url 查询（用于冲突检测）
- `queryRepoInfo`（XML L647-649）：现有按 `project_id` 查询改为 JOIN `repo_project_ref`（本需求 coderepo 切换）
- `queryRepoInfoByProjectId`（L115-119）：`where project_id=?` 改为 JOIN `repo_project_ref`；调用方 [XxlJobHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java) L231/L462、RepoServiceImpl.queryProjectRepoUrlList L5514
- `getNewestSyncTime`（L530-535）：`where project_id=?` 改 JOIN；调用方 RepoServiceImpl L557/L591
- `queryByProjectAndRepoName` / `queryByProjectAndRepoNameCount`（L1103-1142）：`project_id=?` 改 JOIN；调用方 RepoServiceImpl.getRepoSelect L3086/L3089
- `count`（L862-864）：`and project_id=?` 改 JOIN；调用方 doQueryRepoInfo / doInternalQueryRepoInfo
- **公共片段 `repoInfoQueryWhere`（L310-311）**：`and ${rp}project_id = #{info.projectId}` 改为 EXISTS 子查询 `AND ${rp}repo_id IN (SELECT repo_id FROM repo_project_ref WHERE project_id=#{info.projectId} AND is_deleted=0)`；该片段被 5 个查询复用，`rp` 别名有 `''`（repo_info 直查）与 `'ri.'`（repo_info ri 别名）**双分支，改造时两个分支都要适配**：`queryRepoInfoByLimit`（L461）、`queryRepoInfoExport`（L483）、`queryRepoIdsByFilter`（L506）、`queryRepoFilterMetaRows`（L513）、`queryRepoFilterMetaGroupBy`（L522）
- `insertRepo`（L964-978）：保留 `project_id` 列写入（首次录入即最早关联），同时新增 `repo_project_ref` 写入
- `updateRepo`（L981-1064）：不变（已按 `repo_id`；XML 虽支持更新 `project_id` 但无调用方，维持现状不更新）
- `getProjectIds`（L1143-1146）：`SELECT DISTINCT project_id FROM repo_info` 改为 `FROM repo_project_ref WHERE is_deleted=0`；调用方 SyncUserServiceImpl.refreshProjectIdCache L521
- **BaseMapper 直查（绕过 XML）**：RepoServiceImpl.getPlatformOwner（L3032-3048）`new QueryWrapper<RepoInfoEntity>().eq("project_id", projectId)` 同样改 EXISTS/JOIN 关联表，查询「项目下某平台的所有 platform_owner」
- **告警抑制跨项目同步（语义说明）**：`updateSuppressionEnabledByRepoUrl`（L1074）/ `batchUpdateSuppressionEnabledByRepoUrls`（L1086）按 repo_url 更新多行。新模型下新仓库为全局单行、开关天然全局（同步方法对全局单行退化为无需同步）；53 个共享仓多行期间继续按现状同步；Phase 2 归并完成后移除同步逻辑（见 §4.4 附注）

#### 3.1.4 新增 Service

```java
public interface RepoProjectRefService {
  List<RepoProjectRefEntity> listByRepoId(Integer repoId);
  List<RepoProjectRefEntity> listByProjectId(Integer projectId);
  int countByRepoId(Integer repoId);
  void upsert(Integer repoId, Integer projectId, String operator);
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

/** 项目级全局配置读写（project_repo_global_config.config_json） */
public interface ProjectRepoGlobalConfigService {
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
  /** 构造 RepoDTO 默认参数（用途=自研源码/语言=不选/开源类型=主导开源/令牌=不填/是否参与运营=是/各开关=否/规则集=不配置） */
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
  private Integer mainRepoProjectId;    // 当前主仓项目 id（repo_info.project_id；历史多行默认=最早 create_at 行所属项目）
  private RepoInfoEntity currentConfig; // 当前主仓对应配置（默认同步基准，前端自动同步到表单）
  private List<ProjectConfigVO> projectConfigs;      // 各关联项目各自的配置（历史多行配置可能不同，供「主仓设置」切换）
  private List<AssociatedProjectVO> associatedProjects;  // 该 repo 已关联的项目列表（供选择性删除）
}

/** 某关联项目及其配置（「主仓设置」切换主仓后按此重新同步表单） */
@Data @Builder
public class ProjectConfigVO {
  private Integer projectId;
  private String projectName;
  private RepoInfoEntity config;   // 该项目对应 repo_info 行的配置
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
  private Boolean isParticipateOperation;        // 是否参与运营（默认是）
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
| [RepoDTO](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/dto/space/RepoDTO.java) | 新增 `mainRepoProjectId`（Integer，手动录入命中已存在仓库时用户选定的**主仓项目**，默认当前主仓；配置同步与下游任务归属以主仓为准，设为本项目则主仓迁移到当前项目）与 `deleteProjectIds`（List\<Integer\>，手动录入命中已存在仓库时，勾选要删除关联的「之前项目」ID 列表；不传表示不删除，修改配置同步影响所有仍关联项目） |
| [RepoService](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/RepoService.java) | `addRepoInfo` 增加「命中已存在」分支（自动同步 + 选择性删除 `deleteProjectIds`）；`updateRepoInfo` 直接编辑（**无** sig 拦截、**无**多项目确认）；`deleteRepoInfo` 增加 `projectId` 入参；新增 `checkRepoUrl` |
| [RepoServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java) | 实现上述改造；`queryRepoInfo` SQL 改 JOIN `repo_project_ref`；SIG 相关委托 `SigRepoImportService` |
| [RepoInfoMapper.xml](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/resources/mapper/RepoInfoMapper.xml) | `queryRepoInfo` 改 JOIN；新增 `selectByRepoUrl`；`addRepoInfo` 保留 `project_id` 列写入（首次录入即最早关联） |
| 新增 [ProjectRepoGlobalConfigServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/) | 实现 `ProjectRepoGlobalConfigService`：`config_json` 读写（Jackson 序列化/反序列化，按平台合并）、公共账号更新（复用现有加密逻辑） |
| 改造 [GitcodeRoleMappingMapper.xml](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/resources/mapper/GitcodeRoleMappingMapper.xml) | 原 `project_gitcode_role_mapping` 读写改为 `project_repo_global_config.config_json.gitcode.roleMapping` 读写 |
| 改造 [ProjectCommonAccountServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/) | 新增 `updateProjectCommonAccount`（登录名 + 令牌按平台更新，令牌加密入库、留空不覆盖） |

#### 3.1.8 现有业务读取点与定时任务改造清单（`repoInfo.getProjectId()` 多项目语义）

> **审计发现（补项 1）**：除 Mapper 层按 `project_id` 过滤的查询外（见 §3.1.3），业务代码中还有 **~40 处**直接读取 `repoInfo.getProjectId()`（`repoInfoEntity.getProjectId()` / `repoInfo.getProjectId()` / `dataEntity.getProjectId()` 等），其「多项目语义」此前未定义。切换新模型后该字段仅是**冗余的过渡值**，各读取点的语义必须统一明确，避免 Phase 2 归并时误读。以下按用途分类枚举（含代表调用点），实施时逐点核对。

**业务读取点分类清单（过渡期统一语义）**：

| 类别 | 代表调用点（`repo_info` 行内 project_id 读取） | 过渡期语义（Phase 1） | Phase 2 需定义 |
|------|-----------------------------------------------|----------------------|----------------|
| 平台令牌获取 | [RepoServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java) L2379（getGiteeToken）/L2386（getGitcodeToken）/L2394（getGithubToken）/L4869/L4988（getProjectToken）；[CommonServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/CommonServiceImpl.java) L149；[NotifyConfigEventHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/handler/NotifyConfigEventHandler.java) L344/L353；[MergeRequestEventHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/handler/MergeRequestEventHandler.java) L847/L855/L871 | 取**最早关联项目**（= 行内 project_id）的平台 token | 多关联仓库的多项目 token 取数规则 |
| 越权/权限校验 | [CommonServiceImpl.verifyPermissionsByProduct](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/CommonServiceImpl.java#L139-L151) L149（`actualProjectId = repoInfo.getProjectId()`） | 见 §7.1.3：改为「请求 projectId ∈ ref 关联集合」校验 | 多项目任一项目可操作该仓库的权限模型 |
| 业务查询/列表 | [RepoServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java) L557/L591（getNewestSyncTime）、L3086/L3089（queryByProjectAndRepoName） | 已切 JOIN `repo_project_ref`（§3.1.3），此处入参 projectId 即请求项目 | 无需变更 |
| 删除/编辑/同步 | [RepoServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java) L2123（delete 日志+权限）、L2195（batch delete）、L2566（query 日志）、L5200（update 新旧对比）、L1903/L1906（update 写入） | 删除按 §2.4（ref 关联数判定）；编辑/同步沿用行内 projectId 过渡语义 | 归并后按基准行 projectId |
| 成员/角色关系 | [RepoUserServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/RepoUserServiceImpl.java) L203/L254/L284/L298（按 repo 所属项目查/建成员、项目角色） | 沿用行内 projectId（最早关联）维护成员关系 | 多关联时成员关系是否 per-project 需产品明确 |
| 上报/审计日志关联 | [OpenubmcServiceImpl](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/OpenubmcServiceImpl.java) L178/L224（ubmc 资源上报 projectId）；[SpaceUserLogHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/aop/SpaceUserLogHandler.java) L77、CommonServiceImpl L724（审计日志关联项目名） | 仅用于归属/展示，沿用过渡语义即可 | 无需变更 |
| 事件归属判定 | [MergeRequestEventHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/handler/MergeRequestEventHandler.java) L229（事件 op 的 projectId）；[XxlJobHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java) L451（codeMetrics 归属对比） | 沿用行内 projectId（过渡语义） | 归并后按基准行 |

**定时任务改造清单（审计补项 6）**：

| 定时任务 | 读取 `project_id` 的点 | Phase 1 改造 |
|----------|----------------------|--------------|
| [XxlJobHandler.syncRepoInfoHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java#L70-L75) | L231 `queryRepoInfoByProjectId(projectId)` | 查询已切 JOIN（§3.1.3），零逻辑改动 |
| [XxlJobHandler.codeMetricsObsImportHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java#L331-L332) | L451 归属对比、L462 `queryRepoInfoByProjectId` | 同上 |
| [XxlJobHandler.refreshWebhookHandler](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/XxlJobHandler.java#L284-L285) | 全量查 repo 刷新 webhook，projectId 仅用于取 token | 沿用行内 projectId 取 token（token 规则见上表） |
| [FrameworkJobs.refreshProjectIdCache](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/common/job/FrameworkJobs.java#L147-L170) | SyncUserServiceImpl.refreshProjectIdCache L521 `getProjectIds`（`SELECT DISTINCT project_id FROM repo_info`） | 已改为 `FROM repo_project_ref WHERE is_deleted=0`（§3.1.3） |

> **结论**：Phase 1 定时任务**零逻辑改动**（查询已切 JOIN；token/归属沿用 `repo_info.project_id` 过渡语义）。「按项目取数 / 取 token / 鉴权 / 成员」类读取需结合请求上下文 projectId（若有）改为从 `repo_project_ref` 取；「仅展示 / 日志 / 上报」类沿用过渡语义即可。

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
ALTER TABLE repo_info ADD COLUMN is_participate_operation TINYINT(1) NOT NULL DEFAULT 1
  COMMENT '是否参与运营（默认是）' AFTER sig_config_file;

-- 2. 数据迁移（见 §2.5）：对 repo_url 归一化（Phase 1 只回填 repo_url_normalized，不加唯一索引）
ALTER TABLE repo_info ADD COLUMN repo_url_normalized VARCHAR(512) NULL
  COMMENT '归一化后的repo_url(去.git/末尾斜杠/统一小写owner-repo)';
-- 应用层回填 repo_url_normalized，加普通索引用于冲突检测/查重
ALTER TABLE repo_info ADD INDEX idx_repo_url_normalized (repo_url_normalized);
-- 唯一索引暂不添加：存量 53 个共享仓多行在 Phase 2 归并完成、GROUP BY 校验 0 行后再择期升级
-- ALTER TABLE repo_info ADD UNIQUE INDEX uk_repo_url_normalized (repo_url_normalized);

-- 3. project_id 暂不删除（过渡期冗余）：值=该行所属项目（新录入仓库回填 repo_project_ref 中最早关联记录的 project_id），
--    保证 7 个下游仓（codecheck/cicd/framework/anti-poison/sca/gateway/vulnerability）继续按旧方式读取不中断。
--    待 7 仓全部切换为从 repo_project_ref 取 project_id、53 个共享仓归并完成后再择期删除：
-- ALTER TABLE repo_info DROP COLUMN project_id;
```

**repo_url 归一化规则**（应用层 [RepoUrlNormalizer](#316-新增工具类)）：
- 去末尾斜杠
- 去 `.git` 后缀
- 统一 `https://` 协议头（`http://` → `https://`，`git@host:` SSH 形式 → `https://host/`）
- owner/repo 部分小写（GitCode/Gitee/GitHub 的 owner/repo 大小写不敏感）

归一化后存入 `repo_url_normalized`（先加普通索引用于冲突检测/查重；暂不加唯一索引，存量清理完成后择期升级），`repo_url` 原值保留用于展示与跳转。

**`repo_name`（代码仓别名）唯一性范围**：`repo_name` 沿用 `repo_info.repo_name`（全局单行，配置单一来源），**唯一性范围 = 项目内唯一、不做全局唯一**——同一仓在多个项目共享同一别名；同名不同仓在**当前项目内**按 §2.2.3 别名冲突规则区分（`repo名-平台名` 递增）。不为此字段加全局唯一约束（§1.5 决策）。

#### 4.2.1 改造表 `project_repo_global_config`（原 `project_gitcode_role_mapping` 泛化）

**改造思路**：将原 `project_gitcode_role_mapping`（仅存 GitCode 角色映射）泛化为项目级通用配置表 `project_repo_global_config`。所有项目级配置项（GitCode 角色映射、各平台 sig-info.yaml 位置等）**统一以 JSON 存入 `config_json`**，后续新增配置项只需在 JSON 中扩展、无需再改表结构。

**SIG 配置内容不落库**：sig-info.yaml 由各接口实时调对应平台读取解析，本表只保存位置元数据（含在 `config_json` 中）。

```sql
-- 1. 原 project_gitcode_role_mapping 表重命名 + 增加 config_json 字段
RENAME TABLE project_gitcode_role_mapping TO project_repo_global_config;

ALTER TABLE project_repo_global_config
    ADD COLUMN config_json JSON NULL COMMENT '项目级全局配置(JSON)：含各平台 sig-info.yaml 位置、gitcode 角色映射等，按平台分键存储，便于后续扩展新配置项' AFTER project_id;

-- 2. 数据迁移：将原 role_mapping 文本（gitcode 角色映射 JSON 数组字符串）迁移到
--    config_json 的 gitcode.roleMapping 键，然后删除旧字段（见 §2.5）
-- ALTER TABLE project_repo_global_config DROP COLUMN role_mapping;
```

**改造后表结构**：

```sql
CREATE TABLE project_repo_global_config (
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

过渡期 `repo_info.project_id` **保留不删**（值=该行所属项目；新录入仓库回填为 `repo_project_ref` 中该 repo 最早关联记录的 `project_id`），双轨兼容：

- **Phase 1（本需求）**：仅 `coderepo` 全面切换为从 `repo_project_ref` 取 `project_id`（查询 JOIN 关联表，写入同时维护两表），不再依赖 `repo_info.project_id`；**framework 做副仓拦截改造（§7.1.4），其余 6 仓（codecheck/cicd/anti-poison/sca/gateway/vulnerability）一律不改**，仍从 `repo_info.project_id` 读取（该行所属项目；53 个共享仓多行保留、各自项目照常可见，过渡期单项目语义可接受，见 §1.2 说明）
- `addRepoInfo`：写 `repo_info`（保留 `project_id` 写入，首次录入即最早关联）+ 写 `repo_project_ref`
- `queryRepoInfo`（coderepo）：JOIN `repo_project_ref` 取 `project_id`
- **Phase 2（7 仓逐个可控后）**：7 仓逐个切换为从 `repo_project_ref` 取 `project_id`，灰度开关 `coderepo.repo-decouple.enabled=true` 仅走新模型；全部切换完成后归并 53 个共享仓、校验 0 行后加唯一索引，最后 `DROP COLUMN project_id`（见 §2.5 Phase 2）

### 4.5 ER 关系

```
project (1) ──── (N) repo_project_ref (N) ──── (1) repo_info
                     │                            │
                     │ source: manual/sig         │ repo_url_normalized
                     │ sig_config_file            │ source: manual/sig
                     │                            │ sig_config_file
                     │
                     └─ uk(repo_id, project_id)

project (1) ──── (1) project_repo_global_config ──实时读取──▶ SIG 仓 sig-info.yaml (gitcode/gitee/github)
                      config_json[平台].sigInfoLocation          │ 解析 repositories
                                          + roleMapping           ▼
                                        repo_info (source=sig) + repo_project_ref
```

### 4.6 数据量预估

| 维度 | 估算 |
|------|------|
| repo_info | Phase 1 不归并、规模不变（< 10 万行）；Phase 2 归并 53 个共享仓后略减 |
| repo_project_ref | Phase 1 与 repo_info 未删除行 **1:1**（约 10 万行）；归并后按 repo 数 × 平均关联项目数（1.2）收缩 |
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
| `project_repo_global_config` | `uk_project (project_id, is_deleted)` | 每项目一条，按项目查全局配置（sig-info 位置 + 角色映射） |

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

- **位置元数据**：`listSigConfig` 读 `project_repo_global_config.config_json`（按项目唯一，走 `uk_project`），毫秒级
- **实时读取**：`listSigReposInConfig` / `sigImport` 对该平台唯一位置调**对应平台**（gitcode/gitee/github）`getFileContent` 读取 sig-info.yaml → `SigInfoClient` 解析 repositories（§4.3）
- **超时与降级**：平台调用设置超时（如 3s），单个平台位置失败不影响其他平台（标记 UNREACHABLE）；全部失败返回明确错误提示稍后重试
- **并发读取优化**：不同平台的唯一位置独立读取（互不阻塞）；单平台仅一个位置，无需并行放大

#### 5.2.2 不引入缓存的部分

- `repo_info` 查询：走索引足够快，不引入缓存避免一致性问题
- `checkRepoUrlConflict`：每次录入必查最新，不缓存
- sig-info.yaml：内容以 gitcode 实时文件为准，不缓存（保证 SIG 组改文件即生效）；若后续调用量增大，可评估按 `(owner/repo/branch/path, sha)` 短时缓存，本期不做

### 5.3 并发控制

- **录入并发**：同一 `repo_url` 两个项目同时首次录入 → 应用层在事务内按 `repo_url_normalized` 查重（`SELECT ... FOR UPDATE` 锁行 / 分布式锁串行化），后到者查到已存在走「命中」分支（前端已自动同步配置，提交时按表单更新配置 + 可选选择性删除之前项目关联，见 §2.1）；**不依赖 DB 唯一索引兜底**（存量 53 个共享仓在 Phase 2 归并完成前不加唯一约束，见 §2.5 清理时机）。**53 个共享仓（多行）不计入新录入查重**——查重仅针对「该 repo_url 无未删除行」的新仓库，多行 repo_url 按 §2.1 分流走现状行级语义
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
  "isParticipateOperation": true,   // 新增, 可选: 是否参与运营（默认是）
  "mainRepoProjectId": 2,   // 新增, 可选: 手动录入命中已存在仓库时用户选定的主仓项目 ID（默认当前主仓）；
                            // 配置同步与下游任务归属以主仓为准；设为本项目则主仓迁移到当前项目
  "deleteProjectIds": [3]   // 新增, 可选: 手动录入命中已存在仓库时，勾选「是否删除之前项目中的代码仓」的项目 ID 列表；
                            // 空数组/不传表示不删除，修改配置同步影响所有仍关联项目（前端已提示）
}
```

**响应**（不变）：`DataResult<Integer>`（repoId）

**业务变化**：见 §2.1。`repo_url` 命中已存在仓库时**按用户选定主仓（`mainRepoProjectId`）同步其配置到表单**（前端 blur 时已调 check-repo-url），提交时按表单更新配置（未删除之前项目时同步影响所有仍关联项目）、按 `mainRepoProjectId` 确定主仓归属（设为本项目则迁移主仓到当前项目）、可选按 `deleteProjectIds` **选择性删除**所选项目关联（仅取消关联，repo_info 保留）。后端按归一化 `repo_url` 二次查重防并发。

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

**用途**：手动录入时 `repoUrl` blur 触发，检测 repo_url 全局是否已存在；命中时返回**当前主仓**、**各关联项目配置**（前端「主仓设置」默认按当前主仓同步，改选主仓后按所选主仓配置重新同步）与已关联项目列表（供**选择性删除**）。

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
    "mainRepoProjectId": 2,           // 当前主仓项目（repo_info.project_id；历史多行默认=最早 create_at 行所属项目）
    "currentConfig": {                // 当前主仓对应配置（默认同步基准）
      "repoName": "repo", "repoOwner": "sig-owner", "purpose": "自研源码",
      "openSource": "lead", "assumePr": "1", "autoTrigger": "1",
      "autoTriggerDesignScan": "0", "isAutoFormat": false,
      "isSuppressionEnabled": true, "isParticipateOperation": true, "disallowSelfMerge": 1,
      "disallowUnresolvedDiscussionsMerge": 0, "repoLanguage": "java"
    },
    "projectConfigs": [               // 各关联项目各自的配置（历史多行配置可能不同）
      { "projectId": 2, "projectName": "项目A",
        "config": { /* 同 currentConfig 字段 */ } },
      { "projectId": 3, "projectName": "项目B",
        "config": { /* 同 currentConfig 字段 */ } }
    ],
    "associatedProjects": [
      { "projectId": 2, "projectName": "项目A" },
      { "projectId": 3, "projectName": "项目B" }
    ]
  }
}
```

前端据 `exists=true`：展示「主仓设置」单选（`associatedProjects`，默认选中 `mainRepoProjectId`，标记「当前主仓」），默认将 `currentConfig` 同步到表单（可修改）；用户改选主仓后按 `projectConfigs[projectId].config` 重新同步表单；展示「是否删除之前项目中的代码仓」多选（`associatedProjects`）；未勾选删除项时提示「修改会同步修改之前项目中的代码仓配置」。

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

**数据来源**：读 `project_repo_global_config.config_json`（按平台分键，§4.2.1）+ `project_common_account_info`（登录名 + 掩码令牌）。

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

**业务变化**：保存时解析链接为 `owner/repo/branch/path`（`https://{host}/{owner}/{repo}/blob/{branch}/{path}`），实时调**对应平台** `getFileContent` 校验文件存在且 YAML 可解析（`status`=OK / FILE_NOT_FOUND / PARSE_ERROR），不可用位置不阻断保存，便于用户排查；链接写入 `project_repo_global_config.config_json[platform].sigInfoLocation`（§4.2.1，替代原表内逐行 upsert；传 null 清空该平台位置）。

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
          "isAutoFormat": false, "isSuppressionEnabled": false, "isParticipateOperation": true
        }
      },
      {
        "owner": "openlibing", "repo": "repo-b", "platform": "gitcode",
        "repoUrl": "https://gitcode.com/openlibing/repo-b.git",
        "defaultConfig": {
          "alias": "repo-b", "defaultBranchName": "master", "repoOwner": "u-b",
          "openSource": "主导开源", "purpose": "自研源码",
          "isAutoFormat": false, "isSuppressionEnabled": false, "isParticipateOperation": true
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
                  "isAutoFormat": false, "isSuppressionEnabled": false, "isParticipateOperation": true }
    },
    {
      "repoUrl": "https://gitcode.com/openlibing/repo-b.git",
      "config": { "alias": "repo-b", "defaultBranchName": "master", "repoOwner": "u-b",
                  "openSource": "主导开源", "purpose": "自研源码",
                  "isAutoFormat": true, "isSuppressionEnabled": false, "isParticipateOperation": true }
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

**业务变化**：后端校验 `platform` 属于该项目且该项目已配置该平台位置（`project_repo_global_config.config_json` 白名单，§7.2），实时调对应平台读取该位置 sig-info.yaml 解析 repositories，校验每个 `repoConfigs[].repoUrl` 均在解析结果中（防伪造/过期数据）且**尚未录入当前项目**，然后事务内逐个 upsert `repo_info`（未命中才新建，命中复用不覆盖）+ upsert `repo_project_ref`（§2.2.3）。

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

### 6.16 内部 API 契约说明与接口命名对齐（审计补项 9、11）

**内部 API 契约（供下游仓 Feign 调用，无 userId / 不做横向越权，由网关层鉴权）**：
- [InternalProjectRepoController](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/controller/InternalProjectRepoController.java) `POST /project-repo/internal/query-repo`：语义与 `POST /project-repo/query-repo` 一致但不要求 `userId` 参数；响应 `data.list` 为精简视图对象（仅含 repoId / projectId / repoName / repoUrl / repoOwner / platform / status），**不返回** accessToken 解密后的平台用户信息 / webhook 详情 / createBy / updateBy 等敏感字段。
- **切换 `repo_project_ref` 后的契约澄清**：`projectId` 入参 = 期望查询的项目，返回**该项目关联的仓库**（coderepo 侧已 JOIN `repo_project_ref`）；对存量 53 个共享仓多行按行返回（与旧版一致），对新模型多关联仓库返回该请求项目对应的关联（多对多语义）——**下游仓零改动**，`repoId` / `projectId` 仍同表可查，不破坏下游依赖。
- 删除仓库后通知 openlibing-codecheck 重算 `is_used` 的调用（§2.4）契约不变，仍走 `OpenlibingCodeCheckClient`。

**接口命名对齐说明（避免新旧命名混用）**：
- 删除接口为 `POST /project-repo/delete-repo` / `POST /project-repo/batch-delete-repo`（Controller 方法 `deleteRepoInfo` / `batchDeleteRepoInfo`），**不是** `deleteProjectRepo`；文档与实施均以此为准（§2.4 已注明）。
- 内部查询 `/project-repo/internal/query-repo`（internal 前缀）与前端 `/project-repo/query-repo` 语义一致但鉴权层级不同，**禁止前端调用 internal 版本**。
- 新增接口统一命名：`check-repo-url` / `global-config`（get/update）/ `update-project-common-account` / `sig/config`（保存/查询）/ `sig/repos` / `sig/import`（§6.4-6.13 契约汇总见 §6.14）。

## 7. 安全设计

### 7.1 鉴权

#### 7.1.1 现有接口鉴权不变

- `/project-repo/add-repo`、`/update-repo`、`/delete-repo`、`/query-repo`：网关 token + 角色校验（见 [feature-spec.md](./feature-spec.md) 权限矩阵）
- 沿用 `userId` / `userName` 入参 + 网关透传

#### 7.1.2 新增 SIG 接口鉴权

- `/global-config`（查询）、`/sig/config`（查询）、`/sig/repos`：读权限，沿用 `query-repo` 的角色集合
- `/global-config`（更新）、`/update-project-common-account`、`/sig/config`（保存）、`/sig/import`：写权限，沿用 `add-repo` 的角色集合（产业管理者、项目审批人员、流水线工程师、项目管理员）
- 所有 SIG 与全局配置接口均校验 `userId` 对 `projectId` 的访问权限（防止跨项目越权）

#### 7.1.3 仓库操作越权校验的多项目语义与删除审批（审计补项 3、5）

> **现状（删除审批，审计补项 3）**：[RepoDTO.reviewerId](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/dto/space/RepoDTO.java) 为**未使用字段**，现有删除链路（`deleteRepoInfo` / `batchDeleteRepoInfo`）**无任何审批**。若产品按 feature-spec §7.4 SOD 规则组 1/3 要求「删除代码平台仓库需项目审批人员审批」，则删除审批是**新能力**，需新增删除申请单 + 审批流转，不能按「沿用现有」实现；**本期删除链路按 §2.4 实现（暂不带审批），审批能力作为独立新需求排期**。

> **现状（越权校验，审计补项 5）**：[CommonServiceImpl.verifyPermissionsByProduct](file:///d:/Develop/Java/openlibing-coderepo-fork/src/main/java/com/openlibing/coderepo/business/service/impl/CommonServiceImpl.java#L139-L151) 在传 `repoId` 时用 `repoInfo.getProjectId()` 反查仓库所属项目（`actualProjectId`）再做菜单/角色校验。旧模型下 repo 单归属、语义正确；新模型下 repo 可多关联，若仍仅用 `repo_info.project_id`（最早关联）判定，会导致**非最早关联项目的合法用户被判无权限**。

**改造规则（越权校验，Phase 1，与 §2.4 删除、§3.1.8 权限类读取点联动）**：
1. `verifyPermissionsByProduct` 传 `repoId` 时改为查 `repo_project_ref where repo_id=? and is_deleted=0` 得到关联项目集合 `refProjectIds`：
   - 请求同时带 `projectId` → 先校验 `projectId ∈ refProjectIds`（请求项目确实关联该 repo，不通过直接 403），越权判定按请求 `projectId` 走；
   - 未带 `projectId` 且 `refProjectIds.size()==1` → 沿用该唯一项目判定（行为与现状一致）；
   - 未带 `projectId` 且 `refProjectIds.size()>1` → 拒绝（要求请求方显式传 `projectId`，避免多项目语义歧义）。
2. **存量 53 个共享仓多行**（`repo_info.project_id` 仍按行）行为与现状一致：按行所属项目判定，7 仓/成员/日志等读取零变化。
3. `delete-repo` / `batch-delete-repo` 增加 `projectId` 入参后，删除前先校验「请求 projectId ∈ ref 关联集合」，再删对应 ref（见 §2.4）。
4. SIG 与全局配置接口的跨项目越权校验（§7.1.2）不变：基于入参 `projectId` 直接校验 `userId` 项目权限。

#### 7.1.4 framework 仓副仓拦截改造（Phase 1 必要例外）

> **背景（代码审计确认）**：framework 对 `repo_info` 为「只读 + 删除级联」，但把 `repo_info.project_id` 当作「仓库唯一归属项目」，贯穿鉴权/授权落库/SCA 归属/审计日志/社区指标/成员同步六条链路。其中**仓库级成员判定与 git 平台成员校验不校验访问者项目**，副仓用户一旦通过该路径会被静默登记为主仓项目成员，污染主仓数据。本需求对该风险做副仓拦截（「下游仓零改动」的唯一必要例外，见 §1.2/§1.5）。

**改造点**（framework 仓，随本需求 Phase 1 同步上线）：
1. `checkRepoUserNamePermission`（[InternalServerImpl.java](file:///d:/Develop/Java/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/InternalServerImpl.java#L138-L189)）：入参加强访问者项目上下文 `accessProjectId`。先查 `repo_project_ref where repo_id=? and is_deleted=0` 得到关联项目集合 `refProjectIds`：
   - `accessProjectId` 非空且 `∉ refProjectIds`（副仓访问）→ **直接返回无权限**，不进入仓库成员/git 成员校验；
   - `accessProjectId` 为空（webhook/机机调用，无项目上下文）→ 保留现有 repoId 级判定（兼容存量 53 个共享仓多行语义）。
2. `saveRepoUserInfo`（L231-277）：仅当访问者为该 repo 关联项目成员时写入 `user_role_info`（`projectId`=主仓）；**副仓访问不写、不补插 `PROJECT_MEMBER`**。
3. `verifyPermissions` / `checkPermissions`（[CommonServiceImpl.java](file:///d:/Develop/Java/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/CommonServiceImpl.java#L145-L169) L154 / [InternalServerImpl.java](file:///d:/Develop/Java/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/InternalServerImpl.java#L524-L657)）：传 `repoId` 时不再无条件用 `repo_info.project_id` 覆盖入参项目，改为按 §7.1.3 同款规则（请求带 projectId → 校验 `projectId ∈ refProjectIds`；不带且多关联 → 拒绝）。
4. `getSpaceId`（[ApplyPermissionServiceImpl.java](file:///d:/Develop/Java/openlibing-framework/src/main/java/com/openlibing/framework/business/service/impl/ApplyPermissionServiceImpl.java#L832-L853) L843）：权限申请/审核归属不再强制取 `repo_info.project_id`，改为请求项目或唯一关联项目。
5. `getBySca` / `SpaceUserLogHandler` / `inferCommunity` 等归属展示类：归属跟随 `repo_project_ref`（副仓不可见；主仓迁移后归属跟随新主仓）。
6. 删除级联（`ProjectServiceImpl.deleteProject` / `ProductServiceImpl.deleteProduct`）：删主仓项目前检查 `repo_project_ref` 关联项目数，>1 时禁止级联删 `repo_info`（见 §1.5「主仓项目删除对副仓」）。

> **Phase 2**：7 仓统一切换为从 `repo_project_ref` 取 `project_id` 时，以上改造点收敛为「按 ref 关联项目集合鉴权」，删除过渡期特判。

### 7.2 SIG 仓（sig-info.yaml 位置）访问安全

#### 7.2.1 token 传递

- 调用平台（gitcode/gitee/github）API 实时读取指定位置 sig-info.yaml 时，`accessToken` 通过 `Authorization: Bearer <token>` header 传递（遵循项目硬约束「第三方 API 调用 accessToken 必须在 header」）
- token 从对应平台公共账号获取（`commonService.getGitcodeToken(projectId, true)` / gitee / github 同理），解密后使用，**不入日志、不入 URL 参数**
- **与 framework [GitCode.getYaml](file:///d:/Develop/Java/openlibing-framework/src/main/java/com/openlibing/framework/common/utils/GitCode.java#L106-L128) 的差异**：framework 现有实现把 `access_token` 拼在 URL query 参数中，本需求在 coderepo 服务内独立实现（`SigInfoClient`）时改为 header 方式，避免 token 出现在网关访问日志中

#### 7.2.2 sig-info.yaml 位置白名单（防任意文件读取）

- 所有 SIG 读取接口**不接受前端任意传仓路径/文件路径**：`sig/repos`、`sig/import` 均以 `platform` 入参，后端先从 `project_repo_global_config.config_json[platform].sigInfoLocation` 取出 `(owner/repo/branch/path)`，**仅允许读取该项目已配置的位置**，杜绝通过入参读取任意仓内文件
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
- `project_repo_global_config.config_json` 整对象（一旦后续扩展纳入令牌类字段将泄露；打印时仅打平台键与位置 owner/repo/path）

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

- `project_repo_global_config` 迁移：将 `project_gitcode_role_mapping.role_mapping`（gitcode 角色映射 JSON 文本）写入 `config_json.gitcode.roleMapping`，批量 upsert，失败可重跑（幂等：按 `(project_id, is_deleted)` 先查后写）
- **Phase 1** repo 迁移脚本在事务内执行，每批 1000 行提交，失败可重跑（幂等：先查 ref 是否存在再 insert）；**只做 1:1 回填，不归并、不删行**，故不触碰 7 个下游仓数据
- **Phase 2** 归并脚本独立执行，需在对应下游仓配合子表 FK 重映射脚本后逐批执行；迁移前全量备份 `repo_info` 表及涉及子表
- 迁移/脚本**在上线后统一执行**，不阻塞服务上线；执行期间新录入重复由代码层事务内查重保证（见 §2.5 清理时机）
- 迁移后校验：Phase 1 校验 `repo_project_ref` 关联数 = 原 `repo_info` 未删除行数；Phase 2 校验归并后 `repo_url` 全局唯一（GROUP BY 0 行）
- 灰度开关 `coderepo.repo-decouple.enabled` 控制新旧逻辑切换，可快速回滚

### 7.9 安全验收清单

- [ ] `accessToken` 不出现在任何后端日志中（grep 验证）
- [ ] `accessToken` 不出现在 URL 参数中（网关访问日志验证）
- [ ] 调平台 API 的请求 header 中含 `Authorization: Bearer`，URL 中无 `access_token`
- [ ] SIG 读取接口传本项目未配置的 `platform` 返回 403
- [ ] `updateGlobalConfig` / `saveSigConfig` 保存位置时 `path` 含 `..` 被拒绝、后缀非 `sig-info.yaml` 被拒绝
- [ ] 不存在的位置（未在 `project_repo_global_config.config_json` 配置）无法通过任意接口读取其文件
- [ ] `update-project-common-account` 入参令牌不出日志、不返回明文；`get-global-config` 返回令牌为掩码 `******`
- [ ] global-config 传非 gitcode/gitee/github 的 `platform` 返回 403
- [ ] YAML 含 `!!java/object` 等危险标签时解析被拒绝
- [ ] 跨项目访问 SIG / 全局配置接口返回 403（无该 project 权限）
- [ ] **Phase 1** 迁移后 `repo_project_ref` 未删除记录数 = `repo_info` 未删除记录数（1:1 回填完整）；53 个共享仓多行保留、其余 6 仓读取零变化（framework 仅做副仓拦截改造 §7.1.4）
- [ ] **Phase 2**（7 仓可控后）归并完成：`SELECT repo_url_normalized, COUNT(*) FROM repo_info WHERE is_deleted=0 GROUP BY repo_url_normalized HAVING COUNT(*)>1` 返回 0 行，且下游子表 FK 已重映射（无悬空 repo_id）
- [ ] 新录入重复仓库被代码层查重拦截：`add-repo` / `sig/import` 并发重复 `repo_url` 不产生第二条 `repo_info`（并发用例）
- [ ] 单元测试覆盖：手动录入冲突（**主仓设置**：默认按当前主仓同步、切换主仓后按所选主仓配置重新同步、提交携带 `mainRepoProjectId` + 选择性删除）、SIG 录入仅未录入仓库 + 不覆盖已有配置、SIG 来源仓库手动编辑、全局配置 config_json 读写（含 roleMapping 迁移）、迁移幂等、sig-info.yaml 解析与位置白名单
- [ ] 历史多项目配置不同场景（53 个共享仓未归并前）：`check-repo-url` 返回 `mainRepoProjectId` + 各关联项目 `projectConfigs`；用户切换主仓后表单按新主仓配置重新同步，主仓归属与下游任务归属正确（前端用例 + 单测）
- [ ] framework 副仓拦截（§7.1.4）：副仓项目用户对主仓仓库的 `checkRepoUserNamePermission` 返回无权限、`saveRepoUserInfo` 不写入主仓成员表（主仓成员集合未被副仓用户污染）
