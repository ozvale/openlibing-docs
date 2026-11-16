# 34-privilege-escalation-remediation — 需求背景与验收标准

## 背景

提权专项检查发现命令注入与提权风险、路径/软链接校验缺失、镜像构建期压缩包投毒防护不足等 7 项问题：validatePath 仅做前缀校验未显式拒绝软链接、workspace 等下载路径直接拼入 shell 命令、已存在文件权限未复核、Dockerfile 两处 tar 解压未做 SUID/路径穿越/软链接条目预检等。

关联业务 Issue：openlibing/openlibing-anti-poison#34

## 需求范围

- 路径校验强化：canonical + 段边界校验，显式拒绝软链接与 workspace 越界
- 下载/覆盖写链路增加目标目录权限与软链接校验
- Dockerfile tar 解压前增加条目预检（拒绝 `../`、绝对路径、SUID、危险软链接）

## 验收标准

- [x] 提权专项检查问题已整改，已随业务 PR openlibing/openlibing-anti-poison#139 交付（safe_202611 分支）

## 风险

路径与解压策略收紧可能影响既有下载/构建流程，需回归验证。
