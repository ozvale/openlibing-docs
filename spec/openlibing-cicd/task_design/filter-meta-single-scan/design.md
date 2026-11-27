# filter-meta 组合扫描合并（方案一） — 详细设计

业务 Issue：<https://gitcode.com/openlibing/openlibing-cicd/issues/569>

前置变更：[operation-log-query-perf](../operation-log-query-perf/design.md)（阶段一查询侧 TTL 缓存，PR !714 / !364）。本变更对应 Issue #569 根因分析评论（评论 ID 204579547）中的「方案一：合并 5 次 GROUP BY 为 1 次扫描」。

## 1. 方案设计

### 背景与目标

阶段一缓存只是把重复查询挡在缓存层，**每一次首查（含缓存过期后首查）仍对同一批 WHERE 命中的行做 5 次独立全扫描**（userName / resourceName / ip / logResult / moduleId 各一条 `GROUP BY + COUNT`，前 4 条均走回表 + temporary + filesort）。本变更在不做任何 DDL 的前提下，把 5 次 DB 扫描合并为 **2 次**：

1. **1 次组合扫描**：`GROUP BY user_name, resource_name, ip, log_result` 一条 SQL 返回组合计数行；
2. **1 次 moduleId 专用查询**：沿用既有 `selectFilterMetaGroupBy`（dimension=moduleId，GROUP BY module_id，可走 `idx_project_module_time` 前缀，本就是 5 条中最便宜的一条）。

4 个值维度的候选列表在应用侧从组合行拆分聚合，首查 DB 耗时近似降为 2/5；执行计划不变、零 DDL、与已上线 30s TTL 缓存直接叠加。

### 总体方案

```text
queryFilterMeta（缓存未命中路径）
├─ 参数 / 权限校验、时间区间校验、cacheKey 构建与缓存读取：全部不变
├─ allowed = listAllowed()（TTL 缓存，不变）
├─ selectedValues 超限（>1000）paramError：校验前移到任何 DB 查询之前统一预检（语义不变，时机提前）
├─ 请求值维度 ≥ 2（userName/resourceName/ip/logResult 中至少 2 个；恰好 1 个时直走既有 selectFilterMetaGroupBy，不启用 combo）：
│    1 次 combo 扫描（新增 selectFilterMetaCombo）：
│      SELECT user_name, resource_name, ip, log_result, COUNT(*) AS filterCount
│      FROM log_operation
│      WHERE project_id = ? AND module_id IN (白名单交集) AND operation_end_time BETWEEN ? AND ?
│      GROUP BY user_name, resource_name, ip, log_result
│      LIMIT 10000
│    ├─ 返回行数 < 10000：应用侧拆分聚合（见下），不再逐维度查 DB
│    └─ 返回行数 == 10000（可能截断）：熔断回退旧逐维度路径，正确性不劣于现状
├─ moduleId 维度（若请求）：沿用 selectFilterMetaGroupBy + fillMenuNames，不变
└─ 写缓存、返回：不变（cacheKey 构成不变）
```

**应用侧维度拆分**（对维度 d，遍历 combo 行）：

1. 跳过 d 自身值为 null / 空串的行（等价旧 SQL 的 `d IS NOT NULL AND d != ''`）；
2. 校验**其他三个维度**的 selectedValues：**严格 IN 语义**——该维度存在 selectedValues 时，行值必须命中集合（HashSet contains），未命中（含 null / 空串，天然不在集合内）即跳过该行；d 自身的 selectedValues **不过滤**（保留「候选列表不被自身过滤」语义，等价旧 SQL 的 skipDimension）；
3. 命中的行按行值累加 `filterCount`；
4. 结果交给增强后的 `toFilterMetaItems`：logResult 零值枚举补齐、selectedValues 零值补齐、**应用侧完整排序**（selected 优先 → count DESC → value 升序，替代原 SQL 的 ORDER BY）、截断 1000、moduleId 菜单名补齐（不涉及）。

### 关键决策

| 决策点                       | 结论                                                                                                                 | 理由                                                                                                                                                                      |
| ---------------------------- | -------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| moduleId 是否并入 combo      | 不并入，保持独立查询                                                                                                 | module_id 并入会使用户×资源×IP×结果组合数再乘以模块数（白名单可达数十），截断熔断风险显著上升；module_id 单查本就走索引前缀、成本最低，5→2 次已拿到主要收益（用户已确认） |
| 截断熔断阈值                 | 常量 10000（`COMBO_ROW_LIMIT`），返回行数等于阈值即回退                                                              | 项目级日志 30 天窗口内组合数实测远低于此；避免过度配置化（用户已确认）。回退保证最坏情形（超大组合基数）结果正确，仅退化为现状性能                                        |
| skip 自身维度语义            | 应用侧复现：combo 查询不带任何维度值过滤，拆分时对其他维度应用严格 IN 过滤（存在 selectedValues 则行值必须命中集合） | 与旧 SQL `skipDimension` 精确等价；单条 SQL 无法表达 4 种不同 WHERE，应用侧拆分是唯一保真路径                                                                             |
| combo 启用条件               | 仅当请求含 ≥2 个值维度时启用 combo；恰好 1 个值维度时直走既有 `selectFilterMetaGroupBy`                              | 单维度场景 combo 无归并收益，反而传输放大（检视修订）                                                                                                                     |
| 超限校验时机                 | selectedValues >1000 的 paramError 校验统一前移到任何 DB 查询之前                                                    | 避免先发 combo 查询再被拒绝的无效开销；校验语义与结果不变（检视修订）                                                                                                     |
| collation 归一化             | IN 匹配、归并 key、排序 value 均按 `Locale.ROOT` 小写后比较                                                          | 对齐 MySQL `utf8mb4_*_ci` 大小写不敏感排序规则；重音不敏感未实现（代码注释注明）；展示值经 displayNames 保留原文（检视修订）                                              |
| 空值/空串语义                | 拆分时跳过自身列空行的行；该行仍计入其他维度                                                                         | 等价旧 SQL 仅对自身列 `IS NOT NULL AND != ''` 的行为                                                                                                                      |
| 排序位置                     | 原 SQL `ORDER BY selected优先, count DESC, value` 移入应用侧 comparator                                              | combo 行无单一排序目标；应用侧排序结果与原 SQL 语义一致（selected 优先 → count 降序 → 值升序）                                                                            |
| 旧 `selectFilterMetaGroupBy` | 保留                                                                                                                 | moduleId 维度 + 熔断回退路径共用，不删                                                                                                                                    |
| 缓存层                       | 不动                                                                                                                 | 30s TTL 缓存、cacheKey 构成、TTL 配置键均不变；combo 属于缓存未命中路径内部优化                                                                                           |
| 两仓实现方式                 | 各自同构实现，不抽公共库                                                                                             | 沿用既有组织方式（跨仓共享需 common SDK 发版，超出本期范围）                                                                                                              |

## 2. 实现逻辑设计

### 2.1 Mapper 新增 combo 查询（cicd：LogPipelineMapper.xml；coderepo：OperationLogMapper.xml）

```xml
<select id="selectFilterMetaCombo" resultType="java.util.HashMap">
    SELECT user_name, resource_name, ip, log_result, COUNT(*) AS filterCount
    FROM log_operation
    <where>
        <include refid="operationLogFilters"/>   <!-- 复用既有片段；4 个维度值列表不传，IN 子句自然消失 -->
    </where>
    GROUP BY user_name, resource_name, ip, log_result
    LIMIT #{comboLimit}
</select>
```

- WHERE 复用 `operationLogFilters`：服务层构建 combo 专用 filter（projectId + 白名单交集 moduleIds + 时间区间，4 个维度值列表置空），XML 各 `<if ... size > 0>` 守卫使维度过滤子句不出现；
- `comboLimit` 传 `COMBO_ROW_LIMIT`（10000）；
- 不加任何列级 `IS NOT NULL` 过滤（拆分侧处理，保语义）。

### 2.2 Service 拆分聚合（LoggingServiceImpl，两仓同构）

新增私有方法 `aggregateDimensionsFromCombo(rows, dimensions, query, allowed)`：

```text
入参：combo 行、请求维度列表、原始查询、白名单
预计算：
  dimensionKeys = FILTER_META_DIMENSION_KEYS（静态常量表：userName/resourceName/ip/logResult 列名）
  for d: otherKeys[d] = 其余三个维度键（循环外一次性预计算，不在行循环内重复构建）
  for d: selectedSets[d] = selectedValues 按 Locale.ROOT 小写归一的 HashSet
处理：
  for d in dimensionKeys 且 d ∈ 请求维度:
    counts = LinkedHashMap                      # key 为小写归一后的 value
    for row in combo 行:
      value = row[d]（firstPresent 兼容大小写键）
      if value 为 null/空串: continue            # 自身空值不计自身维度
      for k in otherKeys[d]:
        if selectedSets[k] 非空 且 lower(row[k])（Locale.ROOT）不在集合内: continue  # 严格 IN
      counts.merge(lower(value), row.filterCount, Long::sum)
    items = toFilterMetaItems(counts, d, query)   # 零值补齐 + 应用侧排序 + 截断 1000；展示值经 displayNames 保留原文
  返回 filterMeta
```

说明：

- 维度键用静态常量表 `FILTER_META_DIMENSION_KEYS`，`otherKeys` 在行循环外预计算，避免每行重复分配（检视修订）；
- 小写归一统一用 `Locale.ROOT`，对齐 MySQL `utf8mb4_*_ci` 的大小写不敏感语义；重音不敏感（`_ai`）未实现，代码注释注明；对外展示值不使用归一化结果（零值补齐与 menu/displayNames 保留原文）。

`toFilterMetaItems` 增强：拆分路径新增重载（直接接受 counts），排序 comparator 由「仅 selected 优先（依赖 SQL 预排序的稳定排序）」改为完整三级排序 `(!selected, -count, value)`（value 比较同样按 Locale.ROOT 小写归一）；moduleId / 回退路径沿用原重载不受影响。

### 2.3 熔断回退

```text
comboRows = mapper.selectFilterMetaCombo(comboFilter, COMBO_ROW_LIMIT)
if comboRows.size() >= COMBO_ROW_LIMIT:
    走旧逐维度路径（selectFilterMetaGroupBy × N）   # 行为与现状完全一致
```

回退仅发生在组合基数异常大的项目，性能退化为现状、结果始终正确。

## 3. 类设计

| 仓                   | 类 / 文件                                            | 改动                                                                      |
| -------------------- | ---------------------------------------------------- | ------------------------------------------------------------------------- |
| openlibing-cicd      | `LogPipelineMapper.xml` + `LogPipelineMapper.java`   | 新增 `selectFilterMetaCombo`                                              |
| openlibing-cicd      | `LoggingServiceImpl`                                 | combo filter 构建、拆分聚合、熔断回退、`toFilterMetaItems` 重载与三级排序 |
| openlibing-coderepo  | `OperationLogMapper.xml` + `OperationLogMapper.java` | 同构新增                                                                  |
| openlibing-coderepo  | `LoggingServiceImpl`                                 | 同构改动                                                                  |
| openlibing-framework | 无                                                   | 不涉及                                                                    |

## 4. 数据模型设计

不涉及。log_operation 表无任何变化，无 DDL。

## 5. 性能设计

- 缓存未命中路径：4 值维度 4 次全扫描 + moduleId 1 次 → **combo 1 次全扫描 + moduleId 1 次**；首查 DB 侧耗时近似降为 2/5（全扫描行集相同，组合聚合的 CPU 开销由一次 GROUP BY 承担）。
- 网络与内存代价：传输组合行（≤10000 × 5 列）替代 4 份聚合行（各 ≤1000 × 2 列）；典型项目组合数千级，净收益为正；异常项目触发熔断回退，不放大。
- 缓存命中路径：不受影响（0 次 DB）。
- 验证方式：单测（拆分正确性、熔断回退、语义对齐）+ BETA 环境首查接口时延对比（同参数、缓存清空场景）。

## 6. API 接口设计

不涉及。`POST /openlibing-cicd/log/filter/meta` 与 coderepo 对应接口路径、入参、出参、权限语义均不变，候选值列表内容与排序与现状一致。前端无需适配。

## 7. 安全设计

- 鉴权：不变（checkProjectMember 先于缓存与查询）。
- 注入面：无新增；combo 查询沿用 MyBatis `#{}` 参数化与既有 `operationLogFilters` 片段。
- 敏感信息：不变（filter-meta 仅候选值与计数）。
- 资源保护：LIMIT 10000 熔断防组合爆炸导致的结果集膨胀；白名单交集模块过滤保留。
