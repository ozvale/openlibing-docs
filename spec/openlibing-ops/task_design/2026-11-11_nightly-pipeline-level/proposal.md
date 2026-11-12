# Nightly 流水线版本级优先统计口径

## 需求背景

工程能力运营看板（`/manage/ops-overview/main`）的 Nightly 版本可用度、编译成功率当前按项目下全部 `pipeline_type='NIGHTLY'` 流水线计算，指标为逐流水线等权平均。组件级流水线会稀释版本级流水线指标，无法反映版本级真实可用度。

## 功能描述

- 默认统计版本级流水线：版本级流水线有两种命名模式，名称以 `Nightly-Version` 或 `Nightly-CI-Version` 开头；
- 项目无版本级流水线时回退统计组件级流水线：其余全部（即非版本级）；
- GitHub 平台不参与版本级/组件级判定，始终保留；
- 回退判定采用配置口径：relation 中存在非 GitHub 版本级流水线即只统计版本级，不按时间窗内是否有运行数据回退；
- 范围：仅工程能力运营看板——主表 Nightly 编译成功率/版本可用度两列，下钻 Nightly Tab 的明细列表、分页总数、2 个 KPI 卡片。

## 验收标准

- [ ] 混合项目只统计版本级；纯组件级项目回退统计组件级；纯版本级项目不变。
- [ ] 主表两列数值与下钻 KPI 一致（同集合、同 `AVG(ROUND(每流水线率,4))` 口径）。
- [ ] 下钻明细列表条数 = KPI 参与平均的流水线条数。
- [ ] GitHub-only 项目数值与改造前完全一致；混合项目 GitHub 行保留。
- [ ] 导出 `ops-overview-main` 与页面数值一致。
- [ ] 接口无契约变更，前端无需改动。

## 影响范围

- 后端：`OpsMainStatMapper.xml`、`OpsNightlyDetailMapper.xml`；新增 `OpsMainStatMapperXmlTest`、`OpsNightlyDetailMapperXmlTest`。
- 接口/前端：无变更。
- 非目标：开源项目总览（`category=project`）、独立 Nightly 看板（`nightly-dashboard*`）、旧版本流水线图表、资源环境 Tab、Nightly CPU/NPU 等资源用量指标、ETL / relation 表结构。

## 关联

- 业务 Issue：https://gitcode.com/openlibing/openlibing-ops/issues/344
- 业务分支：`feat-nightly-pipeline-level-filter`
- 业务 commit：`79746fb1`
