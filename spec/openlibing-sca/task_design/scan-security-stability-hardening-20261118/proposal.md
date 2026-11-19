# scan-security-stability-hardening-20261118 — 扫描安全门禁、auto-confirm 校验加固与克隆/HTTP 健壮性（#165 #166 #167）

## 交付载体

- 关联 PR：[openlibing/openlibing-sca#384](https://gitcode.com/openlibing/openlibing-sca/pull/384)
  `fix(analysis): 扫描安全门禁、自动确认校验加固与克隆/HTTP 健壮性 (#165 #166 #167)`
  （`ms_safe` → `release_20261118`，16 commit，31 文件，+1716/−237，标签 `ai-assisted`）
- 落地状态：PR #384 已关闭且未合入 `release_20261118`；内容重落 `master`：
  - 安全门禁与权限校验经 `feat-auth-hardening`（!386 / !388，主提交 `5e91b31f`、`718080d8`、`b7f1119d`）
  - HTTP/克隆健壮性经 `fix-robustness-perf`（!387，主提交 `7243dca1`、`28f756d3`）
- 关联 Issue：
  - [Fixes #165](https://gitcode.com/openlibing/openlibing-sca/issues/165)（安全 / 敏感信息泄露，高危）
  - [Fixes #166](https://gitcode.com/openlibing/openlibing-sca/issues/166)（安全 / 授权校验不充分 CWE-863，高危；#146 的后续加固）
  - [Refs #167](https://gitcode.com/openlibing/openlibing-sca/issues/167)（缺陷 / 克隆网络瞬时失败）

## 需求背景

### #165 queryAll 无鉴权接口私仓扫描结果泄露

`POST /open/scan/scanIssue/queryAll` 为机机接口，无鉴权，仅凭 `scanId` 即可全量返回该扫描的
license、copyright、漏洞、依赖成分、文件路径等全部问题明细。修复前对**私仓**扫描记录同样直接
返回，无任何仓库可见性校验。任何能访问该服务的调用方拿到或枚举到私仓 `scanId`，即可拉取私仓
完整扫描问题清单。

### #166 auto-confirm 触发校验不充分

`POST /open/review/auto-confirm` 在 #146 修复（评论 `commentId` 反查作者 + committer 校验）后，
评论**内容**仍未校验：`PlatformCommentUtil#resolveCommentLogin` 只解析评论作者 `user.login`，
是否包含触发关键词完全依赖客户端 sca-action 判断。任何拿到 committer 在该 PR 上任意一条普通
评论（如 "LGTM"、"已处理"）的 `commentId` 的调用方，即可触发批量批复，把门禁拦截的未确认问题
全部"合法化"——committer 的无意评论被升级为有效授权指令。

此外单条评论 API（`/issues/{pr}/comments/{commentId}`）实测不返回评论归属信息，无法证明评论
确实属于目标 PR，归属校验缺失。

### #167 git clone 网络瞬时中断导致扫描失败

PR cann/ops-transformer#15931 SCA 扫描失败：`git clone --depth 1` 传输约 3 分钟后
`RPC failed; curl 18 transfer closed with outstanding read data remaining` / `early EOF`，
同一时段多仓出现同样错误且随后同仓克隆成功，属 Pod 到 gitcode.com 的间歇性网络抖动。根因：

1. `--depth 1` 只减少历史传输，大仓单快照 packfile 仍很大，smart HTTP 单连接不可续传，
   长传输窗口撞上抖动概率高；
2. `DownLoadFilesUtils#cloneAndCheckoutPR` / `downloadVersion` 中 clone 失败一次即抛
   `ScaException`，无重试兜底。

### PR 附加加固项（无独立 Issue）

| 加固项                       | 背景                                                                                                                                        |
| ---------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| HTTP 客户端超时 + 连接池化   | `HttpUtil#doGet` 无 connect/socket 超时且每次请求新建并关闭 client，连接泄漏拖垮线程；触发 apig 网关 504（PR 7551 案例）                    |
| `getPrParams` 空响应重试退避 | 连续 3 次慢请求无间隔串行叠加放大总耗时                                                                                                     |
| `tbl_issue` 批复落库幂等     | 确定性 issueId 在扫描重跑/消息重投时撞主键中断整批复继；`setIssue` 更新分支把库中旧对象原样写回，批复值不生效，已确认问题在后续扫描重复弹审 |
| License API 权限校验         | `/license/repos`、`/license/tree`、`/license/licenseIssue/query` 无用户级权限校验                                                           |
| EmailReview API 权限校验     | `/email/review/add`、`/query`、`/delete` 无社区横向权限校验                                                                                 |
| 确认提审仓库权限校验         | `scanConfirmParseV2` 提交审核前未校验提交人对仓库的操作权限                                                                                 |
| repoId 字段修正              | 扫描详情返回的 `repoId` 误取 `branchId`                                                                                                     |

## 功能描述

**做什么**：

1. **queryAll 私仓门禁（#165，fail-closed）**：`getScanIssueQueryAll` 查询前按
   `scanId → repoId → repo_info.visibility` 判定仓库可见性，仅**外部开源**仓库返回明细；
   私有 / 内部开源 / 无法归因仓库一律返回空列表（复用既有 `prIsOpenSourceRepo` 门禁）。
2. **auto-confirm 双重校验（#166，fail-closed）**：
   - 评论归属硬校验：反查改用平台 v5 PR 评论列表 API（`/pulls/{number}/comments`）分页拉取，
     `commentId` 必须命中列表才确认归属当前 PR；未命中 / 空列表 / 超页数上限一律 403；
   - 触发关键词校验：评论内容必须包含服务端配置 `sca.auto.confirm.keyword`（默认
     `sca-review-pass`，不信任调用方声明），不含关键词一律 403；
   - 身份校验保留：评论作者必须为该仓库 committer；
   - 未命中短 TTL 缓存（60s / 1024 条）：确认未命中的 `prUrl|commentId` 重放直接 403，
     防无鉴权机机接口的请求放大。
3. **克隆重试兜底（#167）**：`DownLoadFilesUtils#runCloneWithRetry` 最多 3 次尝试 + 3s 退避 +
   重试前清理半克隆目录，接入 `cloneAndCheckoutPR`（PR 扫描）与 `downloadVersion`（版本扫描）；
   清理失败仅告警不中断重试；`deleteDirectoryRecursively` 删除失败先清只读位重试、`walk()` 改
   try-with-resources、真删不掉如实抛 `IOException`。
4. **HTTP 健壮性**：`HttpUtil#doGet` 显式超时（connect 5s / socket 10s / 租借 5s）、
   `CloseableHttpClient` 提升为共享池化单例（单路由 32 / 总上限 64）、response
   try-with-resources 修复连接泄漏、捕获池关闭后的 `IllegalStateException`；
   `getPrParams` 空响应重试间加 500ms 退避。
5. **批复幂等（fix(dm)）**：`tbl_issue` 落库统一幂等——先查再写，`DuplicateKeyException`
   降级为更新；更新分支写回**本次入参批复值**（修复旧对象回写导致批复不生效），更新不覆盖
   创建时间。
6. **权限校验扩展**：
   - License 三个接口新增必传 `userId`：社区看板走 `verifyProjectMemberPermission`
     （项目成员或 admin / platform_operater），`/tree`、`/licenseIssue/query` 走
     `prDetailAuth`（scanId → 归属仓库 → 框架服务校验）；
   - EmailReview 三个接口新增必传 `userId`：按 `communityId` 走
     `verifyCommunityPermission` 横向校验，`/delete` 反查待删记录所属社区后逐一校验；
   - `scanConfirmParseV2` 提审前经框架服务校验提交人对仓库的操作权限（公私仓均校验）；
   - `prDetailAuth` 由私有提升为 `OpenScanService` 接口方法供跨服务复用。
7. **repoId 修正**：扫描详情返回 map 中 `repoId` 由 `getBranchId()` 改为 `getRepoId()`。

**不做什么**：

- queryAll 未改造为带鉴权的按用户授权接口（仍是无鉴权机机接口 + 可见性门禁的思路）；
- auto-confirm 未实现机机签名 / token + 时间戳防重放、`prUrl` 频控与批量条数上限
  （#146 P0/P1 遗留项延续）；未绑定评论与目标 scan 版本（历史关键词评论仍可重放）；
- 克隆重试未引入断点续传 / HTTP v2 协议升级（保持 smart HTTP + 重试消化瞬时抖动）；
- License/EmailReview 权限模型沿用既有 `verifyProjectMemberPermission` /
  `verifyCommunityPermission` / `prDetailAuth`，未新增角色或数据权限维度。

## 验收标准

### #165（对应 issue 验收项）

- [x] 私仓 scanId 调用 queryAll 返回空列表，不泄露任何问题明细
      （`getScanIssueQueryAll` 前置 `prIsOpenSourceRepo` 门禁，非公仓返回
      `200/查询成功/空列表`；`OpenScanServiceImplTest` 覆盖）
- [x] 公仓 scanId 调用 queryAll 行为与现状一致（`visibility=外部开源` 放行）
- [x] scanId 无法归因到仓库时返回空（fail-closed）：`prIsOpenSourceRepo` 在
      person/版本扫描记录均缺失、repoInfo 缺失时返回 false
- [x] 相关单元测试覆盖三种场景（`OpenScanServiceImplTest` 新增 +64 行）
- 注：实现口径**严于** issue 草案——issue 写"私有返回空、内部开源放行（口径与安全运营确认）"，
  实现仅放行 `REPO_EXTERNAL`（外部开源），内部开源仓调用方将拿到空列表（见 design.md 风险表）

### #166（对应 issue 验收项）

- [x] committer 发表包含触发关键词的评论 → 自动确认成功
      （`robotAutoConfirm` 关键词 + committer 双门禁顺序通过）
- [x] committer 发表不含关键词的普通评论，以其 commentId 调用接口 → 403，不产生任何审核数据变更
      （`ScaException(403, "权限校验失败，评论缺少自动确认触发关键词", ...)`）
- [x] 非 committer 评论（含伪造身份请求）→ 403（`checkCommitterPermission` 保留）
- [x] 评论内容解析失败/为空 → 403（fail-closed）
- [x] 评论归属校验：其他 PR 的评论 ID 调用接口 → 403（评论列表命中校验，#166 需求第 1 条延伸）
- [x] 相关单元测试覆盖（`PlatformCommentUtilTest` +228/−26、`ConfirmReviewServceImplTest` +57/−3）
- 注：PR 测试计划中"非 committer / 无关键词 / 其他 PR 评论 ID 重放均 403"的**手动验证项未确认**
  （PR body 中为未勾选状态）；关键词配置 `sca.auto.confirm.keyword` 服务端就位情况未验证

### #167（对应 issue 验收项）

- [x] clone 因瞬时网络失败时自动重试，最多 3 次，带 3s 短退避（`runCloneWithRetry`）
- [x] 每次重试前清理半克隆目录，避免 `destination path already exists`
      （清理失败仅告警不中断重试）
- [x] 全部尝试失败后行为与现状一致（抛 `ScaException`，错误信息含最后一次输出）
- [x] 成功路径不增加额外命令执行（重试仅在失败后触发）
- [x] 补充最小单元测试（注入式命令执行器，不真跑 git；`DownLoadFilesUtilsTest` 新增 +106 行）
- 注：PR 测试计划中"瞬时断网下 PR/版本扫描克隆重试成功"手动验证项未确认

### 附加加固项

- [x] `HttpUtil#doGet` 显式超时并复用池化 client，response 关闭（`HttpUtilTest` +120/−34）
- [x] `getPrParams` 空响应重试间 500ms 退避
- [x] `tbl_issue` 幂等落库：先查再写 + `DuplicateKeyException` 降级更新；更新写回本次批复值
      （`OpenScanDMServiceImplTest` 新增 +169 行、`ScanCommonServiceImplTest` 新增 +58 行）
- [x] License / EmailReview / 确认提审权限校验及配套单测
      （`LicenseServiceImplTest`、`LicenseControllerTest`、`EmailReviewControllerTest`、
      `EmailReviewServiceImplTest`）
- [x] 扫描详情 `repoId` 取值修正

## 影响范围

- 业务仓：`openlibing-sca`
  - `analysis` 模块：`OpenScanServiceImpl` / `OpenScanService` / `LicenseController` /
    `LicenseServiceImpl` / `LicenseService` / `ConfirmReviewServceImpl` / `HttpUtil` /
    `DownLoadFilesUtils` / `BinaryLicenseEnterUtils`
  - `dm` 模块：`OpenScanDMServiceImpl` / `ScanCommonServiceImpl` / `EmailReviewController` /
    `EmailReviewServiceImpl` / `EmailReviewService` / `TblEmailReviewMapper`（接口 + XML）/
    `IntegrationApiServiceImpl` / `ScanCommonServiceImpl`
  - `common` 模块：`PlatformCommentUtil` / `IntegrationApiListener`
- **接口契约变化（破坏性，调用方需同步）**：
  - `GET /license/repos`、`GET /license/tree`、`POST /license/licenseIssue/query` 新增**必传**
    `userId` 请求参数；
  - `POST /email/review/add`、`POST /email/review/query`、`POST /email/review/delete` 新增**必传**
    `userId` 请求参数；
  - 前端 / 调用方不传 `userId` 将 400；
- 行为变化（fail-closed 收紧）：
  - queryAll 对私有 / 内部开源 / 无法归因仓库返回空列表；
  - auto-confirm 仅接受包含触发关键词（`sca-review-pass` 或服务端配置值）的 committer 评论；
- 配置：新增可选配置项 `sca.auto.confirm.keyword`（默认 `sca-review-pass`，变更需与
  sca-action 同步）；
- 外部依赖：平台 v5 PR 评论列表 API（`/pulls/{number}/comments`，替代单条评论 API）；
  框架服务 `checkRepoUserNamePermission` / `verifyProjectMemberPermission` /
  `verifyCommunityPermission`（均为既有能力复用）；
- 数据库 schema：无变化（无 Liquibase 变更集）。
