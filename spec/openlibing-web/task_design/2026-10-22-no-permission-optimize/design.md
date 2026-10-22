# 无权限提示优化 — 设计

## 1. 方案设计

无权限气泡（`NoPermissionPopover.vue`）做两处展示层优化：

1. **申请指引链接跳转**：项目级「项目管理->成员管理」点击跳转权限申请页 `/apps/noPermissionApply?showApply=true`（复用现有申请弹窗机制）；仓库级「代码仓管理->成员管理」点击跳转代码仓管理页并自动打开对应仓库成员管理；未传 `repoId` 时仓库级降级为纯文本。
2. **角色组过滤**：只过滤掉 `system`（平台）、`product`（组织）两级角色组，保留 `project`（项目）、`repo`（仓库）、`general`（通用）。

空态展示条件由「后端 `rolesByLevel` 为空」调整为「过滤后为空」，文案不变。

## 2. 实现逻辑设计

### 2.1 新增纯函数模块 `src/utils/noPermissionGuide.ts`

为可单测，将过滤与指引构建抽为纯函数：

- `APPLICABLE_LEVELS: string[]` = `['project', 'repo', 'general']`
- `filterApplicableRoleGroups(groups: any[]): any[]`：按 `level` 过滤，仅保留 `APPLICABLE_LEVELS` 中的级别。
- `buildApplyGuide(level, ctx): { prefix: string; linkText: string; link: { path; query } | null }`：
  - `project` → `prefix: '联系项目管理员添加角色，'`，`linkText: '项目管理->成员管理'`，`link: { path: '/apps/noPermissionApply', query: { showApply: 'true' } }`
  - `repo` → `prefix: '联系项目管理员添加仓库角色，'`，`linkText: '代码仓管理->成员管理'`；`ctx.repoId` 非空时 `link: { path: '/apps/repos', query: { projectId, repoId, showRepoUserManage: '1' } }`，否则 `link: null`（降级纯文本）
  - `general` 及其他未知级别 → `prefix: '联系人工客服进行咨询'`，`linkText: ''`，`link: null`

### 2.2 `NoPermissionPopover.vue`

- `rolesByGroup` / `sortedRoleGroups` 基于 `filterApplicableRoleGroups(opMeta.rolesByLevel)` 计算（排序仍按 `LEVEL_DISPLAY_ORDER`）。
- 申请指引行渲染：`prefix` 文本 +（`link` 存在时）可点击 `el-link`，点击 `router.push(link)`。
- 空态 `v-if` 条件改为 `!sortedRoleGroups.length`，文案不变。
- 引入 `useRouter`。

### 2.3 `Repos/index.vue`

- 项目首次加载（`!oldValue?.projectId`）且 `route.query.showRepoUserManage === '1'`、`route.query.repoId` 存在时，调用新增 `autoOpenRepoUserManage(repoId)`：`queryRepo` 按 repoId 查单条仓库 → 命中后 `activeTab='repo'` + `handleShowUserManage(repo)` 自动打开仓库成员管理；随后 `router.replace` 清理 `showRepoUserManage` 参数（保留其余 query），避免重复自动打开。
- 项目切换时的 URL 清理列表（`restQuery` 解构）补充 `showRepoUserManage`。

## 3. 类设计

不涉及（纯前端 Vue 组件 + 工具函数模块）。

## 4. 数据模型设计

不涉及。

## 5. 性能设计

不涉及。仓库级自动打开仅复用现有 `queryRepo` 接口单条查询（`pageSize: 1`），与既有 `autoGoBranch` 模式一致。

## 6. API接口设计

不涉及新增接口。复用：

- 路由 `/apps/noPermissionApply`（`name: noPermissionApply`，已支持 `?showApply=true` 自动弹申请弹窗）
- 路由 `/apps/repos`（`name: repos`）
- 接口 `queryRepo`（既有仓库查询）

## 7. 安全设计

- 鉴权：不涉及。纯展示层改动，不改变任何权限判定逻辑。
- 敏感信息：不涉及。
- 硬编码：不涉及（跳转路径为平台既有公开路由）。
- 审计日志：不涉及。
