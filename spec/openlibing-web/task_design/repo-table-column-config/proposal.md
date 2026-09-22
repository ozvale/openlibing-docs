# 仓库管理表格列配置及功能优化

## 需求背景

仓库管理页面（`src/views/Repos/index.vue`）表格列数较多（24+列），不同用户关注的信息不同，需要支持用户自定义列的显示/隐藏。同时需要修复若干交互问题。

## 需求范围

### 功能需求
1. **自定义列配置**：仓库管理表格新增"列配置"按钮，支持用户按需显示/隐藏列，配置按用户 ID 持久化到 localStorage
2. **新增同步时间列**：列表新增 `lastSyncTime`（同步时间）列
3. **返回刷新**：从分支管理页返回仓库管理页时自动刷新列表

### Bug 修复
1. 列配置弹窗长标签文本叠加 → 加宽弹窗 + CSS 溢出截断
2. 角色映射弹窗内容溢出 → 增加滚动容器
3. 隐藏分支管理中的 Tag 管理 tab
4. 编辑仓库时 `repoLanguage` 空值导致 `split` 报错
5. 仓库编辑表单中 ruleset 校验阻断提交流程
6. 移除语言字段必填校验
7. gitee 账号标识文案修正（码云账号标识 → gitee账号标识）

## 影响范围

| 文件 | 影响 |
|------|------|
| `src/views/Repos/index.vue` | 主要变更，新增列配置、列、刷新逻辑 |
| `src/views/Repos/branches.vue` | 隐藏 Tag tab |
| `src/views/Repos/roleMappingDialog.vue` | 弹窗滚动修复 |
| `src/utils/common.ts` | 文案修正 |

## 验收标准

- [x] 点击"列配置"按钮弹出列选择面板，默认全选
- [x] 取消勾选某列后表格实时隐藏对应列，确认后持久化到 localStorage
- [x] 代码托管平台、代码仓、操作列不可隐藏
- [x] "恢复默认"恢复全部列可见
- [x] 列配置在不同用户间隔离
- [x] 新增"同步时间"列正常展示
- [x] 从分支管理返回仓库管理时列表自动刷新

## 关联

- Issue: openlibing/openlibing-web#198
- PR: openlibing/openlibing-web#526
