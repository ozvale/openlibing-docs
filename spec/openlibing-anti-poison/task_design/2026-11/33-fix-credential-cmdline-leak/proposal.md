# 33-fix-credential-cmdline-leak — 需求背景与验收标准

## 背景

git clone / curl 通过 `Runtime.exec`/`ProcessBuilder` 以 `sh -c "git clone https://user:token@..."` 方式执行，Linux 下 `/proc/pid/cmdline`、`ps -ef` 会完整暴露命令参数，平台凭据处于「内存+命令行」双重暴露面，符合 SENS-01 明文凭据泄露形态。服务本身是代码安全扫描平台，运维权限可见即等于泄露平台化凭据。

关联业务 Issue：openlibing/openlibing-anti-poison#33

## 需求范围

- git 操作改用 JGit UsernamePasswordCredentialsProvider（复用 pullPr/pullGiteeVersion 现有实现）或 credential helper 临时注入且不落日志
- curl 改用 `--header PRIVATE-TOKEN` 或 `--netrc` 受限权限文件传递凭据
- 严禁将凭据拼入进程 argv

## 验收标准

- [x] 凭据不再出现在进程命令行，已随业务 PR openlibing/openlibing-anti-poison#139 交付（safe_202611 分支）

## 风险

凭据传递方式变更需验证 git clone / 文件下载链路功能正常。
