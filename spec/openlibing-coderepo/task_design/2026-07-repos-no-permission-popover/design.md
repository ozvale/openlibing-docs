# 代码仓管理页面操作无权限提示气泡 — 技术设计

## 方案概述

后端 framework 新增 1 个聚合接口，基于现有 4 张表（menu_info / menu_url_info / role_permission_manager / role_info）反查「操作 → 角色」映射，并按 5 级（system/product/project/repo/general）分组返回；同时基于当前用户 permissions 计算 hasPermission。前端在 Content.vue 一次性拉取全量，存入 store，新建 NoPermissionPopover 组件包裹操作按钮，无权限时悬浮显示三段式气泡。

## 架构决策

### 决策 1：接口放在 framework 而非 coderepo

**选择**：framework

**原因**：
- framework 是权限基础设施仓，RoleInfoMapper / RolePermissionMapper / MenuInfoMapper 已存在
- 接口可被多业务仓复用（cicd / ops 等也可接入）
- coderepo 已有反查链路（CommonServiceImpl.verifyPermissionsByProduct）作为实现参考，但暴露为 HTTP 接口更适合放 framework

### 决策 2：一次性返回全量操作而非按权限码查询

**选择**：全量返回（前端一次拉取）

**原因**：
- 避免每个按钮发一次请求（Repos 目录有 10+ 个权限码）
- 操作元数据量小（预计 < 200 条），全量返回 < 50KB
- 前端缓存后页面切换无需重复请求
- 简化前端组件实现（无需异步加载）

**权衡**：接口响应略大，但 < 50KB 可接受；若未来操作数 > 500 可改为按权限码批量查询。

### 决策 3：hasPermission 在后端计算

**选择**：后端计算

**原因**：
- 前端已有 `user.permissions`（来自 `/user/get-user-permission`），本可前端计算
- 但后端计算可保证一致性（避免前端两个接口数据不同步）
- 后端可复用 Redis 缓存的 permissions，性能开销小

### 决策 4：气泡内容（介绍 + 指引文案）维护在前端

**选择**：前端常量 `permissions-meta.ts`

**原因**：
- 文案迭代频繁，前端硬编码改最快
- 无需 DB 变更 + 后台管理页
- 若未来需运营可配，可扩展 menu_info 表字段后端兜底

### 决策 5：改造策略 — v-if 隐藏也改为显示+气泡

**选择**：现有 `v-if` 隐藏的按钮改为显示+气泡

**原因**：
- 需求要求「让用户知道功能存在但需要何种角色」
- v-if 隐藏会让用户以为功能不存在
- 显示+气泡可引导用户申请权限

**权衡**：页面会多出灰按钮，但通过气泡提示可解释原因，视觉冲击可接受。

### 决策 6：气泡触发方式 — hover

**选择**：hover 触发（默认）

**原因**：
- 轻量，不打断操作流
- 符合 Element Plus el-tooltip / el-popover 既有体验
- 点击气泡内「申请权限」按钮时通过 popover 的 `enterable` 保持显示

## 接口契约

### `GET /user/get-operation-permissions`

**位置**：`UserBasicController`（framework）

**请求参数**：无（基于当前登录用户）

**响应**：

```jsonc
{
  "code": 200,
  "message": "success",
  "data": {
    "operations": [
      {
        "identification": "repo_manage:add",
        "operationName": "新增代码仓",
        "hasPermission": false,
        "rolesByLevel": [
          {
            "level": "project",
            "levelLabel": "项目",
            "roles": [
              { "role": "project_manager", "roleName": "项目管理员" }
            ]
          },
          {
            "level": "repo",
            "levelLabel": "仓库",
            "roles": [
              { "role": "repo_owner", "roleName": "仓库责任人" }
            ]
          }
        ]
      }
      // ... 更多操作
    ]
  }
}
```

**字段说明**：

| 字段 | 类型 | 说明 |
|---|---|---|
| `identification` | string | 权限码，对应 menu_info.identification，如 `repo_manage:update` |
| `operationName` | string | 操作名，来自 menu_info.menu_name |
| `hasPermission` | boolean | 当前用户是否有此操作权限 |
| `rolesByLevel` | array | 该操作有权限的角色，按 5 级分组 |
| `rolesByLevel[].level` | string | 级别码：`system`/`product`/`project`/`repo`/`general` |
| `rolesByLevel[].levelLabel` | string | 级别中文名：平台/组织/项目/仓库/通用 |
| `rolesByLevel[].roles[]` | array | 角色列表 |
| `rolesByLevel[].roles[].role` | string | 角色码，如 `repo_owner` |
| `rolesByLevel[].roles[].roleName` | string | 角色中文名，如 `仓库责任人` |

**异常处理**：
- 用户未登录：返回 401
- 服务异常：返回 500，前端降级为现有行为（无权限按钮 `:disabled`）

## 涉及文件

### framework

| 文件 | 操作 | 说明 |
|---|---|---|
| `UserBasicController.java` | 修改 | 新增 `GET /user/get-operation-permissions` 接口 |
| `UserBasicService.java` | 修改 | 新增 `getOperationPermissions()` 方法签名 |
| `UserBasicServiceImpl.java` | 修改 | 实现反查 + 分组 + hasPermission 计算 |
| `OperationPermissionDTO.java` | 新增 | 响应 DTO |
| `RoleByLevelDTO.java` | 新增 | 角色分组 DTO |
| `RoleBriefDTO.java` | 新增 | 角色简要 DTO |
| `MenuInfoMapper.java` | 修改 | 新增 `queryAllIdentifications()` 方法 |
| `MenuInfoMapper.xml` | 修改 | 新增对应 SQL |
| `UserBasicServiceImplTest.java` | 新增/修改 | 单元测试 |

### coderepo

无改动。

### web-openlibing

| 文件 | 操作 | 说明 |
|---|---|---|
| `src/components/NoPermissionPopover.vue` | 新增 | 三段式气泡组件 |
| `src/constants/permissions-meta.ts` | 新增 | 权限码 → 操作名/介绍/指引文案 |
| `src/api/api.ts` | 修改 | 新增 `getOperationPermissions` API |
| `src/api/url.ts` | 修改 | 新增 URL 常量 |
| `src/stores/app.ts` | 修改 | 扩展 `operationPermissions` 状态 |
| `src/views/Content.vue` | 修改 | 并行调用新接口 |
| `src/views/Repos/index.vue` | 修改 | 改造 canHandle 调用点 |
| `src/views/Repos/branches.vue` | 修改 | 改造 canHandle 调用点 |
| `src/views/Repos/repoUserManage.vue` | 修改 | 改造 canHandle 调用点 |
| `src/views/Repos/tagManagement.vue` | 修改 | 改造 canHandle 调用点 |

## 风险 & 缓解

| 风险 | 等级 | 缓解 |
|---|---|---|
| 新接口失败导致页面卡死 | 中 | 前端 try-catch + 降级为现有行为 |
| hasPermission 与前端 canHandle 不一致 | 中 | 后端复用同一 Redis permissions 缓存 |
| 5 级分组中文映射错误 | 低 | 沿用 ProjectConstant.RoleType + 前端常量双重校验 |
| v-if 改为显示后页面灰按钮过多 | 低 | 气泡提示解释原因，视觉冲击可接受 |
| 气泡定位在表格边缘异常 | 低 | 自动定位 + 边界保护 + 滚动关闭 |
| 跨仓发布顺序不当导致功能不可用 | 中 | 先发 framework，再发 web；web 降级容错 |
| super_admin 用户 permissions 缓存与接口不一致 | 低 | super_admin 直接 hasPermission=true |

## 跨仓影响

| 协调点 | 说明 |
|---|---|
| 接口契约 | framework 响应结构需与 web 前端对齐，本 design 已固化 |
| 权限码清单 | 前端 permissions-meta.ts 需覆盖 Repos 目录所有权限码，后端返回全量无需对齐 |
| 发布顺序 | framework 先发布（向后兼容，新接口不影响现有功能）→ web 发布 |
| 跨仓引用 | web PR body 引用 `openlibing/openlibing-coderepo#73`；framework PR 同样引用 |

## 关键实现参考

### 后端反查逻辑（参考 coderepo `CommonServiceImpl.verifyPermissionsByProduct`）

```java
// 1. 查所有有 identification 的 menu
List<MenuInfoEntity> menus = menuInfoMapper.queryAllIdentifications();
// menus 含 id / identification / menuName

// 2. 按 menu id 批量查 role_permission_manager，得 roleIds
List<Integer> menuIds = menus.stream().map(MenuInfoEntity::getId).toList();
List<RolePermissionEntity> rps = rolePermissionMapper.queryByMenuIds(menuIds);

// 3. 按 roleId 批量查 role_info，得 role + roleName + type
List<Integer> roleIds = rps.stream().map(RolePermissionEntity::getRoleId).distinct().toList();
List<RoleInfoEntity> roles = roleInfoMapper.queryByRoleIds(roleIds);

// 4. 按 menuId 分组角色，再按 RoleType 5 级分组
Map<Integer, List<RoleInfoEntity>> menuIdToRoles = ...;

// 5. 计算每个操作的 hasPermission（基于当前用户 permissions）
Set<String> userPerms = ...; // 来自 Redis 缓存
for (MenuInfoEntity menu : menus) {
    boolean hasPermission = userPerms.contains(menu.getIdentification());
    // 组装 OperationPermissionDTO
}
```

### 前端组件用法

```vue
<NoPermissionPopover auth="repo_manage:update" operation-name="编辑代码仓">
  <el-button :icon="Edit" link @click="openDialog('edit', scope.row)" />
</NoPermissionPopover>
```

组件内部：
- 从 store 取 `operationPermissions[auth]`
- 若 `hasPermission === true` → 透传 slot 的点击
- 若 `hasPermission === false` → 用 `el-popover` 包裹，hover 显示三段式气泡
- 文案从 `permissions-meta.ts[auth]` 取

## 测试策略

### 后端（Standard 模式）

- `UserBasicServiceImplTest.getOperationPermissions_shouldReturnAllOperations` — 全量返回
- `UserBasicServiceImplTest.getOperationPermissions_shouldGroupByLevel` — 5 级分组正确
- `UserBasicServiceImplTest.getOperationPermissions_shouldComputeHasPermission` — hasPermission 计算
- `UserBasicServiceImplTest.getOperationPermissions_superAdminShouldHaveAll` — super_admin 全部 true

### 前端（Standard 模式）

- 组件单测：`NoPermissionPopover.spec.ts`
  - 有权限时不显示气泡
  - 无权限时 hover 显示气泡
  - 气泡内容三段式正确渲染
- 集成验证：Repos/index.vue 操作按钮行为
