## Tasks

### 1. 定义不可选扩展名集合

- [x] 1.1 在 `obsDetails.vue` 顶层定义常量 `UNSELECTABLE_EXTENSIONS = ['json', 'sha256', 'sha256sum', 'sum']`

### 2. 抽取公共判定函数

- [x] 2.1 新增 `isSelectableRow(row)`：先排除 `folder`，再用 `UNSELECTABLE_EXTENSIONS.includes(String(row.type).toLowerCase())` 判定
- [x] 2.2 `selectable` 改为 `(row) => isSelectableRow(row)`

### 3. 同步全选路径

- [x] 3.1 `handleSelectionAllChange` 内 `forEach` 改用 `isSelectableRow(item)` 过滤，确保 emit 集合不含 `json`/`sha256`
- [x] 3.2 验证取消全选时 `val.length !== 0` 仍能正确 emit 空集合

### 4. 验证

- [x] 4.1 大小写变体 `JSON`/`Json`/`SHA256`/`Sha256` 均不可选
- [x] 4.2 单选、全选、取消全选三条路径行为一致
- [x] 4.3 `getFileExtension` 与文件图标渲染未受影响
