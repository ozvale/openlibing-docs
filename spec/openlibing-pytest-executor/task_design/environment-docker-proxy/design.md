# environment-docker-proxy — 技术设计

## 方案概述

在 `Device` 类中新增 `DockerProxy` 代理类，通过 `set_docker` 方法注册容器名后，`Device.__getitem__` 返回该代理对象。代理对象提供：
- `sendcmd`：每次独立执行 `docker exec`（非交互式）
- `sendcmd_interactive`：持久 session 模式，第一次进入容器后后续命令在同一 session 执行
- `exit_docker`：退出 docker session 回到主机 shell

## 架构决策

### 1. DockerProxy 作为独立内部类

**决策**：`DockerProxy` 作为 `Device` 类的同模块类，不继承 `Device`。

**原因**：
- `DockerProxy` 只需实现 `sendcmd`、`sendcmd_interactive` 和 `exit_docker` 方法，继承 `Device` 会带来不必要的属性和方法
- 代理对象持有对父 `Device` 的引用，通过父 Device 执行实际的 SSH 命令
- 保持接口一致性但避免继承复杂性

### 2. 容器名注册使用简单字典存储

**决策**：在 `Device` 类中使用 `_registered_dockers: dict[str, DockerProxy]` 存储已注册容器。

**原因**：
- 简单直接，无需额外数据结构
- 每个容器名对应一个预创建的 `DockerProxy` 实例，避免重复创建

### 3. docker exec 命令格式

**决策**：
- 非交互式（`sendcmd`）：`docker exec {docker_name} {cmd}`，每次独立执行
- 交互式（`sendcmd_interactive`）：持久 session 模式
  - 第一次调用：`docker exec -it {docker_name} {cmd}`，进入容器
  - 后续调用：直接执行 `{cmd}`，在同一 docker session 中
  - 退出 session：调用 `exit_docker()`，执行 `exit` 回到主机

**原因**：
- 持久 session 模式符合用户实际使用习惯：进入容器后执行多条命令
- 非交互式 `sendcmd` 保持每次独立执行，适合单条命令场景
- 与标准 docker exec 用法一致

### 4. Session 状态管理

**决策**：`DockerProxy` 内部维护 `_in_docker_session` 状态。

**原因**：
- 需要区分是否已进入 docker session，决定是否包装命令
- 状态由 `sendcmd_interactive` 和 `exit_docker` 管理
- 每个代理对象独立维护自己的 session 状态

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `pytest_testkit/lib/common/environment/device.py` | 修改 | 新增 `DockerProxy` 类、`set_docker` 方法、修改 `__getitem__` |
| `tests/test_docker_proxy.py` | 新增 | 单元测试 |

## 类设计

### DockerProxy 类

```python
class DockerProxy:
    """代理对象，用于在 Device 上的 Docker 容器内执行命令。"""

    def __init__(self, device, docker_name: str):
        self._device = device
        self._docker_name = docker_name
        self._in_docker_session = False

    def sendcmd(self, cmd, timeout=None, environment=None,
                cwd=None, ignore_err=False, only_stdout=True):
        """非交互式命令：每次独立执行 docker exec。"""
        docker_cmd = f"docker exec {self._docker_name} {cmd}"
        return self._device.sendcmd(docker_cmd, ...)

    def sendcmd_interactive(self, cmd, expect_prompt=None, timeout=30, ...):
        """交互式命令：持久 session 模式。"""
        if not self._in_docker_session:
            # 第一次进入 docker session
            docker_cmd = f"docker exec -it {self._docker_name} {cmd}"
            self._in_docker_session = True
        else:
            # 已在 docker session 中，直接执行命令
            docker_cmd = cmd
        return self._device.sendcmd_interactive(docker_cmd, ...)

    def exit_docker(self, expect_prompt=None, timeout=10, only_stdout=True):
        """退出 docker session，回到主机 shell。"""
        result = self._device.sendcmd_interactive("exit", ...)
        self._in_docker_session = False
        return result
```

### Device 类修改

```python
class Device:
    def __init__(self, param: DeviceParam, **kwargs):
        # ... 现有初始化代码 ...
        self._registered_dockers: dict = {}

    def set_docker(self, docker_name: str) -> None:
        """注册 Docker 容器名。"""
        if docker_name not in self._registered_dockers:
            self._registered_dockers[docker_name] = DockerProxy(self, docker_name)

    def __getitem__(self, key):
        """支持字典式访问：优先返回已注册的 Docker 容器代理。"""
        if key in self._registered_dockers:
            return self._registered_dockers[key]
        if hasattr(self, key):
            return getattr(self, key)
        return self.extra_attrs.get(key)
```

## 使用示例

```python
# 进入容器交互式 session
container = environment["my_container"]
container.sendcmd_interactive("/bin/bash")  # docker exec -it my_container /bin/bash

# 在同一 session 中执行多条命令
container.sendcmd_interactive("ls -la")      # 直接执行 ls -la（已在 docker 中）
container.sendcmd_interactive("cat /etc/hosts")  # 直接执行 cat /etc/hosts

# 退出 docker session
container.exit_docker()  # 执行 exit，回到主机 shell

# 再次进入会重新包装
container.sendcmd_interactive("/bin/bash")  # docker exec -it my_container /bin/bash

# 非交互式命令（每次独立执行）
container.sendcmd("ls")  # docker exec my_container ls（独立进程）
```

## 风险 & 缓解

| 风险 | 缓解措施 |
|------|---------|
| docker_name 重复注册 | 允许重复调用 `set_docker`，不会创建新的代理对象 |
| 容器不存在时执行命令 | 不做前置检查，由 `docker exec` 返回错误，用户自行处理 |
| 命令中含特殊字符（引号、管道） | 直接拼接，docker exec 会正确处理，复杂命令建议用户自行测试 |
| session 状态与实际 SSH 状态不一致 | 用户需正确调用 `exit_docker()` 退出；若 SSH 断开重连，session 状态可能需手动重置 |

## 跨仓影响

无跨仓影响，仅修改 `pytest-testkit` 模块。