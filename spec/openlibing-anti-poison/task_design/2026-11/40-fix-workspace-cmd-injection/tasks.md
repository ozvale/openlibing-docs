# 40-fix-workspace-cmd-injection — 实现任务

## 进度: 3/3 complete

- [x] Task 1: scanPRFile 命令改参数化执行，去除 /bin/sh -c 对用户可控字段的解析
- [x] Task 2: workspace 等字段增加白名单校验，补齐 `..`/空格/制表符拦截
- [x] Task 3: 对 repoName/rulesName 等 DB 来源字段补充校验，回归 PR 扫描流程
