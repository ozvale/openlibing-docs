# Proposal: review-inherit-analysis-fix（PR 扫描评审继承链路修复与 analysis 评审状态治理）

- **仓库**: openlibing/openlibing-sca
- **业务 Issue**: https://gitcode.com/openlibing/openlibing-sca/issues/81
- **交付 PR**: https://gitcode.com/openlibing/openlibing-sca/pull/315（dev_inherit -> release_20260923，10 commits，已合入）
- **流程模式**: Full
- **开发分支**: dev_inherit（业务仓）
- **日期**: 2026-09-23

## 1. 需求背景

PR/版本扫描的评审结论流转链路存在一组相互关联的缺陷，集中表现为"评审中状态丢失"与"评审状态不一致"：

1. **待评审任务无法继承**：结果继承只读 `tbl_issue`（该表在评审批复后才写入），首次扫描提交待评审任务后，二次扫描（版本/PR）无法继承"审核中"状态而必须重复提审；`patchReview` 也只更新提交时绑定的 mongo 文档；
2. **模糊继承缺失**：PR 扫描的待审继承只按 `sourceHash+fileHash` 精确匹配——PR 只要改动了被扫文件（哪怕不触碰 issue 的匹配行），`sourceHash` 就变化，待审状态丢失重新提审；
3. **自动同步错绑**：`saveScanResult/insertScanResult` 按 file+repo（无哈希、无状态）取第一条审核单强制置 40，旧内容的历史通过记录会把当前内容的待审单错误置为已通过；
4. **analysis 评审状态一致性缺陷**：scan_issue 批量确认撞 `(scanId, issueId)` 唯一索引（E11000 整批失败）；人工批量批复后 `tbl_person_scan.un_confirmed_file_num` 不刷新（门禁列表停留失败态）；撤销批复不传播到 reviewId 关联文档；`reviewStatus=10` 自动确认中间态落库后残留并被历史继承放大；
5. **atomgit PR 链接域名不一致**：AtomGit PR 链接与 GitCode 路径格式相同，但域名不同导致校验/仓库地址/参数/MQ 链路不一致；
6. **pom 版本漂移**：openlibing-common BOM 已统一管理依赖版本，pom 中重复声明造成版本漂移。

## 2. 目标

1. 版本/PR 扫描可继承"审核中"状态：精确匹配（归一化 path|sourceHash|fileHash）+ fileHash 模糊回退（PR 未触碰匹配行时），增量 diff 3a 守卫防误继承；
2. 批复/撤销按 reviewId 传播到全部关联 mongo 文档，二次扫描继承的问题单随首次批复/撤销联动；
3. 内容哈希守卫防止自动同步错绑；analysis 四项状态一致性修复；
4. atomgit PR 链接在 `startPrScan` 入口归一为 gitcode 域名后进入扫描链路，回写 PrScanPo；
5. openlibing-common-sdk 升级 1.0.21.0，pom 版本声明收敛由 BOM 管理。

## 3. 非目标

- 不改变评审状态机取值（10 审核中 / 20 转派 / 40 已通过等语义不变）；
- 不调整 tbl_issue / mongo 文档的数据结构（仅 ScanIssue 实体补 reviewId 字段映射、TblConfirmReviewMapper 增查询）；
- 不处理 atomgit 平台差异能力（仅域名归一，按 gitcode 平台链路扫描）；
- 不在本次引入评审继承的灰度开关（依赖灰度观察，见风险）。

## 4. 验收标准（已随 PR #315 合入验证）

| # | 标准 | 验证方式 | 状态 |
|---|------|---------|------|
| 1 | 二次扫描继承待审状态；PR 改文件不碰匹配行时按 fileHash 模糊继承；触碰匹配行不继承 | 单测（ScanCommonServiceImplTest / OpenPersonDMScanDMServiceImplTest，+328 行） | ✅ |
| 2 | 批复/撤销经 reviewId 传播到全部关联 mongo 文档 | 单测（ConfirmReviewServceImplTest +528 行） | ✅ |
| 3 | scan_issue 批量确认不再触发 E11000；人工批复后刷新 un_confirmed_file_num；reviewStatus=10 中间态不再落库 | 单测（ConfirmReviewServceImplTest） | ✅ |
| 4 | 自动同步仅命中 sourceHash/fileHash 匹配且状态 10/20 的审核单 | 单测 | ✅ |
| 5 | atomgit PR 链接归一后走 gitcode 链路并回写 PrScanPo | 单测（IntegrationApiServiceImplTest 新增 4 例） | ✅ |
| 6 | pre-commit 门禁通过（spotless / checkstyle / spotbugs / pmd） | pre-commit | ✅ |
| 7 | 构建与依赖解析正常（spring-boot 解析为 3.5.14） | mvn compile + dependency:tree | ✅ |
| 8 | CI 流水线通过 | PR 标签 ci-pipeline-passed | ✅ |

## 5. 影响范围与风险

- **代码**：`analysis/service/impl/ConfirmReviewServceImpl`、`analysis/dao/TblConfirmReviewMapper`（java+xml）、`analysis/entity/ScanIssue`、`dm/service/impl`（ScanCommonServiceImpl / IntegrationApiServiceImpl / OpenPersonDMScanDMServiceImpl）、`pom.xml`（-305 行）；
- **风险 1（依赖收敛）**：pom.xml 精简后依赖完整性依赖 openlibing-common BOM 覆盖面，已用 `mvn compile` + `dependency:tree` 验证；
- **风险 2（评审继承涉及 mongo 文档关联）**：重扫场景下 reviewId 关联文档数量增长，建议灰度观察批复/撤销传播的正确性与性能；
- **风险 3（行为变化）**：中间态不落库后，批复失败时文档停在"未处理"，依赖下次扫描自愈重跑，属预期行为。
