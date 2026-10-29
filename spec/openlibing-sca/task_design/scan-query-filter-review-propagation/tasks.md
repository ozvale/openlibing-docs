# 扫描查询多过滤与评审结论传播 — 实现任务

## 进度: 6/8 complete

- [x] 查询过滤：人工版本扫描 repoName/branchName/scanStatus 集合化（Mapper XML IN 条件）、repoBranchList 下拉选接口（selectDistinct 去重）、社区扫描 branch 过滤、社区 PR 扫描 repository 过滤（统计与列表同口径）、license 社区查询 branch 过滤
- [x] 评审传播：ScanIssue 新增 reviewId 打标、selectUnderReviewByScope 联查查询、批复传播（applyTime 后全部版本+PR 扫描继承文档回写）、撤销传播（重置继承文档）、受影响 PR 扫描未确认数统一重算
- [x] 待审继承修复：待审单优先于已确认历史（防静默置为 approved）、两级匹配 + PR head 基线守卫、重复提审守卫（非 "00" 状态跳过）、tbl_issue 继承 UUID 主键修复
- [x] 双域名：GitcodeUrlUtil（gitcode.domains 多域名 + 尾斜杠归一化 + 主域名校验），替换 IntegrationApiServiceImpl 约 20 处与 DownLoadFilesUtils 的单域名判定
- [x] 依赖：RabbitMQ prod 免校验 TLS（useTlsWithNoVerification）、amqp-client 5.34.0 显式引入
- [x] 单测：ConfirmReviewServceImplTest（+约 640 行）、ScanCommonServiceImplTest（+约 340 行）、OpenPersonDMScanDMServiceImplTest（+约 180 行）等 9 个测试类新增/适配；CI 流水线通过（`ci-pipeline-passed`）
- [x] 创建 PR #328（`ms_succeed` → `release_20261019_iter1`，23 commits），已打 `ai-assisted` 标签
- [ ] 手动验证多过滤条件查询结果正确
- [ ] 手动验证评审结论传播行为（批复/撤销后继承文档状态与未确认数一致）

## 关联

- 业务 PR: https://gitcode.com/openlibing/openlibing-sca/pull/328
- 分支: `ms_succeed` → `release_20261019_iter1`
- 关联 Issue: openlibing/openlibing-sca#88
- 关联子需求 spec: review-pending-state-consistency / review-propagate-person-scan-count / review-mongo-compensation
- 同迭代关联 PR: #329（NOTICE 扫描迭代）、#330（Gitee token Bearer 化）
