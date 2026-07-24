# migrate-passwd-expire — 实现任务

## 进度: 0/5 complete

### hidevlab-transport-service（新增）

- [ ] Task 1: 新增 `service/passwd_expire.py`，实现 `set_passwd_expire(ssh, os_name)`
  - 使用 `tools.ssh.Ssh` 与 `get_ssh_connection`
  - ubuntu 走 `sudo_exec_command`（3-tuple 返回），其他系统走 `exec_command`
  - 优先用 `exit_code` 判断成功，stderr 仅作错误信息
  - 日志脱敏：IP 走 `security.mask_ip_partial`，用户名走 `security.mask_chars`

- [ ] Task 2: 在 `transport.py` 新增 `POST /passwd/expire` 路由
  - 首行 `auth_filter.auth_filter(headers)` 鉴权，失败返回 401
  - 入参解析：`host_ip / host_port / user_name / user_pwd / os_name`
  - 参数校验：`host_ip / os_name / user_name / user_pwd` 缺一返回 500 + "invalid parameters"
  - 调用 `set_passwd_expire`，按 `(flag, msg)` 返回 `{"code": 200/500, "msg": "...", "data": ""}`
  - import `set_passwd_expire` 与 `Ssh`

### hidevlab-infra-manager-service（删除）

- [ ] Task 3: 删除 `hidevlab_blue_service.py` 中的 `/passwd/expire` 路由（L165-191）
  - 同步删除 `from service.config_network import ... set_passwd_expire` 中的引用

- [ ] Task 4: 删除 `service/config_network.py` 中的 `set_passwd_expire` 函数（L385-422）
  - 确认无其他引用后再删

### 验证

- [ ] Task 5: 验证
  - transport-service 本地 `python -c "import transport"` 可正常加载（无语法错误）
  - infra-manager 本地 `python -c "import hidevlab_blue_service"` 可正常加载（无残留引用）
  - grep 两仓均无 `set_passwd_expire` 残留（infra-manager 侧）

## 验证方式

- 静态验证：import 加载 + grep 残留检查
- 动态验证（用户自测）：实际调接口，验证 ubuntu/centos/openeuler 三种系统下 `chage -d 0` 生效，下次登录强制改密
