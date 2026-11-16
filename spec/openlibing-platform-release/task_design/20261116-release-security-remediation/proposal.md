# 202611 release 安全整改批次（20261116-release-security-remediation）

关联业务 Issue（39 个，均属 openlibing/openlibing-platform-release）：

https://gitcode.com/openlibing/openlibing-platform-release/issues/83 ·
[#84](https://gitcode.com/openlibing/openlibing-platform-release/issues/84) ·
[#85](https://gitcode.com/openlibing/openlibing-platform-release/issues/85) ·
[#86](https://gitcode.com/openlibing/openlibing-platform-release/issues/86) ·
[#87](https://gitcode.com/openlibing/openlibing-platform-release/issues/87) ·
[#89](https://gitcode.com/openlibing/openlibing-platform-release/issues/89) ·
[#91](https://gitcode.com/openlibing/openlibing-platform-release/issues/91) ·
[#92](https://gitcode.com/openlibing/openlibing-platform-release/issues/92) ·
[#93](https://gitcode.com/openlibing/openlibing-platform-release/issues/93) ·
[#94](https://gitcode.com/openlibing/openlibing-platform-release/issues/94) ·
[#95](https://gitcode.com/openlibing/openlibing-platform-release/issues/95) ·
[#96](https://gitcode.com/openlibing/openlibing-platform-release/issues/96) ·
[#98](https://gitcode.com/openlibing/openlibing-platform-release/issues/98) ·
[#99](https://gitcode.com/openlibing/openlibing-platform-release/issues/99) ·
[#100](https://gitcode.com/openlibing/openlibing-platform-release/issues/100) ·
[#101](https://gitcode.com/openlibing/openlibing-platform-release/issues/101) ·
[#102](https://gitcode.com/openlibing/openlibing-platform-release/issues/102) ·
[#103](https://gitcode.com/openlibing/openlibing-platform-release/issues/103) ·
[#104](https://gitcode.com/openlibing/openlibing-platform-release/issues/104) ·
[#105](https://gitcode.com/openlibing/openlibing-platform-release/issues/105) ·
[#106](https://gitcode.com/openlibing/openlibing-platform-release/issues/106) ·
[#107](https://gitcode.com/openlibing/openlibing-platform-release/issues/107) ·
[#108](https://gitcode.com/openlibing/openlibing-platform-release/issues/108) ·
[#109](https://gitcode.com/openlibing/openlibing-platform-release/issues/109) ·
[#110](https://gitcode.com/openlibing/openlibing-platform-release/issues/110) ·
[#114](https://gitcode.com/openlibing/openlibing-platform-release/issues/114) ·
[#115](https://gitcode.com/openlibing/openlibing-platform-release/issues/115) ·
[#116](https://gitcode.com/openlibing/openlibing-platform-release/issues/116) ·
[#117](https://gitcode.com/openlibing/openlibing-platform-release/issues/117) ·
[#118](https://gitcode.com/openlibing/openlibing-platform-release/issues/118) ·
[#119](https://gitcode.com/openlibing/openlibing-platform-release/issues/119) ·
[#121](https://gitcode.com/openlibing/openlibing-platform-release/issues/121) ·
[#122](https://gitcode.com/openlibing/openlibing-platform-release/issues/122) ·
[#124](https://gitcode.com/openlibing/openlibing-platform-release/issues/124) ·
[#125](https://gitcode.com/openlibing/openlibing-platform-release/issues/125) ·
[#126](https://gitcode.com/openlibing/openlibing-platform-release/issues/126) ·
[#127](https://gitcode.com/openlibing/openlibing-platform-release/issues/127) ·
[#129](https://gitcode.com/openlibing/openlibing-platform-release/issues/129) ·
[#130](https://gitcode.com/openlibing/openlibing-platform-release/issues/130)

业务交付 PR：https://gitcode.com/openlibing/openlibing-platform-release/merge_requests/247（`check_safe_202611` → `release_20261116`）

## 需求背景

202611 迭代对 openlibing-platform-release（发布管理平台）开展了多批次安全治理，来源包括：

- **argus 漏洞挖掘平台**：19 项中高危问题（#91~#110 区段），覆盖认证绕过、授权绕过、IDOR、SSRF、路径穿越、反序列化 RCE、状态机竞态、CI 供应链投毒等
- **提权专项检查**（#85）：命令注入与提权风险、路径/软链接校验缺失、镜像构建期压缩包投毒防护不足
- **奇美拉扫描 / SecBinaryCheck / SENINFO**（#83、#84、#86、#129）：URL 硬编码、不安全密码算法、敏感信息 URL 传输、外部参数可控校验缺陷
- **安全缺陷批次**（#87、#89、#106、#107、#114~#122、#124、#126、#127、#130）：XSS、CSRF、SSRF、日志注入、SMTP 证书校验绕过等

全部整改在 `check_safe_202611` 分支完成，随 PR #247 合入 `release_20261116` 发布分支。

## 功能描述

### 做什么

按九大类完成整改（详细方案见 [design.md](design.md)）：

1. 认证与授权：OpenEulerAuthFilter 认证绕过根因修复、全量接口补齐项目权限注解校验、敏感端点收敛
2. 越权与数据归属：附件 IDOR、评审单归属防篡改、状态机竞态（分布式锁 + 条件更新 + 幂等）
3. SSRF：出站地址校验与重定向锁定（含部分按评审意见撤回，见「撤回项」）
4. 路径穿越：产品名/版本号白名单校验、恒真绕过修复
5. 注入与反序列化：fastjson2 RCE、存储型 XSS、命令注入
6. 凭证与敏感信息：HeaderToken 令牌收敛、令牌迁出 URL、硬编码消除、日志脱敏（CWE-532）
7. 证书与传输安全：SMTP 证书强制校验、MongoDB/TLS 主机名校验、TrustAll 清理
8. 供应链与运行时加固：CI 投毒整改、Dockerfile 构建期校验、Actuator 收窄、限流器原子化
9. 响应安全：Content-Disposition 头注入、CRLF 注入、异常信息泄露

### 不做什么

- 不改动业务功能语义（发布/评审主流程行为保持不变）
- 不引入新的鉴权框架（沿用现有过滤器/注解体系）

### 撤回项（评审结论记录）

以下整改经评审后撤回，恢复原实现，避免影响现有链路：

- 全局安全响应头过滤器（commit `a845378a` 被 `70485f01` revert）
- 出站地址统一 SSRF 校验器 `OutboundUrlValidator`（`5e10a653` 被 `24f1fae1` revert）
- repoUrl 入库前 SSRF 校验（`1c191733` 被 `2ad7c9c1` revert）
- Jenkins 触发 token 迁移请求体（`0a74f1b0` 被 `9403c53e` 回退为 URL 拼接，与原实现一致）
- JRE 下载 SHA256 校验去除（`e458eb77`：TUNA 镜像无校验文件且 GitHub 不可达，属场景限定）

## 验收标准

- [x] 39 个关联 issue 的整改项全部落地或有明确的场景限定结论
- [x] `mvn compile` / `mvn test` 通过，CI 门禁（UT/build/pre-commit）通过
- [x] diff 增量行覆盖率达 80% 门禁（commit `c8e86a6e`）
- [x] 撤回项均有评审依据并在本 spec 中留痕
- [x] 无硬编码凭证/敏感信息引入（gitleaks/pre-commit 通过）

## 影响范围

- 业务仓：`openlibing-platform-release`（87 commits，154 files，+8608/-3624，随 PR #247 合入 `release_20261116`）
- 文档仓：`openlibing-docs`（本 spec 目录）

## 子 spec

- 病毒扫描外部接口（#125 的 ClamAV 扫描接口部分）：[20261102-virus-scan-api](../20261102-virus-scan-api/proposal.md)
