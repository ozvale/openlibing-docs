# GitHub 加速 IP-Pinning 设计（transport + worker 集中式）

> 针对 OpenLibing DevEnv 容器内 git clone/push 加速。基于 12 小时实测根因，pinning 数据源用 GitHub 官方 meta；架构从「每容器自治 循环」收敛为「transport 单点重选 + 物理机 worker 只读刷容器」，把 meta 的驱动点从 6000 容器降到 1，扛共用 NAT 的每小时 60 次 限流。

## 1. 背景与目标

DevEnv 容器内 `git clone/push` 慢且不稳。现方案在 `/etc/hosts` 受管块里给 GitHub 域名 pin 一个测速最优 IP，后台循环刷新。

目标：让 pinning 对 clone/push 真正产生速度与可靠性增益，并扛容器重启/新镜像。本设计产出加速逻辑（transport 服务 + worker 脚本）：**transport 每 12h 重选、每 1h 健康检查，保证一个最优 IP（无则空串）；worker 每 1h 探活共享存储里的最优 IP、只 200 才写进容器，坏则删受管块回退 DNS**。拉起 worker 由 transport 在创建容器时编排。TARGETS 只含 git host（`github.com` 等），**不含 `api.github.com`**——克隆/push 不走 API，且 api 探测算每小时 60 次 REST 限流（见 §5.2）。

## 2. 现状与根因（12h 实测）

2026-08-17 13:03 → 08-18 01:33，923957 节点 24 样本 × 30min。

- clone（`git/git` ~59MB）：46% 失败，成功速度 0.75–11.89 MB/s（16 倍方差），中位 3.54 MB/s。
- push：本体中位 2.15s，失败均来自 clone 阶段握手抽风。
- accel 循环存活满 12h，`api.github.com` 100% 被 pin 稳定 200，`github.com` 79% 被 pin、21% 探针 `http=000` 跳过，pin 状态反复 toggle。

### 2.1 根因：每个 GitHub 域名只解析到 1 个 IP，且该 IP 间歇性黑洞

923957 节点上三个 DoH 源 + 系统 DNS **都只返回同一个 IP**：

| 域名 | 解析到的 IP | 个数 |
|---|---|---|
| github.com | 20.205.243.166 | 1 |
| api.github.com | 20.205.243.168 | 1 |
| codeload.github.com | 20.205.243.165 | 1 |

**pinning 的价值是"多 IP 择优"，但这里没有多 IP 可选——pin 不 pin 都走同一个 IP。** A/B 验证：摘掉受管块后系统 DNS 解析回来仍是同一 IP。

深层根因：`github.com` 用地理 DNS，三个 DoH 解析器都按请求来源地区（EDNS client subnet / anycast 入口）返回最近的 edge IP，对中国区请求收口到同一个 `20.205.243.166`。"多 DoH 源"并未带来"多 IP"。而该唯一 IP 对本节点是间歇性黑洞（`curl -m8` 超时 `http=000`，`curl -m20` 才 200）。pin 它无法绕开抽风——没有别的 IP 可绕。12h 数据中 pin 状态与 clone 成败/速度无因果关系（pin 着失败率 53% ≥ 未 pin 33%，差异在 24 样本噪声范围内、不构成因果，属同 IP 噪声）。

结论：逻辑本身按设计正常跑了 12h（循环存活、api 稳定 pin、幂等正确、flock 并发保护生效）——**不是代码 bug，是 pinning 解决的"多 IP 择优"在此环境不存在。**

## 3. 核心思路

把 `get_ips` 的数据源从 **DoH（地理收口→1 IP）** 换成 **`api.github.com/meta`（GitHub 官方全量 edge CIDR）**，让 pinning 有真材实料可择优。

`https://api.github.com/meta`（公开、无需认证）返回 JSON，其中：
- `git` 数组：服务 `github.com` 等 git-over-HTTPS 操作的全部 edge CIDR。
- `api` 数组：服务 `api.github.com` 的 edge CIDR。

实测从 meta 候选里并行探测，最快者 `20.27.177.113`：10/10 成功、延迟 0.43–0.48s、端到端 clone **4.78s / 12.38 MB/s**（vs 基线中位 3.54 MB/s、46% 失败）。

不再受 DoH 地理收口限制，一次拿到全量候选；meta 自身走 `api.github.com`，全段抽风时取不到 → 自动退 DoH 兜底，不会比现状差。

**架构收敛**：全实验室共用一个 NAT 出口（物理机与容器同走、`api.github.com` 也抽风），meta 无认证限流每小时 60 次/IP 是全实验室一份。故 meta 重选与 GitHub 探测必须收敛到**单一驱动点（transport）**，否则 N 容器 / N 物理机并发即爆每小时 60 次、退 DoH 雪崩。worker 每 1h 探活共享存储里的最优 IP（git host 的 `info/refs`，非 REST、不受每小时 60 次）、只 200 才写进容器，坏则删受管块回退 DNS——线性流程自带自纠，死 IP 不会被写回容器。

---

## 4. 架构与拓扑

### 4.1 拓扑与角色

| 角色 | 位置 | 网络 | 职责 |
|---|---|---|---|
| transport | 1 台管理面节点（FastAPI 服务） | 管理面：到不了共享存储后端，到物理机走 SSH | curl meta + pick 重选、每 1h 健康检查当前最优 IP；IP 变→SSH 一台物理机写共享存储；创建容器事件→SSH 该机执行 1→2→3 |
| 共享存储 | 跨物理机一份 | 存储面：100 台物理机挂载，transport 不挂 | 存最优 IP（per-host 一行 `host ip`），worker 读、transport 经物理机代写 |
| worker | 每台物理机常驻 | 存储面：本地 docker | 每 1h 读共享存储最优 IP→探活（git `info/refs`，非 REST）→200 写进容器、非200 删受管块回退 DNS（§5.5） |

- 全实验室共用一个 NAT 出口；物理机访问 `api.github.com` 也抽风。
- 凭据：transport 的 FastAPI 服务**内存**持有各物理机 IP/用户/密码（不落盘文件），SSH 进物理机。服务加固不在本需求内。

### 4.2 调用链

```
transport（FastAPI 服务，管理面）
  ├─ 定时任务（两个节奏）：
  │     每 1h 健康检查（HC_INTERVAL=3600）：探当前内存最优 IP 的 PROBE_PATH（-m5）
  │       ├ 200   -> 健康，不动，等下周期
  │       └ 非200 -> 立即触发重选（不等 12h）
  │     每 12h 强制重选（CACHE_TTL=43200）：到期必重选（刷新 meta，IP 会轮换）
  │     重选触发 = 健康检查 非200 OR 距上次重选 ≥12h -> ip = pick host $(get_ips host)
  │            （共用 NAT 单一驱动点，稳态 ~1 次/12h meta，远在每小时 60 次 内）
  │     重选后：新 IP 非空且与旧值不同 -> SSH 一台物理机代写共享存储 `host ip`（跨机一份全局生效）
  │              新 IP 为空串 / 与旧值相同 -> 不写（保留旧值，不覆盖可能仍可用的旧 IP）
  │              写失败 -> 告警不阻断，transport 内存仍持新 IP，创建容器时直用
  │
  └─ 创建容器事件（某物理机要起容器）-> SSH 该物理机，按序执行（1→2→3：容器先能用优先）：
        1. 创建容器；内存最优 IP 非空 -> docker exec 写新容器 /etc/hosts 受管块（cat 原地，
           bind-mount 不 mv，用 transport 内存 IP，不依赖共享存储）；空串 -> 不改 hosts（走默认 DNS）
        2. 容器创建后：对比内存 IP 与本机共享存储 IP——非空且不同 -> 写共享存储 `host ip`；
           空串 / 相同 -> 不写
        3. 确保 worker 常驻在跑（pgrep；不在则拉起）

worker（每台物理机，由 transport 在创建容器时拉起后常驻）
  └─ 循环（WORKER_INTERVAL=3600，每 1h，线性三步、无防抖）：
        读共享存储各 host 最优 IP
          ├ 读失败（掉挂载/无文件/权限）-> 不动容器 hosts（保持现状），告警，下周期重试
          └ 读成功 -> 逐 host：
               IP 空串 -> 不动容器 hosts（保持现状），下一 host
               IP 非空 -> 物理机 curl --resolve host:443:ip 该 IP 的 PROBE_PATH（-m5）：
                 ├ 200   -> docker ps 列本机 running 容器，逐个：受管块 IP 不同/缺 -> docker exec 刷新；相同 -> 跳过
                 └ 非200 -> docker exec 删各容器 /etc/hosts 受管块 -> 回退 DNS（幂等：已删则 无操作，下周期仍死仍停 DNS）
        （worker 不 curl meta——meta 职责全在 transport；探测的是 git host 的 info/refs，非 REST 端点，
          不受每小时 60 次 限；只 200 才写容器，死 IP 永不被写回——transport 恢复推新 IP 后下周期自动重新 pin）
```

要点：
- **transport 内存是 唯一可信源**（最优 IP），共享存储只是「分发给 worker」的通道；通道任何异常，transport 仍能用内存 IP 直写新容器 hosts。
- **worker 读不到就不动**，绝不把容器 hosts 改坏。
- transport 写共享存储失败**不阻断创建容器**——步骤 1 直接用内存 IP 写新容器 hosts。
- 自愈：transport 健康检查 发现坏→重选→写共享存储→worker 下周期读到→探活→刷容器，延迟 ≈ HC_INTERVAL(1h)+WORKER_INTERVAL(1h)（≈2h），不靠创建容器事件、不靠容器重启。
- **worker 只 200 才写容器**：死 IP 不会被写回；transport 挂了 worker 仍每 1h 探旧 IP，好→继续 pin、坏→删回退 DNS，恢复推新 IP 后下周期自动重新 pin。共享存储文件简化为 `host ip`（worker 不判过期，12h 是 transport 内存计时）。

### 4.3 文件布局

| 文件 | 位置 | 角色 |
|---|---|---|
| 共享存储最优 IP 文件 | 共享存储（跨机一份） | per-host 一行 `host ip`，worker 读、transport 经物理机代写 |
| worker 脚本 | 各物理机本地（transport 拉起） | 只读共享存储 + `docker exec` 刷容器 hosts 的 循环 |
| transport 服务 | transport 节点 | FastAPI：每 1h 健康检查 + 每 12h 重选 + 创建容器编排（SSH 各物理机） |

---

## 5. 逻辑契约

约定：全部脚本 `set -uo pipefail`（**不**用 `-e`，单步失败由调用方决定），日志走 stderr。受管块标记不变：
```
# >>> github-accel (managed) >>>
<IP> <host>
# updated <UTC>
# <<< github-accel (managed) <<<
```
> 每个 TARGET 占一行 `<IP> <host>`，多 host 时在标记内纵向堆叠；`# updated` 是整块一个时间戳（取最近一次写入）。

### 5.1 transport：`get_ips <hostname>` → stdout 逐行 IPv4（meta 数据源）

```
1. hostname -> meta key:  全部 TARGETS（github.com/codeload.github.com/ssh.github.com）-> git
                          （api.github.com 已移出 TARGETS，见 §1；不走 meta 的 api 数组）
2. curl -s -m10 https://api.github.com/meta 现拉（不落盘，用完即弃）
   （meta 是单次重选的中间产物；常态 健康检查 通过不进 get_ips、稳态重选由 transport 单点驱动
     ~1 次/12h，远在无认证每小时 60 次/IP 限内）
   (curl 失败/JSON 解析失败 -> 走 DoH 兜底分支，见步骤 5)
3. 从 meta[git] 数组取每条 CIDR，展开为可探测代表 IP：
     /32            -> 原样
     其他 CIDR       -> 取 2 个代表（网络号 +1、段末 -1），交给 pick 过滤
4. 去重 + 只留合法 IPv4，逐行输出。
5. 兜底：若 meta 取不到（api.github.com 全段抽风），用旧 DoH 逻辑（阿里/1.1.1.1）+ getent 取候选。
```

> 关键修正：meta 的 `git` 数组是 **CIDR 块**（如 `140.82.112.0/20`），不是单个 /32。直接探网络号 `.0` 会探不通，**必须先展开成代表主机 IP**。

> Pin 范围（决策）：**只 pin github.com**，`PIN_HOSTS = ["github.com"]`。codeload.github.com **按设计走 DNS、不 pin**：它仅服务归档/zipball 下载、不参与 git clone/fetch/push；附录 C.8 实测真实 clone 全程仅连 github.com（`info/refs` + `git-upload-pack`，无 codeload、无重定向），pin github.com 即覆盖全部 git 工作流。历史版本曾把 codeload 列入 `PIN_HOSTS`，但其 `info/refs` 探测恒返回 301（非 200）从不进块，徒增每周期一次白探（死 IP 时多耗 ~5s），故移除。ssh.github.com 走 SSH 443 配置（§5.4 `resource_config_container.sh`），不在 https pin 集。

### 5.2 transport：`pick <hostname> <ip...>` → stdout 最优 IP

```
1. 每个候选 IP 起后台 curl，每 IP 探 3 次取中位数（消单次采样方差——
   本设计的全部根因就是单 IP 高方差，一次采样会把"运气好的慢 IP"选上来）：
     curl --resolve "$host:443:$ip" -o /dev/null -s -m5 \
       -w '%{http_code} %{time_total}' "$PROBE_PATH" 2>/dev/null
   每 IP 取 3 次的 code 众数 + 总耗时中位数。
   PROBE_PATH: git 类 host -> "https://$host/git/git/info/refs?service=git-upload-pack"
   （api.github.com 已移出 TARGETS，无 api 类 host、无 `https://$host/` REST 探测，规避每小时 60 次 限流，见 §1）
2. 候选排序优先级：
     a. code == 200 的候选按中位总耗时升序排，取第一个。
     b. 若无 200，才在 code != 000 的候选里按中位总耗时取（504 等不再轻易挤掉好 IP）。
     c. 全部 000 -> 输出空串。
3. 3×候选数个 curl 全并发、每个受 -m5 上限，墙钟 = 最慢单探的总耗时(≤5s)，与候选数无关。
```

> PROBE_PATH 用与 clone 测试同源的真实仓库路径 `git/git/info/refs`，非根 `/info/refs`——根路径无仓库上下文未必返回 200，会使"优先 200"排序落空。

### 5.3 transport：定时健康检查 + 重选 + 写共享存储

```
每 1h 健康检查（HC_INTERVAL=3600）：
1. 逐 host 探当前内存最优 IP 的 PROBE_PATH（-m5）
2. 200 -> 健康，不动；非200 -> 立即触发重选（不等 12h）
每 12h 强制重选（CACHE_TTL=43200）：距上次重选 ≥12h 必重选（刷新 meta，IP 会轮换）
   重选触发 = 健康检查 非200 OR 距上次重选 ≥12h -> ip = pick host $(get_ips host)
3. 新 IP 非空且与旧值不同 -> SSH 一台物理机代写共享存储：host 行替换为 "host ip"（跨机一份，全局生效）
   新 IP 为空串 / 与旧值相同 -> 不写（保留旧值，不覆盖可能仍可用的旧 IP）
4. SSH/写失败（掉挂载/权限/只读）-> 告警，不阻断；transport 内存仍持新 IP，
   创建容器时步骤 1 直用内存 IP，不依赖共享存储写成功
```

### 5.4 transport：创建容器编排（1→2→3）

SSH 目标物理机后，按序：
```
1. 创建容器；内存最优 IP 非空 -> docker exec 新容器 cat 原地写 /etc/hosts 受管块（用 transport 内存 IP；
     /etc/hosts 是 bind-mount，不 mv/sed -i，必须 cat 原地写；空串 -> 不改 hosts，走默认 DNS）
2. 容器创建后：对比内存 IP 与本机共享存储 IP——非空且不同 -> 写共享存储 `host ip`（transport 内存最新值落盘该机共享存储，全局生效）；
     空串 / 相同 -> 不写（见 §5.6，不阻断后续）
3. 检查 worker 进程在否（pgrep），不在则拉起 worker 循环
```
> 顺序 1→2→3：先让新容器能用(1)、再同步共享存储(2)、常驻维护可稍后(3)。步骤 1 用 transport 内存 IP 直写，**不依赖步骤 2 写共享存储成功**——共享存储异常时新容器仍可用；空串时不改 hosts，新容器走默认 DNS 不劣于现状。

### 5.5 worker：探活刷容器 hosts（每物理机常驻 循环）

```
周期 WORKER_INTERVAL=3600（每 1h，线性三步、无防抖、无过期判断）
1. 读共享存储各 host 最优 IP（读失败 -> 不动容器 hosts + 告警，下周期重试，见 §5.6）
2. 逐 host：
   IP 空串 -> 不动容器 hosts（保持现状），下一 host
   IP 非空 -> 物理机 curl --resolve host:443:ip 该 IP 的 PROBE_PATH（复用 §5.2，-m5）：
     200    -> docker ps 列本机 running 容器，逐个：受管块 IP 不同/缺 -> docker exec cat 原地刷新；相同 -> 跳过（省 exec）
     非200  -> docker exec 删各容器 /etc/hosts 受管块 -> 回退 DNS（幂等：已删则 无操作，下周期仍死仍停 DNS）
3. 不 curl meta（meta 职责全在 transport，避免 100 物理机并发爆每小时 60 次）；
   探测的是 git host 的 info/refs，非 REST 端点，不受每小时 60 次 限；
   只 200 才写容器，死 IP 永不被写回；transport 恢复推新 IP 后下周期读到、探活 200、自动重新 pin
```

### 5.6 异常处理

核心原则：**transport 内存持最优 IP（唯一可信源），共享存储只是分发给 worker 的通道**；通道异常 transport 仍能直写新容器 hosts；worker 读不到就不动。

| 异常 | 影响面 | 处理 |
|---|---|---|
| 共享存储掉挂载 | transport 写不了、worker 读不了 | transport 用内存 IP 直写新容器 hosts（步骤 1 不依赖共享存储）；worker 不动容器 hosts；告警；挂载恢复后自动续上 |
| 读不了 IP 文件（不存在/权限） | worker 读不到新 IP | worker 保持容器现有 hosts（上次写的，大概率仍有效）；告警；下周期重试 |
| 写不了 IP 文件（权限/满/只读） | 分发给 worker 中断 | transport 用内存 IP 写新容器（可用）；worker 读旧 IP、探活仍 200 则继续 pin、坏则回退 DNS；告警 |
| transport 链路异常（挂了/写不动共享存储） | worker 读到旧 IP（可能已失效） | worker 每 1h 探旧 IP：200 继续 pin、非200 删受管块回退 DNS（幂等停在 DNS）；transport 恢复推新 IP 后下周期自动重新 pin |

> transport 写共享存储失败不阻断创建容器；worker 拉起失败也不阻断（新容器 hosts 已由步骤 1 写好，只是缺自愈）。所有异常记日志/告警，人工介入。

---

## 6. 部署

### 6.1 transport 服务（FastAPI + 定时任务）

```
1. transport 节点部署 FastAPI 服务，常驻
2. 定时任务：HC_INTERVAL=3600 健康检查（每 1h）、CACHE_TTL=43200 强制重选（见 §5.3）
3. 暴露创建容器编排入口（§5.4），供上层调用触发
4. 凭据：FastAPI 内存持有各物理机 IP/用户/密码（不落盘文件，见 §6.3）
```

### 6.2 worker 部署（transport 创建容器时拉起）

```
worker 脚本部署到各物理机本地（或共享存储，物理机可读）
transport 在创建容器编排步骤 3 检查 worker 进程：
  pgrep 在跑 -> 跳过
  不在 -> 拉起 worker 循环（setsid nohup 脱离，输出并入日志）
```

### 6.3 凭据

- transport FastAPI 服务**内存**持有各物理机 IP/用户/密码，SSH 进物理机执行写共享存储 / 写容器 hosts / 拉起 worker。
- 不落盘文件、不进代码仓库。
- 服务加固不在本需求内（已知边界，见 §9）。

---

## 7. 验证

1. transport 定时任务：健康检查当前最优 IP，手动改坏共享存储里某 host IP -> 下个 健康检查 周期内 transport 重选该 host、写共享存储。
2. 缓存暖启动：清共享存储 IP 文件 -> transport 跑全量 get_ips+pick，写回。
3. `git clone --depth 1 https://github.com/git/git` 计时，对比基线（目标：接近 4.78s / 12.38 MB/s）。
4. 创建容器编排：触发创建容器 -> transport SSH 该机执行 1→2→3；新容器 `/etc/hosts` 受管块立即有 pin IP（内存 IP 空串则不改、走默认 DNS）；`pgrep` 能看到 worker。
5. worker 探活刷：手动改某容器 hosts 受管块 IP 为坏值 -> 下个 WORKER 周期内 worker 读共享存储 IP、探活 200 刷回；手动改共享存储 IP 为坏值 -> worker 探活非200 删受管块回退 DNS。
6. 异常分支：
   - 掉共享存储挂载 -> worker 不动容器 hosts + 告警；transport 创建容器仍用内存 IP 直写新容器 hosts（可用）。
   - 改共享存储 IP 文件为只读 -> transport 写失败告警、不阻断；worker 读旧 IP、探活仍 200 继续 pin。
7. 自愈：transport 健康检查 发现坏 -> 重选 -> 写共享存储 -> worker 下周期探活 200 刷容器，延迟 ≈ HC_INTERVAL(1h)+WORKER_INTERVAL。
8. transport 挂了：停 transport -> worker 每 1h 仍探共享存储旧 IP：200 继续 pin、非200 删受管块回退 DNS（幂等停在 DNS）；重启 transport 推新 IP -> 下周期 worker 探活 200 自动重新 pin。空串路径：内存 IP 空 -> 新容器不改 hosts 走默认 DNS、不写共享存储（保留旧值）。

## 8. 风险与回滚

| 风险 | 缓解 |
|---|---|
| meta 走 api.github.com，全段抽风取不到 | get_ips 自动退 DoH + getent 兜底，不劣于现状 |
| CIDR 展开算错代表 IP | 先实看 meta `git` 数组 CIDR 位数；/32 直用、其余取 2 个代表，见 §5.1 |
| 并行 pick 起约 3×候选数个 curl（每 IP 探 3 次） | 仅 transport 跑，受 -m5 上限、墙钟 ≈5s，与候选数无关 |
| 无认证 meta 限流每小时 60 次 × 共用 NAT 一份 | meta 驱动点收敛到 transport 单点，稳态 ~1 次/12h，远在每小时 60 次 内；冷启动也只 1 次 |
| worker 探测被限流 | worker 只探 git host 的 `info/refs`（git 协议，非 REST），不受每小时 60 次；api.github.com 已移出 TARGETS（其根 `/` 是 REST、算每小时 60 次，100 worker×1h 会超限），见 §1/§5.2 |
| 共享存储掉挂载 / 读写失败 | transport 用内存 IP 直写新容器 hosts 不阻断；worker 不动容器 hosts 保持现状；告警人工介入，见 §5.6 |
| transport 单点（定时任务/编排） | transport 内存是 唯一可信源，挂了 worker 每 1h 探共享存储旧 IP：好继续 pin、坏删受管块回退 DNS（停在 DNS）；transport 恢复推新 IP 后下周期自动重新 pin（§5.5） |
| 凭据存 transport FastAPI 内存 | 不落盘文件；服务加固不在本需求内（已知边界，见 §9） |
| worker 进程崩了不自重启 | transport 创建容器编排步骤 2 会补拉；常驻期间崩需人工/上层 pgrep 重拉 |

**回滚**：停 transport 服务 + 各物理机停 worker；受管块残留可手动清（或容器重启由 Docker 重置 hosts）。旧 DoH 方案不受影响。

---

## 9. 已知边界与后续演进

- 504 在"全无 200"时仍可能被 pin（§5.2.b，保底可用）；但 transport 健康检查以 200 为准，pin 后转入 504 会在下个 健康检查 周期被重选。
- meta IP 多数路由不通（anycast/地理路由）是常态，pick 过滤即可。
- 全实验室出口 IP 统一（线下单 NAT），故最优 IP 共享一份即可、不按节点隔离；若将来出口分化，需按出口隔离。
- **服务加固不在本需求内**：凭据存 FastAPI 内存、transport 被攻破=所有物理机凭据泄露是已知风险，后续可演进为 SSH 密钥认证 + 低权限账号 + `ForceCommand` 从根上免密码。
- **codeload.github.com 走 DNS（已决策，不 pin）**：仅服务归档/zipball 下载、不参与 git 操作，pin github.com 即覆盖全部 git 工作流（附录 C.8 实测真实 clone 全程仅连 github.com）。历史曾列入 `PIN_HOSTS` 但 `info/refs` 探测恒 301、从不进块，已移除以省白探。ssh.github.com 走 SSH 443 配置（§5.4）不在 https pin 集；若将来要给归档下载加速，可单独把 codeload 纳入并用其适配探测路径（`info/refs` 对 codeload 返回 301 不宜复用）。`api.github.com` 不纳入：其探测走 REST 根 `/`、算每小时 60 次，100 worker×1h 会超限；若将来要给 API 客户端加速，需改用 TLS 握手类非 REST 探测或仅 transport 单点探。

## 附录 A：关键实测数据（923957，2026-08-17/18）

### A.1 meta 候选探测（根路径 `/`，并行 -m5）
| IP | http | total | 备注 |
|---|---|---|---|
| 20.27.177.113 | 200 | 0.33s | 最快 |
| 20.200.245.247 | 200 | 0.59s | |
| 20.205.243.166 | 200 | 0.74s | 旧 pin（常抽风 000）|
| 20.29.134.23 | 200 | 1.12s | |
| 4.237.22.38 | 200 | 1.35s | |
| 20.233.83.145 | 200 | 1.40s | |
| … | … | … | 共约 20 个能 200 |

### A.2 候选稳定性（`info/refs`，10 次/IP）
| IP | 成功率 | avg | min–max |
|---|---|---|---|
| 20.27.177.113 | 10/10 | 0.453s | 0.43–0.48 |
| 20.200.245.247 | 10/10 | 0.683s | 0.62–0.92 |
| 20.29.134.23 | 10/10 | 1.07s | — |
| 20.207.73.82 | 10/10 | 1.28s | — |
| 4.237.22.38 | 10/10 | 1.40s | — |
| 20.233.83.145 | 10/10 | 1.45s | — |
| 20.205.243.166（旧）| 7/10 | — | 抽风坐实 |

### A.3 端到端 clone（临时 pin `20.27.177.113`）
- `git clone --depth 1 git/git` → **4.78s / 59.2MB / 12.38 MB/s** ✓

## 附录 C：物理机 79.1.2.128 实测（2026-08-25）

> 首段（§5.1–5.3 + 内存/凭据接口）落地后的真实环境验证。环境：openEuler 22.03 SP1 / aarch64 / root，glusterfs 挂在 `/data/gluster`（可写），多 DevEnv 容器在跑。

### C.1 get_ips（meta 数据源）
- `curl https://api.github.com/meta` 出口通，`git` 数组 46 个 CIDR → 展开 48 个候选 IPv4（/32 原样、其余取网络+1/广播-1 两代表、去重）。

### C.2 pick（并发 3 次取中位选优）
- 48 候选：**20 个 200、28 个 000 黑洞段、0 个非200非零**。
- top8（200，按中位耗时升序）：

  | IP | 中位 |
  |---|---|
  | 20.27.177.113 | 0.436s |
  | 20.200.245.247 | 0.644s |
  | 20.205.243.166 | 0.840s |
  | 20.29.134.23 | 1.004s |
  | 20.207.73.82 | 1.203s |
  | 4.237.22.38 | 1.369s |
  | 20.233.83.145 | 1.398s |
  | 172.182.252.133 | 1.452s |

- 000 黑洞段为旧 edge（192.30.252/185.199.108/140.82.112/143.55.64）——印证 §2.1 抽风根因。
- 最优 `20.27.177.113`，与附录 A（923957 节点）一致，跨节点可复现。

### C.3 共享存储写（`_write_shared_storage`）
- 路径：`/data/gluster/share/docker_config/github_accel_ips`（per-host 一行 `host ip`）。
- `mkdir -p` + `cat >` 原地写（bind-mount 安全）+ `stdin.channel.shutdown_write()` 发 EOF → exit 0；读回正确：
  ```
  github.com 20.27.177.113
  codeload.github.com 20.27.177.113
  ```
  （上为历史实测输出；按 §5.1 决策 codeload 走 DNS，新版 `_write_shared_storage` 只写 `github.com` 行，`PIN_HOSTS` 不含 codeload。）

### C.4 容器 /etc/hosts bind-mount 约束（§5.4/worker 前置）
- `cat >` 原地写受管块 OK（marker + pin IP 正确写入、读回正确）。
- `sed -i` → `cannot rename ... Device or resource busy`（失败，符合预期）。
- `mv` → `Device or resource busy`（失败，符合预期）。
- 证实写容器 `/etc/hosts` 必须用 `cat >` 原地写，不能用 `sed -i`/`mv`。
- 注：本项用临时 marker `# BEGIN/END github_accel managed` 验证 bind-mount 行为，**最终受管块标记以附录 B 的 `# >>> github-accel (managed) >>>` … `# <<<` 为准**。

### C.5 DevEnv 容器默认 DNS vs pin 对比（根因 + 收益）
- 运行中的 DevEnv 容器默认 DNS：`github.com → 20.205.243.166`、`codeload.github.com → 20.205.243.165`。
- `info/refs` 探测：默认 DNS 200 @ **0.903s**；pin `20.27.177.113` 200 @ **0.423s** → **pin 比默认 DNS 快约 2.1×**。
- 该时刻 DNS 恰好解析到可用 IP（未抽风到 000 段）；抽风时段 DNS 会解析到 000 黑洞段（C.2 实测 28 个 IP 全 000），pin 能稳定选到 0.42s 的好 IP。加速价值实证成立。

### C.6 验证项对应 §7
- §7.1 定时任务 get_ips+pick+写共享存储 → C.1/C.2/C.3 通过。
- §7.2 缓存暖启动（清文件→全量重选写回）→ C.3 已证写回链路；全量重选同 C.2。
- §7.4 创建容器编排受管块写入 → C.4 证 bind-mount 写法可行。
- §7.3 clone 计时、§7.5 worker 探活刷 → §7.5 已随 §5.5 落地验证（见 C.7；真实 clone/push + timeout 实测见 C.8）；§7.3 clone 计时待 §5.4 落地后跑。

### C.7 worker 探活刷容器实测（§5.5，2026-08-26）

worker 脚本 `service/docker_config/scripts/github_accel_worker.sh`（bash，`set -uo pipefail`）部署到 79.1.2.128 共享存储 `/data/gluster/share/docker_config/scripts/` 跑 `--once` 单轮实测。

**前置（补 C.4 真实容器缺口）**：在运行中 devenv 容器 `devenv_977680_…` 内：`cat > /etc/hosts` OK；`sed -i` → `cannot rename ... Device or resource busy`。与 C.4 临时容器结论一致，证实真实 devenv 容器同样只能 `cat >` 原地写。

**写块机制全分支通过**（复刻 worker 真实 awk+cat 逻辑，在 devenv 容器上测）：
- 写入受管块 → refreshed，格式符合附录 B（`# >>>` + `<ip> <host>` 纵向堆叠 + `# updated` + `# <<<`）。
- 幂等：同块再写 → `same, skip`（省 exec）。
- 替换：IP 变 → refreshed，旧块整段替换为新块。
- 删块（block 空）→ refreshed，回退 DNS；再删 → `same, skip`。
- 恢复后全机 7 个 running 容器受管块残留计数均 0。

**探活逻辑行为通过**：`curl --resolve host:443:ip -m5 -w '%{http_code}'` 取码正确传回（实测见过 200/301/000），仅 200 进 alive 集合；读共享存储失败/空 → `skip (containers untouched)`；逐 `docker ps` 遍历全部 7 容器均触达。

**发现 1：宿主探活 = 容器探活（假设成立，无需改容器内探活）**。为验证「宿主 curl 能否代表全机」，对 meta 候选 12 个 IP 做 3 轮宿主+容器**并行**探活（共 36 次）：宿主与容器结果 **100% 一致**（旧 edge 段 192.30.252/185.199.108/140.82.112/143.55.64 全 000，新 edge 段 20.201.28.151/20.205.243.166/20.87.245.0/4.237.22.38 全 200，宿主容器同码），0 次不一致、0 次「宿主 200 容器 000」危险情况。§5.5「物理机 curl 代表全机」假设成立，worker 宿主探活够用。此前单次观察到的「宿主边界 200@5.001s、容器 000」是 `curl -m5` 超时边界的假阳性（`time_total≈5.0s` 时 `http_code` 残留 200 但连接实际已超时不可达），非真实差异——批量并行采样下消失。

**发现 2：出口到 github 间歇性，时间尺度而非空间尺度**。pin 不同 IP 均时通时断，几分钟内同 IP 默认 DNS 从 200@0.846s 变 000@5s；但同一时刻宿主与容器对所有 IP 结果一致（发现 1）。故间歇性是**时间维度**（不同时刻 200↔000 切换），不是「宿主/容器出口不同」。含义：worker 每 1h 探活，探到 000 删块回退 DNS，但 DNS 同样抽风 → 两端来回切换都不稳；pinning 加速价值仅在可达窗口成立（C.5 实测 pin 比 DNS 快 2.1×）。

**未触发**：实测时段出口呈分半稳定（新段全 200、旧段全 000），共享存储里的 `20.27.177.113` 此刻属 000 段故未触发 200→写块端到端；但探活取码（200/301/000 均见过）与写块逻辑（C.7 写块机制全分支）已分别验证，拼接路径正确性由两段独立保证。worker 宿主探活代表全机成立。

**已决策**：
1. ~~worker 探活改用容器内 curl~~ —— 经发现 1 验证不必要，宿主探活 = 容器探活，维持 §5.5 宿主 curl 设计。
2. 间歇性是时间维度（两端都抽风）属网络出口硬限制，方案层不改；接受块/DNS 空窗，靠 worker 每 1h 探活 + transport 每 1h 健康检查在可达窗口自愈对齐。
3. 已加固 curl `-m` 超时边界假阳性（发现 1 根因）：transport `pick._probe_once`（`github_accel.py`）与 worker 判活（`github_accel_worker.sh`）均加 `time_total ≥ PROBE_TIMEOUT` 条件——边界超时时拘留的 `200` 视为 `000`，不进 alive / 不被 pick 选入。依据 C.8 证实可达成功均秒级 0–1s、无「慢但能成」中间态，故 ≥ 超时阈值的 200 必为假阳性。awk 浮点比较四边界场景验证通过（`5.000`/`5.001`→置 `000`，`4.999`/`0.436`→保持 `200`）；`py_compile` + `bash -n` 通过。端到端实测（新版部署到 79.1.2.128 共享存储后）：`PROBE_TIMEOUT=1 --once` 轮 codeload `total=1.000191 ≥ 1` → 拘留的 `200` 被改 `000`（不进 alive），github.com `total=0.999874 < 1` 保持 `200`（真可达，进块写 8 容器）；恢复轮 `PROBE_TIMEOUT=5 --once` github.com `total=5.001314 ≥ 5` → 边界 `200` 被改 `000`（坏 IP 不写入容器 hosts），codeload `301` 非 `200` 不进 alive → alive 空 → 删块，8 容器回退 DNS，final 块计数 `0`。两轮均命中假阳性过滤、状态干净。

### C.8 真实 git clone/push 实测（§5.5/§7.5，2026-08-26）

物理机 79.1.2.128 running 容器内跑真实 git clone（HTTPS, `octocat/Hello-World` depth1）+ push 网络层探测，验证 pin 块对真实 git 操作的影响。

**worker 200→写块端到端补触发**（补 C.7「未触发」）：`--once` 单轮探活 `github.com 200 / codeload 000` → 仅存活 host 进块 → 8 容器全 refreshed 写入 `20.27.177.113 github.com`（codeload 000 不进块，走 DNS）；第二轮两 host 均 000 → alive 空 → 块空 = 删块，8 容器 refreshed 删除回退 DNS。写块/删块端到端双向通，宿主探活代表全机成立。注：此轮实测时 codeload 尚在 `PIN_HOSTS`（恒 301/000 不进块）；按 §5.1 决策 codeload 已移出 `PIN_HOSTS` 走 DNS，新版 worker 不再探 codeload。

**clone 成功率三组对比**（每态 5 次，`timeout 30s`）：

| 模式 | 成功率 | 说明 |
|---|---|---|
| pin 好段（此刻可达 IP 20.205.243.166/165） | 4/5 = 80% | pin 对 IP 显著优于 DNS |
| DNS 默认（多 IP 轮转 20.205.243.166 段） | 2/5 = 40% | 轮到坏 IP 即失败 |
| pin 坏段（20.27.177.113，此刻路径差） | 1/5 = 20% | pin 错 IP 反而更糟 |

→ 印证方案核心：pick 选对 IP 时 pin > DNS（80% vs 40%）；选错 < DNS（20%）→ worker 探活 000 删块回退 DNS 是必要安全网（避免停在坏段）。

**push 网络层**（无凭据探测，推到 `octocat/Hello-World` 触发认证）：DNS 与 pin 好段各 3/3 即时返回 `fatal: could not read Username`（rc 非 124，秒级）= TLS 握手 + HTTP + GitHub 认证挑战全通，网络层健康，仅认证层失败。push 的 HTTPS 路径与 clone 同（`github.com:443`），pin 块影响一致；真实 pack 上行走同 TLS 流，clone 已证 pack 传输能过。

**timeout 放大实测**（证失败非超时太短）：pin 坏段 clone `timeout` 放大到 120s ×3，结果全 `rc=0 dur≈1s` 成功——非 timeout 救活，而是此刻窗口开了。对比同 IP 几分钟前 `timeout=30s` 仅 1/5 成功。观察所有样本：成功 = 秒级（0–1s），失败 = 硬超时（≈30s），**无中间态**（无「慢但能成」）→ 失败是 TCP 路径黑洞（SYN 无应答，对应 curl `tcp=0.000`），非带宽慢；放大 timeout 只让失败的 case 等更久才报错，救不了黑洞。

**codeload 不参与 clone 的实证**（2026-08-30，§5.1 codeload 走 DNS 决策依据）：devenv 容器内 `GIT_CURL_VERBOSE=1 git clone --depth 1 https://github.com/vllm-project/vllm-ascend.git`，pin 块 `20.27.177.113 github.com` 在位。verbose 显示 clone **全程仅连 `github.com (20.27.177.113)`**：`GET /.../info/refs?service=git-upload-pack`（HTTP/2 200）+ `POST /.../git-upload-pack`（200），`:authority: github.com` / `Host: github.com`，**无 codeload、无重定向、无其他 host**。pin clone `rc=0 dur=3s`（HEAD `e6a133f` 拉到）；对照剥块走 DNS 连 3 次 `rc=0 ~3.9–4.2s`（此刻 DNS 恰好解析到好 IP）。→ `git clone/fetch/push` 只走 github.com，codeload.github.com 仅服务归档/zipball 下载，pin github.com 即覆盖全部 git 工作流，codeload 走 DNS 不影响任何 git 操作。

**结论**：
1. clone/push 失败是间歇可达窗口问题，非 timeout 长度——worker `PROBE_TIMEOUT=5s` 合理（探测黑洞 5s 足够，放大无收益）。
2. 靠 worker 每 1h 探活 000 删块回退 DNS + transport 每 1h 健康检查重选在可达窗口自愈对齐，不靠放大 timeout。

## 附录 B：文件清单（待写）

- transport 服务（FastAPI）：每 1h 健康检查 + 每 12h 重选（§5.1–5.3）+ 创建容器编排 1→2→3（§5.4），凭据内存（§6.3）
- worker 脚本：各物理机常驻 循环，每 1h 读共享存储→探活→200 写容器 / 非200 删受管块回退 DNS（§5.5）
- 共享存储最优 IP 文件：`host ip`，per-host 一行；worker 不判过期（每 1h 直接探活），12h 重选是 transport 内存计时
- 受管块标记：`# >>> github-accel (managed) >>>` … `# <<<`（每容器 /etc/hosts）
- meta 不落盘：transport 每次 `curl api.github.com/meta` 现拉（中间产物、用完即弃；稳态 ~1 次/12h）
- TARGETS 只含 git host（`github.com` 等），不含 `api.github.com`（见 §1）
