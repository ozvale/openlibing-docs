## Why

OpenLibing 主应用（openlibing-web）的待办中心（ToDoCenter）已聚合了权限申请、工具创建/使用审批等多类待办，但 Argus 子应用（openlibing-vulnerability-hunting-web）的 Skill 审批一直没有接入。审批人需要进入 Argus 子应用内部的 skill-approvals 页面查看和处理 Skill 提交申请，与其它待办分散在两处，体验割裂。

同时，Skill 审批详情页（skill-approval-detail）存在两个体验问题：

- 进入详情页后无返回入口，用户只能通过浏览器后退或重新导航回到待办中心
- 右侧侧栏（审批操作区）在长内容滚动时一起向上滚走，审批人需要回滚才能看到"通过/驳回"按钮

需要将 Skill 审批接入主应用待办中心，让审批人能在统一入口处理 Skill 申请；并优化详情页的返回交互与侧栏跟随行为。

## What Changes

- **openlibing-web（主应用）**
  - `src/api/url.ts`、`src/api/api.ts`：新增 Argus 网关前缀 `/argus/api` 与 `SKILL_REVIEW_LIST` URL，导出 `getSkillReviewList` API 函数
  - `src/stores/app.ts`：新增 `skillCount` 状态与 `setSkillCount` 方法，与其它待办计数并列
  - `src/views/Layout/Banner.vue`：拉取待办计数接口时回填 `skillCount` 到 store
  - `src/views/ToDoCenter/SkillReview.vue`（新增）：Skill 审批列表组件，支持关键字、提交人、来源、审批状态（仅历史 Tab）、提交日期范围筛选；支持分页；"去审批/查看"按钮跳转详情页
  - `src/views/ToDoCenter/ToDoCenter.vue`：在"待我审批"和"审批历史"Tab 下挂载 Skill 审批申请折叠面板，展示待审批数量徽标，并在所有待审批模块均无内容时默认展开 Skill 面板；后续移除 `canHandle('argus')` 权限校验，对所有用户可见
  - `src/router/routes/modules/noMenu.ts`：新增 `/apps/skillApprovalDetail/:pathMatch(.*)*` 路由，`component: WujieMiddleware`，`hideInMenu: true`、`noKeepAlive: true`；URL 在 DEV 模式指向 `https://localhost.beta.openlibing.com:5173/argus/skill-approvals`，非 DEV 模式为 `${VITE_APP_OPENLIBING_URL}/argus/skill-approvals`
  - SkillReview.vue 表格列：在"提交时间"列前增加"状态"列，与 Argus skill-approvals 页面对齐；表格 `max-height` 由 `calc(100vh - 500px)` 调整为 `calc(100vh - 600px)` 适配新增筛选行
  - SkillReview.vue 详情页跳转：从 `window.open` 外链整页打开，改为 `router.push('/apps/skillApprovalDetail/:reviewId')` 站内 WujieMiddleware 跳转，与工具管理按钮的站内导航方式保持一致
  - SkillReview.vue 筛选：新增"提交日期"日期范围选择器、"清空筛选"按钮；列表请求补充 `submittedFrom`/`submittedTo` 参数；`total` 强制 `Number` 转换避免字符串分页异常
- **openlibing-vulnerability-hunting-web（Argus 子应用）**
  - `app/pages/skill-approval-detail.tsx`：顶部新增"返回待办中心"按钮，嵌入 wujie 时通过 `bus.$emit("host-router", { path: "/apps/toDoCenter" })` 通知主应用客户端路由跳转，独立运行回退到 `navigate("/skill-approvals")`；按钮在详情加载成功和加载失败两种状态下均渲染；右侧 `<aside>` 在 `xl` 断点及以上改为 `sticky` 定位（`xl:sticky xl:top-6 xl:self-start xl:max-h-[calc(100vh-3rem)] xl:overflow-y-auto xl:pr-1`），滚动时仅左侧主内容滚动

## Capabilities

### New Capabilities

- `todo-center-skill-review`：在主应用待办中心聚合 Skill 审批申请，支持筛选、分页、站内跳转审批详情
- `skill-approval-detail-back-navigation`：Skill 审批详情页提供返回待办中心入口，嵌入与独立模式均可用
- `skill-approval-detail-sticky-sidebar`：Skill 审批详情页右侧侧栏在大屏下 sticky 跟随滚动

### Modified Capabilities

## Impact

- 修改文件（openlibing-web）：`src/api/api.ts`、`src/api/url.ts`、`src/stores/app.ts`、`src/views/Layout/Banner.vue`、`src/views/ToDoCenter/ToDoCenter.vue`、`src/router/routes/modules/noMenu.ts`，新增 `src/views/ToDoCenter/SkillReview.vue`
- 修改文件（openlibing-vulnerability-hunting-web）：`app/pages/skill-approval-detail.tsx`
- 后端契约依赖：`GET /argus/api/skill-approvals` 列表接口需支持 `current`、`size`、`view`、`keyword`、`submitter`、`sourceType`、`status`、`submittedFrom`、`submittedTo` 参数，返回 `{ records, total }`；`GET /openlibing-framework/to-do-center/get-pending-review-count` 接口返回体需包含 `skillCount` 字段
- 路由契约：主应用新增保留路径 `/apps/skillApprovalDetail/:pathMatch(.*)*`；Argus 子应用需保持 `/argus/skill-approvals` 路径可访问（dev server 与生产静态资源均需满足）
- 权限变更：Skill 审批面板从 `canHandle('argus')` 受控改为对所有用户可见，依赖后端接口层面的数据权限控制
- 复用机制：主应用 `WujieMiddleware` 既有 `host-router` 事件监听与 `wujieRoute` prop 透传机制，无需新增主应用通信代码
