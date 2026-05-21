# Proposal: 管理后台白名单访问改造

**Change ID**: 2026-5-admin-whitelist-auth
**目标仓**: openlibing-ai-agent

## 目标

将管理后台的登录鉴权（用户名密码 + HMAC token）替换为白名单访问控制。白名单从 Apollo 配置读取，用户身份从网关注入的请求头中获取。前端通过 `/api/admin/check-access` 接口判断当前用户是否有权限，非白名单用户无法访问任何管理接口。

## 非目标

- 不实现角色/权限点体系，白名单内所有用户权限相同。
- 不实现白名单的动态管理接口（增删改），白名单变更通过 Apollo 配置中心操作。
- 不修改公开市场接口（`/api/skills/*`、`/api/mcp-servers/*` 等）的访问逻辑。

## 影响

### 代码变更

- **删除** `app/auth.py`：移除 `verify_credentials`、`create_admin_token`、`verify_admin_token`、`require_admin`。
- **新增** `app/whitelist.py`：白名单校验逻辑，从请求头读取用户标识，与 Apollo 白名单配置比对。
- **修改** `app/config.py`：移除 `admin_username`、`admin_password`、`admin_secret_key`、`admin_token_expire_hours`；新增 `admin_whitelist`（逗号分隔的用户名列表）和 `admin_user_header`（请求头名称，默认 `X-User-Name`）。
- **修改** `app/routers/admin.py`：移除 `/login` 接口；所有 `dependencies=[Depends(require_admin)]` 替换为 `dependencies=[Depends(require_whitelisted)]`；新增 `/check-access` 接口。
- **修改** `app/routers/import_.py`：`require_admin` 替换为 `require_whitelisted`。
- **修改** `app/schemas/skill.py`：移除 `AdminLoginRequest`、`AdminLoginResponse`。
- **修改** `tests/conftest.py`：移除 `admin_token`、`admin_headers` fixture；新增白名单相关 fixture。
- **修改** `tests/test_admin.py`：移除登录相关测试；新增白名单校验测试。

### 配置变更

- Apollo 命名空间 `openlibing-ai-agent` 新增配置项 `admin_whitelist`（如 `zhangsan,lisi,wangwu`）和 `admin_user_header`（如 `X-User-Name`）。
- Apollo 可移除 `admin_username`、`admin_password`、`admin_secret_key` 配置项。
