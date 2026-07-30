## 1. 操作列配置

- [x] 1.1 在 config.ts 的操作列（operation 列）中新增"复制"按钮配置：fnName 为 `handleCopy`，所有状态可见，权限为 `platform_release_base`，图标为 `iconfont icon-fuzhi`
- [x] 1.2 操作列宽度从 100 调整为 140，容纳新增按钮

## 2. 列表页复制入口

- [x] 2.1 在 index.vue 的 functionsMap 中新增 `handleCopy` 函数：设置 dialogTitle 为"复制发布评审"，dialogType 为 `reviewCopy`，dialogInfo 为 `{ sourceReviewId: row.id }`，打开弹窗

## 3. 弹窗组件改造（addReview.vue）

- [x] 3.1 在 formInfo 中新增 `sourceReviewId` 字段（类型为 `number | null`），通过 watch currentReview 自动赋值
- [x] 3.2 在 saveInfo 中新增 `reviewCopy` 分支，调用 `handleCopy` 函数
- [x] 3.3 实现 `handleCopy` 函数：校验 sourceReviewId 存在 → 调用 `addPublishReview` 创建空白评审 → 成功后 `router.push` 跳转详情页，携带 `reviewId`（新评审 ID）和 `copySourceReviewId`（源评审 ID）查询参数
- [x] 3.4 引入 `useRouter`，支持复制成功后直接跳转详情页（而非通过 emit refresh 由父组件跳转）

## 4. 详情页预填逻辑（reviewDetail.vue）

- [x] 4.1 新增 `isCopyDataLoaded` ref，作为同一次组件生命周期内的防重复执行保护
- [x] 4.2 在 `getDetailData` 成功回调中，检测 `route.query.copySourceReviewId && !isCopyDataLoaded`，满足则调用 `loadCopyData`
- [x] 4.3 实现 `loadCopyData` 函数：调用 `getPublishReviewDetailById(copySourceReviewId)` 获取源评审详情，对制品数据做变换后预填到内存
- [x] 4.4 制品数据变换：排除源制品 `id`（避免跨评审数据污染）；重置 `releaseResultList`、`scanVirusScanVoList`、`virusScanStatus`；清空 `tagName`、`tagMessage`、`releaseName`、`releaseDescription`；保留 `repoUrl`、`repoId`、`softwareDownloadType`、`releaseMethodList`、`releaseMethod` 等配置字段
- [x] 4.5 预填范围：`releaseArtifactInfoList`（变换后）、`haveReview`、`fieldItemList`、`centralRepoInfoList`，并设置 `reviewStatus: -1`
- [x] 4.6 预填成功后通过 `router.replace` 移除 URL 中的 `copySourceReviewId` 参数，防止刷新页面重复预填覆盖已保存数据
- [x] 4.7 错误处理：源评审加载失败时显示 ElMessage 错误提示

## 5. 详情页验证

- [x] 5.1 验证 releaseArtifacts.vue 对"代码仓已选 repoId 但未选 tag"中间状态的渲染是否正常（验证结论：组件 watch 逻辑会在 repoId 有值时自动加载分支列表，中间状态渲染正常，无需修改）

## 6. 代码清理

- [x] 6.1 移除 saveReview 中遗留的 `console.log('dataaa', data)` 调试语句
