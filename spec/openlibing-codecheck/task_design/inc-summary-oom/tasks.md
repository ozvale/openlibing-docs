# inc-summary-oom — 实现任务

## 进度: 6/6 complete

> 与 proposal.md 验收标准的对应：标准 1-3 已由 Task 4/5 的单测与构建验证；标准 4（生产观察）待生产发布后跟踪。实现分支：业务仓 `fix-inc-summary-oom`（提交 `01fce77e`），已合入 `develop_202608_iter2`。

- [x] Task 1: `getIncSummaryList` count 查询改为 `$count`（独立 pipeline [match, $count]，Document 映射，null 兜底 0）
- [x] Task 2: `getIncSummaryList` 分页参数无条件应用（默认 pageNum=1、pageSize=20）
- [x] Task 3: `getSummaryList` count 查询改为 `$count`（保留 [match, sort, group] 前缀，追加 $count）
- [x] Task 4: 更新/新增单测：`getSummaryList` count stub 适配 Document 映射；新增 `getIncSummaryList` 测试验证 $count 计数与默认分页 skip/limit
- [x] Task 5: 编译 + 运行 `IncSummaryOperationTest` 验证（5 tests, 0 failures）+ `mvn package -DskipTests` 构建通过
- [x] Task 6: 对照生成前约束清单自检并展示 diff（2 files, +102/-18）
