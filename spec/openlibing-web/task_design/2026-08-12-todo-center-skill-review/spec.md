## ADDED Requirements

### Requirement: Skill 审批 API 与状态

系统 SHALL 在主应用 openlibing-web 中新增 Argus 网关前缀 `/argus/api` 与 `SKILL_REVIEW_LIST` URL，导出 `getSkillReviewList` API 函数；并在 `useAppStore` 中新增 `skillCount` 状态与 `setSkillCount` 方法，与其它待办计数并列。

#### Scenario: 调用 Skill 审批列表接口

- **WHEN** 前端调用 `getSkillReviewList({ params: { current, size, view, ... } })`
- **THEN** apiClient 向 `${GATEWAY}/argus/api/skill-approvals` 发起 GET 请求，携带所有筛选参数

#### Scenario: 待办计数写入 store

- **WHEN** Banner.vue 调用 `get-pending-review-count` 接口收到响应
- **THEN** 通过 `app.setSkillCount(res?.data?.skillCount || 0)` 将 Skill 待审批数量写入 store 的 `skillCount` 状态，缺失字段时兜底为 0

### Requirement: Skill 审批列表组件

系统 SHALL 提供 `SkillReview.vue` 组件，支持关键字（Skill 名称/编码）、提交人、来源（UPLOAD/GIT/NPM/LOCAL）、审批状态（仅 `showStatusFilter` 为 true 时显示）、提交日期范围筛选，支持分页，列表列结构与 Argus skill-approvals 页面对齐。

#### Scenario: 渲染筛选表单

- **WHEN** SkillReview 组件挂载
- **THEN** 渲染关键字输入框、提交人输入框、来源下拉、提交日期 daterange 选择器、清空筛选按钮；当 `showStatusFilter` prop 为 true 时额外渲染审批状态下拉

#### Scenario: 状态列始终显示

- **WHEN** 渲染表格列
- **THEN** "状态"列固定出现在"提交时间"列之前，无论 `view` 是 PENDING 还是 HISTORY，与 Argus skill-approvals 页面列结构一致

#### Scenario: 来源列渲染

- **WHEN** 某行 `sourceType` 为 `UPLOAD`/`GIT`/`NPM`/`LOCAL`
- **THEN** 该列渲染对应颜色的 el-tag（上传 primary、Git success、NPM warning、内置 info）；`sourceType` 为空时渲染 "--"

#### Scenario: 状态列渲染

- **WHEN** 某行 `status` 为 `PENDING_REVIEW`/`APPROVED`/`REJECTED`/`WITHDRAWN`
- **THEN** 该列渲染对应颜色的 el-tag（待审核 warning、已通过 success、已驳回 danger、已撤回 info）；`status` 为空时渲染 "--"

#### Scenario: 提交日期范围筛选

- **WHEN** 用户选择 submittedRange 为 `["2026-08-01", "2026-08-10"]` 并触发搜索
- **THEN** 列表请求追加 `submittedFrom=2026-08-01`、`submittedTo=2026-08-10` 参数

#### Scenario: 清空筛选

- **WHEN** 用户点击"清空筛选"按钮且 `hasFilters` 为 true
- **THEN** 所有关键字、提交人、来源、状态、submittedRange 筛选项被清空，分页重置到第 1 页，列表重新加载

#### Scenario: 清空按钮禁用状态

- **WHEN** 所有筛选项均为空（keyword、submitter、sourceType 为空，showStatusFilter 为 false 或 status 为空，submittedRange 不是长度为 2 的数组）
- **THEN** "清空筛选"按钮禁用

#### Scenario: total 字符串转换

- **WHEN** 后端返回 `data.total` 为字符串 `"15"`
- **THEN** `pagination.total` 被设置为 `Number("15") = 15`，el-pagination 正常分页

#### Scenario: 提交时间格式化

- **WHEN** 后端返回 `submittedAt` 为 `"2026-08-12T11:17:50"`
- **THEN** 列表项的 `submittedAt` 被格式化为 `"2026-08-12 11:17:50"`（替换 T 为空格，截取前 19 位）

### Requirement: 待办中心 Skill 审批面板

系统 SHALL 在待办中心的"待我审批"和"审批历史"Tab 下挂载"Skill 审批申请"折叠面板，"待我审批"Tab 下标题通过 el-badge 显示 `skillCount` 待审批数量，并对所有用户可见（无 `canHandle('argus')` 权限校验）。

#### Scenario: 待我审批 Tab 显示面板与徽标

- **WHEN** 用户进入待办中心"待我审批"Tab 且 `app.skillCount > 0`
- **THEN** 渲染"Skill 审批申请"折叠面板，标题右侧显示 el-badge 数量徽标（max 9，超过显示 9+），面板内渲染 `<SkillReview />`（view=PENDING）

#### Scenario: 审批历史 Tab 显示面板无徽标

- **WHEN** 用户进入待办中心"审批历史"Tab
- **THEN** 渲染"Skill 审批申请"折叠面板，标题为纯文本无徽标，面板内渲染 `<SkillReview view="HISTORY" :show-status-filter="true" />`

#### Scenario: skillCount 为 0 时不显示徽标

- **WHEN** "待我审批"Tab 下 `app.skillCount === 0`
- **THEN** el-badge 的 `show-zero=false` 生效，不显示数量徽标，面板仍可手动展开

#### Scenario: 无权限用户可见面板

- **WHEN** 不具备 Argus 权限的用户访问待办中心
- **THEN** "Skill 审批申请"折叠面板仍渲染（无 `canHandle('argus')` 校验），列表请求由后端按用户身份返回空数据

#### Scenario: 自动展开优先级

- **WHEN** 用户进入"待我审批"Tab 且权限、工具创建、工具使用均无待审批内容，但 `skillCount > 0`
- **THEN** "Skill 审批申请"折叠面板自动展开（`secondTabName = ['skill']`）

#### Scenario: 无任何待审批内容时回退展开

- **WHEN** 用户进入"待我审批"Tab 且所有模块（含 Skill）均无待审批内容
- **THEN** 默认展开"权限申请"面板（原 fallback 行为不变）

### Requirement: Skill 审批详情站内跳转

系统 SHALL 在主应用 noMenu 路由模块新增 `/apps/skillApprovalDetail/:pathMatch(.*)*` WujieMiddleware 路由，SkillReview 列表的"去审批/查看"按钮通过 `router.push` 站内跳转到该路由，避免 `window.open` 外链整页打开。

#### Scenario: 点击去审批按钮站内跳转

- **WHEN** 用户在"待我审批"Tab 点击某行的"去审批"按钮
- **THEN** 调用 `router.push('/apps/skillApprovalDetail/' + encodeURIComponent(row.reviewId))`，主应用客户端路由跳转到 WujieMiddleware 路由，wujie 布局内加载 Argus 子应用的 Skill 审批详情页

#### Scenario: 点击查看按钮站内跳转

- **WHEN** 用户在"审批历史"Tab 点击某行的"查看"按钮
- **THEN** 同样通过 `router.push` 站内跳转，按钮文案为"查看"而非"去审批"

#### Scenario: 路由元信息配置

- **WHEN** 主应用匹配到 `/apps/skillApprovalDetail/:pathMatch(.*)*` 路由
- **THEN** 使用 `WujieMiddleware` 组件渲染，`meta.title` 为"Skill 审批详情"，`meta.hideInMenu: true` 不出现在导航菜单，`meta.noKeepAlive: true` 不缓存子应用实例

#### Scenario: 开发模式子应用 URL

- **WHEN** `import.meta.env.DEV` 为 true
- **THEN** WujieMiddleware 的 `meta.url` 为 `https://localhost.beta.openlibing.com:5173/argus/skill-approvals`，指向本地 Argus dev server

#### Scenario: 生产模式子应用 URL

- **WHEN** `import.meta.env.DEV` 为 false
- **THEN** WujieMiddleware 的 `meta.url` 为 `${import.meta.env.VITE_APP_OPENLIBING_URL}/argus/skill-approvals`，由环境变量拼接

#### Scenario: 路由不出现在主导航菜单

- **WHEN** 主应用渲染主导航菜单
- **THEN** 由于 `meta.hideInMenu: true`，`/apps/skillApprovalDetail/:pathMatch(.*)*` 路由不出现在菜单项中

### Requirement: Skill 审批详情页返回按钮

系统 SHALL 在 Argus 子应用 `skill-approval-detail.tsx` 页面顶部渲染"返回待办中心"按钮，嵌入 wujie 模式通过 `bus.$emit("host-router", { path: "/apps/toDoCenter" })` 通知主应用客户端路由跳转，独立运行模式回退到 React Router `navigate("/skill-approvals")`；按钮在详情加载成功和加载失败两种状态下均渲染。

#### Scenario: 嵌入模式点击返回

- **WHEN** 用户在嵌入 wujie 的 Skill 审批详情页点击"返回待办中心"按钮
- **THEN** 子应用通过 `window.$wujie.bus.$emit("host-router", { path: "/apps/toDoCenter" })` 通知主应用，主应用 WujieMiddleware 调用 `router.push` 客户端跳转到 `/apps/toDoCenter`

#### Scenario: 独立运行模式点击返回

- **WHEN** 用户在独立运行（无 wujie）的 Skill 审批详情页点击"返回待办中心"按钮
- **THEN** 调用 `navigate("/skill-approvals")` 通过 React Router 客户端跳转回 Skill 审批列表页

#### Scenario: 详情加载失败时显示返回按钮

- **WHEN** `detailQuery.isError || !detail` 为 true，详情数据加载失败
- **THEN** 错误返回块顶部仍渲染"返回待办中心"按钮，用户可点击返回待办中心

#### Scenario: 详情加载成功时显示返回按钮

- **WHEN** 详情数据加载成功
- **THEN** 页面顶部（PageHeader 之前）渲染"返回待办中心"按钮，样式为 `variant="ghost" size="sm"`，左侧带 `ArrowLeft` 图标

### Requirement: Skill 审批详情页 sticky 侧栏

系统 SHALL 在 Skill 审批详情页右侧 `<aside>` 应用 Tailwind sticky 定位类，在 `xl` 断点（≥1280px）及以上启用 sticky 跟随滚动，小屏下不生效。

#### Scenario: 大屏下侧栏 sticky 跟随

- **WHEN** 视口宽度 ≥ 1280px（xl 断点）
- **THEN** 右侧 `<aside>` 应用 `xl:sticky xl:top-6 xl:self-start xl:max-h-[calc(100vh-3rem)] xl:overflow-y-auto xl:pr-1`，滚动时侧栏固定在视口顶部 `top-6` 位置，仅左侧主内容滚动

#### Scenario: 小屏下 sticky 不生效

- **WHEN** 视口宽度 < 1280px
- **THEN** sticky 类不生效，`<aside>` 与左侧主内容按正常文档流堆叠滚动

#### Scenario: 侧栏内容超长时内部滚动

- **WHEN** 大屏下侧栏内容高度超过 `calc(100vh-3rem)`
- **THEN** 侧栏 `max-h-[calc(100vh-3rem)]` + `overflow-y-auto` 生效，侧栏内部出现滚动条，不撑破视口

#### Scenario: self-start 防止 flex 拉伸

- **WHEN** 大屏下左右两栏为 flex 布局
- **THEN** `xl:self-start` 确保侧栏 flex item 不被拉伸到主内容高度，sticky 定位才能生效
