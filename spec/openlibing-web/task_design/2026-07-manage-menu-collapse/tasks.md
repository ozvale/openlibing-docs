# Tasks: 管理中心左侧菜单支持折叠与右侧自适应

## 实现步骤

- [x] 1. 引入 `@element-plus/icons-vue` 的 `Expand` / `Fold` 图标
- [x] 2. 新增 `isCollapse` ref 状态（默认 false）与 `toggleCollapse` 方法
- [x] 3. `el-menu` 绑定 `:collapse="isCollapse"` 与 `:collapse-transition="false"`（关闭内置动画避免闪烁，宽度过渡由外层 CSS 负责）
- [x] 4. 根 `.apps` 容器增加 `:class="{ 'is-collapsed': isCollapse }"` 动态类
- [x] 5. 左侧 `.l` 底部新增 `.collapse-btn`：含 `Fold`（展开态）/ `Expand`（折叠态）图标 + "收起菜单"文案
- [x] 6. 样式调整：`.l` 改为 `flex-direction: column` + `flex-shrink: 0`，宽度 200px + `transition: width`
- [x] 7. 样式调整：`.r` 由 `width: calc(100% - 200px)` 改为 `flex: 1; min-width: 0;` 自适应
- [x] 8. 折叠态样式：`.is-collapsed .l` 宽度 64px，子菜单标题居中、隐藏文字，折叠按钮隐藏文案
- [x] 9. 验证已有行为不受影响：菜单选中态、`menuSelect` 路由跳转、权限控制（menuShow / opsShow / aiManageShow / aiConfigShow）

## 验证

- [x] 无 TypeScript / 模板诊断错误
- [x] 已提交并推送到远端分支 `jzcfork/202607managemenu`
