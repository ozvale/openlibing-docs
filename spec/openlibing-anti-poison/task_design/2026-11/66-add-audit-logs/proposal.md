# 66-add-audit-logs — 需求背景与验收标准

## 背景

antipoison 多个敏感操作接口无审计日志记录，无法追溯操作人与操作行为，涉及 10 个接口：/checkRule/del/rule/set、/checkRule/update/taskRule、/releaseposion/poisonScan、/poison-pr/sca-pr、/poison-version/scan-version、/shield/audit-pr-revoke、/shield/poisonApply、/shield/poison-pr-apply、/shield/problem-pr-audit、/shield/shield-pr-rederral。

关联业务 Issue：openlibing/openlibing-anti-poison#66

## 需求范围

- 为上述 10 个接口补充审计日志记录（操作人、操作类型、目标资源、操作结果）

## 验收标准

- [x] 10 个接口的操作均有审计日志落库、可追溯（已随业务 PR openlibing/openlibing-anti-poison#139 交付）

## 风险

无。
