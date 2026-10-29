# Design: 项目名称变更与项目漏洞相关配置

## 1. 表单扩展「对接漏洞视图」（需求①）

**核心事实**：`projectAddEditForm.vue` L53-58 存在被注释的 `isCve` radio（当年后端未就绪），`formData.isCve` 默认 `'0'`（L508），新增/修改 payload 均已提交 `isCve`（L799、L864）。本次为**恢复 + 补校验**，非从零开发。

改动点：

1. 恢复 L53-58 注释块，label 定为「对接漏洞视图」（原注释为错别字「漏洞试图」，弃用）
2. **默认值 `'0'`（默认选否）**：与其他 radio 项（`isHwProject` / `isHaveCommonAccount`）完全一致，无必填符号、不做非空校验
3. radio 取值保持字符串 `'1'` / `'0'`，与 `isHwProject` / `isHaveCommonAccount` 一致；提交时后端接口若要求数值型再在 payload 处转换（以后端契约为准，当前 payload 直传字符串与既有字段行为一致）
4. 位置：**新增项目**时置于全部原有配置项下方（整行 w-100、label 左置，从上到下排列）；**修改项目**时占用「同步项目成员」所在行的末尾空位（替换原 `<el-form-item />` 占位，label 左置与同行项一致；未勾选「对接代码托管平台」时该行不存在，isCve 兜底显示在「对接代码托管平台」radio 之后）
5. 编辑态回填：`getProjectDetailInfo` 详情接口已确认返回 `isCve`，编辑时直接回填

参照实现（同文件 L65-86 `isHwProject`）：

```vue
<el-form-item label="对接漏洞视图" label-position="left">
  <el-radio-group v-model="formData.isCve">
    <el-radio value="1" size="large">是</el-radio>
    <el-radio value="0" size="large">否</el-radio>
  </el-radio-group>
</el-form-item>
```

## 2. 项目管理列表新增 3 列（需求②）

仅新增展示列，不涉及筛选/排序/分页/导出能力。`src/views/Project/index.vue` L27-30 项目名称列之后插入 3 列：

```vue
<el-table-column label="是否对接华为云项目" prop="isHwProject">
  <template #default="scope">{{ scope.row.isHwProject === 1 ? '是' : '否' }}</template>
</el-table-column>
```

- `isHaveCommonAccount`、`isCve` 同构；字段为空/undefined 时渲染 `'--'`（与更新人/更新时间列的空值兜底一致）
- 值类型归一已确认：统一封装 `formatYesNo`，内部 `Number(val)` 归一后 1→「是」、0→「否」、其他→`'--'`（兼容后端返回数值或字符串 `'1'`）
- 树形懒加载的子行数据由 `loadProject` 递归拉取，新列随行数据自动渲染，无需额外处理
- 表头宽度：3 列均为长表头（8 字符），设置 `min-width: 120` 避免表头换行

## 3. 项目名称修改（需求③）

### 3.1 入口方案对比

| 方案                          | 说明                                                                                                                                                                                                                                                                                                                                                                                                                                                                           | 结论                                                                                                |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------- |
| A. 项目名称列后方图标         | 名称列内拼接 edit 图标                                                                                                                                                                                                                                                                                                                                                                                                                                                         | 否决：全系统列表无「列内嵌操作图标」先例；名称列窄、图标悬浮目标小；权限 popover 组件在列内排版突兀 |
| **B. 操作列图标按钮（采用）** | 操作列「编辑」旁新增「修改名称」图标                                                                                                                                                                                                                                                                                                                                                                                                                                           | 与现有编辑/成员管理的交互、权限、tooltip、uem 埋点模式完全一致，组件复用零成本                      |
| 附：操作列收纳                | 新增「修改名称」后操作数达 4 个，超过 2 个即收纳；参照敏感词集列表（`SensitiveDict/children/RuleTable.vue`）MoreFilled「更多」el-popover 模式：前 2 个高频操作（编辑、成员管理）直出图标，其余（修改名称、删除）收进弹层；弹层内项**沿用原有图标**（EditPen / Delete）+ el-tooltip 悬浮展示操作名称，修改名称保留 NoPermissionPopover 权限链路、删除保留 el-popconfirm 确认；点击弹层内操作先关闭弹层再执行；弹层样式用独立 popper-class + 全局 style 块（popover 挂 body 下） |

### 3.2 权限设计

- 独立权限码 **`project_manage:rename`**（与 `project_manage:update` 平级，命名遵循 `模块:操作` 既有风格）
- 入口控制与 L46-75 编辑按钮完全同构：`NoPermissionPopover :has-permission="canHandle('project_manage:rename')" auth="project_manage:rename"` 包裹 + 按钮 `:disabled` 双重校验，无权限不渲染可点击入口
- 同步登记 `src/constants/permissions-meta.ts` `PERMISSIONS_META`（无权限提示文案）
- 权限码后端配置生效前，`canHandle` 返回 false 入口不可见——前端可先行开发，联调依赖后端权限数据

### 3.3 编辑弹窗（新组件 `src/views/Project/projectRenameDialog.vue`）

- `el-dialog` 独立弹窗：标题「修改项目名称」，内容仅 1 个名称输入框 + 确认/取消按钮，宽度 480px（参照系统内小型表单弹窗）
- props：`projectId`、`projectName`（当前值回填）、visible 控制；emit `success` 通知列表刷新
- 校验规则（el-form rules）：
  - 非空：required，trigger blur
  - 长度：上限与新增项目一致——**现状 `projectName` 仅 required 无长度校验**，本次新增/修改弹窗统一补 `max: 50`（后端已确认上限 50）
  - 重复：后端确认不提供独立重复校验接口，由 `/project/update-project-name` 保存接口校验名称重复并返回冲突错误信息，前端 toast 后端 message
- 确认按钮 loading 态防重复提交，成功后 ElMessage 提示 + 关闭弹窗 + 刷新当前表格数据（含父行缓存：树形 lazy 加载需清空 `lazyTreeNodeMap` 对应缓存或整体重查，见 3.4）
- 取消/关闭：直接关闭弹窗，无二次确认（输入内容不保留）

### 3.4 API 与数据刷新

- `src/api/url.ts` 新增 URL 常量（FRAME_WORK 前缀），`src/api/api.ts` 新增 `updateProjectName: RequestFunc`；路径已确认：POST `/project/update-project-name`，参数拼接在 URL query（`projectId: Integer`、`projectName`）
- **树形缓存踩坑**：el-table lazy 树的行数据缓存在内部 `lazyTreeNodeMap`，改名后需刷新。方案：改名行若为子行，找到其父行重新触发 load；简化方案为整表重查（`tableData` ref 置空 + `queryProject` 重拉 + `el-table` ref 清空 lazy 缓存 `tableRef.value.store.states.lazyTreeNodeMap.value = {}`）。采用简化方案，行为可接受（项目列表数据量小）

## 4. 漏洞视图「社区配置」二级页签（需求④）

### 4.1 挂载位置

「社区配置」不是 `cveConfigure.vue` 的独立一级页签，而是 **`src/views/cve/cveAdaptation.vue`（社区适配）左侧二级页签的末尾项**：

- `typeList` 追加第三项 `{ label: 'cve.communityConfig', prop: 'communityConfig' }`，与既有「可适配字段 / 社区管理员」并列，激活态样式（#4971ff 高亮竖线）由既有 `.tabItem.active` 样式自动生效
- `rightPart` 新增 `v-show="activeName === 'communityConfig'"` 区块，与 project/community 两个区块互斥切换
- i18n：`src/i18n/{zh,en}/cve.js` 补 `cve.communityConfig` key（社区配置 / Community Configuration）

### 4.2 配置项实现（cveAdaptation.vue 内嵌）

完全复用该页签既有查看/编辑模式（`proDisabled` / `comDisabled` 同构，新增 `configDisabled`）：

- 查看态：`configDisabled = true`，input 只读 +「编辑」按钮
- 编辑态：点「编辑」置 false，出现「提交/取消」按钮；取消恢复 `configInit` 快照并 `clearValidate`；提交校验通过后调保存接口，成功后重查（实时生效）
- 3 个配置项字段与后端契约对齐（`/project/*-cve-config`，framework 网关前缀）：

| 配置项                 | 字段名           | 控件     |
| ---------------------- | ---------------- | -------- |
| gitee 组织名称         | `orgPath`        | el-input |
| gitee 企业名称         | `enterpriseName` | el-input |
| 接入漏洞的库表社区名称 | `cveOrg`         | el-input |

- 接口（均已确认，`src/api/url.ts` / `api.ts` 已登记 `addCveConfig` / `updateCveConfig` / `deleteCveConfig` / `getCveConfig`，FRAME_WORK 前缀）：
  - 查询：GET `/project/get-cve-config`，参数拼接在 URL query（`projectId` 取 `useAppStore().projectInfo?.projectId`）
  - 新增：POST `/project/add-cve-config`，body `data`：`projectId、cveOrg、orgPath、enterpriseName`
  - 修改：POST `/project/update-cve-config`，body 同新增
  - 清空：POST `/project/delete-cve-config`，参数拼接在 URL query（`projectId`；查看态「清空」按钮，confirmDialog.danger 确认后调用；三项配置均为空时按钮禁用）
- 保存策略：查询结果任一字段有值视为已有配置（`hasCveConfig`），保存时走修改接口，否则走新增接口
- `initData()` 追加 `getConfigData()` 调用，随页签激活时机统一加载

## 影响范围

| 文件                                    | 变更                                                                        |
| --------------------------------------- | --------------------------------------------------------------------------- |
| `views/Project/projectAddEditForm.vue`  | 恢复 isCve radio（默认 '0' 选否，无必填符号）；编辑回填                     |
| `views/Project/index.vue`               | 新增 3 状态列；操作列新增「修改名称」入口；引入改名弹窗                     |
| `views/Project/projectRenameDialog.vue` | 新建：改名弹窗（校验 + 提交 + 树形缓存刷新回调）                            |
| `constants/permissions-meta.ts`         | 登记 `project_manage:rename` 元数据                                         |
| `api/url.ts` / `api/api.ts`             | 新增 `updateProjectName`（POST `/project/update-project-name`，query 参数） |
| `views/cve/cveAdaptation.vue`           | 二级页签末尾新增「社区配置」+ 3 配置项 查看/编辑/保存                       |
| locale 中英文文件                       | 新增 `cve.communityConfig` i18n key、弹窗文案                               |

## Trade-off（有意接受）

1. 名称长度上限已确认为 50；重复校验无独立接口，由保存接口返回冲突错误信息，前端不做 blur 重复预校验
2. 「修改名称」权限码 `project_manage:rename` 后端权限数据生效前入口不可见（canHandle false），不影响其余功能交付
