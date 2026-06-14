## Context

**前端（已就绪）**

- 页面：`openlibing-web/apps/web-openlibing/src/views/Project/projectUserManage.vue`
- API：`POST /gateway/openlibing-framework/project/user/query-project-user`（`getCommunityUser`）
- 表格仅「创建时间」列启用 `sortable="custom"`，默认 UI 为 `createTime` 降序
- 排序变更时调用 `handleCustomSort`，将 Element Plus 的 `{ prop, order }` 写入 `sortParams` 并重新请求：

```javascript
sortParams: { sortColumn: '', sortOrder: '' }

handleCustomSort({ prop, order }) {
  this.sortParams.sortColumn = prop;   // 点击创建时间 → "createTime"
  this.sortParams.sortOrder = order; // "ascending" | "descending" | null
  this.getCommunityUserList();
}

// 请求体片段
{
  pageNum, pageSize, userRole, projectId, accountPlatform, accountLogin,
  sortColumn: this.sortParams.sortColumn,
  sortOrder: this.sortParams.sortOrder,
}
```

**后端（待改）**

- Controller：`ProjectUserController.queryProjectUser`
- DTO：`UserDTO` 无 sort 字段
- 查询实体：`QueryProjectUserEntity` 无 sort 字段
- Mapper：`ProjectUserRoleInfoMapper.xml` 三处查询硬编码 `ORDER BY create_time DESC`

**约束**

- 用户无法本地联调，design 必须给出完整前后端契约表与边界行为
- 参考同平台 `ObsInfoServiceImpl` 的白名单 sort 映射模式（`openlibing-platform-release`）

## Goals / Non-Goals

**Goals:**

- 后端接收并应用 `sortColumn` / `sortOrder`，使列头点击排序与首屏默认降序行为与前端一致
- 仅允许 `createTime` → `create_time` 白名单映射，防止 SQL 注入
- 三条查询路径（UNION 全量 / 按 userId / 按三方账号）排序行为一致
- 单元测试覆盖映射与默认值，替代联调验证

**Non-Goals:**

- 不新增其他列排序（前端仅 `createTime` 可排序）
- 不修改 `createTime` 响应格式（已为 `yyyy-MM-dd HH:mm:ss` 字符串）
- 不修改前端代码或初始化 `sortParams` 默认值（首屏空 sort 由后端默认 DESC 兜底）

## Decisions

### D1: sort 字段放在 UserDTO，映射后写入 QueryProjectUserEntity

**选择**: `UserDTO` 增加 `sortColumn`、`sortOrder`（optional）；Service 层映射为 `QueryProjectUserEntity.sortDbColumn`、`sortDirection` 供 MyBatis 使用。

**理由**: 与前端 body 字段名一致，Controller 无需改动；查询实体仅承载已校验的数据库列名，避免 XML 直接引用用户输入。

**备选**: 仅在 `UserDTO` 存 sort 并在 XML 用 `${}` 拼接 — 拒绝，SQL 注入风险高。

### D2: 白名单映射与默认行为

| 前端 `sortColumn` | DB 列 | 说明 |
|-------------------|-------|------|
| `createTime` | `create_time` | 唯一合法值 |
| `null` / `""` / 其他 | `create_time` | 回退默认列 |

| 前端 `sortOrder` | SQL |
|------------------|-----|
| `ascending` | `ASC` |
| `descending` | `DESC` |
| `null` / `""` | `DESC` | 对齐 UI `:default-sort` 与历史硬编码 |

实现参考：

```java
private void applySortParams(UserDTO userDTO, QueryProjectUserEntity query) {
    String dbColumn = "create_time";
    String direction = "DESC";
    if (StringUtils.isNotBlank(userDTO.getSortColumn())) {
        String mapped = mapSortColumn(userDTO.getSortColumn());
        if (mapped != null) {
            dbColumn = mapped;
            direction = mapSortOrder(userDTO.getSortOrder());
        }
    }
    query.setSortDbColumn(dbColumn);
    query.setSortDirection(direction);
}

private String mapSortColumn(String sortColumn) {
    return "createTime".equals(sortColumn) ? "create_time" : null;
}

private String mapSortOrder(String sortOrder) {
    return "ascending".equals(sortOrder) ? "ASC" : "DESC";
}
```

### D3: MyBatis 动态 ORDER BY

三处 `select` 统一使用：

```xml
ORDER BY ${info.sortDbColumn} ${info.sortDirection}, id DESC
```

UNION 全量查询在原有 tie-breaker 基础上保留稳定次序：

```xml
ORDER BY ${info.sortDbColumn} ${info.sortDirection}, id DESC, user_identifier DESC, source_table DESC
```

**理由**: `${}` 仅用于 Service 白名单后的常量；列名与方向均非用户原始输入。

**备选**: `<choose>` 固定 ASC/DESC 分支 — 可行但冗余，白名单后 `${info.sortDirection}` 更简洁。

### D4: 三条查询路径均应用 sort

`queryProjectUserByLimit`、`queryProjectUserByUserIdLimit`、`queryProjectUserByAccountLimit` 均需动态 ORDER BY。

**理由**: Service 根据筛选条件走不同 Mapper 方法，任一路径遗漏都会导致部分筛选场景下排序失效。

### D5: 测试策略（替代联调）

在 `ProjectUserServiceImplTest` 增加：

- sort 参数传入后 `QueryProjectUserEntity` 携带正确 `sortDbColumn`/`sortDirection`（可通过 ArgumentCaptor 或集成 Mapper mock 验证调用）
- 非法 `sortColumn` 回退默认
- `sortOrder` 为 `null` 时默认 `DESC`

可选：Mapper XML 层单独测试排序片段（若项目有 MyBatis 测试惯例）。

## 前后端契约对齐表（联调替代）

| 场景 | 前端请求 sortColumn | 前端请求 sortOrder | 后端 ORDER BY |
|------|---------------------|--------------------|---------------|
| 首屏加载 | `""` | `""` | `create_time DESC` |
| 点击创建时间升序 | `createTime` | `ascending` | `create_time ASC, ...` |
| 点击创建时间降序 | `createTime` | `descending` | `create_time DESC, ...` |
| 取消排序（列头第三次点击） | `createTime` | `null` | `create_time DESC, ...` |
| 恶意/未知列 | `userName` | `ascending` | `create_time DESC, ...`（忽略非法列） |

响应 `createTime` 格式不变：`"yyyy-MM-dd HH:mm:ss"` 字符串，前端展示逻辑无需改动。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| `${}` 动态 SQL 被误用引入注入 | 仅 Service 白名单赋值；Code Review 禁止 XML 直接使用 DTO 原始 sort 字段 |
| UNION 两表 `create_time` 类型不一致导致排序异常 | 现有列均为可比字符串/datetime；实现后 UT 用 mock 数据验证 ASC/DESC |
| 首屏前端未传 sort 与 UI 箭头不一致 | 后端默认 DESC 与历史行为一致；属已知前端小瑕疵，不在本变更范围 |
| 无法 E2E 联调 | 契约表 + 单元测试双重保障；PR 描述附对齐表供 QA 按场景验收 |

## Migration Plan

1. 部署 `openlibing-framework` 新版本（向后兼容：不传 sort 时行为与现网相同）
2. 无需前端发版即可生效（前端已在传参）
3. 回滚： revert 后端 commit；前端无依赖新字段，回滚无影响

## Open Questions

（无 — 前端行为已调研完毕，实现路径明确）
