# 华为云资源池本地执行支持 - 技术设计

## 1. 架构设计

### 1.1 整体架构

```
┌─────────────────────────────────────────────────────────────────────────┐
│ 入口层 (main.py + start.sh)                                            │
│   --env_deploy_model=Co-located (外部参数, 默认 Dislocated)             │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 配置层 (scheduler_config.py)                                           │
│   env_provider = "k8s" (硬编码, 不可配置)                              │
│   env_deploy_model: Co-located / Dislocated                            │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 调度层 (run_scheduler.py)                                              │
│   env_deploy_model=Co-located → 跳过 SSH 密钥生成                       │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 环境管理 (env_manager.py)                                               │
│   Co-located 模式:                                                      │
│     - 跳过 API 申请环境                                                 │
│     - 使用本机 IP 构建设备信息                                          │
│     - 设置 exec_in_runner=True                                         │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ 执行层 (pytest_executor.py)                                            │
│   exec_in_runner=True → 传递 local_exec=True 到 TESTBED_DEVICES         │
│                         仍然拷贝用例代码到 /home/ 下                     │
└─────────────────────────────────────────────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────────┐
│ testkit 层 (device.py)                                                 │
│   local_exec=True → sendcmd() 使用 subprocess 直接执行                  │
│                     login() 跳过 SSH 连接                               │
└─────────────────────────────────────────────────────────────────────────┘
```

### 1.2 核心设计要点

| 设计点 | 方案 | 说明 |
|--------|------|------|
| 场景标识 | `env_deploy_model=Co-located` | 通过命令行参数传入 |
| 执行标志 | `exec_in_runner` (调度层) / `local_exec` (设备层) | 区分调度层和设备层的本地执行标志 |
| 环境申请 | 跳过 API 调用 | Co-located 模式下直接使用本机环境 |
| 设备 IP | 使用本机 IP | 通过 `socket.gethostbyname(socket.gethostname())` 获取 |
| SSH 登录 | 跳过 | `local_exec=True` 时 Device.login() 直接返回成功 |
| 命令执行 | subprocess 本地执行 | `local_exec=True` 时 Device.sendcmd() 使用 subprocess |
| 用例代码拷贝 | 保持原有逻辑 | 仍然拷贝到 `/home/` 下 |
| env_provider | 硬编码为 k8s | 不再从外部传入 |

## 2. 关键类/方法设计

### 2.1 配置层 - Config 类扩展

**文件路径**: `pytest-executor/src/scheduler/scheduler_config.py`

**配置项**:

| 配置项 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `env_provider` | `str` | `"k8s"` | 环境提供者（硬编码，不可配置） |
| `env_deploy_model` | `str` | `"Dislocated"` | 部署模式：Co-located 或 Dislocated |
| `exec_in_runner` | `bool` | `False` | 是否在 runner 上执行用例 |

### 2.2 入口层 - main.py 修改

**文件路径**: `pytest-executor/main.py`

**修改内容**:

| 修改点 | 描述 |
|--------|------|
| 添加命令行参数 | `--env_deploy_model` 参数，可选，默认 `Dislocated` |
| 设置配置 | 在 `_init_config()` 中调用 `Config.set("env_deploy_model", args.env_deploy_model)` |

**修改后代码**:

```python
def parse_args():
    parser = argparse.ArgumentParser()
    # ... 其他参数 ...
    parser.add_argument("--env_deploy_model", required=False, default="Dislocated")
    return parser.parse_args()

def _init_config(args):
    # ... 其他配置 ...
    Config.set("env_deploy_model", args.env_deploy_model)
```

### 2.3 启动脚本 - start.sh 修改

**文件路径**: `pytest-executor/start.sh`

**修改内容**:

| 修改点 | 描述 |
|--------|------|
| 添加参数传递 | `${env_deploy_model:+--env_deploy_model "${env_deploy_model}"}` |

### 2.4 环境管理器 - env_manager.py 修改

**文件路径**: `pytest-executor/src/scheduler/env_manager.py`

**修改方法**: `allocate_environments()`

**修改逻辑**:

```python
def allocate_environments(self, env_case_info):
    env_deploy_model = Config.env_deploy_model

    if env_deploy_model == "Co-located":
        local_ip = self._get_local_ip()
        if len(all_devices) != 1:
            raise ValueError(
                f"Co-located mode requires exactly one device, "
                f"but {len(all_devices)} devices were requested"
            )
        for device in env_case_info["device_list"]:
            device["ip"] = local_ip
            device["exec_in_runner"] = True
        env_case_info["env_apply_status"] = "SUCCESS"
        env_case_info["exec_in_runner"] = True
        return

    # ... 原有 k8s/hidevlab 逻辑
```

**约束说明**: Co-located 模式仅支持单机用例（单 device），设备数量不为 1 时将抛出 ValueError 异常。

**新增辅助方法**:

| 方法名 | 功能 | 返回值 |
|--------|------|--------|
| `_get_local_ip()` | 获取本机 IP 地址 | `str` - 本机 IP |

```python
def _get_local_ip(self):
    import socket
    return socket.gethostbyname(socket.gethostname())
```

### 2.5 执行器 - pytest_executor.py 修改

**文件路径**: `pytest-executor/src/executor/pytest_executor.py`

**修改方法**: `execute()` 和新增 `_execute_in_runner()`

**修改逻辑**:

`execute()` 方法优先检查 `exec_in_runner` 标志：

```python
def execute(self, case_list, env_case_info, env_var):
    exec_in_runner = env_case_info.get("exec_in_runner", False)
    success = True
    
    if exec_in_runner:
        logger.info("Executing in runner mode (Co-located)")
        success &= self._execute_in_runner(case_list, env_case_info, env_var)
    else:
        # ... 原有 local/remote 分支逻辑 ...
    
    self.collect_logs(env_case_info)
    return success
```

新增 `_execute_in_runner()` 方法：

```python
def _execute_in_runner(self, case_list, env_case_info, env_var):
    test_dir_name = self.test_dir.name
    home_path = f"/home/{test_dir_name}"
    
    if not self._is_safe_path(home_path):
        logger.error(f"Unsafe path detected: {home_path}. Aborting.")
        return False
    
    if os.path.exists(home_path):
        shutil.rmtree(home_path)
    shutil.copytree(str(self.test_dir), home_path)
    
    # 在 /home/<test_dir> 目录下本地执行 pytest
    cmd = [sys.executable, "-m", "pytest", ...]
    result = subprocess.run(cmd, cwd=home_path, ...)
    return result.returncode == 0
```

**关键点**:
- 使用 `shutil.copytree` 将用例代码拷贝到 `/home/` 下（本地拷贝，无需 SSH）
- 在 `/home/<test_dir>` 目录下执行 pytest
- 通过 `TESTBED_DEVICES` 环境变量传递 `local_exec=True` 的设备信息

### 2.6 Device 类 - device.py 修改

**文件路径**: `pytest-testkit/pytest_testkit/lib/common/environment/device.py`

**新增属性**:

| 属性名 | 类型 | 默认值 | 描述 |
|--------|------|--------|------|
| `local_exec` | `bool` | `False` | 是否本地执行命令，跳过 SSH |

**修改方法**:

| 方法名 | 修改内容 |
|--------|----------|
| `__init__()` | 添加 `local_exec` 参数和属性 |
| `login()` | `local_exec=True` 时直接返回成功 |
| `sendcmd()` | `local_exec=True` 时使用 subprocess 本地执行 |
| `sendcmd_interactive()` | `local_exec=True` 时使用 subprocess 本地执行 |
| `upload_file()` | `local_exec=True` 时使用 shutil 本地拷贝 |
| `download_file()` | `local_exec=True` 时使用 shutil 本地拷贝 |

**方法实现逻辑 - login**:

```python
def login(self):
    if self.local_exec:
        return True
    # ... 原有 SSH 登录逻辑
```

**方法实现逻辑 - sendcmd**:

```python
def sendcmd(self, cmd, timeout=None, env_vars=None, cwd=None,
            ignore_err=False, only_stdout=True):
    if self.local_exec:
        result = subprocess.run(
            cmd, shell=True, capture_output=True,
            timeout=timeout, cwd=cwd, env=env_vars, text=True
        )
        if ignore_err or result.returncode == 0:
            return result.stdout if only_stdout else {
                'success': result.returncode == 0,
                'stdout': result.stdout,
                'stderr': result.stderr
            }
        raise Exception(f"Command failed: {cmd}\n{result.stderr}")
    # ... 原有 SSH 执行逻辑
```

### 2.7 环境管理器 (testkit) - manager.py 修改

**文件路径**: `pytest-testkit/pytest_testkit/lib/common/environment/manager.py`

**修改方法**: `_parse_devices()`

**修改逻辑**:

```python
def _parse_devices(self, devices_info):
    devices = []
    for device_info in devices_info:
        device = Device(
            ip=device_info.get("ip"),
            port=device_info.get("port", 22),
            username=device_info.get("username"),
            password=device_info.get("password"),
            local_exec=device_info.get("local_exec", False)
        )
        devices.append(device)
    return devices
```

## 3. 数据结构设计

### 3.1 TESTBED_DEVICES 环境变量扩展

```json
{
    "device_list": [
        {
            "ip": "127.0.0.1",
            "port": 22,
            "username": "root",
            "password": "",
            "local_exec": true,
            "exec_in_runner": true
        }
    ]
}
```

## 4. API 设计

### 4.1 对外接口

| 接口 | 功能 | 调用方式 |
|------|------|----------|
| `--env_deploy_model` | 设置部署模式 | 命令行参数 |
| `Device.local_exec` | 设备本地执行标志 | 属性设置 |

### 4.2 内部接口

| 方法 | 功能 | 调用时机 |
|------|------|----------|
| `env_manager._get_local_ip()` | 获取本机 IP | Co-located 模式环境分配时 |
| `pytest_executor.run_tests_on_host()` | 设置 local_exec 标志 | 测试执行前 |

## 5. 部署与集成方案

### 5.1 依赖与环境

| 依赖 | 版本要求 | 说明 |
|------|----------|------|
| Python | 3.8+ | 项目基础依赖 |
| pytest | 6.0+ | 测试框架 |
| subprocess | 内置模块 | 本地命令执行 |
| socket | 内置模块 | 获取本机 IP |

### 5.2 集成方式

1. **修改文件**: `pytest-executor/src/scheduler/scheduler_config.py`
   - `env_provider` 硬编码为 "k8s"
   - 添加 `env_deploy_model` 配置项，默认 "Dislocated"

2. **修改文件**: `pytest-executor/main.py`
   - 添加 `--env_deploy_model` 命令行参数
   - 在 `_init_config()` 中调用 `Config.set("env_deploy_model", args.env_deploy_model)`

3. **修改文件**: `pytest-executor/start.sh`
   - 添加 `${env_deploy_model:+--env_deploy_model "${env_deploy_model}"}` 参数传递

4. **修改文件**: `pytest-executor/src/scheduler/env_manager.py`
   - 在 `allocate_environments()` 中添加 `Co-located` 分支
   - 添加 `_get_local_ip()` 辅助方法

5. **修改文件**: `pytest-executor/src/executor/pytest_executor.py`
   - 在 `run_tests_on_host()` 中设置 `local_exec=True`

6. **修改文件**: `pytest-testkit/pytest_testkit/lib/common/environment/device.py`
   - 添加 `local_exec` 属性
   - 修改 `login()`、`sendcmd()` 等方法支持本地执行

7. **修改文件**: `pytest-testkit/pytest_testkit/lib/common/environment/manager.py`
   - 在 `_parse_devices()` 中解析 `local_exec` 字段

## 6. 安全性考虑

### 6.1 本地执行安全

| 风险点 | 防护措施 |
|--------|----------|
| 命令注入 | `sendcmd()` 使用 shell=True，需要调用方确保命令安全 |
| 权限问题 | 本地执行时使用当前用户权限，需要确保权限足够 |

## 7. 影响范围

### 7.1 修改的文件

| 文件 | 修改类型 | 影响 |
|------|----------|------|
| `scheduler_config.py` | 修改 | `env_provider` 硬编码为 "k8s"，添加 `env_deploy_model` 配置 |
| `main.py` | 修改 | 添加 `--env_deploy_model` 参数，移除 `--env_provider` |
| `start.sh` | 修改 | 添加参数传递 |
| `env_manager.py` | 修改 + 新增 | 添加 `Co-located` 分支和 `_get_local_ip()` 方法 |
| `pytest_executor.py` | 修改 | 设置 `local_exec` 标志 |
| `device.py` | 修改 + 新增 | 添加 `local_exec` 属性和本地执行逻辑 |
| `manager.py` | 修改 | 解析 `local_exec` 字段 |

### 7.2 新增的文件

| 文件 | 用途 |
|------|------|
| 无 | 无需新增文件 |

### 7.3 向后兼容性

| 场景 | 行为 |
|------|------|
| `env_deploy_model=Dislocated` | 原有行为，通过 k8s API 申请环境 |
| `env_deploy_model=Co-located` | 新行为，本地执行 |
| 不传 `env_deploy_model` | 默认 `Dislocated`，保持原有行为 |
| `local_exec=False` | 原有行为，通过 SSH 执行命令 |

## 8. 测试策略

### 8.1 单元测试

| 测试场景 | 测试用例 |
|----------|----------|
| 本机 IP 获取 | 测试 `_get_local_ip()` 返回正确的本机 IP |
| Device 本地执行 | 测试 `local_exec=True` 时 `sendcmd()` 使用 subprocess |
| Device SSH 跳过 | 测试 `local_exec=True` 时 `login()` 直接返回成功 |
| 配置传递 | 测试 `exec_in_runner` 和 `local_exec` 标志正确传递 |

### 8.2 集成测试

| 测试场景 | 测试方法 |
|----------|----------|
| Co-located 模式完整流程 | 设置 `env_deploy_model=Co-located`，验证跳过环境申请、本地执行 |
| Dislocated 模式兼容性 | 设置 `env_deploy_model=Dislocated`，验证原有行为不变 |

### 8.3 验证测试

| 测试场景 | 测试方法 |
|----------|----------|
| 用例代码拷贝 | 验证 `exec_in_runner=True` 时仍然拷贝代码到 `/home/` 下 |
| 命令执行 | 验证本地执行命令返回正确结果 |
