# UT 测试覆盖率插件支持 GitHub - 需求提案

> FE 需求名称：【openLiBing-coderepo】UT测试覆盖率插件支持GitHub
> 关联 Issue：https://gitcode.com/openlibing/openlibing-coderepo/issues/280

## 1. 需求背景

openLiBing 平台已支持 GitHub 仓库接入与 GitHub Actions 流水线。现有 UT 覆盖率上报插件 `upload-ut-action` 仅在 GitCode Actions 下可用：

- 上下文只读取 `ATOMGIT_*` 环境变量，GitHub Actions 下仓库、分支、运行 ID、提交 SHA 均为空；
- OIDC SDK 版本 `0.0.5` 默认使用 `GitCodeActions` 身份提供商与 `gitcode-actions` 信任委托，GitHub Actions 下换证身份不匹配；
- OBS 桶固定为 `openlibing-gitcode-action`，未按 CI 平台隔离；
- step 输出只写 `STEP_OUTPUT`，未兼容 GitHub 的 `GITHUB_OUTPUT`；
- `openlibing-coderepo` 的 OBS 下载白名单只允许 GitCode 桶，即使插件上传成功，GitHub 桶 `obsUrl` 也会被回调拒绝。

## 2. 需求范围

### 2.1 upload-ut-action

1. 以 `GITHUB_ACTIONS=true` 且不存在 `ATOMGIT_*` 关键变量的组合条件识别平台（兼容 runner 双标志冲突时按 GitCode 处理），GitHub 只读 `GITHUB_*`、GitCode 只读 `ATOMGIT_*`，不跨平台混用；
2. 上下文映射：仓库地址、分支（PR 取目标分支）、运行 ID、提交 SHA、仓库名、工作区；
3. OIDC SDK 升级到 `0.0.7`，由 SDK 按平台自动选择 `GitHubActions/github-actions` 或 `GitCodeActions/gitcode-actions`；正常不手写 `configure`，仅在双标志冲突按 GitCode 处理时显式覆盖为 GitCode 提供商；
4. OBS 桶按平台选择：GitHub 为 `openlibing-github-action`，GitCode 保持 `openlibing-gitcode-action`；对象 key 结构不变；
5. `setOutput` 兼容 `GITHUB_OUTPUT`；
6. 同步更新 `action.yml`、`README.md`、单测，并用 ncc 重建 `dist/index.js`。

### 2.2 openlibing-coderepo

1. `ObsBucketServiceImpl.downloadToTempFile` 桶白名单由单桶等值判断改为 GitCode/GitHub 双桶集合判断；
2. 对象前缀白名单（`code-metrics-action/`、`ut-coverage-action/`）、下载大小上限、流式下载与临时文件清理逻辑不变；
3. 同步 `ObsBucketService` 接口注释与 `ObsBucketServiceImplTest`。

### 2.3 不在本次范围

- GitHub PR 增量覆盖率门禁、趋势看板；
- 前端页面改造与历史数据回填；
- 华为云 IAM 侧 `GitHubActions` 身份提供商/信任委托配置（运维前置）；信任策略必须通过 `sub` 限定允许的 GitHub 组织/仓库/分支，禁止通配，未授权仓库换证必须失败；
- 后端 OBS 凭证对 GitHub 桶的授权（运维前置）；
- UT OBS 对象 key 的仓库归属绑定加固（key 仅含 `{repoName}`，彻底加固需加入 `{owner}/{repo}`，列为后续独立需求）。

## 3. 验收标准

1. GitHub Actions 工作流声明 `permissions: id-token: write` 后，OIDC 换证日志显示提供商 `GitHubActions`、委托 `github-actions`；
2. GitHub 上报 OBS 路径为 `obs://openlibing-github-action/ut-coverage-action/{repoName}/{yyyyMMdd}.{HH}/{runId|manual}/ut-coverage.json`；
3. GitHub 仓库 UT 覆盖率可经 `POST /action-api/ut/coverage/report` 成功入库并在平台展示；
4. GitCode 存量工作流的上报、OBS 桶路径、平台展示与改造前一致；
5. 双平台标志同时存在时按 GitCode 处理，OBS 桶与 OIDC 提供商不切换；
6. 未授权的 GitHub 仓库/分支发起 OIDC 换证必须失败（由 IAM 信任策略 `sub` 限定验证）；
7. GitHub PR 事件上报 `branchName=GITHUB_BASE_REF`、`commitId=pull_request.base.sha`，两者同属目标分支；
8. 两仓单元测试通过；`upload-ut-action` 的 `dist/index.js` 已重新执行 `npm run package`，且关键函数/常量（`detectPlatform`、`openlibing-github-action`、`GitHubActions`）已内联，`action.yml` 版本与 `package.json` 一致。
