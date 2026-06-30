# Proposal: 同步仓库分支重复

## 需求背景

`/external/add-repo` 接口在传参包含 `branchName` 时，会在 `repo_branch` 表中创建两条相同的分支记录。根因是现有实现中存在两条路径同时写入分支：
1. `externalAddRepoBranchInfo` 方法：当 `branchName` 非空时，直接 `insertRepoBranch` 插入一条分支记录
2. `syncRepoBranchInfo` 方法：异步调用 `syncRepoBranch` 从平台 API 同步所有分支，也会包含该 `branchName`

## 功能描述

- 去除 `externalAddRepoBranchInfo` 中直接插入分支的逻辑，将规则集设置和 codecheck 触发逻辑移到 `syncRepoBranch` 完成后执行
- 在 `repo_branch` 表添加 `(repo_id, branch_name)` 唯一索引，从数据库层面防止重复分支
- 将 `insertRepoBranch` 和 `insertRepoBranchBatch` 改为 `INSERT IGNORE`，冲突时静默跳过
- 添加 Liquibase changelog 清理 `repo_branch` 表中已有的重复数据

## 验收标准

- [ ] `/external/add-repo` 接口传 `branchName` 时不再产生重复分支
- [ ] 规则集设置和 codecheck 触发功能正常
- [ ] 唯一索引和 INSERT IGNORE 从数据库层面防止任何入口的重复插入
- [ ] Liquibase 清理脚本可正确清除已有重复数据（保留 `create_at` 最早的一条）

## 影响范围

- `RepoServiceImpl.java`：`externalAddRepoInfo` 方法、`syncRepoBranchInfo` 方法、新增 `setupDefaultRuleSetsAndTriggerCodecheck` 方法、删除 `externalAddRepoBranchInfo` 方法
- `RepoBranchInfoMapper.xml`：`insertRepoBranch` 和 `insertRepoBranchBatch` 改为 `INSERT IGNORE`
- `cleanup-duplicate-branch.xml`：新增 Liquibase changelog（清理重复数据 + 添加唯一索引）
- `db.changelog.xml`：引入新 changelog
