# Nightly 流水线版本级优先统计口径 — 实现任务

## 进度: 5/8 complete

- [x] Task 1: `OpsMainStatMapper.xml` 的 `selected_pipelines` 拆为 `nightly_pipelines_all` + `nightly_project_scope` + `selected_pipelines`，实现平台识别、版本级分类、项目级配置回退与 GitHub 恒保留。
- [x] Task 2: `OpsNightlyDetailMapper.xml` 的 `nightlySelectedPipelinesCte` 同步分类与回退（片段名不变，list/count/summary 零改动）。
- [x] Task 3: 新增 `OpsMainStatMapperXmlTest`：XML 解析、分类谓词、回退条件、GitHub 不约束、资源指标不误改、跨 mapper 前缀一致。
- [x] Task 4: 新增 `OpsNightlyDetailMapperXmlTest`：XML 解析、CTE 分类/回退、include 复用次数、GitHub 分支不引用过滤集合、禁止 NULL 不安全的 NOT LIKE。
- [x] Task 5: 通过 `mvn test -Dtest=OpsMainStatMapperXmlTest,OpsNightlyDetailMapperXmlTest`（16 用例）及 spotless/checkstyle/spotbugs/pmd 检查，提交 commit `79746fb1`。
- [ ] Task 6: 用户自测（主表/下钻/混合项目/GitHub-only/特殊项目/导出）。
- [ ] Task 7: 创建业务 PR（关联 Issue #344，打 `ai-assisted` 标签）。
- [ ] Task 8: 归档（用户触发，提交 docs PR 并更新 archive.md）。
