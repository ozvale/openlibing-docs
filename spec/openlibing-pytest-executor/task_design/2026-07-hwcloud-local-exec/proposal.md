# 华为云资源池本地执行支持 - 需求提案

## 1. 需求背景

昇腾社区当前正在切换 Nightly 流水线用例框架到 pytest。在使用华为云上资源池时，带卡环境会由流水线直接申请，这种情况下调度框架和用例将在一个环境内，不再需要登录，需要调度框架和之前 uniautos 时一样，保留这种能力。

## 2. 需求目标

支持华为云资源调度场景，提高资源利用率。调度框架支持直接在华为云申请的 runner 中运行框架+测试用例，不再去 k8s 动态申请被测设备，直接在当前设备执行用例。

## 3. 功能需求

### 3.1 场景标识

| 配置项 | 值 | 描述 |
|--------|-----|------|
| `env_provider` | `hwcloud` | 通过流水线参数传入，标识华为云资源池场景 |

### 3.2 调度层行为

| 行为 | 描述 |
|------|------|
| 跳过环境申请 | `env_provider=hwcloud` 时，不再调用 k8s API 申请被测设备 |
| 设置执行标志 | 将 `exec_in_runner` 标志设置为 `True` |
| 使用本机 IP | 设备信息中的 IP 地址替换为本机 IP |
| 单机用例限制 | hwcloud 模式仅支持单机用例（单 device），多 device 用例将抛出 ValueError |

### 3.3 执行层行为

| 行为 | 描述 |
|------|------|
| 识别 `exec_in_runner` | `execute()` 方法优先检查 `exec_in_runner` 标志 |
| 新增 `_execute_in_runner` | 当 `exec_in_runner=True` 时，使用新方法执行 |
| 拷贝用例代码 | 使用 `shutil.copytree` 将用例代码拷贝到 `/home/` 下 |
| 本地执行 pytest | 在 `/home/<test_dir>` 目录下本地执行 pytest |
| 传递 `local_exec` | 将 `local_exec=True` 标志传递给 testkit 插件的 environment(device 对象) |

### 3.4 testkit 插件行为

| 行为 | 描述 |
|------|------|
| 跳过 SSH 登录 | `local_exec=True` 时，device 对象跳过 SSH 注册和登录 |
| 本地执行命令 | 直接使用 subprocess 本地执行命令 |

### 3.5 配置校验

| 配置项 | 允许值 | 描述 |
|--------|--------|------|
| `env_provider` | `k8s`, `hidevlab`, `hwcloud` | 外部输入时进行名单校验 |

## 4. 验收标准

### 4.1 功能验收

1. ✅ `env_provider=hwcloud` 时，调度框架跳过 k8s 环境申请
2. ✅ `env_provider=hwcloud` 时，设备 IP 为本机 IP，`exec_in_runner=True`
3. ✅ 执行器传递 `local_exec=True` 到 TESTBED_DEVICES 环境变量
4. ✅ testkit 的 Device 对象 `local_exec=True` 时，跳过 SSH 登录
5. ✅ testkit 的 Device 对象 `local_exec=True` 时，使用 subprocess 本地执行命令
6. ✅ 用例代码仍然拷贝到 `/home/` 下
7. ✅ `env_provider` 输入不在白名单时抛出错误
8. ✅ hwcloud 模式下，设备数量不为 1 时抛出 ValueError 异常（多 device 或空列表）

### 4.2 接口验收

```bash
# 启动命令 - 通过流水线参数传入 env_provider
python main.py \
    --testcase_dir /path/to/testcases \
    --env_provider hwcloud \
    ...
```

```python
# Device 对象 local_exec 属性
device = Device(...)
device.local_exec = True
device.login()  # 跳过 SSH，直接返回成功
result = device.sendcmd("ls -l")  # 使用 subprocess 本地执行
```

### 4.3 向后兼容性验收

| 场景 | 行为 |
|------|------|
| `env_provider=k8s` | 原有行为，通过 k8s API 申请环境 |
| `env_provider=hidevlab` | 原有行为，通过 hidevlab API 申请环境 |
| 不传 `env_provider` | 默认 `k8s`，保持原有行为 |

## 5. 非功能需求

| 需求类型 | 描述 |
|----------|------|
| 性能 | 不显著增加测试执行耗时 |
| 兼容性 | 不影响现有测试用例运行 |
| 可维护性 | 代码符合现有项目规范 |

## 6. 关联 Issue

- Issue #xxx: 【pytest-executor】支持华为云资源池本地执行

## 7. 预计交付时间

2026-07-20
