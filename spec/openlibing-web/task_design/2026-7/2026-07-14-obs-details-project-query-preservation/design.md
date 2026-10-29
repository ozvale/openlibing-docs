## Context

### 路由与项目信息流

`openlibing-web` 的应用根组件 `Content.vue` 在初始化与路由变更时调用 `getProjectInfo(isSimpleAuth)`，该函数：

1. 复制 `route.query` 到 `tempQuery`
2. 调用 `getProject(tempQuery, isSimpleAuth)` 从 query 读取 `projectName` / `projectId`，结合 `routeNeedParams` 映射调用 `getBusinessProjectInfo` 接口，将结果写入 `app.projectInfo`
3. 成功后 `delete tempQuery.projectName` 与 `delete tempQuery.projectId`，`router.replace` 刷新 URL，避免残留参数干扰用户后续项目选择

### OBS 桶对象详情跳转

`obsArtifactRepository.vue` 的 `showDetail(rowData)`：

- `isPublishReview.value === true` 时 `emit('getBucketName', rowData.bucketName)`，用于发布评审内嵌场景
- 否则 `router.push({ name: 'obsDetails', query: { bucketName, projectId } })`

`obsDetails.vue` 通过 `watch(() => app.projectInfo, { immediate: true })` 监听项目信息，首次有效时 `handleSearch()` 加载桶对象，切换项目时 `returnBucketList()` 返回桶列表。该组件强依赖 `app.projectInfo.projectId` 发起 `queryBucketFileInfoAxios` 等请求。

### 问题根因

原跳转未传递 `projectName`，且 `getProjectInfo()` 会清除 URL 中的 `projectId`：

1. `obsArtifactRepository.vue` 跳转时未传 `projectName` → `getProject()` 无法从 query 读取 `projectName`
2. 即便 `projectId` 被传递，`getProjectInfo()` 成功后 `delete tempQuery.projectId` → URL 失去 `projectId`
3. `obsDetails.vue` 的 watcher 依赖 `app.projectInfo`，若 `getProject()` 未能正确还原（无 `projectName`），watcher 不触发或触发时项目信息为空
4. 桶对象列表无法加载，呈现「跳转后丢失项目信息」的现象

### 相关代码位置

- `Content.vue:275-298` — `getProjectInfo()`
- `Content.vue:304-` — `getProject()`
- `Content.vue:131` — 应用初始化调用 `getProjectInfo()`
- `obsArtifactRepository.vue:277-290` — `showDetail()`
- `obsDetails.vue:515-528` — `watch(() => app.projectInfo)`
- `noMenu.ts:497-505` — `obsDetails` 路由定义

**已确认产品约束：**

1. 仅 `obsDetails` 路由需保留项目参数；其他路由维持清除行为
2. `obsArtifactRepository.vue` 跳转时需主动传递 `projectName`
3. 不修改 `obsDetails.vue`（其 watcher 逻辑已正确）
4. 不修改 `getProject()` 的 query 读取逻辑
5. 发布评审模式下 `showDetail()` 不走路由跳转分支

## Goals / Non-Goals

**Goals:**

- `obsDetails` 路由的 URL query 在 `getProjectInfo()` 后保留 `projectName` / `projectId`
- `obsArtifactRepository.vue` 跳转 `obsDetails` 时传递 `projectName`
- 提供可扩展的「保留项目参数路由集合」机制，便于后续新增类似路由

**Non-Goals:**

- 不修改 `getProject()` 读取逻辑
- 不修改 `obsDetails.vue` 的 watcher 或数据加载逻辑
- 不为其他路由（如 `cveData`、`pipelineDetail`）保留项目参数
- 不改造 `getProjectInfo()` 的整体流程（仍保留 `router.replace` 清理 URL 的策略）
- 不引入 Pinia / 状态管理重构项目信息流
- 不处理 `isPublishReview` 模式下的 emit 行为

## Decisions

### D1：路由名白名单集合而非硬编码 if

**选择：** 定义 `ROUTES_KEEP_PROJECT_QUERY = new Set(['obsDetails'])`，通过 `has(String(route.name))` 判断。

**理由：**

- 后续如有其他详情页（如 `licenseDetails`、`sbomDetails`）需要保留项目参数，仅需向集合添加路由名
- 集合查询 O(1)，可读性优于多重 `||` 判断
- `String(route.name)` 防御 `route.name` 为 `undefined` 或非字符串类型的边界情况

**备选：**

- `if (route.name !== 'obsDetails')` — 扩展性差，多路由时需叠加 `&&` / `||`
- 在路由 `meta` 中声明 `keepProjectQuery: true` — 需改路由表，影响面大

### D2：集合定义为函数内常量

**选择：** `const ROUTES_KEEP_PROJECT_QUERY` 定义在 `getProjectInfo()` 函数体内（L286），而非模块顶层。

**理由：**

- 本次为最小化 bugfix，避免引入模块级变量
- 集合每次调用 `getProjectInfo()` 时重建，开销可忽略（`new Set(['obsDetails'])` 极轻量）
- 与原 diff 结构一致，便于 review

**备选：** 提升至模块顶层 `const` — 性能微优，但增加本次 diff 范围，未采纳。后续如需扩展可再提取。

### D3：仅保留 `projectName` / `projectId`，不保留其他参数

**选择：** 仅对 `tempQuery.projectName` 与 `tempQuery.projectId` 做条件 `delete`，其他 query 参数（如 `bucketName`）的清理逻辑不变。

**理由：** `bucketName` 原本就不在 `getProjectInfo()` 的清理范围内，无需特殊处理。

### D4：`obsArtifactRepository.vue` 主动传递 `projectName`

**选择：** 在 `showDetail()` 的 `router.push` query 中新增 `projectName: app.projectInfo?.projectName`。

**理由：**

- `getProject()` 依赖 `route.query.projectName` 调用 `getBusinessProjectInfo` 接口
- 即使 `projectId` 存在，`projectName` 缺失可能导致接口无法定位项目
- 与其他 OBS 页面（如 `obsManagement.vue` 读取 `app.projectInfo.projectId`）的取值方式一致

**备选：** 在 `obsDetails.vue` 中通过其他方式获取 `projectName` — 违反单一数据源原则，且 `obsDetails.vue` 不应感知跳转来源。

### D5：`hasError` 时不执行 `router.replace`

**选择：** 保留原有 `if (!hasError)` 包裹，失败时跳过 `router.replace`。

**理由：** 失败时 URL 保留原状，用户可看到触发错误的 query 参数，便于排查；强制 replace 清空参数会丢失上下文。

### D6：不处理 `obsDetails.vue` 内部的 `flag` 状态

**选择：** 不修改 `obsDetails.vue` 的 `flag` 变量与 watcher 逻辑。

**理由：**

- `flag` 用于区分「首次加载」与「切换项目返回桶列表」，逻辑已正确
- 本次问题根因在 `Content.vue` 未还原 `app.projectInfo`，而非 `obsDetails.vue` 的 watcher
- `app.projectInfo` 正确还原后，watcher 会自然触发

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| `ROUTES_KEEP_PROJECT_QUERY` 集合在函数内重建 | 开销可忽略；如后续扩展至多路由可提取为模块常量 |
| `obsDetails` URL 暴露 `projectName` / `projectId` | 与原跳转传 `projectId` 一致，无新增敏感信息；且 `obsDetails` 为已认证路由 |
| 用户在 `obsDetails` 页切换项目后 URL 参数过期 | `obsDetails.vue` 的 watcher 在切换项目时调用 `returnBucketList()`，不依赖 URL 参数；下次进入时由跳转源重新传递 |
| `route.name` 为 `undefined` 时 `String(undefined)` 返回 `'undefined'` | `ROUTES_KEEP_PROJECT_QUERY` 不含 `'undefined'`，自然走 `delete` 分支，与原行为一致 |
| `isPublishReview` 模式下 `showDetail` 未传 `projectName` | 该模式走 emit 分支，不执行 `router.push`，无影响 |

## Migration Plan

纯前端发布，无数据迁移。部署后：

1. 用户从 `obsArtifactRepository.vue` 点击桶名称跳转 `obsDetails`，URL 携带 `bucketName` / `projectId` / `projectName`
2. `Content.vue` 的 `getProjectInfo()` 检测到 `obsDetails` 路由，保留 `projectName` / `projectId`
3. `getProject()` 基于保留的 query 参数还原 `app.projectInfo`
4. `obsDetails.vue` 的 watcher 触发，加载桶对象列表

**回滚：** 移除 `obsArtifactRepository.vue` 中 `projectName` 一行 + 移除 `Content.vue` 中 `ROUTES_KEEP_PROJECT_QUERY` 集合与条件判断即可。

## Open Questions

（无 — 本次为双文件 bugfix，变更范围清晰，根因与修复方案已明确。）
