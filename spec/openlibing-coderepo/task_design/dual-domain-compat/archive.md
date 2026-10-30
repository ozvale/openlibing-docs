# Archive：【黄蓝协同】GitCode 与 AtomGit 双域名兼容（openlibing-coderepo 黄蓝协同 PrSync 链路）

- FE 需求名称：【黄蓝协同】GitCode 与 AtomGit 双域名兼容
- 业务 Issue：openlibing/openlibing-coderepo#259（https://gitcode.com/openlibing/openlibing-coderepo/issues/259，issue_state=已完成）
- 业务 PR：openlibing/openlibing-coderepo!281（https://gitcode.com/openlibing/openlibing-coderepo/merge_requests/281）
  - 分支：`fix/dev` → `release_20261029_iter2`
  - 已合入：2026-10-29（approved + lgtm + CI 通过）
- 同主题关联：openlibing/openlibing-coderepo#234（SIG 仓库同步链路跨域名幂等）
- 归档时间：2026-10-30

## 交付内容

1. **`PrSyncEventHandler` 跨域名归一**：token 反查前按 `RepoCoordinateResolver` 平台坐标兜底反查，命中已录入仓库时将 `prInfo.repoUrl` 归一为录入域名——atomgit.com 录入 + gitcode.com payload 回传（及反向）的 PR 同步事件不再被静默丢弃。
2. **`PrSyncPushEventHandler` 口径确认**：保持既有 `9c3bdeff` 坐标兜底实现对齐 `PushEventHandler`，无新增改动。
3. **测试补齐**：跨域名两个方向的单测覆盖；顺带修复 `MergeRequestEventHandlerTest` 残留引用导致的编译失败。

## 关键决策记录

- 归一插入点选在「去重锁之后、token 反查之前」：去重 key 不受域名影响（owner/repo/platform 坐标天然一致），归一只需覆盖 token 反查及之后的落库/消息链路。
- 反查未命中**保持 payload 原样**（不静默改写、不阻断）：保持原有 token 侧报错行为，避免把真正未录入的仓库伪装成录入仓库。
- 复用 `RepoCoordinateResolver` 而非新建解析逻辑：与 `MergeRequestEventHandler` / `PushEventHandler` 的既有修复模式保持一致，降低维护成本。

## 可复用经验

- 双域名（gitcode.com / atomgit.com）场景下，**任何按 repoUrl 全串精确匹配的反查都存在跨域名失配风险**——新增按 URL 匹配的逻辑时应默认接入 `RepoCoordinateResolver` 坐标兜底。
- 归一原则：命中录入仓库才改写，未命中保持原样并走原报错链路——兼容性修复不放宽认证口径。
- 同类问题历史修复轨迹：`MergeRequestEventHandler` / `PushEventHandler`（早期）→ `PrSyncPushEventHandler`（`9c3bdeff`）→ `PrSyncEventHandler`（本需求），均已收敛。

## 遗留事项

- 每条 repoUrl 非空的 PR 同步事件都经 `resolveByCoordinate` 执行至少一次 DB 查询（快路径精确匹配），跨域名（快路径未命中）追加一次慢路径坐标兜底查询且无缓存；若跨域名录入占比显著上升，可在 `RepoCoordinateResolver` 内评估加短 TTL 缓存。
