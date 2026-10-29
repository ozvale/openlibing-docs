# 扫描查询多过滤与评审结论传播（20261019 iter1）

## 需求背景

两条主线问题：

1. **查询过滤维度不足**：人工版本扫描只能按单状态过滤、无法按仓库名/分支名筛选，前端下拉选数据无专用接口；社区扫描列表不支持分支过滤、社区 PR 扫描不支持按仓库过滤；license 社区查询不支持分支过滤。运营/审核人员在大数据量社区下无法快速定位目标记录。
2. **评审结论传播缺陷**：第二次扫描会继承审核中/转审任务的待审核状态（按归一化路径 + sourceHash + fileHash 匹配），但批复/撤销只更新提交时绑定的 mongo 文档，导致"申请时间到最新扫描之间"所有继承待审状态的文档停留在待审核或被旧"已通过"历史静默刷成 approved；重复提审还会把仍在审核中的问题静默刷成批复状态。
3. **单域名假设**：GitCode 双域名（gitcode.com 与备用域名）场景下，代码中散落的 `startsWith(gitcode.url)` 单域名判定导致备用域名仓库无法识别。

关联业务 Issue：

- openlibing/openlibing-sca#88 【合法合规】扫描兼容 atomgit.com 域名、审核逻辑及风险看板数据看板优化

## 功能描述

### 1. 查询过滤增强

| 位置               | 变更                                                                                                                               |
| ------------------ | ---------------------------------------------------------------------------------------------------------------------------------- |
| 人工版本扫描列表   | `ManualVersionScanQueryPo` 新增 `repoName`/`branchName` 集合过滤（精确匹配），`scanStatus` 由单值改为集合；Mapper XML 改 `IN` 条件 |
| repo-branch 下拉选 | 新增 `GET /manual/version/scan/repoBranchList`（按 communityId 返回去重的仓库名/分支名列表 `ManualVersionScanSelectVO`）           |
| 社区版本扫描       | `ScanCommunityReq` 新增 `branch` 过滤；指定 repository/branch 时绕过 Redis 缓存直查                                                |
| 社区 PR 扫描       | `ScanCommunityDto` 新增 `repository` 过滤，PR 统计数与列表均只计该仓库                                                             |
| license 社区查询   | `LicenseServiceImpl` 支持按 branch 过滤                                                                                            |

### 2. 评审结论传播（批复 / 撤销）

- `ScanIssue` mongo 文档新增 `reviewId` 字段：提审与继承待审状态时打标，批复/撤销传播按 `scanId + reviewId + 仍待审` 精确定位继承文档（不用 fileHash 宽匹配，避免误伤同文件其他审核单）。
- 批复传播：以审核单 `applyTime` 为起点，定位同仓库（仓库本身 + 全部分支）此后的**全部**版本扫描与 PR 扫描中继承该审核单待审状态的文档，回写批复状态/审核人/时间（approved 时附带澄清信息与确认日期）；`issueId` 等确认绑定字段不随传播写入，避免 (scanId, issueId) 唯一索引冲突。
- 撤销传播：继承文档随绑定文档一起重置为撤销态，清空审核人/申请/澄清信息。
- 传播后统一重算受影响 PR 扫描（tbl_person_scan）的未确认文件数。
- 传播均为 best-effort：失败只记日志，不影响批复/撤销主流程。

### 3. 待审状态继承修复

- 待审单优先于已确认历史：存在可继承待审单时直接继承待审核状态，修复新扫描文档被旧"已通过"历史静默置为 approved 的问题。
- 继承匹配两级：内容完全一致（sourceHash+fileHash）直接继承；PR 修改了文件但未改到匹配行（fileHash 一致、sourceHash 变化）时，以审核单提交时的 PR head 为基线取增量 diff，未命中匹配行才继承，基线无法确定时保守不继承。
- 重复提审守卫：已继承待审（10/20）或已决（30/40）的文档不得重复提审，防止重复审核单经 autoPathReview 自动批复把审核中的问题静默刷成批复状态。
- tbl_issue 全字段匹配继承时主键缺失生成 UUID，避免插入失败中断整批继承。

### 4. GitCode 双域名支持

- 新增 `GitcodeUrlUtil`：`gitcode.domains` 配置逗号分隔域名前缀列表，统一尾斜杠归一化，并校验主域名 `gitcode.url` 必须包含在列表内。
- 替换 `IntegrationApiServiceImpl`（约 20 处）与 `DownLoadFilesUtils` 中散落的单域名 `startsWith` 判定。

### 5. 依赖与工程

- RabbitMQ prod 环境 SSL 协议由 `useSslProtocol()` 改为 `useTlsWithNoVerification()`（免校验 TLS）。
- pom.xml 显式引入 `com.rabbitmq:amqp-client:5.34.0`（与同迭代 PR #329/#330 对齐）。

## 验收标准

- [x] 单元测试通过（ConfirmReviewServceImplTest、ScanCommonServiceImplTest、ManualVersionScanServiceImplTest、OpenPersonDMScanDMServiceImplTest、GitcodeUrlUtilTest 等，CI 已过）。
- [x] CI 流水线通过（`ci-pipeline-passed` 标签）。
- [ ] 手动验证多过滤条件查询（repoName/branchName/scanStatus 多选、branch/repository 过滤）结果正确。
- [ ] 手动验证评审结论传播：批复/撤销后，申请时间至最新扫描之间的继承文档状态与页面未确认数一致。
- [ ] 备用域名仓库可正常扫描与文件删除。

## 影响范围

- 仅 `openlibing-sca` 单仓，34 个文件（+2681 / -115，23 commits），无 DB schema 变更（mongo ScanIssue 新增 `reviewId` 字段为文档级新增，无需迁移）。
- 新增配置项 `gitcode.domains`（有默认值）；RabbitMQ SSL 行为变化仅影响 prod 环境。
- 行为变化：查询接口入参兼容（原单值 scanStatus 语义由集合承载）；评审传播扩大了批复/撤销的影响面（从单文档到申请时间后全部继承文档）。
