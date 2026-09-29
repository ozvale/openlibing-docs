# 2026-09-08 精简模式全局「去登录」按钮 - 技术设计

## 1. 总体方案

「401 检测置位 store（Content.vue）+ 纯展示组件订阅 store」解耦：

```text
Content.vue init() → Promise.allSettled([getUserInfor, ...])
├─ fulfilled（已登录）        → app.simpleAuthNeedLogin = false（显式清除）
└─ rejected
   ├─ 精简模式 + 401          → app.simpleAuthNeedLogin = true（布尔表达式整体赋值）
   └─ 非 401 / 非精简模式      → 表达式短路为 false

SimpleAuthLoginButton.vue（挂载于 Content.vue template，全局唯一实例）
├─ 显示条件: app.initApp && app.simpleAuth && app.simpleAuthNeedLogin（三重闸门）
├─ 点击:     ApiClient.autoLoginPlatform()（与 401 自动登录同一套逻辑）
└─ 拖拽:     Pointer 事件 + 指针捕获，阈值判定拖拽/点击
```

三重闸门避免误显示：`initApp`（初始化完成，防止 loading 期间闪现）、`simpleAuth`（仅精简模式）、`simpleAuthNeedLogin`（401 置位）。

## 2. 关键设计决策

| #   | 决策                                                      | 理由                                                                                                                                       |
| --- | --------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ |
| 1   | 401 检测放在 `Content.vue` 而非组件内                     | `init()` 内 `getUserInfor` 以 `disableToken: true` 调用，401 不走 ApiClient 全局跳转而落入 `allSettled` rejected 分支，此处是唯一检测点    |
| 2   | 兼容两种 401 形态                                         | `reason.response.status === 401`（HTTP 状态码）或 `reason.code === 401`（业务码），与 ApiClient 既有错误结构对齐                           |
| 3   | 状态放 `useAppStore`（`simpleAuthNeedLogin`）而非组件局部 | 检测点（Content.vue）与展示组件（SimpleAuthLoginButton）解耦，store 响应式驱动显隐                                                         |
| 4   | rejected 分支用布尔表达式整体赋值（非 if 置位）           | fulfilled 显式置 false + rejected 表达式赋值，四条路径（成功/401/非 401/非精简）全覆盖，无状态残留                                         |
| 5   | 点击复用 `autoLoginPlatform()` 而非新写跳转               | 与精简模式 401 自动登录完全同一套逻辑：缓存 `auto-login-fullpath`、`autoLoginComplete` 防重入、按 `codeHostingPlatformFlag` 分平台跳 OAuth |
| 6   | 图标用内联 SVG（Material Design login）                   | Element Plus 无「登录」语义图标（`User` 是人头、`SwitchButton` 是电源易误解为退出），内联 SVG 继承 `currentColor` 随主题反色               |
| 7   | 拖拽用 Pointer 事件 + `setPointerCapture`                 | 统一鼠标/触屏；指针捕获后移出按钮仍可拖；`touch-action: none` 防触屏拖拽触发页面滚动                                                       |
| 8   | 4px 位移阈值区分点击与拖拽                                | 低于阈值松手视为点击（触发登录）；达到阈值标记拖拽，`handleClick` 检测 `isDragging` 吞掉拖拽结束的那次 click                               |
| 9   | 拖拽开始时切换 `left/top` 定位（清除 `right`）            | 按钮初始 `top/right` 定位，拖动需改为 `left/top` 才能自由移动；`getBoundingClientRect` 读取一次后缓存宽高，避免 transform 干扰             |
| 10  | 拖拽期间禁用 transition/hover 位移并隐藏 tooltip          | `translateY(-2px)` 会影响 `getBoundingClientRect` 与视觉位置；tooltip 跟随拖拽体验差                                                       |

## 3. 交互状态机（拖拽）

```text
pointerdown（主键）
  → 锁定 left/top 定位、记录起点/宽高、setPointerCapture
pointermove
  → 位移 < 4px: 忽略（等待判定）
  → 位移 ≥ 4px: isDragging = true，按 dx/dy 更新位置（clamp 到可视区）
pointerup
  → 释放捕获；isDragging 不重置（pointerup 后才触发 click）
click
  → isDragging 为 true: 吞掉本次点击并重置（拖拽不触发登录）
  → isDragging 为 false: autoLoginPlatform()（原地点击触发登录）
pointercancel（系统中断兜底）
  → 直接重置 isDragging，避免吞掉下一次真实点击
```

## 4. 影响范围

| 维度     | 影响                                                                                          |
| -------- | --------------------------------------------------------------------------------------------- |
| 文件     | `SimpleAuthLoginButton.vue`（新建）、`app.ts`（+1 状态）、`Content.vue`（401 检测 + 挂载）    |
| 接口     | 无新增/变更（复用 `getUserInfor` 结果与 `autoLoginPlatform` 跳转）                            |
| 数据模型 | store 新增 `simpleAuthNeedLogin: ref(false)`，无持久化                                        |
| 普通模式 | 零影响：`simpleAuth` 为 false 时按钮不渲染，`getUserInfor` 401 在非精简模式走原有全局跳转逻辑 |
| 样式层级 | z-index 1500（> DefaultLoading 998、< ElMessage 等 Element 弹层），fixed 定位不参与文档流     |
