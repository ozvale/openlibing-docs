# scan-security-stability-hardening-20261118 — 技术设计

## 方案概述

一个 PR 覆盖三类目标，全部以 **fail-closed** 为取向：

1. **安全门禁**：无鉴权机机接口（queryAll / auto-confirm）与用户侧查询接口（License /
   EmailReview / 确认提审）补齐可见性与授权校验；
2. **稳定性兜底**：git clone 重试、目录清理语义修复、HTTP 超时与连接池化；
3. **正确性修复**：`tbl_issue` 批复幂等落库、repoId 字段取值修正。

## 变更设计

### 1. queryAll 私仓门禁（#165）

```
POST /open/scan/scanIssue/queryAll { scanId, ... }
  └─ OpenScanServiceImpl#getScanIssueQueryAll
       ├─ scanId 为空 → 空列表（现状保留）
       ├─ prIsOpenSourceRepo(scanId)                    ← 复用既有门禁方法
       │    ├─ tbl_person_scan 按 scanId 查（优先）
       │    ├─ 缺失 → tbl_scan 兜底
       │    ├─ 两者均缺 / repo_info 缺失 → false（fail-closed）
       │    └─ repo_info.visibility == REPO_EXTERNAL（外部开源）→ true
       ├─ false → 返回 200/"查询成功"/空列表 + INFO 日志
       └─ true  → 按 Mongo criteria 正常返回明细
```

- 门禁复用既有 `prIsOpenSourceRepo`（`OpenScanServiceImpl` L1042），零新增查询链路；
- 返回 `200 + 空列表` 而非 403：不向无鉴权调用方暴露"该 scanId 属于私仓"的事实，
  且保持机机调用方兼容；
- **口径决策**：仅 `REPO_EXTERNAL` 放行，内部开源仓同样返回空。issue #165 草案写
  "私有返回空、内部开源放行（口径与安全运营确认）"，实现取更严格口径，作为显式决策记录。

### 2. auto-confirm 评论归属 + 关键词门禁（#166）

```
POST /open/review/auto-confirm { scanId, prUrl, commentId }
  └─ ConfirmReviewServceImpl#robotAutoConfirm
       ├─ scanId → repoId（未就绪 → ScaException 60000）
       ├─ PlatformCommentUtil.resolveComment(prUrl, commentId, repoId) → CommentDetail(login, body)
       │    ├─ prUrl/commentId 非空；未命中短 TTL 缓存（prUrl|commentId → 过期时间戳）
       │    ├─ repoId → RepoInfoEntity（缺 projectId → 403）
       │    ├─ prUrl 前缀判定平台（gitee / gitcode）→ 取该平台 token 与 API base
       │    ├─ 分页 GET {apiBase}/repos/{owner}/{repo}/pulls/{prNumber}/comments
       │    │    ?page={1..10}&per_page=100
       │    │    ├─ 空响应 → 403「评论查询失败」（token 失效/限流/5xx，与未命中区分）
       │    │    ├─ commentId 命中列表 → 取 user.login + body，清未命中缓存，返回
       │    │    ├─ 不足一页即末页未命中 → 403「评论与PR不匹配」，记入未命中缓存
       │    │    └─ 翻满 10 页未命中 → 403（页数上限单独文案），记入未命中缓存
       │    └─ 命中但作者为空 / 其他异常 → 403（fail-closed）
       ├─ 评论内容不含 resolveAutoConfirmKeyword()
       │    → 403「评论缺少自动确认触发关键词」
       │    （@Value("${sca.auto.confirm.keyword:" + DEFAULT_AUTO_CONFIRM_KEYWORD + "}")，
       │      默认 sca-review-pass，编译期常量拼接避免两处字面量分叉；
       │      配置空白时回退默认值）
       ├─ checkCommitterPermission(repoId, comment.getLogin())（#146 既有门禁保留）
       └─ 建单/重绑待审单 → autoPathReview 机器人批复 → total/confirmed/remaining
```

- **归属校验改列表命中**：单条评论 API（`/issues/{pr}/comments/{commentId}`）实测不返回
  归属信息，不可作为依据；列表 API 路径绑定 PR，commentId 命中列表才证明归属当前 PR；
- **错误语义三分**：空响应（查询失败）/ 未命中（归属不匹配）/ 超页数（上限提示）分开报错，
  避免把网络/鉴权故障误判为 commentId 归属错误，便于排障；
- **防请求放大**：无鉴权机机接口重放固定翻 10 页平台 API 的成本高；确认未命中记入
  `ConcurrentHashMap` 短 TTL 缓存（TTL 60s，容量 1024，超限先清过期再整体清空），
  TTL 内重放直接 403；命中后清缓存（平台评论可见性短暂延迟时不误拒合法重试）；
- **页数上限**：`COMMENT_PAGE_SIZE=100` × `COMMENT_MAX_PAGES=10`，PR 评论超 1000 条时
  即使 committer + 关键词也会 403（显式文案提示减少 PR 评论）。

### 3. 克隆重试兜底（#167）

```java
// DownLoadFilesUtils（包级可见，便于单测）
static EnumMap<CmdResultInfo, Object> runCloneWithRetry(
    Supplier<EnumMap<CmdResultInfo, Object>> cmdRunner,   // 注入式命令执行器
    Runnable cleanupBeforeRetry,                          // 重试前删半克隆目录
    int maxAttempts,                                      // CLONE_MAX_ATTEMPTS = 3
    long backoffMillis)                                   // CLONE_RETRY_BACKOFF_MILLIS = 3000
```

- 接入两条链路：`cloneAndCheckoutPR`（PR 扫描，cleanup 目标 `repoFilePath`）与
  `downloadVersion`（版本扫描，cleanup 目标 `workspace`）；
- 清理失败仅 WARN 不中断重试：半克隆残留时 git clone 以克隆语义失败，调用方按克隆错误
  统一抛错；避免只读 pack 文件、被 git 子进程短暂占用的句柄等瞬时删除失败以
  「删除文件夹失败」覆盖真实克隆根因；
- `Thread.sleep` 中断时恢复中断位并停止重试，返回最后一次结果；
- 全部失败返回最后一次 `CmdResultInfo`，调用方按现状抛 `ScaException`（错误信息含最后输出）；
- 成功路径零额外命令（重试仅在失败后触发）。

**目录清理语义修复（配套）**：

- `deleteDirectoryRecursively`：
  - `walk()` 改 try-with-resources——walk 持有目录句柄，不关闭则 Windows 上目录本身删不掉；
  - 删除失败先 `setWritable(true)` 清只读位重试（git pack 等文件带只读位）；
  - 失败条目收集后抛 `IOException`——**不允许静默假成功**，否则残留目录使后续 clone 以
    `destination exists` 失败且无告警指向删除问题；
- `deleteRepoFromGitcode` / `deletePrErrorFile`：改为尽力清理语义——`ScaException` 捕获后
  WARN 不上抛。调用方含扫描成功收尾与 MQ 异常处理（`basicReject` 前），删除失败若上抛会把
  成功扫描误标失败、或跳过 `basicReject` 造成消息重投；残留目录由下次克隆前的
  `deleteFolder` 兜底清理；
- `IntegrationApiListener` 两处（`prSamllLisenter` / `receivedPrBigMessage`）：清理调用包
  try-catch，失败不阻断 `basicReject`。

### 4. HTTP 健壮性

`HttpUtil`（非 Spring Bean，静态工具类）：

| 项                         | 值      | 理由                                                                            |
| -------------------------- | ------- | ------------------------------------------------------------------------------- |
| connect timeout            | 5000ms  | 对端不可达快速失败，避免阻塞至 OS 级 TCP 超时（Linux 默认约 127s）              |
| socket timeout             | 10000ms | 慢响应不长期占用调用线程                                                        |
| connection request timeout | 5000ms  | 池租借排队上限                                                                  |
| 单路由上限                 | 32      | PR 扫描线程池峰值 16 线程并发访问同一 GitCode 域名，默认值 2 会在租借处排队超时 |
| 总上限                     | 64      | 与单路由成比例                                                                  |

- `CloseableHttpClient` 提升为类级共享单例（`volatile` + 线程安全），跨请求复用连接池与
  TLS 会话；此前每次 `doGet` 新建并关闭 client，重对象反复重建且连接无法复用；
- response 改 try-with-resources（修复连接泄漏，apig 网关 504 的 PR 7551 案例）；
- 非 Spring Bean 无容器生命周期回调，经 JVM `addShutdownHook` 释放连接池（幂等）；
- 捕获 `IllegalStateException`（池 shutdown 后并发 execute），维持
  "任何请求侧失败都返回空 body" 的既有契约；
- `BinaryLicenseEnterUtils#checkRpmLicense`：`HttpUtil` 由方法内就地实例化改为字段注入，
  便于单测 `@InjectMocks`；
- `IntegrationApiServiceImpl#getPrParams`：空响应重试间 `Thread.sleep(500)`，避免连续
  3 次慢请求无间隔串行叠加放大总耗时。

### 5. tbl_issue 批复幂等落库

两条落库路径统一为「先查再写 + DuplicateKeyException 降级更新」：

| 路径                                         | 修复点                                                                                                                                                                                                                                                                                                                                  |
| -------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `OpenScanDMServiceImpl#setIssue`（批复落库） | 存在记录时**写回本次入参 issue**（含本次 reviewStatus/committerType/clarifyType），不再把库中旧对象原样写回——旧写回导致批复对 tbl_issue 不生效，继承链路按 tbl_issue 重建 Mongo 文档时回读旧状态，已确认问题在后续扫描重复弹审；`setCreated(null)` 不覆盖创建时间；插入撞主键（并发 TOCTOU）降级更新，语义对齐 Mongo 侧 E11000 降级重试 |
| `ScanCommonServiceImpl`（扫描结果继承落库）  | 裸插入改 try-catch：常见「不存在」路径直接插入（零额外 SELECT，避免逐条查询 N+1），`DuplicateKeyException` 降级为更新——确定性 issueId 在扫描重跑/消息重投时可能已存在，撞主键会中断整批继承                                                                                                                                             |

配套：`OpenScanDMServiceImpl#scanConfirmParseV2` 提审前校验提交人仓库权限——
`repoInfoMapper.queryById` 取仓库（缺失 403），`openlibingFrameworkClient
.checkRepoUserNamePermission(userId, repoInfo)` 不通过则 403「当前用户无该仓库操作权限」
（不区分公私仓，均校验）。

### 6. License / EmailReview 权限校验扩展

| 接口                               | 校验方式                                                         | 说明                                                                                                                  |
| ---------------------------------- | ---------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| `GET /license/repos`               | `commonService.verifyProjectMemberPermission(userId, projectId)` | 项目成员或 admin / platform_operater；导出等内部链路走 `doGetScanByCommunity`（无权限校验的私有方法）复用同一数据逻辑 |
| `GET /license/tree`                | `openScanService.prDetailAuth(scanId, userId)`                   | scanId → 归属仓库（person 扫描优先 / tbl_scan 兜底）→ 框架服务校验                                                    |
| `POST /license/licenseIssue/query` | 同上                                                             | 校验在 try 块之外执行，避免 `PermissionException` 被兜底 catch 包装成 `ScaException`                                  |
| `POST /email/review/add`           | 按 `communityId` 集合逐一 `verifyCommunityPermission`            | 批量入参去重后校验全部涉及社区                                                                                        |
| `POST /email/review/query`         | 按 `queryPo.communityId` 校验                                    | —                                                                                                                     |
| `POST /email/review/delete`        | 反查待删记录所属社区后逐一校验                                   | 新增 `TblEmailReviewMapper#selectByIds`（接口 + XML）                                                                 |
| `scanConfirmParseV2`（提审）       | `checkRepoUserNamePermission`                                    | 见 §5 配套                                                                                                            |

- `prDetailAuth` 由 `OpenScanServiceImpl` 私有方法提升为 `OpenScanService` 接口方法
  （javadoc 标注 scanId 归因链路与复用场景）；
- Controller 统一新增 `catch (PermissionException e) → ResponseEntity.failure(code, msg)`，
  `userId` 为必传 `@RequestParam`。

### 7. repoId 字段修正

`OpenScanServiceImpl` 扫描详情返回 map：`repoId` 由 `byScanId.getBranchId()` 改为
`byScanId.getRepoId()`（原取值把分支 ID 当仓库 ID 返回）。

## 架构决策

| 决策                                                                        | 理由                                                                                                                                         |
| --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| D1 queryAll 复用 `prIsOpenSourceRepo` 而非新建鉴权链路                      | scanId 归因（person 扫描优先 / tbl_scan 兜底）与 visibility 判定已是现成门禁，零新增查询；返回 `200+空列表` 而非 403，不暴露 scanId 归属事实 |
| D2 queryAll 仅放行 `REPO_EXTERNAL`（内部开源也拦）                          | 严于 issue 草案口径；无鉴权接口的放行面取最小集，内部开源仓内容是否可公开由后续口径确认后再放宽                                              |
| D3 评论归属用「列表命中」而非信任单条评论 API                               | 单条 API 实测不返回归属信息；列表 API 路径绑定 PR，命中即证明归属                                                                            |
| D4 关键词配置在服务端（`sca.auto.confirm.keyword`），不信任调用方声明       | 客户端判断可绕过；`@Value` 默认值引用编译期常量拼接，避免常量与默认值两处字面量分叉                                                          |
| D5 未命中短 TTL 缓存（60s / 1024 条）                                       | 无鉴权机机接口重放固定翻 10 页平台 API 属请求放大；TTL 内重放直接 403，命中后清缓存兼容评论可见性延迟                                        |
| D6 评论查询失败 / 未命中 / 超页数三分错误语义                               | 空响应是 token 失效/限流/网关 5xx，误判为「评论不属于该 PR」会误导排障方向                                                                   |
| D7 clone 重试为「清理 + 退避 + 重新执行」的纯外层包装                       | smart HTTP 不可续传，断点续传/协议升级成本高；瞬时抖动用 3 次 × 3s 退避消化，成功路径零额外开销                                              |
| D8 清理失败不阻断重试，但目录删除「诚实失败」（上抛 IOException）           | 重试前的清理是尽力语义（残留由 clone 克隆语义失败兜底）；独立删除路径必须如实报错，否则残留无告警指向                                        |
| D9 共享池化 client + JVM shutdown hook                                      | HttpUtil 非 Spring Bean 无生命周期回调；池参数与 prScanThreadPool 并发度（16）对齐留余量                                                     |
| D10 批落库幂等走「撞主键降级更新」而非先 SELECT 后插入为主                  | 常见不存在路径零额外查询（避免 N+1）；TOCTOU 竞态由唯一键约束 + DuplicateKeyException 兜底                                                   |
| D11 `setIssue` 更新写回本次入参而非库中旧对象                               | 继承链路按 tbl_issue 重建 Mongo 文档，旧对象回写使批复不生效、已确认问题重复弹审——这是行为修复而非风格选择                                   |
| D12 `PermissionException` 在 Controller 单独 catch、Service 校验置于 try 外 | 避免 403 被兜底 catch 包装成 500/ScaException，前端可区分权限拒绝与业务失败                                                                  |

## 涉及文件

### 主代码（16 个）

| 文件                                                                                | 变更 | 说明                                                                                                                                                                                     |
| ----------------------------------------------------------------------------------- | ---- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `analysis/service/impl/OpenScanServiceImpl.java`                                    | 修改 | queryAll 前置 `prIsOpenSourceRepo` 门禁；`prDetailAuth` 提升为接口方法；repoId 取值修正                                                                                                  |
| `analysis/service/OpenScanService.java`                                             | 修改 | 新增 `prDetailAuth(scanId, userId)` 接口方法                                                                                                                                             |
| `common/utils/PlatformCommentUtil.java`                                             | 修改 | `resolveCommentLogin` → `resolveComment`（返回 `CommentDetail`）；列表命中归属校验；未命中短 TTL 缓存；错误语义三分                                                                      |
| `analysis/service/impl/ConfirmReviewServceImpl.java`                                | 修改 | `robotAutoConfirm` 关键词门禁（`sca.auto.confirm.keyword`，默认 `sca-review-pass`）；消费 `CommentDetail`                                                                                |
| `analysis/utils/security/DownLoadFilesUtils.java`                                   | 修改 | `runCloneWithRetry`（3 次 / 3s 退避）；接入两条克隆链路；`deleteDirectoryRecursively` 诚实失败 + 只读位重试 + try-with-resources；`deleteRepoFromGitcode` / `deletePrErrorFile` 尽力清理 |
| `analysis/utils/HttpUtil.java`                                                      | 修改 | 显式超时（5s/10s/5s）；共享池化单例（32/64）；response try-with-resources；shutdown hook；`IllegalStateException` 兜底                                                                   |
| `analysis/utils/binary/BinaryLicenseEnterUtils.java`                                | 修改 | `HttpUtil` 字段注入（可 mock）                                                                                                                                                           |
| `dm/service/impl/ScanCommonServiceImpl.java`                                        | 修改 | 继承落库 `DuplicateKeyException` 降级更新                                                                                                                                                |
| `dm/service/impl/OpenScanDMServiceImpl.java`                                        | 修改 | `setIssue` 幂等 + 写回本次批复值；`scanConfirmParseV2` 仓库权限校验                                                                                                                      |
| `analysis/controller/LicenseController.java`                                        | 修改 | 三个接口新增必传 `userId`；`PermissionException` 单独 catch                                                                                                                              |
| `analysis/service/LicenseService.java` + `impl/LicenseServiceImpl.java`             | 修改 | 接口签名加 `userId`；`verifyProjectMemberPermission` / `prDetailAuth` 校验；导出链路走 `doGetScanByCommunity`                                                                            |
| `dm/controller/EmailReviewController.java`                                          | 修改 | 三个接口新增必传 `userId`；`PermissionException` 单独 catch                                                                                                                              |
| `dm/service/EmailReviewService.java` + `impl/EmailReviewServiceImpl.java`           | 修改 | 接口签名加 `userId`；`verifyCommunityPermission` 横向校验（delete 反查社区）                                                                                                             |
| `dm/dao/TblEmailReviewMapper.java` + `resources/mapper/dm/TblEmailReviewMapper.xml` | 修改 | 新增 `selectByIds`                                                                                                                                                                       |
| `dm/service/impl/IntegrationApiServiceImpl.java`                                    | 修改 | `getPrParams` 空响应重试 500ms 退避                                                                                                                                                      |
| `common/config/rabbitmq/IntegrationApiListener.java`                                | 修改 | 两处清理调用 try-catch，失败不阻断 `basicReject`                                                                                                                                         |

### 测试（13 个，+988/−130 中的测试部分）

| 文件                                                     | 类型      | 覆盖                                                                |
| -------------------------------------------------------- | --------- | ------------------------------------------------------------------- |
| `common/utils/PlatformCommentUtilTest.java`              | +228/−26  | 列表命中/未命中、空响应、超页数、未命中缓存、gitcode/gitee 平台分支 |
| `dm/service/impl/OpenScanDMServiceImplTest.java`         | 新增 +169 | `setIssue` 幂等/写回本次批复值/TOCTOU 降级、提审仓库权限            |
| `dm/service/impl/ScanCommonServiceImplTest.java`         | 新增 +58  | 继承落库撞主键降级更新                                              |
| `analysis/utils/security/DownLoadFilesUtilsTest.java`    | 新增 +106 | `runCloneWithRetry` 重试/退避/清理失败继续/全部失败抛错/中断停止    |
| `analysis/utils/HttpUtilTest.java`                       | +120/−34  | 超时配置、共享 client 复用、池关闭兜底、resetSharedClientForTest    |
| `dm/controller/EmailReviewControllerTest.java`           | +72/−30   | userId 权限分支与 403 透传                                          |
| `dm/service/impl/EmailReviewServiceImplTest.java`        | +69/−18   | 社区横向校验（add/query/delete 反查）                               |
| `analysis/service/impl/OpenScanServiceImplTest.java`     | 新增 +64  | queryAll 私仓/公仓/无法归因三场景                                   |
| `analysis/service/impl/LicenseServiceImplTest.java`      | +68/−8    | prDetailAuth / 项目成员校验                                         |
| `analysis/controller/LicenseControllerTest.java`         | +51/−10   | userId 必传与 PermissionException 透传                              |
| `analysis/service/impl/ConfirmReviewServceImplTest.java` | +57/−3    | 关键词缺失 403、归属失败 403、成功路径                              |
| `analysis/utils/binary/BinaryLicenseEnterUtilsTest.java` | +4/−2     | 注入式 HttpUtil 适配                                                |

## 风险 & 缓解

| 风险                                                                           | 缓解 / 遗留                                                                                                                    |
| ------------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------ |
| auto-confirm 收紧：存量触发评论必须含关键词，sca-action 未同步会误拒           | 关键词可配置（`sca.auto.confirm.keyword`，默认 `sca-review-pass`）；需与 sca-action 确认两端一致，服务端配置就位情况**未验证** |
| queryAll fail-closed 严于 issue 草案：内部开源仓调用方将拿到空列表             | 需确认无内部消费方依赖；放宽仅需调整 `prIsOpenSourceRepo` 放行口径（D2 显式记录）                                              |
| PR 评论超 1000 条（10 页上限）时 committer + 关键词也会 403                    | 显式文案提示「减少PR评论」；属极端场景，fail-closed 取向                                                                       |
| License/EmailReview 新增必传 `userId`：存量前端/调用方不传将 400               | **破坏性契约变更**，需前端与调用方同步改造；改造状态未验证                                                                     |
| 评论历史重放：包含关键词的 committer 历史评论 `commentId` 可重放授权后续新扫描 | 未绑定评论与 scanId/时间（#146 遗留延续）；暴露面受内网可达性约束，需后续补频控/时间绑定                                       |
| resolveComment 最坏 10 次平台 API 调用/请求                                    | 未命中缓存消化重放放大；命中即返回，正常路径 1 页内                                                                            |
| clone 重试拉长最坏耗时：3 × 传输时长 + 2 × 3s 退避                             | 换取瞬时抖动成功率；全部失败后按现状抛 `ScaException`，无静默吞错                                                              |
| 共享 HTTP client 被 shutdown hook 关闭后并发调用退化空 body                    | `IllegalStateException` 显式捕获，维持空 body 契约；仅发生在 JVM 退出窗口                                                      |
| 批复幂等 update 语义：重投消息会以旧批复值覆盖较新状态（last-write-wins）      | 与既有 Mongo 侧 E11000 降级口径一致；消息重投场景下旧值重放概率低，未做版本号控制（遗留）                                      |
| 目录删除「诚实失败」使 `deleteFolder` 在重试路径 WARN 后继续重试               | 重试前清理为尽力语义（D8）；独立删除路径失败如实上抛，残留有告警指向                                                           |

## 跨仓影响

- **sca-action**（auto-confirm 触发方）：触发评论必须包含约定关键词（默认 `sca-review-pass`），
  需确认已同步；本轮 PR 测试计划未验证两端一致性。
- **前端 / License、EmailReview 接口调用方**：`userId` 必传参数为破坏性变更，需同步改造。
- **openlibing-framework**：复用既有 `checkRepoUserNamePermission`（提审校验）与
  `verifyProjectMemberPermission` / `verifyCommunityPermission`（既有能力，未修改契约）。
- **平台 v5 API**：auto-confirm 评论反查由单条评论 API 切换为 PR 评论列表 API
  （`/pulls/{number}/comments`），gitee / gitcode 双平台行为需一致（单测覆盖 gitcode/gitee 分支）。
- `openlibing-docs`（本文件）之外无其他仓改动。
