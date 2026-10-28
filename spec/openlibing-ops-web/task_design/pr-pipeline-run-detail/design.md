# PR 流水线执行明细前端下钻 — 技术设计

## 方案概述

在 `open-source-project` 下新增 PR 流水线执行明细和任务明细两个共享组件。工程能力与 PR 门禁页面只负责入口展示和参数组装，不改造现有 Nightly 组件。列配置集中在 `columns/pr-pipeline-columns.ts`，由 `config.ts` 统一导出。

## 组件与数据流

### 工程能力入口

`repo-tab.vue` 为 `prDuration`、`buildQueueP90`、`dtQueueP90` 增加插槽。点击仓库行数值后打开共享执行明细，参数为：

- `projectId`：当前项目。
- `repoId`：当前仓库行。
- `repoName`、`repoUrl`：当前仓库行，用于标题展示与仓库跳转。
- `startDate/endDate`：当前看板时间窗。
- `pipelineStatus`：仅 `prDuration` 传字符串 `true`，与主表 P90 已完成样本一致；其余两列不传。

### PR 门禁入口

`pr-columns.ts` 新增 `runCount` 列（`disabled: true`，不参与列设置）。`sub-table.vue` 渲染可点击执行次数，点击后组装下钻参数：

- `projectId`、`startDate/endDate`、`pipelineStatus`：取自 `subParams`。
- `repoId`、`repoName`：取自当前仓库行。
- `repoUrl`：取当前行的 `url` 字段。

### 执行明细

`pr-pipeline-run-detail.vue` 为 `el-drawer`（`size="90%"`、`destroy-on-close`），使用 `BaseTable` 和 `getCommonDetail`，请求参数固定为
`{ category: 'ops-pr-pipeline-run-detail', projectId, repoId, startDate, endDate, pipelineStatus }`。

- 标题：仓库名称 + “流水线执行明细”。仓库名称在 `isSafeHttpUrl(repoUrl)` 通过时渲染为原生 `<a>`（`text-link hover:underline`），否则渲染纯文本。
- 展示 17 个数据列，无独立操作列：流水线名称、流水线平台、启动时间、结束时间、状态、执行时长、构建/测试/代码检查的平均与最长时长及排队时长、NPU 卡时。
- 流水线名称单元格：存在 `pipelineRunUrl` 时前置跳转图标；存在 `pipelineRunId` 时运行编号与名称可点击下钻任务明细，否则渲染纯文本。
- 平台列使用 `PLATFORM_TEXT` 映射，以浅蓝标签展示；平台为空时输出 `--`。
- 状态列复用 `PipelineStatus` 组件，接口数值不做二次格式化。
- 表格高度由 `useTableHeight(84)` 计算，分页 `pageSize: 20`，`row-key="pipelineRunId"`。
- 下钻时把当前行 `pipelineRunId`、`runNumber`、`pipelineName`、`pipelineRunUrl`、`platformText` 与筛选参数一并传给任务弹窗。

### 任务明细

`pr-pipeline-job-detail.vue` 为 `el-dialog`（`width="85%"`、`destroy-on-close`），请求参数固定为
`{ category: 'ops-pr-pipeline-job-detail', projectId, startDate, endDate, pipelineRunId }`。

- 标题：`#运行编号 流水线名称` + “任务明细”，存在 `pipelineRunUrl` 时上述文本整体渲染为链接；右侧在 `platformText` 非空时展示平台标签。
- 展示 9 个数据列：任务名称（固定左侧）、任务类型、任务状态、调度时间、入队时间、结束时间、任务时长、排队时长、NPU 卡时。
- 任务名称使用 `getPipelineUrl(row, true, true)` 生成链接，空链接显示普通文本。
- 任务类型按 `BUILD/DT/CHECK/OTHER` 映射为构建/测试/代码检查/其他，未知类型回退原值。
- 状态列复用 `PipelineStatus` 组件；表格外层容器固定 `calc(70vh - 170px)`，`border` 关闭。

### 排序

- 列配置的 `sortable: true` 交由 `BaseColumn` 自绘排序箭头，`BaseTable` 在点击后把 `sortField`/`sortRule` 并入请求参数，不传 `handleSortParam`、不在前端做字段映射。
- 执行明细开放 12 个数字列排序，任务明细开放 3 个数字列排序；时间、名称、状态列不开放。
- 前端不设定默认排序字段，默认顺序由后端接口决定。

## 涉及文件

| 文件                                                                     | 操作 | 说明                                |
| ------------------------------------------------------------------------ | ---- | ----------------------------------- |
| `src/views/dashboard/engineering-capability/components/repo-tab.vue`     | 修改 | 三个仓库指标入口、仓库链接校验      |
| `src/views/dashboard/open-source-project/columns/pr-columns.ts`          | 修改 | 新增执行次数列                      |
| `src/views/dashboard/open-source-project/sub-table.vue`                  | 修改 | 执行次数入口、仓库链接校验          |
| `src/views/dashboard/open-source-project/pr-pipeline-run-detail.vue`     | 新增 | 共享 17 列执行明细                  |
| `src/views/dashboard/open-source-project/pr-pipeline-job-detail.vue`     | 新增 | 共享 9 列任务明细                   |
| `src/views/dashboard/open-source-project/columns/pr-pipeline-columns.ts` | 新增 | 两组明细列配置，含排序与列宽        |
| `src/views/dashboard/open-source-project/config.ts`                      | 修改 | 列配置桶导出、`getPipelineUrl` 加固 |
| `src/types/open-source-project.ts`                                       | 修改 | 补充入参与行数据的展示字段类型      |

## 异常与空值

请求 loading、空分页和异常提示沿用 `BaseTable` 与 HTTP 拦截器。接口空值由表格统一显示 `--`；缺少跳转必需字段时不渲染链接。`getPipelineUrl` 的仓库地址部分统一走 `isSafeHttpUrl`：非 http(s) 地址返回空串，因此不会生成可点击链接；`jobRunId` 仅在同时存在 `pipelineRunId` 时追加。

## 测试与验证

- `__tests__/config.test.ts` 覆盖 `getPipelineUrl` 的三平台链接生成、协议校验、`.git` 与尾斜杠处理、缺失字段回退等行为。
- 列配置、入口参数等纯展示逻辑不新增单元测试，避免无行为价值的桩测试。
- 提交前对改动文件执行 ESLint、Prettier 与 `npm run type-check`。

## 风险与缓解

- 仓库级 P90 与主表样本存在已知口径差异：前端按需求传参，不在本地补数或修正。
- 数字列排序依赖后端对两个 category 支持 `sortField`/`sortRule`，接口不支持时顺序不变，需联调确认。
- 长表头叠加排序箭头对列宽敏感，`minWidth` 过小会导致表头换行，需按实际渲染效果调整。
- 共享组件影响两个页面：保持 Nightly 不变，以相同组件和参数保证行为一致。
