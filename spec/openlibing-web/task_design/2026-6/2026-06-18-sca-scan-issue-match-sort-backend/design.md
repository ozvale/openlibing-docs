## Context

### 前端已落地（openlibing-web）

| 文件 | 改动 |
|------|------|
| `analysisTable.config.js` | `matched` 列 `sortable: 'custom'` |
| `gitUrlList.vue` | `sortParams`、`handleCustomSort`、`resetSortParams`、`queryRiskData` 透传 |

前端传参示例（有排序时）：

```json
{
  "scanId": "...",
  "pageNo": 1,
  "pageSize": 10,
  "sortColumn": "matched",
  "sortOrder": "descending"
}
```

### 后端现状（openlibing-sca）

| 项 | 现状 |
|---|---|
| 入口 | `OpenScanController.getScanIssueQuery` → `OpenScanServiceImpl.getScanIssue` |
| DTO | `ScanIssueQueryVO`：无排序字段 |
| 排序 | 固定 `query.with(Sort.by(Sort.Order.asc("scanFile")))`（约 1116 行） |
| 分页 | `mongoTemplate.find(query.skip(start).limit(pageSize), ...)` |
| 匹配度 | Mongo/VO 字段 `matched`，值如 `"90%"`、`"100%"` |
| 数值解析 | `FileUtil.getMatchedScore`（private，去 `%` 转 double，空值 -1.0） |

### 参考模式

`/open/scan/repos` 使用 `ScanColumnList` 白名单 + `sortColumn`/`sortOrder`（`ascending`/`descending`）。但 repos 是**内存排序**；scanIssue 是 **Mongo skip/limit**，排序必须在 DB 层完成。

## Goals / Non-Goals

**Goals:**

- 接收并处理前端已透传的 `sortColumn=matched` + `sortOrder`
- 全量数据范围内正确分页排序（非当前页本地排序）
- 与 SCA 模块 `sortColumn`/`sortOrder` 命名一致
- 非法/空排序参数安全回退，不破坏现有行为

**Non-Goals:**

- 不扩展其他列排序（`vendor`、`component` 等留待后续）
- 不改写入链路、不新增 `matchedScore` 持久化字段（本期用查询时计算）
- 不涉及 `licenseIssue/query`
- 不改前端

## Decisions

### 1. DTO 扩展

在 `ScanIssueQueryVO` 增加：

```java
private String sortColumn;
private String sortOrder;
```

无 `@NotNull`，可选字段。

### 2. 白名单枚举：新建 `ScanIssueColumnList`

与 `ScanColumnList`（repos 专用）分离，避免混用：

```java
public enum ScanIssueColumnList {
    MATCHED("matched", "matched");
    // 后续可扩展 FILE_NAME("fileName", "scanFile") 等
}
```

提供 `getMongoField(String sortColumn)` → 白名单 Mongo 字段名，非法返回空字符串。

### 3. 排序方向解析

```java
private Sort.Direction resolveDirection(String sortOrder) {
    if ("descending".equalsIgnoreCase(sortOrder)) {
        return Sort.Direction.DESC;
    }
    if ("ascending".equalsIgnoreCase(sortOrder)) {
        return Sort.Direction.ASC;
    }
    return null; // 非法 → 走默认
}
```

与 `OpenScanServiceImpl.sortScanList`（repos）及前端 Element Plus 保持一致。

### 4. `matched` 排序：Mongo Aggregation

**问题**：`matched` 为 `"90%"` 字符串，直接 `Sort.by("matched")` 会按字典序错误排序（`"9%"` > `"80%"`）。

**选择**：当 `sortColumn=matched` 且方向合法时，走 **Aggregation 管道**：

```
$match(criteria)
  → $addFields(matchedScore: 解析 matched 数值，空/非法为 -1)
  → $sort(matchedScore: 1|-1)
  → $skip
  → $limit
```

`matchedScore` 为临时计算字段，不写入文档。解析逻辑与 `FileUtil.getMatchedScore` 一致：

- 去 `%` → `Double.parseDouble`
- null/空/解析失败 → `-1.0`

**备选（弃用）**：

| 方案 | 原因 |
|------|------|
| 全量查出后内存排序 | scanId 下 issue 量大，OOM/超时 |
| 直接 Sort.by("matched") | 字符串排序错误 |
| 写入时冗余 matchedScore | 改动面大，非本期目标 |

### 5. 默认排序与非 matched 列

| 条件 | 行为 |
|------|------|
| `sortColumn`/`sortOrder` 任一为空 | `Sort.by(asc("scanFile"))`（保持现状） |
| `sortColumn` 不在白名单 | 同上，忽略非法参数 |
| `sortColumn=matched` 且合法 | Aggregation 数值排序 |

### 6. `getScanIssue` 重构结构

```text
getScanIssue(queryVO, userId)
  ├── 权限 & criteria 构建（不变）
  ├── count = mongoTemplate.count(query, ...)（不变，排序不影响 count）
  ├── if (isMatchedSort(queryVO))
  │     └── scanIssueList = executeMatchedSortQuery(criteria, queryVO, pageNo, pageSize)
  └── else
        └── query.with(defaultOrSimpleSort)
            scanIssueList = executeQuery(query, pageNo, pageSize)
  ├── enrichScanIssueData（不变）
  └── buildResponse（不变）
```

`executeMatchedSortQuery` 使用 `mongoTemplate.aggregate(..., ScanIssueVO.class)`，映射结果需排除临时字段 `matchedScore`（VO 无此字段，Spring Data 自动忽略）。

### 7. Criteria 复用

Aggregation 的 `$match` 阶段复用现有 `buildQuery` 生成的 `Criteria`（从 `Query.getQueryObject()` 或单独提取 `Criteria` 构建逻辑）。**禁止**将前端 `sortColumn` 直接拼入 Mongo 字段名。

### 8. FileUtil 调整（可选）

将 `getMatchedScore(ScanIssue)` 改为 `public static double parseMatchedScore(String matched)`，Aggregation 测试与 Java 侧单测共用，避免逻辑漂移。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| Aggregation 比简单 find 慢 | 仅 matched 排序走聚合；默认路径不变；scanId 通常有索引 |
| matched 格式异常（非数字+%） | 解析失败视为 -1.0，排到最后 |
| count 与 list 条件不一致 | count 仍用原 Query，与 $match 相同 criteria |
| 缺少 matched 索引 | 本期可接受；后续可加 computed index 或冗余字段 |

## Migration Plan

1. 后端合入后，与已部署前端联调 `gitUrlList` 匹配度升降序
2. 无需数据迁移、无 API 路径变更
3. 回滚：移除排序分支，恢复固定 `scanFile ASC`

## Open Questions

1. Mongo `scan_issue` 是否在 `scanId` 上有索引？若无，matched 排序 + 大 scanId 可能偏慢（可后续优化）。
2. 是否需要在 Swagger/接口文档补充 `sortColumn`/`sortOrder` 说明？
