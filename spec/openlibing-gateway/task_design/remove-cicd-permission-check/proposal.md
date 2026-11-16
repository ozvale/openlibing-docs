# remove-cicd-permission-check

## 需求背景

`/openlibing-cicd/` 权限校验体系下线，网关侧为其服务的纵向权限过滤器及配套特殊路径处理需要一并清理，避免死代码残留和误导性过滤链文档。

## 需求范围

- 删除 `PermissionCheckFilter`（仅服务 `/openlibing-cicd/` 路径的纵向权限校验）及其测试。
- 删除 `AuthFilter.publicInterface` 中 cicd 路径 projectId 归一化（`{projectId}` 替换）特殊分支，无认证白名单回归纯路径+HTTP 方法精准匹配。
- 删除仅由该过滤器调用的 `UserRoleMapper.hasPermission`（接口方法 + XML SQL + mapper 用例）。
- 同步更新 `GrayReleaseFilter` 顺序注释、`AGENTS.md` / `README.md` 过滤链文档。

## 验收标准

- [x] 仓库内不再存在 `PermissionCheckFilter` 及 `/openlibing-cicd/` 生产代码特殊处理。
- [x] `mvn clean test-compile` 通过。
- [x] AuthFilterTest / HealthcheckFilterChainTest / UserRoleMapperTest / OperationLogHeaderRelayFilterTest 共 110 个用例全部通过。
- [x] pre-commit 全部门禁（Spotless/CheckStyle/SpotBugs/PMD/Gitleaks）通过。

## 影响与风险

- 行为变化：`/openlibing-cicd/project/{id}` 形式的动态路径不再被归一化后匹配无认证白名单；如线上 DB 白名单仍配置 cicd 路径，需运维确认是否残留（白名单本身为精准匹配，含 `{projectId}` 占位符的存量配置将不再命中真实请求）。
- `user_role_info` 等表数据不动，仅移除读取链路。
