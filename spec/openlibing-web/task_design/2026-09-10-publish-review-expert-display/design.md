# 技术方案

## 方案概述

在 `basicInformation.vue` 的 `getUserOptions` 方法中，接口返回 `data` 数组后、赋值给 `userList` 之前，遍历数组将每项 `userName` 追加 `（userId）` 后缀。

## 改动文件

| 文件 | 改动说明 |
|------|----------|
| `apps/web-openlibing/src/views/Publish/publishReview/detail/components/basicInformation.vue` | `getUserOptions` 的 `.then` 回调中，`data.forEach` 追加 `userName` 格式化 |

## 核心代码

```javascript
// getUserOptions 的 .then 回调
const { code, data } = res;
data.forEach(item => {
  item.userName = `${item.userName}（${item.userId}）`;
});
userList.value = code === 200 ? data : [];
```

## 影响范围

- **影响范围**：仅 `basicInformation.vue` 组件的评审专家下拉选项展示
- **数据来源**：`getUserOptions` 接口返回的 `data` 数组，原始 `userName` 和 `userId` 均由后端提供
- **不影响**：接口请求参数、后端逻辑、其他组件、路由、权限

## 风险分析

1. **userId 为空**：若接口返回 `userId` 为空字符串，则展示为 `用户名（）`，视觉上略不美观但不会报错；当前接口稳定返回 userId，风险低
2. **userName 已含括号**：理论上用户名不会包含中文括号，不构成冲突
3. **提交保存**：评审专家选择后，提交的是 `userId` 而非 `userName`，格式化不影响提交数据
