# codecheck_rule_set.is_used 不同步仓库配置 — 技术设计

## 方案概述

把 `is_used` 从"事件式更新"改为**按需重算（recompute）**：以 `sig_rule_set` 为权威数据源，向 `codecheck_rule_set` 同步。`codecheck` 端提供"重算"接口，`coderepo` 端在写 `sig_rule_set` 前后回调。`is_used` 历史漂移依赖业务侧自然操作逐步收敛。

## 架构决策

### 决策 1：派生量语义"重算"而非"事件同步"
- 选择"重算"而不是"事件"的原因：`is_used` 是派生量，事件式同步在并发、失败重试、回滚场景下极易出现状态漂移。"重算"是幂等的，且只受 `sig_rule_set` 当前状态影响。
- 取舍：重算需要对每个候选 templateId 多查一次 `sig_rule_set`，但 `sig_rule_set` 数量有限（每仓库一行），性能可接受。

### 决策 2：HTTP 端点 + 旧 SigRuleSetOperation 复用
- `codecheck` 端的 `/rule-set/recompute-used` 端点接收 `List<String> templateIds`，委托给 `RuleDelegate.recomputeRuleSetUsed` → `RuleSetOperation.recomputeIsUsedByTemplateIds`。
- 复用现有 `SigRuleSetOperation`（在 `openlibing-codecheck` 端也有一份 `sig_rule_set` 的访问能力），新增 `findInUseTemplateIds(List<String> candidateIds)` 方法做"重算"判定。
- 跨服务调用使用 `RestTemplate` 风格（仓库已有 [OpenlibingCodeCheckClient](file:///d:/code/openlibing/openlibing-coderepo/src/main/java/com/openlibing/coderepo/business/feign/OpenlibingCodeCheckClient.java) 的 Feign 模式，新增 method）。

### 决策 3：重算用 `updateMulti` 而非 `updateFirst`
- 旧 `updateRuleSetUsed` 用 `updateFirst` 会导致多语言/多租户下 `template_id` 重复时只更新一条。修复后统一 `updateMulti`。

### 决策 4：affect 计算 = 旧 binding 集合 ∪ 新 binding 集合
- `addCodececkRuleSet` 在写 `sig_rule_set` 前先读旧 binding 的 templateId，写完后再读新 binding 集合，二者取并集回调 `codecheck`。
- 这样解绑的旧规则集（应该置 "0"）和新增的规则集（应该置 "1"）都会被重算。

## 涉及文件

### `openlibing-codecheck`（分支 `fix/codecheck-rule-set-is-used-sync`）

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/main/java/com/openlibing/codecheck/business/operation/rule/RuleSetOperation.java` | 修改 | 改 `updateRuleSetUsed` 走"重算"语义（`updateMulti` + 按 `sig_rule_set` 实际状态决定）；新增 `recomputeIsUsedByTemplateIds(List<String>)` |
| `src/main/java/com/openlibing/codecheck/business/operation/rule/SigRuleSetOperation.java` | 修改 | 新增 `findInUseTemplateIds(List<String> candidateTemplateIds)`：聚合 `sig_rule_set.languages[].rule_set_id` 找仍在使用的 templateId |
| `src/main/java/com/openlibing/codecheck/business/impl/RuleDelegateImpl.java` | 修改 | `updateRule` 改走新的重算方法；新增 `recomputeRuleSetUsed(List<String>)` |
| `src/main/java/com/openlibing/codecheck/business/controller/RuleController.java` | 修改 | 新增 `POST /ci-portal/v2/grant/auth/rule-set/recompute-used`（机机接口） |
| `src/test/java/com/openlibing/codecheck/business/operation/rule/RuleSetOperationTest.java` | 修改 | 覆盖多 template 命中走 `updateMulti`、`is_used` 从 "1" 回到 "0" 的分支 |
| `src/test/java/com/openlibing/codecheck/business/impl/RuleDelegateImplTest.java` | 修改 | 覆盖 `updateRule` 调度 `recomputeIsUsedByTemplateIds` |

### `openlibing-coderepo`（分支 `fix/coderepo-notify-rule-set-used`）

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/main/java/com/openlibing/coderepo/business/service/impl/RepoServiceImpl.java` | 修改 | `addCodececkRuleSet` 在写 `sig_rule_set` 前后收集 affected templateIds，回调 `codecheck` 重算接口；`defaultCodecheckRuleSet` 同样补回调；如已有删仓路径同步 |
| `src/main/java/com/openlibing/coderepo/business/feign/OpenlibingCodeCheckClient.java` | 修改 | 新增 `recomputeRuleSetUsed(List<String> templateIds)` 方法 |
| `src/test/java/com/openlibing/coderepo/business/service/impl/RepoServiceImplTest.java` | 修改 | 覆盖 addRepo 后回调了 codecheck 重算接口、传入了正确的 affected templateIds |

### `openlibing-docs`（分支 `spec/openlibing-codecheck/rule-set-is-used-sync`）

| 文件 | 操作 | 说明 |
|------|------|------|
| `spec/openlibing-codecheck/task_design/rule-set-is-used-sync/proposal.md` | 新增 | 本目录的 proposal |
| `spec/openlibing-codecheck/task_design/rule-set-is-used-sync/design.md` | 新增 | 本目录的 design |
| `spec/openlibing-codecheck/task_design/rule-set-is-used-sync/tasks.md` | 新增 | 实现任务清单 |
| `spec/openlibing-codecheck/task_design/rule-set-is-used-sync/archive.md` | 新增 | Phase 5 归档 |

> 不再做一次性 Mongo 修复脚本：`is_used` 的"1→0"回滚依赖业务侧自然操作（规则集解绑/仓库删除/规则集更新）逐步收敛。

## 关键代码示意

### `RuleSetOperation.recomputeIsUsedByTemplateIds`

```java
public void recomputeIsUsedByTemplateIds(List<String> templateIds) {
    if (CollectionUtils.isEmpty(templateIds)) {
        return;
    }
    Query zeroQuery = new Query(Criteria.where("template_id").in(templateIds));
    Update zeroUpdate = new Update().set("is_used", "0");
    mongoTemplate.updateMulti(zeroQuery, zeroUpdate, CodeCheckCollectionName.CODECHECK_RULE_SET);

    Set<String> inUseIds = sigRuleSetOperation.findInUseTemplateIds(templateIds);
    if (!inUseIds.isEmpty()) {
        Query oneQuery = new Query(Criteria.where("template_id").in(inUseIds));
        Update oneUpdate = new Update().set("is_used", "1");
        mongoTemplate.updateMulti(oneQuery, oneUpdate, CodeCheckCollectionName.CODECHECK_RULE_SET);
    }
}
```

### `SigRuleSetOperation.findInUseTemplateIds`

```java
public Set<String> findInUseTemplateIds(List<String> candidateTemplateIds) {
    if (CollectionUtils.isEmpty(candidateTemplateIds)) {
        return Collections.emptySet();
    }
    // unwind languages, 收集 languages.rule_set_id 与 candidateIds 交集
    Aggregation agg = Aggregation.newAggregation(
        Aggregation.unwind("languages"),
        Aggregation.match(Criteria.where("languages.rule_set_id").in(candidateTemplateIds)),
        Aggregation.group().addToSet("languages.rule_set_id").as("inUseIds")
    );
    AggregationResults<Document> result = mongoTemplate.aggregate(agg, MongoTableName.SIG_RULE_SET, Document.class);
    Document doc = result.getUniqueMappedResult();
    if (doc == null) return Collections.emptySet();
    return new HashSet<>(doc.getList("inUseIds", String.class, Collections.emptyList()));
}
```

### `addCodececkRuleSet` 改动核心

```java
private void addCodececkRuleSet(RepoInfoEntity repoInfoEntity,
                                List<RepoLanguageRuleSetDTO> codecheckRuleSet) {
    if (StringUtils.isNotBlank(repoInfoEntity.getCodecheckParentTaskId())) {
        return;
    }
    // 1) 取旧 binding 涉及的 templateId
    Set<String> affected = new HashSet<>(listOldTemplateIds(repoInfoEntity.getRepoId()));

    // 2) 清旧写新（保留原逻辑）
    Criteria criteria = Criteria.where("repo_id").is(repoInfoEntity.getRepoId());
    mongoTemplate.remove(Query.query(criteria), MongoTableName.SIG_RULE_SET);
    if (CollectionUtils.isNotEmpty(codecheckRuleSet)) {
        // ... 原有 save 逻辑 ...
        codecheckRuleSet.stream()
            .map(RepoLanguageRuleSetDTO::getRuleSetId)
            .filter(Objects::nonNull)
            .forEach(affected::add);
    }

    // 3) 回调 codecheck 重算
    if (!affected.isEmpty()) {
        openlibingCodeCheckClient.recomputeRuleSetUsed(new ArrayList<>(affected));
    }
}
```

## 风险 & 缓解

- **风险 1：跨服务 HTTP 调用失败** → `addCodececkRuleSet` 已有 try/catch 抛 `DataResultFailException` 触发 mysql 回滚，重算调用放在事务内异常前即可。或者采用 fire-and-forget 异步调用，重算是幂等的可以容忍偶发失败。
- **风险 2：并发配置同一仓库** → 重算幂等，无副作用。
- **风险 3：历史脏数据修复脚本** → 必须先部署 1/2/3，再执行脚本（顺序在 tasks.md 中明确）。脚本本身是只读 + 更新，可重复执行。
- **风险 4：`updateRule` 重算后与原 `updateRuleSetUsed` 行为可能略有差异** → 需在 `RuleDelegateImplTest` 补断言：传 `if_use = "1"` 的 templateId 应当被重算为 "1"，其它不受影响。

## 跨仓影响

- 跨服务 HTTP 契约：新增 `POST /ci-portal/v2/grant/auth/rule-set/recompute-used`，请求体 `List<String>`，响应 `{code, message}`。
- 调用方：仅 `openlibing-coderepo`（机机调用，不开放前端）。
- 不涉及数据库 schema 变化。
