## 1. Service 层查询路径调整



- [x] 1.1 抽取平台判断（如 `isFuzzySearchPlatform(accountPlatform)`）：仅 `gitcode` / `gitee` / `openubmc` 返回 true；`uniportal` 返回 false

- [x] 1.2 **uniportal 分支保持原逻辑**：仍调用 `commonService.getUser()`；`errorMsg` 非空时 `failureMessage`；有 `userId` 时走 `queryProjectUserByUserIdLimit`

- [x] 1.3 **三方平台分支**：当 `accountLogin` 与 `accountPlatform` 均非空且为模糊平台时，跳过 `getUser` 路由，设置 `QueryProjectUserEntity.accountLogin` / `accountPlatform` 后走 UNION 模糊查询（`countProjectUser` + `queryProjectUserByLimit`）

- [x] 1.4 无账号筛选时保持原三分流/全量 UNION 行为不变



## 2. Mapper SQL 模糊条件（仅三方平台）



- [x] 2.1 在 `projectUserQueryWithConditions`：当 `info.accountPlatform` 为 gitcode/gitee/openubmc 时，将 `account_login =` 改为 `account_login LIKE CONCAT('%', #{info.accountLogin}, '%')`；uniportal 或无账号条件时保持 `=`

- [x] 2.2 在 `userQueryWithConditions` 按 `info.accountPlatform` 增加 gitcode/gitee/openubmc 分支模糊条件（对应 binding 表 `account_login LIKE ...`）；**不增加 uniportal 模糊条件**

- [x] 2.3 确认 `countProjectUser` 的 UNION count 与 `queryProjectUserByLimit` 使用相同 WHERE 片段；`countProjectUserByAccount` / `queryProjectUserByAccountLimit` 若仍被三方模糊路径使用则同步 LIKE，否则仅 uniportal/遗留路径保持精确

- [x] 2.4 确认排序 tie-breaker 与 `sortColumn`/`sortOrder` 行为不变



## 3. 单元测试



- [x] 3.1 新增用例：gitee 部分 `accountLogin` 走 UNION 模糊路径（mock `queryProjectUserByLimit`）

- [x] 3.2 新增用例：gitcode 部分 `accountLogin` 不调用 `getUser` 窄路径

- [x] 3.3 **回归 uniportal**：精确工号成功仍走 `queryProjectUserByUserIdLimit`（沿用/保留 `testQueryProjectUserSuccessWithUserId`）

- [x] 3.4 **回归 uniportal**：`getUser` 返回 `errorMsg` 仍 `failureMessage`（沿用/保留 `testQueryProjectUserWithUniportalErrorMsg`）

- [x] 3.5 新增用例：空 `accountLogin` 仍走全量列表逻辑

- [x] 3.6 新增用例：三方模糊筛选 + `sortColumn`/`sortOrder` 正确传入 `QueryProjectUserEntity`



## 4. 验证与收尾



- [x] 4.1 本地执行 `ProjectUserServiceImplTest` 相关用例通过

- [x] 4.2 自检：uniportal 代码路径无 LIKE 模糊；`queryCommitterInfo` 等精确接口未受影响

- [x] 4.3 记录与前端对齐说明：三方平台失焦/回车可模糊筛选；uniportal 仍需完整工号

