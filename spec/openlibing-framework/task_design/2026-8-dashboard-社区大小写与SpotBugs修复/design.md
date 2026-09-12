# Dashboard 社区大小写不敏感与 SpotBugs 安全编码修复 — 技术设计

## 方案概述

本次变更分三条技术线并行：

1. **数据库层**：通过 Liquibase changeset 调整两表 `community` 列 collation 回到大小写不敏感，Java/Mapper 不动代码。
2. **Mapper SQL 层**：将 `selectByOperationUrlsAndDateRange` 的 `operation_url IN (...)` 改为 `operation_url LIKE CONCAT('%', #{url}, '%') OR ...`，子串匹配。
3. **DTO/Config 层**：对 7 个类统一应用「getter 返回不可变视图 + setter/builder 防御性拷贝」模式，同时移除 service 中的 BC_VACUOUS_INSTANCEOF。

## 架构决策

| 决策                    | 选择                                                                                         | 原因                                                                                                                                     |
| ----------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------- |
| 社区大小写方案          | DB collation `utf8mb4_0900_ai_ci`                                                            | case sensitivity 由 DB 决定，Java/Mapper 无需任何代码改动，避免在所有 SQL 中加 `LOWER()` 函数污染查询；与历史 collation 一致，回滚成本低 |
| pv/uv URL 匹配方案      | SQL `LIKE CONCAT('%', #{url}, '%')` + `OR`                                                   | 模糊匹配覆盖实际请求 URL 带 query/前缀的场景；使用 MyBatis `#{url}` 参数化避免 SQL 注入                                                  |
| SpotBugs 防御性拷贝策略 | `Collections.unmodifiableList/Map` (getter) + `new LinkedHashMap/ArrayList` (setter/builder) | 与 `api-sync-interface` 中 EI_EXPOSE_REP 修复方案一致，对外不可变、对内独立副本                                                          |
| Service instanceof 处理 | 直接移除                                                                                     | `injectMetricsIntoReports` 中 `instanceof` 检查的目标类型已由泛型/方法签名保证，移除即可消除 BC_VACUOUS_INSTANCEOF                       |
| 分支与 PR 策略          | 业务仓 `release_20260831_apollo` 单分支 + PR !420                                            | 用户自测通过后统一发版；不创建独立业务 Issue（PR-only 流程，用户已确认）                                                                 |
| commit 粒度             | 一轮交付 = 一次 commit                                                                       | 共 4 个 commit 对应 4 次交付：pv/uv 模糊匹配 → community collation → SpotBugs 修复 → DTO 格式化                                          |

## 涉及文件

### 新增文件（1 个）

| 文件                                                                                                    | 说明                                                                        |
| ------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------- |
| `src/main/resources/db/changelog/v1.0.1/dashboard/feature_ops_dashboard_community_case_insensitive.xml` | Liquibase changeset，恢复两表 `community` 列 `utf8mb4_0900_ai_ci` collation |

### 修改文件（10 个）

| 文件                                                                                                 | 操作 | 说明                                                                                                                      |
| ---------------------------------------------------------------------------------------------------- | ---- | ------------------------------------------------------------------------------------------------------------------------- |
| `src/main/resources/db/changelog/db.changelog.xml`                                                   | 修改 | 引入新 changeset 文件，按依赖顺序在 `20260824_alter_*_community_cs` 之后注册                                              |
| `src/main/resources/mapper/PvUvMapper.xml`                                                           | 修改 | `selectByOperationUrlsAndDateRange` 由 `operation_url IN (...)` 改为 `operation_url LIKE CONCAT('%', #{url}, '%') OR ...` |
| `src/main/java/com/openlibing/framework/business/mapper/PvUvMapper.java`                             | 修改 | 同步更新方法 Javadoc，说明改用 LIKE 模糊匹配                                                                              |
| `src/main/java/com/openlibing/framework/business/impl/FeatureOpsDashboardServiceImpl.java`           | 修改 | 移除 `injectMetricsIntoReports` 中的 `instanceof` 检查                                                                    |
| `src/main/java/com/openlibing/framework/common/config/DashboardMatrixConfig.java`                    | 修改 | `getCommunities`/`getFeatures` 返回 `Collections.unmodifiableList`                                                        |
| `src/main/java/com/openlibing/framework/business/dto/dashboard/DashboardFeatureDetailData.java`      | 修改 | getter 不可变视图 + setter/builder 防御性拷贝                                                                             |
| `src/main/java/com/openlibing/framework/business/dto/dashboard/DashboardMatrixData.java`             | 修改 | 同上                                                                                                                      |
| `src/main/java/com/openlibing/framework/business/dto/dashboard/DashboardMetricConfigData.java`       | 修改 | 同上                                                                                                                      |
| `src/main/java/com/openlibing/framework/business/dto/dashboard/DashboardMetricConfigRequestDTO.java` | 修改 | 同上                                                                                                                      |
| `src/main/java/com/openlibing/framework/business/dto/dashboard/DashboardMetricUpdateRequestDTO.java` | 修改 | 同上                                                                                                                      |
| `src/main/java/com/openlibing/framework/business/dto/dashboard/DashboardReportRequestDTO.java`       | 修改 | 同上                                                                                                                      |
| `src/test/java/com/openlibing/framework/business/impl/FeatureOpsDashboardServiceImplTest.java`       | 修改 | 补充 LIKE 模糊匹配测试用例，DTO 测试改用 setter                                                                           |

## 核心逻辑设计

### 1. 社区列 collation 恢复流程

```text
 Liquibase 启动
     ↓
 加载 db.changelog.xml → 注册 feature_ops_dashboard_community_case_insensitive.xml
     ↓
 changeSet 1: 20260831_alter_feature_ops_dashboard_report_community_ci
   preConditions: feature_ops_dashboard_report.community 列存在
   执行: ALTER TABLE ... MODIFY COLUMN community VARCHAR(100)
         CHARACTER SET utf8mb4 COLLATE utf8mb4_0900_ai_ci
     ↓
 changeSet 2: 20260831_alter_feature_ops_dashboard_community_feature_ci
   preConditions: feature_ops_dashboard_community_feature.community 列存在
   执行: 同上
     ↓
 rollback: 恢复为 utf8mb4_0900_as_cs（保留回滚能力）
```

执行顺序约束：必须晚于 `20260824_alter_*_community_cs` 注册，通过在 `db.changelog.xml` 末尾追加 include 保证。

### 2. PvUvMapper 模糊匹配 SQL

```xml
<select id="selectByOperationUrlsAndDateRange" ...>
    SELECT id, user_id, operation_time, operation_date, operation_url,
           operation_module, productline_id, product_id, project_id, repo_id
    FROM pv_record
    WHERE
    <foreach collection="operationUrls" item="url" open="(" separator=" OR " close=")">
        operation_url LIKE CONCAT('%', #{url}, '%')
    </foreach>
    <if test="projectIds != null and projectIds.size() > 0">
        AND project_id IN
        <foreach collection="projectIds" item="projectId"
                 open="(" separator="," close=")">
            #{projectId}
        </foreach>
    </if>
    ...
</select>
```

**安全考虑**：使用 MyBatis `#{url}` 参数化（非 `${url}`），避免 SQL 注入。`CONCAT('%', #{url}, '%')` 在 JDBC 层做参数绑定，`%` 作为字面量前缀/后缀拼接，安全。

### 3. DTO 防御性拷贝模式

```java
// getter：返回不可变视图
public List<String> getCommunities() {
    if (communities != null) {
        return Collections.unmodifiableList(communities);
    }
    synchronized (this) {
        if (communities == null) {
            communities = loadList(KEY_COMMUNITIES, DEFAULT_COMMUNITIES);
        }
        return Collections.unmodifiableList(communities);
    }
}

// setter：防御性拷贝入参
public void setBusinessMetrics(Map<String, Object> businessMetrics) {
    this.businessMetrics = businessMetrics == null ? null : new LinkedHashMap<>(businessMetrics);
}

// builder：防御性拷贝入参
public MetricConfigItemDTOBuilder aggregationUrls(List<String> aggregationUrls) {
    this.aggregationUrls = aggregationUrls == null ? null : new ArrayList<>(aggregationUrls);
    return this;
}
```

### 4. Service instanceof 移除

```text
修改前: if (metric instanceof SomeType) { ... }  // SomeType 已由方法签名保证
修改后: 直接调用 metric 上的方法                    // BC_VACUOUS_INSTANCEOF 消除
```

## 风险 & 缓解

| 风险                               | 影响                                  | 缓解                                                                                             |
| ---------------------------------- | ------------------------------------- | ------------------------------------------------------------------------------------------------ |
| LIKE 模糊匹配性能下降              | 高 `pv_record` 表数据量下全表扫描风险 | `aggregationUrls` 列表通常 ≤ 10 个，每个 LIKE 短路 OR；后续可对 `operation_url` 加索引或前缀索引 |
| LIKE `%url%` 命中过宽              | 同前缀的无关 URL 也被聚合             | `aggregationUrls` 配置粒度需精确到路径片段，避免过短公共前缀；测试用例已覆盖                     |
| collation 切换影响历史数据排序     | 历史按 `as_cs` 排序的查询结果顺序变化 | 业务侧不依赖 `community` 列排序，仅做等值匹配，影响可忽略                                        |
| 防御性拷贝增加内存与 GC 开销       | 高频构造 DTO 时分配临时 Map/List      | DTO 多为请求/响应边界对象，吞吐量未达微基准量级，影响可忽略；优先保证不可变性                    |
| Spotless 单行格式化触发 hooks 抖动 | pre-commit 钩子重新格式化             | 单 commit 内已统一为 Spotless 风格，pre-commit idempotent                                        |

## 跨仓影响

无跨仓影响。本次变更完全在 `openlibing-framework` 业务仓内完成，不涉及外部接口契约或上下游服务依赖。

## 关联

- 业务仓 PR: openlibing-framework !420 「fix(dashboard): community case-insensitive and fix SpotBugs issues」
- 涉及 commit：
  - `515536c7` 特性看板pv、uv统计urls调整为模糊匹配
  - `499a8c65` fix(dashboard): restore community column case-insensitive collation
  - `d5529b82` fix(dashboard): 修复 SpotBugs EI_EXPOSE_REP 与 BC_VACUOUS_INSTANCEOF 问题
  - `2f64997a` style(dashboard): reflow DTO setter and builder to single-line formatting
