# 任务清单：pr-comment-subtask-refresh

> 关联 Proposal: `proposal.md`
> 关联 Design: `design.md`
> 关联 Issue: openlibing-cicd#207
> 流程模式: Standard

## 任务总览

| ID  | 任务                                                                          | 优先级 | 依赖   | 状态                  |
| --- | ----------------------------------------------------------------------------- | ------ | ------ | --------------------- |
| T1  | 修改 `PipelineJobStatusEnums` 6 个状态的 `ascii_code`                         | 高     | 无     | ✅ 完成               |
| T2  | `CommentTableVo` 新增 `jobStatusNameEn` 字段                                  | 高     | 无     | ✅ 完成               |
| T3  | `buildCommentTableVo`（2 个重载）填充 `jobStatusNameEn`                       | 高     | T2     | ✅ 完成               |
| T4  | `prepareCommentTable` 渲染状态列追加英文名（含左对齐 + 内边距，自测反馈追加） | 高     | T2、T3 | ✅ 完成               |
| T5  | 新增 `PrepareCommentTableTest` 单元测试（覆盖渲染格式与枚举值回归）           | 高     | T1-T4  | ✅ 完成（15/15 通过） |
| T6  | 回归现有测试                                                                  | 中     | T1-T5  | ✅ 完成               |
| T7  | 手动验收 PR 评论渲染                                                          | 中     | T1-T6  | ✅ 完成（PR #557）    |

> 追加任务（自测反馈）：状态列左对齐 + 8px 内边距 — commit `b1a393d5`，✅ 完成

## 详细任务

### T1. 修改 `PipelineJobStatusEnums` 6 个状态的 `ascii_code`

- 文件：[PipelineJobStatusEnums.java](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/common/enums/PipelineJobStatusEnums.java)
- 改动：

  ```java
  // 修改前
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

  // 修改后（仅 6 个状态的 ascii_code 变化，nameEn/nameCn 不动）
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
  ```

- 不改动：构造器、字段、getter、`getEnumByNameEn` / `getAsciiCodeByNameEn` 等方法。
- 验证：本地编译通过。

### T2. `CommentTableVo` 新增 `jobStatusNameEn` 字段

- 文件：[CommentTableVo.java](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/vo/CommentTableVo.java)
- 改动：

  ```java
  // 修改前
  @Data
  @AllArgsConstructor
  @NoArgsConstructor
  public class CommentTableVo {
    private String jobType;
    private String jobName;
    private String jobStatusAscii;
    private String jobUrl;
  }

  // 修改后（新增 jobStatusNameEn 字段）
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

- 兼容性：`@AllArgsConstructor` 新增字段位于末尾，既有 4 参构造调用需改为 setter 或全参构造。`buildCommentTableVo` 已用 setter 链，无影响。
- 验证：本地编译通过。

### T3. `buildCommentTableVo`（2 个重载）填充 `jobStatusNameEn`

- 文件：[PipelineServiceImpl.java](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java)
- 改动 1（[5326-5345 行](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L5326-L5345)，流水线整体行）：

  ```java
  // 在 vo.setJobStatusAscii(...) 之后追加
  vo.setJobStatusNameEn(pipelineRunDetail.getStatus());
  ```

- 改动 2（[5347-5360 行](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L5347-L5360)，子任务行）：

  ```java
  // 在 commentTableVo.setJobStatusAscii(...) 之后追加
  commentTableVo.setJobStatusNameEn(job.getStatus());
  ```

- 验证：本地编译通过。

### T4. `prepareCommentTable` 渲染状态列追加英文名

- 文件：[PipelineServiceImpl.java](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java)
- 改动（[6849-6853 行](file:///d:/CODE/JAVACODE/AIDev/openlibing/openlibing-cicd/src/main/java/com/openlibing/cicd/business/service/impl/PipelineServiceImpl.java#L6849-L6853)）：

  ```java
  // 修改前
  stringBuilder
      .append("        <td>&#")
      .append(commentTableVos.get(i).getJobStatusAscii())
      .append(";</td>\n");

  // 修改后（追加空格 + 状态英文名）
  stringBuilder
      .append("        <td>&#")
      .append(commentTableVos.get(i).getJobStatusAscii())
      .append("; ")
      .append(commentTableVos.get(i).getJobStatusNameEn())
      .append("</td>\n");
  ```

- 渲染示例：
  - INIT: `<td>&#128995; INIT</td>` → 🟣 INIT
  - COMPLETED: `<td>&#9989; COMPLETED</td>` → ✅ COMPLETED
  - SKIPPED: `<td>&#9193; SKIPPED</td>` → ⏭ SKIPPED
- 验证：本地编译通过。

### T5. 新增 `PrepareCommentTableTest` 单元测试（覆盖渲染格式与枚举值回归）

- 文件：`openlibing-cicd/src/test/java/com/openlibing/cicd/business/service/impl/PrepareCommentTableTest.java`（如不存在则新建）
- 用例：
  - 渲染 COMPLETED 状态输出包含 `<td>&#9989; COMPLETED</td>`
  - 渲染 SKIPPED 状态输出包含 `<td>&#9193; SKIPPED</td>`
  - 渲染 INIT 状态输出包含 `<td>&#128995; INIT</td>`
  - 渲染 UNSELECTED 状态输出包含 `<td>&#11036; UNSELECTED</td>`
  - 渲染 RUNNING 状态输出包含 `<td>&#9654; RUNNING</td>`
  - 渲染 QUEUED 状态输出包含 `<td>&#128346; QUEUED</td>`（pipelineStatus=RUNNING 触发渲染）
  - 渲染 FAILED 状态输出包含 `<td>&#10060; FAILED</td>`
  - 渲染 SUSPEND 状态输出包含 `<td>&#128997; SUSPEND</td>`
  - 渲染 IGNORED 状态输出包含 `<td>&#9898; IGNORED</td>`
  - 多任务同阶段（`rowspan` 渲染）、多阶段混合渲染场景
  - `tableData` 为空 / null / `pipelineStatus=QUEUED` 时仅返回 `commentTableTop`，不渲染表格主体（保留现有逻辑）
  - 表头列顺序保持现状（阶段 / 任务名 / 状态 / 详情），表尾内容保持现状
- 说明：本测试通过反射调用私有方法 `prepareCommentTable`，并使用 `PipelineJobStatusEnums.getAsciiCodeByNameEn` 间接覆盖 6 个新 ascii_code 与 5 个未变状态，不再单独编写 `PipelineJobStatusEnumsTest`。
- 验证：`mvn test -Dtest=PrepareCommentTableTest` 全部通过。

### T6. 回归现有测试

- 命令：`mvn test`
- 关注：
  - `PipelineStartEventHandlerTest` / `PipelineStopEventHandlerTest` / `PipelineRetryEventHandlerTest` / `PrOpEventConsumerTest` 等通过。
  - 涉及 `saveBuildCheck` 的测试通过（确认 `success` 判定仍按 `9989` 基准，行为不变）。
  - 涉及 `CommentTableVo` 全参构造的测试（如有）需更新参数。
- 验证：无回归失败。

### T7. 手动验收

- 触发一次 PR 评论流水线（如评论触发或 webhook 触发）。
- 检查 PR 评论表格中各状态 emoji + 英文名渲染：
  - INIT 渲染为 `� INIT`
  - RUNNING 渲染为 `▶ RUNNING`
  - SUSPEND 渲染为 `� SUSPEND`
  - SKIPPED 渲染为 `⏭ SKIPPED`
  - IGNORED 渲染为 `⚪ IGNORED`
  - UNSELECTED 渲染为 `⬜ UNSELECTED`
  - QUEUED / COMPLETED / CANCELED / FAILED / PAUSED 沿用原 emoji + 英文名。
- 验证：与 design.md 3.1 表格一致。

## 风险与缓解

| 风险                                                           | 缓解                                                                |
| -------------------------------------------------------------- | ------------------------------------------------------------------- |
| 第三方代码依赖 `INIT` / `RUNNING` 等状态的 `ascii_code=128346` | 全仓搜索 `128346` / `getAsciiCodeByNameEn` 调用点，确认无硬编码依赖 |
| `saveBuildCheck` 行为变化                                      | T7 回归测试覆盖                                                     |
| `CommentTableVo` 全参构造调用点未更新                          | 全仓搜索 `new CommentTableVo(`，更新为 5 参构造或 setter 链         |
| 老客户端不支持较新 Unicode emoji（如 � � ⬜）                | 仅影响视觉，不阻塞功能                                              |
| 旧 PR 评论中保留旧 emoji                                       | 不主动迁移，新评论按新值 + 英文名渲染                               |

## 不做的事

- 不修改 `savePipelineInfoWithAsyncPrOps`（不做指纹方案）。
- 不新增 `subtaskFingerprint` / `lastSubtaskFingerprint` 字段。
- 不修改 `PipelineStatusUpdateMessage` / `PipelineStatusUpdateConsumer` 等消息相关类。
- 不修改 `PipelineParamDTO`。
- 不修改 RabbitMQ 配置。
- 不修改 `nameEn` / `nameCn` 字段。
- 不修改 `prepareCommentTableTopInfo` / `prepareCommentTableEndInfo`。
- 不修改 `updatePrLabel` / `pushGitCodeCommitStatus`。
- 不修改 `saveBuildCheck` 的成功判定逻辑。
- 不追加中文状态名（仅追加英文名 `nameEn`）。
