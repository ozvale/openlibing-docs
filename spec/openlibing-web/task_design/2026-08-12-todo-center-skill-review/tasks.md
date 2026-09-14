## 1. API 与状态层（openlibing-web）

- [x] 1.1 在 `src/api/url.ts` 新增 `const ARGUS = GATEWAY + '/argus/api'` 网关前缀
- [x] 1.2 在 `src/api/url.ts` 新增 `export const SKILL_REVIEW_LIST = ARGUS + '/skill-approvals'`
- [x] 1.3 在 `src/api/api.ts` 新增 `export const getSkillReviewList: RequestFunc = (a, s) => apiClient.get(urls.SKILL_REVIEW_LIST, a, s)`
- [x] 1.4 在 `src/stores/app.ts` 新增 `skillCount` ref 与 `setSkillCount` 方法，并在 store 返回值中导出
- [x] 1.5 在 `src/views/Layout/Banner.vue` 的 getCount 回调中调用 `app.setSkillCount(res?.data?.skillCount || 0)`

## 2. SkillReview 组件（openlibing-web）

- [x] 2.1 新建 `src/views/ToDoCenter/SkillReview.vue` 组件，接收 `view`（PENDING/HISTORY）和 `showStatusFilter` 两个 props
- [x] 2.2 实现筛选表单：关键字（Skill 名称/编码）、提交人、来源（UPLOAD/GIT/NPM/LOCAL）、审批状态（仅 showStatusFilter 为 true 时显示，APPROVED/REJECTED/WITHDRAWN）、提交日期范围（daterange，value-format YYYY-MM-DD）
- [x] 2.3 实现"清空筛选"按钮，`hasFilters` computed 控制禁用状态；`handleReset` 清空所有筛选项并重置到第 1 页
- [x] 2.4 实现表格列：Skill/版本（skillName + skillCode + versionNo）、提交人、来源（el-tag 渲染 sourceTypeMap）、状态（el-tag 渲染 statusMap）、提交时间、操作（去审批/查看）
- [x] 2.5 状态列在"提交时间"列前，与 Argus skill-approvals 页面对齐
- [x] 2.6 表格 `max-height="calc(100vh - 600px)"` 适配新增筛选行
- [x] 2.7 实现分页：`handleSizeChange`、`handleCurrentChange`、`handleSearch` 均重置/刷新 `getReviewTableData`
- [x] 2.8 `getReviewTableData` 构造参数：`current`、`size`、`view`，按筛选条件追加 `keyword`、`submitter`、`sourceType`、`status`（仅 showStatusFilter）、`submittedFrom`/`submittedTo`（来自 submittedRange 数组）
- [x] 2.9 `getReviewTableData` 响应处理：`pagination.total = data?.total ? Number(data.total) : 0`，强制 Number 转换避免字符串分页异常
- [x] 2.10 `formatTime` 工具函数：`String(value).replace('T', ' ').slice(0, 19)` 格式化提交时间
- [x] 2.11 `onBeforeMount` 调用 `getReviewTableData` 初始化列表

## 3. 详情页跳转（openlibing-web）

- [x] 3.1 在 `src/router/routes/modules/noMenu.ts` 新增 `/apps/skillApprovalDetail/:pathMatch(.*)*` 路由，`name: skillApprovalDetail`、`component: WujieMiddleware`
- [x] 3.2 配置 `meta.title: 'Skill 审批详情'`、`meta.noKeepAlive: true`、`meta.hideInMenu: true`
- [x] 3.3 配置 `meta.url`：DEV 模式 `https://localhost.beta.openlibing.com:5173/argus/skill-approvals`，非 DEV 模式 `${import.meta.env.VITE_APP_OPENLIBING_URL}/argus/skill-approvals`
- [x] 3.4 SkillReview.vue 的 `handleViewDetail` 改为 `router.push('/apps/skillApprovalDetail/' + encodeURIComponent(row.reviewId))`，移除 `window.open` 外链跳转
- [x] 3.5 操作列按钮文案：`view === 'PENDING' ? '去审批' : '查看'`

## 4. ToDoCenter 集成（openlibing-web）

- [x] 4.1 在 `ToDoCenter.vue` 引入 `SkillReview` 组件
- [x] 4.2 新增 `el-collapse-item name="skill"`，`v-if="activeName === 'review' || activeName === 'history'"`（移除 `canHandle('argus')` 权限校验）
- [x] 4.3 折叠面板标题：review Tab 下用 `el-badge` 显示 `app.skillCount`（max 9，show-zero false），history Tab 下纯文本
- [x] 4.4 review Tab 下渲染 `<SkillReview />`（默认 view=PENDING），history Tab 下渲染 `<SkillReview view="HISTORY" :show-status-filter="true" />`
- [x] 4.5 在 watch 监听计数的回调中，将 `app.skillCount` 加入依赖数组
- [x] 4.6 默认展开优先级链：权限 > 工具创建 > 工具使用 > Skill（`else if (skillCount > 0) secondTabName.value = ['skill']`）> 权限申请（fallback）

## 5. 详情页返回按钮与 sticky 侧栏（openlibing-vulnerability-hunting-web）

- [x] 5.1 在 `app/pages/skill-approval-detail.tsx` 引入 `useNavigate` 与 `ArrowLeft` 图标
- [x] 5.2 实现 `handleBack` 函数：嵌入模式 `window.$wujie.bus.$emit("host-router", { path: "/apps/toDoCenter" })`，独立模式 `navigate("/skill-approvals")`
- [x] 5.3 在详情加载失败的返回块（`detailQuery.isError || !detail`）顶部渲染"返回待办中心"按钮：`variant="ghost" size="sm"`，`ArrowLeft` 图标 + 文案
- [x] 5.4 在详情加载成功的返回 JSX 顶部渲染同样的"返回待办中心"按钮
- [x] 5.5 将右侧 `<aside>` className 从 `space-y-6` 改为 `space-y-6 xl:sticky xl:top-6 xl:self-start xl:max-h-[calc(100vh-3rem)] xl:overflow-y-auto xl:pr-1`

## 6. 端到端验证

- [x] 6.1 待办中心"待我审批"Tab 显示"Skill 审批申请"折叠面板，标题带数量徽标
- [x] 6.2 "审批历史"Tab 显示同样面板，无徽标，列表带状态筛选
- [x] 6.3 筛选：关键字、提交人、来源、状态、提交日期范围均能正确过滤列表
- [x] 6.4 清空筛选按钮在无筛选条件时禁用，有筛选时点击清空所有条件并刷新
- [x] 6.5 点击"去审批/查看"按钮站内跳转到 `/apps/skillApprovalDetail/:reviewId`，wujie 布局内加载详情页
- [x] 6.6 详情页顶部"返回待办中心"按钮在嵌入模式下通过 host-router 跳转回 `/apps/toDoCenter`
- [x] 6.7 详情页加载失败时仍显示返回按钮
- [x] 6.8 大屏（≥1280px）下右侧侧栏 sticky 跟随滚动，仅左侧主内容滚动
- [x] 6.9 小屏下 sticky 不生效，两栏正常堆叠滚动
- [x] 6.10 列表 total 在后端返回字符串时仍能正确分页
