# Tasks: 流水线历史记录表格新增 Merge ID 列

## 实现步骤

- [x] 1. 在 `tableColumns` 中新增 Merge ID 列配置（label / prop / width）
- [x] 2. 新增 `searchMergeIdValue` 响应式变量和 `onMergeIdHeaderFilter` 回调
- [x] 3. 列头使用 `TableHeaderFilter` 组件实现文本筛选
- [x] 4. 在 API 请求参数中条件传递 `mergeId`，空值时不传递
- [x] 5. 新增 `goToMergeRequest` 方法，从 `build_params` 拼接 MR URL 并跳转
- [x] 6. 列内容渲染：有值显示 `#<id>` 可点击链接，无值显示 `--`
- [x] 7. 新增 `.merge-id-link` 样式
- [x] 8. 引入 `goToNotice` 工具函数

## 验证步骤

- [ ] 历史记录页面表格展示 Merge ID 列
- [ ] 有 Merge ID 的记录显示 `#<id>` 链接样式，点击可跳转至 MR 页面
- [ ] 无 Merge ID 的记录显示 `--`
- [ ] 列头筛选框输入值后表格正确过滤
- [ ] 清空筛选框后表格恢复全量查询
- [ ] 不影响其他列的筛选和排序功能

## Commit 记录

| Commit | 说明 |
|--------|------|
| `5ac25d6` | feat(pipeline): add Merge ID column with text filter in history table |
| `5286cc7` | fix(pipeline): omit mergeId param from API request when filter is empty |
| `431c81b` | feat(pipeline): add click-to-navigate for Merge ID column |
| `39b733e` | feat(pipeline): prefix Merge ID display with hash symbol |
