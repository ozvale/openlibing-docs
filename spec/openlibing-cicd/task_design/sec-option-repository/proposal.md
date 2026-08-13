# openlibing-cicd: 接收 repository 字段并删除 feign 改用本地 mapper

## 需求背景

`sec-option-scan` 后端服务（位于 `openlibing-cicd` 仓）存在两个问题，本变更与 `code-metrics-scan` 仓的插件侧改动配套，共同修复流水线链接仓路径错误问题。

### 问题 1：流水线链接仓路径错误

`SecOptionScanServiceImpl.buildPipelineLink` 通过 `extractOwnerRepo(gitUrl)` 用正则 match 提取 owner/repo，正则硬编码 `gitcode.com`，**测试环境 `test.gitcode.net` 域名下完全无法 match**，导致前端拼接出的流水线链接 404。

插件侧已经修复：上报 `repository` 字段（用 `new URL()` 解析，不依赖具体域名）。本后端需要接收该字段并优先使用。

### 问题 2：跨服务 feign 依赖冗余

`fetchGitUrlsByProjectId` 通过 feign 调 `openlibing-coderepo` 服务的 `/project-repo/internal/query-repo-list` 接口，但本仓已包含 `repo_info` 表，可直接本地查询，无需跨服务调用，徒增部署耦合与故障传播面。

## 验收标准

- [x] `SecOptionScanReportDTO` 新增 `repository` 字段
- [x] `SecOptionScanRecordEntity` + `sec_option_scan_record` 表新增 `repository` 列（含索引）
- [x] Liquibase changelog 完整（含 precondition + rollback）
- [x] `buildPipelineLink` 优先用 `repository` 拼接链接，`repository` 为空时降级用 `gitUrl` 解析（兼容历史数据）
- [x] `RepoInfoMapper` 新增 `queryRepoListByProjectId` 方法 + XML SQL
- [x] 删除 `CodeRepoClient` feign 接口（确认无其他调用方）
- [x] 三个查询接口（overview / file-detail / dropdown）改用本地 mapper
- [x] `mvn compile` 通过

## 关联 Issue

- openlibing/openlibing-cicd#138

## 关联 PR

- openlibing/openlibing-cicd#414（业务仓 PR）
- yanzhaohong/code-metrics-scan#6（配套插件 PR）
