# SSH链路安全加固

## 需求背景

消除 openlibing-simulation 服务当前 SSH 调用链路中的安全隐患：

- **ECS 中间节点私钥明文存储**：物理机私钥以明文形式落在 ECS 本地，存在泄露风险
- **UBScore 密码明文传输**：接口返回物理机密码时明文传输，存在被截获风险
- **QEMU 镜像耦合 OE**：QEMU 仿真镜像与 OE 侧耦合，部署灵活性差

来源：蓝区安全合规整改。

## 功能描述

### 做什么

1. **双层 SSH 加密链路（隧道转发）**
   - CCE 容器通过 SSH 隧道转发安全连接实验室物理机
   - 物理机私钥从 Apollo 加密获取，运行时仅内存解密，禁止落盘

2. **Host key 渐进式信任机制**
   - 首次连接自动 ssh-keyscan 获取 host key 并入库
   - 后续连接严格校验（StrictHostKeyChecking=yes），防中间人攻击

3. **密码加密传输**
   - 接口返回物理机密码时对称加密传输
   - UBScore 流水线使用时解密

4. **自定义 qcow 镜像**
   - QEMU 任务支持自定义 qcow 文件，替代默认 OE 镜像

### 不做什么

- 不修改 QEMU 任务执行的核心仿真逻辑
- 不改变代理节点（proxy）与实验室物理机的既有网络拓扑
- 不实现 UBScore 侧解密逻辑（外部系统，仅约定加解密算法与密钥）

## 验收标准

- [ ] CCE 容器通过双层 SSH 隧道连接实验室物理机成功
- [ ] 物理机私钥从 Apollo 加密获取，运行时内存解密，无明文落盘
- [ ] 首次连接自动获取 host key，后续连接严格校验（StrictHostKeyChecking=yes）
- [ ] 接口返回物理机密码为对称加密密文，非明文
- [ ] QEMU 任务支持自定义 qcow 文件并正常启动仿真
- [ ] 端口转发本地端口越界（<10000 或 >65535）时拒绝并断开连接
- [ ] Host key 变更时连接拒绝，防止中间人攻击

## 影响范围

### 核心模块

- `JschUtil`（SSH 隧道/私钥解密/host key 管理/端口校验）
- `QemuTaskServiceImpl`（私钥解密调用、qcow 校验与上传、凭据接口）
- `QemuTaskController`（`/env/credential` 凭据接口）
- `AesGcmUtil`（AES-256-CBC 密码加密传输）

### 外部依赖

- ECS 中间节点需配置 `AllowTcpForwarding yes`
- CCE 容器镜像需安装 openssh-client（提供 ssh-keyscan 命令）
- UBScore 项目需配合约定对称加解密算法和密钥

### 数据影响

- `known_hosts` 文件（`/etc/openlibing/known_hosts`，容器内持久化 host key）
- Apollo 配置：`privateKey.to.proxy.node`、`privateKey.to.user.node`、`security.part1`、`security.aesgcm.key`（均为加密存储）

## 参考方案

- 系统设计详见：`system_design/SSH端口转发与主机密钥管理系统设计.md`
- 私钥获取：Apollo 密文配置 → 运行时解密为 byte[] → JSch addIdentity → 用后清零
- Host key：`ssh-keyscan -H -t ed25519,rsa` 获取 → `known_hosts` O_APPEND 原子追加（0600）
- 密码加密：AES-256-CBC，`Base64(IV):Base64(ciphertext)`，与容器内 openssl 解密互通
