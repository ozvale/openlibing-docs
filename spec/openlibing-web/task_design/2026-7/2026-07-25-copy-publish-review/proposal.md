## Why

发布评审列表中，用户经常需要基于已有评审创建新的评审（例如同一产品的不同版本发布、或相似产品的发布流程）。当前只能手动新建空白评审并在详情页逐项填写配置，效率低且容易遗漏。需要提供"复制评审"功能，让用户一键继承源评审的配置信息，只需填写新的产品名称和版本号即可快速创建新评审。

## What Changes

- 在发布评审列表的操作列新增"复制"按钮，所有状态的评审均可复制
- 点击复制按钮弹出表单，填写产品名称和版本号（与新建评审表单一致）
- 复制流程：创建空白评审 → 跳转详情页（携带 copySourceReviewId）→ 详情页加载源评审数据并预填到内存 → 用户检查后手动保存
- 复制范围：评审方式（haveReview）、评审专家结构（fieldItemList）、制品路径配置（releaseArtifactInfoList，排除源制品 id 和状态字段）、中央仓信息（centralRepoInfoList）
- 不复制范围：软件包/路径（scanVirusScanVoList）、发布结果（releaseResultList）、病毒扫描状态、tag/release 内容字段（tagName/tagMessage/releaseName/releaseDescription）、评审结果/意见、产品名称/版本号（用户重新填写）
- 新评审状态为"新建"（reviewStatus=-1），不自动发起评审，用户在详情页检查预填数据后手动保存/提交

## Capabilities

### New Capabilities

- `copy-review`: 发布评审复制功能——从已有评审复制配置信息创建新评审

### Modified Capabilities

## Impact

- 修改文件：`publishReview/config.ts`（操作列配置，宽度 100→140）、`publishReview/index.vue`（复制入口逻辑）、`publishReview/addReview.vue`（支持 reviewCopy 模式，创建空白评审后跳转详情页）、`publishReview/detail/reviewDetail.vue`（loadCopyData 预填逻辑）
- API 调用：复用现有 `addPublishReview`、`getPublishReviewDetailById`，无需新增后端接口
- 路由参数：详情页新增 `copySourceReviewId` 查询参数，预填完成后通过 `router.replace` 自动移除

