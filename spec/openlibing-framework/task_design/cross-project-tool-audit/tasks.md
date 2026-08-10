# 跨社区工具使用审核标识 — 实现任务

## 进度: 8/8 complete

- [x] Task 1: `tool_apply.xml` 新增 `can_cross_project` 字段变更集
- [x] Task 2: `tool_version.xml` 新增 `can_cross_project` 字段变更集
- [x] Task 3: `ToolApplyDTO.java` 新增 `canCrossProject` 字段 + 校验注解
- [x] Task 4: `ToolApplyEntity.java` 和 `ToolVersionEntity.java` 新增 `canCrossProject` 字段
- [x] Task 5: `ToolApplyServiceImpl.java` — `saveToolApply()` 写入 `canCrossProject`；`reviewToolInfo()` 审核通过时写入版本表 + 调用 `ToolUseConfigMapper.insert()` 实现本项目直接使用
- [x] Task 6: `ToolProjectUseServiceImpl.useToolApply()` — 判断 `ownerProjectId` 和 `canCrossProject` 逻辑调整
- [x] Task 7: `ToolVersionDTO.java` + `ToolInfoServiceImpl.updateToolVersion()` 支持修改 `canCrossProject`
- [x] Task 8: `ToolApplyMapper.xml` 和 `ToolVersionMapper.xml` 同步 `can_cross_project` 字段到所有 SQL