## Context

`obsDetails.vue` 在发布评审嵌入模式下，el-table 的 `selectable` 属性控制哪些行可勾选。原实现仅排除 `folder` 类型，导致 `.json`/`.sha256` 等伴生文件也可被选中并回传父组件，污染发布评审数据。

## Goals / Non-goals

**Goals**

- 在 `selectable` 与 `handleSelectionAllChange` 两条路径上统一过滤规则，排除非产物文件类型。
- 大小写不敏感，兼容不同命名习惯的桶对象。
- 保持改动局部，不扩散到 `getFileExtension` 等图标渲染链路。

**Non-goals**

- 不重构 `getFileExtension` 函数。
- 不调整 el-table 的事件订阅方式或父组件契约。
- 不引入新依赖。

## Design

### 核心方案：抽取 `isSelectableRow` 公共判定函数

将"行是否可选"的判定逻辑从 `selectable` 与 `handleSelectionAllChange` 各自重复实现，收敛为单一函数 `isSelectableRow(row)`，两条路径共同复用，确保语义一致。

```
┌─────────────────────────────────────────────┐
│  isSelectableRow(row)                        │
│    1. row.type === 'folder' → false          │
│    2. UNSELECTABLE_EXTENSIONS.includes(      │
│         String(row.type).toLowerCase()       │
│       ) → false                              │
│    3. 否则 → true                            │
└─────────────────────────────────────────────┘
        ↑                       ↑
        │                       │
  selectable(row)     handleSelectionAllChange(val)
  (el-table 单选)     (el-table 全选)
```

### 不可选扩展名集合

定义常量 `UNSELECTABLE_EXTENSIONS = ['json', 'sha256', 'sha256sum', 'sum']`：

- `json`：桶对象的元数据/配置文件。
- `sha256` / `sha256sum` / `sum`：校验和文件常见扩展名及别名。

### 大小写归一化

仅在 `isSelectableRow` 内部对 `row.type` 做 `String(...).toLowerCase()`，**不修改 `getFileExtension`**。理由：

- `getFileExtension` 的输出同时被模板 `v-if` 链消费（如 `['log'].includes(row.type)`），改其大小写行为会扩散到图标渲染。
- 本次改动只关心"是否可选"，归一化限定在判定函数内部，影响半径最小。

## Alternatives

| 方案                            | 优点                         | 缺点                                   | 采纳 |
| ------------------------------- | ---------------------------- | -------------------------------------- | ---- |
| 抽取 `isSelectableRow` 公共函数 | 单一真相源，两条路径天然一致 | 多一个函数                             | ✅   |
| 各自内联判定                    | 改动最小                     | 逻辑重复，易漂移                       | ❌   |
| 改 `getFileExtension` 统一小写  | 全局一致                     | 影响图标渲染链路                       | ❌   |
| 后端过滤                        | 前端零改动                   | 增加后端契约改动，违反"纯前端过滤"目标 | ❌   |

## Risks

- 若未来需选择 `.json`/`.sha256` 作为产物（极不可能），需放宽 `UNSELECTABLE_EXTENSIONS`。当前规则对发布评审场景安全。
- `row.type` 可能为 `undefined`/`null`（理论上不应该），`String(...)` 兜底为 `"undefined"`/`"null"`，不会误匹配。
