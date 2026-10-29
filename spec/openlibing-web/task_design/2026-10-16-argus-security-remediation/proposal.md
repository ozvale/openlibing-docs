# Argus 安全扫描问题整改（12 项）

- 分支：`jzcfork/202610argusfix`
- 核心提交：`fba6aaaf`、`3b4a9e7b`、`50903570`、`5c3a13ca`、`3386d502`、`61e20b0c`、`368b46b5`、`dafd25d1`、`0718fd37`、`6a0b4798`、`8564cad3`

## Why

Argus 安全扫描在 openlibing-web 确认了 12 项风险，覆盖四类：

1. **HTTP 安全响应头缺失/不生效**：nginx 未下发 HSTS、CSP、`X-Frame-Options`；CORS 使用通配来源；`add_header` 在 `location` 与 `server` 之间继承断裂，部分路径实际无安全头。
2. **开放重定向与前端注入**：`Content.vue` 的客户端跳转未校验目标主机；`Login.vue` 拼接跳转参数未编码；富文本 img 过滤存在白名单回归（`defaultImgMd` 兜底可被滥用）。
3. **SSRF**：`securityScanning.vue` / `add.vue` 的内网地址判定只覆盖 IPv4，IPv6 私网地址可绕过。
4. **登录态与凭证暴露**：`PRManage/list.vue` 用接口响应直接覆盖 `app.user`；仓库公共账号 token 输入框可明文查看/复制/剪切。

同时清理若干历史遗留（被覆盖的 `X-Forwarded-For` 配置、已下线的 `/aurogon-web` 代理、vben 内置登录模块、灵枢菜单入口）。

## What Changes

1. **nginx 安全头与 CORS（beta / gamma / prod / prod_new）**

   - 新增 `map $http_origin $cors_origin`，仅放行 `https://<任意子域>.openlibing.com`。
   - 启用 `Strict-Transport-Security "max-age=31536000; includeSubDomains" always`。
   - 启用 CSP：`script-src 'self' https://res.hc-cdn.com 'unsafe-inline' 'unsafe-eval'`、`worker-src blob:`、`object-src 'none'`；后续追加 UEM SDK、华为 CS SDK 域名。
   - 启用 `X-Frame-Options SAMEORIGIN always`。
   - `Access-Control-Allow-Origin` 取 `$cors_origin`，并补 `Vary "Origin" always`。
   - 修复响应头继承断裂：http 级 map 驱动 server 级 `add_header`，恢复 `location /` 与 `/assets/` 的安全头/缓存头；beta/gamma gateway 因 `Set-Cookie` 切断继承，显式补齐。
   - 删除被覆盖的冗余 `X-Forwarded-For` 配置；删除 beta/gamma `/aurogon-web` 代理；beta 新增并修正 `/build` 代理指向 cicd-web。

2. **开放重定向防护**

   - `src/utils/until.js` 新增 `isAllowedRedirectHostname(hostname, allowedHostnames)`（支持 `*.example.com` 通配）。
   - `isSafeClientRedirectUrl(url, allowedProtocols, allowedHostnames)` 增加第三参主机白名单校验。
   - `src/views/Content.vue` 定义 `AGENT_ARENA_REDIRECT_HOSTS = ['openlibing.com','*.openlibing.com','localhost','127.0.0.1']` 并传入。

3. **参数编码**：`src/views/Login.vue` 的 `goLogin` 对 `client`、`state`、`pluginId` 全部 `encodeURIComponent`。

4. **路径穿越收敛**：`WujieMiddleware.vue` 的 `appendPathMatchToUrl` 先 `filter(s => s !== '.' && s !== '..')` 再 encode。

5. **富文本 img 白名单回归修复**

   - 新增 `isAllowedImgSrc(value)`：允许 `data:image/`、`window.location.origin + '/'` 前缀、以 `/` 开头但不以 `//` 或 `/\` 开头的相对路径。
   - 非白名单直接返回 `''`（移除 `defaultImgMd` 兜底）。
   - `onTag` 重建 img 时保留白名单属性（`class`/`width`/`height`/`alt`）。

6. **SSRF IPv6 加固**：`isLocalOrPrivateHost` 增加 IPv6 判定——`::1`/`::`、IPv4-mapped（`::ffff:0:0/96`）、ULA（`fc00::/7`）、链路本地（`fe80::/10`）；`securityScanning.vue` 与 `add.vue` 两处同步。

7. **登录态保护**：`PRManage/list.vue` 的 `refreshUser` 仅在 `payload` 为对象、`Array.isArray(payload.permissions)` 且 `typeof payload.userName === 'string' && length > 0` 时才写入 `app.user`（CWE-754）。

8. **防重复提交**：`InterfaceManage/index.vue`、`securityScanning.vue`、`add.vue`、`BranchReview.vue`、`RepoReview.vue`、`myToDo.vue` 增加 `submitting` 等状态守卫。

9. **路由权限补漏**：`router/routes/modules/noMenu.ts` 的 InterfaceReview 路由补 `meta.auth = 'interface_manage'`。

10. **凭证输入加固**：`Repos/dialog/GlobalConfigDialog.vue` 移除 `show-password`，增加 `autocomplete="new-password"` 与 `@copy.prevent @cut.prevent @contextmenu.prevent`。

11. **历史清理**：删除 vben 内置登录模块（`src/views/_core/authentication/login.vue`、`packages/@core/base/common-ui/src/ui/authentication/login.vue` 及其导出、`layouts/basic.vue` 引用）；移除灵枢菜单入口。

## Capabilities

### New

- 前端重定向主机白名单校验能力（`isAllowedRedirectHostname` / `isSafeClientRedirectUrl` 三参）。
- 图片地址白名单校验能力（`isAllowedImgSrc`）。
- IPv6 私网/本地地址识别能力。
- nginx 统一 CORS 白名单（`$cors_origin`）。

### Modified

- 全部 nginx 站点的安全响应头下发策略。
- 富文本 XSS 过滤的 img 处理路径。
- 登录跳转参数编码方式。
- 仓库公共账号 token 的输入可读性（不可见、不可复制）。
- 若干页面的提交按钮防重逻辑。

### Removed

- vben 内置登录页（前端已统一走自有登录）。
- 灵枢菜单入口。
- `/aurogon-web` 代理（beta/gamma）。
- 冗余被覆盖的 `X-Forwarded-For` 配置。

## Impact

### 受影响代码

| 文件                                                                                                       | 影响                                |
| ---------------------------------------------------------------------------------------------------------- | ----------------------------------- |
| `apps/web-openlibing/nginx/nginx_{beta,gamma,prod,prod_new}.conf`                                          | 安全头、CORS、代理位置调整          |
| `apps/web-openlibing/src/utils/until.js`                                                                   | 新增 3 个校验函数；img 过滤逻辑重写 |
| `src/views/Content.vue`                                                                                    | 跳转主机白名单                      |
| `src/views/Login.vue`                                                                                      | 参数编码                            |
| `src/views/WujieMiddleware.vue`                                                                            | 路径分段过滤                        |
| `src/views/PRManage/list.vue`                                                                              | 用户信息写入守卫                    |
| `src/views/InterfaceManage/index.vue`                                                                      | 防重复提交                          |
| `src/views/Publish/platformRelease/ltsComponents/publishReviewDetail/transferTesting/securityScanning.vue` | SSRF IPv6 + 防重复提交              |
| `src/views/Publish/platformRelease/updateComponents/releaseComponents/add.vue`                             | SSRF IPv6 + 防重复提交              |
| `src/views/BranchReview.vue`、`RepoReview.vue`、`myToDo.vue`                                               | 防重复提交                          |
| `src/router/routes/modules/noMenu.ts`                                                                      | 路由 auth 补漏                      |
| `src/router/routes/modules/menu.ts`                                                                        | 移除灵枢入口                        |
| `src/views/Repos/dialog/GlobalConfigDialog.vue`                                                            | token 输入加固                      |
| `src/views/_core/authentication/login.vue` 等 4 文件                                                       | 删除内置登录模块                    |
| `src/layouts/basic.vue`                                                                                    | 删除内置登录引用                    |

### 明确不受影响

- 后端接口契约、鉴权协议不变。
- 业务功能主流程不变（仅安全校验与提交守卫）。

### 风险

- CSP 启用后若存在未列入白名单的第三方脚本会被拦截，需灰度验证；已知需放行 `res.hc-cdn.com`、UEM SDK、华为 CS SDK。
- `X-Frame-Options: SAMEORIGIN` 会影响被第三方 iframe 嵌入场景。
- 富文本 img 过滤收紧后，历史内容中不合规图片将不再渲染。
- IPv6 判定扩展可能误判合法公网 IPv6（已限定为私网/本地段，风险低）。
