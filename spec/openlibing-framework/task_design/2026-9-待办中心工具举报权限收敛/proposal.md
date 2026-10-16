# 待办中心工具举报审批权限收敛

## 需求背景

待办中心「工具举报」审批入口存在权限越权风险：操作用户在非「工具管理者」角色时，仍可通过待办中心查看其他工具的举报审批信息列表（虽无法审批，但可读信息已越权）。Issue 提出「查看与操作应统一受控」。

本需求在 openlibing-framework 仓收敛 `ToolReport` 举报审批相关接口：将 `userId` 由可选参数改为必填，并按维度（「待我审批」/「审批历史」）判定权限，非工具管理者在受限维度静默返回空列表，确保查看与审批入口统一受控。

## 功能描述

### 做什么

1. **接口签名调整**：`ToolReportController` 待办中心相关查询接口将 `userId` 从可选参数改为必填，并新增「维度」区分（待我审批 / 审批历史 / 全部）。
2. **权限判定收敛**：`ToolReportService` / `ToolReportServiceImpl` 增加按维度判定逻辑，非工具管理者在「待我审批」「审批历史」维度静默返回空列表，不再返回他人工具的举报审批信息。
3. **测试覆盖**：`ToolReportServiceImplTest` 补充按维度的权限收敛单测，覆盖「工具管理者」「非工具管理者」两类用户的查询结果。

### 不做什么

1. 不改写「审批」动作本身的鉴权（审批动作已有鉴权，本需求只收敛查看列表的越权读取）。
2. 不修改举报提交侧（用户上报工具）相关接口与表结构。
3. 不引入新表与字段，权限判定复用现有工具管理者关系。

## 验收标准

- [x] `ToolReportController` 待办中心查询接口 `userId` 必填
- [x] 非工具管理者用户在「待我审批」「审批历史」维度查询返回空列表
- [x] 工具管理者查询行为保持原状（不受影响）
- [x] `ToolReportServiceImplTest` 补充权限收敛维度单测，全部通过
- [x] PR 合入 `release_20260923_iter2` 分支

## 影响范围

- **openlibing-framework**：`ToolReportController` / `ToolReportService` / `ToolReportServiceImpl` / `ToolReportServiceImplTest` 共 4 个文件
- **依赖方**：openlibing-gateway 已统一从 JWT 解析 `userId` 并覆盖 URL Query 中的值，URL 传参不会被越权篡改

## 关联

- 业务 Issue: openlibing/openlibing-framework#92
- 业务 PR: openlibing/openlibing-framework（release_20260923_iter2 分支已合入，head: m0_47969702:fix_20260923_iter2_zq）
