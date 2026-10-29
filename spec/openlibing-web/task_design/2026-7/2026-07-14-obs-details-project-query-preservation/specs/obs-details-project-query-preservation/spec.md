## ADDED Requirements

### Requirement: obsDetails 路由保留项目查询参数

`Content.vue` 的 `getProjectInfo()` 在成功获取项目信息后，MUST 根据当前路由名决定是否保留 URL query 中的 `projectName` 与 `projectId` 参数。对于路由名 `obsDetails`，MUST 保留这两个参数；对于其他路由，MUST 继续移除这两个参数以避免 URL 影响项目选择。

保留判断 MUST 通过常量集合 `ROUTES_KEEP_PROJECT_QUERY` 实现，该集合 MUST 包含 `'obsDetails'`。判断时 MUST 对 `route.name` 调用 `String()` 转字符串后使用 `Set.prototype.has` 查询。

#### Scenario: 进入 obsDetails 路由时保留项目参数

- **WHEN** 用户从 OBS 制品仓库列表页点击桶名称，跳转到 `obsDetails` 路由，URL query 携带 `bucketName`、`projectId`、`projectName`
- **AND** `Content.vue` 的 `getProjectInfo()` 被触发并成功获取项目信息（`hasError = false`）
- **THEN** `ROUTES_KEEP_PROJECT_QUERY.has('obsDetails')` MUST 返回 `true`
- **AND** `tempQuery.projectName` 与 `tempQuery.projectId` MUST NOT 被 `delete`
- **AND** `router.replace` 后的 URL query MUST 仍包含 `projectName` 与 `projectId`

#### Scenario: 进入非 obsDetails 路由时移除项目参数

- **WHEN** 用户进入任意非 `obsDetails` 路由（如 `obsArtifactRepository`、`cveData` 等），URL query 携带 `projectName` 与 `projectId`
- **AND** `getProjectInfo()` 成功执行（`hasError = false`）
- **THEN** `ROUTES_KEEP_PROJECT_QUERY.has(route.name)` MUST 返回 `false`
- **AND** `tempQuery.projectName` 与 `tempQuery.projectId` MUST 被 `delete`
- **AND** `router.replace` 后的 URL query MUST NOT 包含 `projectName` 与 `projectId`

#### Scenario: 获取项目信息失败时不执行 replace

- **WHEN** `getProject()` 抛出异常，`hasError = true`
- **THEN** MUST 跳过 `router.replace` 调用，无论路由名是否在 `ROUTES_KEEP_PROJECT_QUERY` 中
- **AND** URL query 保持触发 `getProjectInfo` 前的状态

### Requirement: OBS 制品仓库列表跳转详情时传递 projectName

`obsArtifactRepository.vue` 的 `showDetail()` 在通过 `router.push` 跳转到 `obsDetails` 路由时，MUST 在 query 中同时传递 `bucketName`、`projectId` 与 `projectName` 三个参数。`projectName` MUST 来源于 `app.projectInfo?.projectName`。

#### Scenario: 跳转 obsDetails 时携带 projectName

- **WHEN** 用户在 `obsArtifactRepository.vue` 的桶列表中点击桶名称触发 `showDetail(rowData)`
- **AND** `isPublishReview` 为 `false`（非发布评审场景）
- **THEN** `router.push` 的 query 对象 MUST 包含：
  - `bucketName: rowData.bucketName`
  - `projectId: app.projectInfo?.projectId`
  - `projectName: app.projectInfo?.projectName`

#### Scenario: 发布评审模式下不跳转路由

- **WHEN** 用户在 `obsArtifactRepository.vue` 中点击桶名称，且 `isPublishReview.value` 为 `true`
- **THEN** `showDetail()` MUST 调用 `emit('getBucketName', rowData.bucketName)` 向父组件传递桶名
- **AND** MUST NOT 执行 `router.push`
- **AND** MUST NOT 读取 `app.projectInfo?.projectName`

### Requirement: obsDetails 页面基于 projectInfo 加载桶对象数据

`obsDetails.vue` MUST 通过 `watch(() => app.projectInfo)` 监听项目信息变化，并在 `app.projectInfo.projectId` 存在时触发桶对象列表加载。当用户首次从 `obsArtifactRepository.vue` 跳转到 `obsDetails` 时，`Content.vue` 的 `getProjectInfo()` 必须能基于保留的 `projectName` / `projectId` query 正确还原 `app.projectInfo`，使 `obsDetails.vue` 的 watcher 能正常触发数据加载。

#### Scenario: 首次进入 obsDetails 时项目信息可用

- **WHEN** 用户首次从 `obsArtifactRepository.vue` 跳转到 `obsDetails`，URL 携带 `projectName` 与 `projectId`
- **THEN** `Content.vue` 的 `getProject()` MUST 能从 `route.query.projectName` / `route.query.projectId` 读取项目信息并写入 `app.projectInfo`
- **AND** `obsDetails.vue` 的 `watch(() => app.projectInfo)` MUST 触发（`immediate: true`）
- **AND** MUST 调用 `handleSearch()` 加载桶对象列表

#### Scenario: 切换项目时返回桶列表

- **WHEN** `obsDetails.vue` 已加载数据（`flag = true`），且 `app.projectInfo` 变化
- **THEN** watcher MUST 调用 `returnBucketList()` 返回桶列表视图
- **AND** MUST NOT 重复调用 `handleSearch()`

### Requirement: ROUTES_KEEP_PROJECT_QUERY 集合可扩展

`ROUTES_KEEP_PROJECT_QUERY` MUST 定义为 `Set` 实例，初始化时包含 `'obsDetails'` 字符串。后续如有其他路由需要保留项目参数，MUST 通过向该集合添加路由名扩展，而非修改 `getProjectInfo()` 的条件判断逻辑。

#### Scenario: 新增保留项目参数的路由

- **WHEN** 后续需要在路由 `xxxDetail` 中保留 `projectName` / `projectId`
- **THEN** 仅需在 `ROUTES_KEEP_PROJECT_QUERY` 初始化时添加 `'xxxDetail'`
- **AND** MUST NOT 修改 `if (!ROUTES_KEEP_PROJECT_QUERY.has(...))` 条件判断
