# 实现任务

## Task 1: 仓库表格自定义列配置

**文件**: `src/views/Repos/index.vue`

- [x] 导入 `Setting` 图标
- [x] 定义 `allColumns` 数组（24 列，含 label/prop/disabled 属性）
- [x] 添加列配置状态：`columnSettingVisible`、`checkedColumnKeys`、`tempCheckedKeys` 等
- [x] 实现 `localStorage` 持久化（按用户 ID 隔离）
- [x] 实现全选/反选逻辑 `handleColumnCheckAllChange`
- [x] 实现列勾选变化逻辑 `handleCheckedColumnChange`
- [x] 实现确认/取消/恢复默认逻辑
- [x] 模板添加列配置 popover 按钮（全选、列列表、恢复默认、确认/取消）
- [x] 模板所有表格列添加 `v-if="checkedColumnKeys.includes('...')"`
- [x] 添加 `.column-setting-*` CSS 样式
- [x] 列配置弹窗宽度优化（360→620），修复长标签叠加
- [x] checkbox 添加溢出截断 CSS 兜底

## Task 2: 新增同步时间列

**文件**: `src/views/Repos/index.vue`

- [x] `allColumns` 中添加 `{ label: '同步时间', prop: 'lastSyncTime' }`
- [x] 模板添加 `el-table-column`（v-if、width=170px、空值兜底）

## Task 3: 返回刷新

**文件**: `src/views/Repos/index.vue`

- [x] `branchBack()` 函数末尾添加 `getRepos()` 调用

## Task 4: Bug 修复

**文件**: `src/views/Repos/branches.vue`
- [x] 注释 Tag 管理 tab

**文件**: `src/views/Repos/roleMappingDialog.vue`
- [x] Dialog 添加 `body-class="form-box"`
- [x] 添加 `.form-box` 滚动样式

**文件**: `src/views/Repos/index.vue`
- [x] `repoLanguage` 空值保护：`formData.repoLanguage ? formData.repoLanguage.split(',') : []`
- [x] `submit()` 中移除 `checkRepoRuleset()` 阻断逻辑
- [x] `checkRepoRuleset()` 中移除 `ElMessage.warning` 阻断
- [x] `rules` 中移除 `repoLanguage` 必填校验

**文件**: `src/utils/common.ts`
- [x] 文案修正：`码云账号标识` → `gitee账号标识`
