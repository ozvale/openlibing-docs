# Proposal：【黄蓝协同】黄蓝协同新增映射实时校验及失败信息展示功能（openlibing-coderepo 侧）

## 需求背景

- 内部服务（及外部调用方）需要根据完整 git 仓库地址获取该仓库在托管平台上的实时分支列表，用于校验仓库/分支是否存在；此前仅有按 repoId 查询的入口，且对「仓库不存在 / 平台仓库已删除 / 令牌失效 / 无分支」等场景无区分提示。
- 实际使用中发现两类问题：
  1. webhook 订阅的评论事件（gitee/gitcode Note Hook、github issue_comment）已无消费场景（评论事件处理器随黄蓝协同 PR 管理下线一并移除），持续接收造成无谓的事件投递；
  2. 同一 PR 源分支多次 push 时，30 分钟去重窗口内的后续 push 不会重新触发流水线，与「每次 push 都应重跑」的预期不符。

- FE 需求名称：【黄蓝协同】黄蓝协同新增映射实时校验及失败信息展示功能
- 业务 Issue：openlibing/openlibing-coderepo#140（https://gitcode.com/openlibing/openlibing-coderepo/issues/140）
- 业务 PR：openlibing-coderepo !196（https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/196，sync-repo → release_20260923_iter2）

## 范围

仅涉及 openlibing-coderepo 单仓：

1. 新增按完整 git 仓库地址查询托管平台实时分支列表接口 `GET /project-repo/query-repo-branch-by-url`（网关层鉴权，内部服务调用）。
2. 录入代码仓创建 webhook 时取消评论事件订阅（gitee/gitcode `note_events=false`、github events 移除 `issue_comment`）。
3. PR 源分支更新改为 commit 粒度去重（每次 push 均重新触发流水线）。

## 验收标准

- [x] 按 repoUrl 查询分支：未录入（`repo not found`）/ 平台 404（`repo not found on <platform> (HTTP 404)`）/ token 无效（`access token invalid or unauthorized`）/ 无分支（`repo has no branches`）分别返回对应提示
- [x] 新录入仓库的 webhook 不含评论事件订阅（gitee/gitcode/github 三平台），push / merge_requests 订阅保持不变，存量 webhook 不受影响
- [x] 同一 PR 源分支多次 push（不同 commit）均重新触发；同 commit 重复投递被去重；消息 req_type 保持 `open` 与黄区消费端兼容
- [x] 入参格式校验：编码态地址（`http%3A` 开头）、含空白字符、非 http(s) 前缀直接返回参数错误
- [x] 单元测试覆盖以上场景；CI pre-commit 门禁通过
