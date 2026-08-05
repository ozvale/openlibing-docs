# file-contents-dto

## 需求背景

`/ci-portal/v1/codecheck/full/task/file/contents`（查看代码问题文件上下文）接口当前直接复用 `QuerySummaryModel` 作为请求体。

但前端调用本接口时**只传 7 个字段**：

```json
{
  "projectName": "openlibing",
  "projectId": 3,
  "repoUrl": "https://gitcode.com/openlibing/openlibing-platform-release.git",
  "repoName": "openlibing-platform-release",
  "manifestBranch": "release_20260704_fix",
  "path": "src/main/java/com/openlibing/platformrelease/business/dto/config/ReleaseFieldItemsDTO.java",
  "summaryId": "6a4ef86d460078b53d0b943b"
}
```

由于 `QuerySummaryModel` 的 `pageNum` / `pageSize` 字段带 `@NotNull` + `@Range(min=1)` 校验（这是 fix-summary-pagination-and-repo-dropdown 任务加的边界防护），而前端**出于业务语义**确实不需要传分页参数，校验直接 400 报错，**该功能目前完全不可用**。

`QuerySummaryModel` 设计为通用查询模型（分页 + 多种过滤条件），与本接口的"取单文件内容"语义不匹配，**继续复用会持续产生污染**。

关联业务 Issue: <https://gitcode.com/openlibing/openlibing-codecheck/issues/138>

## 功能描述

### 做什么

1. 新建专用 DTO `QueryTaskFileContentModel`（路径：`business/entity/`），仅包含实际需要的 7 个字段（`projectName` / `projectId` / `repoUrl` / `repoName` / `manifestBranch` / `path` / `summaryId`），**不带任何 Jakarta Validation 注解**。
2. 修改 `/codecheck/full/task/file/contents` 接口签名，使其接受新 DTO，行为完全等价。
3. 沿调用链路（`CheckboardDelegate` 接口与实现、`CodePlateHelper`、`GiteePlate`、`GitCodePlate`）同步替换 `QuerySummaryModel` → `QueryTaskFileContentModel`，仅该链路涉及，不影响 `QuerySummaryModel` 其他使用方。
4. 同步更新 4 个相关单元测试（`CheckboardControllerTest`、`CodePlateHelperTest`、`GiteePlateTest`、`GitCodePlateTest`）。
5. 同步更新 `doc/api/checkboard.md` 中该接口的请求体说明。
6. 顺手把 `/codecheck/inc/task/sum`（`getIncTaskSum`）标记为 `@Deprecated` 并加一条 INFO 日志，记录已废弃的 taskId，便于后续切流（与本任务一并提交，避免遗留本地未提交修改）。

### 不做什么

- 不动 `QuerySummaryModel` 现有字段与校验规则（其他接口仍依赖）。
- 不改 `QueryDetailModel`、`QueryPrModel` 等其他查询模型。
- 不动 MongoDB 持久化结构。
- 不动 Gitee / GitCode 平台 HTTP 调用层（`GiteeHelper` / `GitCodeHelper` 的 `getRepoFileContents` 签名保持 5 个 String 参数）。
- 不动 `getTaskFileContents` 的运行时行为（仓库查询、平台路由、base64 解码、按行切分）。
- 不新增 `ai-assisted` 之外的标签，不修改 CI/CD 流水线。

## 验收标准

- [ ] 新增 `QueryTaskFileContentModel` 仅含 `projectName`、`projectId`、`repoUrl`、`repoName`、`manifestBranch`、`path`、`summaryId` 字段，无校验注解，package 与 `QuerySummaryModel` 一致。
- [ ] `POST /ci-portal/v1/codecheck/full/task/file/contents` 接受上述 7 字段的请求体时不报 400，能正常返回按行切分的文件内容。
- [ ] `QuerySummaryModel` 现有使用方（`CheckboardDelegateImpl` 中 `getCriteria` / `getRepoSummary` / `getByTaskId` / `taskTrend` / `getFullSummaryList` / `queryFullSummaryList` 等 + `FullSummaryOperation` + `CommonOperation`）**完全未改**。
- [ ] 4 个测试文件（`CheckboardControllerTest`、`CodePlateHelperTest`、`GiteePlateTest`、`GitCodePlateTest`）中 `QuerySummaryModel` 引用全部替换为 `QueryTaskFileContentModel`，编译通过。
- [ ] `doc/api/checkboard.md` 中该接口的请求体说明更新为新 DTO 字段。
- [ ] `getIncTaskSum` 加 `@Deprecated` 注解 + `logger.info("The getIncTaskSum interface has deprecated, repoId:{}", querySummaryModel.getTaskId());`
- [ ] 业务仓 PR 关联 issue #138，标题：`fix(codecheck): split file-contents interface into dedicated DTO`

## 影响范围

- 仓库：openlibing-codecheck
- 模块：Checkboard（Controller + Delegate + Plate Helper）
- 新增文件：
  - `src/main/java/com/openlibing/codecheck/business/entity/QueryTaskFileContentModel.java`
- 修改文件：
  - `src/main/java/com/openlibing/codecheck/business/controller/CheckboardController.java`
  - `src/main/java/com/openlibing/codecheck/business/delegate/CheckboardDelegate.java`
  - `src/main/java/com/openlibing/codecheck/business/impl/CheckboardDelegateImpl.java`
  - `src/main/java/com/openlibing/codecheck/common/codeplate/CodePlateHelper.java`
  - `src/main/java/com/openlibing/codecheck/common/codeplate/GiteePlate.java`
  - `src/main/java/com/openlibing/codecheck/common/codeplate/GitCodePlate.java`
  - `src/test/java/com/openlibing/codecheck/business/controller/CheckboardControllerTest.java`
  - `src/test/java/com/openlibing/codecheck/common/codeplate/CodePlateHelperTest.java`
  - `src/test/java/com/openlibing/codecheck/common/codeplate/GiteePlateTest.java`
  - `src/test/java/com/openlibing/codecheck/common/codeplate/GitCodePlateTest.java`
  - `doc/api/checkboard.md`
- 无数据库 schema 变化
- 无外部接口契约变化（仅入参模型细化，前端不传字段从"必填"变为"忽略"）
- 行为完全等价
