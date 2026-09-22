# Design: 流水线历史记录表格新增 Merge ID 列

## 技术方案

### 变更文件

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `src/views/pipeline/PipelineDetail/History.vue` | 修改 | 新增 Merge ID 列定义、筛选、跳转逻辑和样式 |

仅涉及单文件前端变更，无新增文件、无接口变更、无数据模型变更。

### 实现细节

#### 1. 列定义

在 `tableColumns` 数组中新增 Merge ID 列配置：

```js
{
  label: 'Merge ID',
  prop: 'mergeId',
  width: 120,
}
```

插入位置：执行信息列之后、状态列之前。

#### 2. 列头筛选

- 新增 `searchMergeIdValue` 响应式变量（`ref('')`）
- 列头使用 `TableHeaderFilter` 组件，`filter-type="text"`，支持文本输入筛选
- 筛选回调 `onMergeIdHeaderFilter` 触发表格重新查询

#### 3. 筛选参数传递

在 `getPipelineRunHistory` 的请求参数中，使用展开运算符条件传递 `mergeId`：

```js
...(searchMergeIdValue.value ? { mergeId: searchMergeIdValue.value } : {})
```

当筛选值为空字符串时，不传递 `mergeId` 参数，避免后端误将空字符串作为过滤条件。

#### 4. 列内容渲染

- 有值时渲染可点击链接 `<a class="merge-id-link">`，显示 `#<merge_id>`
- 无值时渲染 `--` 占位符

#### 5. 跳转逻辑

新增 `goToMergeRequest` 方法：

```js
const goToMergeRequest = (row) => {
  const gitUrl = row?.build_params?.git_url;
  const mergeId = row?.build_params?.merge_id;
  if (!gitUrl || !mergeId) return;
  const baseUrl = gitUrl.replace(/\.git$/, '');
  goToNotice(`${baseUrl}/pull/${mergeId}`);
};
```

通过 `build_params.git_url` 去除 `.git` 后缀拼接 `/pull/<mergeId>` 路径，使用已有的 `goToNotice` 工具函数在新窗口打开。

#### 6. 样式

新增 `.merge-id-link` 样式类，与现有 `.show-param` 链接样式保持一致（`color: #526ecc; cursor: pointer;`）。

### 数据流

```
用户输入筛选值 → searchMergeIdValue 更新
  → onMergeIdHeaderFilter → searchTable → getPipelineRunHistory
  → API 请求携带 mergeId 参数 → 返回过滤后的列表数据
```

```
用户点击 Merge ID 链接 → goToMergeRequest(row)
  → 从 build_params 提取 git_url + merge_id
  → 拼接 MR URL → goToNotice 打开新窗口
```

### 无变更项

- 后端 API：无需变更，`mergeId` 查询参数由现有接口已支持
- 路由/权限：无变更
- 数据模型/类型：无新增
- 依赖：无新增外部依赖
