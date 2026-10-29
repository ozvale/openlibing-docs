# 流水线权限组接入 — proposal

- 变更目录：`spec/openlibing-cicd-web/task_design/2026-10-19-pipeline-perm-group-integration/`
- 业务分支：`dev-chenning-20260923-permission-new`（fork 仓 `weixin_45521051/openlibing-cicd-web`）
- 基线：`upstream/master`，领先 22 个 commit（含合入 `upstream/release_20261019_iter1` 工具栏说明），约 952 行新增 / 107 行删除（10 文件）
- 日期：2026-10-19

## Why

1. 流水线模块此前只有项目级全局权限矩阵（`hasOperationPermission`），无法实现"把一组流水线的操作权限收归到特定权限组"的细粒度管控；framework 已提供通用资源权限组能力（组 CRUD、绑定/解绑、组内角色判定），流水线前端尚未接入。
2. 列表页行级按钮（执行/停止/同步）与详情页操作按钮（执行/停止/编辑）均按全局矩阵判定，绑定权限组后无法反映组内真实权限，会出现"组内成员按钮误灰"或"组外成员按钮误亮"。
3. 无权限气泡只描述项目级角色申请路径，绑定组场景用户无从知道"该去哪个权限组配置什么角色"。
4. 后端新增权限组专用错误码（`LOGIN_REQUIRED_BY_GROUP` / `PERMISSION_DENIED_BY_GROUP`），前端默认错误处理会走登出/权限申请页，需要按组语义提示。
5. 工具栏"一键同步 / 操作日志 / 白名单管理"三个入口缺少正式功能说明，同步语义（12 小时自动同步）只能靠旧 tooltip 一句话带过。

## What Changes

- **列表页接入权限组**（`views/pipeline/pipeline.vue`，+652）：
  - 数据层：进入项目时 `getPermGroups` 拉组列表（绑定下拉选项 + 组名映射），每次列表刷新后调 `queryPermGroupResourcePermissions`（不传 `resourceIds`，取全项目 `PIPELINE` 绑定关系）得 `resourceBindings`（pipelineId→permGroupId）与 `groupOperations`（permGroupId→操作码布尔矩阵）。
  - 行级双通道鉴权 `hasRowPermission(row, code)`：绑定组 G 仅看 `groupOperations[G][code]`；未绑定走存量全局矩阵（逻辑零改动）。单条同步为特殊规则 `canSyncRow`：默认组或绑定组任一满足即可。
  - 新增「权限组」列：tag 展示所属组名（未绑定显示"默认权限组"灰 tag），列表头带 tooltip 说明。
  - 行操作按钮（执行/停止/同步）切换为行级判定；`NoPermissionPopover` 透传组名与角色全集状态，placement 调整为 bottom。
  - 行操作区新增「更多操作」dropdown（`MoreFilled` 图标），收纳「切换权限组」入口（`perm_group_operate` 鉴权 + 无权限气泡）。
  - 切换权限组弹窗：单条模式（绑定/改绑/解绑统一入口，预选当前组回显；选「默认权限组」即解绑 `unbind-resource`，已在默认组/目标组有重复操作守卫提示）；批量模式（`batch-bind-resources`，成功提示含 `switchedCount` 切换计数）；提示文案区分单条（切换语义）/批量（绑定语义），带「项目成员管理页」跳转链接；弹窗 520px。
  - 详情入口不做鉴权（列表可见即可进入详情，页内操作鉴权不变）。
  - 工具栏重构：一键同步/操作日志/白名单管理入口样式统一（`toolbar-entry`/`toolbar-example-btn`），各入口配 `PipelineToolbarActionHelp` 说明图标与正式文案，无权限气泡启用 `show-default-group-name`。
- **详情页接入**（`PipelineDetail/Detail.vue`，+120）：单资源模式调通用端点（`resourceIds=该流水线 id`，进入详情时调一次，不随 5s 轮询重复请求）；`hasDetailPermission(code)` 双通道；停止/编辑/执行按钮切换行级判定并透传组信息；`permGroupId`/`groupOperations` 透传给执行抽屉与编辑弹窗。
- **执行抽屉**（`pipelineRunDialog.vue`，+38）：`hasRunPermission` 双通道（绑定组看组矩阵；未绑定保留"匿名豁免 + 全局矩阵"存量语义）；无权限气泡透传组名/默认组/角色全集。
- **编辑弹窗**（`pipelineEditDialog.vue`，+29）：`hasUpdatePermission` 双通道（从详情页单条编辑传入 `permGroupId` 看组矩阵；列表页批量编辑不传，维持存量全局矩阵）。
- **NoPermissionPopover 增强**（`components/NoPermissionPopover.vue`，+82）：新增 4 个纯展示 props——`permGroupName`（副标题指明"在权限组「xxx」中配置"）、`showAllRoles`（绑定组场景角色全集按"待申请"展示，不做"已有"过滤）、`showDefaultGroupName`（无组名时副标题指明「默认权限组」）、`showBothGroups`（默认组 OR 绑定组任一满足的组合文案）；判定逻辑不变。
- **ApiClient 权限组错误码**（`api/ApiClient.ts`，+16）：拦截 `LOGIN_REQUIRED_BY_GROUP` / `PERMISSION_DENIED_BY_GROUP`，不触发登出/权限申请页，`ElMessage` 提示"请联系项目管理员在权限组「groupName」中为你配置相应权限"（无组名时提示"暂无该资源的操作权限"）。
- **API 层**（`api/api.ts` / `api/urls.ts`，+36）：framework 权限组 11 个端点封装（`query-resource-permissions` / `query-groups` / `create-group` / `update-group` / `delete-group` / `bind-resource` / `batch-bind-resources` / `unbind-resource` / `query-binding` / `query-bindings-by-group` / `batch-query-bindings`，2026-09-23 动词式路径）。
- **权限元数据**（`constants/permissions-meta.ts`，+17）：新增 `perm_group_operate`（权限组管理：创建/删除权限组、绑定/解绑流水线，需项目级管理角色；指引：项目管理员授权 / 服务单）。
- **工具栏说明组件**（`PipelineToolbarActionHelp.vue`，新增 69 行）：带 `aria-label` 的问号图标 tooltip，承载一键同步（含 12 小时自动同步语义）/操作日志/白名单管理正式说明。

## Capabilities

### New Capabilities

- `pipeline-perm-row-auth`: 流水线列表行级双通道鉴权（绑定组看组矩阵 / 未绑定走全局矩阵）、单条同步双通道 OR 规则及失败降级（空 Map 回退全局矩阵）行为。
- `pipeline-perm-switch-dialog`: 切换权限组弹窗的单条绑定/改绑/解绑与批量绑定的交互、回显、守卫与提示行为。

### Modified Capabilities

- `pipeline-detail-perm`: 详情页/执行抽屉/编辑弹窗操作按钮从全局矩阵判定改为双通道判定（未绑定场景行为不变）。
- `no-permission-popover`: 无权限气泡新增组维度文案状态（不影响既有判定与展示结构）。
- `pipeline-toolbar`: 工具栏三入口样式重构并新增正式功能说明图标。

## Impact

- **受影响代码**：`src/views/pipeline/pipeline.vue`、`PipelineDetail/Detail.vue`、`PipelineEdit/pipelineEditDialog.vue`、`pipelineRunDialog.vue`、`PipelineToolbarActionHelp.vue`（新增）、`src/components/NoPermissionPopover.vue`、`src/api/{api,urls,ApiClient}.ts`、`src/constants/permissions-meta.ts`。
- **受影响接口**（framework 网关代理）：`GET /perm-group/query-resource-permissions`、`GET /perm-group/query-groups`、`POST /perm-group/bind-resource`、`POST /perm-group/batch-bind-resources`、`POST /perm-group/unbind-resource`；错误码 `LOGIN_REQUIRED_BY_GROUP` / `PERMISSION_DENIED_BY_GROUP` 新语义。
- **风险**：
  - 绑定组判定只看组矩阵，后端若未把全局角色操作码合并进 `groupOperations`，组内成员按钮会误灰（前端注释已声明该契约）。
  - `query-resource-permissions` 全项目量级随流水线数增长，当前随列表刷新全量拉取且静默失败（失败回退全局矩阵，可能出现按钮状态短暂失真）。
  - 批量绑定以 `switchedCount` 提示切换条数，依赖后端返回该字段。
  - ApiClient 组错误码分支 `throw error` 会中断调用方后续 `.then`，依赖调用方已有 `.catch(() => {})` 兜底。
  - 切换弹窗默认组 id 硬编码为 0，依赖"后端组列表内置默认组且 id 固定为 0"的约定。
