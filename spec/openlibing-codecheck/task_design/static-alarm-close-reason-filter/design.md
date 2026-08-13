# static-alarm-close-reason-filter — 技术设计

## 方案概述

在 `static_alarm_issue` 主表新增 `list_state` 派生字段，将 `status` 与关闭原因（屏蔽类型 / 自动修复 / 注释抑制）的组合预计算为单一枚举值。写入侧在所有 status 流转点同步刷新 list_state，查询侧用 list_state 替代 status + 关闭原因组合判断。索引统一收敛到 `repo_key + list_state + sortField` 前缀，从 12 个收敛到 7 个。

## 架构决策

### 1. list_state 派生字段而非引入关闭原因冗余字段

采用单一 list_state 枚举（7 个取值）而非 status + 关闭原因组合字段，理由：

- list_state 是预计算值，查询时无需多字段 equality 组合，索引前缀更短
- 当前主表无关闭原因冗余字段，若新增 closeReason 字段需从 revisions 反推后写入，与直接预计算 list_state 等价但多一层映射
- list_state 直接对应前端 tab 语义，无需查询时再映射

### 2. 不删除 status 字段

list_state 是查询优化字段，不是 status 的替换。保留 status 的理由：

- revisions 历史事件流不读 status，但 status 是审计快照
- 其他潜在消费方（如导出、报表、跨服务调用）可能依赖 status 原始值
- list_state 与 status 的一致性由写入侧保证，status 仍可作为兜底校验

### 3. 保留 idx_issue_branch_status 三元组前缀索引

不下线该索引，理由：

- `searchRepos` 按 owner/repo regex 前缀匹配，正则前缀无法用 repo_key 替代
- `resolveDisappearedIssues` 查询形状 `repo_type+owner+repo+branch+status in [OPEN, PENDING_REVIEW]` 完美命中前 5 字段前缀
- 该索引同时覆盖两个查询路径，是三元组前缀索引中唯一不可替代的

### 4. 不迁移 resolveDisappearedIssues 到 repo_key

保持现有 repo_type+owner+repo+branch+status 查询形状，理由：

- 命中保留的 idx_issue_branch_status 索引，性能可接受
- 该路径是离线批处理（扫描消失自动 RESOLVED），非用户感知路径
- 迁移到 repo_key 需要新索引带 branch 字段，反而引入索引膨胀

### 5. buildSort 注释清理而非逻辑修改

DTO 字段默认值为 "severity"，前端 importance 选项不传 sortBy 时，Jackson 反序列化保留默认值，buildSort 走 `SORT_FIELD_MAP.getOrDefault("severity", "last_seen_at")` 返回 "severity_rank"。fallback "last_seen_at" 是死代码（@Pattern 拦截非法值，DTO 默认值保证 sortBy 非 null）。

**核实结论**：前端 importance 排序时 `query.sortBy = ''`（空字符串），buildParams 中 `'' && query.sortOrder` 为 false，走 `: {}` 分支，**请求体完全不带 sortBy key**（不是传 null）。Jackson 反序列化时 JSON 里没有 sortBy key，DTO 字段保留 Java 声明的默认值 "severity"。Claude 担心的反序列化陷阱（前端传 null 覆盖默认值）在本系统不适用，因为前端是"完全不带 key"而不是"传 null"。

**可选防御性改动**：在 DTO sortBy 字段上加 `@JsonSetter(nulls = Nulls.SKIP)`，防止将来其他调用方传 null 触发 fallback 死代码路径。这是防御性编程，不是 bug 修复。

仅清理 buildSort 误导性注释，不改逻辑，避免引入用户可感知的行为变更。

### 6. 保留 idx_issue_repo_key_state_last_seen 索引

虽然前端不传 lastSeenAt 排序，但 DTO @Pattern 仍允许该入参，对外契约层面支持。保守保留该索引以覆盖潜在外部调用方，避免外部调用方传 lastSeenAt 时退化为内存排序。

### 7. facet 聚合按 tab 精确收窄 list_state

`buildFacetCriteria` 按 dto.tab 精确收窄 list_state $in，避免 $in 全部 7 值放大候选集。例如"已忽略" tab 下，list_state $in 精确到 3 个 IGNORED_* 值。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `StaticAlarmIssueEntity.java` | 修改 | 新增 list_state 字段 |
| `StaticAlarmListStateEnum.java` | 新增 | 枚举定义与映射方法 |
| `StaticAlarmOperation.java` | 修改 | 查询路径合并、写入路径同步、facet 收窄、buildSort 注释清理 |
| `StaticAlarmServiceImpl.java` | 修改 | 切换调用统一查询函数 |
| `StaticAlarmQueryDTO.java` | 修改 | 新增 tab 字段 |
| `StaticAlarmFilterOptionsQueryDTO.java` | 修改 | 新增 tab 字段 |
| `StaticAlarmIssueListVO.java` | 修改 | 新增 listState 字段返回前端 |
| `StaticAlarmIssueCountVO.java` | 修改 | 去掉 unresolvedCount / closedCount 旧字段，替换为 6 个 list_state 分组计数字段 |
| `static_alarm_index_governance.xml` | 修改 | 新增/下线索引 + 历史回填 changeSet |

## 核心改动点

### 1. StaticAlarmListStateEnum 枚举定义

```java
public enum StaticAlarmListStateEnum {
    OPEN("OPEN", "待处理"),
    PENDING_REVIEW("PENDING_REVIEW", "待复核"),
    IGNORED_FALSE_POSITIVE("IGNORED_FALSE_POSITIVE", "已忽略-误报"),
    IGNORED_TEST_USAGE("IGNORED_TEST_USAGE", "已忽略-测试使用"),
    IGNORED_WONT_FIX("IGNORED_WONT_FIX", "已忽略-不修复"),
    RESOLVED_AUTO("RESOLVED_AUTO", "已修复-自动"),
    SUPPRESSED_BY_COMMENT("SUPPRESSED_BY_COMMENT", "已抑制-注释");

    private final String code;
    private final String description;
    // 构造函数、getter 略

    /**
     * Resolve list_state values by frontend tab.
     * @param tab frontend tab identifier (PENDING / IGNORED / RESOLVED_AUTO / SUPPRESSED)
     * @return list of list_state codes for $in query
     */
    public static List<String> resolveListStatesByTab(String tab) {
        if ("PENDING".equals(tab)) {
            return Arrays.asList(OPEN.code, PENDING_REVIEW.code);
        }
        if ("IGNORED".equals(tab)) {
            return Arrays.asList(IGNORED_FALSE_POSITIVE.code, IGNORED_TEST_USAGE.code, IGNORED_WONT_FIX.code);
        }
        if ("RESOLVED_AUTO".equals(tab)) {
            return Collections.singletonList(RESOLVED_AUTO.code);
        }
        if ("SUPPRESSED".equals(tab)) {
            return Collections.singletonList(SUPPRESSED_BY_COMMENT.code);
        }
        // 兜底：返回全部 exposable 值
        return exposableCodes();
    }

    /**
     * Resolve list_state by shield type (for "已忽略" tab 二级筛选).
     * @param shieldType shield type from dto (误报 / 测试使用 / 不修复)
     * @return precise list_state code
     */
    public static String resolveListStateByShieldType(String shieldType) {
        if ("误报".equals(shieldType)) return IGNORED_FALSE_POSITIVE.code;
        if ("测试使用".equals(shieldType)) return IGNORED_TEST_USAGE.code;
        if ("不修复".equals(shieldType)) return IGNORED_WONT_FIX.code;
        return IGNORED_WONT_FIX.code; // 兜底
    }
}
```

### 2. StaticAlarmIssueEntity 新增字段

```java
@Field("list_state")
@Indexed
private String listState;
```

### 3. 查询路径合并

合并 `buildIssueCriteria` 与 `buildRepoCoordinatesCriteria` 为统一函数：

```java
private Criteria buildIssueCriteriaUnified(StaticAlarmQueryDTO dto) {
    // 单仓场景：服务端按 repo_type/owner/repo 计算 repo_key
    List<String> repoKeys = resolveRepoKeys(dto);
    Criteria base = new MongoCriteriaBuilder()
        .inIfNotEmpty("repo_key", repoKeys)
        .eqIfPresent("pipeline_id", dto.getPipelineId())
        .likeIfPresent("pipeline_name", dto.getPipelineName())
        .inIfNotEmpty("branch", dto.getBranches())
        .inIfNotEmpty("severity", dto.getSeverities())
        .inIfNotEmpty("rule_id", dto.getRuleIds())
        .inIfNotEmpty("language", dto.getLanguages())
        .inIfNotEmpty("cwe_tags", dto.getCweTags())
        .inIfNotEmpty("tool", dto.getTools())
        .eqIfPresent("latest_snapshot.source", dto.getSource())
        .build()
        .andOperator(buildOwnerUserIdsCriteria(dto.getOwnerUserIds()));
    return applyListStateAndCategoryFilter(base, dto);
}

private List<String> resolveRepoKeys(StaticAlarmQueryDTO dto) {
    if (CollectionUtils.isNotEmpty(dto.getRepoKeys())) {
        return dto.getRepoKeys();
    }
    // 单仓场景：按 repo_type/owner/repo 计算 repo_key
    if (CollectionUtils.isNotEmpty(dto.getRepos())) {
        return dto.getRepos().stream()
            .map(repo -> RepoUrlParser.buildRepoKey(dto.getRepoTypes(), dto.getOwners(), repo))
            .distinct()
            .collect(Collectors.toList());
    }
    return Collections.emptyList();
}
```

### 4. buildListStateCriteria 替代 buildStatusCriteria

```java
private Criteria buildListStateCriteria(StaticAlarmQueryDTO dto) {
    // 新前端：按 tab 映射
    if (StringUtils.isNotEmpty(dto.getTab())) {
        List<String> listStates = StaticAlarmListStateEnum.resolveListStatesByTab(dto.getTab());
        // "已忽略" tab 下叠加屏蔽类型二级筛选
        if ("IGNORED".equals(dto.getTab()) && StringUtils.isNotEmpty(dto.getShieldType())) {
            String precise = StaticAlarmListStateEnum.resolveListStateByShieldType(dto.getShieldType());
            return Criteria.where("list_state").is(precise);
        }
        return Criteria.where("list_state").in(listStates);
    }
    // 默认：待处理
    return Criteria.where("list_state").in(OPEN.code, PENDING_REVIEW.code);
}
```

### 5. 写入侧 list_state 同步

#### buildIssueEntity（新建）

```java
if (Boolean.TRUE.equals(issue.isSuppressed())) {
    entity.setStatus(StaticAlarmStatusEnum.RESOLVED.getCode());
    entity.setListState(StaticAlarmListStateEnum.SUPPRESSED_BY_COMMENT.getCode());
    // 新增：push SUPPRESSED_RESOLVED 事件到 revisions（用于回填脚本判别）
    entity.addRevision(buildSuppressedResolvedRevision(issue));
} else {
    entity.setStatus(StaticAlarmStatusEnum.OPEN.getCode());
    entity.setListState(StaticAlarmListStateEnum.OPEN.getCode());
}
```

#### updateExistingIssue（翻转）

```java
if (existingIssue.isSuppressed() && !StaticAlarmStatusEnum.IGNORED.getCode().equals(existing.getStatus())
        && !StaticAlarmStatusEnum.PENDING_REVIEW.getCode().equals(existing.getStatus())) {
    existing.setStatus(StaticAlarmStatusEnum.RESOLVED.getCode());
    existing.setListState(StaticAlarmListStateEnum.SUPPRESSED_BY_COMMENT.getCode());
} else if (StaticAlarmStatusEnum.RESOLVED.getCode().equals(existing.getStatus())
        && !existingIssue.isSuppressed()) {
    existing.setStatus(StaticAlarmStatusEnum.OPEN.getCode());
    existing.setListState(StaticAlarmListStateEnum.OPEN.getCode());
    existing.addRevision(buildReopenedRevision());
}
```

#### batchShieldIssues

```java
Update update = new Update()
    .set("status", StaticAlarmStatusEnum.IGNORED.getCode())
    .set("list_state", StaticAlarmListStateEnum.resolveListStateByShieldType(shieldType))
    .push("revisions", buildRevision(...));
```

#### batchUnshieldIssues

```java
Update update = new Update()
    .set("status", StaticAlarmStatusEnum.OPEN.getCode())
    .set("list_state", StaticAlarmListStateEnum.OPEN.getCode())
    .push("revisions", buildRevision(...));
```

#### resolveDisappearedIssues

```java
Update update = new Update()
    .set("status", StaticAlarmStatusEnum.RESOLVED.getCode())
    .set("list_state", StaticAlarmListStateEnum.RESOLVED_AUTO.getCode())
    .set("resolved_at", LocalDateTime.now());
```

### 6. buildFacetCriteria 按 tab 收窄

```java
private Criteria buildFacetCriteria(StaticAlarmFilterOptionsQueryDTO dto, String excludeField) {
    // ... 其他字段筛选 ...
    // list_state 按 tab 精确收窄
    if (StringUtils.isNotEmpty(dto.getTab())) {
        List<String> listStates = StaticAlarmListStateEnum.resolveListStatesByTab(dto.getTab());
        if (!"list_state".equals(excludeField)) {
            criteria.and("list_state").in(listStates);
        }
    }
    return criteria;
}
```

### 7. countIssuesGroupByListState

```java
public Map<String, Long> countIssuesGroupByListState(StaticAlarmQueryDTO dto) {
    // 用 $facet 一次拿到各 tab 数量，避免 4 次 count
    FacetOperation facet = Aggregation.facet(
        buildCountFacet("PENDING", OPEN.code, PENDING_REVIEW.code),
        buildCountFacet("IGNORED", IGNORED_FALSE_POSITIVE.code, IGNORED_TEST_USAGE.code, IGNORED_WONT_FIX.code),
        buildCountFacet("RESOLVED_AUTO", RESOLVED_AUTO.code),
        buildCountFacet("SUPPRESSED", SUPPRESSED_BY_COMMENT.code)
    ).as("counts");
    // ... 执行聚合 ...
}
```

### 8. buildSort 注释清理

```java
/**
 * Build sort by dto.sortBy (mapped via SORT_FIELD_MAP).
 * DTO field default value is "severity", @Pattern validates input,
 * fallback "last_seen_at" is dead code (never triggered).
 */
private Sort buildSort(StaticAlarmQueryDTO dto) {
    String sortBy = dto.getSortBy();
    String mongoField = SORT_FIELD_MAP.getOrDefault(sortBy, "last_seen_at");
    // 逻辑不变
}
```

### 9. 历史数据回填脚本

Liquibase changeSet 通过 MongoDB runCommand 执行 aggregation pipeline：

```javascript
// 回填脚本伪代码
db.static_alarm_issue.aggregate([
  {
    $addFields: {
      list_state: {
        $switch: {
          branches: [
            { case: { $eq: ["$status", "OPEN"] }, then: "OPEN" },
            { case: { $eq: ["$status", "PENDING_REVIEW"] }, then: "PENDING_REVIEW" },
            {
              case: { $eq: ["$status", "IGNORED"] },
              then: {
                $let: {
                  vars: {
                    lastShield: {
                      $arrayElemAt: [
                        {
                          $filter: {
                            input: "$revisions",
                            cond: { $eq: ["$$this.event_type", "SHIELD"] }
                          }
                        },
                        -1
                      ]
                    }
                  },
                  in: {
                    $switch: {
                      branches: [
                        { case: { $eq: ["$$lastShield.shield_type", "误报"] }, then: "IGNORED_FALSE_POSITIVE" },
                        { case: { $eq: ["$$lastShield.shield_type", "测试使用"] }, then: "IGNORED_TEST_USAGE" },
                        { case: { $eq: ["$$lastShield.shield_type", "不修复"] }, then: "IGNORED_WONT_FIX" }
                      ],
                      default: "IGNORED_WONT_FIX"
                    }
                  }
                }
              }
            },
            {
              case: { $eq: ["$status", "RESOLVED"] },
              then: {
                $cond: {
                  if: {
                    $gt: [
                      {
                        $size: {
                          $filter: {
                            input: "$revisions",
                            cond: { $eq: ["$$this.event_type", "SUPPRESSED_RESOLVED"] }
                          }
                        }
                      },
                      0
                    ]
                  },
                  then: "SUPPRESSED_BY_COMMENT",
                  else: "RESOLVED_AUTO"
                }
              }
            }
          ],
          default: "OPEN"
        }
      }
    }
  }
]).forEach(function(doc) {
  db.static_alarm_issue.updateOne(
    { _id: doc._id },
    { $set: { list_state: doc.list_state } }
  );
});
```

**已知局限**：status=RESOLVED 且无 SUPPRESSED_RESOLVED 事件的存量记录会被判为 RESOLVED_AUTO。历史 suppressed 记录因 buildIssueEntity 原不写主表 revisions，会被误判。本次改造同步让 buildIssueEntity suppressed 路径写 SUPPRESSED_RESOLVED 事件，仅对新数据准确。

### 10. Liquibase changeSet 设计

索引新增（幂等，使用 createIndexes 命令）：

```xml
<changeSet id="20260807_create_idx_repo_key_state_first_seen" author="y00845766">
    <ext:runCommand>
        <ext:command>
            {
              "createIndexes": "static_alarm_issue",
              "indexes": [
                {
                  "key": { "repo_key": 1, "list_state": 1, "first_seen_at": -1 },
                  "name": "idx_issue_repo_key_state_first_seen",
                  "background": true
                }
              ]
            }
        </ext:command>
    </ext:runCommand>
</changeSet>
```

索引下线（幂等，使用 ifExists 检查）：

```xml
<changeSet id="20260807_drop_idx_issue_list" author="y00845766">
    <ext:runCommand>
        <ext:command>
            {
              "dropIndexes": "static_alarm_issue",
              "index": "idx_issue_list"
            }
        </ext:command>
    </ext:runCommand>
    <ext:preConditions>
        <ext:indexExists collectionName="static_alarm_issue" indexName="idx_issue_list"/>
    </ext:preConditions>
</changeSet>
```

历史回填：

```xml
<changeSet id="20260807_backfill_list_state" author="y00845766">
    <ext:runCommand>
        <ext:command>
            // 上文回填脚本
        </ext:command>
    </ext:runCommand>
</changeSet>
```

## 数据模型设计

### static_alarm_issue 集合新增字段

| 字段名 | 类型 | 说明 |
|---|---|---|
| list_state | String | 派生状态枚举，写入时由 status + 关闭原因计算得出 |

### list_state 取值映射

| list_state | 对应 status | 触发场景 | 写入代码位置 |
|---|---|---|---|
| OPEN | OPEN | 新建未抑制 / RESOLVED 翻回 | buildIssueEntity / updateExistingIssue / batchUnshieldIssues |
| PENDING_REVIEW | PENDING_REVIEW | 预留（当前无自动写入路径） | — |
| IGNORED_FALSE_POSITIVE | IGNORED | 屏蔽 + shieldType=误报 | batchShieldIssues |
| IGNORED_TEST_USAGE | IGNORED | 屏蔽 + shieldType=测试使用 | batchShieldIssues |
| IGNORED_WONT_FIX | IGNORED | 屏蔽 + shieldType=不修复 | batchShieldIssues |
| RESOLVED_AUTO | RESOLVED | 扫描消失自动 RESOLVED | resolveDisappearedIssues |
| SUPPRESSED_BY_COMMENT | RESOLVED | SARIF suppressions 标记 | buildIssueEntity / updateExistingIssue |

**注意**：upsertInstance 操作的是 instance 子表（`STATIC_ALARM_ISSUE_INSTANCE` 集合），不直接修改主表 status/list_state。主表 list_state 由 buildIssueEntity（新建）和 updateExistingIssue（已存在刷新）同步设置。upsertInstance 中的 suppressed 处理只影响 instance 子表的 scan_status 和 history，不影响主表 list_state。因此 upsertInstance 不出现在 SUPPRESSED_BY_COMMENT 触发代码位置中，也不需要同步刷新 list_state。

### 索引变化

| 操作 | 索引名 | 字段 |
|---|---|---|
| 保留 | idx_issue_fingerprint (unique) | repo_type, owner, repo, branch, fingerprint_key |
| 保留 | idx_issue_branch_status | repo_type, owner, repo, branch, status, severity |
| 新增 | idx_issue_repo_key_state_first_seen | repo_key, list_state, first_seen_at:-1 |
| 新增 | idx_issue_repo_key_state_updated_at | repo_key, list_state, updatedAt:-1 |
| 新增 | idx_issue_repo_key_state_severity | repo_key, list_state, severity_rank:1 |
| 新增 | idx_issue_repo_key_state_last_seen | repo_key, list_state, last_seen_at:-1 |
| 新增 | idx_issue_repo_key_rule | repo_key, rule_id |
| 下线 | idx_issue_list | 被新索引替代 |
| 下线 | idx_issue_rule | 被 idx_issue_repo_key_rule 替代 |
| 下线 | idx_issue_list_first_seen | 被新索引替代 |
| 下线 | idx_issue_sort_last_seen | 与 idx_issue_list 前缀重叠 |
| 下线 | idx_issue_sort_updated_at | 被新索引替代 |
| 下线 | idx_issue_sort_severity | 被新索引替代 |
| 下线 | idx_issue_repo_key_status_sort_last_seen | 字段升级为 list_state |
| 下线 | idx_issue_repo_key_sort_severity | 字段升级为 list_state |
| 下线 | idx_issue_repo_key_sort_updated_at | 字段升级为 list_state |
| 下线 | idx_issue_repo_key_sort_first_seen | 字段升级为 list_state |

最终索引数：12 → 7。

## 性能设计

### 查询场景索引覆盖矩阵

| 查询场景 | 走的索引 | 排序字段在索引 | 退化风险 |
|---|---|---|---|
| list 接口（firstSeenAt） | idx_issue_repo_key_state_first_seen | 是 | 无 |
| list 接口（updatedAt） | idx_issue_repo_key_state_updated_at | 是 | 无 |
| list 接口（severity_rank，importance 默认） | idx_issue_repo_key_state_severity | 是 | 无 |
| list 接口（lastSeenAt） | idx_issue_repo_key_state_last_seen | 是 | 无 |
| list 接口（深筛选 + 上述排序） | 同上，深筛选走 fetch | 是 | 无 |
| count 接口 | repo_key + list_state 前缀 | 无排序 | 无 |
| countIssuesGroupByListState | repo_key + list_state 前缀 | 无（聚合） | 无 |
| findAllFilterOptions (facet) | repo_key + list_state 前缀，其他维度 fetch | 无（facet） | 性能风险但不失败 |
| searchRepos | idx_issue_branch_status | 无（group by） | 无 |
| resolveDisappearedIssues | idx_issue_branch_status | 无 | 无 |
| 导出 _id 游标分页 | repo_key + list_state + 默认 _id 索引 | _id asc | 性能风险但不失败 |
| findIssueById / findIssueStatusByIds | 默认 _id 索引 | 无 | 无 |
| upsertIssue | idx_issue_fingerprint (unique) | 无 | 无 |
| batchShield/Unshield/Assign/Cleanup | 默认 _id 索引 | 无 | 无 |

14 类查询场景中，12 类完全覆盖零退化，2 类有性能风险但不会查询失败。

### 性能风险点缓解

1. **findAllFilterOptions 的 facet 聚合**：buildFacetCriteria 按 dto.tab 精确收窄 list_state，候选集收窄后 fetch 开销可控。
2. **导出接口的 _id 游标分页**：导出是低频操作，单批数据量不会超过 32MB 内存排序限制。

### 入库开销

static_alarm_issue 入库通过消息队列异步写入，非实时写入。新增 5 个索引带来的入库时间开销可接受。本次改造一次性新增 5 个 + 下线 10 个，索引净减 5 个。

## API 接口设计

### 列表查询接口

- URL：POST /static-alarm/v1/list
- 请求参数：
  - tab（String，必填）：前端 tab 标识，取值 PENDING / IGNORED / RESOLVED_AUTO / SUPPRESSED。后端按 tab 映射 list_state $in。
  - shieldType（String，可选）：屏蔽类型筛选，取值 误报 / 测试使用 / 不修复。仅"已忽略" tab 下生效。
  - 去掉 statuses / closed 字段（前端同步改为传 tab）。
- 返回参数新增：
  - listState（String）：每条记录的 list_state 值。

### 计数接口

- URL：POST /static-alarm/v1/issue/count
- **策略：新字段替换旧字段（前端同步改）**
- `StaticAlarmIssueCountVO` 字段变化：
  - 去掉 `unresolvedCount` / `closedCount` 旧字段
  - 新增 6 个 list_state 分组计数字段：
    - `pendingCount`（long）：待处理数量（list_state = OPEN + PENDING_REVIEW）
    - `ignoredFalsePositiveCount`（long）：已忽略-误报数量
    - `ignoredTestUsageCount`（long）：已忽略-测试使用数量
    - `ignoredWontFixCount`（long）：已忽略-不修复数量
    - `resolvedAutoCount`（long）：已修复-自动数量
    - `suppressedByCommentCount`（long）：已抑制-注释数量
- Response JSON 示例：

```json
{
  "code": 0,
  "data": {
    "pendingCount": 15,
    "ignoredFalsePositiveCount": 5,
    "ignoredTestUsageCount": 2,
    "ignoredWontFixCount": 3,
    "resolvedAutoCount": 1,
    "suppressedByCommentCount": 1
  }
}
```

### 筛选项接口

- URL：POST /static-alarm/v1/issue/filter-options
- 请求参数：tab（String，必填），用于 facet 按 tab 精确收窄 list_state。

### 屏蔽接口

- URL：POST /static-alarm/v1/issue/shield
- 行为变化：batchShieldIssues 在 Update 中同步落 list_state，按 shieldType 映射。

## 安全设计

### 鉴权

继承已有鉴权逻辑。本次改造不新增特殊权限，list/count/shield 等接口的权限校验保持现状。

### 敏感信息

屏蔽操作人 userId / userName 已通过 revisions 事件流记录，本次改造不新增敏感信息存储。日志不打印 userId 明文，沿用现有日志脱敏策略。

### 硬编码

本次改造无新增硬编码。list_state 枚举值通过 StaticAlarmListStateEnum 统一管理，不在业务代码中硬编码字符串。

### 审计日志

人工屏蔽 / 取消屏蔽操作通过 revisions 事件流记录，本次改造新增 SUPPRESSED_RESOLVED 事件类型用于 SARIF suppressions 标记的写入侧审计。revisions 事件流保持 push-only 语义，不读 status 字段做判断，list_state 新增不破坏审计链路。
