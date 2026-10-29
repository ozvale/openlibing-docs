# 扫描查询多过滤与评审结论传播 — 技术设计

> 本 spec 为 PR 级统一归档。评审链路此前的子需求见文末"关联 spec"（pending 状态一致性 / 传播计数 / mongo 补偿），本文档侧重本 PR 实际交付。

## 方案概述

三块改动正交交付：

1. **查询过滤**：入参 PO 扩展集合字段 + Mapper XML 动态 `IN` 条件 + 新增下拉选数据接口，全部为 SQL/内存过滤，无 schema 变更。
2. **评审传播**：以 mongo `ScanIssue.reviewId` 打标为锚点，批复/撤销时按"申请时间之后的全部扫描 + reviewId + 仍待审"精确定位继承文档批量回写，传播后重算 PR 扫描未确认数。
3. **双域名**：新增 `GitcodeUrlUtil` 集中承载域名判定，替换散落的 `startsWith(gitcode.url)`。

## 关键决策

### 评审传播

1. **`reviewId` 打标定位，不用 fileHash 宽匹配**：同文件多个问题单共享同一开源文件 fileHash，宽匹配会把其他审核单的继承文档连带刷成批复状态。继承待审状态时文档已打标 `reviewId`（`setPendingReviewParam`），提审路径写入的绑定文档同样携带；传播查询条件为 `scanId IN (目标扫描) + reviewId = 审核单 id + reviewStatus IN (10,20)`，可走 (scanId, issueId) 索引。
2. **传播范围 = 申请时间之后的全部扫描，不只是最新一次**：`resolveInheritScanScope` 按"绑定文档 scanId 反查真实仓库 → `findByRepoIdAndCreatedAfter` 拉全量版本扫描 + PR 扫描"构建目标 scanId 集合（`InheritScanScope` record 区分全部 scanId 与 PR 扫描子集），并按 `boundScanId|applyTime` 缓存批复/撤销批次内复用。
3. **版本扫描审核单 repo_id 存的是 branchId**：不能直接当仓库 id 用，必须从绑定文档 scanId 反查 `tbl_scan`/`tbl_person_scan` 确定真实仓库；绑定记录缺失（历史清理）时按 branchId/repoId 双解释兜底。applyTime 缺失（历史数据）用 epoch 兜底等价不限时间。
4. **issueId 不随传播写入**：避免触发 (scanId, issueId) 唯一索引冲突；仅回写 reviewStatus/reviewTime/committerType/审核人（approved 时加 clarifyType/clarifyRemark/confirmDate）。
5. **传播 best-effort**：单条失败记 error 日志继续，不阻断批复/撤销主流程；受影响 PR 扫描（tbl_person_scan）统一走 `refreshPersonScanUnConfirmedNum` 重算未确认数（复用 `OpenScanDMService.uploadUnConfirmFileNum`，与页面刷新、自动批复口径一致）。
6. **撤销传播与批复共用 `findInheritedDocIds`**：重置字段与绑定文档撤销回写一致（reviewStatus=撤销、清空审核人/申请/澄清信息）。
7. **重复提审守卫**：提审前检查文档当前 reviewStatus，非 "00"（未提审）一律跳过，防止重复审核单被 autoPathReview 自动批复后经传播把审核中的问题静默刷成批复状态。

### 待审状态继承（修复"静默置为 approved"）

8. **待审单优先于已确认历史**：`findInheritablePendingReview` 命中即 `setPendingReviewParam` 并 continue，不再落入旧 tbl_issue "已通过"匹配分支。
9. **两级匹配 + 基线守卫**：
   - 一级：`归一化路径|sourceHash|fileHash` 精确命中直接继承；
   - 二级：fileHash 一致但 sourceHash 变化（PR 改了文件未改到匹配行）时，以审核单提交时 PR head（绑定 mongo 文档 commitId，按审核单 id 缓存）为基线取增量 diff，未命中匹配行才继承；基线无法确定保守不继承。
10. **审核范围扩大到仓库 + 全部分支**：`selectUnderReviewByScope`（SQL 联查申请人/审核人名称，review_status IN (10,20)，repo_id IN scopeIds）与 `getTblIssues(scopeIds)` 共用 `getInheritScopeIds`。
11. **committerType 继承判定**：机器人账号（`SecurityUtil.decrypt(botAccount, part1)`）为 auto，否则 manual；解密失败按 manual 兜底，不阻断继承。
12. **tbl_issue 继承主键修复**：issueId 未继承时落库前生成 UUID（tbl_issue.id 非自增），避免插入失败中断整批继承。

### 双域名

13. **`GitcodeUrlUtil` 集中判定**：`gitcode.domains` 逗号分隔域名前缀列表（默认常量），初始化时统一去尾斜杠归一化（生产 Apollo 的 gitcode.url 带尾斜杠，归一化后 stripDomain 不残留前导斜杠），并校验 `gitcode.url` 包含在列表内（防配置漂移）；`isGitcodeUrl` / strip 域名方法替换 IntegrationApiServiceImpl 约 20 处与 DownLoadFilesUtils 的单域名判定。

### 查询过滤

14. **集合入参防御性拷贝**：`ManualVersionScanQueryPo` 手写全参构造器与 getter/setter，集合字段进出均拷贝，避免可变引用外泄（SpotBugs 风格约束）；`ManualVersionScanSelectVO` 同口径。
15. **指定 repository/branch 时绕过缓存**：社区扫描缓存 key 不含分支维度，指定过滤条件时直查避免脏读；PR 扫描统计数（totalPrNum 等）与列表同口径按 repository 过滤。

### 依赖

16. **RabbitMQ prod 免校验 TLS**：`useSslProtocol()` → `useTlsWithNoVerification()`，解决内网自签证书握手失败；amqp-client 显式钉 5.34.0（与同迭代 PR #329/#330 一致）。

## 涉及文件（分组）

| 分组       | 文件                                                                                                                                                                                                                                                                                                             | 说明                                                                                    |
| ---------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| 域名工具   | `common/utils/GitcodeUrlUtil`（新增）、`GitcodeUrlUtilTest`（新增）                                                                                                                                                                                                                                              | 多域名配置 + 尾斜杠归一化 + 主域名校验                                                  |
| 查询入参   | `ManualVersionScanQueryPo`、`ManualVersionScanSelectVO`（新增）、`ScanCommunityReq`、`ScanCommunityDto`                                                                                                                                                                                                          | repoName/branchName/scanStatus 集合化；branch/repository 过滤字段                       |
| 查询 DAO   | `TblManualVersionScanMapper`（+selectDistinctRepoNames/BranchNames）、`TblScanDMMapper`（+findByRepoIdAndCreatedAfter/findByBranchIdAndCreatedAfter）、`TblPersonScanDMMapper`（+findByRepoIdAndCreatedAfter）、Mapper XML（IN 条件）                                                                            | 过滤与传播范围查询                                                                      |
| 评审传播   | `ConfirmReviewServceImpl`（+约 300 行）、`TblConfirmReviewMapper`（+selectUnderReviewByScope + XML）、`ScanIssue`（+reviewId）                                                                                                                                                                                   | 批复/撤销传播、重复提审守卫                                                             |
| 待审继承   | `ScanCommonServiceImpl`（+约 200 行）、`OpenPersonDMScanDMServiceImpl`（+约 90 行）                                                                                                                                                                                                                              | findInheritablePendingReview 两级匹配 + 基线守卫、setPendingReviewParam 打标、UUID 修复 |
| 查询服务   | `ManualVersionScanController`（+repoBranchList）、`ManualVersionScanService/Impl`、`OpenScanServiceImpl`、`OpenPersonScanServiceImpl`、`LicenseServiceImpl`                                                                                                                                                      | 过滤逻辑与下拉选接口                                                                    |
| 双域名适配 | `IntegrationApiServiceImpl`（约 20 处）、`DownLoadFilesUtils`                                                                                                                                                                                                                                                    | startsWith → isGitcodeUrl                                                               |
| 依赖       | `RabbitConnectionFactoryConfig`、`pom.xml`                                                                                                                                                                                                                                                                       | 免校验 TLS；amqp-client 5.34.0                                                          |
| 测试       | ConfirmReviewServceImplTest（+约 640 行）、ScanCommonServiceImplTest（+约 340 行）、OpenPersonDMScanDMServiceImplTest（+约 180 行）、ManualVersionScanServiceImplTest、ManualVersionScanControllerTest、IntegrationApiServiceImplTest、LicenseServiceImplTest、OpenPersonScanServiceImplTest、GitcodeUrlUtilTest | 传播/继承/过滤/域名全覆盖                                                               |

## 行为逻辑（评审传播主流程）

```
批复/撤销(review):
  for review in findList:
    boundScanId = 绑定 mongo 文档.scanId          # 反查真实仓库
    scope = (boundScanId, applyTime) 缓存解析    # 申请后同仓库全量版本+PR扫描
    inheritIds = mongo(scanId IN scope.scanIds
                       AND reviewId = review.id
                       AND reviewStatus IN (10,20))
    批复: 回写 reviewStatus/reviewTime/committerType/审核人 (+approved: clarify*/confirmDate)
    撤销: 重置为撤销态并清空审核人/申请/澄清信息
  refreshPersonScanUnConfirmedNum(scope.personScanIds)   # PR 扫描未确认数重算
```

## 配置项

| 配置键            | 默认             | 说明                                                                        |
| ----------------- | ---------------- | --------------------------------------------------------------------------- |
| `gitcode.domains` | 内置默认域名列表 | GitCode 域名前缀（逗号分隔），尾斜杠自动归一化；须包含 `gitcode.url` 主域名 |

## 测试策略

- **单测**：新增 ConfirmReviewServceImplTest 传播/守卫用例（批复传播、撤销传播、重复提审跳过、范围解析兜底）、ScanCommonServiceImplTest 待审继承用例（精确匹配、模糊匹配 + 基线守卫、待审优先于已通过）、GitcodeUrlUtilTest（默认/自定义域名、尾斜杠、主域名校验、strip 归一化）、ManualVersionScan* 过滤用例；既有测试适配 scanStatus 集合化与 GitcodeUrlUtil 注入。CI 已通过。
- **手动**：多过滤查询结果正确性；批复/撤销传播后各扫描状态与未确认数一致性；备用域名仓库扫描。

## 风险与缓解

| 风险                                           | 缓解                                                                                      |
| ---------------------------------------------- | ----------------------------------------------------------------------------------------- |
| 传播扩大影响面（申请后全部扫描）误伤其他审核单 | reviewId 精确定位替代 fileHash 宽匹配；issueId 不写入避免唯一索引冲突                     |
| 绑定扫描记录被历史清理后传播范围失准           | repoId 按 branchId/repoId 双解释兜底；传播 best-effort 失败仅记日志                       |
| mongo 无 reviewId 索引，传播查询慢             | 查询条件以 scanId IN 为主可走 (scanId, issueId) 索引；继承文档量级为单仓库申请后扫描数    |
| `gitcode.domains` 配置遗漏备用域名             | 校验仅保证主域名包含，备用域名缺失时行为与旧版一致（不识别）；GitcodeUrlUtilTest 明确契约 |
| RabbitMQ 免校验 TLS 削弱传输安全               | 仅 prod 内网自签证书场景；如需强校验后续引入 truststore 配置                              |
| scanStatus 单值 → 集合的入参兼容               | 原 Integer 语义由 List 承载，老调用方传单值 JSON 数组兼容；单测覆盖                       |

## 关联 spec（评审链路历史迭代）

- `review-pending-state-consistency/` — pending 审核状态一致性
- `review-propagate-person-scan-count/` — 评审结果传播与未确认数
- `review-mongo-compensation/` — ConfirmReview 审核结果 MySQL/Mongo 双写补偿

## 跨仓影响

- 仅 `openlibing-sca`，无其他仓改动、无 DB schema 迁移、无部署链路变更（`gitcode.domains` 有默认值，不配置不影响启动）。
