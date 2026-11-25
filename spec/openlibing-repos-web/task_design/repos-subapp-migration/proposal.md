# 代码仓管理（Repos）模块拆分独立子应用 — proposal

- 变更目录：`spec/openlibing-repos-web/task_design/repos-subapp-migration/`
- 业务 Issue：https://gitcode.com/openlibing/openlibing-web/issues/433
- 目标仓库（新建）：`openlibing-repos-web`
- 宿主仓库：`openlibing-web/apps/web-openlibing`
- 参考实现：`openlibing-cicd-web`（已独立部署的 wujie 子应用）
- 业务分支：待创建（建议 `feat-repos-subapp-migration`，从 fork 仓推送）
- 流程模式：Full（跨仓 + 跨模块 + 部署与发布链路变化）
- 日期：2026-11-25

## Why

`web-openlibing/src/views/Repos` 已演化成完整的"代码仓管理"业务域：仓库列表与同步、分支管理、标签管理、仓库成员、角色映射、全局配置、重复代码、UT 覆盖率、指标详情、接口扫描结果、操作日志。该模块共 **21 个文件、15,659 行代码**，`index.vue` 单文件 **215 KB**，涉及 **60 个接口**，并与宿主的路由、鉴权 store、标签页 store、公共组件、单体 API 文件强耦合。

继续留在宿主内，问题会持续放大：

1. **主包膨胀**：单模块 1.5 万行常驻主包，宿主构建产物与首屏体积随代码仓业务增长继续变大，构建与热更新变慢，拖累全站开发效率。
2. **发布互相牵制**：代码仓域与主工程共用同一条构建与发布流水线，代码仓的紧急修复必须等主工程发布窗口；主工程每次发布也要回归验证代码仓，两侧节奏绑死。
3. **定位与修复慢**：`index.vue` 单文件 215 KB，接口与全站共用 `api/api.ts` 混排，改动影响面难评估，问题定位与修复成本高，冲突面持续扩大。

以上问题同源——代码仓域与主工程的物理耦合。拆分为独立工程后，发布解耦、问题定位收敛到单域、主包同步减负，属结构性收益。

## What Changes

- **新建独立前端仓 `openlibing-repos-web`**：完全对齐 `openlibing-cicd-web` 的工程形态（Vue 3 + Vite + Pinia + Element Plus），`base: '/repos/'`，dev 端口 5175，nginx `location /repos`，新增 beta / gamma / prod 三条发布流水线。
- **全量迁出页面与业务组件**：`views/Repos` 21 个文件迁至 `views/repo/`；`index.vue` → `views/repo/index.vue`，`operationLog.vue` → `views/repo/OperationLog.vue`（子应用路由 `/operation-log`）。
- **接口按域拆分**：60 个接口从宿主 `api/api.ts` / `api/Repos/*` 迁至 `api/repo/{repo,branch,member,tag,scan,role,log}.ts`，URL 统一收敛到 `api/repo/url.ts`，禁止页面内拼字符串。
- **宿主路由改造**：`repos`、`repoOperationLog` 两条路由的 `component` 改为 wujie 中间件，**`name` / `path` / `meta.auth` 保持不变**；`meta.url` 分别指向 `/repos/repo`、`/repos/operation-log`，`meta.assets` 指向 `/repos/`。
- **宿主通信适配层**：子应用内禁止直接访问 `window.$wujie`，统一经 `wujie/host.ts`（`isInWujie` / `navigateToHost` / `upsertHostTab` / `getHostTabs`），保证独立运行不报错。
- **跨应用跳转收敛**：检测中心、接口管理、代码检查、项目管理 4 个目标页由 `router.push` 改为 `navigateToHost` + 白名单。
- **标签页适配**：读取改为宿主 props 的标签页快照，写入改为 bus `add-route-tab` upsert，不再跨应用直接写 `useTabbarStore`。
- **公共依赖策略**：`CategorySearch` / `DateRangePicker` 复用 cicd-web 版本；`BatchOperation` / `Empty` / `NoPermissionPopover` 以 cicd-web 为基线取同源版本；`ContactInformation` / `BatchAddMemberDialog` 宿主独有，复制迁移；`safeOpen` / `validateSafeUrl` / `isTrustDomain`、`TokenCompositeInput` 原样迁移，不得简化。
- **一键回滚**：宿主新增 `ReposEntry` 入口包装，按「菜单管理」中同名按钮型权限标识 `repos_subapp` 在旧组件与 wujie 中间件之间分流；未授权 / 权限为空一律回旧实现；另有 K8s 镜像回滚与 `localStorage` 单用户兜底，共三层。
- **P5 下线旧实现**：改代码直连 wujie、单独一版删除旧文件、最后清理 `repos_subapp` 菜单记录与授权（`repo_manage` 保留），三次动作顺序不可颠倒。

## 非目标

- 不改后端接口契约，不做代码仓域的功能重构或 UI 改版。
- 不迁移代码仓后端仓（`openlibing-coderepo`），本期仅前端。
- 不合并 `openlibing-web` 与 `openlibing-cicd-web` 的公共组件仓，公共层先复制 + 双仓同步，后续再抽包。

## Capabilities

### New Capabilities

- `repos-subapp-bootstrap`：新仓工程骨架、构建配置、环境变量、nginx 与三条发布流水线，可独立开发与部署。
- `repos-subapp-host-integration`：宿主两条路由的 wujie 挂载、props 下发、路由映射、标签页 upsert、跨应用跳转白名单。
- `repos-subapp-rollback`：`repos_subapp` 权限开关 + `ReposEntry` 分流的三层回滚能力（菜单授权 / 镜像回滚 / 单用户兜底）。

### Modified Capabilities

- 宿主代码仓路由：`repos`、`repoOperationLog` 的 `component` 与 `meta.url` / `meta.assets` 变化，`name` / `path` / `meta.auth` 不变。
- 宿主标签页交互：切项目时的 query 清理与 upsert 改由 bus 驱动，行为保持一致。
- 宿主构建产物：`views/Repos` 与 Repos 相关 API/工具不再进入主包。

## 验收标准

1. **功能一致**：仓库列表查询 / 筛选 / 排序 / 分页 / 列配置、同步与进度、增删改、分支管理、标签管理、成员与角色映射、全局配置、重复代码抽屉、UT 覆盖率、指标详情、接口扫描结果、操作日志与详情，行为与迁移前一致。
2. **独立运行**：子应用 `pnpm dev`（5175）在无宿主环境可打开 `/repos/repo` 与 `/repos/operation-log`，无 wujie 相关报错。
3. **宿主集成**：`/apps/repos`、`/apps/repoOperationLog` 正常加载；对外 URL、菜单名称、路由 name、标签页标题与 query、刷新 / 前进后退 / 深链均与迁移前一致。
4. **权限回归**：菜单权限仍由宿主 `meta.auth = repo_manage` 判定；按钮级权限由子应用 `/operation-permission` 拉取并展示 `NoPermissionPopover`；切换项目后权限与数据同步刷新。
5. **跨应用跳转**：检测中心、接口管理、代码检查、项目管理 4 个目标页均落到宿主对应路由且 query 正确。
6. **回滚可用**：beta 演练 `开 → 关 → 开` 通过；取消 `repos_subapp` 授权后用户刷新即回旧实现；`kubectl rollout undo` 可回退子应用镜像；`localStorage.reposSubapp='0'` 可单用户兜底。
7. **主包减负**：宿主构建产物主包体积对比 P0 基线有可量化下降。
8. **零后端变更**：接口路径、入参、出参、cookie 会话均不变。

## Impact

- **受影响仓库**：新建 `openlibing-repos-web`；修改 `openlibing-web`（宿主路由、入口包装组件、公共组件引用）；归档 `openlibing-docs`（本 spec 目录）。
- **受影响接口**：无契约变更，仅前端调用位置迁移；仍走 `/gateway` + cookie 会话。
- **部署**：新增 1 个前端服务（4 个 CCE 实例）与 1 个 nginx location `/repos`、3 条发布流水线；网关、后端不变。
- **风险**：
  - 标签页与项目切换联动是最大风险点，需重点回归"多标签 + 切项目"。
  - 公共组件双仓副本（`CategorySearch` / `DateRangePicker` / `NoPermissionPopover`）需同步修缺陷。
  - 回滚开关依赖 `/user/get-operation-permissions` 正常返回，灰度前必须先确认该接口可用。
  - P5 删除旧文件后 L1 开关失效，只剩镜像与宿主版本回退，因此"切直连"与"删文件"必须拆成两次交付。
