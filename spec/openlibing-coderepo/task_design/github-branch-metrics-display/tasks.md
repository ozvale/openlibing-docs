# 分支管理页 GitHub 度量结果展示适配 — 实现任务

## 进度: 10/12 complete

## 1. 下载白名单扩桶

- [x] `ObsBucketServiceImpl` 白名单由单桶等值判断改为双桶集合包含判断（commit `22eade78`）
- [x] 对象前缀白名单（`code-metrics-action/`、`ut-coverage-action/`）与下载大小上限保持不变
- [x] 合入 `develop_202611_iter1`（commit `2197b7d7`）
- [x] 按项目规范将桶白名单改为 Nacos 配置项 `obs.action.buckets`（commit `ce9f4a65`，PR #304 待合入）
- [x] 接口 Javadoc、上报 DTO、保底导入任务注释同步为配置化桶名表述（commit `df377791`）

## 2. 单测

- [x] 新增 GitHub 桶下载成功用例
- [x] 保留 GitCode 桶成功、非法桶拒绝、非法前缀拒绝、元数据/流量超限用例
- [x] `ObsBucketServiceImplTest` 10 个用例全部通过
- [x] 下载成功用例使用 `try/finally` 清理临时文件

## 3. 端到端与回归

- [x] 前端零改动确认：分支管理页读取统一 `BranchMetricsVO`，按值判空展示 `--`
- [ ] GitHub 工作流上报后台成功入库、`repo_branch` 快照刷新、页面展示正常（依赖插件侧 OIDC 信任策略修复与 PR #304 合入）
- [ ] GitCode 存量上报、展示与 UT 覆盖率链路回归
