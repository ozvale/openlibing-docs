# oss-pr-scan-action — 技术设计

## 方案概述

将 `openlibing-ci/scan/opensource/scan_vuls.sh`（trivy fs 扫描 + jq 统计 + 阈值判定）
迁移为一个自包含的 GitCode `node16` Action 插件。插件在工作流以
`uses: openlibing-test/oss-scan-action/oss-pr-scan-action@master` 方式调用，
在 runner 本地执行 trivy 扫描并输出门禁判定。

## 架构决策

| 决策          | 选择                                                                                   | 原因                                                                          |
| ------------- | -------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------- |
| 插件形态      | `node16` + `dist/index.js`（ncc 打包）                                                 | 与 malicious-code / sca / pre-commit 插件一致，GitCode 当前仅支持 node16      |
| 调 trivy 方式 | `child_process.execFileSync` 调 runner 预装 trivy                                      | 对齐 pre-commit-action 的 node 调 CLI 范式；runner 已预装 trivy+漏洞库        |
| 认证          | 无 OIDC / 无 AK/SK                                                                     | 本地 trivy 扫描不调平台 API，无需凭据，规避 OIDC 白名单问题                   |
| 代码获取      | `checkout` 插件（平台自动注入 token）                                                  | `pull_request` 事件默认检出预合并分支，无需明文 git 凭据                      |
| 漏洞库        | 复用 runner 预置 `cache-dir`；**不传 `--skip-db-update`，过期时由 trivy 自动联网更新** | 与原脚本 scan_vuls.sh 一致；保证漏洞库常新，无需人工定期下载                  |
| 结果输出      | Step Summary（`ATOMGIT_STEP_SUMMARY`）                                                 | 平台支持，展示扫描信息 + 结论 + 明细                                          |
| 共享核心      | 抽取 `shared/index.js`，PR/version 复用                                                | 两插件逻辑一致（版本级不建 issue 后），单一维护点；PR 级重构为薄入口引 shared |

## 涉及文件

| 文件                                 | 操作              | 说明                                    |
| ------------------------------------ | ----------------- | --------------------------------------- |
| `shared/index.js`                    | 新增（抽取）      | 共享门禁引擎（扫描/解析/判定/summary）  |
| `oss-pr-scan-action/action.yml`      | 新增              | 插件元数据（inputs/runs）               |
| `oss-pr-scan-action/index.js`        | 新增→重构为薄入口 | 引 shared，行为不变                     |
| `oss-pr-scan-action/package.json`    | 新增              | `@actions/core` + `@vercel/ncc`         |
| `oss-pr-scan-action/dist/index.js`   | 新增（构建产物）  | ncc 打包结果（内联 shared+core）        |
| `oss-pr-scan-action/test/*.test.js`  | 新增              | 核心逻辑单测（改引 shared，mock trivy） |
| `oss-pr-scan-action/README.md`       | 新增              | 使用文档                                |
| `.gitcode/workflows/oss-pr-scan.yml` | 新增              | 本仓自测 workflow（会用插件扫自己）     |
| `.pre-commit-config.yaml`            | 新增              | 代码规范钩子（对标 malicious-code 仓）  |

## 核心逻辑（index.js）

```
inputs: scan-target(默认.) / trivy-config / cache-dir / debug
        / vuln-critical-limit(0) / vuln-high-limit(0)
        / vuln-medium-limit(1000) / vuln-low-limit(1000)
        / license-critical-limit(0) / license-high-limit(0)
        / license-medium-limit(1000) / license-low-limit(1000)

run():
 1. 解析 inputs + ATOMGIT_REPOSITORY/REFSAPP
 2. 校验 trivy 存在（execFileSync('trivy','--version')）
 3. Maven 依赖预解析（方案 A）:
    找 scanTarget 下含 pom.xml 的工程根目录（findMavenProjectDir，浅层递归，
    排除 .git/node_modules/target/dist 等）；
    存在时先 `mvn -o -q -B dependency:resolve`（离线，优先本地 ~/.m2），
    失败再 `mvn -q -B dependency:resolve`（在线）；超时 600s；
    mvn 缺失/无可用依赖仓库/全程失败/超时 → 降级（打日志，不阻断门禁）
 4. 执行扫描:
    trivy fs --skip-version-check
             --scanners vuln,license
             --severity HIGH,CRITICAL,MEDIUM,LOW,UNKNOWN  (对齐 scan_vuls.sh)
             --config <trivy-config 或 runner 预置>
             --cache-dir <cache-dir>
             --format json --output <tmp>/result.json <scan-target>
    不传 --skip-db-update：trivy 检测到缓存库过期时自动联网更新（对齐原脚本，保证库常新）
    （失败重试 10 次，间隔 1s，对齐 scan_vuls.sh MAX_RETRIES）
 5. 解析 result.json（四级别计数）:
    counts.vulnCounts = { CRITICAL, HIGH, MEDIUM, LOW } 各级别漏洞数
    counts.licenseCounts = { CRITICAL, HIGH, MEDIUM, LOW } 各级别 license 数
    vulnItems/licenseItems = 仅 HIGH/CRITICAL 明细
    （UNKNOWN 不统计；空 Results / 缺字段按 0 处理，含空保护）
 6. 判定（四级别门禁）:
    block = (CRITICAL|HIGH 漏洞 > 对应门禁) || (CRITICAL|HIGH license > 对应门禁)
    warnExceeded = (MEDIUM|LOW 漏洞 > 对应门禁) || (MEDIUM|LOW license > 对应门禁)
    pass = !block        （warnExceeded 仅提示、不阻断）
 7. Step Summary: 扫描信息表 + 四级别计数表 + ✅/❌ 结论 + CRITICAL/HIGH 明细表
    （MEDIUM/LOW 超门禁时追加提示行）
 8. no pass -> core.setFailed，阻断工作流
```

## 细节对齐 scan_vuls.sh

| scan_vuls.sh                                             | 插件实现                                        |
| -------------------------------------------------------- | ----------------------------------------------- |
| `--severity HIGH,CRITICAL,MEDIUM,LOW,UNKNOWN`            | 扫描全部 severity；按四级别计数                 |
| `--scanners vuln,license`                                | 相同                                            |
| 结果文件 `result-${codeBranch}-${TIMESTAMP}.json`        | tmp 目录 result.json                            |
| `jq '.Results[]? ... .Severity == "HIGH" or "CRITICAL"'` | JS 按级别遍历等价；`?` 空保护 = null/empty 安全 |
| `[ -z "$count" ] → 0`                                    | JS 缺省/NaN → 0                                 |
| `count < IGNORE_COUNT`（严格小于）                       | 四级别门禁：`count > limit` 判定超限            |
| 重试 10 次间隔 1s                                        | 相同                                            |
| `exit 1` 阻断                                            | `core.setFailed`                                |

## 输入参数默认值

| 参数                     | 默认值（action.yml）                                               |
| ------------------------ | ------------------------------------------------------------------ |
| `vuln-critical-limit`    | `0`（>门禁阻断）                                                   |
| `vuln-high-limit`        | `0`（>门禁阻断）                                                   |
| `vuln-medium-limit`      | `1000`（>门禁仅提示）                                              |
| `vuln-low-limit`         | `1000`（>门禁仅提示）                                              |
| `license-critical-limit` | `0`（>门禁阻断）                                                   |
| `license-high-limit`     | `0`（>门禁阻断）                                                   |
| `license-medium-limit`   | `1000`（>门禁仅提示）                                              |
| `license-low-limit`      | `1000`（>门禁仅提示）                                              |
| `scan-target`            | `.`                                                                |
| `trivy-config`           | `/opt/cached_resources/trivy_db/trivy.yaml`（存在才加 `--config`） |
| `cache-dir`              | `/opt/cached_resources/trivy_db`（存在才加 `--cache-dir`）         |
| `debug`                  | `false`                                                            |

## 执行机 trivy 环境确认（2026-09-16 实测）

| 项                                        | 版本级机 ecs-vul-a959                              | PR 级机 ecs-2176-7dbc               |
| ----------------------------------------- | -------------------------------------------------- | ----------------------------------- |
| trivy                                     | 0.69.0 @ `/usr/local/bin`                          | 0.69.1 @ `/usr/bin`（apt 安装）     |
| 默认缓存库 `~/.cache/trivy`               | 有（3-19 旧库）                                    | 空                                  |
| 插件用库 `/opt/cached_resources/trivy_db` | 有（9-16，1.3G）                                   | 有（9-18，1.4G）                    |
| 漏洞库自动更新                            | trivy 默认：不带 `--skip-db-update` 时过期自动下载 | 同左（9-18 为新，无额外 cron/脚本） |
| `ignore-unfixed`                          | `true`（trivy.yaml 预置）                          | `true`（同）                        |

> 诊断结论：`trivy --version` 读的是**默认缓存**（`~/.cache/trivy`），与插件扫描用的
> `/opt/cached_resources/trivy_db` **不是同一个库**。曾误判"a959 库旧"——实际 a959 插件库
> 为 9-16 新库。两机均**无独立自动更新机制**，库变新源于"运行 trivy 且不带 `--skip-db-update`"
> 时触发的自动下载；插件已对齐该行为（不传 `--skip-db-update`）。

## 运行时依赖解析漏检问题（2026-09-20 定位，方案 A 修复）

### 现象

同一份代码（head 370058a8）在 nightly 流水线 oss-version-scan：RUN9 扫出 9 个高危并
FAILED，RUN12/13 却 0 漏洞 COMPLETED（漏检放行）。oss-pr-scan 同理（RUN1 9 个 vs RUN3 0 个）。
用户最初观察为"更新漏洞库那次能扫出，nightly 不更新就扫不出"。

### 根因（官方文档 + --debug 日志取证）

- trivy 扫 pom.xml 时，依赖解析顺序为：项目目录 → relativePath → 本地 `~/.m2/repository` → 远程
  `<repositories>` → **Maven Central**（`repo.maven.apache.org`）。每个依赖需拉取自身 `.pom`
  递归解析出传递依赖。
- 两执行机**无 `~/.m2`、无 mvn、无构建产物**，只能实时访问公共 Maven Central。
- `--debug` 日志实锤：`[pom] Failed to fetch ... statusCode=404`（openlibing-common 等私有构件
  本就不在公共仓库）+ 大量 `statusCode=429`（同一秒并发拉取触发服务端**限流**）+ `Repository
error ... not found in local/remote repositories`。
- 结果：传递依赖（CVE 主要分布处）解析不出 → 包数 10（仅直接依赖）、indirect=0、漏洞 0。
- "更新漏洞库那次能扫出"是**时序巧合**：下载库的 60~90s 窗口恰好没撞限流；漏洞库与依赖解析是
  **两条独立网络线**，无因果关系。

### 修复（方案 A：扫描前 mvn 预解析）

- 扫描目标含 pom.xml → `mvn dependency:resolve`（先离线 `-o` 后在线）填充 `~/.m2`，
  trivy 从本地仓库解析完整传递依赖。
- 执行机需装 JDK+Maven 并配置内网私仓（settings.xml），a959 已验证效果：包数 10→255、
  indirect 0→245、漏洞 0→50。
- 降级语义：mvn 缺失/失败/超时不阻断门禁，仅退回旧行为。commit `8cc3159`。

### 执行机环境补充（方案 A 新增要求）

| 项           | a959（版本级）                                       | 7dbc（PR 级） |
| ------------ | ---------------------------------------------------- | ------------- |
| JDK          | 17 @ `/usr/local/jdk-17`                             | 待同步        |
| Maven        | 3.9.9 @ `/opt/apache-maven-3.9.9`                    | 待同步        |
| settings.xml | 华为云 ArtGalaxy 私仓 + huaweicloud mirror（已配置） | 待同步        |
| `~/.m2`      | 已填充（dependency:resolve 全量）                    | 待填充        |

## 待确认问题（开发中遗留，需用户拍板）

| #   | 问题                                            | 现状 / 选项                                                                                           |
| --- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 1   | PR 级执行机 `runs-on` 标签                      | 7dbc 未注册 runner；建议 `["self-hosted","region=overseas","oss-scan"]`（待确认实际标签）             |
| 2   | `ignore-unfixed: true` 是否保留                 | 原脚本 trivy.yaml 预置 `true`；插件加载同一份 yaml 保持对齐。若需报无修复漏洞，需插件显式覆盖         |
| 3   | 漏洞库自动更新时机与网络                        | 已改由 trivy 自动更新（不传 skip-db-update）；PR 机需可访问下载源（ghcr.io），实测 a959 可下载        |
| 4   | 版本级插件是否同期开发                          | 用户已确认同仓增加 `oss-version-scan-action`，共享核心逻辑，仅差异（分支全量 vs 预合并/是否建 issue） |
| 5   | 多分支 workflow（master 本仓 vs main 多仓测试） | master 只扫本仓；main 保留多仓 `workflow_dispatch` 测试能力（含跨仓 checkout + ROBOT_TOKEN）          |

## 风险 & 缓解

| 风险                    | 缓解                                                                                                                                                   |
| ----------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------ |
| trivy JSON 结构版本差异 | 用 null-safe 遍历 + 字段缺省兜底；单测 mock 真实结构                                                                                                   |
| 扫描大仓耗时            | runner 本地执行、skip-version-check；库过期时首次会自动下载（几秒~几十秒）；超时由 workflow timeout 兜底                                               |
| trivy 未预装            | 启动前 `trivy --version` 探测，缺失则报清晰错误（提示 runner 需预置）                                                                                  |
| 预合并分支扫描语义      | checkout 默认预合并分支，与 scan_vuls.sh 预合并逻辑等价                                                                                                |
| 漏洞库自动更新依赖网络  | 已对齐原脚本（不传 skip-db-update）；PR 机需可访问 ghcr.io，否则需内网镜像策略                                                                         |
| pom 传递依赖解析漏检    | 公共 Maven Central 高并发限流(429) + 私有构件 404 → 间接依赖漏洞漏检；扫描前 `mvn dependency:resolve` 预填充 `~/.m2`（方案 A，先离线后在线，失败降级） |

## 跨仓影响

- 生产仓（openlibing/*）**不受影响**——本插件在 `openlibing-test` 测试组织开发验证。
- 未来接入生产：在各目标仓 `.gitcode/workflows/` 增加 `pull_request` workflow 引用本插件即可。
