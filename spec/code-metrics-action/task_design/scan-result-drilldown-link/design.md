# 【openLiBing】代码度量扫描插件结果输出增加openLiBing平台扫描结果链接 — 技术设计

- **FE 需求**：【openLiBing】插件结果输出增加openLiBing平台扫描结果链接
- **业务 Issue**：https://gitcode.com/openlibing/code-metrics-action/issues/25
- **涉及仓库**：code-metrics-action、openlibing-coderepo、openlibing-web（前端侧协同，不随本需求提 PR）
- **流程模式**：Full
- **日期**：2026-10-09
- **修订**：2026-10-19 输出通道收敛为仅 `ATOMGIT_OUTPUT`（移除 `ATOMGIT_STEP_SUMMARY` 通道；插件 commit `692b071`）

## 1. 方案设计

### 1.1 背景与现状

**插件上报链路**：插件扫描完成后，`CoderepoUploader.upload()` 先把全量数据（总体指标 + 文件明细 + 重复块）上传 OBS（经 `getCredentials()` 获取 STS 临时凭证），再以元数据 + obsUrl 调用上报接口 `POST /action-api/metrics/code/report`（OIDC 联邦认证，`callApig` 签名）。另有 AK/SK 模式的旧网关路径（`/openlibing-coderepo/...`，`ApigSigner` 签名 + `apig-app-key`/`apig-app-secret` 输入，OBS 走静态凭证）与 OIDC 并存：OIDC 为用户主用路径，**AK/SK 模式本次保留**（部分测试仓不适合纳入 OIDC 认证凭据授权项目），本次改造不改变插件鉴权模式。后端 `CodeMetricsController#reportMetrics` → `publishToMq` 将请求投递到导入队列，由消费者异步下载 OBS 文件并解析入库。**接口为异步受理模型**：当前响应为 `DataResult<String>`（`data` 为空，仅 message"上报已受理，正在异步导入"），不返回入库记录 ID 与任何链接。

**平台前端现状**：

- 代码仓列表页 `/apps/repos` 支持 URL 直达：现有 `autoGoBranch(repoId)` 在 route query 含 `metricType`（0~4，对应 `MetricTypeEnum`）时，按 repoId 定位仓库后打开指标详情弹窗（`MetricsDetailDialog`，props：repoId/repoName/branchName/pipelineRunId/metricType）；数据接口 `file-detail` 按 (git_url, branch_name, pipeline_run_id) 精确匹配（`pipelineRunId` 现为可选入参，传则定位该次记录、不传取最新）；metricType 决定弹窗明细列布局，**缺失 metricType 时弹窗表格无列**。
- 分支管理页展示每个分支各指标的"最新一次成功记录"（逐指标取最新，`status=0`），**无历史视图**；从弹窗返回时会清空 query，历史上下文无法保留；指标列已有说明气泡（`el-tooltip`）。

**问题**：

1. 若按"每指标各一条链接"输出：5 类指标 → 5 条，未来指标扩展持续膨胀，用户困惑；
2. 链接若钉定 pipelineRunId（携带本次运行标识）：用户看到的是"该次运行"的历史数据，而正常渠道进入只能看到"最新"数据；刷新/回退/重新筛选后历史视图丢失，语义冲突。本次决策：**平台前端页面永远只展示最新数据**——链接不携带 pipelineRunId，只取当前分支最新指标数据，并以指标说明气泡声明数据口径，不引入历史记录页面；
3. 上报响应不含任何链接，插件无法生成下钻入口；且同一 repoUrl 可能归属多个项目（`repo_info` 按项目维度记录），链接需由服务端确定唯一跳转目标（本次取查询第一个项目，不返回多链接）。

### 1.2 改造目标

- 服务端在上报受理成功后返回**固定 1 条**详情链接（多项目时取查询第一个项目；不返回多链接、不带项目名称、不携带指标维度）：落地分支管理页外层并自动按分支管理页既有筛选条件（`platforms`/`repoUrlLike`/`branchNameLike`）筛选（不打开指标弹窗，精确命中行置顶）；分支登记校验下沉服务端，分支未登记 / 仓未录入时返回对应提示（tip）
- 前端链接落地**永远展示最新数据**：链接不携带 pipelineRunId，只按代码仓 + 分支取当前分支最新指标数据；`file-detail` 接口的 `pipelineRunId` 保持**可选**能力（传则精确查该次历史记录，不传取该分支最新成功记录），链接口径与接口能力解耦；刷新/回退/重新筛选后视图语义稳定；指标说明气泡声明数据口径（最新成功检测结果，非历史运行数据）
- 插件把链接 / 提示作为 `ATOMGIT_OUTPUT` 概览行输出（链接行 key 末尾小写 `url`，固定 1 行），并同步打印运行日志（链接打印实际地址）；链接固定 1 条（不随项目数、指标数膨胀）
- 保留插件既有 AK/SK 模式（与 OIDC 并存，部分测试仓不适合纳入 OIDC 凭据授权项目），本次不改变插件鉴权与上报路径
- 不改变上报接口路径、入参、message 语义、扫描逻辑与现有指标输出

### 1.3 总体方案

```text
code-metrics-action
  scanner.scan() → CoderepoUploader.upload()
      1) 全量数据上传 OBS（凭证方式随鉴权模式，现状不变）
      2) POST /action-api/metrics/code/report（鉴权模式现状不变：OIDC 或 AK/SK）
      ▼
openlibing-coderepo  CodeMetricsController#reportMetrics → publishToMq
      1) 投递导入队列（MQ，异步入库，行为不变）
      2) 投递成功后 buildReportVO(gitUrl, branchName)：
         repo_info 按 repo_url 解析（跨项目，含 repoId/projectId/platform；取查询第一行）
         → 校验第一行项目的分支登记（repo_branch 精确 + has_branch='1'）
         → 已登记 → 拼单条链接（链接参数与分支管理页筛选条件一致）
         → 仓未录入 / 第一行项目分支未登记 → detailLink 空 + tip 提示
      ▼
  DataResult<CodeMetricsReportVO> { code, msg:"上报已受理，正在异步导入", data:{ detailLink, tip } }
      ▼
插件 report() 解析 → scanner.uploadInfo → index.js
  ATOMGIT_OUTPUT 追加 扫描结果url=链接 概览行（key 末尾小写 url → 平台渲染可点击；机器消费）+ core.info 打印
      ▼
openlibing-web  用户点击链接（前端侧协同能力）
  /apps/repos?projectId=&platforms=&repoUrlLike=&branchNameLike=
    → autoGoBranch：切换到分支 Tab + 自动应用三筛选条件（不打开弹窗；精确命中行置顶）
    → 展示该分支最新指标数据（永远最新）
    → 指标列说明气泡声明数据口径（最新成功检测结果，非历史运行数据）
```

### 1.4 关键决策

1. **固定 1 条链接（多项目取查询第一个项目），不带指标维度**：同一 repoUrl 可能归属多个项目（`repo_info` 按项目维度记录），服务端按查询顺序取第一个项目生成单条链接（不返回多链接、不带项目名称），插件输出恒定 1 行；链接只定位"代码仓 + 分支"，落地分支管理页外层；指标扩展（未来新增指标）不增加链接；不再依赖 metricType 打开弹窗，规避"弹窗缺 metricType 无列"的冲突。
2. **链接不携带 pipelineRunId，`file-detail` 入参可选化**：链接只定位"代码仓 + 分支"（不含本次运行标识），落地后前端按 repo + 分支取"当前分支最新指标数据"；`file-detail` 接口的 `pipelineRunId` 为**可选入参**（不设必填校验）——传则按 (git_url, branch_name, pipeline_run_id) 精确返回该次历史记录，不传则按 (git_url, branch_name, status=0) 取该分支最新成功记录；链接入口不展示"本次运行"上下文、不提供历史记录入口，口径恒为"最新"，而接口层保留其他调用方按指定记录下钻的能力（链接口径收敛 ≠ 接口能力撤除）。
3. **不引入历史数据视图（记录页与记录列表接口均不建）**：平台前端页面永远只展示最新数据；"历史/最新"语义冲突通过"链接不携带 pipelineRunId + 气泡声明口径"消除，不新增页面、接口与路由（无当前确定调用方的新接口不建）；`file-detail` 的 `pipelineRunId` 可选能力仅服务既有调用方按记录下钻，不承载历史列表视图。
4. **指标说明气泡声明数据口径**：分支管理页指标列说明气泡（既有 `el-tooltip`）补充提示「指标数据均取自该分支最新一次成功检测结果，非历史流水线运行数据。」，消除用户对"是否为我这次流水线的数据"的疑虑。
5. **分支是否登记校验在服务端**：复用 `RepoBranchInfoMapper#queryBranch(repoId, null, branchName, "1", null)` 精确校验（`branch_name` 等值 + `has_branch='1'`，方法已支持，无需新增 Mapper；仅对查询第一行项目校验）；未登记时后端直接返回插件提示（tip），插件只负责输出该提示、不输出链接（不硬编码文案）。既有分页查询 `queryByLimit` 的 branchName 为 LIKE 模糊匹配，不能复用做精确登记校验。
6. **两类提示（tip），服务端单点定义**：
   - 仓未录入（repo_info 无关联行）：「当前仓未录入openLiBing平台，无法生成跳转链接，请先联系SRE完成代码仓录入。」
   - 分支未登记（查询第一个项目该分支未登记）：「当前分支未录入openLiBing平台，请前往openLiBing平台同步最新分支」
     插件按 tip 非空即输出提示行，不区分类型、不硬编码。
7. **多项目时严格取查询第一个项目**：仅校验/生成第一个项目的链接（`selectByRepoUrl` 既有排序：录入时间倒序取第一行，行为确定可预期）；第一个项目该分支未登记即返回分支提示，不回退其他项目。
8. **保持 message 语义**：`DataResult.success("上报已受理，正在异步导入", vo)`；插件 `code !== 200` 判定不变；投递失败仍 `failureMessage`。
9. **平台地址复用既有配置 `openlibing.domain`**：coderepo 与 cicd 均已使用该属性拼接平台页面链接（如 `RepoServiceImpl` 的 `/apps/repos`、`/apps/project` 提示链接），`CodeMetricsServiceImpl` 以 `@Value("${openlibing.domain}")` 注入使用；不新增配置项、不在代码或 yaml 中硬编码公网域名，各环境域名由配置中心统一下发。
10. **URL 归一化下沉单一来源**：新增 `RepoUrlUtil.normalize`（去空白、去末尾 `.git`），`UtCoverageServiceImpl#normalizeGitUrl` 改为委托该方法（行为不变），消除第二份实现。
11. **构建异常不阻断上报**：构建逻辑独立兜底捕获，异常时仅告警并返回空 `detailLink` + 空 `tip`（不误报"未录入"）。
12. **链接参数与分支管理页筛选条件一致（不发明新参数）**：链接落地复用分支管理页既有筛选参数 `platforms` / `repoUrlLike` / `branchNameLike`（`QueryProjectBranchDTO` 既有字段，不新增参数、不新开接口），URL 形如 `/apps/repos?projectId=<项目ID>&platforms=<平台>&repoUrlLike=<owner/repo>&branchNameLike=<分支>`；为弥合 LIKE 模糊筛选与"精确定位"的语义差，分支列表排序首位增加"精确命中优先"（repo_url 精确片段 + branch_name 精确的行排最前），链接落地首屏第一位即目标分支；废弃原 `repoId` + `branchNameExact` 直达方案（不新增 `QueryRepoDTO` 字段）。
13. **保留 AK/SK 模式（本次不移除）**：OIDC 与 AK/SK 双模式并存，AK/SK 的旧网关路径与静态凭证输入项（`apig-app-key`/`apig-app-secret`/`obs-ak`/`obs-sk`）全部保留（部分测试仓不适合纳入 OIDC 认证凭据授权项目）；本次仅做输出链路改造，不触碰鉴权与上报路径。
14. **链接仅以 `ATOMGIT_OUTPUT` 单通道输出**：插件输出 `key=value` 概览行（链接行 key `扫描结果url`——末尾小写 `url` 触发平台渲染可点击；供 `steps.<id>.outputs.<name>` 机器消费、兼容既有消费方）；原 `ATOMGIT_STEP_SUMMARY`（Markdown 超链接，显示文本≠实际链接）通道已移除，收敛为单通道，避免同一链接在运行摘要与任务结果两处分别呈现、展示形态不可由插件统一控制。链接不携带平台授权参数（联调后定稿，commit `ed41c4a4`）。
15. **前端为协同方（不随本需求提业务 PR）**："无 metricType 链接落地"能力由前端侧承载（链接落地契约见 2.3 节），本需求仅服务端与插件提 PR；beta 端到端已验证点击落地效果（三筛选自动应用 + 精确命中置顶）。

## 2. 实现逻辑设计

### 2.1 服务端（openlibing-coderepo）

**A. 上报响应链接构建** —— `CodeMetricsService#buildReportVO(gitUrl, branchName)`，四态：

1. **项目解析（取查询第一行）**：`RepoUrlUtil.normalize(gitUrl)` → `repoInfoMapper.selectByRepoUrl(normalized)`（跨项目、`is_deleted=0`，既有排序 `order by create_at desc, repo_id desc`，取**第一行**作为本次唯一跳转项目）；为空且未带 `.git` 时补 `.git` 重试（与 `UtCoverageServiceImpl#findRepoByUrl` 一致）。仍为空 → **状态③**（仓未录入 tip）。
2. **分支登记校验 + 单条链接生成**：仅取第一行 `(repoId, projectId, platform)`，`repoBranchInfoMapper.queryBranch(repoId, null, branchName, "1", null)` 判非空（精确等值 + 已登记）→ 已登记即生成唯一 1 条链接（ownerRepo 经类内既有 `extractOwnerRepo(gitUrl)` 提取；不再查询项目名称，响应不含项目名称）：
   `url = openlibingDomain + "/apps/repos?projectId=" + projectId + "&platforms=" + urlEncode(platform) + "&repoUrlLike=" + urlEncode(ownerRepo) + "&branchNameLike=" + urlEncode(branchName)`
   赋值给 `detailLink`；`ownerRepo` / `branchName` 按 UTF-8 做 query 参数编码（含 `/` 等特殊字符，未编码会破坏 URL 结构）；`platform` 取自第一行 `repo_info.platform`（与分支管理页 `platforms` 筛选值域一致，gitcode/gitee），非 gitcode/gitee 时省略 `platforms` 参数（其余参数仍可正常落地）。
   - 第一行项目该分支已登记 → **状态①**（单条链接）；
   - 第一行项目该分支未登记 → **状态②**（分支未登记 tip，不回退其他项目）。
3. **异常兜底**：方法体整体 try-catch（最后防御性捕获 `Exception`，覆盖 DB 访问异常等运行时类型），异常 → **状态④**：空 `detailLink` + 空 `tip` + `logger.warn`（记录 gitUrl 与异常摘要），不误报"未录入"。

四态汇总：

| 状态                | 条件                                     | detailLink | tip              |
| ------------------- | ---------------------------------------- | ---------- | ---------------- |
| ① 命中 + 分支已登记 | repo_info 命中，且第一个项目该分支已登记 | 单条链接   | 空               |
| ② 分支未登记        | repo_info 命中，但第一个项目该分支未登记 | 空         | 分支未录入提示   |
| ③ 仓未录入          | repo_info 未命中（含 `.git` 重试后）     | 空         | 仓未录入提示     |
| ④ 异常/不可构造     | 查询/拼接异常                            | 空         | 空（仅告警日志） |

**B. Controller**：`reportMetrics` 返回类型 `DataResult<String>` → `DataResult<CodeMetricsReportVO>`，`publishToMq` 投递成功后组装 VO（message 语义不变）。不新增接口。

**C. 分支列表"精确命中置顶"（供链接落地）**：`RepoBranchInfoMapper.xml` 的 `projectBranchOrderBy` 片段在既有排序前**前置两段 CASE WHEN**，保证"代码仓 + 分支均精确命中"的行排在所有结果第一位（弥合 `repoUrlLike`/`branchNameLike` LIKE 模糊筛选与精确定位的语义差）：

- `repoUrlLike` 非空时：`case when r.repo_url like concat('%/', #{repoUrlLike}) or r.repo_url like concat('%/', #{repoUrlLike}, '.git') then 0 else 1 end`（以 `/` 前缀锚定 owner/repo 段，兼容 repo_url 含/不含 `.git`）；
- `branchNameLike` 非空时：`case when b.branch_name = #{branchNameLike} then 0 else 1 end`（等值同为最前）；
- 参数为空时对应 CASE 段不参与排序（保持既有条件表达式不变），既有排序（`r.repo_url` / `b.update_at` + `branch_id desc`）作为次级排序不变；`countProjectBranch` 无排序不受影响，list/count 口径天然一致。
  链接落地复用分支管理页既有筛选接口 `POST /repo/branch/list`（`QueryProjectBranchDTO` 的 `platforms` / `repoUrlLike` / `branchNameLike` 既有字段，不新增参数、不新增接口）。

### 2.2 插件侧（code-metrics-action）

1. **`dist/uploaders/CoderepoUploader.js#report`**：业务成功后新增 `detailLink` / `tip` 解析（`resData?.data?.detailLink` 为非空字符串时透传，否则为空；`tip` 按字符串透传），返回 `{ success, recordId, detailLink, tip }`；原有兼容分支与 `code !== 200` 判定保留。
2. **`CoderepoUploader#upload`**：上报成功返回 `{ success: true, recordId, obsUrl, detailLink, tip }`（失败路径不变，仍返回 obsUrl 保底提示）。
3. **`dist/scanner.js`**：上报成功后 `result.uploadInfo = { success: true, obsUrl, detailLink, tip }`。
4. **`dist/index.js`** 入口：在现有 5 项指标概览输出之后**单通道追加**链接/提示行：
   - **ATOMGIT_OUTPUT**：输出 key=value 纯值行（供 `steps.<id>.outputs.<name>` 取值、兼容既有消费方），链接行 key 末尾为小写 `url`（平台据此将值渲染为可点击链接、大小写敏感；提示行 key 不带 `url` 后缀，避免提示文本被渲染成无效链接）：

| 场景                          | 输出键        | 值                                  |
| ----------------------------- | ------------- | ----------------------------------- |
| detailLink 非空               | `扫描结果url` | 链接                                |
| 无链接且 tip 非空             | `扫描结果`    | 提示文案                            |
| 无链接且 tip 为空（异常场景） | —             | 不输出，仅 `core.info` 记录便于排查 |

- `detailLink` 非空即输出链接行、tip 非空即输出提示行（二者互斥，服务端保证）；链接/提示均 `core.info` 打印；检查 `ATOMGIT_OUTPUT` 环境变量，缺失时跳过输出；写入失败沿用现有 `core.warning` 兜底。

5. **鉴权模式保持不变（AK/SK 保留）**：OIDC 与 AK/SK 双模式并存，本次不触及 `CoderepoUploader` 的鉴权分支、`ApigSigner`、旧网关路径、`action.yml` 输入项（`apig-app-key`/`apig-app-secret`/`obs-ak`/`obs-sk`）与凭证透传逻辑；输出链路改造与鉴权模式正交（两种模式下均正常输出链接/提示）。
6. **bundle 双写**：`dist/index.js` 为 ncc 打包产物，内联了 `scanner.js` / `CoderepoUploader.js` 副本；改动需同步内联副本，或按仓内既有构建方式（`npm run build`）重新打包，保持分发物单文件。
7. **README**：输出章节补充链接说明（`ATOMGIT_OUTPUT` 链接行/提示行）与两类提示说明及示例。

### 2.3 前端（openlibing-web，前端侧协同，不随本需求提 PR）

> 本节为链接落地契约与前端侧协同事项：前端代码交付由前端团队负责，本需求不产生前端业务 PR；落地效果已随 beta 端到端验证覆盖。

1. **`views/Repos/index.vue#autoGoBranch`**：
   - route query 含 `metricType` → 保持现状（定位仓库后打开指标详情弹窗，兼容旧链接与其他入口）；
   - 不含 `metricType`（新链接形态，链接不含 pipelineRunId）→ 切换到分支 Tab，透传三筛选参数（`platforms` / `repoUrlLike` / `branchNameLike`）至分支页自动应用（精确命中行置顶，首屏第一位即目标分支），页面数据恒为该分支最新指标；**不打开指标弹窗**；同步清理该函数中 `route.query.pipelineRunId` 的读取与向下传递（弹窗自身改由服务端按最新记录回填）。
2. **`views/Repos/branches.vue`**：
   - `initialFilter` 扩展支持 `platforms` / `repoUrlLike` / `branchNameLike` 三参数（URL 直达自动应用，与筛选栏既有筛选项共用同一套参数，不新增筛选维度）；
   - 指标列说明气泡（既有 `el-tooltip`）补充数据口径提示：「指标数据均取自该分支最新一次成功检测结果，非历史流水线运行数据。」
3. **`views/Repos/dialog/MetricsDetailDialog.vue`**：按原"`file-detail` 撤参"方案移除 `pipelineRunId` prop 与 `fetchData` 传参（见决策 2 与 2.3 备注：服务端已恢复可选入参，该清理非必需，前端可按需保留传参）；`runNumber` / `pipelineLink` 与 `DuplicationCodeDrawer` 仍取响应回填值，组件链路不变。

页面数据口径恒为"最新"：刷新/回退/重新筛选后视图语义稳定；异步导入进行中时页面提示文案由前端侧更新（提示稍等同步完成后刷新）。

> 备注：服务端 `file-detail` 的 `pipelineRunId` 已恢复为**可选**入参（见 1.4 决策 2）。前端侧此前为适配"撤参"所做的清理（移除弹窗 `pipelineRunId` prop / 清理 `route.query.pipelineRunId` 传递）**非必需**，前端可按需保留或回传，服务端对"传/不传"两种调用均兼容（传则按指定记录定位、不传取最新）。

### 2.4 边界与降级

| 场景                                                      | 行为                                                                                                                                            |
| --------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 未匹配到项目（repo_info 无关联行）                        | 空 detailLink + 仓未录入 tip → 插件输出提示行、不输出链接；上报受理结果不受影响                                                                 |
| 命中项目但分支未登记                                      | 空 detailLink + 分支未登记 tip → 插件输出提示行、不输出链接                                                                                     |
| 分支刚创建未同步到平台（登记表未同步）                    | 登记校验不过 → 分支未登记 tip（引导联系 SRE 同步分支）                                                                                          |
| 同一 repoUrl 多个项目                                     | 仅取查询第一个项目（`selectByRepoUrl` 排序：录入时间倒序第一行）生成 1 条链接；第一个项目该分支未登记时输出分支提示，不回退其他项目             |
| 无 metricType 链接落地                                    | 前端按分支管理页筛选条件（platforms/repoUrlLike/branchNameLike）落地，精确命中行置顶（首屏第一位为目标分支），展示该分支最新指标数据            |
| 携带 pipelineRunId 调用 file-detail（前端弹窗按记录下钻） | 服务端按 (git_url, branch_name, pipeline_run_id) 精确返回该次记录；不传则按 (git_url, branch_name, status=0) 返回最新成功记录，两种调用均不报错 |
| repo_info / 登记校验 / 拼接异常                           | 兜底捕获 → 空 detailLink、空 tip（仅告警，不误报"未录入"）；响应仍为"上报已受理"                                                                |
| 上报失败（HTTP/业务失败/投递失败）                        | 不输出链接（现有失败提示与 OBS 保底提示不变）                                                                                                   |
| 新插件 + 老服务端（无 detailLink/tip）                    | 解析为空 → 不输出链接/提示，其余行为不变                                                                                                        |
| 老插件 + 新服务端（data 由 null 变对象）                  | 老插件仅判 `code`/`msg`，不读取 data → 行为不变                                                                                                 |
| 鉴权模式（OIDC / AK/SK）                                  | 双模式并存、本次不变（AK/SK 模式保留，部分测试仓不适合纳入 OIDC 凭据授权项目）；两种模式下均正常输出链接/提示                                   |
| 异步导入尚未完成时点击链接                                | 分支页展示最新已入库数据（导入完成后刷新可见，数据链路既有行为）；页面提示文案由前端侧更新（提示稍等同步完成后刷新）                            |
| branchName 含 `/` 等特殊字符                              | 服务端 URL 编码后拼接（`repoUrlLike` / `branchNameLike` 同）；前端 router 解析 query 自动还原                                                   |
| 相近分支名（main 与 main-2）                              | 精确命中优先排序保证 `main` 行排在 `main-2` 之前，链接落地首屏第一位即目标分支                                                                  |
| 无 `ATOMGIT_OUTPUT` 环境变量                              | 跳过输出（仅 `core.info` 打印实际链接），不影响上报受理结果                                                                                     |

## 3. 类设计

### 3.1 服务端（Java，openlibing-coderepo）

| 类/文件                                              | 操作 | 说明                                                                                                                                                                                                                                                                                                                                                                                                                     |
| ---------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `business/controller/CodeMetricsController.java`     | 修改 | `reportMetrics` 返回类型改 `DataResult<CodeMetricsReportVO>`；不新增接口                                                                                                                                                                                                                                                                                                                                                 |
| `business/service/CodeMetricsService.java`           | 修改 | 新增 `buildReportVO(gitUrl, branchName)` 声明                                                                                                                                                                                                                                                                                                                                                                            |
| `business/service/impl/CodeMetricsServiceImpl.java`  | 修改 | 实现 `buildReportVO`（四态：项目解析（取查询第一行）+ 第一行项目分支登记校验 + 单条链接拼接（platforms 可选）+ 两类 tip + 异常兜底）；`getFileMetricDetail` 抽出 `locateMetricsRecord`：传 `pipelineRunId` 走 `selectByPipelineRunId` 精确查该次记录、不传走 `selectLatestByGitAndBranch` 取该分支最新记录（`pipelineLink` / `pipelineRunId` 均取 `record` 字段）；`@Value("${openlibing.domain}")` 注入既有平台域名配置 |
| `common/utils/RepoUrlUtil.java`                      | 修改 | 新增静态 `normalize(String url)`（去空白、去末尾 `.git`）                                                                                                                                                                                                                                                                                                                                                                |
| `business/service/impl/UtCoverageServiceImpl.java`   | 修改 | `normalizeGitUrl` 改为委托 `RepoUrlUtil.normalize`（行为不变）                                                                                                                                                                                                                                                                                                                                                           |
| `business/vo/CodeMetricsReportVO.java`               | 新增 | `String detailLink`（固定单条链接，多项目取查询第一个项目；未登记/异常时为空）+ `String tip`（两类提示，可空）                                                                                                                                                                                                                                                                                                           |
| `business/dto/metrics/FileMetricDetailQueryDTO.java` | 修改 | `pipelineRunId` 改为可选入参（不设 `@NotBlank`）：传则精确定位该次记录，不传取该分支最新成功记录                                                                                                                                                                                                                                                                                                                         |
| `business/mapper/CodeMetricsRecordMapper(.xml)`      | 修改 | 新增 `selectLatestByGitAndBranch(gitUrl, branchName)`（镜像 `CodeUtRecordMapper` 既有同名方法：`status=0 ORDER BY detection_completed_at DESC, id DESC LIMIT 1`）；既有 `selectByPipelineRunId` **保留**（file-detail 传 pipelineRunId 时复用，另 3 处调用：上报幂等清理、file-content 接口、duplication-block-detail 接口）                                                                                             |
| `business/mapper/RepoBranchInfoMapper(.xml)`         | 修改 | `projectBranchOrderBy` 前置"精确命中优先"CASE WHEN（`repoUrlLike` 精确片段 + `branchNameLike` 等值，供链接落地首屏置顶）；登记校验复用既有 `queryBranch`（不新增方法）                                                                                                                                                                                                                                                   |

> `RepoInfoMapper` 复用既有 `selectByRepoUrl`（跨项目解析，取查询第一行）；响应不再返回项目名称，不再需要 `ProjectInfoMapper#queryById`，均不新增 Mapper 方法。

### 3.2 插件侧（Node.js，code-metrics-action）

| 文件                                 | 操作 | 说明                                                                                                                          |
| ------------------------------------ | ---- | ----------------------------------------------------------------------------------------------------------------------------- |
| `dist/uploaders/CoderepoUploader.js` | 修改 | `report` 解析 detailLink/tip；`upload` 成功透传；鉴权分支、`ApigSigner`、旧网关路径等 AK/SK 逻辑全部保留不动                  |
| `dist/scanner.js`                    | 修改 | `uploadInfo` 携带 detailLink/tip；凭证参数透传逻辑保留不动                                                                    |
| `dist/index.js`                      | 修改 | 输出改单通道：`ATOMGIT_OUTPUT` 保留 key=value 概览行（detailLink 非空 1 行链接 / tip 提示行）；`core.info` 打印；同步内联副本 |
| `action.yml`                         | 不改 | `apig-app-key` / `apig-app-secret` / `obs-ak` / `obs-sk` 输入项保留（AK/SK 模式保留）                                         |
| `README.md`                          | 修改 | 输出章节补充链接（单通道）与两类提示说明及示例                                                                                |

### 3.3 前端（openlibing-web，前端侧协同，不随本需求提 PR）

| 文件                                                                 | 操作 | 说明                                                                                                                                                                  |
| -------------------------------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `apps/web-openlibing/src/views/Repos/index.vue`                      | 修改 | `autoGoBranch` 支持无 metricType 落地（分支 Tab + 三筛选参数透传，不打开弹窗）；清理 `route.query.pipelineRunId` 读取与传递                                           |
| `apps/web-openlibing/src/views/Repos/branches.vue`                   | 修改 | `initialFilter` 支持 `platforms` / `repoUrlLike` / `branchNameLike` 三参数（与筛选栏同套字段）；指标列说明气泡补数据口径文案                                          |
| `apps/web-openlibing/src/views/Repos/dialog/MetricsDetailDialog.vue` | 修改 | 原按"撤参"方案移除 `pipelineRunId` prop 与 `fetchData` 传参（服务端恢复可选入参后非必需）；`runNumber` / `pipelineLink` 与 `DuplicationCodeDrawer` 传参改取响应回填值 |

## 4. 数据模型设计

**数据库**：无表结构变更。新增/变更只读查询：`repo_info`（复用 `selectByRepoUrl` 跨项目解析，取第一行；新增使用 `platform` 列）、`repo_branch`（复用 `queryBranch` 做登记校验；`projectBranchOrderBy` 前置"精确命中优先"排序供链接落地）、`code_metrics_record`（新增 `selectLatestByGitAndBranch` 按分支取最新成功记录，供 `file-detail` 未传 pipelineRunId 时下钻）。无新增索引、无迁移 SQL、无存量数据迁移。

**上报响应模型（DataResult\<T\>）**：

改造前：

```json
{ "code": 200, "msg": "上报已受理，正在异步导入", "data": null }
```

改造后（固定单条链接，多项目时取查询第一个项目）：

```json
{
  "code": 200,
  "msg": "上报已受理，正在异步导入",
  "data": {
    "detailLink": "<openlibing.domain>/apps/repos?projectId=3&platforms=gitcode&repoUrlLike=openlibing/openlibing-coderepo&branchNameLike=master",
    "tip": ""
  }
}
```

字段说明：

| 字段         | 类型   | 说明                                                                                                                                                                                                                                                                                      |
| ------------ | ------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `detailLink` | String | 固定单条完整平台链接（多项目取查询第一个项目；未登记/异常场景为空）；链接含 projectId/platforms/repoUrlLike/branchNameLike 参数（与分支管理页筛选条件一致；platform 非 gitcode/gitee 时省略 platforms），repoUrlLike/branchNameLike 已 URL 编码，不含 metricType、repoId 与 pipelineRunId |
| `tip`        | String | 提示文案（服务端单点定义，插件不硬编码）：仓未录入 / 分支未登记两类；命中且已生成链接或异常场景为空                                                                                                                                                                                       |

分支未登记示例：

```json
{
  "code": 200,
  "msg": "上报已受理，正在异步导入",
  "data": {
    "detailLink": null,
    "tip": "当前分支未录入openLiBing平台，请前往openLiBing平台同步最新分支"
  }
}
```

## 5. 性能设计

- 上报接口新增：1 次（最多 2 次，含 `.git` 兜底重试）`repo_info` 等值查询 + 1 次分支登记查询（仅第一个项目）；链接拼接为 O(1)，无跨服务调用、无额外 IO。
- 链接构建与 MQ 投递串行（投递成功后执行），构建异常兜底，不影响响应时延量级与投递结果。
- 分支列表排序增强：`projectBranchOrderBy` 前置两段 CASE WHEN（`repoUrlLike` / `branchNameLike` 非空时参与排序，复用既有查询参数，不新增过滤条件），分页 LIMIT 下排序开销可控；`countProjectBranch` 无排序不受影响。
- `file-detail` 取数两条路径均为索引等值 + `LIMIT 1`：未传 pipelineRunId 走新增 `selectLatestByGitAndBranch`（(git_url, branch_name, status) 等值 + 排序），传 pipelineRunId 走既有 `selectByPipelineRunId`（(git_url, branch_name, pipeline_run_id) 等值），性能量级不变。
- 插件侧新增开销：字符串处理 + 1 次 `appendFileSync`（`ATOMGIT_OUTPUT`），可忽略；输出行数固定为 1（链接行或提示行）。
- 前端：无新增请求（落地仅复用既有分支查询接口的既有筛选参数与既有分支列表/弹窗组件）。

## 6. API接口设计

| 项                                         | 说明                                                                                                                                                                                                                                                                                                                                    |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 上报接口                                   | 路径不变：`/metrics/code/report`；鉴权路径不变（OIDC `/action-api/...` 与 AK/SK 旧网关路径并存）；入参不变（`CodeMetricsReportDTO`）；出参 `DataResult<String>` → `DataResult<CodeMetricsReportVO>`（见第 4 节）；成功 message 与失败语义不变                                                                                           |
| `file-detail` 接口（pipelineRunId 可选）   | `POST /metrics/code/file-detail`：`FileMetricDetailQueryDTO` 的 `pipelineRunId` 为可选入参（不设必填校验）；传则按 (git_url, branch_name, pipeline_run_id) 精确返回该次历史记录，不传则按 (git_url, branch_name, status=0) 取该分支最新成功记录；出参 `FileMetricDetailVO` 的 pipelineRunId/runNumber/pipelineLink 均取自命中的该条记录 |
| 分支列表接口（排序增强，链接落地面）       | `POST /repo/branch/list`（`queryProjectBranch`）：`QueryProjectBranchDTO` 的 `platforms` / `repoUrlLike` / `branchNameLike` 既有字段不新增不改动；`projectBranchOrderBy` 前置"精确命中优先"排序（repo_url 精确片段 + branch_name 等值置顶）                                                                                             |
| 鉴权                                       | 维持现状：OIDC 联邦认证（`callApig` 签名 + OBS `getCredentials()` STS）与 AK/SK 旧网关（`ApigSigner` + 静态凭证）双模式并存，本次不改变插件鉴权模式                                                                                                                                                                                     |
| 前端链接契约（分支管理页落地，前端侧协同） | `/apps/repos?projectId=<项目ID>&platforms=<平台>&repoUrlLike=<owner/repo>&branchNameLike=<分支>`；无 `metricType` → 分支 Tab + 三筛选条件落地（精确命中行置顶，不打开弹窗），展示该分支最新指标数据（链接不含 pipelineRunId）；带 `metricType` → 兼容旧行为打开指标弹窗                                                                 |

不新增其他接口（记录列表接口不建，见 1.4 决策 3）。

## 7. 安全设计

- **无新增凭证与敏感数据**：链接不含 token、不携带平台授权参数，打开时沿用平台既有登录态与页面鉴权；响应仅暴露 projectId/平台标识等非敏感标识（不含项目名称）。
- **权限校验**：分支列表接口沿用既有 `UrlConstant.REPO_BRANCH_QUERY` 权限与横向越权校验（`verifyPermissionsByProduct`）；`file-detail` 沿用既有 `METRICS_FILE_DETAIL` 权限校验；上报接口鉴权维持现状（OIDC / AK/SK 双模式）。
- **SQL 安全**：全部新增/扩展查询使用参数化（`#{}`），无拼接；登记校验为等值匹配；排序 CASE WHEN 中的 `repoUrlLike` / `branchNameLike` 同样参数化绑定。
- **URL 构造安全**：`ownerRepo` / `branchName` 为外部来源（仓地址与上报入参，可能含特殊字符），按 UTF-8 做 query 参数编码，防止参数截断/注入；其余部分为固定模板 + 数字。
- **异常兜底**：日志仅记录 gitUrl 与异常摘要，不打印请求体等数据；异常不阻断上报受理结果。
- **依赖安全**：无新增依赖（服务端复用现有 Mapper/配置；插件零新增依赖）。
- **鉴权模式不变**：保留 AK/SK 与 OIDC 双模式（部分测试仓不适合纳入 OIDC 认证凭据授权项目）；本次不新增、不移除任何凭证输入，凭证面与现状一致。

## 8. 需求设计检查清单对照（requirement-design-check）

**适用条目**：

- 第 2 条（二级页面链接直达）：链接落地分支管理页（URL 可寻址），复用分支管理页既有筛选参数（`platforms` / `repoUrlLike` / `branchNameLike`，与筛选栏同套字段），链接可分享、可刷新；为弥合 LIKE 模糊筛选与精确定位的语义差，列表排序增加"精确命中优先"（repo_url 精确片段 + branch_name 等值置顶），链接落地首屏第一位即目标分支；刷新/回退/分享后视图稳定（口径恒为"最新"）。
- 第 3 条（ID 接口传递用字符串）：projectId 为 int 量级（`Integer`），JSON 数值安全；URL 与接口参数均以字符串承载，无雪花 ID 场景；URL 参数值（owner/repo、分支名、平台）均经 URL 编码。
- 第 5 条（可扩展性）：`detailLink` 为固定单条链接（多项目取查询第一个项目，输出形态恒定、不随项目数变化），指标维度已从链接剥离（指标扩展不新增链接）；链接参数复用既有筛选字段（分支页筛选能力扩展无需改造链接协议）；后续如需多链接可再扩展字段（当前无此需求）；指标数值与分支页同一来源（既有解析逻辑），前端列映射复用。
- 第 6 条（接口精简与复用，"新增接口前三问"）：① 上报接口——可扩展现有接口，不新开；② 分支列表接口——链接落地复用既有筛选参数（三字段均既有，零新增）+"精确命中优先"排序增强，不新开接口、不新增参数；③ `file-detail` 接口——`pipelineRunId` 可选化（传则精确定位该次记录、不传取该分支最新成功记录），不新开接口；④ 记录列表接口——不建（无当前确定调用方，页面恒为"最新"口径）；⑤ 分支登记校验复用既有 `queryBranch`，`file-detail` 新查询镜像既有 `CodeUtRecordMapper#selectLatestByGitAndBranch` 实现（无新查询模式）。
- 第 7 条（筛选口径与展示口径一致）：链接落地筛选维度（platforms + repoUrlLike + branchNameLike）即页面展示维度（分支管理页筛选栏同套字段）；页面展示口径为"最新成功检测结果"，与既有分支管理页取数口径（`status=0` 逐指标最新）一致，`file-detail` 在链接入口路径上按"该分支最新"回填（传 pipelineRunId 时按指定记录），并由指标说明气泡明示。
- 第 8 条（列表口径=统计口径）：排序增强不改变 `projectBranchWhere` 过滤口径，list（`queryProjectBranchByLimit`）与 count（`countProjectBranch`）共用同一 WHERE 片段，口径天然一致（count 无排序、不受 CASE WHEN 影响）；单测断言三筛选条件下 list 与 count 口径一致。
- 第 10 条（大小写归一化）：gitUrl 匹配复用 `selectByRepoUrl` 既有口径 + `RepoUrlUtil.normalize`（trim、去 `.git`），与上报/分支页取数口径一致。
- 第 16 条（重复逻辑下沉单一来源）：URL 归一化下沉 `RepoUrlUtil`（UtCoverage 委托复用）；平台地址复用既有 `openlibing.domain`（不新增配置项与第二份域名定义）；链接参数与分支管理页筛选条件复用同一套字段（不发明第二套定位协议）；两类 tip 文案服务端单点定义（插件不硬编码）；指标明细弹窗前端复用 `MetricsDetailDialog`。

**不适用条目**：

- 第 1 条（筛选能力分级）：本次未新增用户可操作筛选项（三筛选参数均为筛选栏既有能力，URL 直达仅自动带入筛选值，不新增筛选维度、不改筛选交互；无新增列表型入口）。
- 第 4 / 17 / 18 条（分页与分页参数校验）：不新增分页接口（记录列表接口不建），不涉及。
- 第 9 条（跨入口能力一致性）：无"同类查询多入口"场景。
- 第 11 条（时间区间格式校验）、第 12/13/14/15/19 条：无表结构/索引变更、无后端管理字段新增、无新增持久化字段与存量迁移、无数据变更与批量操作。

## 风险 & 缓解

| #   | 风险                                                                        | 缓解                                                                                                                                                                                                 |
| --- | --------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| R1  | repoUrl 格式差异（含/不含 `.git`、跨区域域名）导致解析不到项目              | 归一化 + 补 `.git` 重试；仍未命中返回仓未录入 tip（引导联系 SRE 完成代码仓录入），上报受理不受影响                                                                                                   |
| R2  | 分支登记表由同步任务维护（每日 12/24 点 + 手动同步），新分支可能未及时登记  | 登记校验不通过时输出分支未录入 tip（引导联系 SRE 同步/录入分支）；上报受理不受影响，影响仅为"暂无链接"                                                                                               |
| R3  | 异步导入未完成时点击链接，本次运行数据暂不可见                              | 分支页展示最新已入库数据（导入完成后刷新可见，数据链路既有行为，交付说明中明确）                                                                                                                     |
| R4  | 响应 data 由 null 变对象影响存量插件                                        | 老插件仅判 `code`/`msg`，兼容；上线前用存量插件版本回归一次上报                                                                                                                                      |
| R5  | `repoUrlLike` / `branchNameLike` 含 `/` 等特殊字符破坏 URL                  | 服务端对参数值做 UTF-8 query 编码；前端 router 自动解码还原                                                                                                                                          |
| R6  | 多项目时仅取第一个项目，可能非用户期望的项目                                | 按 `selectByRepoUrl` 既有排序（录入时间倒序）取第一行，行为确定可预期；第一个项目未登记该分支时输出分支 tip；交付说明写明                                                                            |
| R7  | 配置中心未下发 `openlibing.domain` 导致注入失败                             | 该属性为既有标准配置（coderepo `RepoServiceImpl`、cicd 均在使用），各环境已配置；上线前在 beta/gama/prod 各验证一次链接域名正确性                                                                    |
| R8  | `file-detail` 的 `pipelineRunId` 可选化后，未传参数的调用需稳定回落最新记录 | 传 `pipelineRunId` 走 `selectByPipelineRunId` 精确命中该次记录、不传走 `selectLatestByGitAndBranch` 返回分支最新成功记录（均不报错、不缺字段）；上线前回归「传参精确命中」与「不传回落最新」两条路径 |
| R9  | 无 metricType 链接的落地能力依赖前端侧支持（前端为协同方，不随本需求提 PR） | 落地契约已与前端侧对齐（见 2.3 节）；beta 端到端已验证点击落地（三筛选自动应用 + 精确命中置顶）                                                                                                      |
| R10 | 用户期望看到"本次运行"数据，但页面为"最新"口径                              | 链接不携带本次运行标识、页面恒为最新口径；指标说明气泡声明数据口径（最新成功检测结果，非历史运行数据）；交付说明写明                                                                                 |

## 跨仓影响

- **openlibing-coderepo**：上报响应结构变化（出参新增 detailLink/tip）+ 分支列表排序增强（精确命中置顶，既有筛选参数复用）+ `file-detail` 的 `pipelineRunId` 可选化（传则精确命中该次记录、不传按分支最新记录返回）；平台域名复用既有配置 `openlibing.domain`（不新增配置项、无 yaml 变更）；`UtCoverageServiceImpl` 归一化方法委托重构（行为不变）。
- **code-metrics-action**：输出规则改造（单通道 `ATOMGIT_OUTPUT`：固定 1 行链接 / 提示行）与响应解析扩展，分发物（dist）更新；鉴权模式不变（AK/SK 保留）。
- **openlibing-web（前端侧协同，不随本需求提 PR）**：链接落地契约（三筛选参数透传 + 分支页自动应用 + 指标说明气泡口径 + 异步导入窗口提示文案）已与前端侧对齐；前端代码交付由前端团队负责。
- 无数据库表结构变更、无新增接口、无新增依赖。
