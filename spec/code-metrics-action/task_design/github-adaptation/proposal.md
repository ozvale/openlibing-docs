# 代码度量指标插件支持 GitHub

## 需求背景

`code-metrics-action` 原先只支持 GitCode Actions：运行上下文（仓库、分支、提交、流水线）全部读取 `ATOMGIT_*`，OIDC 身份提供商固定为 `GitCodeActions`，结果展示依赖 `ATOMGIT_OUTPUT` 输出面板。

GitHub 仓库接入 openLiBing 后，插件无法直接复用：

1. GitHub Actions 不注入 `ATOMGIT_*`，上报所需的仓库、分支、提交、运行信息缺失；
2. GitHub OIDC 身份提供商为 `GitHubActions`，沿用默认值会导致 STS 换证失败；
3. GitHub 没有 GitCode 式输出面板，结果无处展示；
4. `config-file` / `js-yaml` 与 `winston` 等依赖无实际使用，增加产物体积与维护成本。

## 功能描述

### 本期范围

- 单份代码运行时识别平台：以 `GITHUB_ACTIONS=true` 判定 GitHub，其余按 GitCode 处理，判定后只读取对应平台变量；
- GitHub OIDC 身份提供商与信任委托切换（`GitHubActions` / `github-actions`）；
- 双平台运行摘要（`GITHUB_STEP_SUMMARY` / `ATOMGIT_STEP_SUMMARY`），GitCode 额外保留 `ATOMGIT_OUTPUT` 输出面板；
- OBS 桶按平台隔离：GitCode 使用 `openlibing-gitcode-action`，GitHub 使用 `openlibing-github-action`；
- 依赖清理（移除 `config-file`、`js-yaml`，`winston` 替换为 `@actions/core`）；
- GitHub 示例工作流、README 接入说明、`dist` 重建。

### 不包含

- openLiBing 平台侧页面展示改造（由配套 US「分支管理页 GitHub 度量结果展示适配」承接）；
- GitHub PR 增量门禁、趋势看板；
- 华为云 IAM 侧身份提供商与信任委托配置（运维前置动作）；
- AK/SK 模式对外宣传（保留兼容，已废弃）。

## 验收标准

- [x] GitHub 仓库运行示例工作流，可完成扫描并展示运行摘要；
- [ ] GitHub 生产镜像仓完成 OIDC 换证与结果上报（IAM 信任策略已修正新格式 `sub`，待下次运行复验）；
- [x] 运行摘要以 Markdown 表格展示扫描信息、5 项指标与平台详情链接；
- [x] GitCode 仓库运行后输出面板与摘要页均正常，存量工作流无需修改；
- [x] GitHub 场景无需配置 Secret（OIDC 信任策略配置完成后）；
- [x] `npm test`、`pre-commit` 全量通过；
- [x] `dist` 体积由约 2784KB 降至 2271KB，功能无回归。

## 影响范围

| 项           | 内容                                                                   |
| ------------ | ---------------------------------------------------------------------- |
| 仓           | `openlibing/code-metrics-action`                                       |
| 入口与上下文 | `src/index.js`、`src/utils/ciContext.js`                               |
| 展示         | `src/utils/summary.js`（本次新增）                                     |
| 扫描与上报   | `src/scanner.js`、`src/uploaders/CoderepoUploader.js`                  |
| 配置与日志   | `src/config/loader.js`、`src/utils/logger.js`                          |
| 元数据与文档 | `action.yml`、`README.md`、`.github/workflows/code-metrics-scan.yml`   |
| 构建产物     | `dist/index.js`                                                        |
| 运行前置     | 华为云 IAM：OIDC 身份提供商 `GitHubActions`、信任委托 `github-actions` |

## 关联

- 需求 Issue：https://gitcode.com/openlibing/code-metrics-action/issues/74
- 设计文档：[design.md](./design.md)
- 页面原型：[prototype.html](./prototype.html)
