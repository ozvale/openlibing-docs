## Why

漏洞公告的仓库输入当前是一个 textarea，用户需要用逗号分隔手动输入仓库名，无法指定分支、无法追踪每行的独立发布状态、无法展示每行的发布地址和失败原因。随着后端接口升级为返回行级状态的对象数组，前端需要将仓库输入改造为可编辑表格，支持行内编辑、新增、删除，并展示每行的异步发布结果。

## What Changes

- 将漏洞公告区域的"仓库"textarea 替换为可编辑表格（6列：仓库名称、分支名、发布结果、发布地址、失败原因、操作）
- 新增 `vulnRepoTable` 子组件，管理行级编辑状态（editingIndex/editingBackup）
- 表格支持新增行（直接进入编辑态）、行内编辑（仅一行可编辑，编辑按钮切换为保存/取消）、删除行
- 只有 `pushStatus === 3`（发布失败）或 `null`（新增行）的行可进入编辑态
- `pushStatus === 5`（发布成功）的行展示 `<a>` 发布地址链接，整行锁定不可操作
- `pushStatus === 0/1/4`（待发布/执行中/发布中）的行仓库名/分支名禁用，操作列按钮禁用
- 后端返回 `repoStatusList`（对象数组，每行有 `id`），前端回填为 `VulnRepoItem[]`
- 提交接口 `repos` 参数从 `string[]` 改为 `{repoName: branchName}` object
- 轮询刷新合并逻辑：编辑行完全不动，非编辑行按 `id` 匹配整行覆盖
- 公告级状态（legend statusIcon、isVulnFormDisabled）保持不变
- 新增行时 repo 名称可以重复，无需校验唯一性

## Capabilities

### New Capabilities
- `vuln-repo-table`: 漏洞公告仓库可编辑表格组件，包含行级编辑/新增/删除、行级状态展示、轮询合并逻辑

### Modified Capabilities
<!-- 无现有 spec 需要修改 -->

## Impact

- **前端代码**: `reviewDetail.vue`（模板+脚本改造）、新增 `vulnRepoTable.vue` 子组件、`config.ts`（新增 pushStatusConfig）
- **API 交互**: `triggerVulnerabilityBulletin` 请求参数 `repos` 从 `string[]` 改为 `{repo: branch}` object；`getPublishReviewDetailById` 返回 `repoStatusList` 替代原 `repos` string[]
- **数据结构**: `VulnRepoItem` 新类型（id, repo, branch, pushStatus, pushStatusName, repoUrl, failReason）
- **轮询逻辑**: `getDetailData` 回填逻辑从 string[] 改为 repoStatusList[]，新增 mergeRepoList 合并函数
