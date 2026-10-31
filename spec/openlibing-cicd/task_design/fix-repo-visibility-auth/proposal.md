# fix-repo-visibility-auth

## 需求背景

流水线 **构建日志拉取/导出** 原先仅依赖 `projectId + jobId + buildNo` 即可调用华为云 Build 接口读日志。攻击者在已具备项目菜单权限的前提下，可猜测其它运行的 `jobId` 读取不属于当前 `pipelineRunId` 的构建日志（IDOR）。

**预提交结果** 接口原先仅按 `pipelineRunId` 查询，未约束 `projectId`、`pipelineId`。

**测试报告** 分支 B 查询 `selectByPipelineRunId` 未带 `pipeline_id`，可能混入其它流水线数据。

## 功能描述

1. **GET `/project/pipeline/build/log`**：增加必填 `pipelineId`、`pipelineRunId`；拉日志前 `validateExportBuildJobInPipelineRun`（`jobId` 须出现在该 run 的 `showPipelineRunDetail` 步骤 inputs 中）。**!638 未校验** `pipelineId`/`pipelineRunId` 归属入参 `projectId`（见 design.md §2.2）。
2. **POST `/project/pipeline/build-log/export`**：`ExportLogDTO` 必填 `pipelineId`、`pipelineRunId`；导出前同样校验（**归属校验缺口同上**）。
3. **GET `/project/pipeline/pre-commit`**：改为 `projectId` + `pipelineId` + `pipelineRunId` 查询。
4. **`getTestReport`**：`selectByPipelineRunId(pipelineId, pipelineRunId, stepRunIds)`，SQL 增加 `pipeline_id`。
5. **缓存**：绑定校验按 `projectId:pipelineId:pipelineRunId:jobId` 本地缓存 30 秒，减轻日志轮询对 `showPipelineRunDetail` 的调用；详情失败不写缓存。

## 不做什么

- 不改变 `@CheckPermission` 项目级鉴权（**不等于**已闭合「run/pipeline 归属 projectId」；见 design.md §2.2）。
- 本 spec 仅对应 PR 上 **2 个功能提交**（10 files），不含 merge 相对旧 base 的其它文件 diff。

## 对外契约变更（破坏性）

| 接口                                      | 变更                                                                              | 调用方                               |
| ----------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------ |
| GET `/project/pipeline/build/log`         | 新增 **必填** query：`pipelineId`、`pipelineRunId`（`@NotBlank`）                 | **openlibing-cicd-web** 构建日志轮询 |
| POST `/project/pipeline/build-log/export` | Body **必填** `pipelineId`、`pipelineRunId`（Controller 非空校验）                | cicd-web 导出                        |
| GET `/project/pipeline/pre-commit`        | 由仅 `pipelineRunId` 改为 **三元组** `projectId` + `pipelineId` + `pipelineRunId` | cicd-web 预提交结果                  |

`getTestReport` 仅 Service/SQL 层补 `pipelineId`，若前端 DTO 已带字段则非新增破坏性；以实际页面入参为准。

**!638 已合入后端且入参即必填**，不存在「参数可选过渡」实现；旧版 cicd-web 在未透传新参数时，会触发校验失败或查不到数据 → **构建日志/导出/预提交对全部用户不可用**（见 design.md 发布与回滚）。

## 验收标准

- [x] jobId 与 run 不匹配时构建日志/导出失败并提示
- [ ] **跨项目 run 拒绝（Task 12）**：持有项目 A 菜单权限时，使用 `projectId=A` + 项目 B 的 `pipelineId`/`pipelineRunId` + B 的 run 内真实 `jobId` → **必须失败**（非仅 jobId 不匹配）；若依赖华为云 API 隔离，须在 design §2.2 写明并有用例证明
- [x] 预提交三元组查询
- [x] 测试报告 SQL 含 pipeline_id
- [x] `PipelineServiceImplTest` 覆盖校验与缓存
- [x] 编译 + 单测通过
- [ ] **openlibing-cicd-web** 已发布且对上述三接口透传 `pipelineId`、`pipelineRunId`（及 pre-commit 的 `projectId`）
- [ ] **联合发布验收**：按 design.md「发布顺序」在同一迭代内完成后端+前端，或前端先于/同批后端；未完成前不得单独将含 !638 的后端推生产（若已推须按回滚节处理）

## 影响范围

| 文件                                                | 说明            |
| --------------------------------------------------- | --------------- |
| `PipelineControllerV2.java`                         | 入参扩展        |
| `PipelineService.java` / `PipelineServiceImpl.java` | 校验 + 缓存     |
| `TestCaseResultMapper.java` + XML                   | pipelineId 条件 |
| 相关 Test                                           | 单测            |

## 关联 PR

- https://gitcode.com/openlibing/openlibing-cicd/pull/638（分支 `fix-repo-visibility-auth`，merge `b7e0ce81`，已合入）
