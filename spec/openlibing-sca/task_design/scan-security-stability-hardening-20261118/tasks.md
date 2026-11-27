# scan-security-stability-hardening-20261118 — 实现任务

## 进度: 7/7 complete

> 本文档为**回溯 spec**：基于已交付 PR #384（`ms_safe` 分支 16 个 commit）的 diff 复核生成，
> 任务分组按变更主题重组，SHA 为 `ms_safe` 分支上的原始 commit。

- [x] Task 1: queryAll 私仓门禁（Fixes #165，`02228fe6` + `402a5ebb` 部分）
  - `OpenScanServiceImpl#getScanIssueQueryAll` 前置 `prIsOpenSourceRepo(scanId)` 门禁，
    非外部开源仓库返回 `200/查询成功/空列表`
  - `OpenScanServiceImplTest` 新增（+64）：私仓 / 公仓 / 无法归因三场景
- [x] Task 2: auto-confirm 评论归属 + 关键词门禁（Fixes #166，`959e743f` + `d81d7c40` + `402a5ebb` 部分）
  - `PlatformCommentUtil#resolveCommentLogin` → `resolveComment`（返回 `CommentDetail`）：
    平台 v5 PR 评论列表 API 分页拉取（100 条/页 × 10 页），commentId 命中列表才确认归属；
    空响应 / 未命中 / 超页数三分错误语义；未命中短 TTL 缓存（60s / 1024 条）
  - `ConfirmReviewServceImpl#robotAutoConfirm` 关键词门禁：
    `@Value("${sca.auto.confirm.keyword:" + DEFAULT + "}")`（默认 `sca-review-pass`），
    评论内容不含关键词 403
  - `PlatformCommentUtilTest`（+228/−26）、`ConfirmReviewServceImplTest`（+57/−3）同步更新
- [x] Task 3: HTTP 健壮性（`9e780eab` + `9598280c` + `9f693660` + `402a5ebb` 部分）
  - `HttpUtil`：显式超时（connect 5s / socket 10s / 租借 5s）；共享池化单例
    （单路由 32 / 总上限 64，对齐 prScanThreadPool 16 线程）；response try-with-resources；
    JVM shutdown hook；`IllegalStateException` 兜底
  - `IntegrationApiServiceImpl#getPrParams` 空响应重试 500ms 退避
  - `BinaryLicenseEnterUtils` `HttpUtil` 字段注入（`checkRpmLicense` 可测）
  - `HttpUtilTest`（+120/−34）
- [x] Task 4: 克隆重试 + 目录清理语义（Refs #167，`9d1a9343` + `237dda44` + `baeb0d7d`）
  - `DownLoadFilesUtils#runCloneWithRetry`：3 次尝试 + 3s 退避 + 重试前清理半克隆目录
    （清理失败仅告警不中断），接入 `cloneAndCheckoutPR` / `downloadVersion`
  - `deleteDirectoryRecursively`：walk try-with-resources、只读位清除重试、失败条目收集后
    抛 `IOException`（诚实失败）
  - `deleteRepoFromGitcode` / `deletePrErrorFile` 尽力清理；`IntegrationApiListener` 两处
    清理失败不阻断 `basicReject`
  - `DownLoadFilesUtilsTest` 新增（+106，注入式命令执行器不真跑 git）
- [x] Task 5: tbl_issue 批复幂等 + 提审仓库权限（`b22b1f4c` + `de6c45bb`）
  - `OpenScanDMServiceImpl#setIssue`：先查再写 + `DuplicateKeyException` 降级更新；
    更新分支写回本次入参批复值（修复旧对象回写导致批复不生效）；`setCreated(null)`
  - `ScanCommonServiceImpl` 继承落库撞主键降级更新（常见路径零额外 SELECT）
  - `scanConfirmParseV2` 提审前 `checkRepoUserNamePermission` 仓库权限校验（公私仓均校验）
  - `OpenScanDMServiceImplTest` 新增（+169）、`ScanCommonServiceImplTest` 新增（+58）
- [x] Task 6: License / EmailReview 权限校验（`e3c65677` + `7570d06e` + `b3b63ce4`）
  - `LicenseController` `/repos`、`/tree`、`/licenseIssue/query` 新增必传 `userId`；
    社区看板走 `verifyProjectMemberPermission`，tree/query 走 `prDetailAuth`（私有 → 接口方法）；
    导出内部链路走 `doGetScanByCommunity` 不做校验；`PermissionException` 单独 catch
  - `EmailReviewController` `/add`、`/query`、`/delete` 新增必传 `userId`；
    按 `communityId` 走 `verifyCommunityPermission`，delete 经新增
    `TblEmailReviewMapper#selectByIds` 反查社区
  - `LicenseServiceImplTest`（+68/−8）、`LicenseControllerTest`（+51/−10）、
    `EmailReviewControllerTest`（+72/−30）、`EmailReviewServiceImplTest`（+69/−18）
- [x] Task 7: repoId 字段修正（`99d8216f`）
  - `OpenScanServiceImpl` 扫描详情 map：`repoId` 由 `getBranchId()` 改为 `getRepoId()`

## 交付记录

| commit     | 日期       | 摘要                                                                       | 关联        |
| ---------- | ---------- | -------------------------------------------------------------------------- | ----------- |
| `02228fe6` | 2026-11-17 | fix(analysis): block queryAll scan issues for non-public repos             | Fixes #165  |
| `959e743f` | 2026-11-17 | fix(analysis): enforce PR comment keyword gate for auto-confirm            | Fixes #166  |
| `d81d7c40` | 2026-11-17 | fix(analysis): verify comment ownership via PR comment list scan           | Fixes #166  |
| `9e780eab` | 2026-11-17 | fix(analysis): add HTTP client timeouts to prevent gateway 504             | 无 Refs     |
| `9d1a9343` | 2026-11-17 | fix(analysis): add git clone retry fallback for transient network failures | Refs #167   |
| `b22b1f4c` | 2026-11-17 | fix(dm): make issue persistence idempotent in confirm flow                 | 无 Refs     |
| `9598280c` | 2026-11-18 | perf(analysis): reuse shared pooled http client in HttpUtil                | 无 Refs     |
| `237dda44` | 2026-11-18 | fix(analysis): swallow cleanup failure before clone retry                  | Refs #167   |
| `baeb0d7d` | 2026-11-18 | fix(analysis): make repo dir deletion honest and close walk stream         | Refs #167   |
| `402a5ebb` | 2026-11-18 | fix(analysis): address PR #384 review findings except endpoint choice      | review 修复 |
| `b3b63ce4` | 2026-11-18 | feat(dm): add community permission check to email review APIs              | 无 Refs     |
| `e3c65677` | 2026-11-18 | feat(analysis): add project member permission check to license APIs        | 无 Refs     |
| `7570d06e` | 2026-11-18 | refactor(analysis): switch license tree/query auth to prDetailAuth         | 无 Refs     |
| `de6c45bb` | 2026-11-18 | feat(dm): add repo member permission check before confirm review submit    | 无 Refs     |
| `9f693660` | 2026-11-18 | fix(analysis): use injectable HttpUtil field in checkRpmLicense            | 无 Refs     |
| `99d8216f` | 2026-11-18 | 更新repoId（无规范前缀）                                                   | 无 Refs     |

- 分支：`ms_safe`（fork `qq_39751731/openlibing-sca`），目标分支 `release_20261118`，PR #384
  （16 commit，31 文件，+1716/−237，标签 `ai-assisted`）
- **落地状态**：PR #384 已关闭且未合入 `release_20261118`；内容重落 `master`：
  - `feat-auth-hardening`（!386 / !388）：`5e91b31f`（permission checks and security gates
    from ms_safe）+ `718080d8`（review findings）+ `b7f1119d`（resolve projectId by
    communityName，ShieldRoleServiceImpl，关联后续加固）
  - `fix-robustness-perf`（!387）：`7243dca1`（harden HTTP and clone robustness with JVM
    options）+ `28f756d3`（review findings）
  - `master` 上已验证关键改动存在（`sca.auto.confirm.keyword`、`runCloneWithRetry` grep 命中）

## 验证方式

- 本轮为回溯文档，基于 `git diff df544c86..99d8216f` 复核 + 静态核验生成，
  **未执行 `mvn test`**（回溯场景 + 避免写入 `target/`）；
- PR 测试计划中已勾选「单元测试通过」「PR 流水线编译与 UT 门禁通过」；
  以下手动验证项**未确认**（PR body 中为未勾选状态）：
  - 私仓 scanId 调 queryAll 返回空列表
  - 非 committer / 无关键词 / 其他 PR 评论 ID 重放均 403
  - 瞬时断网下 PR/版本扫描克隆重试成功
- 以下部署前提**未验证**：
  - 服务端 `sca.auto.confirm.keyword` 配置就位（存量触发评论必须含关键词）
  - 前端 / License、EmailReview 调用方已适配必传 `userId`

## 未覆盖项

- auto-confirm 机机认证 / 防重放（签名 + 时间戳）、`prUrl` 频控、批量条数上限、
  评论与目标 scan 版本绑定（#146/#166 遗留延续）
- queryAll 未改造为按用户授权的鉴权接口（维持可见性门禁思路）
- clone 断点续传 / HTTP 协议升级（保持重试兜底路线）
- 批复幂等无版本号控制，消息重投场景 last-write-wins
