# Proposal：代码仓管理平台适配（github-gitcode-adaptation）

## 需求背景

代码仓管理模块对 GitHub / GitCode 平台的三项适配缺口：

1. **GitHub 默认分支无法落库**：GitHub 的默认分支是仓库级属性（仓库详情 API 的 `default_branch` 字段），而分支列表 API 返回项不含任何默认分支标记。现有默认分支落库链路从分支列表中找 `isDefault=true` 的分支，对 GitHub 恒为空，导致 GitHub 仓默认分支在列表、编辑弹窗中永远显示 `--`，机机接口也无法返回默认分支标记。
2. **GitHub 分支创建/删除无感知**：录入代码仓时自动创建的平台 webhook，对 GitHub 创建时仅订阅了 `pull_request` 与 `push` 两个事件（评论订阅 `issue_comment` 已随 branch-query-by-url 需求下线，创建时不携带；评论订阅下线前创建的存量 webhook 可能残留该订阅，残留投递因消费 handler 已删除而被分发器安全跳过），缺少 Branch or tag creation（`create`）与 Branch or tag deletion（`delete`）；且 GitHub 的分支增删走独立的 `create`/`delete` 事件（payload 结构与 push 不同），服务端也没有对应的消费 handler。平台侧新建/删除分支后，openLiBing 分支管理列表不会自动增删。
3. **GitCode 存量 webhook 刷新失败**：webhook 存量刷新调度任务无法为 GitCode webhook 勾选推送事件。经 GitCode 官方 API 实测确认根因：GitCode 平台已变更 `PATCH /api/v5/repos/{owner}/{repo}/hooks/{id}` 的入参校验，body 必须携带 `url` 字段（缺失返回 400 `'url': param is missing`），而服务端 PATCH 只发送 `{"push_events": true}`，导致补齐永远失败且每轮任务重复失败。

## 需求范围

- 需求 1：GitHub 分支查询客户端内部适配，回标分支列表的 `isDefault`，使 GitHub 仓默认分支与 gitcode/gitee 行为一致落库并展示。
- 需求 2：GitHub webhook 创建与存量刷新补齐 `create`/`delete` 事件订阅；新增事件消费 handler，实现平台侧分支增删的自动同步。
- 需求 3：GitCode webhook 刷新 PATCH body 修复（补传原回调地址）。

## 验收标准

1. GitHub 仓录入后（含保存触发的自动同步），列表「默认分支」列与编辑弹窗正确显示平台真实默认分支；机机接口 `query-repo-branch-by-url` 返回的分支列表中默认分支 `isDefault=true`。
2. GitHub 平台侧新建分支后，openLiBing 分支管理列表自动出现该分支；删除分支后自动移除；tag 的创建/删除不产生分支记录；同仓多项目录入全部同步。
3. 存量 GitHub webhook 经刷新调度任务 PATCH 后 events 在平台返回的既有 events 全集基础上包含 `push`/`create`/`delete`（全集基线并集补齐，不丢失人工勾选的其他事件，也不主动移除评论订阅下线前存量仓可能残留的 `issue_comment`）；新录入 GitHub 仓的 webhook 创建即携带正确事件集。
4. 存量 GitCode webhook 经刷新调度任务 PATCH 后「推送事件」勾选成功，任务日志无 400；已订阅齐全的 webhook 自动跳过。回调地址（url）为 null/空白的存量脏数据 webhook 不发 PATCH，计入跳过统计（不计 failed）且 warn 日志可区分「有意跳过」与「正常成功」；此类仓无法通过刷新恢复订阅，需在验收阶段依据跳过统计与 warn 日志识别后重建 webhook。
5. gitee/gitcode 平台既有录入、同步、分支管理、webhook 刷新行为回归不变。
6. 降级语义（三态可区分）：GitHub 仓库详情接口失败时，分支列表返回不受阻断（默认分支保持空，与现状一致）；GitCode webhook 刷新结果在任务日志中按「成功 / 有意跳过（已订阅齐全或 url 为空的脏数据，计入跳过统计）/ 失败（failed 计数 + 失败日志）」三态区分，不存在静默吞没。
7. 存量空数据回填：修复部署后，存量 GitHub 仓默认分支由下一次全量分支同步（含手动「同步仓库」）自然回填，无需数据迁移脚本。

## 涉及服务

| 服务                | 改动                                 |
| ------------------- | ------------------------------------ |
| openlibing-coderepo | 全部三项改动（唯一改动仓）           |
| openlibing-web      | 不涉及（默认分支展示走既有数据链路） |

## 跨仓影响

无外部接口契约变化。机机接口 `query-repo-branch-by-url` 与 webhook 接收接口 `/apig/webhook/github/repo` 为行为级增强（非契约变化），如有机机调用方依赖 GitHub 分支 `isDefault` 恒空语义需知会（当前无已知调用方依赖）。
