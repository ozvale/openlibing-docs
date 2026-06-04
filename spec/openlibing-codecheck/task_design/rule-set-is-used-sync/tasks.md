# codecheck_rule_set.is_used 不同步仓库配置 — 实现任务

## 进度: 14/16 complete（C2 取消）

> 进度计数会随交付轮次更新；每完成一个 Task 改成 `[x]`，Phase 3 提交时确保本文件同步进 commit。

### 仓 A: `openlibing-codecheck`（分支 `fix/codecheck-rule-set-is-used-sync`）

- [x] A1. `SigRuleSetOperation` 新增 `findInUseTemplateIds(List<String> candidateTemplateIds)`，用 aggregation 查仍在使用的 templateId 集合
- [x] A2. `RuleSetOperation` 新增 `recomputeIsUsedByTemplateIds(List<String> templateIds)`：先 `updateMulti` 置 "0"，再按 `sig_rule_set` 实际状态置 "1"
- [x] A3. `RuleSetOperation.updateRuleSetUsed` 改为委托 `recomputeIsUsedByTemplateIds`（行为更准；同时消除 `updateFirst` 的隐患）
- [x] A4. `RuleDelegateImpl` 新增 `recomputeRuleSetUsed(List<String> templateIds)`；`updateRule` 改走该方法
- [x] A5. `RuleController` 新增 `POST /ci-portal/v2/grant/auth/rule-set/recompute-used`（机机接口）
- [x] A6. `RuleSetOperationTest` 覆盖：多 template 命中走 `updateMulti`；`is_used` 从 "1" 回到 "0" 的分支
- [x] A7. `RuleDelegateImplTest` 覆盖：`updateRule` 调度 `recomputeIsUsedByTemplateIds` 而非旧的 `updateRuleSetUsed`
- [x] A8. 本仓跑构建 + 相关单测，提交 commit（每轮 AI 编码 = 1 commit）

### 仓 B: `openlibing-coderepo`（分支 `fix/coderepo-notify-rule-set-used`）

- [x] B1. `OpenlibingCodeCheckClient` 新增 `recomputeRuleSetUsed(List<String> templateIds)` 方法
- [x] B2. `RepoServiceImpl.addCodececkRuleSet` 写 `sig_rule_set` 前后收集 affected templateIds，回调 codecheck 重算接口
- [x] B3. `RepoServiceImpl.defaultCodecheckRuleSet` 自动绑定默认规则集后回调 codecheck 重算接口
- [x] B4. 删仓路径（如果存在）解绑后回调 codecheck 重算接口
- [ ] B5. `RepoServiceImplTest` 覆盖：addRepo 后回调了 codecheck 重算接口、传入了正确的 affected templateIds
- [ ] B6. 本仓跑构建 + 相关单测，提交 commit（每轮 AI 编码 = 1 commit）

### 仓 C: `openlibing-docs`（分支 `spec/openlibing-codecheck/rule-set-is-used-sync`）

- [x] C1. 落盘 `proposal.md` / `design.md` / `tasks.md`（本目录） — 已在 Phase 2 完成
- [ ] C2. ~~落盘一次性 Mongo 修复脚本~~ — **取消**：不做历史脏数据修复，由 A/B 仓的"重算"语义自然覆盖（每次仓库配置都会触发重算，1→0 的回滚会逐步收敛）
- [x] C3. 写 `archive.md`，包含部署/验证步骤、关联 PR permalink 占位、经验沉淀

### 部署顺序（强约束）

1. 先合 A 仓 PR 并发布
2. 再合 B 仓 PR 并发布（B 依赖 A 端的新端点）
3. 合 C 仓 PR（docs 归档）

> 历史脏数据修复：本次**不做**一次性脚本。`is_used` 的"1→0"回滚依赖业务侧自然操作（规则集解绑、仓库删除、规则集更新）逐步收敛；若后续发现积压严重，可单独提一次性脚本任务。
