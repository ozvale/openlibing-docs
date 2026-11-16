# openlibing-web 2026-11 安全加固批次（17 提交）

- 分支：`jzcfork/202611safe`
- 业务 PR：https://gitcode.com/openlibing/openlibing-web/merge_requests/904（head `jiangzhichao:jzcfork/202611safe` → base `release_20261116`）
- 核心提交：`bed425a2`、`f3809744`、`77c7d19e`、`91bdbbc1`、`1e3278a7`、`a8d04f0f`、`245a7487`、`846d85c3`、`f4022fc6`、`284fae9f`、`92eefa8e`、`38183cb0`、`3af1431b`、`7e797f4c`、`43dfcf34`、`2c0f7fd8`、`fc8cffad`

## Why

本批次集中处置 2026 年 11 月安全基线检查与 Argus/majun 扫描在 openlibing-web 确认的多类风险，覆盖六类：

1. **依赖供应链（CVE 整改）**：pnpm 依赖树存在 26 个 CVE 命中，且部分传递依赖以精确锁版方式绕过了范围升级；另有 element-ui、ztree 等仅被 Vue 2 遗留死代码引用的依赖仍在依赖树中。
2. **XSS（CWE-79）**：majun WangEditor 的 `getEditorHtml()` 输出未净化即返回（对照共享组件已净化）；邮件正文 v-html 在模板层未过滤；`xssFilter` 自定义 `onTagAttr` 手工拼接属性绕过了库内置 `safeAttrValue`（Argus M-0012）。
3. **注入 / 参数篡改（CWE-20）**：InterfaceManage 将 `route.query.repoUrl` 未校验直接拼入 iframe src（Argus M-0003）；InterfaceReview iframe 参数字符串拼接；跳转中间页 `jumpIntermediate` 原样渲染含 userinfo 的 URL（`https://www.openlibing.com@evil.example` 钓鱼）；发布评审 `planIssue` 外链未校验协议与主机；发布评审更新组件页 `fullPath` 自由文本未校验直接随 `packageUrls` 提交 `checkReviewPackageUrl`（SSRF，Argus M-0027，CWE-918）。
4. **OAuth 重定向**：Content.vue 的 vscode client `targetPluginId` 未做白名单校验，OAuth code/state 可被重定向到攻击者控制的 `vscode://` 回调目标。
5. **登录态与凭证暴露（SENS 系列）**：disableCopy 指令匿名函数无法解绑导致拦截失效；密码输入组件未统一拦截复制/剪切；console 日志泄露 userInfo 与注册/找回密码提交值（含密码）；遗留 token cookie 缺 Secure/SameSite；banner 轮询携带 token 头。
6. **传输与配置治理**：CORS 反射任意 `$http_origin` 且无条件下发 Allow-Credentials（CWE-942）；27 个文件散落硬编码域名/白名单；.env 遗留 vben demo mock 地址；majun 下存在从未被引用的 config.json。

## What Changes

按主题分组（详细技术方案见 design.md）：

1. **依赖供应链**：bump 14 个易受攻击传递依赖至补丁版本并以 pnpm overrides 钉住（`bed425a2`）；全部 catalog/override 精确锁版（后续提交持续收敛，合并 upstream 后补回 `@vitest/coverage-v8`）；移除 element-ui、ztree 及其仅可达的死源码（`77c7d19e`）；移除 majun 未引用 config.json（`91bdbbc1`）。
2. **XSS**：majun WangEditor `getEditorHtml` 输出经 `handleContent` 净化（`2c0f7fd8`）；邮件正文模板层 `xssFilter`（`a8d04f0f`）；`utils/until.js` 移除绕过 `safeAttrValue` 的自定义 `onTagAttr`（`3af1431b`）。
3. **注入/篡改**：`repoUrl` 经 `isSafeClientRedirectUrl` 对四代码托管平台主机白名单校验、精确 hostname 匹配（`92eefa8e`）；InterfaceReview iframe 参数改 URLSearchParams 并停止透传宿主路由 query（`43dfcf34`）；`jumpIntermediate` 增加剥离 userinfo 的 safeUrl 计算（`38183cb0`）；`planIssue` 存储前经协议/主机校验（`3af1431b`）；openEuler 相对路径黑名单改字符白名单 + 拒 `..`/`//`，非 openEuler 走包 URL 校验（`2c0f7fd8`）。
4. **OAuth**：vscode `targetPluginId` 按 config.json `VSC_PLUGIN_ID_ALLOWLIST` + 扩展 ID 格式正则校验（`3af1431b`）。
5. **会话与凭证**：disableCopy 命名处理器可解绑、密码输入统一拦截、移除敏感 console 日志、遗留 cookie 补 Secure/SameSite（`846d85c3`、`245a7487`）；banner 轮询 5 分钟一次且不带 token 头（`f3809744`）；cookiePolicy `privacyCookieConsent` 改 `disableToken` 发送、失败也走 finally 关闭抽屉（`2c0f7fd8`）。
6. **传输与配置**：CORS 改 `https://*.openlibing.com` 白名单 map 链式门控五个响应头（`1e3278a7`）；27 个文件硬编码域名收敛到 `src/assets/js/config.json` 单一事实源（`f4022fc6`）；移除 vben demo 配置与未用 preview script（`7e797f4c`）；beta/gamma env 指向内网联调地址并保留域名注释行（`fc8cffad`）。
7. **死代码清理**：移除 `queryBranchCommiter`/`queryCommiterList` 及无消费的 `/open/scan/find/repoCommitter` 调用链（`284fae9f`）。

## Acceptance Criteria

- [x] 原始 PoC 复现用例全部被拦截（M-0027 fullPath 18 例静态复现、userinfo 钓鱼 URL、repoUrl 仿冒域名）
- [x] `pnpm audit` CVE 命中数下降至基线要求；catalog/override 与 lock 完全一致
- [x] `pnpm install` + 本地构建通过；pre-commit（gitleaks/Prettier/ESLint/merge-conflict）全部 Passed
- [x] Argus/majun/SENS 对应编号（M-0003、M-0012、M-0027、WEB-11、WEB-16、SENS-03/06/11、FIND-01）在复测中关闭
- [x] 全部变更通过 PR #904 进入 `release_20261116`（冲突已解决，mergeable）

## Out of Scope

- 后端 `checkReviewPackageUrl` 协议/域名/IP 白名单与内网阻断（P0）需在后端仓另行落地
- `vite.config.mts` 本地调试改动不入库
- env 内网联调地址（beta `10.0.15.101:8076` / gamma `10.0.1.109:8071`）为临时状态，正式发布前需恢复域名配置
