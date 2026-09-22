## Context

**前端（已就绪，无需改动）**

- 页面：`openlibing-web/apps/web-openlibing/src/views/Project/projectUserManage.vue`
- 组件：`ContactInformation.vue` — 失焦/回车 `emit('getFormInfor')` → `getCommunityUserList()`
- API：`POST /gateway/openlibing-framework/project/user/query-project-user`（`getCommunityUser`）
- 请求体字段不变：`accountLogin`、`accountPlatform`、`projectId`、`userRole`、`pageNum`、`pageSize`、`sortColumn`、`sortOrder`

**后端（待改）**

- Controller：`ProjectUserController.queryProjectUser`
- Service：`ProjectUserServiceImpl.queryProjectUser` → 私有 `queryProjectUser(openlibingUserId, ...)`
- 当前分流逻辑：
  1. `commonService.getUser(userDTO)` 精确 `threePartyUserInfoMapper.queryByLogin` → 有 `userId` 走 `queryProjectUserByUserIdLimit`
  2. 无 `userId` 且有 `accountLogin`+`accountPlatform` → `queryProjectUserByAccountLimit`（仅查 `project_user_role_info`，`account_login = ?`）
  3. 均无 → `queryProjectUserByLimit`（UNION 全量，无账号过滤）
- uniportal：`getUser` 失败时直接 `return DataResult.failureMessage(errorMsg)` — **本 change 保持不变**
- SQL 精确匹配位置：`ProjectUserRoleInfoMapper.xml` 中 `projectUserQueryWithConditions` 与 `countProjectUserByAccount` 的 `account_login = #{info.accountLogin}`

**参考模糊模式**

- `ProjectInfoMapper.xml`：`project_name like concat('%', #{projectName}, '%')`（`get-project-by-name`）

**约束**

- 不新增联想/suggest 接口
- 不修改 `UserDTO` 字段
- 响应结构不变（`{ total, data: [...] }`）
- 排序能力（`sortColumn`/`sortOrder`）保持与已归档 change `query-project-user-sort-alignment` 一致
- **uniportal 账号筛选逻辑与现网完全一致，不引入模糊匹配**

## Goals / Non-Goals

**Goals:**

- 当 `accountPlatform` 为 **gitcode / gitee / openubmc** 且携带非空 `accountLogin` 时，返回账号字段**包含**该关键字的项目成员（分页列表）
- 同时覆盖两类成员：`user_role_info`（已关联 openLiBing，按平台 binding 表 login 匹配）与 `project_user_role_info`（未登录 openLiBing 的三方账号，`account_login` 匹配）
- `accountPlatform` 仍为精确匹配（筛选指定平台）
- **uniportal 保持原逻辑**：`getUser` 精确解析 → userId 窄查询或 `failureMessage`
- 空关键字、无账号筛选时行为与现网一致（全量列表）
- 单元测试覆盖三方平台模糊路径；uniportal 回归现有行为

**Non-Goals:**

- 不新增 suggest/autocomplete 接口
- 不修改前端 `ContactInformation.vue` 或 `projectUserManage.vue`
- 不修改 `queryCommitterInfo` 等精确查人接口
- **不对 uniportal 做模糊匹配或放宽 getUser 失败逻辑**
- 不对 `accountName`/`userName` 做跨字段 OR 模糊（仅按各平台 login 字段 + `project_user_role_info.account_login`）
- 不做性能优化（如全文索引、最小关键字长度限制）——可作为后续迭代

## Decisions

### D1: 按平台分支——uniportal 走原逻辑，三方平台走模糊

**选择**: `queryProjectUser` 入口按 `accountPlatform` 分支：

| 平台 | 行为 |
|------|------|
| `uniportal` | **不变**：调用 `commonService.getUser()` → 有 `userId` 走 `queryProjectUserByUserIdLimit`；`errorMsg` 非空则 `failureMessage` |
| `gitcode` / `gitee` / `openubmc` | **新逻辑**：跳过 `getUser` 路由；将模糊条件写入 `QueryProjectUserEntity`，走 UNION 模糊查询 |

**理由**: 产品明确要求 uniportal 保留精确工号语义；模糊需求仅针对三方代码托管平台账号。

**备选**: 全平台统一模糊 — 拒绝，与产品约束冲突。

### D2: 三方平台账号过滤走 UNION 双表 + 平台列映射

**选择**: 当 `accountPlatform` 为 gitcode/gitee/openubmc 且 `accountLogin` 非空时，在 UNION 查询两段 SQL 中加模糊条件：

| 数据源 | 平台 | 模糊列 |
|--------|------|--------|
| `userQueryWithConditions` | gitcode | `gitcode.account_login LIKE ...` |
| | gitee | `gitee.account_login LIKE ...` |
| | openubmc | `openubmc.account_login LIKE ...` |
| `projectUserQueryWithConditions` | 与 `accountPlatform` 一致 | `account_login LIKE ...` AND `account_platform = ?` |

**不含 uniportal 行**——uniportal 不进入此 UNION 模糊路径。

LIKE 写法：

```sql
AND <column> LIKE CONCAT('%', #{info.accountLogin}, '%')
```

### D3: uniportal 保持 getUser 硬失败（不变）

**选择**: 保留现有逻辑：

```java
if (StringUtils.isNotBlank(errorMsg) && PLATFORM_UNIPORTAL.equalsIgnoreCase(...)) {
    return DataResult.failureMessage(errorMsg);
}
```

**理由**: 用户明确要求 uniportal 保留原逻辑；部分工号输入仍应报错而非返回模糊列表。

### D4: 三方平台废弃 ByUserId / ByAccount 窄路径（仅账号筛选场景）

**选择**: 当 `accountPlatform` 为 gitcode/gitee/openubmc 且 `accountLogin` 有值时，统一使用带模糊条件的 UNION（`queryProjectUserByLimit` / `countProjectUser`），不再因 `getUser` 命中而走单人 userId 路径。

**理由**: 窄路径无法模糊且会漏掉 `user_role_info` 中符合条件的成员。

**uniportal 例外**: 仍使用 `queryProjectUserByUserIdLimit`（精确 userId）。

### D5: 精确输入仍兼容（三方平台）

完整 `accountLogin` 作为 LIKE 参数时，`LIKE '%fullLogin%'` 仍能命中；可能多命中包含关系的更长 login，属可接受 trade-off。

### D6: 特殊字符与 SQL 注入

使用 MyBatis `#{}` 参数绑定（非 `${}`），与 `ProjectInfoMapper` 一致。

## Risks / Trade-offs

- **[Risk] LIKE 前缀通配导致索引失效** → 接受；仅影响三方平台筛选场景
- **[Risk] 子串匹配误命中** → 符合模糊查询预期；uniportal 不受影响
- **[Risk] 平台分支增加 Service 复杂度** → 通过 `isFuzzySearchPlatform(accountPlatform)` 小函数集中判断
- **[Risk] 行为变更** — 三方平台精确唯一结果可能变为多条 → 对列表筛选为预期行为

## Migration Plan

1. 部署 backend 新版本即可；前端无协同发布要求
2. 回滚：还原 `ProjectUserServiceImpl` 分流与 Mapper XML
3. 验证：
   - gitcode/gitee 部分账号 → 多条或空
   - uniportal 完整工号 → 与原行为一致
   - uniportal 无效/部分工号 → 仍返回 `failureMessage`（与原行为一致）
   - 清空账号 → 全量列表

## Open Questions

- `accountPlatform` 为空但 `accountLogin` 有值时是否支持？**维持现网：两者均非空才启用账号过滤**。

**已关闭**: uniportal 是否模糊？→ **否，保留原逻辑**。
