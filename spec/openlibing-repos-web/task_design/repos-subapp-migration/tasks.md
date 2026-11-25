# 代码仓管理（Repos）模块拆分独立子应用 — tasks

> 对应业务 Issue：https://gitcode.com/openlibing/openlibing-web/issues/433
> 设计依据：同目录 `design.md`；页面原型：同目录 `prototype.html`
> 阶段划分：P0 基线与骨架 → P1 宿主接入 → P2 页面迁移 → P3 接口与公共依赖 → P4 灰度与回滚演练 → P5 下线旧实现

## P0 基线与工程骨架

- [ ] 0.1 记录宿主基线：主包体积、`views/Repos` 21 文件 / 15,659 行、60 个接口清单、功能回归清单。
- [ ] 0.2 新建 `openlibing-repos-web` 仓，按 `openlibing-cicd-web` 复制工程配置：`package.json`、`tsconfig*.json`、`vite.config.ts`（`base: '/repos/'`、port 5175、`/gateway` 代理）、`vitest.config.ts`、`eslint.config.js`、`.prettierrc`、`.stylelintrc`。
- [ ] 0.3 补 `Dockerfile`、`nginx/{nginx_beta,nginx_gamma,nginx_prod}.conf`（`location /repos`）、`.env.development` / `.env.beta` / `.env.gamma` / `.env.production`。
- [ ] 0.4 建三条发布流水线 `openlibing-repos-web-beta` / `-gamma` / `-prod`，对齐 cicd-web 的构建 + 单测门禁。
- [ ] 0.5 搭 `main.ts`、`App.vue`、`api/ApiClient.ts`、`api/core/url.ts`、Element Plus / Pinia 初始化，`pnpm dev` 可在 5175 打开空页面。

## P1 宿主接入与路由

- [ ] 1.1 新增 `src/wujie/host.ts`：`isInWujie` / `hostBus` / `hostProps` / `navigateToHost` / `upsertHostTab` / `getHostTabs`，并补适配层单测（无宿主环境不报错）。
- [ ] 1.2 子应用路由：`createWebHistory('/repos/')`，`/` 重定向 `/repo`，`/repo`（name `repos`）、`/operation-log`（name `repoOperationLog`），兜底重定向 `/repo`。
- [ ] 1.3 `App.vue` 解包宿主 `app` / `tabbar` / `wujieRoute` props，维护 `hostRouteMap`，路由变化时 `bus.$emit('switch-tab', ...)`；监听 `projectInfoChange` 同步 `projectInfo`。
- [ ] 1.4 宿主新增 `views/ReposEntry.vue`：严格 `perms.includes('repos_subapp')` 判断，`permissions` 非数组或未授权一律回旧实现，支持 `localStorage.reposSubapp === '0'` 兜底。
- [ ] 1.5 `router/routes/modules/menu.ts` 的 `repos` 路由：`component` 改 `ReposEntry`，补 `meta.url=${VITE_APP_OPENLIBING_URL}/repos/repo`、`meta.assets=.../repos/`；`name` / `path` / `meta.auth: 'repo_manage'` 保持不变。
- [ ] 1.6 `router/routes/modules/noMenu.ts` 的 `repoOperationLog` 路由同步改为 `ReposEntry`，`meta.url` 指向 `/repos/operation-log`。
- [ ] 1.7 `views/WujieMiddleware.vue` 的 `resolveWujieAppName` 增加 `/apps/repos` 前缀映射为同一 appName，避免两条路由各起实例。
- [ ] 1.8 验证宿主两条路由可加载子应用，切换只换 `wujieRoute`，不重复加载。

## P2 页面迁移

- [ ] 2.1 `views/Repos/index.vue` → `views/repo/index.vue`：tags 读取改 `getHostTabs()`，写入改 `upsertHostTab()`，高度改 `useMainContentHeight`。
- [ ] 2.2 `views/Repos/operationLog.vue` → `views/repo/OperationLog.vue`；`handleShowOperationLog` 由 `router.push('/apps/repoOperationLog')` 改 `router.push('/operation-log')`。
- [ ] 2.3 `branches.vue` → `views/repo/components/Branches.vue`，代码检查与项目管理 2 处跳转改 `navigateToHost`。
- [ ] 2.4 迁移 `repoUserManage.vue`、`tagManagement.vue`、`roleMappingDialog.vue`、`scanResultDialog.vue` 至 `views/repo/components/`。
- [ ] 2.5 迁移 `dialog/*.vue`（6 个弹窗）与 `components/*.vue`（`ColumnFilter` / `JsonDiffViewer` / `TokenCompositeInput`）；`DuplicationCodeDrawer` 保留 CodeMirror 异步 chunk。
- [ ] 2.6 迁移 `useSigSync.ts` 至 `views/repo/composables/`。
- [ ] 2.7 收敛 5 处跨应用跳转为 `navigateToHost`，白名单固定 `inspection` / `interfaceManage` / `codecheck` / `project`。
- [ ] 2.8 鉴权时序：挂载后拉 `/operation-permission`，首屏等待 `operationPermissionReady`，避免按钮级权限闪烁。
- [ ] 2.9 对照 `prototype.html` 核对列表页与操作日志页的工具栏、列、分页、空态、无权限态。

## P3 接口与公共依赖

- [ ] 3.1 `api/Repos/{api,url}.ts` → `api/repo/{api,url}.ts`（18 个接口原样迁移）。
- [ ] 3.2 `api/api.ts` 中 42 个 Repos 函数按域拆分到 `api/repo/{repo,branch,member,tag,scan,role,log}.ts`，URL 统一收敛 `api/repo/url.ts`。
- [ ] 3.3 公共组件：`CategorySearch` / `DateRangePicker` 复用 cicd-web 版本；`BatchOperation` / `Empty` / `NoPermissionPopover` Diff 后取同源较新版本；`ContactInformation` / `BatchAddMemberDialog` 复制迁移。
- [ ] 3.4 `stores/exportTask.ts` + `hooks/useExportTaskSubmit.ts` 迁移，导出下载改走宿主 `host-export-task` 事件。
- [ ] 3.5 `utils` 迁移：`safeOpen` / `validateSafeUrl` / `isTrustDomain`、`TokenCompositeInput` / `tokenPermission.ts` 原样保留，不得简化。
- [ ] 3.6 `constants/permissions-meta.ts` → `constants/permissionsMeta.ts`，仅保留 Repos 条目。
- [ ] 3.7 `localStorage` 列配置 / 筛选缓存 key 加 `repos:` 前缀，首次加载读取并迁移旧 key。
- [ ] 3.8 宿主 `views/Repos/dialog/__tests__/*.spec.ts` 迁至 `tests/unit/`，调整 alias 并跑通。

## P4 灰度与回滚演练

- [ ] 4.1 「菜单管理」新增同名「代码仓管理」按钮型记录，标识 `repos_subapp`，挂「仓库管理」下（不生成路由、不产生导航项）。
- [ ] 4.2 「角色管理」成对授权 `repos_subapp` + `repo_manage`（只授前者会被守卫拦在路由外）。
- [ ] 4.3 灰度放量：先内部角色 → 单项目 → 全量，逐批观察前端错误率与首屏 P95。
- [ ] 4.4 beta 演练 `开 → 关 → 开`，记录配置同步与页面生效时延。
- [ ] 4.5 演练 L2：`kubectl -n <ns> rollout undo deployment/openlibing-repos-web` 并 `rollout status` 确认。
- [ ] 4.6 演练 L3：`localStorage.setItem('reposSubapp','0')` 刷新后回旧实现，`removeItem` 恢复。
- [ ] 4.7 核对回滚触发阈值：JS 错误率 > 1%（5 min）、白屏 > 0.5%、首屏 P95 > 3 s（10 min）、阻断性功能异常，任一命中即回滚不等根因。
- [ ] 4.8 记录回滚时间、操作人、触发指标与结论，纳入发布报告。

## P5 下线旧实现（三次动作，顺序不可颠倒）

- [ ] 5.1 第一次交付：`menu.ts` / `noMenu.ts` 两条路由 `component` 由 `ReposEntry` 改直连 `WujieMiddleware`，补 `meta.url` / `meta.assets`；删除 `ReposEntry.vue` 与 `localStorage.reposSubapp` 读取逻辑；**旧代码文件暂留**。
- [ ] 5.2 观察满一个完整发布周期，确认无需回滚。
- [ ] 5.3 第二次交付（不可逆点）：删除 `views/Repos/**` 21 文件；删除 `api/api.ts` 中 42 个 Repos 函数与 `api/Repos/{api,url}.ts`；按引用情况清理 `stores/exportTask.ts`、`hooks/useExportTaskSubmit.ts`、`hooks/useVbenMainContentHeight.ts`、`utils/until.ts` Repos 段、`constants/permissions-meta.ts` Repos 条目；删除宿主对应单测。
- [ ] 5.4 第三次：清理「菜单管理」`repos_subapp` 记录与各角色授权；**`repo_manage` 保留，禁止删除**。
- [ ] 5.5 收尾验证：`rg` 引用清零 → 构建通过 → 主包体积对比 P0 基线 → 两条路由可进、标签页 / 深链正常、5 处跨应用跳转正常 → 移除 `repo_manage` 的角色仍被正确拦到无权限页。

## 验证

- [ ] V1 子应用独立运行：`pnpm dev`（5175）打开 `/repos/repo`、`/repos/operation-log` 无 wujie 报错。
- [ ] V2 宿主集成：两条路由加载、标签页标题 / 图标 / query、刷新、前进后退、深链。
- [ ] V3 功能回归：按 P0 清单逐项勾选（列表 / 同步 / 分支 / 标签 / 成员 / 全局配置 / 重复代码 / UT 覆盖率 / 指标详情 / 扫描结果 / 操作日志与详情）。
- [ ] V4 权限回归：无权限按钮展示 `NoPermissionPopover` 与申请引导；切项目后权限与数据刷新。
- [ ] V5 跨应用跳转：4 个目标页均落到宿主路由且 query 正确。
- [ ] V6 回滚回归：L1 / L2 / L3 三层均在 beta 验证通过并留档。
- [ ] V7 单元测试：迁移后的 2 个 spec + `wujie/host.ts` 适配层单测全部通过。
