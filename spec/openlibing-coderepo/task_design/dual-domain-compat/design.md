# Design：GitCode 与 AtomGit 双域名兼容（openlibing-coderepo 黄蓝协同 PrSync 链路）

关联：proposal.md（同目录）、业务 Issue openlibing/openlibing-coderepo#259、业务 PR !281（fix/dev → release_20261029_iter2）。

## 1. 方案设计

复用同仓老 handler（`MergeRequestEventHandler` / `PushEventHandler`）已落地的 `RepoCoordinateResolver` 坐标反查模式，对 PrSync 链路对齐：

- **问题本质**：payload 回传的 repoUrl 域名（gitcode.com / atomgit.com 恒定其一）与用户录入 `repo_info.repo_url` 的域名可能不同，而下游 token 反查（`PrAccessTokenService#getValidAccessToken`）按 URL 全串精确匹配，跨域名必然失配。
- **解决思路**：在 token 反查**之前**插入一次「坐标归一」——先按 URL 全串精确匹配，未命中时按平台坐标（owner/repo + platform）兜底反查一次已录入仓库；命中则把 `prInfo.repoUrl` 归一为录入域名，未命中保持 payload 原样（由 token 反查侧按原逻辑报错，不静默改写）。
- `PrSyncPushEventHandler` 已由更早的 `9c3bdeff` 完成同类兜底，本需求仅对齐 `PrSyncEventHandler` 并补齐双向单测。

## 2. 实现逻辑设计

`PrSyncEventHandler#processWebhookEvent` 中，位于去重锁之后、token 反查之前：

1. `resolveRegisteredRepoUrl(prInfo)`：
   - `prInfo.repoUrl` 为空直接返回；
   - `repoCoordinateResolver.resolveByCoordinate(repoUrl)` 按坐标（owner/repo/platform）反查已录入仓库；
   - 反查命中（非空列表）且首行 `repo_url` 非空 → `prInfo.repoUrl = 录入域名 repoUrl`；
   - 反查未命中 → 保持 payload 原样（后续 token 反查按原逻辑报 `No valid access token`，不静默改写）。
2. 归一后的 `prInfo.repoUrl` 随后贯穿：token 反查、`gitee_pr_info` 落库、MQ 消息体、流水线记录——下游全部使用录入域名口径。

## 3. 类设计

| 类                             | 变更                                                                                              |
| ------------------------------ | ------------------------------------------------------------------------------------------------- |
| `PrSyncEventHandler`           | +`resolveRegisteredRepoUrl(PrInfo)` 私有方法；注入 `RepoCoordinateResolver`；token 反查前调用归一 |
| `RepoCoordinateResolver`       | 复用既有组件（老 handler 同款），无改动                                                           |
| `PrSyncEventHandlerTest`       | +2 个跨域名方向用例（atomgit 录入 + gitcode payload、反向）                                       |
| `MergeRequestEventHandlerTest` | 修复残留 `repoInfoMapper` 引用导致的编译失败（顺带）                                              |
| `PrSyncPushEventHandler`       | 无改动（已有 `9c3bdeff` 坐标兜底，口径对齐确认）                                                  |

## 4. 数据模型设计

无表结构变更。归一仅发生在运行时内存（`prInfo.repoUrl`），不回写 `repo_info`。

## 5. 性能设计

- 坐标反查仅在**全串精确匹配未命中**（跨域名）时触发一次 DB 查询；同域名正常路径零额外开销。
- 反查结果未做缓存（单事件单次查询，量级可控）；如后续跨域名仓库占比显著，可评估在 `RepoCoordinateResolver` 内加短 TTL 缓存。

## 6. API 接口设计

无对外接口变化。影响的是既有 webhook → MQS 内部链路的事件存活率（跨域名仓库的 PR / push 事件从「静默丢弃」变为「正常同步」），MQS 消息协议不变。

## 7. 安全设计

- 归一只使用已录入仓库的 `repo_url` 原值，不拼接、不改写用户输入的新 URL，无注入面。
- 反查未命中时保持原错误行为（token 侧报错），不因兼容性放宽认证口径。
- 单测覆盖「未命中不静默改写」的负向断言。
