# 流水线白名单支持按人员维度配置 — 实现任务

## 进度: 6/6 complete（后端编码完成，待用户 review + 自测）

- [x] Task 1: `PipelineInfoEntity.ConfigJson` 新增 `triggerWhiteList` 字段 + DTO/VO 定义（TriggerWhiteListQueryDTO / TriggerWhiteListSaveDTO / TriggerWhiteListRespDTO / TriggerFlagsQueryDTO / PipelineTriggerFlagVO / TriggerWhiteListMemberVO）
- [x] Task 2: `PipelineControllerV2` 新增 trigger-users 查询/保存/flags 接口 + `PipelineService(Impl)` 实现（Service 层复用 run 菜单 URL 校验编辑权限；白名单已开启校验；UUID 格式/去重/上限校验；Redis 锁防并发；全量覆盖保存；查询接口返回名单+项目可选成员列表）
- [x] Task 3: `runPipeline` / `retryPipeline` 叠加名单校验（AND 现有角色权限，UUID 忽略大小写比对，统一文案）；新增 `retryPipelineByEvent` 供 PR 评论等事件链路调用，跳过名单校验
- [x] Task 4: 触发权限标记批量查询接口 `trigger-users/flags`（替代原"列表/详情响应加字段"方案，因列表响应为华为云 SDK 类型）
- [x] Task 5: 操作日志（`UPDATE_PIPELINE_TRIGGER_WHITELIST` 常量 + `PipelineWhiteListLogHandler` 支持名单变更记录，记录变更前后名单）
- [x] Task 6: 单元测试 `TriggerWhiteListServiceTest` 17 个用例全部通过（含 UUID 校验、PR 链路跳过、成员 VO 转换、可选成员列表）+ `mvn compile` 通过（无 liquibase 变更）
