# 2026-06-15 代码仓管理易用性问题修复 - 技术方案

## 1. 方案概述

本次修改针对代码仓管理模块的 3 个前端易用性问题，通过组件 prop 扩展和事件处理优化来解决。

## 2. 技术方案

### 2.1 ContactInformation 组件 - 切换触发搜索 + 可控清空

**问题**：`handleSelectChange` 无条件清空 `accountLogin` 且不触发搜索。

**方案**：

- 新增 `keepInputOnSwitch` prop（Boolean, default: false）
- `handleSelectChange` 中根据 `keepInputOnSwitch` 决定是否清空 `accountLogin`
- 切换后始终调用 `getFormInfor(userForm.value.accountLogin)` 触发搜索

```typescript
// 修改前
function handleSelectChange() {
  userForm.value.accountLogin = '';
}

// 修改后
function handleSelectChange() {
  if (!props.keepInputOnSwitch) {
    userForm.value.accountLogin = '';
  }
  getFormInfor(userForm.value.accountLogin);
}
```

**兼容性**：`keepInputOnSwitch` 默认 false，现有调用方行为不变。

### 2.2 Repos/index.vue - 自动完成选择后校验与填充

**问题**：仓库 URL 自动完成选择后，校验错误提示未清除，仓库名称未自动填充。

**方案**：

- 新增 `repoUrlHandleSelect` 函数，绑定到自动完成选择事件
- 使用 `nextTick` 确保 DOM 更新后再操作
- 先 `clearValidate('repoUrl')` 清除校验错误
- 再执行 `validateSafeUrl` 校验并自动带出仓库名称

```typescript
const repoUrlHandleSelect = () => {
  nextTick(() => {
    formRef.value?.clearValidate('repoUrl');
    const result = validateSafeUrl(formData.repoUrl);
    if (result.validate) {
      formData.repoName = getRepoName(formData.repoUrl);
    }
  });
};
```

### 2.3 repoUserManage.vue - 保留输入

**问题**：仓库用户管理场景切换联系人类型时不应清空登录名。

**方案**：为 ContactInformation 传入 `:keepInputOnSwitch="true"`。

## 3. 影响范围

| 文件 | 变更 | 影响范围 |
|------|------|----------|
| ContactInformation.vue | 新增 prop + 修改 handleSelectChange | 所有使用该组件的页面，但默认值保证向后兼容 |
| Repos/index.vue | 新增 repoUrlHandleSelect + 导入 nextTick | 仅仓库创建/编辑页面 |
| repoUserManage.vue | 传入 keepInputOnSwitch prop | 仅仓库用户管理页面 |

## 4. 无数据模型变更

本次修改不涉及数据模型、接口契约或后端变更。
