# 黄蓝协同 stop 接口修复 — 归档

## 归档信息

| 项目 | 内容 |
|------|------|
| 需求名称 | 黄蓝协同 stop 接口修复 |
| 业务仓 | openlibing-cicd |
| 业务 Issue | openlibing/openlibing-cicd#137 |
| 业务 PR | openlibing/openlibing-cicd!413 (merged) |
| docs PR | openlibing/openlibing-docs#479 |
| 开发分支 | master_zby_0625 |
| 流程模式 | Standard |
| 归档日期 | 2026-06-30 |

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-cicd/issues/137
- 业务 PR: https://gitcode.com/openlibing/openlibing-cicd/merge_requests/413
- 业务 commit 1 (4bec3c18): https://gitcode.com/openlibing/openlibing-cicd/commit/4bec3c182d9e757ccf48be2899ca1f21ab1e032f
- 业务 commit 2 (59a89896): https://gitcode.com/openlibing/openlibing-cicd/commit/59a89896daff42d883523be9abe940476923e0a7
- docs PR: https://gitcode.com/openlibing/openlibing-docs/merge_requests/479

## 交付历程

- commit `4bec3c18`：第一轮交付 — stop 接口修复主体改动
  - DTO/VO 新增 `yellowRecordId` 字段
  - Mapper 新增 `resetForStop` 方法，仅重置 status/mqs_send_time/fail_message/action_type，保留 yellow_record_id
  - ServiceImpl `checkDuplicateAndTimeout` 新增 actionType 参数，stop 操作绕过去重拦截
  - ServiceImpl `saveOrResetRecord` 区分 stop/retry/首次三路
  - MQS payload 透传 `yellowRecordId` 和 `actionType`
  - `BlueYellowPipelineMapper.xml` `queryByBlueRecord` 增加 `yellow_record_id` 字段映射，新增 `resetForStop` SQL
- commit `59a89896`：第二轮交付 — 检视意见修复
  - **G.CMT.03 提示**：`BlueYellowPipelineMapper#resetForStop` javadoc 补 `@param actionType`
  - **Medium 逻辑缺陷**：`checkDuplicateAndTimeout` 在 `exist == null` 时对 stop 操作直接返回失败，避免 stop 对无记录任务下发 MQS 后静默成功

## 用户自测反馈

- **检视意见 1（G.CMT.03 提示）**：`BlueYellowPipelineMapper.java:65` 缺少 `@param tag for 'actionType'` → 修复于 commit `59a89896`
- **检视意见 2（Medium）**：`BlueYellowPipelineServiceImpl#checkDuplicateAndTimeout` 在 `exist == null` 时对所有 actionType 统一返回 success，stop 对无记录任务会走完 saveOrResetRecord（UPDATE 0 行静默无效）→ dispatchMqsMessage（发孤儿 stop 指令）→ handleMqsResult（UPDATE 0 行但返回 success），调用方误判 stop 已生效 → 修复于 commit `59a89896`，在 `exist == null` 分支内对 stop 提前拦截返回失败

## 最终验证

- CI 流水线：通过（PR #413 标签 `ci-pipeline-passed`）
- 代码审查：通过（PR #413 标签 `approved` / `lgtm`）
- PR 合入状态：已 merged 到 `release_20260630_iter2`
- 关联 Issue：#137 通过 `Fixes #137` 自动关闭

## 设计偏差与取舍

### 偏差 1：原设计未考虑 `exist == null` 的 stop 场景

**背景**：第一轮设计假设 stop 总是有已存在记录可停止（因为 stop 语义上是对运行中流水线操作）。但实际调用方可能对未发起 start 或记录已被删除的任务发起 stop。

**取舍**：在 `exist == null` 分支内对 stop 提前拦截返回失败，而不是让流程继续走无效的 UPDATE + MQS 链路。这样调用方收到明确错误，黄区也不会收到无法回写的孤儿 stop 指令。start/retry 路径完全不受影响。

### 偏差 2：`resetForStop` 保留 `yellow_record_id` 而非清空

**背景**：原 `resetForRetry` 在重置时会清空 `yellow_record_id / start_time / end_time / yellow_pipeline_url`，因为是重新发起。但 stop 必须保留这些字段供黄区定位"要停止哪条执行记录"。

**取舍**：新增独立的 `resetForStop` 方法，与 `resetForRetry` 显式区分。虽然 SQL 语句相似，但语义不同，未来字段调整时影响范围更可控。

## 可复用经验

1. **stop/取消类操作不能复用 start 的去重逻辑**：去重逻辑（`checkDuplicateAndTimeout`）针对 start 设计，假设"已存在记录即重复"。但 stop/取消类操作本质上是对已存在记录的操作，必须绕过去重，且 `exist == null` 时应直接拒绝（无可取消对象）。建议在新增 actionType 时同步评估去重逻辑的适用性。

2. **MQS payload 新增字段需评估消费端兼容性**：本次新增 `actionType` 和 `yellowRecordId` 字段，黄区按字段名取值，缺失字段不影响既有逻辑。但若未来新增必填字段，需协调黄区同步升级。

（以上经验已沉淀，可考虑同步到 `ai_memory.md`。）

## 归档日期

2026-06-30
