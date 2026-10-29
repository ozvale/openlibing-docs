# 设计报告：分支管理展示分支维度代码检查告警数

> 需求来源：`requirment_desc.md`。在代码仓管理页面的"分支管理"tab 中，展示每个分支的代码检查告警数，并支持点击指标跳转代码检查告警详情页（跳转由前端实现，本报告不涉及）；告警详情页需支持分支过滤条件。
>
> 实现范围：主要在 openlibing-coderepo；为支持分支维度统计，openlibing-codecheck 需扩展一个内部批量计数接口（仅加字段与聚合维度，无对外契约变化）。

## 1. 背景与目标

- 现状：仓库管理 tab 已展示"代码检查告警数"（`/project-repo/query-repo` 返回 `staticAlertCount`，**口径为整仓所有分支未处理告警之和**），但分支管理 tab（`/repo/branch/list`）只展示分支基本信息与代码度量，无告警数。
- 目标：
  1. `/repo/branch/list` 返回结果每行新增"该分支的代码检查告警数"字段；
  2. 口径沿用仓库 tab 现有告警数的 open 口径（未处理 = OPEN + PENDING_REVIEW），区别仅在新增分支过滤条件；同一仓库下所有分支的告警数之和即等于仓库 tab 展示的整仓告警数；
  3. 告警详情页带分支条件——codecheck 门户型接口已支持 `branches` 过滤，前端跳转时传参即可，后端无需新增接口。

## 2. 现状分析（取数链路调研结论）

### 2.1 `/repo/branch/list` 全链路

- Controller：`BranchController#queryProjectBranch`（`business/controller/BranchController.java`，`@RequestMapping("/repo/branch")` + `@PostMapping("/list")`），入参 `QueryProjectBranchDTO`（projectId 必填，pageSize 上限 200），返回 `DataResult<Map<String,Object>>`，data 结构 `{total, data: List<ProjectBranchInfoVO>}`。
- Service：`RepoServiceImpl#queryProjectBranch`（约 L4305-4348）。数据源是**本地 MySQL** `repo_branch` join `repo_info`（`RepoBranchInfoMapper.xml#queryProjectBranchByLimit`，L367-388），非实时调托管平台 API；权限经 `resolveAccessibleRepoScope` 做 repoId 白名单过滤。
- 返回行 VO：`ProjectBranchInfoVO`，现有字段：`branchId, branchName, repoId, projectId, repoName, repoUrl, platform, isDefault, isCodecheck, aniPoisoningCheck, updateBy, updateAt, metrics, utCoverage`。每行自带 `repoUrl` 与 `branchName`，可直接与 codecheck 告警数据的 `(repo 坐标, branch)` 维度对齐。
- 已有"每行附带外部数据"先例：`buildProjectBranchInfoList`（L8697-8737）中按 repoUrl 批量取代码度量再按 branchName 行级匹配，本次新增告警数字段完全类比该模式。

### 2.2 `/project-repo/query-repo` 仓库"代码检查告警数"实现（参考实现）

> 已确认：该字段口径为**整仓所有分支的未处理告警之和**，并非默认分支口径。

- 字段：`SpaceRepoDTO.staticAlertCount`（Integer，null 表示查询失败、前端显示 `--`）。
- 取数链路：`RepoServiceImpl#fillStaticAlertCounts` → **`fetchStaticAlertCountMap`（L821-874）**：
  1. 查 `repo_info` 取 `repo_id, repo_url`；
  2. `RepoUrlParser.parse(repoUrl)` 解析坐标 `(repoType, owner, repo)`（解析失败的仓库跳过）；
  3. 组装 `StaticAlarmCountBatchDTO{projectId, repos:[{repoId, repoType, owner, repo}]}`；
  4. Feign 调 `OpenlibingCodeCheckClient#batchStaticAlarmCount` → **`POST /internal/codescan/v1/static-alarm/issue/count/batch`**，返回 `StaticAlarmCountBatchVO{counts:[{repoId, openCount, ignoredCount}]}`。
- 降级约定：整个取数方法 try-catch，异常/空返回 `Collections.emptyMap()`，行内保持 null，**绝不阻断列表主查询**。
- **口径澄清**：现有计数未按分支过滤，统计的是该仓所有分支 open 数之和（codecheck Mongo 主表按 branch 拆分记录，聚合 group 未含 branch）。本次做分支维度统计时沿用同一 open 口径，仅新增 branch 维度过滤。

### 2.3 codecheck 侧告警数据与接口

- 存储：MongoDB 集合 `static_alarm_issue`（`StaticAlarmIssueEntity`），定位字段 `repo_type / owner / repo / repo_key / project_ids / branch / list_state / severity` 等；**不同 branch 是不同主表记录**（upsert 保留 branch 维度），已有 `idx_issue_branch_status` 索引——分支维度天然可聚合。
- open 口径（`StaticAlarmServiceImpl#resolveOpenAndIgnoredByListState`，L343-358）：`open = OPEN + PENDING_REVIEW`；`ignored = IGNORED_* + RESOLVED_AUTO + SUPPRESSED_BY_COMMENT`。
- **已支持分支条件（无需改动）**：
  - 告警列表 `POST /static-alarm/v1/list`：`StaticAlarmQueryDTO.branches`（List\<String\>，默认仅查主干分支），底层 `buildBaseFilterCriteria` 已含 `.inIfNotEmpty("branch", ...)`；
  - 状态计数 `POST /static-alarm/v1/issue/count`：`StaticAlarmCountDTO.branches` 同样支持。
  - **结论：告警详情页带分支条件 = 前端在请求体传 `branches` 数组，后端零改动。**
- **不支持分支维度（本次唯一需 codecheck 扩展的点）**：内部批量计数接口 `/internal/codescan/v1/static-alarm/issue/count/batch`——入参 `RepoItem` 无 branch、Mongo 聚合 group 不含 branch、出参 `Item` 无 branch。

## 3. 方案设计

### 3.1 总体思路

完全复用仓库 tab 的"批量坐标对齐 + Feign 批量计数 + 空降级"模式，将批量接口扩展出 branch 维度：一次请求返回当前页所有 `(repo, branch)` 组合的 open 数，行级匹配回填到 `ProjectBranchInfoVO`。不采用"门户型 count 接口按行循环调用"的 N+1 方案（仅作兜底，不推荐）。

### 3.2 数据流

```
前端 /repo/branch/list
  └─ BranchController#queryProjectBranch
      └─ RepoServiceImpl#queryProjectBranch
          ├─ DB 分页查分支行（repo_branch join repo_info）→ List<ProjectBranchInfoVO>
          └─ fillBranchStaticAlertCounts(vos)   ← 新增
              ├─ RepoUrlParser.parse(row.repoUrl) → (repoType, owner, repo)
              ├─ 组装 StaticAlarmCountBatchDTO{projectId, repos:[{repoId, repoType, owner, repo, branch: row.branchName}]}
              ├─ Feign: OpenlibingCodeCheckClient#batchStaticAlarmCount
              │    └─ codecheck: StaticAlarmInternalController#batchIssueCount
              │        └─ StaticAlarmServiceImpl#batchIssueCount（key 扩为 repoType|owner|repo|branch）
              │            └─ StaticAlarmOperation#countIssuesGroupByRepoAndListState（group 加 branch）
              │                └─ Mongo static_alarm_issue：match(project_ids + branch in...) group(repo_type,owner,repo,branch,list_state)
              └─ 按 (repoId, branchName) 行级回填 vo.staticAlertCount（无值保持 null）
```

### 3.3 接口变更

**`/repo/branch/list`（对外，向后兼容）**

- `ProjectBranchInfoVO` 新增字段：

```java
/** 该分支的代码检查未处理告警数（open = OPEN + PENDING_REVIEW；null 表示查询失败或不可用，前端显示 --） */
private Integer staticAlertCount;
```

- 入参不变；返回包装结构不变；对未升级的调用方为纯新增字段，向后兼容。

**`/internal/codescan/v1/static-alarm/issue/count/batch`（内部 Feign，加维度）**

- 请求 `RepoItem` 新增 `branch`（String，可空：为空时保持现状语义=整仓统计）；
- 响应 `Item` 新增 `branch`（String，回显请求维度）；
- 不传 branch 的旧调用方行为完全不变。

### 3.4 codecheck 侧扩展（4 处，均为加维度）

| 层        | 文件                                                                                                  | 改动                                                                                                                                                                             |
| --------- | ----------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| DTO       | `business/entity/dto/alarm/StaticAlarmCountBatchDTO.java`                                             | `RepoItem` 加 `branch` 字段                                                                                                                                                      |
| VO        | `business/vo/alarm/StaticAlarmCountBatchVO.java`                                                      | `Item` 加 `branch` 字段                                                                                                                                                          |
| Service   | `business/service/impl/alarm/StaticAlarmServiceImpl.java#batchIssueCount`（L1289-1372）               | 回填 key 由 `repoType                                                                                                                                                            | owner | repo`扩为`repoType | owner | repo | branch`；branch 为空的条目走原 key |
| Operation | `business/operation/alarm/StaticAlarmOperation.java#countIssuesGroupByRepoAndListState`（L2064-2083） | 聚合 group 追加 `"branch"`：`Aggregation.group("repo_type","owner","repo","branch","list_state")`；底层 `buildBaseFilterCriteria` 已支持 branch 条件（L2125），无需改 match 逻辑 |

- 越权防护：`resolveRepoCoordinates` 的项目坐标交集校验在 repo 维度，branch 属 repo 内维度，权限模型不破坏、无需调整。
- 索引：已有 `idx_issue_branch_status`，group 前的 match 含 `branch $in`，命中索引，聚合规模与现接口同量级。

### 3.5 coderepo 侧改动（3 处）

| 文件                                                                                                         | 改动                                                                                                                                                                                                                       |
| ------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `business/vo/ProjectBranchInfoVO.java`                                                                       | 新增 `staticAlertCount` 字段                                                                                                                                                                                               |
| `business/dto/codecheck/StaticAlarmCountBatchDTO.java`、`business/vo/codecheck/StaticAlarmCountBatchVO.java` | 镜像类同步加 `branch` 字段                                                                                                                                                                                                 |
| `business/service/impl/RepoServiceImpl.java`                                                                 | `buildProjectBranchInfoList`（L8697）中新增批量回填：新增方法 `fillBranchStaticAlertCounts(List<ProjectBranchInfoVO>)`（或复用改造 `fetchStaticAlertCountMap` 支持带 branch 的重载），`OpenlibingCodeCheckClient` 签名不变 |

回填逻辑要点：

1. 当前页分支行按 `repoUrl` 解析坐标（`RepoUrlParser.parse`，解析失败或 `platform` 非 codecheck 支持平台的行直接置 null 跳过）；
2. ~~可选优化：仅对 `isCodecheck='1'`（已接入代码检查）的分支取数，减少无效调用~~（联调阶段已确认：**不做 isCodecheck 过滤**，未接入分支同样展示告警数；仅校验 repoUrl/branchName 非空与坐标解析成功）；
3. 组装去重后的 `(repo, branch)` 坐标集合，一次 Feign 批量调用；
4. 按 `(repoId, branchName)` 匹配回填；Map 无值/调用异常 → 保持 null（前端显示 `--`）；
5. 全程 try-catch，不影响列表主数据返回。

### 3.6 排序与跳转

**排序（补充设计：支持按告警数排序）**

分支 tab 支持按 `staticAlertCount` 排序：前端传 `sortField=staticAlertCount`、`sortOrder=asc/desc`（不传 sortOrder 时沿用现有语义：非 `asc` 一律按 desc 处理）。

方案：复用分支 tab 现有"内存排序"路径（`isMemorySortField` 为 true 时：全量取回 → 内存排序 → 内存分页，`RepoServiceImpl#queryProjectBranch` L4318-4340），不新做 DB 排序——告警数存于 codecheck 的 Mongo，无法进入本地 MySQL 的 order by，内存排序是唯一可行路径，且与仓库 tab 同款先例 `doQueryRepoInfoByStaticAlertCount`（L724-808：全量取回 + 批量计数 + 内存排序 + 内存分页）模式完全一致。

改动点（4 处，均在 coderepo `RepoServiceImpl`）：

1. **排序字段注册**：`PROJECT_BRANCH_MEMORY_SORT_FIELDS`（内存排序字段集合：度量类指标 + `staticAlertCount`，均存于外部存储、无法走 DB order by）加入 `"staticAlertCount"`，使该 sortField 走内存排序路径（原 `PROJECT_BRANCH_METRIC_SORT_FIELDS` 已更名，`isMetricSortField`→`isMemorySortField`、`sortProjectBranchByMetric`→`sortProjectBranchInMemory`，因 staticAlertCount 并非度量类指标）；
2. **回填时机调整（核心）**：内存排序路径中，当 `sortField=staticAlertCount` 时，在排序前对**全量** `allData` 调用 `fillBranchStaticAlertCounts`，排序分页后**不再**对当前页重复回填；其余内存排序字段（度量类指标）维持现状（分页后仅回填当前页），避免无谓的全量 Feign 调用；
3. **比较器**：`sortProjectBranchInMemory` 为 `staticAlertCount` 增加独立比较分支——它是 VO 顶层 Integer 字段而非 `metrics` 内的 `MetricItemVO`，不能走 `extractMetricSortValue`；比较逻辑 `Comparator.comparingInt(vo -> vo.getStaticAlertCount() == null ? 0 : vo.getStaticAlertCount())`，**null（查询失败/未接入）按 0 参与排序**，与现有 metric 取值 null→0d 语义一致；tie-breaker 沿用 branchId 降序不变；
4. **普通路径不受影响**：不传 sortField 或传非 metric 字段时，仍走 DB 分页 + 当前页回填，行为不变。

性能评估：排序触发时全量回填 = 去重 `(repoId, branchName)` 后一次批量 Feign + codecheck Mongo 聚合（group 规模 ≤ 全量分支数 × 状态数）。单项目分支数通常为数百量级，且"全量取回 + 内存排序"本身是现有内存排序路径的既有行为，风险同级可接受；`pageSize ≤ 200` 与降级约定（异常时 null→0 参与排序、不阻断主查询）不变。

**跳转**：由前端实现——点击指标携带 `projectId + repos(owner/repo 坐标或 repoUrl) + branches=[branchName]` 跳转代码检查告警页；告警列表接口 `/static-alarm/v1/list` 与计数接口已支持 `branches` 过滤，后端零改动。前端所需坐标信息可从本接口已有的 `repoUrl` 解析，无需后端新增跳转参数。

## 4. 性能与容量评估

- 分支列表单页上限 200 行，去重后 (repo, branch) 组合 ≤ 200，一次批量 Feign 调用；codecheck Mongo 聚合与仓库 tab 现有批量计数同量级（match 走 project_ids + branch 索引，group 分组数 ≤ 组合数 × 状态数）。
- 不引入本地缓存/落表：现有链路均为实时查询、无分支维度统计表，保持架构一致；`pageSize ≤ 200` 的分页约束天然控制单次聚合规模。
- 降级：codecheck 不可用或超时时，仅新增字段为 null（前端显示 `--`），列表主查询不受影响。

## 5. 兼容性与安全

- 接口兼容：`/repo/branch/list` 纯新增返回字段；内部批量接口 branch 字段可空、旧调用方语义不变。
- 权限：沿用 `resolveAccessibleRepoScope`（repoId 白名单）+ codecheck 侧项目坐标交集校验，branch 维度不引入新的越权面。
- 数据口径：与仓库 tab `staticAlertCount` 一致（open = OPEN + PENDING_REVIEW）；展示文案建议前端标注"未处理告警数"以对齐语义。

## 6. 测试设计

1. **codecheck**：`StaticAlarmServiceImpl#batchIssueCount` 单测——带 branch / 不带 branch（旧语义回归）/ branch 无告警返回 0；`StaticAlarmOperation` 聚合 group 含 branch 的集成用例。
2. **coderepo**：`RepoServiceImplTest` 扩展（已有 `fetchStaticAlertCountMap` 用例约 L2344 可参照）——正常回填、坐标解析失败行置 null（未接入分支不做 isCodecheck 过滤、同样取数）、Feign 异常降级为 null、同仓多分支匹配正确性。
3. **coderepo 排序**（对应 3.6 补充设计）：`sortField=staticAlertCount` 时——全量回填后排序分页正确（asc/desc）、null 告警数按 0 参与排序、分页后不重复发起 Feign（mock 验证调用次数为 1）、其余 metric 排序字段仍为分页后回填（调用次数与页大小相关）、普通路径行为不变。
4. **联调验证**：分支管理 tab 数字与告警详情页（同 repo + branch 过滤）count 一致；按告警数排序后，首位分支的告警数 = 该项目全部分支中的最大值，且与详情页 count 一致。

## 7. 待确认点

1. **跳转参数约定**：前端跳转告警页所需的 repo 定位参数用 `repoUrl` 还是解析后的 `(owner, repo)` 坐标，需与前端约定（后端两者信息都已具备，无需新增字段）。
2. **是否仅统计已接入代码检查的分支**（`isCodecheck='1'`）：建议是，减少无效调用；若产品要求未接入的显示 0 而非 `--`，回填逻辑微调。
3. **告警数口径**：沿用 open（含待评审）口径与仓库 tab 对齐；若产品要求"仅 OPEN"需同步调整 codecheck 口径解析（`resolveOpenAndIgnoredByListState`）。
4. **两 tab 口径语义区分**：仓库 tab 为整仓口径（所有分支之和），分支 tab 为精确分支口径，同一仓库两者数值满足"各分支之和 = 整仓数"。前端展示文案建议区分（如分支 tab 标注"该分支告警数"）；该等式可作为上线后的一致性校验手段。

## 8. 改动点清单汇总

| 仓        | 类型      | 文件                                                                                                         | 改动                           |
| --------- | --------- | ------------------------------------------------------------------------------------------------------------ | ------------------------------ |
| coderepo  | VO        | `business/vo/ProjectBranchInfoVO.java`                                                                       | 加 `staticAlertCount`          |
| coderepo  | DTO/VO    | `business/dto/codecheck/StaticAlarmCountBatchDTO.java`、`business/vo/codecheck/StaticAlarmCountBatchVO.java` | 加 `branch`                    |
| coderepo  | Service   | `RepoServiceImpl#buildProjectBranchInfoList` / 新增 `fillBranchStaticAlertCounts`                            | 批量取数 + 行级回填 + 降级     |
| codecheck | DTO/VO    | `business/entity/dto/alarm/StaticAlarmCountBatchDTO.java`、`business/vo/alarm/StaticAlarmCountBatchVO.java`  | 加 `branch`                    |
| codecheck | Service   | `StaticAlarmServiceImpl#batchIssueCount`                                                                     | 回填 key 加 branch 维度        |
| codecheck | Operation | `StaticAlarmOperation#countIssuesGroupByRepoAndListState`                                                    | Mongo group 加 `"branch"`      |
| 前端      | —         | 分支管理 tab 指标渲染与跳转传参                                                                              | 需求说明：由前端实现，另行设计 |

上线顺序：codecheck 内部接口扩展先发布（向后兼容），coderepo 随后发布即可。
