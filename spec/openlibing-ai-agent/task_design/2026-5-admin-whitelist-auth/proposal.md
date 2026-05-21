# 管理后台鉴权改为用户 ID 白名单访问

## 需求背景

当前管理后台使用"管理员账号密码 + HMAC 签名 token"的登录鉴权方式，前端有独立的登录页面。为简化管理流程，需要将登录逻辑替换为白名单访问形式：前端隐藏管理后台入口，只有白名单上的用户 ID 才能访问管理接口。

## 功能描述

**做什么：**
1. 移除现有登录逻辑（`/api/admin/login` 接口、`verify_credentials`、`create_admin_token`、`verify_admin_token` 等）
2. 新增用户 ID 白名单校验机制：前端请求头携带 `X-User-Id`，后端从 Apollo 配置中心读取白名单列表，校验用户 ID 是否在白名单中
3. 将所有 `dependencies=[Depends(require_admin)]` 替换为 `dependencies=[Depends(require_whitelist_user)]`
4. 更新相关测试

**不做什么：**
- 不改变公开市场接口（`/api/skills/*`、`/api/mcp-servers/*` 等）的访问逻辑
- 不改变数据库结构
- 不实现白名单的动态管理接口（白名单通过 Apollo 配置管理）

## 验收标准

- [ ] `/api/admin/login` 接口已删除，调用返回 404
- [ ] 白名单用户通过 `X-User-Id` 请求头可正常访问所有管理接口
- [ ] 非白名单用户访问管理接口返回 403
- [ ] 无 `X-User-Id` 请求头访问管理接口返回 401
- [ ] 公开市场接口不受影响
- [ ] 白名单配置从 Apollo 读取，支持热更新
- [ ] 相关测试全部通过

## 影响范围

- `app/auth.py`：重写，移除 token 逻辑，新增白名单校验
- `app/config.py`：新增 `admin_whitelist` 配置，移除旧鉴权配置
- `app/routers/admin.py`：删除 login/me 接口，替换鉴权依赖
- `app/routers/import_.py`：替换鉴权依赖
- `app/schemas/skill.py`：删除 `AdminLoginRequest`、`AdminLoginResponse`
- `tests/conftest.py`、`tests/test_admin.py`：更新 fixture 和测试用例
