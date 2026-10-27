# openlibing-ops AI Memory

本文档保存 `openlibing-ops` 代码仓可长期复用的 AI 开发规则。当前为初始版本，后续从需求 `archive.md` 中提炼。

## 仓库定位

`openlibing-ops` 负责 OpenLibing AI 能力的 Web 侧交互。后续系统级职责、页面边界、接口契约、权限控制和用户体验规范需在 `system_design/` 中逐步补齐。

## 稳定规则

- AI 开发前必须读取当前需求的 `design.md` 和 `task.md`。
- 涉及页面路由、权限、接口字段、用户可见交互时，必须在需求设计中说明影响范围。
- 前端需求完成后，必须在 `archive.md` 记录最终交互、验证方式、AI 错误和人工修正。

## 常见 AI 错误与规避

| 错误模式 | 规避规则 | 来源需求 |
| --- | --- | --- |
| 待补充 | 待补充 | 待补充 |
| **SQL 汇总 CTE 以 `sdi_repo_info` 起表导致 N 倍笛卡尔积**：项目下 N 行仓库，JOIN `sdi_version_pipeline_base_info`（M 行流水线）后 `SUM(可加项)` 不去重被 ×N（项目下仓库数），`COUNT(DISTINCT ...)` 反而正常去重，分子被放大 N 倍；`GROUP BY` 无法消除。MindIE 实测版本可用度 10%→80%+、P0 通过数 118→1062。 | ① 写库 SQL 与汇总接口 mapper 的 CTE 统一以"指标所在细粒度表"起表：版本/P0 都是流水线维度，起表应为 `sdi_version_pipeline_base_info`，**不要**先经 `sdi_repo_info`。② `open_source` 显式写死（如 `lead`）或透传 `#{req.openSource}`，**不要**通过 `JOIN sdi_repo_info` 隐式带出。③ 涉及多项目下"项目维度聚合"指标时，凡起表行数 ≠ 实际指标粒度行数都必须做"项目下推算 N"心算复核。 | feat-pr-dashboard-metrics（#38） |
| **排序白名单漏配导致前端排序无响应**：前端按字段名（如 `avgCheckDuration`）调排序接口，后端 `SORT_FIELD_MAPPING` 未配该字段，接口不报错但结果不排序。 | 新增/修改前端排序字段时必须**同步**检查后端 `*SortField`/`SORT_FIELD_MAPPING`/`ORDER_BY` 白名单；为排序字段新增单测（`testGetSortField_xxx`）作为最便宜的护栏。 | feat-pr-dashboard-metrics（#43） |
| **Doris 控制台耗时被误当作 SQL 性能判据**：卡数趋势等待卡数 SQL 在 Doris 控制台稳定 ~4 秒，据此误判为 SQL 性能瓶颈，进而提出加缓存、提 ETL 物化等方案；用户实测同环境 `SELECT 1` 同样 ~4 秒，证明该 4 秒是控制台/会话固定开销。 | 评估 SQL 性能**必须**以应用侧真实调用耗时为准（本项目看 `PathFilter` 的 `request uri … cost` 日志）；控制台耗时仅作参考，怀疑时先在同一控制台跑 `SELECT 1` 作基线对照，基线一致则说明与 SQL 无关。 | npu-usage-card-trend（#208） |
| **派生指标未做"窗口无关"约束导致同一切片取值漂移**：等待卡数由"窗口内运行行的 `assign_npu_second / job_current_slot_running_seconds`"推导，短窗口下尚未跑起来的排队任务取不到值被遗漏，同一 00:00 切片 72h 窗口 3346、20min 窗口 247。 | 切片类派生指标必须区分两类输入：**集合**可来自切片（窗口相关，正常），**属性**必须按主键（如 `platform + job_id`）从事实表取 job 级常量且**事实表不加时间过滤**，保证同一 (切片, 主键) 的取值与查询窗口无关；交付前用不同窗口长度（如 72h 与 20min）对数个切片逐个比对验证。 | npu-usage-card-trend（#208） |
