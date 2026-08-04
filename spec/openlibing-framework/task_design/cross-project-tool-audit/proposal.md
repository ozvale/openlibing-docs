# 跨社区工具使用审核标识

## 需求
工具箱管理功能，创建工具时维护跨社区使用是否审核标识。如果不需审核，跨社区使用则直接使用，无需走审核流程。

## 验收标准
- [ ] `tool_apply` 表新增 `can_cross_project` 字段（VARCHAR(1)，0-不需审核 1-需审核）
- [ ] `tool_version` 表新增 `can_cross_project` 字段（VARCHAR(1)，0-不需审核 1-需审核）
- [ ] `ToolApplyDTO` 新增 `canCrossProject` 字段，带 `@NotBlank` + `@Pattern(regexp = "^(0|1)$")` 校验
- [ ] `saveToolApply()` 保存申请时写入 `canCrossProject` 字段
- [ ] `reviewToolInfo()` 审核通过新增版本时，将 `canCrossProject` 写入版本表，并调用 `ToolUseConfigMapper.insert()` 实现本项目直接使用该工具版本
- [ ] `useToolApply()` 逻辑：`ownerProjectId == 当前projectId` 直接使用；`canCrossProject == 0` 直接使用；其余走审核

## 影响范围
- 模块：tool（工具箱管理）
- 文件：2个DB changelog、1个DTO、2个Service Impl、2个Entity
- 仓：openlibing-framework（单仓）