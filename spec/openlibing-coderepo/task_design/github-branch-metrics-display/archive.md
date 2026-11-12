# 分支管理页 GitHub 度量结果展示适配 — 归档

## 关联

- 业务 Issue：https://gitcode.com/openlibing/code-metrics-action/issues/74
- 业务 PR：[#304](https://gitcode.com/openlibing/openlibing-coderepo/pull/304)（fork 模式，目标 `release_20261116_iter1`，待合入）
- 前置 PR：[#300](https://gitcode.com/openlibing/openlibing-coderepo/pull/300)（非 fork 模式，已关闭并由 #304 重建）
- docs PR：[#1306](https://gitcode.com/openlibing/openlibing-docs/pull/1306)（design.md）
- develop 合入：commit [2197b7d7](https://gitcode.com/openlibing/openlibing-coderepo/commit/2197b7d703196711394e9027d2ce43cd2d30716a)

## 交付历程

- commit `22eade78`：下载白名单由单桶扩展为双桶，允许 GitHub 平台桶
- commit `2197b7d7`：白名单扩桶合入 `develop_202611_iter1`
- commit `ce9f4a65`：按项目规范将桶白名单改为 Nacos 配置项 `obs.action.buckets`
- commit `df377791`：接口 Javadoc、上报 DTO、保底导入任务注释同步配置化桶名表述

## 用户自测反馈

- 需求调整：桶白名单不采用硬编码常量，改为 Nacos 配置项 `obs.action.buckets`（逗号分隔，当前值 `openlibing-gitcode-action,openlibing-github-action`）→ `ce9f4a65`、`df377791`
- 流程纠正：首版 PR #300 为同仓 PR，不符合 fork 模式要求 → 关闭并经 fork PR #304 重建
- 检视意见：下载成功用例的临时文件清理改为 `try/finally`，避免断言失败时残留文件

## 最终验证

- 单测：`mvn -Dtest=ObsBucketServiceImplTest test`，surefire 报告 10 个用例全部通过（已移除 `-DfailIfNoTests=false`，避免测试类失配时静默通过）
- 配置上线：`obs.action.buckets` 需在 develop/测试/生产 Nacos 逐环境确认，并验证首次上报成功（当前仅确认配置值，各环境就绪状态待发布前逐项确认）
- 静态检查：pre-commit 全量通过（spotless、checkstyle、spotbugs、pmd、gitleaks）
- develop 环境：白名单扩桶已合入并可正常解析 GitHub 桶 `obsUrl`
- GitHub 上报端到端：待插件侧 OIDC 信任策略修复复验、PR #304 合入并部署后验证
- GitCode 回归：存量 GitCode 上报、展示与 UT 覆盖率链路待 PR 合入后回归

## 设计偏差与取舍

- 设计 §1.4 / §2.2 选择「桶名固定常量、不做配置化」；实现后续按项目规范化要求改为 Nacos 配置项 `obs.action.buckets`。白名单收敛语义不变：仅允许平台约定桶，对象前缀（`code-metrics-action/`、`ut-coverage-action/`）与下载大小上限继续生效，配置缺失时首次调用 fail-fast
- 本归档在业务 PR #304 合入前完成，端到端与回归结论待合入部署后补充更新
- 安全边界与设计 §7 一致：下载校验仅约束「桶名 + 对象前缀」，不校验 objectKey 中 `{owner}/{repo}` 与上报 `gitUrl` 的归属一致性。跟进方式：由 coderepo 模块维护人在下一迭代（2026-12）评估，复评前按「可读对象集合扩大」评估风险；暂无独立跟踪单，跟踪入口为本归档，避免该加固项在后续迭代中丢失

## 可复用经验

- 下载白名单由硬编码改配置项时，必须保留对象前缀与大小上限校验，并保持配置缺失 fail-fast；`@RefreshScope` 为懒加载，配置校验发生在首次调用而非启动期
- `gitcode pr create` 携带 `--labels` 可能被 APIG 网关拒绝，重试时不得遗漏 `--fork`，否则会退化为同仓 PR；标签应在 PR 创建成功后用 `pr edit` 补打
- 同一 FE 需求可贯穿插件仓与平台仓，统一以需求 Issue 作为跨仓追溯锚点

## 归档日期

2026-11-11
