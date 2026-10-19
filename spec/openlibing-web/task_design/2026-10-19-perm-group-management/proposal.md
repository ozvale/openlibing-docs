# 权限组管理（前端）— proposal

- 变更目录：`spec/openlibing-web/task_design/2026-10-19-perm-group-management/`
- 业务分支：`dev-chenning-20260923-permission`（fork 仓 `weixin_45521051/openlibing-web`）
- 基线：`upstream/master`，领先 13 个 commit，约 980 行改动
- 日期：2026-10-19

## Why

项目用户管理页此前仅有"项目级角色"一种权限维度，资源（流水线）无法按组管控：任何持有对应项目角色的成员都可操作全部资源。后端已在 framework 侧落地权限组模型（默认权限组随项目创建自动生成 + 自定义权限组 + 资源绑定关系），前端需要补齐：

1. 权限组的可视化管理入口（创建/编辑/删除、复制成员建组、查看绑定资源）；
2. 成员列表按权限组展示与筛选，添加/修改成员时支持指定权限组；
3. 批量添加成员支持一次加入多个权限组，并按"账号 × 权限组"维度反馈结果、支持仅重试失败组。

## What Changes

- **API 层**（`src/api/url.ts`、`src/api/api.ts`）：新增 10 个权限组接口封装，对齐 2026-09-23 后端动词式路径重命名——`query-groups` / `create-group` / `update-group` / `delete-group` / `bind-resource` / `batch-bind-resources` / `unbind-resource` / `query-binding` / `query-bindings-by-group` / `batch-query-bindings`。
- **权限元数据**（`src/constants/permissions-meta.ts`）：新增 `perm_group_operate` 操作码（权限组管理），含介绍与授权指引（项目管理员角色 / 服务单）。
- **权限组管理弹窗**（`src/views/Project/components/ManagePermGroupDialog.vue`，新文件）：组列表（组名/说明/成员数/绑定资源数/操作）、创建（支持从已有组复制成员并回显复制结果）、编辑、删除（默认组禁删、有绑定先解绑、二次确认）、绑定资源列表（服务端分页 + 资源类型筛选 + 名称搜索）；全程 `perm_group_operate` 权限控制（`NoPermissionPopover` + disabled）。
- **成员管理页**（`src/views/Project/projectUserManage.vue`）：新增「管理权限组」入口按钮（权限控制）；筛选区新增「权限组」多选下拉（`permGroupIds` 加入成员查询）；成员表格新增「权限组」列（默认组兜底展示 + 说明 tooltip）；添加/修改成员按需透传 `permGroupId`（默认组不传，保留同步/审计联动）。
- **批量添加成员弹窗**（`src/components/BatchAddMemberDialog.vue`）：project 类型新增「权限组」多选（默认仅默认组）；多组时每组独立并行请求，按"账号 × 组"维度记录结果（`Map<account, Map<groupId, {ok,msg}>>`）；重试仅发送失败组（保留成功结果）；结果区按组分态展示（单组保持原有表现）。
- **文档**：成员管理页权限组列说明整合默认组信息（tooltip 文案）。

## Capabilities

### New Capabilities

- `perm-group-management`: 项目权限组的前端管理行为——权限组 CRUD 与复制建组、绑定资源分页查询、成员列表权限组展示/筛选、添加/修改成员指定权限组、批量添加成员多组分态与失败重试。

### Modified Capabilities

无。项目用户管理页既有成员增删改查行为保持兼容（不选自定义组时请求体与原行为一致）。

## Impact

- **受影响代码**：
  - `apps/web-openlibing/src/api/url.ts`、`apps/web-openlibing/src/api/api.ts`
  - `apps/web-openlibing/src/constants/permissions-meta.ts`
  - `apps/web-openlibing/src/views/Project/projectUserManage.vue`
  - `apps/web-openlibing/src/views/Project/components/ManagePermGroupDialog.vue`（新增）
  - `apps/web-openlibing/src/components/BatchAddMemberDialog.vue`
- **受影响接口**（framework 侧，均经 `/gateway` 前缀代理）：
  - `GET /perm-group/query-groups`、`POST /perm-group/create-group`、`POST /perm-group/update-group`、`POST /perm-group/delete-group`
  - `GET /perm-group/query-bindings-by-group`（服务端分页绑定列表）
  - `POST /perm-group/bind-resource`、`POST /perm-group/batch-bind-resources`、`POST /perm-group/unbind-resource`、`GET /perm-group/query-binding`、`GET /perm-group/batch-query-bindings`（本次前端已封装，绑定/解绑操作入口由流水线等资源页消费）
  - 成员接口：`getCommunityUser` 请求体新增可选 `permGroupIds`；`addCommunityUser`/`updateCommunityUser` 新增可选 `permGroupId`
- **风险**：
  - 默认权限组语义（`id=0` 不传 `permGroupId`）需与后端口径一致，否则会破坏成员自动同步/审计联动。
  - 批量添加多组并行请求依赖后端按组幂等（同一账号重复添加单组报错但可在结果区区分）；重试逻辑以前端本地成功结果为准，跨弹窗关闭后结果清空、以整组重发。
  - 绑定资源列表的类型筛选当前仅枚举 `PIPELINE`，后续资源类型扩展需同步下拉项。
  - `perm_group_operate` 权限码需后端权限元数据同步下发，否则按钮按无权限置灰。
