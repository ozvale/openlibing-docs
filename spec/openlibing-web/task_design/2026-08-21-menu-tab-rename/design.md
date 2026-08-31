# 技术方案设计

## 方案概述

本需求为 openlibing-web 菜单管理页面的纯展示层文案优化：2 个 tab 改名 + 4 个 tab 增加问号 tooltip 提示。无业务逻辑变更、无接口变更。

## 详细设计

### 1. tabList 数据结构扩展

`menu.vue` 的 `tabList` 数组每项新增 `tip` 字段：

| label | prop | tip |
|-------|------|-----|
| 菜单 | menu | ''（无提示） |
| 未匹配接口列表 | offline | 菜单中配置的接口，未在接口列表中的数据 |
| 接口列表 | interface | 提示数据由接口管理服务提供 |
| 访问白名单接口 | accessWhitelist | 豁免/无需鉴权/无需登录的访问接口列表 |
| 人工配置接口 | falseReport | 未匹配接口列表中，人工已确认是有效配置的接口 |

仅改 label 与新增 tip，prop 值保持原状，`activeTab` 切换与子组件 `v-if` 挂载逻辑零改动。

### 2. 模板改造

tab 头 v-for 渲染的 `.tab-item` 内，在 `{{ tab.label }}` 后追加：

```vue
<el-tooltip v-if="tab.tip" effect="dark" :content="tab.tip" placement="top">
  <i class="iconfont icon-question-circle tab-tip-icon"></i>
</el-tooltip>
```

- `v-if="tab.tip"`：菜单 tab 无 tip 不渲染问号
- tooltip 复用 Element Plus `el-tooltip`（dark 主题，顶部弹出）

### 3. 样式

`.tab-item` 下新增 `.tab-tip-icon`：

- `margin-left: 4px; font-size: 14px`（小于 tab 文字 16px，视觉层级弱化）
- 默认 `color: #c0c4cc`（灰），hover `#409eff`（蓝）与 tab 主题色一致

## 影响范围分析

### 前端影响

- `apps/web-openlibing/src/views/authorityManagement/menu.vue`（tabList 数据 + 模板 + 样式）
- `apps/web-openlibing/src/views/authorityManagement/components/OfflineInterfaceTab.vue`（同步修正代码检视问题）

### 后端影响

- 无

### 兼容性影响

- 纯展示层变更，prop/路由/子组件引用不变，向前兼容

## 技术约束

1. tooltip 文案为固定中文提示，不走 i18n（与现有 tab label 中文直写风格一致）
2. 问号图标使用项目 iconfont 类名 `icon-question-circle`，如 iconfont 未收录需替换为实际类名

## 风险评估

### 低风险

- 仅展示层改动，无逻辑分支变化
- tooltip 不改变 tab 点击行为（图标在 tab-item 内部，点击仍触发切换）

### 风险应对

- 若 iconfont 无问号类名，运行时图标不渲染但 tooltip 结构仍在，替换类名即可修复
