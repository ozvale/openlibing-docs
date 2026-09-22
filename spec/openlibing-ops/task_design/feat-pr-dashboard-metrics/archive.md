# feat-pr-dashboard-metrics — 归档

## 关联

- 业务 Issue: <https://gitcode.com/openlibing/openlibing-ops/issues/38>
- 业务 PR: <https://gitcode.com/openlibing/openlibing-ops/pull/83>（源 `feat/pr-dashboard-metrics` → 目标 `release_20260611_iter1`）
- docs PR: <待生成后回填>

## 交付历程

业务仓 `openlibing-ops` 在 `feat/pr-dashboard-metrics` 分支自 `release_20260611_iter1` (`d6b00bf`) 起的提交：

| commit | 类型 | 概要 |
|---|---|---|
| `68322ff` | fix | DWI 项目统计排序白名单补齐 `avgCheckDuration`（Refs #43） |
| `7a48485` | fix | 修正版本可用度汇总的 N 倍笛卡尔积（Refs #38） |
| `5d7c4dd` | merge | rebase `origin/release_20260611_iter1` 同步 |
| `5340b5d` | refactor | `ExternalRepoResp` 构造方法 62 行 → 4 行，满足 G.MET.01 |
| `9347db8` | style | import 分组补空行，满足 G.FMT.03 |

外加同分支此前已合入的：

| commit | 类型 | 概要 |
|---|---|---|
| `9d7dc41` | feat | 仪表盘新增 NPU/Memory/vCPU、版本可用度、P0 通过率（Refs #38） |
| `68322ff`（同表上一项） | fix | 排序白名单补齐 `avgCheckDuration` |
| `68322ff` 之上的 `fix(project): 改用 p0_latest CTE 替代 p0_rank 计算 P0 通过率`、`fix(project): 修复 P0 通过率 null / 分母为 0` 等也属本次范围 |

## 用户自测反馈

- 现象：MindIE（projectId=300036）汇总接口 `version_availability_rate` 80% 多，与详情接口各 pipeline 加权平均 ~10% 不一致，差 8~9 倍；P0 通过数同样 9 倍膨胀。
- 根因：`version_availability_per_pipeline` / 等价 CTE 写库侧起表用了 `sdi_repo_info` JOIN `sdi_version_pipeline_base_info`，引入 N×M 笛卡尔积；`SUM(可加项)` 不去重被 ×N（N=项目下仓库数），详情接口无此 JOIN 故正常。
- 修复：`DwiProjectStatisticsMapper.xml` 的 `version_availability_per_pipeline` CTE 改用 `sdi_version_pipeline_base_info` 起表，`open_source` 用 `#{req.openSource}` 透传；与详情接口 `NightlyPipelineDashboardMapper.xml` `version_availability_stats` 口径一致。
- 验证：用户灰度验证后确认修复后数值与详情接口按 pipeline 加权平均一致，反馈"结果验证正确"。
- 后续清理：用户临时加入的调试字段 `pipeline_availability_rates` 已移除；构造方法与 import 分组按 codecheck 规范收敛。

## 最终验证

- 单元测试：`DwiProjectStatisticsServiceImplTest#testGetSortField_AvgCheckDuration`、`#testGetSortField_AvgClosedLoopDuration` 通过
- 集成验证：MindIE（projectId=300036）灰度验证，汇总 `version_availability_rate` 与详情各 pipeline 加权平均一致
- Codecheck：G.MET.01（构造方法行数）、G.FMT.03（import 分组）已修复

## 设计偏差与取舍

- **写库 vs 现查**：版本可用度汇总口径原本应从 `dwi_project_statistics` 读，但写库侧 SQL 存在 N 倍累加 bug；本次采取"汇总接口现查 `dm_rd_efc_build_dim_nightly_pipeline_day`"绕开写库 bug，与详情接口口径完全一致。**遗留**：DS 调度任务 `sql.sql` 的修复需另行协调（issue_docs/openlibing-ops/38/sql.sql 已记录修复脚本，按用户要求不提交）。
- **P0 通过率 SQL**：为消除 N 倍累加同样需修 `sql.sql` 的 `project_nightly_testcase_p0` CTE，本次仅在 mapper 端用 `p0_latest` CTE 兼容（保持与详情接口一致的分母 `case_run_count_p0` 和"取截至 data_time 最新一次 P0"的 ROW_NUMBER 语义）。
- **节假日口径**：汇总接口仅展示工作日（与 `dwi_project_statistics` 写库口径一致）；与详情接口 `isAllDay=true` 切换不同为**有意的业务决策**，已在修复方案中说明。

## 可复用经验

详见同步更新的 `spec/openlibing-ops/ai_memory.md` 表格，主要一条：

- **SQL 汇总 CTE 起表不要选 `sdi_repo_info`**：项目下 N 行仓库，JOIN `sdi_version_pipeline_base_info`（M 行流水线）后 SUM 类聚合 ×N 倍，且 `GROUP BY` 无法消除。**统一以"指标所在的细粒度表"起表**（如版本/P0 都是流水线维度，起表用 `sdi_version_pipeline_base_info`），`open_source` 显式写死或透传 `#{req.openSource}`，不要通过 JOIN 隐式带出。

## 归档日期

2026-06-09
