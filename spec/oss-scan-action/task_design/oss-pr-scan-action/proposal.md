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
   runner 预置漏洞库 cache-dir，漏洞库过期时自动联网更新（不传 `--skip-db-update`）。
4. **Maven 依赖预解析**：扫描目标下存在 `pom.xml` 时，先执行 `mvn dependency:resolve`
   （先离线 `-o` 试本地 `~/.m2`，失败再在线重试）填充本地依赖仓库，保证 trivy
   能解析出**完整传递依赖**（间接依赖中的漏洞不会被漏检）；mvn 缺失 / 无可用仓库 /
   全程失败 / 超时均**降级处理**，不阻断门禁，仅退回"只能解析直接依赖"的旧行为。
5. 解析 trivy JSON 结果，按四级别统计漏洞数与 license 数（CRITICAL/HIGH/MEDIUM/LOW，
   UNKNOWN 不统计；含空结果保护）。
6. 四级别门禁判定：CRITICAL/HIGH（漏洞或 license）任一计数 > 对应门禁 → no pass 并置
   流水线失败；MEDIUM/LOW 任一计数 > 对应门禁 → 仅提示不阻断。
7. 扫描结论写入 Step Summary：扫描信息表 + 四级别计数表 + 通过/未通过结论 + CRITICAL/HIGH
   明细表（漏洞/license 各一张；MEDIUM/LOW 超门禁时增加提示行）。

### 不做什么

- 本阶段不做版本级扫描（master/main 全量）——由后续 `oss-version-scan-action` 承接。
- 不调用平台后端 API，不使用 OIDC 免密换证 / AK/SK 密钥。
- 不创建 Issue、不写仓库、不做代码修复。
- 不依赖 `openlibing-ci` 仓脚本（自包含迁移）。

## 输入参数（action.yml 草案）

| 参数                     | 必填 | 默认值              | 说明                               |
| ------------------------ | ---- | ------------------- | ---------------------------------- |
| `scan-target`            | 否   | `.`（工作区根目录） | 待扫描的代码目录路径               |
| `trivy-config`           | 否   | runner 预置路径     | trivy 配置文件路径                 |
| `cache-dir`              | 否   | runner 预置路径     | trivy 漏洞库 cache-dir             |
| `vuln-critical-limit`    | 否   | `0`                 | CRITICAL 漏洞门禁（>门禁阻断）     |
| `vuln-high-limit`        | 否   | `0`                 | HIGH 漏洞门禁（>门禁阻断）         |
| `vuln-medium-limit`      | 否   | `1000`              | MEDIUM 漏洞门禁（>门禁仅提示）     |
| `vuln-low-limit`         | 否   | `1000`              | LOW 漏洞门禁（>门禁仅提示）        |
| `license-critical-limit` | 否   | `0`                 | CRITICAL license 门禁（>门禁阻断） |
| `license-high-limit`     | 否   | `0`                 | HIGH license 门禁（>门禁阻断）     |
| `license-medium-limit`   | 否   | `1000`              | MEDIUM license 门禁（>门禁仅提示） |
| `license-low-limit`      | 否   | `1000`              | LOW license 门禁（>门禁仅提示）    |
| `debug`                  | 否   | `false`             | 开启调试日志                       |

> 精确参数名以 design.md 为准，此处为需求级草案。旧参数 `ignore-vuln-count` /
> `ignore-license-count` 已废弃，由上面 8 个 limit 参数取代。

## 验收标准

- [ ] 插件在预合并分支代码上正确执行 trivy 扫描并解析结果
- [ ] CRITICAL/HIGH 漏洞与 license 计数正确（含空结果保护、UNKNOWN 不统计）
- [ ] 四级别门禁判定：CRITICAL/HIGH 超门禁阻断，MEDIUM/LOW 超门禁仅提示
- [ ] 默认值：CRITICAL/HIGH=0、MEDIUM/LOW=1000（当前门禁默认行为不变）
- [ ] 不通过时设置 action 失败（`core.setFailed`），阻断 PR 合入
- [ ] Step Summary 展示扫描结论与四级别计数表/明细
- [ ] 含 pom.xml 时先执行 `mvn dependency:resolve` 填充 `~/.m2`，trivy 能解析出传递依赖漏洞（间接依赖不漏检）
- [ ] mvn 缺失/失败/超时降级处理，不阻断门禁
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
