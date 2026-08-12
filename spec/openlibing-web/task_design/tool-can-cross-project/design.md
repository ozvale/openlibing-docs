# tool-can-cross-project — 技术设计

## 方案概述

在工具版本列表的列配置 `toolManageVersionSoftwareColumns` / `toolManageVersionVisitPathColumns` 中新增 `canCrossProject` 列，绑定 `fnName: handleToolCanCrossProject`。在 `toolTable.vue` 中为该列自定义 `el-switch` 渲染，开关切换前通过 `beforeSwitchChange` 拦截，交由父组件 `toolItem.vue` 的 `toolCanCrossProject` 方法处理二次确认与接口调用。同时将「更新时间」列替换为「创建时间」列，并移除操作列固定宽度。

## 架构决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 列渲染方式 | 复用 `toolTable.vue` 的 `column.prop` 分发机制 + `el-switch` 自定义渲染 | 与既有 `handleToolUsageStatus` 等列保持一致的渲染模式，无新技术引入 |
| 切换前拦截 | `el-switch` 的 `before-change` 属性返回 Promise | Element Plus 原生支持，false 时阻止切换，无需手动回滚开关状态 |
| 二次确认 | `ElMessageBox.confirm` | 与同文件 `toolUsageStatusChange` 风格一致 |
| 字段类型 | 字符串 `'1'`/`'0'` | 与后端既有 `hasUse` 等字段类型一致，避免类型转换 |
| 列宽 | 300px | 列标题较长（「跨项目使用该工具版本是否需审核」共 15 字），需较大宽度才能完整显示 |
| 表单校验 | `canCrossProject` 设为 required | 与 `version`、`visitPath` 等字段保持一致的必填校验风格 |

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `apps/web-openlibing/src/views/ToolManagement/config.ts` | 修改 | 两处列配置新增 `canCrossProject` 列；`updateTime` → `createTime`；操作列移除固定宽度 |
| `apps/web-openlibing/src/views/ToolManagement/components/toolTable.vue` | 修改 | 新增 `canCrossProject` 列的 `el-switch` 自定义渲染 |
| `apps/web-openlibing/src/views/ToolManagement/ToolManage/components/toolItem.vue` | 修改 | 新增 `handleToolCanCrossProject` 函数映射 + `toolCanCrossProject` 方法 + `canCrossProject` 校验规则 |
| `apps/web-openlibing/src/views/ToolManagement/MyTool/components/toolItem.vue` | 修改 | 新增 `canCrossProject` 校验规则 |

## 关键代码

### 1. 列配置（config.ts）

```ts
{
  label: '跨项目使用该工具版本是否需审核',
  prop: 'canCrossProject',
  fnName: 'handleToolCanCrossProject',
  width: '300px',
},
```

### 2. el-switch 渲染（toolTable.vue）

```vue
<div v-else-if="column.prop === 'canCrossProject'" class="usage-status">
  <el-switch
    v-model="row[column.prop]"
    inline-prompt
    active-text="需审核"
    inactive-text="不审核"
    active-value="1"
    inactive-value="0"
    style="--el-switch-on-color: #13ce66; --el-switch-off-color: #b5b7bb;"
    :before-change="
      () => {
        return beforeSwitchChange(column, row);
      }
    "
  />
</div>
```

### 3. 切换处理逻辑（toolItem.vue）

```js
const toolCanCrossProject = (row) => {
  const { canCrossProject, version, id } = row;
  const tip = canCrossProject === '0' ? '需审核' : '不审核';
  ElMessageBox.confirm(`是否确定版本${version}跨项目使用时${tip}？`, '提示', {
    confirmButtonText: '确定',
    cancelButtonText: '取消',
    type: 'warning',
  })
    .then(() => {
      updateToolManageItemVisitPath({
        data: {
          id,
          canCrossProject: canCrossProject === '0' ? '1' : '0',
        },
      }).then((res) => {
        if (res.code === 200) {
          ElMessage({ type: 'success', message: res.msg });
          versionSearch();
        }
      });
    })
    .catch(() => {
      ElMessage({ type: 'info', message: '已取消' });
    });
};
```

### 4. 表单校验规则

```js
canCrossProject: [{ required: true, message: '请选择', trigger: 'change' }],
```

## 风险 & 缓解

- **风险**：`before-change` 返回 false 时开关状态不更新，但 `v-model` 已经绑定了 `row` 的字段，需确认 Element Plus 内部是否回滚。
  **缓解**：`before-change` 返回 Promise reject 时 Element Plus 会自动回滚开关状态，无需手动处理；取消二次确认时弹窗 `.catch()` 提示「已取消」即可。
- **风险**：接口更新成功但 `versionSearch()` 刷新失败时，开关状态与后端不一致。
  **缓解**：`versionSearch()` 是既有刷新方法，稳定性已验证；失败时用户可手动刷新页面。
- **风险**：列宽 300px 在小屏幕下可能挤压其他列。
  **缓解**：表格已有横向滚动机制，列宽超出时自动滚动，不影响其他列可见性。

## 跨仓影响

- 后端：需提供 `canCrossProject` 字段返回与更新接口支持（如尚未提供）
- 无前端跨仓影响
