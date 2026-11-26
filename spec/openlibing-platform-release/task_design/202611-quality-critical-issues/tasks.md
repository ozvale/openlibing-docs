# tasks：质量管理——关键问题统计（缺陷/资料/需求交付率）与单包重试发布

## 一期：缺陷/资料关键问题数统计（2026-11-20 交付）

- [x] 1. 新增 dto/vo：QualitySummaryDTO、QualityDetailDTO、QualitySummaryVO、QualityIssueVO、缓存对象 QualityCacheModel
- [x] 2. 新增 GitCode issue 查询封装：分页拉取 issue + 本地按类型/label/优先级过滤
- [x] 3. 新增 QualityService(+Impl)：仓集合收集（reviewId 反查去重）、统计、Redis 缓存读写、明细查询
- [x] 4. 新增 QualityController：summary/detail 两个接口 + @ProjectPermission + 参数校验
- [x] 5. ReleaseBaseServiceImpl 提交评审成功后异步触发统计
- [x] 6. 单元测试：过滤口径、缓存逻辑、越权校验
- [x] 7. 本地构建 + 相关测试通过（gitcode-dev-quality）
- [x] 8. commit 交付，用户自测

## 二期：需求交付率与单包重试发布（2026-11-26 交付，PR #271）

- [x] 9. 关键问题汇总新增「需求交付率」：issue 改为 state=all 全量拉取，需求类口径（类型或 label 命中 需求/requirement）
- [x] 10. 特殊值口径：无制品信息返回 -1；有制品无需求 issue（分母 0）返回 0
- [x] 11. 汇总接口透出病毒扫描状态（virusScanStatus）与验签结果（verifyResult）
- [x] 12. 缓存收敛为评审单维度 2 分钟（QualityCacheModel 增加 requirementTotal/ClosedCount）
- [x] 13. 明细接口返回按制品包分组结构（QualityDetailGroupVo）
- [x] 14. 发布决策支持单个软件包重试发布（retryArtifactRelease：失败记录清理 + 成功幂等 + 状态抢占）
- [x] 15. tag 描述改为非必填
- [x] 16. openlibing-common SDK 升级 1.0.21.6（cherry-pick 至 release_security_202611，PR #270）
- [x] 17. QualityServiceImplTest 833 行（增量行覆盖率 81%）+ ReleaseDecisionServiceImplTest 单包重试用例
- [x] 18. fork PR 交付：#271（master）、#269（release-20261130-rc1）、#270（security 分支）

## 遗留

- [ ] 发布决策状态机竞态窗口加固（issue #140/#141，CWE-362）：发布中可重复触发、撤回与异步回调竞态——方案已评审，待排期实施
