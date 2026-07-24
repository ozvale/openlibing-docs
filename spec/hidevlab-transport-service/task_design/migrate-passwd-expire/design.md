# migrate-passwd-expire — 技术设计

## 方案概述

将 `/passwd/expire` 接口从 `hidevlab-infra-manager-service` 迁移到 `hidevlab-transport-service`，保持入参/响应契约不变。transport-service 跑在目标 OS 本地，可直连本机 IP，规避 infra-manager 部署机跨网段不通的问题。

## 架构决策

### 1. 接口路径不变：`/passwd/expire`

**决策**：transport-service 新接口路径保持 `/passwd/expire`，不挂到 `/VM/*` 前缀下。

**原因**：该接口同时服务虚拟机和裸金属，挂 `/VM/*` 会让裸金属场景语义混乱。原路径不变也方便调用方平滑迁移（仅切 host:port）。

### 2. 入参/响应契约完全不变

**决策**：入参 `host_ip / host_port / user_name / user_pwd / os_name`，响应沿用 `return_post` 的 `{"code","msg","data"}` 结构。

**原因**：调用方零改动即可切换。

### 3. service 层合并到 `service/clab_agent.py`

**决策**：`set_passwd_expire(ssh, os_name)` 函数追加到 `service/clab_agent.py` 末尾，不单独建文件。

**原因**：用户偏好精简文件数量。`clab_agent.py` 已 import 了 `Ssh / get_ssh_connection / sudo_exec_command`，新增函数直接复用，只需补 `security` 一个 import。

### 4. SSH 客户端用 transport-service 的 `Ssh` 类

**决策**：用 `tools.ssh.Ssh`（transport-service 仓的类），不复用 infra-manager 的 `SshConnection`。

**关键差异**：
- transport-service 的 `sudo_exec_command` 返回 **3-tuple `(stdout, stderr, exit_code)`**
- infra-manager 的 `sudo_exec_command` 返回 **2-tuple `(stdout, stderr)`**

新实现必须按 3-tuple 处理，并优先用 `exit_code` 判断成功，避免 stderr 有内容但实际成功的误判（chage 在某些系统上会把 warn 输出到 stderr）。

### 5. ubuntu 走 `sudo -S`，其他系统直接执行

**决策**：保持原 chage 执行逻辑：
- ubuntu：`sudo -S /usr/bin/chage -d 0 <user>`，密码通过 stdin 传入（transport-service 的 `sudo_exec_command` 已这样实现）
- 其他系统（centos/openeuler）：`exec_command('/usr/bin/chage -d 0 <user>')`，直接执行

**原因**：ubuntu 默认账户无 root 权限需 sudo 提权；centos/openeuler 默认账户通常可直接执行 chage。

### 6. infra-manager 侧彻底删除

**决策**：移除 `/passwd/expire` 路由、`set_passwd_expire` 函数、`from service.config_network import ... set_passwd_expire` 的 import。

**原因**：全仓仅一处引用，无其他调用方。保留死代码不符合"避免无关重构"反向原则（已确认要删）。

## 涉及文件

### hidevlab-transport-service（新增）

| 文件 | 操作 | 说明 |
|------|------|------|
| `service/clab_agent.py` | 修改 | 末尾追加 `set_passwd_expire(ssh, os_name)`，补 `security` import |
| `transport.py` | 修改 | 新增 `/passwd/expire` 路由 + import `set_passwd_expire` from `clab_agent` |

### hidevlab-infra-manager-service（删除）

| 文件 | 操作 | 说明 |
|------|------|------|
| `hidevlab_blue_service.py` | 修改 | 删除 `/passwd/expire` 路由 + import 中的 `set_passwd_expire` |
| `service/config_network.py` | 修改 | 删除 `set_passwd_expire` 函数 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 调用方未及时切换 host:port，infra-manager 升级后接口消失 | 部署顺序：先发 transport-service（接口可用）→ 调用方切换 → 再发 infra-manager（移除旧接口） |
| transport-service 的 `sudo_exec_command` 返回 3-tuple，与 infra 不同，易写出错 | design.md 已明确，编码时按 3-tuple 解包 |
| ubuntu chage 失败时 stderr 可能为空，需靠 exit_code 判断 | 新实现优先用 `exit_code != 0` 判断失败，stderr 仅作错误信息回显 |
| SSH 重试默认 3 次 × (130s TCP 超时 + 30s delay) ≈ 8min，可能阻塞调用方 | 沿用既有行为，本次不调整；后续如需优化另起 Issue |

## 跨仓影响

- `hidevlab-transport-service`：新增对外接口 `POST /passwd/expire`
- `hidevlab-infra-manager-service`：移除对外接口 `POST /passwd/expire`
- 调用方：所有上游服务（需自查）切换 host:port

## 关联

- 业务 Issue: https://gitcode.com/openlibing/hidevlab-transport-service/issues/61
- 源实现参考: https://gitcode.com/openlibing/hidevlab-infra-manager-service/blob/master/hidevlab_blue_service.py#L165-L191
