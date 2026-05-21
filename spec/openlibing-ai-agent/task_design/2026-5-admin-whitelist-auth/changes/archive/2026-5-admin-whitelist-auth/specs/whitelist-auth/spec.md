# Spec: 白名单访问控制

**Change ID**: 2026-5-admin-whitelist-auth
**Feature**: 管理后台白名单访问改造

## Scenario 1: 白名单用户访问管理接口

**GIVEN** Apollo 配置 `admin_whitelist` 包含 `zhangsan`，`admin_user_header` 为 `X-User-Name`

**WHEN** 携带请求头 `X-User-Name: zhangsan` 调用 `POST /api/admin/skills`

**THEN** 请求正常处理，返回 200 和创建的 Skill 数据

## Scenario 2: 非白名单用户访问管理接口

**GIVEN** Apollo 配置 `admin_whitelist` 包含 `zhangsan`，`admin_user_header` 为 `X-User-Name`

**WHEN** 携带请求头 `X-User-Name: lisi` 调用 `POST /api/admin/skills`

**THEN** 返回 403，错误信息为"无管理后台访问权限"

## Scenario 3: 未携带用户标识头访问管理接口

**GIVEN** `admin_user_header` 为 `X-User-Name`

**WHEN** 不携带 `X-User-Name` 请求头调用 `GET /api/admin/projects`

**THEN** 返回 403，错误信息为"无管理后台访问权限"

## Scenario 4: 前端权限检查——白名单用户

**GIVEN** Apollo 配置 `admin_whitelist` 包含 `zhangsan`

**WHEN** 携带请求头 `X-User-Name: zhangsan` 调用 `GET /api/admin/check-access`

**THEN** 返回 200，`{"ok": true, "has_access": true, "username": "zhangsan"}`

## Scenario 5: 前端权限检查——非白名单用户

**GIVEN** Apollo 配置 `admin_whitelist` 包含 `zhangsan`

**WHEN** 携带请求头 `X-User-Name: lisi` 调用 `GET /api/admin/check-access`

**THEN** 返回 200，`{"ok": true, "has_access": false, "username": "lisi"}`

## Scenario 6: 登录接口已删除

**GIVEN** 白名单访问控制已生效

**WHEN** 调用 `POST /api/admin/login`

**THEN** 返回 404，该接口已不存在

## Scenario 7: auth.py 已删除

**GIVEN** 白名单访问控制已生效

**WHEN** 检查 `app/auth.py` 文件

**THEN** 该文件不存在，已被删除

## Scenario 8: 白名单为空时拒绝所有访问

**GIVEN** Apollo 配置 `admin_whitelist` 为空字符串

**WHEN** 携带任意 `X-User-Name` 请求头调用管理接口

**THEN** 返回 403，错误信息为"无管理后台访问权限"

## Scenario 9: 公开接口不受影响

**GIVEN** 白名单访问控制已生效

**WHEN** 调用 `/api/skills/*` 等公开接口

**THEN** 行为不变，正常返回数据，不需要 `X-User-Name` 头

## Scenario 10: 白名单大小写不敏感匹配

**GIVEN** Apollo 配置 `admin_whitelist` 包含 `ZhangSan`

**WHEN** 携带请求头 `X-User-Name: zhangsan` 调用管理接口

**THEN** 请求正常处理，返回 200（白名单匹配忽略大小写）
