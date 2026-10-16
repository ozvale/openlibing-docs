# 分支管理代码度量展示增强与 atomgit 平台适配

## 需求背景

仓库管理（Repos）页面的分支管理列表与代码度量详情在使用中发现以下改进点：

1. 分支管理列表的 5 个代码度量指标列平铺展示，缺少归属分组，用户不清楚这些指标的含义与数据时效（数据为最新一次扫描结果）。
2. UT 行覆盖率列同样缺少说明文档入口。
3. 分支管理列表缺少「代码检查告警数」列，无法在分支维度直接看到静态检查告警规模，也不能从分支一键跳转到对应告警列表。
4. 分支管理筛选条件（代码托管平台/代码仓/分支名称）无法通过 URL 传达与恢复，跨页面跳转和刷新后筛选丢失，难以分享特定筛选视图。
5. 平台新增 atomgit.com 域名（与 gitcode.com 互为镜像、同属 GitCode 平台），前端的录入校验、平台识别、跳转白名单需要同步放行。
6. 代码度量详情摘要区缺少扫描时间，流水线仅显示 runNumber，无法区分不同流水线的扫描结果。

## 功能描述

### 1. 代码度量分组表头与说明文档（branches.vue）

- 5 个代码度量指标列合并到一级分组表头「代码度量」下，仅当任一度量列可见时展示
- 分组表头内容居中，一级与二级表头之间有可见分割线
- 表头带问号图标，悬浮 tooltip 说明「当前展示的指标数据为最新一次扫描结果」，tooltip 内含高亮「点击查看详细说明文档」链接，跳转 code-metrics-scan-solution 说明文档（`METRICS_DOC_URL`）
- 跳转使用页面统一跳转方法 `goToNotice`（信任域中转）
- UT 行覆盖率表头同样增加问号图标 + tooltip 内「点击查看说明文档」链接（`UT_COVERAGE_DOC_URL`）

### 2. 代码检查告警数列（branches.vue）

- 分支名称后新增「代码检查告警数」列（`staticAlertCount`），样式与仓库管理列表同名列一致
- 通过 knownColumns 列设置机制默认展示，存量用户自动合并（`knownColumnsBaseline` 追加新列）
- 列值可点击，跳转静态告警页并按当前分支过滤（搜索串 `branch:<分支名>` 限定符）
- 支持服务端排序（`sortable="custom"`，后端内存排序白名单已含 staticAlertCount）
- 空值显示 `--`

### 3. 分支管理筛选 URL 联动（branches.vue + index.vue）

- URL 同时携带 `platforms` / `repoUrlLike` / `branchNameLike` 三个参数时，自动切换到分支管理 tab 并还原对应筛选
- 筛选变化实时同步到 URL（`router.replace`，不产生历史记录）
- 刷新后保持当前 tab（sessionStorage）与筛选条件
- 仓库详情/度量详情等子页面跳转返回时保留筛选参数
- `applyingInitialFilter` 标志防止 URL 还原期间误触发筛选变化上报

### 4. atomgit 平台适配

- 仓库录入：URL 白名单放行 atomgit.com，平台识别为 gitcode（`getPlatform` 域名正则合并）
- `config.json` 新增 `ATOMGIT_BASE_URL` 常量
- 全局跳转白名单 `whiteLinks`（until.js）放行 atomgit
- 静态告警仓链接白名单 `ALLOWED_REPO_HOSTS`（staticAlarmRepoLink.ts）放行 atomgit.com / www.atomgit.com
- 全局配置弹窗同步源 URL 校验：gitcode 平台允许 atomgit.com / www.atomgit.com（`PLATFORM_ALLOWED_HOSTS`）
- SCA 开源合规分析表：atomgit 平台选项与仓库 URL 拼链映射

### 5. 度量详情摘要区增强（MetricsDetailDialog.vue）

- 「分支」后新增「扫描时间」字段（接口返回 `checkTime`）
- 流水线显示拼接流水线名称（接口返回 `pipelineName`）：有值展示 `pipelineName #runNumber`；为空或 null 只展示 `#runNumber`
- `pipelineLink` 存在时保持可点击跳转，仅展示文本变化

## 验收标准

- [ ] 分支管理列表出现居中的「代码度量」分组表头，与二级表头之间有分割线
- [ ] 问号 tooltip 显示最新扫描说明，说明文档链接高亮且跳转正确
- [ ] UT 行覆盖率表头问号 tooltip 内说明文档链接可跳转
- [ ] 「代码检查告警数」列默认展示，位于分支名称后
- [ ] 点击告警数跳转静态告警页且按当前分支过滤
- [ ] 告警数列支持服务端排序
- [ ] URL 三参数进入页面自动切分支管理 tab 并带出筛选
- [ ] 修改筛选 URL 同步更新；刷新后 tab 与筛选保持
- [ ] 仓库详情跳转返回后筛选条件保留
- [ ] atomgit 仓库链接可录入并识别为 GitCode 平台
- [ ] 静态告警页 atomgit 仓库链接可正常跳转代码托管平台
- [ ] 全局配置同步源可保存 atomgit 域名 URL，其他平台仍按各自域名校验
- [ ] 度量详情摘要区显示扫描时间
- [ ] 流水线按 `pipelineName #runNumber` 拼接展示；pipelineName 为空或 null 时只显示 `#runNumber`

## 影响范围

| 文件                                                                         | 变更类型                      |
| ---------------------------------------------------------------------------- | ----------------------------- |
| `apps/web-openlibing/src/views/Repos/branches.vue`                           | 重构（表头/列/联动）          |
| `apps/web-openlibing/src/views/Repos/index.vue`                              | 重构（tab/URL 联动/平台识别） |
| `apps/web-openlibing/src/views/Repos/dialog/MetricsDetailDialog.vue`         | 增强（摘要区）                |
| `apps/web-openlibing/src/views/Repos/dialog/GlobalConfigDialog.vue`          | 增强（同步源域名校验）        |
| `apps/web-openlibing/src/assets/js/config.json`                              | 新增 ATOMGIT_BASE_URL         |
| `apps/web-openlibing/src/utils/until.js`                                     | 跳转白名单放行 atomgit        |
| `apps/web-openlibing/src/views/StaticAlarm/utils/staticAlarmRepoLink.ts`     | 仓链接白名单放行 atomgit      |
| `apps/web-openlibing/src/views/sca/componentAnalysis/index.vue`              | atomgit 平台选项              |
| `apps/web-openlibing/src/views/sca/personalScandTaskInfor/analysisTable.vue` | atomgit 仓 URL 拼链           |
| `apps/web-openlibing/src/components/openSourceCompliance/analysisTable.vue`  | atomgit 仓 URL 拼链           |
| `apps/web-openlibing/src/components/openSourceCompliance/index.vue`          | atomgit 平台选项              |

## 相关提交（dev-chenning-20261019）

| commit      | 说明                                                               |
| ----------- | ------------------------------------------------------------------ |
| `de1f11507` | feat(repos): metrics group header and branch filter URL sync       |
| `bab313f27` | feat(repos): show static alert count in branch manage list         |
| `d027cfbe6` | fix(repos): keep branch filters stable across detail navigation    |
| `317d255a4` | feat(repos): add doc link to UT coverage and metrics headers       |
| `d58ce2824` | fix(repos): carry branch in static alarm jump and sort alert count |
| `1f6d6e8d4` | feat(sca): add atomgit platform option and repo URL mapping        |
| `b23c0d357` | feat(repos): allow atomgit hosts in global config sync sources     |
| `ec42de1a8` | docs(repos): 补充 UT 行覆盖率说明文档地址                          |
| `8fa23007d` | feat(metrics): show scan time and pipeline name in detail dialog   |

## 关联接口

| 接口                                       | 用途                                                                                        |
| ------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `POST /code-repo/metrics/code/file-detail` | 度量详情数据，返回新增 `checkTime`、`pipelineName` 字段（原有 `runNumber`、`pipelineLink`） |
| 分支列表查询接口                           | 返回 `staticAlertCount` 字段，支持 `staticAlertCount` 排序字段                              |

## 跨仓依赖与待办

- 后端 openlibing-coderepo 的 `checkRepoUrl` / `addRepo` 及 SIG 同步的域名白名单需同步支持 atomgit；后端未放行前，atomgit 链接录入仍会被后端拒绝
- UT 行覆盖率说明文档地址已由使用方补充
