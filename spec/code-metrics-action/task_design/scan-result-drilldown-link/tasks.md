# 【openLiBing】代码度量扫描插件结果输出增加openLiBing平台扫描结果链接 — 实现任务

- **业务 Issue**：https://gitcode.com/openlibing/code-metrics-action/issues/25

## 进度: 21/21 complete

## 服务端（openlibing-coderepo）

- [x] T1：`RepoUrlUtil` 新增静态 `normalize`（trim + 去末尾 `.git`），`UtCoverageServiceImpl#normalizeGitUrl` 改为委托调用（行为不变，消除重复实现）
- [x] T2：新增 `business/vo/CodeMetricsReportVO`（`String detailLink`（固定单条链接，多项目取查询第一个项目）+ `String tip`）
- [x] T3：`CodeMetricsService` 声明 `buildReportVO(gitUrl, branchName)`；Impl 实现四态：`normalize` + `selectByRepoUrl`（空则补 `.git` 重试）；命中取**第一行** `(repoId, projectId, platform)`（既有排序：录入时间倒序），复用 `RepoBranchInfoMapper#queryBranch(repoId, null, branchName, "1", null)` 校验该行登记 → 已登记即拼唯一 1 条链接赋值 `detailLink`（不再查询项目名称）；链接 URL 复用分支管理页筛选参数（`/apps/repos?projectId=&platforms=&repoUrlLike=&branchNameLike=`，ownerRepo 经类内既有 `extractOwnerRepo` 提取，platform 非 gitcode/gitee 时省略 platforms——联调后移除 codeHostingPlatformFlag，commit `ed41c4a4`；ownerRepo/branchName 做 UTF-8 query 编码）；仓未录入 → 仓提示；第一行项目分支未登记 → 分支提示（不回退其他项目）；查询/拼接异常兜底 → 空 detailLink + 空 tip（仅告警，不误报）
- [x] T4：`CodeMetricsServiceImpl` 以 `@Value("${openlibing.domain}")` 注入既有平台域名配置（不新增配置项、不硬编码公网域名；与 `RepoServiceImpl` 既有用法一致）
- [x] T5：`CodeMetricsController#reportMetrics` 返回类型 `DataResult<String>` → `DataResult<CodeMetricsReportVO>`，`publishToMq` 投递成功后组装 VO（`DataResult.success("上报已受理，正在异步导入", vo)`，message 语义不变），失败仍 `failureMessage`
- [x] T6：分支列表排序增强：`RepoBranchInfoMapper.xml#projectBranchOrderBy` 前置两段 CASE WHEN（`repoUrlLike` 非空 → repo_url 精确片段（兼容含/不含 `.git`）置前；`branchNameLike` 非空 → branch_name 等值置前；参数为空时该段不参与排序，既有排序作为次级不变）；`countProjectBranch` 无排序不受影响；`QueryProjectBranchDTO` 三筛选字段零改动
- [x] T7：`file-detail` 取数改造：`CodeMetricsRecordMapper(.xml)` 新增 `selectLatestByGitAndBranch(gitUrl, branchName)`（镜像 `CodeUtRecordMapper` 同名方法：`status=0 ORDER BY detection_completed_at DESC, id DESC LIMIT 1`）；`getFileMetricDetail` 抽出 `locateMetricsRecord`：未传 `pipelineRunId` 走新查询取分支最新成功记录、传则走既有 `selectByPipelineRunId` 精确查该次记录，`pipelineLink` / VO 的 `pipelineRunId` 统一取 `record` 字段；`selectByPipelineRunId` 保留（file-detail + 另 3 处：上报幂等清理、file-content、duplication-block-detail）
- [x] T8：单测/回归通过：`CodeMetricsServiceImplTest` 46/46（含 7 个 `buildReportVO` 四态用例；T23 恢复可选 pipelineRunId 后为 48/48）、`CodeMetricsControllerTest` 5/5、`CodeMetricsImportConsumerTest` 5/5；覆盖 `.git` 重试命中、ownerRepo/branchName 含 `/` 编码正确、platform 非 gitcode/gitee 省略 platforms、排序增强（精确命中置顶、相近分支名、list/count 口径一致）、`getFileMetricDetail` 取数分流（见 T23）

## 插件（code-metrics-action）

- [x] T9：`dist/uploaders/CoderepoUploader.js#report` 解析 `detailLink`（非空字符串时透传）/ `tip`（字符串），`upload` 成功后透传；`code !== 200` 判定保留
- [x] T10：`dist/scanner.js` 上报成功后 `uploadInfo` 携带 `detailLink` / `tip`
- [x] T11：`dist/index.js` 输出规则（文案定稿）：ATOMGIT_OUTPUT 保留 key=value 概览行（链接行 `扫描结果url`=链接——key 末尾小写 `url` 触发平台渲染为可点击链接；提示行 `扫描结果`=提示文案；均空不输出）；判环境变量、失败 `core.warning` 兜底；每条内容 `core.info` 打印（原 STEP_SUMMARY 通道见 T24）
- [x] T12：`dist/index.js` 内联副本同步（scanner + uploader + 输出规则），保持 bundle 单文件分发
- [x] T13：鉴权模式保持核实（不改动）：`ApigSigner`、`AKSK_API_PREFIX`、`useOidc`/`apigAppKey`/`apigAppSecret`/`obsAk`/`obsSk` 参数与分支、`action.yml` 四输入项（`apig-app-key`/`apig-app-secret`/`obs-ak`/`obs-sk`）、`getCredentials()` 与静态凭证分支全部保留；本次改造仅限输出链路
- [x] T14：README 输出章节补充链接（`ATOMGIT_OUTPUT` 链接行/提示行）与两类提示说明及示例
- [x] T15：冒烟测试通过（基于真实 bundle 的 vm 沙箱 7 场景）：AK/SK 链接、分支提示、均空不输出、上报失败不输出、缺 OUTPUT、OIDC 全链路

## 前端（openlibing-web，前端侧协同）

- [x] T16-T19（前端侧协同）：链接落地契约已与前端侧对齐（无 metricType 落地分支管理页并自动应用 platforms/repoUrlLike/branchNameLike 三筛选、精确命中行置顶、指标说明气泡口径）；异步导入进行中时的页面提示文案已由前端侧更新（提示稍等同步完成后刷新）；前端代码交付由前端团队负责，不随本需求提业务 PR

## 联调验证

- [x] T20：beta 环境端到端通过（用户确认）：真实流水线上报 → OUTPUT 链接输出 → 点击落地分支页三筛选 + 精确置顶 → 展示该分支最新指标数据（气泡口径提示由前端侧承载）
- [x] T21：边界场景验证通过：多项目取查询第一个项目（其分支未登记时输出分支提示、不回退其他项目）、仓未录入 / 分支未登记（两类提示行、不输出链接）、异步导入窗口（展示最新已入库数据，导入后刷新可见）、AK/SK 模式 workflow 上报正常
- [x] T22：兼容回归：存量插件版本 × 新服务端上报（老插件仅判 `code`/`msg`，不读取 data → 行为不变）；前端 × 新服务端（file-detail 传 pipelineRunId 按该次记录精确定位、不传按分支最新记录返回，两种调用均不报错）
- [x] T23：`file-detail` 恢复 `pipelineRunId` 为**可选**入参（补充交付）：`FileMetricDetailQueryDto` 新增 `pipelineRunId`（不设 `@NotBlank`）；`getFileMetricDetail` 经 `locateMetricsRecord` 分流（传则 `selectByPipelineRunId` 查该次历史记录、不传则 `selectLatestByGitAndBranch` 查最新）；`CodeMetricsServiceImplTest` 补 2 条用例（48/48）、pre-commit 全通过（openlibing-coderepo#234，分支 `restore-file-detail-pipeline-run-id` → `release_20261019_iter1`，commit `faa0351d`）
- [x] T24：输出通道收敛（需求决策变更）：移除 `ATOMGIT_STEP_SUMMARY` 通道（`stepSummaryLine` 常量与写入 try/catch、相关注释），仅保留 `ATOMGIT_OUTPUT`；README 同步改为单通道说明（commit `692b071`）

## 流程交付（Phase 4 / 5）

- [x] 业务 PR：openlibing/code-metrics-action#32（分支 `scan-result-drilldown-link` → master）、openlibing/openlibing-coderepo#215（分支 `scan-result-drilldown-link` → release_20261019_iter1）、openlibing/openlibing-coderepo#234（分支 `restore-file-detail-pipeline-run-id` → release_20261019_iter1，补充交付 T23）；均关联 Issue #25、打 `ai-assisted` 标签；前端侧协同（不随本需求提业务 PR）
- [x] 用户自测确认完成；本 spec 三件套 + 归档文档随 docs PR 提交（与安全编译选项插件文档同属本 FE，随同一 docs PR 归档）
