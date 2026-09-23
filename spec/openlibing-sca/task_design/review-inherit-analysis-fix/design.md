# Design: review-inherit-analysis-fix

- **业务 Issue**: openlibing/openlibing-sca#81
- **交付 PR**: https://gitcode.com/openlibing/openlibing-sca/pull/315（dev_inherit -> release_20260923，10 commits，已合入）

## 1. 方案总览

四个子域，围绕"评审状态在多次扫描间的正确流转"这一主线：

```text
子域 A  待评审任务继承（dm）        cd14bedb / 97f22005 / 228b6053
子域 B  analysis 评审状态治理       a4f12ba3 / 13539b69 / e237cdc3 / 01881a0e
子域 C  atomgit 域名归一（dm）      b934eaf3
子域 D  依赖治理（pom）             34a66ccf / c90be2f6
```

## 2. 子域 A：待评审任务继承

### 2.1 精确继承（cd14bedb）

- 新增 `TblConfirmReviewMapper.selectUnderReviewByScope`：按仓库范围查询"审核中（10）/转派（20）"的审核单（java + xml）；
- 版本扫描 `resultInheritV3` 与 PR 扫描 `prResultInherit` 在无已批复 `tbl_issue` 记录可继承时，按**归一化 path|sourceHash|fileHash** 匹配待审单，继承其"审核中"状态，避免重复提审；
- `patchReview` 批复时把结论传播到**所有以 reviewId 关联**的 mongo 文档（此前只更新提交时由 mongId 绑定的单条），首次批复即等效批复二次扫描继承的问题单；
- `ScanIssue` 实体补充 `reviewId` 字段映射（+2 行）。

### 2.2 模糊继承（97f22005）

精确匹配 `sourceHash+fileHash` 在 PR 改动了被扫文件时失效（sourceHash 变化）。新增模糊回退：

- 条件：同一文件的待审单，且 `fileHash` 相同——`fileHash` 是**开源文件身份**哈希，对仓内文件编辑稳定；
- 基线解析：从待审单绑定的 mongo 文档（mongId → commitId）解析提交时的 PR head；
- 守卫：复用已批复历史继承的 **3a 增量 diff 守卫**——自该 head 以来的增量 diff 若触碰 issue 匹配行则跳过继承，否则继承；
- 兜底：基线无法解析时保守跳过（宁可重复提审，不可误继承）。

### 2.3 内容哈希防错绑（228b6053）

`saveScanResult/insertScanResult` 的自动同步（mongo=40 → 同步审核单=40）原实现 `reviewFindAll(file, repoId).getFirst()`：file+repo 匹配、无哈希无状态过滤，旧内容的历史通过单会强置当前内容的待审单为 40（mongo 仍审核中，状态撕裂）。

- 收敛为仅同步 `sourceHash/fileHash` 与当前扫描 issue 匹配、且状态仍为 10/20 的审核单；
- 不同内容的审核单一律不触碰。

## 3. 子域 B：analysis 评审状态治理（ConfirmReviewServceImpl）

### 3.1 停止持久化 reviewStatus=10 中间态（a4f12ba3，最大单项）

版本/PR 扫描自动确认链路原先在提交阶段即写 `reviewStatus=10 + committerType=auto`，后续 `autoPathReview` 批复失败时中间态永久残留并被历史继承放大（licenseStatus=1 且 copyrightStatus=1 的问题长期停在"审核中"）：

- `buildMongoUpdate` 不再写 `reviewStatus` / `committerType`，两字段统一由批复阶段落定；批复失败文档停在"未处理"，下次扫描可自愈重跑；
- `prepareReviewUpdate` 批复时补写 `committerType`（机器人 auto / 真人 manual），并补齐人工 issuePath 提交入口不写 committerType 的缺口；
- `processApprovalLogic` 容忍 `user_basic_info` 查不到机器人账号（此前 NPE 导致整批自动批复事务回滚），reviewUserId 回退为审核人 userId；
- `processScanIssue` 去重命中已存在待审审核单时，把该审核单 `mong_id` 重指到本次扫描文档并同步关联信息（此前直接跳过，autoPathReview 只刷旧文档）；
- `executeUpdate` 不再静默吞 Mongo bulk 异常，输出审核单 id 便于按 mong_id 补偿；
- 修正 `autoPathReview` 误导性的 "redis is error" 日志，补齐 scanId/scanType/reposId。

### 3.2 批量确认去重 issueId 写入（13539b69）

同一 scan 下多条记录确认后可能经 hash 匹配解析到同一个 TblIssue，批量写 issueId 撞 `scan_issue(scanId, issueId)` 唯一索引 → 整批 bulk 更新报 E11000：

- 同一 key 只允许一条文档写入：批内先到先得，历史文档已占用时让位；
- 让位文档仅跳过 issueId，审核状态等其他字段照常更新。

（附带 3 个 dm 模块文件 Google Java Format 格式化，纯格式，因 pre-commit mvn-spotless 全量扫描无法拆分。）

### 3.3 人工批复刷新门禁未确认数（e237cdc3）

`tbl_person_scan.un_confirmed_file_num` 此前只被 `autoPathReview`（机器人自动批复）刷新，`patchReview` 人工批量批复不更新 → 问题全部批复后门禁列表仍停留失败态：

- patchReview 提交后，从批复文档的 mongId 与 reviewId 关联文档收集受影响 scanId，重刷门禁扫描（仅 tbl_person_scan）的 un_confirmed_file_num；
- 刷新失败仅记日志，不阻断评审事务。

### 3.4 撤销传播（01881a0e）

`patchRevoke` 原只重置提交时 mongId 绑定的单条 mongo 文档；引入待审继承后，后续扫描的 mongo 文档携带同一 reviewId，撤销后仍停留 reviewStatus=10（详情页显示"审核中"）：

- 撤销传播到所有 reviewId 关联 mongo 文档，复用 patchReview 已有的 reviewId 回填机制。

## 4. 子域 C：atomgit 域名归一（b934eaf3）

- AtomGit PR 链接与 GitCode 的 `/pull/{n}` 路径格式一致：`startPrScan` 入口将 `atomgit.com` 域名替换为 `gitcode.com` 后进入扫描链路；
- 归一化后的 URL 回写 `PrScanPo`，保证 URL 校验、仓库地址构建、PR 参数获取、MQ 消息全链路一致按 gitcode 平台处理。

## 5. 子域 D：依赖治理（c90be2f6 / 34a66ccf）

- `openlibing-common-sdk` 1.0.20.6 → 1.0.21.0；
- dependencyManagement 精简为仅 import openlibing-common BOM（-305 行）；删除 properties 中重复的编码/java.version 声明及不再被引用的版本属性；
- dependencies 中移除 BOM 已覆盖的版本号（lettuce/amqp/redisson/fastjson2/poi/poi-ooxml/springdoc），未覆盖的固定版本保留；
- 版本随 common 对齐：spring-boot 3.5.5→3.5.14、spring-framework 6.2.12→6.2.19、spring-boot-starter-amqp 3.4.4→3.5.14、lettuce 改由 boot BOM 管理；
- 验证：`mvn compile` + `dependency:tree`（spring-boot 解析为 3.5.14）。

## 6. 涉及文件（12 个）

| 文件 | 变更 | 子域 |
|------|------|------|
| `analysis/service/impl/ConfirmReviewServceImpl.java` | +217：中间态治理 / 批量确认去重 / 未确认数刷新 / 撤销传播 | B |
| `analysis/dao/TblConfirmReviewMapper.java` + `resources/mapper/dm/TblConfirmReviewMapper.xml` | +9 / +21：新增 selectUnderReviewByScope | A |
| `analysis/entity/ScanIssue.java` | +2：reviewId 字段映射 | A |
| `dm/service/impl/ScanCommonServiceImpl.java` | +226：resultInheritV3 / prResultInherit 待审继承（精确 + 模糊）、saveScanResult/insertScanResult 哈希守卫 | A |
| `dm/service/impl/OpenPersonDMScanDMServiceImpl.java` | +69：继承链路配套调整 | A |
| `dm/service/impl/IntegrationApiServiceImpl.java` | +90：startPrScan atomgit 域名归一 + PrScanPo 回写 | C |
| `pom.xml` | -305：BOM 收敛 + sdk 1.0.21.0 | D |
| `ConfirmReviewServceImplTest` / `IntegrationApiServiceImplTest` / `OpenPersonDMScanDMServiceImplTest` / `ScanCommonServiceImplTest` | +528 / +120 / +88 / +240：上述行为单测（含 atomgit 4 例） | A/B/C |

## 7. 风险与缓解

| 风险 | 缓解 |
|------|------|
| pom 依赖收敛（-305 行）后构建产物依赖完整性 | mvn compile + dependency:tree 验证；版本随 BOM 对齐（spring-boot 3.5.14） |
| 评审继承涉及 mongo 文档关联，重扫场景关联文档数量增长 | 建议 PR/版本重扫灰度观察批复/撤销传播正确性与性能（PR 风险项） |
| 模糊继承误继承 | 3a 增量 diff 守卫触碰匹配行即跳过；基线不可解保守跳过 |
| 中间态不落库后批复失败的问题单停在"未处理" | 属预期 fail-safe：下次扫描自愈重跑；bulk 异常不再吞掉，可按审核单 id 补偿 |
| reviewStatus=10 语义保留 | 状态机取值不变，仅落库时机后移到批复阶段 |

## 8. 跨仓影响

无。openlibing-common BOM（openlibing-common-sdk）为既有关联依赖，本次仅升级 patch 版本并对齐其托管版本。
