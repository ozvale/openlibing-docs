# 流水线权限组接入 — design

## 方案设计

总体分四层：数据接入层（API 封装 + ApiClient 错误码）、通用组件层（NoPermissionPopover 组维度扩展）、页面接入层（列表页 / 详情页 / 执行抽屉 / 编辑弹窗的双通道判定）、配置层（权限元数据）：

```text
api/urls.ts / api.ts        # framework 权限组 11 端点封装（动词式路径）
api/ApiClient.ts            # LOGIN_REQUIRED_BY_GROUP / PERMISSION_DENIED_BY_GROUP 拦截
components/NoPermissionPopover.vue  # +permGroupName / showAllRoles / showDefaultGroupName / showBothGroups
views/pipeline/pipeline.vue                 # 列表页：组数据加载、行级双通道、权限组列、切换弹窗、工具栏重构
views/pipeline/PipelineDetail/Detail.vue    # 详情页：单资源端点 + hasDetailPermission + props 下传
views/pipeline/pipelineRunDialog.vue        # 执行抽屉：hasRunPermission
views/pipeline/PipelineEdit/pipelineEditDialog.vue  # 编辑弹窗：hasUpdatePermission
views/pipeline/PipelineToolbarActionHelp.vue        # 工具栏说明图标（新增）
constants/permissions-meta.ts               # perm_group_operate 元数据
```

## 实现逻辑设计

### 1. 组数据模型与加载策略

- 三份核心状态：`resourceBindings: resourceId→permGroupId`（不在 Map 中 = 未绑定 = 默认组）、`groupOperations: permGroupId→{操作码→bool}`（后端已把全局角色操作码合并进各组）、`permGroupNameMap: permGroupId→groupName`。
- 列表页：`getPermGroups` 在进入项目时加载一次（下拉选项 + 组名映射）；`queryPermGroupResourcePermissions`（不传 `resourceIds`）在每次列表刷新成功后并行加载，`disabledLoading` 静默，失败清空两个 Map 降级为"全部未绑定"回退全局矩阵。
- 详情页：进入详情调一次通用端点（`resourceIds=String(pipelineId)` 单资源模式），不随 5s 轮询重复请求；组名映射同样仅进入时加载。
- 匿名/失败统一降级：空 Map → 全部按未绑定 → 存量全局矩阵，不白屏。

### 2. 行级双通道鉴权（核心契约）

```text
hasRowPermission(row, code):
  groupId = resourceBindings[row.pipeline_id]
  groupId === undefined → app.hasOperationPermission(code)   // 存量全局矩阵，逻辑零改动
  否则            → groupOperations[groupId][code] === true  // 仅看组矩阵，勿再叠加全局矩阵
```

- 后端已合并全局角色操作码进各组 → 前端若叠加全局矩阵会导致组内成员按钮误灰（代码注释明确该契约）。
- 特例：单条同步 `canSyncRow = 组矩阵通过 || 全局矩阵通过`（默认组 OR 绑定组任一满足）。
- 未绑定场景保留匿名豁免语义（详情/执行抽屉 `!app.user?.userId` 直接放行）。
- 详情入口不鉴权：列表可见即可进入详情页，页内操作鉴权不变。

### 3. 切换权限组弹窗（单条/批量共用）

- 打开入口：行 dropdown「切换权限组」（`perm_group_operate` 鉴权）→ 单条模式，预选当前组回显（未绑定预选默认组）；批量操作按钮 → 批量模式（空选中 warning）。
- 默认组约定：后端组列表内置默认组且 id 固定为 0（`DEFAULT_GROUP_ID = 0`）；单条选中默认组 = 解绑。
- 提交分支：单条 + 默认组 → 重复守卫（已在默认组 warning）→ `unbind-resource`，成功提示「已切换到默认权限组」；单条 + 自定义组 → 重复守卫（已在目标组 warning）→ `bind-resource`，按是否原已绑定提示「切换成功/绑定成功」；批量 → `batch-bind-resources`，成功提示含 `switchedCount`（「绑定成功，其中 N 条已从原组切换」）。
- 文案区分：`bindPermGroupAlertText` computed——单条为切换语义（含解绑说明），批量为绑定语义；均带「项目成员管理页」新窗口链接（`/apps/project?showCurrentProjectManagers=true`）。
- 成功后关闭弹窗并重新拉取组总览，弹窗宽度 520px。

### 4. NoPermissionPopover 组维度扩展（纯展示）

- `permGroupName`：副标题改为"需要下列任一角色，请联系项目管理员在权限组「xxx」中配置"。
- `showAllRoles`：绑定组场景按钮判定只看组内角色，项目级"已有"不代表组内满足 → 角色清单不做"已有/待申请"过滤，全集按"待申请"chip 展示供配置参考；空集显示"无"。
- `showDefaultGroupName`：无组名时副标题指明「默认权限组」。
- `showBothGroups`：与 `permGroupName` 同传时副标题组合"「默认权限组」或权限组「xxx」任一配置即可"（单条同步 OR 场景）。
- 四者只影响文案与展示，不改变 `hasPermission` 判定与气泡结构；列表行按钮气泡 placement 统一 bottom。

### 5. ApiClient 组错误码拦截

- 在既有错误处理前插入分支：`code === LOGIN_REQUIRED_BY_GROUP | PERMISSION_DENIED_BY_GROUP` → 关闭默认错误提示（`enabledErrorMsg = false`），不走 401 登出 / 权限申请页；`ElMessage.error` 按 `error.data.groupName` 有无提示「请联系项目管理员在权限组「groupName」中为你配置相应权限」或「暂无该资源的操作权限」，随后 `throw error` 交调用方（调用方以 `.catch(() => {})` 兜底）。

### 6. 工具栏重构与说明组件

- 三入口（一键同步/操作日志/白名单管理）样式统一为 `toolbar-entry`（带图标文字按钮，禁用态置灰）；一键同步为 `toolbar-example-btn` 边框按钮 + `PipelineToolbarActionHelp` 说明图标。
- `PipelineToolbarActionHelp`：问号图标 + `el-tooltip`（hover/focus 触发），`aria-label` 为「label。content」保证无障碍可读；文案收敛在 `toolbarActionTips` 常量（同步含"每 12 小时自动同步"语义）。
- 无权限气泡对三入口启用 `show-default-group-name`，提示按默认组粒度申请。

## 类设计

无新增类；均为组合式 API 页面内函数与纯展示组件 props 扩展。

## 数据模型设计

- 前端新增三份响应式映射（`resourceBindings` / `groupOperations` / `permGroupNameMap`），结构由 framework 通用端点响应决定：
  - `resourceBindings: Record<resourceId, permGroupId>`
  - `groupOperations: Record<permGroupId, Record<operationCode, boolean>>`
  - 组列表项：`{ id, groupName }`（默认组 id 固定 0）
- 无本地持久化，无 schema/迁移。

## 性能设计

- 组总览随列表刷新并行加载且 `disabledLoading`，不阻塞列表渲染；失败静默降级。
- 详情页端点仅进入时一次，不随 5s 轮询放大请求量。
- 绑定/解绑/批量操作成功后仅重拉组总览（不整页刷新）。

## API接口设计

前端仅消费（无后端改动，本仓为前端仓）：

| 方法 | 路径（FRAME_WORK 代理）                                         | 用途                                                       |
| ---- | --------------------------------------------------------------- | ---------------------------------------------------------- |
| GET  | `/perm-group/query-resource-permissions`                        | 通用资源权限总览（列表不传 resourceIds 全量；详情传单个）  |
| GET  | `/perm-group/query-groups`                                      | 项目权限组列表（含内置默认组）                             |
| POST | `/perm-group/bind-resource`                                     | 单条绑定/改绑（payload 含 `resourceDisplayInfo`）          |
| POST | `/perm-group/batch-bind-resources`                              | 批量绑定（返回 `switchedCount`）                           |
| POST | `/perm-group/unbind-resource`                                   | 解绑回默认组（query 传 projectId/resourceType/resourceId） |
| —    | 错误码 `LOGIN_REQUIRED_BY_GROUP` / `PERMISSION_DENIED_BY_GROUP` | 组维度无权限，`data.groupName` 随错误返回                  |

其余 6 个端点（组 CRUD + binding 查询类）本期仅封装未接入页面。

## 安全设计

- 前端判定仅控制按钮可用性与提示，权限强校验在后端；前端矩阵不可信原则不变。
- `perm_group_operate` 元数据声明项目级管理角色要求，气泡引导走项目管理员授权/服务单，不暴露授权实现细节。
- ApiClient 拦截不吞错误（rethrow），不因错误分支泄露堆栈/敏感信息（仅展示后端给的 groupName）。

## 影响范围

| 维度     | 说明                                                                                                                          |
| -------- | ----------------------------------------------------------------------------------------------------------------------------- |
| 组件契约 | `NoPermissionPopover` 新增 4 个可选 props，默认值下行为与旧版完全一致（向后兼容）；`PipelineToolbarActionHelp` 为新增独立组件 |
| 页面行为 | 列表/详情/执行/编辑的操作按钮判定从"仅全局矩阵"变为"双通道"；未绑定行/未传组场景行为零变化                                    |
| 接口契约 | 新消费 5 个 framework 端点 + 2 个组错误码语义                                                                                 |
| 样式     | 工具栏入口视觉重构；操作列宽 110→140px；新增权限组列 140px                                                                    |
| 兼容性   | 默认组 id=0 依赖后端约定；批量绑定提示依赖 `switchedCount` 字段                                                               |

## 验证方式

1. `pnpm lint` 改动文件无新增 error/warn（白名单说明换行已按格式检查调整）。
2. 手动验证列表页：绑定行的执行/停止/同步按钮按组矩阵置灰与放行；未绑定行走全局矩阵；无权限气泡组名/角色全集/默认组/双组文案四态正确；权限组列 tag 与列表头 tooltip。
3. 手动验证切换弹窗：单条回显当前组、选默认组解绑（已在默认组守卫）、改绑重复守卫、批量绑定 `switchedCount` 提示、成功后列表组列刷新。
4. 手动验证详情页/执行抽屉/编辑弹窗：双通道判定与列表一致；单条编辑保存按钮按组矩阵；批量编辑维持全局矩阵；匿名用户未绑定流水线可执行（存量语义）。
5. 手动验证组错误码：无组权限操作时 toast 按组名提示，不触发登出/权限申请页。
6. 手动验证工具栏：三入口说明图标 hover/focus 文案、无障碍 aria-label、禁用态与气泡。
