# remove-cicd-permission-check — 归档

## 关联

- 业务 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/170 （【安全】网关纵向权限校验存在请求方法与动态参数校验盲区，可导致低权限用户越权访问管理接口；修复方式为 `/openlibing-cicd/` 纵向权限校验体系下线）
- 关联 Issue: https://gitcode.com/openlibing/openlibing-gateway/issues/101 （【缺陷】cicd 拦截器拦截了其他模块请求）
- 业务 PR: https://gitcode.com/openlibing/openlibing-gateway/merge_requests/232 （fix(auth): harden token, whitelist and csrf handling on release_20261116，已合入）
- 批次总览: [security-remediation-202611/archive.md](../security-remediation-202611/archive.md)

## 交付历程

- commit `42b44a4b`: 删除 `PermissionCheckFilter` 及其测试、`AuthFilter` cicd 路径 `{projectId}` 归一化特殊分支、仅由该过滤器调用的 `UserRoleMapper.hasPermission`（接口 + XML SQL + mapper 用例）；同步更新 GrayReleaseFilter 顺序注释与 AGENTS.md / README.md 过滤链文档

## 用户自测反馈

- 本轮无新增反馈记录；测试证据见下

## 最终验证

- AuthFilterTest / HealthcheckFilterChainTest / UserRoleMapperTest / OperationLogHeaderRelayFilterTest 共 110 个用例全部通过
- `mvn clean test-compile` 通过，pre-commit 全门禁（Spotless/CheckStyle/SpotBugs/PMD/Gitleaks）通过

## 设计偏差与取舍

- 行为变化：动态路径不再归一化后匹配无认证白名单；含 `{projectId}` 占位符的存量 DB 白名单配置将不再命中真实请求，需运维确认是否残留
- `user_role_info` 等表数据不动，仅移除读取链路
- 无新架构决策，design.md 省略

## 归档日期

2026-11-16
