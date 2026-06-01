# univpn-graceful-disconnect — 归档凭证

## 变更概述
为 env-deploy-core 的 Ansible 任务 Pod 中的 univpn sidecar 容器添加优雅断开机制。

## 业务仓信息
- **仓库**: env-deploy-core
- **分支**: fix/univpn-graceful-disconnect
- **Commit**: ed761c7
- **关联 Issue**: openlibing/openlibing-ai-engineering#7

## 修改文件
| 文件 | 操作 | 说明 |
|------|------|------|
| KubernetesVpnSupport.java | 修改 | 添加信号卷、覆盖 command、添加 preStop |
| KubernetesTaskJobFactory.java | 修改 | ansible-runner 添加信号卷挂载和写入逻辑 |
| KubernetesVpnSupportTest.java | 修改 | 新增 4 个测试用例 |

## 技术方案
使用共享 emptyDir 卷 + 信号文件机制：
1. 添加 `vpn-signal` emptyDir 卷用于容器间通信
2. 覆盖 univpn 容器 command，使用包装脚本监控信号文件
3. ansible-runner 完成后写入 `.task-complete` 信号文件
4. univpn 收到信号后向 UniVPNCS 进程发送 `q` 命令断开 VPN
5. 添加 preStop 钩子作为兜底机制

## 归档日期
2026-05-30
