# pr-comment-multi-cmd — 技术设计

## 方案概述

在 `PipelineStartEventHandler.prNoteStartPipeline` 中，将用户配置的 `eventComment` 按 `|` 拆分为多个命令并逐个 trim，PR 评论同样 trim 后，检查是否以任一配置命令开头（前缀匹配，兼容带流水线名称的场景）；不带流水线名称的纯命令场景则检查是否与任一配置命令精确相等。

## 架构决策

1. **按 `|` 拆分配置命令**：`|` 在常见命令词中不会出现，作为分隔符安全；拆分后逐个 `trim` 并过滤空串，兼容 `/start | /run | /go` 这类带空格的配置写法。
2. **PR 评论统一 trim**：对 `prComment` 做一次 `trim`，避免评论前后空白导致匹配失败；评论内部空白（如 `/run pipeline1` 中的空格）保留，不影响 `parseStartPipelineNames` 解析。
3. **前缀匹配 + 精确匹配分层**：
   - 第一层（前缀匹配）：`trimmedPrComment.startsWith(cmd)` —— 兼容 `/run pipeline1,pipeline2` 这种带参数的评论。
   - 第二层（精确匹配）：当 `parseStartPipelineNames` 返回空列表（即评论不带流水线名称）时，要求 `trimmedPrComment` 与任一配置命令精确相等，避免 `/start` 误匹配 `/start-xxx` 这类前缀重叠的配置。
4. **单命令向后兼容**：单命令配置（如 `/start`）经 `parseConfiguredCommands` 处理后得到 `["/start"]`，匹配逻辑等价于改动前。
5. **不改动 `parseStartPipelineNames`**：该函数负责从评论中解析流水线名称列表（按逗号分隔），与多命令配置正交，保持原逻辑。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `business/listener/PipelineStartEventHandler.java` | 修改 | `prNoteStartPipeline` 两处命令校验改用多命令列表；新增 `parseConfiguredCommands` 私有方法 |
| `src/test/java/.../PipelineStartEventHandlerTest.java` | 修改 | 补充多命令匹配、trim、带/不带流水线名称等场景用例 |

## 核心改动点

### 1. 新增 `parseConfiguredCommands` 私有方法

```java
private List<String> parseConfiguredCommands(String eventComment) {
    if (StringUtils.isBlank(eventComment)) {
        return Collections.emptyList();
    }
    return Arrays.stream(eventComment.split("\\|"))
            .map(String::trim)
            .filter(s -> !s.isEmpty())
            .distinct()
            .collect(Collectors.toList());
}
```

### 2. 第一层校验（前缀匹配）

改动前：

```java
String prComment = noteEvent.getNote();
String eventComment = eventTriggerVO.getEventComment();
if (StringUtils.isBlank(prComment) || StringUtils.isBlank(eventComment)
        || !prComment.trim().startsWith(eventComment)) {
    LOGGER.info("PR评论命令、配置命令匹配失败，...");
    return;
}
```

改动后：

```java
String prComment = noteEvent.getNote();
String eventComment = eventTriggerVO.getEventComment();
List<String> configuredCommands = parseConfiguredCommands(eventComment);
String trimmedPrComment = prComment == null ? "" : prComment.trim();
if (StringUtils.isBlank(prComment) || configuredCommands.isEmpty()
        || configuredCommands.stream().noneMatch(cmd -> trimmedPrComment.startsWith(cmd))) {
    LOGGER.info("PR评论命令、配置命令匹配失败，prComment：{}，eventComment：{}", prComment, eventComment);
    return;
}
```

### 3. 第二层校验（纯命令精确匹配）

改动前：

```java
} else {
    if (!StringUtils.equals(prComment, eventComment)) {
        LOGGER.info("PR评论命令与配置不一致，...");
        return;
    }
}
```

改动后：

```java
} else {
    if (configuredCommands.stream().noneMatch(cmd -> cmd.equals(trimmedPrComment))) {
        LOGGER.info("PR评论命令与配置不一致，prComment：{}，eventComment：{}", prComment, eventComment);
        return;
    }
}
```

## 业务流程

```text
prNoteStartPipeline(event)
  ├─ 校验 Note Hook / PR 评论 / 评论人权限 / webhook 开关 / 事件触发开关
  ├─ 解析配置命令列表 configuredCommands = parseConfiguredCommands(eventComment)
  ├─ trimmedPrComment = prComment.trim()
  ├─ 第一层校验：configuredCommands 中任一命令是 trimmedPrComment 的前缀？
  │     否 → return
  ├─ 获取流水线详情 → currentPipelineName
  ├─ targetPipelineNames = parseStartPipelineNames(prComment)
  ├─ if targetPipelineNames 非空：
  │     当前流水线名 ∈ targetPipelineNames？否 → return
  ├─ else（纯命令评论）：
  │     trimmedPrComment ∈ configuredCommands？否 → return
  └─ 触发 prStartPipeline
```

## 向后兼容性

| 配置形态 | 改动前行为 | 改动后行为 |
|---------|----------|----------|
| `/start`（单命令） | `prComment.trim().startsWith("/start")` | `configuredCommands=["/start"]`，`trimmedPrComment.startsWith("/start")` —— 等价 |
| `/start`（单命令，纯命令评论） | `StringUtils.equals(prComment, "/start")` | `configuredCommands=["/start"]`，`"/start".equals(trimmedPrComment)` —— 等价 |
| `/start \| /run`（多命令） | 不支持，`startsWith` 会把整串当一个命令 | 拆分为 `["/start", "/run"]`，命中任一即匹配 |

## 测试

`PipelineStartEventHandlerTest` 新增用例（通过 `ReflectionTestUtils.invokeMethod` 调私有方法）：

- 单命令配置 + 纯命令评论 → 触发启动
- 单命令配置 + 带流水线名称评论 → 触发启动
- 多命令配置 + 命中第一个命令 → 触发启动
- 多命令配置 + 命中非第一个命令 → 触发启动
- 多命令配置 + 命中带流水线名称的命令 → 触发启动
- 多命令配置 + 不命中任何命令 → 不触发
- 配置命令带首尾空白 + PR 评论带首尾空白 → trim 后命中
- 空配置命令 → 不触发

## 风险 & 缓解

| 风险 | 缓解措施 |
|------|---------|
| `\|` 在命令词中出现的概率极低，但仍可能误拆 | 文档明确 `\|` 为分隔符；用户配置时避免在单个命令内使用 `\|` |
| 前缀匹配可能误命中（如配置 `/start` 与 `/start-full`） | 第二层精确匹配兜底纯命令场景；带参数场景由 `parseStartPipelineNames` 进一步约束 |
| 改动影响所有 PR 评论启动流水线的事件 | 单命令配置行为完全等价（见向后兼容性表）；多命令为纯增量能力 |

## 跨仓影响

无。本次改动仅涉及 `openlibing-cicd` 业务仓，不涉及 `openlibing-codecheck` 或其他仓。
