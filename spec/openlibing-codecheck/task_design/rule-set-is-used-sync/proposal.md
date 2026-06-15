# codecheck_rule_set.is_used 不同步仓库配置

## 需求背景

`codecheck_rule_set` 集合的 `is_used`（"1"/"0"）字段本应反映"该规则集是否被 ≥1 个代码仓配置"，实际却长期不随仓库配置变化：

- `openlibing-coderepo` 端 addRepo / updateRepo 配置规则集时，**完全没有任何回写**到 `codecheck_rule_set.is_used`；
- `openlibing-codecheck` 端 `updateRuleSetUsed` 本身只置 "1"、不置 "0"、且用 `updateFirst`（多语言多租户下 `template_id` 重复时只更新一条）；
- 规则集被解绑、代码仓被删除后 `is_used` 永远是 "1"，导致 `delRuleSet` 误判为"正在使用"。

`is_used` 本质是 `sig_rule_set` 中"任一仓库的 `languages[].rule_set_id` 引用了本 templateId"的派生量，被当成了手工维护的"事实字段"，跨服务无回写机制必然腐化。

## 功能描述

1. 在 `openlibing-codecheck` 端新增"重算"语义：
   - 新增 `RuleSetOperation.recomputeIsUsedByTemplateIds(List<String> templateIds)`：把候选集合先全部置 "0"，再去 `sig_rule_set` 查实际被引用的 templateId 置 "1"，使用 `updateMulti` 而非 `updateFirst`。
   - 修正 `RuleSetOperation.updateRuleSetUsed` 调用方式：删 `template_id` 重复时只更新一条的隐性 bug，统一走"重算"语义。
   - 新增 HTTP 端点 `POST /ci-portal/v2/grant/auth/rule-set/recompute-used`，接收 `List<String> templateIds`，返回是否成功。
2. 在 `openlibing-coderepo` 端配置仓库规则集时回调 `codecheck` 重算接口：
   - `RepoServiceImpl.addCodececkRuleSet`：在写 `sig_rule_set` 前先查旧 binding 涉及的 templateId，写完后把"旧+新" templateIds 合并回调 codecheck 重算。
   - `RepoServiceImpl.defaultCodecheckRuleSet`：自动绑定默认规则集后同样回调。
   - 删仓路径（如有）解绑后回调。
3. 历史脏数据**不**做一次性 Mongo 修复脚本，依赖业务侧自然操作（规则集解绑/仓库删除/规则集更新）逐步收敛。详见 archive.md §7.4 的取舍说明。
4. 任务级 `updateRule` 改走新的重算方法（行为更准）。

不做：
- 不改变 `is_used` 字段类型（保持 `String "0"/"1"`）。
- 不做"读时实时聚合"改造（保持冗余字段 + 重算同步的方案）。
- 不动防投毒规则集相关逻辑。
- 不改前端展示。

## 验收标准

- [ ] 仓库 add/updateRepo 后，关联规则集 `is_used = "1"`，解除关联的规则集 `is_used = "0"`，结果与 `sig_rule_set` 一致
- [ ] 任务级 `updateRule` 修改规则集后，同上重算
- [ ] `delRuleSet` 对无仓库引用的规则集能成功删除
- [ ] 新增 `codecheck` 端 `/rule-set/recompute-used` 端点作为机机接口
- [ ] ~~提供一次性 Mongo 修复脚本 + 运行手册~~ — 取消：由 A/B 仓"重算"语义自然收敛
- [ ] `RuleSetOperationTest` 覆盖：多 template 命中走 `updateMulti`；`is_used` 从 "1" 回到 "0" 的分支
- [ ] `RepoServiceImplTest` 覆盖：addRepo 后回调了 codecheck 重算接口、传入了正确的 affected templateIds
- [ ] `updateRule` 单测覆盖：调度 `RuleSetOperation.recomputeIsUsedByTemplateIds` 而非旧的 `updateRuleSetUsed`

## 影响范围

| 仓 | 改动 |
| --- | --- |
| `openlibing-codecheck` | 新增 `/rule-set/recompute-used` 端点；`RuleSetOperation` 新增 `recomputeIsUsedByTemplateIds`；`updateRuleSetUsed` 走"重算"语义；`updateRule` 改走新方法 |
| `openlibing-coderepo` | `addCodececkRuleSet` / `defaultCodecheckRuleSet` 在写完 `sig_rule_set` 后回调 `codecheck` 重算接口；删仓路径同步 |
| `openlibing-docs` | 本目录归档 + Phase 5 archive |

## 关联

- 业务 Issue: https://gitcode.com/taohuoquan/openlibing-codecheck/issues/1
- 跨仓 PR 互引：`taohuoquan/openlibing-coderepo#<n>` ↔ `taohuoquan/openlibing-codecheck#<n>`
