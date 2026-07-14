## 1. Content.vue 路由参数保留逻辑

- [x] 1.1 在 `getProjectInfo()` 中定义 `const ROUTES_KEEP_PROJECT_QUERY = new Set(['obsDetails'])`
- [x] 1.2 将原 `delete tempQuery.projectName` / `delete tempQuery.projectId` 包裹在 `if (!ROUTES_KEEP_PROJECT_QUERY.has(String(route.name)))` 条件内
- [x] 1.3 保留 `if (!hasError)` 外层条件与 `router.replace({ name, query, params })` 调用

## 2. obsArtifactRepository.vue 跳转传递 projectName

- [x] 2.1 在 `showDetail()` 的 `router.push` query 中新增 `projectName: app.projectInfo?.projectName`
- [x] 2.2 验证 `isPublishReview` 分支仍走 `emit('getBucketName', ...)`，不执行 `router.push`

## 3. 手动验收

- [ ] 3.1 从 `obsArtifactRepository.vue` 点击桶名称跳转到 `obsDetails`，URL query 包含 `bucketName` / `projectId` / `projectName`
- [ ] 3.2 `obsDetails` 页面 URL 在 `getProjectInfo()` 执行后仍保留 `projectName` / `projectId`
- [ ] 3.3 `obsDetails.vue` 的 `watch(() => app.projectInfo)` 触发，桶对象列表正常加载（`handleSearch()`）
- [ ] 3.4 在 `obsDetails` 页面切换项目后，watcher 调用 `returnBucketList()` 返回桶列表
- [ ] 3.5 进入非 `obsDetails` 路由（如 `cveData`），URL 中的 `projectName` / `projectId` 仍被清除
- [ ] 3.6 `getProjectInfo()` 失败（`hasError = true`）时不执行 `router.replace`，URL 保持原状
- [ ] 3.7 发布评审模式下（`isPublishReview = true`）点击桶名称走 emit 分支，不跳转路由、不读取 `projectName`
- [ ] 3.8 直接通过 URL 访问 `/apps/obsDetails?bucketName=x&projectId=y&projectName=z`，`app.projectInfo` 能正确还原
