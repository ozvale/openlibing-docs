# Security Assessment

---

## Report Files

| File | Description |
|------|-------------|
| [0-assessment.md](0-assessment.md) | This document — executive summary, risk rating, action plan, metadata |
| [0.1-architecture.md](0.1-architecture.md) | Architecture overview, components, scenarios, tech stack |
| [1-threatmodel.md](1-threatmodel.md) | Threat model DFD diagram with element, flow, and boundary tables |
| [1.1-threatmodel.mmd](1.1-threatmodel.mmd) | Pure Mermaid DFD source file |
| [2-stride-analysis.md](2-stride-analysis.md) | Full STRIDE-A analysis for all components |
| [3-findings.md](3-findings.md) | Prioritized security findings with remediation |
| [threat-inventory.json](threat-inventory.json) | Machine-readable inventory of components, threats, and findings |

---

## Executive Summary

`security-compilation-options-action` 是 OpenLiBing 工作流平台的一个 GitCode CI/CD Action（Node.js 16+ 实现，调用 Python 子进程扫描 ELF 文件的安全编译选项），由 ncc 打包为 `dist/index.js`（1.86 MB），通过 `action.yml` 暴露 `artifact-path`/`output`/`package-name`/`artifact-download-url`/`scan-options`/`apig-app-key`/`apig-app-secret` 七个 inputs。Action 自身无 inbound 网络监听器，仅发起 outbound HTTPS（APIG/OIDC/PyPI）与本地 `child_process.spawn` 子进程调用，部署分类为 `LOCALHOST_DESKTOP`（CI runner 临时单租户独占工作区），因此 T1 在所有组件上禁止。

安全控制方面：Action 同时支持 OIDC 联邦认证（`@openlibing/huaweicloud-oidc-client@0.0.5` SDK，新接口 `/action-api/...`）与 AK/SK HMAC-SHA256 签名（自实现 `ApigSigner`，旧接口 `/openlibing-cicd/...`）双模式上报，OIDC 模式由 `process.env.ACTIONS_ID_TOKEN_REQUEST_URL` 自动判定，AK/SK 通过 workflow secrets 传入；`SecOptionScanScript._entry_path_unsafe()` 提供 zip-slip/tar-slip 路径穿越防御；`pre-commit` + `gitleaks v8.30.1` + `codeql-action` 提供静态安全扫描（仅 push 到 master 时触发，不影响 Action 运行时）。

主要风险集中在 Action 的输入校验薄弱（`artifact-path`/`scan-options`/`package-name` 未做严格白名单/路径校验）、日志与上报 payload 中包含未脱敏的 `gitUrl`/`filePath`/`errorMessage`/APIG 错误响应、`pip install --trusted-host` 削弱 SSL 校验、APIG 端点硬编码无证书固定、`pull_request_target` 触发场景下 OIDC token 以 base 仓权限签发可被 PR 作者间接盗用、产物文件大小/解压比/递归深度无限制存在 DoS 风险。建议优先修复 FIND-11（pip `--trusted-host` 削弱 SSL）与 FIND-04（pull_request_target OIDC 滥用）两个 Important 严重级别的快速修复项。

The analysis covers 11 system elements across 2 trust boundaries.

### Risk Rating: Elevated

Action 自身无 inbound 监听器、CI runner 单租户独占工作区，T1 直接暴露风险被 `LOCALHOST_DESKTOP` 部署分类排除；但 Action 接受 PR 作者控制的多个 workflow inputs（`artifact-path`/`scan-options`/`package-name`/`artifact-download-url`）作为攻击面，且上报路径与认证模式由 runner 注入的 env 变量决定，2 个 Important 严重级别的 findings（FIND-04 pull_request_target OIDC 滥用、FIND-11 pip `--trusted-host` MITM）可在单一 Authenticated User prerequisite 下触发，构成 Elevated 风险。多个 Moderate 级别的输入校验与日志泄露问题在 self-hosted runner 或共享 runner 场景下风险升级。

> **Note on threat counts:** This analysis identified 38 threats across 11 components. This count reflects comprehensive STRIDE-A coverage, not systemic insecurity. Of these, **0 are directly exploitable** without prerequisites (Tier 1). The remaining 38 represent conditional risks and defense-in-depth considerations.

---

## Action Summary

| Tier | Description | Threats | Findings | Priority |
|------|-------------|---------|----------|----------|
| [Tier 1](3-findings.md#tier-1--direct-exposure-no-prerequisites) | Directly exploitable | 0 | 0 | 🔴 Critical Risk |
| [Tier 2](3-findings.md#tier-2--conditional-risk-authenticated--single-prerequisite) | Requires authenticated access | 25 | 14 | 🟠 Elevated Risk |
| [Tier 3](3-findings.md#tier-3--defense-in-depth-prior-compromise--host-access) | Requires prior compromise | 13 | 9 | 🟡 Moderate Risk |
| **Total** | | **38** | **23** | |

### Priority by Tier and CVSS Score (Top 10)

| Finding | Tier | CVSS Score | SDL Severity | Title |
|---------|------|------------|-------------|-------|
| [FIND-04](3-findings.md#find-04-pull_request_target-triggered-oidc-token-issued-with-base-repo-permissions-indirectly-stolen-by-pr-author) | T2 | 7.5 | Important | pull_request_target 触发场景下 OIDC Token 以 Base 仓权限签发被 PR 作者间接盗用 |
| [FIND-11](3-findings.md#find-11-pip-install-uses---trusted-host-weakening-ssl-verification-supply-chain-mitm-risk) | T2 | 7.0 | Important | pip install 使用 --trusted-host 削弱 SSL 校验，存在供应链 MITM 风险 |
| [FIND-02](3-findings.md#find-02-incomplete-git-remote-url-sanitization-causes-non-standard-format-token-leak-to-ci-logs-and-upload-payload) | T2 | 6.5 | Moderate | git remote URL 清洗正则不完整导致非标准格式的 Token 泄露到 CI 日志与上报 payload |
| [FIND-03](3-findings.md#find-03-no-limits-on-artifact-file-sizecompression-ratiorecursion-depth-resource-exhaustion-dos-risk) | T2 | 6.5 | Moderate | 产物文件大小/解压比/递归深度无限制，存在资源耗尽 DoS 风险 |
| [FIND-09](3-findings.md#find-09-apig-endpoint-hardcoded-and-no-tls-certificate-fingerprint-pinning-dns-hijacking-and-mitm-risk) | T2 | 5.5 | Moderate | APIG 端点硬编码且无 TLS 证书指纹固定，存在 DNS 劫持与 MITM 风险 |
| [FIND-01](3-findings.md#find-01-artifact-path-input-without-path-traversal-validation-can-scan-files-outside-runner-workspace-and-leak-to-upload-payload) | T2 | 5.3 | Moderate | artifact-path 输入未校验路径穿越，可扫描 runner 工作区外文件并泄露到上报 payload |
| [FIND-14](3-findings.md#find-14-no-integrity-validation-of-build-artifacts-from-external-build-step-pr-authors-can-deliver-malicious-elf-or-archives-triggering-subsequent-parsing-chain) | T2 | 5.3 | Moderate | 构建产物来源无完整性校验，PR 作者可投递恶意 ELF 或归档触发后续解析链路 |
| [FIND-06](3-findings.md#find-06-python-subprocess-stdoutstderr-without-control-character-filtering-log-injection-and-terminal-control-sequence-attack-risk) | T2 | 5.0 | Moderate | Python 子进程 stdout/stderr 未做控制字符过滤，存在日志注入与终端控制序列攻击 |
| [FIND-05](3-findings.md#find-05-scan-result-filepath-absolute-path-and-error-message-directly-leak-to-ci-logs-and-upload-payload) | T2 | 4.3 | Moderate | 扫描结果 filePath 绝对路径与错误 message 直接泄露到 CI 日志与上报 payload |
| [FIND-07](3-findings.md#find-07-windows-platform-hardcoded-short-path-prefix-dsec_option_tmpcsec_option_tmp-can-be-pre-planted-with-symbolic-link-hijack) | T2 | 4.3 | Moderate | Windows 平台硬编码短路径前缀 D:\sec_option_tmp/C:\sec_option_tmp 可被符号链接预植劫持 |

### Quick Wins

| Finding | Title | Why Quick |
|---------|-------|-----------|
| [FIND-11](3-findings.md#find-11-pip-install-uses---trusted-host-weakening-ssl-verification-supply-chain-mitm-risk) | pip install 使用 --trusted-host 削弱 SSL 校验 | 单行命令修改：移除 `--trusted-host mirrors.aliyun.com` 标志或固定 pyelftools 版本 + `--require-hashes`，无需重构 |
| [FIND-01](3-findings.md#find-01-artifact-path-input-without-path-traversal-validation-can-scan-files-outside-runner-workspace-and-leak-to-upload-payload) | artifact-path 输入未校验路径穿越 | 单文件单点校验：在 `dist/index.js:54311` 后加 `path.relative` + `..` 前缀校验，约 5 行代码 |
| [FIND-06](3-findings.md#find-06-python-subprocess-stdoutstderr-without-control-character-filtering-log-injection-and-terminal-control-sequence-attack-risk) | Python stdout/stderr 未做控制字符过滤 | 单文件修改：在 `SecOptionDetector._runPythonScript` 的 stdout/stderr 捕获处加 `\x1b[...` CSI 序列剥离与 NUL 字节过滤 |
| [FIND-07](3-findings.md#find-07-windows-platform-hardcoded-short-path-prefix-dsec_option_tmpcsec_option_tmp-can-be-pre-planted-with-symbolic-link-hijack) | Windows 短路径前缀固定可预测 | 单文件修改：删除 `dist/bin/sec_option_scan.py:137-144` 的 `D:\sec_option_tmp`/`C:\sec_option_tmp` 短路径逻辑，统一用 `tempfile.mkdtemp(prefix='sec_option_extract_')` |
| [FIND-13](3-findings.md#find-13-scanresultfile-default-permission-0644-self-hosted-runner-multi-tenant-scenario-information-disclosure) | ScanResultFile 默认权限 0644 | 单点修改：`fs.writeFileSync` 第三参数加 `{ mode: 0o600 }`，Python 端 `json.dump` 后 `os.chmod(output_path, 0o600)` |
| [FIND-17](3-findings.md#find-17-scan-options-workflow-input-accepts-arbitrary-keys-triggers-python-sys-exit1-interrupting-scan) | scan-options 接受任意 key | 单点修改：在 `dist/index.js:54281` scanOptions 解析处用 `.filter(k => ALL_OPTION_KEYS.includes(k))` 过滤非法 key |

---

## Analysis Context & Assumptions

### Analysis Scope

| Constraint | Description |
|------------|-------------|
| Scope | `security-compilation-options-action` 仓库的 `dist/`（ncc 打包产物与模块化源码）+ `action.yml`（Action 元数据）+ `package.json`（npm 依赖）+ `dist/bin/sec_option_scan.py`（Python 扫描脚本）+ `.pre-commit-config.yaml`（本地静态扫描配置）|
| Excluded | `.gitcode/workflows/`（CI workflow 定义，非 Action 运行时代码）、`zip.js`（构建期打包工具，非运行时）、`node_modules`（npm 依赖，通过 `package.json` 间接分析）、`@openlibing/huaweicloud-oidc-client` SDK 内部实现（第三方代码，仅审计调用点）|
| Focus Areas | Action 输入校验（`artifact-path`/`scan-options`/`package-name`）、OIDC/AKSK 双模式认证流程、ELF 文件扫描与归档解压链路、文件系统操作（ScanResultFile 读写）、Python 子进程 spawn 调用、HTTPS 上报路径（APIG/OIDC/PyPI）|

### Infrastructure Context

| Category | Discovered from Codebase | Findings Affected |
|----------|--------------------------|-------------------|
| OIDC 联邦认证 | `package.json:16` `@openlibing/huaweicloud-oidc-client@0.0.5`，由 `CicdUploader.js:305 callApig('POST', url, headers, body)` 调用 | [FIND-04](3-findings.md#find-04-pull_request_target-triggered-oidc-token-issued-with-base-repo-permissions-indirectly-stolen-by-pr-author), [FIND-08](3-findings.md#find-08-oidc-callapig-invocation-without-explicit-timeout-sts-endpoint-unreachable-action-hangs-for-long-time), [FIND-15](3-findings.md#find-15-runner-environment-variables-can-spoof-oidc-mode-determination-and-pipeline-metadata-upload), [FIND-21](3-findings.md#find-21-third-party-oidc-sdk-error-path-may-leak-id-token-dependency-audit-not-done) |
| AK/SK HMAC 签名 | `dist/uploaders/CicdUploader.js:16-244` `ApigSigner` 自实现 SDK-HMAC-SHA256 签名，AK/SK 通过 `apig-app-key`/`apig-app-secret` inputs 传入 | [FIND-02](3-findings.md#find-02-incomplete-git-remote-url-sanitization-causes-non-standard-format-token-leak-to-ci-logs-and-upload-payload), [FIND-09](3-findings.md#find-09-apig-endpoint-hardcoded-and-no-tls-certificate-fingerprint-pinning-dns-hijacking-and-mitm-risk), [FIND-19](3-findings.md#find-19-apigsigner-hmac-signature-without-noncejti-replay-risk) |
| 归档路径穿越防御 | `dist/bin/sec_option_scan.py:173-187` `_entry_path_unsafe()` 校验绝对路径、`..` 段、Windows 盘符；`_safe_extract_zip`/`_safe_extract_tar` 逐条目校验 | [FIND-18](3-findings.md#find-18-_entry_path_unsafe-does-not-reject-nul-bytes-and-unicode-equivalent-characters-archive-path-validation-bypass-risk) |
| pre-commit + gitleaks | `.pre-commit-config.yaml` 启用 `detect-private-key` hook + `gitleaks v8.30.1`，仅在 `pre-commit` workflow 触发时检查提交内容 | 不影响 Action 运行时；不覆盖 Action 运行时配置 |
| codeql-action | `.gitcode/workflows/codeql.yaml` 配置 javascript + security-and-quality query suite | 仅在 push 到 master 时扫描，不影响 Action 运行时 |
| Python 依赖运行时安装 | `dist/index.js:54288-54292` `pip install --break-system-packages pyelftools -i https://mirrors.aliyun.com/pypi/simple/ --trusted-host mirrors.aliyun.com` | [FIND-11](3-findings.md#find-11-pip-install-uses---trusted-host-weakening-ssl-verification-supply-chain-mitm-risk), [FIND-22](3-findings.md#find-22-pyelftools-dependency-not-version-pinned-pypi-supply-chain-poisoning-risk) |
| 部署分类 LOCALHOST_DESKTOP | `0.1-architecture.md` Component Exposure Table 标注 Action 无 inbound 监听器、CI runner 单租户独占工作区 | 所有 38 个 threats 均为 T2+，无 T1 |

### Needs Verification

| Item | Question | What to Check | Why Uncertain |
|------|----------|---------------|---------------|
| `@openlibing/huaweicloud-oidc-client@0.0.5` SDK 行为 | SDK error 路径是否会泄露 OIDC ID Token 到 error.message 或 error.config.headers | 审查 SDK 源码（`node_modules/@openlibing/huaweicloud-oidc-client/`），grep `error.message`/`Authorization`/`eyJ` JWT 前缀引用 | SDK 是第三方代码，行为依赖审计，npm audit 无法覆盖逻辑漏洞 |
| APIG 服务端 nonce/replay 保护 | APIG 网关是否已对 SDK-HMAC-SHA256 签名请求做 nonce 去重或时间窗口 + 重放保护 | 联系 OpenLibingAPIG 服务端团队确认签名校验策略；或构造两次相同签名请求测试响应 | 客户端 `ApigSigner` 无 nonce/jti，但服务端可能有去重；无法从客户端代码确认 |
| Runner 镜像预装 pyelftools | GitCode `codearts-hosted` runner 镜像是否已预装 pyelftools | 在 runner 上执行 `python3 -c "import elftools; print(elftools.__version__)"` 确认 | 若已预装则 `pip install` 可移除，FIND-11/FIND-22 风险降低 |
| `ATOMGIT_*` 环境变量注入链路 | GitCode runner 是否对 `ATOMGIT_RUN_ID`/`ATOMGIT_WORKFLOW`/`ATOMGIT_RUN_NUMBER` 做签名或防篡改 | 查阅 GitCode runner 文档或源码 | 客户端无法确认 env 变量来源是否可信 |
| `codearts-hosted` vs `self-hosted` runner 多租户隔离 | self-hosted runner 是否允许多 job 并发共享工作区 | 查阅 GitCode CI 文档与 self-hosted runner 配置 | FIND-12 TOCTOU 与 FIND-13 文件权限依赖此隔离模型 |

### Finding Overrides

| Finding ID | Original Severity | Override | Justification | New Status |
|------------|-------------------|----------|---------------|------------|
| — | — | — | No overrides applied. Update this section after review. | — |

### Additional Notes

- 本分析未对 `@openlibing/huaweicloud-oidc-client@0.0.5` SDK 内部实现做完整源码审计（仅审计调用点），SDK 内部行为（如 token 持有、error 路径、STS endpoint 选择）需通过依赖审计（npm audit + 源码审查）进一步验证。
- 本分析的 38 个 threats 全部为 Open 状态，已全部映射到 23 个 findings（Coverage 表中每行均为 `✅ Covered (FIND-XX)`），无 `⚠️ Accepted Risk` 或 `⚠️ Needs Review` 项。
- 本分析未做 Platform-classified threats（0/38 = 0%），低于 Standalone Application 模式的 ≤20% 上限。

---

## References Consulted

### Security Standards

| Standard | URL | How Used |
|----------|-----|----------|
| Microsoft SDL Bug Bar | https://www.microsoft.com/en-us/msrc/sdlbugbar | Severity classification |
| OWASP Top 10:2025 | https://owasp.org/Top10/2025/ | Threat categorization |
| CVSS 4.0 | https://www.first.org/cvss/v4.0/specification-document | Risk scoring |
| CWE | https://cwe.mitre.org/ | Weakness classification |
| STRIDE | https://learn.microsoft.com/en-us/azure/security/develop/threat-modeling-tool-threats | Threat enumeration |
| Huawei Cloud APIG Signing | https://support.huaweicloud.com/devg-apig/apig-04-01-1.html | SDK-HMAC-SHA256 签名算法参考 |
| Makeself .run 格式 | https://github.com/megastep/makeself | `_extract_run_payload` 解压逻辑参考 |

### Component Documentation

| Component | Documentation URL | Relevant Section |
|-----------|------------------|------------------|
| `@openlibing/huaweicloud-oidc-client` SDK | https://www.npmjs.com/package/@openlibing/huaweicloud-oidc-client | `callApig(method, url, headers, body)` 接口与 timeout 选项 |
| `pyelftools` | https://github.com/eliben/pyelftools | `ELFFile`/`ENUM_DT_FLAGS` 用于解析 ELF 安全选项 |
| `@actions/core` | https://github.com/actions/toolkit/tree/main/packages/core | `getInput`/`setOutput`/`setFailed`/`info` API |
| `@vercel/ncc` | https://github.com/vercel/ncc | `ncc build dist/index.js -o dist` 打包机制 |
| GitCode CI Actions | https://gitcode.com/docs/Actions/actions.html | `node16` 运行时与 `ATOMGIT_*` env 变量注入 |

---

## Report Metadata

| Field | Value |
|-------|-------|
| Source Location | `d:\Develop\Java\security-compilation-options-action` |
| Git Repository | `https://gitcode.com/openlibing/security-compilation-options-action.git` |
| Git Branch | `sec-option-oidc-auth` |
| Git Commit | `5189dc5` (`2026-09-02T04:24:04Z`) |
| Model | `GLM-5.2` |
| Machine Name | `DESKTOP-1L0N2MM` |
| Analysis Started | `2026-09-02T10:48:00Z` |
| Analysis Completed | `2026-09-02T11:17:26Z` |
| Duration | `29 minutes` |
| Output Folder | `d:\Develop\Java\openlibing-docs\architecture_desgin\threat-models\security-compilation-options-action` |
| Prompt | `你是一名 Threat Model Analyst 专家。请对 Node.js 仓库 d:\Develop\Java\security-compilation-options-action 执行完整的 STRIDE-A 威胁建模分析（Single Analysis Mode）。` |

---

## Classification Reference

| Classification | Values |
|---------------|--------|
| **Exploitability Tiers** | **T1** Direct Exposure (no prerequisites) · **T2** Conditional Risk (single prerequisite) · **T3** Defense-in-Depth (multiple prerequisites or infrastructure access) |
| **STRIDE + Abuse** | **S** Spoofing · **T** Tampering · **R** Repudiation · **I** Information Disclosure · **D** Denial of Service · **E** Elevation of Privilege · **A** Abuse (feature misuse) |
| **SDL Severity** | `Critical` · `Important` · `Moderate` · `Low` |
| **Remediation Effort** | `Low` · `Medium` · `High` |
| **Mitigation Type** | `Redesign` · `Standard Mitigation` · `Custom Mitigation` · `Existing Control` · `Accept Risk` · `Transfer Risk` |
| **Threat Status** | `Open` · `Mitigated` · `Platform` |
| **Incremental Tags** | `[Existing]` · `[Fixed]` · `[Partial]` · `[New]` · `[Removed]` (incremental reports only) |
| **CVSS** | CVSS 4.0 vector with `CVSS:4.0/` prefix |
| **CWE** | Hyperlinked CWE ID (e.g., [CWE-306](https://cwe.mitre.org/data/definitions/306.html)) |
| **OWASP** | OWASP Top 10:2025 mapping (e.g., A01:2025 – Broken Access Control) |
