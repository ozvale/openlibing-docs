# 实现任务清单：openlibing-web 按钮无权限控制（NoPermissionPopover 落地）

- **目标仓**：`openlibing/openlibing-web`
- **业务分支**：`feature/nopermission`（fork：`vermouth_fee/openlibing-web`）
- **流程模式**：Standard
- **创建日期**：2026-08-27
- **最近同步**：2026-08-31（`feature/nopermission` `cb8f8842` 已随 `!739` 合入 `release_20260831`；后续 `fix-permission-bubble-and-offline-notice` `a4f622ee` 回退工具市场接入，见 Step 6）

## 实现步骤

### Step 1: 权限元数据

- [x] `src/constants/permissions-meta.ts` 新增 12 个权限码 `PermissionMeta`（`project_manage:update` / `project_user_manage` / `project_user_manage:add` / `project_user_manage:update` / `project_user_manage:delete` / `loophole_view_config:query` / `vulnerability_sync:button` / `commu_manager` / `platform_release_config` / `tool_apply` / `tool_manage` / `my_tool`）
- [x] 注册到 `PERMISSIONS_META` 映射

### Step 2: 项目管理

- [x] `src/views/Project/index.vue`：操作列"编辑"按钮用 `NoPermissionPopover`（`auth="project_manage:update"`，`placement="left"`）包裹
- [x] 操作列"成员管理"按钮用 `NoPermissionPopover`（`auth="project_user_manage"`，`placement="left"`）包裹
- [x] 两处 `el-tooltip` 仅在有权限时渲染（`v-if="canHandle(...)"`），无权限渲染裸按钮（`v-else`），避免嵌套冲突

### Step 3: 项目成员管理

- [x] `src/views/Project/projectUserManage.vue`："添加项目成员"按钮由 `v-if` 改 `NoPermissionPopover` + `:disabled`（`auth="project_user_manage:add"`，`placement="bottom"`）
- [x] 成员列表"编辑"按钮接入 `NoPermissionPopover`（`auth="project_user_manage:update"`，`placement="top"`）
- [x] 成员列表"删除"按钮接入 `NoPermissionPopover`（`auth="project_user_manage:delete"`，`placement="top"`）
- [x] 保留原有业务置灰条件（`committerList` / `judgeSyncFlag`）

### Step 4: 漏洞视图

- [x] `src/views/cve/cveManager.vue`："配置"按钮由 `v-if` 改 `NoPermissionPopover`（`auth="loophole_view_config:query"`）+ 点击守卫
- [x] "同步漏洞"按钮接入 `NoPermissionPopover`（`auth="vulnerability_sync:button"`）；有权限保留 `el-tooltip`，无权限 `v-else` 渲染裸按钮
- [x] `syncVulnerabilityRefresh()` 方法入口新增权限守卫（无权限直接 return，不触发请求）
- [x] `src/assets/css/cve.less`：`.disabled` 光标 `cursor: text` → `cursor: not-allowed`

### Step 5: 发布评审

- [x] `src/views/Publish/publishReview/index.vue`："发布模版" / "发布设置"按钮由 `v-if` 改 `NoPermissionPopover` + `:disabled`（`auth="platform_release_config"`，`placement="bottom"`）

### Step 6: 工具市场（已回退）

- [x] ~~`src/views/ToolManagement/ToolMarket/index.vue`："创建工具"（`tool_apply`）/ "工具管理"（`tool_manage`）/ "我的流程"（`my_tool`）按钮由 `v-if` 改 `NoPermissionPopover` + `:disabled`（`placement="bottom"`）~~
- [x] 后续回退（`fix-permission-bubble-and-offline-notice` 提交 `a4f622ee`）：移除上述 `NoPermissionPopover` 包裹与导入，恢复为纯 `:disabled` 置灰控制

### Step 7: SCA 布局

- [x] `src/views/sca/layout/index.vue`：侧边导航"社区配置"按钮（`btn.value === 'managerConfiguration'`）接入 `NoPermissionPopover`（`:auth="btn.auth"`，`:disabled="!canHandle(btn.auth)"`，`placement="bottom"`），保留 `activeIndex` 高亮

### Step 8: 验证与提交

- [x] IDE LSP 诊断：无 error / warning
- [x] 业务仓 5 个 commit（`2f014068` → `20487ff0` → `fe45c9aa` → `8f4457eb` → `cb8f8842`，基于 master `ea44d2fa`，已随 `!739` 合入 `release_20260831`）
- [x] 后续回退 commit（`fix-permission-bubble-and-offline-notice` `a4f622ee`，工具市场部分，见 Step 6）
- [ ] 业务仓 PR（用户自测确认后）
- [ ] docs 仓 PR（业务 PR 合入后）

## 不在本轮范围

- 修改 `NoPermissionPopover.vue` 组件本体
- 路由级权限拦截（已有 guard.ts 负责）
- 覆盖全部页面的权限按钮（本轮仅 6 处页面场景）
- 后端权限接口 / 权限码定义改动
- 新增单元测试（改动均为模板层使用方式，无新增业务逻辑）
