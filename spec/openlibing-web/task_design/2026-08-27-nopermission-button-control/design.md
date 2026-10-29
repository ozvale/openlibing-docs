# 技术设计：openlibing-web 按钮无权限控制（NoPermissionPopover 落地）

- **目标仓**：`openlibing/openlibing-web`
- **业务分支**：`feature/nopermission`（fork：`vermouth_fee/openlibing-web`）
- **流程模式**：Standard
- **创建日期**：2026-08-27
- **最近同步**：对齐 `feature/nopermission` 最新提交 `cb8f8842`

## 1. 总体方案

复用既有 `NoPermissionPopover.vue` 组件（无权限 hover 三段式气泡），将"隐藏无权限按钮"（`v-if="canHandle(...)"`）统一改为"置灰 + hover 气泡提示"（`NoPermissionPopover` 包裹 + `:disabled="!canHandle(...)"`），并覆盖 6 个页面的 12 个权限码。

**统一交互约定**：

- 有权限：按钮正常可用（`:disabled=false`），`NoPermissionPopover` 气泡自动 `:disabled`（`hasPermission=true` 时组件内部禁用气泡，不显示）。
- 无权限：按钮置灰（`:disabled=true`），hover 弹出三段式气泡（无权限提示 / 角色归属级别 / 权限介绍与申请指引）。
- 权限判定：沿用全局 `canHandle(auth)`（见 `src/bootstrap.ts` `app.config.globalProperties.canHandle`，校验 `user.permissions` 是否含权限码）。
- 气泡元数据：`NoPermissionPopover` 内部从 `useAppStore().operationPermissions[auth]`（后端 `/user/get-operation-permissions`）取角色分组，从 `@/constants/permissions-meta` 的 `getPermissionMeta(auth)` 取介绍与申请指引文案。

**核心避坑点——el-tooltip 与 el-popover 嵌套冲突**：

`NoPermissionPopover` 内部是 `el-popover`（`#reference` slot 是按钮）。若按钮外层再套 `el-tooltip`，二者均基于浮层定位，会出现 tooltip 不生效 / 气泡不弹的嵌套冲突。处理方式统一为：

```vue
<NoPermissionPopover :has-permission="canHandle('xxx')" auth="xxx">
  <el-tooltip v-if="canHandle('xxx')" ...>...</el-tooltip>  <!-- 有权限才渲染 tooltip -->
  <el-button v-else :disabled="!canHandle('xxx')" ... />      <!-- 无权限渲染裸按钮 -->
</NoPermissionPopover>
```

即：`el-tooltip` 仅在有权限时渲染（`v-if`），无权限时渲染裸按钮（`v-else`）。

## 2. 各页面接入明细

### 2.1 项目管理（`src/views/Project/index.vue`）

- 操作列"编辑"按钮：`NoPermissionPopover`（`auth="project_manage:update"`，`placement="left"`）。
- 操作列"成员管理"按钮：`NoPermissionPopover`（`auth="project_user_manage"`，`placement="left"`）。
- 两处均按"el-tooltip 仅在有权限时渲染"的约定处理。
- 删除按钮维持原有 `el-popconfirm`，不在本轮范围。

### 2.2 项目成员管理（`src/views/Project/projectUserManage.vue`）

- 头部"添加项目成员"按钮：`NoPermissionPopover`（`auth="project_user_manage:add"`，`placement="bottom"`），由原 `v-if` 改为 `:disabled`。
- 成员列表操作列"编辑"按钮：`NoPermissionPopover`（`auth="project_user_manage:update"`，`placement="top"`）。
- 成员列表操作列"删除"按钮：`NoPermissionPopover`（`auth="project_user_manage:delete"`，`placement="top"`）。
- 编辑/删除按钮除权限外仍保留原有业务置灰条件（`committerList` / `judgeSyncFlag`）。

### 2.3 漏洞视图（`src/views/cve/cveManager.vue`）

- "配置"按钮（`loophole_view_config:query`，`placement="bottom"`）：原 `v-if` 改 `NoPermissionPopover` + `:disabled`，点击守卫 `canHandle(...) && (activeName = 'configure')`。
- "同步漏洞"按钮（`vulnerability_sync:button`，`placement="bottom"`）：
  - 有权限：保留 `el-tooltip`（同步时间提示）包裹原按钮；
  - 无权限：`v-else` 渲染裸按钮（去掉 `el-tooltip`，避免其事件拦截导致外层 NoPermissionPopover 气泡无法弹出）。
- **方法入口权限守卫**：`syncVulnerabilityRefresh()` 开头新增 `if (!this.canHandle('vulnerability_sync:button')) return;`，保证无权限时即使按钮被触发也不发请求。
- 辅助样式：`src/assets/css/cve.less` 中 `.disabled` 光标由 `cursor: text` 调整为 `cursor: not-allowed`，无权限置灰视觉正确。

### 2.4 发布评审（`src/views/Publish/publishReview/index.vue`）

- "发布模版"按钮：`NoPermissionPopover`（`auth="platform_release_config"`，`placement="bottom"`），原 `v-if` 改 `:disabled`。
- "发布设置"按钮：同上（同一权限码 `platform_release_config`）。

### 2.5 工具市场（`src/views/ToolManagement/ToolMarket/index.vue`）（已回退）

- ~~"创建工具"按钮：`NoPermissionPopover`（`auth="tool_apply"`，`placement="bottom"`），原 `v-if` 改 `:disabled`。~~
- ~~"工具管理"按钮：`NoPermissionPopover`（`auth="tool_manage"`，`placement="bottom"`）。~~
- ~~"我的流程"按钮：`NoPermissionPopover`（`auth="my_tool"`，`placement="bottom"`）。~~
- **后续回退**（`fix-permission-bubble-and-offline-notice` 提交 `a4f622ee`）：三个按钮移除 `NoPermissionPopover` 包裹与导入，恢复为纯 `:disabled="!canHandle(...)"` 置灰控制。`permissions-meta.ts` 中对应元数据保留（其他场景仍可引用）。

### 2.6 SCA 布局（`src/views/sca/layout/index.vue`）

- 侧边导航"社区配置"按钮（`btn.value === 'managerConfiguration'`）：`NoPermissionPopover`（`:auth="btn.auth"`，`placement="bottom"`），`:disabled="!canHandle(btn.auth)"`；`activeIndex` 高亮逻辑保留。
- 其余导航项维持原 `v-else-if="canHandle(btn.auth)"` 渲染方式，不在本轮范围。

## 3. 权限元数据（`src/constants/permissions-meta.ts`）

新增 12 个权限码元数据（`PermissionMeta`：`operationName` / `intro` / `guide`，供 `NoPermissionPopover` 展示"操作名 / 介绍 / 申请指引"）：

| 权限码                       | 操作名       |
| ---------------------------- | ------------ |
| `project_manage:update`      | 编辑项目     |
| `project_user_manage`        | 项目成员管理 |
| `project_user_manage:add`    | 添加项目成员 |
| `project_user_manage:update` | 编辑项目成员 |
| `project_user_manage:delete` | 删除项目成员 |
| `loophole_view_config:query` | 漏洞视图配置 |
| `vulnerability_sync:button`  | 同步漏洞     |
| `commu_manager`              | 社区管理     |
| `platform_release_config`    | 发布配置     |
| `tool_apply`                 | 创建工具     |
| `tool_manage`                | 工具管理     |
| `my_tool`                    | 我的流程     |

`guide` 均为两条：联系项目管理员（项目用户管理）授权 + 紧急情况走服务单。介绍文案使用 `<span class="hl">` 高亮关键角色名，与既有元数据风格一致。

## 4. 影响范围

| 文件                                            | 改动                                                             |
| ----------------------------------------------- | ---------------------------------------------------------------- |
| `src/assets/css/cve.less`                       | `.disabled` 光标 `text` → `not-allowed`                          |
| `src/constants/permissions-meta.ts`             | 新增 12 个权限码元数据并注册到 `PERMISSIONS_META`                |
| `src/views/Project/index.vue`                   | 编辑 / 成员管理按钮接入 `NoPermissionPopover`                    |
| `src/views/Project/projectUserManage.vue`       | 添加 / 编辑 / 删除成员按钮接入                                   |
| `src/views/Publish/publishReview/index.vue`     | 发布模版 / 发布设置按钮接入                                      |
| `src/views/ToolManagement/ToolMarket/index.vue` | 创建工具 / 工具管理 / 我的流程按钮接入（后续 `a4f622ee` 已回退） |
| `src/views/cve/cveManager.vue`                  | 配置 / 同步漏洞按钮接入 + `syncVulnerabilityRefresh` 权限守卫    |
| `src/views/sca/layout/index.vue`                | 社区配置按钮接入                                                 |

> 组件本体 `NoPermissionPopover.vue` 未改动，仅作为使用方引用。

## 5. 测试策略

- **改动均为模板层使用方式**，无新增逻辑单元，不引入新的单测文件。
- 权限判定复用既有 `canHandle`（bootstrap 全局注册），核心行为（三段式气泡渲染）已由 `NoPermissionPopover.vue` 既有实现保证。
- 手动验证覆盖：无权限 hover 气泡内容与角色归属正确、有权限按钮正常、无权限点击不触发业务动作（尤其同步漏洞）、`el-tooltip` 在有权限时仍正常展示。

## 6. 兼容性与回滚

- **无接口变更**：纯前端模板改动，后端权限码定义与 `/user/get-operation-permissions` 接口不变。
- **无数据模型变化**。
- 回滚：还原 8 个文件即可（`git revert` 或重置 `feature/nopermission` 到 master），无残留依赖；新增元数据条目删除后不影响其他页面。
