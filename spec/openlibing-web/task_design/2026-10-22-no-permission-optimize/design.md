# 无权限提示优化 — 设计

## 1. 方案设计

无权限气泡（`NoPermissionPopover.vue`）做两处展示层优化：

1. **申请指引链接跳转**：项目级「项目管理->成员管理」点击跳转权限申请页 `/apps/noPermissionApply?showApply=true`（复用现有申请弹窗机制）；仓库级「代码仓管理->成员管理」点击跳转代码仓管理页并自动打开对应仓库成员管理；未传 `repoId` 时仓库级降级为纯文本。
2. **平台/组织级别申请指引调整**：角色归属**不隐藏任何级别**（平台/组织/项目/仓库/通用全部展示）；平台（system）、组织（product）暂不开放角色申请，申请指引**整行替换**为说明「说明：暂不开放角色申请，详情请联系人工客服进行咨询」（不带「申请指引：」标签）；通用（general）保持「申请指引：联系人工客服进行咨询」。

空态保持原逻辑与文案：后端 `rolesByLevel` 为空时显示「暂无角色配置信息，请联系项目管理员或通过服务单咨询。」

> **需求变更说明**：业务 Issue #373 原验收标准为「气泡仅展示 project/repo/general 角色组，system/product 不展示」「全部角色组被过滤后显示原空态文案」。实现阶段评审确认调整为「不隐藏任何级别，system/product 申请指引整行替换为说明文案」，空态保持「后端 `rolesByLevel` 为空」原逻辑。变更原因：平台/组织角色组仍是用户可见的权限归属信息，直接隐藏会让用户误判配置缺失；这两级暂不开放角色申请，用「说明：」文案替代申请指引即可消除误导。Issue #373 验收标准已同步更新（第 4、5 条）。

## 2. 实现逻辑设计

### 2.1 纯函数模块 `src/utils/noPermissionGuide.ts`

为可单测，将申请指引构建抽为纯函数，返回判别联合 `ApplyGuide = ApplyGuideGuide | ApplyGuideNotice`：

- `buildApplyGuide(level, ctx)`：
  - `system` / `product` → `{ type: 'notice', label: '说明：', text: '暂不开放角色申请，详情请联系人工客服进行咨询' }`（整行替换申请指引；`label` 与「申请指引：」标签同款深色加粗样式）
  - `project` → `{ type: 'guide', prefix: '联系项目管理员添加角色，', linkText: '项目管理->成员管理', link: { name: 'noPermissionApply', query: { showApply: 'true' } } }`
  - `repo` → `{ type: 'guide', prefix: '联系项目管理员添加仓库角色，', linkText: '代码仓管理->成员管理' }`；`ctx.repoId` 非空时 `link: { name: 'repos', query: { projectId, repoId, showRepoUserManage: '1' } }`，否则 `link: null`（降级纯文本）
  - `general` 及其他未知级别 → `{ type: 'guide', prefix: '联系人工客服进行咨询', linkText: '', link: null }`

### 2.2 `NoPermissionPopover.vue`

- `rolesByGroup` / `sortedRoleGroups` 直接基于后端 `rolesByLevel`（不做任何级别过滤），排序仍按 `LEVEL_DISPLAY_ORDER`。
- 申请指引行按结果类型分两支渲染：
  - `notice` 型（平台/组织）：`label`（「说明：」）+ `text`，均复用与指引型相同的标签/正文样式（`no-perm-apply-guide-label` / `no-perm-apply-guide-text`）。
  - `guide` 型（项目/仓库/通用）：`prefix` 文本 +（`link` 存在时）可点击 `el-link`，点击 `router.push(link)`。
- 空态 `v-if="!opMeta?.rolesByLevel?.length"`，文案不变。
- 引入 `useRouter`。

### 2.3 `Repos/index.vue`

- 自动打开仓库成员管理有两条触发路径，共用 `showRepoUserManageHandled` 防重入标志：
  1. **route.query watcher**（`route.query.showRepoUserManage`）：覆盖同路由点击场景——用户已在代码仓管理页时点击气泡链接，`router.push` 到同名路由仅 query 变化，`projectInfo` watcher 不触发，需该 watcher 自动打开；query 参数被清理（`val !== '1'`）时复位标志。
  2. **projectInfo watcher 兜底**（项目首次加载 `!oldValue?.projectId` 且 query 带 `showRepoUserManage` + `repoId`）：覆盖刷新场景——挂载时项目尚未加载，route watcher 先行返回，项目加载后由该 watcher 触发。
- `autoOpenRepoUserManage(repoId)`：`queryRepo` 按 repoId 查单条仓库 → 命中后 `activeTab='repo'` + `handleShowUserManage(repo)` 自动打开仓库成员管理；随后 `router.replace` 清理 `showRepoUserManage` 参数（保留其余 query），避免重复自动打开。
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
