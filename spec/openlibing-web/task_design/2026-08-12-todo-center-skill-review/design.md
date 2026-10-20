## Context

OpenLibing 主应用（openlibing-web）的待办中心（ToDoCenter.vue）是一个聚合各类审批/申请任务的页面，按"待我审批（review）/ 审批历史（history）/ 我的申请（approve）/ 我的工单（myorders）"四个 Tab 组织，每个 Tab 下用 `el-collapse` 折叠面板展示不同业务模块（权限申请、工具创建审批、工具使用审批等）。每个业务模块由一个独立的 Vue 子组件渲染，折叠面板标题通过 `el-badge` 显示待办数量。

待办计数流程：

- `Layout/Banner.vue` 在顶部栏调用 `get-pending-review-count` 接口
- 接口返回 `{ toolReportCount, toolApplyCount, toolUseApplyCount, ... }` 等各类计数
- 通过 `useAppStore` 的 setter 写入 store
- `ToDoCenter.vue` 监听 store 中各类计数的变化，自动展开第一个有待审批内容的折叠面板

Argus 子应用（openlibing-vulnerability-hunting-web）是嵌入主应用的 React 19 子应用，已存在独立的 Skill 审批列表页（`/argus/skill-approvals`）和详情页（`/skill-approvals/:reviewId`，由 `skill-approval-detail.tsx` 实现）。详情页右侧 `<aside>` 渲染审批操作区（通过/驳回按钮、审批意见），左侧渲染 Skill 元信息、版本、内容预览等长内容。

现有技术栈与机制：

- 主应用：Vue 3 + Element Plus + Pinia + Vue Router
- 主应用 API 层：统一 apiClient 封装，按业务域前缀组织 URL（`FRAME_WORK`、`CODE_CHECK`、`PLATFORM_RELEASE` 等）
- 子应用路由：主应用 `noMenu.ts` 配置 `WujieMiddleware` 路由，通过 `meta.url` 指定子应用加载入口；`/apps/xxx` 路径约定嵌入 wujie 加载
- 主应用 `WujieMiddleware.vue`：已通用监听 `bus.$on('host-router', handleHostRouter)` → `router.push(obj)`；已将 `wujieRoute` prop 透传给子应用
- 子应用 `window.$wujie.bus`：可用于向主应用 emit 事件
- 待办中心其它模块跳转详情：工具管理使用 `router.push` 站内导航到 `/apps/xxx` WujieMiddleware 路由

## Goals / Non-Goals

**Goals:**

- 在待办中心"待我审批"和"审批历史"Tab 下新增"Skill 审批申请"折叠面板，展示待审批数量徽标
- Skill 审批列表支持关键字（Skill 名称/编码）、提交人、来源、审批状态（仅历史 Tab）、提交日期范围筛选，支持分页
- "去审批/查看"按钮站内跳转到嵌入主应用的 Argus Skill 审批详情页，与工具管理按钮的站内导航方式保持一致
- Skill 审批详情页提供"返回待办中心"按钮，嵌入模式通过 wujie bus 通知主应用客户端路由跳转
- Skill 审批详情页右侧侧栏在大屏下 sticky 跟随滚动
- SkillReview 表格列结构与 Argus skill-approvals 页面对齐（含"状态"列）

**Non-Goals:**

- 不改造 Argus 子应用 `/argus/skill-approvals` 列表页本身
- 不修改主应用 `WujieMiddleware.vue` 的通用事件监听逻辑
- 不新增后端接口，复用 Argus 既有 `GET /argus/api/skill-approvals` 列表接口
- 不处理 Skill 详情页左侧主内容的长内容分块/目录导航
- 不在小屏（< xl 断点）下启用 sticky 侧栏

## Decisions

### D1: 列表组件位置 —— 待办中心内嵌 vs 独立路由

**选择**: 在 ToDoCenter.vue 内嵌 SkillReview.vue 折叠面板，复用待办中心的 Tab/折叠布局

**理由**: Skill 审批是待办的一类，与权限申请、工具审批同属"待我审批/审批历史"流程。独立路由会割裂体验，用户需要在多个入口间切换。复用待办中心的折叠面板布局，让审批人在一处处理所有待办，是产品诉求。

### D2: API URL 前缀 —— 新增 ARGUS vs 复用既有前缀

**选择**: 新增 `const ARGUS = GATEWAY + '/argus/api'`，`SKILL_REVIEW_LIST = ARGUS + '/skill-approvals'`

**理由**: Argus 是独立子应用，其 API 走 `/argus/api` 网关前缀，与既有 `FRAME_WORK`、`CODE_CHECK` 等业务域前缀并列。新增前缀保持 URL 组织清晰，便于后续 Argus 相关接口扩展。

### D3: 计数集成 —— 复用 get-pending-review-count vs 独立接口

**选择**: 复用 `get-pending-review-count` 接口，依赖后端在返回体中新增 `skillCount` 字段

**理由**: 待办计数已在 Banner.vue 统一拉取并写入 store，ToDoCenter 通过监听 store 响应式更新徽标。新增独立接口会增加请求次数和复杂度。后端在既有计数接口返回体中追加 `skillCount` 字段是最低成本方案，前端只需在 Banner.vue 增加一行 setter 调用。

### D4: 默认展开策略 —— 自动展开优先级

**选择**: 在"待我审批"Tab 下，若权限、工具创建、工具使用均无待审批内容，则自动展开 Skill 面板（`else if (skillCount > 0) secondTabName.value = ['skill']`）

**理由**: 待办中心原逻辑是"展开第一个有待审批数量的模块"，新增 Skill 后需将其纳入优先级链。放在工具使用之后、权限申请之前，保持"高频业务优先"的展开顺序。无待审批内容时仍默认展开权限申请（原 fallback 行为）。

### D5: 详情页跳转 —— window.open 外链 vs router.push 站内

**选择**: 改为 `router.push('/apps/skillApprovalDetail/:reviewId')`，新增 `/apps/skillApprovalDetail/:pathMatch(.*)*` WujieMiddleware 路由

**理由**:

- `window.open` 整页打开 Argus 子应用，会脱离主应用布局（菜单/Tab/会话上下文），与工具管理按钮的站内导航方式不一致
- 站内跳转在 wujie 布局内加载详情页，保留主应用上下文，体验连贯
- WujieMiddleware 路由 `meta.url` 指向 `${VITE_APP_OPENLIBING_URL}/argus/skill-approvals`，wujie 会以该 URL 为入口加载子应用，并通过 `:pathMatch(.*)*` 透传剩余路径段给子应用内部路由
- DEV 模式 URL 指向 `https://localhost.beta.openlibing.com:5173/argus/skill-approvals`，便于本地直连子应用 dev server 联调

### D6: 详情页返回按钮 —— wujie bus vs 浏览器后退

**选择**: 嵌入模式 `bus.$emit("host-router", { path: "/apps/toDoCenter" })`，独立模式 `navigate("/skill-approvals")`

**理由**:

- 浏览器后退在 wujie 嵌入模式下行为不可控（可能退出整个主应用 SPA），不可用
- 主应用 `WujieMiddleware` 已通用监听 `host-router` 事件并 `router.push`，复用即可
- 返回目标为待办中心（`/apps/toDoCenter`），与用户心智模型一致（"从待办进，回待办"）
- 独立运行模式没有 wujie bus，回退到 React Router `navigate` 回到 Skill 审批列表页
- 按钮在详情加载成功和加载失败两种状态下均渲染，避免加载失败时用户卡在详情页无出口

### D7: 侧栏 sticky 断点 —— xl 及以上

**选择**: `xl:sticky xl:top-6 xl:self-start xl:max-h-[calc(100vh-3rem)] xl:overflow-y-auto xl:pr-1`

**理由**:

- 大屏（`xl` ≥ 1280px）下左右两栏并排，主内容长、侧栏短，sticky 让审批操作区始终可见
- 小屏下两栏会堆叠，sticky 会导致侧栏占满视口无法滚动主内容，不适用
- `top-6` 留出顶部导航栏空间；`max-h-[calc(100vh-3rem)]` + `overflow-y-auto` 防止侧栏自身内容超长时溢出视口
- `self-start` 确保 flex item 不被拉伸到主内容高度，sticky 才能生效

### D8: 状态列对齐 —— 始终显示 vs 仅历史 Tab 显示

**选择**: 始终显示"状态"列（在"提交时间"列前），与 Argus skill-approvals 页面对齐

**理由**: 原 SkillReview.vue 设计是仅在"审批历史"Tab 显示状态列（`showStatusColumn = props.view === 'HISTORY'`）。但 Argus 子应用 skill-approvals 页面始终显示状态列，为保持两个入口的视觉一致性，改为始终显示。待我审批 Tab 下记录状态多为"待审核"，展示状态列不会造成信息冗余。

### D9: 权限校验移除 —— canHandle('argus') vs 全员可见

**选择**: 移除 `canHandle('argus')` 校验，Skill 审批面板对所有用户可见

**理由**:

- 前端权限校验只能控制 UI 可见性，无法控制数据访问，后端接口仍会按用户身份返回相应数据
- `canHandle('argus')` 会将无 Argus 权限的用户完全挡在面板外，连"无待办"状态都看不到，体验不一致
- 移除前端校验后，依赖后端接口返回空列表实现"无权限则无数据"，更符合最小权限原则
- 与其它待办模块（权限申请、工具审批）的可见性策略保持一致

## Risks / Trade-offs

- **[后端 skillCount 字段未就绪]** → 若 `get-pending-review-count` 接口未返回 `skillCount` 字段，Banner.vue 通过 `res?.data?.skillCount || 0` 兜底为 0，徽标不显示但面板仍可手动展开。应对：前端已做空值兜底，后端字段就绪后自动生效。
- **[DEV 模式 wujie 子应用 URL 需本地启动]** → 开发模式下 `skillApprovalDetail` 路由指向 `https://localhost.beta.openlibing.com:5173/argus/skill-approvals`，需 Argus 子应用 dev server 在该 host:port 运行。应对：联调时需先启动子应用；生产模式不受影响。
- **[sticky 侧栏在内容超长时滚动冲突]** → 侧栏 `overflow-y-auto` 与主内容滚动可能产生 wheel 事件穿透。应对：侧栏内容（审批操作）本身较短，触发概率低；`xl:max-h-[calc(100vh-3rem)]` 限制侧栏最大高度，超出时侧栏内部滚动而非撑破视口。
- **[返回按钮在加载失败态的导航目标]** → 加载失败时点击返回仍跳转待办中心，用户无法在详情页重试加载。应对：这是预期行为，加载失败通常不可恢复（如 reviewId 不存在），返回待办中心重新选择是合理路径。
- **[权限校验移除后数据可见性]** → 无 Argus 权限的用户看到 Skill 面板但列表为空。应对：依赖后端接口按用户身份过滤数据，前端展示空列表与"无待办"状态一致，不泄露敏感信息。
- **[total 字符串导致分页异常]** → 原 `data?.total || 0` 在后端返回字符串 total 时会保留字符串，导致 el-pagination 分页计算异常。应对：已强制 `Number(data.total)` 转换。
