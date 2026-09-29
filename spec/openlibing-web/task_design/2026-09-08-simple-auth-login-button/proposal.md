# 2026-09-08 精简模式全局「去登录」按钮提案

## 1. 需求背景

平台「精简模式」（simpleAuth，URL query `codeHostingPlatformFlag=gitee/gitcode` 或 `autoLogin=complete` 触发）会隐藏 tabbar/sidebar/header，嵌入外部系统使用。该模式下用户未登录时（`getUserInfor` 报 401），页面无任何登录入口：

- 401 时 ApiClient 虽会自动走 `autoLoginPlatform()` 跳 OAuth，但自动授权失败（如用户取消授权）后页面停留在未登录状态，用户无法手动再次发起登录
- 精简模式隐藏了 header，普通模式的用户菜单入口不可用

因此需要一个**全局显示**的「去登录」悬浮按钮，作为精简模式未登录状态的兜底登录入口。

### 需求演进（含用户迭代反馈）

1. **初版需求**：精简模式 + 未登录（`getUserInfor` 401）时显示全局悬浮按钮，图标形式 + tooltip「去登录」，样式精致；点击逻辑暂留空（用户后续接入）
2. **迭代 1**：图标从人头 `User` 换为「箭头进门」登录语义图标（Element Plus 无自带登录图标，改用内联 SVG）
3. **迭代 2**：接入点击事件，复用精简模式 401 自动登录逻辑（`ApiClient.autoLoginPlatform`）
4. **迭代 3**：非 401 / 已登录场景显式将 `simpleAuthNeedLogin` 置 false（用户反馈：非 401 情况要重置状态）
5. **迭代 4**：按钮支持拖拽移动位置，且拖拽不能误触发登录跳转

## 2. 验收标准

### 功能验收

- [x] 精简模式 + `getUserInfor` 401（HTTP 401 或业务 code 401）→ 右上角显示「去登录」按钮
- [x] 精简模式 + 已登录（`getUserInfor` 成功）→ 按钮不显示（状态显式清除）
- [x] 精简模式 + 非 401 失败 → 按钮不显示（不属于未登录场景）
- [x] 非精简模式 → 任何情况下按钮都不显示
- [x] 全局显示：挂在 Content.vue 布局包装层，所有页面可见
- [x] 鼠标悬浮显示 tooltip「去登录」
- [x] 点击按钮复用 `autoLoginPlatform()`：缓存当前路由 fullPath → 跳对应平台（gitee/gitcode）OAuth 授权页
- [x] 按钮可拖拽移动，位置限制在可视区内；拖拽结束的那次 click 不触发登录
- [x] 原地点击（位移 < 4px 阈值）正常触发登录跳转

### 代码质量验收

- [x] ESLint 无告警（SimpleAuthLoginButton.vue / app.ts / Content.vue）
- [x] `vue-tsc --build --force` 类型检查通过
- [x] z-index 1500 > DefaultLoading（998），不被加载遮罩遮挡

## 3. 变更范围

### 涉及模块

- **新组件**: `apps/web-openlibing/src/components/SimpleAuthLoginButton.vue` — 全局「去登录」悬浮按钮（显示判定 + 点击登录 + 拖拽移动）
- **Store**: `apps/web-openlibing/src/stores/app.ts` — 新增 `simpleAuthNeedLogin` 状态并导出
- **初始化**: `apps/web-openlibing/src/views/Content.vue` — `getUserInfor` 401 检测置位/清位 store；template 挂载按钮组件

### 变更类型

- 新功能（精简模式登录入口补齐）

## 4. 风险评估

- **风险等级**: 低
- **影响范围**: 仅精简模式未登录场景的 UI 增强；普通模式零影响（按钮不渲染）
- **破坏性变更**: 无（不改既有 401 自动登录流程，仅叠加手动入口）
- **已知行为**（符合设计设定）:
  - 按钮位置不持久化，刷新后回到默认右上角
  - 拖拽中 tooltip 隐藏、过渡动效禁用

## 5. 关联信息

- **分支**: `jzcfork/202609loginmenu`
- **Commits**: `fbdf2bfa`（feat 初版按钮）、`235dd972`（fix 非 401 状态重置）、`47204b06`（feat 拖拽移动）
- **标签**: ai-assisted
