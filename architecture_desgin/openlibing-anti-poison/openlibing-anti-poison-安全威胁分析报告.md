# 安全威胁分析报告：openlibing-anti-poison

| 项 | 内容 |
|---|---|
| 仓库路径 | `D:\skill\skill收集\repo\openlibing-anti-poison` |
| 分析日期 | 2026-09-02 |
| 分析方法 | 静态代码审计（STRIDE-A 威胁建模 + 配置/依赖/供应链检查） |
| 报告语言 | 中文 |
| 部署分类 | 容器化微服务（K8s 集群内，端口 8086，经网关/API 网关暴露部分接口），容器内附带 Python3 + yara-python 扫描引擎 |

---

## 一、系统概述

### 1.1 用途与技术栈

开源社区代码安全/投毒检测平台：提供仓库版本级扫描、PR 门禁扫描（Gitee/GitCode/GitLab）、YARA 规则管理、扫描结果导出。服务在扫描任务中会 **clone 外部仓库、通过 curl 下载 PR 差异文件、调用 python+yara 执行扫描**，是命令执行与外部输入处理最密集的服务。

- Java 21、Spring Boot 3.x、MyBatis(-Plus) + MySQL、MongoDB、Redis、Feign、Apollo 配置中心、JGit 7.3、fastjson2、OkHttp、Apache POI
- 容器：openEuler 基础镜像 + RASP agent，非 root 用户 `openlibing` 运行
- 入口：`OpenLiBingAntiPoisonApplication.java:29`；`Dockerfile:181` → `entrypoint.sh` → `start.sh`

### 1.2 组件与信任边界

| 组件 ID | 锚点 | 职责 | 信任边界 |
|---|---|---|---|
| PoisonPRController | `business/controller/PoisonPRController.java:47` | PR 门禁接口 `/poison-pr/**` | 外部/网关 → 服务 |
| PoisonVersionOpenController | `business/controller/PoisonVersionOpenController.java:38` | 版本扫描对外接口 | 外部 → 服务 |
| ActionPRController | `business/controller/action/ActionPRController.java:40` | Action 触发 `/action-pr/**` | CI Action → 服务（HMAC 网关） |
| CheckRuleController | `business/controller/CheckRuleController.java` | YARA 规则/规则集增删改查 | 网关 → 服务 |
| AntiServiceImpl | `business/service/impl/AntiServiceImpl.java` | clone 仓库、curl 下载 diff、调 python 扫描（**命令执行核心**） | 服务 → 容器 OS / 外部 Git 平台 |
| ActionPRServiceImpl | `business/service/action/ActionPRServiceImpl.java` | PR 任务处理、差异文件复制、拼 shell | 服务 → 容器 OS |
| JGitUtil | `common/util/JGitUtil.java:31` | git clone/checkout（shell 拼接） | 服务 → 容器 OS |
| ExecCmdUtil / CmdInjection / LinuxCommandInjectCheck | `common/utils/ExecCmdUtil.java`、`common/util/CmdInjection.java`、`common/utils/LinuxCommandInjectCheck.java:12` | 命令执行封装与黑名单校验 | 服务内 |
| HttpUtil / GiteeOrGitcodeApiUtil | `common/util/HttpUtil.java:32`、`common/util/GiteeOrGitcodeApiUtil.java:19` | 外部 HTTP 调用、HMAC 转发签名 | 服务 → 外部平台 |
| YaraScan | `tools/SoftwareSupplyChainSecurity-v1/yara_scan.py`、`openeuler_scan.py` | YARA 扫描脚本 | 容器内被调用 |
| MySQL / MongoDB / Redis | 配置于 Apollo | 业务数据、规则、缓存 | 数据存储边界 |
| ExternalActor | PR 提交者、Git 平台 API 响应 | 不可信输入（分支名、文件名、raw_url、diff 内容） | 外部攻击者 |

**关键信任边界**：① 外部 PR 元数据/平台 API 响应（`raw_url`、`new_path`、分支名、仓库名）→ 服务内拼接到 shell 命令 → 容器 OS 执行；② Action/外部调用 → 无服务内鉴权的业务接口；③ 密钥材料（`.ks`/`.pfx`）→ 容器镜像层。

---

## 二、STRIDE-A 威胁分析汇总

| STRIDE 类别 | 威胁数 | 代表性威胁 |
|---|---|---|
| S 仿冒 | 2 | 业务接口无服务内鉴权；外链 HMAC 签名恒用 null 密钥失效 |
| T 篡改 | 4 | shell 命令拼接注入；ExecCmdUtil 数组 join 回字符串；差异文件路径穿越写；构建期下载无校验 |
| R 抵赖 | 1 | 操作日志中 userId 取自请求参数，可伪造抵赖 |
| I 信息泄露 | 5 | git token 入命令行/异常日志；密钥烘焙镜像；Swagger 暴露；beta SQL 日志；路径 startsWith 越界读 |
| D 拒绝服务 | 2 | Actuator shutdown 暴露；扫描任务无线索限流可被刷爆（线程池 50~300） |
| E 权限提升 | 3 | 命令注入 RCE；越权篡改/删除规则；SSRF 打内网/元数据 |
| A 业务滥用 | 2 | 无鉴权发起扫描任务消耗资源；扫描他人仓库 |

### 关键威胁场景

**场景 1（E，RCE）**：攻击者控制 PR 内容或诱导平台 API 返回恶意 `raw_url`/`new_path`（`AntiServiceImpl.java:577,633,717`）→ `cmdOfCurl` 将其拼入 `curl ... <url>` 命令（`:825-835`）→ `Runtime.exec("/bin/sh","-c",cmd)`（`:591,647,722,773`）→ 黑名单仅校验 workspace/target 两个字段且未拦截引号/空格/`$(...)` → 容器内以 `openlibing` 用户执行任意命令 → 读取 `/keys/*.ks`、访问内网。

**场景 2（T/E，任意文件写）**：PR diff API 返回的 `filename` 由提交者控制（`ActionPRServiceImpl.java:665`）→ `new File(targetDir, fileName)` + `Files.copy`（`:688-694`）未做规范化校验 → `../../` 跳出工作目录覆盖扫描配置/脚本 → 结合命令执行实现持久化 RCE。

**场景 3（D）**：`POST /actuator/shutdown`（application.yaml:28-35 暴露且 enabled）匿名关闭服务。

---

## 三、安全发现明细

### 严重

#### FIND-01：PR 差异文件下载/扫描链路 Shell 命令注入（RCE）

| 属性 | 内容 |
|---|---|
| STRIDE | E（权限提升/RCE） |
| CWE | [CWE-78](https://cwe.mitre.org/data/definitions/78.html) OS 命令注入；[CWE-88](https://cwe.mitre.org/data/definitions/88.html) 参数注入 |
| OWASP | A03:2025 – Injection |
| 利用前提 | 能向被扫描仓库提交 PR（或污染内源 Git 平台 API 响应） |
| 证据 | `AntiServiceImpl.java:591/647/722/773` `Runtime.getRuntime().exec(new String[]{"/bin/sh","-c",cmd},null,null)`；`:825-835` curl 命令拼接 `info.getUser()/getPassword()/getWorkspace()/url`，其中 `url=json.getString("raw_url")`（:577/633/717）；`:578-579` 黑名单仅校验 workspace、target 两个字段；`LinuxCommandInjectCheck.java:13-14` 黑名单未拦截引号、空格、`$()`、反引号闭合等 |
| 风险 | 外部 PR 数据经 `/bin/sh -c` 执行，黑名单可绕过（引号闭合、`$(...)`、git 参数注入），导致容器内 RCE，进而窃取密钥、横向访问内网。 |
| 修复建议 | ① 禁止 `/bin/sh -c` 拼接，改用 `ProcessBuilder(String[])` 参数数组（curl 的 URL、`-o`、`-u` 各自独立参数，凭据用 `--netrc-file`）；② 所有进入命令的字段做白名单校验（URL 限定官方域名 + 字符白名单）；③ 迁移到 common 仓已有的 `SecureCmdExecutor`（白名单模板 + 参数化 + 超时）。 |
| 修复成本 | 高 |

#### FIND-02：PR 差异文件复制存在路径穿越（任意文件写）

| 属性 | 内容 |
|---|---|
| STRIDE | T / E |
| CWE | [CWE-22](https://cwe.mitre.org/data/definitions/22.html) 路径穿越 |
| OWASP | A01:2025 – Broken Access Control |
| 利用前提 | 能提交 PR（filename 可控） |
| 证据 | `ActionPRServiceImpl.java:665` `fileName = fileObj.getString("filename")`；`:684` `new File(repoDir, fileName)`；`:688` `new File(targetDir, fileName)`；`:694` `Files.copy(sourceFile, targetFile, REPLACE_EXISTING)`；全程无 normalize/边界校验；`:336` `normalizeBranch` 仅替换 `/`、`\`，未处理 `..` |
| 风险 | `../../` 形式文件名可跳出工作目录，将攻击者控制的仓库文件写到服务端任意可写路径（覆盖 yaml 配置、结果 json、定时脚本），结合 FIND-01 实现 RCE 持久化。 |
| 修复建议 | 对 fileName 做 `Path.normalize()` 并校验 `targetPath.startsWith(targetDir)`（严格到段边界）；拒绝含 `..`、绝对路径、控制字符的文件名；落盘文件名服务端重生成（UUID）。 |
| 修复成本 | 中 |

### 高危

#### FIND-03：`ExecCmdUtil` 字符串形式执行命令，数组参数被 join 回字符串

| 属性 | 内容 |
|---|---|
| STRIDE | E / I |
| CWE | [CWE-78](https://cwe.mitre.org/data/definitions/78.html)；[CWE-532](https://cwe.mitre.org/data/definitions/532.html) |
| OWASP | A03:2025；A09:2025 |
| 证据 | `common/utils/ExecCmdUtil.java:39-41` `Runtime.getRuntime().exec(cmd)`（字符串重载）；`:28-29` `executeCmdArray(String[]){ return executeCmd(String.join(" ", cmdArray)); }`；`:40` `log.info("cmd: {}", cmd)` 记录含凭据命令 |
| 风险 | 参数数组本可隔离注入，join 成整串后经 StringTokenizer 重新解析，防护失效；完整命令（含 `curl -u user:password`、git token）写入 info 日志。 |
| 修复建议 | 删除字符串重载，统一 `ProcessBuilder(String[])`；日志对凭据脱敏（user:password、token URL 模式打码）。 |
| 修复成本 | 中 |

#### FIND-04：git clone 命令拼接，凭据置于命令行/URL

| 属性 | 内容 |
|---|---|
| STRIDE | I / E |
| CWE | [CWE-78](https://cwe.mitre.org/data/definitions/78.html)；[CWE-522](https://cwe.mitre.org/data/definitions/522.html)；[CWE-214](https://cwe.mitre.org/data/definitions/214.html) |
| OWASP | A03:2025；A07:2025 |
| 证据 | `common/util/JGitUtil.java:143-153` `" git clone https://" + user + ":" + token + "@" + ... + " -b " + branch + " " + workspace` 经 `CmdInjection.runCmd`（`CmdInjection.java:81` `Runtime.exec(cmd, envArray)`）执行；`ActionPRServiceImpl.java:590-594` 同类拼接；`:730` 异常 `"command failed: " + command`（含 token URL）；`:265-266,644-645` token 放 URL query `?access_token=`；`AntiServiceImpl.java:825` `curl -u user:password` |
| 风险 | ① token 出现在进程命令行（`/proc/<pid>/cmdline`、ps 可见）；② 命令失败时含 token 的完整命令进入应用日志；③ URL query token 被代理/网关日志记录；④ branch/workspace 可注入。 |
| 修复建议 | 统一使用 JGit API + `UsernamePasswordCredentialsProvider`（仓内已有安全实现 `pullGiteeVersion`）；凭据走 git credential helper 或 `http.extraHeader`；异常日志脱敏；API 调用用 Authorization 头替代 query token。 |
| 修复成本 | 中 |

#### FIND-05：业务接口无服务内鉴权，userId 取自请求参数（越权）

| 属性 | 内容 |
|---|---|
| STRIDE | E / S |
| CWE | [CWE-306](https://cwe.mitre.org/data/definitions/306.html) 缺失认证；[CWE-639](https://cwe.mitre.org/data/definitions/639.html) 用户可控键越权 |
| OWASP | A01:2025 – Broken Access Control |
| 证据 | 全仓无 `SecurityFilterChain`/`HandlerInterceptor`/`@PreAuthorize`；`PoisonPRController.java:90`、`PoisonVersionOpenController.java:58`、`ActionPRController.java:71`、`CheckRuleController.java:97,155` 等敏感接口无鉴权注解；`CheckRuleController.java:99` 等用 `@RequestParam("userId") String userId` 直接取自请求 |
| 风险 | 鉴权完全依赖外层网关；服务被直连（容器网络/SSRF 反弹/网关路由误配）时，任何人可发起扫描、篡改/删除 YARA 规则集、伪造 userId 越权操作。 |
| 修复建议 | 服务内引入统一鉴权（JWT 过滤器/内部令牌），userId 从认证上下文获取而非请求参数；内部任务接口用签名 + 共享密钥并 fail-close；默认拒绝。 |
| 修复成本 | 高 |

#### FIND-06：Actuator `shutdown` 端点暴露并启用

| 属性 | 内容 |
|---|---|
| STRIDE | D |
| CWE | [CWE-732](https://cwe.mitre.org/data/definitions/732.html) 不安全权限分配；[CWE-400](https://cwe.mitre.org/data/definitions/400.html) |
| OWASP | A05:2025 – Security Misconfiguration |
| 证据 | `src/main/resources/application.yaml:28-35` `management.endpoints.web.exposure.include: shutdown,health,info` 且 `endpoint.shutdown.enabled: true` |
| 风险 | `POST /actuator/shutdown` 可远程关闭服务（无服务内鉴权时即匿名 DoS）。 |
| 修复建议 | 移除 shutdown 暴露或 `enabled: false`；actuator 独立管理端口、绑定内网、加鉴权；`include` 最小化为 health,info。 |
| 修复成本 | 低 |

### 中危

#### FIND-07：外链转发 HMAC 签名逻辑失效（恒用 null 密钥）

- STRIDE：S ｜ CWE：[CWE-345](https://cwe.mitre.org/data/definitions/345.html) 数据真实性校验不足 ｜ OWASP：A02:2025
- 证据：`common/util/HttpUtil.java:139-144` `String secretKey = null; SecurityUtil.decrypt(KEY, part1);`（返回值丢弃）→ `HmacUtil.getBase64HmacSHA256(secretKey, message)` 用 null 计算签名。
- 风险：服务间 AK/SK 校验形同虚设，可伪造 `appid/timestamp/sign` 调用内部转发接口。
- 建议：`secretKey = SecurityUtil.decrypt(...)` 并判空；修正后回归验证。
- 修复成本：低

#### FIND-08：SSRF——外部 URL 用于 HTTP 请求与 curl 下载

- STRIDE：I / E ｜ CWE：[CWE-918](https://cwe.mitre.org/data/definitions/918.html) SSRF ｜ OWASP：A10:2025
- 证据：`GiteeOrGitcodeApiUtil.java:50` `new HttpUtil(params.get("url") + url)`（base url 由请求体 prUrl 派生）；`AntiServiceImpl.java:835` `curl --create-dir <raw_url>`，raw_url 来自 PR diff API，curl 默认跟随重定向。
- 风险：可让服务端请求 `169.254.169.254`（云元数据）、内网地址、`file://` 等，探测内网/窃取凭据。
- 建议：域名白名单（仅 gitee.com/gitcode.com/gitlab 官方域名）；禁止重定向到非白名单主机；禁用 file/gopher 协议；解析后校验 IP 非内网/链路本地。
- 修复成本：中

#### FIND-09：路径校验使用 `startsWith` 前缀匹配，可被同前缀目录绕过

- STRIDE：I / T ｜ CWE：[CWE-22](https://cwe.mitre.org/data/definitions/22.html) ｜ OWASP：A01:2025
- 证据：`common/util/AntiMainUtil.java:143-145` `path.startsWith(homePath)`；`AntiServiceImpl.java:806` 同模式；`AntiMainUtil.java:113` 拼接处缺 `File.separator`。
- 风险：`/opt/app/x-evil/` 等同前缀路径可绕过边界判断。
- 建议：canonical 后 `path.equals(base) || path.startsWith(base + File.separator)`；文件名白名单。
- 修复成本：低

#### FIND-10：MyBatis `${tableName}` 表名拼接（当前不可利用，模式危险）

- STRIDE：E / I ｜ CWE：[CWE-89](https://cwe.mitre.org/data/definitions/89.html) SQL 注入 ｜ OWASP：A03:2025
- 证据：`mapper/GetLogsMapper.xml:7` `insert into ${tableName}`；tableName 现来自 `@LogApi(tableName=...)` 注解常量。
- 风险：一旦后续有请求参数流入表名即形成 SQL 注入。
- 建议：表名服务端白名单/枚举映射，禁止 `${}` 接收外部值。
- 修复成本：低

#### FIND-11：beta 环境 MyBatis SQL 全量 stdout 日志

- STRIDE：I ｜ CWE：[CWE-532](https://cwe.mitre.org/data/definitions/532.html) ｜ OWASP：A09:2025
- 证据：`application-beta.yaml:9` `log-impl: StdOutImpl`（prod 已为 NoLoggingImpl）。
- 风险：SQL 及参数（可能含 token、账号）输出到容器标准输出/日志平台。
- 建议：beta 同样关闭 StdOutImpl；敏感字段脱敏。
- 修复成本：低

#### FIND-12：fastjson safeMode JVM 参数对 fastjson2 无效（虚假安全感）

- STRIDE：T ｜ CWE：[CWE-1188](https://cwe.mitre.org/data/definitions/1188.html) ｜ OWASP：A06:2025
- 证据：`start.sh:40` `-Dfastjson.parser.safeMode=true`（fastjson1 参数），项目实际使用 fastjson2 2.0.56。
- 风险：给人"已关闭 autoType"的错误安全感；fastjson2 默认不开启 autoType 风险较低，但参数无效。
- 建议：改为 `-Dfastjson2.parser.safeMode=true`；代码中避免解析不可信 JSON 为 Object。
- 修复成本：低

### 低危 / 信息

#### FIND-13：密钥/证书文件烘焙进容器镜像层

- STRIDE：I ｜ CWE：[CWE-540](https://cwe.mitre.org/data/definitions/540.html)、[CWE-312](https://cwe.mitre.org/data/definitions/312.html) ｜ OWASP：A07:2025
- 证据：`Dockerfile:36-44` COPY `tcpFile.ks/tcsFile.ks/tcwFile.ks/openlibing.pfx/cacerts` 入镜像（三段式根密钥组件 + TLS 证书）。
- 风险：能 pull/导出镜像者可从镜像层提取 `.ks/.pfx`，结合硬编码 part1 可还原工作密钥，解密数据库中 AES 存储的 token/密码。
- 建议：密钥运行时经 KMS/K8s Secret（tmpfs）挂载，不烘焙进镜像；轮换已泄露密钥。
- 修复成本：中

#### FIND-14：构建期下载 JRE/pip 依赖无完整性校验

- STRIDE：T ｜ CWE：[CWE-494](https://cwe.mitre.org/data/definitions/494.html) 下载代码未校验完整性 ｜ OWASP：A08:2025
- 证据：`Dockerfile:92-93` wget 动态"最新"JRE tarball 后直接 `tar -zxvf`，无 checksum；`:75` `pip3 install ... --trusted-host pypi.tuna...`。
- 建议：固定版本并校验 SHA256/签名；移除 `--trusted-host`。
- 修复成本：低

#### FIND-15：Swagger/OpenAPI 生产环境暴露

- STRIDE：I ｜ CWE：[CWE-1059](https://cwe.mitre.org/data/definitions/1059.html) ｜ OWASP：A05:2025
- 证据：common 依赖引入 `springdoc-openapi-starter-webmvc-ui`，本服务接口均带 `@Operation`，未见生产关闭配置。
- 建议：生产 `springdoc.swagger-ui.enabled=false`、`api-docs.enabled=false`。
- 修复成本：低

#### FIND-16：start.sh / entrypoint.sh 变量未引用与语法缺陷

- STRIDE：T ｜ CWE：[CWE-78](https://cwe.mitre.org/data/definitions/78.html)（纵深防御不足）｜ OWASP：A05:2025
- 证据：`start.sh:37-45` JVM 参数变量未引用；`:65` `kill -9 $(springboot_pid)`；`:76` `[` 后缺空格（功能 bug）。
- 建议：JVM 参数用数组；`"$pid"` 加引号；修复语法。
- 修复成本：低

### 正面安全实践（已核实）

- Python 扫描脚本 `yara_scan.py:22` 使用 `yaml.safe_load`，未发现 `os.system/subprocess(shell=True)/eval/pickle`；`run-mvn.py:93-99` 用 `subprocess.run(cmd_list)` 数组形式、凭据走环境变量；`.mvn/settings.xml` 私仓凭据用 `${env}` 占位。
- 数据库/Redis/gitee 凭据不在 yaml 明文，由 Apollo 下发并经 Jasypt/`SecurityUtil.decrypt` 解密；SnakeYAML 均用 `SafeConstructor`（`YamlUtil.java:104-106,137,240`）。
- 容器非 root 运行（`Dockerfile:175`）、umask 077、SSH 加固、删除编译器/调试器、RASP agent；logback 对 `\r\n` 做替换防日志伪造。
- 依赖版本整体较新（Spring 6.2.x/Boot 3.5.x/fastjson2 2.0.56/log4j 2.25.4），未见 log4shell/shiro/fastjson1 等老牌高危组件。

---

## 四、行动摘要（整改优先级）

### Quick Wins（低成本快速修复）

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-06 | 移除/关闭 actuator shutdown 暴露 | 低 |
| FIND-07 | 修复 HttpUtil 签名 secretKey 丢弃 bug | 低 |
| FIND-09 | 路径校验改 canonical + 段边界 startsWith | 低 |
| FIND-11 | beta 关闭 SQL stdout 日志 | 低 |
| FIND-12 | fastjson safeMode 参数改为 fastjson2 | 低 |
| FIND-15 | 生产关闭 Swagger | 低 |

### 需专项处理

| 编号 | 事项 | 成本 |
|---|---|---|
| FIND-01 | 命令执行全面迁移 ProcessBuilder 参数数组 / SecureCmdExecutor，字段白名单 | 高 |
| FIND-02 | 差异文件复制路径穿越修复（normalize + 边界校验 + UUID 落盘） | 中 |
| FIND-03/04 | ExecCmdUtil/JGitUtil 命令执行与凭据处理重构 | 中 |
| FIND-05 | 服务内统一鉴权、userId 服务端化 | 高 |
| FIND-08 | SSRF 域名白名单 + 内网 IP 校验 | 中 |
| FIND-13 | 密钥从镜像剥离改 KMS/Secret 挂载并轮换 | 中 |
| FIND-14 | 构建制品完整性校验 | 低 |

---

## 五、分析假设与需验证项

1. 本报告为静态分析；网关/API 网关是否对 `/action-pr/**`、`/poison-pr/**` 做了 HMAC 签名校验与限流需在运行环境确认（若网关兜底，FIND-05 的外部可利用性降低，但服务内纵深防御仍缺失）。
2. Apollo 实际下发的配置（`security.part1`、凭据、开关值）未在仓内，需在运行环境核验密钥轮换与配置访问控制。
3. `Dockerfile` 引用的 `.ks/.pfx` 文件当前不在仓内（靠 CI 注入），但镜像层是否含密钥需对实际构建产物核验。
4. 线程池/队列（core 50/max 300/队列 1000）的限流与任务归属校验需结合压测验证 DoS 阈值。

## 六、参考标准

- STRIDE-A 威胁建模；OWASP Top 10:2025；CWE/MITRE；CIS Docker/K8s 基线；OWASP Cheat Sheet（命令注入、SSRF、路径穿越）。
