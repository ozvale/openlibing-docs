# docker-isolation-peers — 实现任务

## 进度: 12/12 complete

合并于 `!184 merge feat/container-interconnection into master`（commit `9d3216db5afafa70a1a210ca0e756b7e5d3629af`）。

### Task 1: 新增点对点放通/删除/恢复脚本 + 默认网络隔离接入

- [x] `script/network_peer.sh` 新增 `allow`/`deny`/`restore` 三动作脚本（两通道模型 + `PEER_RESULT` 输出契约 + 持久化文件维护）
- [x] `script/lib_container.sh::apply_network_isolation` 创建 `allowed_peers` ipset 后调 `network_peer.sh restore` 回灌
- [x] `script/resource_start_docker.sh` / `resource_restart_container.sh` 接入 `apply_network_isolation`
- Commit: `b830f76c435259e58ac89c04c5e1c6d12c0dbbb2` / `c2a7a64301db057a4667b50aa5724205e135064a`（`feat(isolation): add default network isolation + peer allow/deny script`）

### Task 2: 重写 peers API 调 network_peer.sh 跨机批量

- [x] `transport.py` 新增 `@APP.route("/docker/isolation/peers")` 视图函数
- [x] `service/docker_manager.py` 新增 `DockerManager.update_isolation_peers_batch`（机内串行）+ 模块级 `update_isolation_peers_multi_host`（多机 `ThreadPoolExecutor` ≤10 并行）
- [x] 逐容器 `shlex.quote` 拼参 + `_parse_peer_result` 解析 `PEER_RESULT`
- Commit: `2b3c53573b1c0a5eccbe681c941f1e28aeb349aa`（`feat(isolation): rewrite peers API to call network_peer.sh across hosts`）

### Task 3: peer 规则跨重启持久化

- [x] `network_peer.sh` allow/deny 维护 `peers/<容器名>.list`（幂等增删）
- [x] `restore` 逐行回灌 ipset
- Commit: `75a58d440d52dde19fca3dbd97f5270a28a12f50`（`feat(isolation): persist allowed_peers across container restart`）

### Task 4: 每容器返回 live/persist 结果与 reason

- [x] `network_peer.sh` 末行输出 `PEER_RESULT: live=... persist=... status=... reason=...`
- [x] `update_isolation_peers_batch` 解析后返回 per-container 结果
- Commit: `c4d37aaaadc80eba38608f3545ae3db1c9cd495e`（`feat(isolation): return per-container live/persist results with reasons`）

### Task 5: deny 对缺失 peer 幂等

- [x] `network_peer.sh` deny 分支：IP 不在集合视为成功（与 allow 的 `add -exist` 对称）
- Commit: `c0d1f850c3269617a9a6770476ce99fb14da9e1f`（`fix(isolation): make deny idempotent for absent peers`）

### Task 6: 接口入口/400 原因/结果日志

- [x] `docker_isolation_peers` 加 `enter`/`proceed`/`done` 三段日志
- [x] 400 失败日志定位到 `host[idx]` / `host[idx] containers[c_idx]`
- Commit: `576944a8c4ee5abddca175a3deeaef413b953df7`（`feat(isolation): log entry/400-reason/outcome for /docker/isolation/peers`）

### Task 7: network_peer.sh deny 走 persist_del + restore IPv4 校验 + set -u 兜底

- [x] `persist_del` 用 `grep -vxF` + `mv` 整行精确移除，删空自动 rm
- [x] `restore` 逐行 IPv4 格式校验跳过非法行
- [x] `set -uo pipefail` + 参数空兜底
- Commit: `c7c1e18c075b1646ce0c344474c44295650d919e`（`fix(isolation): network_peer deny 走 persist_del + restore 加 IPv4 校验 + set -u 参数兜底`）

### Task 8: peers API 兼容 failed_containers + 全量失败 500 + 摘要类型归一

- [x] 响应保留 `failed_containers`（live 未成功子集）+ `failed`（计数）兼容旧调用方
- [x] 全量 `status=failure` 返 500 触发上游重试
- [x] 脱敏摘要 `share_storage` 字段 `isinstance` 归一
- Commit: `8ec884e086c10c1297f02f9dd8b54a3170b131ac`（`fix(isolation): peers API 兼容旧 failed_containers + 全量失败 500 + 摘要类型归一`）

### Task 9: failed_containers 改 live-based 口径 + containers 元素类型防护

- [x] `failed_containers` 从「status=failure 子集」改为「live 未成功子集」（含容器未运行/依赖缺失/ipset 失败，含 persist 已落盘的 partial_success）
- [x] `update_isolation_peers_batch` 逐容器 `isinstance(c, dict)` 防护，非 dict 元素记 failure 不阻断同机其他容器
- Commit: `67f988107bb8f3c72f36d550e0e59224e65c85f9`（`fix(isolation): failed_containers 改 live-based 口径 + 全量硬失败 500 解耦 + containers 元素类型防护`）

### Task 10: network_peer.sh 加 per-container flock + 容器删除清理锁文件

- [x] `/var/lock/network_peer/<容器名>.lock`（fd 9, `flock -w 120`）串行化同容器 allow/deny/restore
- [x] `resource_delete_docker.sh` 容器删除后清理 `peers/<容器名>.list` 与 `flock` 锁文件
- Commit: `3f55173f60066fdf40232f93abc5fd8272f096c2`（`feat(isolation): network_peer 加 per-container flock + 容器删除清理锁文件`）

### Task 11: network_peer.sh flock touch 预检 + exec 持久静音 stderr

- [x] `exec 9>"$LOCK_FILE"` 前 `touch` 预检可创建，防非交互 bash 静默退出无 `PEER_RESULT`
- [x] `ipset create -exist` 等 `2>/dev/null` 静音无关 stderr
- Commit: `ce551805bb71b217c407474e94222d1453446d0b`（`fix(isolation): network_peer flock touch 预检 + 去 exec 持久静音 stderr`）

### Task 12: share_storage 字段 isinstance 兜底 + validate_path 路径校验

- [x] `update_isolation_peers_batch` 对 `c.get("share_storage")` 做 `isinstance(_ss, dict)` 兜底（防 str 真值绕过 `.get`）
- [x] `CommandSecurity.validate_path(share_path)` 防 `..` 遍历/空字节/特殊字符
- Commit: `e9cbd3dbcb2cd35d8cfee6227fc727c5d20c31f7`（`fix(isolation): share_storage 字段 isinstance 兜底 + validate_path 路径校验`）

## 验证

- `py_compile` / `bash -n network_peer.sh` 语法通过
- 多机批量放通：跨物理机数组一次调用，机间并行、机内串行，per-container 结果含成功+失败
- 容器未运行兜底：`allow`/`deny` 仅落盘，`live=false, persist=true, status=partial_success`
- 跨重启持久化：容器重启后 `apply_network_isolation` 调 `restore` 按 `peers/<容器名>.list` 回灌 ipset
- deny 幂等：对不在集合的 IP 视为成功
- 全量硬失败 500：所有容器 `status=failure` 返 500；存在任一非 failure 返 200
- 兼容旧入参：单对象自动包成单元素数组
- 兼容旧出参：`failed_containers`/`failed` 旧键可读
- per-container flock：并发同容器 allow/deny/restore 串行化，`peers/<容器名>.list` 读-改-写不丢更新
- 容器删除清理：`peers/<容器名>.list` 与 `/var/lock/network_peer/<容器名>.lock` 随容器删除清理
- 命令注入防护：容器名/peer IP/share 路径均经 `CommandSecurity` 校验 + `shlex.quote` 转义
