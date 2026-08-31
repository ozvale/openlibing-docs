# 代码仓管理优化 + SIG 仓一键同步（需求设计文档）

> 配套：[feature-spec.md](./feature-spec.md)（特性规格：版本变化点 / 页面原型 / 权限 / 验收）；[demo.html](./demo.html)（页面原型）。
>
> **核心结论（本文档唯一基线）**：整体思路：尽量规避多项目下统一代码仓配置项不一致。`repo_info` 保持「一项目一行、多行并存」现状模型。**录入时**检测到同 repo_url 已在其他项目录入 → 从上次录入该代码仓的数据中复制配置到表单（可修改），提交时仅提示用户与之前某某项目中的配置不一致，**不做配置覆盖**；用户想修改之前项目配置或删除之前代码仓，按提示自己手动去改。**编辑时**检测到同 repo_url 跨项目配置不一致 → 仅做提示性告警让用户知道与其他项目下的配置不一致，**不自动覆盖**。**开关类配置 OR 聚合**：下游使用该配置时先校验该 repo_url 是否存在重复录入，存在的话只要其中一个开关打开即认为开启，全关闭才关闭（不修改用户在其他项目下的配置）。**SIG 仓一键同步**：全局配置窗口内的「一键同步」按钮，异步执行 + 分布式锁，支持多路径 sig-info.yaml 配置（输入路径后即时调 `validate-sig-path` 校验路径存在性与 sig-info.yaml 文件；同步任务状态在全局配置弹窗内展示）。**默认分支直接从代码托管平台获取、不可修改**。repo_info 层面下游 7 仓（codecheck/cicd/framework/anti-poison/sca/gateway/vulnerability）零改动；例外：全局配置表迁移涉及 framework 删除产品/项目的级联清理改指新表（见 §4.2）。

## 0. 版本修订记录（对齐当前代码实现）

> 本文档为设计基线，以下条目为按**当前实际代码实现**对早期设计做的对齐修订，标为「已实现」或「已修订」。如无后续再变更，以下述描述为准。

| #   | 早期设计                                                                      | 当前实现（对齐）                                                                                                                                                                                                                                                                | 状态                                      |
| --- | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------- |
| 1   | `sigInfoLocations` 为**顶层 URL 数组**，不按平台分键，后端按 URL 域名解析归类 | `config_json.sigInfoLocations` 改为**按平台分键的 Map**（`{"gitcode":[url...],"gitee":[...],"github":[...]}`）；`GlobalConfigUpdateDTO.sigInfoLocations` 为 `Map<String, List<String>>`，前端按平台分组提交，后端保存时校验「路径域名与平台键一致」；读取回显直接按平台分键返回 | 已修订（见 §1.4/§2.2.1/§3.1.4/§4.2/§6.4） |
| 2   | `validate-sig-path` 单 `path` 入参、单结果返回                                | 改为**批量**：入参 `{"paths":[...]}`，返回 `DataResult<List<SigPathValidateVO>>`，每条含 `path/valid/platform/errorCode/message`，单条失败不阻断其余路径（>20 条直接拒绝）                                                                                                      | 已修订（见 §6.5/§6.8）                    |
| 3   | 开关类配置 OR 聚合由 coderepo 提供 `internal/aggregate-switch` 接口           | 因当前**无下游调用方**，配套的 `internal/aggregate-switch` 接口及 `repo_info` 侧 `aggregateSwitchByRepoUrl` 聚合查询**已移除**（遵循「无下游调用方即不保留」原则）；开关 OR 聚合仅作为下游有需求时的设计约定，本期不落地接口                                                    | 已修订（§6.10/§2.4 相应收敛）             |
| 4   | 业务日志未明确 updateGlobalConfig / triggerSigSync 记录                       | 新增 `@LogApi` 独立 operation：`UPDATE_GLOBAL_CONFIG`（修改项目全局配置）、`SYNC_SIG_REPOS`（触发SIG仓一键同步）；`ProjectLogHandler.getOldData`/`encapsulatingLogsDetailVO` 分别记录旧 config_json 与返回的 data（新配置回显/同步任务信息，已去令牌）                          | 已实现                                    |
| 5   | config_json 角色映射键值为 `gitcode`                                          | 保持按平台分键，仅 gitcode 有 roleMapping；与实现一致                                                                                                                                                                                                                           | 一致                                      |

> 其余章节（repo_info 多行模型、一站式 key 结构、SIG 同步异步+分布式锁、默认参数、迁移策略等）与当前实现保持一致，不再单列。

## 1. 方案设计

### 1.1 问题域

> 痛点明细（配置漂移 / 重复录入 / 缺批量录入 / 跨项目不可见）见 [feature-spec.md](./feature-spec.md) §1.2，本文不重复。核心矛盾：同一代码仓被多项目各自录入维护导致配置漂移；且 SCA 等下游按 `(project_id, repo_url)` 反查 `repo_info`，要求每项目必须存在独立行。

### 1.2 核心方案（提示不覆盖 + 开关 OR 聚合 + 多路径 SIG + 异步一键同步）

**模型不拆分，靠提示性告警 + 开关 OR 聚合规避配置不一致**：

1. **repo_info 保持一项目一行**：同一 `repo_url` 可跨项目多行并存。repo_info 层面 7 个下游仓按 `(project_id, repo_url)` 反查每行都命中，**零改动**。每行配置独立维护，用户自行决定是否统一。
2. **录入时复制上次配置 + 提示不覆盖**：录入时检测到同 repo_url 已在其他项目录入 → 从**上次录入该代码仓的数据**中复制配置到表单（可修改）；提交时仅提示用户与之前某某项目中的配置不一致，**不做配置覆盖**（不修改其他项目行）。用户想修改之前项目配置或删除之前代码仓，按提示自己手动去改。
3. **编辑时提示性告警 + 不覆盖**：编辑保存时检测到同 repo_url 跨项目配置不一致 → 仅做提示性告警让用户知道与其他项目下的配置不一致，**不自动覆盖**（不修改其他项目行）。用户确认后仅更新本行。
4. **开关类配置 OR 聚合**：下游使用开关类配置时，先校验该 repo_url 是否存在重复录入（同 repo_url 多行），存在的话只要其中一个开关打开即认为开启，全关闭才关闭。**不修改用户在其他项目下的配置**，仅在读取时聚合判定。
5. **SIG 仓一键同步（异步 + 分布式锁）**：全局配置窗口内的「一键同步」按钮，异步执行 + 分布式锁（防并发重复执行），支持多路径 sig-info.yaml 配置。
6. **查重约束**：`(repo_url, project_id)` 唯一（一项目一行），不做 `repo_url` 全局唯一。

### 1.3 改造边界（重要）

- 本次改造**仅涉及 `repo_info` 表**（新增 `is_participate_operation` 字段）与**新增 `project_repo_global_config` 全局配置表**（每项目一行，承接项目级全局配置；存量角色映射数据从 `project_gitcode_role_mapping` 迁移而来，迁移后旧表废弃，见 §4.2）。
- 代码仓相关配置表还包括 `codecheck` 下的 Mongo 表（如 `sig_rule_set` 规则集表），**本次不改动**——仍允许不同项目对同一代码仓存在不同配置（规则集、告警抑制等项仍按各项目在 codecheck 侧各自配置，不在本期收敛范围内）。
- 不归并存量多行；每行 `project_id` 语义=该行所属项目，与现状一致。

### 1.4 关键决策汇总

| 决策点             | 选择                                                                                                                                                                                                                                                                                                                                 | 理由                                                                                                                                  |
| ------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| repo_info 数据模型 | **保持一项目一行、多行并存**；每行 `project_id`=该行所属项目，语义与现状一致                                                                                                                                                                                                                                                         | SCA 等 7 仓按 `(project_id, repo_url)` 反查每行命中、零改动；多项目扫描共享仓为真实场景                                               |
| 配置同步（录入时） | 录入时同 repo_url 已在其他项目存在 → 从**上次录入该代码仓的数据**复制配置到表单（可修改）；提交时仅提示与之前项目配置不一致，**不做配置覆盖**                                                                                                                                                                                        | 规避重复手填；不强制覆盖用户在各项目下的独立配置；通过提示让用户感知差异                                                              |
| 配置同步（编辑时） | 编辑保存时检测到同 repo_url 跨项目配置不一致 → 仅做提示性告警，**不自动覆盖**；用户确认后仅更新本行                                                                                                                                                                                                                                  | 不强制覆盖；让用户知道配置差异但保留独立维护权                                                                                        |
| 开关配置聚合       | 下游使用开关类配置时，先校验该 repo_url 是否存在重复录入，存在的话对多行开关取 **OR**（有一开启则开启，全关闭才关闭）；**不修改其他项目行**，仅在读取时聚合                                                                                                                                                                          | 保证下游行为判定正确（如门禁、webhook 等只要一个项目开启即生效）；不强制统一配置                                                      |
| 查重               | `(repo_url, project_id)` 唯一（一项目一行）；不做 repo_url 全局唯一                                                                                                                                                                                                                                                                  | 保证同项目不重复录入；不同项目各自建行以支撑各自扫描                                                                                  |
| 组 key             | 直接用 `repo_url`（录入已保证协议/https/平台/`.git` 结尾格式统一，直接使用）；repo_url 加普通索引用于组查询                                                                                                                                                                                                                          | 用于「同 repo_url 组」判定（录入复制上次配置、编辑冲突检测、开关聚合查询）                                                            |
| 跨项目录入         | 仓库已在其他项目存在 → 当前项目**新建一行**并复制上次录入配置（可修改）；不删除其他项目行；提交时提示配置不一致                                                                                                                                                                                                                      | SCA 兼容 + 避免重复手填；不强制覆盖                                                                                                   |
| 下游仓改造         | **repo_info 层面 7 仓零改动**；**例外：全局配置表迁移（§4.2）影响 framework**——其删除产品/项目时原级联清理 `project_gitcode_role_mapping` 的逻辑需改指新表                                                                                                                                                                           | repo_info 多行模型下每项目都有行，权限/归属按行内 project_id 语义与现状一致；仅全局配置表迁移波及 framework 的删除级联清理（见 §4.2） |
| 全局配置           | **新建 `project_repo_global_config` 表**（每项目一行），存 `config_json`：存量 role_mapping 从 `project_gitcode_role_mapping` 迁入 `config_json[platform].roleMapping`，迁移完成后旧表废弃；角色映射条目用 `platformRole` 区分平台，可扩展；SIG 路径列表存 `config_json.sigInfoLocations`（**按平台分键的 Map**，后端保存时校验每条路径域名与平台键一致） | 集中管理 sig-info 路径 / 角色映射（公共账号仍存现有表，经 global-config 接口统一读写），见 §4.2                                       |
| SIG 配置读取       | 实时调对应平台读取指定路径下 sig-info.yaml 并解析，不落库不缓存                                                                                                                                                                                                                                                                      | 保证读到最新配置，简化链路                                                                                                            |
| SIG 路径配置       | 用户可自由设置**多个** sig-info.yaml 路径；配置时不区分平台，后端根据 URL 域名统一区分平台；路径指向目录（如 `.../sigs/openLiBing-private`），在该目录下找 sig-info.yaml 文件；**输入路径后即时调 `validate-sig-path` 校验路径存在性与 sig-info.yaml 文件**（见 §6.5）                                                               | 支持多 SIG 组；后端统一管理平台归属；即时校验让用户当场发现路径错误                                                                   |
| SIG 仓一键同步     | 全局配置窗口内「一键同步」按钮；**异步执行 + 分布式锁**（防并发重复执行）；**任务状态在全局配置弹窗内展示**；默认参数自动填充（别名/责任人/用途/开源类型/默认分支/公共账号令牌/各开关，见 §2.2.4）                                                                                                                                   | 异步 + 锁避免执行时间长与并发问题                                                                                                     |
| 默认分支           | **直接从代码托管平台获取，不可修改**（表单只读展示，编辑时也不可改）                                                                                                                                                                                                                                                                 | 默认分支以平台为准，避免手工填错                                                                                                      |
| 历史迁移           | **Phase 1**：清洗同项目重复行（按 repo_url）+ 加 `(repo_url, project_id)` 唯一索引                                                                                                                                                                                                                                                   | 本期不归并、不删行，7 仓零影响                                                                                                        |
| 改造边界           | 仅 repo_info 改造（新增 `is_participate_operation`）+ 新增 project_repo_global_config（从 project_gitcode_role_mapping 迁移数据后旧表废弃）；codecheck Mongo（sig_rule_set）等不改                                                                                                                                                   | 规则集等按各项目在 codecheck 侧各自配置，不在本期收敛范围                                                                             |
| YAML 解析安全      | SnakeYAML `SafeConstructor`                                                                                                                                                                                                                                                                                                          | 防 YAML 反序列化攻击                                                                                                                  |
| accessToken 传递   | 调平台 API 时 `Authorization: Bearer <token>` header                                                                                                                                                                                                                                                                                 | 遵循项目硬约束「第三方 API 调用 accessToken 必须在 header」                                                                           |

## 2. 实现逻辑设计

### 2.1 手动录入逻辑（复制上次配置 + 提示不覆盖）

> 输入 `repo_url` blur 即调检测接口，命中其他项目已录入（同组多行）时，从**上次录入该代码仓的数据**中复制配置到表单（可修改）；提交时仅提示用户与之前某某项目中的配置不一致，**不做配置覆盖**（不修改其他项目行）。用户想修改之前项目配置或删除之前代码仓，按提示自己手动去改。

```
addRepoInfo(userId, userName, projectId, RepoDTO):
  1. 组 key = repo_url（原样，录入已保证格式统一）
  2. 查该组现有行（repo_info where repo_url=? and is_deleted=0）
  3. 未命中（全局首次录入）：
     - insert repo_info（配置取 RepoDTO）
     - 同步平台元数据 + 配置 webhook（沿用现有 syncRepoInfo / autoSetWebHook）
  4. 命中（该 repo_url 已在其他项目存在）：
     - 前端 blur 已调 checkRepoUrl：返回 associatedProjects 与 lastConfig（上次录入该代码仓的配置副本）
     - 前端直接使用 lastConfig 同步进表单（可修改）
     - 当前项目已存在本行 → update 本行配置（以表单为准）
     - 当前项目无本行 → insert 本行（配置=用户修改后的表单值）
  5. 提交前前端再次调 checkRepoUrl（传 formConfig=用户当前表单配置；blur 返回 repoId 非 null 时
     一并传 repoId 排除本行），后端比对表单配置与同组其他行配置，返回 configDiff：
     - configDiff 为空 → 正常提交（add-repo 纯写入，不做比对）
     - configDiff 非空 → 弹窗提示「与项目A、项目B 中的配置不一致，是否继续保存？
       （仅影响当前项目行，不修改其他项目配置）」
     - 用户确认 → 仅 insert/update 本行，不触碰其他项目行
> **过渡期存量 53 个共享仓**（同 repo_url 多行、各项目配置可能不同）：检测返回各关联项目及其配置；
录入新项目行时默认复制上次录入配置（可修改），避免重复手填；配置不一致仅提示，不强制统一。
```

### 2.2 SIG 仓一键同步（异步 + 多路径支持）

> 全局配置窗口内的「一键同步」按钮，**异步执行 + 分布式锁**；支持多路径 sig-info.yaml 配置；默认参数自动填充（含实时调平台获取创建人账号名和默认分支）。

#### 2.2.1 sig-info.yaml 路径配置（全局配置弹窗，支持多路径）

- 用户在「全局配置」弹窗的「代码仓录入配置」区域维护**多个** sig-info.yaml **路径**，存 `project_repo_global_config.config_json.sigInfoLocations`（**按平台分键的 Map**：key 为 gitcode/gitee/github，value 为路径 URL 列表）。
- 路径指向**目录**（如 `https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private`），系统在该目录下找 sig-info.yaml 文件。
- **配置时按平台分组提交**，后端保存时校验每条 URL 域名与其所属平台键一致（gitcode.com → gitcode，gitee.com → gitee，github.com → github）。
- **输入路径后即时批量校验**：用户输入/修改路径后（blur / 防抖），前端调 `POST /project-config/validate-sig-path`（见 §6.5）**批量**校验这些路径是否存在、其下是否存在 sig-info.yaml 文件；校验结果（可用 / 路径不存在 / 文件不存在）就地展示，**不阻断保存**。

#### 2.2.2 sig-info.yaml 文件格式（固定）

```yaml
# sig-info.yaml —— SIG 组代码仓清单（固定格式）
repositories:
  - repo: # 可存在多个不同的 repo 分组
      - openlibing/community
      - openlibing/openlibing-web
  - repo:
      - openlibing/anti-poison
      - openlibing/coderepo
```

解析规则：顶层 `repositories` 必填（列表）；列表项 `- repo:` 值为该组代码仓清单（`owner/repo` 字符串列表）。**不含任何录入参数**（录入参数全部用默认值或用户编辑）。每个 `owner/repo` 按路径所属平台组装完整 repoUrl。重复项跨分组去重、跨路径去重。

#### 2.2.3 一键同步异步任务（分布式锁 + 默认参数填充）

```
syncSigReposAsync(userId, userName, projectId):
  1. 分布式锁：lockKey = "sig_sync:" + projectId
     try (DistributedLock lock = distributedLock.lock(lockKey, 300000)):  // 5分钟锁
       if (lock == null):
         log.warn("SIG同步任务获取锁失败，已有任务在执行，projectId={}", projectId)
         return  // 不重复执行
       2. 从 config_json.sigInfoLocations 取所有路径
       3. 按平台分组拉取 sig-info.yaml 并合并去重：
          for loc in sigInfoLocations:
            platform = parsePlatformFromUrl(loc)  // 从 URL 域名判断平台
            content = sigInfoClient.getFileContent(loc, platform)  // 读 {path}/sig-info.yaml
            repos = parseRepositories(content)  // 解析 owner/repo 列表
            allRepos.addAll(repos)
          allRepos = dedup(allRepos)  // 跨路径去重
       4. 过滤：仅保留 (repo_url, projectId) 尚无行的仓库（已录入当前项目的不同步，避免覆盖）
       5. 对每个仓库实时调平台获取详情（创建人账号名 + 默认分支）+ 按默认规则填充参数（见 §2.2.4）
       6. 事务内批量录入：
          for repo in allRepos:
            a. 查该组现有行（repo_url）
            b. 未命中（全局首次）→ insert 本行（配置取默认参数 + 平台元数据）
            c. 命中（其他项目已存在）→ insert 本行（配置=复制上次录入配置副本，避免重复手填）
       7. 异步同步平台元数据 + 配置 webhook（不阻塞录入）
       8. 返回结果（异步，通过任务状态查询或消息通知）
  // 锁在 try-with-resources 结束时自动释放
```

#### 2.2.4 默认参数（自动填充，用户可在录入后手动编辑）

| 字段                                                        | 默认值                                                                  | 说明                                       |
| ----------------------------------------------------------- | ----------------------------------------------------------------------- | ------------------------------------------ |
| 代码仓别名                                                  | 先用 repo 名；当前项目已存在同名 → `repo名-平台名`；仍冲突 → 加数字递增 | 当前项目内查重                             |
| 默认分支                                                    | **实时调代码托管平台获取**（和已有逻辑一样从平台获取默认分支）          | **不可修改**（直接取自平台，表单只读展示） |
| 仓库责任人                                                  | **实时调代码托管平台获取该代码仓的创建人账号名**                        | 可编辑                                     |
| 用途                                                        | 自研源码                                                                | 可编辑                                     |
| 开源类型                                                    | 主导开源                                                                | 可编辑                                     |
| 是否参与运营                                                | 是                                                                      | 可编辑                                     |
| 接管 PR / 自动触发门禁 / 接口扫描 / 代码风格修复 / 告警抑制 | 否                                                                      | 可编辑                                     |
| 公共账号令牌                                                | **项目级公共账号令牌**（从项目公共账号表获取）                          | 沿用项目公共账号                           |
| 仓库规则集配置                                              | 不配置                                                                  | —                                          |

> **一键同步后允许手动编辑**：SIG 来源仓库同样允许手动编辑；编辑时若检测到跨项目配置不一致，同 §2.3 提示性告警，不覆盖。

> **异步任务状态查询**：一键同步触发后立即返回任务 ID；**任务状态直接在全局配置弹窗内展示**（代码仓录入配置区域下方），前端轮询任务状态（RUNNING / SUCCESS / FAILED / PARTIAL），任务完成后展示 imported / failed 计数与失败原因。

### 2.3 编辑逻辑（提示性告警 + 不覆盖）

> **编辑本行保存时，若该 repo_url 组内存在跨项目行（同 repo_url 多行）且配置不一致 → 仅做提示性告警，让用户知道与其他项目下的配置不一致；用户确认后仅更新本行，不覆盖其他项目行**。用户可选择继续保存（仅本行生效）或取消去手动统一。**不自动覆盖其他项目行配置**——保留用户在各项目下的独立维护权，通过提示让用户感知差异。

```
updateRepoInfo(userId, userName, projectId, repoId, RepoDTO):
  1. 校验请求 projectId == 本行 project_id（越权沿用现有 verifyPermissionsByProduct）
  2. update 本行配置（写接口纯写入，不做跨项目比对——比对由前端保存前调 checkRepoUrl 完成，见下）
  3. 同步平台元数据 + webhook（沿用现有逻辑）
```

**前端保存前比对流程**（编辑对话框打开时回显本行当前配置，不预填其他项目数据）：

```
编辑保存按钮点击:
  1. 前端调 checkRepoUrl（传 repoId=本行 + formConfig=用户当前表单配置）
  2. 后端查同 repo_url 组内其他行（is_deleted=0 且 repo_id != 本行）并比对，返回 configDiff：
     - configDiff 为空（无其他行或配置一致）→ 直接调 update-repo 保存本行
     - configDiff 非空 → 弹窗提示「与项目A、项目B 中的配置不一致，是否继续保存？
       （仅影响当前项目行，不修改其他项目配置）」
     - 用户确认 → 调 update-repo 仅更新本行，不触碰其他项目行
     - 用户取消 → 不保存
```

> **提示性告警字段范围**：行内全部**可编辑**配置字段（别名、仓库令牌、责任人、开源类型、各开关等）；**默认分支不参与比对**（直接从代码托管平台获取、不可修改，见 §2.2.4）；不含 `repo_id` / `project_id` / `create_at` / `create_user` 等行级元数据字段。不涉及 codecheck 侧规则集（`sig_rule_set` 等）与其他子表。

### 2.4 开关配置 OR 聚合规则（下游读取）

> 下游使用开关类配置时，**先校验该 repo_url 是否存在重复录入**（同 repo_url 多行），存在的话对多行开关取 **OR**（有一开启则开启，全关闭才关闭）。**不修改用户在其他项目下的配置**，仅在读取时聚合判定。

**开关类字段清单**（`repo_info` 表）：

- `assume_pr`（接管 PR 管理）
- `is_auto_trigger_gate`（自动触发门禁流水线）
- `is_auto_interface_scan`（自动触发接口扫描）
- `is_auto_format`（代码风格自动修复）
- `is_suppression_enabled`（告警抑制自动检视）
- `is_participate_operation`（是否参与运营）

**聚合规则**：

```sql
-- 下游查询某 repo_url 的开关配置时，对同组多行取 OR（MAX 等价于 OR for TINYINT(0/1)）
SELECT
  repo_url,
  MAX(assume_pr)              AS assume_pr,
  MAX(is_auto_trigger_gate)   AS is_auto_trigger_gate,
  MAX(is_auto_interface_scan) AS is_auto_interface_scan,
  MAX(is_auto_format)         AS is_auto_format,
  MAX(is_suppression_enabled) AS is_suppression_enabled,
  MAX(is_participate_operation) AS is_participate_operation
FROM repo_info
WHERE repo_url = ? AND is_deleted = 0
GROUP BY repo_url;
```

> **实现方式**：下游仓读取开关配置时，改为按 `repo_url` 聚合查询（而非按 `project_id` 单行查询）。若下游仓当前按 `(project_id, repo_url)` 反查单行，需在 SQL 层改为 `SELECT MAX(...) FROM repo_info WHERE repo_url = ? GROUP BY repo_url`。**本期下游 7 仓零改动**——聚合逻辑由 coderepo 侧在提供数据时统一处理（如 internal/query-repo 接口返回聚合后的开关值，或下游仓调用 coderepo 的聚合查询接口）。

> **非开关类配置**（如责任人、默认分支、别名等）不聚合——各项目行独立维护，下游按 `(project_id, repo_url)` 反查单行获取该项目的配置。开关类配置因影响平台行为（门禁、webhook 等）才聚合。

### 2.5 历史存量迁移策略（Phase 1 清洗 + 唯一索引）

> **背景**：存量体检发现 53 个共享仓（同 repo_url 多项目多行、配置可能不同）。归并需重映射各仓子表 FK（sca `tbl_scan.repo_id` 等），而这些仓不归属本项目、不可控 → **归并推迟到 Phase 2**。

**Phase 1（本期上线时执行，幂等可重跑，不阻塞上线）**：

```
migrateRepoInfoPhase1():
  1. 清洗同项目重复行：对 (repo_url, project_id) 多行的脏数据，保留最早 create_at 行，
     其余行迁移子表 FK 后删除（或提示人工处理，数量应极少）
  2. ALTER TABLE repo_info ADD UNIQUE INDEX uk_repo_project (repo_url, project_id)
  3. 校验：无同项目重复行
```

- **效果**：7 个下游仓零影响（每行 project_id 语义不变）；新录入一项目一行由唯一索引兜底。
- **Phase 1 明确不做**：不归并 53 个共享仓多行、不删存量行。

**Phase 2（远期，7 仓逐个可控后）**：

- 届时再评估存量共享仓的归并方案；本期不实施。

### 2.6 前端实现逻辑

#### 2.6.1 全局配置弹窗（新增，`Repos/index.vue`）

- 工具栏「导出仓库」右侧新增「全局配置」按钮；原「gitcode 角色映射」「项目公共账号」按钮并入。
- 三页签 GitCode / Gitee / GitHub，各页签（**接口走 `/project-config`，由现有 `ProjectConfigController` 提供**）：
  - **项目公共账号**：直接编辑登录名 + 令牌（留空不修改），**随 `/project-config/global-config` 统一提交**（实现层仍写入现有项目公共账号表 `project_common_account_info`，不进 config_json，见 §4.2 / §6.4）
  - **角色映射**：仅 GitCode 页签（gitcode 角色 ↔ openLiBing 角色），存 `config_json.gitcode.roleMapping`，**统一调 `/project-config/global-config` 读写（现有 `/project-config/update-gitcode-role-mapping` 废弃，前端改调新接口，角色映射唯一写入口）**
- **代码仓录入配置（SIG sig-info.yaml 路径列表）**：不限定在页签内，作为独立区域展示；用户可自由添加多个路径（不区分平台），输入路径后（blur / 防抖）调 `/project-config/validate-sig-path` 即时校验该路径是否存在、其下是否存在 sig-info.yaml（结果就地展示，不阻断保存）；路径列表随 `/project-config/global-config` 统一提交（保存时不再重复校验）
- **一键同步按钮**：放在代码仓录入配置区域内，触发异步同步任务（带分布式锁）；**同步任务状态直接在本弹窗内展示**（代码仓录入配置区域下方的任务状态卡片：RUNNING / SUCCESS / FAILED / PARTIAL + imported / failed 计数与失败原因）

#### 2.6.2 录入对话框改造

- 手动录入：`repoUrl` blur 调 `checkRepoUrl`（防抖 300ms，只传基础参数）→ 命中时，表单**直接使用**上次录入该代码仓的数据（可修改）；提交前传 `formConfig`（blur 返回 repoId 非 null 时一并传 repoId）再调 `checkRepoUrl` 比对，`configDiff` 非空 → 弹窗提示（不覆盖其他项目行），用户确认后调 `add-repo`
- **默认分支只读展示**：沿用现有录入流程的仓库信息获取逻辑（从代码托管平台实时获取），不经 `checkRepoUrl` 返回

#### 2.6.3 编辑对话框

- 编辑对话框：不做 SIG 来源拦截；打开时回显本行当前配置（**不预填其他项目数据**）；保存前传 `repoId` + `formConfig` 调 `checkRepoUrl` 比对，**存在跨项目行且配置不一致 → 弹窗提示性告警（不覆盖其他项目行），用户确认后调 `update-repo` 仅更新本行**；默认分支只读展示（从代码托管平台获取，不可修改）

### 2.7 交互流程示例图

```
【手动录入（命中多行，配置不一致）】
┌────────────────────────────────────────────────┐
│ 录入代码仓                              ✕       │
│ 仓库链接: https://gitcode.com/org/repo.git     │
│ ℹ 该仓库已在 项目A、项目B 录入，表单已按上次    │
│   录入配置自动同步，可直接修改后提交。          │
├────────────────────────────────────────────────┤
│ 托管平台: gitcode  别名: repo  责任人: sig-owner │
│ ...（其余表单字段，可修改）                      │
└────────────────────────────────────────────────┘
        │ 点击「确定」
        ▼
┌────────────────────────────────────────────────┐
│ ⚠ 配置不一致提示                                │
│ 该代码仓已在 项目A、项目B 录入，当前表单配置与  │
│ 上述项目中的配置不一致。是否继续保存？           │
│ （仅影响当前项目行，不修改其他项目配置）        │
│                          [取消]  [确认保存]     │
└────────────────────────────────────────────────┘

【全局配置 - 代码仓录入配置 + 路径校验 + 一键同步任务状态】
┌────────────────────────────────────────────────┐
│ 全局配置（对项目下所有代码仓生效）        ✕     │
│ [GitCode] [Gitee] [GitHub]                     │
├────────────────────────────────────────────────┤
│ 项目公共账号（GitCode）                         │
│ 登录名: openlibing-gitcode  令牌: ••••••        │
├────────────────────────────────────────────────┤
│ 代码仓录入配置（SIG sig-info.yaml 路径列表）    │
│ ┌──────────────────────────────────────┬─────┐ │
│ │ https://gitcode.com/.../sigs/sig1    │ ●可 │ │
│ │ https://gitcode.com/.../sigs/sig2    │ ●可 │ │
│ └──────────────────────────────────────┴─────┘ │
│   ↑ 输入路径 blur 即调 validate-sig-path 校验   │
│ [+ 添加路径]  [↻ 一键同步] ← 异步+分布式锁     │
│ ┌────────────────────────────────────────────┐ │
│ │ 最近一次同步任务 [RUNNING] 已同步:36 失败:2 │ │
│ └────────────────────────────────────────────┘ │
├────────────────────────────────────────────────┤
│ 角色映射（GitCode）                             │
│ ...                                             │
├────────────────────────────────────────────────┤
│                        [取消]  [保存]          │
└────────────────────────────────────────────────┘
```

## 3. 类设计

### 3.1 后端类设计（openlibing-coderepo-fork）

#### 3.1.1 Entity 改造

- `RepoInfoEntity` 新增字段：

| 字段                     | 说明                                                               |
| ------------------------ | ------------------------------------------------------------------ |
| `isParticipateOperation` | 是否参与运营（默认是，**新增**——现实体/表无此字段，见 §4.1 ALTER） |

- **新增 `ProjectRepoGlobalConfigEntity`**（表 `project_repo_global_config`，每项目一行）：`configJson` 字段作为项目级全局配置载体（config_json 中 `sigInfoLocations` 与角色映射均按平台分键）。存量 `GitCodeRoleMappingEntity`（表 `project_gitcode_role_mapping`）的 role_mapping 数据迁移至新表 `config_json.gitcode.roleMapping` 后，旧表废弃（不物理删除）。

#### 3.1.2 Mapper 改造

- `RepoInfoMapper.xml`：
  - 新增 `selectByRepoUrl`：按 repo_url 查同组所有行（供录入复制上次配置 / 编辑冲突检测）
  - 现有按 `project_id` / `repo_id` 的查询**不变**（多行模型语义与现状一致）

#### 3.1.3 Service

- `RepoService` / `RepoServiceImpl`：
  - `addRepoInfo`：新增「命中多行」分支（复制上次录入配置 + 提示不覆盖，见 §2.1）
  - `updateRepoInfo`：存在跨项目行且配置不一致时提示性告警，不覆盖（§2.3）；DTO 新增 `isParticipateOperation` 参数（见 §6.2）
  - 新增 `checkRepoUrl`（返回上次录入配置副本 + 配置差异，供录入复制与编辑冲突检测复用）
- 全局配置与一键同步能力**统一收敛到现有 `ProjectConfigService`**，底层表 `project_repo_global_config`（新增，数据从 `project_gitcode_role_mapping` 迁移）：`getGlobalConfig` / `updateGlobalConfig`（**全局配置唯一写入口**：config_json 读写，含 sigInfoLocations + roleMapping；**项目公共账号更新也并入该方法**——实现层仍写现有项目公共账号表 `project_common_account_info`，不进 config_json，见 §6.4）/ `validateSigPath`（批量校验 sig-info 路径存在性与 sig-info.yaml 文件，见 §6.5）/ `syncSigReposAsync`（异步一键同步，带分布式锁，见 §2.2.3）。全局配置接口由现有 `ProjectConfigController`（`/project-config`）暴露。

#### 3.1.4 工具类 / DTO

- 新增 `SigInfoClient`（实时读 sig-info.yaml，支持多路径，参考 framework GitCode.getYaml 但 accessToken 走 header）、`SigDefaultParamBuilder`（默认参数填充：实时调平台获取创建人账号名 + 默认分支 + 别名冲突处理）。
- 新增 DTO/VO：`RepoUrlCheckQueryDTO`（projectId、repoUrl + 可选 repoId/formConfig，见 §6.3）/ `RepoUrlCheckVO`（exists、repoId、lastConfig、associatedProjects、configDiff）、`GlobalConfigVO`（sigInfoLocations 按平台分键 + gitcode roleMapping + 公共账号掩码）、`GlobalConfigUpdateDTO`（sigInfoLocations **按平台分键 Map** + roleMapping + **项目公共账号登录名/令牌**，账号实现层写 `project_common_account_info`）、`SigPathValidateDTO/VO`（路径批量校验入参/结果，见 §6.5）、`SyncSigReposTaskVO`（任务 ID + 状态 + imported/failed 计数）。

#### 3.1.5 现有业务读取点（`repoInfo.getProjectId()` 多项目语义）

> **结论：全部无需改造。** 多行模型下每行 `project_id`=该行所属项目，`repoInfo.getProjectId()` 语义与现状完全一致（平台 token、越权校验、列表查询、删除/编辑、成员/角色、上报/日志、事件归属）。本期**不做**任何读取点改造。
> 定时任务（syncRepoInfoHandler / codeMetricsObsImportHandler / refreshWebhookHandler / FrameworkJobs.refreshProjectIdCache）均按 `project_id` 逐项目处理，语义不变，零改动。
> **开关聚合读取点（下游约定）**：开关 OR 聚合仅作为下游读取约定（本期无下游调用方，聚合接口与 `aggregateSwitchByRepoUrl`/`aggregateSwitchConfig` 均不落地，见 §0 修订记录 3）；下游需要使用开关聚合时，由 coderepo 在提供数据时按 `repo_url` 统一聚合（MAX）返回。

### 3.2 前端类设计（openlibing-web）

- `Repos/index.vue`：录入对话框手动录入 blur 检测（命中时复制上次配置、提交时提示不一致不覆盖）；工具栏新增「全局配置」按钮与三页签弹窗（含代码仓录入配置多路径 + 路径即时校验 + 一键同步按钮 + 同步任务状态展示）；**编辑对话框保存时若存在跨项目行且配置不一致 → 弹窗提示性告警（不覆盖其他项目行），用户确认后仅更新本行**。
- api/url 层新增：`checkRepoUrl`（录入/编辑冲突检测）/ `getGlobalConfig` / `updateGlobalConfig`（含项目公共账号提交）/ `validateSigPath`（sig-info 路径即时校验）/ `syncSigRepos`（异步一键同步，返回任务 ID）/ `getSyncTaskStatus`（轮询任务状态，在全局配置弹窗内展示）（全局配置相关走 `/project-config`，见 §6.3-6.7）。

## 4. 数据模型设计

### 4.1 现有表 `repo_info` 改造

```sql
-- 1. 新增字段
ALTER TABLE repo_info ADD COLUMN is_participate_operation TINYINT(1) NOT NULL DEFAULT 1
  COMMENT '是否参与运营（默认是）' AFTER default_branch_name;

-- 2. 确保 repo_url 有普通索引用于组查询（若原表无则新增）：
-- ALTER TABLE repo_info ADD INDEX idx_repo_url (repo_url);
-- 3. 清洗 + 唯一索引（见 §2.5 Phase 1 迁移）
-- ALTER TABLE repo_info ADD UNIQUE INDEX uk_repo_project (repo_url, project_id);
```

- 每行 `project_id`=该行所属项目，语义与现状一致，7 个下游仓继续按现有方式读取。
- **不做 `repo_url` 全局唯一**：跨项目多行并存，`uk_repo_project (repo_url, project_id)` 保证一项目一行。

### 4.2 新建全局配置表 `project_repo_global_config`（数据从 `project_gitcode_role_mapping` 迁移，迁移后旧表废弃）

> **核心变化**：**新建**项目级全局配置表 `project_repo_global_config`（每项目一行），统一承载 sig-info 路径 / 角色映射等全局配置（**项目公共账号仍存现有 `project_common_account_info` 表，不进 config_json、不迁移，仅经 global-config 接口统一读写**）；存量 `project_gitcode_role_mapping` 中的 role_mapping 数据**迁移**到新表 `config_json.gitcode.roleMapping`，迁移完成后旧表废弃（不物理删除，角色映射读写改指新表）。
>
> **下游影响（framework 例外）**：经工作区全量核对，除 coderepo（+fork）外，**openlibing-framework** 也引用旧表——`ProductServiceImpl` / `ProjectServiceImpl` 删除产品/项目时通过 `GitcodeRoleMappingMapper.deleteMappingByProjectId` 级联清理 `project_gitcode_role_mapping`。旧表废弃后该级联清理需**改指新表对应行**（删除产品/项目时同步清理 `project_repo_global_config` 该 project_id 行），否则删项目后新表残留脏数据；framework 的 `selectMappingByProjectId` 为未使用注入，随迁移一并清理。其余仓（codecheck/cicd/web/common/sca/anti-poison/gateway/vulnerability 等）均未引用该表。

```sql
-- 1. 新建项目级全局配置表（每项目一行，承接 sig-info 路径 / 角色映射等全局配置；
--    项目公共账号仍存 project_common_account_info，不入本表）
CREATE TABLE project_repo_global_config (
    id             BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    project_id     BIGINT UNSIGNED NOT NULL COMMENT '项目ID',
    config_json    JSON            NULL COMMENT '项目级全局配置(JSON)：sigInfoLocations按平台分键、各平台角色映射(按平台分键)，可扩展',
    create_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    create_user    VARCHAR(64)     NULL COMMENT '创建人',
    update_user    VARCHAR(64)     NULL COMMENT '更新人',
    is_deleted     TINYINT(1)      NOT NULL DEFAULT 0 COMMENT '逻辑删除(0-否,1-是)',
    PRIMARY KEY (id),
    UNIQUE KEY uk_project (project_id, is_deleted)
) COMMENT='项目级全局配置表（从 project_gitcode_role_mapping 迁移数据而来）';

-- 2. 建表与数据迁移由 Liquibase 同一 changeset 定义（createTable + 存量迁移 SQL，幂等 precondition），
--    随实例启动原子执行：存量 role_mapping 迁入 config_json.gitcode.roleMapping（每项目一行 upsert）
--    具体 role_mapping → config_json.gitcode.roleMapping 的字段映射见迁移脚本；
--    迁移完成后旧表 project_gitcode_role_mapping 废弃（不物理删除）
```

**config_json 结构（约定，sigInfoLocations 按平台分键，角色映射亦按平台分键）**：

```jsonc
{
  // SIG sig-info.yaml 路径列表（按平台分键：key 为 gitcode/gitee/github，value 为路径URL列表；
  //   保存时校验每条 URL 域名与平台键一致；兼容旧版顶层数组存储，读取时自动归组）
  "sigInfoLocations": {
    "gitcode": [
      "https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private",
      "https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/sig2",
    ],
    "gitee": [],
    "github": [],
  },
  // 角色映射按平台分键（仅 gitcode 有）
  "gitcode": {
    "roleMapping": [
      { "platformRole": "owner", "openlibingRole": "project_admin" },
      { "platformRole": "master", "openlibingRole": "repo_admin" },
      { "platformRole": "developer", "openlibingRole": "developer" },
    ],
  },
  "gitee": {},
  "github": {},
}
```

> 项目公共账号仍存 `project_common_account_info`（登录名 + 加密令牌），不迁移、不进 config_json；全局配置弹窗内直接编辑并**随 `global-config` 接口统一提交**（实现层写回该表）。

### 4.3 sig-info.yaml 配置文件结构（固定格式）

见 §2.2.2。文件位于用户配置的路径下（目录下 `sig-info.yaml`），仅声明 SIG 组代码仓清单，不含录入参数。

### 4.4 ER 关系

```
project (1) ──── (N) repo_info (每行=该项目下的一条代码仓；同 repo_url 跨项目多行)
                     ├─ project_id       = 该行所属项目（7 仓反查键）
                     ├─ repo_url         = 组 key（同 repo_url 为一组，开关聚合按此分组）
                     └─ is_participate_operation

project (1) ──── (1) project_repo_global_config ──实时读取──▶ SIG 仓 sig-info.yaml（多路径）
                      config_json.sigInfoLocations（按平台分键）  │ 解析 repositories
                      + config_json[平台].roleMapping            ▼
                                                          repo_info（一键同步批量录入）
```

### 4.5 数据量预估

| 维度         | 估算                                                                       |
| ------------ | -------------------------------------------------------------------------- |
| repo_info    | 现状规模不变（< 10 万行），一项目一行；同 repo_url 多行并存（53 个共享仓） |
| 单项目仓库数 | 平均 50-200，列表按 project_id 走索引，毫秒级                              |
| SIG 路径配置 | 每项目多个 sig-info.yaml 路径（存 config_json），内容不落库                |

## 5. 性能设计

### 5.1 数据库性能

| 表                           | 索引                                     | 服务场景                                             |
| ---------------------------- | ---------------------------------------- | ---------------------------------------------------- |
| `repo_info`                  | `uk_repo_project (repo_url, project_id)` | 一项目一行唯一；同组查询走前缀                       |
|                              | `idx_project_id (project_id)`            | 列表页按项目查询（现有，保留）                       |
|                              | `idx_repo_url (repo_url)`                | 组查询（录入复制上次配置 / 编辑冲突检测 / 开关聚合） |
| `project_repo_global_config` | `uk_project (project_id, is_deleted)`    | 每项目一行全局配置（从旧表迁移，旧表废弃）           |

- 开关聚合查询：按 `repo_url` 一次 SELECT + GROUP BY，组内行数少（1~N），单次 < 50ms。
- 一键同步：单次最多数百个仓库（多路径合并去重后），异步执行 + 分布式锁，不阻塞前端。

### 5.2 配置读取设计（实时调对应平台）

- sig-info.yaml 由各接口**实时调对应平台读取并解析**，不缓存、不落库（去除 webhook / 定时兜底）。
- 位置元数据读 `config_json`（毫秒级）；平台调用设超时（如 3s），单平台失败不影响其他平台；全部失败返回明确错误提示稍后重试。
- 一键同步时实时调平台获取仓库详情（创建人账号名 + 默认分支），设超时（如 5s/仓库），失败仓库记入 failed 列表。

### 5.3 并发控制

- **录入并发**：同一项目同 repo_url 并发首次录入 → `uk_repo_project` 唯一索引兜底（INSERT 冲突即报错/幂等）。不同项目同 repo_url 各自建行。
- **编辑并发**：编辑本行仅更新本行（不覆盖其他项目行），无跨行 UPDATE；同项目同 repo_url 并发编辑由乐观锁（`update_at`）防并发覆盖。
- **一键同步并发**：**分布式锁**（`sig_sync:{projectId}`，锁 5 分钟），防同一项目并发触发多次同步；锁内串行化执行，执行完释放锁；锁超时自动释放防死锁。
- **全局配置并发**：`global-config POST` 对 `projectId` 加分布式锁（config_json 为整存整取的读-改-写模式，锁内串行化防并发丢更新——两个用户并发更新不同区域时后写覆盖先写）；读取不加锁。

### 5.4 前端性能

| 维度              | 策略                                                                                                                          |
| ----------------- | ----------------------------------------------------------------------------------------------------------------------------- |
| 冲突预查          | `repoUrl` blur 防抖 300ms 调 `checkRepoUrl`                                                                                   |
| sig-info 路径校验 | 路径输入框 blur 防抖 300ms 调 `validateSigPath`，结果就地展示                                                                 |
| 一键同步          | 异步触发，返回任务 ID，前端轮询任务状态（如每 3s 轮询，超时 10 分钟，**在全局配置弹窗内展示**）；loading + 禁用按钮防重复提交 |

### 5.5 性能验收指标

| 指标                                | 目标                                |
| ----------------------------------- | ----------------------------------- |
| `checkRepoUrl` 响应                 | < 100ms                             |
| `validateSigPath` 响应              | < 2s（含调平台读目录校验，超时 3s） |
| `queryRepoInfo` 响应                | < 100ms（与现状持平）               |
| `syncSigRepos` 触发响应             | < 200ms（立即返回任务 ID）          |
| 一键同步执行（100 个仓库）          | < 5 分钟（异步，含平台元数据获取）  |
| Phase 1 迁移脚本（10 万行）         | < 10 分钟                           |

## 6. API 接口设计

### 6.1 现有接口改造：`POST /project-repo/add-repo`

请求体在 `RepoDTO` 基础上新增：

```jsonc
{
  // ... 现有字段不变（含表单配置） ...
  "isParticipateOperation": true, // 新增, 可选: 是否参与运营（默认是）
}
```

业务变化见 §2.1：命中多行 → 当前项目新建/更新本行（复制上次录入配置）、提交时提示配置不一致不覆盖。

### 6.2 现有接口改造：`POST /project-repo/update-repo`

请求体在 `RepoDTO` 基础上新增：

```jsonc
{
  // ... 现有字段不变（含表单配置） ...
  "isParticipateOperation": true, // 新增, 可选: 是否参与运营（默认是）
}
```

业务变化见 §2.3：不做 SIG 来源拦截；**编辑本行保存时若该 repo_url 组内存在跨项目行且配置不一致 → 前端保存前弹窗提示性告警，用户确认后仅更新本行（不覆盖其他项目行）**；无跨项目行或配置一致时直接更新本行。

### 6.3 新增接口 1：`POST /project-repo/check-repo-url`（录入/编辑冲突检测）

**用途**：同一接口支持两类调用：① 录入 blur 检测（只传基础参数）——检测 repo_url 是否已在其他项目录入（同组多行），命中返回上次录入配置副本 `lastConfig` 与已关联项目列表（供表单预填与提示文案）；② 保存前一致性比对（传 `formConfig`，编辑时另传 `repoId`）——比对用户当前表单配置与同组其他行，返回差异字段 `configDiff`（录入提交前 / 编辑保存前均调本接口；写接口 add-repo / update-repo 不做比对，保持纯写入语义）。

请求：

```jsonc
// 录入 blur 检测
{ "projectId": 1, "repoUrl": "https://gitcode.com/org/repo.git" }

// 保存前一致性比对（编辑场景示例；录入场景 blur 返回 repoId 非 null 时一并传）
{
  "projectId": 1,
  "repoUrl": "https://gitcode.com/org/repo.git",
  "repoId": 1001,                      // 比对时排除本行
  "formConfig": { ... }                // 用户当前表单配置（默认分支不传、不参与比对）
}
```

响应（已存在）：

```jsonc
{
  "code": 200,
  "data": {
    "exists": true,
    "repoId": 1001,                    // 当前项目本行 repo_id（未录入为 null）
    "lastConfig": {                    // 上次录入该代码仓的配置副本（仅录入场景预填表单用；不含 remark——备注为项目特定信息，不跨项目复制）
      "repoName": "repo", "repoOwner": "sig-owner", "purpose": "自研源码",
      "openSource": "lead", "assumePr": "1", "isAutoFormat": false,
      "isSuppressionEnabled": true, "isParticipateOperation": true, ...
    },
    "associatedProjects": [            // 已关联项目列表（不含当前项目，供提示文案展示）
      { "projectId": 2, "projectName": "项目A" },
      { "projectId": 3, "projectName": "项目B" }
    ],
    "configDiff": [                    // 仅当请求传 formConfig 时返回：表单配置与同组其他行的差异字段
      { "field": "assumePr", "fieldLabel": "接管PR管理", "currentValue": "1", "otherValues": [{"projectId": 2, "projectName": "项目A", "value": "0"}] }
    ]
  }
}
```

前端逻辑（录入与编辑不同）：**录入**据 `exists=true` 直接使用 `lastConfig` 同步进表单（可修改），提交前传 `formConfig` 再调本接口，据 `configDiff` 提示配置不一致；**编辑**打开时回显本行当前配置（不预填其他项目数据），保存前传 `repoId` + `formConfig` 调本接口，据 `configDiff` 提示性告警。默认分支不在本接口返回（录入沿用现有仓库信息获取逻辑，编辑回显本行数据）。

### 6.4 新增接口 2/3：`GET|POST /project-config/global-config`（项目级全局配置，由 ProjectConfigController 实现）

- `GET /project-config/global-config?userId=xxx&projectId=1`：回显全局配置（sigInfoLocations 多路径 + 各平台 roleMapping + 公共账号掩码）。**sigInfoLocations 回显按平台分键**（`{ gitcode: [...], gitee: [...], github: [...] }`）；POST 提交同样按平台分键提交。
- `POST /project-config/global-config`：**全局配置唯一写入口**，一次提交全部配置内容（三页签 + 代码仓录入配置区）——① 更新 `config_json.sigInfoLocations`（**按平台分键的 Map**，保存时校验每条 URL 域名与平台键一致）+ `config_json[platform].roleMapping`（仅 gitcode）（现有 `/project-config/update-gitcode-role-mapping` 废弃，前端改调本接口；路径可用性校验已前移至输入时的 `validate-sig-path` 接口，见 §6.5）；② **项目公共账号更新也并入本接口**（按平台提交登录名 + 令牌，令牌加密入库、留空不覆盖；**实现层仍写入现有项目公共账号表 `project_common_account_info`，不进 config_json，不迁移**）；接口内对 `projectId` 加分布式锁（防 config_json 读-改-写并发丢更新，见 §5.3）。

> **控制器归属**：由现有 `ProjectConfigController` 提供（`/project-config` 路径），不占用 `/project-repo`。

### 6.5 新增接口 4：`POST /project-config/validate-sig-path`（sig-info 路径批量校验，由 ProjectConfigController 实现）

**用途**：用户在全局配置弹窗输入/修改 sig-info 路径后（blur / 防抖）**批量**校验：每条路径（owner/repo/branch/path）是否可访问、其下是否存在 sig-info.yaml 文件。单条失败不阻断其余路径；校验结果就地展示，不阻断保存。

请求（批量）：

```jsonc
{
  "userId": 10001,
  "projectId": 1,
  "paths": [
    // ≤20 条
    "https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/openLiBing-private",
    "https://gitcode.com/openlibing/community-private/blob/master/openLiBing-private/sigs/sig2",
  ],
}
```

响应（数组，逐条对应入参 paths）：

```jsonc
{
  "code": 200,
  "data": [
    {
      "path": "https://gitcode.com/openlibing/community-private/blob/master/...", // 对应该条入参路径
      "valid": true, // 路径存在且 sig-info.yaml 文件存在
      "platform": "gitcode", // 后端根据 URL 域名解析的平台（gitcode/gitee/github）
      "errorCode": null, // 失败时：REPO_NOT_FOUND / BRANCH_NOT_FOUND / FILE_NOT_FOUND / API_ERROR
      "message": "校验通过", // 失败原因描述
    },
  ],
}
```

### 6.6 新增接口 5：`POST /project-config/sig-sync`（SIG 仓一键同步，异步 + 分布式锁，由 ProjectConfigController 实现）

**用途**：触发 SIG 仓一键同步异步任务（带分布式锁，见 §2.2.3）。

请求：`{ "userId": xxx, "userName": "xxx", "projectId": 1 }`

响应（立即返回任务 ID，异步执行）：

```jsonc
{
  "code": 200,
  "data": {
    "taskId": "sig-sync-123456",
    "status": "RUNNING",
    "message": "SIG同步任务已触发，请稍后查询结果",
  },
}
```

> 若分布式锁获取失败（已有任务在执行），返回 `status=RUNNING` + 已有任务信息，不重复触发。

### 6.7 新增接口 6：`GET /project-config/sig-sync/status`（查询一键同步任务状态，由 ProjectConfigController 实现）

**用途**：前端轮询一键同步任务状态（**任务状态在全局配置弹窗内展示**）。

请求：`GET /project-config/sig-sync/status?userId=xxx&projectId=1&taskId=sig-sync-123456`

响应：

```jsonc
{
  "code": 200,
  "data": {
    "taskId": "sig-sync-123456",
    "status": "SUCCESS", // RUNNING / SUCCESS / FAILED / PARTIAL
    "imported": 45,
    "failed": 3,
    "failedRepos": [
      // 失败仓库列表（含失败原因）
      { "repoUrl": "...", "reason": "平台API超时" },
    ],
    "message": "同步完成：成功 45 个，失败 3 个",
  },
}
```

### 6.8 接口契约汇总

| 接口                                   | 方法 | 路径                                | 控制器                  | 请求体                                                                            | 响应体                                                                           |
| -------------------------------------- | ---- | ----------------------------------- | ----------------------- | --------------------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| 录入仓库（改造）                       | POST | `/project-repo/add-repo`            | RepoController          | RepoDTO（新增 isParticipateOperation）                                            | `DataResult<Integer>`                                                            |
| 修改仓库（改造）                       | POST | `/project-repo/update-repo`         | RepoController          | RepoDTO（新增 isParticipateOperation）                                            | `DataResult<Integer>`                                                            |
| 录入/编辑冲突检测（新增）              | POST | `/project-repo/check-repo-url`      | RepoController          | RepoUrlCheckQueryDTO                                                              | `DataResult<RepoUrlCheckVO>`                                                     |
| 查询全局配置（新增）                   | GET  | `/project-config/global-config`     | ProjectConfigController | projectId                                                                         | `DataResult<GlobalConfigVO>`（含公共账号掩码）                                   |
| 更新全局配置（新增，公共账号更新并入） | POST | `/project-config/global-config`     | ProjectConfigController | GlobalConfigUpdateDTO（sigInfoLocations + roleMapping + 项目公共账号登录名/令牌） | `DataResult<GlobalConfigVO>`（公共账号实现层仍存 `project_common_account_info`） |
| sig-info 路径校验（新增，批量）        | POST | `/project-config/validate-sig-path` | ProjectConfigController | {userId, projectId, paths[]}                                                      | `DataResult<List<SigPathValidateVO>>`（逐条 valid/platform/errorCode/message）   |
| SIG 仓一键同步（新增，异步 + 锁）      | POST | `/project-config/sig-sync`          | ProjectConfigController | {userId, userName, projectId}                                                     | `DataResult<SyncSigReposTaskVO>`（任务 ID + 状态）                               |
| 查询同步任务状态（新增）               | GET  | `/project-config/sig-sync/status`   | ProjectConfigController | taskId + projectId                                                                | `DataResult<SyncSigReposTaskVO>`（状态 + imported/failed）                       |

### 6.9 错误码约定

| code | msg                              | 场景                                           |
| ---- | -------------------------------- | ---------------------------------------------- |
| 200  | success                          | 成功                                           |
| 403  | SIG 路径不存在或不属于该项目     | sig-sync 接口未配置任何 sigInfoLocations       |
| 403  | 平台不合法                       | 路径 URL 域名非 gitcode/gitee/github           |
| 404  | sig-info.yaml 文件不存在         | 实时读取指定路径失败（目录下无 sig-info.yaml） |
| 500  | sig-info.yaml 格式错误或解析失败 | 实时解析失败                                   |
| 500  | 配置文件读取失败，请稍后重试     | 平台 API 调用失败                              |
| 500  | 仓库链接不合法                   | repoUrl 校验失败                               |
| 500  | 该仓库已录入当前项目             | 违反 uk_repo_project 唯一约束（并发兜底）      |

### 6.10 内部 API 契约

- `InternalProjectRepoController`（`POST /project-repo/internal/query-repo`）：语义与 `query-repo` 一致、不要求 `userId`；响应 `data.list` 为精简视图（repoId/projectId/repoName/repoUrl/repoOwner/platform/status），不返回敏感字段。**多行模型下按行返回，语义与现状一致，下游仓零改动**。
- 删除仓库后通知 openlibing-codecheck 重算 `is_used` 的调用契约不变（走 `OpenlibingCodeCheckClient`）。

## 7. 安全设计

### 7.1 鉴权

- 现有接口（add/update/delete/query-repo）鉴权不变（网关 token + 角色校验）。
- 新增接口：
  - 读权限（check-repo-url / global-config GET / validate-sig-path / sig-sync/status）：沿用 `query-repo` 角色集合
  - 写权限（global-config POST（含公共账号更新）/ sig-sync）：沿用 `add-repo` 角色集合
- 所有接口校验 `userId` 对 `projectId` 的访问权限（防跨项目越权）；越权校验沿用现有 `verifyPermissionsByProduct`（多行模型下 `repo_info.getProjectId()`=该行所属项目，语义与现状一致，**无需 ref 集合改造**）。

### 7.2 SIG 仓（sig-info.yaml 路径）访问安全

- **token 传递**：调平台 API 用 `Authorization: Bearer <token>` header（遵循项目硬约束），token 从项目公共账号获取、解密后使用，不入日志、不入 URL 参数。
- **路径白名单**：SIG 同步（sig-sync）等读取接口仅允许读取 `config_json.sigInfoLocations` 配置的路径，不接受前端任意传仓路径；`validate-sig-path` 为用户输入路径的**即时校验**接口（校验路径存在性与 sig-info.yaml 文件，仅返回校验结果、不返回文件内容）；校验 `owner/repo/branch` 安全字符、`path` 不含 `..`。
- **YAML 解析安全**：SnakeYAML `SafeConstructor`，拒绝实例化标签，失败返回明确错误不暴露堆栈。

### 7.3 输入校验

- 新增接口 `@Valid` + JSR-303 校验；`repoUrl` 沿用现有 `validateSafeUrl` 镜像校验（协议头白名单、域名信任、无 `..`）；`repoUrl` ≤512、`repoName` ≤50；`sigInfoLocations` 单次最多 20 个路径；`platform` 必须合法（从 URL 域名解析）；`validate-sig-path` 的 `path` 沿用同一 URL 校验规则（协议头白名单、域名信任、无 `..`）。

### 7.4 日志脱敏

- 禁止打印：accessToken（仓库/项目公共账号令牌）、`lastConfig.accessToken`、YAML 内 accessToken、`config_json` 整对象。
- 允许打印：projectId / repoUrl / platform / owner/repo/branch/path / 计数等。
- 冲突检测返回的 `lastConfig` 中 accessToken 序列化前置空；`get-global-config` 公共账号令牌掩码 `******`；`global-config POST` 提交的公共账号明文令牌不出日志、不返回。

### 7.5 一键同步与手动录入互不覆盖

- 一键同步只针对尚未录入当前项目的仓库（已录入不展示、不覆盖）；全局已存在仓库一键同步时**复制上次录入配置、不覆盖**（新行配置与上次一致）。
- SIG 来源仓库允许手动编辑（不做来源拦截）。
- 手动录入命中多行不视为错误：自动同步上次录入配置、提交时提示配置不一致不覆盖（见 §2.1）。

### 7.6 数据库安全

- `uk_repo_project (repo_url, project_id)` 防同项目重复录入；不做 repo_url 全局唯一。
- 软删除现状保留（is_deleted）；删除链路本期保持物理删除（与现状一致，7 仓零变化）。
- accessToken 明文存储现状不改（可后续独立立项加密）。

### 7.7 平台 token 安全

沿用现有 `GitCodeUtil`/`GiteeUtil`/`GithubUtil` token 使用方式；`SigInfoClient` 复用 `commonService.getGitcodeToken`，不引入新凭证。

### 7.8 迁移脚本安全

- **新增 `project_repo_global_config` 表 + 数据迁移（Liquibase）**：建表与存量 `project_gitcode_role_mapping.role_mapping` 迁移（→ `config_json.gitcode.roleMapping`，每项目一行批量 upsert 幂等可重跑）在**同一 Liquibase changeset** 内定义，**随实例启动原子执行**（与代码上线同步，杜绝「上线后-迁移前」角色映射读空的空窗）；迁移完成后旧表 `project_gitcode_role_mapping` 废弃（不物理删除，角色映射读写改指新表）。
- **framework 同步改造（例外仓）**：`ProjectServiceImpl` / `ProductServiceImpl` 删除产品/项目时的 `GitcodeRoleMappingMapper.deleteMappingByProjectId` 级联清理**改指新表** `project_repo_global_config`（删该 project_id 行）；清理未使用的 `selectMappingByProjectId` 注入。
- **Phase 1** repo 迁移（清洗同项目重复行 + 加唯一索引）：事务分批（每批 1000 行）提交、可重跑；只动 repo_info 本身，不触碰 7 仓数据。
- **framework 级联清理改造建议与 coderepo 同迭代上线**（避免 coderepo 上线而 framework 未改期间删除产品/项目时级联清理落空、新表残留脏行）。
- **Phase 1** repo 迁移在上线后统一执行、不阻塞上线；迁移前备份 repo_info（全局配置建表/迁移见首条，随实例启动）。
- 灰度开关 `coderepo.repo-decouple.enabled`（仅控制新逻辑开关，可快速回滚）。

### 7.9 安全验收清单

- [ ] accessToken 不出现在任何日志与 URL 参数中（grep + 网关日志验证）；调平台 API 走 `Authorization: Bearer` header
- [ ] SIG 读取接口传未配置的路径无法通过任意接口读取；`validate-sig-path` 仅返回校验结果、不返回文件内容
- [ ] `global-config POST` 提交的公共账号令牌不出日志、不返回明文；`global-config GET` 令牌掩码
- [ ] YAML 含 `!!java/object` 等危险标签时解析被拒绝
- [ ] 跨项目访问返回 403
- [ ] **Phase 1** 迁移后：`uk_repo_project` 生效（同项目同 repo_url 无法重复插入）；7 个下游仓按 `(project_id, repo_url)` 反查全部命中（SCA 联调用例）
- [ ] 录入时复制上次录入配置为普通查询+赋值（无全组 UPDATE）；提交时提示配置不一致不覆盖（单测）
- [ ] 编辑时检测配置不一致仅提示性告警，不覆盖其他项目行（单测 + DB 校验）
- [ ] **开关聚合**：同 repo_url 多行开关取 OR（MAX）——一行开启则聚合为开启，全关闭才关闭（单测 + DB 校验）
- [ ] `validate-sig-path`：路径存在 + sig-info.yaml 存在返回 valid=true；路径不存在 / 文件缺失返回对应 errorCode（单测）
- [ ] 一键同步异步执行 + 分布式锁：同一项目并发触发仅执行一次（单测）；锁超时自动释放防死锁
- [ ] 一键同步默认参数：别名冲突处理（repo名→repo-platform→加数字）、责任人=平台创建人账号名、默认分支=平台获取且不可修改、用途=自研源码、开源类型=主导开源、是否参与运营=是、其他开关=否、公共账号令牌=项目级（单测）
- [ ] 单元测试覆盖：手动录入命中多行（复制上次配置/提示不覆盖）、编辑提示性告警不覆盖、开关聚合 OR 逻辑、一键同步异步+锁+默认参数、全局配置 config_json 读写（含 roleMapping 迁移 + sigInfoLocations 多路径）、sig-info 路径校验、迁移幂等、sig-info.yaml 解析与路径白名单
