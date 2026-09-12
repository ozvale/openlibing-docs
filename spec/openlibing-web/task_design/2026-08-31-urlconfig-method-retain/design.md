# 技术方案设计

## 方案概述

本需求为 openlibing-web 菜单管理 URL 配置组件（UrlConfig.vue）的交互修正：请求方式支持手动切换同步 + URL 未命中时保留已选请求方式。无接口变更，仅组件内部事件流修正。

## 详细设计

### 1. 请求方式 change 事件同步

请求方式 `el-select` 增加 `@change="getMethodResult"`：

```vue
<el-select
  v-model="data.requestMethod"
  @change="getMethodResult"
>
```

新增 `getMethodResult` 方法，向父组件 emit 完整配置数据（保持与 `getUrlResult` 相同的 emit 结构，父组件无需区分来源）：

```javascript
getMethodResult(val) {
  const res = {
    ...this.data,
    requestMethod: val,
  };
  this.$emit('change', res);
},
```

### 2. getUrlResult 保留请求方式

`getUrlResult` 中 URL 命中下拉选项时仍按接口 `httpMethod` 回填；未命中与清空分支改为保留 `this.data.requestMethod`，仅无值时兜底 `'GET'`：

```javascript
// 命中：tmp ? tmp.httpMethod : (this.data.requestMethod || 'GET')
// 未命中/清空：this.data.requestMethod || 'GET'
```

## 影响范围分析

### 前端影响

- `apps/web-openlibing/src/views/authorityManagement/components/UrlConfig.vue`（+10/-2 行）

### 后端影响

- 无

### 兼容性影响

- emit 的 `change` 事件数据结构不变（仍是完整配置对象），父组件（menu.vue 弹窗）零改动，向前兼容

## 技术约束

1. `getMethodResult` 必须展开 `...this.data` 保留 menuUrl/flag 等字段，避免覆盖丢失
2. 兜底 `GET` 逻辑保持，确保旧数据（无 requestMethod）打开时默认值不变

## 风险评估

### 低风险

- 纯前端交互修正，单一组件，改动 12 行
- URL 命中回填 httpMethod 的主路径逻辑不变

### 风险应对

- 若用户先手选 POST 再选择一个 GET 接口的 URL，请求方式会被接口 httpMethod 覆盖为 GET——此为预期行为（接口真实方式优先），回归验证覆盖
