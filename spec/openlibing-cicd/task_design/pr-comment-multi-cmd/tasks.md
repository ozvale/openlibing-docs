# pr-comment-multi-cmd — 实现任务

## 进度: 4/4 complete

### 核心改动

- [x] Task 1: 在 `PipelineStartEventHandler` 新增私有方法 `parseConfiguredCommands(String eventComment)`，按 `|` 拆分并 trim、过滤空串、去重
- [x] Task 2: 修改 `prNoteStartPipeline` 第一层校验：用 `configuredCommands` 列表做前缀匹配，PR 评论统一 trim
- [x] Task 3: 修改 `prNoteStartPipeline` 第二层校验（纯命令精确匹配）：用 `configuredCommands` 列表做精确相等匹配

### 测试

- [x] Task 4: 在 `PipelineStartEventHandlerTest` 补充用例：单命令兼容、多命令命中、多命令不命中、trim 处理、带/不带流水线名称场景
