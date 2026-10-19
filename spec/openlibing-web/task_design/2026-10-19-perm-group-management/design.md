# 权限组管理（前端）— design

## 总体结构

改动按"API 封装 → 权限元数据 → 页面/组件"三层落位，全部位于 `apps/web-openlibing/src/`：

```text
api/url.ts                          # 9 个 /perm-group/* 端点常量
api/api.ts                          # 9 个 RequestFunc 封装
constants/permissions-meta.ts       # perm_group_operate 操作码元数据
views/Project/projectUserManage.vue # 成员管理页（入口按钮/筛选/列/添加修改透传）
views/Project/components/ManagePermGroupDialog.vue  # 权限组管理弹窗（新增）
components/BatchAddMemberDialog.vue # 批量添加成员多组分态
```

## 关键设计决策

### 1. 默认权限组语义：`id = 0`，请求不携带 `permGroupId`

- 项目创建时后端自动生成默认权限组，前端以 `id === 0` 标识。
- 添加/修改成员时，`permGroupId` 为 0 或空均**不携带**该字段——默认组路径保留后端成员自动同步/审计联动，显式选组才透传。
- UI 兜底：成员列表权限组列 `permGroupName` 为空时展示「默认权限组」tag；批量添加弹窗权限组多选默认值 `[0]`（选项列表仅含自定义组，0 表示默认组）。

### 2. 权限控制：`perm_group_operate` 操作码 + NoPermissionPopover

- 管理权限组入口按钮、创建/编辑/删除按钮统一挂 `canHandle('perm_group_operate')`：无权限时 `NoPermissionPopover` 气泡说明授权路径（项目管理员角色 / 服务单），按钮 `disabled` 置灰。
- 默认组行不渲染编辑/删除按钮（而非置灰），避免暗示可操作。
- `permissions-meta.ts` 为 `perm_group_operate` 维护 `operationName`/`intro`/`guide`，供权限说明页与气泡复用。

### 3. ManagePermGroupDialog 弹窗内聚三层子弹窗

- 主弹窗（720px）：组列表 `el-table`（组名/说明/成员数/绑定资源数/操作），顶部 info alert 说明"成员同步等通用功能仍按默认权限组校验"。
- 创建子弹窗（480px）：组名（必填）+ 说明 + 复制来源（下拉已有组，可空白创建）；成功后若响应含 `copiedCount`/`excludedCount` 回显「已复制 N 人，另有 M 人因自动同步未纳入」。
- 编辑子弹窗（480px）：仅组名 + 说明（默认组不可编辑）。
- 绑定资源子弹窗（800px）：`getPermBindingsByGroup` **服务端分页**（pageNum/pageSize + total），类型筛选（PIPELINE）+ 名称搜索（`resourceName`），筛选/改 pageSize 重置页码；默认组绑定数展示 `--` 并附 tooltip 说明。
- 删除守卫链：默认组直接 warning → `bindingCount > 0` 提示先解绑 → `ElMessageBox.confirm` 二次确认（删除成员记录连带清理文案）。
- 对外契约：`defineExpose({ openDialog })` 供父组件 `$refs` 调用；组变更后 `emit('refresh')`，父组件刷新权限组筛选下拉。

### 4. 批量添加成员：按"账号 × 组"结果矩阵与失败组重试

- 数据结构：`Map<account, Map<groupId, { ok, msg }>>`，组 id 以 `0` 表示默认组。
- 提交：选中组集合每组构建一个请求（`gid !== 0` 才带 `permGroupId`），**过滤掉该组已成功的账号**后 `Promise.all` 并行发送。
- 结果合并：基于旧 Map 拷贝生成新 Map，仅覆写本轮发送的"账号 × 组"格子，成功结果跨轮保留。
- 整体判定：全部账号 × 全部选中组均 ok → 成功并锁表单；存在 500 且无明细 error → 整体失败可重提；否则 warning「存在添加失败的数据」并锁表单进入重试态。
- 重试态：`resetUsers` 仅保留存在失败的账号行，并清理无失败结果账号的历史格子；再次提交只发失败组。
- 展示：多组（`permGroupIds.length > 1`）时每行按组纵向分态（组名 + ✓/✗ + 失败原因 tooltip）；单组保持原有"添加成功 / 添加失败，原因"表现。
- 弹窗关闭/重开：结果清空、权限组重置 `[0]`、重新拉取组列表（`repo` 类型不展示权限组项）。

### 5. 成员管理页集成

- 筛选：`formInline.permGroupIds` 多选，仅非空时加入 `getCommunityUser` 请求体；`getFormInline` 合并外部筛选时保留已有权限组筛选不被覆盖。
- 列：权限组列位于表格前列，tag 展示，表头 `?` tooltip 说明默认组两条规则（随项目创建生成不可编辑删除、绑定后仅组内对应角色可操作）。
- 单条添加/修改弹窗：`permGroupId` 非 0 非空才透传。

## 影响范围

| 维度     | 说明                                                                                                      |
| -------- | --------------------------------------------------------------------------------------------------------- |
| 组件契约 | `ManagePermGroupDialog` 为新增组件；`BatchAddMemberDialog` 新增 project 类型专属表单项，repo 类型行为不变 |
| 接口契约 | 消费 framework `/perm-group/*` 动词式新路径（2026-09-23 重命名后）；成员三接口为可选字段扩展，向后兼容    |
| 权限     | 新增 `perm_group_operate` 操作码依赖后端下发                                                              |
| 兼容性   | 不选自定义组时请求体与原行为一致；旧成员（未入自定义组）列表展示「默认权限组」                            |
| 测试     | 应用内该模块无既有单测；以 lint/typecheck + 手动联调验证（与仓内现状一致）                                |

## 验证方式

1. `pnpm lint`（或改动文件范围 ESLint）无新增 error/warn。
2. `pnpm check:type` 无本模块相关错误。
3. 手动联调：创建（含复制来源）→ 列表回显复制统计 → 编辑 → 绑定资源分页/筛选 → 删除守卫链；成员列表权限组筛选、权限组列展示；单条/批量添加成员指定组、多组分态结果与失败组重试；无 `perm_group_operate` 权限账号全按钮置灰。
