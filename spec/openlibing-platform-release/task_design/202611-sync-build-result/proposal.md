# 同步构建结果到仓库（update 发布流程步骤 1）

## 需求背景

openEuler update 发布（如 `openEuler-22.03-LTS_update20220205`）的发布数据准备阶段，
需要把 OBS 侧最新构建出的 RPM 同步进发布仓库，使后续的版本检查、测试 repo 导入等
步骤基于最新产物进行。此前该操作依赖人工在 Jenkins 上触发 `get-latest-rpms` 任务，
无平台内操作入口、无状态跟踪、无操作留痕。

本需求在平台内新增"同步构建结果到仓库"接口，作为 update 发布自动化编排
（见 `202611-update-automation`）的步骤 1，也可独立手动触发。

## 需求范围

**范围内**：

- 新增 `POST /publish/jenkins/syncBuildResultToRepo` 接口（`OpeneulerjenkinsController`）
- 归属校验：仅评审单创建者可操作
- 版本号拆解：`openEuler-22.03-LTS_update20220205` → branch 取 `openEuler-22.03-LTS`
- 触发 Jenkins `get-latest-rpms` 参数化构建（仅 branch 参数，token 从 job 配置解密）
- 新增状态槽 `syncBuildResult` 与触发时间字段 `syncBuildResultTriggerTime`
- 新增查询接口 `querySyncBuildResult` 供前端轮询；等待时长届满后惰性推进为成功
- 触发成功/失败均写入评审单操作历史（`review_history`）

**范围外**：

- Jenkins 任务本身的执行结果回传（该任务无回调，采用等待时长判定）
- token 从 URL query 迁移到请求头（沿用既有触发模式，见 design.md 风险说明）

## 验收标准

1. 非创建者调用返回 400 无权限。
2. 状态为执行中时重复调用直接返回当前状态（幂等防重），不重复触发 Jenkins。
3. 触发成功后 Jenkins 任务入队（HTTP 201），状态槽置执行中并记录触发时间。
4. 触发失败（BusinessException）时状态槽置执行失败，操作历史记录失败。
5. 查询接口轮询时，执行中且距触发时间满 35 分钟（`SYNC_BUILD_RESULT_WAIT_MILLIS`）
   则状态推进为执行成功；未届满返回当前状态不写库。
6. 状态推进逻辑以 `advanceSyncBuildResultIfTimeout` 公共方法暴露，
   供查询接口与自动化编排定时任务共用。

## 关联

- 业务分支：`feat-update-release-automation`（openlibing-platform-release 仓）
- 实现 commit：`997ca480`（新增接口）、`089426ab`（补充操作历史）
- 关联 spec：`202611-update-automation`（本接口为其编排步骤 1）
