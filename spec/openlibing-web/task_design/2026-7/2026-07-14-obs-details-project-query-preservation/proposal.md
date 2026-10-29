## Why

OBS（对象桶服务）制品仓库列表页 `obsArtifactRepository.vue` 通过 `showDetail()` 跳转到 `obsDetails` 路由查看桶对象详情。原跳转仅传递 `bucketName` 与 `projectId`，未传递 `projectName`。

`Content.vue` 的 `getProjectInfo()` 在路由变更后被触发，用于从 URL query 中读取 `projectName` / `projectId` 还原 `app.projectInfo`。但该函数在成功获取项目信息后，会无条件 `delete tempQuery.projectName` 与 `delete tempQuery.projectId`，目的是避免 URL 中残留的项目参数影响用户后续的项目选择交互。

这导致 `obsDetails` 页面在首次进入时，URL 中的 `projectId` 被 `getProjectInfo()` 清除，`projectName` 从未传递，`app.projectInfo` 无法正确还原，`obsDetails.vue` 的 `watch(() => app.projectInfo)` 无法触发桶对象列表加载，出现「跳转后丢失项目信息」的体验问题。

## What Changes

- `obsArtifactRepository.vue` 的 `showDetail()` 在 `router.push` 的 query 中新增 `projectName: app.projectInfo?.projectName`，使跳转 URL 携带完整项目信息
- `Content.vue` 的 `getProjectInfo()` 引入常量 `ROUTES_KEEP_PROJECT_QUERY = new Set(['obsDetails'])`，仅当当前路由名不在该集合时才 `delete` 项目参数；在集合中的路由（如 `obsDetails`）保留 `projectName` / `projectId`，供 `getProject()` 还原 `app.projectInfo`

## Capabilities

### New Capabilities

- `obs-details-project-query-preservation`: OBS 桶对象详情页跳转时保留项目查询参数，确保 `Content.vue` 能基于 URL query 还原 `app.projectInfo`，使 `obsDetails.vue` 的项目信息 watcher 正常触发数据加载

### Modified Capabilities

（无现有 openspec spec 需修改。本次为新增前端路由参数保留能力，不改变既有 spec 级行为契约。）

## Impact

- **前端文件**
  - `apps/web-openlibing/src/views/Content.vue` — `getProjectInfo()` 新增 `ROUTES_KEEP_PROJECT_QUERY` 集合与条件判断
  - `apps/web-openlibing/src/views/Publish/obs/obsArtifactRepository.vue` — `showDetail()` 的 `router.push` query 新增 `projectName`
- **路由** — `obsDetails` 路由（`/apps/obsDetails`）的 URL query 现保留 `projectName` / `projectId` / `bucketName` 三个参数
- **其他路由** — 行为不变，仍会在 `getProjectInfo()` 后清除 `projectName` / `projectId`
- **obsDetails.vue** — 无需修改；依赖 `watch(() => app.projectInfo)` 的现有逻辑即可正常工作
- **后端 / API** — 无变更
- **发布评审模式** — `isPublishReview` 为 `true` 时 `showDetail()` 走 emit 分支，不受本次改动影响
