# Tasks: 管理后台白名单访问改造

**Change ID**: 2026-5-admin-whitelist-auth

## Task 1: 新增白名单校验模块

创建 `app/whitelist.py`，实现 `require_whitelisted` FastAPI 依赖项：
- 从请求头读取用户标识（header 名称由 `settings.admin_user_header` 配置）
- 与 `settings.admin_whitelist`（逗号分隔列表，大小写不敏感）比对
- 白名单为空或用户不在白名单中时返回 403
- 白名单用户通过校验，返回用户名

## Task 2: 修改配置模块

修改 `app/config.py`：
- 移除 `admin_username`、`admin_password`、`admin_secret_key`、`admin_token_expire_hours`
- 新增 `admin_whitelist: str`（默认空字符串）和 `admin_user_header: str`（默认 `X-User-Name`）
- 从 Apollo 读取 `admin_whitelist` 和 `admin_user_header`
- 移除 Apollo 中 `admin_password`、`admin_secret_key` 的解密逻辑

## Task 3: 修改管理端路由

修改 `app/routers/admin.py`：
- 移除 `/login` 接口
- 移除 `auth` 相关导入，替换为 `whitelist` 模块导入
- 所有 `dependencies=[Depends(require_admin)]` 替换为 `dependencies=[Depends(require_whitelisted)]`
- 新增 `GET /api/admin/check-access` 接口，返回当前用户是否有白名单权限

## Task 4: 修改导入路由

修改 `app/routers/import_.py`：
- `require_admin` 替换为 `require_whitelisted`

## Task 5: 清理旧鉴权代码和 Schema

- 删除 `app/auth.py`
- 从 `app/schemas/skill.py` 中移除 `AdminLoginRequest` 和 `AdminLoginResponse`

## Task 6: 更新测试

- 修改 `tests/conftest.py`：移除 `admin_token`、`admin_headers` fixture；新增 `whitelist_headers` fixture
- 修改 `tests/test_admin.py`：移除 `TestAdminLogin` 类；新增白名单校验测试；更新所有使用 `admin_headers` 的测试用 `whitelist_headers` 替换
