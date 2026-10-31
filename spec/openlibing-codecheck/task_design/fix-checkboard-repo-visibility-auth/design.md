# fix-checkboard-repo-visibility-auth — 技术设计

## 1. 方案设计

在网关允许免登录的看板/导出 API 上，增加**业务层二级校验**：根据任务维度解析出 `RepoInfoEntity`，再按是否存在**网关注入的可信 userId** 分支：

```
请求
  → gateway：匿名 → 不透传/剥离 userId；登录 → JWT 解析后注入 userId（query/Header）
  → Controller / Delegate / ExcelReportImpl
    → CheckboardRepoAccessHelper
        → 无可信 userId？
            是 → 仓 visibility 是否公开/开源？ 否 → 4001
            否 → checkRepoUserNamePermission(可信 userId, repoInfo)  否 → 403
        → 通过 → 继续原有查询/导出逻辑
```

**可信身份（与 spec/openlibing-cicd/task_design/sec-option-detail-export/design.md 对齐）**：用于 Feign 仓读判据的 `userId` **仅**指 gateway 从 JWT/登录态解析并注入的值，不是客户端在免登录白名单上自填的 query/body 字段。`CheckboardController` 上需登录的接口 javadoc 已写明「网关注入的可信身份」；本批免登录看板/导出接口沿用同一语义。

### 2.3 仓 `visibility` 判定口径（遗留 + 目标）

**现状（!381 `CheckboardRepoAccessHelper`，!382 删 Helper 后逻辑散落 `CheckboardDelegateImpl` 等同名方法）**

| 路径                        | 代码                                                       | 说明                                                                              |
| --------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------------- |
| 全量 `fullIsOpenSourceRepo` | `"public".equals(repoInfo.getVisibility())`                | 字面量，**无编译期**与常量联动                                                    |
| MR `incIsOpenSourceRepo`    | `ProjectConstant.RepoVisibility.REPO_EXTERNAL.equals(...)` | 常量；**当前** `REPO_EXTERNAL == "public"`（见 `ProjectConstant.RepoVisibility`） |

两路径**运行时等价**，但收敛 Helper 时**未**抽成单一判定，后续维护易只改一侧。

**失败模式**

| 变更                                                               | 后果                                                                                    |
| ------------------------------------------------------------------ | --------------------------------------------------------------------------------------- |
| `repo_info.visibility` 新增等价可见值（如 `PUBLIC`、其它对外枚举） | 仅改常量侧 → 全量仍只认 `"public"` → 私有误判公开（**越权**）或公开误判私有（**4001**） |
| 重命名/改值 `REPO_EXTERNAL` 而漏改字面量                           | 全量/MR **分叉**，同上                                                                  |
| !382 删 Helper 后复制粘贴                                          | 分叉点从 1 处变为 Delegate 内多处，风险放大                                             |

**目标行为（Task 13；Task 27 闭合鉴权时须一并满足）**

- 在仓读 Helper（或收拢后的唯一组件）内提供 **`isExternallyVisible(RepoInfoEntity)`**（命名可调整），**全量 / MR / 导出**匿名分支均调用；
- 判定只引用 **`ProjectConstant.RepoVisibility`**（至少 `REPO_EXTERNAL`；若产品扩展「匿名可读」集合，在该方法内集中扩展，禁止再散落 `"public"` 字面量）；
- 单测：同一 `repoInfo` 在全量与 MR 入口匿名判定结果一致；常量值变更时仅改一处。

### 2.0 实现边界（PR !381 代码）

| 项       | 说明                                                                                                                 |
| -------- | -------------------------------------------------------------------------------------------------------------------- |
| 代码行为 | Helper 仅根据 **入参** `userId` 是否 blank 分支，非 blank 则直接调用 `checkRepoUserNamePermission(userId, repoInfo)` |
| 未实现   | 业务层 **未** 校验入参 `userId` 与 `AuthUtils`/网关当前登录用户是否一致                                              |
| 安全闭环 | 私有仓防窥探 **依赖** gateway：登录链路必须注入真实 userId；免登录链路不得让业务层看到可伪造的 userId                |
| 后续加固 | 建议在 Controller/Filter 层只接受网关注入 identity，或与 `AuthUtils` 比对不一致则 403                                |

### 2.0.1 失败模式

| 场景                                                                    | 结果                                                                                |
| ----------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
| 匿名访问私有仓                                                          | 4001（预期）                                                                        |
| 网关未注入 userId，但用户实际已登录                                     | 按匿名处理 → 私有仓 4001（**降级**，需网关透传 userId 修复）                        |
| 攻击者在白名单路由自填他人 `userId`                                     | Feign 可能按**被伪造 id** 放行私有仓（**!381 未防**；依赖网关剥离或后续一致性校验） |
| 网关注入 userId 且无仓读权限                                            | 403（预期）                                                                         |
| **已登录 + 私有仓 owner + userId 未透传**（!381 已上、网关/web 未完成） | **4001**（**功能回归**；非「越权修复」预期，须按发布顺序消除）                      |

### 2.0.2 身份解析（目标 vs !381）

| 优先级 | 目标行为                                                                                                                                |
| ------ | --------------------------------------------------------------------------------------------------------------------------------------- |
| 1      | 使用 query/Header 上网关 **JWT 注入**的 `userId` 走 Feign                                                                               |
| 2      | query `userId` 为空但请求带有效登录态时，**回退** `AuthUtils.getCurrentUserId()`（或等价网关注入 Header），避免已登录私有仓用户被当匿名 |
| !381   | 仅看入参 `String userId` 是否 blank，**无回退**                                                                                         |

## 2. 实现逻辑设计

### 2.1 入口与 Helper 方法映射

| 业务入口                            | Helper 方法                     | 定位键                       |
| ----------------------------------- | ------------------------------- | ---------------------------- |
| 全量任务详情 `getTaskResultDetails` | `assertFullSummaryAccess`       | summaryId                    |
| 全量趋势 `getFullTaskTrend`         | `assertFullTaskAccess`          | taskId → summary             |
| 详情数量 `getDetailNum`（全量）     | `assertFullSummaryAccess`       | summaryId                    |
| 详情数量 `getDetailNum`（MR）       | `assertIncAccess`               | uuid                         |
| Excel 提交任务                      | `assertExportAccess`            | summaryId + checkType + uuid |
| Excel 状态 / 按 recordKey 导出      | `assertExportAccessByRecordKey` | 先查 `ExportRecord` 再分流   |

### 2.2 响应约定

| 场景                       | code  | message                       |
| -------------------------- | ----- | ----------------------------- |
| summaryId/taskId/uuid 为空 | 50001 | `* must not empty`            |
| 免登录 + 非公开仓          | 4001  | `private repo, no permission` |
| 可信 userId + 无仓读权限   | 403   | `no permission`               |
| 通过                       | —     | Helper 返回 `null`            |

文件导出拒绝时：`exportBoardByFile` 返回 `error.txt` 内容的 `FileResponse`。

## 3. 类设计

| 类                                           | 职责                                                              |
| -------------------------------------------- | ----------------------------------------------------------------- |
| `CheckboardRepoAccessHelper`                 | 仓解析、**visibility（§2.3 待统一）**、Feign 读权限、assert* 系列 |
| `CheckboardRepoAccessService`                | 导出链路门面                                                      |
| `CheckboardDelegateImpl`                     | 看板业务；关键读接口前调用 assert*                                |
| `ExcelReportImpl` / `FileDownLoadController` | 导出前校验                                                        |

## 4. 数据模型设计

不涉及表结构变更。鉴权依赖 `RepoInfoEntity.visibility`、`ExportRecord.checkType/uuid`、任务与 repo 关联字段。

## 5. 性能设计

每次受保护请求增加少量 DB 查询 + 可选 1 次 Feign；免登录路径不调 Feign。

## 6. API 接口设计

基路径：`/openlibing-codecheck/ci-portal/...`（以 Controller 为准）。下列 `userId` **语义**均为 **gateway 解析 JWT 注入的可信身份**；匿名请求该参数为空或未注入。

| 方法 | 路径（后缀）                        | userId 传递方式                                                       |
| ---- | ----------------------------------- | --------------------------------------------------------------------- |
| GET  | `/codecheck/getDetailNum`           | query optional；**有登录态则须有可信 userId**（网关注入），否则按匿名 |
| GET  | `/codecheck/full/task/issues/trend` | 同上                                                                  |
| GET  | Excel 导出任务 / 状态               | 同上                                                                  |
| POST | 看板明细文件导出                    | !381 读 Body.userId；须与网关注入一致                                 |

**说明**：Spring 层 `required=false` **不会**因缺 userId 返回 400；缺参时 Helper 走匿名分支 → 私有仓 **4001**。

**契约要求（部署侧）**：与 `sec-option-detail-export` 一致——登录请求的 `userId` 由 gateway 解析 JWT 注入；免登录白名单路由不应向 codecheck 转发客户端自填 `userId`。

## 7. 安全设计

鉴权：继承原有鉴权逻辑；**仓读二级校验**以网关注入 `userId` 为唯一身份依据，匿名仅允许公开/开源仓

敏感信息：不打印日志，不明文存储数据库，不可下载

硬编码：appkey，token，cookie不写在代码中

审计日志：操作记录可追溯

---

## 测试要点（身份相关）

- 匿名 + 私有仓 → 4001
- 网关注入 userId A + A 无仓读权限 → 403
- **已登录 + 私有仓 owner + userId 已透传 + 有仓读权限 → 200/正常数据**（发布冒烟必测）
- **已登录 + 私有仓 + userId 未透传 → 当前 !381 为 4001**（回归；网关/web 完成透传或实现 AuthUtils 回退后应变为正常）
- **（网关/加固后）** 伪造 userId → 403 或忽略伪造 id
- **visibility**：全量/MR 对同一 `visibility="public"` 仓库匿名判定一致；改 `REPO_EXTERNAL` 后单测仍绿（Task 13）

## 跨仓影响与发布顺序

本修复 **不能** 仅靠 codecheck !381 单独闭环：Helper 硬分流依赖 **可信 userId 进入 Helper**。

| 仓                       | 职责                                                                                                                         | 阻塞                   |
| ------------------------ | ---------------------------------------------------------------------------------------------------------------------------- | ---------------------- |
| **openlibing-gateway**   | 登录访问 ci-portal 看板/导出白名单 API 时，JWT 解析后注入 `userId`（query 或约定 Header）；免登录路由剥离客户端自填 `userId` | **是**                 |
| **openlibing-web**       | 看板/导出页在登录态下携带网关注入的 `userId`（不手写他人 id）                                                                | **是**（与网关同迭代） |
| **openlibing-framework** | `checkRepoUserNamePermission` Feign                                                                                          | 依赖                   |
| **openlibing-codecheck** | !381 Helper；可选后续 `AuthUtils` 回退                                                                                       | 已合入                 |

### 发布顺序（检查清单）

1. [ ] **网关**：登录链路对白名单看板/导出路由注入 `userId`（测试环境验证 Header/query）。
2. [ ] **前端**：openlibing-web 合入并发布，登录态请求带 `userId`。
3. [ ] **codecheck**：含 !381 版本（若已上生产而 1–2 未完成，私有仓已登录用户可能已 4001，须紧急补 1–2 或临时回滚 codecheck）。
4. [ ] **冒烟**：已登录私有仓 owner 打开看板统计/趋势/导出，**非 4001**；匿名访问私有仓仍为 4001。

### 回滚

- 仅回滚 web **不能**恢复私有仓已登录访问（仍缺 userId → 4001）。
- 回滚 codecheck 至 !381 前 → 私有仓越权风险复现；须与网关策略成对决策。
