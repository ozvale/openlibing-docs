# hidevlab-transport-service AI Memory

本文件沉淀经过验证且未来会复用的规则，不存放一次性实现细节。

## 运维与配置

### Apollo 配置变更后需重启服务才生效

本仓的 Apollo 客户端对部分配置项**不热更新**。在 Apollo 修改/新增配置值后，必须重启 transport 服务（`systemctl restart transport-alpha.service`），否则运行时读到的是旧值（可能是 `None`）。

典型表现：Apollo 配置明明改了，但代码报"配置未定义"或拼出含 `%s` 占位符的旧值 URL。

### gunicorn sync worker 超时是长耗时接口的隐形坑

`gunicorn_config.py` 的 `timeout`（当前为 120s）是硬上限。worker 超时会被 master SIGKILL，日志只记 `[ERROR] Error handling request <path>`，**不带 traceback**。

长耗时操作（远程安装、大文件下载、SSH 慢连接）要么：
- 调大 `timeout`（治标），或
- 异步化（治本，可参考 `service/docker_manager.py` 的 `async_install_agent` 模式）

排查此类超时时，先看请求开始到 ERROR 的耗时是否接近 `timeout` 值。

## 接口设计

### body 解析用 `ast.literal_eval` 而非 JSON

本仓所有 POST 接口用 `ast.literal_eval(str(request.get_data(), "utf-8"))` 解析 body，**不是标准 JSON**。调用方需传 Python 字面量格式：
- dict 用 `{}`，字符串必须加引号
- 数字可直接写，不需要引号

新增端点时沿用此模式保持一致性。详见 `transport.py` 中 `set_agent_interval` / `delete_agent` 等既有端点。

## 远程安装

### PXE 刚装完系统的机器可能缺 tar

通过 SSH 在 PXE 新机上执行解压前，必须先确保 tar 可用：
- 检测：`command -v tar`
- 安装：ubuntu/debian 用 `apt-get`，openeuler/centos 用 `dnf`
- 安装命令本身也要加重试（`apt-get -o Acquire::Retries=3` / `dnf --setopt=retries=5`）

参考实现：`service/clab_agent.py` 的 `_ensure_tar_available`。

### 目标机器被释放会导致 SSH 不通

远端机器被释放后，SSH 连接会卡在握手阶段直到超时。`get_ssh_connection` 自带 3 次重试，但每次握手慢时累积耗时可能撞上 gunicorn timeout。排查 SSH 不通时，先确认机器是否还在运行。
