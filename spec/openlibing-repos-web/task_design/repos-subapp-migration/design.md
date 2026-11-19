# 代码仓管理（Repos）模块独立子工程迁移 — design

> 状态：设计稿（待评审）
> 目标仓库（新建）：`openlibing-repos-web`
> 参考实现：`openlibing-cicd-web`（已独立部署的 wujie 子应用）
> 宿主：`openlibing-web/apps/web-openlibing`

## 1. 方案设计

### 1.1 背景

`web-openlibing` 中的 `src/views/Repos` 已演化成"代码仓管理"完整业务域：仓库列表/同步、分支管理、标签管理、仓库成员、角色映射、全局配置、重复代码、UT 覆盖率、指标详情、接口扫描结果、操作日志。该模块共 **21 个文件、15,659 行代码**，其中 `index.vue` 单文件 **215 KB**，且与宿主的路由、鉴权 store、标签页 store、公共组件、单体 API 文件强耦合。

继续留在宿主内会导致：

- 宿主主包与首屏体积持续膨胀，构建与热更新变慢；
- 代码仓域与流水线域（`openlibing-cicd-web`）职责边界不清，发布节奏互相牵制；
- 单体 `api/api.ts` 被两个业务域共同修改的概率上升，冲突面扩大。

### 1.2 目标与非目标

**目标**

1. 新建独立前端仓 `openlibing-repos-web`，把 `views/Repos` 全量迁出，按 `openlibing-cicd-web` 的工程形态承载。
2. 以 wujie 微前端方式挂在宿主 `/apps/repos`、`/apps/repoOperationLog` 两个路由下，**对外 URL 与路由 name 保持不变**。
3. 宿主与子应用通过 `app / tabbar / wujieRoute` props 与 wujie bus 通信，子应用可独立开发、构建、部署。
4. 迁移后功能、权限、埋点、导出、跳转行为与迁移前一致。

**非目标**

- 不改后端接口契约，不做代码仓域的功能重构或 UI 改版。
- 不迁移代码仓后端仓（`openlibing-coderepo`），仅前端。
- 不在本期合并 `openlibing-web` 与 `openlibing-cicd-web` 的公共组件仓（公共层先复制 + 双仓同步，后续再抽包）。

### 1.3 关键结论

| 结论       | 说明                                                                           |
| ---------- | ------------------------------------------------------------------------------ |
| 迁移形态   | 完全对齐 `openlibing-cicd-web`：Vue 3 + Vite + wujie 子应用，`base: '/repos/'` |
| 宿主改动   | 仅 2 个路由改为 `WujieMiddleware`，`name` / `path` / `meta.auth` 不变          |
| 主要工作量 | 60 个 API 函数抽取、7 个公共组件/工具迁移、5 处跨应用跳转改造、标签页适配      |
| 最大风险   | 宿主标签页与项目切换的联动（`useTabbarStore` 不可跨应用直接写）                |
| 回滚方式   | 菜单权限开关切回旧组件，旧代码在验收期内不删除                                 |

## 2. 实现逻辑设计

### 2.1 目标架构

```text
┌─────────────────────────────── openlibing-web（宿主） ───────────────────────────────┐
│  菜单 / 标签页 / 项目切换 / 登录态 / 权限菜单                                          │
│  /apps/repos            -> WujieMiddleware  app="repos"  url="/repos/repo"            │
│  /apps/repoOperationLog -> WujieMiddleware  app="repos"  url="/repos/operation-log"    │
│            │ props: app / tabbar / wujieRoute / wujieAppName                           │
│            │ bus  : projectInfoChange / switch-tab / add-route-tab / host-router ...    │
└────────────┼───────────────────────────────────────────────────────────────────────────┘
             │  wujie（iframe + proxy + shadow DOM）
┌────────────▼───────────────────── openlibing-repos-web ──────────────────────────────┐
│  base: /repos/    dev: 5175    nginx location /repos                                 │
│  views/repo/index.vue          （仓库管理，原 Repos/index.vue）                        │
│  views/repo/OperationLog.vue   （操作日志，原 Repos/operationLog.vue）                  │
│  api/repo/*                    （60 个接口按域拆分）                                   │
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
│   │       ├── api.ts        # 原 api/Repos/api.ts（18 个）
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
│   └── wujie/host.ts         # 宿主通信适配层（见 2.5）
└── tests/unit/               # 迁移后的 2 个 spec + 适配层单测
```

### 2.3 代码迁移映射

| 原路径（`web-openlibing/src`）                              | 新路径（`openlibing-repos-web/src`）                 | 处理方式                                                  |
| ----------------------------------------------------------- | ---------------------------------------------------- | --------------------------------------------------------- |
| `views/Repos/index.vue`                                     | `views/repo/index.vue`                               | 直接迁移；tabbar / 跨应用跳转 / 高度 hook 改造            |
| `views/Repos/branches.vue`                                  | `views/repo/components/Branches.vue`                 | 业务组件下沉；跨应用跳转改造                              |
| `views/Repos/operationLog.vue`                              | `views/repo/OperationLog.vue`                        | 转为子应用路由 `/operation-log`                           |
| `views/Repos/repoUserManage.vue`                            | `views/repo/components/RepoUserManage.vue`           | 依赖 `ContactInformation`、`BatchAddMemberDialog`         |
| `views/Repos/tagManagement.vue`                             | `views/repo/components/TagManagement.vue`            | 直接迁移                                                  |
| `views/Repos/roleMappingDialog.vue`                         | `views/repo/components/RoleMappingDialog.vue`        | 直接迁移                                                  |
| `views/Repos/scanResultDialog.vue`                          | `views/repo/components/ScanResultDialog.vue`         | 直接迁移                                                  |
| `views/Repos/dialog/*.vue`                                  | `views/repo/dialog/*.vue`                            | 6 个弹窗；`DuplicationCodeDrawer` 保留 CodeMirror 依赖    |
| `views/Repos/components/*.vue`                              | `views/repo/components/*.vue`                        | `ColumnFilter` / `JsonDiffViewer` / `TokenCompositeInput` |
| `views/Repos/useSigSync.ts`                                 | `views/repo/composables/useSigSync.ts`               | 直接迁移                                                  |
| `views/Repos/dialog/__tests__/*.spec.ts`                    | `tests/unit/*.spec.ts`                               | 路径与 alias 调整                                         |
| `api/Repos/{api,url}.ts`                                    | `api/repo/{api,url}.ts`                              | 18 个接口原样迁移                                         |
| `api/api.ts`（Repos 相关 42 个）                            | `api/repo/{repo,branch,member,tag,scan,role,log}.ts` | 按域拆分，URL 从 `api/url.ts` 收敛                        |
| `stores/exportTask.ts`                                      | `stores/exportTask.ts`                               | 依赖宿主 `extractExportId`，需一并迁移                    |
| `hooks/useExportTaskSubmit.ts`                              | `hooks/useExportTaskSubmit.ts`                       | 改为走宿主导出事件                                        |
| `hooks/routerActive.js`                                     | `hooks/useRouteActive.ts`                            | 补类型                                                    |
| `hooks/useVbenMainContentHeight.ts`                         | `hooks/useMainContentHeight.ts`                      | 去掉 vben 依赖，改为宿主高度变量 + 兜底计算               |
| `utils/until.ts`（部分）                                    | `utils/{repoUrl,notice,link}.ts`                     | `isTrustDomain` / `validateSafeUrl` / `safeOpen` 必须保留 |
| `majun/src/utils/common.ts`（`formatLanguage`）             | `utils/formatLanguage.ts`                            | 单独抽出                                                  |
| `components/ContactInformation.vue`                         | `components/ContactInformation.vue`                  | 复制迁移                                                  |
| `components/BatchAddMemberDialog.vue`                       | `components/BatchAddMemberDialog.vue`                | 复制迁移                                                  |
| `components/{BatchOperation,Empty,NoPermissionPopover}.vue` | `components/`                                        | 与 cicd-web 已有实现比对后取同源版本                      |
| `components/{CategorySearch,DateRangePicker}`               | `components/`                                        | 复用 cicd-web 版本，避免第三份副本                        |
| `constants/permissions-meta.ts`                             | `constants/permissionsMeta.ts`                       | 仅保留 Repos 相关条目                                     |

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

/** 跳主应用路由：仅允许白名单 */
export function navigateToHost(target: {
  name?: string;
  path?: string;
  query?: Record<string, any>;
}) {
  if (!isInWujie()) return false;
  hostBus()?.$emit("host-router", target);
  return true;
}

/** 标签页 upsert：替代 useTabbarStore.addTab */
export function upsertHostTab(tab: {
  name: string;
  path: string;
  query?: Record<string, any>;
}) {
  if (!isInWujie()) return;
  hostBus()?.$emit("add-route-tab", tab);
}

/** 读取宿主标签页快照 */
export const getHostTabs = () => hostProps()?.tabbar?.tabs ?? [];
```

跨应用跳转改造点：

| 位置                                        | 原实现                                               | 新实现                                               |
| ------------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------- |
| `index.vue handleShowOperationLog`          | `router.push('/apps/repoOperationLog')`              | `router.push('/operation-log')`（子应用内）          |
| `index.vue goInspection`                    | `router.push({ name: 'inspection' })`                | `navigateToHost({ name: 'inspection', query })`      |
| `index.vue openScanResult`                  | `router.push({ name: 'interfaceManage' })`           | `navigateToHost({ name: 'interfaceManage', query })` |
| `branches.vue 跳代码检查`                   | `router.push({ name: 'codecheck' })`                 | `navigateToHost({ name: 'codecheck', query })`       |
| `branches.vue / ProjectPublicAccountDialog` | `router.push({ name: 'project' })` / `/apps/project` | `navigateToHost({ name: 'project' })`                |

宿主白名单需在 `wujie/host.ts` 内维护：`inspection` / `interfaceManage` / `codecheck` / `project`。

### 2.6 宿主路由改造

`src/router/routes/modules/menu.ts`：

```ts
{
  name: 'repos',                      // 保持不变（PRManage 等处按 name 跳转）
  path: '/apps/repos',                // 保持不变
  component: WujieMiddleware,
  meta: {
    icon: getIcon(codeRepository),
    title: '代码仓管理',
    auth: 'repo_manage',
    url: `${import.meta.env.VITE_APP_OPENLIBING_URL}/repos/repo`,
    assets: `${import.meta.env.VITE_APP_OPENLIBING_URL}/repos/`,
  },
},
```

`src/router/routes/modules/noMenu.ts`：

```ts
{
  name: 'repoOperationLog',
  path: '/apps/repoOperationLog',
  component: WujieMiddleware,
  meta: {
    hideInMenu: true,
    title: '代码仓操作日志',
    noKeepAlive: true,
    url: `${import.meta.env.VITE_APP_OPENLIBING_URL}/repos/operation-log`,
    assets: `${import.meta.env.VITE_APP_OPENLIBING_URL}/repos/`,
  },
},
```

要点：

- `app` name 统一为 `repos`；同一子应用的两个宿主路由复用同一个 wujie 实例 key，切路由只换 `wujieRoute`。
- `meta.auth` 保留，菜单权限仍由宿主判定；子应用内操作权限仍由 `useAppStore` 拉取，二者不互相替代。
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
      path: "/operation-log",
      name: "repoOperationLog",
      component: () => import("@/views/repo/OperationLog.vue"),
    },
    { path: "/:pathMatch(.*)*", redirect: "/repo" },
  ],
});
```

| 宿主要求                 | 子应用响应（name → path）             |
| ------------------------ | ------------------------------------- |
| `/apps/repos`            | `repos` → `/repo`                     |
| `/apps/repoOperationLog` | `repoOperationLog` → `/operation-log` |

`App.vue` 维护 `hostRouteMap`，路由变化时 `bus.$emit('switch-tab', { name, path, query })`，与 cicd-web 一致。

### 2.8 标签页与项目切换适配

原 `index.vue` 的两处宿主耦合：

1. 读取 `useTabbarStore().tabs`，在切项目时清理其它标签页里的 `metrics` / `branch` 旧 query；
2. `useTabbarStore().addTab` 更新当前 Repos 标签页的 query。

迁移后：

- 读取改为 `getHostTabs()`（来自 `props.tabbar.tabs`，宿主已持续同步）；
- 写入改为 `upsertHostTab({ name: 'repos', path: '/apps/repos', query })`，由宿主 `handleAddRouteTab` 走 `tabbarStore.addTab` upsert；
- 独立运行（无宿主）时两个方法降级为本地 `router.replace`，不报错；
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

**兼容要求**：`localStorage` 旧 key 在首次加载时读取一次并迁移到新 key，随后删除旧 key（或保留只读一个版本周期）。

## 5. 性能设计

| 项           | 措施                                                                                                                                                          |
| ------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 宿主减负     | `views/Repos` 整块移出后，宿主对应 chunk（约 215 KB 源码）不再进入主包                                                                                        |
| 子应用首屏   | 路由级懒加载；`index.vue` 内部重组件（`JsonDiffViewer`、`DuplicationCodeDrawer`、`MetricsDetailDialog`、`UtCoverageDetailDialog`）保持 `defineAsyncComponent` |
| CodeMirror   | 仅重复代码抽屉使用，独立 manualChunks，避免进入首屏                                                                                                           |
| wujie 预加载 | 宿主在菜单 hover/进入首页空闲时 `preloadApp`，降低首次进入白屏                                                                                                |
| 缓存         | 静态资源 `immutable` 长缓存，`index.html` 不缓存；与 cicd-web nginx 策略一致                                                                                  |
| 请求         | 沿用现有分页与防抖；迁移不新增串行请求                                                                                                                        |

## 6. API 接口设计

前端只消费，无后端改动。迁移后接口按域拆分，共 **60 个函数**：

| 域                             | 数量 | 代表接口                                                                                                               | 迁移目标                                 |
| ------------------------------ | ---- | ---------------------------------------------------------------------------------------------------------------------- | ---------------------------------------- |
| 仓库（`api/api.ts`）           | 16   | `queryRepo`、`addRepo`、`updateRepo`、`batchDeleteRepo`、`setRepoWebhook`、`queryProjectRepoUrlListAxios`              | `api/repo/repo.ts`                       |
| 分支                           | 11   | `queryRepoBranch`、`addRepoNewBranchAxios`、`checkBranchNameAxios`、`scaAddVersionScan`                                | `api/repo/branch.ts`                     |
| 成员 / 角色                    | 9    | `getRepoUser`、`addRepoUser`、`getCommunityRoleList`、`getGitcodeRoleMappingAxios`                                     | `api/repo/member.ts`、`api/repo/role.ts` |
| 标签                           | 2    | `getApplyRepoListAxios`、`addRepoNewTag`                                                                               | `api/repo/tag.ts`                        |
| 扫描 / 基线                    | 2    | `getInterfaceScanResult`、`postInterfaceBaseline`                                                                      | `api/repo/scan.ts`                       |
| 日志                           | 1    | `getOperationLogDetail`                                                                                                | `api/repo/log.ts`                        |
| 仓库扩展（`api/Repos/api.ts`） | 18   | `syncRepos`、`querySyncProgress`、`fileDetail`、`duplicationBlockDetail`、`getGlobalConfig`、`getRepoOperationLogList` | `api/repo/api.ts`                        |

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
| L3 单用户兜底         | `localStorage` 强制走旧组件                                           | 立即           | 权限变更未生效、个别用户被阻断           | 不改代码         |

三层互不依赖：L1 失效时用 L2，L2 仍无法恢复时用 L3 让用户先可用。

### 8.2 L1：菜单权限开关实现

复用宿主已有的「菜单管理 + 角色管理」权限体系，不新增配置平台、不依赖 K8s ConfigMap：

1. 在「菜单管理」(`/manageCenter/menuManagement`) 新增一条记录：名称「Repos 新子应用」、类型「按钮」、标识 `repos_subapp`，挂在「仓库管理」下。按钮类型不进导航，只作为权限点。
2. 在「角色管理」给需要走新实现的角色授予该权限。
3. 前端 `app.user.permissions` 由 `GET /user/get-operation-permissions` 下发，包含当前用户已授权的全部 `identification`。

宿主新增一个入口包装组件，两个路由都指向它：

```ts
// src/views/Repos/ReposEntry.vue
import WujieMiddleware from "@/views/WujieMiddleware.vue";
import LegacyRepos from "@/views/Repos/index.vue";

const app = useAppStore();
// 单用户应急覆盖 > 权限标识 > 代码默认值（走新实现）
const useSubapp = computed(() => {
  if (localStorage.getItem("reposSubapp") === "0") return false;
  const perms: string[] = (app.user as any)?.permissions || [];
  return perms.length === 0 || perms.includes("repos_subapp");
});
const target = computed(() =>
  useSubapp.value ? WujieMiddleware : LegacyRepos,
);
```

约束：

- **不要复用 `repos` 路由自身的 `meta.auth`（`repo_manage`）做开关**。权限守卫是无权限即拦截路由，取消它会连旧页面一起挡掉。
- 权限标识只用于 `ReposEntry` 内部判定，不写入任何路由的 `meta.auth`。
- 菜单记录只有 `menuName / identification / menuType / parentId`，没有 path 或 component；宿主路由与入口都是静态的，所以无法靠"新增一条菜单指向子应用"直接切页面，菜单只承担开关作用，选路由仍由 `ReposEntry` 判断。用户侧菜单名称保持不变。

```ts
// menu.ts
{ name: 'repos', path: '/apps/repos', component: ReposEntry, meta: { /* 不变 */ } }
// noMenu.ts
{ name: 'repoOperationLog', path: '/apps/repoOperationLog', component: ReposEntry, meta: { /* 不变 */ } }
```

`ReposEntry` 内部按当前路由 `name` 选择旧组件（`index.vue` / `operationLog.vue`）或 `WujieMiddleware`；`WujieMiddleware` 仍从路由 `meta.url` / `meta.assets` 取值，因此两套实现共用同一份路由配置。

开关来源与优先级：

```text
localStorage.reposSubapp = '0'（单用户应急，最高）
  > permissions.includes('repos_subapp')（菜单 + 角色授权，主开关）
  > 代码默认值（permissions 为空时，默认走新实现）
```

- `permissions` 为空视为权限接口未就绪（或超管账号），默认走新实现，避免刷新瞬间闪回旧页面；
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
- **路由与标签页**：`name` / `path` 不变，标签页、深链、收藏无需迁移，回滚不影响已打开页面。
- **localStorage**：新子应用只读旧 key、只写 `repos:` 新 key，窗口期内不删除旧 key；回滚后旧页面照常读取。
- **未提交数据**：回滚需要刷新页面，未提交的表单会丢失，操作前提示用户。
- **不可逆变更**：本期不涉及数据库与接口契约变更，回滚不存在数据修复成本。

### 8.6 演练与验证

1. P4 灰度前在 beta 演练一次 `开 → 关 → 开`，记录配置同步与页面生效时延；
2. 回滚后逐项验证：旧列表加载、查询筛选、同步、成员管理、按钮权限、操作日志、标签页 query；
3. 记录回滚时间、操作人、触发指标与结论，纳入发布报告；
4. 若 L1 回滚后问题仍存在，说明缺陷在宿主或后端，转 L2/常规故障流程。

## 影响范围

| 维度         | 说明                                                                                                 |
| ------------ | ---------------------------------------------------------------------------------------------------- |
| 宿主路由     | `repos`、`repoOperationLog` 两个路由的 `component/meta.url/meta.assets` 变化，`name/path/auth` 不变  |
| 宿主构建     | `views/Repos`、`api/Repos`、`api/api.ts` 中 Repos 段、`stores/exportTask` 可下线，主包减小           |
| 宿主公共组件 | `ContactInformation`、`BatchAddMemberDialog` 复制到新仓，宿主侧在确认无其他引用后删除                |
| 跨应用跳转   | 检测中心 / 接口管理 / 代码检查 / 项目管理 4 个目标页需验证从子应用跳转正常                           |
| 标签页       | 切项目时的 query 清理逻辑改由 bus upsert 实现，需回归"多标签 + 切项目"场景                           |
| 部署         | 新增 1 个前端服务与 1 个 nginx location，不改变网关与后端                                            |
| 双仓同步     | 公共组件（CategorySearch / DateRangePicker / NoPermissionPopover）与 cicd-web 保持同源，缺陷需双仓修 |

## 验证方式

1. **工程可独立运行**：`pnpm dev`（5175）在无宿主环境下可打开 `/repos/repo`，不出 wujie 相关报错。
2. **宿主集成**：`/apps/repos`、`/apps/repoOperationLog` 正常加载，标签页标题/图标/query 保持；刷新、前进后退、深链可用。
3. **功能回归清单**：仓库列表查询/筛选/排序/分页/列配置、同步与进度、新增/编辑/删除、分支管理、标签管理、成员与角色映射、全局配置、重复代码抽屉、UT 覆盖率、指标详情、接口扫描结果、操作日志与详情。
4. **权限回归**：无权限按钮展示 `NoPermissionPopover` 与申请引导；切换项目后权限与数据同步刷新。
5. **跨应用跳转**：4 个目标页跳转均落到宿主对应路由，且携带 query 正确。
6. **构建与部署**：`pnpm build` 产物 `base=/repos/`；nginx `location /repos` 下静态资源与 `assets` 重写正常；三环境部署可访问。
7. **质量门禁**：迁移后的 2 个单测通过；新增 `host.ts` 适配层单测；lint 无新增 error。
8. **对比验证**：迁移前后对同一项目分别执行同一组操作，接口请求参数与页面结果一致。
