# machine-check — 技术设计

## 方案概述
在 hidevlab-transport-service 新增两个 HTTP 接口：
1. `/docker/machine/check`（异步）：`ThreadPoolExecutor` 并行 SSH 巡检多机 NPU + 共享存储，完成后 `sign_request` 回调黄区
2. `/docker/server/check`（同步）：`ThreadPoolExecutor` 并行 SSH 执行 df，同步聚合返回

## 架构决策

### 1. 异步接口用 threading.Thread + ThreadPoolExecutor
- 与现有 `async_docker_image_unpublish` 一致：接口线程立即返回，内部 `ThreadPoolExecutor` 并行处理多机
- 回调走 Apollo 配置 `DOCKER_MACHINE_CHECK_CALLBACK_URL`，经 `sign_request` 签名

### 2. 同步接口用 ThreadPoolExecutor 并行
- 多台机器并行 df 检查，减少响应时间
- 单台失败不中断，聚合所有结果同步返回

### 3. NPU 解析策略
- `npu-smi info` 输出表格，解析每个 NPU 的 `id` 和 `Health` 列
- health 含 `OK` 视为正常，含 `Warning`/`Critical`/`Fault` 视为异常
- `npu-smi` 命令不存在时 success=false, msg="npu-smi command not found"

### 4. 共享存储检查策略
- 接口1：`timeout 5 df -h <share_path>`，命令成功且路径出现在输出中即 success=true
- 接口2 share_storage：`df -h <check_path>/*`，解析所有行
- 接口2 harbor：`df -h <check_path>`，解析输出行

### 5. 命令白名单扩展
新增 `npu-smi` / `df` / `timeout` 到 `ALLOWED_COMMANDS`，与现有安全校验一致

## 涉及文件
| 文件 | 操作 | 说明 |
|------|------|------|
| transport.py | 修改 | 新增 `/docker/machine/check` + `/docker/server/check` 路由 |
| service/docker_manager.py | 修改 | 新增 `check_machine_health` + `check_server_disk` 方法 + NPU/df 解析辅助 |
| base/config.py | 修改 | 新增 `DOCKER_MACHINE_CHECK_CALLBACK_URL` Apollo 配置 |
| utils/command_security.py | 修改 | `ALLOWED_COMMANDS` 新增 `npu-smi`/`df`/`timeout` |

## 风险 & 缓解
| 风险 | 缓解 |
|------|------|
| SSH 凭证泄露 | 日志只记 IP，不记密码；密码仅用于 SSH 连接 |
| 路径注入 | 所有路径经 `CommandSecurity.safe_path` 转义 |
| npu-smi 不存在导致卡死 | `exec_command_check_status` 按 exit status 判断，超时由 SSH 层控制 |
| 并发连接数过多 | 复用现有 ThreadPoolExecutor 默认线程数，与 async_install_agent 一致 |

## 跨仓影响
无。仅 hidevlab-transport-service 单仓改动。
