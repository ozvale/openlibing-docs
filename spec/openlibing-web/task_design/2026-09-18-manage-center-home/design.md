# 2026-09-18 管理中心首页落地页 - 技术方案

## 1. 总体设计

为 `/manageCenter` 新增独立首页 `/manageCenter/home` 作为 redirect 落地页。页面由 Hero 欢迎区与能力卡片网格两部分组成：Hero 提供问候语与内联 SVG 插画，能力卡片按后台管理业务聚合为 8 大模块入口，并依据路由 `meta.auth` 与用户 permissions 动态过滤。同时升级管理中心左侧菜单的视觉样式。

纯前端改动，无后端接口、数据模型与部署配置变更。

## 2. 关键实现

### 2.1 路由调整（manageRouter.ts）

- 新增子路由 `manageCenterHome`（path: `/manageCenter/home`，meta: `{ title: '首页', auth: 'manage_config' }`），懒加载 `views/manageCenter/Home/index.vue`
- 父路由 redirect 由 `/manageCenter/roleManagement` 改为 `/manageCenter/home`

### 2.2 首页结构（Home/index.vue）

- **Hero 欢迎区**：问候语（5-9/9-12/12-14/14-18/18+ 分时段）+ 用户名（取自 `app.user` 的 gitcodeLogin/gitcodeName/giteeLogin/giteeName/userName，与个人中心取名逻辑一致）+ 当前日期（`YYYY年MM月DD日 星期X`）+ 内联 SVG 插画（viewBox 0 0 320 240，渐变 + 玻璃质感面板 + 浮动卡片），min-height 300px
  - 插画使用内联 SVG 而非图片资源：避免 CDN/本地图片加载失败（首版踩坑），且无额外资源依赖
- **能力卡片网格**：8 张卡片，每张含彩色图标（@element-plus/icons-vue）+ 标题 + 描述 + 主题色（blue/purple/teal/orange/green/violet/red/gold）

### 2.3 权限过滤（核心逻辑）

```ts
function canAccessRoute(routeName: string): boolean {
  const auth = router.resolve({ name: routeName }).meta?.auth;
  // 无权限要求或仅需管理中心基础权限时，默认可见
  if (!auth || auth === "manage_config") {
    return true;
  }
  const permissions = app.user?.permissions ?? [];
  return permissions.includes(auth);
}

const visibleCapabilities = computed(() =>
  capabilities.filter((item) =>
    item.routes.some((name) => canAccessRoute(name)),
  ),
);
```

设计要点：

- **以路由 `meta.auth` 为单一权限来源**：卡片不硬编码权限字符串，而是通过 `router.resolve({ name })` 读取既有路由的权限配置，路由权限调整时首页自动跟随，避免两处维护
- **模块级聚合**：每张卡片配置 `routes` 数组（该模块下全部子路由 name），`some` 判断——任一子路由有权即显示整卡，符合"模块入口"语义
- **默认可见规则**：路由无 auth（如 `bulletinBoard`、`userDashboard`），或仅需 `manage_config`（进入管理中心本身即具备该权限）时默认可见

卡片与路由 name → auth 映射：

| 卡片     | 路由 name                                                                                                                                     | 涉及 auth                                                                                                                                     |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| 组织管理 | product                                                                                                                                       | product_manage                                                                                                                                |
| 权限管理 | userManagement / roleManagement / menuManagement / swaggerInterface                                                                           | user_manage / role_manage / menu_manage / swagger_pages                                                                                       |
| 机机管理 | machineInterface / machineAccount / machineLog                                                                                                | interface_manager / account_manager / log_manager                                                                                             |
| 日志审计 | businessLog / securityLog                                                                                                                     | log_manage                                                                                                                                    |
| 运营运维 | pv / allFeedback / allEvaluation / bulletinBoard / userDashboard / featureDashboard / oSPDashboard / RDDashboard / TRCDashboard / ECDashboard | operations_maintenance / open_source_project / rd_operation / test_resource_consumption / engineering_capability_operation（部分路由无 auth） |
| AI 工具  | aitoolsManage / aiToolsConfig                                                                                                                 | ai_tools_manage / ai_tools_config                                                                                                             |
| 漏洞挖掘 | dashboard / projects / schedules / system                                                                                                     | argus_manage                                                                                                                                  |
| 帮助中心 | helpCenterSetting                                                                                                                             | manage_config（默认可见）                                                                                                                     |

### 2.4 菜单美化（manageCenter/index.vue）

- 一级菜单/子菜单标题统一挂 `el-icon`（size 16）+ 主题色 class（`.mc-blue/.mc-indigo/.mc-violet/.mc-cyan/.mc-amber/.mc-green/.mc-pink/.mc-red/.mc-slate`，9 色）
- `el-sub-menu__title` / `el-menu-item` 高度 40px、圆角 6px、hover 浅灰背景 + 0.2s 过渡
- 激活态：浅蓝底（`#ecf5ff`）+ 主色文字；子菜单项前置 4px 小圆点，激活时变主色
- 帮助中心由 `el-sub-menu`（含子项）改为一级 `el-menu-item`（index: `helpCenterSetting`），图标保留
- 新增首页一级菜单项（index: `manageCenterHome`，Monitor 图标，置顶）
- 菜单跳转机制不变：`menuSelect` 仍通过 `router.push({ name: e })`

## 3. 影响范围

| 文件                                | 变更                                                                    |
| ----------------------------------- | ----------------------------------------------------------------------- |
| `router/manageRouter.ts`            | 新增 home 路由、redirect 调整                                           |
| `views/manageCenter/Home/index.vue` | 新增首页：Hero + 8 卡片 + canAccessRoute 权限过滤 + visibleCapabilities |
| `views/manageCenter/index.vue`      | 首页菜单项、帮助中心改一级菜单、菜单彩色图标与交互样式                  |

无后端接口变更、无数据模型变更、无部署配置变更。

## 4. 备选方案与取舍

- **卡片直接跳转对应模块**：用户确认为纯视觉页面，卡片不加跳转，保持概览定位
- **卡片硬编码权限字符串过滤**：改用 `router.resolve` 读取路由 `meta.auth`，避免权限配置双份维护
- **Hero 使用图片资源（CDN/本地 jpg）**：首版 CDN 图片加载失败踩坑后改为内联 SVG，零外部依赖且可随主题色微调
- **新增菜单项路由跳转改用 path**：沿用既有 `router.push({ name })` 机制，与全部菜单项一致
