# 任务：用户管理新增"普通用户"页签

> 分支：`jzcfork/202610normaluser`　核心提交：`74ac5f2e`

## 1. 接口封装

- [x] `src/api/url.ts` 新增 `GET_GENERAL_USER = FRAME_WORK + '/manage/system/user/query-general-user'`
- [x] `src/api/api.ts` 新增 `getGeneralUser = (a, s) => apiClient.post(urls.GET_GENERAL_USER, a, s)`

## 2. 左侧树新增页签

- [x] `user.vue` 在"黑名单用户"上方新增"普通用户"节点
- [x] 节点绑定 `@click="tabChange('general')"`，激活态由 `currentData.type === 'general'` 控制
- [x] `currentData.type` 注释更新为 `// user black system general`

## 3. 数据源分流

- [x] 导入 `getGeneralUser`
- [x] `resMap` 新增 `general: this.getUsers`（两处 resMap）
- [x] `getUsers()` 按 `currentData.type === 'general'` 选择 `getGeneralUser` / `getSystemUser`

## 4. 普通用户视图裁剪

- [x] 用户组筛选下拉：`v-if="currentData.type !== 'black' && currentData.type !== 'general'"`
- [x] 用户组表格列：同上条件
- [x] 操作列：`v-if="!currentData.repo && currentData.type !== 'general'"`
- [x] 弹窗内用户组表单项：同上条件

## 5. 布局修复

- [x] `.management-content` 增加 `min-height: 0`

## 6. 验证

- [ ] 普通用户页签数据来自 `query-general-user`，分页正常
- [ ] 普通用户视图无用户组筛选、无用户组列、无操作列
- [ ] 新增/编辑弹窗无用户组表单项
- [ ] 切回平台用户/黑名单用户，元素显示恢复原样
- [ ] 组织树深层展开后内容区不溢出白色卡片
- [ ] 普通用户视图搜索条件组合查询正确

## 7. 交付

- [ ] 与后端确认 `query-general-user` 上线时间
- [ ] ESLint / TypeScript 检查通过
- [ ] 用户管理 4 个页签回归通过
