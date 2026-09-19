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
inputs: scan-target(默认.) / severity(默认HIGH,CRITICAL) / ignore-vuln-count(0)
        / ignore-license-count(0) / trivy-config / cache-dir / debug

run():
 1. 解析 inputs + ATOMGIT_REPOSITORY/REFSAPP
 2. 校验 trivy 存在（execFileSync('trivy','--version')）
 3. 执行扫描:
    trivy fs --skip-version-check
             --scanners vuln,license
             --severity HIGH,CRITICAL,MEDIUM,LOW,UNKNOWN  (对齐 scan_vuls.sh)
             --config <trivy-config 或 runner 预置>
             --cache-dir <cache-dir>
             --format json --output <tmp>/result.json <scan-target>
    不传 --skip-db-update：trivy 检测到缓存库过期时自动联网更新（对齐原脚本，保证库常新）
    （失败重试 10 次，间隔 1s，对齐 scan_vuls.sh MAX_RETRIES）
 4. 解析 result.json:
    HIGH_CRITICAL_VULN = sum(.Results[]?.Vulnerabilities[] where Severity in [HIGH,CRITICAL])
    HIGH_CRITICAL_LICENSE = sum(.Results[]?.Licenses[] where Severity in [HIGH,CRITICAL])
    （空 Results / 缺字段按 0 处理，对齐 jq '.Results[]? ...' 空保护）
 5. 判定（对齐 scan_vuls.sh 第 85 行）:
    if 双计数均为 0 -> pass
    elif vuln < ignore_vuln_count && license < ignore_license_count -> pass
    else -> no pass
 6. Step Summary: 扫描信息表 + ✅/❌ 结论 + 明细表（漏洞/license 各一张）
 7. no pass -> core.setFailed，阻断工作流
```

## 细节对齐 scan_vuls.sh

| scan_vuls.sh                                             | 插件实现                                  |
| -------------------------------------------------------- | ----------------------------------------- |
| `--severity HIGH,CRITICAL,MEDIUM,LOW,UNKNOWN`            | 扫描全 severity；判定只统计 HIGH/CRITICAL |
| `--scanners vuln,license`                                | 相同                                      |
| 结果文件 `result-${codeBranch}-${TIMESTAMP}.json`        | tmp 目录 result.json                      |
| `jq '.Results[]? ... .Severity == "HIGH" or "CRITICAL"'` | JS 遍历等价；`?` 空保护 = null/empty 安全 |
| `[ -z "$count" ] → 0`                                    | JS 缺省/NaN → 0                           |
| `count < IGNORE_COUNT`（严格小于）                       | 相同（`<` 而非 `<=`）                     |
| 重试 10 次间隔 1s                                        | 相同                                      |
| `exit 1` 阻断                                            | `core.setFailed`                          |

## 输入参数默认值

| 参数                   | 默认值（action.yml）                                               |
| ---------------------- | ------------------------------------------------------------------ |
| `ignore-vuln-count`    | `0`                                                                |
| `ignore-license-count` | `0`                                                                |
| `scan-target`          | `.`                                                                |
| `trivy-config`         | `/opt/cached_resources/trivy_db/trivy.yaml`（存在才加 `--config`） |
| `cache-dir`            | `/opt/cached_resources/trivy_db`（存在才加 `--cache-dir`）         |
| `debug`                | `false`                                                            |

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

## 待确认问题（开发中遗留，需用户拍板）

| #   | 问题                                            | 现状 / 选项                                                                                           |
| --- | ----------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 1   | PR 级执行机 `runs-on` 标签                      | 7dbc 未注册 runner；建议 `["self-hosted","region=overseas","oss-scan"]`（待确认实际标签）             |
| 2   | `ignore-unfixed: true` 是否保留                 | 原脚本 trivy.yaml 预置 `true`；插件加载同一份 yaml 保持对齐。若需报无修复漏洞，需插件显式覆盖         |
| 3   | 漏洞库自动更新时机与网络                        | 已改由 trivy 自动更新（不传 skip-db-update）；PR 机需可访问下载源（ghcr.io），实测 a959 可下载        |
| 4   | 版本级插件是否同期开发                          | 用户已确认同仓增加 `oss-version-scan-action`，共享核心逻辑，仅差异（分支全量 vs 预合并/是否建 issue） |
| 5   | 多分支 workflow（master 本仓 vs main 多仓测试） | master 只扫本仓；main 保留多仓 `workflow_dispatch` 测试能力（含跨仓 checkout + ROBOT_TOKEN）          |

## 风险 & 缓解

| 风险                    | 缓解                                                                                                     |
| ----------------------- | -------------------------------------------------------------------------------------------------------- |
| trivy JSON 结构版本差异 | 用 null-safe 遍历 + 字段缺省兜底；单测 mock 真实结构                                                     |
| 扫描大仓耗时            | runner 本地执行、skip-version-check；库过期时首次会自动下载（几秒~几十秒）；超时由 workflow timeout 兜底 |
| trivy 未预装            | 启动前 `trivy --version` 探测，缺失则报清晰错误（提示 runner 需预置）                                    |
| 预合并分支扫描语义      | checkout 默认预合并分支，与 scan_vuls.sh 预合并逻辑等价                                                  |
| 漏洞库自动更新依赖网络  | 已对齐原脚本（不传 skip-db-update）；PR 机需可访问 ghcr.io，否则需内网镜像策略                           |

## 跨仓影响

- 生产仓（openlibing/*）**不受影响**——本插件在 `openlibing-test` 测试组织开发验证。
- 未来接入生产：在各目标仓 `.gitcode/workflows/` 增加 `pull_request` workflow 引用本插件即可。
