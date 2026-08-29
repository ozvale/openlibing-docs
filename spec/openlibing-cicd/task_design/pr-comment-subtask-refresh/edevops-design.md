# EDEVOPS 设计文档：pr-comment-subtask-refresh

> 关联 Issue: openlibing-cicd#207
> 流程模式: Standard
> 评审调整（2026-08-21）：经评审，"子任务状态变化触发评论刷新"不再需要，本次保留"任务状态 emoji 优化 + 状态英文名追加"。

## 1. 方案设计

### 1.1 目标

1. 通过调整 `PipelineJobStatusEnums` 中部分状态的 `ascii_code` 字段值，解决 PR 评论中多个状态共用同一 emoji、辨识度低的问题。
2. 在状态列 emoji 后追加状态英文名（`nameEn`），提升可读性，例如 `🟣 INIT`、`✅ COMPLETED`。

### 1.2 范围

| 项         | 是否涉及                                                                           |
| ---------- | ---------------------------------------------------------------------------------- |
| 业务仓文件 | `PipelineJobStatusEnums.java` / `CommentTableVo.java` / `PipelineServiceImpl.java` |
| 测试文件   | `PrepareCommentTableTest.java`（新增）                                             |
| 消息流转   | 否（`PipelineStatusUpdateMessage` / `PipelineStatusUpdateConsumer` 不动）          |
| DB schema  | 否                                                                                 |
| 配置文件   | 否                                                                                 |
| RabbitMQ   | 否                                                                                 |

### 1.3 核心思路

1. **emoji 优化**：`prepareCommentTable` 渲染状态列时直接输出 `&#<ascii_code>;`，因此**只修改枚举字段值**即可让渲染链路自然输出新 emoji，无需改渲染方法。
2. **状态英文名追加**：在 `CommentTableVo` 新增 `jobStatusNameEn` 字段，由 `buildCommentTableVo` 填充，`prepareCommentTable` 渲染时拼接 `<emoji> <nameEn>` 格式。

### 1.4 关键技术决策

| 决策点                       | 选择                                                                              | 理由                                                                                                  |
| ---------------------------- | --------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 改动范围                     | `PipelineJobStatusEnums.ascii_code` + `CommentTableVo.jobStatusNameEn` + 渲染拼接 | 评审删除指纹方案后，仅剩 UI 视觉调整，最小变更                                                        |
| 是否新增字段                 | 是，仅 `CommentTableVo.jobStatusNameEn`（状态英文名）                             | 评审要求 emoji 后追加状态英文名，需要承载该数据的字段                                                 |
| 是否改渲染方法               | 是，仅 `prepareCommentTable` 状态列拼接逻辑追加 ` <nameEn>`                       | 评审要求渲染输出 `<emoji> <nameEn>` 格式                                                              |
| 是否需要 DB 迁移             | 否                                                                                | 枚举字段值与新增 VO 字段均不落库                                                                      |
| `saveBuildCheck` 兼容性      | 兼容                                                                              | `COMPLETED.ascii_code=9989` 不变，成功判定基准不变；新增 `jobStatusNameEn` 未被 `saveBuildCheck` 使用 |
| `nameEn` / `nameCn` 是否改动 | 不动                                                                              | 仅改 `ascii_code`，避免牵连调用方                                                                     |
| 是否追加中文名               | 否                                                                                | 评审要求仅追加英文名（如 `INIT` / `COMPLETED`），不追加中文名                                         |

## 2. 实现逻辑

### 2.1 实现流程

```
开发阶段：
  T1 修改 PipelineJobStatusEnums 6 个状态 ascii_code
   │
   ▼
  T2 CommentTableVo 新增 jobStatusNameEn 字段
   │
   ▼
  T3 buildCommentTableVo（2 个重载）填充 jobStatusNameEn
   │
   ▼
  T4 prepareCommentTable 渲染状态列追加英文名
   │
   ▼
  T5 编写 PrepareCommentTableTest 单元测试（反射调用 prepareCommentTable，覆盖渲染格式与枚举值回归）
   │
   ▼
  T6 回归现有测试（含 saveBuildCheck 相关测试）
   │
   ▼
  T7 手动验收 PR 评论渲染
```

### 2.2 改造前后对照

| nameEn     | nameCn     | 原 ascii_code | 新 ascii_code  | 原 emoji | 新 emoji | 渲染格式（改后） |
| ---------- | ---------- | ------------- | -------------- | -------- | -------- | ---------------- |
| INIT       | 初始化     | 128346        | **128995**     | ⏱        | 🟣       | `🟣 INIT`        |
| QUEUED     | 排队中     | 128346        | 128346（不变） | ⏱        | ⏱        | `⏱ QUEUED`       |
| COMPLETED  | 已完成     | 9989          | 9989（不变）   | ✅       | ✅       | `✅ COMPLETED`   |
| RUNNING    | 运行中     | 128346        | **9654**       | ⏱        | ▶        | `▶ RUNNING`      |
| CANCELED   | 已终止运行 | 129000        | 129000（不变） | 🔴       | 🔴       | `🔴 CANCELED`    |
| FAILED     | 运行失败   | 10060         | 10060（不变）  | ❌       | ❌       | `❌ FAILED`      |
| PAUSED     | 已暂停     | 128721        | 128721（不变） | ⛔       | ⛔       | `⛔ PAUSED`      |
| SUSPEND    | 已挂起     | 128721        | **128997**     | ⛔       | 🟥       | `🟥 SUSPEND`     |
| SKIPPED    | 已跳过     | 128721        | **9193**       | ⛔       | ⏭        | `⏭ SKIPPED`      |
| IGNORED    | 已忽略     | 128721        | **9898**       | ⛔       | ⚪       | `⚪ IGNORED`     |
| UNSELECTED | 无法查询   | 10060         | **11036**      | ❌       | ⬜       | `⬜ UNSELECTED`  |

### 2.3 emoji 选择理由

| 状态       | 新 emoji | Unicode 名称                                           | 选择理由                                  |
| ---------- | -------- | ------------------------------------------------------ | ----------------------------------------- |
| INIT       | 🟣       | LARGE PURPLE CIRCLE                                    | 区别于 QUEUED/RUNNING 的"等待启动"提示    |
| RUNNING    | ▶        | BLACK RIGHT-POINTING TRIANGLE                          | 直觉性"播放/运行中"符号                   |
| SUSPEND    | 🟥       | LARGE RED SQUARE                                       | 与 PAUSED（⛔）及 CANCELED（🔴）区分      |
| SKIPPED    | ⏭        | BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR | "快进/跳过"直觉性符号                     |
| IGNORED    | ⚪       | MEDIUM WHITE CIRCLE                                    | "空白/忽略"的视觉感                       |
| UNSELECTED | ⬜       | WHITE LARGE SQUARE                                     | "未选中/空白槽位"，与 FAILED（❌）区分    |

### 2.4 渲染链路（改造后）

```
PipelineJobStatusEnums.INIT.ascii_code = "128995"   ← 字段值变化
   │
   ▼
buildCommentTableVo(...).setJobStatusAscii("128995")
buildCommentTableVo(...).setJobStatusNameEn("INIT")  ← 新增字段填充
   │
   ▼
CommentTableVo.jobStatusAscii = "128995"
CommentTableVo.jobStatusNameEn = "INIT"
   │
   ▼
prepareCommentTable 输出 "<td>&#128995; INIT</td>"  ← 拼接 emoji + 空格 + 英文名
   │
   ▼
PR 评论 HTML 渲染为 "🟣 INIT"
```

### 2.5 边界场景

| 场景                                                        | 行为                                                                                                        |
| ----------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| 历史已发布的 PR 评论含旧 emoji（如 ⏱）                      | 不主动迁移，新评论按新 emoji + 英文名渲染                                                                   |
| 第三方调用 `getAsciiCodeByNameEn("INIT")` 拿到 `128995`     | 自动得到新 emoji，无需调用方修改                                                                            |
| `prepareCommentTable` 渲染 `&#128995; INIT`                 | 浏览器/邮件客户端支持 Unicode emoji，正常渲染为 `🟣 INIT`                                                   |
| 极少数老客户端不支持较新 Unicode 字符                       | 退化显示为方框或空白 + 英文名，不阻塞功能                                                                   |
| `pipelineRunDetail.getStatus()` / `job.getStatus()` 为 null | `setJobStatusNameEn(null)` → 渲染输出 `&#<ascii>; null`，需回归验证华为云不会返回 null（正常不会返回 null） |

### 2.6 异常处理

本次改造为枚举字段值替换 + VO 字段新增 + 渲染拼接追加，无新增异常路径。仅需关注：

| 异常                                    | 触发                                        | 处理                                                        |
| --------------------------------------- | ------------------------------------------- | ----------------------------------------------------------- |
| 单元测试断言失败                        | `getAsciiCodeByNameEn` 返回值与预期不符     | 修正枚举字段值或测试断言                                    |
| 渲染测试断言失败                        | `prepareCommentTable` 输出不含 ` <nameEn>`  | 修正拼接逻辑或测试断言                                      |
| 现有测试回归失败                        | 第三方代码硬编码 `ascii_code=128346` 等旧值 | 全仓搜索定位硬编码点，与用户确认是否调整                    |
| `CommentTableVo` 全参构造调用点编译失败 | `@AllArgsConstructor` 参数数量变化          | 全仓搜索 `new CommentTableVo(`，更新为 5 参构造或 setter 链 |

## 3. 类设计

### 3.1 `PipelineJobStatusEnums`

[PipelineJobStatusEnums.java:15-26](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/common/enums/PipelineJobStatusEnums.java#L15-L26)

**改造前**：

```java
public enum PipelineJobStatusEnums {
    INIT("INIT", "初始化", "128346"),
    QUEUED("QUEUED", "排队中", "128346"),
    COMPLETED("COMPLETED", "已完成", "9989"),
    RUNNING("RUNNING", "运行中", "128346"),
    CANCELED("CANCELED", "已终止运行", "129000"),
    FAILED("FAILED", "运行失败", "10060"),
    PAUSED("PAUSED", "已暂停", "128721"),
    SUSPEND("SUSPEND", "已挂起", "128721"),
    SKIPPED("SKIPPED", "已跳过", "128721"),
    IGNORED("IGNORED", "已忽略", "128721"),
    UNSELECTED("UNSELECTED", "无法查询", "10060");
    // 构造器 / getter / 静态方法...
}
```

**改造后**：

```java
public enum PipelineJobStatusEnums {
    INIT("INIT", "初始化", "128995"),          // ⏱ → 🟣
    QUEUED("QUEUED", "排队中", "128346"),      // 沿用
    COMPLETED("COMPLETED", "已完成", "9989"),   // 沿用
    RUNNING("RUNNING", "运行中", "9654"),       // ⏱ → ▶
    CANCELED("CANCELED", "已终止运行", "129000"), // 沿用
    FAILED("FAILED", "运行失败", "10060"),      // 沿用
    PAUSED("PAUSED", "已暂停", "128721"),        // 沿用
    SUSPEND("SUSPEND", "已挂起", "128997"),      // ⛔ → 🟥
    SKIPPED("SKIPPED", "已跳过", "9193"),        // ⛔ → ⏭
    IGNORED("IGNORED", "已忽略", "9898"),        // ⛔ → ⚪
    UNSELECTED("UNSELECTED", "无法查询", "11036"); // ❌ → ⬜
    // 构造器 / getter / 静态方法保持不变
}
```

**改动清单**：

- `INIT.ascii_code`: `128346` → `128995`
- `RUNNING.ascii_code`: `128346` → `9654`
- `SUSPEND.ascii_code`: `128721` → `128997`
- `SKIPPED.ascii_code`: `128721` → `9193`
- `IGNORED.ascii_code`: `128721` → `9898`
- `UNSELECTED.ascii_code`: `10060` → `11036`

**未改动**：

- `nameEn` / `nameCn` 字段值
- 构造器、字段定义、`@Getter` / `@AllArgsConstructor` 等注解
- `getEnumByNameEn` / `getAsciiCodeByNameEn` 等静态方法实现

### 3.2 `CommentTableVo`

[CommentTableVo.java](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/vo/CommentTableVo.java)

**改造前**：

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

**改造后**：

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

**兼容性**：

- `@AllArgsConstructor` 新增字段位于末尾，4 参构造器变为 5 参构造器。
- `@NoArgsConstructor` + `@Data` 提供 setter 链，所有调用点应改用 setter 链（如 `buildCommentTableVo` 已用 setter 链）。
- 全仓搜索 `new CommentTableVo(...)` 全参构造调用点（如有），更新为 5 参或改用 setter。

### 3.3 `PipelineServiceImpl`

#### 3.3.1 `buildCommentTableVo`（流水线整体行）

[PipelineServiceImpl.java:5326-5345](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L5326-L5345)

**改造前**：

```java
private CommentTableVo buildCommentTableVo(
    PipelineParamDTO param, ShowPipelineRunDetailResponse pipelineRunDetail, String projectId) {
  CommentTableVo vo = new CommentTableVo();
  vo.setJobType(PipelineJobTypeEnums.PIPELINE.getNameCn());
  vo.setJobStatusAscii(
      PipelineJobStatusEnums.getAsciiCodeByNameEn(pipelineRunDetail.getStatus()));
  vo.setJobName(pipelineRunDetail.getName());
  vo.setJobUrl(...);
  return vo;
}
```

**改造后**：

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

#### 3.3.2 `buildCommentTableVo`（子任务行）

[PipelineServiceImpl.java:5347-5360](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L5347-L5360)

**改造前**：

```java
private CommentTableVo buildCommentTableVo(
    JobRun job, String jobTypeCode, Map<String, PipelineJobTypVO> pipelineJobTypeMap, String openlibingUrl) {
  // ...
  CommentTableVo commentTableVo = new CommentTableVo();
  commentTableVo.setJobType(jobTypeName);
  commentTableVo.setJobStatusAscii(PipelineJobStatusEnums.getAsciiCodeByNameEn(job.getStatus()));
  commentTableVo.setJobName(job.getName());
  commentTableVo.setJobUrl(openlibingUrl);
  return commentTableVo;
}
```

**改造后**：

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

#### 3.3.3 `prepareCommentTable` 状态列渲染

[PipelineServiceImpl.java:6849-6853](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L6849-L6853)

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

#### 3.3.4 `saveBuildCheck`（未改动）

[PipelineServiceImpl.java:6876-6890](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L6876-L6890) 未改：

```java
buildCheckDTO.setState(
    PipelineJobStatusEnums.COMPLETED.getAscii_code().equals(tableVo.getJobStatusAscii())
        ? "success"
        : "failed");
```

- `COMPLETED.ascii_code=9989` 不变 → 成功判定基准不变。
- 新增 `jobStatusNameEn` 字段未被 `saveBuildCheck` 使用 → 不影响。

## 4. 数据模型

无新增表、无新增字段、无 DB 迁移。

`PipelineJobStatusEnums.ascii_code` 字段为内存枚举值，不落库。`CommentTableVo.jobStatusNameEn` 为内存 VO 字段，不落库。`saveBuildCheck` 将状态写入 `pipeline_build_check` 表的 `status` 字段（存储 `nameEn` 字符串，如 `SKIPPED`），不依赖 `ascii_code` 与 `jobStatusNameEn`。

## 5. 接口设计

无新增接口、无接口签名变化。

## 6. 部署与配置

### 6.1 部署形态

- 标准业务仓发版，无独立服务。
- 无新增配置项、无新增环境变量。

### 6.2 回滚策略

如新 emoji + 英文名在生产环境渲染异常，可通过回滚 `PipelineJobStatusEnums.java` / `CommentTableVo.java` / `PipelineServiceImpl.java` 三个文件提交恢复原渲染。无 DB 数据回滚负担。

## 7. 风险与缓解

| 风险                                        | 影响 | 缓解                                                           |
| ------------------------------------------- | ---- | -------------------------------------------------------------- |
| 第三方代码硬编码 `ascii_code=128346` 等旧值 | 中   | T7 回归测试覆盖，全仓搜索 `128346` / `128721` / `10060` 调用点 |
| `saveBuildCheck` 行为变化                   | 中   | `COMPLETED.ascii_code=9989` 不变，T7 覆盖                      |
| `CommentTableVo` 全参构造调用点编译失败     | 中   | 全仓搜索 `new CommentTableVo(`，更新为 5 参构造或 setter 链    |
| 老客户端不支持较新 Unicode emoji            | 低   | 仅视觉退化，不阻塞功能                                         |
| 旧 PR 评论保留旧 emoji                      | 低   | 不主动迁移，新评论按新值 + 英文名渲染                          |

## 8. 测试设计

### 8.1 单元测试

**`PrepareCommentTableTest`**（渲染格式与枚举值联合回归，通过 `PipelineJobStatusEnums.getAsciiCodeByNameEn` 间接覆盖 6 个新 ascii_code 与 5 个未变状态）：

| 用例                    | 预期输出包含                                                            |
| ----------------------- | ----------------------------------------------------------------------- |
| 渲染 COMPLETED 状态     | `<td>&#9989; COMPLETED</td>`                                            |
| 渲染 SKIPPED 状态       | `<td>&#9193; SKIPPED</td>`                                              |
| 渲染 INIT 状态          | `<td>&#128995; INIT</td>`                                               |
| 渲染 UNSELECTED 状态    | `<td>&#11036; UNSELECTED</td>`                                          |
| 渲染 RUNNING 状态       | `<td>&#9654; RUNNING</td>`                                              |
| 渲染 QUEUED 状态        | `<td>&#128346; QUEUED</td>`                                             |
| 渲染 FAILED 状态        | `<td>&#10060; FAILED</td>`                                              |
| 渲染 SUSPEND 状态       | `<td>&#128997; SUSPEND</td>`                                            |
| 渲染 IGNORED 状态       | `<td>&#9898; IGNORED</td>`                                              |
| 多任务同阶段            | `<td rowspan="N">` + 各任务状态行                                       |
| 多阶段混合              | 各阶段状态行依次渲染                                                    |
| `tableData` 为空        | 仅返回 `commentTableTop`，不含 `<table class="access-control-table"`    |
| `tableData` 为 null     | 仅返回 `commentTableTop`，不含 `<table class="access-control-table"`    |
| `pipelineStatus=QUEUED` | 仅返回 `commentTableTop`，不渲染表格主体                                |
| 表头列顺序              | `<th>阶段</th>` / `<th>任务名</th>` / `<th>状态</th>` / `<th>详情</th>` |
| 表尾内容                | 保持现状                                                                |

### 8.2 回归测试

- `PipelineStartEventHandlerTest` / `PipelineStopEventHandlerTest` / `PipelineRetryEventHandlerTest`
- `PrOpEventConsumerTest`
- 涉及 `saveBuildCheck` 的测试：确认 `COMPLETED` 任务判定为 `success`，其他状态判定为 `failed`，与改造前一致。
- 涉及 `CommentTableVo` 全参构造的测试（如有）：更新为 5 参构造或 setter 链。

### 8.3 手动验收

- 触发一次 PR 评论流水线（评论触发或 webhook 触发）。
- 检查 PR 评论表格中各状态 emoji + 英文名渲染符合 2.2 表格。

## 9. 上线与监控

### 9.1 上线步骤

1. 业务仓合并 PR 至目标 Release 分支。
2. 标准 CI/CD 流水线发版。
3. 验证线上 PR 评论新 emoji + 英文名渲染正常。

### 9.2 监控指标

- 无新增监控项。
- 现有 PR 评论发送成功率、API 限流告警保持原监控覆盖。

## 10. 向后兼容性

| 场景                                                         | 兼容性                                        |
| ------------------------------------------------------------ | --------------------------------------------- |
| 第三方调用 `getAsciiCodeByNameEn(...)` 拿到新 ascii_code     | 自动获得新 emoji，无需调用方修改              |
| `saveBuildCheck` 用 `9989` 判定成功                          | 兼容（COMPLETED.ascii_code 未变）             |
| 已落库的 `pipeline_build_check.status` 字段（nameEn 字符串） | 兼容（不依赖 ascii_code）                     |
| 旧 PR 评论 HTML 中保留 `&#128346;` 等旧 emoji                | 兼容（不主动迁移）                            |
| `CommentTableVo` 全参构造调用点                              | 需更新为 5 参构造或 setter 链                 |
| `CommentTableVo` 反序列化（如 JSON）                         | 兼容（新增字段为可选，反序列化时缺省为 null） |

## 11. 关联资源

- Proposal: [proposal.md](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-docs/spec/openlibing-cicd/task_design/pr-comment-subtask-refresh/proposal.md)
- Design: [design.md](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-docs/spec/openlibing-cicd/task_design/pr-comment-subtask-refresh/design.md)
- Tasks: [tasks.md](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-docs/spec/openlibing-cicd/task_design/pr-comment-subtask-refresh/tasks.md)
- 业务仓 Issue: openlibing-cicd#207
