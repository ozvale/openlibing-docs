# 2026-09-08 精简模式全局「去登录」按钮 - 任务清单

## 实现步骤

- [x] app.ts 新增 `simpleAuthNeedLogin` 状态（ref(false)）并导出
- [x] 新建 `SimpleAuthLoginButton.vue`：三重闸门显示条件 + 圆形图标按钮 + tooltip「去登录」（初版点击留空）
- [x] Content.vue 接入：`getUserInfor` rejected 分支检测 401（HTTP/业务码双形态）置位 store；template 挂载组件
- [x] 迭代 1：图标由 `User`（人头）换为内联 SVG 登录图标（箭头进门，继承 currentColor）
- [x] 迭代 2：接入点击事件，复用 `ApiClient.autoLoginPlatform()`（缓存 fullpath + 分平台跳 OAuth）
- [x] 迭代 3：`simpleAuthNeedLogin` 全路径覆盖——fulfilled 显式置 false，rejected 布尔表达式赋值（非 401 / 非精简均为 false）
- [x] 迭代 4：拖拽移动——Pointer 事件 + 指针捕获，4px 阈值区分点击/拖拽，可视区边界 clamp
- [x] 拖拽细节：`.dragging` 禁用过渡与 hover 位移、tooltip 拖拽中隐藏、`touch-action: none`、`pointercancel` 兜底重置
- [x] ESLint 验证通过（三个改动文件）
- [x] `vue-tsc --build --force` 类型检查通过
- [x] 提交并推送（commits: `fbdf2bfa`、`235dd972`、`47204b06`，分支 `jzcfork/202609loginmenu`）
- [ ] 用户自测确认（精简模式 401 显示 / 已登录隐藏 / 点击跳 OAuth / 拖拽不误触发）
- [ ] 创建业务 PR（跨仓 `--head` fork 分支）并打 `ai-assisted` 标签
- [ ] 关联业务 Issue
- [ ] 归档 archive.md（Phase 5 用户触发后）
