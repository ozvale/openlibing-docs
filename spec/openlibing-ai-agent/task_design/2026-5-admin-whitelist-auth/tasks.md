# 管理后台鉴权改为用户 ID 白名单访问 — 实现任务

## 进度: 0/7 complete

- [ ] Task 1: 重写 `app/auth.py`，移除 token 逻辑，新增 `require_whitelist_user` 依赖项
- [ ] Task 2: 更新 `app/config.py`，新增 `admin_whitelist` 配置，移除旧鉴权配置
- [ ] Task 3: 更新 `app/routers/admin.py`，删除 login/me 接口，替换鉴权依赖
- [ ] Task 4: 更新 `app/routers/import_.py`，替换鉴权依赖
- [ ] Task 5: 清理 `app/schemas/skill.py`，删除 `AdminLoginRequest`、`AdminLoginResponse`
- [ ] Task 6: 更新 `tests/conftest.py` 和 `tests/test_admin.py`
- [ ] Task 7: 运行全量测试验证
