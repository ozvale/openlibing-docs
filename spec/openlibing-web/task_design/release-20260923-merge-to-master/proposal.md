# release-20260923-merge-to-master 提案

## 需求背景

openlibing-web 9月迭代二在 release_20260923 分支完成开发与验证，需整体合入 master 归档。本文档记录归档操作的范围、前置条件与验收标准。

- 业务 Issue：https://gitcode.com/openlibing/openlibing-web/issues/318
- 业务 PR（归档 PR）：https://gitcode.com/openlibing/openlibing-web/merge_requests/810
- 发布门禁报告：`release_docs/openlibing-web/release_20260923/b055355b/obweb_release_report.md`（经 openlibing-docs PR #1060 归档）

## 变更范围

release_20260923 相对 master 领先 138 个 commit，其中：

- **19 个已合并业务 PR**（target=release_20260923），全部带 `ci-pipeline-passed` 标签合入
- 关联 **17 个去重 Issue**，0 个 PR 无关联
- 覆盖发布管理、SBOM、代码检查、代码仓管理、漏洞管理、运营看板、UT 覆盖率等模块

## 验收标准

1. 归档 PR（release_20260923 → master）创建成功并关联 Issue #318（openlibing/openlibing-web#810）
2. 业务 PR 合入后 master 分支流水线通过
3. 发布门禁报告（PR #1060）与本 spec 一并归档至 openlibing-docs
