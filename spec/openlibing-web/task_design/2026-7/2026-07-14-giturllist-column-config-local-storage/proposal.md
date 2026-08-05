## Why

SCA 软件信息页（`gitUrlList.vue`）的表头列配置此前使用 `sessionStorage` 持久化用户勾选的列 `id` 列表。`sessionStorage` 的生命周期仅限于浏览器标签页会话，用户关闭标签页或重启浏览器后缓存即丢失，导致列配置偏好无法跨会话保留，每次重新打开页面都需重新设置列显隐，影响使用体验。

为统一与 `branches.vue`、`TableSetting`、`mytable-column-setting` 等项目内其他列配置实现的持久化策略，需要将 `clunmLists` 的存储由 `sessionStorage` 改为 `localStorage`，使列配置偏好能跨标签页会话保留。

## What Changes

- `updateSelectList()`：将 `sessionStorage.getItem('clunmLists')` 改为 `localStorage.getItem('clunmLists')`，读取逻辑保持不变（split 为数组、空值降级为 `[]`）
- `updateShowCulomList()`：将 `sessionStorage.setItem('clunmLists', columnList)` 改为 `localStorage.setItem('clunmLists', columnList)`
- 相关注释由「判断 sessionStorage 是否有缓存数据」同步更新为「判断 localStorage 是否有缓存数据」
- 持久化 key（`clunmLists`）与值格式（`id` 数组逗号分隔字符串）保持不变，不做迁移
- 列配置 Popover UI、`min=5`、`disabled` 列规则、全选/半选交互逻辑均保持不变

## Capabilities

### New Capabilities

- `sca-giturllist-column-config-persistence`: SCA 软件信息页表头列配置的跨会话持久化能力，基于 `localStorage` 存储 `clunmLists` 键

### Modified Capabilities

（无现有 openspec spec 需修改。本次仅替换底层 Web Storage API，不改变更契约行为本身。）

## Impact

- **前端文件**
  - `apps/web-openlibing/src/views/sca/softInformation/gitUrlList.vue` — `updateSelectList()` 与 `updateShowCulomList()` 两个方法的存储 API 调用替换，及注释文案更新
- **后端 / API** — 无变更
- **持久化数据**
  - 存储位置：`sessionStorage` → `localStorage`
  - key：`clunmLists`（不变）
  - value 格式：逗号分隔字符串（不变）
  - 旧 `sessionStorage.clunmLists` 不做主动迁移；用户再次配置后自然写入 `localStorage`
- **用户体验**
  - 关闭标签页/重启浏览器后，列配置偏好得以保留
  - 同一浏览器不同标签页打开页面时，将共享同一份列配置（与 `sessionStorage` 每标签页独立不同）
- **不修改**
  - 列定义（`table.column`）、`selectList` 计算属性、`checkedList`、`checkAll`、`isIndeterminate` 等响应式状态
  - Popover 模板结构、`:min="5"`、`disabled` 列规则
  - `handleCheckedTabelChange`、`handleCheckAllChange`、`cancelUpdateTabelHeader` 方法
  - `created` 钩子中 `updateSelectList()` 的调用时机
