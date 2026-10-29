# SCA 遗留 Vue2 单文件组件迁移至 `<script setup>`

- 分支：`jzcfork/202610setup`
- 核心提交：`d09b04fe`（27 文件迁移）、`1801cedd`（`Empty.vue` 回退 Options API）

## Why

1. `src/sca` 下仍存在大量 Vue2 时期遗留的 Options API 单文件组件（部分通过 Vue2 兼容构建运行），与仓库主流写法（`<script setup lang="ts">` + Composition API）不一致，维护成本高、类型推导弱。
2. Options API 的 `this` 上下文在混用 `setup` 的组件中容易产生歧义，`defineProps`/`defineEmits` 无法被编译器静态优化。
3. 迁移后组件可被 Vite 做更好的 tree-shaking 与编译期优化，同时消除 Vue2 兼容层的隐性依赖。

## What Changes

1. **批量迁移 27 个 `src/sca` 下的 Vue2 Options API 组件为 `<script setup>`**，覆盖四层：

   | 层       | 组件                                                                                                                                                                                                       |
   | -------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
   | 业务页   | `codeTree/index.vue`、`codeTree/ztreeCompent.vue`、`batchUpdate/index.vue`、`combinationCondition/index.vue`                                                                                               |
   | 业务组件 | `PrRepoSelect/index.vue`、`RepoSelect/index.vue`、`communityRepoSelect/index.vue`、`tabs/index.vue`                                                                                                        |
   | 通用组件 | `BaseComponents/Pagination/index.vue`、`Pagination/index.vue`、`DeleteMessage.vue`、`Hamburger/index.vue`、`SvgIcon/index.vue`、`TextTooltip/index.vue`、`wangEditor/index.vue`、`ReturnIcon`、`TitleIcon` |
   | 布局     | `layout/index.vue`、`layout/components/AppMain.vue`、`Navbar.vue`、`Sidebar/{index,Item,Link,Logo,SidebarItem}.vue`、`TagsView/index.vue`                                                                  |

2. **`Empty.vue` 有意保持 Options API**（`1801cedd` 回退）：该组件在迁移后行为异常，经确认回退为 Options API 并加注释说明"该组件有意保持未迁移"，避免后续被重复"修正"。

3. 迁移过程中保持组件的对外契约不变：`props` 名称/默认值、`emits` 事件名与载荷、`expose` 的方法、`name`（通过 `defineOptions`）均与原实现对齐。

## Capabilities

### New

- `src/sca` 组件统一为 `<script setup>` 写法，具备编译期 props/emits 推导。

### Modified

- 27 个 SFC 的内部实现（Options -> Composition），对外接口不变。
- `src/sca` 目录整体的代码风格与仓库主流一致。

### Removed

- Vue2 Options API 写法（`data`/`computed`/`methods`/`mounted`/`watch` 对象式声明）在 `src/sca` 的大面积残留。

## Impact

### 受影响代码

> 下表路径省略统一前缀 `apps/web-openlibing/`。

| 文件                                                         | 行数变化（约） | 说明               |
| ------------------------------------------------------------ | -------------- | ------------------ |
| `src/sca/src/codeTree/index.vue`                             | 31             | 代码树容器         |
| `src/sca/src/codeTree/ztreeCompent.vue`                      | 193            | ztree 封装         |
| `src/sca/src/components/BaseComponents/Pagination/index.vue` | 143            | 分页组件（基础层） |
| `src/sca/src/components/PrRepoSelect/index.vue`              | 452            | PR 仓库选择        |
| `src/sca/src/components/RepoSelect/index.vue`                | 449            | 仓库选择           |
| `src/sca/src/components/batchUpdate/index.vue`               | 406            | 批量更新           |
| `src/sca/src/components/combinationCondition/index.vue`      | 718            | 组合条件           |
| `src/sca/src/components/communityRepoSelect/index.vue`       | 370            | 社区仓库选择       |
| `src/sca/src/components/tabs/index.vue`                      | 86             | 页签               |
| `src/sca/src/components/DeleteMessage.vue`                   | 40             | 删除确认           |
| `src/sca/src/components/Empty.vue`                           | 33             | 空态（迁移后回退） |
| `src/sca/src/components/Hamburger/index.vue`                 | 37             | 折叠按钮           |
| `src/sca/src/components/Pagination/index.vue`                | 137            | 分页               |
| `src/sca/src/components/SvgIcon/index.vue`                   | 62             | 图标               |
| `src/sca/src/components/TextTooltip/index.vue`               | 80             | 文本提示           |
| `src/sca/src/components/wangEditor/index.vue`                | 307            | 富文本             |
| `src/sca/src/layout/components/AppMain.vue`                  | 7              | 内容区             |
| `src/sca/src/layout/components/Navbar.vue`                   | 38             | 顶栏               |
| `src/sca/src/layout/components/Sidebar/Item.vue`             | 42             | 菜单项             |
| `src/sca/src/layout/components/Sidebar/Link.vue`             | 45             | 菜单链接           |
| `src/sca/src/layout/components/Sidebar/Logo.vue`             | 29             | Logo               |
| `src/sca/src/layout/components/Sidebar/SidebarItem.vue`      | 132            | 菜单项递归         |
| `src/sca/src/layout/components/Sidebar/index.vue`            | 56             | 侧栏               |
| `src/sca/src/layout/components/TagsView/index.vue`           | 340            | 多页签             |
| `src/sca/src/layout/index.vue`                               | 66             | 布局容器           |
| `src/sca/src/components/ReturnIcon`                          | 6              | 返回图标           |
| `src/sca/src/components/TitleIcon`                           | 6              | 标题图标           |

汇总：27 文件，+2224 / -2087。

### 明确不受影响

- 组件对外 props / emits / expose 契约。
- `src/sca` 之外的业务模块。
- 构建配置（未新增依赖）。

### 风险

- **隐式 `this` 依赖遗漏**：Options API 中 `this.$refs`、`this.$parent`、`this.$router` 等迁移后需显式改用 `ref`/`useRouter`，易漏改导致运行时 `undefined`。
- **`mounted`/`watch` 时序差异**：`<script setup>` 中 `onMounted` 与 `watch` 的注册顺序影响首次执行时机，`immediate` 选项需逐处核对。
- **`this.$emit` 与 `defineEmits` 载荷不一致**：事件名大小写、参数个数需对齐。
- **`name` 丢失**：使用 `keep-alive` 或按 `name` 查找组件的场景必须补 `defineOptions({ name })`。
- **`Empty.vue` 特殊处理**：迁移后行为异常，已回退为 Options API，需在代码中注释保留原因，禁止后续无脑迁移。

## 验证清单

| 场景                                                        | 期望                           |
| ----------------------------------------------------------- | ------------------------------ |
| 代码树展开/选中/搜索                                        | 与原行为一致                   |
| 仓库选择（PrRepoSelect / RepoSelect / communityRepoSelect） | 远程搜索、分页、选中回填一致   |
| 批量更新、组合条件                                          | 表单联动、提交载荷一致         |
| 分页组件（两处）                                            | 页码/页大小变更事件一致        |
| 富文本 wangEditor                                           | 初始化、取值、高度正常         |
| 布局（Navbar/Sidebar/TagsView）                             | 菜单渲染、页签关闭、折叠正常   |
| `Empty.vue`                                                 | 保持 Options API，空态展示正常 |
