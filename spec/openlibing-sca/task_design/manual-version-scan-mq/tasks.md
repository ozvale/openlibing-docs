# 实现任务清单

## Phase 3：编码与验证

- [ ] T1：修改 `IntegrationApiServiceImpl`
  - [ ] T1.1：新增常量 `private static final long MANUAL_REPO_SIZE = 10_000_000L;`（紧邻 `REPO_SIZE`）
  - [ ] T1.2：修改 `startVersionScan(versionScanPo, isManualScan)`：把 `RepoInfoEntity repoInfoEntity = repoInfoMapper.queryById(...)` 提到 `if (isManualScan)` 之前；`isManualScan=true` 分支改为调用新增 `sendManualScanToMqBasedOnRepoSize`，`else` 分支保留 `sendToMqBasedOnRepoSize`
  - [ ] T1.3：新增 `sendManualScanToMqBasedOnRepoSize(versionScanPo, scanRequestVO, repoInfoEntity, msg)`，方法体镜像 `sendToMqBasedOnRepoSize`，但调用 `checkManualRepoSizeAndSendToMq` 而非 `checkRepoSizeAndSendToMq`
  - [ ] T1.4：新增 `checkManualRepoSizeAndSendToMq(url, msg)`，方法体镜像 `checkRepoSizeAndSendToMq`，但阈值用 `MANUAL_REPO_SIZE`、路由到 `amq_version_manual_big_direct` / `amq_version_manual_small_direct`，异常 / 非 200 兜底走 `amq_version_manual_big_direct`
- [ ] T2：修改 `IntegrationApiListener`
  - [ ] T2.1：删除 `receivedVersionManualMessage` 方法（原单一 manual queue listener）
  - [ ] T2.2：新增 `receivedVersionManualBigMessage`，绑定 `amq_version_manual_big_direct` / `version_manual_big_rout_key` / `version_manual_big_queue`，方法体与 `receivedVersionBigMessage` 完全一致
  - [ ] T2.3：新增 `receivedVersionManualSmallMessage`，绑定 `amq_version_manual_small_direct` / `version_manual_small_rout_key` / `version_manual_small_queue`，方法体与 `receivedVersionSmallMessage` 完全一致
  - [ ] T2.4：Javadoc 注释更新，移除"由 startVersionScan 投递到 amq_version_manual_direct"等旧描述，改为"按仓库 size 路由到 manual_big / manual_small"
- [ ] T3：更新 `IntegrationApiServiceImplTest`
  - [ ] T3.1：把原 `testStartVersionScan_ManualScanTrue_RoutesToManualQueue` 改为 `testStartVersionScan_ManualScanTrue_CallsSendManualScanToMqBasedOnRepoSize`：spy + verify `sendManualScanToMqBasedOnRepoSize` 被调用，verify `sendToMqBasedOnRepoSize` 未被调用
  - [ ] T3.2：新增 `testCheckManualRepoSizeAndSendToMq_Big`：response body length > 10MB → `convertAndSend` 被调用且参数为 `amq_version_manual_big_direct` / `version_manual_big_rout_key`
  - [ ] T3.3：新增 `testCheckManualRepoSizeAndSendToMq_Small`：response body length ≤ 10MB → `convertAndSend` 参数为 `amq_version_manual_small_direct` / `version_manual_small_rout_key`
  - [ ] T3.4：新增 `testCheckManualRepoSizeAndSendToMq_ExceptionFallbackBig`：HTTP 异常时兜底 `amq_version_manual_big_direct`
- [ ] T4：更新 `IntegrationApiListenerTest`
  - [ ] T4.1：删除 `receivedVersionManualMessage` 相关测试
  - [ ] T4.2：新增 `receivedVersionManualBigMessage_Success` / `_Failure`（复用 big 队列测试 mock 结构）
  - [ ] T4.3：新增 `receivedVersionManualSmallMessage_Success` / `_Failure`（复用 small 队列测试 mock 结构）
- [ ] T5：运行 `mvn test` 全量验证
- [ ] T6：pre-commit 检查（Spotless / CheckStyle / SpotBugs / PMD）
- [ ] T7：提交 commit，消息：
  ```
  feat(dm): split manual version scan into manual big/small queues by 10MB

  在第一版单一 version_manual_queue 基础上，对手动版本扫描按仓库 size 分流：
  > 10MB 走 amq_version_manual_big_direct / version_manual_big_queue，
  ≤ 10MB 走 amq_version_manual_small_direct / version_manual_small_queue，
  阈值 MANUAL_REPO_SIZE=10MB 与自动扫描侧 REPO_SIZE=5MB 解耦。

  - 新增 MANUAL_REPO_SIZE 常量、sendManualScanToMqBasedOnRepoSize、
    checkManualRepoSizeAndSendToMq 方法，行为镜像自动扫描侧
  - 删除 receivedVersionManualMessage（单一 manual queue listener），新增
    receivedVersionManualBigMessage / receivedVersionManualSmallMessage
  - 旧 version_manual_queue 变孤儿，部署前由运维 drain 后清理
  - ManualVersionScanServiceImpl#L214 调用签名不变

  Refs #64

  Co-authored-by: Trae <noreply@trae.ai>
  Generated-by: GLM-5.2
  ```

## Phase 4：业务 PR（用户自测后）

- [ ] P1：用户在本地启动应用，验证 `POST /version/scan/startVersionScan` 按 size 路由到 `version_manual_big_queue` / `version_manual_small_queue`
- [ ] P2：用户确认 `tbl_manual_version_scan.scan_status` 流转正常
- [ ] P3：用户明确确认完成后，创建业务 PR
  - [ ] P3.1：`gitcode pr create -R openlibing/openlibing-sca --title "feat(dm): split manual version scan into manual big/small queues by 10MB" --body-file ... --base master`
  - [ ] P3.2：`gitcode pr edit <n> -R openlibing/openlibing-sca --labels ai-assisted`
  - [ ] P3.3：PR body 关联 `Refs #64`

## Phase 4：docs PR（业务 PR 创建后）

- [ ] D1：在 openlibing-docs 仓基于 origin/master 新建分支 `spec-openlibing-sca-manual-version-scan-mq`
- [ ] D2：将更新后的 `spec/openlibing-sca/task_design/manual-version-scan-mq/{proposal,design,tasks}.md` 提交
- [ ] D3：`gitcode pr create -R openlibing/openlibing-docs --title "docs(spec/openlibing-sca): manual-version-scan-mq 按size分大小队列迭代" --body-file ... --base master`
- [ ] D4：PR body 关联业务仓 issue `Refs openlibing/openlibing-sca#64`

## Phase 5：归档（用户触发）

- [ ] A1：补充 `archive.md`，记录最终落地状态、验证证据、经验沉淀
- [ ] A2：将 archive.md 通过 docs PR 提交到 openlibing-docs 主干
- [ ] A3：在 Issue #64 评论区发布最终归档链接并关闭 Issue
