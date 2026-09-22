## ADDED Requirements

### Requirement: 复制按钮可见性
系统 SHALL 在发布评审列表的操作列中为每条评审记录显示"复制"按钮，无论评审处于何种状态（新建、评审中、发布中、成功、失败）。

#### Scenario: 所有状态评审均可复制
- **WHEN** 用户查看发布评审列表
- **THEN** 每条评审记录的操作列中均显示"复制"按钮，不受评审状态限制

### Requirement: 复制弹窗表单
系统 SHALL 在用户点击"复制"按钮后弹出表单，要求用户填写产品名称和版本号。表单 UI 与新建评审弹窗一致。

#### Scenario: 点击复制按钮弹出表单
- **WHEN** 用户点击某条评审的"复制"按钮
- **THEN** 弹出对话框，包含产品名称和版本号两个必填输入框，弹窗标题为"复制发布评审"

#### Scenario: 表单校验
- **WHEN** 用户未填写产品名称或版本号并点击确定
- **THEN** 表单校验失败，提示用户填写必填字段

### Requirement: 复制评审数据流程
系统 SHALL 通过以下步骤完成复制：创建空白评审 → 跳转详情页（携带 copySourceReviewId）→ 详情页加载源评审数据并预填到内存 → 用户检查后手动保存。

#### Scenario: 复制成功
- **WHEN** 用户填写产品名称和版本号后点击确定
- **THEN** 系统依次执行：1) addPublishReview 创建空白评审获取 newReviewId；2) 跳转详情页，携带 reviewId 和 copySourceReviewId 查询参数；3) 详情页加载新评审数据完成后，检测 copySourceReviewId 并调用 loadCopyData；4) 获取源评审数据并预填到新评审内存中；5) 移除 URL 中的 copySourceReviewId 参数；6) 用户检查预填数据后手动保存

#### Scenario: 源评审数据加载失败
- **WHEN** 详情页调用 getPublishReviewDetailById 获取源评审数据失败
- **THEN** 系统显示"获取源评审详情失败"错误提示，新评审保持空白状态，用户可手动填写或重新操作

### Requirement: 可复制字段范围
系统 SHALL 复制以下源评审字段到新评审：评审方式（haveReview）、评审专家结构（fieldItemList）、制品路径配置（releaseArtifactInfoList，排除源制品 id 和状态字段）、中央仓信息（centralRepoInfoList）。

#### Scenario: 评审方式和评审专家复制
- **WHEN** 源评审的评审方式为线上评审（haveReview=1）且包含评审专家列表
- **THEN** 新评审继承相同的评审方式，评审项结构和评审专家名单被复制，但评审结果（itemStatus）和评审意见（itemComment）不复制

#### Scenario: 制品路径配置复制
- **WHEN** 源评审包含制品信息（releaseArtifactInfoList）
- **THEN** 新评审继承制品配置（softwareDownloadType、releaseMethodList、releaseMethod、repoUrl、repoId 等），但排除源制品主键 id，重置发布结果（releaseResultList）、病毒扫描状态（scanVirusScanVoList、virusScanStatus），清空 tag/release 内容字段（tagName、tagMessage、releaseName、releaseDescription）

#### Scenario: 中央仓信息复制
- **WHEN** 源评审包含中央仓信息（centralRepoInfoList）
- **THEN** 新评审继承完整的中央仓信息列表

### Requirement: 不可复制字段范围
系统 SHALL 不复制以下字段：软件包/路径（scanVirusScanVoList）、发布结果（releaseResultList）、病毒扫描状态（virusScanStatus）、tag/release 内容字段（tagName、tagMessage、releaseName、releaseDescription）、评审结果/意见（itemStatus/itemComment）、源制品主键（id）、产品名称和版本号。

#### Scenario: 软件包和发布结果不复制
- **WHEN** 源评审包含软件包/路径列表和发布结果
- **THEN** 新评审的软件包/路径列表为空（scanVirusScanVoList=[]），发布结果为空（releaseResultList=[]），病毒扫描状态为 undefined

#### Scenario: 产品名称和版本号由用户填写
- **WHEN** 用户在复制弹窗中填写产品名称和版本号
- **THEN** 新评审的产品名称和版本号为用户输入值，不继承源评审的值

### Requirement: 新评审状态
系统 SHALL 将复制创建的新评审状态设为"新建"（reviewStatus=-1），不自动发起评审。

#### Scenario: 复制后新评审为新建状态
- **WHEN** 复制评审流程完成
- **THEN** 新评审的 reviewStatus 为 -1（新建），用户需在详情页手动检查配置后提交评审

### Requirement: 代码仓制品部分复制
系统 SHALL 对代码仓发行版路径保留 repoUrl 和 repoId（代码仓标识），不复制 tagName、tagMessage、releaseName、releaseDescription。

#### Scenario: 代码仓制品保留仓库信息但清空 tag/release
- **WHEN** 源评审的制品信息中包含代码仓发行版路径（releaseMethod 包含 "2")
- **THEN** 新评审的该制品保留 repoUrl 和 repoId 字段，tag/release 相关字段清空，用户需在详情页重新选择 tag 和填写 release 信息

### Requirement: 预填参数生命周期管理
系统 SHALL 在预填成功后立即从 URL 中移除 copySourceReviewId 参数，防止用户刷新页面时重复预填覆盖已保存数据。

#### Scenario: 预填成功后 URL 参数清理
- **WHEN** loadCopyData 成功完成预填
- **THEN** 系统通过 router.replace 移除 URL 中的 copySourceReviewId 参数，保留其他查询参数（如 reviewId）

#### Scenario: 刷新页面不重复预填
- **WHEN** 用户在预填完成并保存后刷新详情页
- **THEN** 由于 copySourceReviewId 已从 URL 移除，不会触发重复预填，页面显示已保存的数据
