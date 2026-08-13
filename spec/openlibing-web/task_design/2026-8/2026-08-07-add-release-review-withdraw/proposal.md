## Why

发布评审单在提交后（状态离开"新建"），创建者如果发现填写错误或需要补充信息，当前没有自助撤回入口，必须联系后端人工干预，流程低效且增加沟通成本。需要在评审详情页为创建者提供自助回撤能力，让评审单回到可编辑的"新建"状态。

## What Changes

- 在 `reviewDetail.vue` 的"基本信息"分区标题（`<reviewPartHeader>`）右侧新增"回撤"按钮，靠右对齐。
- 按钮显示条件：评审单状态不为"新建"（`reviewStatus !== -1`）**且** 当前登录用户是评审单创建者（`creatorId === app.user.userId`）。
- 点击按钮调用后端已有接口 `POST /base/withdrawReleaseReview`（query 参数：`projectId`、`userId`、`id`）。
- 接口调用成功后重新调用 `getDetailData()` 刷新评审单数据，使页面状态与后端一致。
- 在 `reviewDetail.vue` 中用 flex 容器包裹"基本信息"的 `<reviewPartHeader>` 和回撤按钮，按钮通过 `margin-left: auto` 靠右对齐。**不修改 `reviewPartHeader` 通用组件**（仅这一处需要按钮，不为单一使用点扩展通用组件接口）。
- 在前端 API 层（`url.ts` + `api.ts`）注册 `withdrawReleaseReview` 接口常量与请求函数。

## Capabilities

### New Capabilities

- `release-review-withdraw`: 发布评审回撤操作。定义评审单创建者在前端发起回撤的显示门控条件、调用契约（接口/参数/成功后行为）以及按钮的 UI 位置规则。

### Modified Capabilities

无。`openspec/specs/` 当前为空，本 change 为首次引入该 capability。

## Impact

- **受影响代码**：
  - `openlibing-web/apps/web-openlibing/src/api/url.ts`：新增 `WITHDRAW_RELEASE_REVIEW` URL 常量（1 行）。
  - `openlibing-web/apps/web-openlibing/src/api/api.ts`：新增 `withdrawReleaseReview` 请求函数（2 行）。
  - `openlibing-web/apps/web-openlibing/src/views/Publish/publishReview/detail/reviewDetail.vue`：用 flex 容器包裹"基本信息"的 `<reviewPartHeader>` 和回撤按钮，新增 `handleWithdrawReview` 处理函数、`canWithdrawReview` 计算属性、`withdrawLoading` 状态、`.header-row` 样式。
- **受影响接口**：调用后端已有接口 `POST /base/withdrawReleaseReview`，前端新增 API 注册，无后端改动。
- **不受影响**：评审单的数据模型、其他分区（制品/附件/评审信息等）、保存与发起评审流程、轮询逻辑。
- **风险**：回撤操作会让评审单回到"新建"状态，需确保用户理解后果。按钮仅在创建者可见，且仅在非新建状态出现，降低误操作概率。是否需要二次确认在 design 阶段决定。
