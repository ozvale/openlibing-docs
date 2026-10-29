# Design: review-pending-state-consistency

- **业务 Issue**: openlibing/openlibing-sca#87（反馈轮次）
- **业务分支**: `ms_succeed`

## 1. 方案总览

三个缺陷共享同一根因：**继承文档与审核单之间只有「内容特征」这种弱关联（fileHash+路径），缺少身份级强关联**。方案核心是在继承发生的那一刻把审核单 id 写到文档上（`reviewId`），传播与去重全部改为按身份关联：

```text
继承（写入时打标）                     传播/去重（读取时按身份）
┌────────────────────────────┐      ┌──────────────────────────────────┐
│ setPendingReviewParam       │      │ findInheritedDocIds:              │
│  sIssue.reviewId = R.id     │ ───► │   scanId $in + reviewId = R.id    │
│  （PR + 版本扫描两处）        │      │   + reviewStatus in (10,20)       │
└────────────────────────────┘      └──────────────────────────────────┘
autoSubmitConfirmV2：仅 reviewStatus=00 入选（杜绝重复审核单）
prResultInherit / resultInheritV3：待审单优先，未命中回退 tbl_issue 历史链
findMatchingIssue 3b：saveOne 前 null issueId 生成 UUID
```

## 2. 关键设计点

### 2.1 reviewId 打标（写入时），规避 a8259c0e 撤回的回填查询

a8259c0e 撤回的是「对存量文档按内容反查回填 reviewId」（scan_issue 无可用索引）。本方案 reviewId 在**继承写入时**落盘，不产生任何回填查询：

- `ScanIssue` 新增 `reviewId` 字段（String，mongo 动态 schema，无 Liquibase 变更）；
- `ScanCommonServiceImpl#setPendingReviewParam`（PR 扫描）与 `OpenPersonDMScanDMServiceImpl#setPendingReviewParam`（版本扫描）继承待审单时写 `sIssue.setReviewId(review.getId())`；
- `rebindPendingReview`（自动提审重绑审核单 mongId 的场景）不涉及 reviewId（该路径文档状态仍为 00，未打标）。

传播查询 `scanId $in + reviewId + reviewStatus in (10,20)` 走现有 scanId 前缀索引，扫描内文档量级与现状相同。

### 2.1a 确认方式随待审单继承（用户反馈轮补充）

继承待审状态时同步继承确认方式（`committerType`，人工/自动）：`tbl_confirm_review` 不落该字段，沿用 `OpenScanDMServiceImpl#setIssue` 的判定口径——审核人（`reviewUserId`）为机器人账号（解密 `sca.bot.account`）即 `auto`，否则 `manual`；解密失败按 `manual` 兜底并告警，不阻断继承。批复/撤销传播仍会在落库时按批复者重写该字段，继承值仅覆盖待审展示期。涉及 PR/版本扫描两处 `setPendingReviewParam`。

### 2.2 传播精确化（findInheritedDocIds / propagateRevokeToInheritScans）

查询条件从 `scanId $in + fileHash + reviewStatus in (10,20)` + 内存归一化路径过滤，改为 `scanId $in + reviewId + reviewStatus in (10,20)`：

- reviewId 全局唯一，同文件其他问题单 / 机器人重复单的继承文档（reviewId 不同）不再被连带；
- 内存归一化路径过滤删除（身份匹配后无需内容特征二次过滤）；
- 无兼容层：待审继承（69060a61）尚未合入 master，线上不存在无标继承文档。

### 2.3 自动提审去重（autoSubmitConfirmV2）

`needAutoSubmitConfirm` 选取条件追加 `"00".equals(issue.getReviewStatus())`：

- 已继承待审（10/20）文档不再重复建单（机器人重复单 R0 是传播过杀的弹药来源）；
- 已决（30/40）文档同样跳过，消除「重复提审→自动批复」的幂等空转；
- 正常自动分析链路不受影响：自动分析对象本就是未处理（00）文档。

### 2.4 继承优先级反转（待审单优先）

`prResultInherit`（PR 扫描）每个 issue 的处理顺序调整为：

1. 先 `findInheritablePendingReview`（精确 path|sourceHash|fileHash + fileHash 模糊 + 3a 守卫，逻辑不变）；
2. 命中 → `setPendingReviewParam`（写 10/20 + applyTime + reviewId），**跳过** tbl_issue 历史链；
3. 未命中 → 原 `findMatchingIssue` 历史继承链（行为不变）。

`resultInheritV3`（版本扫描）同样反转：先 `pendingReviewMap` 精确匹配，未命中回退原链。

语义依据：待审单存在即代表该内容正在走审核流程；历史 40 若实际晚于待审单批复，传播（已按 reviewId 精确化）会把待审文档刷成 40，状态自洽。修复前「旧 40 遮蔽在审待审单」正是本次实测缺陷。

### 2.5 3b saveOne null id 兜底

`findMatchingIssue` 3b 中 `getTblIssueInfo(currentIssue, tblIssue)` 构建的记录 id 取自 `scan.getIssueId()`——该字段在继承命中前尚未赋值（setSIssueParam 在返回后才执行），必为 null；tbl_issue.id 主键非自增，INSERT 必失败并导致 resultInherit 整体 catch 中断。修复：saveOne 前对空 id 生成 UUID（与 53c15c2b 修复审批路径的口径一致）。

> 附带收益：3b 命中后写入的新 tbl_issue 记录（created/modified=now、sourceHash=当前）此前因异常从未落库，修复后开始产生数据——该记录是后续扫描精确/模糊继承的基线，属预期行为。

## 3. 涉及文件（8 个）

| 文件                                                 | 变更                                                                       |
| ---------------------------------------------------- | -------------------------------------------------------------------------- |
| `analysis/entity/ScanIssue.java`                     | +`reviewId` 字段                                                           |
| `dm/service/impl/ScanCommonServiceImpl.java`         | setPendingReviewParam 打标；prResultInherit 待审优先；3b saveOne UUID 兜底 |
| `dm/service/impl/OpenPersonDMScanDMServiceImpl.java` | setPendingReviewParam 打标；resultInheritV3 待审优先                       |
| `analysis/service/impl/ConfirmReviewServceImpl.java` | autoSubmitConfirmV2 仅 00 入选；findInheritedDocIds 按 reviewId 定位       |
| `ConfirmReviewServceImplTest.java`                   | 传播精确命中/过杀防回归、提审去重用例                                      |
| `ScanCommonServiceImplTest.java`                     | 待审优先、reviewId 打标、UUID 兜底用例                                     |
| `OpenPersonDMScanDMServiceImplTest.java`             | 版本扫描待审优先 + 打标用例                                                |
| `IntegrationApiServiceImplTest.java`                 | （如提审入口用例在此）按需补充                                             |

## 4. 风险与缓解

| 风险                                                            | 缓解                                                                                                                                                                                                                                                                                                                                                                                                                |
| --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 传播查询依赖 reviewId，若继承路径遗漏打标则文档永远不被传播命中 | 打标集中在两处 setPendingReviewParam（全部继承入口），单测 verify 打标；漏标文档行为等同「未继承」，下次扫描重新继承                                                                                                                                                                                                                                                                                                |
| reviewId 无索引                                                 | 传播查询以 scanId $in 打头，走既有 (scanId, issueId) 唯一索引的 scanId 前缀，reviewId/reviewStatus 仅作候选集内过滤；候选集=申请后同仓扫描文档，量级小；与旧 fileHash 查询索引画像一致，零回退。a8259c0e 撤回的是无 scanId 绑定的全表回填查询，现 reviewId 为写入时打标，不存在该查询。仅当未来出现不带 scanId 前缀的 reviewId 全表读才需加 {scanId:1, reviewId:1} 复合索引（走 mongo changeset），灰度监控后再评估 |
| 待审优先后，旧场景「历史 40 + 新待审单」显示从 40 变 10         | 业务期望即待审；审核单批复后传播刷 40 自愈                                                                                                                                                                                                                                                                                                                                                                          |
| autoSubmitConfirmV2 跳过非 00 文档，自动批复量下降              | 下降部分正是重复单空转；人工审核流程不受影响                                                                                                                                                                                                                                                                                                                                                                        |
| 3b 修复后 tbl_issue 开始新增记录                                | 记录为后续继承基线，属设计内行为；主键 UUID 生成口径与 53c15c2b 一致                                                                                                                                                                                                                                                                                                                                                |

## 5. 跨仓影响

无。
