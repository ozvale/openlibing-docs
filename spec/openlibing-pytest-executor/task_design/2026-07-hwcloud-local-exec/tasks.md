# 华为云资源池本地执行支持 - 任务清单

## 任务总览

| 任务编号 | 任务描述 | 状态 | 备注 |
|---------|---------|------|------|
| T-01 | scheduler_config.py: 硬编码 env_provider 为 k8s，添加 env_deploy_model 配置 | PENDING | |
| T-02 | main.py: 添加 --env_deploy_model 命令行参数 | PENDING | |
| T-03 | start.sh: 添加 env_deploy_model 参数传递 | PENDING | |
| T-04 | env_manager.py: 添加 Co-located 分支和 _get_local_ip 方法 | PENDING | |
| T-05 | pytest_executor.py: 设置 local_exec 标志传递给 testkit | PENDING | |
| T-06 | device.py: 添加 local_exec 属性和本地执行逻辑 | PENDING | |
| T-07 | manager.py: 解析 local_exec 字段到 Device 对象 | PENDING | |
| T-08 | 单元测试: 配置校验和 Device 本地执行 | PENDING | |
| T-09 | 集成测试: Co-located 模式完整流程 | PENDING | |
| T-10 | 验证测试: 用例代码拷贝和命令执行 | PENDING | |

## 任务详情

### T-01: scheduler_config.py - 硬编码 env_provider 为 k8s，添加 env_deploy_model 配置

**文件**: `pytest-executor/src/scheduler/scheduler_config.py`

**实现内容**:
- `env_provider` 硬编码为 "k8s"，不再可配置
- 添加 `env_deploy_model` 类属性，默认 "Dislocated"
- 添加 `exec_in_runner` 类属性，默认 `False`
- 删除 `set_env_provider()` 方法（不再需要）

**完成标准**:
- [ ] `env_provider` 保持硬编码为 "k8s"
- [ ] `env_deploy_model` 属性正确添加，默认 "Dislocated"
- [ ] `exec_in_runner` 属性正确添加
- [ ] `set_env_provider()` 方法已删除

### T-02: main.py - 添加 --env_deploy_model 命令行参数

**文件**: `pytest-executor/main.py`

**实现内容**:
- 在 `parse_args()` 中添加 `--env_deploy_model` 参数，可选，默认 `Dislocated`
- 删除 `--env_provider` 参数（不再需要）
- 在 `_init_config()` 中调用 `Config.set("env_deploy_model", args.env_deploy_model)`

**完成标准**:
- [ ] `--env_deploy_model` 参数正确添加
- [ ] 默认值为 `Dislocated`
- [ ] `--env_provider` 参数已删除
- [ ] `_init_config()` 正确调用 `Config.set("env_deploy_model", ...)`

### T-03: start.sh - 添加 env_deploy_model 参数传递

**文件**: `pytest-executor/start.sh`

**实现内容**:
- 在 python 命令中添加 `${env_deploy_model:+--env_deploy_model "${env_deploy_model}"}`

**完成标准**:
- [ ] 参数传递正确添加

### T-04: env_manager.py - 添加 Co-located 分支和 _get_local_ip 方法

**文件**: `pytest-executor/src/scheduler/env_manager.py`

**实现内容**:
- 在 `allocate_environments()` 中添加 `Co-located` 分支
- `Co-located` 模式下：跳过 API 调用，使用本机 IP，设置 `exec_in_runner=True`
- 添加 `_get_local_ip()` 辅助方法获取本机 IP
- 添加单机用例限制检查：多 device 用例抛出 ValueError
- 将所有 `if Config.env_provider == "hwcloud"` 判断改为 `if Config.env_deploy_model == "Co-located"`

**完成标准**:
- [ ] `Co-located` 分支正确添加
- [ ] 跳过 API 调用
- [ ] 设备 IP 设置为本机 IP
- [ ] `exec_in_runner=True` 正确设置
- [ ] `_get_local_ip()` 方法正确实现
- [ ] 多 device 用例抛出 ValueError 异常
- [ ] 所有 hwcloud 分支判断已改为 Co-located

### T-05: pytest_executor.py - 设置 local_exec 标志传递给 testkit

**文件**: `pytest-executor/src/executor/pytest_executor.py`

**实现内容**:
- 在 `run_tests_on_host()` 中判断 `exec_in_runner` 标志
- `exec_in_runner=True` 时，设置设备的 `local_exec=True`
- 仍然保持用例代码拷贝到 `/home/` 下的逻辑

**完成标准**:
- [ ] `exec_in_runner` 判断逻辑正确
- [ ] `local_exec=True` 正确设置到设备信息
- [ ] 用例代码拷贝逻辑保持不变

### T-06: device.py - 添加 local_exec 属性和本地执行逻辑

**文件**: `pytest-testkit/pytest_testkit/lib/common/environment/device.py`

**实现内容**:
- 添加 `local_exec` 属性，默认 `False`
- 修改 `__init__()` 方法，添加 `local_exec` 参数
- 修改 `login()` 方法：`local_exec=True` 时直接返回成功
- 修改 `sendcmd()` 方法：`local_exec=True` 时使用 subprocess 本地执行
- 修改 `sendcmd_interactive()` 方法：`local_exec=True` 时使用 subprocess 本地执行
- 修改 `upload_file()` 方法：`local_exec=True` 时使用 shutil 本地拷贝
- 修改 `download_file()` 方法：`local_exec=True` 时使用 shutil 本地拷贝

**完成标准**:
- [ ] `local_exec` 属性正确添加
- [ ] `__init__()` 支持 `local_exec` 参数
- [ ] `login()` `local_exec=True` 时跳过 SSH
- [ ] `sendcmd()` `local_exec=True` 时使用 subprocess
- [ ] `sendcmd_interactive()` `local_exec=True` 时使用 subprocess
- [ ] `upload_file()` `local_exec=True` 时使用 shutil
- [ ] `download_file()` `local_exec=True` 时使用 shutil

### T-07: manager.py - 解析 local_exec 字段到 Device 对象

**文件**: `pytest-testkit/pytest_testkit/lib/common/environment/manager.py`

**实现内容**:
- 修改 `_parse_devices()` 方法
- 解析设备信息中的 `local_exec` 字段并设置到 Device 对象

**完成标准**:
- [ ] `_parse_devices()` 正确解析 `local_exec` 字段
- [ ] Device 对象正确设置 `local_exec` 属性

### T-08: 单元测试 - 配置校验和 Device 本地执行

**文件**: 待创建或修改现有测试文件

**测试用例**:
- [ ] `test_get_local_ip` - 获取本机 IP
- [ ] `test_device_local_exec_login` - local_exec=True 时 login() 直接返回成功
- [ ] `test_device_local_exec_sendcmd` - local_exec=True 时 sendcmd() 使用 subprocess
- [ ] `test_config_env_deploy_model_default` - env_deploy_model 默认值为 Dislocated

### T-09: 集成测试 - Co-located 模式完整流程

**文件**: 待创建

**测试用例**:
- [ ] `test_co_located_mode_full_flow` - Co-located 模式完整流程测试
- [ ] `test_dislocated_mode_compatibility` - Dislocated 模式兼容性测试

### T-10: 验证测试 - 用例代码拷贝和命令执行

**执行命令**:
```bash
cd pytest-executor
python -m pytest tests/ -v -k "co_located"
```

**完成标准**:
- [ ] 所有单元测试通过
- [ ] 所有集成测试通过
- [ ] `exec_in_runner=True` 时用例代码仍然拷贝到 `/home/` 下
- [ ] 本地执行命令返回正确结果
