# univpn-graceful-disconnect

## 需求背景
当前 env-deploy-core 的 Ansible 任务 Pod 中，univpn sidecar 容器在 VPN 连接成功后持续运行，直到 Pod 被清理（TTL 默认 3600 秒）才释放 VPN 连接。这导致 VPN 隧道被不必要地占用，影响其他任务的资源使用。

## 功能描述
在 Pod 执行完所有 Ansible 任务后，主动释放 univpn 连接。通过共享卷信号机制，让 ansible-runner 容器在任务完成后通知 univpn 容器断开 VPN 连接。

## 验收标准
- [ ] ansible-runner 完成任务后，univpn 容器能在 5 秒内检测到信号并断开 VPN
- [ ] VPN 断开后，univpn 容器正常退出（exit code 0）
- [ ] Pod 终止时（兜底场景），preStop 钩子也能正确断开 VPN
- [ ] 不影响现有的 VPN 连接建立流程
- [ ] 单元测试覆盖新增逻辑

## 影响范围
- `KubernetesVpnSupport.java` - VPN sidecar 容器构建逻辑
- `KubernetesTaskJobFactory.java` - Job 构建逻辑
- 相关测试文件
