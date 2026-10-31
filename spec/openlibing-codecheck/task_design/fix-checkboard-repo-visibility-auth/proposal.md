# fix-checkboard-repo-visibility-auth

## 需求背景

看板详情、全量趋势、Excel 导出/下载等接口在网关侧配置为**可免登录访问**（匿名请求无可信 `userId`）。改造前，部分入口未在业务层校验关联代码仓是否**公开/开源**，或未校验**当前登录用户**是否具备**仓读权限**，存在通过 summaryId / taskId / uuid 窥探私有仓检查结果的风险。

本 PR 将原先散落在 `CheckboardDelegateImpl` 内的仓可见性与 Feign 读权限逻辑抽到 `CheckboardRepoAccessHelper`，并在此前缺少校验的看板统计、趋势、导出链路上统一调用。

## 功能描述

1. **新增 `CheckboardRepoAccessHelper`**：封装全量 summary / task、门禁 MR（uuid）两类维度的鉴权。
2. **匿名（无网关注入的可信 `userId`）**：仅当关联仓为对外可见时放行——全量与 MR **语义均为「外部可见仓」**；!381 实现上全量用字面量 `"public"`、MR 用 `ProjectConstant.RepoVisibility.REPO_EXTERNAL`（当前常量值亦为 `"public"`，见 design.md §2.3）。
3. **已登录（网关从 JWT/登录态解析并注入的可信 `userId`）**：通过 `OpenlibingFrameworkClient.checkRepoUserNamePermission(userId, repoInfo)` 校验**该身份**对目标仓的读权限；失败返回 `403` / `no permission`。参数语义与 `CheckboardController` 其它接口 javadoc「网关注入的可信身份」一致，**不得**将调用方在 query/body 中自填的 `userId` 当作授权凭据（见 design.md「可信身份」）。
4. **参数缺失**：summaryId / taskId / uuid 为空返回 `50001`。
5. **私有仓 + 免登录**：返回 `4001` / `private repo, no permission`。
6. **看板入口补校验**（HTTP 上仍为 query `userId`，**语义**为网关注入；未注入则按匿名公开仓规则）：
   - `getDetailNum`、`getFullTaskTrend` 等将 `userId` 传入 Helper，按 type 走全量 summary 或 MR uuid 校验；
   - `getTaskResultDetails` 在查询前走 `assertFullSummaryAccess`（Delegate 内 auth 方法委托 Helper）。
7. **导出链路**：
   - `CheckboardRepoAccessService` 门面供 Excel/文件下载使用；
   - 导出任务/状态查询以 **query 上网关注入的 `userId`** 做仓权限校验（与 `sec-option-detail-export` 同类：身份来自 gateway JWT，而非客户端自选）；
   - `ExportDetailRequestDTO.userId`：!381 代码会读取 Body 字段参与校验——**文档约定**该字段须与网关注入身份一致，或仅作冗余透传；禁止依赖 Body 单独作为授权依据（后续应改为只信网关 Header/query 或与 `AuthUtils` 当前用户比对）。
8. **仓库解析**：优先 `parentTaskId` / `repoBranchInfo` 查 `repo_info`；缺失时用 `RepoInfoCoordinateResolver.resolveByUrl(gitUrl)` 兜底。

## 不做什么

- 不改变需 `projectId` + 菜单 URL 的**项目管理类**接口鉴权方式（仍走 `AuthUtils.checkPermission`）。
- 不调整网关免登录白名单本身；**不在 !381 单独实现** JWT 解析（身份来源仍依赖 gateway；业务层未做「入参 userId vs 登录态」一致性校验，见 design.md 实现边界与后续加固项）。

## 验收标准

- [x] 匿名（无网关注入 userId）访问私有仓看板统计、全量趋势、导出相关接口返回 `4001`
- [x] 网关注入 userId 且对该仓无读权限时返回 `403`
- [x] 公开/开源仓匿名仍可访问
- [ ] **阻塞前置（发布门禁）**：**openlibing-gateway** 对登录用户访问看板/导出白名单路由时 **必须** 注入 JWT 解析后的 `userId`；**openlibing-web**（或调用方）不得依赖「用户已登录但 query 不带 userId」——否则已登录私有仓 owner 会被当成匿名而 **4001**（见 design.md §2.0.1、发布顺序）
- [ ] **已登录 + 自有私有仓 + userId 已透传**：`getDetailNum` / `getFullTaskTrend` / 导出链路返回正常数据（非 4001）；联调/冒烟用例必测
- [ ] **（目标行为，!381 未实现）** query `userId` 为空时，若存在网关注入登录态（如 Header / `AuthUtils` 当前用户），应回退使用该身份走 Feign，避免已登录用户被误判匿名
- [ ] **网关策略**：免登录访问不得携带可被业务采信的 `userId` query（防伪造同事 id）
- [ ] **后续加固（可选）**：入参 `userId` 与 `AuthUtils` 一致性强校验
- [ ] **visibility 判定统一（Task 13）**：全量/MR/导出匿名分支均经 `ProjectConstant.RepoVisibility` 单一方法，禁止 `"public"` 字面量与常量混用（design.md §2.3）
- [x] Controller / Delegate / Excel 相关单测已适配 `userId` 入参
- [x] 编译通过，相关单测通过

## 影响范围

### 业务仓 `openlibing-codecheck`（PR !381，13 files，约 +871 / -290）

| 文件                                                | 操作    | 说明                                                |
| --------------------------------------------------- | ------- | --------------------------------------------------- |
| `business/service/CheckboardRepoAccessHelper.java`  | 新增    | 仓可见性 + Feign 读权限                             |
| `business/service/CheckboardRepoAccessService.java` | 新增    | 导出链路门面                                        |
| `business/impl/CheckboardDelegateImpl.java`         | 修改    | 注入 Helper；趋势/详情数/任务详情等入口校验         |
| `business/controller/CheckboardController.java`     | 修改    | 免登录看板接口增加 query `userId`（语义：网关注入） |
| `business/controller/FileDownLoadController.java`   | 修改    | 导出任务、状态、文件导出前校验                      |
| `business/delegate/CheckboardDelegate.java`         | 修改    | 接口签名增加 `userId`                               |
| `business/entity/dto/ExportDetailRequestDTO.java`   | 修改    | 新增 `userId`（须与网关身份一致，不可自报授权）     |
| `business/impl/ExcelReportImpl.java`                | 修改    | `getExcelStatus` 鉴权                               |
| 相关 `*Test.java`                                   | 新增/改 | 单测                                                |

### docs 仓

| 文件                                                                                    | 操作 |
| --------------------------------------------------------------------------------------- | ---- |
| `spec/openlibing-codecheck/task_design/fix-checkboard-repo-visibility-auth/proposal.md` | 新增 |
| `spec/openlibing-codecheck/task_design/fix-checkboard-repo-visibility-auth/design.md`   | 新增 |
| `spec/openlibing-codecheck/task_design/fix-checkboard-repo-visibility-auth/tasks.md`    | 新增 |

## 关联 PR

- https://gitcode.com/openlibing/openlibing-codecheck/pull/381（分支 `fix-checkboard-repo-visibility-auth-2` → `release_20261029_iter2`，已合入）

## 发布与阻塞说明

Helper 对 `userId` **硬分流**：blank → 仅公开/开源仓；非 blank → Feign 仓读。HTTP 上 `userId` 为 **optional query**，**是否走已登录分支完全取决于网关/前端是否透传**。

| 状态                                            | 后果                                                                                                                |
| ----------------------------------------------- | ------------------------------------------------------------------------------------------------------------------- |
| !381 已上 codecheck，网关/web **未**透传 userId | 已登录用户访问**私有仓**看板统计/趋势/导出 → **4001**，功能回归（owner 亦同）                                       |
| 推荐顺序                                        | ① 网关登录链路注入 `userId` → ② web 确认 URL 携带（或后端回退 `AuthUtils`，见 design.md）→ ③ 再对外宣称安全修复闭环 |

单测 mock 传入 `userId`，**不能**替代「已登录但未透传」联调；须按 design.md 发布清单验收。

## 说明

后续 PR !382 在同一 release 上再次调整看板鉴权并**移除**本 PR 新增的 Helper/Service；本 spec 描述 **!381 合入时** 的代码形态。**!382 侧须满足** [project-rename-adaptation](../project-rename-adaptation/design.md) §2.4 与 Task 27，否则视为对 !381 的安全回退。
