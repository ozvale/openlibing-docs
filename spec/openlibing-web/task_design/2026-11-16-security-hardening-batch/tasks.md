# tasks — 2026-11 安全加固批次

> 全部步骤已完成；对应提交均已包含在分支 `jzcfork/202611safe`（PR #904）中。

## 1. 依赖供应链

- [x] `bed425a2` bump 14 个易受攻击传递依赖至补丁版本（@babel/core、@humanfs/node、colord、echarts、fast-uri、glob、katex、minimatch、nitropack、postcss-selector-parser、qs、serialize-javascript、turbo）
- [x] `bed425a2` 为易受攻击传递依赖添加 pnpm overrides，覆盖精确锁版消费方
- [x] `bed425a2` catalog 与 overrides 全部精确锁版（与 lock 解析结果一致）
- [x] `77c7d19e` 移除 element-ui、ztree 依赖声明、catalog 条目、lock 记录及仅可达的死源码（src/sca 遗留 Vue 2 代码）
- [x] `91bdbbc1` 删除 majun 从未被引用的 config.json（独有 key 无消费方）
- [x] 合并 upstream 后 `pnpm-workspace.yaml` 冲突解决：保留我方精确锁版 + 补回 release 新增 `@vitest/coverage-v8: 3.2.4`，`pnpm install` 重新生成 lock

## 2. XSS

- [x] `2c0f7fd8` majun WangEditor `getEditorHtml()` 输出经 `handleContent`（xssFilter）净化
- [x] `a8d04f0f` transferTestEmail（releaseComponents + LTS）邮件正文模板层过 xssFilter（WEB-11，数据层过滤保留作纵深防御）
- [x] `3af1431b` `utils/until.js` 移除绕过内置 safeAttrValue 的自定义 onTagAttr（M-0012）

## 3. 注入 / 参数篡改

- [x] `92eefa8e` InterfaceManage iframe repoUrl 经 `isSafeClientRedirectUrl` 对四平台主机白名单校验，失败丢弃并 console.warn（M-0003）
- [x] `92eefa8e` 校验改精确 hostname 匹配，封堵 `gitcode.com.evil.com` 仿冒
- [x] `43dfcf34` InterfaceReview iframe src 改 URLSearchParams 组装，停止透传宿主路由 query
- [x] `38183cb0` jumpIntermediate 增加剥离 userinfo 的 safeUrl computed，展示/跳转/信任域保存统一使用规范化地址
- [x] `3af1431b` releaseComponents add.vue `planIssue` 存储前经 `isSafeClientRedirectUrl` 校验 http/https；detail.vue 移除 raw-href plan 块与注释死代码
- [x] `2c0f7fd8` openEuler 相对路径黑名单改字符白名单 + 拒 `//` 与 `..` 分段（M-0027，Ref argus M-0027）

## 4. OAuth / 重定向

- [x] `3af1431b` Content.vue vscode client `targetPluginId` 按 config.json `VSC_PLUGIN_ID_ALLOWLIST` + 扩展 ID 格式正则校验

## 5. 会话与凭证

- [x] `846d85c3` disableCopy 指令改命名模块级处理器，unmounted 真正解绑 copy/cut/keydown
- [x] `846d85c3` input-password 基础组件统一拦截 copy/cut；TokenCompositeInput 补 contextmenu 拦截（SENS-06）
- [x] `846d85c3` 移除泄露 userInfo、注册/找回密码提交值、产品表单的 console 日志（SENS-11）
- [x] `846d85c3` utils/auth.js 与 majun auth.ts 遗留 token cookie 补 Secure/SameSite（SENS-03）
- [x] `245a7487` 确认两条 document.cookie/js-cookie 写路径为死代码后仍补齐属性（WEB-16）
- [x] `846d85c3` gitleaks 对 .vue 模板 camelCase 标识符的显式密码规则误报加 allowlist
- [x] `f3809744` banner 每 5 分钟轮询评审数且不带 token 头
- [x] `2c0f7fd8` cookiePolicy `privacyCookieConsent` 改 `disableToken` 发送，cookie/抽屉处理移入 finally（失败也执行）

## 6. 传输安全

- [x] `1e3278a7` nginx CORS 改 `https://*.openlibing.com` 白名单 map，五个响应头链式门控（FIND-01，CWE-942）

## 7. 配置治理

- [x] `f4022fc6` 27 个文件硬编码域名/白名单收敛到 `src/assets/js/config.json`（微应用 dev URL 约 19 处、SDK 端点、主机白名单、文档/备案/下载链接、AI_CODEFIX）
- [x] `f4022fc6` NoApplicationPermission.vue WECARE URL `&amp;` HTML 实体修复（查询参数误解析）
- [x] `7e797f4c` 移除 .env.gamma/.env.production 的 vben demo mock 地址与未用 preview script
- [x] `fc8cffad` beta/gamma env 指向内网联调地址，域名配置保留为注释行

## 8. 死代码清理

- [x] `284fae9f` 删除 gitUrlList.vue `queryBranchCommiter()` 与 initData 调用（结果写入非响应式字段且从未消费）
- [x] `284fae9f` 删除孤儿 API `queryCommiterList`（/open/scan/find/repoCommitter 无前端调用方）

## 9. 集成与交付

- [x] `7e797f4c` chore 清理
- [x] `a571af4c` 合并 upstream/release_20261116，解决 .env.beta/.env.gamma/pnpm-lock.yaml/pnpm-workspace.yaml 四处冲突
- [x] pre-commit 全部 Passed（gitleaks/Prettier/ESLint/merge-conflict/yaml/large-files）
- [x] PR #904 创建并补打 `ai-assisted` 标签：https://gitcode.com/openlibing/openlibing-web/merge_requests/904
- [x] 冲突解决后推送，GitCode `mergeable: True`

## 后续待办

- [ ] 后端仓落地 `checkReviewPackageUrl` 服务端校验（协议/域名/IP 白名单 + 内网阻断，P0）
- [ ] 正式发布前将 env 内网联调地址恢复为域名配置
- [ ] PR #904 CI（含新增 ut.yml 单测流）与审批门禁跟进
- [ ] 业务 PR 合入后补 archive.md 并走 docs 仓归档 PR
