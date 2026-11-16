# openlibing-gateway 2026-11 安全整改批次 — 归档总览

## 概述

2026 年 11 月，openlibing-gateway 针对漏洞报告（VULN-* 扫描、auth-session-gray-release / gateway-auth-whitelist-range / operation-log-and-perm-scheme 专项）完成一批安全整改，共 11 个已立规格的修复项（见同目录各 task_design 子目录）+ 若干横向加固修复。本文件为批次总览，并按工作区规范关联 gateway 仓本次安全整改的全部 issues（#154~#172）。

## 交付载体

| 批次                           | PR                                                                                                                                                          | 状态                 | 内容                                                          |
| ------------------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------- | ------------------------------------------------------------- |
| 前置批次（11-03 ~ 11-07 上半） | [!223](https://gitcode.com/openlibing/openlibing-gateway/merge_requests/223) / [!225](https://gitcode.com/openlibing/openlibing-gateway/merge_requests/225) | 已合入               | 公开接口凭证校验、fail-closed 白名单、白名单 HMAC 完整性      |
| 主批次（11-07 ~ 11-07 下半）   | [!232](https://gitcode.com/openlibing/openlibing-gateway/merge_requests/232)                                                                                | 已合入（2026-11-16） | harden token, whitelist and csrf handling on release_20261116 |
| 尾批次（11-13 ~ 11-16）        | [!235](https://gitcode.com/openlibing/openlibing-gateway/merge_requests/235)                                                                                | **待合入**（open）   | harden auth, oauth and redis handling                         |

## 已立规格的修复项 ↔ Issue 映射

| spec 目录                        | 关联 Issue                                                                                                                                                                                  | 主修复 commit                | PR          |
| -------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------- | ----------- |
| fix-open-redirect-bind-authoriz  | [#162](https://gitcode.com/openlibing/openlibing-gateway/issues/162)（M-0001 开放重定向）                                                                                                   | bbba6249                     | !235        |
| fix-plugin-auth-code-consumption | [#165](https://gitcode.com/openlibing/openlibing-gateway/issues/165)（M-0005）、[#144](https://gitcode.com/openlibing/openlibing-gateway/issues/144)（Redis Key 遍历，同源）                | 790bf0b4                     | !235        |
| fix-logout-grace-key-revocation  | [#166](https://gitcode.com/openlibing/openlibing-gateway/issues/166)（M-0007 登出会话复活）                                                                                                 | 40fe979a                     | !235        |
| fix-exception-log-uri-redaction  | [#161](https://gitcode.com/openlibing/openlibing-gateway/issues/161)（M-0004 异常日志泄凭证）                                                                                               | 5d826ed6                     | !235        |
| fix-login-brute-force-protection | [#148](https://gitcode.com/openlibing/openlibing-gateway/issues/148)、[#158](https://gitcode.com/openlibing/openlibing-gateway/issues/158)（L-0011 暴力破解，双录）                         | 8661bc75                     | !235        |
| fix-refresh-token-key-alignment  | [#149](https://gitcode.com/openlibing/openlibing-gateway/issues/149)（L-0013 刷新令牌 key 不一致）                                                                                          | e394104d                     | !235        |
| fix-idor-query-bind-accounts     | [#151](https://gitcode.com/openlibing/openlibing-gateway/issues/151)（H-0002 IDOR）、[#163](https://gitcode.com/openlibing/openlibing-gateway/issues/163)（M-0003 IDOR）                    | 9e14a5ec、a6f287da、e55584ba | !232 / !235 |
| fix-silent-refresh-csrf-bypass   | [#164](https://gitcode.com/openlibing/openlibing-gateway/issues/164)（M-0004 静默刷新绕过 CSRF）                                                                                            | 971790f3、0985a802           | !235        |
| fix-oauth-bind-state-session     | [#169](https://gitcode.com/openlibing/openlibing-gateway/issues/169)（绑定劫持）                                                                                                            | ab7285a4                     | !235        |
| fix-verify-token-allow-expired   | [#110](https://gitcode.com/openlibing/openlibing-gateway/issues/110)（缺陷：token 过期 500→401）                                                                                            | bc5281a1                     | !232        |
| remove-cicd-permission-check     | [#170](https://gitcode.com/openlibing/openlibing-gateway/issues/170)（纵向权限盲区）、[#101](https://gitcode.com/openlibing/openlibing-gateway/issues/101)（缺陷：cicd 拦截器拦截其他模块） | 42b44a4b                     | !232        |

## 横向加固修复（未单独立规格，随批次 PR 交付）

- 235301ca X-Forwarded-For 不再信任客户端头（关联 [#171](https://gitcode.com/openlibing/openlibing-gateway/issues/171)）
- 12ea69b8 / 1a7bc16c access_token 改走 Authorization 头、移除 query 参数信任（关联 [#172](https://gitcode.com/openlibing/openlibing-gateway/issues/172)、[#168](https://gitcode.com/openlibing/openlibing-gateway/issues/168)、[#152](https://gitcode.com/openlibing/openlibing-gateway/issues/152)）
- ab7285a4 OAuth token-exchange 凭证从 URL 移入 form body（关联 [#172](https://gitcode.com/openlibing/openlibing-gateway/issues/172)）
- 93e31967 被污染 CSRF token 清洗 + 凭证头去重（关联 [#125](https://gitcode.com/openlibing/openlibing-gateway/issues/125)、[#126](https://gitcode.com/openlibing/openlibing-gateway/issues/126)、[#128](https://gitcode.com/openlibing/openlibing-gateway/issues/128)、[#154](https://gitcode.com/openlibing/openlibing-gateway/issues/154)）；0985a802 过期 CSRF JWT 静默自愈
- aec60143 移除 InterfaceRateLimitFilter webhook 豁免（关联 [#153](https://gitcode.com/openlibing/openlibing-gateway/issues/153) Gitee Webhook 重放）
- 32864dee / df584caf / 775f742b 账号白名单 fail-closed + Redis 缓存 HMAC 完整性 + 强制 HTTP 方法匹配（关联 [#150](https://gitcode.com/openlibing/openlibing-gateway/issues/150)、[#147](https://gitcode.com/openlibing/openlibing-gateway/issues/147)、[#155](https://gitcode.com/openlibing/openlibing-gateway/issues/155)）
- c638bfa4 lGet 失败 fail-closed（吊销凭证检查）；4bc1e592 Redis 连接失败记日志
- db6dd42d 绑定通知邮件外部字段 HTML 转义；be607c57 解绑端点 GET→POST（关联 [#143](https://gitcode.com/openlibing/openlibing-gateway/issues/143)）
- 6c51c0a2 绑定 token 清理 Redis key 与读取 key 对齐
- df438a4b WebFilter 全局安全响应头；a784af2e 认证 Cookie 增加 SameSite=Lax
- 02452555 GitHub 回调 Redis 故障返回固定 500 body；0cc8d1cb 移除无意义 hashCode()==401 校验
- 62a56dfe 移除废弃机机接口认证
- e61f6acb / d12bf9f9 / c6f97d41 公开接口凭证校验与完整 CSRF 攻击检测（关联 [#146](https://gitcode.com/openlibing/openlibing-gateway/issues/146)）
- M-0013 public 页面身份参数剥离（随公开接口分支加固覆盖，见 [#167](https://gitcode.com/openlibing/openlibing-gateway/issues/167)）
- 76ef5c66 OkHttpClient 单例共享（关联 [#132](https://gitcode.com/openlibing/openlibing-gateway/issues/132) TLS 校验项）
- 8263ad50 deleteAccount 吊销 refresh 凭证

## 本批次安全整改修复 issues（#154~#172，共 19 个）

[#154](https://gitcode.com/openlibing/openlibing-gateway/issues/154)（CSRF 签名未比对）、[#155](https://gitcode.com/openlibing/openlibing-gateway/issues/155)（H-0002 contains 白名单）、[#156](https://gitcode.com/openlibing/openlibing-gateway/issues/156) / [#157](https://gitcode.com/openlibing/openlibing-gateway/issues/157)（UT/build 门禁）、[#158](https://gitcode.com/openlibing/openlibing-gateway/issues/158)（L-0011 暴力破解）、[#159](https://gitcode.com/openlibing/openlibing-gateway/issues/159)（H-0002 审计失真）、[#160](https://gitcode.com/openlibing/openlibing-gateway/issues/160)（H-0006 netty 回退）、[#161](https://gitcode.com/openlibing/openlibing-gateway/issues/161)（M-0004 异常日志）、[#162](https://gitcode.com/openlibing/openlibing-gateway/issues/162)（M-0001 开放重定向）、[#163](https://gitcode.com/openlibing/openlibing-gateway/issues/163)（M-0003 IDOR）、[#164](https://gitcode.com/openlibing/openlibing-gateway/issues/164)（M-0004 静默刷新 CSRF）、[#165](https://gitcode.com/openlibing/openlibing-gateway/issues/165)（M-0005 auth code）、[#166](https://gitcode.com/openlibing/openlibing-gateway/issues/166)（M-0007 登出绕过）、[#167](https://gitcode.com/openlibing/openlibing-gateway/issues/167)（M-0013 身份剥离）、[#168](https://gitcode.com/openlibing/openlibing-gateway/issues/168)（access_token 注入）、[#169](https://gitcode.com/openlibing/openlibing-gateway/issues/169)（绑定劫持）、[#170](https://gitcode.com/openlibing/openlibing-gateway/issues/170)（纵向权限盲区）、[#171](https://gitcode.com/openlibing/openlibing-gateway/issues/171)（XFF 伪造）、[#172](https://gitcode.com/openlibing/openlibing-gateway/issues/172)（OAuth 凭据泄露）

其中 [#170](https://gitcode.com/openlibing/openlibing-gateway/issues/170)、[#171](https://gitcode.com/openlibing/openlibing-gateway/issues/171) 修复已交付（!232 / !235），issue 待 !235 合入后关闭。

## 本批次同时关联的早批次安全/缺陷 issues

同型双录（whitelist-range / auth-session-gray-release 漏洞单，随本批次一并修复）：[#147](https://gitcode.com/openlibing/openlibing-gateway/issues/147)、[#148](https://gitcode.com/openlibing/openlibing-gateway/issues/148)、[#149](https://gitcode.com/openlibing/openlibing-gateway/issues/149)、[#150](https://gitcode.com/openlibing/openlibing-gateway/issues/150)、[#151](https://gitcode.com/openlibing/openlibing-gateway/issues/151)、[#152](https://gitcode.com/openlibing/openlibing-gateway/issues/152)、[#153](https://gitcode.com/openlibing/openlibing-gateway/issues/153)；历史【安全】/缺陷关联：[#101](https://gitcode.com/openlibing/openlibing-gateway/issues/101)、[#110](https://gitcode.com/openlibing/openlibing-gateway/issues/110)、[#125](https://gitcode.com/openlibing/openlibing-gateway/issues/125)、[#126](https://gitcode.com/openlibing/openlibing-gateway/issues/126)、[#127](https://gitcode.com/openlibing/openlibing-gateway/issues/127)、[#128](https://gitcode.com/openlibing/openlibing-gateway/issues/128)、[#129](https://gitcode.com/openlibing/openlibing-gateway/issues/129)、[#143](https://gitcode.com/openlibing/openlibing-gateway/issues/143)、[#144](https://gitcode.com/openlibing/openlibing-gateway/issues/144)、[#145](https://gitcode.com/openlibing/openlibing-gateway/issues/145)、[#146](https://gitcode.com/openlibing/openlibing-gateway/issues/146)；跟踪中（未在本批次范围，open）：[#130](https://gitcode.com/openlibing/openlibing-gateway/issues/130)（Dockerfile 提权）、[#131](https://gitcode.com/openlibing/openlibing-gateway/issues/131)（不安全密码算法）、[#132](https://gitcode.com/openlibing/openlibing-gateway/issues/132)（出站 TLS/明文缓存）、[#133](https://gitcode.com/openlibing/openlibing-gateway/issues/133)（CVE-2026-59314 等）、[#135](https://gitcode.com/openlibing/openlibing-gateway/issues/135)（威胁建模）、[#136](https://gitcode.com/openlibing/openlibing-gateway/issues/136)（majun token 明文）、[#137](https://gitcode.com/openlibing/openlibing-gateway/issues/137)（RabbitMQ TLS）、[#139](https://gitcode.com/openlibing/openlibing-gateway/issues/139)（ICSL 安全缺陷）、[#140](https://gitcode.com/openlibing/openlibing-gateway/issues/140)（argus 漏洞挖掘）

## 发布报告

- [release_20261116 发布报告](../../../release_docs/openlibing-gateway/release_20261116/7a0d84e7/gateway_release_report.md)

## 配套安全设计文档

- [security-design.md](../system_design/security-design.md)
- [threat-model.md](../system_design/threat-model.md)

## 归档日期

2026-11-16
