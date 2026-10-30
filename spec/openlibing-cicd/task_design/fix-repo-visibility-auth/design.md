# fix-repo-visibility-auth — 技术设计

## 1. 方案设计

在 **项目级 `@CheckPermission`** 之上，增加 **流水线运行实例级绑定**：

```
已具备 project 权限的请求
  → validateExportBuildJobInPipelineRun（构建日志/导出）
      → 【目标】校验 pipelineId/pipelineRunId 归属 projectId（§2.2；!638 未做）
      → 30s 本地缓存 → showPipelineRunDetail(projectId 解析华为凭证 + 入参 pipelineId/runId)
      → jobId 是否在 steps inputs 中
  → getPreCommitResult(projectId, pipelineId, pipelineRunId)  ← 库表三元组，含 project 归属
  → getTestReport 分支 B 带 pipelineId 查库
```

**!638 修复边界（文档必须写清）**：构建日志/导出闭合的是 **jobId ↔ pipelineRunId** 一步绑定，**未**像预提交一样断言 **OpenLibing `projectId` ↔ pipelineId ↔ pipelineRunId** 三元组归属。

## 2. 实现逻辑设计

### 2.2 构建日志/导出：project 归属与跨项目组合（!638 缺口）

| 层级                                  | !638 行为                                                                                | 闭合的越权                          |
| ------------------------------------- | ---------------------------------------------------------------------------------------- | ----------------------------------- |
| `@CheckPermission`                    | 校验用户对 **入参 projectId** 有菜单权限                                                 | 无项目权限 → 403                    |
| `validateExportBuildJobInPipelineRun` | `getPipelineRunDetail(projectId, pipelineId, pipelineRunId)` → 步骤 inputs 含 `jobId`    | **同一次 run 内** 乱猜 jobId → 拒绝 |
| **缺失**                              | **未**查 `pipeline_run_info`（或等价）确认 `projectId + pipelineId + pipelineRunId` 一致 | 见下「跨项目组合」                  |

**跨项目组合失败模式（文档层未闭合）**

攻击者具备 **项目 A** 权限，请求：

`projectId=A`，`pipelineId`/`pipelineRunId` 取自 **项目 B** 某次运行，`jobId` 为该 run 步骤 inputs 中真实值。

| 步骤                     | 可能结果                                                                                                                                                                                          |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `getPipelineRunDetail`   | 用 **A 绑定的** `HwProjectInfoEntity` 调华为云 `showPipelineRunDetail(A的hwProjectId, B的pipelineId, B的runId)` — 成功/失败取决于 **A/B 是否共用同一华为云 CodeArts 项目**；成功则进入 jobId 绑定 |
| jobId 绑定               | run 详情来自 B 的 run → **可通过**                                                                                                                                                                |
| `showActionIInfo(jobId)` | 用 **A 的** Build 客户端读 **B run 里的 jobId** — 是否读到 B 的日志取决于 **Build 租户/项目级隔离**（**spec 不得默认已防越权**）                                                                  |

**目标行为（Task 12，建议优先于宣称 IDOR 完全修复）**

1. **本地归属（推荐）**：在 `validateExportBuildJobInPipelineRun` **之前或之内**查询 `pipeline_run_info`（或项目内权威表）：
   `project_id = :projectId AND pipeline_id = :pipelineId AND pipeline_run_id = :pipelineRunId`
   不存在或不一致 → 固定错误码/文案（与 pre-commit 三元组语义对齐），**不**调用 Build 读日志。
2. **或**明确 **下游依赖**：若产品确认「一 OpenLibing 项目 ↔ 一华为云项目且 pipelineRunId 全局不可跨 hwProject 查询」，须在本文档 **§2.2 依赖表** 登记，并附 **跨 hwProject 负例** 联调用例；否则视为未闭合。
3. **验收用例（必测）**：项目 A 权限 + B 的 `(pipelineId, pipelineRunId, jobId)` 合法组合 → build/log 与 export **均失败**；项目 A 自身 run **仍成功**。

**与预提交对比**：`getPreCommitResult` 已在 DB 层 `eq(projectId).eq(pipelineId).eq(pipelineRunId)` — 构建日志链路 **应对齐** 同一归属模型。

### validateExportBuildJobInPipelineRun（!638 实现）

- 缓存 key：`projectId:pipelineId:pipelineRunId:jobId`，TTL 30s，max 5000。
- 调用 `getPipelineRunDetail(projectId, pipelineId, pipelineRunId)`：**仅用入参 projectId 解析华为云凭证**，**不**校验 run 在 OpenLibing 侧归属（§2.2）。
- `getPipelineRunDetail` 失败或 data 为空：**不写缓存**。
- 成功拿到 detail 后 `put(bound)`；bound=false 返回「构建任务不属于该流水线运行实例…」。
- `isBuildJobReferencedInPipelineRun` 遍历 stages/jobs，复用 `findMatchedStep(jobRun, jobId)`。

### 预提交

```java
wrapper.eq(projectId).eq(pipelineId).eq(pipelineRunId);
```

PR 评论内部 `getPreCommitResult` 同步三参数。

## 3. 类设计

`PipelineControllerV2`、`PipelineServiceImpl`、`TestCaseResultMapper`（+ XML）。

## 4. 数据模型设计

无 DDL 变更；使用 `pre_commit_record`、`test_case_result` 既有 `project_id` / `pipeline_id` / `pipeline_run_id` 字段；**Task 12** 构建日志归属校验可复用 `pipeline_run_info.project_id` / `pipeline_id` / `pipeline_run_id`（表已存在，!638 未用于 validate）。

## 5. 性能设计

构建日志轮询靠 30s 缓存降低 `showPipelineRunDetail` QPS；未命中时单次请求多 1 次详情调用。

## 6. API 接口设计

基路径：`/project/pipeline`（`PipelineControllerV2`）。下列为 **PR !638 起对外契约**（相对旧版为 **破坏性变更**）。

| 接口                     | 入参（相对旧版）                                                                             | 缺失时行为（!638）                       |
| ------------------------ | -------------------------------------------------------------------------------------------- | ---------------------------------------- |
| GET `/build/log`         | 新增必填 query：`pipelineId`、`pipelineRunId`（原有 `projectId`、`jobId`、`buildNo` 等不变） | `@NotBlank` / 框架校验失败，无法拉日志   |
| POST `/build-log/export` | Body 必填 `pipelineId`、`pipelineRunId`                                                      | Controller 返回 failureMessage，无法导出 |
| GET `/pre-commit`        | 必填 `projectId`、`pipelineId`、`pipelineRunId`（旧版仅 `pipelineRunId`）                    | 参数校验失败或查无记录                   |

`getTestReport`：分支 B 须同时传 DTO 内 `pipelineId` 与 `pipelineRunId`。

### 6.1 兼容与发布策略

**理想过渡（后续若再改契约可参考）**：后端先接受「缺 `pipelineId`/`pipelineRunId` 但打告警 + 拒绝绑定校验或限流」，待 **openlibing-cicd-web** 全量透传后再改为 `@NotBlank` 必填。

**!638 实际**：后端一步收紧为必填，**无兼容期**。因此：

| 顺序         | 要求                                                                                                                |
| ------------ | ------------------------------------------------------------------------------------------------------------------- |
| 推荐         | **同一发布窗口**：cicd-web 与 openlibing-cicd 同版本上线（web 先或同批，不得长期落后）                              |
| 禁止         | 仅合入/仅发布含 !638 的 cicd 后端，而 cicd-web 仍为旧调用（缺三参）                                                 |
| 已发生错位时 | 优先 **热修发布 cicd-web** 透传参数；或 **回滚 cicd** 至 !638 之前版本（临时恢复旧契约，IDOR 风险复现，须排期再发） |

### 6.2 回滚口径

- **前端回滚**：回退 cicd-web 不能单独解决问题（后端仍要求新参）；须与后端策略一致。
- **后端回滚**：部署 !638 之前 cicd 包 → 构建日志/预提交恢复旧入参，**越权修复失效**，需工单跟踪重新上线。
- **联合回滚**：cicd + cicd-web 成对回退到上一稳定版本。

## 7. 安全设计

鉴权：继承原有鉴权逻辑

敏感信息：不打印日志，不明文存储数据库，不可下载

硬编码：appkey，token，cookie不写在代码中

审计日志：操作记录可追溯

---

补充：在菜单权限通过后防止 **横向越权**（跨 pipelineRun / 跨 job / **跨 OpenLibing project 组合 runId**，§2.2）。

## 跨仓影响

- **openlibing-cicd-web**（必须）：构建日志 GET、导出 POST、预提交 GET 透传 `pipelineId`、`pipelineRunId`（pre-commit 另需 `projectId`）；与 cicd 后端 **同迭代发布**（见 §6.1）。
- 发布负责人按 §6.1 检查清单签字，避免「后端已上、前端未上」导致日志功能全站不可用。

## 发布顺序（检查清单）

1. [ ] cicd-web 合入并出包：三接口参数与 §6 表一致（可在测试环境对打 !638 后端验证）。
2. [ ] openlibing-cicd 含 !638 的后端部署（或与步骤 1 **同一窗口**上线）。
3. [ ] 生产冒烟：打开流水线运行详情 → 构建日志滚动加载、导出、预提交结果均成功。
4. [ ] **安全冒烟（Task 12）**：跨项目 `projectId=A` + B 的 `pipelineId`/`pipelineRunId`/合法 `jobId` → build/log、export **拒绝**；或已登记 §2.2 华为云隔离依赖并通过负例联调。
5. [ ] 若步骤 1 未完成即已部署后端：立即执行 §6.2 回滚或紧急发 web，并记录事故单。
