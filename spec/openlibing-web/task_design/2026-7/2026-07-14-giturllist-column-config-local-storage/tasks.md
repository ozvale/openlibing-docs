## 1. 持久化存储 API 替换

- [x] 1.1 在 `gitUrlList.vue` 的 `updateSelectList()` 方法中，将 `sessionStorage.getItem('clunmLists')`（两处）替换为 `localStorage.getItem('clunmLists')`
- [x] 1.2 在 `gitUrlList.vue` 的 `updateShowCulomList()` 方法中，将 `sessionStorage.setItem('clunmLists', columnList)` 替换为 `localStorage.setItem('clunmLists', columnList)`

## 2. 注释同步

- [x] 2.1 将 `updateSelectList()` 中的注释 `// 判断sessionStorage是否有缓存数据` 更新为 `// 判断localStorage是否有缓存数据`

## 3. 手动验收

- [ ] 3.1 首次访问（无 `localStorage.clunmLists`）：表格按各列 `show` 默认值渲染，`checkedList` 含所有 `show: true` 列
- [ ] 3.2 修改列配置并点击「确认」：`localStorage.clunmLists` 写入逗号分隔字符串，Popover 关闭，表格列显隐更新
- [ ] 3.3 修改列配置后点击「取消」：`localStorage.clunmLists` 不变，表格列显隐保持原状
- [ ] 3.4 关闭浏览器标签页后重新打开页面：列配置偏好从 `localStorage` 恢复
- [ ] 3.5 关闭浏览器并重新打开：列配置偏好仍从 `localStorage` 恢复
- [ ] 3.6 固定列（`disabled: true`）在 Popover 中仍为 disabled 且不可取消
- [ ] 3.7 `:min="5"` 约束生效：勾选数到 5 时无法继续取消
- [ ] 3.8 全选/取消全选：`checkAll` 与 `isIndeterminate` 状态正确同步，disabled 列始终保留在 `checkedList`
- [ ] 3.9 Popover `@show` 触发 `updateSelectList()` 时，从 `localStorage` 读取最新值并初始化 `checkedList`
