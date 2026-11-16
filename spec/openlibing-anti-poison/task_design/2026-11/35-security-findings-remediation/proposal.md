# 35-security-findings-remediation — 需求背景与验收标准

## 背景

对照《安全威胁分析报告》（2026-09-02）复核，16 项安全发现（FIND-01~16）均未整改。核心场景：PR 差异文件下载/扫描链路 Shell 命令注入（RCE）、PR 差异文件复制路径穿越（任意文件写）、ExecCmdUtil 数组参数被 join 回字符串执行、Actuator shutdown 端点暴露。

关联业务 Issue：openlibing/openlibing-anti-poison#35

## 需求范围

- 严重项：命令执行迁移 ProcessBuilder 参数数组、路径穿越修复、ExecCmdUtil/JGitUtil 重构、SSRF 白名单、密钥剥离与制品完整性校验（FIND-01~04/08/13/14）
- 高危项：关闭 actuator shutdown、服务内统一鉴权与 userId 服务端化（FIND-05/06）
- Quick Wins：HMAC 密钥、路径校验、SQL 日志、fastjson2 参数、start.sh、Swagger、tableName 白名单（FIND-07/09~12/15/16）

## 验收标准

- [ ] 16 项安全发现全部闭环并复测通过；本 issue 当前仍为 open 状态，待逐项勾选验收（部分整改已随业务 PR openlibing/openlibing-anti-poison#139 交付）

## 风险

涉及面广（命令执行/鉴权/配置/构建），需分优先级推进并充分回归。
