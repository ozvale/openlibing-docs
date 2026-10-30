# fix-repo-visibility-auth

## 需求背景

流水线 **构建日志拉取/导出** 原先仅依赖 `projectId + jobId + buildNo` 即可调用华为云 Build 接口读日志。攻击者在已具备项目菜单权限的前提下，可猜测其它运行的 `jobId` 读取不属于当前 `pipelineRunId` 的构建日志（IDOR）。

**预提交结果** 接口原先仅按 `pipelineRunId` 查询，未约束 `projectId`、`pipelineId`。

**测试报告** 分支 B 查询 `selectByPipelineRunId` 未带 `pipeline_id`，可能混入其它流水线数据。

## 功能描述

1. **GET `/project/pipeline/build/log`**：增加必填 `pipelineId`、`pipelineRunId`；拉日志前 `validateExportBuildJobInPipelineRun`（`jobId` 须出现在该 run 的 `showPipelineRunDetail` 步骤 inputs 中）。
2. **POST `/project/pipeline/build-log/export`**：`ExportLogDTO` 必填 `pipelineId`、`pipelineRunId`；导出前同样校验。
3. **GET `/project/pipeline/pre-commit`**：改为 `projectId` + `pipelineId` + `pipelineRunId` 查询。
4. **`getTestReport`**：`selectByPipelineRunId(pipelineId, pipelineRunId, stepRunIds)`，SQL 增加 `pipeline_id`。
5. **缓存**：绑定校验按 `projectId:pipelineId:pipelineRunId:jobId` 本地缓存 30 秒，减轻日志轮询对 `showPipelineRunDetail` 的调用；详情失败不写缓存。

## 不做什么

- 不改变 `@CheckPermission` 项目级鉴权。
- 本 spec 仅对应 PR 上 **2 个功能提交**（10 files），不含 merge 相对旧 base 的其它文件 diff。

## 验收标准

- [x] jobId 与 run 不匹配时构建日志/导出失败并提示
- [x] 预提交三元组查询
- [x] 测试报告 SQL 含 pipeline_id
- [x] `PipelineServiceImplTest` 覆盖校验与缓存
- [x] 编译 + 单测通过
- [ ] 前端传递 pipelineId、pipelineRunId 联调

## 影响范围

| 文件                                                | 说明            |
| --------------------------------------------------- | --------------- |
| `PipelineControllerV2.java`                         | 入参扩展        |
| `PipelineService.java` / `PipelineServiceImpl.java` | 校验 + 缓存     |
| `TestCaseResultMapper.java` + XML                   | pipelineId 条件 |
| 相关 Test                                           | 单测            |

## 关联 PR

- https://gitcode.com/openlibing/openlibing-cicd/pull/638（分支 `fix-repo-visibility-auth`，merge `b7e0ce81`，已合入）
