# 代码仓管理（Repos）模块独立子工程迁移 — design

> 状态：设计稿（待评审）
> 目标仓库（新建）：`openlibing-repos-web`
> 参考实现：`openlibing-cicd-web`（已独立部署的 wujie 子应用）
> 宿主：`openlibing-web/apps/web-openlibing`

## 1. 方案设计

### 1.1 背景

`web-openlibing` 中的 `src/views/Repos` 已演化成"代码仓管理"完整业务域：仓库列表/同步、分支管理、标签管理、仓库成员、角色映射、全局配置、重复代码、UT 覆盖率、指标详情、接口扫描结果、操作日志。该模块共 **21 个文件、16,568 行代码**（另有 2 个单测文件），其中 `index.vue` 单文件 **6,660 行 / 238,015 字节（约 232 KB）**，且与宿主的路由、鉴权 store、标签页 store、公共组件、单体 API 文件强耦合。

继续留在宿主内会导致：

- 宿主主包与首屏体积持续膨胀，构建与热更新变慢；
- Repos 与 `openlibing-web` 主工程共用同一条构建与发布流水线，发布节奏互相牵制，职责边界不清晰；
- 单体 `api/api.ts` 被两个业务域共同修改的概率上升，冲突面扩大。

### 1.2 目标与非目标

**目标**

1. 新建独立前端仓 `openlibing-repos-web`，把 `views/Repos` 全量迁出，按 `openlibing-cicd-web` 的工程形态承载。
2. 以 wujie 微前端方式挂在宿主 7 条 Repos 路由下（`/apps/repos` 及其 5 条子路由、`/apps/repoOperationLog`），**对外 URL 与路由 name 保持不变**。
3. 宿主与子应用通过 `app / tabbar / wujieRoute` props 与 wujie bus 通信，子应用可独立开发、构建、部署。
4. 迁移后功能、权限、埋点、导出、跳转行为与迁移前一致。

**非目标**

- 不改后端接口契约，不做代码仓域的功能重构或 UI 改版。
- 不迁移代码仓后端仓（`openlibing-coderepo`），仅前端。
- 不在本期合并 `openlibing-web` 与 `openlibing-cicd-web` 的公共组件仓（公共层先复制 + 双仓同步，后续再抽包）。

### 1.3 关键结论

| 结论       | 说明                                                                                     |
| ---------- | ---------------------------------------------------------------------------------------- |
| 迁移形态   | 完全对齐 `openlibing-cicd-web`：Vue 3 + Vite + wujie 子应用，`base: '/repos/'`           |
| 宿主改动   | 7 条路由（6 条仓库 + 1 条操作日志）改为 `ReposEntry`，`name` / `path` / `meta.auth` 不变 |
| 主要工作量 | 61 个 API 函数抽取、10 个公共组件/工具迁移、5 处跨应用跳转改造、标签页适配               |
| 最大风险   | 宿主标签页与项目切换的联动（`useTabbarStore` 不可跨应用直接写）                          |
| 回滚方式   | 同名菜单授权切换 + 入口代码兜底，旧代码在验收期内不删除                                  |

## 2. 实现逻辑设计

### 2.1 目标架构

```text
┌─────────────────────────────── openlibing-web（宿主） ───────────────────────────────┐
│  菜单 / 标签页 / 项目切换 / 登录态 / 权限菜单                                          │
│  /apps/repos（含 branch / ut-coverage / code-metrics 等共 6 条子路由）                  │
│      -> ReposEntry（开关） -> WujieMiddleware  app="repos"  url="/repos/..."           │
│  /apps/repoOperationLog -> ReposEntry（开关） -> WujieMiddleware  app="repos"          │
│            │ props: app / tabbar / wujieRoute / wujieAppName                           │
│            │ bus  : projectInfoChange / switch-tab / add-route-tab / host-router ...    │
└────────────┼───────────────────────────────────────────────────────────────────────────┘
             │  wujie（iframe + proxy + shadow DOM）
┌────────────▼───────────────────── openlibing-repos-web ──────────────────────────────┐
│  base: /repos/    dev: 5175    nginx location /repos                                 │
│  views/repo/index.vue          （仓库管理，原 Repos/index.vue）                        │
│  views/repo/OperationLog.vue   （操作日志，原 Repos/operationLog.vue）                  │
│  api/repo/*                    （61 个接口按域拆分）                                   │
│  stores/app.ts                 （与 cicd-web 同源的鉴权/项目上下文）                    │
│  wujie/host.ts                 （宿主能力适配层，子应用内唯一出口）                     │
└────────────┬───────────────────────────────────────────────────────────────────────────┘
             │  /gateway（cookie 会话）
        openlibing-gateway -> openlibing-coderepo / openlibing-codecheck / ...
```

### 2.2 仓库骨架（对齐 cicd-web）

```text
openlibing-repos-web/
├── Dockerfile
├── nginx/{nginx_beta.conf,nginx_gamma.conf,nginx_prod.conf}
├── index.html
├── package.json
├── tsconfig.json / tsconfig.node.json
├── vite.config.ts            # base '/repos/', port 5175, /gateway 代理, 本地 https
├── vitest.config.ts
├── eslint.config.js / .prettierrc / .stylelintrc
├── .env.development / .env.beta / .env.gamma / .env.production
├── .gitcode/workflows/       # 构建、镜像、部署流水线
├── src/
│   ├── main.ts               # createApp + router + pinia + ElementPlus
│   ├── App.vue               # 宿主 props 解包、项目同步、路由映射、tab 桥接
│   ├── api/
│   │   ├── ApiClient.ts      # 与 cicd-web 同源（拦截器、错误提示、traceId）
│   │   ├── core/url.ts       # 网关前缀与公共常量
│   │   └── repo/
│   │       ├── api.ts        # 原 api/Repos/api.ts（20 个）
│   │       ├── url.ts        # 原 api/Repos/url.ts
│   │       ├── repo.ts       # 仓库 CRUD / 同步 / 过滤项
│   │       ├── branch.ts     # 分支 CRUD / 评审人 / SCA 版本扫描
│   │       ├── member.ts     # 成员 / 社区角色 / 同步
│   │       ├── tag.ts        # 标签 / 可申请仓库
│   │       ├── scan.ts       # 接口扫描结果 / 基线
│   │       ├── role.ts       # GitCode 角色映射
│   │       └── log.ts        # 操作日志详情
│   ├── components/           # 公共组件（见 2.4）
│   ├── constants/            # permissionsMeta 等
│   ├── hooks/                # useRouteActive / useExportTaskSubmit / useMainContentHeight
│   ├── router/index.ts       # createWebHistory('/repos/')
│   ├── stores/               # app / exportTask
│   ├── utils/                # repoUrl / notice / link / formatLanguage / export
│   ├── views/repo/           # 页面与业务组件（见 2.3）
│   ├── wujie/host.ts         # 宿主通信适配层（见 2.5）
│   └── tests/unit/           # 迁移后的 2 个 spec + 适配层单测 + 开关判定单测
```

### 2.3 代码迁移映射

| 原路径（`web-openlibing/src`）                              | 新路径（`openlibing-repos-web/src`）                 | 处理方式                                                                  |
| ----------------------------------------------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------- |
| `views/Repos/index.vue`                                     | `views/repo/index.vue`                               | 直接迁移；tabbar / 跨应用跳转 / 高度 hook 改造                            |
| `views/Repos/branches.vue`                                  | `views/repo/components/Branches.vue`                 | 业务组件下沉；跨应用跳转改造                                              |
| `views/Repos/operationLog.vue`                              | `views/repo/OperationLog.vue`                        | 转为子应用路由 `/operation-log`                                           |
| `views/Repos/repoUserManage.vue`                            | `views/repo/components/RepoUserManage.vue`           | 依赖 `ContactInformation`、`BatchAddMemberDialog`                         |
| `views/Repos/tagManagement.vue`                             | `views/repo/components/TagManagement.vue`            | 直接迁移                                                                  |
| `views/Repos/roleMappingDialog.vue`                         | `views/repo/components/RoleMappingDialog.vue`        | 直接迁移                                                                  |
| `views/Repos/scanResultDialog.vue`                          | `views/repo/components/ScanResultDialog.vue`         | 直接迁移                                                                  |
| `views/Repos/dialog/*.vue`                                  | `views/repo/dialog/*.vue`                            | 8 个弹窗（另有 2 个 `.ts`）；`DuplicationCodeDrawer` 保留 CodeMirror 依赖 |
| `views/Repos/components/*.vue`                              | `views/repo/components/*.vue`                        | `ColumnFilter` / `JsonDiffViewer` / `TokenCompositeInput`                 |
| `views/Repos/useSigSync.ts`                                 | `views/repo/composables/useSigSync.ts`               | 直接迁移                                                                  |
| `views/Repos/dialog/__tests__/*.spec.ts`                    | `tests/unit/*.spec.ts`                               | 路径与 alias 调整                                                         |
| `api/Repos/{api,url}.ts`                                    | `api/repo/{api,url}.ts`                              | 20 个函数原样迁移（19 个 URL，`GLOBAL_CONFIG` 被 get/post 复用）          |
| `api/api.ts`（Repos 相关 41 个）                            | `api/repo/{repo,branch,member,tag,scan,role,log}.ts` | 按域拆分，URL 从 `api/url.ts` 收敛                                        |
| `stores/exportTask.ts`                                      | `stores/exportTask.ts`                               | 依赖宿主 `extractExportId`，需一并迁移                                    |
| `hooks/useExportTaskSubmit.ts`                              | `hooks/useExportTaskSubmit.ts`                       | 改为走宿主导出事件                                                        |
| `hooks/routerActive.js`                                     | `hooks/useRouteActive.ts`                            | 补类型                                                                    |
| `hooks/useVbenMainContentHeight.ts`                         | `hooks/useMainContentHeight.ts`                      | 去掉 vben 依赖，改为宿主高度变量 + 兜底计算                               |
| `utils/until.ts`（部分）                                    | `utils/{repoUrl,notice,link}.ts`                     | `isTrustDomain` / `validateSafeUrl` / `safeOpen` 必须保留                 |
| `majun/src/utils/common.ts`（`formatLanguage`）             | `utils/formatLanguage.ts`                            | 单独抽出                                                                  |
| `components/ContactInformation.vue`                         | `components/ContactInformation.vue`                  | 复制迁移                                                                  |
| `components/BatchAddMemberDialog.vue`                       | `components/BatchAddMemberDialog.vue`                | 复制迁移                                                                  |
| `components/{BatchOperation,Empty,NoPermissionPopover}.vue` | `components/`                                        | 与 cicd-web 已有实现比对后取同源版本                                      |
| `components/{CategorySearch,DateRangePicker}`               | `components/`                                        | 复用 cicd-web 版本，避免第三份副本                                        |
| `constants/permissions-meta.ts`                             | `constants/permissionsMeta.ts`                       | 仅保留 Repos 相关条目                                                     |

### 2.4 公共依赖处理策略

| 依赖                                               | 处理                                                                                |
| -------------------------------------------------- | ----------------------------------------------------------------------------------- |
| `BatchOperation` / `Empty` / `NoPermissionPopover` | 以 `openlibing-cicd-web` 同名组件为基线，Diff 后取较新版本                          |
| `CategorySearch` / `DateRangePicker`               | 直接复用 cicd-web 版本（已含 `daterange` 类型重构）                                 |
| `ContactInformation` / `BatchAddMemberDialog`      | 宿主独有，复制到新仓 `components/`                                                  |
| `NoPermissionPopover` 用到的权限元数据             | 同步 `constants/permissionsMeta.ts` 的 Repos 段                                     |
| Element Plus / CodeMirror                          | 沿用主应用版本号；`codemirror` + `@codemirror/*` 仅被重复代码抽屉使用，走异步 chunk |

### 2.5 宿主通信适配层（`src/wujie/host.ts`）

子应用内**禁止**直接访问 `window.$wujie`，统一通过适配层，保证独立运行（`pnpm dev`）不报错。

```ts
export const isInWujie = () => Boolean((window as any).$wujie);
export const hostBus = () => (window as any).$wujie?.bus;
export const hostProps = () => (window as any).$wujie?.props ?? {};

/** 跨应用跳转白名单：只允许这 4 个宿主路由 */
const HOST_ROUTE_WHITELIST = new Set([
  "inspection",
  "interfaceManage",
  "codecheck",
  "project",
]);

/**
 * 跳主应用路由。
 * - 只接受白名单内的 name；签名里不提供 path，杜绝拼接任意 URL 绕过白名单。
 * - 无宿主（独立开发）时返回 false，由调用方提示或禁用入口。
 */
export function navigateToHost(target: {
  name?: string;
  query?: Record<string, any>;
}) {
  if (!isInWujie()) return false;
  if (!target?.name || !HOST_ROUTE_WHITELIST.has(target.name)) return false;
  hostBus()?.$emit("host-router", { name: target.name, query: target.query });
  return true;
}

/** 标签页 upsert：替代 useTabbarStore.addTab；无宿主时降级为子应用内 query 同步 */
export async function upsertHostTab(tab: {
  name: string;
  path: string;
  query?: Record<string, any>;
}) {
  if (!isInWujie()) {
    const { router } = await import("@/router");
    await router.replace({ query: tab.query ?? {} });
    return;
  }
  hostBus()?.$emit("add-route-tab", tab);
}

/** 读取宿主标签页快照 */
export const getHostTabs = () => hostProps()?.tabbar?.tabs ?? [];
```

> 宿主侧现状：`WujieMiddleware.handleHostRouter` 直接 `router.push(obj)`，**没有任何白名单校验**，所有子应用共享这条裸通道。本期必须在子应用侧收口（上面 `navigateToHost`），宿主侧统一白名单另行立项，不得在文档里当作已具备。

跨应用跳转改造点：

| 位置                                        | 原实现                                               | 新实现                                               |
| ------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| `index.vue handleShowOperationLog`          | `router.push('/apps/repoOperationLog')`              | `router.push('/operation-log')`（子应用内）          |
| `index.vue goInspection`                    | `router.push({ name: 'inspection' })`                | `navigateToHost({ name: 'inspection', query })`      |
| `index.vue openScanResult`                  | `router.push({ name: 'interfaceManage' })`           | `navigateToHost({ name: 'interfaceManage', query })` |
| `branches.vue 跳代码检查`                   | `router.push({ name: 'codecheck' })`                 | `navigateToHost({ name: 'codecheck', query })`       |
| `branches.vue / ProjectPublicAccountDialog` | `router.push({ name: 'project' })` / `/apps/project` | `navigateToHost({ name: 'project' })`                |

跨应用白名单在子应用 `wujie/host.ts` 内维护：`inspection` / `interfaceManage` / `codecheck` / `project`。

### 2.6 宿主路由改造（唯一配置来源）

宿主实际有 **7 条**路由指向 Repos 业务，全部统一改为 `component: ReposEntry`：

| 文件                            | 路由 name                       | path                                      |
| ------------------------------- | ------------------------------- | ----------------------------------------- |
| `menu.ts`（`reposRoot` 子路由） | `repos`                         | `/apps/repos`                             |
| 同上                            | `reposBranch`                   | `/apps/repos/branch`                      |
| 同上                            | `reposBranchUtCoverage`         | `/apps/repos/branch/ut-coverage`          |
| 同上                            | `reposBranchUtCoverageHistory`  | `/apps/repos/branch/ut-coverage-history`  |
| 同上                            | `reposBranchCodeMetrics`        | `/apps/repos/branch/code-metrics`         |
| 同上                            | `reposBranchCodeMetricsHistory` | `/apps/repos/branch/code-metrics-history` |
| `noMenu.ts`                     | `repoOperationLog`              | `/apps/repoOperationLog`                  |

`src/router/routes/modules/menu.ts`：

```ts
const ReposEntry = () => import('@/views/ReposEntry.vue');

{
  name: 'reposRoot',
  path: '/apps/repos',
  meta: { icon: getIcon(codeRepository), title: '代码仓管理', auth: 'repo_manage', hideChildrenInMenu: true },
  children: [
    { name: 'repos', path: '', component: ReposEntry, meta: { /* 不变 */ } },
    { name: 'reposBranch', path: 'branch', component: ReposEntry, meta: { /* 不变 */ } },
    { name: 'reposBranchUtCoverage', path: 'branch/ut-coverage', component: ReposEntry, meta: { /* 不变 */ } },
    { name: 'reposBranchUtCoverageHistory', path: 'branch/ut-coverage-history', component: ReposEntry, meta: { /* 不变 */ } },
    { name: 'reposBranchCodeMetrics', path: 'branch/code-metrics', component: ReposEntry, meta: { /* 不变 */ } },
    { name: 'reposBranchCodeMetricsHistory', path: 'branch/code-metrics-history', component: ReposEntry, meta: { /* 不变 */ } },
  ],
}
```

`src/router/routes/modules/noMenu.ts`：

```ts
{ name: 'repoOperationLog', path: '/apps/repoOperationLog', component: ReposEntry, meta: { /* 不变 */ } }
```

要点：

- **`ReposEntry` 是唯一入口**：7 条路由的 `component` 只能写 `ReposEntry`；`WujieMiddleware` 由 `ReposEntry` 在开关命中时渲染。§8.2 引用本表，不允许再写第二套路由配置。
- `meta.url` / `meta.assets` 写在路由上：`meta.url` = `${VITE_APP_OPENLIBING_URL}` + 2.7 表中对应子应用 path，`meta.assets` 统一为 `${VITE_APP_OPENLIBING_URL}/repos/`；旧实现分支不读取这两个字段。
- `meta.auth` 保留，菜单权限仍由宿主判定；子应用内操作权限仍由 `useAppStore` 拉取，二者不互相替代。
- **appName 必须先归一**：当前 `WujieMiddleware.resolveWujieAppName` 默认返回 `route.name`，7 条路由会生成 7 个 wujie 实例，切路由时子应用反复重建。P4 前必须增加前缀归一（`/apps/repos`、`/apps/repoOperationLog` → 统一 `repos`），之后才成立"同一实例内只换 `wujieRoute`"。
- 宿主 `WujieMiddleware` 需要支持 `meta.url` 变化时下发 `mainRouteChange`（cicd-web 已具备的形式），Repos 直接复用。

### 2.7 子应用路由与宿主路由映射

```ts
// src/router/index.ts
const router = createRouter({
  history: createWebHistory("/repos/"),
  routes: [
    { path: "/", redirect: "/repo" },
    {
      path: "/repo",
      name: "repos",
      component: () => import("@/views/repo/index.vue"),
    },
    {
      path: "/branch",
      name: "reposBranch",
      component: () => import("@/views/repo/index.vue"),
    },
    {
      path: "/branch/ut-coverage",
      name: "reposBranchUtCoverage",
      component: () => import("@/views/repo/index.vue"),
    },
    {
      path: "/branch/ut-coverage-history",
      name: "reposBranchUtCoverageHistory",
      component: () => import("@/views/repo/index.vue"),
    },
    {
      path: "/branch/code-metrics",
      name: "reposBranchCodeMetrics",
      component: () => import("@/views/repo/index.vue"),
    },
    {
      path: "/branch/code-metrics-history",
      name: "reposBranchCodeMetricsHistory",
      component: () => import("@/views/repo/index.vue"),
    },
    {
      path: "/operation-log",
      name: "repoOperationLog",
      component: () => import("@/views/repo/OperationLog.vue"),
    },
    { path: "/:pathMatch(.*)*", redirect: "/repo" },
  ],
});
```

> **子应用路由 `name` 必须与宿主完全同名**。`index.vue` 内部有 6 处 `router.replace({ name: 'reposBranch' })` 这类写法（[index.vue#L184-L189](file:///d:/openlibing/openlibing-web/apps/web-openlibing/src/views/Repos/index.vue#L184-L189)），子应用沿用同名后这些调用无需改动；若改名，分支管理、UT 详情、度量详情、历史记录之间的跳转与刷新全部失效。

| 宿主要求                                  | 子应用响应（name → path）                                        |
| ----------------------------------------- | ---------------------------------------------------------------- |
| `/apps/repos`                             | `repos` → `/repo`                                                |
| `/apps/repos/branch`                      | `reposBranch` → `/branch`                                        |
| `/apps/repos/branch/ut-coverage`          | `reposBranchUtCoverage` → `/branch/ut-coverage`                  |
| `/apps/repos/branch/ut-coverage-history`  | `reposBranchUtCoverageHistory` → `/branch/ut-coverage-history`   |
| `/apps/repos/branch/code-metrics`         | `reposBranchCodeMetrics` → `/branch/code-metrics`                |
| `/apps/repos/branch/code-metrics-history` | `reposBranchCodeMetricsHistory` → `/branch/code-metrics-history` |
| `/apps/repoOperationLog`                  | `repoOperationLog` → `/operation-log`                            |

`App.vue` 维护 `hostRouteMap`（上表 7 条，双向映射），路由变化时 `bus.$emit('switch-tab', { name, path, query })`，与 cicd-web 一致。

### 2.8 标签页与项目切换适配

原 `index.vue` 的两处宿主耦合：

1. 读取 `useTabbarStore().tabs`，在切项目时清理其它标签页里的 `metrics` / `branch` 旧 query；
2. `useTabbarStore().addTab` 更新当前 Repos 标签页的 query。

迁移后：

- 读取改为 `getHostTabs()`（来自 `props.tabbar.tabs`，宿主已持续同步）；
- 写入改为 `upsertHostTab({ name: hostName, path: hostPath, query })`，`hostName` / `hostPath` 由当前子应用路由按 2.7 映射表反查（6 个仓库路由 + `repoOperationLog`），再由宿主 `handleAddRouteTab` 走 `tabbarStore.addTab` upsert；
- 原逻辑按 6 个仓库路由 name 遍历清理其他标签页 query 的行为保持不变（[index.vue#L514-L535](file:///d:/openlibing/openlibing-web/apps/web-openlibing/src/views/Repos/index.vue#L514-L535)），只把读取来源从 `useTabbarStore` 换成 `getHostTabs()`；
- 独立运行（无宿主）时：`upsertHostTab` 降级为本地 `router.replace({ query })`；`navigateToHost` 返回 `false`，调用方提示或禁用入口（4 个跨应用目标在子应用内没有对应路由，不能盲跳）；
- 项目切换仍以 `bus.$on('projectInfoChange')` 为主入口，`useAppStore.projectInfo` 同步后触发筛选重置与列表刷新。

### 2.9 鉴权时序

沿用 cicd-web 方案：

1. `App.vue` 挂载后调用 `/operation-permission` 拉取 `operationPermissions`；
2. 首屏路由渲染等待 `operationPermissionReady`，避免按钮级权限闪烁；
3. `NoPermissionPopover` 的申请引导链路由宿主权限元数据生成，子应用只做展示与跳转；
4. 请求仍带 cookie（`withCredentials`），token 刷新由网关/宿主统一处理。

## 3. 类设计

无新增后端类。前端新增一层适配与拆分模块：

```text
api/repo/*            # 纯函数模块：入参 -> ApiClient 调用
wujie/host.ts         # 宿主能力门面（isInWujie / navigateToHost / upsertHostTab）
ReposEntry.vue        # 宿主侧分流入口：shouldUseSubapp 纯函数 + 新旧组件切换
stores/app.ts         # 与 cicd-web 同源：projectInfo / operationPermissions / hasOperationPermission
stores/exportTask.ts  # 导出任务轮询（从宿主迁移）
hooks/useMainContentHeight.ts  # 内容区高度：宿主 CSS 变量优先，失败时用视口计算兜底
```

不改动 `Repos/index.vue` 内部的组件拆分粒度（本期只做迁移，不做子组件化重构），避免"迁移 + 重构"叠加导致回归定位困难。

## 4. 数据模型设计

无新增数据结构、无数据库变更。

前端关键状态：

| 状态                   | 来源                                        | 说明                                                           |
| ---------------------- | ------------------------------------------- | -------------------------------------------------------------- |
| `projectInfo`          | 宿主 props / `projectInfoChange`            | `{ projectId, projectName, ... }`                              |
| `operationPermissions` | 子应用自拉取                                | 按钮级权限集合，按运营/项目维度                                |
| 路由 query             | 宿主 `wujieRoute` + 子应用 `router.replace` | `repoId` / `platform` / `branch` / `metrics` 等既有字段不变    |
| `exportTask`           | 子应用 store                                | 导出任务 id 与轮询状态；由宿主 `host-export-task` 事件承接下载 |
| 列配置 / 筛选缓存      | `localStorage`                              | key 增加 `repos:` 前缀，避免与宿主旧 key 冲突                  |

**兼容要求**：旧 key 在首次加载时读取一次并迁移到 `repos:` 新 key；**窗口期内不删除旧 key**（保留只读至少一个版本周期），保证 §8 L1/L2/L3 任一回滚后旧页面可正常读取原配置。旧 key 的删除统一放到 P5 清理阶段，与 §8.5 保持一致。

## 5. 性能设计

| 项           | 措施                                                                                                                                                          |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 宿主减负     | `views/Repos` 整块移出后，宿主对应 chunk（`index.vue` 6,660 行 / 约 232 KB 源码）不再进入主包；回滚窗口内旧组件以异步 chunk 形式保留，只有命中旧实现时才加载  |
| 子应用首屏   | 路由级懒加载；`index.vue` 内部重组件（`JsonDiffViewer`、`DuplicationCodeDrawer`、`MetricsDetailDialog`、`UtCoverageDetailDialog`）保持 `defineAsyncComponent` |
| CodeMirror   | 仅重复代码抽屉使用，独立 manualChunks，避免进入首屏                                                                                                           |
| wujie 预加载 | 宿主在菜单 hover/进入首页空闲时 `preloadApp`，降低首次进入白屏                                                                                                |
| 缓存         | 静态资源 `immutable` 长缓存，`index.html` 不缓存；与 cicd-web nginx 策略一致                                                                                  |
| 请求         | 沿用现有分页与防抖；迁移不新增串行请求                                                                                                                        |

## 6. API 接口设计

前端只消费，无后端改动。迁移后接口按域拆分，共 **61 个函数**（统计口径：`views/Repos/**` 实际 import 的 `api/api.ts` 去重函数 41 个 + `api/Repos/api.ts` 导出 20 个）：

| 域                             | 数量 | 代表接口                                                                                                               | 迁移目标                                 |
| ------------------------------ | ---- | ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| 仓库（`api/api.ts`）           | 16   | `queryRepo`、`addRepo`、`updateRepo`、`batchDeleteRepo`、`setRepoWebhook`、`queryProjectRepoUrlListAxios`              | `api/repo/repo.ts`                       |
| 分支                           | 11   | `queryRepoBranch`、`addRepoNewBranchAxios`、`checkBranchNameAxios`、`scaAddVersionScan`                                | `api/repo/branch.ts`                     |
| 成员 / 角色                    | 9    | `getRepoUser`、`addRepoUser`、`getCommunityRoleList`、`getGitcodeRoleMappingAxios`                                     | `api/repo/member.ts`、`api/repo/role.ts` |
| 标签                           | 2    | `getApplyRepoListAxios`、`addRepoNewTag`                                                                               | `api/repo/tag.ts`                        |
| 扫描 / 基线                    | 2    | `getInterfaceScanResult`、`postInterfaceBaseline`                                                                      | `api/repo/scan.ts`                       |
| 日志                           | 1    | `getOperationLogDetail`                                                                                                | `api/repo/log.ts`                        |
| 仓库扩展（`api/Repos/api.ts`） | 20   | `syncRepos`、`querySyncProgress`、`fileDetail`、`duplicationBlockDetail`、`getGlobalConfig`、`getRepoOperationLogList` | `api/repo/api.ts`                        |

约束：

- 所有 URL 统一收敛到 `api/repo/url.ts`，禁止在页面内拼字符串；
- `ApiClient` 与 cicd-web 同源，错误提示、`traceId`、登录失效跳转行为保持一致；
- 导出类接口（`exportRepo`、`submitUtOriginalReportExport`）返回任务 id 后走 `exportTask` 轮询，下载由宿主事件完成。

## 7. 安全设计

| 风险         | 现状                                                  | 迁移措施                                                          |
| ------------ | ----------------------------------------------------- | ----------------------------------------------------------------- |
| 仓库地址外链 | 使用 `safeOpen` / `validateSafeUrl` / `isTrustDomain` | 原样迁移这些工具函数，**不得简化**                                |
| Token 输入   | `TokenCompositeInput` + `tokenPermission.ts`          | 原样迁移；不回显、不落 `localStorage`、不进日志                   |
| 跨应用跳转   | 直接 `router.push` 宿主 name                          | 收敛到 `navigateToHost` + 白名单，禁止拼接任意 URL                |
| 权限绕过     | 宿主 `meta.auth` + 子应用 `operationPermissions`      | 双层保留；子应用不信任 URL 上的 `repoId`，以接口鉴权为准          |
| XSS          | 富文本/JSON 详情                                      | 详情仍走 `parseJsonSafely` + 文本渲染，禁止 `v-html` 新增使用     |
| 会话         | cookie 同域                                           | 子应用与宿主同域部署（`/repos/`），沿用 cookie；不新增 token 存储 |
| 第三方依赖   | CodeMirror / Element Plus                             | 版本与宿主对齐，新增依赖需过许可证与漏洞检查                      |

## 8. 回滚设计（一键回滚）

### 8.1 回滚分层

| 层级                  | 手段                                                                  | 生效时间       | 适用场景                                 | 是否改宿主       |
| --------------------- | --------------------------------------------------------------------- | -------------- | ---------------------------------------- | ---------------- |
| L1 菜单权限开关（主） | 用「菜单管理」里的一条权限标识控制「旧 Repos 组件 / WujieMiddleware」 | 用户刷新后生效 | 子应用页面异常、回归未通过、灰度指标恶化 | 不改代码、不发版 |
| L2 子应用版本回滚     | K8s `rollout undo` 或发布平台回退上一镜像                             | 3–5 分钟       | 子应用某次发布引入缺陷，但路由形态正常   | 不改宿主         |
| L3 单用户兜底         | `localStorage` 强制走旧组件                                           | 刷新后立即     | 权限变更未生效、个别用户被阻断           | 不改代码         |

三层互不依赖：L1 失效时用 L2，L2 仍无法恢复时用 L3 让用户先可用。

### 8.2 L1：菜单权限开关实现

复用宿主已有的「菜单管理 + 角色管理」权限体系，不新增配置平台、不依赖 K8s ConfigMap：

1. 在「菜单管理」(`/manageCenter/menuManagement`) 新增一条记录：名称与旧菜单**同名**「代码仓管理」、类型「按钮」、标识 `repos_subapp`，挂在「仓库管理」下。**它不是新菜单**——不生成路由、不产生导航项，本质是一个临时开关标识；同名只是为了运营侧能对口识别"切哪条即切实现"。
2. 在「角色管理」给需要走新实现的角色授予该权限。
3. 前端 `app.user.permissions` 由 `GET /user/get-operation-permissions` 下发，包含当前用户已授权的全部 `identification`。

宿主新增一个入口包装组件，7 条路由都指向它（配置见 2.6，此处不重复）：

```ts
// src/utils/reposSubappSwitch.ts
/** 纯函数，便于单测：localStorage 覆盖 > 菜单授权 > 默认旧实现 */
export function shouldUseSubapp(source: {
  localOverride?: string | null;
  permissions?: unknown;
}) {
  if (source.localOverride === "0") return false;
  const perms = source.permissions;
  if (!Array.isArray(perms)) return false;
  return perms.includes("repos_subapp");
}
```

```ts
// src/views/ReposEntry.vue
import { computed, defineAsyncComponent } from "vue";
import { useRoute } from "vue-router";

import { useAppStore } from "@/stores/app";
import { shouldUseSubapp } from "@/utils/reposSubappSwitch";

const WujieMiddleware = () => import("@/views/WujieMiddleware.vue");
// 旧组件必须异步加载：静态 import 会把 232 KB 旧代码绑进路由 chunk，
// 命中新实现的用户也要下载，回滚窗口内的宿主减负收益直接归零。
const LegacyRepos = defineAsyncComponent(
  () => import("@/views/Repos/index.vue"),
);
const LegacyOperationLog = defineAsyncComponent(
  () => import("@/views/Repos/operationLog.vue"),
);

const route = useRoute();
const app = useAppStore();
const useSubapp = computed(() =>
  shouldUseSubapp({
    localOverride: localStorage.getItem("reposSubapp"),
    permissions: (app.user as any)?.permissions,
  }),
);
const Legacy = computed(() =>
  route.name === "repoOperationLog" ? LegacyOperationLog : LegacyRepos,
);
const target = computed(() =>
  useSubapp.value ? WujieMiddleware : Legacy.value,
);
```

```vue
<template>
  <component :is="target" />
</template>
```

> `localStorage` 不是响应式源，`useSubapp` 只在 `permissions` 变化时重算，因此 L3 兜底必须刷新页面才生效（与 §8.3 操作一致），§8.1 已按此修正。

约束：

- **不要复用 `repos` 路由自身的 `meta.auth`（`repo_manage`）做开关**。权限守卫是无权限即拦截路由，取消它会连旧页面一起挡掉。
- **不要写成 `perms.length === 0 || includes(...)`**。路由守卫的「空即放行」是"没权限数据别挡人"，而开关的语义是"没授权就别上"：一旦权限接口失败或返回空列表，宽松写法会永远停留在新实现，取消授权无法回退。默认值必须是旧实现。
- 权限标识只用于 `ReposEntry` 内部判定，不写入任何路由的 `meta.auth`。
- **`repos_subapp` 不替代 `repo_manage`，两者必须成对授权**。路由能否进入仍由 `meta.auth = repo_manage` 决定（`guard.ts` 中 `permissions.includes(to.meta.auth)`）；只授 `repos_subapp` 而不授 `repo_manage`，用户会被守卫拦在路由外，表现为"页面打不开"而非"回滚到旧实现"。灰度检查清单需同时核对两个标识。
- **不要把两者做成"或"门票**（改守卫支持 `meta.auth` 数组，或为 `repo_manage` 加 `|| repos_subapp` 特例）。原因有二：① 守卫是全站安全边界，为单个业务域加硬编码分支，回归面与评审成本都不划算；② 一旦 `repos_subapp` 能当门票，灰度期"未授权"就从"回旧实现"变成"完全进不去"，回滚语义被破坏。`repo_manage` 是代码仓域的功能权限，与新旧实现无关，P5 之后也应继续保留，不需要迁移门票。
- 菜单记录只有 `menuName / identification / menuType / parentId`，没有 path 或 component。宿主 `preferences.app.accessMode` 为 `'frontend'`（`packages/@core/preferences/src/config.ts`，应用未覆盖），路由由 `generateRoutesByFrontend` 从 `router/routes/modules` 静态表按角色过滤生成，`fetchMenuListAsync` 在该分支不会被调用。因此**无法通过"新建一条同名菜单指向子应用"直接切换页面**：菜单只承担权限开关，选路由仍由 `ReposEntry` 判断。用户侧菜单名称保持不变。

路由配置**只以 2.6 为准**：7 条路由的 `component` 均为 `ReposEntry`，此处不再重复示例，避免出现第二套配置。

`ReposEntry` 内部按当前路由 `name` 选择旧组件：6 个仓库路由（`repos` / `reposBranch` / `reposBranchUtCoverage` / `reposBranchUtCoverageHistory` / `reposBranchCodeMetrics` / `reposBranchCodeMetricsHistory`）走 `index.vue`，`repoOperationLog` 走 `operationLog.vue`；新实现统一走 `WujieMiddleware`，仍从路由 `meta.url` / `meta.assets` 取值，因此两套实现共用同一份路由配置。

开关来源与优先级：

```text
localStorage.reposSubapp = '0'（单用户应急，最高）
  > permissions.includes('repos_subapp')（菜单 + 角色授权，主开关）
  > 代码默认值（未授权 / permissions 为空时，默认走旧实现）
```

- `permissions` 为空或接口未就绪时**默认走旧实现**：宁可灰度没生效，也不能让"取消授权"失效；
- 代价是灰度初期必须先确认 `/user/get-operation-permissions` 正常工作，否则会误判成"没授权"；
- 权限在 `Content.vue` 中 `projectId` 就绪后拉取，变更后需用户刷新页面重新获取；
- 切换到关闭时，旧组件与旧 API 必须仍在宿主包内（P5 前不删除）。

### 8.3 运维操作

| 方式       | 操作                                                               | 说明                                                                                 |
| ---------- | ------------------------------------------------------------------ | ------------------------------------------------------------------------------------ |
| 全量回滚   | 「角色管理」取消所有角色的 `repos_subapp` 授权（或删除该菜单记录） | 用户刷新后回到旧实现，不改代码、不改标识；多角色时需逐个取消，删除记录会丢失角色绑定 |
| 按角色回滚 | 「角色管理」取消部分角色的 `repos_subapp` 授权                     | 灰度回退，只影响所选角色                                                             |
| 单用户应急 | `localStorage.setItem('reposSubapp', '0')` 后刷新                  | 仅影响当前浏览器；恢复用 `removeItem`                                                |

L2 回滚命令：

```bash
kubectl -n <ns> rollout undo deployment/openlibing-repos-web
kubectl -n <ns> rollout status deployment/openlibing-repos-web
```

### 8.4 触发条件

满足任一条件即执行 L1 回滚，不等待定位根因：

| 指标                  | 阈值                                     |
| --------------------- | ---------------------------------------- |
| 前端 JS 错误率        | > 1%，持续 5 分钟                        |
| 子应用加载失败 / 白屏 | > 0.5%                                   |
| 首屏 P95              | > 3s，持续 10 分钟                       |
| 阻断性功能异常        | 仓库列表、同步、成员管理、权限任一不可用 |

### 8.5 可回滚窗口与数据兼容

- **窗口**：P4 切流开始至 P5 清理之前，建议不少于一个发布周期；P5 删除旧代码后仅保留 L2。
- **P5 必须改代码，不能靠菜单下线**：宿主为前端静态路由（`accessMode: 'frontend'`），菜单只下发权限标识、不决定组件；"下掉旧菜单"只会收回 `repo_manage` 连带挡住新页面。P5 分三次动作，顺序不可颠倒：
  1. 发一版宿主：7 条路由的 `component` 由 `ReposEntry` 改为直连 `WujieMiddleware`，移除分流逻辑与 `LegacyRepos` 引用，旧文件暂留；
  2. 观察满一个完整发布周期，确认无需回滚后，再单独发一版删除旧代码文件；
  3. 最后清理 `repos_subapp` 菜单记录与角色授权，`repo_manage` 保留。
- **不可逆点**：第 2 步删除旧文件后 L1 开关即失效，只剩 L2 镜像回滚与宿主版本回退。因此"切直连"与"删文件"必须拆成两次交付。

**P5 需要改动的清单**（宿主 `openlibing-web/apps/web-openlibing/src`）：

| #   | 对象                                                                                                                                                                           | 动作                                                                                                  | 注意                                              |
| --- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| 1   | `router/routes/modules/menu.ts` 中 6 条仓库路由、`noMenu.ts` 中 `repoOperationLog`                                                                                             | `component` 由 `ReposEntry` 改为 `WujieMiddleware`，按 2.7 映射表补各路由 `meta.url` 与 `meta.assets` | `meta.auth` 保持 `repo_manage` 不变               |
| 2   | `views/ReposEntry.vue`                                                                                                                                                         | 删除                                                                                                  | 分流判断、`localStorage.reposSubapp` 读取一并移除 |
| 3   | `views/Repos/**`（21 个非测试文件 + 2 个单测）                                                                                                                                 | 删除                                                                                                  | 删前 `rg` 确认无其他引用                          |
| 4   | `api/api.ts` 中 41 个 Repos 函数、`api/Repos/{api,url}.ts`                                                                                                                     | 删除                                                                                                  | 先确认其他业务域未复用同名函数                    |
| 5   | `stores/exportTask.ts`、`hooks/useExportTaskSubmit.ts`、`hooks/useVbenMainContentHeight.ts`、`utils/until.ts` 中 Repos 专用函数、`constants/permissions-meta.ts` 中 Repos 条目 | 按引用情况删除或保留                                                                                  | 仍被其他域使用的必须保留，不能整文件删            |
| 6   | `views/WujieMiddleware.vue` 的 `resolveWujieAppName`                                                                                                                           | P4 前已完成 `/apps/repos`、`/apps/repoOperationLog` 前缀归一为 `repos`；P5 只做校验                   | 未归一则 7 条路由各自实例化，切换时子应用反复重建 |
| 7   | 菜单管理 `repos_subapp` 记录与各角色授权                                                                                                                                       | 删除                                                                                                  | `repo_manage` 保留，禁止删                        |
| 8   | 宿主单测 `views/Repos/dialog/__tests__/*.spec.ts`                                                                                                                              | 迁移至子应用仓并从宿主删除                                                                            | 避免宿主覆盖率被已迁代码拖低                      |

**验证项**：`rg` 引用清零 → 构建通过 → 主包体积对比 P0 基线 → 7 条路由可进、5 条深链子路由刷新可用、标签页与跨应用跳转正常 → 移除 `repo_manage` 的角色仍被正确拦到无权限页。

### 8.6 演练与验证

1. P4 灰度前在 beta 演练一次 `开 → 关 → 开`，记录配置同步与页面生效时延；
2. 回滚后逐项验证：旧列表加载、查询筛选、同步、成员管理、按钮权限、操作日志、标签页 query；
3. 记录回滚时间、操作人、触发指标与结论，纳入发布报告；
4. 若 L1 回滚后问题仍存在，说明缺陷在宿主或后端，转 L2/常规故障流程。

## 影响范围

| 维度         | 说明                                                                                                 |
| ------------ | ---------------------------------------------------------------------------------------------------- |
| 宿主路由     | 7 条路由（6 条仓库 + 1 条操作日志）的 `component/meta.url/meta.assets` 变化，`name/path/auth` 不变   |
| 宿主构建     | `views/Repos`、`api/Repos`、`api/api.ts` 中 Repos 段、`stores/exportTask` 可下线，主包减小           |
| 宿主公共组件 | `ContactInformation`、`BatchAddMemberDialog` 复制到新仓，宿主侧在确认无其他引用后删除                |
| 跨应用跳转   | 检测中心 / 接口管理 / 代码检查 / 项目管理 4 个目标页需验证从子应用跳转正常                           |
| 标签页       | 切项目时的 query 清理逻辑改由 bus upsert 实现，需回归"多标签 + 切项目"场景                           |
| 部署         | 新增 1 个前端服务与 1 个 nginx location，不改变网关与后端                                            |
| 双仓同步     | 公共组件（CategorySearch / DateRangePicker / NoPermissionPopover）与 cicd-web 保持同源，缺陷需双仓修 |

## 验证方式

1. **工程可独立运行**：`pnpm dev`（5175）在无宿主环境下可打开 `/repos/repo`，不出 wujie 相关报错；4 个跨应用入口可见但点击给出明确提示（不得静默无响应）。
2. **宿主集成**：7 条路由（含 5 条深链子路由）正常加载，标签页标题/图标/query 保持；刷新、前进后退、深链可用。
3. **功能回归清单**：仓库列表查询/筛选/排序/分页/列配置、同步与进度、新增/编辑/删除、分支管理、标签管理、成员与角色映射、全局配置、重复代码抽屉、UT 覆盖率、指标详情、接口扫描结果、操作日志与详情。
4. **权限回归**：无权限按钮展示 `NoPermissionPopover` 与申请引导；切换项目后权限与数据同步刷新。
5. **跨应用跳转**：4 个目标页跳转均落到宿主对应路由，且携带 query 正确。
6. **构建与部署**：`pnpm build` 产物 `base=/repos/`；nginx `location /repos` 下静态资源与 `assets` 重写正常；三环境部署可访问。
7. **质量门禁**：迁移后的 2 个单测通过；新增 `host.ts` 适配层单测；新增 `shouldUseSubapp` 纯函数单测（覆盖 `localStorage='0'` 覆盖、已授权、未授权、`permissions=[]` 四种情况）；`navigateToHost` 非白名单 name 必须返回 `false`；lint 无新增 error。
8. **对比验证**：迁移前后对同一项目分别执行同一组操作，接口请求参数与页面结果一致。
