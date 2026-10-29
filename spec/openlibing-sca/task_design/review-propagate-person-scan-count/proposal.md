# Proposal: review-propagate-person-scan-count

- **业务 Issue**: openlibing/openlibing-sca#87（反馈轮次）
- **业务分支**: `ms_succeed`
- **前置链路**: 69060a61 → 8968c644 → 40fea9ef → b9020bd1 → 26ade1f1（待审继承 + 批复/撤销按「申请时间之后全部扫描」传播）

## 需求背景

上一轮已实现批复/撤销结果向「申请时间之后所有继承该审核单待审状态的 mongo scan_issue 文档」传播，但 `tbl_person_scan.un_confirmed_file_num` 仅在**本次审核绑定扫描**上被刷新（页面审核后前端调 `/refresh/confirmNum/V2`，只按绑定 mongIds 反查 scanId）。传播目标扫描（申请时间之后的 PR 扫描）的 mongo 文档状态已更新，但其 `un_confirmed_file_num` 停留在旧值，门禁列表显示错误的未确认/未通过状态。

## 需求描述

1. 批量批复（`patchReview` → `updateIssueData`）传播命中后，收集受影响扫描中属于 `tbl_person_scan` 的 scanId，在 mongo 批量更新执行完成后统一重算 `un_confirmed_file_num`；
2. 批量撤回（`patchRevoke`）传播命中后，同样收集并刷新；
3. 计数口径复用既有 `OpenScanDMServiceImpl#uploadUnConfirmFileNum`（`getPendingRisksNum`），与其他刷新入口一致；
4. 刷新为 best-effort：逐个 scanId try/catch，失败只记日志，不阻断批复/撤销主流程。

## 验收标准

- [ ] 批复传播命中继承文档后，受影响 PR 扫描的 `un_confirmed_file_num` 被重算（单测 verify）
- [ ] 撤回传播命中继承文档后，受影响 PR 扫描的 `un_confirmed_file_num` 被重算（单测 verify）
- [ ] 无传播目标（scope 为空或无继承文档命中）时不触发刷新（单测 verify）
- [ ] 单个 scanId 刷新失败不影响批复/撤销事务与后续 scanId 刷新（单测）
- [ ] 版本扫描 scanId（tbl_scan）不会被误刷 tbl_person_scan（personScanIds 仅来自 tbl_person_scan 查询）
- [ ] 既有 ConfirmReviewServceImplTest 全部通过，编译/静态检查通过

## 影响范围

单仓（openlibing-sca）单模块（analysis 层 ConfirmReviewServceImpl + 其单测），无表结构、无接口契约、无鉴权变化。
