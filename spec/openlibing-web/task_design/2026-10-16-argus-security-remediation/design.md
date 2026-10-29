# 设计：Argus 安全扫描问题整改

## Context

Argus 扫描在 openlibing-web 确认 12 项风险，集中在四层：

| 层         | 风险                                            | 现状                                                                     |
| ---------- | ----------------------------------------------- | ------------------------------------------------------------------------ |
| nginx 网关 | 缺 HSTS / CSP / `X-Frame-Options`；CORS 通配    | `add_header` 未加 `always`，且 `location` 内声明会覆盖父级继承           |
| 前端跳转   | 开放重定向、参数未编码、路径穿越                | `Content.vue` 直接跳转 `redirect` 参数；`Login.vue` 拼接未编码           |
| 富文本     | img 过滤回归 + XSS                              | `defaultImgMd` 兜底使非法 src 仍被渲染；`onTag` 重建时丢属性             |
| 请求       | SSRF（仅拦 IPv4）、凭证明文、异常响应覆盖登录态 | `isLocalOrPrivateHost` 无 IPv6；token 输入框可复制；`refreshUser` 无校验 |

第一次整改（`fba6aaaf`）修复了 12 项，但引入了三个回归，由 `3b4a9e7b` 二次修复：nginx 响应头继承断裂、img 过滤把合法图片屏蔽、SSRF 仍可通过 IPv6 映射地址绕过。

## Goals / Non-Goals

### Goals

1. 四个站点（beta/gamma/prod/prod_new）在**所有路径**上稳定下发 HSTS、CSP、`X-Frame-Options`，CORS 只允许 `*.openlibing.com`。
2. 所有跨域/客户端跳转目标经过协议 + 主机白名单双重校验。
3. 富文本 img 只允许安全来源，且保留原有展示属性。
4. 内网/本地地址判定覆盖 IPv6 常见私网段。
5. 登录态不被异常响应覆盖；凭证输入不可复制、不可明文查看。
6. 关键提交按钮防重复提交。

### Non-Goals

- 不改造后端鉴权与接口协议。
- 不引入新的前端安全框架（如 CSP nonce 体系），保持现有 `'unsafe-inline'` 兼容历史脚本。
- 不重构与安全无关的业务页面。

## Decisions

### D1：用 http 级 `map` 驱动 CORS，而非在 `location` 内写死

```nginx
map $http_origin $cors_origin {
    default "";
    "~*^https://([a-z0-9-]+\.)*openlibing\.com$" $http_origin;
}
```

`map` 只能在 `http` 作用域定义，server/location 通过变量引用。好处是来源白名单集中一处，四个站点行为一致，且不合法来源得到空值（浏览器侧等效拒绝）。

### D2：安全头必须显式补齐在会切断继承的 location

nginx 规则：`location` 内一旦出现任一 `add_header`，父级 `add_header` 全部失效。beta/gamma 的 gateway location 需要追加 `Set-Cookie` 处理，因此会切断继承。处置：在 `location /`、`/assets/` 以及所有含 `add_header` 的 location 中显式重复安全头与 CORS 头，并统一加 `always`（保证 4xx/5xx 也下发）。

### D3：CSP 采用"最小可用白名单 + 记录扩展点"

```
script-src 'self' https://res.hc-cdn.com https://hwa.his.huawei.com https://app.huawei.com 'unsafe-inline' 'unsafe-eval';
worker-src blob:;
object-src 'none'
```

- `res.hc-cdn.com`：静态资源 CDN。
- `hwa.his.huawei.com` / `app.huawei.com`：UEM SDK、华为 CS SDK（`50903570`、`5c3a13ca` 两次追加）。
- 保留 `'unsafe-inline'`/`'unsafe-eval'`：历史构建产物与第三方 SDK 依赖，移出需单独评估。

### D4：开放重定向采用"协议白名单 + 主机白名单"双校验

```js
isAllowedRedirectHostname(hostname, allowedHostnames); // 支持 *.example.com
isSafeClientRedirectUrl(url, allowedProtocols, allowedHostnames);
```

`Content.vue` 注入 `AGENT_ARENA_REDIRECT_HOSTS = ['openlibing.com','*.openlibing.com','localhost','127.0.0.1']`。保留 `localhost/127.0.0.1` 是为本地联调；生产构建下由后端下发的 `redirect` 通常为正式域名。

### D5：img 过滤改为"显式白名单判定 + 保留合法属性"

```js
isAllowedImgSrc(value) =>
  value.startsWith('data:image/')
  || value.startsWith(`${window.location.origin}/`)
  || (value.startsWith('/') && !value.startsWith('//') && !value.startsWith('/\\'))
```

非白名单返回 `''`（不再回落到 `defaultImgMd`）。`onTag` 重建 img 时按 `whiteList.img` 的 `class/width/height/alt` 复制属性，避免过滤后排版塌陷。

### D6：SSRF 判定补齐 IPv6

`isLocalOrPrivateHost` 在 IPv4 判定之外增加：

| 段              | 含义                              |
| --------------- | --------------------------------- |
| `::1`、`::`     | 环回 / 未指定                     |
| `::ffff:0:0/96` | IPv4-mapped，需解出内嵌 IPv4 再判 |
| `fc00::/7`      | 唯一本地地址（ULA）               |
| `fe80::/10`     | 链路本地                          |

`securityScanning.vue` 与 `add.vue` 两处重复实现必须同步，避免只改一处。

### D7：登录态写入以前置校验替代直接覆盖

```js
if (
  payload &&
  typeof payload === "object" &&
  Array.isArray(payload.permissions) &&
  typeof payload.userName === "string" &&
  payload.userName.length > 0
) {
  app.user = payload;
}
```

对应 CWE-754（异常条件未正确检查）。宁可保留旧登录态，也不用异常响应覆盖。

### D8：凭证输入以交互限制替代可见性

`GlobalConfigDialog.vue` 移除 `show-password`，加 `autocomplete="new-password"`（阻止浏览器自动填充）与 `@copy.prevent @cut.prevent @contextmenu.prevent`。属于纵深防御，不替代后端存储加密。

### D9：删除 vben 内置登录模块

项目已统一走自有登录流程，`_core/authentication/login.vue` 及其 common-ui 组件成为未使用攻击面（含默认文案与演示逻辑）。整体删除并清理 `layouts/basic.vue` 引用，同时移除灵枢菜单入口。

## 交互矩阵

| 场景                                               | 期望行为                                            |
| -------------------------------------------------- | --------------------------------------------------- |
| 浏览器访问任意静态资源                             | 响应含 HSTS、CSP、`X-Frame-Options`、`Vary: Origin` |
| 跨域请求来自 `https://a.openlibing.com`            | `Access-Control-Allow-Origin` 回显该来源            |
| 跨域请求来自 `https://evil.com`                    | `Access-Control-Allow-Origin` 为空，浏览器阻断      |
| 跳转 `redirect=https://evil.com`                   | 被白名单拦截，不跳转                                |
| 富文本含 `<img src="javascript:...">`              | 渲染为空 src                                        |
| 富文本含 `<img src="/a.png" class="x" width="10">` | 正常渲染且保留属性                                  |
| 扫描目标填写 `http://[::ffff:127.0.0.1]/`          | 判定为内网，拒绝提交                                |
| 用户信息接口返回异常结构                           | 登录态保持，不被覆盖                                |
| 公共账号 token 输入框                              | 不可见、不可复制/剪切/右键                          |

## 涉及文件

| 文件                                                                                                                           | 操作 | 说明                                                                                                        |
| ------------------------------------------------------------------------------------------------------------------------------ | ---- | ----------------------------------------------------------------------------------------------------------- |
| `apps/web-openlibing/nginx/nginx_beta.conf`                                                                                    | 修改 | map + 安全头 + `/build` 代理 + 删除 `/aurogon-web`                                                          |
| `apps/web-openlibing/nginx/nginx_gamma.conf`                                                                                   | 修改 | map + 安全头 + 删除 `/aurogon-web`                                                                          |
| `apps/web-openlibing/nginx/nginx_prod.conf`                                                                                    | 修改 | map + 安全头                                                                                                |
| `apps/web-openlibing/nginx/nginx_prod_new.conf`                                                                                | 修改 | map + 安全头                                                                                                |
| `apps/web-openlibing/src/utils/until.js`                                                                                       | 修改 | `isAllowedRedirectHostname`、`isSafeClientRedirectUrl` 三参、`isAllowedImgSrc`、`isLocalOrPrivateHost` IPv6 |
| `apps/web-openlibing/src/views/Content.vue`                                                                                    | 修改 | 跳转主机白名单                                                                                              |
| `apps/web-openlibing/src/views/Login.vue`                                                                                      | 修改 | `client/state/pluginId` 编码                                                                                |
| `apps/web-openlibing/src/views/WujieMiddleware.vue`                                                                            | 修改 | 过滤 `.`/`..` 分段                                                                                          |
| `apps/web-openlibing/src/views/PRManage/list.vue`                                                                              | 修改 | `refreshUser` 守卫                                                                                          |
| `apps/web-openlibing/src/views/InterfaceManage/index.vue`                                                                      | 修改 | 防重复提交                                                                                                  |
| `apps/web-openlibing/src/views/Publish/platformRelease/ltsComponents/publishReviewDetail/transferTesting/securityScanning.vue` | 修改 | SSRF IPv6 + 防重复提交                                                                                      |
| `apps/web-openlibing/src/views/Publish/platformRelease/updateComponents/releaseComponents/add.vue`                             | 修改 | SSRF IPv6 + 防重复提交                                                                                      |
| `apps/web-openlibing/src/views/ToDoCenter/BranchReview.vue`                                                                    | 修改 | `submitting` 防重                                                                                           |
| `apps/web-openlibing/src/views/ToDoCenter/RepoReview.vue`                                                                      | 修改 | `submitting` 防重                                                                                           |
| `apps/web-openlibing/src/views/ToolManagement/MyTool/myToDo.vue`                                                               | 修改 | 防重复提交                                                                                                  |
| `apps/web-openlibing/src/router/routes/modules/noMenu.ts`                                                                      | 修改 | InterfaceReview 补 `auth`                                                                                   |
| `apps/web-openlibing/src/router/routes/modules/menu.ts`                                                                        | 修改 | 移除灵枢入口                                                                                                |
| `apps/web-openlibing/src/views/Repos/dialog/GlobalConfigDialog.vue`                                                            | 修改 | token 输入加固                                                                                              |
| `apps/web-openlibing/src/views/_core/authentication/login.vue`                                                                 | 删除 | vben 内置登录页                                                                                             |
| `packages/@core/base/common-ui/src/ui/authentication/login.vue`                                                                | 删除 | vben 内置登录组件                                                                                           |
| `packages/@core/base/common-ui/src/ui/authentication/index.ts`                                                                 | 修改 | 移除导出                                                                                                    |
| `apps/web-openlibing/src/layouts/basic.vue`                                                                                    | 修改 | 移除内置登录引用                                                                                            |

## 风险与兼容性

| 风险                                       | 影响 | 应对                                                                   |
| ------------------------------------------ | ---- | ---------------------------------------------------------------------- |
| CSP 拦截未白名单的第三方脚本               | 高   | 先在 beta/gamma 验证；新增域名走同一 map 追加                          |
| `X-Frame-Options: SAMEORIGIN` 影响被嵌入   | 中   | 确认无第三方 iframe 嵌入需求                                           |
| `add_header` 重复声明导致遗漏某 location   | 中   | 以"每个含 `add_header` 的 location 必须自带全套安全头"为 review 检查项 |
| img 过滤收紧导致历史富文本图片丢失         | 中   | 白名单已覆盖 `data:image/`、同源、站内相对路径；外链图片需改站内或 CDN |
| IPv6 判定误伤公网 IPv6                     | 低   | 仅限 `::1/::`、mapped、ULA、链路本地四类                               |
| 删除 vben 登录模块引发残留引用             | 低   | 构建期即可暴露未解析导入                                               |
| beta `/build` 代理指向变更影响 cicd 微前端 | 中   | 与 cicd 侧联调确认服务名与端口                                         |

## 验证策略

1. **安全头**：`curl -I https://<beta>/`、`/assets/*.js`、`/api/*` 均返回 HSTS、CSP、`X-Frame-Options`、`Vary: Origin`。
2. **CORS**：带 `Origin: https://a.openlibing.com` 与 `Origin: https://evil.com` 分别请求，检查回显。
3. **开放重定向**：构造 `redirect=https://evil.com`、`javascript:alert(1)`、`//evil.com`，均被拦截。
4. **富文本**：分别注入 `javascript:`、`data:text/html`、`//evil.com/x.png`、`/a.png`、`https://<同源>/b.png`，核对渲染结果与属性保留。
5. **SSRF**：目标填 `[::1]`、`[::ffff:127.0.0.1]`、`[fc00::1]`、`[fe80::1]` 均被拒绝；公网 IPv6 正常。
6. **登录态**：mock 用户信息接口返回 `null`/字符串/缺 `permissions`，确认 `app.user` 不被覆盖。
7. **凭证**：token 输入框尝试复制、右键、查看，均被阻止。
8. **回归**：菜单配置、发布评审、待办中心、工具管理主流程可用。
