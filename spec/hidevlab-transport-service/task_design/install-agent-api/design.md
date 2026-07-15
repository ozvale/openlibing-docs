# install-agent-api — 技术设计

## 方案概述

在 `service/clab_agent.py` 新增 `install_agent` 处理函数（核心逻辑 TODO 占位），在 `transport.py` 新增 `POST /install/agent` 路由，复用现有鉴权与异常处理机制。接口模式参考 `/VM/obs/set`（SSH 操作类同步路由）。

## 架构决策

### 决策1：采用同步模式而非异步任务模式

**原因**：监控 Agent 安装是单次 SSH 操作，不像 docker 创建那样涉及多阶段编排（pull/create/start/wait_port/git_clone）。同步模式更简单，与 `/VM/obs/set` 一致。

**权衡**：若后续安装流程变复杂（多步骤、需回调上游），可重构为异步模式 + `sign_request` 回调。

### 决策2：鉴权在路由内单独处理，不依赖全局 before_request

**原因**：transport-service 的 `before_request` 仅设置请求上下文（`set_request_context`），不鉴权。所有业务路由（`/agent/*`、`/VM/*`、`/software/*`）均在路由内单独调用 `auth_filter.auth_filter(headers)`。新增路由保持一致。

### 决策3：参数名用 `host_ip` 而非 `ip`

**原因**：transport-service 有两种参数命名：
- Agent 转发类路由（`/agent/*`、`/VM/agent/delete`）用 `ip`
- SSH 操作类路由（`/VM/obs/set`）用 `host_ip`、`user_name`、`user_pwd`、`host_port`

`/install/agent` 属于 SSH 操作类，采用 `host_ip` 命名与 `/VM/obs/set` 一致。

### 决策4：核心安装逻辑以 TODO 占位，不引入半成品实现

**原因**：本次需求明确要求仅搭建接口框架。半成品实现反而增加风险（未经验证的安装步骤可能破坏目标主机）。TODO 占位 + 完整的参数校验/异常处理框架，便于后续迭代填充。

### 决策5：新增 `service/clab_agent.py` 而非复用 `pre_install.py`

**原因**：`pre_install.py` 的 `check_software_status` 只做日志解析判定，不涉及 SSH 操作。监控 Agent 安装需要 SSH 连接目标主机，逻辑更接近 `service/obs.py::set_obs`。新建独立模块避免职责混淆。

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `service/clab_agent.py` | 新增模块 | `install_agent(ssh, os_name)` — TODO 占位，SSH 连接 + 异常兜底 |
| `transport.py` | 新增 import | `from service.clab_agent import install_agent` |
| `transport.py` | 新增路由 | `POST /install/agent` — 鉴权 + 参数解析 + 校验 + 调用 `install_agent` + dict 响应 |

## 接口契约

### POST /install/agent

请求头：`Authorization: <token>`

请求体（json，沿用 `ast.literal_eval` 解析）：
```
{
  "host_ip": "10.x.x.x",
  "host_port": "22",
  "user_name": "root",
  "user_pwd": "***",
  "os_name": "ubuntu" | "openEuler" | ...
}
```

响应（dict，与 `/VM/obs/set` 一致）：
- 成功：`{"code": 200, "msg": "install agent in <ip> successfully", "data": ""}`
- 参数错误：`{"code": 500, "msg": "invalid parameters", "data": ""}`
- 业务失败：`{"code": 500, "msg": "<原因>", "data": ""}`
- 鉴权失败：`return_post` 返回 401

## 实现参考

- 路由模式参考：`transport.py::set_vm_obs`（`/VM/obs/set`）
- 业务函数模式参考：`service/obs.py::set_obs`
- SSH 工具：`tools/ssh.py::Ssh`（属性 `ip`/`port`/`username`/`password`）+ `get_ssh_connection`

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| `/install/agent` 当前不执行真实安装，上游误以为已安装 | TODO 占位 + 返回成功但 msg 明确；后续迭代填充真实逻辑时改返回语义 |
| SSH 连接失败导致阻塞 | `get_ssh_connection` 已有 3 次重试 + 30s 间隔；`install_agent` 内 try/except 兜底 |
| 目标主机凭证泄露 | 凭证从请求体获取走 `Ssh` 封装；日志不打印密码（`Ssh` 构造时不记录密码） |

## 跨仓影响

无。本次仅改 `hidevlab-transport-service` 业务仓 + `openlibing-docs` spec 归档。
