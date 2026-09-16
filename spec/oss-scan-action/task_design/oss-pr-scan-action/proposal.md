# oss-pr-scan-action — PR 级开源漏洞与 license 扫描门禁插件

## 需求背景

原 openlibing PR 流水线中「开源漏洞 + license 扫描门禁」环节，通过克隆
`openlibing-ci`（master_01 分支）+ 预合并目标分支 + 本地执行
`ci_tools/scan/opensource/scan_vuls.sh`（trivy fs）实现。该环节依赖：

- 明文 git 凭据（`${gitcode_user}:${gitcode_pwd}`）
- runner 预置 trivy 二进制与漏洞库缓存（`/opt/cached_resources/trivy_db`）

本次迁移目标：将 `scan_vuls.sh` 的核心逻辑插件化为 GitCode Action 插件，
在目标仓 `.gitcode/workflows/` 中以标准 workflow 方式接入，替代原服务端流水线调度。

## 功能描述

### 做什么

1. 在 `pull_request`（预合并分支）/ `push: master` / `workflow_dispatch` 事件下触发。
2. 由 `checkout` 插件检出代码（依赖平台自动注入 token，无明文 git 凭据）。
3. 插件内执行 trivy 文件系统扫描（`trivy fs --scanners vuln,license`），复用
   runner 预置漏洞库 cache-dir，不联网更新漏洞库。
4. 解析 trivy JSON 结果，统计 HIGH/CRITICAL 漏洞数与 HIGH/CRITICAL license 数
   （对齐 `scan_vuls.sh` 的 jq 统计口径，含空结果保护）。
5. pass/no pass 判定与 `scan_vuls.sh` 一致：双高风险计数均小于对应
   ignore 阈值（默认 0）时 pass，否则 no pass 并置流水线失败。
6. 扫描结论写入 Step Summary：扫描信息表 + 通过/未通过结论 + 高风险明细表
   （在 `scan_vuls.sh` 文本输出的基础上扩展为 summary 表格展示）。

### 不做什么

- 本阶段不做版本级扫描（master/main 全量）——由后续 `oss-version-scan-action` 承接。
- 不调用平台后端 API，不使用 OIDC 免密换证 / AK/SK 密钥。
- 不创建 Issue、不写仓库、不做代码修复。
- 不依赖 `openlibing-ci` 仓脚本（自包含迁移）。

## 输入参数（action.yml 草案）

| 参数                   | 必填 | 默认值              | 说明                                         |
| ---------------------- | ---- | ------------------- | -------------------------------------------- |
| `scan-target`          | 否   | `.`（工作区根目录） | 待扫描的代码目录路径                         |
| `trivy-config`         | 否   | runner 预置路径     | trivy 配置文件路径                           |
| `cache-dir`            | 否   | runner 预置路径     | trivy 漏洞库 cache-dir                       |
| `severity`             | 否   | `HIGH,CRITICAL`     | 判定阈值级别单位（对齐原脚本 HIGH/CRITICAL） |
| `ignore-vuln-count`    | 否   | `0`                 | 高危漏洞豁免个数                             |
| `ignore-license-count` | 否   | `0`                 | 高危 license 豁免个数                        |
| `debug`                | 否   | `false`             | 开启调试日志                                 |

> 精确参数名以 design.md 为准，此处为需求级草案。

## 验收标准

- [ ] 插件在预合并分支代码上正确执行 trivy 扫描并解析结果
- [ ] high/critical 漏洞与 license 计数口径与 `scan_vuls.sh` 的 jq 统计一致（含空结果保护）
- [ ] 判定逻辑一致：`count < ignore 阈值` 放行，否则阻断
- [ ] 不通过时设置 action 失败（`core.setFailed`），阻断 PR 合入
- [ ] Step Summary 展示扫描结论与明细
- [ ] 无硬编码凭据、无敏感信息
- [ ] 单测覆盖解析与判定核心逻辑（mock trivy 输出）

## 影响范围

- 新仓：`openlibing-test/oss-scan-action`（master 分支直接开发）
- 插件目录：`oss-pr-scan-action/`（action.yml + index.js + dist + package.json + test）
- 本需求仅在 `openlibing-test` 测试组织开发验证，不涉及生产仓 workflow 改动

## 关联

- 迁移基准：`openlibing-ci/scan/opensource/scan_vuls.sh` + `trivy.yaml`
- 插件范式：`malicious-code-scan-action/malicious-code-pr-scan-action`
  （action.yml/dist/Step Summary 结构）、`openlibing-pre-commit-action`（node action 调 CLI）
- 测试组织，不关联业务 Issue
