# pr-comment-subtask-refresh

> 关联 Issue: openlibing-cicd#207
> FE 需求名称: PR流水线报告支持子任务结束刷新、任务状态增加文字提示
> 流程模式: Standard
> 评审调整（2026-08-21）：经评审，"子任务状态变化触发评论刷新"不再需要，本次保留"任务状态 emoji 优化 + 状态英文名追加"——通过修改 `PipelineJobStatusEnums.ascii_code` 字段让不同状态视觉区分，并在 emoji 后追加状态英文名提升可读性。

## 需求背景

CICD 平台通过 PR 评论向用户展示流水线进度，`prepareCommentTable` 渲染状态列时直接输出 `PipelineJobStatusEnums.ascii_code` 对应的 HTML 实体字符（仅 emoji）。当前存在两个体验问题：

### 问题 1：多个状态共用同一 emoji，辨识度低

`PipelineJobStatusEnums` 中多个状态共用同一 `ascii_code`：

- `INIT` / `QUEUED` / `RUNNING` 共用 `&#128346;`（⏱）
- `PAUSED` / `SUSPEND` / `SKIPPED` / `IGNORED` 共用 `&#128721;`（⛔）
- `FAILED` / `UNSELECTED` 共用 `&#10060;`（❌）

用户难以一眼分辨"运行中"与"排队中"、"已跳过"与"已暂停"等状态。

### 问题 2：状态列仅显示 emoji，无文字提示

[PipelineServiceImpl.java:6797-6860](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L6797-L6860) 渲染状态列时仅输出 `<td>&#<ascii>;</td>`，无文字说明。用户对图标含义的认知成本较高，且不同状态共用 emoji 时无法分辨。

### 现状参考：状态枚举映射

`PipelineJobStatusEnums` ([PipelineJobStatusEnums.java:15-26](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/common/enums/PipelineJobStatusEnums.java#L15-L26))：

| nameEn     | nameCn     | ascii_code | 渲染字符 |
| ---------- | ---------- | ---------- | -------- |
| INIT       | 初始化     | 128346     | ⏱        |
| QUEUED     | 排队中     | 128346     | ⏱        |
| COMPLETED  | 已完成     | 9989       | ✅       |
| RUNNING    | 运行中     | 128346     | ⏱        |
| CANCELED   | 已终止运行 | 129000     | 🔴       |
| FAILED     | 运行失败   | 10060      | ❌       |
| PAUSED     | 已暂停     | 128721     | ⛔       |
| SUSPEND    | 已挂起     | 128721     | ⛔       |
| SKIPPED    | 已跳过     | 128721     | ⛔       |
| IGNORED    | 已忽略     | 128721     | ⛔       |
| UNSELECTED | 无法查询   | 10060      | ❌       |

## 功能描述

### 需求 1：任务状态 emoji 优化

**改动范围**：修改 `PipelineJobStatusEnums` 枚举中部分状态的 `ascii_code` 字段值，让每个状态在 PR 评论中具有差异化的视觉标识。

**新 ascii_code 映射**：

| nameEn     | nameCn     | 原 ascii_code | 新 ascii_code  | 原 emoji | 新 emoji | 说明                         |
| ---------- | ---------- | ------------- | -------------- | -------- | -------- | ---------------------------- |
| INIT       | 初始化     | 128346        | **128995**     | ⏱        | 🟣       | 紫色圆圈，标识"初始化准备中" |
| QUEUED     | 排队中     | 128346        | 128346（不变） | ⏱        | ⏱        | 沿用                         |
| COMPLETED  | 已完成     | 9989          | 9989（不变）   | ✅       | ✅       | 沿用                         |
| RUNNING    | 运行中     | 128346        | **9654**       | ⏱        | ▶        | 黑色右指三角，标识"运行中"   |
| CANCELED   | 已终止运行 | 129000        | 129000（不变） | 🔴       | 🔴       | 沿用                         |
| FAILED     | 运行失败   | 10060         | 10060（不变）  | ❌       | ❌       | 沿用                         |
| PAUSED     | 已暂停     | 128721        | 128721（不变） | ⛔       | ⛔       | 沿用                         |
| SUSPEND    | 已挂起     | 128721        | **128997**     | ⛔       | 🟥       | 红色方块，与 PAUSED 区分     |
| SKIPPED    | 已跳过     | 128721        | **9193**       | ⛔       | ⏭        | 快进符号，标识"跳过"         |
| IGNORED    | 已忽略     | 128721        | **9898**       | ⛔       | ⚪       | 白色圆圈，标识"忽略"         |
| UNSELECTED | 无法查询   | 10060         | **11036**      | ❌       | ⬜       | 白色方形，与 FAILED 区分     |

### 需求 2：状态列追加状态英文名

**渲染改造**：`prepareCommentTable` 渲染状态列时，在 emoji 后追加状态英文名（`nameEn`），格式为 `<emoji> <nameEn>`（emoji + 空格 + 英文名），例如 `🟣 INIT`、`✅ COMPLETED`、`▶ RUNNING`、`⏭ SKIPPED`。

**改造前**：`<td>&#<ascii>;</td>` → 仅显示 emoji（如 `⏱`）

**改造后**：`<td style="padding:8px;text-align:left;">&#<ascii>; <nameEn></td>` → 显示 emoji + 空格 + 英文名，状态列左对齐 + 8px 内边距（如 `⏱ QUEUED`；左对齐为用户自测反馈后追加，commit `b1a393d5`）

**字段设计**：

- `CommentTableVo` 新增 `jobStatusNameEn` 字段（String），存储状态英文名（如 `"INIT"` / `"COMPLETED"`）。
- `PipelineServiceImpl.buildCommentTableVo`（两个重载）填充 `jobStatusNameEn`：
  - 流水线整体行：`vo.setJobStatusNameEn(pipelineRunDetail.getStatus())`
  - 子任务行：`commentTableVo.setJobStatusNameEn(job.getStatus())`
- `prepareCommentTable` 渲染状态列时拼接：`<td>&#<ascii>; <nameEn></td>`

**视觉对照**：

| 状态       | 修改前 | 修改后        |
| ---------- | ------ | ------------- |
| INIT       | ⏱      | 🟣 INIT       |
| QUEUED     | ⏱      | ⏱ QUEUED      |
| RUNNING    | ⏱      | ▶ RUNNING     |
| COMPLETED  | ✅     | ✅ COMPLETED  |
| CANCELED   | 🔴     | 🔴 CANCELED   |
| FAILED     | ❌     | ❌ FAILED     |
| PAUSED     | ⛔     | ⛔ PAUSED     |
| SUSPEND    | ⛔     | � SUSPEND     |
| SKIPPED    | ⛔     | ⏭ SKIPPED     |
| IGNORED    | ⛔     | ⚪ IGNORED    |
| UNSELECTED | ❌     | ⬜ UNSELECTED |

## 不做什么

- **不做子任务状态变化触发评论刷新**（评审已删除该需求）：`savePipelineInfoWithAsyncPrOps` 幂等判断保持现状，仅比较流水线整体 `status`。
- 不追加中文状态名（仅追加英文名 `nameEn`）。
- 不修改 `prepareCommentTableTopInfo` / `prepareCommentTableEndInfo`（表头表尾）。
- 不修改 `updatePrLabel` / `pushGitCodeCommitStatus`。
- 不修改 `saveBuildCheck` 的成功判定逻辑（仍按 `COMPLETED.ascii_code=9989` 判定）。
- 不新增 `subtaskFingerprint` / `lastSubtaskFingerprint` 字段，不修改 `PipelineStatusUpdateMessage` / `PipelineStatusUpdateConsumer` 等消息类。
- 不修改 `PipelineParamDTO`。
- 不引入 Redis 或新增 DB 字段。
- 不修改 RabbitMQ 配置。
- 不修改 `buildJobTableData` 的 job 过滤逻辑。
- 不修改 `PipelineJobStatusEnums` 的 `nameEn` / `nameCn` 字段值（仅改 `ascii_code`）。
- 不修改 `PipelineStartEventHandler` / `PrOpEventConsumer` / `WebHookEventConsumer` 等其他类。

## 验收标准

- [ ] `PipelineJobStatusEnums.INIT.ascii_code` 从 `128346` 改为 `128995`（🟣）。
- [ ] `PipelineJobStatusEnums.RUNNING.ascii_code` 从 `128346` 改为 `9654`（▶）。
- [ ] `PipelineJobStatusEnums.SUSPEND.ascii_code` 从 `128721` 改为 `128997`（🟥）。
- [ ] `PipelineJobStatusEnums.SKIPPED.ascii_code` 从 `128721` 改为 `9193`（⏭）。
- [ ] `PipelineJobStatusEnums.IGNORED.ascii_code` 从 `128721` 改为 `9898`（⚪）。
- [ ] `PipelineJobStatusEnums.UNSELECTED.ascii_code` 从 `10060` 改为 `11036`（⬜）。
- [ ] `QUEUED` / `COMPLETED` / `CANCELED` / `FAILED` / `PAUSED` 五个状态 `ascii_code` 保持原值不变。
- [ ] `CommentTableVo` 新增 `jobStatusNameEn` 字段，`@Data` + `@AllArgsConstructor` + `@NoArgsConstructor` 注解兼容。
- [ ] `PipelineServiceImpl.buildCommentTableVo(PipelineParamDTO, ShowPipelineRunDetailResponse, String)` 设置 `vo.setJobStatusNameEn(pipelineRunDetail.getStatus())`。
- [ ] `PipelineServiceImpl.buildCommentTableVo(JobRun, String, Map, String)` 设置 `commentTableVo.setJobStatusNameEn(job.getStatus())`。
- [ ] `prepareCommentTable` 渲染状态列时输出 `<td>&#<ascii>; <nameEn></td>` 格式（emoji + 空格 + 英文名）。
- [ ] 单元测试 `PrepareCommentTableTest` 覆盖：
  - [ ] 渲染 COMPLETED 状态输出 `<td>&#9989; COMPLETED</td>`。
  - [ ] 渲染 SKIPPED 状态输出 `<td>&#9193; SKIPPED</td>`。
  - [ ] 渲染 INIT 状态输出 `<td>&#128995; INIT</td>`。
  - [ ] 渲染 UNSELECTED 状态输出 `<td>&#11036; UNSELECTED</td>`。
  - [ ] 渲染 RUNNING 状态输出 `<td>&#9654; RUNNING</td>`。
  - [ ] 渲染 QUEUED 状态输出 `<td>&#128346; QUEUED</td>`。
  - [ ] 渲染 FAILED 状态输出 `<td>&#10060; FAILED</td>`。
  - [ ] 多任务同阶段、多阶段混合渲染场景。
  - [ ] `tableData` 为空 / null / `pipelineStatus=QUEUED` 时仅返回 `commentTableTop`，不渲染表格主体。
  - [ ] 表头表尾内容保持现状（`commentTableTop` / `commentTableEnd` 不变，表头列顺序：阶段/任务名/状态/详情）。
- [ ] `saveBuildCheck` 行为回归：`COMPLETED.ascii_code`（9989）保持不变，SKIPPED/IGNORED 等非 9989 状态仍判定为 `failed`，行为不变。
- [ ] 现有测试无回归（`PipelineStartEventHandlerTest` / `PipelineStopEventHandlerTest` / `PipelineRetryEventHandlerTest` / `PrOpEventConsumerTest` 等）。
- [ ] 手动验收：触发一次 PR 评论流水线，检查各状态 emoji + 英文名渲染符合上表。

## 影响范围

### 业务仓 `openlibing-cicd`

| 文件                                                                   | 操作 | 说明                                                                                                |
| ---------------------------------------------------------------------- | ---- | --------------------------------------------------------------------------------------------------- |
| `common/enums/PipelineJobStatusEnums.java`                             | 修改 | 6 个状态的 `ascii_code` 字段值调整                                                                  |
| `business/vo/CommentTableVo.java`                                      | 修改 | 新增 `jobStatusNameEn` 字段                                                                         |
| `business/service/impl/PipelineServiceImpl.java`                       | 修改 | `buildCommentTableVo`（2 个重载）填充 `jobStatusNameEn`；`prepareCommentTable` 渲染状态列追加英文名 |
| `src/test/java/.../business/service/impl/PrepareCommentTableTest.java` | 新增 | 覆盖状态列渲染格式与边界场景（含 6 个新 ascii_code 值与 5 个未变状态回归）                          |

### docs 仓 `openlibing-docs`

| 文件                                                                            | 操作 | 说明                     |
| ------------------------------------------------------------------------------- | ---- | ------------------------ |
| `spec/openlibing-cicd/task_design/pr-comment-subtask-refresh/proposal.md`       | 新增 | 本文件                   |
| `spec/openlibing-cicd/task_design/pr-comment-subtask-refresh/design.md`         | 新增 | 详见 `design.md`         |
| `spec/openlibing-cicd/task_design/pr-comment-subtask-refresh/tasks.md`          | 新增 | 详见 `tasks.md`          |
| `spec/openlibing-cicd/task_design/pr-comment-subtask-refresh/edevops-design.md` | 新增 | 详见 `edevops-design.md` |
