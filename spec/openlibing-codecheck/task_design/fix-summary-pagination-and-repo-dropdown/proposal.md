# fix-summary-pagination-and-repo-dropdown

## 需求背景

codecheck 仓概览接口存在两个问题：

1. **分页入参无限制**：`/codecheck/inc/v1/task/result/summary` 和 `/codecheck/full/task/result/summary` 接口的分页参数（pageNum、pageSize）没有任何校验，攻击者可传入超大 pageSize 导致单次查询返回大量数据，引发 OOM 或慢查询；传入负数、0 等非法值时缺少防护，可能导致计算异常。

2. **下拉框仓库列表缺失**：`/summary/project/repo` 接口返回的仓库下拉框中，部分实际存在的仓库未显示。经排查，根因为 MongoDB 聚合 `$group` + `$first("repoId")` 没有前置 `$sort`，当同一仓库存在新旧 repoId（仓库重新注册场景）时，`$first` 可能取到旧 repoId，导致 `existingRepoIds` 白名单过滤失败。

关联业务 Issue: https://gitcode.com/openlibing/openlibing-codecheck/issues/134

## 功能描述

### 做什么

1. 为 `QuerySummaryModel` 的 `pageNum` 和 `pageSize` 字段添加 Jakarta Validation 校验注解（`@NotNull` + `@Range`），在 Controller 层通过 `@Valid` 触发校验。
2. 在 `SelectionOperaton.getCodeCheckProjectsDeFromDB` 的 MongoDB 聚合管道中，`$group` 前添加 `$sort` 按 `executeTime` 降序排列，确保 `$first("repoId")` 取到最新文档的 repoId。

### 不做什么

- 不修改 MongoDB 持久化结构。
- 不修改 `repo_info` 表 schema。
- 不修改分页参数的默认值逻辑（仅做入参边界校验）。
- 不修改其他接口的分页校验逻辑（如 `QueryDetailModel` 已有的 `inputCheck` 方法）。

## 验收标准

- [ ] `/codecheck/inc/v1/task/result/summary` 接口：pageNum 为空时返回 4010103 + "查询页码不能为空"
- [ ] `/codecheck/inc/v1/task/result/summary` 接口：pageNum < 1 时返回 4010103 + "查询页码不能小于1"
- [ ] `/codecheck/inc/v1/task/result/summary` 接口：pageSize > 5000 时返回 4010103 + "每页查询大小范围为1-5000"
- [ ] `/codecheck/full/task/result/summary` 接口：同样适用上述校验规则
- [ ] `/summary/project/repo` 接口：重新注册过的仓库（如 openlibing-cicd-test）能正常出现在下拉框中
- [ ] 正常分页参数（pageNum=1, pageSize=20）的请求不受影响

## 影响范围

- 仓库：openlibing-codecheck
- 模块：概览查询（CheckboardController、QuerySummaryModel）、下拉框（SelectionOperaton）
- 接口：
  - `POST /codecheck/inc/v1/task/result/summary`
  - `POST /codecheck/full/task/result/summary`
  - `POST /summary/project/repo`
- 无数据库 schema 变化
- 无外部接口契约变化（仅增加入参校验拦截）
