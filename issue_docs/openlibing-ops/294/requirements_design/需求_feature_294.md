# #294 需求分析说明书

## 1. 基础信息

| 项目       | 内容                                                            |
| ---------- | --------------------------------------------------------------- |
| 需求名称   | 【蓝区】【运营看板】PR流水线数据支持明细查看                    |
| 关联 Issue | https://gitcode.com/openlibing/openlibing-ops/issues/294        |
| 关联页面   | https://www.openlibing.com/ops/dashboard/engineering-capability |
| 后端仓库   | openlibing-ops                                                  |
| 前端仓库   | openlibing-ops-web                                              |
| 开发分支   | `feature_293_new`（当前分支）                                   |

## 2. 需求目标

工程能力看板“项目详情-PR流水线”中的以下指标支持点击查看流水线执行明细：

- PR执行时长(min)[P90]
- PR构建资源排队时长(min)[P90]
- PR测试资源排队时长(min)[P90]

点击指标后，直接展示构成该指标的 PR 流水线 run 级明细，而不是只展示仓库级汇总。

## 3. 口径说明（重要）

本分支未实施 #293 的排队 P90 成功口径优化，因此明细必须与当前主表口径一致：

| 指标               | 主表当前口径                               | 明细样本               |
| ------------------ | ------------------------------------------ | ---------------------- |
| PR执行时长 P90     | 仅 `status='COMPLETED'` 且 `end_time` 非空 | 成功 PR run            |
| PR构建资源排队 P90 | 全部状态，`end_time` 非空，取 BUILD 排队   | 有 BUILD job 的 PR run |
| PR测试资源排队 P90 | 全部状态，`end_time` 非空，取 DT 排队      | 有 DT job 的 PR run    |

后续如果合入 #293 的排队成功口径，构建/测试明细需同步增加 `status='COMPLETED'`。

## 4. 后端设计

### 4.1 接口

复用 `POST /common/detail`，新增 category：

```text
ops-pr-pipeline-run-detail
```

请求参数：

- `category`：`ops-pr-pipeline-run-detail`
- `projectId`：必填
- `metricType`：`duration` / `buildQueue` / `dtQueue`
- `startDate` / `endDate`
- `page` / `pageSize`
- `sortField` / `sortRule`：可选；不传时按指标默认倒序

响应字段：

- 运行编号、pipelineRunId、pipelineId
- 流水线名称、平台
- 仓库 ID/名称/URL
- PR 编号、标题、链接
- 开始时间、结束时间、状态
- PR 执行时长(min)
- 构建排队(min)、测试排队(min)
- workflow 运行跳转 URL

### 4.2 数据口径

PR run 样本与 `OpsMainStatMapper.pr_run_sample` 保持一致：

1. `dwi_rd_efc_pr_info_sum` 关联桥表，`pr_id` 非空；
2. 关联 `dwr_rd_efc_pipeline_run_unified`，按 `pipeline_run_id` 去重；
3. 运营仓过滤 + GitHub 展示配置过滤；
4. 时间按 `start_time` 过滤；
5. 一个 run 关联多个 PR 时，按 run 聚合 PR 编号，避免重复行。

指标过滤：

- `duration`：`status='COMPLETED' AND end_time IS NOT NULL`
- `buildQueue`：`end_time IS NOT NULL` 且存在 BUILD job
- `dtQueue`：`end_time IS NOT NULL` 且存在 DT job

排序白名单：

- `duration_minutes`
- `build_queue_minutes`
- `dt_queue_minutes`
- `start_time`
- `run_id`
- `status`
- `pipeline_name`

### 4.3 一致性

- 明细列表的 run 集合必须与主表指标样本一致；
- 排队指标只列出有对应 job 的 run，P90 忽略空值；
- 分页总数使用与列表相同的过滤条件；
- GitHub run 仅保留配置表内的 workflow。

## 5. 前端设计

### 5.1 入口

1. 主表点击三个 PR 指标单元格，直接打开“PR流水线执行明细”弹窗。
2. 项目详情-PR Tab 的三张 KPI 卡片也支持点击，打开同一弹窗。
3. 弹窗按点击指标默认倒序，标题显示项目名和指标名。

### 5.2 表格列

- 运行编号（可跳转）
- 流水线/Workflow
- 仓库
- PR
- 平台
- 启动时间
- 状态
- PR执行时长(min)
- 构建排队(min)
- 测试排队(min)

空值统一展示 `--`。

## 6. 验收标准

- [ ] 三个指标点击后均能打开执行明细弹窗。
- [ ] 弹窗默认按当前指标倒序。
- [ ] 明细 run 集合与主表指标样本一致。
- [ ] 构建/测试排队明细只展示有对应 job 的 run。
- [ ] PR 执行时长明细只展示成功运行。
- [ ] 分页、排序、空值展示正常。
- [ ] 后端 XML、格式检查、编译和单元测试通过。
- [ ] 前端格式检查和可执行测试通过。

## 7. 范围外

- 不修改主表指标计算逻辑；
- 不实施 #293 的排队/NPU 成功口径优化；
- 不做明细导出；
- 不新增独立 Controller，复用 `/common/detail`。
