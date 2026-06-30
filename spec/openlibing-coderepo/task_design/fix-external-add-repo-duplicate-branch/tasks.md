# fix-external-add-repo-duplicate-branch — 实现任务

## 进度: 4/4 complete

- [x] Task 1: 去除 `externalAddRepoBranchInfo` 方法调用及方法体，将规则集/codecheck 逻辑移到 `syncRepoBranch` 完成后执行
- [x] Task 2: 在 `repo_branch` 表添加 `(repo_id, branch_name)` 唯一索引
- [x] Task 3: 将 `insertRepoBranch` 和 `insertRepoBranchBatch` 改为 `INSERT IGNORE`
- [x] Task 4: 新增 Liquibase changelog 清理 `repo_branch` 表重复数据
