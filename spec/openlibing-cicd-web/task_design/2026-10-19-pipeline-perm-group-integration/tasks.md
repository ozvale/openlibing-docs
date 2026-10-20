# 流水线权限组接入 — tasks

> 实现已随业务分支 `dev-chenning-20260923-permission-new` 完成，本清单按实际交付内容勾选。

## 1. API 层与错误处理

- [x] 1.1 `api/urls.ts`：framework 权限组 11 个端点常量（`query-resource-permissions` / `query-groups` / `create-group` / `update-group` / `delete-group` / `bind-resource` / `batch-bind-resources` / `unbind-resource` / `query-binding` / `query-bindings-by-group` / `batch-query-bindings`，2026-09-23 动词式路径重命名适配 `a8c6988`）。
- [x] 1.2 `api/api.ts`：11 个请求函数封装（组 CRUD 与 binding 查询类本期仅封装未接入页面）。
- [x] 1.3 `api/ApiClient.ts`：拦截 `LOGIN_REQUIRED_BY_GROUP` / `PERMISSION_DENIED_BY_GROUP`——关闭默认错误提示、不走登出/权限申请页，按 `error.data.groupName` 提示组名语义，rethrow 交调用方兜底。

## 2. NoPermissionPopover 组维度扩展

- [x] 2.1 新增 props：`permGroupName`（副标题指明权限组名）、`showAllRoles`（角色全集按"待申请"展示不做已有过滤）、`showDefaultGroupName`（无组名时指明「默认权限组」）、`showBothGroups`（默认组 OR 绑定组组合文案）。
- [x] 2.2 副标题四态模板分支与「待申请」chip 展示逻辑（`showAllRoles` 时空集显示"无"）；默认值下与旧版行为完全一致。
- [x] 2.3 行级气泡 placement 调整为 bottom（`b6f7552` 组版双维度提示重构）。

## 3. 列表页接入（pipeline.vue）

- [x] 3.1 组数据加载：进入项目 `getPermGroups`（下拉选项 + 组名映射）；每次列表刷新后 `queryPermGroupResourcePermissions`（不传 resourceIds 全项目绑定关系），失败静默降级空 Map。
- [x] 3.2 行级双通道鉴权 `hasRowPermission`（绑定组仅看组矩阵 / 未绑定走全局矩阵）；执行/停止按钮切换行级判定。
- [x] 3.3 单条同步双通道 OR 规则 `canSyncRow`（默认组或绑定组任一满足），气泡 `show-both-groups` 组合文案。
- [x] 3.4 新增「权限组」列（默认组灰 tag + 组名 tag，列表头 tooltip 说明，列宽 140px；操作列 110→140px）。
- [x] 3.5 行「更多操作」dropdown 收纳「切换权限组」入口（`perm_group_operate` 鉴权 + 无权限气泡）。
- [x] 3.6 切换权限组弹窗：单条/批量共用（预选当前组回显；选默认组=解绑 `unbind-resource` 并提示「已切换到默认权限组」；重复操作守卫「已在默认权限组/已在该权限组」；批量 `batch-bind-resources` 提示 `switchedCount`；文案区分单条切换/批量绑定语义；「项目成员管理页」链接；宽 520px）。
- [x] 3.7 绑定/解绑与批量按钮从两个独立入口合并为「切换权限组」单入口（`094e239`），去掉解绑二次确认弹窗，改为提示文案说明解绑语义。
- [x] 3.8 详情入口放开鉴权（列表可见即可进入，页内操作鉴权不变）；执行抽屉透传 `permGroupId`/`groupOperations`/`permGroupName`。

## 4. 详情页与编辑/执行弹窗

- [x] 4.1 详情页单资源模式调通用端点（`resourceIds=String(pipelineId)`，进入详情调一次不随 5s 轮询）+ 组名映射加载；失败降级空 Map。
- [x] 4.2 `hasDetailPermission` 双通道（未绑定保留匿名豁免 + 全局矩阵存量语义）；停止/编辑/执行按钮切换判定并透传组气泡信息。
- [x] 4.3 执行抽屉 `hasRunPermission` 双通道（绑定组看组矩阵 / 未绑定匿名豁免 + 全局矩阵），气泡组名/默认组/角色全集（`4.3` props 已在 3.8 透传）。
- [x] 4.4 编辑弹窗 `hasUpdatePermission` 双通道（详情页单条编辑传 `permGroupId` 看组矩阵；列表页批量编辑维持全局矩阵），保存按钮与气泡切换判定。
- [x] 4.5 工具栏说明辅助：保存按钮双通道判定复用（`2d99ba0` 执行抽屉与编辑弹窗补齐双通道）。

## 5. 工具栏重构与说明组件

- [x] 5.1 新增 `PipelineToolbarActionHelp.vue`：问号图标 tooltip（hover/focus），`aria-label` 组合 label 与 content。
- [x] 5.2 工具栏三入口样式统一（`toolbar-entry`/`toolbar-example-btn`，含禁用态）与正式说明文案（`toolbarActionTips`：同步含 12 小时自动同步语义、操作日志、白名单）；一键同步/操作日志/白名单管理气泡启用 `show-default-group-name`。
- [x] 5.3 白名单管理图标改内联 SVG（`114bc7a`/`952149d` 说明补充与格式调整）。

## 6. 权限元数据与过程修复

- [x] 6.1 `permissions-meta.ts` 新增 `perm_group_operate`（权限组管理介绍 + 项目管理员/服务单授权指引）。
- [x] 6.2 过程修复记录：权限判断改为两个维度都满足 + 气泡维度二动态状态（`17aa9fd`）；组版双维度提示重构 + 行级气泡 bottom（`b6f7552`）；切换弹窗复用后端默认组修复重复选项（`db08e4a`）；解绑成功提示改为切换到默认权限组语义（`99b05e7`）；提示文案按模式区分（`5929dee`）；权限组列名与说明文案优化及绑定弹窗管理入口（`e6dd448`）；行级判定与气泡提示优化（`fd150a3`）。

## 7. 验证

- [x] 7.1 改动文件 ESLint 通过，无新增 error/warn（白名单说明换行格式调整已通过检查）。
- [x] 7.2 手动验证：绑定/未绑定行的执行、停止、同步按钮判定与气泡四态文案；权限组列展示与列表头说明。
- [x] 7.3 手动验证：切换弹窗单条回显、默认组解绑、重复守卫、批量绑定切换计数、成功后刷新。
- [x] 7.4 手动验证：详情页/执行抽屉/编辑弹窗双通道判定一致性；批量编辑维持全局矩阵；匿名用户未绑定流水线可执行。
- [x] 7.5 手动验证：组错误码 toast 提示且不触发登出/权限申请页；工具栏说明图标与禁用态。
