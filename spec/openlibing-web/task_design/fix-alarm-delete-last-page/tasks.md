# 任务清单

## Phase 1: 需求确认

- [x] 理解需求：删除最后一页数据后跳转到最后一个有数据的页
- [x] 关联 Issue：openlibing/openlibing-web#358

## Phase 2: 设计与计划

- [x] 定位根因：批量清理成功后 `refresh(false)` 保留页码，删除后 `pageNo` 超出 `totalPages`，请求到空页
- [x] 确定修改方案：修复点放在 `fetchList` 数据层（拿到最新数据后做页码边界校正），而非清理调用点，使所有"保留页码刷新"路径（含批量忽略导致当前筛选数据减少）自动纠正
- [x] 简单变更，spec 仅包含 proposal.md 和 tasks.md（省略 design.md）

## Phase 3: 编码实现

- [x] `fetchList()` 成功分支：`normalizeListResponse` 后，若当前页为空且 `pageNo > 1`，回退 `pageNo = totalPages`，`syncRouteQuery()` 同步路由，`await fetchList()` 重新拉取（await 保证外层 loading 时序正确）
- [x] 无死循环保障：`total=0` 时回退到第 1 页后不再递归；回退页码每次至少减 1
- [x] 提交代码到本地分支 `fix-alarm-delete-last-page`（commit `0e8d2aaf`）
- [x] Prettier / ESLint 校验通过

## Phase 4: PR 提交

- [x] 推送分支到 fork 仓
- [x] 创建业务 PR 到主仓并关联 Issue #358，补打 `ai-assisted` 标签
- [x] 更新 proposal.md 关联 PR 链接（[docs 归档 PR !1132](https://gitcode.com/openlibing/openlibing-docs/merge_requests/1132)）

## Phase 5: 归档

- [ ] 用户自测确认后，补充 archive.md 并通过 docs PR 归档
