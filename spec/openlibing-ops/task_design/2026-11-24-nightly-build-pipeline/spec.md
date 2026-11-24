# Nightly 专用 build 流水线适配 — Spec

| 字段     | 内容                                      |
| -------- | ----------------------------------------- |
| 变更标识 | `nightly-build-pipeline`                  |
| 关联设计 | `./需求设计说明书.md`                     |
| 目标仓库 | `openlibing-ops`、DolphinScheduler、Doris |
| 代码基线 | `openlibing-ops` main                     |
| 状态     | Draft（待评审）                           |
| 日期     | 2026-11-24                                |

## 1. 背景与目标

Nightly 统计新增专用**构建流水线**，命名以上述两个固定字符串为**前缀**，后缀允许自定义内容。构建流水线只做编译构建、不执行测试用例，因此：

- 需要纳入**编译成功率**；
- 不能纳入**版本可用度**（否则恒为 0，拉低项目级指标）；
- 不能参与“版本级优先、无版本级回退组件级”的集合判定；
- 需要在两个看板的流水线列表中展示，但版本可用度显示 `--`。

## 2. 范围

### 2.1 In Scope

- `dm_rd_efc_project_pipeline_relation` 新增 `is_build_pipeline`；
- 4 个 DolphinScheduler 任务（base、fact、dwr->dwr 逻辑流水线、以及不改但要回归的 2 个 DM 汇总 + 1 个 DM 逻辑）；
- Nightly 流水线看板、工程能力运营看板的取数口径；
- 开源项目运营看板项目统计（共用版本可用度口径）。

### 2.2 Out of Scope

- 资源类看板（资源运营、项目资源、环境资源）的特殊处理；
- 前端新增“构建流水线”标签；
- 构建流水线内测试任务指标的重新定义；
- 历史事实表/DM 表结构变更。

## 3. 术语与口径

| 术语       | 定义                                                                                                |
| ---------- | --------------------------------------------------------------------------------------------------- |
| 构建流水线 | 名称以 `nightly-version-build_pipeline` 或 `nightly-component-build_pipeline` 开头的 Nightly 流水线 |
| 测试流水线 | `pipeline_type='NIGHTLY'` 且 `is_build_pipeline=0` 的流水线                                         |
| 编译成功率 | 逐流水线 `SUM(build_pass_count)/SUM(build_count)`，项目级再对单流水线比率取 AVG                     |
| 版本可用度 | 逐流水线 `SUM(is_version_available=1 的天数)/COUNT(DISTINCT 运行日期)`，项目级再取 AVG              |
| 版本级回退 | 项目存在非 GitHub 版本级测试流水线时只取版本级，否则取全部非 GitHub 测试流水线；GitHub 恒保留       |

## ADDED Requirements

### Requirement: 构建流水线识别（前缀匹配）

系统 SHALL 基于 `LOWER(TRIM(pipeline_name))` 前缀匹配识别构建流水线，前缀为：

- `nightly-version-build_pipeline`
- `nightly-component-build_pipeline`

命中时 `pipeline_type` MUST 仍为 `NIGHTLY`，并写入 `is_build_pipeline = 1`。

#### Scenario: 标准命名命中

- **WHEN** 流水线名称为 `Nightly-Version-build_pipeline`
- **THEN** relation 中该流水线 `pipeline_type='NIGHTLY'` 且 `is_build_pipeline=1`

#### Scenario: 自定义后缀命中

- **WHEN** 流水线名称为 `Nightly-Component-build_pipeline-xxx` 或 `Nightly-Version-build_pipeline_custom`
- **THEN** 同样被识别为构建流水线（`is_build_pipeline=1`）

#### Scenario: 非构建流水线不受影响

- **WHEN** 流水线名称为 `Nightly-CI-Version-xxx`、`Nightly-Version-xxx`（不含 `build_pipeline` 前缀）或 PR 流水线
- **THEN** `is_build_pipeline=0`，原有分类逻辑不变

#### Scenario: 大小写与空格

- **WHEN** 名称包含大写字母或首尾空格
- **THEN** 通过 `LOWER(TRIM(...))` 仍可正确识别

#### Scenario: GitHub 流水线

- **WHEN** 平台为 `github`
- **THEN** `is_build_pipeline=0`（构建流水线仅存在于 codearts/gitcode）

#### Scenario: codearts 基础表缺失

- **WHEN** codearts 构建流水线未登记在 `sdi_version_pipeline_base_info`
- **THEN** 该流水线 `pipeline_type='OTHER'`、`is_build_pipeline=1`，不进入 Nightly 指标；可通过校验 SQL 发现

### Requirement: 构建流水线参与编译成功率

编译成功率的取数集合 SHALL 包含 `is_build_pipeline=1` 的流水线，且不受版本级/组件级回退限制。

#### Scenario: 项目级编译成功率分母包含构建任务

- **WHEN** 项目下存在构建流水线且有 `BUILD` 任务
- **THEN** 项目级 `nightlyBuildSuccessRate` 的分子/分母包含构建流水线的 `build_pass_count`/`build_count`

#### Scenario: 构建流水线单独成行

- **WHEN** 查询 Nightly 看板流水线级汇总或工程能力 Nightly 明细
- **THEN** 构建流水线作为独立流水线行返回，`buildSuccess` 有值

#### Scenario: 版本级项目下的组件构建流水线

- **WHEN** 项目存在版本级测试流水线，同时存在 `Nightly-Component-build_pipeline`
- **THEN** 该构建流水线仍进入编译成功率集合（不因组件级被回退排除）

### Requirement: 构建流水线不参与版本可用度

版本可用度的取数集合 MUST 排除 `is_build_pipeline=1` 的流水线，构建流水线 MUST NOT 出现在可用度分子、分母或逐流水线平均中。

#### Scenario: 项目级版本可用度不回归

- **WHEN** 在已有项目上新增构建流水线后重新计算
- **THEN** 项目级 `nightlyVersionAvailabilityRate` 与新增前一致

#### Scenario: 流水线级可用度为 NULL

- **WHEN** Nightly 看板流水线级汇总返回构建流水线
- **THEN** `versionAvailabilityRate` 为 `null`，前端展示 `--` 且不可点击

#### Scenario: KPI 卡片不被稀释

- **WHEN** 工程能力 Nightly KPI 卡片聚合所有测试流水线
- **THEN** `avgVersionAvail` 的样本不包含构建流水线

#### Scenario: 版本可用度下钻

- **WHEN** 用户点击版本可用度列
- **THEN** 构建流水线不出现或不可进入下钻

#### Scenario: 开源项目运营看板项目统计

- **WHEN** 查询项目级版本可用度
- **THEN** 分母只包含测试流水线

### Requirement: 构建流水线不参与版本级/组件级回退

版本级判定 SHALL 排除构建流水线；构建流水线 MUST 无条件进入编译成功率集合。

#### Scenario: 混合项目

- **WHEN** 项目同时存在版本级测试、组件级测试、版本构建、组件构建
- **THEN** 编译成功率集合 = 版本级测试 + 全部构建；版本可用度集合 = 版本级测试

#### Scenario: 仅组件级项目

- **WHEN** 项目只有组件级测试流水线和构建流水线
- **THEN** 编译成功率集合 = 全部组件级测试 + 全部构建；版本可用度集合 = 全部组件级测试

### Requirement: 看板展示

两个看板的流水线列表 SHALL 展示构建流水线；版本可用度列显示 `--`，编译成功率/时长正常。

#### Scenario: Nightly 看板流水线级汇总

- **WHEN** 打开 `/dashboard/version-pipeline/:projectId`
- **THEN** 列表包含构建流水线；`版本可用度=--`；`编译成功率`、`编译任务时长` 有值

#### Scenario: Nightly 看板趋势图

- **WHEN** 勾选构建流水线
- **THEN** 版本可用度柱为空（`null`），编译时长等曲线正常

#### Scenario: 工程能力 Nightly 明细

- **WHEN** 打开工程能力看板 Nightly Tab
- **THEN** 构建流水线行出现，`版本可用度=--`，`编译成功率` 有值

### Requirement: 运行次数与资源口径不变

构建流水线的运行次数、CPU/NPU 消耗 SHALL 按现有 NIGHTLY 口径继续统计，本期不做特殊处理。

#### Scenario: Nightly 运行次数

- **WHEN** 统计项目 Nightly 运行次数
- **THEN** 包含构建流水线的运行次数

#### Scenario: 资源类看板

- **WHEN** 查询资源运营/项目资源
- **THEN** 构建流水线资源按 NIGHTLY 正常计入

### Requirement: 数据模型向后兼容

`is_build_pipeline` 新增后，所有不感知该列的旧查询 SHALL 保持原有行为。

#### Scenario: 存量数据

- **WHEN** DDL 执行完成但 base 任务尚未重跑
- **THEN** 所有流水线 `is_build_pipeline=0`，指标与改造前一致

#### Scenario: 接口兼容

- **WHEN** 前端仍按旧字段解析
- **THEN** 仅新增 `isBuildPipeline` 字段，无字段删除/改名

### Requirement: 测试约束

XML 结构测试 MUST 保持通过，并补充构建流水线相关断言。

#### Scenario: `OpsMainStatMapperXmlTest`

- **WHEN** 执行测试
- **THEN** `selected_pipelines` 字符串计数仍为 3；`nightly_pipelines_all` 含 `is_build_pipeline`；`nightly_avail_pipelines` 含 `a.is_build_pipeline = 0`

#### Scenario: `OpsNightlyDetailMapperXmlTest`

- **WHEN** 执行测试
- **THEN** `nightlySelectedPipelinesCte` include 计数仍为 4；不出现 `NOT LIKE 'nightly`

## 4. 验收标准

- [ ] 两条前缀（含自定义后缀）在 relation 中 `pipeline_type='NIGHTLY' AND is_build_pipeline=1`
- [ ] 事实表中构建流水线 `is_version_available` 为 `NULL`
- [ ] 项目级 `nightlyVersionAvailabilityRate` 改造前后一致
- [ ] 项目级 `nightlyBuildSuccessRate` 分母包含构建流水线的 BUILD 任务
- [ ] Nightly 看板：构建流水线出现、版本可用度 `--`、编译成功率有值
- [ ] 工程能力看板：Nightly 明细与 KPI 卡片符合上述口径
- [ ] 开源项目运营看板项目统计不回归
- [ ] 相关单元测试与 XML 结构测试通过
- [ ] 资源类看板无异常变化

## 5. 非功能要求

| 项     | 要求                                                                |
| ------ | ------------------------------------------------------------------- |
| 性能   | 新增 relation JOIN 均为小表关联；看板查询不得新增对事实表的全量扫描 |
| 兼容   | DDL 带默认值；后端先于 DDL 回滚不报错                               |
| 可回滚 | 后端 → ETL → DDL 逐层可回滚，列保留不影响旧逻辑                     |
| 可观测 | 提供分类核对 SQL；上线后 24h 内核对构建流水线数量与可用度           |
