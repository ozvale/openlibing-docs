# Proposal: review-pending-state-consistency

- **业务 Issue**: openlibing/openlibing-sca#87（反馈轮次）
- **业务分支**: `ms_succeed`
- **前置链路**: 69060a61 → 8968c644 → 40fea9ef → b9020bd1 → 26ade1f1 → 89e27710 → 51bfbd6b（待审继承 + 批复/撤销传播 + 计数刷新）

## 需求背景

用户实测发现：PR 扫描未改到匹配行代码时，本应保持/继承「待审核」的问题在 mongo 中直接变成「审核通过」（40），而对应 `tbl_confirm_review` 审核单仍停留在待审核（10）——即未经任何人批复，待审状态被静默覆盖。

排查确认 ms_succeed 链路存在三个相互耦合的缺陷：

1. **传播过杀**：`findInheritedDocIds` 按 `scanId $in + fileHash + 归一化路径 + 状态(10/20)` 定位传播目标，无内容级匹配。同文件多个问题单共享同一开源文件 fileHash，批复任一审核单（含 `autoPathReview` 在每次 PR 扫描末尾的机器人自动批复）会把同文件全部待审文档连带刷成批复状态，待审单本体不受影响（与实测现象完全吻合）。
2. **重复审核单**：`autoSubmitConfirmV2` 选取自动提审问题只看 licenseStatus/copyrightStatus，不看 reviewStatus；`processScanIssue` 查重键含 sourceHash，PR 改了文件即查重不中，为已继承待审（10）的文档新建机器人待审单，随即被 `autoPathReview` 批复并触发缺陷 1 的传播过杀。
3. **继承优先级反转**：`prResultInherit`/`resultInheritV3` 先走 `tbl_issue`（仅批复后写入，状态 40/30）确认历史继承，未命中才继承待审状态——旧「已通过」记录会遮蔽在审待审单。另发现 `findMatchingIssue` 3b 路径 `issueMapper.saveOne` 的 issueId 此时必为 null（tbl_issue.id 主键非自增），生产必抛异常导致 resultInherit 整体中断，单测 mock 掩盖（53c15c2b 仅修复了审批路径同类问题）。

## 需求描述

1. 待审状态继承时在 mongo 文档写入 `reviewId`（继承那一刻即知关联审核单），批复/撤销传播改为按 `reviewId` 精确定位继承文档，替代 fileHash+路径的宽匹配；
2. `autoSubmitConfirmV2` 仅对 `reviewStatus=00` 的文档自动提审，已继承待审（10/20）与已决（30/40）文档不再重复建单；
3. 结果继承优先级反转：存在可继承待审单时优先继承待审状态（10/20），未命中才回退 `tbl_issue` 历史继承链（PR 扫描与版本扫描同步调整）；
4. `findMatchingIssue` 3b 的 `issueMapper.saveOne` 对 null issueId 生成 UUID 兜底（与 53c15c2b 口径一致）。

## 验收标准

- [ ] 批复传播仅命中 reviewId 等于被批复审核单的继承文档；同 fileHash 同路径但 reviewId 不同的待审文档不被误刷（单测 verify）
- [ ] 撤销传播同口径收窄（单测）
- [ ] 自动提审跳过 reviewStatus != 00 的文档；00 且 license/copyright SUCCESS 的文档正常提审（单测）
- [ ] PR 扫描：同内容存在待审单 + 历史已通过记录时继承 10 而非 40；无待审单时历史继承行为不变（单测）
- [ ] 版本扫描：同上优先级反转（单测）
- [ ] 继承文档携带 reviewId（PR + 版本扫描，单测 verify）
- [ ] 3b 命中且 issueId 为 null 时 saveOne 收到 UUID 主键（单测 verify）
- [ ] 既有 ConfirmReviewServceImplTest / ScanCommonServiceImplTest / OpenPersonDMScanDMServiceImplTest / IntegrationApiServiceImplTest 全部通过，compile + pre-commit 门禁通过

## 影响范围

单仓（openlibing-sca），analysis 层 ConfirmReviewServceImpl + dm 层 ScanCommonServiceImpl / OpenPersonDMScanDMServiceImpl + ScanIssue 实体（新增 reviewId 字段）及对应单测。无 MySQL 表结构变化（mongo 文档新增动态字段，无需 Liquibase）；无接口契约变化；无鉴权变化。待审继承功能尚未合入 master（仅 ms_succeed），传播语义收窄无需兼容历史无标文档。
