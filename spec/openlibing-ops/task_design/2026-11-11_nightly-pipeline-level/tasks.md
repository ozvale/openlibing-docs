# Nightly 流水线版本级优先统计口径 — 实现任务

## 进度: 7/10 complete

- [x] Task 1: `OpsMainStatMapper.xml` 的 `selected_pipelines` 拆为 `nightly_pipelines_all` + `nightly_project_scope` + `selected_pipelines`，实现平台识别、版本级分类、项目级配置回退与 GitHub 恒保留。
- [x] Task 2: `OpsNightlyDetailMapper.xml` 的 `nightlySelectedPipelinesCte` 同步分类与回退（片段名不变，list/count/summary 零改动）。
- [x] Task 3: 新增 `OpsMainStatMapperXmlTest`：XML 解析、分类谓词、回退条件、GitHub 不约束、资源指标不误改、跨 mapper 前缀一致。
- [x] Task 4: 新增 `OpsNightlyDetailMapperXmlTest`：XML 解析、CTE 分类/回退、include 复用次数、GitHub 分支不引用过滤集合、禁止 NULL 不安全的 NOT LIKE。
- [x] Task 5: 现网命名兼容：本地数据核对发现版本级实际命名为 `Nightly-CI-Version-pipeline_*`，补充 `nightly-ci-version-pipeline%` 前缀并保留目标命名 `Nightly-Version-Pipeline`（commit `5c36ba00`）。
- [x] Task 6: 本地服务数据验证（localhost:8098）：主表与下钻 KPI 完全一致；明细总数 = KPI 分母；GitHub-only 项目保留且数值不变；模拟混合项目仅 Ascend-CANN 变化。
- [x] Task 7: 提交业务 commit `79746fb1`（首版）+ `5c36ba00`（命名兼容）。
- [ ] Task 8: 用户自测（重启本地服务，确认 Ascend-CANN(300057) 版本可用度 0.8148 → 0.9444、编译成功率 0.9642 → 1.0，其余项目不变）。
- [ ] Task 9: 创建业务 PR（关联 Issue #344，打 `ai-assisted` 标签）。
- [ ] Task 10: 归档（用户触发，提交 docs PR 并更新 archive.md）。
