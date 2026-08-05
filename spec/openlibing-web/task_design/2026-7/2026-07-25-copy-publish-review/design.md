## Context

发布评审（publishReview）是 OpenLibing 平台的核心功能之一，用于管理产品发布的评审流程。当前新建评审只能创建空白评审，用户需要在详情页手动填写所有配置（评审方式、评审专家、制品信息等）。对于相似产品的发布或同一产品的不同版本发布，用户需要重复填写大量相同配置，效率低且容易遗漏。

现有技术栈：

- 前端：Vue 3 + Element Plus + TypeScript
- API 层：统一 apiClient 封装，已有 `addPublishReview`、`getPublishReviewDetailById`、`updatePublishReview` 等接口
- 列表页操作列：通过 config.ts 配置 fnName，由 index.vue 的 functionsMap 映射到具体函数
- 新建弹窗：addReview\.vue 组件，支持 `reviewAdd` 和 `reviewUpdate` 两种 dialogType

## Goals / Non-Goals

**Goals:**

- 在列表操作列新增"复制"按钮，所有状态评审均可复制
- 复制评审时弹出 productName + productVersion 表单（与新建一致）
- 复制源评审的配置信息到新评审，跳转详情页后用户可检查并手动提交
- 复用现有 API（add → getDetail → transform → update），无需新增后端接口

**Non-Goals:**

- 不自动发起/提交评审
- 不复制软件包/路径（scanVirusScanVoList）
- 不复制附件信息
- 不复制评审结果/意见（itemStatus/itemComment）

不新增后端 copy API

## Decisions

### D1: 前端驱动 vs 后端驱动

**选择**: 前端驱动（方案 A）

**理由**: 无需后端配合，复用现有 API 即可实现。前端只需做数据变换，用户在详情页检查后手动保存。

**流程**:

1. `addPublishReview` → 创建空白评审，拿到 newReviewId
2. `router.push` → 跳转详情页，携带 `reviewId=newReviewId` + `copySourceReviewId=sourceReviewId`
3. 详情页 `getDetailData` 加载新评审数据完成后，检测 URL 中的 `copySourceReviewId`
4. `loadCopyData` → `getPublishReviewDetailById(sourceReviewId)` 获取源评审数据
5. 前端内存预填 → 提取可复制字段，重置状态字段，合并到新评审 dataList
6. `router.replace` 移除 `copySourceReviewId` 参数，防止刷新重复预填
7. 用户检查预填数据后手动保存（`updatePublishReview`）

### D2: 复用 addReview\.vue vs 新建 copyReview\.vue

**选择**: 复用 addReview\.vue，扩展 dialogType

**理由**: 表单 UI 完全一致（productName + productVersion），只是提交逻辑不同。新增 `reviewCopy` 类型，在 saveInfo 中根据 dialogType 调用不同的处理流程。改动量更小，不引入新文件。

### D3: 复制按钮的可见条件

**选择**: 所有状态均可复制

**理由**: 用户可能在任何阶段需要基于已有评审创建新评审（包括新建、评审中、成功、失败等状态）。

### D4: 制品字段的复制策略

**选择**: 全量复制源制品字段，但排除标识字段（id）并重置状态/内容字段

**理由**: 制品对象包含多种路径类型的配置（华为云流水线、PYPI、代码仓），全量复制可确保各类型配置完整继承。排除 `id` 避免后端按主键误更新源评审制品；重置 `releaseResultList`、`scanVirusScanVoList`、`virusScanStatus` 避免继承运行时状态；清空 `tagName`、`tagMessage`、`releaseName`、`releaseDescription` 因为 tag/release 是具体发布内容，新评审需重新填写。保留 `repoUrl`、`repoId` 代表"选择了哪个代码仓"。

### D5: 预填时机与生命周期管理

**选择**: 详情页内存预填 + URL 参数清理

**理由**: 将预填逻辑放在详情页（而非弹窗中）有以下优势：
- 用户可在详情页直观检查预填结果，确认无误后再保存
- 避免弹窗中多步 API 串行调用的复杂度和失败回滚问题
- 预填数据仅在内存中，未保存前不影响后端数据

**URL 参数生命周期**: `copySourceReviewId` 作为一次性触发参数，预填成功后立即通过 `router.replace` 移除，防止用户刷新页面时重复预填覆盖已保存数据。组件内 `isCopyDataLoaded` ref 作为同一次组件生命周期内的防重复执行保护。

## Risks / Trade-offs

- **\[源评审加载失败]** → `loadCopyData` 调用 `getPublishReviewDetailById` 失败时，新评审已创建但预填未生效。应对：显示错误提示，用户可手动填写或重新操作；空白评审不会自动清理，用户可手动删除。
- **\[制品中间状态渲染]** → 复制制品保留了 repoId/repoUrl 但清空了 tag/release 字段，详情页制品组件需能正确渲染"已选代码仓但未选 tag"的状态。应对：已验证 releaseArtifacts.vue 的 watch 逻辑会在 repoId 有值时自动加载分支列表，中间状态渲染正常。
- **\[预填未保存即离开]** → 用户进入详情页后未保存即离开，预填数据丢失。应对：这是预期行为，预填仅为辅助，用户可重新复制。

