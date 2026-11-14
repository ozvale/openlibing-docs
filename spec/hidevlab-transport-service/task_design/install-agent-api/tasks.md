# install-agent-api — 实现任务

## 进度: 4/4 complete

- [x] Task 1: 新增 `service/clab_agent.py` 模块，实现 `install_agent(ssh, os_name)` 函数，核心逻辑以 `# TODO: 实现监控Agent自动化安装的具体流程` 占位，含 SSH 连接建立与异常兜底
- [x] Task 2: 在 `transport.py` 新增 `from service.clab_agent import install_agent` import
- [x] Task 3: 在 `transport.py` 新增 `POST /install/agent` 路由，鉴权 + 参数解析 + 非空校验 + 调用 `install_agent` + dict 响应
- [x] Task 4: 本地语法校验 `python -m py_compile transport.py service/clab_agent.py`，确认无语法错误

## 验证方式

- `python -m py_compile` 通过
- 人工 review：路由结构、参数校验、响应格式与现有 `/VM/obs/set` 路由一致
- 鉴权：确认 `/install/agent` 路由内有 `auth_filter.auth_filter` 校验
