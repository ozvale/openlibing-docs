# 40-fix-workspace-cmd-injection — 需求背景与验收标准

## 背景

argus 漏洞挖掘确认（CWE-78，高危）：scanPRFile 将 workspace/repoName/scanId 等字段直接拼入 Python 扫描命令并经 `/bin/sh -c` 执行；LinuxCommandInjectCheck 黑名单仅覆盖 16 个元字符，缺少 `..`、空格、制表符等，且 repoName/rulesName（DB 值）完全未校验，存在命令注入与路径遍历风险。

关联业务 Issue：openlibing/openlibing-anti-poison#40

## 需求范围

- 命令构建改参数化方式执行，避免 shell 解析用户可控字段
- 输入验证改白名单（仅允许字母/数字/下划线/连字符）
- 路径构建前做规范化 + 边界校验，拦截 `..` 等路径穿越

## 验收标准

- [x] 注入与路径遍历风险已整改，已随业务 PR openlibing/openlibing-anti-poison#139 交付（safe_202611 分支）

## 风险

扫描命令构建方式变更需回归 PR 门禁扫描全流程。
