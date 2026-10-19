# 权限组管理（前端）— tasks

> 实现已随业务分支 `dev-chenning-20260923-permission` 完成，本清单按实际交付内容勾选。

## 1. API 层

- [x] 1.1 `api/url.ts` 新增 9 个 `/perm-group/*` 端点常量（`PERM_GROUP_LIST`/`PERM_GROUP_CREATE`/`PERM_GROUP_UPDATE`/`PERM_GROUP_DELETE`/`PERM_BINDING`/`PERM_BINDING_BATCH`/`PERM_UNBIND`/`PERM_BINDING_QUERY`/`PERM_BINDING_BY_GROUP`/`PERM_BINDING_BATCH_QUERY`），对齐 2026-09-23 动词式路径重命名。
- [x] 1.2 `api/api.ts` 按端点封装 `getPermGroups`/`createPermGroup`/`updatePermGroup`/`deletePermGroup`/`bindPermResource`/`batchBindPermResource`/`unbindPermResource`/`getPermBinding`/`getPermBindingsByGroup`/`batchQueryPermBindings`。

## 2. 权限元数据

- [x] 2.1 `constants/permissions-meta.ts` 新增 `perm_group_operate`：operationName「权限组管理」、intro（项目级管理角色要求）、guide（项目管理员角色 / 服务单两条授权路径）。

## 3. ManagePermGroupDialog（新增组件）

- [x] 3.1 主弹窗组列表：组名（默认组附 tooltip）/说明/成员数/绑定资源数/操作列，`disabledLoading` 静默加载。
- [x] 3.2 创建权限组：组名必填校验、说明、复制来源下拉（已有组，可空白创建）；成功后按 `copiedCount`/`excludedCount` 回显复制统计并刷新列表。
- [x] 3.3 编辑权限组：默认组行不渲染编辑入口；仅组名 + 说明。
- [x] 3.4 删除权限组：默认组禁删 → 有绑定先解绑 → 二次确认（成员记录连带清理文案）。
- [x] 3.5 绑定资源列表：服务端分页（pageNum/pageSize/total）、资源类型筛选（PIPELINE）、名称搜索，筛选变更重置页码；默认组绑定数展示 `--` + tooltip。
- [x] 3.6 权限控制：入口与创建/编辑/删除按钮统一 `perm_group_operate` + `NoPermissionPopover`；组变更后 `emit('refresh')`。

## 4. 成员管理页（projectUserManage.vue）

- [x] 4.1 新增「管理权限组」按钮（`perm_group_operate` 权限控制 + uem 埋点），打开 `ManagePermGroupDialog`。
- [x] 4.2 筛选区新增「权限组」多选下拉；`permGroupIds` 非空才加入成员查询请求体；外部筛选合并时保留权限组筛选。
- [x] 4.3 成员表格新增「权限组」列：tag 展示，空值兜底「默认权限组」，表头 tooltip 说明默认组规则。
- [x] 4.4 单条添加/修改成员：`permGroupId` 非 0 非空才透传（默认组保留同步/审计联动）。
- [x] 4.5 权限组选项加载 `loadPermGroupOptions`：页面初始化与弹窗 refresh 回调时刷新。

## 5. 批量添加成员（BatchAddMemberDialog.vue）

- [x] 5.1 project 类型新增「权限组」多选表单项（默认 `[0]`，repo 类型不展示）；打开弹窗时拉取组列表并重置状态。
- [x] 5.2 结果结构升级为 `Map<account, Map<groupId, {ok,msg}>>`（账号 × 组维度）。
- [x] 5.3 多组提交：每组构建独立请求（`gid !== 0` 才带 `permGroupId`），过滤该组已成功账号后 `Promise.all` 并行发送。
- [x] 5.4 结果合并：仅覆写本轮发送格子，成功结果跨轮保留；整体成功/500/部分失败判定与消息分级。
- [x] 5.5 重试：`resetUsers` 仅保留有失败结果的账号行并清理无关历史格子；再次提交只发失败组。
- [x] 5.6 展示：多组按组分态（组名 + ✓/✗ + 失败原因 tooltip）；单组保持原有表现；弹窗关闭清空结果与选择。

## 6. 验证

- [x] 6.1 改动文件 ESLint 通过，无新增 error/warn。
- [x] 6.2 手动联调：权限组创建（含复制来源统计回显）/编辑/删除守卫链/绑定资源分页筛选。
- [x] 6.3 手动联调：成员列表权限组筛选与权限组列展示；单条/批量添加成员指定组；多组分态结果与失败组重试。
- [x] 6.4 无 `perm_group_operate` 权限账号验证入口与操作按钮置灰、气泡说明展示。
- [x] 6.5 检视修复：权限组操作列「编辑」「删除」按钮补齐与「创建权限组」一致的 `perm_group_operate` 权限控制（NoPermissionPopover + disabled）。
