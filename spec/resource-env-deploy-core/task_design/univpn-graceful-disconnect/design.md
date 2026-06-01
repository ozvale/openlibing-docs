# univpn-graceful-disconnect — 技术设计

## 方案概述
使用共享 emptyDir 卷 + 信号文件机制，实现 ansible-runner 到 univpn 容器的任务完成通知，触发 VPN 优雅断开。

## 架构决策

### 容器间通信：共享卷信号文件
- 选择 emptyDir 卷 `vpn-signal` 作为容器间通信介质
- ansible-runner 完成后写入 `/vpn-signal/.task-complete` 信号文件
- univpn 包装脚本轮询检测信号文件，收到信号后向 UniVPN 进程发送 `q` 命令断开

### univpn 容器 command 覆盖
- 使用 `sh -c` 包装脚本覆盖镜像默认 entrypoint
- 包装脚本：启动原始 entrypoint → 后台运行 → 轮询信号文件 → 收到信号后断开
- 保留原始 entrypoint 的所有环境变量和卷挂载

### preStop 兜底钩子
- 在 univpn 容器上添加 preStop 钩子
- 当 Pod 终止时（异常场景），preStop 中执行 `pkill -f UniVPNCS` 确保 VPN 断开
- 超时 10 秒，避免阻塞 Pod 删除

## 涉及文件
| 文件 | 操作 | 说明 |
|------|------|------|
| KubernetesVpnSupport.java | 修改 | 添加信号卷、覆盖 command、添加 preStop |
| KubernetesTaskJobFactory.java | 修改 | ansible-runner 添加信号卷挂载和写入逻辑 |
| KubernetesVpnSupportTest.java | 修改 | 新增测试用例 |
| KubernetesTaskJobFactoryTest.java | 修改 | 新增测试用例 |

## 风险 & 缓解
| 风险 | 缓解 |
|------|------|
| univpn 镜像 entrypoint 路径未知 | 从日志推断使用 `/entrypoint.sh`，包装脚本中使用 `$@` 或 `/proc/1/cmdline` 获取原始命令 |
| UniVPNCS 不响应 `q` 命令 | preStop 中使用 `pkill` 作为兜底 |
| 信号文件写入延迟 | emptyDir 是本地存储，延迟可忽略 |
