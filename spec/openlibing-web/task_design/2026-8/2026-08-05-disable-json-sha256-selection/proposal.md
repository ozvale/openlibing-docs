## Why

OBS 桶对象详情页 `obsDetails.vue` 在发布评审嵌入模式下，允许用户勾选桶内文件作为发布产物路径。当前 `selectable` 仅排除文件夹（`row.type !== 'folder'`），导致 `.json`（元数据/配置文件）和 `.sha256`（校验和文件）这类**非真正的发布产物文件**也能被勾选并回传给父组件。这些文件是发布过程的**伴生校验/描述文件**，不应作为可发布的软件产物路径被选中，需要从可选集合中排除，避免用户误选导致发布评审数据污染。

## What Changes

- 扩展 `obsDetails.vue` 的 `selectable` 函数判定规则：在原有「排除文件夹」基础上，**增加排除扩展名为 `json`、`sha256`、`sha256sum` 和 `sum` 的文件行**（后三者为校验和文件的常见扩展名及别名）。
- 判定基于文件扩展名（`row.type`），**大小写不敏感**：`JSON`、`Json`、`SHA256`、`Sha256` 等大小写变体均应被识别为不可选，兼容不同命名习惯的桶对象。
- 同步更新 `handleSelectionAllChange` 的冗余防御过滤逻辑，保持与 `selectable` 语义一致，确保全选/取消全选时 emit 给父组件的集合不含 `json`/`sha256` 文件。
- **不修改** `getFileExtension` 函数本身：该函数的输出同时被模板里的文件类型图标映射消费（`['log'].includes(row.type)` 等），改动其大小写行为会扩散影响范围，本次只在 `selectable`/`handleSelectionAllChange` 内部做大小写归一化比较。

## Capabilities

### New Capabilities

- `obs-object-selection-filter`: OBS 桶对象表格行可选性过滤规则，定义哪些文件类型可被勾选为发布产物路径。覆盖 `selectable` 单选判定与 `handleSelectionAllChange` 全选过滤两条路径的不可选类型集合。

### Modified Capabilities

无。`openspec/specs/` 当前为空，本 change 为首次引入该 capability。

## Impact

- **受影响代码**：`openlibing-web/apps/web-openlibing/src/views/Publish/obs/obsDetails.vue`（单文件）
  - `selectable` 函数（约第 451-454 行）
  - `handleSelectionAllChange` 函数（约第 462-474 行）
- **受影响组件契约**：父组件通过 `@getSelectedData` 接收的行集合，不再包含 `.json`/`.sha256` 文件。父组件（如 `reviewDetail.vue`）无需改动，因为原本就只消费 `filePath`/`lastModified`/`contentLength`/`obsBucketName` 字段。
- **不受影响**：
  - `getFileExtension` 函数（保持原大小写行为，避免影响图标渲染）
  - 文件图标映射（模板 `v-if` 链）
  - 下载逻辑、分页逻辑、路径导航逻辑
  - 后端 API 契约（纯前端过滤）
- **风险**：若未来有场景需要选择 `.json`/`.sha256` 作为产物（极不可能），需放宽规则。当前规则对发布评审场景安全。