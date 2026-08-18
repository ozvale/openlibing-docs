# machine-check

## 需求背景
黄区需要批量巡检机器状态（NPU 健康 + 共享存储挂载）以及服务器磁盘使用情况，用于环境健康度评估与容量监控。当前 transport-service 缺少批量设备巡检与磁盘检查能力，需新增两个接口支撑黄区运维场景。

关联业务 Issue: https://gitcode.com/openlibing/hidevlab-transport-service/issues/76

## 功能描述

### 接口1：POST /docker/machine/check（异步）
黄区传入多台机器 SSH 凭证 + 共享存储路径，transport-service 并行巡检每台机器：
- 执行 `npu-smi info` 检查每个 NPU 健康状态
- 执行 `timeout 5 df -h <share_path>` 检查共享存储挂载情况
- 巡检完成后异步回调黄区，回传每台机器的 npu + share_storage 明细

### 接口2：POST /docker/server/check（同步）
黄区传入多台服务器 SSH 凭证 + 检查路径 + type，transport-service 同步检查磁盘：
- type=share_storage：执行 `df -h <check_path>/*`（检查路径下所有子目录）
- type=harbor：执行 `df -h <check_path>`（检查整体磁盘）
- 同步返回每台服务器的磁盘使用明细（disk 直接是列表）

### 不做
- 不做 harbor 登录验证（接口1 移除 harbor 检查）
- 不做磁盘阈值告警，只回原始数据

## 验收标准
- [ ] /docker/machine/check 接收多机器，异步回调含每台 npu.items[{id,health}] + share_storage.success/msg
- [ ] /docker/server/check 同步返回，disk 直接是列表，按 type 区分 df 命令
- [ ] 所有路径经 CommandSecurity.safe_path 转义，密码日志脱敏（只记 IP）
- [ ] npu-smi / df / timeout 加入 ALLOWED_COMMANDS 白名单
- [ ] 新增 Apollo 配置 DOCKER_MACHINE_CHECK_CALLBACK_URL

## 影响范围
- transport.py：新增 2 个路由
- service/docker_manager.py：新增巡检/磁盘检查方法
- base/config.py：新增回调配置
- utils/command_security.py：扩展白名单
