# 分支管理页 GitHub 度量结果展示适配

## 需求背景

插件侧已完成 `code-metrics-action` 的 GitHub 适配：GitHub Actions 按 `GITHUB_ACTIONS` 识别平台、使用 `GitHubActions` 身份提供商完成 OIDC 换证、扫描结果上传到平台桶 `openlibing-github-action`。

openlibing-coderepo 侧接收链路未同步适配：`ObsBucketService#downloadToTempFile` 的下载白名单仅允许 `openlibing-gitcode-action`，GitHub 上报的 `obsUrl` 在解析桶名后被判定为非法，`reportMetrics` 落失败记录，`refreshBranchMetricsSnapshot` 不执行，「代码仓管理 → 分支管理」页对 GitHub 分支的 5 项代码度量全部显示 `--`。

## 功能描述

### 本期范围

- OBS 下载白名单由单桶扩展为双桶（`openlibing-gitcode-action`、`openlibing-github-action`），对象前缀与大小上限保持不变；
- 打通 GitHub 上报链路：GitHub Actions 扫描 → OBS（平台桶）→ `/metrics/code/report` → 异步入库 → 分支快照 → 页面展示；
- 补充单测，覆盖 GitHub 桶下载、GitCode 桶下载与非法桶拒绝。

### 不包含

- 插件侧平台识别、OIDC 换证、运行摘要（由 `code-metrics-action` US 承接）；
- 前端页面改造（分支管理页读取统一 VO，无平台分支，零改动）；
- GitHub PR 增量门禁、趋势看板；
- 存量数据回填（GitHub 历史扫描数据不存在，首轮扫描后自然产生）。

## 验收标准

- [x] GitHub 桶 `obsUrl` 可被 `downloadToTempFile` 正常下载解析；
- [x] GitCode 桶行为不变，非白名单桶与非法前缀仍被拒绝；
- [x] 单测覆盖 GitHub 桶成功、GitCode 桶成功、非法桶拒绝、非法前缀与大小超限；
- [ ] GitHub 上报端到端：`code_metrics_record` 有成功记录、`repo_branch` 快照刷新、分支管理页展示 5 项指标；
- [ ] 业务 PR 合入 `release_20261116_iter1` 并完成 GitCode 存量回归。

## 影响范围

| 项   | 内容                                                                                       |
| ---- | ------------------------------------------------------------------------------------------ |
| 仓   | `openlibing/openlibing-coderepo`                                                           |
| 类   | `ObsBucketServiceImpl`、`ObsBucketService`（契约注释）、`ObsBucketServiceImplTest`         |
| 配置 | `obs.action.buckets`（Nacos，当前值 `openlibing-gitcode-action,openlibing-github-action`） |
| 数据 | 无 DDL、无表结构与索引变更                                                                 |
| 接口 | 无新增/变更；`POST /metrics/code/report` 的 `obsUrl` 允许 GitHub 平台桶                    |

## 关联

- 需求 Issue：https://gitcode.com/openlibing/code-metrics-action/issues/74
- 设计文档：[design.md](./design.md)
