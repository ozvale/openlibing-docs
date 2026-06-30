# 代码仓列表新增列筛选、时间排序及代码风格自动修复

**Issue**: openlibing/openlibing-web#202

## 需求背景

代码仓（Repos）列表页缺少按列筛选和排序功能，用户无法快速定位目标仓库。同时存在 getRepos 在 watch immediate 触发时 TDZ 报错的问题，以及编辑仓库时缺少代码风格自动修复选项。

## 功能描述

### 做什么
- 新增 ColumnFilter.vue 通用列筛选组件，支持 checkbox / radio 两种模式
- Repos 列表页新增语言、代码风格、活跃度等列筛选
- 语言筛选新增空语言选项，支持筛选未设置语言的仓库
- Repos 列表支持按时间字段排序
- 编辑仓库表单新增代码风格自动修复选项
- 修复 getRepos 因 watch immediate 触发时访问 TDZ const 抛错的问题

### 不做什么
- 不修改现有表格数据展示逻辑
- 不实现自定义筛选条件保存功能
- 不实现跨页筛选状态持久化

## 验收标准

- [ ] Repos 列表页筛选功能正常（语言、代码风格、活跃度筛选）
- [ ] Repos 列表时间排序功能正常
- [ ] 无语言的仓库能被正确筛选
- [ ] 代码风格自动修复表单项功能正常
- [ ] 页面加载不再出现 TDZ 报错
- [ ] 编辑仓库表单中不出现"无语言"选项

## 影响范围

- 文件：`apps/web-openlibing/src/views/Repos/index.vue`、`apps/web-openlibing/src/views/Repos/components/ColumnFilter.vue`（新增）
- 模块：Repos - 代码仓管理
- 接口：无新增后端接口，纯前端变更
