# Bug 修复：分支列表 UT 覆盖率排序不生效

| 项           | 内容                                                                                                          |
| ------------ | ------------------------------------------------------------------------------------------------------------- |
| 所属仓       | openlibing-coderepo                                                                                           |
| 接口         | `POST /gateway/openlibing-coderepo/repo/branch/list`（项目维度分支列表）                                      |
| 现象         | 前端传 `sortField=utCoverage&sortOrder=desc`，列表未按行覆盖率排序，实际仍按更新时间排序                      |
| 前端请求示例 | `{"projectId":3,"pageNum":1,"pageSize":10,"sortField":"utCoverage","sortOrder":"desc"}`                       |
| 修复分支     | `fix-ut-coverage-sort`（基于 master）                                                                          |
| 修复日期     | 2026-11-12                                                                                                    |

## 1. 根因分析

排序参数在链路上有两层白名单校验，**两层均未纳入 `utCoverage`**，导致该字段被静默回退为默认排序，无任何报错：

```text
QueryProjectBranchDTO.sortField = "utCoverage"
  ↓ RepoServiceImpl#buildProjectBranchQueryEntity
      resolveProjectBranchSortField("utCoverage")
        ↓ PROJECT_BRANCH_SORT_FIELD_MAP 白名单（无 "utCoverage" 条目）
          → getOrDefault 回退 PROJECT_BRANCH_DEFAULT_SORT_FIELD = "update_at"
  ↓ RepoBranchInfoMapper.xml <sql id="projectBranchOrderBy">
      <choose> 无 ut_line_coverage 分支
        → <otherwise>b.update_at</otherwise>
```

关键事实：**数据侧具备排序条件**。`queryProjectBranchByLimit` 本就 SELECT 了 repo_branch 分支表的 UT 覆盖率快照列 `b.ut_line_coverage`（与 `code_scale`、`static_alert_count` 等度量快照列同表同模式），仅排序白名单遗漏该字段。白名单双重校验的设计目的是防 SQL 注入（用户输入不直接拼列名），因此修复不是放开透传，而是在两层白名单中补齐合法映射。

## 2. 修复方案（共 2 行生产代码 + 1 个契约测试）

### 2.1 Java 服务层白名单补映射

`RepoServiceImpl#PROJECT_BRANCH_SORT_FIELD_MAP`：

```java
"staticAlertCount", "static_alert_count",
"utCoverage", "ut_line_coverage");   // 新增
```

### 2.2 Mapper XML ORDER BY 补 when 分支

`RepoBranchInfoMapper.xml <sql id="projectBranchOrderBy">`：

```xml
<when test="info.sortField == 'static_alert_count'">b.static_alert_count</when>
<when test="info.sortField == 'ut_line_coverage'">b.ut_line_coverage</when> <!-- 新增 -->
<otherwise>b.update_at</otherwise>
```

### 2.3 SQL 渲染契约测试防回归

`RepoBranchInfoMapperSqlTest` 新增用例 `projectBranchOrderBy_RendersBareColumn_ForUtLineCoverage`：断言该 when 分支渲染为**裸列** `b.ut_line_coverage`，防止被误删或改写成 `IFNULL` 包裹（NULL 按 0 参与排序会导致未上报分支与 0 覆盖率分支混排）。

## 3. 排序语义（沿用仓内既定口径）

- **裸列排序，依赖 MySQL 原生 NULL 语义**：`desc` 时无 UT 覆盖率（未上报）的分支恒排最后，`asc` 时恒排最前——与 `static_alert_count` 及其余度量快照字段口径完全统一（该口径已在 staticAlertCount 排序定案时确认）。
- UT 覆盖率快照列由上报链路写入/维护（分支最新一次成功解析的行覆盖率），排序值与详情页展示值同源，无一致性风险。

## 4. 影响范围与风险

| 维度     | 评估                                                                                     |
| -------- | ---------------------------------------------------------------------------------------- |
| 改动面   | 2 行生产代码（白名单映射 + ORDER BY 分支）+ 1 个轻量契约测试用例，无接口契约/DDL/MQ 变化 |
| 兼容性   | 纯增量：`utCoverage` 从「静默回退 update_at」变为按预期排序；其余字段行为不变             |
| SQL 注入 | sortField 仍经白名单归一后才进入 ORDER BY（`<choose>` 精确匹配 OGNL 常量），无注入面扩大 |
| 性能     | ORDER BY 列与既有度量列同表同模式，无新增 join/子查询；如需可后续评估 `ut_line_coverage` 索引 |
| 数据     | 无 DDL、无数据迁移                                                                       |

## 5. 验证

- `RepoBranchInfoMapperSqlTest`：2/2 通过（static_alert_count + ut_line_coverage 裸列断言）。
- 建议联调验证：`projectId=3` 下传 `sortField=utCoverage&sortOrder=desc`，确认列表按行覆盖率降序、无覆盖率的分支排尾部；`sortOrder=asc` 时排头部。
