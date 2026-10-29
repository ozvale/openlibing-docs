## Context

`gitUrlList.vue` 是 SCA 模块「软件信息」页主组件，渲染扫描结果表格并提供「列配置」Popover（`tebelHeaderSelectVisible`），允许用户勾选需要展示的列。组件采用 Options API 实现，列配置相关状态与方法包括：

- `table.column`：列定义数组，每项含 `id`（字符串标识）、`label`、`show`（布尔显隐）、`disabled`（是否固定不可取消）
- `selectList`：计算属性，返回 `table.column` 的浅拷贝，供 Popover 渲染
- `checkedList`：当前 Popover 中勾选的列 `id` 数组
- `checkAll` / `isIndeterminate`：全选 checkbox 状态
- `updateSelectList()`：读取缓存 → 初始化 `checkedList` 与各列 `show`
- `updateShowCulomList()`：根据 `checkedList` 应用变更 → 写入缓存 → 关闭 Popover
- `cancelUpdateTabelHeader()`：放弃修改 → 关闭 Popover
- `handleCheckedTabelChange()`：勾选变化时同步全选状态
- `handleCheckAllChange()`：全选/取消全选

原实现使用 `sessionStorage` 读写 `clunmLists` 键，导致跨会话偏好丢失。项目内其他列配置实现（`branches.vue`、`mytable-column-setting`）已统一使用 `localStorage`，本次对齐。

**已确认产品约束：**

1. 仅修改存储 API（`sessionStorage` → `localStorage`），不重构列配置逻辑
2. 持久化 key `clunmLists` 保持不变
3. value 格式保持不变（`id` 数组 `.toString()` 形成的逗号分隔字符串）
4. 不做旧 `sessionStorage` 数据迁移
5. Popover UI、`:min="5"`、`disabled` 列规则保持不变

## Goals / Non-Goals

**Goals:**

- 将 `clunmLists` 持久化由 `sessionStorage` 改为 `localStorage`，实现跨浏览器会话保留用户列配置偏好
- 保持读取、解析、写入逻辑不变，仅替换底层 Web Storage API
- 更新相关注释文案以反映存储位置变更

**Non-Goals:**

- 不引入 `userId` 维度的 key 隔离（与 `mytable-column-setting` 不同，本次不扩展为多用户场景）
- 不替换为 `mytable-column-setting` 的 composable 方案（不在本次范围）
- 不修改 `table.column` 列定义结构
- 不修改 Popover UI 与交互
- 不做旧 `sessionStorage.clunmLists` → `localStorage` 的数据迁移
- 不修改 `disabled` 列规则与 `:min="5"` 约束

## Decisions

### D1：仅替换存储 API，不重构列配置实现

**选择：** 将 `sessionStorage.getItem` / `sessionStorage.setItem` 替换为 `localStorage.getItem` / `localStorage.setItem`，其余逻辑保持原样。

**理由：** 本次提交是 bugfix 性质，目的是修正「关闭标签页缓存丢失」的体验问题，不应耦合架构重构。现有 `updateSelectList` / `updateShowCulomList` 逻辑可读且工作正常。

**备选：** 迁移到 `useTableColumnSetting` composable — rejected，超出本次修复范围，且 `gitUrlList.vue` 是 Options API，混用 Composable 会引入额外复杂度。

### D2：保持 key `clunmLists` 不变

**选择：** `localStorage` 中的 key 仍为 `clunmLists`，不重命名为 `columnList` 或加前缀。

**理由：** 与原 `sessionStorage` 保持一致的命名，便于代码 review 与历史追溯；key 不存在命名冲突。

**备选：** 重命名为 `scaGitUrlListColumns` — rejected，无收益且引入额外迁移成本。

### D3：保持 value 格式不变

**选择：** value 为 `id` 数组的逗号分隔字符串（`['fileName', 'compatible'].toString()` → `"fileName,compatible"`），读取时 `split(',')`。

**理由：** 与原 `sessionStorage` 格式一致，无需序列化/反序列化迁移；数组 `.toString()` 隐式调用 `.join(',')`。

**备选：** 改为 JSON 字符串（`JSON.stringify`）— rejected，无功能收益，且原格式工作正常。

### D4：不做旧数据迁移

**选择：** 不在 `created` 钩子中检测 `sessionStorage.clunmLists` 并迁移到 `localStorage`。

**理由：**

1. `sessionStorage` 数据在标签页关闭后已自动清除，迁移窗口极短
2. 用户首次访问时无 `localStorage.clunmLists` → 走默认列配置（全 `show: true`），等价于「新用户首次进入」流程
3. 迁移逻辑会污染本次 bugfix 的 diff，且收益微弱

**备选：** `created` 中 `localStorage.clunmLists = localStorage.clunmLists || sessionStorage.clunmLists` — rejected。

### D5：保留 `:min="5"` 与 `disabled` 列规则

**选择：** 不修改 Popover 模板的 `:min="5"` 与 `:disabled="_list.disabled"`。

**理由：** 这些约束是既有产品决策（保证表格至少显示 5 列、固定列不可取消），与存储 API 变更无关。

### D6：注释同步更新

**选择：** 将 `updateSelectList` 中的 `// 判断sessionStorage是否有缓存数据` 更新为 `// 判断localStorage是否有缓存数据`。

**理由：** 保持注释与代码一致，避免误导后续维护者。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 同一浏览器多标签页共享 `localStorage`，与原 `sessionStorage` 每标签页独立不同 | 可接受：列配置是用户偏好，跨标签页共享符合预期；与 `branches.vue`、`mytable-column-setting` 行为一致 |
| 隐私模式下 `localStorage` 写入可能失败 | 原生 `localStorage.setItem` 在隐私模式下可能抛 `QuotaExceededError`；本次未加 try/catch（与原 `sessionStorage` 实现一致），后续如遇问题可统一补充 |
| 旧 `sessionStorage.clunmLists` 残留数据 | 标签页关闭后自动清除；不影响 `localStorage` 读取（key 相同但存储隔离） |
| value 格式非 JSON，扩展性受限 | 与原实现一致；如未来需存储列顺序或宽度，再统一升级为 JSON |

## Migration Plan

纯前端发布，无数据迁移。部署后：

1. 用户首次访问时 `localStorage.clunmLists` 为 `null` → 走默认列配置
2. 用户确认列配置后写入 `localStorage.clunmLists`
3. 后续访问（含关闭浏览器重启）从 `localStorage` 恢复偏好

**回滚：** 将 `localStorage` 改回 `sessionStorage` 即可；`localStorage.clunmLists` 残留数据不影响 `sessionStorage` 读取。

## Open Questions

（无 — 本次为单文件、双方法的 bugfix，变更范围清晰。）
