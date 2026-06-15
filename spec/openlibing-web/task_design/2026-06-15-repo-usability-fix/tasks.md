# 2026-06-15 代码仓管理易用性问题修复任务清单

## 开发任务

### ContactInformation 组件修改

- [x] 新增 `keepInputOnSwitch` prop（Boolean，默认 false），控制切换联系人类型时是否保留 accountLogin 输入
- [x] 修改 `handleSelectChange` 函数：当 `keepInputOnSwitch` 为 true 时不清空 `accountLogin`
- [x] 修改 `handleSelectChange` 函数：切换时调用 `getFormInfor(userForm.value.accountLogin)` 触发搜索

### Repos/index.vue 修改

- [x] 新增 `repoUrlHandleSelect` 函数：自动完成选择后使用 `nextTick` 清除 repoUrl 校验错误并自动带出仓库名称
- [x] 导入 `nextTick`（从 vue）
- [x] 移除 `repoUrlHandleBlur` 中多余的注释代码

### repoUserManage.vue 修改

- [x] 为 ContactInformation 组件添加 `:keepInputOnSwitch="true"` prop，切换联系人类型时保留已输入的登录名

## 验证任务

### 功能验证

- [ ] 手动测试 Repos 页面：仓库 URL 自动完成选择后校验提示消失且仓库名称自动填充
- [ ] 手动测试 repoUserManage 页面：切换联系人类型时登录名保留
- [ ] 手动测试其他使用 ContactInformation 组件的页面：默认行为不受影响

### Code Review

- [ ] Reviewer 检查代码变更
- [ ] 解决 Review 反馈（如有）
- [ ] 获得 Approval

### 合并与部署

- [ ] PR 合并到 `release_20260615` 分支
- [ ] 等待 CI/CD 流水线通过
- [ ] 验证生产环境功能正常
