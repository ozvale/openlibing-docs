# Tasks：代码仓管理平台适配（github-gitcode-adaptation）

> 改动仓：openlibing-coderepo。特性分支建议名：`feat-github-gitcode-adaptation`（基于源仓 master 最新创建，分支名禁用斜杠）。

## 1. 需求 1：GitHub 默认分支回标

- [ ] `common/utils/Github` 新增 `getGithubRepoDefaultBranch(owner, repo, accessToken)`：GET /repos/{owner}/{repo} 解析 `default_branch`；失败路径（无响应/非 2xx/字段缺失/空白）warn 日志 + 返回 null，不抛异常
- [ ] `business/platform/branch/GithubBranchClient#listBranches` 尾部追加回标：分支列表非空时调用上述方法，非空返回则按 name 精确匹配置 `isDefault=true`；空列表短路不调仓库详情

## 2. 需求 2：GitHub 分支增删 webhook 同步

- [ ] `RepoServiceImpl#buildWebhookCreateBody` GitHub 分支 events 补齐为 `["pull_request", "push", "create", "delete"]`
- [ ] `RepoServiceImpl#buildGithubPushEventUpdateBody` events 补齐 create/delete（保留 pull_request / issue_comment / push），更新 javadoc
- [ ] `RepoServiceImpl#isPushEventSubscribed` GitHub 分支扩展为 push/create/delete 三事件齐备判定（gitee/gitcode 不变）
- [ ] 新增 `business/handler/GithubBranchChangeEventHandler`：`supportedEventTypes={"create","delete"}`；`ref_type=branch` 判定（tag 忽略）；`ref` 纯分支名解析；clone_url→html_url 候选反查（对齐 PushEventHandler 模式，按 repoId 去重）；逐行 `syncSingleBranch`，单仓失败隔离
- [ ] `updateDefaultBranchInfo` 相关 javadoc 补充 GitHub 回标来源说明（如有必要）

## 3. 需求 3：GitCode PATCH body 修复

- [ ] `RepoServiceImpl` 新增 `buildGitcodePushEventUpdateBody(RepoWebhook webhook)`：返回 `{"url": <webhook.getUrl()>, "push_events": true}`
- [ ] `RepoServiceImpl#updateRepoWebhookForPushEvent` gitcode 分支改调新方法；gitee 分支沿用 `buildGiteeGitcodePushEventUpdateBody` 不变

## 4. 单元测试

- [ ] `GithubBranchClient` 测试：仓库详情成功回标 / 详情失败降级（isDefault 保持空且不抛异常）/ 空分支列表短路 / 分支名未匹配保持原样
- [ ] `GithubBranchChangeEventHandler` 测试：create 建分支 / delete 删分支 / tag 事件忽略 / 未注册仓跳过 / 多项目录入全同步 / 单仓失败不中断 / payload 缺字段防御
- [ ] `RepoServiceImpl` 测试更新：GitHub webhook 创建 body 与刷新 PATCH body 含 create/delete 且保留原订阅；GitCode PATCH body 含 url + push_events；gitee PATCH body 保持 `{"push_events": true}`

## 5. 本地验证与 pre-commit

- [ ] `mvn` 编译通过 + 上述单测全部通过（遵循仓内既有单测命令约定）
- [ ] 对本次全部改动文件执行 `pre-commit run --files <改动文件>`，修复直到全部通过
- [ ] 暂不 commit，向用户报告分支名、修改文件清单（git status / git diff --stat）、验证结果

## 6. beta 部署验证（用户手动部署后配合验证）

- [ ] XXL-Job 手动触发 `refreshWebhookHandler`（先传 projectId/repoId 小范围）→ GitCode 仓 webhook 设置页「推送事件」勾选成功、任务日志无 400
- [ ] GitHub 存量仓 webhook events 含 push/create/delete；已齐备仓自动 skipped
- [ ] GitHub 平台侧新建/删除分支 → 分支管理列表自动增删；tag 创建/删除无分支记录
- [ ] 录入 GitHub 公共仓 → 列表/编辑弹窗默认分支正确显示；机机接口 `query-repo-branch-by-url` 返回 isDefault 标记
- [ ] gitee/gitcode 既有仓回归：录入、同步、分支管理、webhook 刷新行为不变
- [ ] 全量触发刷新任务补齐存量仓

## 7. 收尾

- [ ] 测试环境验证通过后：评论业务 issue 回填验证结论
- [ ] 推送特性分支到 fork 仓 → 创建业务 PR（关联 issue 完整 URL、ai-assisted 标签、评审人 ozvale、测试人沿用任务默认）
- [ ] docs PR（本 spec 目录）合入后确认 issue 状态
