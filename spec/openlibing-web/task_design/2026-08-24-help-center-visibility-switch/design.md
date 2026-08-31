# 2026-08-24 帮助中心文档可见性开关 - 技术方案

## 1. 总体设计

在帮助中心文档阅读页标题行右侧增加"管理中心文档"开关，通过权限 + URL 双重条件控制显示；同时在管理中心挂载帮助中心页面的路由复用入口。开关切换直接复用编辑弹窗的保存接口，仅变更 `visibility` 字段。

## 2. 关键实现

### 2.1 开关显示条件（helpCenter.vue）

```js
// 是否有管理中心配置权限
const hasManageConfigPermission = computed(() =>
  Boolean(app?.user?.permissions?.find?.((i) => i === "manage_config")),
);
// 当前 url 是否在管理中心模块下
const isManageCenterRoute = computed(() =>
  route.path.startsWith("/manageCenter"),
);
```

模板：`v-if="hasManageConfigPermission && isManageCenterRoute"`。

权限判断方式与 `layouts/basic.vue` 中既有用法保持一致；路径前缀判断与 `Banner.vue` 一致。

### 2.2 int 型 visibility 绑定

`el-switch` 通过 `active-value={1}` / `inactive-value={0}` 支持 int 绑定。由于 `currentReadInfo.visibility` 可能为 `undefined`（未取到值），不能直接 `v-model` 绑定原始字段，引入可写计算属性做归一化：

```js
const visibilityValue = computed({
  get: () => currentReadInfo.value.visibility ?? 0, // 默认 0
  set: (val) => {
    currentReadInfo.value.visibility = val;
  },
});
```

### 2.3 切换保存（复用编辑确定接口）

`handleVisibilityChange` 调用 `updateHelpCenterFile`，参数为 `{ ...currentReadInfo.value, visibility: val, updateDate }`，与编辑弹窗"确定"调用同一接口，仅 `visibility` 字段变更。成功后刷新文件树与当前文档详情；失败时按 int 取反回滚开关状态（`val === 1 ? 0 : 1`）。

### 2.4 管理中心入口（路由 + 菜单）

- `manageRouter.ts` 新增路由 `helpCenterSetting`（path: `/manageCenter/helpCenterSetting`），component 复用 `HelpCenter/helpCenter.vue`
- `manageCenter/index.vue` 左侧菜单新增 `el-sub-menu`（index=8，标题"帮助中心"），子项 `helpCenterSetting`（"帮助文档"）

组件复用下，`/manageCenter` 路径条件自然满足，开关在管理中心入口进入时可见，普通帮助中心入口不可见。

### 2.5 异步路由跳转守卫

`handleNodeClick` 中 `await getWikiDetail(data)` 完成时用户可能已跳转，此时 `router.push({ query })` 会把 query 挂到其他页面 URL，且 vue-router 4 中新导航会中止进行中的用户跳转。引入组件激活标志：

```js
const isComponentActive = ref(true);
onActivated(() => {
  isComponentActive.value = true;
});
onDeactivated(() => {
  isComponentActive.value = false;
});
onBeforeUnmount(() => {
  isComponentActive.value = false;
});
```

push 前检查 `if (isComponentActive.value)` 再执行。同时覆盖 keep-alive 失活与组件卸载两种场景。

## 3. 影响范围

| 文件                              | 变更                                                                        |
| --------------------------------- | --------------------------------------------------------------------------- |
| `views/HelpCenter/helpCenter.vue` | 开关 UI + visibilityValue 计算属性 + 保存/回滚逻辑 + isComponentActive 守卫 |
| `router/manageRouter.ts`          | 新增 /manageCenter/helpCenterSetting 路由                                   |
| `views/manageCenter/index.vue`    | 菜单新增帮助中心入口                                                        |

无后端接口变更、无数据模型变更、无部署配置变更。

## 4. 备选方案与取舍

- **开关直接 v-model 绑定 visibility**：undefined 时显示为关但字段值不正确，且 el-switch 默认布尔值与 int 字段不符，故采用可写计算属性归一化。
- **路由跳转守卫用 watch route 替代**：watch 回调时序同样滞后，无法覆盖"异步完成瞬间路由已变化"的窗口，组件激活标志更直接可靠。
