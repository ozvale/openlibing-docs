# role-detail-permission-disabled — 技术设计

## 方案概述

利用 Element Plus `el-tree` 组件对节点数据 `disabled` 字段的内置支持：在 `fomatTree` 遍历树节点时，根据当前 `dialogType` 给每个节点写入 `disabled` 字段。同时通过非 scoped 样式覆盖 disabled 复选框在不同 checked 状态下的视觉表现。

## 架构决策

| 决策点     | 选择                            | 原因                                                                                       |
| ---------- | ------------------------------- | ------------------------------------------------------------------------------------------ |
| 禁用方式   | 节点数据 `disabled` 字段        | Element Plus `el-tree` 原生支持，无需修改模板，无需侵入组件逻辑                            |
| 样式作用域 | 非 scoped `<style lang="less">` | 已存在的非 scoped 样式块已覆盖 `.el-tree` 内的 checkbox 自定义样式，复用同一作用域保持一致 |
| 颜色取值   | `#4971ff`（品牌蓝）             | 与同文件 `.subTitle .icons .blue` 一致，保持视觉统一                                       |

## 涉及文件

| 文件                                                         | 操作 | 说明                                                       |
| ------------------------------------------------------------ | ---- | ---------------------------------------------------------- |
| `apps/web-openlibing/src/views/authorityManagement/role.vue` | 修改 | `fomatTree` 方法新增一行赋值；样式块新增 disabled 状态规则 |

## 关键代码

### 1. fomatTree 赋值 disabled 字段

```js
fomatTree(data) {
  data.forEach((item) => {
    item.label = item.menuName;
    item.disabled = this.dialogType === 'detail';
    if (Array.isArray(item.children)) {
      this.fomatTree(item.children);
    }
  });
  return data.sort((pre, cur) => ~~pre.number - ~~cur.number);
}
```

### 2. CSS 样式覆盖

```less
// disabled + checked：品牌蓝背景 + 白色勾
.el-tree
  .el-checkbox.is-disabled
  .el-checkbox__input.is-checked
  .el-checkbox__inner {
  background-color: #4971ff;
  border-color: #4971ff;
  &::after {
    border-color: #ffffff;
  }
}
// disabled + unchecked：浅灰背景，与已勾选形成明显对比
.el-tree
  .el-checkbox.is-disabled
  .el-checkbox__input:not(.is-checked)
  .el-checkbox__inner {
  background-color: #f5f7fa;
  border-color: #dcdfe6;
}
```

## 风险 & 缓解

- **风险**：`fomatTree` 在 `add`/`update` 模式下也会被调用，可能误写入 `disabled: false`。
  **缓解**：显式赋值 `this.dialogType === 'detail'` 表达式结果，add/update 模式下即为 `false`，不影响行为；同时每次 `openDialog` 都会重新拉取后端数据，无残留风险。
- **风险**：非 scoped 样式可能影响其他页面的 `el-tree` 复选框。
  **缓解**：样式选择器以 `.userGroup-container .el-tree` 开头限定作用域，仅当前页面的 el-tree 受影响。

## 跨仓影响

无。仅前端 UI 改动，无后端接口、数据模型、跨仓契约变化。
