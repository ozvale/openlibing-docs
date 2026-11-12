# 流水线任务明细增加机器/资源池 — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-ops/issues/343
- 业务 PR: https://gitcode.com/openlibing/openlibing-ops/merge_requests/281（目标分支 `dev`，head `caoxiaolin:feat-pr-job-machine-resource`）
- docs PR: 本文件所在 PR

## 交付历程

- commit `943d8ba7` feat(pr-pipeline): add machine and resource pool to task detail（初版，基于当时工作区分支）
- commit `7f4f8ba1` fix(pr-pipeline): source task machines from apply info with npu filter（切换到申请表口径 + `npu_num > 0`）
- commit `17871621` feat(pr-pipeline): add machine and resource pool to task detail（将上述改动 rebase 到 upstream `dev` 后形成的单提交，当前交付版本）

> 说明：`943d8ba7`/`7f4f8ba1` 为本地验证阶段提交，分支基于旧基线且包含无关 nightly 提交；为避免向 `dev` 混入无关改动，最终以 upstream `dev` 为基线重建为 `17871621` 单提交后推送。

## 用户自测反馈

- 首轮验证后补充要求：查询机器数据时必须限定 `npu_num > 0` → 已切换为 `dwi_rd_efc_resource_apply_info` 并限定 `npu_num > 0`（commit `7f4f8ba1`，后合并入 `17871621`）。
- 服务重启后验证通过（见下）。

## 最终验证

| 验证项 | 结果 |
|---|---|
| 定向单元测试 | 19/19 通过（XML 6 + Service 13） |
| spotless / checkstyle / pmd / spotbugs | 全部通过（checkstyle 0 违规、spotbugs 0 bug） |
| 行数/分页不变式 | codearts run `08f6a78d747947cba4164cff51a87887`：total=12，pageSize=5 三页 5/5/2，三页 total 恒为 12，12 个不同 jobId |
| jobType 过滤 | BUILD=4、DT=1，与明细行一致 |
| 空 run / 缺 pipelineRunId | total=0、records=[] / code=40001 |
| codearts 机器数据 | 仅 NPU 任务 `presmoke` 返回 `172.16.0.121 → Ascend统一资源池-贵阳`；纯 CPU 构建/检查任务返回 `[]` |
| gitcode 多机数据 | run `96a99591e34c4c54a3c31560c13da660`：15 个任务 × 2 台机器 = 30 条成对数据；与数仓 SQL 逐条对照 0 差异、0 排序违例 |
| 重复请求确定性 | 两次请求 machines 序列完全一致 |
| 接口耗时 | 313–397ms（首请求冷启动 710ms），无 N+1 |
| 前端 | 未验证：当前工作区 `openlibing-ops-web` 快照早于 #294，缺少任务明细组件 |

## 设计偏差与取舍

1. **机器数据源**：需求分析文档指向 `dwi_rd_efc_resource_apply_info`，实际实现按此落地；并额外发现 codearts 申请 `job_id` 与统一 `job_id` 不一致，新增 `sdi_rd_efc_pipeline_run_clean_codearts` 映射（2026-11-04 codearts 申请行 180/180 可解析）。
2. **两段式查询 vs 单条 SQL**：选择分页后批量查询 + 内存装配，原因是 1:N JOIN 会放大行数与 total；固定 3 次 SQL、无 N+1，实测延迟可接受。MyBatis 集合映射也可行，但需要先做父行分页 CTE 并处理 Doris CTE 多引用、IP 数值序与集合映射细节，本次按风险最小方案实现。
3. **前端列未落地**：当前前端仓快照缺少 #294 任务明细组件，后端契约已就绪；需在前端仓更新后补「机器/资源池」列。
4. **需求单信息缺口**：交付迭代、工作量、系统用户、前置条件、扩展场景等仍为空，建议补齐后进入正式验收；IP 不做脱敏、华为云/实验室标签本期不做。

## 可复用经验

- 数仓任务→机器映射中，不同平台 `job_id` 口径可能不一致（codearts 使用 build job id + daily build number），跨表关联前必须先用真实数据核对取值/格式，不能只看字段名。
- 分页接口叠加 1:N 子数据时，优先"分页父查询 + 页内批量查询子数据"，用固定查询次数换取行数/分页不变式。
- 本地验证可临时启动第二个实例（不同端口）加载未重启分支的代码，与用户正在运行的服务互不影响。

## 归档日期

2026-11-12
