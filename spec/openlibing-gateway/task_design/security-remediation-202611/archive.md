# openlibing-gateway 2026-11 安全整改批次 — 归档总览

## 概述

2026 年 11 月，openlibing-gateway 针对漏洞报告（argus / WEB 漏洞判定引擎 / auth-session-gray-release 专项）完成一批安全整改，共 11 个已立规格的修复项（见同目录各 task_design 子目录）+ 若干横向加固修复。本文件为批次总览，并按工作区规范关联 gateway 仓全部【安全】类 issues。

## 交付载体

| 批次                           | PR                                                                                                                                                          | 状态                 | 内容                                                          |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ------------------------------------------------------------- |
| 前置批次（11-03 ~ 11-07 上半） | [!223](https://gitcode.com/openlibing/openlibing-gateway/merge_requests/223) / [!225](https://gitcode.com/openlibing/openlibing-gateway/merge_requests/225) | 已合入               | 公开接口凭证校验、fail-closed 白名单、白名单 HMAC 完整性      |
| 主批次（11-07 ~ 11-07 下半）   | [!232](https://gitcode.com/openlibing/openlibing-gateway/merge_requests/232)                                                                                | 已合入（2026-11-16） | harden token, whitelist and csrf handling on release_20261116 |
| 尾批次（11-13 ~ 11-16）        | [!235](https://gitcode.com/openlibing/openlibing-gateway/merge_requests/235)                                                                                | **待合入**（open）   | harden auth, oauth and redis handling                         |

## 已立规格的修复项 ↔ Issue 映射

| spec 目录                        | 关联【安全】Issue                                                                                                                          | 主修复 commit      | PR          |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------ | ------------------ | ----------- |
| fix-open-redirect-bind-authoriz  | [#162](https://gitcode.com/openlibing/openlibing-gateway/issues/162)                                                                       | bbba6249           | !235        |
| fix-plugin-auth-code-consumption | [#165](https://gitcode.com/openlibing/openlibing-gateway/issues/165)、[#143](https://gitcode.com/openlibing/openlibing-gateway/issues/143) | 790bf0b4           | !235        |
| fix-logout-grace-key-revocation  | [#166](https://gitcode.com/openlibing/openlibing-gateway/issues/166)                                                                       | 40fe979a           | !235        |
| fix-exception-log-uri-redaction  | [#161](https://gitcode.com/openlibing/openlibing-gateway/issues/161)                                                                       | 5d826ed6           | !235        |
| fix-login-brute-force-protection | [#158](https://gitcode.com/openlibing/openlibing-gateway/issues/158)、[#147](https://gitcode.com/openlibing/openlibing-gateway/issues/147) | 8661bc75           | !235        |
| fix-refresh-token-key-alignment  | [#148](https://gitcode.com/openlibing/openlibing-gateway/issues/148)                                                                       | e394104d           | !235        |
| fix-idor-query-bind-accounts     | [#150](https://gitcode.com/openlibing/openlibing-gateway/issues/150)、[#163](https://gitcode.com/openlibing/openlibing-gateway/issues/163) | 9e14a5ec、e55584ba | !232 / !235 |
| fix-silent-refresh-csrf-bypass   | [#164](https://gitcode.com/openlibing/openlibing-gateway/issues/164)                                                                       | 971790f3、0985a802 | !235        |
| fix-oauth-bind-state-session     | [#169](https://gitcode.com/openlibing/openlibing-gateway/issues/169)                                                                       | ab7285a4           | !235        |
| fix-verify-token-allow-expired   | [#109](https://gitcode.com/openlibing/openlibing-gateway/issues/109)（缺陷类）                                                             | d22f46d1           | !232        |
| remove-cicd-permission-check     | [#170](https://gitcode.com/openlibing/openlibing-gateway/issues/170)、[#100](https://gitcode.com/openlibing/openlibing-gateway/issues/100) | 42b44a4b           | !232        |

## 横向加固修复（未单独立规格，随批次 PR 交付）

- 235301ca X-Forwarded-For 不再信任客户端头（关联 [#171](https://gitcode.com/openlibing/openlibing-gateway/issues/171)）
- 12ea69b8 / 1a7bc16c access_token 改走 Authorization 头、移除 query 参数信任（关联 [#172](https://gitcode.com/openlibing/openlibing-gateway/issues/172)、[#168](https://gitcode.com/openlibing/openlibing-gateway/issues/168)）
- ab7285a4 OAuth token-exchange 凭证从 URL 移入 form body（关联 [#172](https://gitcode.com/openlibing/openlibing-gateway/issues/172)）
- 93e31967 被污染 CSRF token 清洗 + 凭证头去重；0985a802 过期 CSRF JWT 静默自愈（关联 [#153](https://gitcode.com/openlibing/openlibing-gateway/issues/153)、[#127](https://gitcode.com/openlibing/openlibing-gateway/issues/127)、[#125](https://gitcode.com/openlibing/openlibing-gateway/issues/125)、[#124](https://gitcode.com/openlibing/openlibing-gateway/issues/124)）
- 32864dee / df584caf 账号白名单 fail-closed + Redis 缓存 HMAC 完整性（关联 [#149](https://gitcode.com/openlibing/openlibing-gateway/issues/149)、[#146](https://gitcode.com/openlibing/openlibing-gateway/issues/146)、[#154](https://gitcode.com/openlibing/openlibing-gateway/issues/154)）
- 775f742b 白名单查找强制 HTTP 方法匹配（关联 [#154](https://gitcode.com/openlibing/openlibing-gateway/issues/154)）
- c638bfa4 lGet 失败 fail-closed（吊销凭证检查）；4bc1e592 Redis 连接失败记日志
- db6dd42d 绑定通知邮件外部字段 HTML 转义；be607c57 解绑端点 GET→POST（关联 [#142](https://gitcode.com/openlibing/openlibing-gateway/issues/142)）
- 6c51c0a2 绑定 token 清理 Redis key 与读取 key 对齐
- df438a4b WebFilter 全局安全响应头；a784af2e 认证 Cookie 增加 SameSite=Lax
- 02452555 GitHub 回调 Redis 故障返回固定 500 body；0cc8d1cb 移除无意义 hashCode()==401 校验
- 62a56dfe 移除废弃机机接口认证；aec60143 移除 InterfaceRateLimitFilter webhook 豁免（关联 [#152](https://gitcode.com/openlibing/openlibing-gateway/issues/152)）
- e61f6acb / d12bf9f9 / c6f97d41 公开接口凭证校验与完整 CSRF 攻击检测（关联 [#145](https://gitcode.com/openlibing/openlibing-gateway/issues/145)）
- 76ef5c66 OkHttpClient 单例共享（关联 [#131](https://gitcode.com/openlibing/openlibing-gateway/issues/131) TLS 校验项）
- 8263ad50 deleteAccount 吊销 refresh 凭证

## Gateway 仓全部【安全】类 issues 关联清单（41 个）

### 本批次已修复（spec 覆盖或随批次交付）

[#124](https://gitcode.com/openlibing/openlibing-gateway/issues/124)、[#125](https://gitcode.com/openlibing/openlibing-gateway/issues/125)、[#127](https://gitcode.com/openlibing/openlibing-gateway/issues/127)、[#143](https://gitcode.com/openlibing/openlibing-gateway/issues/143)、[#144](https://gitcode.com/openlibing/openlibing-gateway/issues/144)、[#146](https://gitcode.com/openlibing/openlibing-gateway/issues/146)、[#147](https://gitcode.com/openlibing/openlibing-gateway/issues/147)、[#148](https://gitcode.com/openlibing/openlibing-gateway/issues/148)、[#149](https://gitcode.com/openlibing/openlibing-gateway/issues/149)、[#150](https://gitcode.com/openlibing/openlibing-gateway/issues/150)、[#151](https://gitcode.com/openlibing/openlibing-gateway/issues/151)、[#152](https://gitcode.com/openlibing/openlibing-gateway/issues/152)、[#153](https://gitcode.com/openlibing/openlibing-gateway/issues/153)、[#154](https://gitcode.com/openlibing/openlibing-gateway/issues/154)、[#158](https://gitcode.com/openlibing/openlibing-gateway/issues/158)、[#161](https://gitcode.com/openlibing/openlibing-gateway/issues/161)、[#165](https://gitcode.com/openlibing/openlibing-gateway/issues/165)、[#166](https://gitcode.com/openlibing/openlibing-gateway/issues/166)、[#167](https://gitcode.com/openlibing/openlibing-gateway/issues/167)、[#168](https://gitcode.com/openlibing/openlibing-gateway/issues/168)、[#169](https://gitcode.com/openlibing/openlibing-gateway/issues/169)、[#171](https://gitcode.com/openlibing/openlibing-gateway/issues/171)、[#172](https://gitcode.com/openlibing/openlibing-gateway/issues/172)

### 本批次修复中，待 PR !235 合入后关闭

[#162](https://gitcode.com/openlibing/openlibing-gateway/issues/162)（M-0001 开放重定向）、[#164](https://gitcode.com/openlibing/openlibing-gateway/issues/164)（M-0004 静默刷新绕过 CSRF）、[#170](https://gitcode.com/openlibing/openlibing-gateway/issues/170)（纵向权限盲区，修复方式为过滤器下线）

### 早前批次（10 月及以前）已修复

[#128](https://gitcode.com/openlibing/openlibing-gateway/issues/128)（GithubOAuthUtil 日志敏感信息，随 CI 告警存量修复）、[#159](https://gitcode.com/openlibing/openlibing-gateway/issues/159)、[#160](https://gitcode.com/openlibing/openlibing-gateway/issues/160)（随 operation-log 与依赖收敛批次）

### 待修复 / 跟踪中（open，未在本批次范围）

[#126](https://gitcode.com/openlibing/openlibing-gateway/issues/126)（contains 白名单校验潜在绕过，部分随 775f742b 缓解）、[#129](https://gitcode.com/openlibing/openlibing-gateway/issues/129)（Dockerfile 提权）、[#130](https://gitcode.com/openlibing/openlibing-gateway/issues/130)（不安全密码算法）、[#131](https://gitcode.com/openlibing/openlibing-gateway/issues/131)（出站 TLS 校验 / Redis 明文缓存）、[#132](https://gitcode.com/openlibing/openlibing-gateway/issues/132)（CVE-2026-59314 等）、[#134](https://gitcode.com/openlibing/openlibing-gateway/issues/134)（威胁建模）、[#135](https://gitcode.com/openlibing/openlibing-gateway/issues/135)（majun token 明文）、[#136](https://gitcode.com/openlibing/openlibing-gateway/issues/136)（RabbitMQ TLS）、[#138](https://gitcode.com/openlibing/openlibing-gateway/issues/138)（ICSL 安全缺陷）、[#139](https://gitcode.com/openlibing/openlibing-gateway/issues/139)（argus 漏洞挖掘分析）、[#142](https://gitcode.com/openlibing/openlibing-gateway/issues/142)（GET 提交敏感数据，部分随 be607c57 缓解）

## 配套安全设计文档

- [security-design.md](../system_design/security-design.md)
- [threat-model.md](../system_design/threat-model.md)

## 归档日期

2026-11-16
