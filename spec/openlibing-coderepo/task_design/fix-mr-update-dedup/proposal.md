# Proposal: 修复 MergeRequestEventHandler 更新事件去重逻辑缺陷

## 需求背景

MergeRequestEventHandler 用于在代码提交（创建 PR 或在 PR 中提交代码）时检测提交代码中的三方检查工具告警抑制注释，并生成代码检视意见提示 committer。

当前实现存在两个逻辑缺陷，导致更新文件时可能创建大量重复的代码检视意见：

1. **更新原因检查条件反转**：第 110 行条件 `!"gitcode".equals(event.getRepoType())` 与注释"仅 GitCode 需要"矛盾，实际排除了 GitCode 平台，导致 GitCode 所有非代码变更的更新事件（标题修改、标签变更等）未被过滤，全部进入后续处理流程。同时，第 112 行检查的更新原因为 `source_branch_changed`（Gitee 值），而 GitCode 对应的有效更新原因应为 `source update`。

2. **非代码变更更新事件复用 CREATE key**：当 `hasActualCodeChange` 返回 false 时，更新事件的 Redis 去重 key 被设为与创建事件相同的 `...CREATE`。若原始 CREATE 锁已过期（30 分钟），非代码变更的更新事件会重新获取锁并执行全量扫描，为所有文件创建重复的代码检视意见。

## 验收标准

- [ ] GitCode 平台仅当 `update_reason` 为 `source update` 时才处理更新事件
- [ ] Gitee 平台仅当 `action_desc` 为 `source_branch_changed` 时才处理更新事件
- [ ] 非代码变更的更新事件不再复用 CREATE key，直接跳过处理
- [ ] 修复后不再出现因非代码变更触发的重复检视意见
- [ ] handle 方法不超过 50 行

## 影响范围

- 仓库：openlibing-coderepo
- 模块：MergeRequestEventHandler
- 平台：GitCode、Gitee
- 关联 Issue：openlibing/openlibing-coderepo#35
