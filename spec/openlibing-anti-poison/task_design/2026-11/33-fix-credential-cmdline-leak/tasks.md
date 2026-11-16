# 33-fix-credential-cmdline-leak — 实现任务

## 进度: 3/3 complete

- [x] Task 1: 梳理所有 git/curl 命令拼接凭据的调用点
- [x] Task 2: git 改用 JGit 凭据 provider 或安全注入方式，curl 改用 header/netrc 传递凭据
- [x] Task 3: 验证进程命令行（ps/proc cmdline）不再包含 token 明文
