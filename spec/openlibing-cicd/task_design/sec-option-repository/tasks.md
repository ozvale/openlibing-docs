# 实现步骤：接收 repository 字段并删除 feign 改用本地 mapper

## Phase 1: 数据模型变更

- [x] `SecOptionScanReportDTO` 新增 `repository` 字段（String 类型，注释说明格式为 owner/repo）
- [x] `SecOptionScanRecordEntity` 新增 `repository` 字段 + `@TableField` 注解
- [x] `db.changelog.xml` 新增 changeset `20260630-add-repository-to-sec-option-scan-record`（含 precondition + rollback + 索引）

## Phase 2: feign → 本地 mapper 替换

- [x] `RepoInfoMapper.java` 新增 `queryRepoListByProjectId` 方法
- [x] `RepoInfoMapper.xml` 新增 `queryRepoListByProjectId` SQL（仅查 `assume_pr='1'` 的仓，返回 repoName + repoUrl）
- [x] `RepoInfoMapper.xml` resultMap 增加 `autoFormat`（`is_auto_format`）字段映射
- [x] `RepoInfoEntity` 新增 `isAutoFormat` 字段
- [x] `SecOptionScanServiceImpl` 删除 `CodeRepoClient` feign 依赖，改用 `RepoInfoMapper`
- [x] `fetchGitUrlsByProjectId` 重构：删除 feign 调用 + try-catch，改为本地 mapper 查询

## Phase 3: 流水线链接构建改造

- [x] `SecOptionScanServiceImpl.buildPipelineLink` 签名改为 `buildPipelineLink(String repository, String gitUrl, String pipelineRunId)`
- [x] `buildPipelineLink` 优先用 `repository`（含 `/` 才视为合法），拼接 `{gitcodeDomain}/{repository}/actions/runs/{pipelineRunId}`
- [x] `repository` 为空时降级用 `extractOwnerRepo(gitUrl)` 解析（兼容历史数据）
- [x] `SecOptionScanServiceImpl.buildRecordEntity` 构建 entity 时设置 `repository(request.getRepository())`
- [x] 三个查询接口（overview / file-detail / dropdown）调用 `buildPipelineLink` 时传入 `record.getRepository()`

## Phase 4: 兼容性保障

- [x] 新增 `repository` 列允许 NULL，历史数据不受影响
- [x] `buildPipelineLink` 保留 `gitUrl` 降级路径，历史数据可正常展示流水线链接
- [x] 确认 `CodeRepoClient` 无其他调用方后删除 feign 接口
