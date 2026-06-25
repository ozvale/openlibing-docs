# repo-query-multi-select — 技术设计

## 方案概述

在 `/project-repo/query-repo` 接口的请求 DTO 中新增 4 个 List 过滤字段（`purposes` / `visibilities` / `repoLanguages` / `statuses`）和 1 个单值字段（`status`）。Service 层将 List 透传到 `RepoInfoEntity`（`@TableField(exist=false)`），Mapper SQL 改用 `<choose>/<when>/<otherwise>`：List 非空走 `IN (...)`，否则回退到原单值字段。

## 架构决策

### 决策 1：多选语义采用 OR（任一命中）

**选择**：传 `["java","go"]` 表示"语言为 java 或 go"，SQL 走 `IN ('java','go')`。

**原因**：运营场景的多选筛选语义是"任一命中"（如"用途包含 测试 或 正式"），符合用户预期。

### 决策 2：双轨保留 List + 原 String

**选择**：保留原 `purpose` / `visibility` / `repoLanguage` 字符串字段，新增 `purposes` / `visibilities` / `repoLanguages` List 字段；status 字段（之前未在 DTO 暴露）新增 `status` 单值 + `statuses` List。

**原因**：
- 旧调用方传 `purpose=test` 仍然生效（List 为 null/空时回退到单值）
- 降低联调成本，无需一刀切迁移
- 与同仓 filter/sort 变更（#56）的扩展模式保持一致

### 决策 3：Mapper 用 `<choose>/<when>/<otherwise>` 而非 SQL 拼接

**选择**：使用 MyBatis `<choose>` 标签实现"先 List 后 String"的两段式判断。

**原因**：
- MyBatis `<choose>` 语义清晰（类似 Java 的 if-else if-else），避免多个独立 `<if>` 都命中的歧义
- 不需要 Service 层额外的合并逻辑，逻辑下沉到 SQL 层
- 性能等价（每次只走一个分支）

### 决策 4：`count` 查询的 list 字段在 count 端复用同一 Entity 传参

**选择**：`count(RepoInfoEntity repoInfo)` 方法的 XML 直接读 `repoInfo.purposes` 等字段（不强制要求 `@Param("info")`）。

**原因**：
- `count` 当前已用 `purpose` / `visibility` 等单值字段；继续用 List 字段语义一致
- MyBatis 对单 Entity 参数的 `info.purpose` 访问自然支持（也兼容旧的 bare `purpose` 写法，但新代码统一加 `info.` 前缀以保持一致）
- `queryRepoInfoByLimit` / `queryRepoInfo` 已有 `@Param("info")`，用 `info.purposes`；count 没有，继续 bare 用 `purposes`，与既有约定一致

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `QueryRepoDTO.java` | 修改 | 新增 `purposes` / `visibilities` / `repoLanguages` / `statuses` List 字段 + `status` 单值字段 |
| `RepoInfoEntity.java` | 修改 | 新增 4 个 `@TableField(exist=false)` List 字段 |
| `RepoServiceImpl.java` | 修改 | `queryRepoInfo` 透传 List + 新增 `status` 字段 |
| `RepoInfoMapper.xml` | 修改 | `queryRepoInfoByLimit` / `queryRepoInfo` / `count` 三处 SQL 的 4 个过滤条件改 `<choose>/<when>/<otherwise>` |
| `doc/api/repo-management.md` | 修改 | 补充多选参数说明与示例 |
| `RepoServiceImplTest.java` | 新增/修改 | 覆盖：List 命中、List 空回退单值、单值命中、status 过滤 |

## Mapper XML 改动模式

以 `purpose` 为例（`queryRepoInfoByLimit`）：

```xml
<choose>
  <when test="info.purposes != null and info.purposes.size > 0">
    and purpose IN
    <foreach collection="info.purposes" item="p" open="(" close=")" separator=",">
      #{p}
    </foreach>
  </when>
  <when test="info.purpose != null and info.purpose != ''">
    and purpose = #{info.purpose}
  </when>
</choose>
```

`count` SQL 同样模式（属性 bare，无 `info.` 前缀），4 个字段统一处理。

## 接口示例

```http
POST /project-repo/query-repo
{
  "projectId": 1,
  "pageNum": 1,
  "pageSize": 20,
  "purposes": ["test", "formal"],
  "visibilities": ["private", "internal"],
  "repoLanguages": ["java", "go"],
  "statuses": ["normal", "suspend"]
}
```

兼容调用（旧字段仍生效）：

```http
POST /project-repo/query-repo
{
  "projectId": 1,
  "pageNum": 1,
  "pageSize": 20,
  "purpose": "test",
  "visibility": "private",
  "repoLanguage": "java"
}
```

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| `IN (...)` SQL 注入 | List 内元素经 MyBatis `#{}` 占位符预编译，等价于单值精确匹配；无 `${}` 拼接 |
| 旧的单值字段被无意覆盖 | 字段独立保留，List 与 String 互不干扰；`<choose>` 保证二选一 |
| count 与 list 查询条件不一致 | 三个 SQL 同步改用同一 `<choose>` 模式 |
| 性能：List 长度无上限 | 当前场景 List 通常 < 10 项（用途/可见性/语言/状态枚举数有限），可接受 |

## 跨仓影响

无。仅影响 `openlibing-coderepo` 仓的查询接口，无跨仓接口/契约变化。
