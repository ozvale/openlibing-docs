# Tasks: review-inherit-analysis-fix

- **业务 Issue**: openlibing/openlibing-sca#81
- **交付 PR**: https://gitcode.com/openlibing/openlibing-sca/pull/315（dev_inherit -> release_20260923，10 commits，已合入）
- **分支**: dev_inherit（业务仓）

## T1 待评审任务继承（子域 A，commits `cd14bedb` / `97f22005` / `228b6053`）

- [x] T1.1 `TblConfirmReviewMapper.selectUnderReviewByScope`（java + xml）：按仓库范围查询审核中/转派审核单
- [x] T1.2 `resultInheritV3`（版本扫描）/ `prResultInherit`（PR 扫描）：无已批复 tbl_issue 可继承时，按归一化 path|sourceHash|fileHash 继承待审状态（cd14bedb）
- [x] T1.3 `patchReview` 按 reviewId 传播批复到全部关联 mongo 文档；ScanIssue 补 reviewId 字段映射（cd14bedb）
- [x] T1.4 fileHash 模糊继承回退：同文件 + fileHash 相同 + 从 mongId→commitId 解析提交时 PR head + 3a 增量 diff 守卫；基线不可解保守跳过（97f22005）
- [x] T1.5 `saveScanResult/insertScanResult` 自动同步收敛：仅命中 sourceHash/fileHash 匹配且状态 10/20 的审核单，防旧内容历史通过单错绑（228b6053）
- [x] T1.6 单测：ScanCommonServiceImplTest +240、OpenPersonDMScanDMServiceImplTest +88

## T2 analysis 评审状态治理（子域 B，commits `a4f12ba3` / `13539b69` / `e237cdc3` / `01881a0e`）

- [x] T2.1 `buildMongoUpdate` 不再写 reviewStatus/committerType；`prepareReviewUpdate` 批复期落定 committerType（补齐人工 issuePath 入口缺口）；`processApprovalLogic` 容忍机器人账号缺失回退审核人；`processScanIssue` 去重重指 mong_id；`executeUpdate` 不吞 bulk 异常；autoPathReview 日志修正（a4f12ba3；新增 5 单测，全量 1548 通过）
- [x] T2.2 scan_issue 批量确认去重：同一 (scanId, issueId) 批内先到先得，让位文档仅跳过 issueId，其余字段照常更新；附带 3 个 dm 文件 spotless 格式化（13539b69）
- [x] T2.3 patchReview 提交后收集受影响 scanId（mongId + reviewId 关联文档），重刷 tbl_person_scan.un_confirmed_file_num，失败不阻断评审事务（e237cdc3）
- [x] T2.4 patchRevoke 传播撤销到 reviewId 关联 mongo 文档（01881a0e）
- [x] T2.5 单测：ConfirmReviewServceImplTest +528

## T3 atomgit 域名归一（子域 C，commit `b934eaf3`）

- [x] T3.1 startPrScan 入口将 atomgit.com 域名归一为 gitcode.com 后进入扫描链路
- [x] T3.2 归一化 URL 回写 PrScanPo，全链路（校验/仓库地址/参数/MQ）一致
- [x] T3.3 单测：IntegrationApiServiceImplTest 新增 4 例（+120）

## T4 依赖治理（子域 D，commits `34a66ccf` / `c90be2f6`）

- [x] T4.1 openlibing-common-sdk 1.0.20.6 → 1.0.21.0（34a66ccf）
- [x] T4.2 dependencyManagement 收敛为仅 import BOM，properties 去重，dependencies 移除 BOM 托管版本号；版本随 common 对齐（spring-boot 3.5.14 等）；mvn compile + dependency:tree 验证（c90be2f6）

## T5 验证与交付

- [x] T5.1 pre-commit 门禁通过（spotless / checkstyle / spotbugs / pmd）
- [x] T5.2 受影响单测通过（含 atomgit 域名归一 4 例）
- [x] T5.3 CI 流水线通过（PR 标签 ci-pipeline-passed）
- [x] T5.4 业务 PR 创建并合入（#315，ai-assisted / lgtm / approved 标签，Fixes #81）

## 遗留项

- [ ] 重扫场景（reviewId 关联 mongo 文档）灰度观察批复/撤销传播的正确性与性能（PR 风险项，建议合并后观察）

## T6 归档（用户触发）

- [ ] T6.1 archive.md 写入 openlibing-docs（本目录）
- [ ] T6.2 docs PR：spec 沉淀至 openlibing-docs 主干
