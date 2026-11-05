# docker-isolation-peers — 技术设计

## 方案概述

在 `transport.py` 新增 `POST /docker/isolation/peers` 异步路由，请求体为按物理机分组的数组，每台物理机含若干容器与对端 IP 列表。视图函数完成鉴权、入参校验与脱敏摘要后，调 `service/docker_manager.py` 模块级 `update_isolation_peers_multi_host`：每机一条 SSH 连接（独立 `DockerManager` 实例，线程安全），机内串行调 `DockerManager.update_isolation_peers_batch`，机间 `ThreadPoolExecutor(max_workers≤10)` 并行。`update_isolation_peers_batch` 逐容器 `shlex.quote` 拼参后 `bash network_peer.sh <allow|deny> <name> <ip1,ip2,...>`，解析脚本末行 `PEER_RESULT` 取 `live/persist/status/reason`，汇总每容器结果返回。

`network_peer.sh` 是点对点放通/删除/恢复脚本，采用 **两通道模型**：

- **persist 通道**：无条件维护 `<脚本目录>/peers/<容器名>.list`（`allow` 幂等去重 / `deny` 整行精确移除 / 删空自动 rm）。文件随共享存储持久化，是 peer 规则的**唯一事实源**。
- **live 通道**：尽力而为操作容器 netns 内 `allowed_peers` ipset（`nsenter -t <PID> -n ipset add/del`）。容器未运行 / 依赖缺失（nsenter/ipset）/ 未配置隔离（无 `allowed_peers` ipset）时 `live=false`（含未尝试），不阻断 persist 通道。
- **派生 status**：`full_success`（均 true）/ `partial_success`（仅一 true）/ `failure`（均 false）。只要一通道 true 即 `exit 0`；均 false `exit 1`。
- **重启回灌**：`network_peer.sh restore <容器名>` 由 `lib_container.sh::apply_network_isolation` 在创建/重启容器时调用，按 `peers/<容器名>.list` 逐行回灌 ipset。容器未运行时 restore 跳过（无 netns 可回灌）。
- **per-container `flock`**：`/var/lock/network_peer/<容器名>.lock`（fd 9, `flock -w 120`）串行化同容器的 allow/deny/restore，防 `peers/<容器名>.list` 读-改-写丢更新与 ipset 竞态。

## 架构决策

| 决策点 | 选择 | 原因 |
|--------|------|------|
| 接口形态 | 单接口 `POST /docker/isolation/peers`，action 字段区分 add/remove | 双向互通需两端各调一次，单接口支持数组批量降低跨机双向放通的墙钟时间；分两个接口（add/delete）会双倍 SSH 连接 |
| 并发模型 | 多机并行（`ThreadPoolExecutor` ≤10）+ 机内串行 | 同机容器共享一条 SSH 连接（连接复用），串行避免 ipset/文件锁竞态；跨机并行降低 A↔B 双向放通的墙钟时间 |
| 两通道拆分 | live + persist 独立取布尔，status 派生 | 容器未运行时仍可落盘（重启后 restore 回灌），不丢规则；调用方可按 per-container status 精确处理，不全成功也不全失败 |
| 持久化事实源 | `peers/<容器名>.list`（每行一个 IPv4） | 共享存储随物理机持久化；纯文本便于排查；`restore` 逐行回灌幂等（`ipset add -exist`） |
| 重启回灌入口 | `apply_network_isolation` 内调 `restore` | 创建/重启容器时 netns 新建，此时 `allowed_peers` 仅含网关，正好按文件回灌历史放通 |
| `deny` 幂等语义 | IP 不在集合视为成功（与 `allow` 的 `add -exist` 对称） | 期望态达成即成功，避免调用方重试时误报失败 |
| 全量硬失败 500 | 所有容器 `status=failure` 才返 500 | SSH 不可达等硬失败值得上游重试；`partial_success`（容器未运行）重试无益，持久化已兜底 |
| 兼容旧出参 | 保留 `failed_containers`（live 未成功子集）+ `failed`（计数） | 旧调用方读 `failed_containers` 判失败，新调用方按 per-container `live/status` 精确处理；过渡期双契约 |
| 兼容旧入参 | 单对象自动包成单元素数组 | 旧 CBB 单机调用无需改入参即可升级到新接口 |
| `flock` 粒度 | per-container（`/var/lock/network_peer/<容器名>.lock`） | 串行化同容器的 allow/deny/restore，不影响其他容器并发；锁随进程退出自动释放 |
| 脚本位置 | `{share_path}/share/docker_config/network_peer.sh`（共享存储） | 多机共享一份脚本，部署/升级一致；`share_path` 缺省 `/data/gluster`，可按容器覆写 |

## 涉及文件

| 文件 | 操作 | 关键改动 |
|------|------|---------|
| `transport.py` | 新增路由 | `@APP.route("/docker/isolation/peers")` `docker_isolation_peers`：鉴权 → JSON 解析（兼容单对象）→ 逐机/逐容器校验（`host[idx]`/`containers[c_idx]` 定位）→ 脱敏摘要日志 → 调 `update_isolation_peers_multi_host` → 派生 `failed_containers`/`failed` → 全量硬失败 500 |
| `service/docker_manager.py` | 新增方法/函数 | `DockerManager.update_isolation_peers_batch`（机内串行，逐容器拼参+解析 `PEER_RESULT`）；`DockerManager._parse_peer_result`/`_parse_peer_failure_reason`（解析脚本输出）；模块级 `update_isolation_peers_multi_host`（多机 `ThreadPoolExecutor`） |
| `script/network_peer.sh` | 新增脚本 | `allow`/`deny`/`restore` 三动作；两通道模型 + `PEER_RESULT` 输出契约 + per-container `flock` + 持久化文件维护（幂等增删） |
| `script/lib_container.sh` | 修改 `apply_network_isolation` | 创建 `allowed_peers` ipset 后调 `bash network_peer.sh restore "$CONTAINER_NAME"` 回灌 |
| `script/resource_restart_container.sh` | 修改重启流程 | `apply_network_isolation` 失败即 `DEPLOY_FAILED`，回灌由该函数内部完成 |
| `script/resource_start_docker.sh` | 修改创建流程 | 同上 |
| `script/resource_delete_docker.sh` | 修改删除流程 | 容器删除后清理 `peers/<容器名>.list` 与 `/var/lock/network_peer/<容器名>.lock` |
| `docs/docker-isolation-peers-api.md` | 新增文档 | 接口契约（请求体/响应/`status` 派生/持久化文件格式/行为说明） |

## 方法签名

### `transport.py::docker_isolation_peers`

```python
@APP.route("/docker/isolation/peers", methods=["POST"])
def docker_isolation_peers():
    """批量更新容器 netns ipset allowed_peers，放通/移除跨任务容器 IP。
    请求体: JSON 数组，每元素一台物理机 {ip, username, password, action, containers:[{name, peer_ips, share_storage?}]}
    响应 data: {containers:[{ip,name,live,persist,status,reason}], failed_containers:[...], failed:N}
    HTTP: 全量硬失败(status=failure) 返 500 触发上游重试; partial_success 返 200.
    """
```

### `DockerManager.update_isolation_peers_batch`

```python
def update_isolation_peers_batch(self, host_ip, username, pwd, containers, action):
    """调用 network_peer.sh 批量放通/移除容器 allowed_peers，返回每容器结果(含成功)。
    Args:
        containers: list of {name, container_ip, peer_ips, [share_storage.path]}
        action: "add" 放通 / "remove" 移除
    Returns:
        list of per-container results [{name, live, persist, status, reason}]，含全部容器(成功+失败)。
    """
```

### `update_isolation_peers_multi_host`（模块级）

```python
def update_isolation_peers_multi_host(hosts):
    """多物理机批量放通/移除容器 allowed_peers，跨机并行、机内串行。
    每台物理机开一次 SSH 连接（独立 DockerManager 实例，线程安全），
    多机间 ThreadPoolExecutor(max_workers=min(len(hosts),10)) 并行。
    Returns:
        list of per-container results [{ip, name, live, persist, status, reason}]，含全部容器(成功+失败)。
    """
```

## 调用链

```
上游(CBB ContainerIsolationSPI)
  └─ POST /docker/isolation/peers  [JSON 数组: 多物理机 + 容器 + peer_ips]
     │
     ├─ transport.py::docker_isolation_peers
     │    ├─ auth_filter (401 if invalid)
     │    ├─ JSON 解析 (兼容单对象 → 单元素数组)
     │    ├─ 逐机/逐容器校验 (400 if host[idx]/containers[c_idx] 非法)
     │    ├─ 脱敏摘要日志 (ip/action/容器数/peer_ip 总数, 不含 password)
     │    └─ update_isolation_peers_multi_host(data)
     │
     └─ service/docker_manager.py::update_isolation_peers_multi_host
          └─ ThreadPoolExecutor(max_workers≤10) per host:
               ├─ DockerManager.connect(ip, username, pwd)
               │    └─ SSH 失败 → 展开为该机每容器一条 failure (status=failure)
               ├─ DockerManager.update_isolation_peers_batch(ip, username, pwd, containers, action)
               │    └─ per container (机内串行):
               │         ├─ CommandSecurity.validate_container_name / validate_ip / validate_path
               │         ├─ 拼参: bash {shlex.quote(script_path)} {allow|deny} {shlex.quote(name)} {shlex.quote(ip_list)}
               │         ├─ exec_command_check_status(cmd)
               │         ├─ _parse_peer_result(output) → (live, persist, status, reason)
               │         │    └─ 无 PEER_RESULT → failure + _parse_peer_failure_reason 兜底
               │         └─ results.append({name, live, persist, status, reason})
               └─ DockerManager.close()  (finally)
          └─ 汇总: entry["ip"] = ip; all_results.extend
     │
     └─ transport.py: 派生 failed_containers=[r for r in results if not r.get("live")]
        ├─ 全量 status=failure → 500 "all containers failed"
        └─ 否则 → 200 {containers, failed_containers, failed}
```

## network_peer.sh 输出契约

脚本末行输出（allow/deny）：

```
PEER_RESULT: live=<true|false> persist=<true|false> status=<full_success|partial_success|failure> reason=<text>
```

| live | persist | status | exit |
|------|---------|--------|------|
| true | true | `full_success` | 0 |
| true | false | `partial_success` | 0 |
| false | true | `partial_success` | 0 |
| false | false | `failure` | 1 |

`live=false` 含未尝试：容器未运行 / 依赖缺失（nsenter/ipset）/ 未配置隔离（无 `allowed_peers` ipset）。`reason` 写明失败通道、具体 IP、未尝试原因与重启影响。

## 持久化文件格式

`{share}/share/docker_config/peers/<容器名>.list`，纯文本、每行一个 IPv4、UTF-8/LF：

- 每行一个 IP，无逗号/无引号
- `#` 及其后为注释，被 `restore` 忽略
- 空行/空白行跳过；`allow` 幂等去重，`deny` 整行精确移除；删空后文件自动删除
- `restore` 逐行 IPv4 格式校验（跳过被污染/手改的非法行），`nsenter ipset add -exist allowed_peers` 回灌

## 安全

- **命令注入防护**：容器名经 `CommandSecurity.validate_container_name`（Docker 命名规范）；peer IP 经 `validate_ip`（合法 IPv4）；share 路径经 `validate_path`（防 `..` 遍历/空字节/特殊字符）。`share_storage` 字段做 `isinstance(_ss, dict)` 兜底（防 str 真值绕过 `.get`）。
- **shell 转义**：`script_path`/`name`/`ip_list` 拼参前均 `shlex.quote`。
- **鉴权**：`auth_filter.auth_filter(Authorization)` 校验 dynamic token。
- **摘要日志脱敏**：`summary` 只含 `ip/action/容器数/peer_ip 总数`，不含 `password`；逐机/逐容器校验失败时日志只写 `ip`，不写凭证。
- **flock 预检**：`exec 9>"$LOCK_FILE"` 前先 `touch` 验证可创建，防非交互 bash 静默退出（无 `PEER_RESULT`）。

## 错误处理

| 失败场景 | HTTP | 处理 |
|---------|------|------|
| 鉴权失败 | 401 | `auth_filter` 拦截 |
| 请求体非非空 JSON 数组 / host 字段缺失 / containers 非非空数组 / action 非法 | 400 | 错误信息定位到 `host[idx]` / `host[idx] containers[c_idx]` |
| 单容器 `network_peer.sh` 异常退出（无 `PEER_RESULT`） | 200 | 该容器 `status=failure`，`reason` 取 `_parse_peer_failure_reason`；不阻断同机其他容器 |
| 主机级 SSH 失败 / 异常 | 200 | 展开为该机每容器一条 `failure`（同 reason）；不返 500（除非全部 failure） |
| 全量硬失败（所有容器 `status=failure`） | 500 | 触发上游重试 |
| 未预期异常 | 500 | `str(e)` |

## 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| 容器未运行时 `live=false`，调用方误判失败 | 派生 `status=partial_success`（persist 已落盘），`reason` 显式说明「仅持久化落盘; 重启后由 restore 按持久化对账」；响应保留 `failed_containers` 兼容旧调用方 |
| `network_peer.sh` 异常退出无 `PEER_RESULT` | `_parse_peer_result` 返回 `None` 时按退出码兜底判 `failure`，不臆测 `live/persist=true`；`_parse_peer_failure_reason` 取首个 `错误:/失败:/FAIL` 行 |
| 并发同容器 allow/deny/restore 竞态 | per-container `flock -w 120`；`touch` 预检锁文件可创建防非交互 bash 静默退出 |
| `peers/<容器名>.list` 被手改污染 | `restore` 逐行 IPv4 格式校验跳过非法行；`allow` 幂等去重；`deny` 整行精确移除 |
| `share_storage.path` 路径穿越 | `CommandSecurity.validate_path` 校验 + `shlex.quote`；`isinstance(_ss, dict)` 兜底非 dict 真值 |
| 跨机双向放通漏调一端 | 由调用方（CBB `ContainerIsolationSPI`）保证 A 放 B 且 B 放 A；transport 仅执行单方向，不臆测双向 |
| 容器删除后 `peers/<容器名>.list` 残留 | `resource_delete_docker.sh` 容器删除后清理持久化文件与 `flock` 锁文件 |

## 跨仓影响

- **CBB（resource-schedule-cbb 等）**：`ContainerIsolationSPI` 实现调用本接口，负责双向互通语义（A↔B 两端各调一次）。
- **transport 既有 `/docker/block/add`、`/docker/block/delete`**：不冲突，二者面向「按网段隔离 docker0」粗粒度场景；本接口面向「指定对端容器 IP 的细粒度放通」，可并存。
- **`hidevlab-hid-agent`**：不涉及，本接口全程经 SSH 操作宿主机 `nsenter`/`ipset`，不调 host Agent。
