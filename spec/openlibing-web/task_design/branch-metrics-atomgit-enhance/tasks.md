# 实现任务清单

## 1. 代码度量列说明文档（branches.vue）

- [x] 1.1 5 个度量指标列保持顶层平铺，列头内嵌问号图标 + 说明 tooltip
- [x] 1.2 tooltip：「当前展示的数据为最新一次扫描结果…」+「方案说明文档」高亮链接；各指标公式说明（`col.tip`）保留
- [x] 1.3 说明文档链接走统一跳转方法 `goToNotice`，地址 `METRICS_DOC_URL`（code-metrics-scan-solution）
- [x] 1.4 UT 行覆盖率列头 tooltip 保留公式说明，并加「方案说明文档」链接（`UT_COVERAGE_DOC_URL`）
- [x] 1.5 补充 UT 行覆盖率说明文档地址
- [x] 1.6 过程调整：初期实现的一级分组表头（居中/分割线）评审后拍平为顶层列，说明下放各列头（`9f9adc09e`）

## 2. 代码检查告警数列（branches.vue）

- [x] 2.1 分支名称后新增「代码检查告警数」列（`staticAlertCount`）
- [x] 2.2 knownColumns 机制默认展示（`knownColumnsBaseline` 追加，存量用户自动合并）
- [x] 2.3 列值可点击跳转静态告警页，搜索串拼 `branch:<分支名>` 限定符；单仓模式从 `props.repo` 兜底
- [x] 2.4 支持服务端排序（`sortable="custom"` + `branchSortOrders`）
- [x] 2.5 空值显示 `--`

## 3. 分支管理筛选 URL 联动（branches.vue + index.vue）

- [x] 3.1 URL 三参数（platforms/repoUrlLike/branchNameLike）齐全时自动切分支管理 tab 并还原筛选
- [x] 3.2 筛选变化双向同步 URL（`router.replace`）
- [x] 3.3 `applyingInitialFilter` 标志防止 URL 还原期间误上报
- [x] 3.4 刷新后保持当前 tab（sessionStorage）与筛选条件
- [x] 3.5 仓库详情/度量详情跳转返回保留筛选参数
- [x] 3.6 修复跳转过程中误删 `goMetricsDetail` 的问题

## 4. atomgit 平台适配

- [x] 4.1 `config.json` 新增 `ATOMGIT_BASE_URL`
- [x] 4.2 仓库录入白名单放行 atomgit，`getPlatform` 识别为 gitcode
- [x] 4.3 `until.js` 全局跳转白名单 `whiteLinks` 放行 atomgit
- [x] 4.4 `staticAlarmRepoLink.ts` `ALLOWED_REPO_HOSTS` 放行 atomgit.com / www.atomgit.com
- [x] 4.5 `GlobalConfigDialog.vue` 同步源校验 `PLATFORM_ALLOWED_HOSTS.gitcode` 放行 atomgit 域名
- [ ] 4.6 SCA 组件分析 / 开源合规分析表 atomgit 平台选项与仓 URL 拼链（未落地：对应提交 `1f6d6e8d4` 未纳入业务 PR openlibing-web#825 最终变更集，不在本次交付范围）

## 5. 度量详情摘要区（MetricsDetailDialog.vue）

- [x] 5.1 新增 `checkTime`、`pipelineName` refs 与接口赋值
- [x] 5.2 `pipelineDisplayName` computed：pipelineName 有值拼 `pipelineName #runNumber`，为空/null 只展示 `#runNumber`
- [x] 5.3 摘要区「分支」后新增「扫描时间」，流水线文本改用 `pipelineDisplayName`（保留 pipelineLink 跳转）

## 6. 验证方式

- 人工验证：度量列头 tooltip 与说明文档链接跳转正常
- 人工验证：告警数列默认展示、跳转静态告警页带分支过滤、排序生效
- 人工验证：URL 三参数进入自动切 tab 带筛选；改筛选 URL 同步；刷新后 tab 与筛选保持；详情返回筛选保留
- 人工验证：atomgit 链接可录入、平台识别为 GitCode、静态告警页链接可跳转、全局配置同步源可保存
- 人工验证：度量详情显示扫描时间；流水线拼接展示；pipelineName 为空只显示 `#runNumber`
- 静态检查：Prettier / ESLint 通过（新代码零新增 warning）
- 无单元测试（纯页面展示与交互逻辑，行为变化通过人工验证）
