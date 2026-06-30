# 黄蓝协同 stop 接口修复 — 实现步骤

## Phase 1: Issue 与需求确认

- [x] 创建业务 Issue openlibing/openlibing-cicd#137
- [x] 明确需求范围：stop 接口修复 + yellowRecordId 透传

## Phase 2: 轻量设计与计划

- [x] 修改文件清单确认
- [x] 验证方式确认（单元测试 + 手动验证 + 回归验证）

## Phase 3: AI 编码交付

### 第一轮交付（commit `4bec3c18`）

- [x] `CrossRegionStartReqDTO`：新增 `yellowRecordId` 字段
- [x] `CrossRegionQueryVO`：新增 `yellowRecordId` 字段（builder 模式）
- [x] `BlueYellowPipelineMapper.java`：
  - [x] 新增 `resetForStop` 方法签名
  - [x] javadoc 完整（@param/@return）
- [x] `BlueYellowPipelineMapper.xml`：
  - [x] `queryByBlueRecord` 增加 `yellow_record_id` 字段映射
  - [x] 新增 `resetForStop` SQL
- [x] `BlueYellowPipelineServiceImpl`：
  - [x] `checkDuplicateAndTimeout` 新增 `actionType` 参数，stop 操作绕过去重拦截
  - [x] `saveOrResetRecord` 区分 stop/retry/首次，stop 调用 `resetForStop`
  - [x] `buildMqsPayload` 透传 `yellowRecordId` 和 `actionType`
  - [x] `queryYellowPipelineStatus` 查询映射补 `yellowRecordId`
- [x] commit 提交并推送
- [x] PR #413 创建并打 `ai-assisted` 标签

### 第二轮交付（commit `59a89896`）— 检视意见修复

- [x] **G.CMT.03 提示**：`BlueYellowPipelineMapper#resetForStop` javadoc 补 `@param actionType`
- [x] **Medium 逻辑缺陷**：`checkDuplicateAndTimeout` 在 `exist == null` 时对 stop 操作直接返回失败，避免 stop 对无记录任务下发 MQS 后静默成功
- [x] commit 提交并推送，PR #413 自动更新

## 用户自测/反馈循环

- [x] 用户自测通过，PR #413 获得 `ci-pipeline-passed` / `approved` / `lgtm` 标签

## Phase 4: 业务 PR 交付

- [x] PR #413 已 merged 到 release_20260630_iter2 分支
- [x] 关联 Issue #137 自动关闭（Fixes #137）

## Phase 5: 最终归档

- [x] 生成 archive.md
- [ ] docs PR 合入 openlibing/openlibing-docs master
- [ ] 业务 Issue #137 状态确认
