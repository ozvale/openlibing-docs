# cancel-queue-push-pipeline-status — 归档

## 关联

| 类型 | 链接 |
|---|---|
| 业务 Issue | https://gitcode.com/openlibing/openlibing-cicd/issues/200 |
| 业务 Issue 标题 | 【openlibing】取消排队中的流水线gitcode的流水线状态需要刷新 |
| 业务 PR | https://gitcode.com/openlibing/openlibing-cicd/merge_requests/522 |
| 业务 PR 标题 | 取消排队推送到gitcode |
| 业务 PR 分支 | `master-gitcode-pipeline-status` → `release_20260730_iter2` |
| 业务 PR 标签 | `ai-assisted`, `ci-pipeline-passed` |
| docs PR | (本 PR) |
| docs PR 分支 | `spec-openlibing-cicd-cancel-queue-push-pipeline-status` → `master` |

## 需求背景

流水线在排队阶段被取消时，gitcode 平台上的对应 commit status 不会自动更新，导致 PR 列表长期显示"排队中"或"运行中"，与实际取消状态不一致。需要在校验接口成功返回后，主动将流水线状态推送为 `CANCELED` 到 gitcode 平台，使 PR 状态实时反映取消结果。

## 交付历程

| commit | 说明 |
|---|---|
| `991f3e180` | 取消排队推送状态至gitcode —— 新增 `pushGitCodePipelineStatus` 私有方法，封装"按 pipelineRunId 查实体 → 仅当 prId 非空且 repoType=gitcode 时推送"逻辑；在 `cancelPipelineQueue` 中调 `gitcode` 平台成功后调用 |
| `32a9267d9` | 取消排队推送到gitcode —— 修复 `pushGitCodePipelineStatus` 条件反向 Bug：原条件为 `\|\| "gitcode".equals(entity.getRepoType())`（语义为"gitcode 仓跳过推送"），改为 `\|\| !"gitcode".equals(entity.getRepoType())`（仅非 gitcode 仓跳过） |

## 用户自测反馈

- 用户明确触发 Phase 5 归档。
- 业务 PR #522 CI 已通过（`ci_state_passed: true`，`conflict_passed: true`），标签 `ai-assisted` + `ci-pipeline-passed` 已打。

## 最终验证

| 项 | 结果 |
|---|---|
| 业务代码修改 | ✅ 2 个核心 commit 已 push 到 fork 仓 `master-gitcode-pipeline-status` |
| 业务 PR | ✅ PR #522 已创建（`state: open, merged: false`） |
| 业务 PR 标签 `ai-assisted` | ✅ 已打 |
| 业务 PR CI | ✅ `ci_state_passed: true` |
| 业务 PR 合入 | ⏳ 待用户/评审合入 `release_20260730_iter2` |
| docs PR | ⏳ 本次提交（target=master） |

## 设计偏差与取舍

| 取舍 | 原因 |
|---|---|
| 复用现有 `pushGitCodeCommitStatus(param, status)` 入口 | 已存在通用推送通道，避免在 cancel 路径重复实现签名拼装、token 装配、异常隔离等逻辑 |
| 单独抽 `pushGitCodePipelineStatus` 私有方法 | cancel 主流程只关心"取消成功"，gitcode 推送是非必须副作用；独立方法 + try/catch 隔离异常不影响 cancel 返回结果 |
| 异常隔离用 `try/catch (Exception)` + 错误日志，不上抛 | 推送失败不应改变 cancel 接口的成功语义；业务数据已落 DB，状态不一致可由后续轮询任务修正 |
| 条件用 `!"gitcode".equals(entity.getRepoType())` 而非 `switch` 表达式 | 保持单仓判定与项目其他 gitcode 专属逻辑（`gitcode-pipeline-commit-status`）一致 |
| repoType 判定而非"凭 commit status 接口可用性"判定 | 仓类型在创建时已确定，gitcode 与其他平台行为差异由 `pushGitCodeCommitStatus` 内部处理 |
| 推送仅在 `gitcode` 平台调通后触发 | 调通前流水线尚未真正取消，状态未稳定，提前推送会出现状态闪变 |

## 可复用经验

1. **取消类操作的状态联动模板**：业务侧"调上游取消接口"与"推送平台状态"分两步时，第二步必须放在**第一步成功之后**且必须做**异常隔离**。本次实现把第二步抽成 `pushGitCodePipelineStatus` 私有方法 + 全 `catch (Exception)` 兜底，避免推送失败污染 cancel 返回。
2. **Boolean 复合条件编写防反向 Bug**：判等反向是高频踩坑点（`==` vs `!=`、`equals` vs `!equals`）。当条件形如 `entity == null || entity.getPrId() == null || <平台判定>`，必须先把每个子条件写"跳过条件"再串联，避免误把"包含"写成"排除"。本次 `32a9267d9` 即为此类修复（`"gitcode".equals(repoType)` → `!"gitcode".equals(repoType)`）。
3. **平台类型判定的"白名单"风格**：用 `!"gitcode".equals(...)` 这种**排除**式判定是反模式，应优先**包含**式（`"gitcode".equals(...)`），新接入平台时自动走跳过路径，避免误推。本次是历史代码延续，未重构成 switch 表达式以保持与项目其他 `pushGitCode*` 调用点风格一致。
4. **取消类副作用失败的兜底手段**：本次仅日志兜底，未引入重试 / 落库 / 异步补偿。如果后续出现"gitcode 推送失败但 cancel 已返回"导致 PR 状态卡死，应在 `pipeline_run_info` 表加 `gitcode_status_pushed` 标志位 + 定时补偿任务（与 `pr-op-mq` 的延迟重试思路类似）。
5. **commit status 推送与 cancel 主流程解耦**：将 `preparePipelineParam + pushGitCodeCommitStatus` 封装为通用入口后，cancel / build-finish / build-start / queue-cancel / fail 等多种触发场景都能复用同一推送通道，避免每个事件都重写 token / param 拼装。

## 归档日期

2026-07-30
