# environment-docker-proxy

## 需求背景

在实际的裸机测试场景中，用例通常需要在裸机上动态拉起业务容器，此时希望 `environment` / `environments` fixture 能够灵活指向该新拉起的容器，从而通过统一的接口调用 `sendcmd` 执行命令，而无需手动处理底层的 `docker exec` 逻辑。

当前 `Device` 类的 `sendcmd` 方法直接在目标设备上执行命令，无法便捷地在设备上动态创建的容器内执行命令。测试用例需要手动拼接 `docker exec <container_name> <cmd>` 命令，这增加了测试代码的复杂度，且无法保持与原有 `Device` 接口的一致性。

## 功能描述

### 做什么

1. **`Device` 类新增 `set_docker` 方法**：
   - 用于注册/保存当前设备上已拉起的 Docker 容器名称
   - 参数：`docker_name`（字符串），容器名称
   - 支持注册多个容器名称

2. **`Device` 类扩展 `__getitem__` 字典取值能力**：
   - 当传入已注册的 `docker_name` 时，返回一个 `DockerProxy` 代理对象
   - `DockerProxy` 对象提供与 `Device` 一致的接口（`sendcmd` / `sendcmd_interactive`）
   - `DockerProxy` 的 `sendcmd` / `sendcmd_interactive` 自动将命令包装为 `docker exec <docker_name> <cmd>` 形式

3. **`environment` 和 `environments` fixture 均支持此能力**：
   - 单设备场景：`environment.set_docker("container1")` → `environment["container1"].sendcmd("ls")`
   - 多设备场景：`environments["device1"].set_docker("container1")` → `environments["device1"]["container1"].sendcmd("ls")`

### 不做什么

- 不改变 `environment.sendcmd` 的默认行为，调用 `set_docker` 后 `environment.sendcmd(cmd)` 仍执行裸机命令
- 不提供容器生命周期管理（创建、启动、停止、删除），这些由测试用例自行处理
- 不处理容器不存在或容器名无效的错误（由 `docker exec` 命令本身返回错误）

## 验收标准

- [ ] `Device` 类新增 `set_docker(docker_name: str)` 方法，支持注册容器名
- [ ] `Device` 类的 `__getitem__` 方法支持传入已注册的 `docker_name`，返回 `DockerProxy` 代理对象
- [ ] `DockerProxy` 代理对象提供 `sendcmd` 和 `sendcmd_interactive` 方法
- [ ] `DockerProxy.sendcmd(cmd)` 等价于执行 `docker exec <docker_name> <cmd>`
- [ ] `DockerProxy.sendcmd_interactive(cmd)` 等价于执行交互式 `docker exec -it <docker_name> <cmd>`
- [ ] `environment` fixture 支持上述功能
- [ ] `environments` fixture 支持上述功能
- [ ] 提供单元测试验证功能正确性

## 影响范围

| 模块/文件 | 操作 | 说明 |
|-----------|------|------|
| `pytest_testkit/lib/common/environment/device.py` | 修改 | 新增 `set_docker` 方法、扩展 `__getitem__`、新增 `DockerProxy` 类 |
| `pytest_testkit/plugin.py` | 无修改 | fixture 返回的 Device 对象已具备新能力 |
| `tests/test_docker_proxy.py` | 新增 | 单元测试验证功能 |

## 使用示例

```python
# 单设备场景
@pytest.mark.env({'model': 'Atlas 800T A2'})
@pytest.mark.remote_run
def test_with_docker(environment):
    # 在裸机上拉起容器
    environment.sendcmd("docker run -d --name my_container ubuntu:latest sleep 3600")

    # 注册容器
    environment.set_docker("my_container")

    # 通过代理对象在容器内执行命令
    container = environment["my_container"]
    output = container.sendcmd("ls /")
    assert "bin" in output

    # 交互式命令
    result = container.sendcmd_interactive("bash", expect_prompt="#")

    # environment.sendcmd 仍执行裸机命令
    environment.sendcmd("docker ps")

# 多设备场景
@pytest.mark.env({'name': 'device1'}, {'name': 'device2'})
@pytest.mark.remote_run
def test_multi_device_with_docker(environments):
    dev1 = environments["device1"]

    # 在 device1 上拉起容器
    dev1.sendcmd("docker run -d --name app_container nginx")

    # 注册容器
    dev1.set_docker("app_container")

    # 在容器内执行命令
    container = dev1["app_container"]
    output = container.sendcmd("nginx -v")
```

## 关联 Issue

- 业务 Issue: https://gitcode.com/openlibing/openlibing-pytest-executor/issues/18