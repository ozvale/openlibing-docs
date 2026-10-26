# #294 任务分解

## 1. 基本信息

| 项目       | 内容                                                     |
| ---------- | -------------------------------------------------------- |
| 需求文档   | [需求_feature_294.md](./需求_feature_294.md)             |
| 关联 Issue | https://gitcode.com/openlibing/openlibing-ops/issues/294 |
| 开发分支   | `feature_293_new`（openlibing-ops）                      |
| 前端分支   | `feature_293`（openlibing-ops-web）                      |

## 2. 任务总览

| 编号 | 任务                   | 仓库/模块          | 主要文件                                                              | 依赖  | 验收                    |
| ---- | ---------------------- | ------------------ | --------------------------------------------------------------------- | ----- | ----------------------- |
| T1   | 新增明细分类与请求响应 | openlibing-ops     | `DetailCommonEnum`、`DetailReq`、`OpsPrPipelineRunDetailReq/Resp`     | 无    | category 可路由         |
| T2   | 实现 run 级明细 SQL    | openlibing-ops     | `OpsPrPipelineRunDetailMapper.java/.xml`                              | T1    | 指标样本与主表一致      |
| T3   | 实现 DetailService     | openlibing-ops     | `OpsPrPipelineRunDetailDetailService`                                 | T2    | 分页、排序、空值正确    |
| T4   | 后端测试与质量门禁     | openlibing-ops     | 单测/XML 校验                                                         | T1-T3 | 编译、测试全部通过      |
| T5   | 新增执行明细弹窗与列   | openlibing-ops-web | `pr-run-detail-modal.vue`、`columns.ts`                               | T3    | 表格正常渲染            |
| T6   | 接入主表与 PR Tab 点击 | openlibing-ops-web | `engineering-capability-view.vue`、`detail-panel.vue`、`repo-tab.vue` | T5    | 点击直接打开弹窗        |
| T7   | 前端格式与测试         | openlibing-ops-web | —                                                                     | T5-T6 | prettier/可执行测试通过 |

## 3. 详细任务

### T1 新增明细分类与请求响应

**步骤**：

1. `DetailCommonEnum` 增加 `OPS_PR_PIPELINE_RUN_DETAIL("ops-pr-pipeline-run-detail")`。
2. `DetailReq` 增加 `OpsPrPipelineRunDetailReq` 子类型。
3. 请求增加 `projectId`（必填）、`metricType`（duration/buildQueue/dtQueue）。
4. 响应字段覆盖运行、仓库、PR、状态、三类指标和跳转 URL。

**验收**：

- `/common/detail` 能按 category 路由到新 Service；
- 参数校验生效。

### T2 实现 run 级明细 SQL

**步骤**：

1. 复用主表 `pr_run_sample` 口径：桥表 `pr_id` 非空、统一表、运营仓、GitHub 配置、时间窗。
2. 按 `pipeline_run_id` 聚合，PR 编号用 `GROUP_CONCAT`，避免一 run 多 PR 重复。
3. job 统一表按 `job_type` 透视 BUILD/DT 排队。
4. 指标过滤：
   - duration：`status='COMPLETED' AND end_time IS NOT NULL`
   - buildQueue：`end_time IS NOT NULL AND build_pd IS NOT NULL`
   - dtQueue：`end_time IS NOT NULL AND dt_pd IS NOT NULL`
5. 列表和 count 共用同一过滤条件。
6. 排序字段走白名单，默认按当前指标倒序。

**验收**：

- 明细 run 集合与主表 P90 样本一致；
- 分页 total 与列表一致。

### T3 实现 DetailService

**步骤**：

1. 校验 `metricType`；
2. 规范化 `sortField` / `sortRule`；
3. 未传排序时按指标设置默认排序；
4. 查询 count 和列表，组装 `PageResult`。

**验收**：

- 非法 metricType / sortField 返回参数错误；
- 空数据返回空分页。

### T4 后端测试与质量门禁

```bash
mvn spotless:apply
mvn checkstyle:check
mvn spotbugs:check
mvn pmd:check
mvn test
```

补充 Service 单元测试：默认排序、非法 metricType、空列表。

### T5 新增执行明细弹窗与列

**步骤**：

1. `columns.ts` 增加 `prRunDetailColumns`。
2. 新增 `pr-run-detail-modal.vue`，请求 category=`ops-pr-pipeline-run-detail`。
3. 列展示运行编号、流水线、仓库、PR、平台、启动时间、状态、三类指标。
4. 空值展示 `--`，运行编号支持跳转。

### T6 接入主表与 PR Tab 点击

**步骤**：

1. 主表点击 `prDurationP90 / buildQueueP90 / dtQueueP90` 时直接打开弹窗。
2. 项目详情 PR Tab 三张 KPI 卡片点击时，通过事件链打开同一弹窗。
3. 弹窗标题显示项目名和指标名，默认按指标倒序。

### T7 前端格式与测试

```bash
npx prettier --check "src/views/dashboard/engineering-capability/**/*.{ts,vue}"
npx vitest run src/views/dashboard/engineering-capability
```

如仓库未生成 auto-import 类型声明，`vue-tsc` 全量检查会报既有全局错误，不作为本次改动失败依据。

## 4. 依赖与顺序

```text
T1 -> T2 -> T3 -> T4
T3 -> T5 -> T6 -> T7
```

## 5. 验收清单

- [ ] 主表三个指标点击直接打开执行明细。
- [ ] PR Tab 三张 KPI 卡片点击打开执行明细。
- [ ] 明细列、排序、分页、空值正确。
- [ ] 明细样本与主表指标口径一致。
- [ ] 后端质量门禁和单元测试通过。
- [ ] 前端格式检查通过，可执行测试通过。
- [ ] 未修改主表指标计算逻辑。

## 6. 提交建议

| 仓库               | 建议提交信息                                                            |
| ------------------ | ----------------------------------------------------------------------- |
| openlibing-ops     | `feat(pr-run-detail): add PR pipeline execution detail API`             |
| openlibing-ops-web | `feat(engineering-capability): add PR pipeline execution detail drawer` |
| docs               | `docs(issue-294): add requirement design and task breakdown`            |
