# 31-fix-command-injection — 需求背景与验收标准

## 背景

SENINFO 安全扫描发现服务存在恶意代码执行与系统命令注入风险（命令字符串拼接执行相关），与 #33/#34/#35/#40 所述命令执行链路问题同源，需一并整改。Issue 详情见 openlibing/openlibing-anti-poison#31。

关联业务 Issue：openlibing/openlibing-anti-poison#31

## 需求范围

- 排查并整改命令拼接执行链路中的恶意代码执行/注入风险
- 与 #33（凭据命令行泄露）、#40（workspace 命令注入）整改协同推进

## 验收标准

- [x] 命令注入风险已整改，已随业务 PR openlibing/openlibing-anti-poison#139 交付（safe_202611 分支）

## 风险

命令执行链路改造涉及扫描核心流程，需回归验证扫描功能。
