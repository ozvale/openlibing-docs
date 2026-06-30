# 实现任务

## Task 1: 新增 ColumnFilter 通用组件

**文件**: `apps/web-openlibing/src/views/Repos/components/ColumnFilter.vue`（新增）

- [x] 定义 props：options（选项列表）、modelValue（已选值）、title（列标题）、columns（显示列数）、width（弹窗宽度）
- [x] 实现 checkbox 多选模式
- [x] 实现 radio 单选模式（用于排序等场景）
- [x] 实现全选/取消全选逻辑
- [x] 实现 popover 弹窗交互
- [x] emit confirm/reset 事件

## Task 2: Repos 列表新增列筛选

**文件**: `apps/web-openlibing/src/views/Repos/index.vue`

- [x] 导入 ColumnFilter 组件
- [x] 定义筛选状态：repoLanguageFilter、statusFilter 等
- [x] 语言列 header 添加 ColumnFilter（checkbox 模式，2 列布局）
- [x] 状态列 header 添加 ColumnFilter（radio 模式）
- [x] 列筛选 popper 添加 repos 命名空间前缀避免样式冲突
- [x] 实现 onFilterChange 回调，将筛选参数传给 getRepos 接口

## Task 3: 语言筛选空选项

**文件**: `apps/web-openlibing/src/views/Repos/index.vue`

- [x] 新增 languageFilterOptions 计算属性，在 languageList 基础上追加 `{ label: '无语言', value: '' }`
- [x] ColumnFilter 的 :options 绑定 languageFilterOptions（非 languageList）
- [x] 确保 languageList 保持原始接口数据，编辑表单 el-select 不出现"无语言"选项

## Task 4: 时间排序

**文件**: `apps/web-openlibing/src/views/Repos/index.vue`

- [x] 实现 handleSortChange 处理排序变化
- [x] 定义 sortField/sortOrder 状态
- [x] el-table 添加 @sort-change 事件绑定
- [x] 相关列添加 sortable="custom" 属性
- [x] 将排序参数传给 getRepos 接口

## Task 5: 代码风格自动修复表单项

**文件**: `apps/web-openlibing/src/views/Repos/index.vue`

- [x] 编辑仓库表单新增代码风格自动修复 radio 选项

## Task 6: Bug 修复 - TDZ 报错

**文件**: `apps/web-openlibing/src/views/Repos/index.vue`

- [x] 修复 getRepos 因 watch immediate 触发时访问 TDZ const 抛错的问题
