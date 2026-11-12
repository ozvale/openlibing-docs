# 流水线任务明细增加机器/资源池 — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-ops/issues/343
- 业务 PR: https://gitcode.com/openlibing/openlibing-ops/merge_requests/281（目标分支 `dev`，**未合并，已关闭**）
- docs PR: https://gitcode.com/openlibing/openlibing-docs/merge_requests/1333
- 最终交付方式: 按用户要求直接推送 `openlibing/openlibing-ops:dev`，不通过 PR 合并

## 交付历程

- commit `943d8ba7` feat(pr-pipeline): add machine and resource pool to task detail（初版本地验证提交）
- commit `7f4f8ba1` fix(pr-pipeline): source task machines from apply info with npu filter（切换申请表口径 + `npu_num > 0`）
- commit `17871621` feat(pr-pipeline): add machine and resource pool to task detail（rebase 到 upstream dev 后的单提交）
- commit `407fbcdd` fix(pr-pipeline): harden codearts job mapping and duplicate row fill（AI 检视修复）
- commit `5baf96bd` feat(pr-pipeline): add machine and resource pool to task detail（重新 rebase 到最新 dev `ab7857ef` 后）
- commit `71ebab46` fix(pr-pipeline): harden codearts job mapping and duplicate row fill（重新 rebase 后，**最终合入 dev 的提交**）

> 说明：早期本地提交基于当时工作区分支且包含无关 nightly 提交，后续以 upstream `dev` 为基线重建；`17871621`/`407fbcdd` 被最新 dev 上的 `5baf96bd`/`71ebab46` 取代。

## 用户自测反馈

- 首轮验证后补充要求：查询机器数据时必须限定 `npu_num > 0` → 已切换为 `dwi_rd_efc_resource_apply_info` 并限定 `npu_num > 0`。
- 服务重启后验证通过（见下）。

## 最终验证

| 验证项 | 结果 |
|---|---|
| 定向单元测试 | 22/22 通过（XML 6 + Service 16，含检视修复新增用例） |
| spotless / checkstyle / pmd / spotbugs | 全部通过（checkstyle 0 违规、spotbugs 0 bug） |
| 行数/分页不变式 | codearts run `08f6a78d747947cba4164cff51a87887`：total=12，pageSize=5 三页 5/5/2，三页 total 恒为 12，12 个不同 jobId |
| jobType 过滤 | BUILD=4、DT=1，与明细行一致 |
| 空 run / 缺 pipelineRunId | total=0、records=[] / code=40001 |
| codearts 机器数据 | 仅 NPU 任务 `presmoke` 返回 `172.16.0.121 → Ascend统一资源池-贵阳`；纯 CPU 构建/检查任务返回 `[]` |
| gitcode 多机数据 | run `96a99591e34c4c54a3c31560c13da660`：15 个任务 × 2 台机器 = 30 条成对数据；与数仓 SQL 逐条对照 0 差异、0 排序违例 |
| 重复请求确定性 | 两次请求 machines 序列完全一致 |
| 接口耗时 | 313–397ms（首请求冷启动 710ms），无 N+1 |
| 全量测试基线 | `mvn clean test`：1418 个用例，仅 `ProductQualityCoreMapperXmlTest` 2 个用例失败；已在无本改动的 `upstream/dev`（`f497a7c9`）基线上复现，属 dev 基线问题，非本需求引入 |
| 前端 | 未验证：当前工作区 `openlibing-ops-web` 快照早于 #294，缺少任务明细组件 |

## 合并状态（归档时）

- **已直接推送 `openlibing/openlibing-ops:dev`**：`dev` 由 `ab7857ef` 更新为 `71ebab46`，包含 `5baf96bd`、`71ebab46` 两个提交。
- 业务 PR #281 未合并，已评论说明并关闭（CI 曾因 dev 基线 `ProductQualityCoreMapperXmlTest` 失败及审批要求无法通过 PR 合并）。
- docs PR #1333 已创建；当前账号对 `openlibing/openlibing-docs` master 无直接合并权限，需维护者合并。
- 说明：直接推送绕过了 PR 审批与 CI 门禁，属于用户明确要求的交付方式；建议后续发布前补充在 dev/main 分支上复跑全量 CI。

## 设计偏差与取舍

1. **机器数据源**：需求分析文档指向 `dwi_rd_efc_resource_apply_info`，实际实现按此落地；并额外发现 codearts 申请 `job_id` 与统一 `job_id` 不一致，新增 `sdi_rd_efc_pipeline_run_clean_codearts` 映射（2026-11-04 codearts 申请行 180/180 可解析）。
2. **两段式查询 vs 单条 SQL**：选择分页后批量查询 + 内存装配，原因是 1:N JOIN 会放大行数与 total；固定 3 次 SQL、无 N+1，实测延迟可接受。MyBatis 集合映射也可行，但需要先做父行分页 CTE 并处理 Doris CTE 多引用、IP 数值序与集合映射细节，本次按风险最小方案实现。
3. **前端列未落地**：当前前端仓快照缺少 #294 任务明细组件，后端契约已就绪；需在前端仓更新后补「机器/资源池」列。
4. **需求单信息缺口**：交付迭代、工作量、系统用户、前置条件、扩展场景等仍为空，建议补齐后进入正式验收；IP 不做脱敏、华为云/实验室标签本期不做。

## 可复用经验

- 数仓任务→机器映射中，不同平台 `job_id` 口径可能不一致（codearts 使用 build job id + daily build number），跨表关联前必须先用真实数据核对取值/格式，不能只看字段名。
- 分页接口叠加 1:N 子数据时，优先「分页父查询 + 页内批量查询子数据」，用固定查询次数换取行数/分页不变式。
- 本地验证可临时启动第二个实例（不同端口）加载未重启分支的代码，与用户正在运行的服务互不影响。
- 合入前需确认目标分支基线 CI 是否健康；直接推送可绕过门禁，但发布前仍应补跑全量 CI。

## 归档日期

2026-11-12
