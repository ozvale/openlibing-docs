# 设计文档：pr-comment-subtask-refresh

> 关联 Proposal: `proposal.md`
> 关联 Issue: openlibing-cicd#207
> 流程模式: Standard

## 1. 设计目标

1. 通过调整 `PipelineJobStatusEnums` 中部分状态的 `ascii_code` 字段值，解决 PR 评论中多个状态共用同一 emoji、辨识度低的问题。
2. 在状态列 emoji 后追加状态英文名（`nameEn`），提升可读性，例如 `🟧 INIT`、`✅ COMPLETED`。

## 2. 现状分析

### 2.1 枚举定义

[PipelineJobStatusEnums.java:15-26](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/common/enums/PipelineJobStatusEnums.java#L15-L26)：

```java
public enum PipelineJobStatusEnums {
    INIT("INIT", "初始化", "128995"),
    QUEUED("QUEUED", "排队中", "128346"),
    COMPLETED("COMPLETED", "已完成", "9989"),
    RUNNING("RUNNING", "运行中", "9654"),
    CANCELED("CANCELED", "已终止运行", "129000"),
    FAILED("FAILED", "运行失败", "10060"),
    PAUSED("PAUSED", "已暂停", "128721"),
    SUSPEND("SUSPEND", "已挂起", "128997"),
    SKIPPED("SKIPPED", "已跳过", "9193"),
    IGNORED("IGNORED", "已忽略", "9898"),
    UNSELECTED("UNSELECTED", "无法查询", "11036");
    // ...
}
```

emoji 冲突清单（改造前的现状）：

- `INIT` / `QUEUED` / `RUNNING` 共用 `128346`（⏱）
- `PAUSED` / `SUSPEND` / `SKIPPED` / `IGNORED` 共用 `128721`（⛔）
- `FAILED` / `UNSELECTED` 共用 `10060`（❌）

### 2.2 渲染链路

```
PipelineJobStatusEnums.ascii_code (字符串)
   │
   ▼
buildCommentTableVo(...).setJobStatusAscii(ascii_code)
   │
   ▼
CommentTableVo.jobStatusAscii  →  prepareCommentTable 输出 "<td>&#<ascii>;</td>"
   │
   ▼
PR 评论 HTML 渲染为 emoji 字符
```

### 2.3 当前 `prepareCommentTable` 状态列渲染

[PipelineServiceImpl.java:6797-6860](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L6797-L6860)：

```java
stringBuilder
    .append("        <td>&#")
    .append(commentTableVos.get(i).getJobStatusAscii())
    .append(";</td>\n");
```

仅输出 `<td>&#<ascii>;</td>`，状态列只显示 emoji，无文字。

### 2.4 当前 `CommentTableVo` 结构

[CommentTableVo.java](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/vo/CommentTableVo.java)：

```java
@Data
@AllArgsConstructor
@NoArgsConstructor
public class CommentTableVo {
  private String jobType;
  private String jobName;
  private String jobStatusAscii;
  private String jobUrl;
}
```

无状态名字段，需新增 `jobStatusNameEn`。

## 3. 方案设计

### 3.1 字段值映射

| nameEn     | nameCn     | 原 ascii_code | 新 ascii_code  | 原 emoji | 新 emoji | 说明                         |
| ---------- | ---------- | ------------- | -------------- | -------- | -------- | ---------------------------- |
| INIT       | 初始化     | 128346        | **128995**     | ⏱        | 🟧       | 橙色圆圈，标识"初始化准备中" |
| QUEUED     | 排队中     | 128346        | 128346（不变） | ⏱        | ⏱        | 沿用                         |
| COMPLETED  | 已完成     | 9989          | 9989（不变）   | ✅       | ✅       | 沿用                         |
| RUNNING    | 运行中     | 128346        | **9654**       | ⏱        | ▶        | 黑色右指三角，标识"运行中"   |
| CANCELED   | 已终止运行 | 129000        | 129000（不变） | 🔴       | 🔴       | 沿用                         |
| FAILED     | 运行失败   | 10060         | 10060（不变）  | ❌       | ❌       | 沿用                         |
| PAUSED     | 已暂停     | 128721        | 128721（不变） | ⛔       | ⛔       | 沿用                         |
| SUSPEND    | 已挂起     | 128721        | **128997**     | ⛔       | 🟪       | 紫色圆圈，与 PAUSED 区分     |
| SKIPPED    | 已跳过     | 128721        | **9193**       | ⛔       | ⏭        | 快进符号，标识"跳过"         |
| IGNORED    | 已忽略     | 128721        | **9898**       | ⛔       | ⚪       | 白色圆圈，标识"忽略"         |
| UNSELECTED | 无法查询   | 10060         | **11036**      | ❌       | ⬜       | 白色方形，与 FAILED 区分     |

### 3.2 改造后的枚举定义

```java
public enum PipelineJobStatusEnums {
    INIT("INIT", "初始化", "128995"),          // ⏱ → 🟧
    QUEUED("QUEUED", "排队中", "128346"),      // 沿用
    COMPLETED("COMPLETED", "已完成", "9989"),   // 沿用
    RUNNING("RUNNING", "运行中", "9654"),       // ⏱ → ▶
    CANCELED("CANCELED", "已终止运行", "129000"), // 沿用
    FAILED("FAILED", "运行失败", "10060"),      // 沿用
    PAUSED("PAUSED", "已暂停", "128721"),        // 沿用
    SUSPEND("SUSPEND", "已挂起", "128997"),      // ⛔ → 🟪
    SKIPPED("SKIPPED", "已跳过", "9193"),        // ⛔ → ⏭
    IGNORED("IGNORED", "已忽略", "9898"),        // ⛔ → ⚪
    UNSELECTED("UNSELECTED", "无法查询", "11036"); // ❌ → ⬜
    // 其他字段、构造器、getter、getEnumByNameEn、getAsciiCodeByNameEn 等保持不变
}
```

### 3.3 `CommentTableVo` 新增 `jobStatusNameEn` 字段

```java
@Data
@AllArgsConstructor
@NoArgsConstructor
public class CommentTableVo {
  private String jobType;
  private String jobName;
  private String jobStatusAscii;
  private String jobUrl;
  private String jobStatusNameEn;  // 新增：状态英文名（如 "INIT" / "COMPLETED"）
}
```

> 由于 `@AllArgsConstructor` 会按字段顺序生成构造器，新增字段位于末尾，对既有 `new CommentTableVo(type, name, ascii, url)` 调用兼容（用 4 参构造器的代码仍可编译，但建议统一改为 setter 或全参构造）。`@NoArgsConstructor` + `@Data` 提供 setter 链，所有调用点应改用 setter。

### 3.4 `buildCommentTableVo` 填充 `jobStatusNameEn`

[PipelineServiceImpl.java:5326-5345](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L5326-L5345)（流水线整体行）：

```java
private CommentTableVo buildCommentTableVo(
    PipelineParamDTO param, ShowPipelineRunDetailResponse pipelineRunDetail, String projectId) {
  CommentTableVo vo = new CommentTableVo();
  vo.setJobType(PipelineJobTypeEnums.PIPELINE.getNameCn());
  vo.setJobStatusAscii(
      PipelineJobStatusEnums.getAsciiCodeByNameEn(pipelineRunDetail.getStatus()));
  vo.setJobStatusNameEn(pipelineRunDetail.getStatus());  // 新增
  vo.setJobName(pipelineRunDetail.getName());
  vo.setJobUrl(...);
  return vo;
}
```

[PipelineServiceImpl.java:5347-5360](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L5347-L5360)（子任务行）：

```java
private CommentTableVo buildCommentTableVo(
    JobRun job, String jobTypeCode, Map<String, PipelineJobTypVO> pipelineJobTypeMap, String openlibingUrl) {
  // ...
  CommentTableVo commentTableVo = new CommentTableVo();
  commentTableVo.setJobType(jobTypeName);
  commentTableVo.setJobStatusAscii(PipelineJobStatusEnums.getAsciiCodeByNameEn(job.getStatus()));
  commentTableVo.setJobStatusNameEn(job.getStatus());  // 新增
  commentTableVo.setJobName(job.getName());
  commentTableVo.setJobUrl(openlibingUrl);
  return commentTableVo;
}
```

### 3.5 `prepareCommentTable` 渲染状态列

[PipelineServiceImpl.java:6849-6853](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L6849-L6853)：

**改造前**：

```java
stringBuilder
    .append("        <td>&#")
    .append(commentTableVos.get(i).getJobStatusAscii())
    .append(";</td>\n");
```

**改造后**：

```java
stringBuilder
    .append("        <td>&#")
    .append(commentTableVos.get(i).getJobStatusAscii())
    .append("; ")
    .append(commentTableVos.get(i).getJobStatusNameEn())
    .append("</td>\n");
```

渲染示例：

- INIT: `<td>&#128995; INIT</td>` → 🟧 INIT
- COMPLETED: `<td>&#9989; COMPLETED</td>` → ✅ COMPLETED
- SKIPPED: `<td>&#9193; SKIPPED</td>` → ⏭ SKIPPED
- UNSELECTED: `<td>&#11036; UNSELECTED</td>` → ⬜ UNSELECTED

### 3.6 不涉及的关键模块

| 模块                                                           | 是否影响 | 说明                                                     |
| -------------------------------------------------------------- | -------- | -------------------------------------------------------- |
| `savePipelineInfoWithAsyncPrOps` 幂等判断                      | 否       | 仅比较 `status`，未读取 `ascii_code` / `jobStatusNameEn` |
| `saveBuildCheck` 门禁结果存库                                  | 需回归   | 见 4.2 兼容性分析                                        |
| `updatePrLabel` / `pushGitCodeCommitStatus`                    | 否       | 不依赖 `ascii_code` / `jobStatusNameEn`                  |
| `PipelineStatusUpdateMessage` / `PipelineStatusUpdateConsumer` | 否       | 不涉及 `ascii_code`                                      |
| `PipelineStartEventHandler` / `PrOpEventConsumer`              | 否       | 不涉及渲染                                               |
| `prepareCommentTableTopInfo` / `prepareCommentTableEndInfo`    | 否       | 表头表尾不变                                             |

## 4. 兼容性与边界

### 4.1 `getAsciiCodeByNameEn` 静态方法

[PipelineJobStatusEnums.java:15-26](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/common/enums/PipelineJobStatusEnums.java#L15-L26) 中 `getAsciiCodeByNameEn` 通过 `nameEn` 查找 `ascii_code`，未改 `nameEn`，方法逻辑无需修改，自动返回新值。

### 4.2 `saveBuildCheck` 兼容性

[PipelineServiceImpl.java:6876-6890](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L6876-L6890) `saveBuildCheck` 用 `COMPLETED.ascii_code`（`9989`）作为成功判定基准：

```java
buildCheckDTO.setState(
    PipelineJobStatusEnums.COMPLETED.getAscii_code().equals(tableVo.getJobStatusAscii())
        ? "success"
        : "failed");
```

本次改造：

- `COMPLETED.ascii_code` 保持 `9989` 不变 → 成功判定基准不变。
- SKIPPED / IGNORED / UNSELECTED 的 `ascii_code` 改为非 `9989` 的值 → 仍判定为 `failed`，行为不变。
- 新增 `jobStatusNameEn` 字段未被 `saveBuildCheck` 使用 → 不影响。

> 需要回归测试覆盖：COMPLETED 任务判定为 `success`，其他状态判定为 `failed`，与改造前一致。

### 4.3 `CommentTableVo` 调用点兼容性

全仓搜索 `new CommentTableVo(...)` 调用点（除 `@NoArgsConstructor` + setter 链外的全参构造）：

- `buildCommentTableVo`（2 个重载）已用 setter 链，新增字段不影响。
- 其他类如 `saveBuildCheck` 仅读 `getJobStatusAscii` / `getJobName` / `getJobUrl`，不读 `jobStatusNameEn`，兼容。

### 4.4 边界场景

| 场景                                                        | 行为                                                                                                                            |
| ----------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------- |
| 历史已发布的 PR 评论中含旧 emoji（如 ⏱）                    | 不主动迁移，新评论按新 emoji + 英文名渲染                                                                                       |
| 第三方调用 `getAsciiCodeByNameEn("INIT")` 拿到 `128995`     | 自动得到新 emoji，无需调用方修改                                                                                                |
| `prepareCommentTable` 渲染 `&#128995; INIT`                 | 浏览器/邮件客户端支持 Unicode emoji，正常渲染为 `🟧 INIT`                                                                       |
| 极少数老客户端不支持 `&#128995;` 等 Unicode 较新字符        | 退化显示为方框或空白 + 英文名，不影响功能                                                                                       |
| `pipelineRunDetail.getStatus()` / `job.getStatus()` 为 null | `setJobStatusNameEn(null)` → 渲染输出 `&#<ascii>; null`，需在调用前过滤或回归验证华为云不会返回 null（华为云正常不会返回 null） |

## 5. 测试策略

### 5.1 单元测试新增

**`PrepareCommentTableTest`**（渲染格式与枚举值联合回归，通过 `PipelineJobStatusEnums.getAsciiCodeByNameEn` 间接覆盖 6 个新 ascii_code 与 5 个未变状态）：

- 渲染 COMPLETED 状态输出 `<td>&#9989; COMPLETED</td>`
- 渲染 SKIPPED 状态输出 `<td>&#9193; SKIPPED</td>`
- 渲染 INIT 状态输出 `<td>&#128995; INIT</td>`
- 渲染 UNSELECTED 状态输出 `<td>&#11036; UNSELECTED</td>`
- 渲染 RUNNING 状态输出 `<td>&#9654; RUNNING</td>`
- 渲染 QUEUED 状态输出 `<td>&#128346; QUEUED</td>`
- 渲染 FAILED 状态输出 `<td>&#10060; FAILED</td>`
- 渲染 SUSPEND 状态输出 `<td>&#128997; SUSPEND</td>`
- 渲染 IGNORED 状态输出 `<td>&#9898; IGNORED</td>`
- 多任务同阶段（`rowspan` 渲染）、多阶段混合渲染场景
- `tableData` 为空 / null / `pipelineStatus=QUEUED` 时仅返回 `commentTableTop`，不渲染表格主体（保留现有逻辑）
- 表头列顺序保持现状（阶段 / 任务名 / 状态 / 详情），表尾内容保持现状

### 5.2 现有测试回归

- `PipelineStartEventHandlerTest`
- `PipelineStopEventHandlerTest`
- `PipelineRetryEventHandlerTest`
- `PrOpEventConsumerTest`
- 涉及 `saveBuildCheck` 的测试（确认 `success` 判定仍按 `9989` 基准）
- 涉及 `CommentTableVo` 全参构造的测试（如有）

### 5.3 手动验收

- 触发一次 PR 评论流水线（如评论触发或 webhook 触发）。
- 检查 PR 评论表格中各状态 emoji + 英文名渲染：
  - INIT 渲染为 `🟧 INIT`
  - RUNNING 渲染为 `▶ RUNNING`
  - SUSPEND 渲染为 `🟪 SUSPEND`
  - SKIPPED 渲染为 `⏭ SKIPPED`
  - IGNORED 渲染为 `⚪ IGNORED`
  - UNSELECTED 渲染为 `⬜ UNSELECTED`
  - QUEUED / COMPLETED / CANCELED / FAILED / PAUSED 沿用原 emoji + 英文名。

## 6. 实现步骤

参见 `tasks.md`。
