# SSH链路安全加固 — 技术设计

## 方案概述

基于 JSch 实现双层 SSH 隧道（proxy + target 端口转发）安全连接实验室物理机；私钥经 Apollo 密文配置运行时内存解密、用后清零；host key 首次 ssh-keyscan 获取并入库、后续严格校验；节点密码经 AES-256-CBC 对称加密传输；QEMU 任务支持自定义 qcow 镜像。

详细设计见：`system_design/SSH端口转发与主机密钥管理系统设计.md`。

## 架构决策

| 决策 | 选择 | 原因 |
|------|------|------|
| SSH 库 | JSch（mwiede/jsch） | 现有依赖；ProxySSH 类不可用，采用 setPortForwardingL 端口转发 |
| 隧道封装 | `TunnelSession`（AutoCloseable） | 封装 proxy+target 双层连接与命令执行，close() 统一释放 |
| 私钥传递 | 内存 byte[] + addIdentity，finally `Arrays.fill` 清零 | 满足"禁止落盘"约束，缩短明文驻留窗口 |
| Host key 策略 | StrictHostKeyChecking=yes + 首次 keyscan 渐进信任 | 兼顾首连可用性与防 MITM |
| known_hosts 写入 | Files.write O_APPEND + 0600 | 避免并发丢失更新（read-modify-write 会丢） |
| 密码加密 | AES-256-CBC（AesGcmUtil），SHA-256 派生密钥 | 与容器内 openssl 解密互通（OpenSSL 不支持 AEAD） |
| 节点密码存储 | 库中 SecurityUtil 密文 + 接口二次 AES-CBC 加密返回 | 密码不落明文日志/响应 |
| 端口转发 | 本地端口 [10000, 65535] 范围校验 | 防止端口越界（扩展场景要求） |

## 涉及文件

| 文件 | 操作 | 说明 |
|------|------|------|
| `src/main/java/com/openlibing/simulation/utils/JschUtil.java` | 修改 | TunnelSession / createTunnel / connectProxySession / decryptKey（内存解密+清零）/ host key 管理 / 端口校验 / removeAllIdentity |
| `src/main/java/com/openlibing/simulation/utils/AesGcmUtil.java` | 修改 | AES-256-CBC 加解密（类名保留历史） |
| `src/main/java/com/openlibing/simulation/service/impl/QemuTaskServiceImpl.java` | 修改 | getEnvNodeCredential 二次加密返回、validateQcow、uploadQcowToNode、deployTask 后删除节点 aes.key |
| `src/main/java/com/openlibing/simulation/controller/QemuTaskController.java` | 修改 | `/simulation/qemu/auto/task/env/credential` 凭据接口 |
| `src/main/java/com/openlibing/simulation/entity/dto/QemuTaskConfigCreateDTO.java` | 修改 | qcowId/qcowName 入参（白名单校验） |
| `src/main/java/com/openlibing/simulation/constans/Constans.java` | 修改 | KNOWN_HOSTS_FILE 等常量 |
| `src/main/resources/application-{env}.yaml` | 修改 | Apollo 配置来源（私钥/part1/aesgcm.key） |
| `src/main/resources/db/changelog/v1.0.0/t_qcow_info.xml` | 新增 | qcow 镜像元数据表 |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 私钥明文残留内存 | decryptKey byte[] 用后 Arrays.fill 清零 + TunnelSession.close 调 removeAllIdentity |
| Host key 并发写入丢失 | per-host 锁（hostLockMap）+ O_APPEND 原子追加 |
| 端口转发冲突/越界 | 本地端口范围 [10000, 65535] 校验，越界断开连接 |
| 解密算法不兼容 | AesGcmUtil 与脚本侧 openssl 解密互通（CBC + SHA-256 派生） |
| 日志泄露密钥 | SensitiveDataConverter logback 脱敏（私钥→[REDACTED]） |

## 跨仓影响

- **UBScore**：约定对称加解密算法（AES-256-CBC）与密钥分发渠道，解密失败返回错误码感知
- **openlibing-common**：`SecurityUtil` 外部公共依赖（密钥派生逻辑不可控，故密码二次加密用 AesGcmUtil）
- **ECS 中间节点**：sshd 需配置 `AllowTcpForwarding yes`
- **CCE 容器镜像**：需安装 openssh-client（ssh-keyscan）
