# docker-isolation-peers

## 需求背景

HiDevLab DevEnv 容器默认开启网络隔离（`apply_network_isolation`）：在容器 netns 内用 iptables+ipset `allowed_peers` 把容器出入站收紧到「仅网关 + 白名单 IP」，同子网互访全部 DROP。该机制保护多租户隔离，但阻断了合法的跨容器协作场景：

- 分布式训练 / 多容器联调：A 容器需直连 B 容器的 IP 做 RPC、SSH、数据交换
- 跨物理机容器互通：A、B 容器可能漂移到不同物理机，仍需点对点放通
- 容器重启后规则丢失：netns 重建后 ipset 仅含网关，原放通规则全部丢失，需要重新放通

既有的 `/docker/block/add`、`/docker/block/delete` 接口面向「按网段隔离 docker0」的粗粒度场景（glusterfs 共享存储 + 整段 DROP），无法做到「指定对端容器 IP 的细粒度放通/移除」，也没有跨物理机批量、跨重启持久化的能力。

## 功能描述

新增 `POST /docker/isolation/peers` 接口，对 DevEnv 容器 `allowed_peers` ipset 做批量点对点放通/移除：

1. **跨物理机批量**：请求体为按物理机分组的数组，一次调用可跨多台物理机批量放通/移除；多机间线程池并行（≤10）、机内串行，每台物理机一条 SSH 连接复用，逐容器调用 `network_peer.sh`。
2. **两通道模型**：每容器结果拆为 `live`（容器 netns 实时 ipset）与 `persist`（`peers/<容器名>.list` 持久化文件）两个布尔，`status` 由二者派生（`full_success` / `partial_success` / `failure`）。
3. **跨重启持久化**：`allow`/`deny` 同步维护 `{share}/share/docker_config/peers/<容器名>.list`；容器重启后 `resource_restart_container.sh` 的 `apply_network_isolation` 调 `network_peer.sh restore` 按文件回灌，实现 peer 规则跨重启恢复。
4. **容器未运行兜底**：`allow`/`deny` 在容器未运行时仅落盘（`live=false, persist=true, status=partial_success`），重启后由 `restore` 回灌生效。
5. **双向互通**：A↔B 需两端各自放通对端 IP（A 放 B 的 IP 且 B 放 A 的 IP），由调用方（CBB 的 `ContainerIsolationSPI`）保证。
6. **兼容旧版入参/出参**：自动把单对象入参包成单元素数组；响应保留 `failed_containers`/`failed` 旧键供老调用方读，新调用方按 per-container `live`/`status` 处理。
7. **全量硬失败 500**：所有容器两通道均败（如 SSH 不可达）才返 500 触发上游重试；`partial_success`（如容器未运行）不返 500（重试无益，持久化已兜底）。

## 验收标准

- [ ] `POST /docker/isolation/peers` 接受 JSON 数组（每元素一台物理机），逐机 SSH + 机内串行调 `network_peer.sh`
- [ ] 兼容旧版单对象入参：自动包成单元素数组
- [ ] 请求体非法（非数组、空数组、host 字段缺失、containers 非非空数组、action 非 add/remove）返 400，错误信息能定位到 `host[idx]`
- [ ] 鉴权失败返 401；未预期异常返 500
- [ ] 每容器返回 `{ip, name, live, persist, status, reason}`，`status` 由 `live`+`persist` 派生
- [ ] `allow`/`deny` 无条件维护 `peers/<容器名>.list`；`allow` 幂等去重，`deny` 整行精确移除；删空后文件自动删除
- [ ] 容器未运行时 `allow`/`deny` 仅落盘，`live=false, persist=true, status=partial_success`
- [ ] 容器重启后 `apply_network_isolation` 调 `network_peer.sh restore` 按持久化文件回灌 `allowed_peers`
- [ ] `deny` 对不在集合中的 IP 幂等（视为成功，与 `allow` 的 `add -exist` 对称）
- [ ] 单容器失败不中断同机其他容器；主机级失败（SSH 连不上/异常）展开为该机每容器一条 `failure`
- [ ] 全量硬失败（所有容器 `status=failure`）返 500 触发上游重试；存在任一非 `failure` 则返 200
- [ ] 响应保留 `failed_containers`（live 未成功子集，兼容旧调用方）与 `failed`（计数）
- [ ] 所有容器名/peer IP/share 路径经 `CommandSecurity` 校验，命令拼参用 `shlex.quote` 转义
- [ ] `network_peer.sh` per-container `flock` 串行化同容器的 allow/deny/restore，防 `peers/<容器名>.list` 读-改-写丢更新与 ipset 竞态
- [ ] 容器删除流程清理 `peers/<容器名>.list` 持久化文件与 `/var/lock/network_peer/<容器名>.lock` 锁文件

## 影响范围

| 文件 | 操作 | 说明 |
|------|------|------|
| `transport.py` | 新增 | `@APP.route("/docker/isolation/peers")` 视图函数；校验、摘要日志、调用 `update_isolation_peers_multi_host` |
| `service/docker_manager.py` | 新增 | `DockerManager.update_isolation_peers_batch`（机内串行）+ `_parse_peer_result`/`_parse_peer_failure_reason`；模块级 `update_isolation_peers_multi_host`（多机并行 `ThreadPoolExecutor`） |
| `script/network_peer.sh` | 新增 | 点对点放通/删除/恢复脚本；两通道模型 + `PEER_RESULT` 输出契约 + per-container `flock` |
| `script/lib_container.sh` | 修改 | `apply_network_isolation` 创建 `allowed_peers` ipset 后调 `network_peer.sh restore` 回灌 |
| `script/resource_restart_container.sh` | 修改 | 重启流程在 `apply_network_isolation` 后自动回灌 peer 规则 |
| `script/resource_start_docker.sh` | 修改 | 创建流程同上 |
| `script/resource_delete_docker.sh` | 修改 | 容器删除流程清理 `peers/<容器名>.list` 与 `flock` 锁文件 |
| `docs/docker-isolation-peers-api.md` | 新增 | 接口契约文档（请求体/响应/持久化文件格式/行为说明） |

**不修改的文件：**

- `transport.py` 其他路由 — 不影响 `/docker/block/add`、`/docker/block/delete` 等既有隔离接口
- `base/`、`utils/` — 复用既有 `CommandSecurity`、`auth_filter`、`Ssh`，无基础设施层改动
- 上游 CBB 的 `ContainerIsolationSPI` — 由调用方维护双向互通语义，transport 不负责

## 关联

- 业务 Issue / PR：`feat/container-interconnection` 需求分支，合并于 `!184 merge feat/container-interconnection into master`（commit `9d3216d`）
- 接口文档：`hidevlab-transport-service/docs/docker-isolation-peers-api.md`
- 系统设计参考：`openlibing-docs/spec/hidevlab-transport-service/system_design/Docker容器编排与传输代理系统设计.md` 第 5.3 节「容器网络隔离（block_add）」与第 6 节接口列表
