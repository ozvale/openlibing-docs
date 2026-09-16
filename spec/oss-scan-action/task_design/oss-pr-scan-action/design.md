# oss-pr-scan-action — 技术设计

## 方案概述

将 `openlibing-ci/scan/opensource/scan_vuls.sh`（trivy fs 扫描 + jq 统计 + 阈值判定）
迁移为一个自包含的 GitCode `node16` Action 插件。插件在工作流以
`uses: openlibing-test/oss-scan-action/oss-pr-scan-action@master` 方式调用，
在 runner 本地执行 trivy 扫描并输出门禁判定。

## 架构决策

| 决策          | 选择                                              | 原因                                                                     |
| ------------- | ------------------------------------------------- | ------------------------------------------------------------------------ |
| 插件形态      | `node16` + `dist/index.js`（ncc 打包）            | 与 malicious-code / sca / pre-commit 插件一致，GitCode 当前仅支持 node16 |
| 调 trivy 方式 | `child_process.execFileSync` 调 runner 预装 trivy | 对齐 pre-commit-action 的 node 调 CLI 范式；runner 已预装 trivy+漏洞库   |
| 认证          | 无 OIDC / 无 AK/SK                                | 本地 trivy 扫描不调平台 API，无需凭据，规避 OIDC 白名单问题              |
| 代码获取      | `checkout` 插件（平台自动注入 token）             | `pull_request` 事件默认检出预合并分支，无需明文 git 凭据                 |
| 漏洞库        | 复用 runner 预置 `cache-dir`，不联网更新          | 与原脚本一致，免首次大库下载、离线快速                                   |
| 结果输出      | Step Summary（`ATOMGIT_STEP_SUMMARY`）            | 平台支持，展示扫描信息 + 结论 + 明细                                     |

## 涉及文件

| 文件                                 | 操作             | 说明                                   |
| ------------------------------------ | ---------------- | -------------------------------------- |
| `oss-pr-scan-action/action.yml`      | 新增             | 插件元数据（inputs/runs）              |
| `oss-pr-scan-action/index.js`        | 新增             | 插件源码入口                           |
| `oss-pr-scan-action/package.json`    | 新增             | `@actions/core` + `@vercel/ncc`        |
| `oss-pr-scan-action/dist/index.js`   | 新增（构建产物） | ncc 打包结果，供 workflow `uses`       |
| `oss-pr-scan-action/test/*.test.js`  | 新增             | 核心逻辑单测（mock trivy 输出）        |
| `oss-pr-scan-action/README.md`       | 新增             | 使用文档                               |
| `.gitcode/workflows/oss-pr-scan.yml` | 新增             | 本仓自测 workflow（会用插件扫自己）    |
| `.pre-commit-config.yaml`            | 新增             | 代码规范钩子（对标 malicious-code 仓） |

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

| 参数                   | 默认值（action.yml）                                                                    |
| ---------------------- | --------------------------------------------------------------------------------------- |
| `ignore-vuln-count`    | `0`                                                                                     |
| `ignore-license-count` | `0`                                                                                     |
| `scan-target`          | `.`                                                                                     |
| `severity`             | `HIGH,CRITICAL`                                                                         |
| `trivy-config`         | （取 runner 预置 `/opt/cached_resources/trivy_db/trivy.yaml`，未传时跳过 `--config`）   |
| `cache-dir`            | 空（未传时交给 trivy，但 runner 通常预置 `--cache-dir /opt/cached_resources/trivy_db`） |
| `debug`                | `false`                                                                                 |

## 风险 & 缓解

| 风险                    | 缓解                                                                                |
| ----------------------- | ----------------------------------------------------------------------------------- |
| trivy JSON 结构版本差异 | 用 null-safe 遍历 + 字段缺省兜底；单测 mock 真实结构                                |
| 扫描大仓耗时            | runner 本地执行、skip-version-check、无网上库下载；超时由 workflow job timeout 兜底 |
| trivy 未预装            | 启动前 `trivy --version` 探测，缺失则报清晰错误（提示 runner 需预置）               |
| 预合并分支扫描语义      | checkout 默认预合并分支，与 scan_vuls.sh 预合并逻辑等价                             |

## 跨仓影响

- 生产仓（openlibing/*）**不受影响**——本插件在 `openlibing-test` 测试组织开发验证。
- 未来接入生产：在各目标仓 `.gitcode/workflows/` 增加 `pull_request` workflow 引用本插件即可。
