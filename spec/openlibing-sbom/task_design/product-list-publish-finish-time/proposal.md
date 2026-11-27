# 制品信息列表新增制品发布时间与任务完成时间 — product-list-publish-finish-time

## 业务 Issue

- openlibing/openlibing-sbom#186 — 【openlibing-sbom】制品信息列表新增制品发布时间/任务完成时间列
- https://gitcode.com/openlibing/openlibing-sbom/issues/186

## 需求背景

SBOM 管理页「制品信息」列表（CompositionAnalysis）当前展示制品名称、动态属性列、解析状态、依赖包数量、License 数量、待闭环漏洞数等，缺少两个时间维度：

1. **制品发布时间**：制品最近一次被发布（写入解析任务）的时间，用于判断制品是否已按最新内容重新发布；
2. **任务完成时间**：解析任务最近一次状态更新的时间（漏洞刷新也会刷新）。

解析状态列的 tooltip 虽有"更新时间"，但不独立成列、不支持排序与列配置。需求要求两列独立展示、支持排序，并参考软件包列表的「列配置」能力，将制品发布时间及之后的字段纳入可配置范围。

## 功能描述

- **制品发布时间（publishTime）**：`raw_sbom` 表新增 `publish_time` 字段（TIMESTAMP），记录制品最近一次开始发布的时刻。写入点在发布链路（`publishSbom`）而非解析启动：
  - 新建（无历史记录）：INSERT 前 `setPublishTime(now)`，从 WAIT 状态起即有值；
  - 已有制品复用行（唯一索引 `raw_sbom_uk (value_type, product_id)`）：借 `updateRawSbomIfStatusAllowed` 原子覆盖 UPDATE 追加 `publish_time = now()`（该 SQL 同时显式刷 `update_time = now()`，finishTime 同步刷新），重新发布即刷新；
  - RUNNING 中发布被拒（0 行更新抛异常），时间不刷新；解析启动（置 RUNNING）、FAILED 恢复（重置 WAIT）均不写该字段；
  - 漏洞刷新不触碰该字段，发布时间不受污染。
- **任务完成时间（finishTime）**：直接取 `raw_sbom.update_time`（`@UpdateTimestamp` 自动维护，最近一次状态更新时刻；WAIT/RUNNING 制品显示最近一次状态更新时刻，重新发布后刷新为本次发布时刻）。
- **列表展示**：`queryProductListMultiFilter` 出参新增 `publishTime` / `finishTime`；前端新增两列（位于动态属性列之后、解析状态之前），无解析记录的制品显示 `--`。
- **排序**：`ProductSortField` 白名单新增 `PUBLISH_TIME` / `FINISH_TIME`，两列支持升降序（native SQL `CASE WHEN` 分支 + `NULLS LAST`）。
- **列配置**：复用软件包列表 `useProductColumnSetting` 组合式函数零改动接入；可配置范围从制品发布时间（含）起 6 列（publishTime / finishTime / scanStatus / dependencyCount / licenseCount / vulCount）；基础列（制品名称/组件名/版本号/更多）与动态属性列（`attr_<name>`，位于发布时间之前）锁定恒展示；各社区（userId_projectName 维度）配置独立存储。
- **存量数据清洗**：借 `job_execution_id` 关联 `sbom_batch_job_execution.start_time` 回填存量 `publish_time`（只补空值、幂等可重跑、排除 WAIT 行避免旧执行引用写入偏差值）；孤儿引用、从未解析与 WAIT 行保持 null。

## 不做

- 不修改 `raw_sbom` 其他字段与解析任务状态机（WAIT/RUNNING/FINISH/FAILED 恢复流程不变）
- 不修改既有列的展示逻辑与既有筛选能力（筛选/刷新/导出声明文档/详情维持现状）
- 不修改 `sbom_batch_job_execution` 表结构
- 待闭环漏洞数列的样式优化不在本次范围
- 生产环境 DDL 与存量回填按"DDL → 发版 → 存量回填"顺序由发版流程执行，随本设计交付 SQL

## 验收标准

- [ ] 新上传制品（新建 `raw_sbom` 行）从 WAIT 状态起 `publish_time` 即记录发布时刻
- [ ] 已有制品再次发布（行复用，原状态 NULL/FINISH/FAILED_FINISH/WAIT）`publish_time` 刷新为本次发布时刻，finishTime（update_time）同步刷新
- [ ] RUNNING 中发布被拒绝（原子 UPDATE 0 行、抛异常），`publish_time` 不刷新
- [ ] 解析启动（置 RUNNING）与 FAILED 恢复（重置 WAIT）不写 `publish_time`
- [ ] 漏洞刷新后 publishTime 不变、finishTime 随 update_time 刷新
- [ ] `queryProductListMultiFilter` 出参含 `publishTime` / `finishTime`，无解析记录的制品前端显示 `--`
- [ ] 两列支持 `sortField=publishTime / finishTime` 升降序排序，NULL 排最后
- [ ] 「列配置」弹层支持 publishTime 起的 6 列勾选显隐与拖拽排序，锁定列（基础列 + 动态属性列）恒展示不可取消
- [ ] 各社区列配置独立存储互不影响（storageScope 按 userId_projectName 隔离）
- [ ] 存量回填后按量化校验 SQL 核对：回填后 `publish_time IS NULL` 行数 = 孤儿引用行数 + 从未解析行数 + WAIT 行数（回填前后各执行一次 NULL 计数对照，孤儿引用核对 SQL 见 design.md，孤儿引用保持 null 前端 `--`）

## 影响范围

- 业务仓：`openlibing-sbom`（model / dao / sbom-web）
- 跨仓影响：`openlibing-web`（CompositionAnalysis 制品信息列表新增两列、排序接入、列配置接入）

## 流程模式

Standard 模式：proposal + design + tasks，UT 按 ai_memory 规则在 Phase 4 生成。
