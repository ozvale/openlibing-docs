## Context

`reviewDetail.vue` 是发布评审详情页主组件，已具备以下可复用基础设施：

- `getDetailData()`：拉取评审单完整详情并回填 `dataList`，含轮询逻辑。回撤成功后直接复用此函数刷新。
- `isDataOwner` computed（约第 932 行）：`dataList.value?.creatorId === app?.user?.userId`，已封装"当前用户是否创建者"判断。
- `reviewStatus === -1`：代码中已建立的"新建"状态判定约定（保存/发起评审按钮仅在 `reviewStatus === -1` 时显示）。
- API 层约定：URL 常量集中在 `src/api/url.ts`（`PLATFORM_RELEASE + '/base/xxx'`），请求函数集中在 `src/api/api.ts`（`export const fn: RequestFunc = (a, s) => apiClient.post(urls.URL, a, s)`）。
- `reviewPartHeader.vue`：通用分区标题组件，仅有箭头图标 + 装饰圆点 + 标题文字，根元素 `.part-header-container` 为 `display: flex; margin-bottom: 15px`。**不改此组件**——回撤按钮仅"基本信息"一处需要。
- 后端接口 `POST /base/withdrawReleaseReview` 已存在（Apifox endpoint id `497256413`，status `released`），query 参数 `projectId` / `userId` / `id`，响应 schema 后端未定义具体字段（前端按业务码 `code === 200` 判定成功）。

## Goals / Non-Goals

**Goals:**

- 让创建者在非"新建"状态下能自助回撤评审单，无需联系后端。
- 复用现有 `getDetailData` / `isDataOwner` / API 注册约定，最小侵入。
- 在 `reviewDetail.vue` 内用 flex 容器包裹第一个 `reviewPartHeader` 和按钮，不扩展通用组件。

**Non-Goals:**

- 不改动后端 `/base/withdrawReleaseReview` 接口契约或响应结构。
- 不引入权限/角色层面的额外校验（接口侧已有 `userId` 参数，后端负责鉴权）。
- 不处理回撤后评审单的具体字段差异展示（由 `getDetailData` 刷新后自然反映）。
- 不在"基本信息"以外的其他分区标题加回撤入口。

## Decisions

### 决策 1：在 `reviewDetail.vue` 中用 flex 容器包裹第一个 `reviewPartHeader` 和按钮，不扩展通用组件

**选择**：在 `reviewDetail.vue` 的"基本信息" `<reviewPartHeader>` 外包一层 `<div class="header-row">`（`display: flex; align-items: center;`），按钮通过 `margin-left: auto` 靠右，`margin-bottom: 15px` 与 `reviewPartHeader` 的 `margin-bottom` 对齐。

**理由**：回撤按钮仅出现在"基本信息"这一个 `reviewPartHeader` 旁，其他分区（制品/附件/评审信息等）无需此能力。为单一使用点扩展通用组件 `reviewPartHeader` 属于过度设计，违反"职责限于使用点"原则。外层 flex 包裹限定在 `reviewDetail.vue` 内，其他 `reviewPartHeader` 使用处零改动。

**替代方案**：给 `reviewPartHeader.vue` 加 `#action` 具名插槽。**否决**：虽然插槽为空时不影响其他使用处，但本次仅一处使用，扩展通用组件接口的收益不足以覆盖其引入的耦合面。若未来多处需要右侧操作，再提取插槽。

### 决策 2：回撤前增加 `ElMessageBox.confirm` 二次确认

**选择**：点击回撤按钮后先弹 `ElMessageBox.confirm`，用户确认后才发请求。

**理由**：回撤会让评审单从已提交状态回到"新建"，是带状态副作用的操作。发布评审是正式流程，评审单状态回退可能影响下游（评审专家已收到的通知、已发起的评审项等）。二次确认是低成本防御，符合该页面"发起评审"等关键操作的处理习惯。

**替代方案**：不加确认，点击即发请求，靠后端不可逆性兜底。**否决**：误操作成本高于一次点击确认。

### 决策 3：新增 `canWithdrawReview` computed 而非在模板内联判断

**选择**：新增 `const canWithdrawReview = computed(() => isDataOwner.value && dataList.value?.reviewStatus !== -1)`。

**理由**：门控条件有两个维度（创建者 + 状态），内联到模板会变成 `v-if="isDataOwner && dataList.reviewStatus !== -1"`，可读性差且无法在 console 中快速验证。独立 computed 让意图自解释，且未来若需调整门控只改一处。

### 决策 4：API 函数签名与调用方式

**选择**：遵循现有约定 ——
- `url.ts`：`export const WITHDRAW_RELEASE_REVIEW = PLATFORM_RELEASE + '/base/withdrawReleaseReview';`
- `api.ts`：`export const withdrawReleaseReview: RequestFunc = (a, s) => apiClient.post(urls.WITHDRAW_RELEASE_REVIEW, a, s);`
- 调用处：`withdrawReleaseReview({ params: { projectId, userId, id } })`

**理由**：与 `submitPublishReview` / `triggerReleaseDecision` 等同模块接口完全一致，参数通过 `params` 传 query string 是 `apiClient` 的既有约定。接口定义为 `POST` + query（非 body），按 Apifox 契约执行。

### 决策 5：成功/失败处理复用页面既有模式

**选择**：成功 → `ElMessage.success` + `getDetailData()` 刷新；失败 → `ElMessage.error` + 不刷新。参考 `handlePublishDecision`（约第 530 行）的成功处理模式。

**理由**：保持与同页面其他关键操作（发布决策、发起评审）一致的用户反馈体验，降低维护认知成本。

## Risks / Trade-offs

- **[评审单 id 取值]** 回撤接口的 `id` 参数取 `dataList.value?.id`。若详情接口在某些边界场景未返回 `id`（如复制评审未保存前），回撤按钮因 `reviewStatus === -1` 门控本就不显示，风险低。→ 不额外加 `id` 缺失防御，依赖门控条件覆盖。
- **[响应 schema 未定义]** 后端 `withdrawReleaseReview` 的响应体 schema 在 Apifox 中为空对象，前端按 `res.code === 200` 判定成功。若后端未来改为非 200 业务码表示部分失败，前端需同步。→ 当前与同页面其他接口判定方式一致，可接受。
- **[布局对齐]** `reviewPartHeader` 根元素有 `margin-bottom: 15px`，外包 flex 容器后按钮需加相同 `margin-bottom` 保持底部对齐。→ 在 `.header-row` 内的按钮样式显式补 `margin-bottom: 15px`，`align-items: center` 确保内容垂直居中。