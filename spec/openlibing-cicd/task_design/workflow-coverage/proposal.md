# workflow-coverage: 流水线 & pre-commit action 覆盖率统计

## 需求背景

运营看板（openlibing-framework）需要按社区维度统计 4 个治理类指标，用于评估各社区在 GitCode 流水线配置和 pre-commit action 接入方面的推进情况。当前无任何自动化采集途径，需要在 openlibing-cicd 仓新增一个 xxl-job 定时任务，遍历社区下所有仓库的 `.gitcode/workflows/*.yaml`，聚合后上报到 framework 的 `/manage/feature-dashboard/report` 接口。

## 需求描述

1. 在 `openlibing-cicd` 新增一个 xxl-job handler `reportWorkflowCoverageHandler`。
2. 启动时调 framework `GET /manage/feature-dashboard/matrix` 获取 `data.communities` 作为社区列表（结果带 5 分钟 TTL 缓存）。
3. 对每个社区：
   - 调 framework `GET /select/only-one/get-project-by-name?projectName={community}` 获取 `projectId`。
   - 调 coderepo `POST /project-repo/query-repo?userId={系统账号}&body={projectId,platforms:["gitcode"],pageNum,pageSize:100}` 分页拉取该社区下所有 gitcode 仓库，过滤 `status not in (archived, not_exist)`。
4. 对每个 gitcode 仓库：
   - 通过 `CrossRegionService.getRepoAccessToken(repoUrl)` 获取加密 token，再 `SecurityUtil.decrypt` 解密。
   - 调 GitCode `GET /api/v5/repos/{owner}/{repo}/contents/.gitcode/workflows?ref=master` 列出目录下的所有 `.yaml` 文件。
   - 调 GitCode `GET /api/v5/repos/{owner}/{repo}/contents/{path}?ref=master` 读取每个 `.yaml` 文件内容（走 `download_url` 也可，但优先 contents 接口拿 base64 内容）。
5. 聚合该社区下：
   - `配置仓库数` = 至少有一个 `.yaml` 文件的仓库数
   - `pre-commit action配置仓库数` = 至少有一个 `.yaml` 文件包含字符串 `openlibing-pre-commit-action` 的仓库数
   - `流水线配置覆盖率` = 配置仓库数 / 社区总仓库数（保留 4 位小数）
   - `pre-commit action覆盖率` = pre-commit 仓库数 / 社区总仓库数（保留 4 位小数）
6. 通过 `framework /manage/feature-dashboard/report` 上报，`feature='流水线'`，`community` 为社区名，`userMetrics` 4 个 key 全部上报。`timestamp` 传当前 UTC 时间。

## 验收标准

- [ ] xxl-job handler `reportWorkflowCoverageHandler` 注册成功，可在 xxl-job-admin 调度列表中看到
- [ ] 启动时调 framework `/manage/feature-dashboard/matrix` 获取社区列表（带 5 分钟 TTL 缓存），多社区配置时遍历全部
- [ ] 通过 Feign 调 framework `/select/only-one/get-project-by-name` + coderepo `/project-repo/query-repo` 获取每个社区的 gitcode 仓库列表
- [ ] 对每个仓库调 GitCode contents API 拉取 `.gitcode/workflows/` 下的 `.yaml` 文件列表和内容
- [ ] 4 个指标计算结果与人工抽样对账一致（`配置仓库数`、`流水线配置覆盖率`、`pre-commit action配置仓库数`、`pre-commit action覆盖率`）
- [ ] 通过 `POST /manage/feature-dashboard/report` 上报成功（HTTP 200）
- [ ] 单个仓库 / 社区失败不影响其他社区（异常隔离 + 日志）
- [ ] 单元测试覆盖：配置仓库数 / 覆盖率 / pre-commit 命中 / 异常隔离
- [ ] framework 端 `feature_ops_dashboard_metric_config` 表已手工预注册 4 条指标

## 关联 Issue

openlibing/openlibing-cicd#134
