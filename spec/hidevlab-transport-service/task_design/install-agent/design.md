# install-agent — 技术设计

## 方案概述

在 transport 服务内新增同步接口 `POST /install/agent`，通过 paramiko SSH 连接目标主机，按线性流水线执行 clabAgent 安装；安装包元数据（URL / x86 包名 / arm 包名）从 Apollo 读取，避免硬编码；针对 PXE 新机的 tar 缺失场景，按 OS 自动用 apt / dnf 安装。

## 架构决策

| 决策 | 选择 | 原因 |
|------|------|------|
| 同步 vs 异步 | 同步 | 内部接口、调用方少；异步化引入 task_id 轮询复杂度，收益不匹配 |
| 配置来源 | Apollo | 与仓内既有 `DOCKER_CONTAINER_CHECK_SCRIPTS` 等配置一致，避免硬编码 |
| 函数拆分 | 7 个私有子函数 + 主编排 | 单函数 200+ 行可读性差；拆分后每个子函数职责单一，便于定位失败环节 |
| tar 缺失处理 | 自动按 OS 安装 | PXE 刚装完系统的机器普遍没 tar；失败重试不如直接装 |
| SSH 命令执行 | `exec_command` + 重试 | wget 下载 / tar 安装 / 服务状态检查等环节网络/源不稳，需要重试 |

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `service/clab_agent.py` | 新增 | `install_agent` 主函数 + 7 个子函数（`_get_host_arch` / `_download_agent_pkg` / `_ensure_tar_available` / `_extract_agent_pkg` / `_write_server_id_ip` / `_start_agent` / `_wait_for_service_active`） |
| `transport.py` | 新增路由 | `POST /install/agent`，解析 Python 字面量 body（项目既有模式） |
| `base/config.py` | 新增配置 | `CLABAGENT_PACK_SOURCE_URL` / `CLABAGENT_X86_PACK_NAME` / `CLABAGENT_ARM64_PACK_NAME`（均从 Apollo `agent` 命名空间读取） |

## 安装流水线

```
install_agent(ssh_obj, server_id)
  ├─ get_ssh_connection(ssh_obj)            # 含 3 次重试
  ├─ _get_host_arch(client)                 # uname -m → x86_64/aarch64
  ├─ _download_agent_pkg(client, arch)      # 拼接 URL + wget（含重试）
  ├─ _extract_agent_pkg(client, ssh_obj, pkg_path)
  │    ├─ _ensure_tar_available(client, ssh_obj)   # 检测→按OS装tar→重试
  │    └─ tar -xzf <pkg> -C <dir>
  ├─ _write_server_id_ip(client, ssh_obj, server_id)  # 写 id_ip.txt
  ├─ _start_agent(client, ssh_obj)          # bash init_clabagent.sh
  ├─ _wait_for_service_active(client, 'clabagent.service')  # 轮询 systemctl is-active
  └─ rm -f <pkg_path>                       # 清理临时包（失败不阻塞）
```

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| gunicorn sync worker 超时（默认 120s） | `gunicorn_config.py` `timeout = 120`；慢机器需调大或排查 sshd 慢连接 |
| Apollo 配置未发布导致读到旧值 | 代码层校验配置非空；运维侧需发布后重启服务（Apollo 客户端热更新对部分配置项不生效） |
| 目标机器被释放导致 SSH 不通 | `get_ssh_connection` 自带 3 次重试，失败后返回明确错误 |
| wget 下载源不稳 | `wget --tries=3 --timeout=30` |
| PXE 新机缺 tar | `_ensure_tar_available` 按 OS 自动 apt/dnf 安装 |

## 跨仓影响

无。本次改动仅限 `hidevlab-transport-service` 业务仓。
