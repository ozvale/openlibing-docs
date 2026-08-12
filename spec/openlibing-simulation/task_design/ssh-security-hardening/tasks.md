# SSH链路安全加固 — 实现任务

## 进度: 7/7 complete

> 说明：用户确认当前分支代码即为完整版实现，本清单作为实现核对记录。

## 主场景实现核对

- [x] Task 1: 双层 SSH 隧道（proxy + target 端口转发）连接实验室物理机
  - `JschUtil.TunnelSession` / `createTunnel` / `connectProxySession` / `connectTargetSession`
- [x] Task 2: 私钥 Apollo 密文获取，运行时内存解密不落盘
  - `decryptKey` 内存解密为 byte[] → addIdentity → finally `Arrays.fill` 清零
  - `TunnelSession.close()` 调 `removeAllIdentity()` 释放 JSch 内部 Identity
- [x] Task 3: Host key 渐进式信任机制
  - `checkAndFetchHostKey(ViaProxy)`：首连 ssh-keyscan（ed25519,rsa）→ `appendToKnownHosts`（O_APPEND + 0600）
  - `StrictHostKeyChecking=yes` 统一配置
- [x] Task 4: 接口返回密码对称加密传输
  - `getEnvNodeCredential` → `buildCredential`：SecurityUtil 密文解密后经 `AesGcmUtil.encrypt`（AES-256-CBC）二次加密返回
- [x] Task 5: 自定义 qcow 镜像替代默认 OE
  - `validateQcow`（t_qcow_info 表校验）+ `uploadQcowAttachments` / `uploadQcowToNode` / `uploadSimulatorToServer` 上传链路

## 扩展场景实现核对

- [x] Task 6: 端口转发本地端口越界（<10000 或 >65535）拒绝并断开
  - `createTunnel` 端口范围校验 + `disconnectQuietly`
- [x] Task 7: 私钥/密码日志脱敏
  - `SensitiveDataConverter`（logback 脱敏，私钥 → [REDACTED]）

## 关联

- 业务 Issue: openlibing/openlibing-simulation#18
- 系统设计: `system_design/SSH端口转发与主机密钥管理系统设计.md`
