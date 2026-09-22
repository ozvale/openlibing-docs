# hidevlab-transport-service 安全分析报告

> 报告日期：2026-08-27
> 分析方法：STRIDE-A 威胁建模
> 适用版本：当前仓库 HEAD（2026-08-27）
> 报告语言：简体中文

---

## 一、项目概述

### 1.1 项目定位

`hidevlab-transport-service` 是华为 HiDevLab 实验室平台的 **transport 控制面服务**。其核心职责为：

- 通过 SSH/paramiko 远程管理宿主机（安装软件、部署 agent、修改密码、配置 OBS）；
- 编排 Docker 容器全生命周期（创建/启停/镜像保存发布/恢复/迁移/清理）；
- 提供对外 RESTful API（经华为云 APIG 签名鉴权）；
- 通过 flask_apscheduler 内嵌定时任务，执行清理与巡检；
- 借助 gunicorn（sync worker，自带 SSL）提供生产 WSGI 能力；
- 使用 Apollo 配置中心集中下发配置，敏感字段经 AES-GCM + PBKDF2 双层解密。

### 1.2 技术栈

| 维度 | 组件 |
|------|------|
| 语言 | Python 3 |
| Web 框架 | Flask + flask_apscheduler |
| WSGI | gunicorn（sync worker，启动时加载 SSL） |
| 远程管理 | paramiko（SSH/SFTP） |
| 配置中心 | python-apollo（HTTPS 校验） |
| 加解密 | pyOpenSSL / pycryptodome（AES-GCM、PBKDF2） |
| 鉴权 | 动态 Token + APIG 签名（X-HW-ID / X-HW-SIGN / SHA256） |
| 容器化 | Docker CLI、Harbor、GlusterFS 共享存储 |
| 部署 | systemd（transport.service / fileserver.service） |
| 文件服务 | `python3 -m http.server 18443`（静态分发） |

### 1.3 仓库目录结构（关键部分）

```
transport.py              # Flask 入口 + 路由
gunicorn_config.py         # 生产 WSGI 配置（SSL 解密→加载→when_ready 删除）
base/                      # apollo_manager / config / auth_filter / common /
                           # decrypt / logging_handler
service/                   # docker_manager(133KB) / clab_agent / obs / pre_install /
                           # docker_config / start_docker.sh / obs/{arm,x86}/obsutil
tools/                     # ssh（Ssh 类、sudo_exec_command、改密码、建运维账号）/ json2file
utils/                     # security（IP/MAC 脱敏）/ command_security（路径/容器名/镜像名/命令校验）
config/software_check.yaml # 软件安装成功/失败 TAG
script/                    # create_container.sh / delete_image.sh
deploy/                    # post_deploy.sh / post_scripts.sh / history_post_scripts/
software/                  # {platform}/{软件名}/{版本}/install.sh+uninstall.sh
docs/                      # openapi.yaml / docker_images.md
.cid/deploy.sh             # 一键部署脚本
```

---

## 二、系统架构与数据流（DFD）

### 2.1 逻辑架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                          黄区（控制调用方）                              │
│   实验室业务平台 → 经 APIG 网关 → X-HW-ID/X-HW-SIGN 签名请求              │
└────────────────────────────────────┬────────────────────────────────────┘
                                     │ HTTPS（APIG 签名 + 动态 Token）
                                     ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                      绿区：transport-service                             │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌────────────┐  │
│  │ Flask 路由   │  │ flask_apscheduler│ │ Apollo 客户端│ │ gunicorn+SSL│  │
│  └──────┬───────┘  └──────────────┘  └──────┬───────┘  └────────────┘  │
│         │                                     │ 解密 ENC_*               │
│         ▼                                     ▼                          │
│  ┌────────────────────────────────────────────────────────────────────┐  │
│  │ service/                                                            │  │
│  │  - docker_manager（容器全生命周期、Harbor、GlusterFS、异步任务）     │  │
│  │  - clab_agent（监控 Agent 安装）                                    │  │
│  │  - obs（OBS obsutil 配置）                                          │  │
│  │  - pre_install（软件安装状态解析）                                  │  │
│  └──────┬─────────────────────────────────────────────────────────────┘  │
│         │                                                                │
│  ┌──────▼───────┐  ┌──────────────┐  ┌──────────────┐                   │
│  │ tools/ssh    │  │ utils/         │  │ base/decrypt │                   │
│  │ Ssh + sudo   │  │ command_       │  │ AES-GCM/PBKDF2│                  │
│  │ 运维账号      │  │ security       │  └──────────────┘                 │
│  └──────┬───────┘  └──────────────┘                                     │
└─────────┼────────────────────────────────────────────────────────────────┘
          │ SSH/SFTP（22）           │ HTTPS              │ 文件分发
          ▼                          ▼                    ▼
┌──────────────────┐   ┌──────────────────┐   ┌──────────────────┐
│ 红区：宿主机       │   │ Harbor 镜像仓库    │   │ 华为云 OBS         │
│ - Docker 引擎     │   │ - 镜像 push/pull   │   │ - 备份/归档         │
│ - GlusterFS 节点  │   └──────────────────┘   └──────────────────┘
│ - 运维账号        │
│ - clabAgent       │
└──────────────────┘
```

### 2.2 信任边界

| 边界 | 起点 | 终点 | 通道 | 风险面 |
|------|------|------|------|--------|
| TB1 | 黄区业务平台 | 绿区 transport | HTTPS + APIG 签名 + Token | 越权调用、签名重放、Token 泄露 |
| TB2 | 绿区 transport | 红区宿主机 | SSH（22） | 凭证泄露、命令注入、主机逃逸 |
| TB3 | 绿区 transport | Harbor | HTTPS（APIG 签名回传） | 镜像篡改、凭证泄露 |
| TB4 | 绿区 transport | 华为云 OBS | HTTPS（AK/SK） | AK/SK 泄露、桶越权 |
| TB5 | 绿区 transport | Apollo 配置中心 | HTTPS | 配置篡改、密钥下发泄露 |
| TB6 | 红区宿主机 ↔ 容器 | 宿主机 Docker daemon | Docker CLI / mount | 容器逃逸、资源耗尽 |
| TB7 | 绿区 fileserver（:18443） | 宿主机/容器 | HTTP 静态服务 | 未授权下载、目录遍历 |
| TB8 | transport 内部线程 | 异步任务队列 | `threading.Thread(daemon=True)` | 任务无隔离、无速率限制 |

### 2.3 关键数据流

1. **API 请求流**：黄区 → APIG 签名 → HTTPS → Flask 路由 → `auth_filter.auth_filter` 校验 Authorization → 业务处理 → 回调（`sign_request` 生成 X-HW-SIGN）→ 黄区。
2. **SSH 命令流**：transport → `Ssh` / `sudo_exec_command` → paramiko → 宿主机 shell（root / sudo）。
3. **容器创建流**：API 入参 → `CommandSecurity` 校验 → `create_container.sh` 拼装 → SSH 执行 `docker run`。
4. **镜像发布流**：多机分组 → `docker pull` → `docker tag` → `docker login`（stdin 传密码）→ `docker push` Harbor → 分发至其余机器。
5. **凭证下发流**：Apollo 加密字段 → `decrypt`/`decryptbyroot` 双层解密 → 内存使用 / 临时文件 → `when_ready` 删除。
6. **日志流**：`logging_handler.JsonFormatter` → `/var/log/hidevlab/transport-<region>.*.json`（含 IP 哈希、操作者、请求 ID）。

---

## 三、安全代码审查发现

### 3.1 既有安全控制（值得肯定）

| 控制 | 实现位置 | 说明 |
|------|----------|------|
| 命令白名单 | `docker_manager.exec_command` / `CommandSecurity.validate_command_ops` | 仅允许白名单命令，禁止 shell 元字符（单引号外） |
| 路径校验 | `CommandSecurity.validate_path` | 禁 `..`、限制字符集，防路径穿越 |
| 容器名/镜像名校验 | `CommandSecurity.validate_container_name` / `validate_image_name` | 防止注入恶意 docker 参数 |
| 凭证 stdin 传递 | `docker_login`、`sudo_exec_command`、`_exec_with_status` | 通过 stdin 传密码，避免命令行/进程列表泄露 |
| SSL 证书临时化 | `gunicorn_config.when_ready`、`transport.py.__main__` | 启动解密 → 加载 → 删除临时文件 |
| 双层解密 | `base/decrypt.py` | root key → work key → AES-GCM，减少密钥单点暴露 |
| IP/MAC 脱敏 | `utils/security.mask_ip_partial`、日志中 `operator` SHA256 | 降低日志中敏感信息泄露 |
| APIG 签名回传 | `sign_request` | 对回调请求生成 X-HW-SIGN，防回传被仿冒 |
| 资源配额校验 | `docker_manager` 校验 CPU/RAM/PIDs/存储 | 防止单容器耗尽宿主机资源 |
| 请求 ID 追踪 | `logging_handler` | 全链路日志关联，便于事后追溯 |
| `AutoAddPolicy` 限制 | GlusterFS 节点连接使用 `AutoAddPolicy` | 在内网固定节点间使用，风险可控（但见 T-SSH-02） |

### 3.2 风险发现（按文件）

#### 3.2.1 `transport.py`（路由层）

- **R-ROUTE-01**：`/install/agent`、`/VM/obs/set`、`/passwd/expire` 使用 `ast.literal_eval(str(ret, "utf-8"))` 解析请求体，而其余路由使用 `json.loads`。`ast.literal_eval` 对非 JSON 字面量（如嵌套元组、数字）会执行得更宽松，一旦被绕过可造成解析异常。建议统一 `json.loads`。
- **R-ROUTE-02**：`/os/ops/account/create` 路由直接返回 `200 success` 而未真正创建账号（函数体仅返回响应）。存在「假成功」风险——上层以为账号已建，实际未生效。属功能缺陷，但从安全角度看会导致**审计与实际状态不一致**。
- **R-ROUTE-03**：大量路由对入参仅做 `if not all([...])` 存在性校验，未做**类型/长度/范围**校验。例如 `host_port` 未限制为 1-65535，`os_name` 未枚举，`lab` 未限制字符集。
- **R-ROUTE-04**：异步任务用 `threading.Thread(daemon=True)` 启动，**无任务数上限、无速率限制、无幂等保护**。攻击者高频调用 `/docker/image/publish` 等接口可造成线程爆炸、宿主机 SSH 连接数耗尽。

#### 3.2.2 `service/docker_manager.py`（133KB，核心）

- **R-DOCKER-01**：`exec_command` 虽有白名单，但白名单以「命令前缀」匹配（如允许 `docker`），仍可能在参数位拼装危险选项（如 `docker run --privileged --net=host -v /:/host ...`）。需对 docker 子命令做**结构化解析**而非字符串前缀匹配。
- **R-DOCKER-02**：`mount_glusterfs`、`_cleanup_member_ws_on_gfs_node` 等使用 `paramiko.AutoAddPolicy()` 并以**密码**连接 GlusterFS 节点。密码在内存与日志上下文中流转，且 `AutoAddPolicy` 不防中间人。建议改用 SSH 证书 + `known_hosts`。
- **R-DOCKER-03**：`_cleanup_member_ws_on_gfs_node` 拼装 shell 命令使用 f-string + `shlex.quote`。虽对路径做了 quote，但 `ctx.task_id` 直接嵌入 `LOCK="/tmp/.member_ws_{ctx.task_id}.lock"`，未校验 task_id 字符集。若 task_id 可被外部控制且含特殊字符，存在注入风险。
- **R-DOCKER-04**：`async_docker_image_publish` 等异步函数将 `harbor_server_password` 透传至 `_prepare_and_push_image`，最终经 `docker_login` 以 stdin 传入。但函数签名与日志中易打印 `params` 整体（见 `LOG.info(f"callback_data={callback_data}")`），存在**密码被日志记录**的风险。
- **R-DOCKER-05**：容器创建参数 `is_custom_image`、`is_base_image`、`device_model` 未在 `CommandSecurity` 中校验，直接进入 `create_container.sh` 模板。若模板未做二次转义，可能注入 docker run 参数。
- **R-DOCKER-06**：`storage_opt = f"--storage-opt size={int(size_val)}g"` 直接拼字符串，虽 `size_val` 经数值化，但若 `int()` 抛异常被外层捕获后仍返回原值，需确保**所有分支**都走数值化。

#### 3.2.3 `tools/ssh.py`

- **R-SSH-01**：`sudo_exec_command` 通过 stdin 传 sudo 密码（`echo '<pwd>' | sudo -S` 风格已避免），但 `create_ops_account` 给运维账号授予 **NOPASSWD:ALL**。一旦运维账号被攻陷，等同 root。建议收敛为 `NOPASSWD: /usr/bin/docker, /usr/bin/systemctl ...` 等最小集合。
- **R-SSH-02**：`Ssh` 类默认 `set_missing_host_key_policy(paramiko.AutoAddPolicy())`，首次连接不校验主机指纹，存在** SSH 中间人**风险。应预置 `known_hosts` 或指纹校验。
- **R-SSH-03**：`create_ops_account` 明文接收 `ops_pwd`、`admin_password`，在日志中若未脱敏，存在凭证泄露。需复核日志输出点。

#### 3.2.4 `base/auth_filter.py`

- **R-AUTH-01**：`auth_filter` 通过 HTTP 请求 token URL 校验动态 Token。若该 URL 为 HTTP 或证书校验关闭，存在** Token 校验被中间人绕过**的风险。此外，`auth_filter` 未捕获网络异常，TOKEN_URL 不可达时异常直接上抛导致 500（属 fail-closed，可接受，但建议收敛为统一 401/503）。
- **R-AUTH-02**：`ENABLE_AUTH` 来自 Apollo，可被远程配置关闭。一旦 Apollo 被攻陷或配置被篡改，所有路由鉴权失效。建议增加「本地 fallback」与启动期断言。
- **R-AUTH-03**（已核实）：`sign_request` 的签名为 `sha256(uri|POST|params|dateStr|X_HW_ID|X_HW_APPKEY)`。**签名不覆盖请求体（data），且无 nonce**，时间戳仅分钟级精度。这意味着：同一分钟内捕获的合法请求可在**篡改请求体后重放**（签名仍然有效），存在重放 + 篡改双重风险。
- **R-AUTH-04**：`X_HW_APPKEY = decrypt(ENC_X_HW_APPKEY)` 在模块导入期执行。结合 `decrypt` 的 fail-open 行为（见 R-DEC），若解密失败会静默使用密文作为 APPKEY，导致签名全部失效且难以察觉，建议解密失败时 fail-fast。

#### 3.2.5 `base/decrypt.py`

- **R-DEC-01**：root key 与 work key 若均来自 Apollo，则「双层」实质仍是单点。若 Apollo 配置项被读取，可解密所有密文。建议至少一层来自本地环境变量/HSM。
- **R-DEC-02**：解密后的明文（SSL 私钥、Harbor 密码）在内存中以 Python 字符串存在，Python 不可控内存回收，存在**内存转储泄露**风险（高级威胁，Tier 3）。

#### 3.2.6 `gunicorn_config.py` / `transport.py.__main__`

- **R-SSL-01**：临时证书文件 `tempfile.NamedTemporaryFile(delete=False)` 创建后，`when_ready` 删除。但若 `when_ready` 未触发（启动失败），临时文件残留磁盘。建议加 `atexit` + `try/finally` 兜底删除。
- **R-SSL-02**：`ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)` 未显式设置最小版本与密码套件。应强制 `min_version=TLSv1_2`，禁用弱套件。
- **R-SSL-03**：`fileserver.service` 使用 `python3 -m http.server 18443`，**纯 HTTP**，且 `WorkingDirectory=/home/fileserver`。若该目录含敏感脚本/镜像，存在**未授权下载**风险。

#### 3.2.7 `utils/command_security.py`

- **R-CS-01**：`validate_command_ops` 的白名单与元字符规则较复杂，维护成本高。建议引入**结构化命令构造器**（如 `subprocess.run(args=[...])`）替代字符串拼装，从根本上消除注入面。
- **R-CS-02**：`validate_path(allow_relative)` 允许相对路径时，未限制工作目录。若调用方未切换到预期目录，相对路径仍可穿越。

#### 3.2.8 `base/logging_handler.py`

- **R-LOG-01**：`operator` 使用固定 salt `hidevlab_log_salt_2024` + SHA256。salt 硬编码于源码，攻击者获知后可**预计算彩虹表**反推 IP。
- **R-LOG-02**：日志目录 `/var/log/hidevlab/` 权限未在代码中声明，依赖部署方手动配置。需在 `post_deploy.sh` 中显式 `chmod 750`。

#### 3.2.9 `fileserver.service`

- **R-FS-01**：`python3 -m http.server` 无鉴权、无 HTTPS、无访问日志。分发内容含 `software/`、`script/` 等可执行脚本，存在**供应链投毒**风险（中间人篡改 install.sh）。
- **R-FS-02**：`StandardOutput=file:/var/log/fileserver/os.log` 无日志轮转，长期运行可致磁盘打满（DoS）。

---

## 四、STRIDE-A 威胁分析

> 可利用性分层（Exploitability Tier）：
> - **Tier 1 直接暴露**：外部调用方可直接触发，无需前置条件。
> - **Tier 2 条件风险**：需满足特定条件（如凭证泄露、配置被改）。
> - **Tier 3 纵深防御**：属于内部强化项，被直接利用概率低。

### 4.1 Spoofing（伪装）

| ID | 威胁 | 描述 | 数据流 | Tier | 风险等级 |
|----|------|------|--------|------|----------|
| S-01 | APIG 签名重放 + 请求体篡改 | 已核实：`sign_request` 签名不覆盖请求体、无 nonce、时间戳仅分钟级。同一分钟内捕获的合法请求可在篡改请求体后重放，签名依然有效 | TB1 | Tier 1 | 高 |
| S-02 | 动态 Token 泄露后冒用 | Token 校验依赖远端 URL，Token 一旦泄露可在有效期内冒充调用方 | TB1 | Tier 2 | 中 |
| S-03 | Apollo 配置篡改致 `ENABLE_AUTH=false` | 攻击者改 Apollo 即可关闭鉴权 | TB5→TB1 | Tier 2 | 高 |
| S-04 | SSH 中间人（AutoAddPolicy） | 首次连接不校验主机指纹，内网 ARP 欺骗可劫持 SSH | TB2 | Tier 2 | 中 |
| S-05 | 宿主机运维账号被冒用 | NOPASSWD:ALL 权限，账号被攻陷即等同 root | TB2 | Tier 2 | 高 |
| S-06 | Harbor 凭证泄露后冒充推送 | `harbor_server_password` 经日志/内存流转，泄露后可推送恶意镜像 | TB3 | Tier 2 | 高 |

### 4.2 Tampering（篡改）

| ID | 威胁 | 描述 | 数据流 | Tier | 风险等级 |
|----|------|------|--------|------|----------|
| T-01 | 命令注入（docker run 参数） | 白名单前缀匹配，参数位仍可注入 `--privileged` 等危险选项 | TB2 | Tier 1 | 高 |
| T-02 | 路径穿越写公钥 | `write_public_key` 虽校验公钥格式，但目标路径若未充分校验，可写至宿主机敏感目录 | TB2 | Tier 2 | 中 |
| T-03 | create_container.sh 模板注入 | `is_custom_image` 等未校验参数进入 shell 模板 | TB2 | Tier 1 | 高 |
| T-04 | 软件包仓库篡改 | `fileserver` 无鉴权，`software/*/install.sh` 可被中间人替换 | TB7 | Tier 1 | 高 |
| T-05 | GlusterFS 卷数据篡改 | 共享存储未加密，节点被攻陷可篡改用户数据 | TB6 | Tier 2 | 中 |
| T-06 | Apollo 配置被篡改 | 配置中心单点，篡改可改变服务行为（如解密密钥、回调 URL） | TB5 | Tier 2 | 高 |
| T-07 | 日志被篡改 | `/var/log/hidevlab` 若权限过松，攻击者可擦除审计痕迹 | 内部 | Tier 3 | 中 |

### 4.3 Repudiation（抵赖）

| ID | 威胁 | 描述 | 数据流 | Tier | 风险等级 |
|----|------|------|--------|------|----------|
| R-01 | 异步任务无任务 ID 关联审计 | 部分异步函数未在日志中贯穿 task_id，事后无法追溯 | TB8 | Tier 2 | 中 |
| R-02 | `/os/ops/account/create` 假成功 | 路由返回 success 但未执行，审计日志与实际不一致 | TB2 | Tier 1 | 中 |
| R-03 | 日志 IP 哈希 salt 硬编码 | salt 泄露后无法可靠关联调用方 IP | 内部 | Tier 3 | 低 |
| R-04 | fileserver 无访问日志 | `python3 -m http.server` 默认输出 stdout，未记录访问者 | TB7 | Tier 2 | 中 |

### 4.4 Information Disclosure（信息泄露）

| ID | 威胁 | 描述 | 数据流 | Tier | 风险等级 |
|----|------|------|--------|------|----------|
| I-01 | 密码被日志记录 | `LOG.info(f"callback_data={callback_data}")` 可能含密码字段 | TB8 | Tier 1 | 高 |
| I-02 | 临时 SSL 文件残留 | `when_ready` 未触发时证书私钥残留磁盘 | 内部 | Tier 2 | 中 |
| I-03 | fileserver 未授权下载 | 静态服务无鉴权，`software/`、`script/` 可被遍历下载 | TB7 | Tier 1 | 高 |
| I-04 | 进程列表泄露凭证 | 虽 stdin 传密码，但 `docker login` 偶发回显、异常栈可能含密码 | TB2 | Tier 2 | 中 |
| I-05 | 错误信息回显 | 路由 `except Exception as exc: return {"msg": str(exc)}` 回显内部异常 | TB1 | Tier 1 | 中 |
| I-06 | IP 脱敏不彻底 | 部分路由（如 `set_vm_obs`）日志中直接出现 `host_ip`，未统一脱敏 | TB2 | Tier 2 | 中 |
| I-07 | 内存转储泄露明文密钥 | Python 字符串不可控回收，核心 dump 可暴露 SSL 私钥/密码 | 内部 | Tier 3 | 低 |

### 4.5 Denial of Service（拒绝服务）

| ID | 威胁 | 描述 | 数据流 | Tier | 风险等级 |
|----|------|------|--------|------|----------|
| D-01 | 异步线程爆炸 | 无任务上限的 `threading.Thread`，高频调用耗尽线程/SSH 连接 | TB1→TB8 | Tier 1 | 高 |
| D-02 | 容器资源耗尽 | 虽校验 CPU/RAM，但 `pids_limit` 上限未与宿主机总量联动 | TB6 | Tier 2 | 中 |
| D-03 | fileserver 日志打满磁盘 | `os.log` 无轮转 | TB7 | Tier 2 | 中 |
| D-04 | GlusterFS 清理锁死 | `_cleanup_member_ws_on_gfs_node` 使用 `flock`，异常退出未释放锁 | TB2 | Tier 2 | 中 |
| D-05 | 慢速 SSH 致请求超时 | paramiko 连接无超时或超时过长，gunicorn sync worker 阻塞 | TB2 | Tier 1 | 中 |

### 4.6 Elevation of Privilege（权限提升）

| ID | 威胁 | 描述 | 数据流 | Tier | 风险等级 |
|----|------|------|--------|------|----------|
| E-01 | 容器逃逸（危险 run 选项） | 若 `--privileged`/`--cap-add` 被注入，容器可逃逸至宿主机 | TB6 | Tier 1 | 高 |
| E-02 | 运维账号 NOPASSWD:ALL | 被攻陷即 root | TB2 | Tier 2 | 高 |
| E-03 | docker group 提权 | 若运维账号在 docker 组，可 `docker run -v /:/m ...` 挂载宿主根 | TB6 | Tier 2 | 高 |
| E-04 | Apollo 任意配置写入 | 攻击者改 Apollo 即可改服务行为，等同控制面提权 | TB5 | Tier 2 | 高 |
| E-05 | 路由级权限不一致 | `/os/ops/account/create` 等路由仅校验 Token，未校验调用者是否具备「建账号」权限 | TB1 | Tier 1 | 中 |

### 4.7 Abuse Cases（滥用案例）

| ID | 滥用场景 | 涉及威胁 | 严重度 |
|----|----------|----------|--------|
| A-01 | 攻击者高频调用 `/docker/image/publish`，传入大量 machines，触发数十个并发 SSH + Harbor push，耗尽宿主机资源 | D-01, D-05 | 高 |
| A-02 | 攻击者篡改 `software/` 中的 `install.sh`，诱导用户「重装软件」时执行恶意脚本 | T-04, I-03 | 高 |
| A-03 | 攻击者获取运维账号后，利用 NOPASSWD:ALL 执行 `docker run --privileged -v /:/host`，完全接管宿主机 | E-02, E-03 | 严重 |
| A-04 | 攻击者重放合法 APIG 签名请求（若无 nonce），重复触发容器删除/清理，造成业务数据丢失 | S-01, T-01 | 高 |
| A-05 | 攻击者通过 `fileserver` 未授权下载 `script/create_container.sh`，分析模板后构造针对性注入参数 | T-03, I-03 | 高 |
| A-06 | 内部人员改 Apollo 关闭 `ENABLE_AUTH`，随后直接调用 `/passwd/expire` 重置任意主机密码 | S-03, E-04 | 严重 |
| A-07 | 攻击者通过日志文件读取 `callback_data`，获取 Harbor 密码，推送恶意镜像至所有环境 | I-01, S-06 | 严重 |

---

## 五、威胁优先级矩阵

| 优先级 | 威胁 ID | 说明 |
|--------|---------|------|
| **P0 严重** | A-03, A-06, A-07, E-02, E-04 | 直接导致宿主机/控制面被接管 |
| **P1 高** | S-01, S-03, T-01, T-03, T-04, I-01, I-03, D-01, E-01, E-05, A-01, A-02, A-04, A-05 | 可被外部直接触发或造成大范围数据/服务影响 |
| **P2 中** | S-02, S-04, S-06, T-02, T-05, T-06, R-01, R-02, R-04, I-02, I-04, I-05, I-06, D-02, D-03, D-04, D-05, E-03 | 需特定条件触发或影响范围有限 |
| **P3 低** | R-03, I-07, T-07 | 纵深防御项，直接利用概率低 |

---

## 六、修复建议

### 6.1 P0/P1 短期修复（1-2 周内）

1. **收敛建议为 `subprocess.run(args=[...])` 结构化调用**，杜绝 shell 字符串拼装（针对 T-01, T-03, E-01）。
2. **关闭 `fileserver` 匿名访问**：改为带 Token 的 Flask 蓝图，或加 Nginx Basic Auth；启用 HTTPS；增加访问日志与轮转（针对 T-04, I-03, R-04, D-03, A-02, A-05）。
3. **复核并清理日志中的密码/凭证输出**：对 `callback_data`、`params` 等结构体日志引入脱敏中间件（针对 I-01, A-07）。
4. **修复 APIG 签名缺陷**：签名原文加入请求体摘要（body hash）与 nonce，服务端校验时间窗（如 5 分钟）与 nonce 去重（针对 S-01, A-04）。
5. **异步任务加全局信号量/队列**，限制并发 SSH 数与任务数；对幂等性强的操作加分布式锁（针对 D-01, A-01）。
6. **修复 `/os/ops/account/create` 路由**：补全真实创建逻辑或明确返回 501，避免假成功（针对 R-02）。
7. **收窄运维账号 sudo 权限**：`NOPASSWD: /usr/bin/docker, /usr/bin/systemctl restart clab-agent`，禁止 `ALL`（针对 E-02, A-03）。
8. **Apollo 配置变更审计**：对 `ENABLE_AUTH`、密钥相关项加变更告警 + 本地 fallback（启动期断言 `ENABLE_AUTH` 必须为 true）（针对 S-03, E-04, A-06）。

### 6.2 P2 中期加固（1 个月内）

1. **SSH 主机指纹校验**：预置 `known_hosts`，禁用 `AutoAddPolicy`（针对 S-04）。
2. **统一请求体解析为 `json.loads`**，移除 `ast.literal_eval`（针对 R-ROUTE-01）。
3. **入参类型/范围校验**：`host_port` 限 1-65535、`os_name` 枚举、`lab` 字符集白名单（针对 R-ROUTE-03）。
4. **SSL 配置硬化**：`min_version=TLSv1_2`、禁用弱套件；临时证书文件加 `atexit` 兜底删除（针对 R-SSL-01, R-SSL-02）。
5. **错误信息收敛**：对外仅返回通用错误码，内部异常仅入日志（针对 I-05）。
6. **日志 salt 动态化**：改为部署期生成的随机 salt，存于受保护文件（针对 R-03）。
7. **容器资源上限与宿主机联动**：`pids_limit` 按宿主机 PID 总量比例设置（针对 D-02）。
8. **GlusterFS 清理加超时与锁释放**：`flock` 加 `-w 60`，异常分支显式释放（针对 D-04）。
9. **Harbor 凭证使用一次性 Token / robots**：减少长期密码流转（针对 S-06）。

### 6.3 P3 长期优化

1. **密钥管理升级**：引入 HSM 或本地环境变量承载 root key，Apollo 仅存 work key（针对 R-DEC-01）。
2. **敏感字符串零拷贝**：对明文密钥使用 `bytearray` + 用后清零（针对 I-07）。
3. **日志权限基线**：`post_deploy.sh` 显式 `chmod 750 /var/log/hidevlab && chown root:adm`（针对 T-07）。
4. **引入 Open Policy Agent / Casbin**：对路由级权限做细粒度授权（针对 E-05）。

---

## 七、执行性与追踪

| 建议项 | 对应威胁 | 责任域 | 建议验收方式 |
|--------|----------|--------|--------------|
| 结构化命令调用 | T-01, T-03, E-01 | service/ | 单元测试：传入恶意参数应被拒 |
| fileserver 鉴权 + HTTPS | T-04, I-03 | deploy/ + 新增路由 | 未授权请求返回 401 |
| 日志脱敏中间件 | I-01, A-07 | base/logging_handler | grep 密码字段为空 |
| APIG nonce/timestamp | S-01, A-04 | base/auth_filter | 重放请求返回 401 |
| 异步任务限流 | D-01, A-01 | service/docker_manager | 压测：N+1 任务被拒 |
| `/os/ops/account/create` 修复 | R-02 | transport.py | 真实创建并返回账号状态 |
| sudo 权限收窄 | E-02, A-03 | tools/ssh.py | `sudo -l` 仅列白名单命令 |
| Apollo 配置变更审计 | S-03, E-04, A-06 | base/apollo_manager | 关键项变更触发告警 |
| SSH 指纹校验 | S-04 | tools/ssh.py | 首次连接需交互确认 |
| SSL 硬化 | R-SSL-01/02 | gunicorn_config.py | `nmap --ssl-enum` 无弱套件 |
| 错误信息收敛 | I-05 | transport.py | 异常响应无堆栈 |
| 密钥管理升级 | R-DEC-01 | base/decrypt.py | root key 不再来自 Apollo |

---

## 八、残余风险与说明

1. **本报告基于当前仓库静态分析**，未包含运行时插桩证据（如实际日志内容、Apollo 配置快照）。`sign_request` 签名机制已核实（不含 body、无 nonce，见 R-AUTH-03）；仍需结合生产环境确认 TOKEN_URL 的协议与证书校验策略。
2. **`docker_manager.py` 体量 133KB**，本次审查聚焦于命令执行、镜像发布、GlusterFS 清理等高风险路径，未穷举所有辅助函数。建议后续补充单元测试覆盖率门禁。
3. **`software/`、`script/` 目录内容**未逐个审查安装脚本，假定其可信度依赖 `fileserver` 鉴权与分发完整性，需在 P1 修复后复核。
4. **部署侧配置**（如 `/var/log/hidevlab` 权限、systemd unit 的 `User=root`）依赖运维基线，本报告给出建议但未实际校验生产环境。
5. 本报告不涉及对华为云 APIG、Apollo、Harbor、OBS 等外部服务自身漏洞的分析，仅关注其与 transport-service 的交互边界。

---

## 九、附录：审查覆盖文件清单

| 文件 | 审查深度 | 关键发现 |
|------|----------|----------|
| `transport.py` | 路由与入口全览 | R-ROUTE-01~04 |
| `service/docker_manager.py` | 高风险函数（exec_command、login、create、cleanup、publish） | R-DOCKER-01~06 |
| `tools/ssh.py` | Ssh 类、sudo_exec_command、create_ops_account | R-SSH-01~03 |
| `base/auth_filter.py` | auth_filter、sign_request | R-AUTH-01~03 |
| `base/decrypt.py` | decrypt、decryptbyroot | R-DEC-01~02 |
| `gunicorn_config.py` | SSL 加载、when_ready | R-SSL-01~02 |
| `transport.py.__main__` | 临时证书处理 | R-SSL-01 |
| `utils/command_security.py` | validate_command_ops、validate_path | R-CS-01~02 |
| `base/logging_handler.py` | JsonFormatter、operator 哈希 | R-LOG-01~02 |
| `fileserver.service` | 静态文件服务 | R-FS-01~02 |
| `service/pre_install.py` | 软件状态解析 | 无新增风险 |
| `base/common.py` | return_post | 无新增风险 |
| `transport.service` | systemd unit（User=root） | 建议非 root 运行（见 6.2） |
| `requirements.txt` | 依赖清单 | 建议补充 paramiko/flask/gunicorn 等显式版本约束 |

---

**报告结束。**
