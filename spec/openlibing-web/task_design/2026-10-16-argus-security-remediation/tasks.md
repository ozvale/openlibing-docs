# 任务：Argus 安全扫描问题整改

> 分支：`jzcfork/202610argusfix`　核心提交：`fba6aaaf`、`3b4a9e7b`、`50903570`、`5c3a13ca`、`3386d502`、`61e20b0c`、`368b46b5`、`dafd25d1`、`0718fd37`、`6a0b4798`、`8564cad3`

## 1. nginx 安全响应头与 CORS

- [x] 四个站点（beta/gamma/prod/prod_new）新增 `map $http_origin $cors_origin`，仅放行 `https://*.openlibing.com`
- [x] 启用 `Strict-Transport-Security "max-age=31536000; includeSubDomains" always`
- [x] 启用 CSP（`script-src` 白名单 + `worker-src blob:` + `object-src 'none'`）
- [x] 启用 `X-Frame-Options SAMEORIGIN always`
- [x] `Access-Control-Allow-Origin` 改为 `$cors_origin`，补 `Vary "Origin" always`
- [x] 修复响应头继承断裂：`location /`、`/assets/` 及会切断继承的 location 显式补齐安全头与 CORS 头
- [x] CSP 追加 UEM SDK 域名（`50903570`）
- [x] CSP 追加华为 CS SDK 域名（`5c3a13ca`）
- [x] 删除被覆盖的冗余 `X-Forwarded-For` 配置（`3386d502`）
- [x] 删除 beta/gamma 已下线 `/aurogon-web` 代理（`61e20b0c`）
- [x] beta 新增 `/build` 代理指向 cicd 微前端（`368b46b5`），并修正指向 beta cicd-web 服务（`dafd25d1`）

## 2. 开放重定向与参数编码

- [x] `until.js` 新增 `isAllowedRedirectHostname(hostname, allowedHostnames)`，支持 `*.example.com` 通配
- [x] `isSafeClientRedirectUrl(url, allowedProtocols, allowedHostnames)` 增加主机白名单参数
- [x] `Content.vue` 定义 `AGENT_ARENA_REDIRECT_HOSTS` 并传入
- [x] `Login.vue` 对 `client`、`state`、`pluginId` 做 `encodeURIComponent`
- [x] `WujieMiddleware.vue` 的 `appendPathMatchToUrl` 过滤 `.`/`..` 分段后再编码

## 3. 富文本 XSS 与 img 过滤

- [x] 新增 `isAllowedImgSrc(value)`（`data:image/`、同源前缀、站内相对路径）
- [x] 非法 src 直接返回 `''`，移除 `defaultImgMd` 兜底
- [x] `onTag` 重建 img 时保留 `class`/`width`/`height`/`alt`
- [x] 二次修复 img 过滤回归（`3b4a9e7b`）

## 4. SSRF 加固

- [x] `isLocalOrPrivateHost` 增加 IPv6：`::1`/`::`、`::ffff:0:0/96`、`fc00::/7`、`fe80::/10`
- [x] `securityScanning.vue` 同步 IPv6 判定
- [x] `add.vue` 同步 IPv6 判定

## 5. 登录态与凭证安全

- [x] `PRManage/list.vue` 的 `refreshUser` 增加结构校验后才写 `app.user`
- [x] `noMenu.ts` 的 InterfaceReview 路由补 `meta.auth = 'interface_manage'`
- [x] `GlobalConfigDialog.vue` 移除 `show-password`，加 `autocomplete="new-password"` 与 `@copy/@cut/@contextmenu.prevent`

## 6. 防重复提交

- [x] `InterfaceManage/index.vue` 增加提交守卫
- [x] `securityScanning.vue` 增加提交守卫
- [x] `add.vue` 增加提交守卫
- [x] `BranchReview.vue` 增加 `submitting` 守卫
- [x] `RepoReview.vue` 增加 `submitting` 守卫
- [x] `myToDo.vue` 增加提交守卫

## 7. 历史清理

- [x] 删除 `src/views/_core/authentication/login.vue`
- [x] 删除 `packages/@core/base/common-ui/src/ui/authentication/login.vue`
- [x] 移除 authentication 统一导出
- [x] 移除 `layouts/basic.vue` 中内置登录引用
- [x] 移除灵枢菜单入口（`menu.ts`）

## 8. 验证

- [ ] 四站点 `curl -I` 校验 HSTS / CSP / `X-Frame-Options` / `Vary` 全覆盖（含静态资源与 API）
- [ ] CORS 合法子域回显、非法域为空
- [ ] 开放重定向用例全部拦截
- [ ] 富文本 img 白名单用例（含属性保留）+ XSS 注入用例
- [ ] SSRF 目标 `[::1]` / `[::ffff:127.0.0.1]` / `[fc00::1]` / `[fe80::1]` 均拒绝
- [ ] mock 异常用户信息响应，登录态不被覆盖
- [ ] token 输入框复制/剪切/右键均被阻止
- [ ] beta `/build` 微前端加载正常
- [ ] 删除内置登录模块后构建与登录流程正常

## 9. 交付

- [ ] `pnpm build` 通过（含 nx 构建）
- [ ] ESLint / TypeScript 检查通过
- [ ] 安全扫描（Argus）复测通过
- [ ] 发布说明注明 CSP 白名单与 `X-Frame-Options` 的对外影响
