# 62-fix-credential-leak — 需求背景与验收标准

## 背景

`/action-pr/scan` 接口在日志中打印 prInfo，而构建 prInfo 时解密了密文存储的公共 accessToken 与 password 凭据，导致明文敏感信息进入日志，可被日志访问者利用进行仓库越权操作，构成敏感信息泄露风险。

关联业务 Issue：openlibing/openlibing-anti-poison#62

## 需求范围

- 移除/脱敏 prInfo 相关日志中的 accessToken、password 等敏感字段
- 确保解密后的凭据不再进入任何日志输出路径

## 验收标准

- [x] 日志中不再出现明文 accessToken/password（已随业务 PR openlibing/openlibing-anti-poison#139 交付）

## 风险

无。
