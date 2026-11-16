# 35-security-findings-remediation — 实现任务

## 进度: 0/6 complete

- [ ] Task 1: 命令执行全面迁移 ProcessBuilder 参数数组 / SecureCmdExecutor，字段白名单（FIND-01）
- [ ] Task 2: 差异文件复制路径穿越修复：normalize + 边界校验 + 落盘文件名服务端重生成（FIND-02）
- [ ] Task 3: ExecCmdUtil/JGitUtil 命令执行与凭据处理重构（FIND-03/04）
- [ ] Task 4: SSRF 域名白名单 + 内网 IP 校验；actuator shutdown 移除/关闭（FIND-06/08）
- [ ] Task 5: 密钥从镜像剥离改 KMS/Secret 挂载并轮换；构建制品完整性校验（FIND-13/14）
- [ ] Task 6: Quick Wins：HMAC 密钥、路径校验、SQL stdout 日志、fastjson2 参数、start.sh、Swagger、tableName 白名单（FIND-05/07/09~12/15/16）
