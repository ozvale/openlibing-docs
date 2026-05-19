# Spec: Admin Auth Removal

**Change ID**: skill-market-sync
**Feature**: 管理后台接口权限管控模式改造

## Scenario 1: 无 token 访问 admin 接口

**GIVEN** 管理后台接口已移除 `require_admin` 依赖

**WHEN** 不携带任何 Authorization header 调用 `POST /api/admin/skills`

**THEN** 请求正常处理，返回 200 和创建的 Skill 数据

## Scenario 2: 携带 token 访问 admin 接口

**GIVEN** 管理后台接口已移除 `require_admin` 依赖

**WHEN** 携带有效 Authorization header 调用 `POST /api/admin/skills`

**THEN** 请求正常处理，token 被忽略（不校验也不报错）

## Scenario 3: 登录接口已删除

**GIVEN** 管理后台接口已移除 `require_admin` 依赖，`auth.py` 已删除

**WHEN** 调用 `POST /api/admin/login`

**THEN** 返回 404，该接口已不存在

## Scenario 4: auth.py 文件已删除

**GIVEN** 管理后台接口已移除 `require_admin` 依赖

**WHEN** 检查 `app/auth.py` 文件

**THEN** 该文件不存在，已被删除

## Scenario 5: 所有 admin 路由均移除认证

**GIVEN** 管理后台接口已移除 `require_admin` 依赖

**WHEN** 调用任意 `/api/admin/*` 接口（不含 `/api/admin/login`，该接口已删除）

**THEN** 均不需要 token 校验

## Scenario 6: 公开接口不受影响

**GIVEN** 管理后台接口已移除 `require_admin` 依赖

**WHEN** 调用 `/api/skills/*` 等公开接口

**THEN** 行为不变，正常返回数据
