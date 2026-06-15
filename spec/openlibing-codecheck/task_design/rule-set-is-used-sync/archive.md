# codecheck_rule_set.is_used 不同步仓库配置 — 归档

## 1. 背景摘要

`codecheck_rule_set` 集合的 `is_used` 字段本应反映"该规则集是否被 ≥1 个代码仓配置"，但实际长期不同步。`openlibing-coderepo` 配置/解绑/删除仓库时**没有任何回写**到该字段；`openlibing-codecheck` 端 `updateRuleSetUsed` 本身也只置 "1"、不置 "0"、且用 `updateFirst` 在 `template_id` 重复时只更新一条。导致 `delRuleSet` 误判"正在使用"、规则集被卡住无法删除。

本次修复分三仓：
- **A 仓** `openlibing-codecheck`：把 `is_used` 从"事件式更新"改为"重算"语义，新增机机接口
- **B 仓** `openlibing-coderepo`：在写 `sig_rule_set` 前后收集 affected templateIds，回调 A 仓重算接口
- **C 仓** `openlibing-docs`：本目录 + 一次性 Mongo 修复脚本

## 2. 改动清单

### 2.1 A 仓（`openlibing-codecheck`，分支 `fix/codecheck-rule-set-is-used-sync`）

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/main/java/com/openlibing/codecheck/business/operation/rule/SigRuleSetOperation.java` | 修改 | 新增 `findInUseTemplateIds(List<String>)` 用 aggregation 查仍在使用的 templateId |
| `src/main/java/com/openlibing/codecheck/business/operation/rule/RuleSetOperation.java` | 修改 | 新增 `recomputeIsUsedByTemplateIds(List<String>)`；旧 `updateRuleSetUsed` 改为委托此方法（消除 `updateFirst` 隐患） |
| `src/main/java/com/openlibing/codecheck/business/impl/RuleDelegateImpl.java` | 修改 | 新增 `recomputeRuleSetUsed(List<String>)`；`updateRule` 改走新方法 |
| `src/main/java/com/openlibing/codecheck/business/controller/RuleController.java` | 修改 | 新增 `POST /ci-portal/v2/grant/auth/rule-set/recompute-used`（机机接口） |
| `src/test/java/com/openlibing/codecheck/business/operation/rule/RuleSetOperationTest.java` | 修改 | 覆盖多 template 命中走 `updateMulti`；`is_used` 1→0 分支 |
| `src/test/java/com/openlibing/codecheck/business/impl/RuleDelegateImplTest.java` | 修改 | 覆盖 `updateRule` 调度新方法 |

提交记录（origin/master..HEAD）：
- 1 commit ahead of master

### 2.2 B 仓（`openlibing-coderepo`，分支 `fix/coderepo-notify-rule-set-used`）

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/main/java/com/openlibing/coderepo/business/feign/OpenlibingCodeCheckClient.java` | 修改 | 新增 `recomputeRuleSetUsed(List<String>)` Feign 方法 |
| `src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java` | 修改 | 3 个入口加回调：`addRepoInfo`→`defaultCodecheckRuleSet`、`updateRepoInfo`→`addCodececkRuleSet`（空+非空分支）、`deleteRepoInfo` |
| `src/test/java/com/openlibing/coderepo/business/service/impl/RepoServiceImplTest.java` | 未改 | 用户临时决定不补新测试；现有 89 个测试全量通过 |

提交记录：
- 1 commit ahead of master（待人工 commit）

### 2.3 C 仓（`openlibing-docs`，分支 `spec/openlibing-codecheck/rule-set-is-used-sync`）

| 文件 | 操作 | 说明 |
|------|------|------|
| `spec/openlibing-codecheck/task_design/rule-set-is-used-sync/proposal.md` | 新增 | 需求背景 + 验收标准 |
| `spec/openlibing-codecheck/task_design/rule-set-is-used-sync/design.md` | 新增 | 技术方案 + 影响范围 |
| `spec/openlibing-codecheck/task_design/rule-set-is-used-sync/tasks.md` | 新增 | 实现任务清单（含 checkbox 进度） |
| `spec/openlibing-codecheck/task_design/rule-set-is-used-sync/archive.md` | 新增 | 本文件 |

> C 仓**未**包含一次性 Mongo 修复脚本，理由见 §4 备注。

## 3. 关联 PR

| 仓 | PR | 状态 |
|------|------|------|
| `openlibing-codecheck` | https://gitcode.com/taohuoquan/openlibing-codecheck/pulls/<待填> | 待创建（Phase 4） |
| `openlibing-coderepo` | https://gitcode.com/taohuoquan/openlibing-coderepo/pulls/<待填> | 待创建（Phase 4） |
| `openlibing-docs` | https://gitcode.com/taohuoquan/openlibing-docs/pulls/<待填> | 待创建（Phase 5） |

> PR 创建后请把 permalink（commit SHA 形式）回填本节，确保分支删除后 URL 仍可访问。

## 4. 部署顺序（强约束）

1. **A 仓**：合 PR + 发布 → codecheck 服务上线新接口 `/rule-set/recompute-used`
2. **B 仓**：合 PR + 发布 → coderepo 服务开始回调新接口（依赖 A 已发布）
3. **C 仓 PR**：合 docs 归档 PR

> 关于历史脏数据：本次**不做**一次性 Mongo 修复。`is_used` 的"1→0"回滚依赖业务侧自然操作（规则集解绑、仓库删除、规则集更新）逐步收敛；B 仓每次写 `sig_rule_set` 都会触发 A 仓"重算"，所以 1→0 错误状态会在用户操作后被自动校正。若后续发现积压严重，可单独提一次性脚本任务。

## 5. 验证步骤（部署后必做）

### 5.1 接口可用性验证（A 仓部署后）

```bash
# 直接调用新接口（用 admin token 或临时申请）
curl -X POST "https://codecheck-host/ci-portal/v2/grant/auth/rule-set/recompute-used" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer <token>" \
    -d '["<一个已知 template_id>"]'
```

预期：`{"code": 0, "msg": "success", ...}`

### 5.2 端到端验证（B 仓部署后）

1. 在测试项目新增一个仓库，配置 codecheck 规则集 A
2. Mongo 查询 `db.codecheck_rule_set.findOne({ template_id: "A" })` 确认 `is_used === "1"`
3. 在测试项目解绑该规则集
4. Mongo 再次查询 `db.codecheck_rule_set.findOne({ template_id: "A" })` 确认 `is_used === "0"`
5. 尝试删除该规则集（走 `delRuleSet` 流程），确认**不再被卡住**

## 6. 测试覆盖摘要

| 仓 | 新增/修改的测试类 | 通过情况 |
|------|------|------|
| `openlibing-codecheck` | `RuleSetOperationTest` + `RuleDelegateImplTest` | 全部通过（具体数见 CI 报告） |
| `openlibing-coderepo` | 无新增（用户决定） | 既有 89 个 `RepoServiceImplTest` 全部通过 |

> 临时决定：B 仓未补新测试。已在 tasks.md 标记 B5 未完成，留作后续 PR 补齐。

## 7. 经验沉淀（reusable insights）

### 7.1 派生量应"重算"而非"事件同步"

`is_used` 是 `sig_rule_set` 的派生量。任何派生量都应：
- 设唯一定义来源（`sig_rule_set` 是 source of truth）
- 在不确定的状态变更时**重算**而非补丁
- 提供"重算"接口供跨服务调用

事件式同步在并发、回滚、失败重试下极易漂移，重算是幂等的。

### 7.2 Mongo `updateFirst` 是常见反模式

`updateFirst` 在 `template_id` 等字段不唯一（多语言/多租户下普遍存在）时**只更新一条**，但语义上通常期望"全部更新"。新代码应**默认 `updateMulti`**，除非有明确证据只需要更新一条。

### 7.3 跨服务的"派生量同步"应走"回调 + 重算"而非"事件总线"

事件总线方案需要 coderepo 和 codecheck 共享事件源、增加中间件依赖。回调 + 重算的方案：
- 接口契约简单（一个 POST + List）
- 失败不影响主流程（重算是幂等的，下次写还会触发）
- 易于测试（mock Feign client 即可）

### 7.4 历史脏数据修复要权衡"一次性脚本"与"自然收敛"

本次没做一次性 Mongo 修复脚本，理由：
- 历史脏数据（`is_used=1` 但实际无引用）会随业务自然操作逐步收敛
- 一次性脚本需要 DBA 协调、停机窗口、备份，**收益与成本不匹配**
- 若业务侧长期不操作导致脏数据积压，再单独提一次性脚本任务即可

判断标准：派生量漂移**可自然收敛**时不做一次性脚本；漂移**无收敛路径**（如历史 event log 已丢）才必须做。

## 8. 未完成项 & 后续 PR

- [ ] B5：`RepoServiceImplTest` 补 3 个新测试（deleteRepoInfo 通知 codecheck、addRepo 通知 codecheck、codecheck 失败不影响主流程）— 用户临时决定跳过
- [ ] 跨仓 PR 互引（`openlibing-coderepo#<n>` ↔ `openlibing-codecheck#<n>`）— Phase 4 创建 PR 时回填
- [ ] 业务 Issue 与 PR 的 `Refs` 关联 — Phase 4 时回填
