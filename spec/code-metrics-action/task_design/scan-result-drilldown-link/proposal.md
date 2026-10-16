# 【openLiBing】代码度量扫描插件结果输出增加openLiBing平台扫描结果链接

- **FE 需求**：【openLiBing】插件结果输出增加openLiBing平台扫描结果链接
- **业务 Issue**：https://gitcode.com/openlibing/code-metrics-action/issues/25
- **涉及仓库**：code-metrics-action（插件输出侧）、openlibing-coderepo（上报响应侧）、openlibing-web（链接落地侧，前端侧协同，不随本需求提 PR）
- **流程模式**：Full
- **日期**：2026-10-09

## 1. 需求背景

代码度量扫描插件在流水线中完成扫描并上报后，工作流概览（ATOMGIT_OUTPUT）只输出 5 项指标数值（代码规模、平均代码行数、平均圈复杂度、总代码重复率、总文件重复率）。用户无法直接进入 openLiBing 平台查看该仓库/分支的指标数据（按文件行数、函数行数、重复文件列表等），只能手工在平台中按仓库/分支/流水线反复翻找，使用成本高。

平台前端现状带来两个设计约束：

1. 指标详情弹窗依赖 metricType 且弹窗数据被 pipelineRunId 钉定：若按"每指标各一条链接"输出，5 类指标 → 5 条，未来指标扩展持续膨胀，用户困惑；
2. 分支管理页只展示"最新"数据，而插件输出链接指向"本次运行"：若直接以链接钉定历史数据，用户刷新/回退/重新筛选后历史视图丢失，产生"历史/最新"语义冲突。本次确定：**openlibing 前端页面永远只展示最新数据**——链接不携带 pipelineRunId，落地后只取当前分支最新指标数据，并在页面指标说明气泡中提示指标数据均为最新数据而非历史数据；不引入历史记录页面。

因此本次改造将链接收敛为**固定 1 条**（多项目时取查询第一个项目，只定位代码仓 + 分支，落地分支管理页外层），前端落地后永远展示最新数据 + 气泡声明口径；上报接口当前为异步受理模型，响应需扩展携带链接与提示（tip）。

## 2. 功能描述

1. **服务端（openlibing-coderepo）**：`/metrics/code/report` 上报响应由仅返回 message（`DataResult<String>`）改为 `message + detailLink + tip`：
   - 按上报 `gitUrl` 在 `repo_info` 解析关联项目（跨项目，含 repoId/projectId/platform），取查询第一个项目校验分支登记（`repo_branch`，精确匹配 + `has_branch='1'`），**已登记即返回固定 1 条链接**（URL 复用分支管理页筛选参数 projectId/platforms/repoUrlLike/branchNameLike，不含 metricType、repoId 与 pipelineRunId；多项目不返回多链接、不带项目名称；platform 非 gitcode/gitee 时省略 platforms）；
   - 分支未登记 → 返回分支提示（tip）；仓未录入 → 返回仓提示（tip）；查询/拼接异常 → 不返回链接也不返回提示（避免误报）；
   - 原 message 语义不变（"上报已受理，正在异步导入"），埋点/投递失败语义不变。
2. **插件（code-metrics-action）**：上报成功后解析 `detailLink` / `tip`，双通道输出：ATOMGIT_STEP_SUMMARY 追加 Markdown 超链接（`- [代码度量指标扫描结果](实际链接)`，显示文本与链接解耦）；ATOMGIT_OUTPUT 保留 key=value 概览行（链接行 `扫描结果url`=链接——key 末尾小写 `url` 触发平台渲染为可点击链接；提示行 `扫描结果`=提示文案）；提示非空且无链接时输出提示行（文案由服务端单点定义，插件不硬编码）；同步打印运行日志。上报失败时不输出链接（仅保留现有失败提示与 OBS 保底提示）。
3. **链接落地（前端侧协同，不随本需求提 PR）**：
   - 无 metricType 的链接落地分支管理页外层：自动应用分支管理页既有筛选条件（platforms / repoUrlLike / branchNameLike，与筛选栏同套字段；精确命中行置顶，首屏第一位即目标分支，不打开指标弹窗）；链接不携带 pipelineRunId，只取当前分支最新指标数据（页面永远只展示最新数据）；
   - 分支管理页指标说明气泡提示：指标数据均取自该分支最新一次成功检测结果，非历史流水线运行数据；
   - 异步导入进行中时的页面提示文案由前端侧更新，提示用户稍等同步完成后刷新页面；
   - 分支管理页布局与既有能力不变；不新增历史记录页面；前端侧代码交付由前端团队负责。
4. **插件鉴权模式保持不变**：OIDC 与 AK/SK 双模式并存（部分测试仓不适合纳入 OIDC 认证凭据授权项目），`apig-app-key` / `apig-app-secret` / `obs-ak` / `obs-sk` 输入项与旧网关路径全部保留，本次仅改造输出链路。

不涉及：

- 扫描/检测逻辑与 5 项指标口径、上报 payload 结构（OBS 全量文件 + 元数据）
- 数据库表结构变更
- 新增历史记录页面与记录列表接口
- 平台域名在插件侧的配置：链接由服务端拼接完整 URL 返回，插件不感知平台地址

## 3. 验收标准

- [ ] 上报成功后工作流运行摘要（ATOMGIT_STEP_SUMMARY）出现 Markdown 超链接、工作流概览（ATOMGIT_OUTPUT）出现对应 key=value 概览行（固定 1 条，多项目取查询第一个项目；显示文本≠实际链接）；点击落地分支管理页并自动应用 platforms/repoUrlLike/branchNameLike 三筛选条件（精确命中行置顶，不打开指标弹窗）
- [ ] 链接固定 1 条：不随项目数、指标数变化，指标扩展不增加链接行
- [ ] 无 metricType 链接落地（链接不含 pipelineRunId）展示该分支最新指标数据（非该次运行历史数据）；相近分支名（如 main 与 main-2）时目标分支精确结果排在第一位；刷新/回退/重新筛选后视图语义恒为"最新"
- [ ] 分支管理页指标说明气泡提示「指标数据均取自该分支最新一次成功检测结果，非历史流水线运行数据。」
- [ ] 分支未登记（查询第一个项目该分支未登记）不输出链接、输出提示「当前分支未录入openLiBing平台，请前往openLiBing平台同步最新分支」
- [ ] 未匹配到项目（repoUrl 在 repo_info 中无关联行）不输出链接、输出提示「当前仓未录入openLiBing平台，无法生成跳转链接，请先联系SRE完成代码仓录入。」，上报受理语义不受影响（仍返回"上报已受理"）
- [ ] 多项目场景仅取查询第一个项目：其分支未登记则输出分支提示（不回退其他项目）；异常场景（查询/拼接异常）不输出链接也不输出提示（不误报"未录入"）
- [ ] 上报失败时不输出任何链接；无 ATOMGIT_STEP_SUMMARY / ATOMGIT_OUTPUT 环境变量时跳过对应通道（互不影响）
- [ ] 插件鉴权模式保持现状（OIDC 与 AK/SK 双模式并存、`apig-app-key`/`apig-app-secret`/`obs-ak`/`obs-sk` 输入项保留）；file-detail 接口的 `pipelineRunId` 为**可选**入参：传则按 (git_url, branch_name, pipeline_run_id) 返回该次历史记录，不传则按 (git_url, branch_name, status=0) 返回该分支最新成功记录，两种调用均不报错
- [ ] 插件现有 5 项指标数值输出保持不变

## 4. 影响范围

- `openlibing/code-metrics-action`：`dist/index.js`（输出规则改造：STEP_SUMMARY Markdown 超链接 + ATOMGIT_OUTPUT 概览行双通道；固定 1 行链接/提示行）、`dist/scanner.js`（uploadInfo 携带 detailLink/tip）、`dist/uploaders/CoderepoUploader.js`（响应解析扩展；AK/SK 逻辑保留不动）、`action.yml`（不改）、README（输出章节双通道链接与提示说明）
- `openlibing/openlibing-coderepo`：`CodeMetricsController`（上报响应类型与组装）、`CodeMetricsService(+Impl)`（`buildReportVO` 四态；`getFileMetricDetail` 抽出 `locateMetricsRecord`，按 pipelineRunId 可选定位：传则精确查该次记录、不传取分支最新成功记录）、`RepoUrlUtil` 新增 URL 归一化（`UtCoverageServiceImpl` 委托复用）、`FileMetricDetailQueryDTO`（`pipelineRunId` 改为可选入参）、`CodeMetricsRecordMapper`（新增 `selectLatestByGitAndBranch`；`selectByPipelineRunId` 复用回 file-detail）、`RepoBranchInfoMapper.xml`（`projectBranchOrderBy` 精确命中置顶）、新增 VO（`CodeMetricsReportVO`，`detailLink` 单条链接 + tip）、平台域名复用既有配置 `openlibing.domain`（不新增配置项、无 yaml 变更）
- `openlibing/openlibing-web`（前端侧协同，不随本需求提 PR）：`views/Repos/index.vue`（`autoGoBranch` 无 metricType 落地：三筛选参数透传 + 清理 pipelineRunId 传递）、`views/Repos/branches.vue`（三筛选参数自动应用、指标说明气泡口径文案、异步导入窗口页面提示文案）、`views/Repos/dialog/MetricsDetailDialog.vue`（曾按「file-detail 撤参」移除 pipelineRunId prop 与传参；服务端恢复可选入参后该清理非必需，前端可按需保留传参）；落地能力与前端侧对齐（beta 端到端已验证）；异步导入窗口的页面提示文案已由前端侧更新
- 无数据库表结构变更、无新增接口、无新增依赖
