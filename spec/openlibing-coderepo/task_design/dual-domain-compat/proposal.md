# Proposal：【黄蓝协同】GitCode 与 AtomGit 双域名兼容

## 需求背景

atomgit.com 与 gitcode.com 同属 GitCode 平台双域名。用户录入 `repo_info.repo_url` 时域名不确定，而平台 webhook payload 回传域名也因入口不同而异（恒定其一）。黄蓝协同 PrSync 链路按 payload repoUrl **URL 全串精确匹配**反查仓库与 access token，跨域名录入时匹配失配：

- `PrSyncEventHandler`：token 反查失败打 error 后直接 return，**PR 同步事件被静默丢弃**；
- `PrSyncPushEventHandler`：跨域名录入的仓库曾被判为"未注册"，push 同步事件被跳过（已由 `9c3bdeff` 坐标兜底覆盖）。

同仓老 handler（`MergeRequestEventHandler` / `PushEventHandler`）此前已通过 `RepoCoordinateResolver` 坐标反查修复同类问题，PrSync 系列需对齐。

- FE 需求名称：【黄蓝协同】GitCode 与 AtomGit 双域名兼容
- 业务 Issue：openlibing/openlibing-coderepo#259（https://gitcode.com/openlibing/openlibing-coderepo/issues/259）
- 业务 PR：openlibing-coderepo !281（https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/281，fix/dev → release_20261029_iter2，已合入）
- 同主题关联：openlibing/openlibing-coderepo#234（SIG 仓库同步链路的跨域名幂等）

## 范围

仅涉及 openlibing-coderepo 单仓黄蓝协同 PrSync 链路：

1. `PrSyncEventHandler`：token 反查前按平台坐标（`RepoCoordinateResolver`）将 repoUrl 归一为录入域名，跨域名场景不再失配；
2. `PrSyncPushEventHandler`：注册仓库反查与 repoUrl 处理保持坐标兜底口径（对齐 `PushEventHandler`，此前已覆盖）；
3. 补充跨域名（atomgit.com 录入 + gitcode.com payload 回传，及反向）单元测试。

## 验收标准

- [x] 同一仓库 atomgit.com 录入 + gitcode.com payload 回传（及反向）时，PR / push 同步事件均正常触发
- [x] 坐标反查未命中时保持原有报错行为，不静默改写 repoUrl
- [x] 跨域名单测覆盖两个方向（handler 相关 45 个用例全部通过）
