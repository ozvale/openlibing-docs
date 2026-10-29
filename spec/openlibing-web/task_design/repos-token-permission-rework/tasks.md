# 【openlibing-web】代码仓管理令牌体系重构 — 实现任务

## 进度: 已完成（分支 dev-chenning-20260923-repos）

- [x] Task 1: 新增 checkTokenPermission 接口定义（url.ts `CHECK_TOKEN_PERMISSION` 常量 + api.ts POST 函数）
- [x] Task 2: 主编辑弹窗令牌复合输入：prepend 类型下拉（手动填写/继承自项目）、继承态禁用传空、placeholder 分态提示
- [x] Task 3: 令牌类型状态管理：accessTokenType / initialAccessTokenType 反显、切换继承清值清校验、isInheritProjectToken 不入参
- [x] Task 4: 编辑锁定交互：tokenEditLocked 锁定态、"修改令牌"解锁、"取消修改"还原类型与值
- [x] Task 5: 令牌动态必填校验：手动态必填、继承态/已配置未修改不校验（accessTokenFormRules）
- [x] Task 6: 抽取 getSavePayload() 统一 add/edit 提交入参构建，剔除 languageTableData / defaultBranchName / isInheritProjectToken
- [x] Task 7: 保存前权限检查 proceedToSave()：needAlert 弹确认框、取消中止、检查失败不阻断
- [x] Task 8: formatTokenAlertInfo() 文案格式化：HTML 转义防注入、换行转 br、【xxx】高亮、内联警告图标 + token-permission-message-box 样式
- [x] Task 9: 列表新增令牌成员角色/角色状态/权限状态三列（ColumnFilter 表头筛选 + tag 展示）
- [x] Task 10: CategorySearch 新增"令牌信息"分组三项筛选，与查询入参、列头筛选双向联动
- [x] Task 11: 平台限制收紧：isAutoFormat 扩展到 gitee、isSuppressionEnabled gitee 禁用、assumePr/autoTrigger github 重置、autoTriggerDesignScan 非 gitcode 重置
- [x] Task 12: watch(formData.platform) 统一重置受平台影响开关 + applyLastConfig 按平台跳过预填
- [x] Task 13: 移除 disallowSelfMerge / disallowUnresolvedDiscussionsMerge（表单项、列、字段常量、重置逻辑）
- [x] Task 14: 批量编辑弹窗：令牌类型选择与必填校验、切继承清值清校验、提交前权限检查确认
- [x] Task 15: 批量编辑平台受限字段禁选：disabledFieldKeys 计算、全选排除禁用项、el-option disabled
- [x] Task 16: 录入/编辑、批量编辑、全局配置弹窗 close-on-click-modal=false 防误关
- [x] Task 17: 全局配置按钮 project_config 权限控制（NoPermissionPopover + disabled）
- [x] Task 18: 代码风格自动修复帮助文档链接更新为 pre-commit/README.md 新路径
