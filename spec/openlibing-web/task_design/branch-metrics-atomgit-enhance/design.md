# 技术方案：分支管理代码度量展示增强与 atomgit 平台适配

## 总体设计

全部改动集中在 openlibing-web 前端，不涉及后端接口契约变更（仅消费后端已提供的新字段 `checkTime` / `pipelineName` / `staticAlertCount`）。按三个主题展开：分支管理展示增强、筛选 URL 联动、atomgit 域名全链路放行。

## 1. 代码度量分组表头（branches.vue）

### 结构

使用 Element Plus 嵌套 `el-table-column` 实现一级分组表头「代码度量」，5 个度量列作为二级列：

```html
<el-table-column v-if="visibleColumns.some((c) => c.metrics)" align="center">
  <template #header>
    代码度量
    <el-icon><QuestionFilled /></el-icon>
    <el-tooltip>…（最新扫描说明 + 说明文档链接）</el-tooltip>
  </template>
  <!-- 5 个度量二级列 -->
</el-table-column>
```

- `v-if="visibleColumns.some((c) => c.metrics)"`：列设置里 5 个度量列全部隐藏时，分组表头一并隐藏，避免出现空表头
- 说明文档链接定义 `METRICS_DOC_URL` 常量，指向 `code-metrics-scan-solution` 文档；跳转统一走 `goToNotice`（信任域白名单/中转页），不直接 `window.open`

### 样式坑与对策

| 问题                           | 原因                                                                        | 对策                                       |
| ------------------------------ | --------------------------------------------------------------------------- | ------------------------------------------ |
| 分组表头与二级表头之间无分割线 | `header-cell-style` 内联 `borderBottom: 1px solid #f0f0f0` 与背景色几乎同色 | 非叶子 th 用 `!important` 覆盖为 `#dbdbdb` |
| 分组表头内容不居中             | 非 leaf th 的 `.cell` 为 inline-block、宽度收缩                             | 分组表头 `.cell` 改 flex 撑满后居中        |

### UT 行覆盖率说明文档

与代码度量组同款交互（问号图标 + tooltip 内「点击查看说明文档」链接），定义 `UT_COVERAGE_DOC_URL` 常量与 `goUtCoverageDoc` 处理器，minWidth 保持 120 不受影响。

## 2. 代码检查告警数列（branches.vue）

### 列定义与默认展示

- 列插入 `allColumns` 中 `branchName` 之后，`prop: 'staticAlertCount'`，`sortable="custom"` 参与既有 `branchSortOrders` 排序链路
- 默认展示走 knownColumns 机制：`knownColumnsBaseline` 追加 `staticAlertCount`，存量用户 sessionStorage（`branch_column_known_{userId}`）中无该列时自动合并为展示，不需要用户手动开启

### 跳转静态告警页（goStaticAlarm）

StaticAlarm 页初始化约定：URL 带 `query` 参数时走 `parseStaticAlarmSearch` 解析搜索串，**忽略独立的 `branch` 参数**。因此分支过滤必须拼进搜索串限定符：

```
?projectId=<id>&query=repotype:gitcode owner:<owner> repo:<repo> branch:<分支名>
```

- 分支管理「全部分支」模式：使用行数据自带的 platform / repoUrl
- 单仓详情模式：行数据可能缺字段，从 `props.repo` 兜底
- 空值（null/undefined）显示 `--`，不做跳转

### 排序

后端分支排序双路径：MySQL `order by` 白名单 + 内存排序（`PROJECT_BRANCH_MEMORY_SORT_FIELDS` 已含 `staticAlertCount`，null 按 0 处理）。前端只需 `sortable="custom"` + `branchSortOrders` 传参，无需后端改动。

## 3. 分支管理筛选 URL 联动

### 进入还原（index.vue → branches.vue）

- URL 同时存在 `platforms` / `repoUrlLike` / `branchNameLike` 时，`projectInfo` 首次加载且无 repoId 场景下调用 `goBranchFromQuery()`：切换到分支管理 tab，并将三个参数通过 props 传入 branches
- branches 内 `applyBranchInitialFilter` 还原三项筛选；还原期间置 `applyingInitialFilter = true`，避免 watch `filterChange` 上报造成 URL 回写环路，还原结束复位
- tab 恢复：activeTab 变化写 sessionStorage，进入页面时恢复，刷新后停留原 tab

### 双向同步

- watch 筛选项变化 → emit `filterChange` → index.vue `handleBranchFilterChange` → `pickBranchFilterQuery()` 取三项 → `router.replace` 写 URL（不产生历史记录）
- 仓库详情/度量详情等子页面跳转（`syncMetricsQuery` / `syncUtCoverageQuery` / `backToBranch`）拼 URL 时保留已有筛选参数，返回后筛选不丢
- 仓库详情模式（`props.repo` 存在）不上报筛选变化，避免污染列表页 URL

## 4. atomgit 域名全链路放行

前提（业务约定）：atomgit.com 与 gitcode.com 互为镜像，同属 GitCode 平台。

| 环节 | 文件 | 改动 |
| -------------- | ----------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------- |
| 域名常量 | `config.json` | 新增 `ATOMGIT_BASE_URL: "https://atomgit.com/"` |
| 平台识别 | `Repos/index.vue` `getPlatform` | `/gitcode\.com                                                                                                                             | atomgit\.com/i`统一识别为`gitcode` |
| 全局跳转白名单 | `utils/until.js` `whiteLinks` | 追加 `ATOMGIT_BASE_URL` |
| 静态告警仓链接 | `staticAlarmRepoLink.ts` | `ALLOWED_REPO_HOSTS` 加 `atomgit.com` / `www.atomgit.com` |
| 全局配置同步源 | `GlobalConfigDialog.vue` | `PLATFORM_ALLOWED_HOSTS.gitcode` 加 `atomgit.com` / `www.atomgit.com`，校验改为 `!PLATFORM_ALLOWED_HOSTS[platform].includes(url.hostname)` |
| SCA 分析表 | `componentAnalysis/index.vue`、两个 `analysisTable.vue`、`openSourceCompliance/index.vue` | atomgit 平台选项与仓 URL 拼链映射 |

全局配置侧新增 `PLATFORM_ALLOWED_HOSTS` 常量表，替代原先散落的域名字符串判断，各平台域名收敛为一张表，后续加域名只改配置。

## 5. 度量详情摘要区（MetricsDetailDialog.vue）

```js
const pipelineName = ref("");
const checkTime = ref("");
const pipelineDisplayName = computed(() => {
  return pipelineName.value
    ? `${pipelineName.value} #${runNumber.value}`
    : `#${runNumber.value}`;
});
```

- 接口赋值：`pipelineName.value = res?.data?.pipelineName || ''`、`checkTime.value = res?.data?.checkTime || ''`，null/undefined/空串统一兜底为空串
- 模板：流水线两个 span（有链接/无链接）文本统一改用 `{{ pipelineDisplayName }}`，`pipelineLink` 的可点击跳转判断保持不变；「分支」后新增 `<span>扫描时间：{{ checkTime }}</span>`

## 影响范围与兼容性

- knownColumns 新列对存量用户自动合并展示，无感升级
- URL 参数为增量（新增三个 query key），旧链接无参数时行为不变
- atomgit 放行均为白名单追加，不影响既有三平台的校验逻辑
- ESLint 约束：新代码避免 `==`（eqeqeq）、嵌套三元（no-nested-ternary）等 warning

## 已知边界

- 后端 openlibing-coderepo 的 `checkRepoUrl` / `addRepo` 与 SIG 同步域名白名单尚未放行 atomgit，前端放行不改变后端行为
- SCA 分析表拼链依赖 atomgit 镜像语义（数据中无原始 repoUrl，按镜像域名拼链）
