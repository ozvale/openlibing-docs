# Tasks: review-pending-state-consistency

- **业务 Issue**: openlibing/openlibing-sca#87（反馈轮次）
- **业务分支**: ms_succeed（业务仓）；spec-openlibing-sca-review-pending-state-consistency（docs 仓）

## T1 实体与打标

- [ ] T1.1 `ScanIssue` 新增 `reviewId` 字段
- [ ] T1.2 `ScanCommonServiceImpl#setPendingReviewParam`（PR 扫描）写入 reviewId
- [ ] T1.3 `OpenPersonDMScanDMServiceImpl#setPendingReviewParam`（版本扫描）写入 reviewId

## T2 传播精确化（ConfirmReviewServceImpl）

- [ ] T2.1 `findInheritedDocIds` 查询条件改为 `scanId $in + reviewId + reviewStatus in (10,20)`，删除 fileHash 初筛与内存路径过滤
- [ ] T2.2 确认 `propagateRevokeToInheritScans` 复用同一查询路径后行为一致

## T3 自动提审去重（ConfirmReviewServceImpl）

- [ ] T3.1 `autoSubmitConfirmV2` 选取条件追加 `reviewStatus=00` 过滤

## T4 继承优先级反转 + 兜底

- [ ] T4.1 `ScanCommonServiceImpl#prResultInherit`：待审单优先，命中即跳过 tbl_issue 历史链
- [ ] T4.2 `OpenPersonDMScanDMServiceImpl#resultInheritV3`：待审单优先
- [ ] T4.3 `ScanCommonServiceImpl#findMatchingIssue` 3b：saveOne 前 null issueId 生成 UUID

## T5 单测（TDD：先 RED 后 GREEN）

- [ ] T5.1 传播：reviewId 命中 / 同 fileHash 不同 reviewId 不误刷 / 撤销同口径
- [ ] T5.2 提审：10/20/30/40 文档跳过，00 正常入选
- [ ] T5.3 PR 继承：待审+历史 40 → 继承 10；无待审 → 历史 40 不变；打标 verify；3b UUID verify
- [ ] T5.4 版本继承：待审优先 + 打标 verify

## T6 验证

- [ ] T6.1 ConfirmReviewServceImplTest / ScanCommonServiceImplTest / OpenPersonDMScanDMServiceImplTest / IntegrationApiServiceImplTest 全量通过
- [ ] T6.2 compile + checkstyle + spotbugs + pmd（pre-commit 全绿）
- [ ] T6.3 commit（Refs #87，新 commit 不 amend）

## T7 交付（用户自测确认后）

- [ ] T7.1 业务 PR（ms_succeed，ai-assisted 标签，关联 #87）
- [ ] T7.2 docs PR（spec 三件套归档 openlibing-docs）

## T8 用户反馈轮

- [ ] T8.1 继承待审状态时同步继承确认方式（committerType）：审核人=机器人 → auto，否则 manual，解密失败兜底 manual（PR + 版本扫描两处 setPendingReviewParam + 单测）
- [ ] T8.2 reviewId 无索引影响评估结论补入 design.md 风险表（scanId 前缀索引兜底，无需预加索引）
