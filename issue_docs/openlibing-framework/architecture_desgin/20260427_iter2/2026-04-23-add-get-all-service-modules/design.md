## Context

系统中的服务模块对应菜单层级中的二级菜单。现有 `getUserRootPermission` 接口根据用户角色权限过滤菜单，仅返回用户可访问的模块。在服务单分配场景中，评审人需要从完整的服务模块列表中进行选择。

当前菜单层级结构：
- 一级菜单（parentId=0）：导航入口（如"服务中心"、"general_config")
- 二级菜单：实际功能页面 = serviceModule（menuType=0）

注：`general_config` 本身就是一级菜单（parentId=0），其子菜单无需单独查询。

## Goals / Non-Goals

**Goals:**
- 提供完整的服务模块名称列表，用于服务单分配时的下拉选择
- 自动去重，相同 menuName 只保留一个
- 简洁的 API 契约，只返回业务需要的 menuName

**Non-Goals:**
- 接口内部不做权限过滤（由公共认证层处理）
- 不返回 identification 字段
- 不提供排序功能（Set 无序）

## Decisions

### 1. 返回类型选择
**决策**: 返回 `Set<String>` 而非 `List<RootMenuInfoDTO>`

**原因**: 
- 业务只需 menuName，不需要 identification
- Set 自动去重，无需额外逻辑
- 简化 API 契约，调用方直接使用字符串集合

**备选方案:**
- 保留 RootMenuInfoDTO，手动去重 — 拒绝：DTO 冗余，增加复杂度
- 返回 List<String> 去重后 — 拒绝：Set 天然去重，语义更清晰

### 2. 数据来源策略
**决策**: 直接查询菜单表，不做角色权限过滤

**原因**: 接口目的是提供完整列表供选择，而非用户特定访问权限。简化查询逻辑：
- `queryByParentId(0)` — 获取一级菜单 ID 列表
- `queryByParentIds(一级IDs)` — 获取所有二级菜单
- 过滤 menuType=0，提取 menuName

注：`general_config` 是一级菜单之一，其子菜单已包含在 `queryByParentIds` 结果中，无需单独查询。

### 3. 去重策略
**决策**: 使用 `Collectors.toSet()` 自动去重

**原因**: Set 自动去重相同 menuName，无需额外代码。

### 4. 接口位置
**决策**: 放置于 `UserBasicController` 的 `/user/` 路径下

**原因**: 与现有菜单相关接口 `/user/get-user-root-permission` 保持一致，服务模块属于用户相关数据。

## Risks / Trade-offs

| 风险 | 缓解措施 |
|------|----------|
| 菜单数据量增大 | 通常菜单数量 <100，无需分页 |
| 接口无权限校验 | 公共层处理认证，文档说明为内部使用 |
| Set 无序 | 业务场景用于下拉选择，顺序不重要；如需排序可前端处理 |