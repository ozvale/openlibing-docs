# remove-cicd-permission-check 实现步骤

- [x] 删除 `PermissionCheckFilter.java`、`PermissionCheckFilterTest.java`
- [x] `AuthFilter` 移除 `CICD_PROJECT_PATTERN`、regex import、`publicInterface` cicd 归一化分支
- [x] 删除 `UserRoleMapper.hasPermission`（接口 + `UserRoleMapper.xml` + `UserRoleMapperTest` 用例）
- [x] `AuthFilterTest` 删除 `testPublicInterface_WithCicdPath` / `testPublicInterface_CicdPathNoMatch`，重命名 `WithNonCicdPath` → `WithNonWhitelistPath`
- [x] `HealthcheckFilterChainTest` 过滤链移除 PermissionCheckFilter（四个 → 三个）
- [x] `GrayReleaseFilter` 顺序注释更新（低于 AuthFilter）
- [x] `AGENTS.md` / `README.md` 过滤链表格与目录树同步
- [x] 编译 + 相关单测（110/110 通过）+ pre-commit 门禁
- [x] commit `fb7bab52`（develop_202611_iter1）

> 无新架构决策，design.md 省略。
