# docker-isolation-peers — 归档

## 关联

- 业务仓：`hidevlab-transport-service`
- 业务分支：`feat/container-interconnection`
- 业务合并：`!184 merge feat/container-interconnection into master`（commit `9d3216db5afafa70a1a210ca0e756b7e5d3629af`）
- 接口文档：`hidevlab-transport-service/docs/docker-isolation-peers-api.md`
- docs PR：`spec/hidevlab-transport-service/docker-isolation-peers`（本归档分支）

## 交付历程

| #   | Commit                                                                                  | 说明                                                                                                                                                                 |
| --- | --------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | `b830f76c435259e58ac89c04c5e1c6d12c0dbbb2` / `c2a7a64301db057a4667b50aa5724205e135064a` | feat(isolation): add default network isolation + peer allow/deny script — `network_peer.sh` 三动作 + `apply_network_isolation` 接入 restore                          |
| 2   | `2b3c53573b1c0a5eccbe681c941f1e28aeb349aa`                                              | feat(isolation): rewrite peers API to call network_peer.sh across hosts — `transport.py` 路由 + `update_isolation_peers_batch` / `update_isolation_peers_multi_host` |
| 3   | `75a58d440d52dde19fca3dbd97f5270a28a12f50`                                              | feat(isolation): persist allowed_peers across container restart — `peers/<容器名>.list` 持久化 + restore 回灌                                                        |
| 4   | `c4d37aaaadc80eba38608f3545ae3db1c9cd495e`                                              | feat(isolation): return per-container live/persist results with reasons — `PEER_RESULT` 输出契约 + per-container 结果                                                |
| 5   | `c0d1f850c3269617a9a6770476ce99fb14da9e1f`                                              | fix(isolation): make deny idempotent for absent peers — deny 幂等                                                                                                    |
| 6   | `576944a8c4ee5abddca175a3deeaef413b953df7`                                              | feat(isolation): log entry/400-reason/outcome for /docker/isolation/peers — 三段日志 + 400 定位                                                                      |
| 7   | `c7c1e18c075b1646ce0c344474c44295650d919e`                                              | fix(isolation): network_peer deny 走 persist_del + restore 加 IPv4 校验 + set -u 参数兜底                                                                            |
| 8   | `8ec884e086c10c1297f02f9dd8b54a3170b131ac`                                              | fix(isolation): peers API 兼容旧 failed_containers + 全量失败 500 + 摘要类型归一                                                                                     |
| 9   | `67f988107bb8f3c72f36d550e0e59224e65c85f9`                                              | fix(isolation): failed_containers 改 live-based 口径 + 全量硬失败 500 解耦 + containers 元素类型防护                                                                 |
| 10  | `3f55173f60066fdf40232f93abc5fd8272f096c2`                                              | feat(isolation): network_peer 加 per-container flock + 容器删除清理锁文件                                                                                            |
| 11  | `ce551805bb71b217c407474e94222d1453446d0b`                                              | fix(isolation): network_peer flock touch 预检 + 去 exec 持久静音 stderr                                                                                              |
| 12  | `e9cbd3dbcb2cd35d8cfee6227fc727c5d20c31f7`                                              | fix(isolation): share_storage 字段 isinstance 兜底 + validate_path 路径校验                                                                                          |

合并提交：`9d3216db5afafa70a1a210ca0e756b7e5d3629af`（`!184 merge feat/container-interconnection into master`）。

## 最终验证

- `POST /docker/isolation/peers` 接受 JSON 数组（多物理机 + 容器 + peer_ips），多机并行 ≤10、机内串行 ✅
- 兼容旧版单对象入参（自动包成单元素数组）✅
- 每容器返回 `{ip, name, live, persist, status, reason}`，`status` 由 `live`+`persist` 派生 ✅
- `allow`/`deny` 同步维护 `peers/<容器名>.list`；容器重启后 `apply_network_isolation` 调 `restore` 回灌 ✅
- 容器未运行时 `live=false, persist=true, status=partial_success` ✅
- `deny` 对不在集合的 IP 幂等（视为成功）✅
- 全量硬失败（所有 `status=failure`）返 500；存在任一非 failure 返 200 ✅
- 响应保留 `failed_containers`（live 未成功子集）+ `failed`（计数）兼容旧调用方 ✅
- per-container `flock` 串行化同容器 allow/deny/restore ✅
- 容器删除清理 `peers/<容器名>.list` 与 `/var/lock/network_peer/<容器名>.lock` ✅
- 容器名/peer IP/share 路径经 `CommandSecurity` 校验 + `shlex.quote` 转义 ✅

## 设计偏差与取舍

- **两通道模型 vs 单布尔**：设计初版用单布尔「放通成功/失败」表征，落地时拆为 `live`+`persist` 双通道。原因：容器未运行场景单布尔无法表达「持久化已落盘、重启后生效」的语义，调用方无法区分「当次未生效需重试」与「持久化已兜底」。拆分后 `partial_success` 不返 500，避免无益重试。
- **`failed_containers` 口径**：初版用「status=failure 子集」，后改为「live 未成功子集」（含 partial_success 中 persist 已落盘的项）。原因：旧调用方读 `failed_containers` 判「当次放通是否生效」，对旧契约而言 partial_success 的 live 未放通即需关注；新调用方按 per-container `live/status` 精确处理。过渡期双契约。
- **`flock touch 预检**：`exec 9>"$LOCK_FILE"`在非交互 bash 下重定向失败会静默退出（无`PEER_RESULT`），`update_isolation_peers_batch`会误判为脚本异常。落地时加`touch`预检 + 失败即`emit_result failure` 兜底。
- **`share_storage` 字段 isinstance 兜底**：初版 `c.get("share_storage") or {}` 只兜 `None`，未兜 str 真值（如调用方误传 `"path"` 字符串），`.get("path")` 会抛 `AttributeError` 致整请求 500。落地时改为 `isinstance(_ss, dict)` 兜底。
- **`_parse_peer_result` 不臆测**：脚本异常退出无 `PEER_RESULT` 时，不按退出码 0 臆测 `live/persist=true`，统一判 `failure` + `_parse_peer_failure_reason` 兜底取原因行。

## 可复用经验

- **跨机批量 SSH 操作的并发模型**：多机 `ThreadPoolExecutor(max_workers=min(len(hosts),10))` 并行 + 机内串行 + 每机一条 SSH 连接复用，是 transport 侧跨机批量操作的通用范式（`update_isolation_peers_multi_host` 与 `async_docker_multi_create` 一致）。主机级失败展开为该机每容器一条 `failure`，避免调用方特判占位名。**前置约束**：调用前须保证 `hosts` 非空（`max_workers=0` 会抛 `ValueError`），transport.py 入口已校验空数组返 400；复用该范式时须保留非空前置校验，或改为 `max(1, min(len(hosts),10))`。
- **两通道拆分（live + persist）**：当实时操作可能因目标未就绪（容器未运行/依赖缺失）而失败、但有持久化兜底时，拆为 live+persist 双布尔 + 派生 status，比单布尔更精确，能让调用方区分「当次未生效需重试」与「持久化已兜底」。适用于任何「实时操作 + 持久化兜底 + 重启回灌」的场景。
- **`PEER_RESULT` 末行输出契约**：shell 脚本末行输出结构化 `KEY=VAL` 行（`live=... persist=... status=... reason=...`），Python 侧正则解析，比按退出码 + 多行文本猜测原因更稳健。脚本异常退出无标记时按退出码兜底判 failure，不臆测成功。
- **per-container `flock` 串行化（同机）**：当脚本读写 per-container 文件（`peers/<容器名>.list`）+ 操作 per-container 资源（ipset）时，用 `/var/lock/<namespace>/<容器名>.lock`（fd N, `flock -w <timeout>`）串行化，比全局锁并发度高，比无锁安全。`touch` 预检锁文件可创建防非交互 bash 重定向失败静默退出。**边界**：`/var/lock` 是 host-local，**仅同机互斥、不跨机**；若受保护文件在共享存储（如 gluster 上的 `.list`），跨机并发仍可能后写覆盖前写，需调用方按容器名去重或把锁文件置于同一共享存储。
- **`deny` 幂等语义**：对集合操作（ipset/file list），「期望态达成即成功」比「实际发生改动即成功」更友好调用方——`add -exist` 与 `del absent-as-success` 对称，调用方重试不会因已达成态而误报失败。
- **`share_storage` 字段类型归一**：调用方传 `share_storage` 字段时可能误传 str/None/dict 三种类型，`isinstance(_ss, dict)` 兜底比 `or {}` 更稳，避免 `.get` 抛 `AttributeError` 致整请求 500。适用于所有「调用方传嵌套 dict 字段」的场景。
- **全量硬失败 500 + 部分成功 200**：批量操作的 HTTP 状态码语义——所有项 `failure` 才返 500 触发上游重试；存在任一非 failure（含 partial_success）返 200，由调用方按 per-item status 处理。避免「容器未运行」等无益重试场景拖垮上游。**使用约束**：HTTP 200 仅表示请求被受理，`allow`/`deny` 是否实时生效须读 per-container `live`；`deny` 在 `partial_success`（容器未运行）下通路仍开放，需调用方重试或等待重启 `restore`，不能仅凭 200 判定已生效（fail-open 风险）。

## 归档日期

2026-11-05
