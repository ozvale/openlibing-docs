# 设计：SCA 遗留 Vue2 SFC 迁移至 `<script setup>`

## Context

`apps/web-openlibing/src/sca` 是从旧版 SCA 系统整体搬迁进来的子应用，组件普遍保留了 Vue2 时期写法：`export default { data(), computed: {}, methods: {}, mounted() {}, watch: {} }`，并通过 `src/sca/src/main.js` 一类的兼容入口挂载。仓库其他模块已统一使用 `<script setup lang="ts">` + Composition API。

迁移目标不是"改功能"，而是"改实现风格且行为等价"。因此风险控制的核心是**对外契约零变化**。

## Goals / Non-Goals

### Goals

1. 27 个 `src/sca` 组件迁移为 `<script setup>`。
2. 对外契约完全不变：`props`（名称/类型/默认值）、`emits`（事件名与载荷）、`expose` 方法、组件 `name`。
3. 迁移后 `src/sca` 与其他模块风格一致，可通过统一 lint 规则。

### Non-Goals

- 不重构组件内部业务逻辑、不拆分组件、不改样式。
- 不升级 `src/sca` 的构建入口或路由体系。
- 不为迁移引入新依赖（如 `@vue/composition-api`）。
- 不迁移 `Empty.vue`（见 D4）。

## Decisions

### D1：按"基础组件 -> 业务组件 -> 页面 -> 布局"自底向上迁移

依赖方向决定迁移顺序：

```
BaseComponents/{Pagination, ReturnIcon, TitleIcon, tabs}
  -> {RepoSelect, PrRepoSelect, communityRepoSelect, batchUpdate, combinationCondition}
  -> codeTree/{ztreeCompent, index}
  -> components/{Pagination, SvgIcon, Hamburger, TextTooltip, wangEditor, DeleteMessage}
  -> layout/{AppMain, Navbar, Sidebar/*, TagsView, index}
```

先迁被依赖方，可让上层组件在迁移时直接使用新写法，避免出现"新旧混用"的中间态长期存在。

### D2：`props`/`emits` 用编译宏显式声明

```vue
<script setup>
const props = defineProps({
  picture: { type: String, default: emptyPic },
  descriptContent: { type: String, default: "暂无相关内容！" },
});
const emit = defineEmits(["change", "update:modelValue"]);
</script>
```

对齐原则：

| Options API                    | `<script setup>`                               |
| ------------------------------ | ---------------------------------------------- |
| `props: {...}`                 | `defineProps({...})`（保持同样的类型与默认值） |
| `this.$emit('x', payload)`     | `emit('x', payload)`                           |
| `this.$refs.y`                 | `const y = ref()` + 模板 `ref="y"`             |
| `this.$router` / `this.$route` | `useRouter()` / `useRoute()`                   |
| `data()`                       | `ref()` / `reactive()`                         |
| `computed: {}`                 | `computed()`                                   |
| `mounted()`                    | `onMounted()`                                  |
| `watch: {}`                    | `watch()` / `watchEffect()`                    |
| `name: 'X'`                    | `defineOptions({ name: 'X' })`                 |

### D3：`name` 必须保留

`TagsView`、`keep-alive`、以及部分按组件名查找的逻辑依赖 `name`。迁移时统一补 `defineOptions({ name })`，不依赖文件名推断。

### D4：`Empty.vue` 有意保留 Options API

`Empty.vue` 迁移为 `<script setup>` 后出现行为异常（空态图片/描述渲染不符合预期）。评估结论是：该组件体量小（33 行）、复用点少、迁移收益低于排查成本，故回退为 Options API，并在代码中保留注释说明"该组件有意保持未迁移"，防止后续被重复"修正"。

```js
export default {
  name: "Empty",
  components: {},
  props: {
    picture: { type: String, default: emptyPic },
    descriptContent: { type: String, default: "暂无相关内容！" },
  },
  data() {
    return {};
  },
  computed: {},
  mounted() {},
  methods: {},
};
```

### D5：迁移不改变模板结构

模板部分仅做必要调整（`ref` 绑定、事件名、`v-model` 拆分），不改 DOM 结构与 class。这样样式与既有快照/视觉基线保持稳定，回归范围可控。

## 迁移矩阵（关键组件）

| 组件                                                  | 关键迁移点                                                                               |
| ----------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| `ztreeCompent.vue`                                    | ztree 实例挂载于 `onMounted`，销毁于 `onBeforeUnmount`；`this.$refs.tree` 改为模板 `ref` |
| `PrRepoSelect` / `RepoSelect` / `communityRepoSelect` | 远程搜索、分页、`v-model` 回填；`props` 中的 `value` 语义需与 `modelValue` 对齐          |
| `combinationCondition`                                | 多层条件数组的响应式（`reactive` 深层更新）；`watch` 深度与 `immediate` 对齐             |
| `batchUpdate`                                         | 表单校验（`ref.validate()`）与提交事件载荷                                               |
| `Pagination`（两处）                                  | `current-change` / `size-change` 事件名与参数                                            |
| `wangEditor`                                          | 编辑器实例生命周期，`onMounted` 后初始化，`onBeforeUnmount` 销毁                         |
| `TagsView`                                            | 依赖组件 `name`；路由监听改 `watch(() => route.fullPath)`                                |
| `Sidebar/SidebarItem`                                 | 递归组件需 `defineOptions({ name })` 才能自引用                                          |

## 涉及文件

> 路径统一前缀 `apps/web-openlibing/`。

| 文件                                                                   | 操作         | 说明                     |
| ---------------------------------------------------------------------- | ------------ | ------------------------ |
| `src/sca/src/codeTree/index.vue`                                       | 修改         | 代码树容器               |
| `src/sca/src/codeTree/ztreeCompent.vue`                                | 修改         | ztree 封装               |
| `src/sca/src/components/BaseComponents/Pagination/index.vue`           | 修改         | 基础分页                 |
| `src/sca/src/components/BaseComponents/PrRepoSelect/index.vue`         | 修改         | PR 仓库选择              |
| `src/sca/src/components/BaseComponents/RepoSelect/index.vue`           | 修改         | 仓库选择                 |
| `src/sca/src/components/BaseComponents/ReturnIcon/index.vue`           | 修改         | 返回图标                 |
| `src/sca/src/components/BaseComponents/TitleIcon/index.vue`            | 修改         | 标题图标                 |
| `src/sca/src/components/BaseComponents/batchUpdate/index.vue`          | 修改         | 批量更新                 |
| `src/sca/src/components/BaseComponents/combinationCondition/index.vue` | 修改         | 组合条件                 |
| `src/sca/src/components/BaseComponents/communityRepoSelect/index.vue`  | 修改         | 社区仓库选择             |
| `src/sca/src/components/BaseComponents/tabs/index.vue`                 | 修改         | 页签                     |
| `src/sca/src/components/DeleteMessage.vue`                             | 修改         | 删除确认                 |
| `src/sca/src/components/Empty.vue`                                     | 修改（回退） | 迁移后回退为 Options API |
| `src/sca/src/components/Hamburger/index.vue`                           | 修改         | 折叠按钮                 |
| `src/sca/src/components/Pagination/index.vue`                          | 修改         | 分页                     |
| `src/sca/src/components/SvgIcon/index.vue`                             | 修改         | 图标                     |
| `src/sca/src/components/TextTooltip/index.vue`                         | 修改         | 文本提示                 |
| `src/sca/src/components/wangEditor/index.vue`                          | 修改         | 富文本                   |
| `src/sca/src/layout/components/AppMain.vue`                            | 修改         | 内容区                   |
| `src/sca/src/layout/components/Navbar.vue`                             | 修改         | 顶栏                     |
| `src/sca/src/layout/components/Sidebar/Item.vue`                       | 修改         | 菜单项                   |
| `src/sca/src/layout/components/Sidebar/Link.vue`                       | 修改         | 菜单链接                 |
| `src/sca/src/layout/components/Sidebar/Logo.vue`                       | 修改         | Logo                     |
| `src/sca/src/layout/components/Sidebar/SidebarItem.vue`                | 修改         | 菜单项递归               |
| `src/sca/src/layout/components/Sidebar/index.vue`                      | 修改         | 侧栏                     |
| `src/sca/src/layout/components/TagsView/index.vue`                     | 修改         | 多页签                   |
| `src/sca/src/layout/index.vue`                                         | 修改         | 布局容器                 |

## 风险与兼容性

| 风险                                                              | 影响 | 应对                                                   |
| ----------------------------------------------------------------- | ---- | ------------------------------------------------------ |
| 隐式 `this` 依赖（`$refs`/`$parent`/`$router`）漏改               | 高   | 以 `this.` 全局搜索为迁移完成判据；逐组件冒烟          |
| `mounted` 与 `onMounted` 时序差异导致 ztree/wangEditor 初始化失败 | 高   | 依赖 DOM 的初始化统一放 `onMounted`，必要时 `nextTick` |
| `watch` 的 `immediate`/`deep` 语义遗漏                            | 中   | 逐处对照原 `watch` 选项                                |
| `emits` 载荷不一致（参数个数/名称）                               | 中   | 对照原 `this.$emit` 调用点                             |
| 组件 `name` 丢失导致 `keep-alive` / 递归组件失效                  | 中   | 统一 `defineOptions({ name })`                         |
| `Empty.vue` 被后续误迁移                                          | 低   | 代码内注释 + 本文档记录                                |
| 大文件（718 行 `combinationCondition`）迁移引入细微行为差异       | 中   | 优先做"逐行等价翻译"，不顺手优化                       |

## 验证策略

1. **静态检查**：`src/sca` 下 `this.` 引用清零（除 `Empty.vue`）；ESLint（`vue/script-setup` 相关规则）通过。
2. **构建**：`pnpm build` 通过，无未解析导入。
3. **功能回归**（按组件分层）：
   - 分页组件：页码切换、每页条数切换事件参数。
   - 仓库选择三件套：远程搜索、分页加载、选中回填、清空。
   - 组合条件：条件增删、嵌套、提交载荷。
   - 批量更新：表单校验、提交。
   - 代码树：展开、选中、搜索、ztree 实例销毁无泄漏。
   - 富文本：初始化、取值、只读态、销毁。
   - 布局：菜单渲染、折叠、页签切换/关闭、面包屑。
4. **空态**：`Empty.vue` 默认图与自定义描述均正常。
5. **内存**：反复进出含 ztree/wangEditor 的页面，确认无重复实例堆积。
