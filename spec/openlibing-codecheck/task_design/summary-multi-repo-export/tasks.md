# summary-multi-repo-export — 实现任务

> 范围变更（2026-08-25）：导出需求取消，任务清单仅保留仓库多选筛选。
> 模式降级为 Standard（scope_snapshot 见 proposal.md）。

## 进度: 5/5 complete

### 后端（openlibing-codecheck，分支 feat-summary-multi-repo-export）

- [x] Task 1: `QuerySummaryModel` 增加 `repoNames`（List<String>）字段
- [x] Task 2: `IncSummaryOperation.getCriteria` 与 `CommonOperation.getSummaryCriteria` 支持 repoNames in 查询（repoName 回退，单选向后兼容）
- [x] Task 3: 后端编译验证（mvn compile）——通过（exit 0）

### 前端（openlibing-web，分支 feat-summary-multi-repo-filter）

- [x] Task 4: `shared.ts` 表单 `repoName`→`repoNames: []`、resetFormInline 同步；`GatingCheck.vue` / `StaticCheck.vue` 仓库多选（multiple + collapse-tags），handleRepoChanged 分支去重并集；`IncrementCheckList.vue` / `StaticCheckList.vue` 本地 formInline 改 repoNames、查询参数传 repoNames、同步时防御性拷贝 repoNames 数组
- [x] Task 5: 前端验证——ESLint 5 文件零问题（exit 0）；vue-tsc 类型检查本次文件零错误（全仓预存类型错误与本次改动无关）

### 交付

- 自检（生成前约束清单）+ diff 汇总；docs PR 随 Phase 3 一并提交
