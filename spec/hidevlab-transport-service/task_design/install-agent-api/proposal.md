# install-agent-api

## 需求背景

`hidevlab-transport-service` 是控制面与计算节点/Agent 之间的代理网关，已有 Agent 转发能力（token/采集间隔/删除）。本次新增监控 Agent 的自动化安装接口，通过 SSH 到目标主机执行安装流程，补齐 Agent 生命周期管理的安装环节。

## 功能描述

### 监控 Agent 安装接口

- 新增路由 `POST /install/agent`，触发监控 Agent 自动化安装流程。
- 在 `service/clab_agent.py` 实现处理函数 `install_agent`。
- 核心业务逻辑暂以 `# TODO: 实现监控Agent自动化安装的具体流程` 占位，本次不实现具体安装步骤。
- 接口具备：参数校验（`host_ip`/`host_port`/`user_name`/`user_pwd`/`os_name` 非空）、权限控制（路由内 `auth_filter.auth_filter` 鉴权）、异常处理（`install_agent` 内 try/except 兜底）。
- 设计符合 RESTful 风格，与现有 `/VM/obs/set` 路由结构一致（SSH 操作类同步模式）。

## 不做什么

- 本次不实现监控 Agent 安装的具体业务逻辑（仅 TODO 占位）。
- 不改动鉴权框架本身，仅复用现有 `auth_filter` 机制。
- 不引入新的数据模型 / 持久化。
- 不采用异步任务模式（安装为单次 SSH 操作，不像 docker 创建那样复杂耗时）。

## 验收标准

- [ ] `POST /install/agent` 接口框架就绪：路由注册、参数校验、鉴权、异常处理生效；核心逻辑以 TODO 占位。
- [ ] 鉴权：无 token 或 token 非法时返回 401。
- [ ] 参数校验：缺参时返回 `{"code": 500, "msg": "invalid parameters", "data": ""}`。
- [ ] 代码风格与现有 `/VM/obs/set` 路由一致（`Ssh` 构造、`install_agent` 返回 `(flag, msg)` 元组、dict 响应）。
- [ ] 通过本地语法校验（`python -m py_compile`）。

## 影响范围

- `service/clab_agent.py`：新增模块，实现 `install_agent` 函数（TODO 占位）。
- `transport.py`：新增 `from service.clab_agent import install_agent` import 和 `/install/agent` 路由。

关联业务 Issue：openlibing/hidevlab-transport-service#（待创建）
