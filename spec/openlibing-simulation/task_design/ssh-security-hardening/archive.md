# SSH链路安全加固 — 归档

## 归档信息

| 项目        | 内容                                  |
| ----------- | ------------------------------------- |
| FE 需求名称 | SSH链路安全加固                       |
| 业务 Issue  | openlibing/openlibing-simulation#18   |
| 业务 PR     | openlibing/openlibing-simulation #139 |
| 开发分支    | ligao_verfy_ssh（保留）               |
| 归档日期    | 2026-08-13                            |

## 实现总结

### 功能概述

完成 SSH 链路全链路安全加固，覆盖双层隧道建立、私钥密文管理、主机密钥信任、节点密码加密传输、自定义 qcow 校验五类场景，并附带 OBS 数据定时上报与多轮安全整改。

### 核心改动

1. **双层 SSH 隧道**：`JschUtil.TunnelSession` 封装 proxy + target 双层连接，端口转发复用执行多条命令，关闭时释放全部 Identity 缩短私钥驻留窗口
2. **私钥安全**：Apollo 密文 → 运行时内存解密为 byte[] → `addIdentity` → finally `Arrays.fill` 清零；接口返回密码经 `AesGcmUtil`（AES-256-CBC）二次加密
3. **Host key 渐进式信任**：首连 `ssh-keyscan` 抓取（ed25519/rsa）→ `appendToKnownHosts`（O_APPEND + 0600），`StrictHostKeyChecking=yes`
4. **日志脱敏**：`SensitiveDataConverter`（logback 转换器）私钥/密码/Token/IP 自动脱敏
5. **附加整改**：scene 字段白名单校验（`^[A-Za-z0-9_-]+$`）、移除硬编码 internal token、distributed lock 超时调优、OBS 每日 1 点定时采集

### 验收情况

- 用户 gamma/自测环境验证通过，Issue #18 各场景实测可用
- PR #139 已合并，CI 流水线通过（ci-pipeline-passed / approved / lgtm）
- pre-commit 全量 hooks Passed（detect-secrets / check-xml / check-yaml 等）

### 关联文档

- 需求分析: `proposal.md`
- 详细设计: `design.md`
- 实现核对: `tasks.md`
