# Design: 排队Tab取消排队按钮增加权限判断

## 技术方案

### 权限判断复用

参照 Detail.vue 已有的 `hasAuth` + `getCurrentProjectAuth` 模式，在 Queue.vue 中实现相同的权限判断逻辑：

1. 调用 `getUserRole` 获取当前用户在项目中的角色列表
2. 判断角色是否为 `project_manager` 或 `project_cie`
3. 结果存入 `hasAuth` ref，驱动模板条件渲染

### 未登录保护

`getCurrentProjectAuth` 增加 `app.user?.userId` 前置判断，未登录时直接 return，避免无意义请求。`hasAuth` 保持默认值 `true`，不改变状态。

### 模板条件渲染

```vue
<el-tooltip v-if="hasAuth" content="取消排队" placement="top">
  <el-button :icon="TopLeft" link @click="cancelQueue(row)" />
</el-tooltip>
<TipMemberListComp v-else>
  <el-button :icon="TopLeft" link disabled />
</TipMemberListComp>
```

### ApiClient 路由跳转统一

提取 `navigateToRoute()` 方法统一处理微前端（hostBus.$emit）和独立模式（router.push）的路由跳转，消除 403 处理中的重复代码。

## 影响范围

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| Queue.vue | 功能新增 | 增加 hasAuth + TipMemberListComp 权限判断 |
| Detail.vue | 逻辑修正 | 移除 Turing 项目限制；增加未登录保护 |
| ApiClient.ts | 重构 | 提取 getHostBus / navigateToRoute；补全 needCheck=2 路由跳转；类型安全 |

## 无破坏性变更

- hasAuth 默认值为 true，未登录时保持 true，不影响现有行为
- navigateToRoute 是纯提取重构，行为与原内联代码一致
