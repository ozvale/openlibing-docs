# pr-comment-multi-cmd

## 需求背景

当前 PR 评论启动流水线只支持配置单个命令（`EventTriggerVO.eventComment`），用户在流水线事件触发配置中只能填一个命令词。部分团队希望同一个流水线能响应多个不同的评论命令（如 `/start`、`/run`、`/go` 都能触发），现有实现无法满足。

## 功能描述

1. 支持 `eventComment` 配置多个命令，多个命令之间用 `|` 分隔（如 `/start | /run | /go`）。
2. 匹配时，对用户配置的每个命令和 PR 实际评论内容都做 `trim`（去除首尾空白字符）。
3. PR 评论命中任意一个配置命令即视为匹配成功，触发流水线启动。
4. 仅修改"评论启动流水线"逻辑（`PipelineStartEventHandler.prNoteStartPipeline`）。

## 不做什么

- 不修改停止逻辑（`PipelineStopEventHandler`）。
- 不修改重试逻辑（`PipelineRetryEventHandler`）。
- 不改变 `parseStartPipelineNames` 解析流水线名称的逻辑（仍按逗号分隔）。
- 不修改前端配置页面、DB schema、`EventTriggerVO` 字段定义。

## 验收标准

- [ ] 配置单个命令时，行为与改动前一致（向后兼容）
- [ ] 配置多个命令（`cmd1 | cmd2 | cmd3`）时，PR 评论命中任一命令即触发流水线
- [ ] 配置命令和 PR 评论的首尾空白被正确 trim
- [ ] 评论带流水线名称的场景（如 `/run pipeline1`）在多命令配置下仍正常工作
- [ ] 不带流水线名称的纯命令评论（如 `/run`）在多命令配置下能精确匹配任一命令
- [ ] 停止、重试逻辑不受影响
- [ ] 补充单元测试覆盖多命令场景

## 影响范围

### 业务仓 `openlibing-cicd`

| 文件 | 操作 | 说明 |
|------|------|------|
| `business/listener/PipelineStartEventHandler.java` | 修改 | `prNoteStartPipeline` 命令匹配逻辑支持多命令；新增私有 helper `parseConfiguredCommands` |
| `src/test/java/.../PipelineStartEventHandlerTest.java` | 修改 | 补充多命令匹配场景用例 |

### docs 仓 `openlibing-docs`

| 文件 | 操作 | 说明 |
|------|------|------|
| `spec/openlibing-cicd/task_design/pr-comment-multi-cmd/proposal.md` | 新增 | 本文件 |
| `spec/openlibing-cicd/task_design/pr-comment-multi-cmd/design.md` | 新增 | 技术设计 |
| `spec/openlibing-cicd/task_design/pr-comment-multi-cmd/tasks.md` | 新增 | 实现任务清单 |

## 关联 Issue

- 业务 Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/129
