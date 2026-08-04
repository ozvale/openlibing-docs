# 跨社区工具使用审核标识 — 技术设计

## 方案概述
在工具箱管理功能中，为 `tool_apply` 和 `tool_version` 表新增 `can_cross_project` 字段，标识跨社区使用是否需要审核。当标识为"不需审核"时，其他社区可直接使用该工具版本，无需走审核流程。

## 架构决策
- 无新增架构决策，直接在现有工具管理模块内扩展字段和逻辑
- 字段类型 `VARCHAR(1)` 与现有 `status`、`valid_flag` 等标识字段风格一致

## 涉及文件
| 文件 | 操作 | 说明 |
|------|------|------|
| `src/main/resources/db/changelog/v1.0.1/tool/tool_apply.xml` | 修改 | 新增 `can_cross_project` 字段变更集 |
| `src/main/resources/db/changelog/v1.0.1/tool/tool_version.xml` | 修改 | 新增 `can_cross_project` 字段变更集 |
| `src/main/java/.../dto/tool/ToolApplyDTO.java` | 修改 | 新增 `canCrossProject` + 校验注解 |
| `src/main/java/.../entity/tool/ToolApplyEntity.java` | 修改 | 新增 `canCrossProject` 字段 |
| `src/main/java/.../entity/tool/ToolVersionEntity.java` | 修改 | 新增 `canCrossProject` 字段 |
| `src/main/java/.../service/impl/ToolApplyServiceImpl.java` | 修改 | ① `saveToolApply()` 写入字段；② `reviewToolInfo()` 写入版本表 + 自动授权本项目使用 |
| `src/main/java/.../service/impl/ToolProjectUseServiceImpl.java` | 修改 | `getToolUseApplyResultEntity()` 增加 `canCrossProject=="0"` 直接使用逻辑 |

## 核心逻辑

### 1. saveToolApply()
在 `getToolApplyInfo()` 组装实体时，将 `toolApplyDTO.getCanCrossProject()` 设置到 `toolApplyEntity.setCanCrossProject()`。

### 2. reviewToolInfo() 审核通过
创建 `ToolVersionEntity` 时设置 `canCrossProject`，并调用 `toolUseConfigMapper.insert()` 插入一条 `ToolUseConfigEntity`，使当前申请项目（`toolApplyInfo.getProjectId()`）自动获得该版本使用权限。

### 3. getToolUseApplyResultEntity() 判断逻辑
```
1. 已使用过 → 跳过
2. 已在申请列表 → 跳过
3. ownerProjectId == currentProjectId → 直接使用（已有逻辑）
4. canCrossProject == "0" → 直接使用（新增逻辑）
5. 无审核人 → 无法申请
6. 其余 → 走审核流程
```

## 风险 & 缓解
- 无显著风险，该变更为字段扩展 + 逻辑判断，不涉及外部接口变更或数据迁移

## 跨仓影响
- 无，单仓变更